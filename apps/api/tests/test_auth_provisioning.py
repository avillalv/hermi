# ruff: noqa: E501  (long SQL strings and comments)
"""WF-013.2: POST /v1/me/bootstrap, GET /v1/me and the dev routes against a real PostgreSQL (04 sections 1.2 and 5.1)."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from tests.test_migrations_imports_affiliate import _applied, _flags, _pass_plan, _trip

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

BODY = {"age_confirmed": True}


def _settings(db_urls, **kw):
    base = dict(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
    )
    return Settings(**{**base, **kw})


@pytest.fixture
def client(db_urls):
    s = _settings(db_urls)
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _auth(client, sub=None, **kw):
    sub = sub or uuid.uuid4().hex
    kw.setdefault("email", f"{sub[:12]}@example.com")
    return {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, **kw)}


def test_bootstrap_is_201_for_a_new_user_and_200_for_an_existing_one(client, system_conn):
    h = _auth(client)
    r = client.post("/v1/me/bootstrap", json={**BODY, "display_name": "Sam"}, headers=h)
    assert r.status_code == 201
    me = r.json()
    assert me["status"] == "active" and me["tier"] == "free" and me["email_is_relay"] is False
    again = client.post("/v1/me/bootstrap", json=BODY, headers=h)
    assert again.status_code == 200 and again.json()["id"] == me["id"]
    assert again.json()["me_person_id"] == me["me_person_id"]
    n = system_conn.execute(
        "SELECT count(*) FROM people WHERE owner_user_id = %s AND is_self", (me["id"],)
    ).fetchone()[0]
    assert n == 1
    code = system_conn.execute(
        "SELECT count(*) FROM referral_codes WHERE user_id = %s", (me["id"],)
    ).fetchone()[0]
    assert code == 1


def test_bootstrap_stores_the_profile_on_creation(client):
    body = {
        **BODY,
        "locale": "pt-PT",
        "timezone": "Europe/Lisbon",
        "home_currency": "EUR",
        "home_airports": ["LIS"],
    }
    me = client.post("/v1/me/bootstrap", json=body, headers=_auth(client)).json()
    assert (me["locale"], me["timezone"], me["home_currency"], me["home_airports"]) == (
        "pt-PT",
        "Europe/Lisbon",
        "EUR",
        ["LIS"],
    )


def test_bootstrap_needs_a_confirmed_age_and_a_valid_body(client):
    h = _auth(client)
    assert client.post("/v1/me/bootstrap", json={}, headers=h).status_code == 422
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": False}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
    assert r.json()["errors"][0]["field"] == "age_confirmed"
    bad = client.post("/v1/me/bootstrap", json={**BODY, "home_currency": "euro"}, headers=h)
    assert bad.status_code == 422
    assert client.post("/v1/me/bootstrap", json=BODY).status_code == 401


def test_a_second_account_with_the_same_email_gets_409_email_in_use(client):
    email = f"{uuid.uuid4().hex[:10]}@example.com"
    first = client.post("/v1/me/bootstrap", json=BODY, headers=_auth(client, email=email))
    assert first.status_code == 201
    r = client.post("/v1/me/bootstrap", json=BODY, headers=_auth(client, email=email.upper()))
    assert r.status_code == 409 and r.json()["code"] == "email_in_use"
    assert r.headers["content-type"].startswith("application/problem+json")


def test_apple_hide_my_email_relay_address_is_accepted_and_flagged(client, system_conn):
    h = _auth(client, provider="apple", email=f"{uuid.uuid4().hex[:10]}@privaterelay.appleid.com")
    r = client.post("/v1/me/bootstrap", json=BODY, headers=h)
    assert r.status_code == 201 and r.json()["email_is_relay"] is True
    flags = system_conn.execute(
        "SELECT email_is_relay FROM auth_identities WHERE user_id = %s", (r.json()["id"],)
    ).fetchone()
    assert flags == (True,)


def test_bootstrap_without_an_email_is_refused(client):
    token = mint_dev_token(client.settings, uuid.uuid4().hex)
    r = client.post("/v1/me/bootstrap", json=BODY, headers={"Authorization": "Bearer " + token})
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
    assert r.json()["errors"][0]["field"] == "email"


def test_concurrent_first_login_creates_exactly_one_user(client, system_conn):
    h = _auth(client)
    email = jwt.decode(h["Authorization"].split()[1], options={"verify_signature": False})["email"]

    def call(_):
        return client.post("/v1/me/bootstrap", json=BODY, headers=h).status_code

    with ThreadPoolExecutor(8) as pool:
        codes = list(pool.map(call, range(8)))
    assert codes.count(201) == 1 and set(codes) <= {200, 201}
    n = system_conn.execute("SELECT count(*) FROM users WHERE email = %s", (email,)).fetchone()[0]
    assert n == 1


def test_a_recreated_account_gets_no_second_taster(client, system_conn):
    def grants(uid):
        system_conn.execute("SELECT ensure_taster_grant(%s)", (uid,))
        return system_conn.execute(
            "SELECT count(*) FROM credit_grants WHERE user_id = %s AND period_key = 'taster'",
            (uid,),
        ).fetchone()[0]

    def sign_up(upstream):
        h = _auth(client, provider="apple", provider_subject=upstream)
        return client.post("/v1/me/bootstrap", json=BODY, headers=h).json()

    upstream = "000" + uuid.uuid4().hex[:12]
    first = sign_up(upstream)
    assert grants(first["id"]) == 1
    system_conn.execute("DELETE FROM users WHERE id = %s", (first["id"],))
    again = sign_up(upstream)
    assert again["id"] != first["id"] and grants(again["id"]) == 0
    other = sign_up("999" + uuid.uuid4().hex[:12])
    assert grants(other["id"]) == 1  # a different person still gets theirs


def test_a_recreated_email_account_gets_no_second_taster(client, system_conn):
    email = f"{uuid.uuid4().hex[:10]}@example.com"

    def grants(uid):
        system_conn.execute("SELECT ensure_taster_grant(%s)", (uid,))
        return system_conn.execute(
            "SELECT count(*) FROM credit_grants WHERE user_id = %s AND period_key = 'taster'",
            (uid,),
        ).fetchone()[0]

    first = client.post("/v1/me/bootstrap", json=BODY, headers=_auth(client, email=email)).json()
    assert grants(first["id"]) == 1
    system_conn.execute("DELETE FROM users WHERE id = %s", (first["id"],))
    again = client.post("/v1/me/bootstrap", json=BODY, headers=_auth(client, email=email)).json()
    assert again["id"] != first["id"] and grants(again["id"]) == 0


def test_a_recreated_account_gets_no_second_first_import_pass(client, system_conn):
    _pass_plan(system_conn)
    _flags(system_conn)
    email = f"{uuid.uuid4().hex[:10]}@example.com"
    upstream = "000" + uuid.uuid4().hex[:12]

    def sign_up():
        h = _auth(client, provider="apple", email=email, provider_subject=upstream)
        return client.post("/v1/me/bootstrap", json=BODY, headers=h).json()["id"]

    def reward(uid):
        imp = _applied(system_conn, uid, _trip(system_conn, uid))
        return system_conn.execute("SELECT grant_import_reward(%s)", (imp,)).fetchone()[0]

    first = sign_up()
    assert reward(first) is not None
    system_conn.execute("DELETE FROM trips WHERE owner_user_id = %s", (first,))  # trips restrict user deletes
    system_conn.execute("DELETE FROM users WHERE id = %s", (first,))
    again = sign_up()
    assert again != first and reward(again) is None


def test_get_me_needs_a_users_row_and_works_in_the_grace_period(client, system_conn):
    h = _auth(client)
    r = client.get("/v1/me", headers=h)
    assert r.status_code == 401 and r.json()["code"] == "unauthenticated"
    uid = client.post("/v1/me/bootstrap", json=BODY, headers=h).json()["id"]
    ok = client.get("/v1/me", headers=h)
    assert ok.status_code == 200 and ok.json()["id"] == uid
    assert {"server_time", "min_client_version", "flags", "consents"} <= ok.json().keys()
    system_conn.execute("UPDATE users SET status = 'pending_deletion' WHERE id = %s", (uid,))
    pending = client.get("/v1/me", headers=h)
    assert pending.status_code == 200, pending.text
    assert pending.json()["status"] == "pending_deletion"
    assert client.post("/v1/me/bootstrap", json=BODY, headers=h).status_code == 200


def test_bootstrap_for_a_suspended_account_is_403(client, system_conn):
    h = _auth(client)
    uid = client.post("/v1/me/bootstrap", json=BODY, headers=h).json()["id"]
    system_conn.execute(
        "UPDATE users SET status = 'suspended', suspended_at = now() WHERE id = %s", (uid,)
    )
    r = client.post("/v1/me/bootstrap", json=BODY, headers=h)
    assert r.status_code == 403 and r.json()["code"] == "account_inactive"


# --- dev routes -----------------------------------------------------------------------------------------------------


def test_dev_personas_lists_free_plus_and_admin(client):
    r = client.get("/v1/dev/personas")
    assert r.status_code == 200
    assert [p["persona"] for p in r.json()] == ["free", "plus", "admin"]


@pytest.mark.parametrize("persona,tier", [("free", "free"), ("plus", "plus"), ("admin", "free")])
def test_dev_session_returns_a_token_that_signs_the_persona_in(client, system_conn, persona, tier):
    r = client.post("/v1/dev/session", json={"persona": persona})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    me = client.get("/v1/me", headers={"Authorization": "Bearer " + r.json()["access_token"]})
    assert me.status_code == 200 and me.json()["tier"] == tier
    admins = system_conn.execute(
        "SELECT count(*) FROM admin_users WHERE user_id = %s", (me.json()["id"],)
    ).fetchone()[0]
    assert admins == (1 if persona == "admin" else 0)


def test_the_first_dev_session_creates_all_three_personas_once(client, system_conn):
    system_conn.execute("DELETE FROM users WHERE email LIKE '%@hermi.test'")
    assert client.post("/v1/dev/session", json={"persona": "free"}).status_code == 200
    client.post("/v1/dev/session", json={"persona": "free"})
    n = system_conn.execute(
        "SELECT count(*) FROM users WHERE email LIKE '%@hermi.test'"
    ).fetchone()[0]
    assert n == 3


def test_an_unknown_persona_is_422(client):
    assert client.post("/v1/dev/session", json={"persona": "root"}).status_code == 422


@pytest.mark.parametrize(
    "kw",
    [
        {"auth_mode": "supabase"},
        {"auth_mode": "dev", "environment": "production"},
        {"auth_mode": "supabase", "environment": "production"},
    ],
)
def test_dev_routes_are_not_mounted_or_documented_outside_dev_mode(db_urls, kw):
    app = create_app(_settings(db_urls, **kw))
    assert not [p for p in app.openapi()["paths"] if "/dev/" in p]
    with TestClient(app) as c:
        assert c.get("/v1/dev/personas").status_code == 404
        assert c.post("/v1/dev/session", json={"persona": "free"}).status_code == 404


def test_bootstrap_is_the_only_route_that_takes_a_token_without_a_users_row(client):
    h = _auth(client)  # a valid token, no users row
    # The waitlist, the invite preview and the shared trip and the sample trips are public: they take no token at all.
    allowed = {"/v1/me/bootstrap", "/v1/me/legacy-claim", "/v1/dev/personas", "/v1/dev/session", "/v1/waitlist", "/v1/unsubscribe", "/v1/invites/{token}", "/v1/shared/{token}", "/v1/public/sample-trips", "/v1/public/sample-trips/{slug}"}
    checked = 0
    for path, ops in client.app.openapi()["paths"].items():
        if not path.startswith("/v1/") or path in allowed:
            continue
        for method in ops:
            url = path.replace("{", "").replace("}", "")  # path params take any text here
            r = client.request(method.upper(), url, headers=h)
            assert r.status_code == 401 and r.json()["code"] == "unauthenticated", (method, path)
            checked += 1
    assert checked >= 1
    assert client.post("/v1/me/bootstrap", json=BODY, headers=h).status_code == 201


def test_nothing_references_the_old_passcode_path():
    root = Path(__file__).resolve().parents[3]
    hits = []
    for base in (root / "apps/api/hermi", root / "apps/web/src", root / "scripts"):
        for p in base.rglob("*") if base.exists() else []:
            if p.suffix in {".py", ".ts", ".tsx", ".js", ".mjs", ".json"}:
                if "passcode" in p.read_text(errors="ignore").lower():
                    hits.append(str(p.relative_to(root)))
    assert hits == [], hits


@pytest.fixture
def sink():
    from hermi import analytics

    s = analytics.MemorySink()
    analytics.set_sink(s)
    yield s
    analytics.set_sink(analytics.MemorySink())


def test_signup_completed_fires_once_on_first_sign_in_only(client, sink):
    h = _auth(client)
    first = client.post("/v1/me/bootstrap", json=BODY, headers=h)
    assert first.status_code == 201
    assert client.post("/v1/me/bootstrap", json=BODY, headers=h).status_code == 200
    events = [e for e in sink.events if e["event"] == "signup_completed"]
    assert len(events) == 1
    e = events[0]
    assert e["distinct_id"] == first.json()["id"]
    assert e["properties"]["method"] == "email_code"
    assert (e["properties"]["from_invite"], e["properties"]["from_referral"], e["properties"]["was_guest"]) == (False, False, False)
    assert "@" not in json.dumps(e)


def test_signup_completed_is_dropped_under_global_privacy_control(client, sink):
    r = client.post("/v1/me/bootstrap", json=BODY, headers={**_auth(client), "Sec-GPC": "1"})
    assert r.status_code == 201
    assert not sink.events
