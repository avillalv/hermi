# ruff: noqa: E501  (long SQL strings)
"""WF-052.1: live fares and rentals through SerpApi. Flag and kill switch, canonical key, the 6 hour shared cache, single
flight, ceilings, credits, spend metering and typed provider errors. The provider is an httpx MockTransport that counts calls
(the fixture JSON under providers/fixtures); no test reaches the network."""

import json
import threading
import time
import uuid
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from sqlalchemy import create_engine

from hermi import db
from hermi.config import NotConfigured, Settings
from hermi.errors import ApiError
from hermi.modules.admin.flags import Flag, FlagRuntime, Snapshot, Switch, engine_loader
from hermi.modules.ai.policy import blocked_domain
from hermi.modules.flights import live
from hermi.modules.flights.live import flight_search_key, rental_search_key
from hermi.modules.lodging import rentals
from hermi.providers import ProviderError, serpapi

DEP, RET = date(2026, 11, 5), date(2026, 11, 12)
IN, OUT = date(2026, 11, 5), date(2026, 11, 8)
PRICE_MICROS = 15_000  # pricing.provider_call_micros["serpapi"]
PAID = {"tiers": ["plus", "trip_pass"]}
ON = FlagRuntime(
    lambda: Snapshot(flags={live.FLAG: Flag(live.FLAG, "flag", True, 100, PAID, {})}), ttl=0
)
OFF = FlagRuntime(
    lambda: Snapshot(flags={live.FLAG: Flag(live.FLAG, "flag", False, 100, PAID, {})}), ttl=0
)
KILLED = FlagRuntime(
    lambda: Snapshot(
        flags={live.FLAG: Flag(live.FLAG, "flag", True, 100, PAID, {})},
        switches={live.KILL_KEY: Switch(live.KILL_KEY, True)},
    ),
    ttl=0,
)


class Provider:
    """A SerpApi stand-in. `calls` counts requests; `delay` makes concurrent callers overlap; `error` answers every call with it."""

    def __init__(self, *, delay: float = 0.0, error: tuple[int, dict] | None = None):
        self.calls, self.hosts, self.error, self.delay = 0, [], error, delay
        self._lock = threading.Lock()
        self._fixture = serpapi.fixture_client()

    def _handle(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.calls += 1
            self.hosts.append(request.url.host)
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            return httpx.Response(self.error[0], json=self.error[1])
        return self._fixture.get(request.url)

    @property
    def client(self) -> tuple[str, httpx.Client]:
        return "test-key", httpx.Client(transport=httpx.MockTransport(self._handle))


EMPTY = (200, {"error": "Google hasn't returned any results for this search."})


@pytest.fixture
def settings(db_urls):
    return Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        providers_mode="fake",
        ai_provider="fake",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
    )


@pytest.fixture(autouse=True)
def _dispose_system_engines():
    yield
    db.dispose_system_engines()


@pytest.fixture(autouse=True)
def _clean(system_conn):
    """Observations and rental entries are shared by every user, so an earlier test's rows would count as a fresh cache."""
    system_conn.execute("DELETE FROM fare_observations")
    system_conn.execute("DELETE FROM shared_research_cache WHERE kind = 'rentals'")
    system_conn.execute("DELETE FROM provider_calls WHERE provider = 'serpapi'")


@pytest.fixture
def engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]), pool_size=20, max_overflow=0)
    yield e
    e.dispose()


