# ruff: noqa: E501  (long SQL strings)
"""WF-045: provider-spend ceilings and the admission rule (03 section 7.4, 06 section 6.5). Rows are arranged with the
system login; admission runs as the app login (RLS applies). `now` is fixed mid-month where a test needs calendar edges."""

import threading
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, OperationalError

from hermi import db
from hermi.errors import ApiError
from hermi.modules.credits import budget, service

NOW = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)
MONTH_START = datetime(2026, 3, 1, tzinfo=UTC)
YESTERDAY = datetime(2026, 3, 14, 12, 0, tzinfo=UTC)
HARD = 10_000  # explain
TIERS = [("free", 250_000, 50_000), ("plus", 2_250_000, 400_000), ("trip_pass", 1_800_000, 400_000)]


@pytest.fixture
def engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]), pool_size=20, max_overflow=0)
    yield e
    e.dispose()


@pytest.fixture
def make_tier(system_conn, make_user):
    def make(tier="free"):
        uid, _ = make_user()
        if tier in ("plus", "trip_pass"):  # a trip_pass tier here means the pass ceiling applies via an active pass on the trip
            system_conn.execute("INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, %s, 'comp')", (uid, "plus" if tier == "plus" else "free"))
        return uid

    return make


def _trip(c, owner):
    return c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)).fetchone()[0]


def _pass(c, trip):
    c.execute("INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', '2026-01-01', '2027-01-01', 'active')", (trip,))


def _usage(c, user, trip, cost, at=None, action="explain", state="settled", reserved=0, reservation=None):
    c.execute(
        "INSERT INTO ai_usage (user_id, trip_id, action, cost_usd_micros, state, credits_reserved, credits_charged, reservation_id, idempotency_key, created_at, settled_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, CASE WHEN %s = 'reserved' THEN NULL ELSE %s END)",
        (user, trip, action, cost, state, reserved, reservation, f"t:{uuid.uuid4()}", at or datetime.now(UTC), state, at or datetime.now(UTC)),
    )


def _provider(c, user, cost, at=None, provider="serpapi"):
    c.execute("INSERT INTO provider_calls (provider, endpoint, user_id, cost_usd_micros, created_at, ok) VALUES (%s, 'x', %s, %s, %s, true)", (provider, user, cost, at or datetime.now(UTC)))


def _check(engine, user, trip=None, action="explain", trip_id=None, **kw):
    with db.request_transaction(engine, user) as s:
        budget.check(s, user_id=user, trip_id=trip or trip_id, action=action, now=kw.pop("now", NOW), **kw)


def _refused(engine, user, scope, **kw):
    with pytest.raises(ApiError) as e:
        _check(engine, user, **kw)
    assert (e.value.status, e.value.code, e.value.extra["scope"]) == (429, "provider_budget_exhausted", scope)
    return e.value


# ---- ceilings by tier (boundary: exactly fits is admitted, one micro over is refused) ----


@pytest.mark.parametrize(("tier", "month", "day"), TIERS)
def test_month_boundary_per_tier(engine, system_conn, make_tier, tier, month, day):
    user = make_tier(tier)
    trip = _trip(system_conn, user)
    if tier == "trip_pass":
        _pass(system_conn, trip)
    _usage(system_conn, user, trip, month - HARD, YESTERDAY)
    _check(engine, user, trip)  # month spend + hard stop == ceiling
    _usage(system_conn, user, trip, 1, YESTERDAY)
    err = _refused(engine, user, "month", trip_id=trip)
    assert err.extra["resets_at"].startswith("2026-04-01")


@pytest.mark.parametrize(("tier", "month", "day"), TIERS)
def test_day_boundary_per_tier(engine, system_conn, make_tier, tier, month, day):
    user = make_tier(tier)
    trip = _trip(system_conn, user)
    if tier == "trip_pass":
        _pass(system_conn, trip)
    _usage(system_conn, user, trip, day - HARD, NOW)
    _check(engine, user, trip)
    _usage(system_conn, user, trip, 1, NOW)
    err = _refused(engine, user, "day", trip_id=trip)
    assert err.extra["resets_at"].startswith("2026-03-16")


