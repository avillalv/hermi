# ruff: noqa: E501  (long SQL strings)
"""WF-030.1: cached fares module. Routes API limits, Travelpayouts through the ledger, 6 h cache, observation dedupe, trip fare links."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import NotConfigured, Settings
from hermi.main import create_app
from hermi.modules.flights import fares
from hermi.providers import ProviderError, travelpayouts
from hermi.security.jwt import mint_dev_token

ROUTE = {
    "origin_codes": ["LAX"],
    "destination_codes": ["TYO"],
    "trip_type": "round_trip",
    "depart_from": "2026-11-01",
    "depart_to": "2026-11-30",
    "return_from": "2026-11-10",
    "return_to": "2026-11-25",
    "adults": 2,
    "children": 0,
    "cabin": "economy",
    "mode": "cached",
    "active": True,
}
OBS_OF_ROUTE = "SELECT o.id FROM fare_observations o JOIN trip_fare_links l ON l.observation_id = o.id WHERE l.route_id = %s"


@pytest.fixture
def client(db_urls):
    s = Settings(_env_file=None, environment="ci", auth_mode="dev", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10)
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


@pytest.fixture(autouse=True)
def _clean_observations(system_conn):
    """Observations are shared by every trip, so an earlier test's rows would count as a fresh cache."""
    system_conn.execute("DELETE FROM fare_observations")


@pytest.fixture
def session(db_urls):
    engine = db.make_engine(db_urls["system"])
    with Session(engine) as s:
        yield s
    engine.dispose()


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    assert client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h).status_code == 201
    return h