@pytest.fixture
def world(system_conn, make_user):
    """account(credits=60, tier='plus') -> (user, trip, route): a user with credits, a trip and a LAX to NRT or HND round trip."""

    def account(credits=60, tier="plus", pass_trip=False):
        uid, _ = make_user()
        if tier != "free":
            system_conn.execute(
                "INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, %s, 'comp')",
                (uid, tier),
            )
        if credits:
            system_conn.execute(
                "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key) VALUES (%s, 'monthly', %s, %s, to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'))",
                (uid, credits, credits),
            )
        trip = system_conn.execute(
            "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id",
            (uid,),
        ).fetchone()[0]
        if pass_trip:
            system_conn.execute(
                "INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', now() - interval '1 day', now() + interval '30 days', 'active')",
                (trip,),
            )
        route = system_conn.execute(
            "INSERT INTO flight_routes (trip_id, origin_codes, destination_codes, trip_type, depart_from, depart_to, return_from, return_to, adults, cabin, is_live) "
            "VALUES (%s, '{LAX}', '{NRT,HND}', 'round_trip', '2026-11-01', '2026-11-30', '2026-11-10', '2026-11-25', 2, 'economy', true) RETURNING id",
            (trip,),
        ).fetchone()[0]
        return uid, trip, route

    return account


def balance(conn, uid):
    return conn.execute(
        "SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = %s", (uid,)
    ).fetchone()[0]


def flights(engine, settings, flags, who, provider, **kw):
    uid, trip, route = who
    kw.setdefault("poll_seconds", 0.02)
    currency = kw.pop("currency", "USD")
    with db.request_transaction(engine, uid) as s:
        return live.search_live_flights(
            s,
            settings=settings,
            flags=flags,
            user_id=uid,
            trip_id=trip,
            route_id=route,
            depart_date=DEP,
            return_date=RET,
            currency=currency,
            idempotency_key=kw.pop("idempotency_key", uuid.uuid4().hex),
            provider_client=provider.client if provider else None,
            **kw,
        )


def rent(engine, settings, flags, who, provider, **kw):
    uid, trip, _ = who
    kw.setdefault("poll_seconds", 0.02)
    args = dict(
        place="Kyoto, Japan", check_in=IN, check_out=OUT, adults=2, children=0, currency="USD"
    )
    with db.request_transaction(engine, uid) as s:
        return rentals.search_live_rentals(
            s,
            settings=settings,
            flags=flags,
            user_id=uid,
            trip_id=trip,
            idempotency_key=kw.pop("idempotency_key", uuid.uuid4().hex),
            provider_client=provider.client if provider else None,
            **{**args, **kw},
        )


def ledger(conn, uid=None, hash_=None):
    q = "SELECT ok, cached, cost_usd_micros, endpoint, user_id, trip_id, request_hash, cache_layer FROM provider_calls WHERE provider = 'serpapi'"
    args = ()
    if uid:
        q, args = q + " AND user_id = %s", (uid,)
    return conn.execute(q + " ORDER BY created_at", args).fetchall()


# ---- the canonical key ----


def test_flight_key_is_canonical():
    base = dict(cabin="economy", adults=2, children=0, max_stops=None, currency="USD")
    k = flight_search_key(["LAX"], ["NRT", "HND"], DEP, RET, **base)
    assert len(k) == 64
    assert k == flight_search_key(
        ["lax "], ["hnd", "NRT", "nrt"], DEP, RET, **base
    )  # case, order, spaces and duplicates fold
    for change in (
        {"cabin": "business"},
        {"adults": 3},
        {"children": 1},
        {"max_stops": 0},
        {"currency": "EUR"},
    ):
        assert flight_search_key(["LAX"], ["NRT", "HND"], DEP, RET, **{**base, **change}) != k
    assert flight_search_key(["LAX"], ["NRT", "HND"], DEP, None, **base) != k
    assert flight_search_key(["LAX"], ["NRT"], DEP, RET, **base) != k


def test_rental_key_is_canonical():
    k = rental_search_key("Kyoto, Japan", IN, OUT, adults=2, children=0, currency="USD")
    assert k == rental_search_key(
        "  kyoto,   JAPAN ", IN, OUT, adults=2, children=0, currency="usd"
    )
    assert k != rental_search_key("Kyoto, Japan", IN, OUT, adults=3, children=0, currency="USD")
    assert k != rental_search_key("Osaka, Japan", IN, OUT, adults=2, children=0, currency="USD")


# ---- the gate: flag and kill switch ----


