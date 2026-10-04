# ruff: noqa: E501  (long SQL strings)
"""WF-016.1: Idempotency-Key replay (04 section 1.6) and If-Match parsing (04 section 1.7)."""

import itertools
import json

import pytest
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.deps import CurrentUser
from hermi.errors import ApiError
from hermi.main import create_app
from hermi.security.idempotency import request_hash
from hermi.security.jwt import mint_dev_token
from hermi.security.preconditions import resolve_version, version_conflict

KEY = "key-0000-aaaa"
REQUIRED = "/v1/trips/00000000-0000-0000-0000-000000000001/ai/draft"  # matches /trips/{id}/ai/*
OPTIONAL = "/v1/_test/free"


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        cors_allowed_origins="https://hermi.example",
    )
    app = create_app(s)
    calls = itertools.count(1)
    r = APIRouter(prefix="/v1")

    @r.post("/trips/{trip_id}/ai/draft", status_code=201)
    def required(body: dict, user: CurrentUser):
        if body.get("boom"):
            raise RuntimeError("boom")
        return {"n": next(calls), "echo": body}

    @r.post("/_test/free")
    def free(body: dict, user: CurrentUser):
        return {"n": next(calls)}

    @r.post("/_test/modes")
    def modes(body: dict, user: CurrentUser):
        m = body.get("mode")
        if m == "429":
            return JSONResponse({"n": next(calls)}, 429)
        if m == "409":
            raise ApiError(409, "state_conflict", "Refresh.")
        if m == "text":
            return PlainTextResponse("plain")
        if m == "headers":
            return JSONResponse(
                {"n": next(calls)},
                201,
                {"ETag": '"1"', "Location": "/v1/things/1", "X-Other": "no"},
            )
        return {"n": next(calls)}

    @r.patch("/_test/versioned")
    def patch(request: Request, body: dict):
        return {"v": resolve_version(request, body.get("version"))}

    @r.patch("/_test/conflict")
    def conflict():
        raise version_conflict({"id": "x", "version": 7})

    app.include_router(r)
    with TestClient(app, raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _h(client, sub, key=KEY):
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub)}
    if key:
        h["Idempotency-Key"] = key
    return h


def test_missing_key_on_required_route_is_400(client, make_user):
    _, sub = make_user()
    r = client.post(REQUIRED, json={}, headers=_h(client, sub, key=None))
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"


def test_unauthenticated_request_skips_the_middleware(client):
    r = client.post(REQUIRED, json={}, headers={"Idempotency-Key": KEY})
    assert r.status_code == 401


@pytest.mark.parametrize("key", ["short", "x" * 129])
def test_key_length_is_8_to_128(client, make_user, key):
    _, sub = make_user()
    r = client.post(REQUIRED, json={}, headers=_h(client, sub, key=key))
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"


def test_replay_returns_stored_response_and_runs_once(client, make_user):
    _, sub = make_user()
    first = client.post(REQUIRED, json={"a": 1, "b": 2}, headers=_h(client, sub))
    again = client.post(
        REQUIRED,
        content=json.dumps({"b": 2, "a": 1}),
        headers={**_h(client, sub), "Content-Type": "application/json"},
    )
    assert first.status_code == again.status_code == 201
    assert "idempotent-replay" not in first.headers
    assert again.headers["Idempotent-Replay"] == "true"
    assert again.json() == first.json()  # same n: the handler did not run again


def test_same_key_different_body_is_422(client, make_user):
    _, sub = make_user()
    client.post(REQUIRED, json={"a": 1}, headers=_h(client, sub))
    r = client.post(REQUIRED, json={"a": 2}, headers=_h(client, sub))
    assert r.status_code == 422 and r.json()["code"] == "idempotency_key_reused"


def test_same_key_different_path_is_422(client, make_user):
    _, sub = make_user()
    client.post(OPTIONAL, json={}, headers=_h(client, sub))
    r = client.post(REQUIRED, json={}, headers=_h(client, sub))
    assert r.json()["code"] == "idempotency_key_reused"


