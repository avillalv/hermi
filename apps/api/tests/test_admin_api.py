# ruff: noqa: E501  (long lines)
"""WF-058.1: admin identity, token separation, the role by route matrix, admin-users routes and rate limits (08 sections 2, 3, 8, 9)."""

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.modules.admin.identity import AdminDirectory
from hermi.security import rate_limit
from hermi.security.jwt import mint_access_token, mint_dev_token

ASSERTION = "Cf-Access-Jwt-Assertion"
ROLES = ("owner", "engineer", "support", "finance", "content")


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def settings(db_urls):
    admin_url = os.environ.get("TEST_DATABASE_URL_ADMIN")  # hermi_admin_login; npm run test:api derives it
    if not admin_url:
        if os.environ.get("CI") and not os.environ.get("HERMI_TESTS_WITHOUT_DB"):
            pytest.fail("TEST_DATABASE_URL_ADMIN is not set")
        pytest.skip("TEST_DATABASE_URL_ADMIN is not set")
    return Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        admin_auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_url_admin=admin_url,
        field_encryption_key=base64.b64encode(bytes(range(32))).decode(),
        admin_session_secret="test-admin-session-secret",
    )


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(settings, clock):
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=False) as c:
        c.settings = settings
        app.state.admin_directory = AdminDirectory(lambda: app.state.admin_engine, clock=clock)
        yield c


@pytest.fixture
def admin_conn(settings):
    """Autocommit connection as the admin login: the one role (with hermi_admin) that reads and writes the 2FA tables
    (admin_credentials, admin_recovery_codes, admin_sessions, admin_auth_challenges). hermi_worker has no grant on them."""
    import psycopg

    from hermi import db

    with psycopg.connect(db.psycopg_url(settings.database_url_admin.get_secret_value()), autocommit=True) as c:
        yield c


@pytest.fixture
def make_admin(system_conn, make_user):
    def make(role="owner", disabled=False, enrolled=True):
        uid, subject = make_user()
        email = f"{subject[:10]}@example.com"
        system_conn.execute(
            "INSERT INTO admin_users (user_id, role, mfa_enrolled) VALUES (%s, %s, %s)", (uid, role, enrolled)
        )
        if disabled:
            system_conn.execute("UPDATE admin_users SET disabled_at = now() WHERE user_id = %s", (uid,))
        return uid, email

    return make


def hdr(settings, email, **extra):
    return {ASSERTION: mint_access_token(settings, email), **extra}


def session_cookie(settings, admin_conn, user_id, *, now=None, last_seen=None, stepup="now", method="webauthn"):
    """Arrange a 2FA session row (the cookie a sign-in would have set) and return the Cookie header value."""
    now = now or datetime.now(UTC)
    token = secrets.token_urlsafe(32)
    digest = hmac.new(settings.admin_session_secret.get_secret_value().encode(), token.encode(), hashlib.sha256).digest()
    admin_conn.execute(
        "INSERT INTO admin_sessions (user_id, token_hash, method, created_at, last_seen_at, expires_at, stepup_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (user_id, digest, method, now, last_seen or now, now + timedelta(hours=8), now if stepup == "now" else stepup),
    )
    return f"hermi_admin_session={token}"


@pytest.fixture
def auth(client, system_conn, admin_conn):
    """auth(email, **extra) -> the Access header plus, for an enrolled enabled admin, a fresh 2FA session cookie."""

    def make(email, **extra):
        h = hdr(client.settings, email, **extra)
        row = system_conn.execute(
            "SELECT a.user_id FROM users u JOIN admin_users a ON a.user_id = u.id WHERE u.email = %s AND a.mfa_enrolled", (email.lower(),)
        ).fetchone()
        if row:
            h["Cookie"] = session_cookie(client.settings, admin_conn, row[0])
        return h

    return make


def key():
    return {"Idempotency-Key": uuid.uuid4().hex}


