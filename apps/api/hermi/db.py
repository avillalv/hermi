"""Database helpers shared by migrations, startup checks and tests (03 sections 2, 6.1, 10).

Connection strings come from the environment (hermi.config), never from this file.
"""

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

    open_app_engine calls it when the API starts.
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
