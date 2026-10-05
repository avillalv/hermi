# ruff: noqa: E501  (long comments)
"""WF-033.1: places search through places_cache, rate limit and daily quota, detail with a Wikipedia summary, saved places (04 section 5.11).

PROVIDERS_MODE is fake (recorded fixtures, no network); tests patch the provider functions to count real calls.
"""

import time
import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.modules.places import service
from hermi.security import rate_limit
from hermi.security.jwt import mint_dev_token

LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14, "timezone": "Europe/Lisbon"}
SEARCH = {"q": "belem", "lat": 38.7, "lon": -9.1}


@pytest.fixture
def client(db_urls):
    s = Settings(_env_file=None, environment="ci", auth_mode="dev", providers_mode="fake", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10)
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


@pytest.fixture(autouse=True)
def _empty_cache(system_conn):
    """The test database is shared, so every test starts with a cold cache."""
    system_conn.execute("DELETE FROM places_cache")


@pytest.fixture
def calls(monkeypatch):
    """Counts of provider calls, with the fixture behavior kept."""
    n = {"search": 0, "details": 0, "wiki": 0}
    for name, fn in (("search", service.fetch_search), ("details", service.fetch_details), ("wiki", service.fetch_wiki)):
        def wrap(*a, _fn=fn, _name=name, **k):
            n[_name] += 1
            return _fn(*a, **k)
        monkeypatch.setattr(service, "fetch_" + name, wrap)
    return n


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h)
    assert r.status_code == 201
    return h, r.json()


@pytest.fixture
def world(client, system_conn):
    o, ou = _user(client)
    e, eu = _user(client)
    v, vu = _user(client)
    s, _ = _user(client)
    t = client.post("/v1/trips", json={"name": "Trip", "destinations": [LISBON], "start_date": "2027-05-01", "end_date": "2027-05-03"}, headers=o).json()
    for u, role in ((eu, "editor"), (vu, "viewer")):
        system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (t["id"], u["id"], role))
    return {"o": o, "e": e, "v": v, "s": s, "t": t, "ou": ou}


def _search(client, h, **kw):
    return client.get("/v1/places/search", params={**SEARCH, **kw}, headers=h)