def test_calendar_periods_not_rolling(engine, system_conn, make_tier):
    user = make_tier("free")
    _usage(system_conn, user, None, 250_000, datetime(2026, 2, 28, 23, 59, tzinfo=UTC))  # last month: not counted
    _usage(system_conn, user, None, 240_000, YESTERDAY)  # yesterday: this month's spend, not today's
    _check(engine, user)
    _usage(system_conn, user, None, 1, MONTH_START)
    _refused(engine, user, "month")


def test_provider_calls_count_and_anthropic_rows_do_not(engine, system_conn, make_tier):
    user = make_tier("free")
    _provider(system_conn, user, 999_999, provider="anthropic")  # Claude cost lives in ai_usage
    _check(engine, user, now=None)
    _provider(system_conn, user, 45_000)  # SerpApi, through my_provider_spend_micros
    _refused(engine, user, "day", now=None)


def test_open_reservations_count_at_their_hard_stop(engine, system_conn, make_tier):
    user = make_tier("plus")
    _usage(system_conn, user, None, 0, YESTERDAY, action="verify_plan", state="reserved", reserved=5)  # 5 items x 20,000
    _usage(system_conn, user, None, 5_000_000, YESTERDAY, state="released")  # released rows never count
    _usage(system_conn, user, None, 2_250_000 - 100_000 - HARD, YESTERDAY)
    _check(engine, user)
    _usage(system_conn, user, None, 1, YESTERDAY)
    _refused(engine, user, "month")


def test_reservation_without_a_usage_row_counts_from_the_ledger(engine, system_conn, make_tier):
    user = make_tier("plus")
    system_conn.execute("INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'purchase', 50, 50)", (user,))
    with db.request_transaction(engine, user) as s:
        service.reserve(s, user_id=user, trip_id=None, action="research", idempotency_key=f"k:{uuid.uuid4()}")  # hard stop 160,000
    _usage(system_conn, user, None, 400_000 - 160_000 - HARD)
    _check(engine, user, now=None)
    _usage(system_conn, user, None, 1)
    _refused(engine, user, "day", now=None)


# ---- the agent-run admission rule ----


def test_agent_run_needs_monthly_headroom_even_when_the_day_is_spent(engine, system_conn, make_tier):
    user = make_tier("plus")
    _usage(system_conn, user, None, 400_000, NOW)  # today's budget is gone
    _refused(engine, user, "day")  # any other paid action is paused...
    _check(engine, user, action="agent_run")  # ...but a run has 1,850,000 of month headroom
    _check(engine, user, action="verify_plan", items=3)  # a plan check is admitted the same way


def test_agent_run_boundary_is_exactly_the_hard_stop(engine, system_conn, make_tier):
    user = make_tier("plus")
    _usage(system_conn, user, None, 2_250_000 - 800_000, YESTERDAY)
    _check(engine, user, action="agent_run")
    _usage(system_conn, user, None, 1, YESTERDAY)
    _refused(engine, user, "month", action="agent_run")


def test_an_admitted_run_blocks_other_paid_actions_that_day(engine, system_conn, make_tier):
    user = make_tier("plus")
    _usage(system_conn, user, None, 0, NOW, action="agent_run", state="reserved", reserved=40)  # counts 800,000 today
    _refused(engine, user, "day")


def test_free_run_needs_the_taster_and_the_taster_spend_is_outside_the_ceiling(engine, system_conn, make_tier):
    user = make_tier("free")
    _refused(engine, user, "month", action="agent_run")  # $0.80 does not fit a $0.25 ceiling
    system_conn.execute("SELECT ensure_taster_grant(%s)", (user,))
    with db.request_transaction(engine, user) as s:
        res = budget.admit(s, user_id=user, trip_id=None, action="agent_run", idempotency_key=f"k:{uuid.uuid4()}")
        assert res.amount == 40
    _check(engine, user, now=None)  # the open taster reservation (800,000) does not eat the Free ceiling


def test_cached_work_is_never_stopped_by_a_ceiling(engine, system_conn, make_tier):
    user = make_tier("plus")
    system_conn.execute("INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'purchase', 50, 50)", (user,))
    _usage(system_conn, user, None, 2_250_000)
    with db.request_transaction(engine, user) as s:
        res = budget.admit(s, user_id=user, trip_id=None, action="research", cached=True, idempotency_key=f"k:{uuid.uuid4()}")
        assert res.amount == 1
    with pytest.raises(ApiError) as e, db.request_transaction(engine, user) as s:
        budget.admit(s, user_id=user, trip_id=None, action="research", idempotency_key=f"k:{uuid.uuid4()}")
    assert e.value.code == "provider_budget_exhausted"


