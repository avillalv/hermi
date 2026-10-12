# ruff: noqa: E501, F811  (long lines; fixtures imported from test_admin_api are redefined as test arguments)
"""WF-058.2: admin 2FA. Passkey and TOTP enrolment, recovery codes, the 8 hour and 30 minute session, step-up 428 and its lockout
(08 sections 2.2, 2.3, 8 and 9). The software authenticator in tests/webauthn_authenticator.py drives the real verifier."""

import base64
import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from tests.test_admin_api import (  # noqa: F401
    ASSERTION,
    DEFAULT_KEY,
    admin_conn,
    auth,
    client,
    clock,
    hdr,
    key,
    make_admin,
    session_cookie,
    settings,
)
from tests.webauthn_authenticator import Authenticator

from hermi.main import create_app
from hermi.modules.admin.identity import AdminDirectory
from hermi.security import fieldcrypt, rate_limit, totp, webauthn
from hermi.security.jwt import mint_dev_token

B = "/v1/admin/auth"


class Wall:
    """The wall clock behind admin sessions, challenges and TOTP; tests move it."""

    def __init__(self):
        self.t = datetime.now(UTC)

    def __call__(self):
        return self.t

    def advance(self, **kw):
        self.t += timedelta(**kw)


@pytest.fixture
def wall(client):
    w = Wall()
    client.app.state.admin_clock = w
    return w


def _enrol_passkey(client, h, authn):
    o = client.post(f"{B}/webauthn/register/options", headers=h)
    assert o.status_code == 200, o.text
    ch = webauthn.b64u_decode(o.json()["public_key"]["challenge"])
    r = client.post(
        f"{B}/webauthn/register/verify", headers=h, json={"challenge_id": o.json()["challenge_id"], **authn.register(ch)}
    )
    assert r.status_code == 200, r.text
    return r