def test_session_returns_the_admin_role_and_permissions(client, make_admin, auth):
    uid, email = make_admin("support", enrolled=False)
    r = client.get("/v1/admin/auth/session", headers=auth(email))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["admin"] == {"user_id": str(uid), "email": email, "role": "support", "mfa_enrolled": False}
    assert body["permissions"]["credits.grant"] == "W" and "killswitch.set" not in body["permissions"]
    assert body["two_factor"] == {"enrolled": False, "fresh": False}


def test_every_admin_response_is_noindex_even_errors(client, make_admin, auth):
    _, email = make_admin()
    ok = client.get("/v1/admin/auth/session", headers=auth(email))
    no_token = client.get("/v1/admin/auth/session")
    missing = client.get("/v1/admin/nothing-here", headers=auth(email))
    for r in (ok, no_token, missing):
        assert r.headers["x-robots-tag"] == "noindex"
    assert "x-robots-tag" not in client.get("/health/live").headers


def test_no_assertion_or_a_bad_one_is_401(client):
    assert client.get("/v1/admin/auth/session").status_code == 401
    r = client.get("/v1/admin/auth/session", headers={ASSERTION: "garbage"})
    assert r.status_code == 401 and r.json()["code"] == "unauthenticated"


def _denied_rows(system_conn, subject):
    return system_conn.execute(
        "SELECT actor_user_id, actor_type, result, error_code, entity_type, request_id, retention_class FROM audit_log "
        "WHERE action = 'admin_session.denied' AND entity_id = %s",
        (subject,),
    ).fetchall()


def test_identity_without_an_enabled_admin_row_is_403_and_audited(client, system_conn, make_user, make_admin, auth):
    ghost = "nobody-at-all@example.com"
    ghost_sub = str(uuid.uuid5(uuid.NAMESPACE_DNS, ghost))  # the dev signer subject for that email
    r = client.get("/v1/admin/auth/session", headers=auth(ghost))
    assert r.status_code == 403 and r.json()["code"] == "admin_not_enabled"
    rows = _denied_rows(system_conn, ghost_sub)
    assert len(rows) == 1
    assert rows[0][:5] == (None, "admin", "denied", "admin_not_enabled", "access_identity")
    assert rows[0][5] == r.json()["request_id"] and rows[0][6] == "extended"
    assert system_conn.execute("SELECT count(*) FROM audit_log WHERE entity_id = %s AND entity_id LIKE '%%@%%'", (ghost,)).fetchone()[0] == 0
    _, subject = make_user()  # a customer who is not an admin
    cust = f"{subject[:10]}@example.com"
    assert client.get("/v1/admin/auth/session", headers=auth(cust)).status_code == 403
    assert len(_denied_rows(system_conn, str(uuid.uuid5(uuid.NAMESPACE_DNS, cust)))) == 1
    _, off = make_admin("owner", disabled=True)
    assert client.get("/v1/admin/auth/session", headers=auth(off)).status_code == 403
    assert len(_denied_rows(system_conn, str(uuid.uuid5(uuid.NAMESPACE_DNS, off)))) == 1


def test_a_rejected_assertion_logs_a_warning_without_the_token(client, caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="hermi.admin"):
        client.get("/v1/admin/auth/session", headers={ASSERTION: "garbage.token.value"})
    rec = [r for r in caplog.records if r.getMessage() == "admin_assertion_rejected"]
    assert len(rec) == 1 and "garbage" not in str(rec[0].__dict__)


def test_email_match_ignores_case(client, make_admin, auth):
    _, email = make_admin()
    r = client.get("/v1/admin/auth/session", headers=auth(email.upper()))
    assert r.status_code == 200


def test_a_suspended_account_cannot_be_an_admin(client, system_conn, make_admin, auth):
    uid, email = make_admin()
    system_conn.execute("UPDATE users SET status = 'suspended', suspended_at = now() WHERE id = %s", (uid,))
    assert client.get("/v1/admin/auth/session", headers=auth(email)).status_code == 403