def test_flag_is_off_by_default_and_off_hides_live_search(engine, settings, world, system_conn):
    seeded = system_conn.execute(
        "SELECT enabled FROM feature_flags WHERE key = %s", (live.FLAG,)
    ).fetchone()
    assert seeded == (False,)
    who, p = world(), Provider()
    for flags in (FlagRuntime(engine_loader(engine), ttl=0), OFF):
        for call in (flights, rent):
            with pytest.raises(ApiError) as e:
                call(engine, settings, flags, who, p)
            assert (e.value.status, e.value.code, e.value.extra["reason"]) == (
                503,
                "feature_disabled",
                "flag_off",
            )
    assert p.calls == 0 and balance(system_conn, who[0]) == 60 and ledger(system_conn) == []


def test_flag_tier_rule_keeps_free_accounts_out(engine, settings, world, system_conn):
    who, p = world(tier="free"), Provider()
    with pytest.raises(ApiError) as e:
        flights(engine, settings, ON, who, p)
    assert e.value.extra["reason"] == "flag_off" and p.calls == 0


def test_kill_switch_stops_the_call_even_with_a_fresh_cache(engine, settings, world, system_conn):
    who, p = world(), Provider()
    flights(engine, settings, ON, who, p)
    assert p.calls == 1
    for call in (flights, rent):
        with pytest.raises(ApiError) as e:
            call(engine, settings, KILLED, who, p)
        assert (e.value.status, e.value.code, e.value.extra["reason"]) == (
            503,
            "feature_disabled",
            "provider_paused",
        )
    assert p.calls == 1


def test_unconfigured_provider_degrades_without_a_call(engine, db_urls, world):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        providers_mode="live",
        ai_provider="fake",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
    )
    with pytest.raises(ApiError) as e:
        flights(engine, s, ON, world(), None)
    assert e.value.extra["reason"] == "not_configured"
    with pytest.raises(NotConfigured):
        serpapi.client_for(s)


# ---- the cache: one provider call for many users ----


def test_ten_users_one_route_cause_one_provider_call(engine, settings, world, system_conn):
    people, p = [world() for _ in range(10)], Provider()
    results = [flights(engine, settings, ON, w, p) for w in people]
    assert p.calls == 1
    assert [r.cached for r in results] == [False] + [True] * 9
    assert [r.credits_charged for r in results] == [1] + [0] * 9
    assert [balance(system_conn, w[0]) for w in people] == [59] + [60] * 9
    for w, r in zip(
        people, results, strict=True
    ):  # everyone sees the same fares, linked to their own route
        assert [f["price_total_minor"] for f in r.data] == [98000, 131000]
        assert (
            system_conn.execute(
                "SELECT count(*) FROM trip_fare_links WHERE route_id = %s", (w[2],)
            ).fetchone()[0]
            == 2
        )
    obs = system_conn.execute(
        "SELECT count(*), min(source), min(confidence::text) FROM fare_observations"
    ).fetchone()
    assert obs == (2, "serpapi", "live")
    rows = ledger(system_conn)
    assert [(r[0], r[1]) for r in rows] == [(True, False)] + [
        (True, True)
    ] * 9  # one paid call, nine cache hits


def test_concurrent_users_share_one_flight(engine, settings, world, system_conn):
    people, p = [world() for _ in range(8)], Provider(delay=0.4)
    out, errors = [], []

    def go(w):
        try:
            out.append(flights(engine, settings, ON, w, p))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=go, args=(w,)) for w in people]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors
    assert p.calls == 1
    assert sorted(r.credits_charged for r in out) == [0] * 7 + [1]
    assert sum(balance(system_conn, w[0]) for w in people) == 8 * 60 - 1


