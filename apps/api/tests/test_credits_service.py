# ruff: noqa: E501  (long SQL strings)
"""WF-044: the credit ledger service over the 0006 SQL functions. Rows are arranged with the system login (worker);
the API paths run as the app login with app.user_id set (RLS applies)."""

import json
import re
import threading
import uuid
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from hermi import db
from hermi.errors import ApiError
from hermi.modules.credits import prices, repo, service

SHARED = Path(__file__).resolve().parents[3] / "packages" / "shared" / "src" / "credits.ts"


@pytest.fixture
def make_paid(system_conn, make_user):
    """A user on a paid entitlement, so the lazy Free allowance never adds credits to the numbers under test."""

    def make():
        uid, sub = make_user()
        system_conn.execute("INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, 'plus', 'comp')", (uid,))
        return uid, sub

    return make


@pytest.fixture
def engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]), pool_size=20, max_overflow=0)
    yield e
    e.dispose()


@pytest.fixture
def sys_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["system"]))
    yield e
    e.dispose()


def _trip(c, owner):
    return c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)).fetchone()[0]


def _grant(c, user, credits=100, kind="promo", **kw):
    cols = {"user_id": user, "kind": kind, "credits": credits, "remaining": credits, **kw}
    return c.execute(
        f"INSERT INTO credit_grants ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id", tuple(cols.values())
    ).fetchone()[0]


def _key():
    return f"k:{uuid.uuid4()}"


def _remaining(c, user):
    return c.execute("SELECT coalesce(sum(remaining), 0) FROM credit_grants WHERE user_id = %s", (user,)).fetchone()[0]


def _deep_run(c, user, trip, kind="deep_research"):
    """A queued run row: the taster is drawn only by a deep_research run of a Free account (0026)."""
    return c.execute(
        "INSERT INTO runs (trip_id, user_id, kind, action) VALUES (%s, %s, %s, 'agent_run') RETURNING id", (trip, user, kind)
    ).fetchone()[0]


def _reserve(engine, user, trip, action="explain", key=None, **kw):
    with db.request_transaction(engine, user) as s:
        return service.reserve(s, user_id=user, trip_id=trip, action=action, idempotency_key=key or _key(), **kw)


# ---- prices ----


def test_prices_match_seed_plans_and_shared_package(system_conn):
    rows = system_conn.execute("SELECT action, credits, credits_cached FROM credit_action_prices").fetchall()
    assert {a: (c, cc) for a, c, cc in rows} == prices.ACTION_CREDITS
    assert prices.price("research") == 8 and prices.price("research", cached=True) == 1
    assert prices.price("agent_run", cached=True) == 8 and prices.price("explain", cached=True) == 1
    assert prices.price("verify_plan", items=5) == 5
    for tier, n in prices.MONTHLY_CREDITS.items():
        assert system_conn.execute("SELECT (limits->>'monthly_credits')::int FROM plans WHERE code = %s", (tier,)).fetchone()[0] == n
    src = SHARED.read_text(encoding="utf-8")
    block = re.search(r"BEGIN CREDIT_PRICES\nexport const CREDIT_PRICES = (.*?);\n// END CREDIT_PRICES", src, re.S).group(1)
    assert {k: tuple(v) for k, v in json.loads(block).items()} == prices.ACTION_CREDITS
    assert re.search(r"MONTHLY_CREDITS = \{ free: 12, plus: 60 \}", src) and prices.MONTHLY_CREDITS == {"free": 12, "plus": 60}
    assert f"TASTER_CREDITS = {prices.TASTER_CREDITS};" in src
    assert f"AGENT_RUN_MINIMUM_CHARGE = {prices.AGENT_RUN_MINIMUM_CHARGE};" in src
    assert f"PURCHASED_CREDITS_VALID_MONTHS = {prices.PURCHASED_CREDITS_VALID_MONTHS};" in src


def test_agent_run_charge_is_pro_rata_with_an_eight_credit_minimum():
    assert prices.agent_run_charge(0, called_tools=False) == 0  # cancelled in the queue
    assert prices.agent_run_charge(1) == 8 and prices.agent_run_charge(4) == 8  # minimum
    assert prices.agent_run_charge(10) == 20 and prices.agent_run_charge(20) == 40 and prices.agent_run_charge(30) == 60


# ---- reserve, settle, refund ----


