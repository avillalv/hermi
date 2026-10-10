# ruff: noqa: E501  (long SQL strings and assertions)
"""WF-132.1: GET /v1/me/credits, the balance behind the AI sheet's chips (04 section 5.19)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None, environment="ci", auth_mode="dev", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10
    )
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h)
    assert r.status_code == 201
    return h, uuid.UUID(r.json()["id"])


def _trip(client, h):
    r = client.post("/v1/trips", json={"name": "T"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_requires_a_token(client):
    assert client.get("/v1/me/credits").status_code == 401


def test_free_account_sees_its_allowance_and_the_price(client):
    h, _ = _user(client)
    r = client.get("/v1/me/credits", params={"action": "draft_trip"}, headers=h)
    assert r.status_code == 200, r.text
    b = r.json()
    assert (b["available"], b["own"], b["pool"], b["payer"], b["blocked"]) == (12, 12, 0, "own", False)
    assert b["monthly"] == 12 and b["total"] == 12
    assert "price" not in b
    assert b["spend_order"] == ["monthly", "promo", "trip_pass", "adjustment", "purchase"]
    assert [(g["kind"], g["remaining"], g["trip_id"]) for g in b["grants"]] == [("monthly", 12, None)]
    assert "expires_at" in b["grants"][0]


def test_matches_the_entitlements_credit_balance_and_counts_the_taster(client, system_conn):
    h, u = _user(client)
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key) VALUES (%s, 'promo', 40, 40, 'taster')", (u,)
    )
    c = client.get("/v1/me/credits", headers=h).json()
    e = client.get("/v1/me/entitlements", headers=h).json()["credits"]
    assert c["total"] == e["total"] == 52
    for k in ("monthly", "trip_pass", "purchased", "spend_order", "grants", "blocked", "next_monthly_grant_at"):
        assert c[k] == e[k], k


def test_pool_and_payer_for_an_editor_and_none_for_a_viewer(client, system_conn):
    ho, owner = _user(client)
    he, editor = _user(client)
    hv, viewer = _user(client)
    trip = _trip(client, ho)
    for u, role in ((editor, "editor"), (viewer, "viewer")):
        system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (trip, u, role))
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, trip_id) VALUES (%s, 'trip_pass', 40, 40, %s)", (owner, trip)
    )
    client.get("/v1/me/credits", headers=he)  # the lazy allowance is granted on the first read
    client.get("/v1/me/credits", headers=hv)
    e = client.get("/v1/me/credits", params={"trip_id": trip, "action": "draft_trip"}, headers=he).json()
    assert (e["own"], e["pool"], e["payer"], e["available"]) == (12, 40, "own", 52)  # the monthly allowance is drawn first
    system_conn.execute("UPDATE credit_grants SET remaining = 0 WHERE user_id IN (%s, %s)", (editor, viewer))
    e = client.get("/v1/me/credits", params={"trip_id": trip, "action": "draft_trip"}, headers=he).json()
    assert (e["own"], e["pool"], e["payer"], e["available"]) == (0, 40, "trip_pass", 40)
    v = client.get("/v1/me/credits", params={"trip_id": trip}, headers=hv).json()
    assert (v["own"], v["pool"], v["payer"], v["available"]) == (0, 0, "own", 0)


def test_a_trip_the_caller_is_not_on_is_404(client):
    ho, _ = _user(client)
    hs, _ = _user(client)
    trip = _trip(client, ho)
    assert client.get("/v1/me/credits", params={"trip_id": trip}, headers=hs).status_code == 404
    assert client.get("/v1/me/credits", params={"trip_id": str(uuid.uuid4())}, headers=hs).status_code == 404


def test_unknown_action_is_422(client):
    h, _ = _user(client)
    assert client.get("/v1/me/credits", params={"action": "nope"}, headers=h).status_code == 422