def test_a_cached_result_is_free_and_says_how_old_it_is(engine, settings, world, system_conn):
    a, b, p = world(), world(), Provider()
    first = flights(engine, settings, ON, a, p)
    assert (first.cached, first.age_seconds, first.credits_charged) == (False, 0, 1)
    system_conn.execute(
        "UPDATE provider_calls SET created_at = now() - interval '5 hours 59 minutes' WHERE provider = 'serpapi' AND NOT cached"
    )
    again = flights(engine, settings, ON, b, p)
    assert again.cached and again.credits_charged == 0 and p.calls == 1
    assert 5 * 3600 + 58 * 60 <= again.age_seconds <= 6 * 3600
    assert again.checked_at < datetime.now(UTC) - timedelta(hours=5, minutes=58)
    assert balance(system_conn, b[0]) == 60
    system_conn.execute(
        "UPDATE provider_calls SET created_at = now() - interval '6 hours 1 minute' WHERE provider = 'serpapi' AND NOT cached"
    )
    third = flights(engine, settings, ON, b, p)  # past 6 hours: a new, paid search
    assert not third.cached and third.credits_charged == 1 and p.calls == 2


def test_a_different_search_is_not_a_hit(engine, settings, world):
    who, p = world(), Provider()
    flights(engine, settings, ON, who, p)
    uid, trip, route = who
    with db.request_transaction(engine, uid) as s:
        r = live.search_live_flights(
            s,
            settings=settings,
            flags=ON,
            user_id=uid,
            trip_id=trip,
            route_id=route,
            depart_date=date(2026, 11, 6),
            return_date=RET,
            currency="USD",
            idempotency_key=uuid.uuid4().hex,
            provider_client=p.client,
        )
    assert not r.cached and p.calls == 2


def test_default_client_serves_the_fixture_when_no_key_is_set(engine, settings, world):
    r = flights(engine, settings, ON, world(), None)  # PROVIDERS_MODE=fake, no SERPAPI_API_KEY
    assert not r.cached and r.credits_charged == 1 and {f["currency"] for f in r.data} == {"USD"}


def test_a_replayed_idempotency_key_never_calls_again(engine, settings, world, system_conn):
    who, p = world(), Provider()
    flights(engine, settings, ON, who, p, idempotency_key="k1")
    with pytest.raises(ApiError) as e:
        flights(engine, settings, ON, who, p, idempotency_key="k1")
    assert (
        e.value.code == "idempotency_key_reused"
        and p.calls == 1
        and balance(system_conn, who[0]) == 59
    )


# ---- ceilings and credits ----


def test_ceiling_refuses_before_any_provider_call(engine, settings, world, system_conn):
    who, p = world(), Provider()
    system_conn.execute(
        "INSERT INTO provider_calls (provider, endpoint, user_id, cost_usd_micros, ok) VALUES ('serpapi', 'x', %s, 395000, true)",
        (who[0],),
    )  # plus day ceiling 400000
    with pytest.raises(ApiError) as e:
        flights(engine, settings, ON, who, p)
    assert (e.value.status, e.value.code, e.value.extra["scope"]) == (
        429,
        "provider_budget_exhausted",
        "day",
    )
    assert p.calls == 0 and balance(system_conn, who[0]) == 60


def test_a_cache_hit_ignores_the_ceiling(engine, settings, world, system_conn):
    a, b, p = world(), world(), Provider()
    flights(engine, settings, ON, a, p)
    system_conn.execute(
        "INSERT INTO provider_calls (provider, endpoint, user_id, cost_usd_micros, ok) VALUES ('serpapi', 'x', %s, 395000, true)",
        (b[0],),
    )
    assert flights(engine, settings, ON, b, p).cached


def test_no_credits_is_a_402_and_no_call(engine, settings, world):
    who, p = world(credits=0), Provider()
    with pytest.raises(ApiError) as e:
        flights(engine, settings, ON, who, p)
    assert (e.value.status, e.value.code) == (402, "insufficient_credits") and p.calls == 0


