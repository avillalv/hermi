# ruff: noqa: E501  (long SQL strings)
"""WF-052.2: the HTTP layer of live fares and rentals. Flag off hides it, 1 credit fresh, free and labelled from the shared
cache, replay under one Idempotency-Key charges once, a provider error charges nothing, a viewer is refused. The provider is
the SerpApi fixture client (providers_mode=fake); no test reaches the network."""

import uuid
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from hermi import db
from hermi.config import Settings
from hermi.main import create_app
from hermi.modules.admin.flags import Flag, FlagRuntime, Snapshot
from hermi.modules.flights import live
from hermi.providers import serpapi
from hermi.security.jwt import mint_dev_token

DEP = date.today() + timedelta(days=30)
RET = DEP + timedelta(days=7)
KEY = str(uuid.uuid4())
PAID = {"tiers": ["plus", "trip_pass"]}
LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14, "timezone": "Europe/Lisbon"}


def runtime(on: bool) -> FlagRuntime:
    return FlagRuntime(lambda: Snapshot(flags={live.FLAG: Flag(live.FLAG, "flag", on, 100, PAID, {})}), ttl=0)


@pytest.fixture(autouse=True)
def _clean(system_conn):
    system_conn.execute("DELETE FROM fare_observations")
    system_conn.execute("DELETE FROM shared_research_cache WHERE kind = 'rentals'")
    system_conn.execute("DELETE FROM provider_calls WHERE provider = 'serpapi'")
    yield
    db.dispose_system_engines()


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        providers_mode="fake",
        ai_provider="fake",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
    )
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        c.app.state.flags = runtime(True)
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "USD"}, headers=h)
    assert r.status_code == 201
    return h, r.json()["id"]


@pytest.fixture
def world(client, system_conn):
    """Plus owner `o` with 60 credits, a trip with a Lisbon destination and a live LAX to NRT route, plus a viewer `v`."""
    o, oid = _user(client)
    v, vid = _user(client)
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus', valid_until = NULL WHERE user_id = %s", (oid,))
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key) VALUES (%s, 'monthly', 60, 60, to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'))",
        (oid,),
    )
    t = client.post("/v1/trips", json={"name": "Trip", "destinations": [LISBON]}, headers=o).json()
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (t["id"], vid))
    route = system_conn.execute(
        "INSERT INTO flight_routes (trip_id, origin_codes, destination_codes, trip_type, depart_from, depart_to, return_from, return_to, adults, cabin, is_live) "
        "VALUES (%s, '{LAX}', '{NRT}', 'round_trip', %s, %s, %s, %s, 1, 'economy', true) RETURNING id",
        (t["id"], DEP, DEP + timedelta(days=5), RET, RET + timedelta(days=5)),
    ).fetchone()[0]
    return {"o": o, "v": v, "oid": oid, "tid": t["id"], "route": str(route)}


def balance(conn, uid):
    return conn.execute("SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = %s", (uid,)).fetchone()[0]


def search(client, w, who="o", key=None, **kw):
    body = {"route_id": w["route"], "depart_date": DEP.isoformat(), "return_date": RET.isoformat(), **kw}
    return client.post(f"/v1/trips/{w['tid']}/flights/live-search", json=body, headers={**w[who], "Idempotency-Key": key or uuid.uuid4().hex})


def rent(client, w, who="o", key=None, **kw):
    body = {"check_in": DEP.isoformat(), "check_out": RET.isoformat(), **kw}
    return client.post(f"/v1/trips/{w['tid']}/lodging/rental-search", json=body, headers={**w[who], "Idempotency-Key": key or uuid.uuid4().hex})


def test_flag_off_hides_both_searches_and_charges_nothing(client, world, system_conn):
    client.app.state.flags = runtime(False)
    before = balance(system_conn, world["oid"])
    for r in (search(client, world), rent(client, world)):
        assert r.status_code == 503
        assert r.json()["code"] == "feature_disabled"
    assert balance(system_conn, world["oid"]) == before


def test_fresh_search_charges_one_credit_then_shared_cache_is_free(client, world, system_conn):
    before = balance(system_conn, world["oid"])
    first = search(client, world)
    assert first.status_code == 200, first.text
    a = first.json()
    assert a["cached"] is False and a["credits_charged"] == 1 and a["age_seconds"] == 0
    assert a["fares"] and a["fares"][0]["source"] == "serpapi" and a["fares"][0]["route_id"] == world["route"]
    assert balance(system_conn, world["oid"]) == before - 1
    b = search(client, world).json()  # another key: not a replay, a shared cache hit
    assert b["cached"] is True and b["credits_charged"] == 0 and b["age_seconds"] < 6 * 3600
    assert [f["price"] for f in b["fares"]] == [f["price"] for f in a["fares"]]
    assert balance(system_conn, world["oid"]) == before - 1


def test_replay_with_the_same_key_charges_once(client, world, system_conn):
    before = balance(system_conn, world["oid"])
    r1, r2 = search(client, world, key=KEY), search(client, world, key=KEY)
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
    assert balance(system_conn, world["oid"]) == before - 1


