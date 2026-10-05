# ruff: noqa: E501  (long comments)
"""GET /v1/geo/destinations (04 section 5.5): typeahead over Geoapify through places_cache, with a per-user quota. The provider is faked."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.modules.geo import router as geo
from hermi.providers import ProviderError
from hermi.providers.schemas import DestinationSuggestion
from hermi.security.jwt import mint_dev_token


def _suggestion(name):
    return DestinationSuggestion(
        label=f"{name}, Portugal", name=name, region=None, country="Portugal", country_code="PT", kind="city",
        lat=41.15, lon=-8.61, timezone="Europe/Lisbon", bbox=None, geoapify_place_id="gp-" + name,
    )


@pytest.fixture
def client(db_urls, monkeypatch):
    s = Settings(
        _env_file=None, environment="ci", auth_mode="dev", database_url=db_urls["app"],
        database_url_system=db_urls["system"], database_pool_size=10, geoapify_api_key="test-key", providers_mode="live",
    )
    calls = []

    async def fake(query, api_key, client):
        calls.append(query)
        if query.startswith("boom"):
            raise ProviderError("down")
        return [_suggestion(query.title()), _suggestion("Other")]

    monkeypatch.setattr(geo, "search_destinations", fake)
    geo._used.clear()
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings, c.calls = s, calls
        yield c


@pytest.fixture
def fake_client(db_urls, monkeypatch):
    s = Settings(
        _env_file=None, environment="ci", auth_mode="dev", database_url=db_urls["app"],
        database_url_system=db_urls["system"], database_pool_size=10, providers_mode="fake",
    )
    calls = []

    async def spy(query, api_key, client):
        calls.append(query)
        return []

    monkeypatch.setattr(geo, "search_destinations", spy)
    geo._used.clear()
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings, c.calls = s, calls
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    assert client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h).status_code == 201
    return h


def test_requires_a_token(client):
    assert client.get("/v1/geo/destinations", params={"q": "Porto"}).status_code == 401


def test_returns_suggestions_with_time_zone_and_limit(client):
    h, q = _user(client), "porto" + uuid.uuid4().hex[:6]
    r = client.get("/v1/geo/destinations", params={"q": q, "limit": 1}, headers=h)
    assert r.status_code == 200
    [one] = r.json()
    assert one["timezone"] == "Europe/Lisbon" and one["label"].endswith(", Portugal") and one["lat"] == 41.15


def test_short_or_missing_query_is_422(client):
    h = _user(client)
    assert client.get("/v1/geo/destinations", params={"q": "a"}, headers=h).status_code == 422
    assert client.get("/v1/geo/destinations", headers=h).status_code == 422


def test_second_lookup_is_served_from_places_cache(client, system_conn):
    h, q = _user(client), "lisbon" + uuid.uuid4().hex[:6]
    first = client.get("/v1/geo/destinations", params={"q": q}, headers=h).json()
    second = client.get("/v1/geo/destinations", params={"q": q.upper()}, headers=h).json()
    assert first == second and client.calls == [q]
    hits = system_conn.execute("SELECT sum(hit_count) FROM places_cache WHERE provider = 'geoapify' AND kind = 'autocomplete' AND response::text LIKE %s", (f"%{q.title()}%",)).fetchone()[0]
    assert hits == 1


def test_per_user_quota_counts_provider_lookups_not_cache_hits(client, monkeypatch):
    monkeypatch.setattr(geo, "QUOTA_PER_HOUR", 2)
    a, b, tag = _user(client), _user(client), uuid.uuid4().hex[:6]
    assert client.get("/v1/geo/destinations", params={"q": "aa" + tag}, headers=a).status_code == 200
    assert client.get("/v1/geo/destinations", params={"q": "aa" + tag}, headers=a).status_code == 200  # cached, free
    assert client.get("/v1/geo/destinations", params={"q": "bb" + tag}, headers=a).status_code == 200
    r = client.get("/v1/geo/destinations", params={"q": "cc" + tag}, headers=a)
    assert r.status_code == 429 and r.json()["code"] == "rate_limited"
    assert "cc" + tag not in client.calls  # refused before the provider was called
    assert client.get("/v1/geo/destinations", params={"q": "cc" + tag}, headers=b).status_code == 200


def test_provider_failure_is_503_and_nothing_is_cached(client):
    h = _user(client)
    q = "boom" + uuid.uuid4().hex[:6]
    assert client.get("/v1/geo/destinations", params={"q": q}, headers=h).status_code == 503
    assert client.get("/v1/geo/destinations", params={"q": q}, headers=h).status_code == 503
    assert client.calls.count(q) == 2


def test_no_api_key_is_503(client):
    h = _user(client)
    client.app.state.settings = client.settings.model_copy(update={"geoapify_api_key": None})
    assert client.get("/v1/geo/destinations", params={"q": "porto"}, headers=h).status_code == 503


def test_fake_mode_serves_fixtures_without_calling_the_provider(fake_client, system_conn):
    h = _user(fake_client)
    before = system_conn.execute("SELECT count(*) FROM places_cache").fetchone()[0]
    r = fake_client.get("/v1/geo/destinations", params={"q": "LIS"}, headers=h)
    assert r.status_code == 200
    assert [d["name"] for d in r.json()] == ["Lisbon"] and r.json()[0]["timezone"] == "Europe/Lisbon"
    assert len(fake_client.get("/v1/geo/destinations", params={"q": "or", "limit": 1}, headers=h).json()) == 1
    assert fake_client.get("/v1/geo/destinations", params={"q": "zzzz"}, headers=h).json() == []
    assert fake_client.calls == [] and not geo._used
    assert system_conn.execute("SELECT count(*) FROM places_cache").fetchone()[0] == before


def test_quota_is_charged_only_after_the_provider_succeeds(client, monkeypatch):
    monkeypatch.setattr(geo, "QUOTA_PER_HOUR", 1)
    h, tag = _user(client), uuid.uuid4().hex[:6]
    assert client.get("/v1/geo/destinations", params={"q": "boom" + tag}, headers=h).status_code == 503
    assert client.get("/v1/geo/destinations", params={"q": "ok" + tag}, headers=h).status_code == 200
