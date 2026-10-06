# ruff: noqa: E501  (long SQL strings)
"""WF-040.1: revision 0023_legacy_claims, POST /v1/me/legacy-claim and the bootstrap 409 for a pending legacy email."""

import hashlib
import uuid

import psycopg
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.test_auth_provisioning import _auth, _settings

from hermi import db
from hermi.main import create_app
from hermi.modules.auth import legacy_claim


@pytest.fixture
def client(db_urls):
    s = _settings(db_urls)
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


@pytest.fixture
def legacy(system_conn):
    """A pre-created legacy owner: an active users row and a person, no auth_identities row."""

    def make():
        email = f"{uuid.uuid4().hex[:10]}@example.com"
        uid = system_conn.execute(
            "INSERT INTO users (email, display_name, status, email_verified_at) VALUES (%s, 'Legacy', 'active', now()) RETURNING id",
            (email,),
        ).fetchone()[0]
        system_conn.execute(
            "INSERT INTO people (owner_user_id, linked_user_id, name, is_self) VALUES (%s, %s, 'Legacy', true)",
            (uid, uid),
        )
        system_conn.execute("INSERT INTO entitlements (user_id) VALUES (%s)", (uid,))
        return uid, email

    return make


@pytest.fixture
def mint(db_urls):
    """create_claim on the system login, like the importer; returns the raw token."""
    eng = create_engine(db.sqlalchemy_url(db_urls["system"]))

    def make(uid):
        with Session(eng) as s:
            token = legacy_claim.create_claim(s, uid)
            s.commit()
        return token

    yield make
    eng.dispose()


def _claim(client, token, sub=None, **kw):
    return client.post(
        "/v1/me/legacy-claim", json={"token": token}, headers=_auth(client, sub, **kw)
    )


def test_redeem_attaches_the_identity_and_makes_no_second_user(client, system_conn, legacy, mint):
    uid, email = legacy()
    token = mint(uid)
    sub = uuid.uuid4().hex
    r = _claim(client, token, sub, email=email)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == str(uid) and r.json()["email"] == email
    assert system_conn.execute(
        "SELECT user_id FROM auth_identities WHERE subject = %s", (sub,)
    ).fetchone() == (uid,)
    assert system_conn.execute(
        "SELECT count(*) FROM users WHERE email = %s", (email,)
    ).fetchone() == (1,)
    h = _auth(client, sub, email=email)  # the signed-in identity now finds the same account
    assert client.get("/v1/me", headers=h).json()["id"] == str(uid)
    assert (
        client.post("/v1/me/bootstrap", json={"age_confirmed": True}, headers=h).status_code == 200
    )


def test_the_token_works_once(client, legacy, mint):
    uid, email = legacy()
    token = mint(uid)
    assert _claim(client, token, email=email).status_code == 200
    r = _claim(client, token, email=email)  # another sign-in, same token
    assert r.status_code == 410 and r.json()["code"] == "claim_link_expired"


def test_a_retry_by_the_same_identity_is_not_an_error(client, legacy, mint):
    uid, email = legacy()
    token = mint(uid)
    sub = uuid.uuid4().hex
    assert _claim(client, token, sub, email=email).status_code == 200
    assert _claim(client, token, sub, email=email).json()["id"] == str(uid)


def test_expired_and_unknown_tokens_are_410(client, system_conn, legacy, mint):
    uid, email = legacy()
    token = mint(uid)
    system_conn.execute(
        "UPDATE legacy_claims SET expires_at = now() - interval '1 second' WHERE user_id = %s",
        (uid,),
    )
    for t in (token, "x" * 43):
        r = _claim(client, t, email=email)
        assert r.status_code == 410 and r.json()["code"] == "claim_link_expired", t
    assert system_conn.execute(
        "SELECT count(*) FROM auth_identities WHERE user_id = %s", (uid,)
    ).fetchone() == (0,)


def test_the_claim_needs_a_jwt_and_a_body(client):
    assert client.post("/v1/me/legacy-claim", json={"token": "x" * 43}).status_code == 401
    assert client.post("/v1/me/legacy-claim", json={}, headers=_auth(client)).status_code == 422


def test_an_identity_with_an_account_cannot_claim(client, system_conn, legacy, mint):
    uid, _ = legacy()
    token = mint(uid)
    h = _auth(client)
    assert (
        client.post("/v1/me/bootstrap", json={"age_confirmed": True}, headers=h).status_code == 201
    )
    assert client.post("/v1/me/legacy-claim", json={"token": token}, headers=h).status_code == 409
    assert system_conn.execute(
        "SELECT used_at FROM legacy_claims WHERE user_id = %s", (uid,)
    ).fetchone() == (None,)


def test_bootstrap_for_a_pending_legacy_email_is_409_email_in_use(
    client, system_conn, legacy, mint
):
    uid, email = legacy()
    mint(uid)
    before = system_conn.execute("SELECT count(*) FROM users").fetchone()[0]
    r = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True}, headers=_auth(client, email=email)
    )
    assert (
        r.status_code == 409
        and r.json()["code"] == "email_in_use"
        and r.json()["legacy_claim_pending"] is True
    )
    assert system_conn.execute("SELECT count(*) FROM users").fetchone()[0] == before


def test_bootstrap_for_another_accounts_email_has_no_claim_hint(client):
    email = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True}, headers=_auth(client)
    ).json()["email"]
    r = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True}, headers=_auth(client, email=email)
    )
    assert (
        r.status_code == 409
        and r.json()["code"] == "email_in_use"
        and "legacy_claim_pending" not in r.json()
    )


def test_the_token_is_stored_only_as_a_sha256_hash(system_conn, legacy, mint):
    uid, _ = legacy()
    token = mint(uid)
    h, days, used = system_conn.execute(
        "SELECT token_hash, round(extract(epoch FROM expires_at - created_at) / 86400), used_at FROM legacy_claims WHERE user_id = %s",
        (uid,),
    ).fetchone()
    assert bytes(h) == hashlib.sha256(token.encode()).digest()
    assert len(token) >= 43 and used is None and days == 7


def test_the_app_role_cannot_touch_the_table(db_urls):
    with (
        psycopg.connect(db.psycopg_url(db_urls["app"]), autocommit=True) as c,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        c.execute("SELECT * FROM legacy_claims")


def test_round_trip_from_the_last_revision(db_urls):
    from tests.test_migrations import _alembic_cfg

    cfg = _alembic_cfg(db_urls["migrate"])
    command.downgrade(cfg, "0022_vote_tombstone")
    with psycopg.connect(db.psycopg_url(db_urls["system"]), autocommit=True) as c:
        assert c.execute("SELECT to_regclass('legacy_claims')").fetchone() == (None,)
    command.upgrade(cfg, "head")
    with psycopg.connect(db.psycopg_url(db_urls["system"]), autocommit=True) as c:
        assert c.execute("SELECT to_regclass('legacy_claims')").fetchone()[0] is not None


def test_live_columns_and_constraints_match_the_03_ddl(system_conn):
    from tests.test_migrations_trips_people import _ddl_tables, _ddl_text

    spec = _ddl_tables(_ddl_text())["legacy_claims"]
    cols = {r[0] for r in system_conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'legacy_claims'")}
    cons = {r[0] for r in system_conn.execute("SELECT conname FROM pg_constraint WHERE conrelid = 'legacy_claims'::regclass AND contype = 'u'")}
    assert cols == spec["columns"]
    assert cons == spec["constraints"]