def test_rental_search_charges_then_serves_free(client, world, system_conn):
    before = balance(system_conn, world["oid"])
    a = rent(client, world)
    assert a.status_code == 200, a.text
    body = a.json()
    assert body["cached"] is False and body["credits_charged"] == 1 and body["offers"]
    assert body["sorted_by"] == "price, lowest first"
    b = rent(client, world).json()
    assert b["cached"] is True and b["credits_charged"] == 0 and len(b["offers"]) == len(body["offers"])
    assert balance(system_conn, world["oid"]) == before - 1


def test_rental_replay_with_the_same_key_charges_once(client, world, system_conn):
    before = balance(system_conn, world["oid"])
    r1, r2 = rent(client, world, key=KEY), rent(client, world, key=KEY)
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
    assert balance(system_conn, world["oid"]) == before - 1


def test_past_dates_are_a_422_before_anything_is_charged(client, world, system_conn):
    before, past = balance(system_conn, world["oid"]), (date.today() - timedelta(days=1)).isoformat()
    r = search(client, world, depart_date=past)
    assert r.status_code == 422
    r = rent(client, world, check_in=past)
    assert r.status_code == 422
    assert balance(system_conn, world["oid"]) == before


def test_viewer_is_forbidden(client, world):
    assert search(client, world, who="v").status_code == 403
    assert rent(client, world, who="v").status_code == 403


def test_route_not_in_live_mode_is_a_live_routes_paywall(client, world, system_conn):
    system_conn.execute("UPDATE flight_routes SET is_live = false, live_enabled_at = NULL WHERE id = %s", (world["route"],))
    r = search(client, world)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"
    assert r.json()["paywall"]["reason"] == "live_routes"


def test_departure_past_the_window_is_refused(client, world):
    r = search(
        client,
        world,
        depart_date=(date.today() + timedelta(days=200)).isoformat(),
        return_date=(date.today() + timedelta(days=207)).isoformat(),
    )
    assert r.status_code == 402 and r.json()["paywall"]["reason"] == "live_routes"


def test_provider_error_charges_nothing(client, world, system_conn, monkeypatch):
    def down(settings):
        return "k", httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(503, json={"error": "down"})))

    monkeypatch.setattr(serpapi, "client_for", down)
    before = balance(system_conn, world["oid"])
    r = search(client, world)
    assert r.status_code >= 500
    assert balance(system_conn, world["oid"]) == before


def test_entitlements_report_the_flag_for_the_web(client, world):
    assert client.get("/v1/me/entitlements", headers=world["o"]).json()["flags"]["live_search"] is True
    client.app.state.flags = runtime(False)
    assert client.get("/v1/me/entitlements", headers=world["o"]).json()["flags"]["live_search"] is False


def _spent_pass(system_conn, w, used):
    system_conn.execute("UPDATE entitlements SET tier_code = 'free', valid_until = NULL WHERE user_id = %s", (w["oid"],))
    system_conn.execute(
        "INSERT INTO trip_passes (trip_id, plan_code, purchaser_user_id, starts_at, expires_at, status, live_checks_max, live_checks_used) "
        "VALUES (%s, 'trip_pass', %s, now() - interval '1 day', now() + interval '30 days', 'active', 60, %s)",
        (w["tid"], w["oid"], used),
    )


def _checks_used(conn, w):
    return conn.execute("SELECT live_checks_used FROM trip_passes WHERE trip_id = %s", (w["tid"],)).fetchone()[0]


def test_spent_trip_pass_on_a_free_owner_is_a_live_routes_paywall(client, world, system_conn):
    _spent_pass(system_conn, world, 60)
    before = balance(system_conn, world["oid"])
    r = search(client, world)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"
    assert r.json()["paywall"]["reason"] == "live_routes"
    assert r.json()["detail"] == "This trip has used its 60 live checks."
    assert balance(system_conn, world["oid"]) == before


def test_spent_trip_pass_does_not_block_a_plus_owner(client, world, system_conn):
    _spent_pass(system_conn, world, 60)
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus', valid_until = NULL WHERE user_id = %s", (world["oid"],))
    assert search(client, world).status_code == 200


def test_last_pass_check_succeeds_then_the_next_fresh_search_is_refused(client, world, system_conn):
    _spent_pass(system_conn, world, 59)
    r = search(client, world)
    assert r.status_code == 200 and r.json()["cached"] is False
    assert _checks_used(system_conn, world) == 60
    system_conn.execute("DELETE FROM fare_observations")
    system_conn.execute("DELETE FROM shared_research_cache")
    r = search(client, world)
    assert r.status_code == 402 and r.json()["paywall"]["reason"] == "live_routes"
    assert _checks_used(system_conn, world) == 60


def test_free_user_with_an_active_trip_pass_sees_the_live_search_flag(client, world, system_conn):
    system_conn.execute("UPDATE entitlements SET tier_code = 'free', valid_until = NULL WHERE user_id = %s", (world["oid"],))
    assert client.get("/v1/me/entitlements", headers=world["o"]).json()["flags"]["live_search"] is False
    _spent_pass(system_conn, world, 0)
    assert client.get("/v1/me/entitlements", headers=world["o"]).json()["flags"]["live_search"] is True
