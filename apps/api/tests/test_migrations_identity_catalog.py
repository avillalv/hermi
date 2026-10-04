"""WF-012.1: revisions 0002_identity and 0003_reference_catalog (03 sections 5.1 to 5.3, 10).

Constraints are exercised as the migrate login (the owner) at PRE_RLS, before 0014_rls binds it.
"""

import psycopg
import pytest
import sqlalchemy as sa
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy.dialects.postgresql import DOMAIN
from tests.test_migrations import MIGRATE_URL, PRE_RLS, _alembic_cfg, _need_db

from hermi import db
from hermi.modules.auth import models as _auth  # noqa: F401  (register on Base.metadata)
from hermi.modules.base import Base
from hermi.modules.catalog import models as _catalog  # noqa: F401
from hermi.modules.collaboration import models as _collab  # noqa: F401
from hermi.modules.trips import models as _trips  # noqa: F401


@pytest.fixture
def conn():
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, PRE_RLS)
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as c:
        yield c


def _fails(c, exc, sql, *params):
    with pytest.raises(exc):
        c.execute(sql, params)


def test_chain_is_linear_0001_0002_0003():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0002_identity").down_revision == "0001_setup"
    assert s.get_revision("0003_reference_catalog").down_revision == "0002_identity"


def test_tables_types_and_functions_exist(conn):
    tables = {
        r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    }
    assert {
        "users",
        "auth_identities",
        "device_attestations",
        "guest_allowances",
        "devices",
        "airports",
        "fx_rates",
        "places_cache",
        "plans",
        "store_products",
        "credit_action_prices",
    } <= tables
    types = conn.execute("SELECT to_regtype('user_status'), to_regtype('ai_action')").fetchone()
    assert all(t is not None for t in types)
    funcs = conn.execute(
        "SELECT to_regproc('fx_convert_minor'), to_regproc('spend_guest_allowance')"
    ).fetchone()
    assert all(f is not None for f in funcs)


def test_round_trip_drops_everything_added(conn):
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0001_setup")
    assert (
        conn.execute(
            "SELECT to_regclass('users'), to_regclass('plans'), to_regtype('ai_action'), "
            "to_regtype('user_status'), to_regproc('fx_convert_minor'), to_regproc('spend_guest_allowance')"  # noqa: E501
        ).fetchone()
        == (None,) * 6
    )
    command.upgrade(cfg, PRE_RLS)
    assert conn.execute("SELECT to_regclass('users')").fetchone()[0]


def _user(c, email="a@example.com"):
    return c.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (email,)).fetchone()[0]


def test_users_defaults_and_checks(conn):
    uid = _user(conn)
    assert uid.version == 7
    assert conn.execute(
        "SELECT status, home_currency, home_airports::text[], prefs FROM users WHERE id = %s",
        (uid,),
    ).fetchone() == ("active", "USD", [], {})
    _fails(
        conn,
        psycopg.errors.CheckViolation,
        "INSERT INTO users (email, status) VALUES ('d@example.com', 'deleted')",
    )
    _fails(
        conn,
        psycopg.errors.CheckViolation,
        "INSERT INTO users (email, status) VALUES ('s@example.com', 'suspended')",
    )
    _fails(
        conn,
        psycopg.errors.CheckViolation,
        "INSERT INTO users (email, display_name) VALUES ('n@example.com', repeat('x', 81))",
    )
    # Email is unique (case-insensitive) among live users only.
    _fails(
        conn, psycopg.errors.UniqueViolation, "INSERT INTO users (email) VALUES ('A@EXAMPLE.com')"
    )
    conn.execute("UPDATE users SET status = 'deleted', deleted_at = now() WHERE id = %s", (uid,))
    _user(conn)


def test_users_updated_at_trigger(conn):
    uid = _user(conn)
    conn.execute("UPDATE users SET updated_at = '2000-01-01' WHERE id = %s", (uid,))
    assert conn.execute(
        "SELECT updated_at > '2001-01-01' FROM users WHERE id = %s", (uid,)
    ).fetchone() == (True,)


