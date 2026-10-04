"""WF-011: migration framework, roles and migration 0001 (03 sections 3, 6.1, 10).

Needs PostgreSQL 18 with the roles from `npm run db:init`. The process environment must hold
TEST_MIGRATION_DATABASE_URL (hermi_migrate_login, runs the chain) and TEST_DATABASE_URL
(hermi_api_login, every assertion about what the app can do). `npm run test:api` loads both.
"""

import os
import re
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.exc import OperationalError

from hermi import db

API_DIR = Path(__file__).resolve().parents[1]
MIGRATE_URL = os.environ.get("TEST_MIGRATION_DATABASE_URL")
APP_URL = os.environ.get("TEST_DATABASE_URL")
# The last revision before 0014_rls. Constraint tests run as the owner, which FORCE row-level security binds from 0014 on.
PRE_RLS = "0013_notifications_samples"


def _alembic_cfg(url: str | None = None) -> Config:
    cfg = Config(str(API_DIR / "alembic.ini"))
    if url:
        cfg.attributes["database_url"] = url
    return cfg


def test_single_alembic_head():
    # No database needed: two heads fail here and in the CI "Single head" step.
    heads = ScriptDirectory.from_config(_alembic_cfg()).get_heads()
    assert len(heads) == 1


def test_head_check_rejects_two_heads():
    assert db.assert_single_head(SimpleNamespace(get_heads=lambda: ["0001_setup"])) == "0001_setup"
    with pytest.raises(db.MigrationError, match="exactly one Alembic head"):
        db.assert_single_head(SimpleNamespace(get_heads=lambda: ["a", "b"]))


def test_uuid7_is_version_7_and_time_ordered():
    a, b = db.uuid7(), db.uuid7()
    assert a.version == 7 and b.version == 7 and a.variant == "specified in RFC 4122"
    assert a != b
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", str(a)
    )


def _need_db():
    if MIGRATE_URL and APP_URL:
        return
    msg = "TEST_MIGRATION_DATABASE_URL and TEST_DATABASE_URL are not set (run npm run db:init, then npm run test:api)"
    if os.environ.get("CI"):
        pytest.fail(msg)
    pytest.skip(msg)


@pytest.fixture
def migrated():
    """hermi_test at 0001, from empty. The migrate login owns the schema, so it resets it."""
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return cfg


def _app():
    return psycopg.connect(db.psycopg_url(APP_URL), autocommit=True)


def test_upgrade_from_empty_creates_shared_setup(migrated):
    with _app() as c:
        fns = {
            r[0]
            for r in c.execute(
                "SELECT proname FROM pg_proc WHERE pronamespace = 'public'::regnamespace"
            )
        }
        assert {
            "set_updated_at",
            "add_updated_at_trigger",
            "bump_version",
            "add_version_trigger",
            "currency_exponent",
            "app_user_id",
        } <= fns
        assert c.execute(
            "SELECT currency_exponent('JPY'), currency_exponent('USD'), currency_exponent('KWD')"
        ).fetchone() == (0, 2, 3)
        assert c.execute("SELECT app_user_id()").fetchone() == (None,)
        assert c.execute("SELECT extname FROM pg_extension WHERE extname = 'citext'").fetchone()
        doms = {
            r[0]
            for r in c.execute(
                "SELECT typname FROM pg_type WHERE typtype = 'd' AND typnamespace = 'public'::regnamespace"
            )
        }
        assert {"currency_code", "iata_code", "country_code2", "hex_color"} <= doms
        with pytest.raises(psycopg.errors.CheckViolation):
            c.execute("SELECT 'usd'::currency_code")
        assert c.execute("SELECT uuidv7()").fetchone()[0].version == 7
        # Helpers are owned by the owner role, which migrations run as.
        owner = c.execute(
            "SELECT pg_get_userbyid(proowner) FROM pg_proc WHERE proname = 'app_user_id'"
        ).fetchone()
        assert owner == ("hermi_owner",)