def test_in_progress_is_409_with_retry_after(client, make_user, system_conn):
    uid, sub = make_user()
    system_conn.execute(
        "INSERT INTO idempotency_keys (user_id, key, method, path, request_hash) VALUES (%s, %s, 'POST', %s, %s)",
        (uid, KEY, REQUIRED, request_hash(b'{"a":1}')),
    )
    r = client.post(REQUIRED, json={"a": 1}, headers=_h(client, sub))
    assert r.status_code == 409 and r.json()["code"] == "idempotency_in_progress"
    assert r.headers["Retry-After"] == "1"


def test_expired_key_runs_again(client, make_user, system_conn):
    uid, sub = make_user()
    first = client.post(REQUIRED, json={"a": 1}, headers=_h(client, sub))
    system_conn.execute(
        "UPDATE idempotency_keys SET expires_at = now() - interval '1 minute' WHERE user_id = %s",
        (uid,),
    )
    again = client.post(REQUIRED, json={"a": 1}, headers=_h(client, sub))
    assert "idempotent-replay" not in again.headers
    assert again.json()["n"] == first.json()["n"] + 1


def test_5xx_releases_the_key(client, make_user, system_conn):
    uid, sub = make_user()
    r = client.post(REQUIRED, json={"boom": True}, headers=_h(client, sub))
    assert r.status_code == 500
    count = system_conn.execute("SELECT count(*) FROM idempotency_keys WHERE user_id = %s", (uid,))
    assert count.fetchone() == (0,)
    ok = client.post(
        REQUIRED, json={"boom": False}, headers=_h(client, sub)
    )  # a retry with the key
    assert ok.status_code == 201 and "idempotent-replay" not in ok.headers


def test_stored_row_is_completed_with_status(client, make_user, system_conn):
    uid, sub = make_user()
    client.post(REQUIRED, json={}, headers=_h(client, sub))
    row = system_conn.execute(
        "SELECT state, status_code, method, path FROM idempotency_keys WHERE user_id = %s", (uid,)
    ).fetchone()
    assert row == ("completed", 201, "POST", REQUIRED)


def test_keys_are_per_user(client, make_user):
    _, a = make_user()
    _, b = make_user()
    ra = client.post(REQUIRED, json={}, headers=_h(client, a))
    rb = client.post(REQUIRED, json={}, headers=_h(client, b))
    assert "idempotent-replay" not in rb.headers and rb.json()["n"] == ra.json()["n"] + 1


def test_optional_key_is_honored_on_other_posts(client, make_user):
    _, sub = make_user()
    assert client.post(OPTIONAL, json={}, headers=_h(client, sub, key=None)).status_code == 200
    a = client.post(OPTIONAL, json={}, headers=_h(client, sub))
    b = client.post(OPTIONAL, json={}, headers=_h(client, sub))
    assert b.headers["Idempotent-Replay"] == "true" and a.json() == b.json()


def test_cors_allows_and_exposes_the_concurrency_headers(client):
    r = client.options(
        "/v1/_test/free",
        headers={
            "Origin": "https://hermi.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "idempotency-key,if-match,if-none-match",
        },
    )
    assert r.status_code == 200
    r = client.get("/health/live", headers={"Origin": "https://hermi.example"})
    exposed = r.headers["access-control-expose-headers"].lower()
    for h in ("etag", "retry-after", "idempotent-replay", "x-request-id", "location"):
        assert h in exposed


# --- If-Match and body version ------------------------------------------------------------------------------------

MODES = "/v1/_test/modes"


def _patch(client, body=None, **headers):
    return client.patch("/v1/_test/versioned", json=body or {}, headers=headers)


def test_both_missing_is_428(client):
    r = _patch(client)
    assert r.status_code == 428 and r.json()["code"] == "precondition_required"


@pytest.mark.parametrize("value", ["3", '"abc"', '"0"', '"-1"', '"3", "4"', "*", 'W/"3"', '""'])
def test_if_match_unparseable_is_412(client, value):
    r = _patch(client, **{"If-Match": value})
    assert r.status_code == 412 and r.json()["code"] == "precondition_failed"