def _codes(client, h):
    r = client.post(f"{B}/recovery-codes", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _enrolled_admin(client, make_admin, role="owner"):
    """A fully enrolled admin (passkey plus recovery codes) made through the API with Access only. -> (uid, email, authn, codes, h)"""
    uid, email = make_admin(role, enrolled=False)
    h = hdr(client.settings, email)
    authn = Authenticator()
    _enrol_passkey(client, h, authn)
    codes = _codes(client, h)
    assert codes["mfa_enrolled"] is True
    return uid, email, authn, codes["codes"], h


def _signin_passkey(client, h, authn, purpose="signin", path="signin", use_challenge=None, **assert_kw):
    o = client.post(f"{B}/webauthn/options", headers=h, json={"purpose": purpose})
    assert o.status_code == 200, o.text
    ch = webauthn.b64u_decode(o.json()["public_key"]["challenge"])
    return client.post(
        f"{B}/{path}",
        headers=h,
        json={"method": "webauthn", "challenge_id": o.json()["challenge_id"], "assertion": authn.assert_(use_challenge or ch, **assert_kw)},
    )


def _cookie(r):
    return r.headers["set-cookie"].split(";", 1)[0]


# --- enrolment ---------------------------------------------------------------------------------------------


def test_an_unenrolled_admin_enrols_with_access_only_and_codes_complete_it(client, make_admin, system_conn, admin_conn):
    uid, email = make_admin("support", enrolled=False)
    h = hdr(client.settings, email)
    authn = Authenticator()
    r = _enrol_passkey(client, h, authn)
    assert r.json() == {"mfa_enrolled": False}  # a passkey alone is half of it
    codes = _codes(client, h)
    assert codes["mfa_enrolled"] is True and len(codes["codes"]) == 10 and len(set(codes["codes"])) == 10
    assert all(len(c) == 14 and c[4] == "-" and c[9] == "-" for c in codes["codes"])
    assert system_conn.execute("SELECT mfa_enrolled FROM admin_users WHERE user_id = %s", (uid,)).fetchone() == (True,)
    rows = admin_conn.execute("SELECT salt, code_hash, used_at FROM admin_recovery_codes WHERE user_id = %s", (uid,)).fetchall()
    assert len(rows) == 10 and all(r[2] is None and len(r[1]) == 32 for r in rows)
    flat = b"".join(bytes(x) for r in rows for x in r[:2])
    assert not any(c.replace("-", "").encode() in flat for c in codes["codes"])  # never stored as given
    cred = admin_conn.execute("SELECT kind, credential_id, public_key, sign_count FROM admin_credentials WHERE user_id = %s", (uid,)).fetchone()
    assert cred[0] == "webauthn" and bytes(cred[1]) == authn.credential_id
    s = client.get(f"{B}/session", headers=h).json()
    assert s["two_factor"] == {"enrolled": True, "fresh": False} and s["signed_in"] is False
    assert s["factors"] == {"passkeys": 1, "totp": False, "recovery_codes_left": 10}


def test_totp_enrolment_needs_a_valid_first_code_and_a_code_works_once(client, wall, make_admin, system_conn, admin_conn):
    uid, email = make_admin("engineer", enrolled=False)
    h = hdr(client.settings, email)
    b = client.post(f"{B}/totp/enrol", headers=h)
    assert b.status_code == 200 and b.json()["otpauth_uri"].startswith("otpauth://totp/Hermi%20admin:")
    secret = base64.b32decode(b.json()["secret"] + "=" * (-len(b.json()["secret"]) % 8))
    assert admin_conn.execute("SELECT secret_enc FROM admin_credentials WHERE user_id = %s", (uid,)).fetchone()[0] != secret  # sealed
    step = int(wall.t.timestamp() // 30)
    bad = client.post(f"{B}/totp/confirm", headers=h, json={"code": totp.code_for(secret, step + 5)})
    assert bad.status_code == 422 and bad.json()["code"] == "registration_failed"
    ok = client.post(f"{B}/totp/confirm", headers=h, json={"code": totp.code_for(secret, step)})
    assert ok.status_code == 200 and ok.json() == {"mfa_enrolled": False}  # no recovery codes yet
    assert _codes(client, h)["mfa_enrolled"] is True
    # Sign in with TOTP: the confirming code is spent (replay), the next step's code works (+1 window).
    replay = client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": totp.code_for(secret, step)})
    assert replay.status_code == 401 and replay.json()["code"] == "two_factor_failed"
    nxt = client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": totp.code_for(secret, step + 1)})
    assert nxt.status_code == 200 and nxt.json()["signed_in"] is True
    again = client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": totp.code_for(secret, step + 1)})
    assert again.status_code == 401
    older = client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": totp.code_for(secret, step - 1)})
    assert older.status_code == 401  # an earlier counter than the last used one is a replay too


def test_totp_window_is_one_step_either_side(client, wall, make_admin):
    uid, email = make_admin("engineer", enrolled=False)
    h = hdr(client.settings, email)
    b = client.post(f"{B}/totp/enrol", headers=h).json()["secret"]
    secret = base64.b32decode(b + "=" * (-len(b) % 8))
    step = int(wall.t.timestamp() // 30)
    assert client.post(f"{B}/totp/confirm", headers=h, json={"code": totp.code_for(secret, step - 2)}).status_code == 422
    assert client.post(f"{B}/totp/confirm", headers=h, json={"code": totp.code_for(secret, step + 2)}).status_code == 422
    assert client.post(f"{B}/totp/confirm", headers=h, json={"code": totp.code_for(secret, step - 1)}).status_code == 200


def test_bad_registrations_are_refused(client, make_admin):
    _, email = make_admin("support", enrolled=False)
    h = hdr(client.settings, email)
    bad = {
        "wrong origin": dict(origin="https://evil.example"),
        "wrong rp": dict(rp_id="evil.example"),
        "wrong type": dict(typ="webauthn.get"),
        "not verified": dict(flags=0x41),
        "not present": dict(flags=0x44),
        "no attested data": dict(flags=0x05),
        "bad packed signature": dict(fmt="packed", bad_sig=True),
    }
    for name, kw in bad.items():
        o = client.post(f"{B}/webauthn/register/options", headers=h).json()
        ch = webauthn.b64u_decode(o["public_key"]["challenge"])
        data = Authenticator().register(ch, **kw)
        r = client.post(f"{B}/webauthn/register/verify", headers=h, json={"challenge_id": o["challenge_id"], **data})
        assert r.status_code == 422 and r.json()["code"] == "registration_failed", name
    # A wrong challenge, and a challenge used twice.
    o = client.post(f"{B}/webauthn/register/options", headers=h).json()
    data = Authenticator().register(b"\x00" * 32)
    assert client.post(f"{B}/webauthn/register/verify", headers=h, json={"challenge_id": o["challenge_id"], **data}).status_code == 422
    data = Authenticator().register(webauthn.b64u_decode(o["public_key"]["challenge"]))
    assert client.post(f"{B}/webauthn/register/verify", headers=h, json={"challenge_id": o["challenge_id"], **data}).status_code == 422  # consumed


def test_packed_self_attestation_and_rs256_are_accepted(client, make_admin):
    _, email = make_admin("support", enrolled=False)
    h = hdr(client.settings, email)
    for alg, fmt in (("ES256", "packed"), ("RS256", "none"), ("RS256", "packed")):
        a = Authenticator(alg=alg)
        o = client.post(f"{B}/webauthn/register/options", headers=h).json()
        data = a.register(webauthn.b64u_decode(o["public_key"]["challenge"]), fmt=fmt)
        r = client.post(f"{B}/webauthn/register/verify", headers=h, json={"challenge_id": o["challenge_id"], **data})
        assert r.status_code == 200, (alg, fmt, r.text)
    assert client.get(f"{B}/session", headers=h).json()["factors"]["passkeys"] == 3


def test_the_same_passkey_cannot_be_registered_twice(client, make_admin):
    _, email = make_admin("support", enrolled=False)
    h = hdr(client.settings, email)
    a = Authenticator()
    _enrol_passkey(client, h, a)
    o = client.post(f"{B}/webauthn/register/options", headers=h).json()
    assert [c["id"] for c in o["public_key"]["excludeCredentials"]] == [webauthn.b64u(a.credential_id)]
    data = a.register(webauthn.b64u_decode(o["public_key"]["challenge"]))
    assert client.post(f"{B}/webauthn/register/verify", headers=h, json={"challenge_id": o["challenge_id"], **data}).status_code == 422


# --- sign-in -----------------------------------------------------------------------------------------------


def test_routes_need_enrolment_then_a_session(client, make_admin):
    _, bare = make_admin("owner", enrolled=False)
    r = client.get("/v1/admin/admin-users", headers=hdr(client.settings, bare))
    assert r.status_code == 403 and r.json()["code"] == "mfa_enrollment_required"
    _, email, authn, _, h = _enrolled_admin(client, make_admin)
    r = client.get("/v1/admin/admin-users", headers=h)  # Access alone, no completed 2FA
    assert r.status_code == 401 and r.json()["code"] == "two_factor_required"
    r = _signin_passkey(client, h, authn)
    assert r.status_code == 200, r.text
    assert r.json()["signed_in"] is True and r.json()["two_factor"] == {"enrolled": True, "fresh": True}
    cookie = _cookie(r)
    assert client.get("/v1/admin/admin-users", headers={**h, "Cookie": cookie}).status_code == 200


def test_the_cookie_is_httponly_secure_strict_host_only_and_8_hours(client, make_admin):
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    r = _signin_passkey(client, h, authn)
    attrs = [a.strip().lower() for a in r.headers["set-cookie"].split(";")]
    assert attrs[0].startswith("hermi_admin_session=")
    assert {"httponly", "secure", "samesite=strict", "path=/v1/admin", "max-age=28800"} <= set(attrs)
    assert not any(a.startswith("domain=") for a in attrs)  # host-only: scoped to the admin host
    token = attrs[0].split("=", 1)[1]
    assert len(token) >= 40


def test_signin_failures_are_one_generic_401(client, make_admin, system_conn):
    uid, _, authn, _, h = _enrolled_admin(client, make_admin)
    other = Authenticator()
    cases = {
        "unknown passkey": lambda: _signin_passkey(client, h, other),
        "wrong origin": lambda: _signin_passkey(client, h, authn, origin="https://evil.example"),
        "wrong rp": lambda: _signin_passkey(client, h, authn, rp_id="evil.example"),
        "no user verification": lambda: _signin_passkey(client, h, authn, flags=0x01),
        "wrong type": lambda: _signin_passkey(client, h, authn, typ="webauthn.create"),
        "counter went back": lambda: _signin_passkey(client, h, authn, count=0),
    }
    # One good sign-in first so the stored counter is above zero and "counter went back" has something to beat.
    assert _signin_passkey(client, h, authn).status_code == 200
    for name, call in cases.items():
        r = call()
        assert r.status_code == 401 and r.json()["code"] == "two_factor_failed", name
    r = client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": "123456"})
    assert r.status_code == 401
    r = client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": "AAAA-AAAA-AAAA"})
    assert r.status_code == 401
    denied = system_conn.execute(
        "SELECT count(*) FROM audit_log WHERE action = 'admin_session.signin' AND result = 'denied' AND entity_id = %s", (str(uid),)
    ).fetchone()[0]
    assert denied >= 8


def test_a_passkey_challenge_is_single_use_short_lived_and_purpose_bound(client, wall, make_admin, system_conn, admin_conn):
    uid, _, authn, _, h = _enrolled_admin(client, make_admin)
    o = client.post(f"{B}/webauthn/options", headers=h, json={"purpose": "signin"}).json()
    ch = webauthn.b64u_decode(o["public_key"]["challenge"])
    a = authn.assert_(ch)
    body = {"method": "webauthn", "challenge_id": o["challenge_id"], "assertion": a}
    assert client.post(f"{B}/signin", headers=h, json=body).status_code == 200
    assert client.post(f"{B}/signin", headers=h, json=body).status_code == 401  # replayed: the challenge is gone
    # Expired.
    o = client.post(f"{B}/webauthn/options", headers=h, json={"purpose": "signin"}).json()
    ch = webauthn.b64u_decode(o["public_key"]["challenge"])
    wall.advance(minutes=6)
    r = client.post(f"{B}/signin", headers=h, json={"method": "webauthn", "challenge_id": o["challenge_id"], "assertion": authn.assert_(ch)})
    assert r.status_code == 401
    # A registration challenge is no sign-in challenge.
    fresh = {**h, "Cookie": session_cookie(client.settings, admin_conn, uid, now=wall.t)}  # enrolled admins need a session to add factors
    reg = client.post(f"{B}/webauthn/register/options", headers=fresh)
    assert reg.status_code == 200, reg.text
    rch = webauthn.b64u_decode(reg.json()["public_key"]["challenge"])
    r = client.post(f"{B}/signin", headers=h, json={"method": "webauthn", "challenge_id": reg.json()["challenge_id"], "assertion": authn.assert_(rch)})
    assert r.status_code == 401 and r.json()["code"] == "two_factor_failed"
    # Another admin's challenge id does not open this admin's sign-in.
    _, _, authn2, _, h2 = _enrolled_admin(client, make_admin)
    o2 = client.post(f"{B}/webauthn/options", headers=h2, json={"purpose": "signin"}).json()
    ch2 = webauthn.b64u_decode(o2["public_key"]["challenge"])
    r = client.post(f"{B}/signin", headers=h, json={"method": "webauthn", "challenge_id": o2["challenge_id"], "assertion": authn.assert_(ch2)})
    assert r.status_code == 401


@pytest.mark.parametrize("purpose", ["signin", "stepup"])
def test_assertion_signature_challenge_and_purpose_are_enforced(purpose, client, wall, make_admin, system_conn, admin_conn):
    """The verifier must check the signature itself: each bad assertion is the one generic 401, a good one still works."""
    rate_limit.TEST_LIMITS["admin_signin"] = rate_limit.TEST_LIMITS["admin_stepup"] = 1000
    _, authn, h = _stale_owner(client, wall, make_admin, admin_conn)  # a cookie lets /webauthn/options and /stepup work too
    other = "stepup" if purpose == "signin" else "signin"

    def bad(**kw):
        r = _signin_passkey(client, h, authn, purpose=kw.pop("options_purpose", purpose), path=purpose, **kw)
        assert r.status_code == 401 and r.json()["code"] == "two_factor_failed", (kw, r.text)

    bad(bad_sig=True)  # one flipped signature byte
    bad(sign_challenge=b"\x01" * 32)  # right challenge id and client data, signed over a different challenge
    bad(options_purpose=other)  # the other purpose's challenge sent to this route
    bad(use_challenge=b"\x00" * 32)  # a valid signature over client data whose challenge is not the issued one
    assert _signin_passkey(client, h, authn, purpose=purpose, path=purpose).status_code == 200


def test_a_recovery_session_is_not_a_step_up_but_can_re_enrol(client, wall, make_admin):
    rate_limit.TEST_LIMITS["admin_signin"] = 1000
    _, _, _, codes, h = _enrolled_admin(client, make_admin)
    r = client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": codes[0]})
    assert r.status_code == 200 and r.json()["two_factor"] == {"enrolled": True, "fresh": False} and r.json()["fresh_until"] is None
    h = {**h, "Cookie": _cookie(r)}
    r = client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE)
    assert r.status_code == 428 and r.json()["code"] == "stepup_required"
    _enrol_passkey(client, h, Authenticator())  # break-glass: a lost passkey can be replaced from this session
    assert client.post(f"{B}/totp/enrol", headers=h).status_code == 200
    wall.advance(minutes=6)  # the break-glass window is the first 5 minutes of the session
    assert client.post(f"{B}/webauthn/register/options", headers=h).status_code == 428


def test_a_recovery_code_signs_in_once_and_is_logged_as_break_glass(client, make_admin, system_conn, caplog):
    rate_limit.TEST_LIMITS["admin_signin"] = 1000
    uid, _, _, codes, h = _enrolled_admin(client, make_admin)
    with caplog.at_level(logging.WARNING, logger="hermi.admin"):
        r = client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": codes[0].lower()})  # case and dashes are forgiven
    assert r.status_code == 200 and r.json()["signed_in"] is True
    rec = [x for x in caplog.records if x.getMessage() == "admin_break_glass"]
    assert len(rec) == 1 and rec[0].codes_left == 9 and codes[0] not in str(rec[0].__dict__)
    assert system_conn.execute("SELECT count(*) FROM audit_log WHERE action = 'admin_session.break_glass' AND entity_id = %s", (str(uid),)).fetchone()[0] == 1
    assert client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": codes[0]}).status_code == 401  # single use
    assert client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": codes[1].replace("-", "")}).status_code == 200
    assert client.get(f"{B}/session", headers=h).json()["factors"]["recovery_codes_left"] == 8
    # Using them up never reopens enrolment to a bare Access identity.
    for c in codes[2:]:
        assert client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": c}).status_code == 200
    assert system_conn.execute("SELECT mfa_enrolled FROM admin_users WHERE user_id = %s", (uid,)).fetchone() == (True,)
    assert client.post(f"{B}/totp/enrol", headers=h).status_code == 401  # enrolled: a live session is needed to add a factor


def test_signin_is_locked_after_10_attempts_an_hour(client, make_admin, caplog):
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    for i in range(10):
        assert client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": "000000"}).status_code == 401, i
    with caplog.at_level(logging.WARNING, logger="hermi.admin"):
        r = _signin_passkey(client, h, authn)  # the right factor is refused during the lockout
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert [x for x in caplog.records if x.getMessage() == "admin_2fa_lockout"]


def test_failed_logins_from_one_ip_are_limited_and_alert(client, make_admin, system_conn, auth, caplog):
    system_conn.execute("DELETE FROM rate_limit_counters WHERE bucket LIKE 'admin_auth_fail_ip:%'")
    rate_limit.TEST_LIMITS["admin_auth_fail_ip"] = 3
    _, email = make_admin("owner")
    for _ in range(2):
        assert client.get(f"{B}/session", headers={ASSERTION: "garbage"}).status_code == 401
    assert client.get(f"{B}/session", headers=hdr(client.settings, "nobody-here@example.com")).status_code == 403  # the 3rd
    with caplog.at_level(logging.WARNING, logger="hermi.admin"):
        r = client.get(f"{B}/session", headers={ASSERTION: "garbage"})
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert [x for x in caplog.records if x.getMessage() == "admin_login_lockout"]
    assert client.get(f"{B}/session", headers=auth(email)).status_code == 200  # only failures are counted


def test_failed_2fa_proofs_count_against_the_ip_limit(client, make_admin, system_conn, caplog):
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    system_conn.execute("DELETE FROM rate_limit_counters WHERE bucket LIKE 'admin_auth_fail_ip:%'")
    rate_limit.TEST_LIMITS["admin_auth_fail_ip"] = 3
    for _ in range(3):  # wrong TOTP codes at sign-in
        assert client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": "000000"}).status_code == 401
    with caplog.at_level(logging.WARNING, logger="hermi.admin"):
        r = client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": "000000"})
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert [x for x in caplog.records if x.getMessage() == "admin_login_lockout"]


def test_signin_ip_lockout_logs_the_alert(client, make_admin, caplog):
    rate_limit.TEST_LIMITS["admin_signin_ip"] = 1
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": "000000"})
    with caplog.at_level(logging.WARNING, logger="hermi.admin"):
        r = client.post(f"{B}/signin", headers=h, json={"method": "totp", "code": "000000"})
    assert r.status_code == 429
    assert [x for x in caplog.records if x.getMessage() == "admin_2fa_lockout" and x.rate_class == "admin_signin_ip"]


def test_one_admins_recovery_code_does_not_open_another(client, make_admin):
    _, _, _, codes_a, _ = _enrolled_admin(client, make_admin)
    _, _, _, _, h_b = _enrolled_admin(client, make_admin)
    assert client.post(f"{B}/signin", headers=h_b, json={"method": "recovery", "code": codes_a[0]}).status_code == 401


def test_new_recovery_codes_replace_the_old_set(client, make_admin):
    _, _, authn, codes, h = _enrolled_admin(client, make_admin)
    s = _signin_passkey(client, h, authn)
    h = {**h, "Cookie": _cookie(s)}
    new = client.post(f"{B}/recovery-codes", headers=h)
    assert new.status_code == 200
    assert client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": codes[0]}).status_code == 401
    assert client.post(f"{B}/signin", headers=h, json={"method": "recovery", "code": new.json()["codes"][0]}).status_code == 200


# --- the session clocks ------------------------------------------------------------------------------------


def test_session_is_8_hours_absolute(client, wall, make_admin):
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    h = {**h, "Cookie": _cookie(_signin_passkey(client, h, authn))}
    for _ in range(15):  # busy: a request every 30 minutes keeps the idle clock fresh up to 7.5 hours
        wall.advance(minutes=29)
        assert client.get("/v1/admin/admin-users", headers=h).status_code == 200
    wall.advance(minutes=29)  # 7 h 45 m... still inside
    assert client.get("/v1/admin/admin-users", headers=h).status_code == 200
    wall.advance(minutes=29)  # 8 h 14 m: past the absolute limit although it was never idle
    r = client.get("/v1/admin/admin-users", headers=h)
    assert r.status_code == 401 and r.json()["code"] == "two_factor_required"
    assert client.get(f"{B}/session", headers=h).json()["signed_in"] is False


def test_session_is_30_minutes_idle(client, wall, make_admin):
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    h = {**h, "Cookie": _cookie(_signin_passkey(client, h, authn))}
    wall.advance(minutes=29)
    assert client.get("/v1/admin/admin-users", headers=h).status_code == 200  # slides the idle clock
    wall.advance(minutes=29)
    assert client.get("/v1/admin/admin-users", headers=h).status_code == 200
    wall.advance(minutes=31)
    assert client.get("/v1/admin/admin-users", headers=h).status_code == 401


def test_reading_the_session_does_not_keep_it_alive(client, wall, make_admin):
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    h = {**h, "Cookie": _cookie(_signin_passkey(client, h, authn))}
    wall.advance(minutes=20)
    assert client.get(f"{B}/session", headers=h).json()["signed_in"] is True
    wall.advance(minutes=20)  # 40 minutes since the last real activity
    assert client.get(f"{B}/session", headers=h).json()["signed_in"] is False


def test_signout_ends_the_session(client, make_admin):
    _, _, authn, _, h = _enrolled_admin(client, make_admin)
    h = {**h, "Cookie": _cookie(_signin_passkey(client, h, authn))}
    r = client.post(f"{B}/signout", headers=h)
    assert r.status_code == 204 and "hermi_admin_session=" in r.headers["set-cookie"]
    assert client.get("/v1/admin/admin-users", headers=h).status_code == 401


def test_a_disabled_admin_loses_a_live_session_within_60_seconds(client, clock, make_admin, system_conn, auth):
    uid, email = make_admin("owner")
    h = auth(email)
    assert client.get("/v1/admin/admin-users", headers=h).status_code == 200
    system_conn.execute("UPDATE admin_users SET disabled_at = now() WHERE user_id = %s", (uid,))
    clock.t += 31
    r = client.get("/v1/admin/admin-users", headers=h)
    assert r.status_code == 403 and r.json()["code"] == "admin_not_enabled"


def test_disabling_through_the_api_deletes_the_sessions(client, make_admin, system_conn, auth, admin_conn):
    _, owner = make_admin("owner")
    uid, target = make_admin("support")
    auth(target)
    auth(target)
    assert admin_conn.execute("SELECT count(*) FROM admin_sessions WHERE user_id = %s", (uid,)).fetchone()[0] == 2
    r = client.patch(f"/v1/admin/admin-users/{uid}", headers=auth(owner, **key()), json={"disabled": True, "reason": "left the company"})
    assert r.status_code == 200, r.text
    assert admin_conn.execute("SELECT count(*) FROM admin_sessions WHERE user_id = %s", (uid,)).fetchone()[0] == 0


# --- separation --------------------------------------------------------------------------------------------


def test_the_admin_session_opens_nothing_else_and_belongs_to_one_admin(client, make_admin, system_conn, admin_conn):
    uid, email = make_admin("owner")
    cookie = session_cookie(client.settings, admin_conn, uid)
    assert client.get("/v1/admin/admin-users", headers=hdr(client.settings, email, Cookie=cookie)).status_code == 200
    # Customer routes: neither the cookie nor the Access assertion is a customer credential.
    r = client.get("/v1/me", headers=hdr(client.settings, email, Cookie=cookie))
    assert r.status_code == 401
    r = client.get("/v1/me", headers={"Cookie": cookie})
    assert r.status_code == 401
    # The cookie is bound to its admin: another admin's Access identity with it is no session.
    _, other = make_admin("owner")
    r = client.get("/v1/admin/admin-users", headers=hdr(client.settings, other, Cookie=cookie))
    assert r.status_code == 401 and r.json()["code"] == "two_factor_required"
    # A made-up cookie, and a customer bearer in its place.
    r = client.get("/v1/admin/admin-users", headers=hdr(client.settings, email, Cookie="hermi_admin_session=nope"))
    assert r.status_code == 401 and r.json()["code"] == "two_factor_required"
    bearer = {"Authorization": f"Bearer {mint_dev_token(client.settings, str(uuid.uuid4()), email=email)}"}
    r = client.get("/v1/admin/admin-users", headers=hdr(client.settings, email, **bearer))
    assert r.status_code == 401 and r.json()["code"] == "two_factor_required"


def test_cookie_is_stored_hashed(client, make_admin, system_conn, admin_conn):
    uid, email = make_admin("owner")
    cookie = session_cookie(client.settings, admin_conn, uid)
    token = cookie.split("=", 1)[1]
    stored = admin_conn.execute("SELECT token_hash FROM admin_sessions WHERE user_id = %s", (uid,)).fetchone()[0]
    assert token.encode() not in bytes(stored) and len(bytes(stored)) == 32


# --- step-up -----------------------------------------------------------------------------------------------


def _stale_owner(client, wall, make_admin, admin_conn):
    """An enrolled owner with a live session whose last 2FA check is 10 minutes old."""
    uid, email, authn, codes, h = _enrolled_admin(client, make_admin)
    cookie = session_cookie(client.settings, admin_conn, uid, now=wall.t, stepup=wall.t - timedelta(minutes=10))
    return uid, authn, {**h, "Cookie": cookie}


INVITE = {"email": "nobody-here@example.com", "role": "finance", "reason": "bookkeeper starts Monday"}


def test_x_action_is_428_until_a_step_up_and_stale_again_after_5_minutes(client, wall, make_admin, system_conn, admin_conn):
    uid, authn, h = _stale_owner(client, wall, make_admin, admin_conn)
    assert client.get("/v1/admin/admin-users", headers=h).status_code == 200  # a read is not an X action
    s = client.get(f"{B}/session", headers=h).json()
    assert s["signed_in"] is True and s["two_factor"] == {"enrolled": True, "fresh": False}
    r = client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE)
    assert r.status_code == 428 and r.json()["code"] == "stepup_required", r.text
    r = _signin_passkey(client, h, authn, purpose="stepup", path="stepup")
    assert r.status_code == 200, r.text
    assert r.json()["two_factor"]["fresh"] is True and r.json()["fresh_until"]
    r = client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE)
    assert r.status_code == 422 and r.json()["code"] == "account_required"  # got past the step-up to the route's own checks
    wall.advance(minutes=4, seconds=50)
    r = client.get(f"{B}/session", headers=h).json()
    assert r["two_factor"]["fresh"] is True
    wall.advance(seconds=20)  # 5 m 10 s after the check
    assert client.get(f"{B}/session", headers=h).json()["two_factor"]["fresh"] is False
    r = client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE)
    assert r.status_code == 428