def test_search_returns_places_with_attribution(client, world, calls):
    r = _search(client, world["o"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cached"] is False and body["sorted_by"] == "relevance" and body["attribution"] == "Powered by Geoapify, © OpenStreetMap contributors"
    assert [p["name"] for p in body["places"]] == ["Belem Tower"] and body["places"][0]["id"] == "geoapify:fixture-belem"


def test_repeated_search_hits_the_cache_with_a_one_week_ttl(client, world, calls, system_conn):
    first = _search(client, world["o"]).json()
    second = _search(client, world["o"]).json()
    assert calls["search"] == 1 and first["cached"] is False and second["cached"] is True and first["places"] == second["places"]
    days = system_conn.execute("SELECT max(extract(epoch FROM expires_at - fetched_at) / 86400) FROM places_cache WHERE kind = 'places_search'").fetchone()[0]
    assert round(days) == 7
    assert system_conn.execute("SELECT max(hit_count) FROM places_cache WHERE kind = 'places_search'").fetchone()[0] >= 1
    _search(client, world["s"])  # the cache is shared between users
    assert calls["search"] == 1


def test_category_search_and_validation(client, world):
    r = client.get("/v1/places/search", params={"category": "museums", "lat": 38.7, "lon": -9.1}, headers=world["o"])
    assert r.status_code == 200, r.text
    assert [p["name"] for p in r.json()["places"]] == ["Museu do Azulejo"] and r.json()["sorted_by"] == "distance"
    assert client.get("/v1/places/search", params={"lat": 1, "lon": 1}, headers=world["o"]).status_code == 422  # no q and no category
    assert _search(client, world["o"], category="casinos").status_code == 422
    assert client.get("/v1/places/search", params={"q": "belem"}, headers=world["o"]).status_code == 422  # no point
    assert client.get("/v1/places/search", params=SEARCH).status_code == 401


def test_search_around_a_destination(client, world, calls):
    dest = client.get(f"/v1/trips/{world['t']['id']}/destinations", headers=world["o"]).json()[0]["id"]
    r = client.get("/v1/places/search", params={"q": "belem", "destination_id": dest, "trip_id": world["t"]["id"]}, headers=world["o"])
    assert r.status_code == 200 and len(r.json()["places"]) == 1
    assert client.get("/v1/places/search", params={"q": "belem", "destination_id": str(uuid.uuid4())}, headers=world["o"]).status_code == 404


def test_rate_limit_is_30_a_minute(client, world, calls):
    assert rate_limit.ROUTE_CLASSES["places_search"] == (30, 60)
    h = world["o"]
    for _ in range(30):
        assert _search(client, h).status_code == 200  # cached after the first, but every request counts
    r = _search(client, h)
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and int(r.headers["Retry-After"]) >= 1
    assert _search(client, world["s"]).status_code == 200  # per user


def test_daily_quota_stops_provider_calls_but_cached_results_keep_working(client, world, calls, system_conn):
    assert _search(client, world["o"]).status_code == 200  # fills the cache, spends 1
    day = int(time.time() // 86400) * 86400
    system_conn.execute("UPDATE rate_limit_counters SET count = 30 WHERE bucket = %s AND window_start = to_timestamp(%s)", (f"places_day:{world['ou']['id']}", day))
    again = _search(client, world["o"])
    assert again.status_code == 200 and again.json()["cached"] is True
    r = _search(client, world["o"], q="museu")  # a miss
    assert r.status_code == 429 and r.json()["code"] == "quota_exceeded" and "Retry-After" in r.headers
    assert calls["search"] == 1  # refused before any provider call


def test_a_search_spends_one_and_a_hit_spends_none(client, world, calls, system_conn):
    _search(client, world["o"])
    _search(client, world["o"])
    n = system_conn.execute("SELECT sum(count) FROM rate_limit_counters WHERE bucket = %s", (f"places_day:{world['ou']['id']}",)).fetchone()[0]
    assert n == 1


def test_provider_failure_is_503_and_does_not_spend(client, world, monkeypatch, system_conn):
    def boom(*a, **k):
        raise service.UNAVAILABLE
    monkeypatch.setattr(service, "fetch_search", boom)
    r = _search(client, world["o"])
    assert r.status_code == 503 and r.json()["code"] == "provider_unavailable"
    assert system_conn.execute("SELECT count(*) FROM rate_limit_counters WHERE bucket = %s", (f"places_day:{world['ou']['id']}",)).fetchone()[0] == 0


def test_detail_adds_the_wikipedia_summary_and_caches_it(client, world, calls):
    pid = _search(client, world["o"]).json()["places"][0]["id"]
    r = client.get(f"/v1/places/{pid}", headers=world["o"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["name"] == "Belem Tower" and d["opening_hours"] and d["attribution"].startswith("Powered by Geoapify")
    assert d["wiki"]["extract"].startswith("The Belem Tower") and d["wiki"]["url"] and d["wiki"]["attribution"] == "Text from Wikipedia, CC BY-SA 4.0"
    assert calls["details"] == 0  # the search already held the details
    client.get(f"/v1/places/{pid}", headers=world["o"])
    assert calls["wiki"] == 1


def test_detail_fetches_details_once_for_a_basic_place(client, world, calls):
    pid = _search(client, world["o"], q="ramen").json()["places"][0]["id"]
    d = client.get(f"/v1/places/{pid}", headers=world["o"]).json()
    assert d["has_details"] is True and d["wiki"] is None and calls["details"] == 1
    client.get(f"/v1/places/{pid}", headers=world["s"])
    assert calls["details"] == 1


def test_detail_unknown_and_malformed_ids(client, world):
    assert client.get("/v1/places/geoapify:nope", headers=world["o"]).status_code == 404
    assert client.get("/v1/places/other:abc", headers=world["o"]).status_code == 422


def test_saved_places_crud_is_idempotent_and_role_checked(client, world, system_conn):
    base = f"/v1/trips/{world['t']['id']}/saved-places"
    pid = _search(client, world["o"]).json()["places"][0]["id"]
    r = client.post(base, json={"place_id": pid, "note": "sunset"}, headers=world["e"])
    assert r.status_code == 201, r.text
    saved = r.json()
    assert saved["place"]["id"] == pid and saved["place"]["name"] == "Belem Tower" and saved["note"] == "sunset" and saved["added_by"]["id"]
    assert saved["place"]["opening_hours"] and saved["place"]["lat"] is not None
    again = client.post(base, json={"place_id": pid}, headers=world["o"])
    assert again.status_code == 201 and again.json()["id"] == saved["id"]
    page = client.get(base, headers=world["v"])  # a viewer can read
    assert page.status_code == 200 and [i["id"] for i in page.json()["items"]] == [saved["id"]] and page.json()["attribution"]
    assert system_conn.execute("SELECT count(*) FROM saved_places WHERE trip_id = %s", (world["t"]["id"],)).fetchone()[0] == 1
    assert client.delete(f"{base}/{saved['id']}", headers=world["e"]).status_code == 204
    assert client.delete(f"{base}/{saved['id']}", headers=world["e"]).status_code == 404
    assert client.get(base, headers=world["o"]).json()["items"] == []


def test_viewer_writes_are_rejected_and_strangers_see_nothing(client, world):
    base = f"/v1/trips/{world['t']['id']}/saved-places"
    pid = _search(client, world["o"]).json()["places"][0]["id"]
    saved = client.post(base, json={"place_id": pid}, headers=world["o"]).json()
    assert client.post(base, json={"place_id": pid}, headers=world["v"]).status_code == 403
    assert client.delete(f"{base}/{saved['id']}", headers=world["v"]).status_code == 403
    assert client.get(base, headers=world["s"]).status_code == 404
    assert client.post(base, json={"place_id": pid}, headers=world["s"]).status_code == 404


def test_saving_validates_and_never_calls_a_provider(client, world, calls):
    base = f"/v1/trips/{world['t']['id']}/saved-places"
    assert client.post(base, json={"place_id": "nope"}, headers=world["o"]).status_code == 422
    assert client.post(base, json={"place_id": "geoapify:unseen"}, headers=world["o"]).json()["code"] == "place_not_found"
    assert client.post(base, json={"place_id": "geoapify:x", "extra": 1}, headers=world["o"]).status_code == 422
    assert calls == {"search": 0, "details": 0, "wiki": 0}


def test_saved_places_page(client, world):
    base = f"/v1/trips/{world['t']['id']}/saved-places"
    for q in ("belem", "museu", "ramen"):
        pid = _search(client, world["o"], q=q).json()["places"][0]["id"]
        assert client.post(base, json={"place_id": pid}, headers=world["o"]).status_code == 201
    first = client.get(base, params={"limit": 2}, headers=world["o"]).json()
    assert len(first["items"]) == 2 and first["has_more"] and first["next_cursor"]
    rest = client.get(base, params={"limit": 2, "cursor": first["next_cursor"]}, headers=world["o"]).json()
    assert len(rest["items"]) == 1 and not rest["has_more"]
    assert client.get(base, params={"cursor": "!!"}, headers=world["o"]).status_code == 422


def test_detail_of_a_cached_basic_place_works_over_the_daily_cap(client, world, calls, system_conn):
    pid = _search(client, world["o"], q="ramen").json()["places"][0]["id"]
    day = int(time.time() // 86400) * 86400
    system_conn.execute("UPDATE rate_limit_counters SET count = 30 WHERE bucket = %s AND window_start = to_timestamp(%s)", (f"places_day:{world['ou']['id']}", day))
    r = client.get(f"/v1/places/{pid}", headers=world["o"])
    assert r.status_code == 200 and r.json()["has_details"] is False and calls["details"] == 0
    miss = _search(client, world["o"], q="museu")
    assert miss.status_code == 429 and miss.json()["detail"] == "You have reached today's 30 place searches. Saved places still work. Searches reset at midnight."


def test_no_details_from_the_provider_is_remembered(client, world, calls, monkeypatch):
    pid = _search(client, world["o"], q="ramen").json()["places"][0]["id"]
    monkeypatch.setattr(service, "fetch_details", lambda *a, **k: calls.__setitem__("details", calls["details"] + 1))
    assert client.get(f"/v1/places/{pid}", headers=world["o"]).status_code == 200
    assert client.get(f"/v1/places/{pid}", headers=world["o"]).status_code == 200
    assert calls["details"] == 1


def test_a_stranger_cannot_search_around_another_trips_destination(client, world):
    dest = client.get(f"/v1/trips/{world['t']['id']}/destinations", headers=world["o"]).json()[0]["id"]
    r = client.get("/v1/places/search", params={"q": "belem", "destination_id": dest}, headers=world["s"])
    assert r.status_code == 404