def test_auth_identities_constraints_and_cascade(conn):
    uid = _user(conn)
    ins = "INSERT INTO auth_identities (user_id, provider, subject) VALUES (%s, %s, %s)"
    conn.execute(ins, (uid, "apple", "s1"))
    _fails(conn, psycopg.errors.UniqueViolation, ins, uid, "apple", "s1")
    _fails(conn, psycopg.errors.CheckViolation, ins, uid, "github", "s2")
    conn.execute("DELETE FROM users WHERE id = %s", (uid,))
    assert conn.execute("SELECT count(*) FROM auth_identities").fetchone() == (0,)


def test_attestations_and_guest_allowances(conn):
    ins = "INSERT INTO device_attestations (key_id, public_key, environment) VALUES (%s, %s, %s)"
    conn.execute(ins, ("k1", b"pk", "production"))
    _fails(conn, psycopg.errors.CheckViolation, ins, "k2", b"pk", "staging")
    ga = "INSERT INTO guest_allowances (key_id, period_key, credits_used) VALUES (%s, %s, %s)"
    _fails(conn, psycopg.errors.CheckViolation, ga, "k1", "2026-13", 0)
    _fails(conn, psycopg.errors.CheckViolation, ga, "k1", "2026-01", -1)
    conn.execute(ga, ("k1", "2026-01", 0))
    _fails(conn, psycopg.errors.UniqueViolation, ga, "k1", "2026-01", 0)
    conn.execute("DELETE FROM device_attestations WHERE key_id = 'k1'")
    assert conn.execute("SELECT count(*) FROM guest_allowances").fetchone() == (0,)


def test_spend_guest_allowance(conn):
    conn.execute(
        "INSERT INTO device_attestations (key_id, public_key, environment) VALUES ('k', 'pk', 'development')"  # noqa: E501
    )
    # Table grants for the definer land in 0014_rls; give them here so the function body can run.
    conn.execute("GRANT SELECT, INSERT, UPDATE ON guest_allowances TO hermi_definer")
    spend = "SELECT spend_guest_allowance('k', %s, 5)"
    assert conn.execute(spend, (3,)).fetchone() == (True,)
    assert conn.execute(spend, (3,)).fetchone() == (False,)
    assert conn.execute(spend, (2,)).fetchone() == (True,)
    assert conn.execute("SELECT credits_used FROM guest_allowances").fetchone() == (5,)
    _fails(conn, psycopg.errors.InvalidParameterValue, spend, 0)


def test_devices_constraints(conn):
    uid = _user(conn)
    ins = "INSERT INTO devices (user_id, platform, push_token, push_environment) VALUES (%s, %s, %s, %s)"  # noqa: E501
    conn.execute(ins, (uid, "ios", "t1", "sandbox"))
    _fails(conn, psycopg.errors.UniqueViolation, ins, uid, "ios", "t1", "sandbox")
    conn.execute(ins, (uid, "web", "t1", None))
    _fails(conn, psycopg.errors.CheckViolation, ins, uid, "windows", None, None)
    _fails(conn, psycopg.errors.CheckViolation, ins, uid, "ios", "t2", "beta")
    # A revoked device frees its push token.
    conn.execute("UPDATE devices SET revoked_at = now() WHERE platform = 'ios'")
    conn.execute(ins, (uid, "ios", "t1", "sandbox"))


def test_airports_fx_places_cache_checks(conn):
    air = "INSERT INTO airports (iata, name, country_code, lat, lon, kind) VALUES (%s, 'n', 'US', 0, 0, %s)"  # noqa: E501
    conn.execute(air, ("JFK", "large_airport"))
    _fails(conn, psycopg.errors.CheckViolation, air, "XXX", "heliport")
    _fails(conn, psycopg.errors.CheckViolation, air, "jfk", "large_airport")
    fx = "INSERT INTO fx_rates (currency, per_eur, rate_date) VALUES (%s, %s, '2026-01-01')"
    _fails(conn, psycopg.errors.CheckViolation, fx, "USD", 0)
    pc = (
        "INSERT INTO places_cache (key, provider, kind, response, expires_at) "
        "VALUES (repeat('a', 64), %s, %s, '{}', now())"
    )
    _fails(conn, psycopg.errors.CheckViolation, pc, "google", "geocode")
    _fails(conn, psycopg.errors.CheckViolation, pc, "geoapify", "nope")
    conn.execute(pc, ("geoapify", "geocode"))


