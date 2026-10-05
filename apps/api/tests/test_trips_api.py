# ruff: noqa: E501  (long comments)
"""WF-018.2: GET /v1/trips and POST /v1/trips (04 section 5.4) against a real PostgreSQL."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14}


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
    )
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client):
    """A bootstrapped user: (headers, me)."""
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h)
    assert r.status_code == 201
    return h, r.json()


def test_create_returns_the_trip_with_owner_destinations_and_the_me_traveler(client, system_conn):
    h, me = _user(client)
    body = {"name": "Lisbon, March", "start_date": "2027-03-12", "end_date": "2027-03-19", "destinations": [LISBON]}
    r = client.post("/v1/trips", json=body, headers=h)
    assert r.status_code == 201, r.text
    t = r.json()
    assert (t["name"], t["status"], t["my_role"], t["home_currency"], t["version"]) == ("Lisbon, March", "planning", "owner", "EUR", 1)
    assert [d["name"] for d in t["destinations"]] == ["Lisbon"]
    assert system_conn.execute("SELECT role::text FROM trip_members WHERE trip_id = %s AND user_id = %s", (t["id"], me["id"])).fetchone() == ("owner",)
    assert system_conn.execute("SELECT person_id FROM trip_people WHERE trip_id = %s", (t["id"],)).fetchone() == (uuid.UUID(me["me_person_id"]),)


def test_list_returns_my_trips_as_a_page_and_pages_by_cursor(client):
    h, _ = _user(client)
    ids = []
    for n in ("One", "Two"):
        ids.append(client.post("/v1/trips", json={"name": n, "destinations": [LISBON]}, headers=h).json()["id"])
    page = client.get("/v1/trips", headers=h).json()
    assert [t["id"] for t in page["items"]] == ids[::-1] and page["has_more"] is False and page["next_cursor"] is None
    assert page["items"][0]["destinations_label"] == "Lisbon" and page["items"][0]["my_role"] == "owner" and page["items"][0]["member_count"] == 1
    first = client.get("/v1/trips", params={"limit": 1}, headers=h).json()
    assert first["has_more"] is True and len(first["items"]) == 1
    second = client.get("/v1/trips", params={"limit": 1, "cursor": first["next_cursor"]}, headers=h).json()
    assert [first["items"][0]["id"], second["items"][0]["id"]] == ids[::-1] and second["has_more"] is False


def test_another_user_does_not_see_the_trip(client):
    a, _ = _user(client)
    b, _ = _user(client)
    client.post("/v1/trips", json={"name": "Secret"}, headers=a)
    assert client.get("/v1/trips", headers=b).json()["items"] == []


def test_list_leaves_out_trips_in_trash(client, system_conn):
    h, _ = _user(client)
    t = client.post("/v1/trips", json={"name": "Gone"}, headers=h).json()
    system_conn.execute("UPDATE trips SET deleted_at = now() WHERE id = %s", (t["id"],))
    assert client.get("/v1/trips", headers=h).json()["items"] == []


def test_a_third_active_trip_on_free_is_402_limit_reached(client):
    h, _ = _user(client)
    for n in ("One", "Two"):
        assert client.post("/v1/trips", json={"name": n}, headers=h).status_code == 201
    r = client.post("/v1/trips", json={"name": "Three"}, headers=h)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"
    pay = r.json()["paywall"]
    assert pay["reason"] == "trip_limit" and pay["trigger"] == "third_trip"
    assert pay["free_path"] == "Archive a trip or join trips other people plan"
    assert len(client.get("/v1/trips", headers=h).json()["items"]) == 2


def test_an_archived_trip_makes_room(client, system_conn):
    h, _ = _user(client)
    ids = [client.post("/v1/trips", json={"name": n}, headers=h).json()["id"] for n in ("One", "Two")]
    system_conn.execute("UPDATE trips SET status = 'archived', archived_at = now() WHERE id = %s", (ids[0],))
    assert client.post("/v1/trips", json={"name": "Three"}, headers=h).status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": ""},
        {"name": "x" * 121},
        {"name": "A", "start_date": "2027-03-12"},
        {"name": "A", "start_date": "2027-03-12", "end_date": "2027-03-01"},
        {"name": "A", "destinations": [LISBON] * 13},
        {"name": "A", "destinations": [{"name": "Nowhere"}]},
        {"name": "A", "home_currency": "euro"},
    ],
)
def test_invalid_bodies_are_422(client, body):
    h, _ = _user(client)
    r = client.post("/v1/trips", json=body, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"


def test_a_traveler_that_is_not_mine_is_refused(client):
    h, _ = _user(client)
    _, other = _user(client)
    r = client.post("/v1/trips", json={"name": "A", "traveler_ids": [other["me_person_id"]]}, headers=h)
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "traveler_ids"


def test_no_token_is_401(client):
    assert client.get("/v1/trips").status_code == 401
    assert client.post("/v1/trips", json={"name": "A"}).status_code == 401


def test_the_same_idempotency_key_creates_one_trip(client):
    h, _ = _user(client)
    k = {**h, "Idempotency-Key": str(uuid.uuid4())}
    first = client.post("/v1/trips", json={"name": "Once"}, headers=k)
    again = client.post("/v1/trips", json={"name": "Once"}, headers=k)
    assert first.status_code == 201 and again.status_code == 201 and again.json()["id"] == first.json()["id"]
    assert len(client.get("/v1/trips", headers=h).json()["items"]) == 1


def test_trips_module_maps_on_its_own():
    """A cold import of the trips repo must resolve its foreign keys (the dev server hit NoReferencedTableError once)."""
    import subprocess
    import sys

    code = "import hermi.modules.trips.repo as r; from sqlalchemy.orm import configure_mappers; configure_mappers()"
    assert subprocess.run([sys.executable, "-c", code], capture_output=True).returncode == 0