def test_helper_triggers_work(migrated):
    # Migrate login (owner) builds a scratch table; the app login must not be able to.
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as c:
        c.execute(
            "CREATE TABLE _t0001 (id int PRIMARY KEY, version int NOT NULL DEFAULT 1, "
            "updated_at timestamptz NOT NULL DEFAULT '2000-01-01')"
        )
        try:
            c.execute("SELECT add_updated_at_trigger('_t0001'), add_version_trigger('_t0001')")
            c.execute("INSERT INTO _t0001 (id) VALUES (1)")
            c.execute("UPDATE _t0001 SET id = 1")
            version, fresh = c.execute(
                "SELECT version, updated_at > '2001-01-01' FROM _t0001"
            ).fetchone()
            assert (version, fresh) == (2, True)
        finally:
            c.execute("DROP TABLE _t0001")


def test_upgrade_is_repeatable_and_reversible(migrated):
    command.upgrade(migrated, "head")  # already at head: no-op
    command.downgrade(migrated, "base")
    command.upgrade(migrated, "head")


def test_app_login_cannot_run_ddl(migrated):
    with _app() as c:
        row = c.execute(
            "SELECT rolsuper, rolbypassrls, pg_has_role(current_user, 'hermi_owner', 'member'), "
            "pg_has_role(current_user, 'hermi_app', 'member') FROM pg_roles "
            "WHERE rolname = current_user"
        ).fetchone()
        assert row == (False, False, False, True)
        assert c.execute("SELECT current_user").fetchone() == ("hermi_api_login",)
        for ddl in (
            "CREATE TABLE _nope (id int)",
            "CREATE FUNCTION _nope() RETURNS int LANGUAGE sql AS 'SELECT 1'",
            "CREATE SCHEMA _nope",
            "DROP FUNCTION app_user_id()",
            "ALTER FUNCTION app_user_id() RENAME TO _nope",
            "CREATE DOMAIN _nope AS int",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                c.execute(ddl)
        # It may still call the helpers (a plain function with the default EXECUTE grant).
        assert c.execute("SELECT currency_exponent('EUR')").fetchone() == (2,)


def test_missing_role_stops_with_db_init_message(monkeypatch):
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    monkeypatch.setattr(
        db, "REQUIRED_ROLES", (*db.REQUIRED_ROLES, "hermi_role_that_does_not_exist")
    )
    with pytest.raises(db.MigrationError, match=r"npm run db:init") as exc:
        command.upgrade(cfg, "head")
    assert "hermi_role_that_does_not_exist" in str(exc.value)
    # The failed migration rolled back: nothing was created.
    with _app() as c:
        assert c.execute("SELECT to_regproc('app_user_id')").fetchone() == (None,)
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as m:
        if m.execute("SELECT to_regclass('alembic_version')").fetchone()[0] is not None:
            assert m.execute("SELECT count(*) FROM alembic_version").fetchone() == (0,)
    monkeypatch.undo()
    command.upgrade(cfg, "head")


def test_no_migration_creates_roles():
    text = "\n".join(
        p.read_text(encoding="utf-8") for p in (API_DIR / "hermi/migrations").rglob("*.py")
    )
    assert not re.search(r"CREATE ROLE|ALTER ROLE", text, re.I)


def test_second_migrator_waits_on_advisory_lock_then_fails_fast(migrated):
    command.downgrade(migrated, "base")
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as holder:
        holder.execute("SELECT pg_advisory_lock(%s)", (db.MIGRATION_LOCK_KEY,))
        with pytest.raises(OperationalError, match="lock timeout"):
            command.upgrade(migrated, "head")
        holder.execute("SELECT pg_advisory_unlock(%s)", (db.MIGRATION_LOCK_KEY,))
    command.upgrade(migrated, "head")


def test_app_login_safety_check(migrated):
    from sqlalchemy import create_engine

    with create_engine(db.sqlalchemy_url(APP_URL)).connect() as c:
        db.assert_app_login_is_safe(c)
    with create_engine(db.sqlalchemy_url(MIGRATE_URL)).connect() as c:
        with pytest.raises(db.MigrationError, match="app connection"):
            db.assert_app_login_is_safe(c)


def test_cli_migrate_upgrades_to_head(migrated, monkeypatch):
    from hermi import cli

    command.downgrade(migrated, "base")
    monkeypatch.setenv("MIGRATION_DATABASE_URL", MIGRATE_URL)
    cli.main(["migrate"])
    with _app() as c:
        assert c.execute("SELECT to_regproc('app_user_id')").fetchone() != (None,)
