# ruff: noqa: E501  (long SQL strings and comments)
"""WF-013.1: CurrentUser, DbSession and the problem+json handler against a real PostgreSQL (04 sections 1.2 and 1.4)."""

import uuid

import psycopg
import pytest
from alembic import command
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import text
from tests.test_migrations import _alembic_cfg

from hermi import db
from hermi.config import Settings
from hermi.deps import CurrentUser, CurrentUserOrPendingDeletion, DbSession
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

SIGS = "SELECT oid::regprocedure::text FROM pg_proc WHERE proname = 'bootstrap_user'"


class Body(BaseModel):
    n: int


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        cors_allowed_origins="https://hermi.example",
        database_pool_size=1,  # one pooled connection: a leaked app.user_id would show on the next request
        database_max_overflow=0,
    )
    app = create_app(s)
    r = APIRouter(prefix="/v1/_test")

    @r.get("/me")
    def me(user: CurrentUser, session: DbSession):
        seen = session.execute(text("SELECT app_user_id()")).scalar()
        return {"id": str(user.id), "db_user": str(seen)}

    @r.get("/pending")
    def pending(user: CurrentUserOrPendingDeletion):
        return {"status": user.status}

    @r.post("/body")
    def body(b: Body):
        return b

    @r.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    app.include_router(r)
    with TestClient(app, raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _auth(client, sub, **kw):
    return {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, **kw)}


def test_active_user_gets_a_transaction_with_app_user_id(client, make_user):
    uid, sub = make_user()
    r = client.get("/v1/_test/me", headers=_auth(client, sub))
    assert r.status_code == 200 and r.json() == {"id": str(uid), "db_user": str(uid)}
    assert r.headers["X-Request-Id"]


def test_app_user_id_does_not_leak_to_the_next_request_on_the_same_connection(client, make_user):
    (a, sa), (b, sb) = make_user(), make_user()
    for uid, sub in [(a, sa), (b, sb), (a, sa)]:
        assert client.get("/v1/_test/me", headers=_auth(client, sub)).json()["db_user"] == str(uid)
    with (
        client.app.state.engine.connect() as c
    ):  # the only pooled connection, after the request ended
        assert (
            c.execute(text("SELECT coalesce(current_setting('app.user_id', true), '')")).scalar()
            == ""
        )


@pytest.mark.parametrize("status", ["suspended", "deleted"])
def test_suspended_and_deleted_accounts_get_account_inactive(client, make_user, status):
    _, sub = make_user(status)
    r = client.get("/v1/_test/me", headers=_auth(client, sub))
    assert r.status_code == 403 and r.json()["code"] == "account_inactive"
    assert r.headers["content-type"].startswith("application/problem+json")


def test_pending_deletion_is_403_except_where_allowed(client, make_user):
    _, sub = make_user("pending_deletion")
    r = client.get("/v1/_test/me", headers=_auth(client, sub))
    assert r.status_code == 403 and r.json()["code"] == "account_pending_deletion"
    ok = client.get("/v1/_test/pending", headers=_auth(client, sub))
    assert ok.status_code == 200 and ok.json() == {"status": "pending_deletion"}


def test_missing_bad_expired_and_unknown_identity_are_401(client, make_user):
    assert client.get("/v1/_test/me").json()["code"] == "unauthenticated"
    assert client.get("/v1/_test/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/v1/_test/me", headers={"Authorization": "Basic abc"}).status_code == 401
    _, sub = make_user()
    r = client.get("/v1/_test/me", headers=_auth(client, sub, ttl_seconds=-120))
    assert r.status_code == 401 and r.json()["code"] == "token_expired"
    assert r.headers["WWW-Authenticate"] == "Bearer"
    r = client.get("/v1/_test/me", headers=_auth(client, "no-such-subject"))
    assert r.status_code == 401 and r.json()["code"] == "unauthenticated"


def test_the_provider_in_the_token_picks_the_identity(client, make_user):
    _, sub = make_user(provider="apple")
    assert (
        client.get("/v1/_test/me", headers=_auth(client, sub, provider="apple")).status_code == 200
    )
    assert (
        client.get("/v1/_test/me", headers=_auth(client, sub, provider="google")).status_code == 401
    )


def test_problem_json_shape_for_validation_unknown_route_and_request_id(client):
    rid = str(uuid.uuid4())
    r = client.post("/v1/_test/body", json={"n": "x"}, headers={"X-Request-Id": rid})
    p = r.json()
    assert r.status_code == 422 and p["code"] == "validation_failed" and p["request_id"] == rid
    assert p["errors"][0]["field"] == "n" and p["instance"] == "/v1/_test/body"
    assert p["type"].endswith("/validation_failed") and p["status"] == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    nf = client.get("/v1/nothing-here")
    assert nf.status_code == 404 and nf.json()["code"] == "not_found"
    assert client.get("/v1/_test/body").json()["code"] == "method_not_allowed"


def test_unhandled_error_is_internal_error_without_a_stack(client):
    r = client.get("/v1/_test/boom")
    assert r.status_code == 500 and r.json()["code"] == "internal_error"
    assert "secret detail" not in r.text
    assert r.headers["X-Request-Id"] == r.json()["request_id"]