def _trip(client, h):
    r = client.post("/v1/trips", json={"name": "Tokyo"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _route(client, h, trip, **kw):
    return client.post(f"/v1/trips/{trip}/routes", json={**ROUTE, **kw}, headers=h)


def _setup(client, h, **kw):
    trip = _trip(client, h)
    r = _route(client, h, trip, **kw)
    assert r.status_code == 201, r.text
    return trip, r.json()["id"]


def _rows(system_conn, sql, *args):
    return system_conn.execute(sql, args).fetchall()


class Counting:
    """The recorded fixture, counting the requests that reach the provider."""

    def __init__(self):
        self.calls = 0
        inner = travelpayouts.fixture_client()

        def handler(request):
            self.calls += 1
            return inner.send(request)

        self.client = httpx.Client(transport=httpx.MockTransport(handler))


def test_create_route_and_free_route_limit(client):
    h = _user(client)
    trip = _trip(client, h)
    r = _route(client, h, trip)
    assert r.status_code == 201, r.text
    assert r.json()["mode"] == "cached" and r.json()["version"] == 1 and r.json()["last_checked_at"] is None
    second = _route(client, h, trip, label="Other")
    assert second.status_code == 402 and second.json()["code"] == "limit_reached"
    assert second.json()["paywall"]["trigger"] == "second_route"
    assert len(client.get(f"/v1/trips/{trip}/routes", headers=h).json()) == 1


def test_airports_per_side_limit_on_free(client):
    h = _user(client)
    trip = _trip(client, h)
    r = _route(client, h, trip, origin_codes=["LAX", "SFO", "SAN"])
    assert r.status_code == 402 and r.json()["code"] == "limit_reached" and "paywall" not in r.json()
    assert _route(client, h, trip, origin_codes=["LAX", "SFO"], destination_codes=["NRT", "HND"]).status_code == 201


def test_live_mode_needs_a_live_slot(client):
    h = _user(client)
    trip = _trip(client, h)
    assert _route(client, h, trip, mode="live").status_code == 402  # Free has no live routes


def test_viewer_cannot_create_and_stranger_gets_404(client, system_conn):
    h, viewer, stranger = _user(client), _user(client), _user(client)
    trip = _trip(client, h)
    me = client.get("/v1/me", headers=viewer).json()["id"]
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (trip, me))
    assert _route(client, viewer, trip).status_code == 403
    assert client.get(f"/v1/trips/{trip}/routes", headers=viewer).status_code == 200
    assert client.get(f"/v1/trips/{trip}/routes", headers=stranger).status_code == 404


def test_put_is_versioned_and_delete_removes(client):
    h = _user(client)
    trip, rid = _setup(client, h)
    url = f"/v1/trips/{trip}/routes/{rid}"
    assert client.put(url, json={**ROUTE, "label": "Spring"}, headers=h).status_code == 428
    ok = client.put(url, json={**ROUTE, "label": "Spring", "version": 1}, headers=h)
    assert ok.status_code == 200 and ok.json()["label"] == "Spring" and ok.json()["version"] == 2
    assert client.put(url, json={**ROUTE, "version": 1}, headers=h).status_code == 409
    assert client.delete(url, headers=h).status_code == 204
    assert client.get(f"/v1/trips/{trip}/routes", headers=h).json() == []


def test_validation_return_rule_and_window(client):
    h = _user(client)
    trip = _trip(client, h)
    assert _route(client, h, trip, return_from=None, return_to=None).status_code == 422  # round trip needs a return window or nights
    assert _route(client, h, trip, depart_to="2026-10-01").status_code == 422
    assert _route(client, h, trip, origin_codes=[]).status_code == 422
    assert _route(client, h, trip, depart_from="2026-09-01", depart_to="2026-10-04", return_from="2026-09-05", return_to="2026-10-04").status_code == 422  # in the past


def test_window_at_most_330_days_out(client):
    h = _user(client)
    trip = _trip(client, h)
    today = datetime.now(UTC).date()
    far = lambda n: (today + timedelta(days=n)).isoformat()  # noqa: E731
    r = _route(client, h, trip, depart_from=far(300), depart_to=far(331), return_from=far(300), return_to=far(331))
    assert r.status_code == 422
    assert _route(client, h, trip, depart_from=far(300), depart_to=far(320), return_from=far(300), return_to=far(331)).status_code == 422  # return too far
    assert _route(client, h, trip, depart_from=far(300), depart_to=far(330), return_from=far(300), return_to=far(330)).status_code == 201


def test_refresh_keeps_cheapest_per_fare_links_and_ledger(client, session, system_conn):
    h = _user(client)
    _, rid = _setup(client, h)
    system_conn.execute("DELETE FROM provider_calls WHERE provider = 'travelpayouts'")
    out = fares.refresh_route(session, uuid.UUID(rid), client=Counting().client, token="t", now=datetime(2026, 10, 5, 9, tzinfo=UTC))
    session.commit()
    # Nov 10 NRT 760 and NH 905 share a key, so only the cheaper is kept. Dec 3 is outside the depart window.
    assert out.cached is False and out.linked == 2
    got = _rows(system_conn, "SELECT o.destination, o.price_total_minor, o.currency, o.confidence, o.source, o.deep_link_template FROM trip_fare_links l JOIN fare_observations o ON o.id = l.observation_id WHERE l.route_id = %s ORDER BY o.price_total_minor", rid)
    assert [g[:5] for g in got] == [("NRT", 76000 * 2, "USD", "cached", "travelpayouts"), ("HND", 81200 * 2, "USD", "cached", "travelpayouts")]
    assert got[0][5].startswith("https://www.aviasales.com/search/")
    call = _rows(system_conn, "SELECT status_code, ok, cached, cost_usd_micros FROM provider_calls WHERE provider = 'travelpayouts'")
    assert call[0] == (200, True, False, 0)
    assert _rows(system_conn, "SELECT last_checked_at IS NOT NULL FROM flight_routes WHERE id = %s", rid) == [(True,)]


def test_stops_and_window_filters(client, session, system_conn):
    h = _user(client)
    _, rid = _setup(client, h, max_stops=0, depart_to="2026-11-11")
    fares.refresh_route(session, uuid.UUID(rid), client=Counting().client, token="t", now=datetime(2026, 10, 5, tzinfo=UTC))
    session.commit()
    got = _rows(system_conn, "SELECT o.airlines, o.stops_out FROM trip_fare_links l JOIN fare_observations o ON o.id = l.observation_id WHERE l.route_id = %s", rid)
    assert got == [(["NH"], 0)]  # the cheaper MU fare has a stop; the Nov 12 fare departs after the window


def test_cache_window_six_hours_and_dedupe(client, session, system_conn):
    h = _user(client)
    _, rid = _setup(client, h)
    system_conn.execute("DELETE FROM provider_calls WHERE provider = 'travelpayouts'")
    c, t0, route = Counting(), datetime(2026, 10, 5, 9, tzinfo=UTC), uuid.UUID(rid)
    fares.refresh_route(session, route, client=c.client, token="t", now=t0)
    session.commit()
    first_calls = c.calls
    before = _rows(system_conn, OBS_OF_ROUTE, rid)

    again = fares.refresh_route(session, route, client=c.client, token="t", now=t0 + timedelta(hours=5, minutes=59))
    session.commit()
    assert again.cached is True and c.calls == first_calls and again.linked == 2
    cached = _rows(system_conn, "SELECT cache_layer, cost_usd_micros FROM provider_calls WHERE provider = 'travelpayouts' AND cached")
    assert cached and cached[0][1] == 0

    later = fares.refresh_route(session, route, client=c.client, token="t", now=t0 + timedelta(hours=6, minutes=1))
    session.commit()
    assert later.cached is False and c.calls == 2 * first_calls
    assert _rows(system_conn, OBS_OF_ROUTE, rid) == before  # the same fares seen again reuse the same observations
    assert _rows(system_conn, "SELECT count(*) FROM trip_fare_links WHERE route_id = %s", rid) == [(2,)]
    expires = _rows(system_conn, "SELECT min(expires_at) FROM fare_observations WHERE id = ANY(%s)", [r[0] for r in before])[0][0]
    assert expires > t0 + timedelta(hours=6)  # the cache window moved forward


def test_cached_fares_never_touch_credits(client, session, system_conn):
    h = _user(client)
    trip, rid = _setup(client, h)
    uid = client.get("/v1/me", headers=h).json()["id"]
    state = lambda: (  # noqa: E731
        _rows(system_conn, "SELECT count(*) FROM credit_ledger WHERE user_id = %s", uid),
        _rows(system_conn, "SELECT count(*), coalesce(sum(remaining), 0) FROM credit_grants WHERE user_id = %s", uid),
    )
    before = state()
    now = datetime(2026, 10, 5, 9, tzinfo=UTC)
    fares.refresh_route(session, uuid.UUID(rid), client=Counting().client, token="t", now=now)  # fresh
    fares.refresh_route(session, uuid.UUID(rid), client=Counting().client, token="t", now=now + timedelta(hours=1))  # cached
    session.commit()
    assert client.get(f"/v1/trips/{trip}/routes", headers=h).status_code == 200
    assert client.get(f"/v1/trips/{trip}/routes/{rid}/fares", headers=h).status_code == 200
    assert state() == before


def test_two_trips_share_observations(client, session, system_conn):
    h1, h2 = _user(client), _user(client)
    _, r1 = _setup(client, h1)
    _, r2 = _setup(client, h2)
    now = datetime(2026, 10, 5, 9, tzinfo=UTC)
    fares.refresh_route(session, uuid.UUID(r1), client=Counting().client, token="t", now=now)
    c = Counting()
    fares.refresh_route(session, uuid.UUID(r2), client=c.client, token="t", now=now + timedelta(hours=1))
    session.commit()
    assert c.calls == 0  # served from the shared observations
    ids = _rows(system_conn, OBS_OF_ROUTE + " ORDER BY o.id", r1)
    assert ids and ids == _rows(system_conn, OBS_OF_ROUTE + " ORDER BY o.id", r2)


def test_provider_failure_is_recorded_and_raised(client, session, system_conn):
    h = _user(client)
    _, rid = _setup(client, h)
    system_conn.execute("DELETE FROM provider_calls WHERE provider = 'travelpayouts'")
    bad = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500, json={})))
    with pytest.raises(ProviderError):
        fares.refresh_route(session, uuid.UUID(rid), client=bad, token="t", now=datetime(2026, 10, 5, tzinfo=UTC))
    session.rollback()
    assert _rows(system_conn, "SELECT ok FROM provider_calls WHERE provider = 'travelpayouts'") == [(False,)]
    assert _rows(system_conn, "SELECT last_checked_at FROM flight_routes WHERE id = %s", rid) == [(None,)]