def test_header_only_ok(client):
    assert _patch(client, **{"If-Match": '"12"'}).json() == {"v": 12}


def test_body_only_ok(client):
    assert _patch(client, {"version": 5}).json() == {"v": 5}


def test_header_and_body_agree_ok(client):
    assert _patch(client, {"version": 5}, **{"If-Match": '"5"'}).json() == {"v": 5}


def test_header_and_body_disagree_is_412(client):
    r = _patch(client, {"version": 4}, **{"If-Match": '"5"'})
    assert r.status_code == 412 and r.json()["code"] == "precondition_failed"


@pytest.mark.parametrize("v", [0, -3])
def test_body_version_below_one_is_412(client, v):
    assert _patch(client, {"version": v}).status_code == 412


def test_version_conflict_carries_current(client):
    r = client.patch("/v1/_test/conflict")
    assert r.status_code == 409
    assert r.json()["code"] == "version_conflict" and r.json()["current"] == {
        "id": "x",
        "version": 7,
    }
    assert isinstance(version_conflict({}), ApiError)


# --- more idempotency rules ----------------------------------------------------------------------------------------


def test_body_over_1_mib_is_413(client, make_user):
    _, sub = make_user()
    r = client.post(REQUIRED, content=b"x" * (1024 * 1024 + 1), headers=_h(client, sub))
    assert r.status_code == 413 and r.json()["code"] == "payload_too_large"


def test_4xx_is_stored_and_replayed(client, make_user):
    _, sub = make_user()
    a = client.post(MODES, json={"mode": "409"}, headers=_h(client, sub))
    b = client.post(MODES, json={"mode": "409"}, headers=_h(client, sub))
    assert a.status_code == b.status_code == 409 and b.headers["Idempotent-Replay"] == "true"
    assert b.json()["code"] == "state_conflict" and b.headers["content-type"].startswith(
        "application/problem+json"
    )


def test_429_releases_the_key(client, make_user, system_conn):
    uid, sub = make_user()
    assert client.post(MODES, json={"mode": "429"}, headers=_h(client, sub)).status_code == 429
    assert system_conn.execute(
        "SELECT count(*) FROM idempotency_keys WHERE user_id = %s", (uid,)
    ).fetchone() == (0,)


def test_non_json_2xx_releases_the_key(client, make_user, system_conn):
    uid, sub = make_user()
    assert client.post(MODES, json={"mode": "text"}, headers=_h(client, sub)).text == "plain"
    assert system_conn.execute(
        "SELECT count(*) FROM idempotency_keys WHERE user_id = %s", (uid,)
    ).fetchone() == (0,)


def test_etag_and_location_are_replayed(client, make_user):
    _, sub = make_user()
    client.post(MODES, json={"mode": "headers"}, headers=_h(client, sub))
    b = client.post(MODES, json={"mode": "headers"}, headers=_h(client, sub))
    assert b.headers["Idempotent-Replay"] == "true"
    assert (
        b.headers["ETag"] == '"1"'
        and b.headers["Location"] == "/v1/things/1"
        and "x-other" not in b.headers
    )


def test_stale_in_progress_claim_is_taken_over(client, make_user, system_conn):
    uid, sub = make_user()
    system_conn.execute(
        "INSERT INTO idempotency_keys (user_id, key, method, path, request_hash, created_at) "
        "VALUES (%s, %s, 'POST', %s, %s, now() - interval '6 minutes')",
        (uid, KEY, REQUIRED, request_hash(b'{"a":1}')),
    )
    r = client.post(REQUIRED, json={"a": 1}, headers=_h(client, sub))
    assert r.status_code == 201 and "idempotent-replay" not in r.headers


def test_cors_allows_the_write_methods(client):
    r = client.options(
        "/v1/_test/versioned",
        headers={"Origin": "https://hermi.example", "Access-Control-Request-Method": "PATCH"},
    )
    assert r.status_code == 200 and "PATCH" in r.headers["access-control-allow-methods"]