def test_a_disabled_admin_loses_access_within_60_seconds(client, clock, system_conn, make_admin, auth):
    uid, email = make_admin()
    h = auth(email)
    assert client.get("/v1/admin/auth/session", headers=h).status_code == 200
    system_conn.execute("UPDATE admin_users SET disabled_at = now() WHERE user_id = %s", (uid,))
    clock.t += 10
    assert client.get("/v1/admin/auth/session", headers=h).status_code == 200  # still inside the 30 second cache
    clock.t += 21
    r = client.get("/v1/admin/auth/session", headers=h)
    assert r.status_code == 403  # 31 seconds after the read, well inside 60


def test_the_lookup_is_cached_for_30_seconds(client, clock, system_conn, make_admin, auth):
    uid, email = make_admin("support")
    h = auth(email)
    assert client.get("/v1/admin/auth/session", headers=h).json()["admin"]["role"] == "support"
    system_conn.execute("UPDATE admin_users SET role = 'finance' WHERE user_id = %s", (uid,))
    assert client.get("/v1/admin/auth/session", headers=h).json()["admin"]["role"] == "support"
    clock.t += 31
    assert client.get("/v1/admin/auth/session", headers=h).json()["admin"]["role"] == "finance"


def test_customer_token_is_rejected_on_admin(client, make_user, make_admin):
    uid, subject = make_user()
    _, email = make_admin()
    s = client.settings
    bearer = {"Authorization": f"Bearer {mint_dev_token(s, subject, email=email)}"}
    assert client.get("/v1/admin/auth/session", headers=bearer).status_code == 401
    as_assertion = {ASSERTION: mint_dev_token(s, subject, email=email)}
    assert client.get("/v1/admin/auth/session", headers=as_assertion).status_code == 401


def test_admin_identity_is_rejected_on_customer_routes(client, make_admin):
    _, email = make_admin()
    assertion = mint_access_token(client.settings, email)
    assert client.get("/v1/me", headers={ASSERTION: assertion}).status_code == 401
    assert client.get("/v1/me", headers={"Authorization": f"Bearer {assertion}"}).status_code == 401


def test_admin_users_list_is_owner_only_and_names_the_missing_permission(client, make_admin, auth):
    for role in ROLES[1:]:
        _, email = make_admin(role)
        r = client.get("/v1/admin/admin-users", headers=auth(email))
        assert r.status_code == 403, role
        assert r.json()["permission"] == "admin_users.manage"
    _, owner = make_admin("owner")
    r = client.get("/v1/admin/admin-users", headers=auth(owner))
    assert r.status_code == 200
    assert any(a["email"] == owner and a["role"] == "owner" for a in r.json()["items"])


def test_non_owner_cannot_invite_or_patch(client, make_admin, make_user, auth):
    _, subject = make_user()
    target = f"{subject[:10]}@example.com"
    for role in ROLES[1:]:
        _, email = make_admin(role)
        h = auth(email, **key())
        r = client.post("/v1/admin/admin-users", headers=h, json={"email": target, "role": "support", "reason": "needs a seat"})
        assert r.status_code == 403
        r = client.patch(f"/v1/admin/admin-users/{uuid.uuid4()}", headers=h, json={"role": "support", "reason": "needs a seat"})
        assert r.status_code == 403


def _audit(system_conn, entity_id):
    return system_conn.execute(
        "SELECT id, actor_user_id, actor_type, actor_role, action, entity_type, before, after, reason, retention_class "
        "FROM audit_log WHERE entity_type = 'admin_user' AND entity_id = %s ORDER BY id",
        (str(entity_id),),
    ).fetchall()


