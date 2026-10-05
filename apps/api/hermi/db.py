"""Database helpers shared by migrations, startup checks and tests (03 sections 2, 6.1, 10).

Connection strings come from the environment (hermi.config), never from this file.
"""

import logging
import secrets
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

# Roles that infra/db/bootstrap.sql creates (03 section 6.1). Migration 0001 checks them.
REQUIRED_ROLES = (
    "hermi_owner",
    "hermi_app",
    "hermi_worker",
    "hermi_admin",
    "hermi_definer",
    "hermi_migrate_login",
    "hermi_api_login",
    "hermi_worker_login",
    "hermi_admin_login",
)

# One migration at a time, across every process (03 section 10).
MIGRATION_LOCK_KEY = 0x4D494752  # "MIGR", the key 02-architecture.md and render.yaml name

# 03 says lock 3s, 02 section 12 says 5s: 3s kept (03 owns the schema). Statement limit per 02.
LOCK_TIMEOUT = "3s"
STATEMENT_TIMEOUT = "60s"


class MigrationError(Exception):
    """A migration precondition failed. The message says what to do."""


def psycopg_url(url: str) -> str:
    """Turn a SQLAlchemy style URL (postgresql+psycopg://) into one psycopg accepts."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def sqlalchemy_url(url: str) -> str:
    """Make sure the URL names the psycopg 3 driver."""
    return (
        url
        if "+psycopg" in url.split("://", 1)[0]
        else url.replace("postgresql://", "postgresql+psycopg://", 1)
    )


def uuid7() -> uuid.UUID:
    """A time-ordered UUIDv7 (RFC 9562), for tests and code that needs an id before insert.

    PostgreSQL 18 has uuidv7() for column defaults; Python 3.13 has no uuid7.
    """
    ms = time.time_ns() // 1_000_000
    rand = secrets.randbits(74)  # 12 bits rand_a, 62 bits rand_b
    value = (
        (ms & (2**48 - 1)) << 80
        | 0x7 << 76
        | (rand >> 62) << 64
        | 0b10 << 62
        | (rand & (2**62 - 1))
    )
    return uuid.UUID(int=value)


def assert_roles_exist(connection, roles=None) -> None:
    """Stop with a clear message when a bootstrap role is missing. Never creates one."""
    roles = REQUIRED_ROLES if roles is None else roles
    rows = connection.exec_driver_sql(
        "SELECT r FROM unnest(%s::text[]) AS r WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r)",
        (list(roles),),
    )
    missing = [r[0] for r in rows]
    if missing:
        raise MigrationError(
            f"Missing database roles: {', '.join(missing)}. Run `npm run db:init` first, then migrate again."
        )


def assert_single_head(script) -> str:
    """Two heads means two open revisions. Return the head, or raise."""
    heads = script.get_heads()
    if len(heads) != 1:
        raise MigrationError(
            f"Expected exactly one Alembic head, found {len(heads)}: {', '.join(heads)}"
        )
    return heads[0]


def assert_app_login_is_safe(connection) -> None:
    """Refuse an app connection that could bypass row-level security (03 6.5).

    open_app_engine calls it, then assert_rls_forced, when the API starts.
    """
    unsafe = connection.exec_driver_sql(
        "SELECT r.rolsuper OR r.rolbypassrls "
        "OR EXISTS (SELECT 1 FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p') "
        "AND (c.relowner = r.oid OR pg_has_role(r.oid, c.relowner, 'member'))) AS unsafe "
        "FROM pg_roles r WHERE r.rolname = current_user"
    ).scalar()
    if unsafe:
        raise MigrationError(
            "The app connection must not be a superuser, a BYPASSRLS role, or own or be a member of the owner of any table in public."
        )


# Tables 03 section 6.5 closes by grants instead of RLS.
RLS_EXEMPT_TABLES = frozenset({"admin_users", "deletion_requests", "affiliate_conversions", "provider_calls"})
# Deny-all tables: RLS on with no policy, and no trip_id or user_id column to find them by.
RLS_DENY_ALL_TABLES = frozenset({"identity_hashes", "device_attestations", "guest_allowances"})


def assert_rls_forced(connection) -> None:
    """Refuse to start when a tenant table lacks ENABLE or FORCE row-level security (03 6.5).

    A table counts as tenant when it has a trip_id or user_id column, has a policy, has RLS on,
    or is a named deny-all table. That also catches trips, users and people.
    """
    rows = connection.exec_driver_sql(
        "SELECT c.relname FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p') "
        "AND NOT c.relispartition AND NOT (c.relrowsecurity AND c.relforcerowsecurity) "
        "AND (c.relrowsecurity OR c.relname = ANY(%(deny)s) "
        "OR EXISTS (SELECT 1 FROM pg_policies p WHERE p.schemaname = 'public' AND p.tablename = c.relname) "
        "OR EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attname IN ('trip_id', 'user_id') AND NOT a.attisdropped)) "
        "ORDER BY 1",
        {"deny": sorted(RLS_DENY_ALL_TABLES)},
    )
    bad = [r[0] for r in rows if r[0] not in RLS_EXEMPT_TABLES]
    if bad:
        raise MigrationError(f"Row-level security is not enabled and forced on: {', '.join(bad)}.")


def make_engine(url: str, *, pool_size: int = 5, max_overflow: int = 2, statement_timeout_ms: int = 15000) -> Engine:
    return create_engine(
        sqlalchemy_url(url),
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        connect_args={"options": f"-c statement_timeout={int(statement_timeout_ms)}"},
    )


def open_app_engine(settings) -> Engine:
    """The API engine (DATABASE_URL, hermi_api_login). Refuses a login that could bypass row-level security."""
    engine = make_engine(
        settings.require("DATABASE_URL"),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        statement_timeout_ms=settings.database_statement_timeout_ms,
    )
    try:
        with engine.connect() as conn:
            assert_app_login_is_safe(conn)
            assert_rls_forced(conn)
    except Exception:
        engine.dispose()
        raise
    return engine


@contextmanager
def request_transaction(engine: Engine, user_id: uuid.UUID) -> Iterator[Session]:
    """One transaction per request. app.user_id is transaction-local, so it dies with the commit or rollback
    and cannot leak to the next request on a pooled connection (02 section 3 step 4)."""
    with Session(engine) as session:
        try:
            session.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": str(user_id)})
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise


# The purposes that may open a SystemSession: the ten in 03 section 6.6 plus dev_session (local and ci only).
# Adding one is a reviewed change to this constant, the 6.6 table and the test.
SYSTEM_SESSION_ALLOWLIST = frozenset(
    {
        "share_view",
        "share_report",
        "share_outbound",
        "go_redirect",
        "calendar_feed",
        "sample_read",
        "billing_sync",
        "import_preview",
        "verify_extract",
        "places_cache",
        "fare_refresh",
        "dev_session",
    }
)

_system_engines: dict[str, Engine] = {}
_system_log = logging.getLogger("hermi.system_session")


def dispose_system_engines() -> None:
    while _system_engines:
        _system_engines.popitem()[1].dispose()


@contextmanager
def system_session(
    purpose: str, *, settings, route: str, caller: str | None = None
) -> Iterator[Session]:
    """The only place the worker login (DATABASE_URL_SYSTEM, BYPASSRLS) is opened for a request (03 section 6.6).

    The engine is built once from settings and kept. A purpose off the allowlist raises. Every use logs the
    purpose, the route and the caller (a user id, or "anonymous")."""
    if purpose not in SYSTEM_SESSION_ALLOWLIST:
        raise PermissionError(f"{purpose!r} may not open a SystemSession")
    url = settings.require("DATABASE_URL_SYSTEM")
    if url not in _system_engines:
        _system_engines[url] = make_engine(url, pool_size=2, max_overflow=0)
    _system_log.info(
        "system_session",
        extra={"purpose": purpose, "route": route, "caller": caller or "anonymous"},
    )
    with Session(_system_engines[url]) as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
