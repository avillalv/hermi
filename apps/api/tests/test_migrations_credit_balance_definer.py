# ruff: noqa: E501  (long SQL strings)
"""WF-132.1: revision 0027_credit_balance_definer. my_credit_balance(trip, action, price) is the caller's own credits plus
the Trip Pass pool they may spend, read past row-level security. Rows are arranged with the worker login; every
assertion runs as the app login with app.user_id set."""

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from tests.test_migrations import _alembic_cfg

from hermi import db


@pytest.fixture
def engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]))
    yield e
    e.dispose()


def _user(make_user):
    return make_user()[0]


def _trip(c, owner):
    return c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)).fetchone()[0]


def _member(c, trip, user, role):
    c.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (trip, user, role))


def _grant(c, user, credits, kind="promo", **kw):
    cols = {"user_id": user, "kind": kind, "credits": credits, "remaining": credits, **kw}
    return c.execute(
        f"INSERT INTO credit_grants ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id", tuple(cols.values())
    ).fetchone()[0]


def _bal(engine, user, trip, action="explain", price=None):
    with db.request_transaction(engine, user) as s:
        r = s.execute(
            text("SELECT * FROM my_credit_balance(:t, CAST(:a AS ai_action), :p)"), {"t": trip, "a": action, "p": price}
        ).one()
    return r._asdict()


def test_owner_sees_own_credits(engine, system_conn, make_user):
    u = _user(make_user)
    _grant(system_conn, u, 7, "purchase")
    r = _bal(engine, u, None)
    assert (r["own"], r["pool"], r["blocked"], r["payer"]) == (7, 0, False, "own")


def test_editor_with_no_credits_sees_the_pool_and_trip_pass_pays(engine, system_conn, make_user):
    owner, editor = _user(make_user), _user(make_user)
    trip = _trip(system_conn, owner)
    _member(system_conn, trip, editor, "editor")
    _grant(system_conn, owner, 40, "trip_pass", trip_id=trip)
    r = _bal(engine, editor, trip)
    assert (r["own"], r["pool"], r["payer"]) == (0, 40, "trip_pass")


def test_pool_comes_after_monthly_and_before_purchases(engine, system_conn, make_user):
    u = _user(make_user)
    trip = _trip(system_conn, u)
    _grant(system_conn, u, 5, "purchase")
    _grant(system_conn, u, 40, "trip_pass", trip_id=trip)
    assert _bal(engine, u, trip)["payer"] == "trip_pass"  # reserve draws the pass before a purchase
    _grant(system_conn, u, 3, "monthly", period_key="2026-10")
    assert _bal(engine, u, trip)["payer"] == "own"  # the monthly allowance goes first


def test_viewer_gets_no_pool(engine, system_conn, make_user):
    owner, viewer = _user(make_user), _user(make_user)
    trip = _trip(system_conn, owner)
    _member(system_conn, trip, viewer, "viewer")
    _grant(system_conn, owner, 40, "trip_pass", trip_id=trip)
    r = _bal(engine, viewer, trip)
    assert (r["own"], r["pool"], r["payer"]) == (0, 0, "own")


def test_non_member_trip_is_42501_and_so_is_no_user(engine, system_conn, make_user):
    owner, stranger = _user(make_user), _user(make_user)
    trip = _trip(system_conn, owner)
    with pytest.raises(DBAPIError) as e:
        _bal(engine, stranger, trip)
    assert e.value.orig.sqlstate == "42501"
    with pytest.raises(DBAPIError) as e, engine.connect() as c:  # no app.user_id at all
        c.execute(text("SELECT * FROM my_credit_balance(NULL, 'explain', 1)"))
    assert e.value.orig.sqlstate == "42501"


def test_expired_and_restricted_grants_are_left_out(engine, system_conn, make_user):
    u = _user(make_user)
    trip = _trip(system_conn, u)
    _grant(system_conn, u, 10, "promo", expires_at="2020-01-01T00:00:00Z")
    _grant(system_conn, u, 10, "trip_pass", trip_id=trip, expires_at="2020-01-01T00:00:00Z")
    _grant(system_conn, u, 10, "promo", restricted_action="agent_run")
    _grant(system_conn, u, 2, "purchase")
    assert _bal(engine, u, trip, "explain")["own"] == 2
    assert _bal(engine, u, trip, "agent_run")["own"] == 12


def test_taster_counts_only_for_an_agent_run_it_covers(engine, system_conn, make_user):
    u = _user(make_user)
    _grant(system_conn, u, 40, "promo", period_key="taster", restricted_action="agent_run")
    assert _bal(engine, u, None, "explain")["own"] == 0
    assert _bal(engine, u, None, "agent_run")["own"] == 40
    assert _bal(engine, u, None, "agent_run", 41)["own"] == 0  # does not cover a price of 41


def test_taster_is_not_counted_on_a_paid_tier(engine, system_conn, make_user):
    u = _user(make_user)
    _grant(system_conn, u, 40, "promo", period_key="taster", restricted_action="agent_run")
    system_conn.execute("INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, 'plus', 'comp')", (u,))
    assert _bal(engine, u, None, "agent_run")["own"] == 0


def test_refund_debt_blocks_and_version_moves(engine, system_conn, make_user):
    u = _user(make_user)
    _grant(system_conn, u, 20, "purchase")
    v0 = _bal(engine, u, None)["version"]
    system_conn.execute("INSERT INTO credit_debts (user_id, amount) VALUES (%s, 5)", (u,))
    system_conn.execute(
        "INSERT INTO credit_ledger (user_id, entry_type, delta, note) VALUES (%s, 'adjust', 1, 'x')", (u,)
    )
    r = _bal(engine, u, None)
    assert r["blocked"] is True and r["own"] == 20 and r["version"] > v0


def test_downgrade_and_upgrade_are_clean_with_one_head(db_urls):
    cfg = _alembic_cfg(db_urls["migrate"])
    assert len(ScriptDirectory.from_config(cfg).get_heads()) == 1
    command.downgrade(cfg, "0026_taster_deep_only")
    with db_conn(db_urls) as c:
        assert c.execute("SELECT to_regproc('my_credit_balance')").fetchone()[0] is None
    command.upgrade(cfg, "head")
    with db_conn(db_urls) as c:
        assert c.execute("SELECT to_regproc('my_credit_balance')").fetchone()[0] is not None


def db_conn(urls):
    import psycopg

    return psycopg.connect(db.psycopg_url(urls["system"]), autocommit=True)