def test_monthly_quota_stops_the_call(engine, settings, world, system_conn):
    who, p = world(), Provider()
    system_conn.execute(
        "INSERT INTO provider_calls (provider, endpoint, user_id, cost_usd_micros, ok) VALUES ('serpapi', 'x', %s, 1, true)",
        (who[0],),
    )
    before = system_conn.execute(
        "SELECT rules FROM feature_flags WHERE key = 'setting_serpapi_monthly_quota'"
    ).fetchone()[0]
    system_conn.execute(
        "UPDATE feature_flags SET rules = '{\"searches\": 1}' WHERE key = 'setting_serpapi_monthly_quota'"
    )
    try:
        with pytest.raises(ApiError) as e:
            flights(engine, settings, ON, who, p)
    finally:
        system_conn.execute(
            "UPDATE feature_flags SET rules = %s::jsonb WHERE key = 'setting_serpapi_monthly_quota'",
            (json.dumps(before),),
        )
    assert (
        e.value.extra["reason"] == "quota" and p.calls == 0 and balance(system_conn, who[0]) == 60
    )


def test_a_pass_counts_its_live_checks(engine, settings, world, system_conn):
    who, p = world(tier="free", pass_trip=True), Provider()
    flights(engine, settings, ON, who, p)
    assert system_conn.execute(
        "SELECT live_checks_used FROM trip_passes WHERE trip_id = %s", (who[1],)
    ).fetchone() == (1,)


# ---- provider errors ----


@pytest.mark.parametrize(
    ("status", "body", "http", "code", "reason"),
    [
        (500, {"error": "Internal error"}, 502, "provider_error", "provider_error"),
        (429, {"error": "Too many requests"}, 503, "provider_unavailable", "rate_limited"),
        (
            401,
            {
                "error": "Invalid API key. Your API key should be here: https://serpapi.com/manage-api-key"
            },
            503,
            "provider_unavailable",
            "bad_key",
        ),
        (
            200,
            {"error": "Your account has run out of searches."},
            503,
            "provider_unavailable",
            "quota_exhausted",
        ),
    ],
)
def test_provider_errors_are_typed_and_never_charged_or_cached(
    engine, settings, world, system_conn, status, body, http, code, reason
):
    who = world()
    bad = Provider(error=(status, body))
    for call in (flights, rent):
        with pytest.raises(ApiError) as e:
            call(engine, settings, ON, who, bad)
        assert (e.value.status, e.value.code, e.value.extra["reason"]) == (http, code, reason)
    assert balance(system_conn, who[0]) == 60
    assert system_conn.execute("SELECT count(*) FROM fare_observations").fetchone() == (0,)
    assert system_conn.execute(
        "SELECT count(*) FROM shared_research_cache WHERE kind = 'rentals'"
    ).fetchone() == (0,)
    rows = ledger(system_conn)
    assert len(rows) == 2 and all(
        r[0] is False and r[2] is None for r in rows
    )  # a failed call is a row with no cost
    good = Provider()  # the failure was not cached: the next search runs and is charged
    r = flights(engine, settings, ON, who, good)
    assert good.calls == 1 and not r.cached and r.credits_charged == 1


def test_an_empty_result_is_not_charged_but_the_call_is_metered_and_cached(
    engine, settings, world, system_conn
):
    who, p = world(), Provider(error=EMPTY)
    r = flights(engine, settings, ON, who, p)
    assert (r.data, r.cached, r.credits_charged) == ([], False, 0)
    assert balance(system_conn, who[0]) == 60
    assert [(x[0], x[1], x[2]) for x in ledger(system_conn)] == [(True, False, PRICE_MICROS)]
    again = flights(engine, settings, ON, who, p)
    assert again.cached and again.data == [] and p.calls == 1


def test_a_response_over_the_size_limit_is_an_error():
    big = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b"x" * (serpapi.MAX_BYTES + 1))
        )
    )
    with pytest.raises(serpapi.SerpApiError):
        serpapi.search_rentals(
            big,
            "k",
            place="Kyoto",
            check_in=IN,
            check_out=OUT,
            adults=1,
            children=0,
            currency="USD",
        )