def test_fx_convert_minor(conn):
    conn.execute(
        "INSERT INTO fx_rates (currency, per_eur, rate_date) "
        "VALUES ('USD', 1.25, '2026-01-01'), ('JPY', 150, '2026-01-01')"
    )
    q = "SELECT fx_convert_minor(%s, %s, %s)"
    assert conn.execute(q, (1000, "USD", "USD")).fetchone() == (1000,)
    assert conn.execute(q, (1000, "EUR", "USD")).fetchone() == (1250,)  # 10.00 EUR to 12.50 USD
    assert conn.execute(q, (1250, "USD", "EUR")).fetchone() == (1000,)
    assert conn.execute(q, (1000, "EUR", "JPY")).fetchone() == (
        1500,
    )  # 10.00 EUR to 1500 JPY, exponent 0
    assert conn.execute(q, (1000, "EUR", "GBP")).fetchone() == (None,)  # missing rate
    assert conn.execute(q, (1000, "GBP", "EUR")).fetchone() == (None,)


def test_plans_store_products_credit_prices(conn):
    plan = "INSERT INTO plans (code, kind, name, duration_days) VALUES (%s, %s, 'n', %s)"
    conn.execute(plan, ("free", "tier", None))
    _fails(conn, psycopg.errors.CheckViolation, plan, "x", "bundle", None)
    _fails(conn, psycopg.errors.CheckViolation, plan, "tp", "pass", None)
    conn.execute(plan, ("tp", "pass", 90))
    sp = "INSERT INTO store_products (product_id, store, plan_code, period, price_minor) VALUES (%s, %s, %s, %s, %s)"  # noqa: E501
    conn.execute(sp, ("p1", "apple", "free", "month", 0))
    _fails(conn, psycopg.errors.CheckViolation, sp, "p2", "stripe", "free", "month", 1)
    _fails(conn, psycopg.errors.CheckViolation, sp, "p3", "apple", "free", "week", 1)
    _fails(conn, psycopg.errors.CheckViolation, sp, "p4", "apple", "free", "month", -1)
    _fails(conn, psycopg.errors.ForeignKeyViolation, sp, "p5", "apple", "nope", "month", 1)
    _fails(conn, psycopg.errors.RestrictViolation, "DELETE FROM plans WHERE code = 'free'")
    cap = "INSERT INTO credit_action_prices (action, credits, hard_stop_micros) VALUES (%s, %s, %s)"
    conn.execute(cap, ("explain", 1, 10))
    _fails(conn, psycopg.errors.CheckViolation, cap, "research", 0, 10)
    _fails(conn, psycopg.errors.CheckViolation, cap, "research", 1, 0)
    _fails(conn, psycopg.errors.InvalidTextRepresentation, cap, "bogus", 1, 10)
    assert [r[0] for r in conn.execute("SELECT unnest(enum_range(NULL::ai_action))")] == [
        "explain",
        "live_search",
        "draft_day",
        "draft_trip",
        "research",
        "agent_run",
        "verify_plan",
    ]


_ALIASES = {
    "largebinary": "bytea",
    "biginteger": "bigint",
    "smallinteger": "smallint",
    "float": "doubleprecision",
}


def _family(t):
    """Type family: enum name for enums, else the lowercase SQL type name without length."""
    if isinstance(t, DOMAIN):  # reflected domains (currency_code, iata_code) compare by base type
        return _family(t.data_type)
    if isinstance(t, sa.ARRAY):
        return f"{_family(t.item_type)}[]"
    if isinstance(t, sa.Enum):
        return f"enum:{t.name}"
    name = type(t).__visit_name__.lower().replace("_", "")
    return _ALIASES.get(name, name)


def test_orm_columns_match_ddl(conn):
    """Columns only: names, nullability and type family of every mapped table vs the live schema."""
    eng = sa.create_engine(db.sqlalchemy_url(MIGRATE_URL))
    try:
        insp = sa.inspect(eng)
        assert Base.metadata.tables
        for name, table in Base.metadata.tables.items():
            live = {c["name"]: c for c in insp.get_columns(name)}
            assert set(table.columns.keys()) == set(live), name
            for col in table.columns:
                got = live[col.name]
                where = f"{name}.{col.name}"
                # Primary keys are NOT NULL in the DDL even when the mapping omits it.
                assert (col.nullable and not col.primary_key) == got["nullable"], where
                assert _family(col.type) == _family(got["type"]), where
    finally:
        eng.dispose()