def test_step_up_with_totp_and_the_recovery_code_is_not_a_step_up_factor(client, wall, make_admin, system_conn, admin_conn):
    uid, email = make_admin("owner", enrolled=False)
    h = hdr(client.settings, email)
    b = client.post(f"{B}/totp/enrol", headers=h).json()["secret"]
    secret = base64.b32decode(b + "=" * (-len(b) % 8))
    step = int(wall.t.timestamp() // 30)
    assert client.post(f"{B}/totp/confirm", headers=h, json={"code": totp.code_for(secret, step - 1)}).status_code == 200
    codes = _codes(client, h)["codes"]
    h = {**h, "Cookie": session_cookie(client.settings, admin_conn, uid, now=wall.t, stepup=wall.t - timedelta(minutes=10))}
    assert client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE).status_code == 428
    assert client.post(f"{B}/stepup", headers=h, json={"method": "recovery", "code": codes[0]}).status_code == 401
    r = client.post(f"{B}/stepup", headers=h, json={"method": "totp", "code": totp.code_for(secret, step)})
    assert r.status_code == 200 and r.json()["two_factor"]["fresh"] is True
    assert client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE).status_code == 422


def test_step_up_needs_a_session_and_fails_with_a_wrong_factor(client, wall, make_admin, system_conn, admin_conn):
    uid, authn, h = _stale_owner(client, wall, make_admin, admin_conn)
    no_cookie = {k: v for k, v in h.items() if k != "Cookie"}
    assert client.post(f"{B}/stepup", headers=no_cookie, json={"method": "totp", "code": "123456"}).status_code == 401
    r = client.post(f"{B}/stepup", headers=h, json={"method": "totp", "code": "123456"})
    assert r.status_code == 401 and r.json()["code"] == "two_factor_failed"
    assert client.get(f"{B}/session", headers=h).json()["two_factor"]["fresh"] is False