def test_a_refused_ceiling_reserves_nothing(engine, system_conn, make_tier):
    user = make_tier("plus")
    system_conn.execute("INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'purchase', 50, 50)", (user,))
    _usage(system_conn, user, None, 2_250_000)
    with pytest.raises(ApiError), db.request_transaction(engine, user) as s:
        budget.admit(s, user_id=user, trip_id=None, action="explain", idempotency_key=f"k:{uuid.uuid4()}")
    assert system_conn.execute("SELECT count(*) FROM credit_ledger WHERE user_id = %s AND entry_type = 'reserve'", (user,)).fetchone()[0] == 0


# ---- the pass pays ----


def test_pass_work_counts_against_the_pass_for_every_member_not_the_actor(engine, system_conn, make_tier):
    a, b = make_tier("free"), make_tier("free")
    trip = _trip(system_conn, a)
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'editor')", (trip, b))
    _pass(system_conn, trip)
    _usage(system_conn, b, trip, 1_380_000, YESTERDAY)  # B's pass-funded work on an earlier day, invisible to A under RLS
    _usage(system_conn, a, trip, 410_000, YESTERDAY)  # A's: the pass month is now 1,790,000
    _check(engine, a, trip)  # + 10,000 == the 1,800,000 pass ceiling, and Free's own 250,000 does not apply
    _usage(system_conn, b, trip, 1, YESTERDAY)
    err = _refused(engine, a, "month", trip_id=trip)
    assert err.extra["payer"] == "pass"
    _check(engine, a)  # off the pass trip A's own ceiling applies, and the pass work is left out of it


def test_pass_sum_refuses_a_trip_the_caller_is_not_in(engine, system_conn, make_tier):
    owner, stranger = make_tier("free"), make_tier("free")
    trip = _trip(system_conn, owner)
    with pytest.raises(DBAPIError) as e, db.request_transaction(engine, stranger) as s:
        s.execute(text("SELECT * FROM trip_pass_spend_micros(:t, now(), now())"), {"t": trip})
    assert e.value.orig.sqlstate == "42501"


def test_an_expired_pass_is_not_the_payer(engine, system_conn, make_tier):
    user = make_tier("free")
    trip = _trip(system_conn, user)
    system_conn.execute("INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', '2025-01-01', '2025-04-01', 'expired')", (trip,))
    _usage(system_conn, user, trip, 245_000, YESTERDAY)
    err = _refused(engine, user, "month", trip_id=trip)
    assert err.extra["payer"] == "account"


# ---- settings and failing closed ----


def test_ceilings_come_from_plans_limits(engine, system_conn, make_tier):
    user = make_tier("free")
    _usage(system_conn, user, None, 245_000, YESTERDAY)
    _refused(engine, user, "month")
    try:
        system_conn.execute("UPDATE plans SET limits = jsonb_set(limits, '{monthly_ceiling_micros}', '300000') WHERE code = 'free'")
        _check(engine, user)  # an admin edit applies at once
    finally:
        system_conn.execute("UPDATE plans SET limits = jsonb_set(limits, '{monthly_ceiling_micros}', '250000') WHERE code = 'free'")


def test_unreadable_ledger_refuses(engine, make_tier, monkeypatch):
    user = make_tier("plus")

    def boom(*a, **k):
        raise OperationalError("select", {}, Exception("connection lost"))

    monkeypatch.setattr(budget, "_sums", boom)
    with pytest.raises(ApiError) as e:
        _check(engine, user)
    assert (e.value.status, e.value.code) == (503, "ai_unavailable")


def test_missing_ceiling_setting_refuses(engine, system_conn, make_tier):
    user = make_tier("free")
    try:
        system_conn.execute("UPDATE plans SET limits = limits - 'daily_ceiling_micros' WHERE code = 'free'")
        with pytest.raises(ApiError) as e:
            _check(engine, user)
        assert (e.value.status, e.value.code) == (503, "ai_unavailable")
    finally:
        system_conn.execute("UPDATE plans SET limits = jsonb_set(limits, '{daily_ceiling_micros}', '50000') WHERE code = 'free'")


# ---- parallel admission ----


