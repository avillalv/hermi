# ruff: noqa: E501  (long SQL strings and comments)
import os

import pytest

from hermi.config import refuse_tests_in_production

# Tests never run against production settings (02 section 7.1, ENVIRONMENT).
refuse_tests_in_production()
# ENVIRONMENT has no default; tests run as ci unless the caller says otherwise.
os.environ.setdefault("ENVIRONMENT", "ci")
# Tests never use a real AI provider (CLAUDE rules: AI_PROVIDER=fake).
os.environ["AI_PROVIDER"] = "fake"


@pytest.fixture(autouse=True)
def _no_root_env(monkeypatch, tmp_path):
    # A developer's root .env must not leak into create_app() or cli tests.
    monkeypatch.setattr("hermi.config.ROOT_ENV_FILE", tmp_path / "no-such.env")


# --- shared database fixtures (a real PostgreSQL 18 prepared by `npm run db:init`) -------------------------------------


def _db_urls() -> dict[str, str]:
    urls = {
        "migrate": os.environ.get("TEST_MIGRATION_DATABASE_URL"),
        "app": os.environ.get("TEST_DATABASE_URL"),
        "system": os.environ.get("TEST_DATABASE_URL_SYSTEM"),
    }
    if all(urls.values()):
        return urls
    msg = "TEST_MIGRATION_DATABASE_URL, TEST_DATABASE_URL and TEST_DATABASE_URL_SYSTEM are not set (npm run test:api loads them from .env)"
    if os.environ.get("CI"):
        pytest.fail(msg)
    pytest.skip(msg)


@pytest.fixture(scope="module")
def db_urls():
    """The three test database URLs, with the schema migrated to head from empty."""
    from alembic import command
    from tests.test_migrations import _alembic_cfg

    urls = _db_urls()
    cfg = _alembic_cfg(urls["migrate"])
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return urls


@pytest.fixture
def system_conn(db_urls):
    """Autocommit connection as the worker login (BYPASSRLS): for arranging rows, never for assertions about tenants."""
    import psycopg

    from hermi import db

    with psycopg.connect(db.psycopg_url(db_urls["system"]), autocommit=True) as c:
        yield c


@pytest.fixture
def make_user(system_conn):
    """make_user(status='active', provider='email') -> (user_id, subject): a users row plus its auth_identities row."""
    import uuid

    def make(status="active", provider="email", subject=None):
        subject = subject or uuid.uuid4().hex
        extra = {"suspended": ", suspended_at", "deleted": ", deleted_at"}.get(status, "")
        extra_val = ", now()" if extra else ""
        uid = system_conn.execute(
            f"INSERT INTO users (email, display_name, status{extra}) VALUES (%s, 'T', %s{extra_val}) RETURNING id",
            (f"{subject[:10]}@example.com", status),
        ).fetchone()[0]
        system_conn.execute(
            "INSERT INTO auth_identities (user_id, provider, subject) VALUES (%s, %s, %s)",
            (uid, provider, subject),
        )
        return uid, subject

    return make


@pytest.fixture(autouse=True)
def _rate_limit_test_hook():
    """Many tests create accounts from one test-client IP, so signup_ip is lifted here. test_rate_limit.py clears it."""
    from hermi.security import rate_limit

    rate_limit.reset_cache()
    rate_limit.TEST_LIMITS = {"signup_ip": 100000}
    yield
    rate_limit.TEST_LIMITS = {}