def test_owner_invites_an_admin_with_a_role_and_one_audit_row(client, make_admin, make_user, system_conn, auth):
    owner_id, owner = make_admin("owner")
    uid, subject = make_user()
    r = client.post(
        "/v1/admin/admin-users",
        headers=auth(owner, **key()),
        json={"email": f"{subject[:10]}@example.com", "role": "finance", "reason": "bookkeeper starts Monday"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["result"]["user_id"] == str(uid) and body["result"]["role"] == "finance"
    rows = _audit(system_conn, uid)
    assert len(rows) == 1 and str(rows[0][0]) == body["audit_id"]
    _, actor, actor_type, actor_role, action, _, before, after, reason, retention = rows[0]
    assert (actor, actor_type, actor_role, action) == (owner_id, "admin", "owner", "admin_user.invite")
    assert before is None and after["role"] == "finance" and reason == "bookkeeper starts Monday" and retention == "extended"
    row = system_conn.execute("SELECT role, mfa_enrolled, created_by, disabled_at FROM admin_users WHERE user_id = %s", (uid,)).fetchone()
    assert row == ("finance", False, owner_id, None)


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"role": "finance", "reason": "bookkeeper starts Monday"}, 422, "validation_failed"),
        ({"email": "x@example.com", "role": "admin", "reason": "bookkeeper starts Monday"}, 422, "validation_failed"),
        ({"email": "x@example.com", "role": "finance", "reason": "short"}, 422, "validation_failed"),
        ({"email": "x@example.com", "role": "finance", "reason": "x" * 501}, 422, "validation_failed"),
        ({"email": "nobody-here@example.com", "role": "finance", "reason": "bookkeeper starts Monday"}, 422, "account_required"),
    ],
)
def test_invite_validation(client, make_admin, body, status, code, auth):
    _, owner = make_admin("owner")
    r = client.post("/v1/admin/admin-users", headers=auth(owner, **key()), json=body)
    assert r.status_code == status and r.json()["code"] == code


def test_invite_needs_an_idempotency_key_and_refuses_an_existing_admin(client, make_admin, auth):
    _, owner = make_admin("owner")
    _, other = make_admin("support")
    body = {"email": other, "role": "finance", "reason": "bookkeeper starts Monday"}
    r = client.post("/v1/admin/admin-users", headers=auth(owner), json=body)
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"
    r = client.post("/v1/admin/admin-users", headers=auth(owner, **key()), json=body)
    assert r.status_code == 409 and r.json()["code"] == "already_admin"


def test_patch_changes_role_then_disables_then_enables_each_with_an_audit_row(client, make_admin, system_conn, auth):
    _, owner = make_admin("owner")
    uid, _ = make_admin("support")
    url = f"/v1/admin/admin-users/{uid}"
    r = client.patch(url, headers=auth(owner, **key()), json={"role": "engineer", "reason": "promoted to engineer"})
    assert r.status_code == 200 and r.json()["result"]["role"] == "engineer"
    r = client.patch(url, headers=auth(owner, **key()), json={"disabled": True, "reason": "left the company"})
    assert r.status_code == 200 and r.json()["result"]["disabled_at"]
    r = client.patch(url, headers=auth(owner, **key()), json={"disabled": False, "reason": "back from leave"})
    assert r.status_code == 200 and r.json()["result"]["disabled_at"] is None
    actions = [row[4] for row in _audit(system_conn, uid)]
    assert actions == ["admin_user.role_change", "admin_user.disable", "admin_user.enable"]
    first = _audit(system_conn, uid)[0]
    assert first[6]["role"] == "support" and first[7]["role"] == "engineer"


def test_disabling_through_the_api_cuts_access_in_this_process_at_once(client, make_admin, auth):
    _, owner = make_admin("owner")
    uid, target = make_admin("support")
    assert client.get("/v1/admin/auth/session", headers=auth(target)).status_code == 200
    client.patch(f"/v1/admin/admin-users/{uid}", headers=auth(owner, **key()), json={"disabled": True, "reason": "left the company"})
    assert client.get("/v1/admin/auth/session", headers=auth(target)).status_code == 403