def test_request_id_header_is_on_a_cors_preflight(client):
    rid = str(uuid.uuid4())
    r = client.options(
        "/v1/_test/body",
        headers={
            "Origin": "https://hermi.example",
            "Access-Control-Request-Method": "POST",
            "X-Request-Id": rid,
        },
    )
    assert r.status_code == 200 and r.headers["X-Request-Id"] == rid
    assert r.headers["access-control-allow-origin"] == "https://hermi.example"


def test_app_engine_refuses_an_unsafe_login(db_urls):
    s = Settings(_env_file=None, environment="ci", database_url=db_urls["system"])  # BYPASSRLS
    with pytest.raises(db.MigrationError):
        db.open_app_engine(s)
    ok = Settings(_env_file=None, environment="ci", database_url=db_urls["app"])
    db.open_app_engine(ok).dispose()


# --- 0016_bootstrap_subject ----------------------------------------------------------------------------


def test_bootstrap_user_with_six_parameters_writes_provider_subject(db_urls, system_conn):
    sub, upstream = uuid.uuid4().hex, "apple-" + uuid.uuid4().hex
    args = (sub, f"{sub[:8]}@example.com", upstream)
    with psycopg.connect(db.psycopg_url(db_urls["app"]), autocommit=True) as app:
        q = "SELECT * FROM bootstrap_user('apple', %s, %s, true, 'Zoe', %s)"
        first = app.execute(q, args).fetchone()
        again = app.execute(q, args).fetchone()
    assert first[1] is True and again == (first[0], False)
    row = system_conn.execute(
        "SELECT provider_subject FROM auth_identities WHERE provider = 'apple' AND subject = %s",
        (sub,),
    ).fetchone()
    assert row == (upstream,)


def test_bootstrap_user_five_parameters_still_works_and_fills_a_missing_provider_subject(
    db_urls, system_conn
):
    sub = uuid.uuid4().hex
    email = f"{sub[:8]}@example.com"
    sel = "SELECT provider_subject FROM auth_identities WHERE subject = %s"
    with psycopg.connect(db.psycopg_url(db_urls["app"]), autocommit=True) as app:
        app.execute("SELECT * FROM bootstrap_user('google', %s, %s, false, 'Yan')", (sub, email))
        assert system_conn.execute(sel, (sub,)).fetchone() == (None,)
        app.execute(
            "SELECT * FROM bootstrap_user('google', %s, %s, false, 'Yan', 'g-123')", (sub, email)
        )
    assert system_conn.execute(sel, (sub,)).fetchone() == ("g-123",)


def test_bootstrap_user_signature_and_grants(system_conn):
    sigs = [r[0] for r in system_conn.execute(SIGS)]
    assert sigs == [
        "bootstrap_user(text,text,citext,boolean,text,text)"
    ]  # the five parameter signature is gone
    sig = sigs[0]
    q = "SELECT has_function_privilege(%s, %s::regprocedure, 'EXECUTE')"
    assert system_conn.execute(q, ("hermi_api_login", sig)).fetchone() == (True,)
    assert system_conn.execute(q, ("hermi_worker_login", sig)).fetchone() == (False,)
    assert system_conn.execute(q, ("public", sig)).fetchone() == (False,)
    owner = system_conn.execute(
        "SELECT proowner::regrole::text, prosecdef FROM pg_proc WHERE oid = %s::regprocedure",
        (sig,),
    ).fetchone()
    assert owner == ("hermi_definer", True)


RESOLVE_SIG = "resolve_identity(text,text)"
HAS_RESOLVE = "SELECT to_regprocedure('resolve_identity(text,text)') IS NOT NULL"


def test_resolve_identity_grants_and_lookup(db_urls, system_conn, make_user):
    q = "SELECT has_function_privilege(%s, %s::regprocedure, 'EXECUTE')"
    assert system_conn.execute(q, ("hermi_api_login", RESOLVE_SIG)).fetchone() == (True,)
    assert system_conn.execute(q, ("hermi_worker_login", RESOLVE_SIG)).fetchone() == (False,)
    assert system_conn.execute(q, ("public", RESOLVE_SIG)).fetchone() == (False,)
    uid, sub = make_user()
    with psycopg.connect(db.psycopg_url(db_urls["app"]), autocommit=True) as app:
        found = app.execute("SELECT * FROM resolve_identity('email', %s)", (sub,)).fetchall()
        none = app.execute("SELECT * FROM resolve_identity('email', 'nobody')").fetchall()
    assert found == [(uid, "active")] and none == []


def test_0016_round_trip(db_urls, system_conn):
    cfg = _alembic_cfg(db_urls["migrate"])
    command.downgrade(cfg, "0015_seed")
    assert [r[0] for r in system_conn.execute(SIGS)] == [
        "bootstrap_user(text,text,citext,boolean,text)"
    ]
    assert system_conn.execute(HAS_RESOLVE).fetchone() == (False,)  # downgrade drops it
    command.upgrade(cfg, "head")
    assert [r[0] for r in system_conn.execute(SIGS)] == [
        "bootstrap_user(text,text,citext,boolean,text,text)"
    ]
    assert system_conn.execute(HAS_RESOLVE).fetchone() == (True,)