def test_a_transport_error_never_carries_the_key():
    def boom(request):
        raise httpx.ConnectError(f"cannot reach {request.url}")

    c = httpx.Client(transport=httpx.MockTransport(boom))
    with pytest.raises(ProviderError) as e:
        serpapi.search_rentals(
            c,
            "secret-key-123",
            place="Kyoto",
            check_in=IN,
            check_out=OUT,
            adults=1,
            children=0,
            currency="USD",
        )
    assert "secret-key-123" not in str(e.value) and "secret-key-123" not in repr(e.value.__cause__)


# ---- spend metering ----


def test_spend_is_metered_per_account_and_trip_at_the_price_constant(
    engine, settings, world, system_conn
):
    a, b, p = world(), world(), Provider()
    flights(engine, settings, ON, a, p)
    flights(engine, settings, ON, b, p)
    key = flight_search_key(
        ["LAX"],
        ["NRT", "HND"],
        DEP,
        RET,
        cabin="economy",
        adults=2,
        children=0,
        max_stops=None,
        currency="USD",
    )
    paid, hit = ledger(system_conn, a[0])[0], ledger(system_conn, b[0])[0]
    assert paid == (True, False, PRICE_MICROS, "google_flights", a[0], a[1], key, None)
    assert hit == (True, True, None, "google_flights", b[0], b[1], key, "db")
    spend = system_conn.execute(
        "SELECT coalesce(sum(cost_usd_micros), 0) FROM provider_calls WHERE provider = 'serpapi'"
    ).fetchone()[0]
    assert spend == PRICE_MICROS  # ten more users would add nothing


# ---- rentals: the same flag, cache, credit and ledger ----


def test_rentals_are_cached_shared_and_sorted_by_price_or_rating_only(
    engine, settings, world, system_conn
):
    a, b, p = world(), world(), Provider()
    first = rent(engine, settings, ON, a, p)
    assert (first.cached, first.credits_charged, p.calls) == (False, 1, 1)
    assert first.data["sorted_by"] == "price, lowest first"
    assert [o["title"] for o in first.data["offers"]] == [
        "Fixture Unrated Studio",
        "Fixture Riverside Apartment",
        "Fixture Machiya House",
    ]
    assert (
        first.data["offers"][2]["price_per_night_minor"] == 18000
        and first.data["offers"][2]["rating"] == 4.81
    )
    second = rent(
        engine, settings, ON, b, p, place="  kyoto,  JAPAN", sort="rating"
    )  # same search key, other sort
    assert (
        second.cached and second.credits_charged == 0 and p.calls == 1 and second.age_seconds >= 0
    )
    assert [o["title"] for o in second.data["offers"]] == [
        "Fixture Machiya House",
        "Fixture Riverside Apartment",
        "Fixture Unrated Studio",
    ]
    assert second.data["sorted_by"] == "rating, highest first"
    assert (balance(system_conn, a[0]), balance(system_conn, b[0])) == (59, 60)
    assert system_conn.execute(
        "SELECT count(*) FROM shared_research_cache WHERE kind = 'rentals' AND provider = 'serpapi'"
    ).fetchone() == (1,)


def test_rentals_past_six_hours_are_a_new_search(engine, settings, world, system_conn):
    who, p = world(), Provider()
    rent(engine, settings, ON, who, p)
    system_conn.execute(
        "UPDATE shared_research_cache SET expires_at = now() - interval '1 minute', fetched_at = now() - interval '6 hours 1 minute', stale_until = now() + interval '5 hours' WHERE kind = 'rentals'"
    )
    r = rent(engine, settings, ON, who, p)
    assert not r.cached and p.calls == 2


def test_rental_inputs_are_validated(engine, settings, world):
    who, p = world(), Provider()
    for bad in ({"sort": "commission"}, {"check_out": IN}, {"place": " "}, {"adults": 0}):
        with pytest.raises(ApiError) as e:
            rent(engine, settings, ON, who, p, **bad)
        assert e.value.status == 422
    assert p.calls == 0