def test_last_enabled_owner_cannot_be_demoted_or_disabled(client, system_conn, make_admin, auth):
    a_id, a = make_admin("owner")
    b_id, _ = make_admin("owner")
    assert client.get("/v1/admin/auth/session", headers=auth(a)).status_code == 200  # A is now cached
    # Other tests leave owners behind: B must be the only enabled owner. A stays in this process cache.
    system_conn.execute("UPDATE admin_users SET disabled_at = now() WHERE user_id <> %s AND disabled_at IS NULL", (b_id,))
    for body in ({"role": "support"}, {"disabled": True}):
        r = client.patch(f"/v1/admin/admin-users/{b_id}", headers=auth(a, **key()), json={**body, "reason": "a long enough reason"})
        assert r.status_code == 409 and r.json()["code"] == "last_owner", body
    assert system_conn.execute("SELECT role, disabled_at FROM admin_users WHERE user_id = %s", (b_id,)).fetchone() == ("owner", None)


def test_patch_rules(client, make_admin, auth):
    owner_id, owner = make_admin("owner")
    uid, _ = make_admin("support")
    ok = {"reason": "a long enough reason"}
    r = client.patch(f"/v1/admin/admin-users/{owner_id}", headers=auth(owner, **key()), json={"disabled": True, **ok})
    assert r.status_code == 409 and r.json()["code"] == "cannot_modify_self"
    r = client.patch(f"/v1/admin/admin-users/{uuid.uuid4()}", headers=auth(owner, **key()), json={"disabled": True, **ok})
    assert r.status_code == 404
    for body in ({**ok}, {"role": "support", "disabled": True, **ok}, {"role": "root", **ok}):
        r = client.patch(f"/v1/admin/admin-users/{uid}", headers=auth(owner, **key()), json=body)
        assert r.status_code == 422, body


def test_rate_limits_are_per_admin_and_per_class(client, make_admin, auth):
    _, a = make_admin("owner")
    _, b = make_admin("owner")
    rate_limit.TEST_LIMITS["admin_read"] = 2
    for _ in range(2):
        assert client.get("/v1/admin/auth/session", headers=auth(a)).status_code == 200
    r = client.get("/v1/admin/auth/session", headers=auth(a))
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert client.get("/v1/admin/auth/session", headers=auth(b)).status_code == 200


def test_admin_write_limit(client, make_admin, auth):
    _, owner = make_admin("owner")
    rate_limit.TEST_LIMITS["admin_x"] = 1  # inviting is an X action (5 a minute)
    body = {"email": "nobody-here@example.com", "role": "finance", "reason": "bookkeeper starts Monday"}
    h = lambda: auth(owner, **key())  # noqa: E731
    assert client.post("/v1/admin/admin-users", headers=h(), json=body).status_code == 422
    assert client.post("/v1/admin/admin-users", headers=h(), json=body).status_code == 429


def test_dev_signer_route_mints_an_assertion_the_api_accepts(client, make_admin):
    _, email = make_admin("finance")
    r = client.post("/v1/dev/admin-session", json={"email": email})
    assert r.status_code == 200
    s = client.get("/v1/admin/auth/session", headers={ASSERTION: r.json()["assertion"]})
    assert s.status_code == 200 and s.json()["admin"]["role"] == "finance"


def test_dev_signer_route_is_absent_in_cf_access_mode(db_urls):
    s = Settings(
        _env_file=None, environment="ci", auth_mode="dev", admin_auth_mode="cf_access",
        cf_access_team_domain="hermi.cloudflareaccess.com", cf_access_aud="a" * 64,
        database_url=db_urls["app"], database_url_system=db_urls["system"],
    )
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        assert c.post("/v1/dev/admin-session", json={"email": "a@example.com"}).status_code == 404
