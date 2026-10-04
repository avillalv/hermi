# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-022.2: revision 0006_billing_credits (03 sections 5.7, 5.8, 10).

Constraints are exercised as the migrate login (the owner), because grants land in 0014_rls.
The schema-vs-DDL comparison for 5.7 and 5.8 lives in test_migrations_trips_people.py (it spans 0002 to 0006).
"""

import uuid

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import MIGRATE_URL, _alembic_cfg, _need_db

from hermi import db

TABLES = (
    "store_transactions subscriptions entitlements trip_passes webhook_events credit_grants credit_ledger "
    "credit_debts identity_hashes credit_balances"
).split()
FUNCS = (
    "identity_hashes_for assert_credit_caller reserve_credits settle_credits release_stale_reservations "
    "expire_credit_grants record_credit_debt settle_credit_debt ensure_free_monthly_grant ensure_taster_grant "
    "credit_ledger_immutable"
).split()


@pytest.fixture
def conn():
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as c:
        yield c


def _user(c, verified=False):
    return c.execute(
        "INSERT INTO users (email, email_verified_at) VALUES (%s, CASE WHEN %s THEN now() END) RETURNING id",
        (f"{uuid.uuid4().hex[:8]}@example.com", verified),
    ).fetchone()[0]


def _trip(c, owner):
    return c.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)
    ).fetchone()[0]


def _grant(c, user, credits=10, kind="purchase", **kw):
    cols = {"user_id": user, "kind": kind, "credits": credits, "remaining": credits, **kw}
    return c.execute(
        f"INSERT INTO credit_grants ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id",
        tuple(cols.values()),
    ).fetchone()[0]


def _txn(c, tid="t1", kind="pass"):
    return c.execute(
        "INSERT INTO store_transactions (store, store_transaction_id, kind, purchased_at) VALUES ('apple', %s, %s, now()) RETURNING id",
        (tid, kind),
    ).fetchone()[0]


def _plans(c):
    """Seeds arrive in a later revision, so the tests insert the plan rows they need."""
    c.execute(
        "INSERT INTO plans (code, kind, name, monthly_credits, limits) VALUES ('free', 'tier', 'Free', 12, '{\"taster_agent_runs\": 1}') "
        "ON CONFLICT DO NOTHING"
    )
    c.execute("INSERT INTO plans (code, kind, name, duration_days) VALUES ('trip_pass', 'pass', 'Trip Pass', 90) ON CONFLICT DO NOTHING")
    c.execute("INSERT INTO credit_action_prices (action, credits, hard_stop_micros) VALUES ('agent_run', 40, 800000) ON CONFLICT DO NOTHING")


def _remaining(c, g):
    return c.execute("SELECT remaining FROM credit_grants WHERE id = %s", (g,)).fetchone()[0]


def test_chain_is_linear_and_single_head():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0006_billing_credits").down_revision == "0005_ai"
    assert len(s.get_heads()) == 1


def test_objects_exist_and_round_trip(conn):
    for n in TABLES:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n
    for f in FUNCS:
        assert conn.execute("SELECT count(*) FROM pg_proc WHERE proname = %s", (f,)).fetchone()[0] == 1, f
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0005_ai")
    assert conn.execute(
        "SELECT to_regclass('credit_ledger'), to_regclass('trip_passes'), to_regtype('pass_status')"
    ).fetchone() == (None,) * 3
    assert conn.execute("SELECT count(*) FROM pg_proc WHERE proname = ANY(%s)", (FUNCS,)).fetchone() == (0,)
    command.upgrade(cfg, "head")
    assert conn.execute("SELECT to_regclass('credit_ledger')").fetchone()[0]


def test_store_transaction_and_webhook_event_uniqueness(conn):
    _txn(conn, "a")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _txn(conn, "a")
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO store_transactions (store, store_transaction_id, kind, purchased_at) VALUES ('google', 'g', 'pass', now())"
        )
    ins = "INSERT INTO webhook_events (provider, event_id, event_type, payload) VALUES (%s, %s, 'x', '{}')"
    conn.execute(ins, ("revenuecat", "e1"))
    conn.execute(ins, ("resend", "e1"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, ("revenuecat", "e1"))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(ins, ("stripe", "e2"))
    conn.execute(ins + " ON CONFLICT DO NOTHING", ("revenuecat", "e1"))


def test_one_active_trip_pass_per_trip_and_sources(conn):
    _plans(conn)
    owner = _user(conn)
    tid = _trip(conn, owner)
    ins = (
        "INSERT INTO trip_passes (trip_id, purchaser_user_id, plan_code, source, expires_at) "
        "VALUES (%s, %s, 'trip_pass', %s, now() + interval '90 days') RETURNING id"
    )
    first = conn.execute(ins, (tid, owner, "purchase")).fetchone()[0]
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, (tid, owner, "import_reward"))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(ins, (_trip(conn, owner), owner, "gift"))
    conn.execute("UPDATE trip_passes SET status = 'expired' WHERE id = %s", (first,))
    conn.execute(ins, (tid, owner, "import_reward"))
    assert conn.execute(
        "SELECT credits_granted, live_checks_max FROM trip_passes WHERE id = %s", (first,)
    ).fetchone() == (40, 60)


def test_credit_ledger_is_append_only(conn):
    u = _user(conn)
    g = _grant(conn, u)
    lid = conn.execute(
        "INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta) VALUES (%s, %s, 'grant', 10) RETURNING id",
        (u, g),
    ).fetchone()[0]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE credit_ledger SET delta = 11 WHERE id = %s", (lid,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("DELETE FROM credit_ledger WHERE id = %s", (lid,))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO credit_ledger (user_id, entry_type, delta) VALUES (%s, 'reserve', -1)", (u,))
    # The anonymizing update is allowed: account deletion nulls user_id.
    conn.execute("UPDATE credit_ledger SET user_id = NULL WHERE id = %s", (lid,))
    assert conn.execute("SELECT user_id FROM credit_ledger WHERE id = %s", (lid,)).fetchone() == (None,)


def test_credit_grant_rules(conn):
    u = _user(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        _grant(conn, u, remaining=11)
    with pytest.raises(psycopg.errors.CheckViolation):
        _grant(conn, u, kind="trip_pass")
    _grant(conn, u, kind="monthly", period_key="2026-10")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _grant(conn, u, kind="monthly", period_key="2026-10")
    t = _txn(conn, "pack1", "credit_pack")
    _grant(conn, u, store_transaction_id=t)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _grant(conn, u, store_transaction_id=t)


def test_reserve_settle_and_idempotency(conn):
    u = _user(conn)
    trip = _trip(conn, u)
    monthly = _grant(conn, u, 5, "monthly", period_key="2026-10")
    pack = _grant(conn, u, 10, "purchase")
    sql = "SELECT reserve_credits(%s, %s, %s, 'research', NULL, %s)"
    res = conn.execute(sql, (u, trip, 8, "k1")).fetchone()[0]
    assert conn.execute(sql, (u, trip, 8, "k1")).fetchone()[0] == res  # replay returns the same reservation
    assert (_remaining(conn, monthly), _remaining(conn, pack)) == (0, 7)  # allowance first, then the pack
    assert conn.execute("SELECT settle_credits(%s, 3)", (res,)).fetchone() == (5,)
    assert _remaining(conn, monthly) + _remaining(conn, pack) == 12
    assert conn.execute("SELECT settle_credits(%s, 3)", (res,)).fetchone() == (0,)  # already settled
    with pytest.raises(psycopg.errors.Error) as e:
        conn.execute(sql, (u, trip, 99, "k2"))
    assert e.value.sqlstate == "WF402"
    assert _remaining(conn, monthly) + _remaining(conn, pack) == 12  # a failed reserve changes nothing


def test_debt_blocks_reserve_and_is_repaid(conn):
    u = _user(conn)
    t = _trip(conn, u)
    conn.execute("SELECT record_credit_debt(%s, 4, 'refund:x')", (u,))
    conn.execute("SELECT record_credit_debt(%s, 4, 'refund:x')", (u,))  # replayed webhook
    assert conn.execute("SELECT amount FROM credit_debts WHERE user_id = %s", (u,)).fetchone() == (4,)
    _grant(conn, u, 10)
    with pytest.raises(psycopg.errors.Error) as e:
        conn.execute("SELECT reserve_credits(%s, %s, 1, 'research', NULL, 'k')", (u, t))
    assert e.value.sqlstate == "WF402"
    assert conn.execute("SELECT settle_credit_debt(%s)", (u,)).fetchone() == (4,)
    assert conn.execute("SELECT amount FROM credit_debts WHERE user_id = %s", (u,)).fetchone() == (0,)
    conn.execute("SELECT reserve_credits(%s, %s, 1, 'research', NULL, 'k')", (u, t))


def test_expire_and_release_stale(conn):
    u = _user(conn)
    t = _trip(conn, u)
    g = _grant(conn, u, 5, expires_at="2020-01-01")
    assert conn.execute("SELECT expire_credit_grants()").fetchone() == (1,)
    assert _remaining(conn, g) == 0
    assert conn.execute("SELECT expire_credit_grants()").fetchone() == (0,)
    g2 = _grant(conn, u, 5)
    conn.execute("SELECT reserve_credits(%s, %s, 3, 'research', NULL, 'stale')", (u, t))
    assert conn.execute("SELECT release_stale_reservations()").fetchone() == (0,)
    assert conn.execute("SELECT release_stale_reservations(interval '0', interval '0')").fetchone() == (1,)
    assert conn.execute("SELECT release_stale_reservations(interval '0', interval '0')").fetchone() == (0,)
    assert _remaining(conn, g2) == 5


def test_free_monthly_and_taster_grants(conn):
    _plans(conn)
    u = _user(conn, verified=True)
    conn.execute("SELECT ensure_free_monthly_grant(%s)", (u,))
    conn.execute("SELECT ensure_free_monthly_grant(%s)", (u,))
    assert conn.execute(
        "SELECT count(*), sum(credits) FROM credit_grants WHERE user_id = %s AND kind = 'monthly'", (u,)
    ).fetchone() == (1, 12)
    conn.execute("SELECT ensure_taster_grant(%s)", (u,))
    conn.execute("SELECT ensure_taster_grant(%s)", (u,))
    assert conn.execute(
        "SELECT count(*) FROM credit_grants WHERE user_id = %s AND period_key = 'taster'", (u,)
    ).fetchone() == (1,)
    assert conn.execute("SELECT count(*) FROM identity_hashes WHERE kind = 'taster'").fetchone()[0] >= 1
    # A re-created account with the same verified email does not earn it again.
    email = conn.execute("SELECT email FROM users WHERE id = %s", (u,)).fetchone()[0]
    conn.execute("DELETE FROM credit_grants WHERE user_id = %s", (u,))
    conn.execute("DELETE FROM users WHERE id = %s", (u,))
    u2 = conn.execute(
        "INSERT INTO users (email, email_verified_at) VALUES (%s, now()) RETURNING id", (email,)
    ).fetchone()[0]
    conn.execute("SELECT ensure_taster_grant(%s)", (u2,))
    assert conn.execute("SELECT count(*) FROM credit_grants WHERE user_id = %s", (u2,)).fetchone() == (0,)


def test_balances_view_and_caller_check_passes_for_owner_login(conn):
    u, other = _user(conn), _user(conn)
    t = _trip(conn, u)
    _grant(conn, u, 7, "monthly", period_key="2026-10")
    _grant(conn, u, 3, "purchase")
    assert conn.execute(
        "SELECT remaining, allowance_remaining, purchased_remaining FROM credit_balances WHERE user_id = %s", (u,)
    ).fetchone() == (10, 7, 3)
    # The owner login is not a member of hermi_app, so it may act for any user.
    conn.execute("SELECT assert_credit_caller(%s)", (other,))
    conn.execute("SELECT reserve_credits(%s, %s, 1, 'research', NULL, 'z')", (u, t))