# ---- never a listing site ----


def test_only_serpapi_is_ever_contacted_and_it_is_not_a_blocked_host(engine, settings, world):
    who, p = world(), Provider()
    flights(engine, settings, ON, who, p)
    rent(engine, settings, ON, who, p)
    assert set(p.hosts) == {"serpapi.com"}
    assert blocked_domain("serpapi.com") is None
    assert httpx.URL(serpapi.SEARCH_URL).host == "serpapi.com"


def test_a_blocked_host_link_in_a_result_is_text_and_never_followed():
    body = {
        "properties": [
            {
                "name": "Listing",
                "link": "https://www.airbnb.com/rooms/1",
                "rate_per_night": {"extracted_lowest": 100},
            }
        ]
    }
    seen = []

    def handler(request):
        seen.append(request.url.host)
        return httpx.Response(200, json=body)

    out = serpapi.search_rentals(
        httpx.Client(transport=httpx.MockTransport(handler)),
        "k",
        place="Kyoto",
        check_in=IN,
        check_out=OUT,
        adults=1,
        children=0,
        currency="USD",
    )
    assert out[0].link == "https://www.airbnb.com/rooms/1" and seen == ["serpapi.com"]


# ---- review fixes ----


def test_a_cache_hit_returns_only_rows_in_the_searched_currency(
    engine, settings, world, system_conn
):
    a, p = world(), Provider()
    flights(engine, settings, ON, a, p, currency="USD")
    flights(engine, settings, ON, a, p, currency="EUR")
    assert p.calls == 2
    hit = flights(engine, settings, ON, world(), p, currency="USD")
    assert hit.cached and p.calls == 2
    assert {f["currency"] for f in hit.data} == {"USD"} and len(hit.data) == 2


def test_rentals_for_a_foreign_trip_are_a_404_and_no_call(engine, settings, world, system_conn):
    owner, other, p = world(tier="free", pass_trip=True), world(), Provider()
    with pytest.raises(ApiError) as e:
        rent(engine, settings, ON, (other[0], owner[1], None), p)
    assert e.value.status == 404 and p.calls == 0
    assert system_conn.execute(
        "SELECT live_checks_used FROM trip_passes WHERE trip_id = %s", (owner[1],)
    ).fetchone() == (0,)
    assert balance(system_conn, other[0]) == 60


def test_rentals_do_not_count_a_pass_check(engine, settings, world, system_conn):
    who, p = world(tier="free", pass_trip=True), Provider()
    assert rent(engine, settings, ON, who, p).credits_charged == 1
    assert system_conn.execute(
        "SELECT live_checks_used FROM trip_passes WHERE trip_id = %s", (who[1],)
    ).fetchone() == (0,)


@pytest.mark.parametrize(
    ("call", "body"),
    [
        (flights, {"best_flights": ["x"]}),
        (flights, {"other_flights": [{"flights": ["x"], "price": 5}]}),
        (flights, {"best_flights": {"a": 1}}),
        (rent, {"properties": [1, 2]}),
        (rent, {"properties": [{"name": "A", "gps_coordinates": "x"}]}),
    ],
)
def test_a_malformed_body_is_a_provider_error_and_is_metered(
    engine, settings, world, system_conn, call, body
):
    who = world()
    with pytest.raises(ApiError) as e:
        call(engine, settings, ON, who, Provider(error=(200, body)))
    assert e.value.status == 502 and e.value.code == "provider_error"
    assert balance(system_conn, who[0]) == 60 and len(ledger(system_conn)) == 1


def test_the_env_cap_tightens_the_console_quota(engine, db_urls, world, system_conn):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        providers_mode="fake",
        ai_provider="fake",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        serpapi_monthly_cap=1,
    )
    who, p = world(), Provider()
    flights(engine, s, ON, who, p)
    with pytest.raises(ApiError) as e:
        rent(engine, s, ON, who, p)
    assert e.value.extra["reason"] == "quota" and p.calls == 1