def test_step_up_lockout_after_10_attempts_an_hour_with_an_alert(client, wall, make_admin, system_conn, caplog, admin_conn):
    uid, authn, h = _stale_owner(client, wall, make_admin, admin_conn)
    for i in range(10):
        r = client.post(f"{B}/stepup", headers=h, json={"method": "totp", "code": "000000"})
        assert r.status_code == 401, i
    with caplog.at_level(logging.WARNING, logger="hermi.admin"):
        r = _signin_passkey(client, h, authn, purpose="stepup", path="stepup")  # even the right factor is refused now
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert [x for x in caplog.records if x.getMessage() == "admin_2fa_lockout"]
    assert client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE).status_code == 428


def test_x_writes_use_the_5_a_minute_class_and_w_writes_do_not(client, wall, make_admin, system_conn, auth):
    _, owner = make_admin("owner")
    rate_limit.TEST_LIMITS["admin_x"] = 1
    h = auth(owner, **key())
    assert client.post("/v1/admin/admin-users", headers=h, json=INVITE).status_code == 422
    assert client.post("/v1/admin/admin-users", headers={**h, **key()}, json=INVITE).status_code == 429


def test_adding_a_factor_when_enrolled_needs_a_live_fresh_session(client, wall, make_admin, system_conn, admin_conn):
    uid, authn, h = _stale_owner(client, wall, make_admin, admin_conn)
    access_only = {k: v for k, v in h.items() if k != "Cookie"}
    assert client.post(f"{B}/totp/enrol", headers=access_only).status_code == 401
    assert client.post(f"{B}/recovery-codes", headers=access_only).status_code == 401
    assert client.post(f"{B}/webauthn/register/options", headers=access_only).status_code == 401
    assert client.post(f"{B}/totp/enrol", headers=h).status_code == 428
    assert _signin_passkey(client, h, authn, purpose="stepup", path="stepup").status_code == 200
    assert client.post(f"{B}/totp/enrol", headers=h).status_code == 200
    assert client.post(f"{B}/webauthn/register/options", headers=h).status_code == 200