def test_parallel_runs_on_the_last_headroom_admit_exactly_one(engine, system_conn, make_tier):
    user = make_tier("plus")
    system_conn.execute("INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'promo', 400, 400)", (user,))
    _usage(system_conn, user, None, 2_250_000 - 800_000, datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0))
    barrier, out = threading.Barrier(6), []

    def go():
        try:
            with db.request_transaction(engine, user) as s:
                barrier.wait(timeout=15)
                out.append(budget.admit(s, user_id=user, trip_id=None, action="agent_run", idempotency_key=f"k:{uuid.uuid4()}"))
        except ApiError as e:
            out.append(e)

    threads = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in threads]
    [t.join(timeout=60) for t in threads]
    ok = [r for r in out if isinstance(r, service.Reservation)]
    refused = [r for r in out if isinstance(r, ApiError)]
    assert len(out) == 6 and len(ok) == 1 and len(refused) == 5
    assert all(e.status == 429 and e.code == "provider_budget_exhausted" for e in refused)
    assert system_conn.execute("SELECT count(DISTINCT reservation_id) FROM credit_ledger WHERE user_id = %s AND entry_type = 'reserve'", (user,)).fetchone()[0] == 1


# ---- purchased credits raise the monthly ceiling ----


def _spent(system_conn, user, kind, credits):
    """Arrange `credits` net-debited from a grant of `kind` this month (a reserve row, as reserve_credits writes it)."""
    g = system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key) VALUES (%s, %s, %s, 0, %s) RETURNING id", (user, kind, credits, f"p:{uuid.uuid4()}")
    ).fetchone()[0]
    system_conn.execute(
        "INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, reservation_id, action, idempotency_key, created_at) VALUES (%s, %s, 'reserve', %s, %s, 'explain', %s, %s)",
        (user, g, -credits, uuid.uuid4(), f"k:{uuid.uuid4()}", NOW),
    )
    system_conn.execute("INSERT INTO credit_ledger (user_id, entry_type, delta, charged, reservation_id, action) SELECT user_id, 'settle', 0, %s, reservation_id, action FROM credit_ledger WHERE grant_id = %s", (credits, g))


def test_purchased_spend_raises_the_ceiling_by_exactly_its_cost_value(engine, system_conn, make_tier):
    user = make_tier("free")
    _usage(system_conn, user, None, 245_000, YESTERDAY)  # Free month 250,000: an explain (10,000) no longer fits
    _refused(engine, user, "month")
    _spent(system_conn, user, "purchase", 1)  # +20,000: 245,000 + 10,000 fits 270,000
    _check(engine, user)
    _usage(system_conn, user, None, 15_001, YESTERDAY)  # 260,001 + 10,000 > 270,000
    _refused(engine, user, "month")


@pytest.mark.parametrize("kind", ["monthly", "promo", "adjustment"])
def test_no_other_credit_raises_the_ceiling(engine, system_conn, make_tier, kind):
    user = make_tier("free")
    _usage(system_conn, user, None, 245_000, YESTERDAY)
    _spent(system_conn, user, kind, 5)
    _refused(engine, user, "month")


# ---- the taster race ----


def test_two_parallel_runs_cannot_both_take_the_taster_path(engine, system_conn, make_tier):
    user = make_tier("free")
    system_conn.execute("SELECT ensure_taster_grant(%s)", (user,))
    system_conn.execute("INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'purchase', 400, 400)", (user,))
    _usage(system_conn, user, None, 250_000, datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0))  # month used up
    barrier, out = threading.Barrier(2), []

    def go():
        try:
            with db.request_transaction(engine, user) as s:
                barrier.wait(timeout=15)
                out.append(budget.admit(s, user_id=user, trip_id=None, action="agent_run", idempotency_key=f"k:{uuid.uuid4()}"))
        except ApiError as e:
            out.append(e)

    threads = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in threads]
    [t.join(timeout=60) for t in threads]
    assert sorted(type(r).__name__ for r in out) == ["ApiError", "Reservation"]
    assert next(r for r in out if isinstance(r, ApiError)).code == "provider_budget_exhausted"
    assert system_conn.execute("SELECT remaining FROM credit_grants WHERE user_id = %s AND period_key = 'taster'", (user,)).fetchone()[0] == 0
    assert system_conn.execute("SELECT remaining FROM credit_grants WHERE user_id = %s AND kind = 'purchase'", (user,)).fetchone()[0] == 400