def test_no_token_uses_the_fixture_only_in_fake_mode():
    token, client = fares.provider_for(Settings(_env_file=None, providers_mode="fake"))
    assert client is not None and token
    with pytest.raises(NotConfigured):
        fares.provider_for(Settings(_env_file=None, providers_mode="live"))


def test_fares_list_shows_age_price_and_filters(client, session):
    h = _user(client)
    trip, rid = _setup(client, h)
    fares.refresh_route(session, uuid.UUID(rid), client=Counting().client, token="t", now=datetime.now(UTC))
    session.commit()
    url = f"/v1/trips/{trip}/routes/{rid}/fares"
    page = client.get(url, headers=h).json()
    assert page["has_more"] is False and len(page["items"]) == 2
    f = page["items"][0]
    assert f["price"] == {"amount_minor": 152000, "currency": "USD"} and f["passengers"] == 2 and f["confidence"] == "cached"
    assert f["age_label"].startswith("cached ") and f["age_label"].endswith(" ago")
    assert "observation_id" not in f and f["hidden"] is False and f["route_id"] == rid
    prices = [x["price"]["amount_minor"] for x in page["items"]]
    assert prices == sorted(prices)
    first = client.get(url + "?limit=1", headers=h).json()
    assert len(first["items"]) == 1 and first["has_more"] is True
    assert len(client.get(url + f"?limit=1&cursor={first['next_cursor']}", headers=h).json()["items"]) == 1
    assert client.get(url + "?source=serpapi", headers=h).json()["items"] == []