# --- unit: TOTP, WebAuthn parser, field encryption, migration ----------------------------------------------


def test_totp_rfc6238_vectors():
    secret = b"12345678901234567890"
    for t, want in ((59, "287082"), (1111111109, "081804"), (1234567890, "005924"), (2000000000, "279037")):
        assert totp.code_for(secret, t // 30) == want
        assert totp.match(secret, want, t) == t // 30
    assert totp.match(secret, "287082", 59 + 60) is None  # two steps away
    assert totp.match(secret, "28708", 59) is None and totp.match(secret, "abcdef", 59) is None


def test_cbor_rejects_indefinite_trailing_and_deep_input():
    from tests.webauthn_authenticator import cbor

    assert webauthn.cbor_decode(cbor({1: [b"x", "y", -5, True]}))[0] == {1: [b"x", "y", -5, True]}
    for bad in (b"\x5f\x41a\xff", b"\xa1", b"\x82\x01", b"\x1c", b""):
        with pytest.raises(webauthn.WebAuthnError):
            webauthn.cbor_decode(bad)
    with pytest.raises(webauthn.WebAuthnError):
        webauthn.cbor_decode(b"\x81" * 20 + b"\x00")


def test_registration_refuses_full_attestation_and_unknown_formats():
    a = Authenticator()
    ch = b"c" * 32
    reg = a.register(ch)
    obj, _ = webauthn.cbor_decode(webauthn.b64u_decode(reg["attestation_object"]))
    from tests.webauthn_authenticator import cbor

    for fmt, stmt in (("packed", {"alg": -7, "sig": b"x", "x5c": [b"cert"]}), ("tpm", {}), ("fido-u2f", {}), ("none", {"alg": -7})):
        att = cbor({"fmt": fmt, "attStmt": stmt, "authData": obj["authData"]})
        with pytest.raises(webauthn.WebAuthnError):
            webauthn.verify_registration(
                client_data_json=webauthn.b64u_decode(reg["client_data_json"]),
                attestation_object=att,
                challenge=ch,
                origin="http://localhost:5173",
                rp_id="localhost",
            )


def test_field_encryption_round_trip_binding_and_missing_key(settings):
    blob = fieldcrypt.seal(settings, b"secret", b"owner-1")
    assert b"secret" not in blob and fieldcrypt.unseal(settings, blob, b"owner-1") == b"secret"
    with pytest.raises(fieldcrypt.FieldCryptError):
        fieldcrypt.unseal(settings, blob, b"owner-2")
    with pytest.raises(fieldcrypt.FieldCryptError):
        fieldcrypt.unseal(settings, blob[:-1] + bytes([blob[-1] ^ 1]), b"owner-1")
    assert fieldcrypt.seal(settings, b"secret", b"owner-1") != blob  # a fresh nonce each time
    bare = settings.model_copy(update={"field_encryption_key": None})
    from hermi.config import NotConfigured

    with pytest.raises(NotConfigured):
        fieldcrypt.seal(bare, b"x", b"y")


def test_totp_enrolment_degrades_to_503_without_the_encryption_key(settings, db_urls, make_admin):
    s = settings.model_copy(update={"field_encryption_key": None})
    app = create_app(s)
    with TestClient(app, raise_server_exceptions=False, headers=DEFAULT_KEY) as c:
        app.state.admin_directory = AdminDirectory(lambda: app.state.admin_engine)
        _, email = make_admin("support", enrolled=False)
        r = c.post(f"{B}/totp/enrol", headers=hdr(s, email))
        assert r.status_code == 503 and r.json()["code"] == "admin_unavailable"


def test_the_secret_in_the_database_is_not_plain_and_is_bound_to_the_admin(client, make_admin, system_conn, settings, admin_conn):
    uid, email = make_admin("support", enrolled=False)
    h = hdr(client.settings, email)
    b = client.post(f"{B}/totp/enrol", headers=h).json()["secret"]
    secret = base64.b32decode(b + "=" * (-len(b) % 8))
    sealed = bytes(admin_conn.execute("SELECT secret_enc FROM admin_credentials WHERE user_id = %s", (uid,)).fetchone()[0])
    assert secret not in sealed
    assert fieldcrypt.unseal(settings, sealed, uid.bytes) == secret
    with pytest.raises(fieldcrypt.FieldCryptError):
        fieldcrypt.unseal(settings, sealed, uuid.uuid4().bytes)
