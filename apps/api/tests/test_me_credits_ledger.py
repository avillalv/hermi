# ruff: noqa: E501  (long SQL strings and assertions)
"""WF-132.3: GET /v1/me/credits/ledger, the history behind the credits screen (04 section 5.19)."""

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


def _row(conn, u, entry, delta, *, charged=None, action=None, res=None, note=None):
    conn.execute(
        "INSERT INTO credit_ledger (user_id, entry_type, delta, charged, reservation_id, action, note) "
        "VALUES (%s, %s::credit_entry_type, %s, %s, %s, %s::ai_action, %s)",
        (u, entry, delta, charged, res, action, note),
    )


def test_requires_a_token(client):
    assert client.get("/v1/me/credits/ledger").status_code == 401


def test_empty_for_a_new_account(client):
    h, _ = _user(client)
    r = client.get("/v1/me/credits/ledger", headers=h)
    assert r.status_code == 200
    assert r.json() == {"items": [], "next_cursor": None, "has_more": False}


def test_newest_first_with_the_documented_fields_and_no_bigint_id(client, system_conn):
    h, u = _user(client)
    res = uuid.uuid4()
    _row(system_conn, u, "grant", 12, note="monthly")
    _row(system_conn, u, "reserve", -8, res=res, action="research")
    _row(system_conn, u, "refund", 8, res=res, action="research")
    _row(system_conn, u, "settle", 0, charged=0, res=res, action="research")
    items = client.get("/v1/me/credits/ledger", headers=h).json()["items"]
    assert [i["kind"] for i in items] == ["settle", "refund", "reserve", "grant"]
    assert set(items[0]) == {"reservation_id", "at", "kind", "delta", "charged", "action", "trip_id", "run_id", "note"}
    assert items[1]["delta"] == 8 and items[1]["action"] == "research" and items[1]["reservation_id"] == str(res)
    assert sum(i["delta"] for i in items) == 12  # the history adds up to the balance movement


def test_kind_filter_and_cursor_paging(client, system_conn):
    h, u = _user(client)
    for n in range(5):
        _row(system_conn, u, "grant", n + 1)
    _row(system_conn, u, "expire", -1)
    only = client.get("/v1/me/credits/ledger", params={"kind": "expire"}, headers=h).json()
    assert [i["delta"] for i in only["items"]] == [-1] and only["has_more"] is False
    p1 = client.get("/v1/me/credits/ledger", params={"limit": 4}, headers=h).json()
    assert len(p1["items"]) == 4 and p1["has_more"] and p1["next_cursor"]
    p2 = client.get("/v1/me/credits/ledger", params={"limit": 4, "cursor": p1["next_cursor"]}, headers=h).json()
    assert len(p2["items"]) == 2 and p2["has_more"] is False and p2["next_cursor"] is None


def test_bad_kind_and_cursor_are_422(client):
    h, _ = _user(client)
    assert client.get("/v1/me/credits/ledger", params={"kind": "nope"}, headers=h).status_code == 422
    assert client.get("/v1/me/credits/ledger", params={"cursor": "!!"}, headers=h).status_code == 422


def test_never_shows_another_accounts_rows(client, system_conn):
    h, u = _user(client)
    _, other = _user(client)
    _row(system_conn, other, "grant", 99)
    _row(system_conn, u, "grant", 3)
    assert [i["delta"] for i in client.get("/v1/me/credits/ledger", headers=h).json()["items"]] == [3]


def test_a_spend_between_pages_neither_repeats_nor_skips_a_row(client, system_conn):
    h, u = _user(client)
    for n in range(5):
        _row(system_conn, u, "grant", n + 1)
    p1 = client.get("/v1/me/credits/ledger", params={"limit": 2}, headers=h).json()
    _row(system_conn, u, "reserve", -1, res=uuid.uuid4(), action="explain")  # lands after the first page was read
    p2 = client.get("/v1/me/credits/ledger", params={"limit": 10, "cursor": p1["next_cursor"]}, headers=h).json()
    assert [i["delta"] for i in p1["items"]] == [5, 4]
    assert [i["delta"] for i in p2["items"]] == [3, 2, 1]