def test_refresh_endpoint_links_fares_inline_without_credits(client, system_conn):
    h = _user(client)
    trip, rid = _setup(client, h)
    uid = client.get("/v1/me", headers=h).json()["id"]
    credits = lambda: _rows(system_conn, "SELECT (SELECT count(*) FROM credit_ledger WHERE user_id = %s), (SELECT count(*) FROM credit_grants WHERE user_id = %s)", uid, uid)  # noqa: E731
    before = credits()
    r = client.post(f"/v1/trips/{trip}/flights/refresh", json={}, headers=h)
    assert r.status_code == 202 and r.json()["status"] == "done" and r.json()["location"] == f"/v1/trips/{trip}/routes"
    assert _rows(system_conn, "SELECT count(*) FROM trip_fare_links WHERE route_id = %s", rid) == [(2,)]
    assert client.post(f"/v1/trips/{trip}/flights/refresh", json={"route_ids": [rid]}, headers=h).status_code == 202
    assert credits() == before


def test_refresh_endpoint_roles_and_ids(client, system_conn):
    h, viewer = _user(client), _user(client)
    trip, rid = _setup(client, h)
    _, other_rid = _setup(client, _user(client))
    me = client.get("/v1/me", headers=viewer).json()["id"]
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (trip, me))
    url = f"/v1/trips/{trip}/flights/refresh"
    assert client.post(url, json={}, headers=viewer).status_code == 403
    assert client.post(url, json={"route_ids": [other_rid]}, headers=h).status_code == 404  # another trip's route
    assert client.post(url, json={"route_ids": [str(uuid.uuid4())]}, headers=h).status_code == 404
    assert client.post(url, json={"route_ids": [str(uuid.uuid4()) for _ in range(21)]}, headers=h).status_code == 422
    assert _rows(system_conn, "SELECT count(*) FROM trip_fare_links WHERE route_id = %s", rid) == [(0,)]


def test_refresh_endpoint_is_limited_to_ten_an_hour_per_trip(client):
    h = _user(client)
    trip, _ = _setup(client, h)
    url = f"/v1/trips/{trip}/flights/refresh"
    codes = [client.post(url, json={}, headers=h).status_code for _ in range(11)]
    assert codes == [202] * 10 + [429]
    other = _trip(client, h)
    assert client.post(f"/v1/trips/{other}/flights/refresh", json={}, headers=h).status_code == 202  # the limit is per trip