def test_twenty_parallel_reservations_never_overspend(engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    _grant(system_conn, user, 5, "purchase")
    barrier = threading.Barrier(20)
    out: list = []

    def go():
        try:
            with db.request_transaction(engine, user) as s:
                barrier.wait(timeout=15)
                out.append(service.reserve(s, user_id=user, trip_id=trip, action="explain", idempotency_key=_key()))
        except ApiError as e:
            out.append(e)

    threads = [threading.Thread(target=go) for _ in range(20)]
    [t.start() for t in threads]
    [t.join(timeout=60) for t in threads]
    ok = [r for r in out if isinstance(r, service.Reservation)]
    refused = [r for r in out if isinstance(r, ApiError)]
    assert len(out) == 20 and len(ok) == 5 and len(refused) == 15
    assert all(e.status == 402 and e.code == "insufficient_credits" for e in refused)
    assert _remaining(system_conn, user) == 0
    assert system_conn.execute("SELECT count(*) FROM credit_ledger WHERE user_id = %s AND entry_type = 'reserve'", (user,)).fetchone()[0] == 5


def test_failed_or_empty_action_is_refunded_in_full(engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    g = _grant(system_conn, user, 10, "purchase")
    res = _reserve(engine, user, trip, "draft_trip")
    assert (res.amount, _remaining(system_conn, user)) == (4, 6)
    with db.request_transaction(engine, user) as s:
        assert service.refund(s, res.id) == 4
        assert service.refund(s, res.id) == 0  # a replay does nothing
    assert _remaining(system_conn, user) == 10
    rows = system_conn.execute("SELECT entry_type, delta, charged, grant_id FROM credit_ledger WHERE reservation_id = %s ORDER BY id", (res.id,)).fetchall()
    assert rows == [("reserve", -4, None, g), ("refund", 4, None, g), ("settle", 0, 0, None)]


def test_partial_settle_charges_and_returns_the_rest(engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    _grant(system_conn, user, 20, "purchase")
    res = _reserve(engine, user, trip, "research")
    with db.request_transaction(engine, user) as s:
        assert service.settle(s, res.id, 3) == 5
    assert _remaining(system_conn, user) == 17
    assert system_conn.execute("SELECT charged FROM credit_ledger WHERE reservation_id = %s AND entry_type = 'settle'", (res.id,)).fetchone()[0] == 3


@pytest.mark.parametrize("turns, called_tools, charged", [(0, False, 0), (3, True, 8), (10, True, 20), (20, True, 40)])
def test_stopped_agent_run_is_billed_pro_rata(engine, system_conn, make_paid, turns, called_tools, charged):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    _grant(system_conn, user, 100, "purchase")
    res = _reserve(engine, user, trip, "agent_run")
    assert res.amount == 40
    with db.request_transaction(engine, user) as s:
        assert service.settle_stopped_agent_run(s, res.id, turns_used=turns, called_tools=called_tools) == charged
    assert _remaining(system_conn, user) == 100 - charged


def test_negative_balance_after_a_refund_blocks_new_actions(engine, sys_engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    _grant(system_conn, user, 20, "purchase")
    with Session(sys_engine) as w:
        repo.record_credit_debt(w, user, 5, f"refund:{uuid.uuid4()}")
        w.commit()
    with db.request_transaction(engine, user) as s:
        b = service.balance(s, user, trip_id=trip, action="explain")
        assert b.blocked is True and b.available == 20
    with pytest.raises(ApiError) as e:
        _reserve(engine, user, trip)
    assert (e.value.status, e.value.code, e.value.extra) == (402, "insufficient_credits", {"blocked": True})
    _grant(system_conn, user, 10, "purchase")
    with Session(sys_engine) as w:  # the worker pays the debt down from the grants, which lifts the block
        assert repo.settle_credit_debt(w, user) == 5
        w.commit()
    with db.request_transaction(engine, user) as s:
        assert service.balance(s, user, trip_id=trip, action="explain").blocked is False
    _reserve(engine, user, trip)


# ---- spend order, trip pool, taster ----


def test_spend_order_allowance_promo_pass_adjustment_then_purchases_oldest_first(engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    purchase_late = _grant(system_conn, user, 1, "purchase", expires_at="2031-01-01T00:00:00Z")
    purchase_early = _grant(system_conn, user, 1, "purchase", expires_at="2030-01-01T00:00:00Z")
    adjustment = _grant(system_conn, user, 1, "adjustment")
    pass_ = _grant(system_conn, user, 1, "trip_pass", trip_id=trip)
    promo = _grant(system_conn, user, 1, "promo")
    monthly = _grant(system_conn, user, 1, "monthly", period_key="2026-10", expires_at="2031-01-01T00:00:00Z")
    res = _reserve(engine, user, trip, "draft_trip")  # 4 credits
    res2 = _reserve(engine, user, trip, "draft_day")
    res3 = _reserve(engine, user, trip, "draft_day")
    order = [r[0] for r in system_conn.execute("SELECT grant_id FROM credit_ledger WHERE user_id = %s AND entry_type = 'reserve' ORDER BY id", (user,)).fetchall()]
    assert order == [monthly, promo, pass_, adjustment, purchase_early, purchase_late]
    assert res.amount == 4 and res2.amount == 1 and res3.amount == 1


def test_trip_pass_credits_are_a_pool_for_editors_only(engine, sys_engine, system_conn, make_paid):
    owner, _ = make_paid()
    editor, _ = make_paid()
    viewer, _ = make_paid()
    trip = _trip(system_conn, owner)
    for u, role in ((editor, "editor"), (viewer, "viewer")):
        system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (trip, u, role))
    pool = _grant(system_conn, owner, 5, "trip_pass", trip_id=trip)
    # balance() reads credit_grants as the caller: a worker session sees the pool, an API session (RLS: own rows only) does not.
    with Session(sys_engine) as w:
        assert service.balance(w, editor, trip_id=trip, action="explain").available == 5
        assert service.balance(w, viewer, trip_id=trip, action="explain").available == 0
    with db.request_transaction(engine, editor) as s:  # pins the RLS blind spot: the pool is not visible to the API session
        assert service.balance(s, editor, trip_id=trip, action="explain").available == 0
    with pytest.raises(ApiError):
        _reserve(engine, viewer, trip)
    res = _reserve(engine, editor, trip, "draft_trip")
    assert system_conn.execute("SELECT user_id, grant_id FROM credit_ledger WHERE reservation_id = %s", (res.id,)).fetchone() == (editor, pool)


def test_taster_is_granted_once_and_draws_its_own_grant(engine, sys_engine, system_conn, make_user):
    user, _ = make_user()  # Free: no entitlement row, so the lazy monthly 12 credits arrive with the first reserve
    trip = _trip(system_conn, user)
    for _ in range(3):
        with db.request_transaction(engine, user) as s:
            repo.ensure_taster_grant(s, user)
    assert system_conn.execute("SELECT count(*) FROM credit_grants WHERE user_id = %s AND period_key = 'taster'", (user,)).fetchone()[0] == 1
    _grant(system_conn, user, 100, "purchase")
    with db.request_transaction(engine, user) as s:
        assert service.balance(s, user, trip_id=trip, action="agent_run").available == 100
        assert service.balance(s, user, trip_id=trip, action="explain").available == 100  # the taster never pays for anything else
    res = _reserve(engine, user, trip, "agent_run", run_id=_deep_run(system_conn, user, trip))
    draws = system_conn.execute(
        "SELECT g.period_key, -l.delta FROM credit_ledger l JOIN credit_grants g ON g.id = l.grant_id WHERE l.reservation_id = %s", (res.id,)
    ).fetchall()
    assert draws == [("taster", 40)]  # whole price from the taster alone
    assert _remaining(system_conn, user) == 112  # 100 bought plus the 12 monthly credits, none of them touched
    for _ in range(2):  # a spent taster is never granted again
        with db.request_transaction(engine, user) as s:
            repo.ensure_taster_grant(s, user)
    assert system_conn.execute("SELECT count(*) FROM credit_grants WHERE user_id = %s AND period_key = 'taster'", (user,)).fetchone()[0] == 1
    res2 = _reserve(engine, user, trip, "agent_run")  # now paid from the other grants
    assert system_conn.execute("SELECT count(*) FROM credit_ledger WHERE reservation_id = %s", (res2.id,)).fetchone()[0] == 2
    assert _remaining(system_conn, user) == 72


# ---- monthly, purchase, adjust, expire, stale ----


def test_free_monthly_grant_is_lazy_and_once(engine, system_conn, make_user):
    free, _ = make_user()
    for _ in range(2):
        _reserve(engine, free, None, "explain")
    assert system_conn.execute("SELECT credits, period_key IS NOT NULL FROM credit_grants WHERE user_id = %s AND kind = 'monthly'", (free,)).fetchall() == [(12, True)]
    assert _remaining(system_conn, free) == 10


def test_every_ledger_entry_type_is_written_and_the_ledger_reconciles(engine, sys_engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    with Session(sys_engine) as w:
        adj = service.adjust(w, user, 5, reason="goodwill after a failed import")  # adjust
        w.commit()
    pack = _grant(system_conn, user, 50, "purchase")
    system_conn.execute("INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta) VALUES (%s, %s, 'grant', 50)", (user, pack))  # grant
    with Session(sys_engine) as w:
        repo.record_credit_debt(w, user, 2, f"refund:{uuid.uuid4()}")  # clawback (debt, no grant)
        repo.settle_credit_debt(w, user)  # clawback (repayment)
        w.commit()
    res = _reserve(engine, user, trip, "research")  # reserve
    with db.request_transaction(engine, user) as s:
        service.settle(s, res.id, 2)  # refund + settle
    old = _grant(system_conn, user, 3, "purchase", expires_at="2020-01-01T00:00:00Z")
    with Session(sys_engine) as w:
        assert service.expire_grants(w) == 1  # expire
        w.commit()
    kinds = {r[0] for r in system_conn.execute("SELECT entry_type FROM credit_ledger WHERE user_id = %s", (user,)).fetchall()}
    assert kinds == {"grant", "reserve", "settle", "refund", "expire", "clawback", "adjust"}
    assert system_conn.execute("SELECT remaining FROM credit_grants WHERE id = %s", (old,)).fetchone()[0] == 0
    assert system_conn.execute("SELECT expires_at > now() + interval '12 months' - interval '1 minute' FROM credit_grants WHERE id = %s", (adj,)).fetchone()[0]
    assert system_conn.execute("SELECT count(*) FROM audit_log WHERE action = 'credits.adjust' AND reason = 'goodwill after a failed import'").fetchone()[0] == 1
    # 07 5.7: per grant, credits plus the sum of its non-grant deltas equals remaining (the adjust row is the grant's own entry)
    bad = system_conn.execute(
        """SELECT g.id FROM credit_grants g WHERE g.user_id = %s AND g.id <> %s AND g.credits +
           coalesce((SELECT sum(delta) FROM credit_ledger l WHERE l.grant_id = g.id AND l.entry_type NOT IN ('grant', 'adjust')), 0) <> g.remaining""",
        (user, old),
    ).fetchall()
    assert bad == []


def test_expired_grants_do_not_spend_and_expiry_runs_once(engine, sys_engine, system_conn, make_paid):
    user, _ = make_paid()
    _grant(system_conn, user, 10, "purchase", expires_at="2020-01-01T00:00:00Z")
    with pytest.raises(ApiError):
        _reserve(engine, user, None)
    with db.request_transaction(engine, user) as s:
        assert service.balance(s, user, trip_id=None, action="explain").available == 0
    with Session(sys_engine) as w:
        assert service.expire_grants(w) >= 1
        assert service.expire_grants(w) == 0  # a second run finds nothing
        w.commit()


def test_reserve_price_follows_the_credit_action_prices_table(engine, system_conn, make_paid):
    user, _ = make_paid()
    _grant(system_conn, user, 100, "purchase")
    try:
        system_conn.execute("UPDATE credit_action_prices SET credits = 9, credits_cached = 2 WHERE action = 'research'")
        assert _reserve(engine, user, None, "research").amount == 9
        assert _reserve(engine, user, None, "research", cached=True).amount == 2
    finally:
        system_conn.execute("UPDATE credit_action_prices SET credits = 8, credits_cached = 1 WHERE action = 'research'")
    assert _reserve(engine, user, None, "research").amount == 8


def test_stopped_run_paid_from_the_taster_is_charged_in_full_and_replay_charges_nothing(engine, system_conn, make_user):
    user, _ = make_user()
    trip = _trip(system_conn, user)
    with db.request_transaction(engine, user) as s:
        repo.ensure_taster_grant(s, user)
    res = _reserve(engine, user, trip, "agent_run", run_id=_deep_run(system_conn, user, trip))
    with db.request_transaction(engine, user) as s:
        assert service.settle_stopped_agent_run(s, res.id, turns_used=2) == 40  # the taster stays spent
        assert service.settle_stopped_agent_run(s, res.id, turns_used=2) == 0  # replay
    assert _remaining(system_conn, user) == 12  # only the monthly credits are left
    assert system_conn.execute("SELECT count(*) FROM credit_ledger WHERE reservation_id = %s AND entry_type = 'settle'", (res.id,)).fetchone()[0] == 1


def test_taster_run_stopped_in_the_queue_is_refunded(engine, system_conn, make_user):
    user, _ = make_user()
    trip = _trip(system_conn, user)
    with db.request_transaction(engine, user) as s:
        repo.ensure_taster_grant(s, user)
    res = _reserve(engine, user, trip, "agent_run", run_id=_deep_run(system_conn, user, trip))
    with db.request_transaction(engine, user) as s:
        assert service.settle_stopped_agent_run(s, res.id, turns_used=0, called_tools=False) == 0
    assert _remaining(system_conn, user) == 52  # the taster is back, plus the monthly 12


def test_stopped_run_uses_max_turns_from_the_table(engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    _grant(system_conn, user, 100, "purchase")
    res = _reserve(engine, user, trip, "agent_run")
    try:
        system_conn.execute("UPDATE credit_action_prices SET max_turns = 10 WHERE action = 'agent_run'")
        with db.request_transaction(engine, user) as s:
            assert service.settle_stopped_agent_run(s, res.id, turns_used=5) == 20  # half of 10 turns
    finally:
        system_conn.execute("UPDATE credit_action_prices SET max_turns = 20 WHERE action = 'agent_run'")


def test_stale_reservations_are_released(engine, sys_engine, system_conn, make_paid):
    user, _ = make_paid()
    trip = _trip(system_conn, user)
    _grant(system_conn, user, 10, "purchase")
    _reserve(engine, user, trip, "draft_trip")
    with Session(sys_engine) as w:
        assert service.release_stale_reservations(w) == 0  # nothing is old enough yet
        assert w.execute(text("SELECT release_stale_reservations(interval '-1 hour', interval '0')")).scalar_one() >= 1  # a deadline in the past
        assert w.execute(text("SELECT release_stale_reservations(interval '-1 hour', interval '0')")).scalar_one() == 0  # idempotent
        w.commit()
    assert _remaining(system_conn, user) == 10


def test_balance_carries_a_ledger_version_that_moves(engine, system_conn, make_paid):
    user, _ = make_paid()
    _grant(system_conn, user, 10, "purchase")
    with db.request_transaction(engine, user) as s:
        v0 = service.balance(s, user, trip_id=None, action="explain")
    _reserve(engine, user, None)
    with db.request_transaction(engine, user) as s:
        v1 = service.balance(s, user, trip_id=None, action="explain")
    assert (v0.available, v1.available) == (10, 9) and v1.version > v0.version


# ---- caller check and append-only ----


def test_another_users_p_user_is_refused(engine, system_conn, make_paid):
    a, _ = make_paid()
    b, _ = make_paid()
    trip = _trip(system_conn, b)
    _grant(system_conn, b, 10, "purchase")
    for call in (
        lambda s: repo.reserve_credits(s, user_id=b, trip_id=trip, amount=1, action="explain", run_id=None, idempotency_key=_key()),
        lambda s: repo.ensure_free_monthly_grant(s, b),
        lambda s: repo.ensure_taster_grant(s, b),
    ):
        with pytest.raises(DBAPIError) as e:
            with db.request_transaction(engine, a) as s:
                call(s)
        assert e.value.orig.sqlstate == "42501"
    assert _remaining(system_conn, b) == 10


def test_settle_of_another_users_reservation_is_refused(engine, system_conn, make_paid):
    a, _ = make_paid()
    b, _ = make_paid()
    _grant(system_conn, b, 10, "purchase")
    res = _reserve(engine, b, None)
    with pytest.raises(DBAPIError) as e:
        with db.request_transaction(engine, a) as s:
            service.settle(s, res.id, 0)
    assert e.value.orig.sqlstate == "42501"


def test_credit_ledger_is_append_only(engine, system_conn, make_paid):
    user, _ = make_paid()
    _grant(system_conn, user, 10, "purchase")
    _reserve(engine, user, None)
    for sql in ("UPDATE credit_ledger SET delta = -9 WHERE user_id = %s", "DELETE FROM credit_ledger WHERE user_id = %s"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            system_conn.execute(sql, (user,))
    with pytest.raises(DBAPIError):
        with db.request_transaction(engine, user) as s:
            s.execute(text("UPDATE credit_ledger SET delta = -9 WHERE user_id = :u"), {"u": user})
