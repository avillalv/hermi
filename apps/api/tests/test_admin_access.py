# ruff: noqa: E501  (long lines)
"""WF-058.1: the Cloudflare Access assertion check (08 sections 2.2, 2.3 and 9): signature, audience, issuer, expiry, and the
dev signer that mints the same shape. No database."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from hermi.config import Settings
from hermi.security.jwt import (
    AccessVerifier,
    AuthModeError,
    TokenError,
    TokenVerifier,
    mint_access_token,
    mint_dev_token,
)

TEAM, AUD = "hermi.cloudflareaccess.com", "a" * 64
ISS = f"https://{TEAM}"
RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _settings(**kw) -> Settings:
    base = {
        "environment": "ci",
        "auth_mode": "dev",
        "admin_auth_mode": "cf_access",
        "cf_access_team_domain": TEAM,
        "cf_access_aud": AUD,
    }
    return Settings(_env_file=None, **{**base, **kw})


def _jwks(key=RSA_KEY, kid="cf1"):
    return lambda: {"keys": [{**RSAAlgorithm.to_jwk(key.public_key(), as_dict=True), "kid": kid, "alg": "RS256", "use": "sig"}]}


def _claims(**over):
    now = int(time.time())
    return {"iss": ISS, "aud": [AUD], "sub": "cf-sub", "email": "Ada@Example.com", "type": "app", "iat": now, "exp": now + 600, **over}


def _token(claims=None, key=RSA_KEY, alg="RS256", kid="cf1"):
    return jwt.encode(claims or _claims(), key, algorithm=alg, headers={"kid": kid})


def _verifier(**kw):
    return AccessVerifier(_settings(**kw), fetch=_jwks())


def test_valid_assertion_yields_the_lowercased_email():
    who = _verifier().verify(_token())
    assert who.email == "ada@example.com" and who.subject == "cf-sub"


def test_audience_may_be_a_list_with_other_apps():
    assert _verifier().verify(_token(_claims(aud=["other", AUD]))).email


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": ["someone-else"]},
        {"iss": "https://evil.cloudflareaccess.com"},
        {"exp": int(time.time()) - 3600},
        {"email": None},
    ],
)
def test_bad_claims_are_rejected(claims):
    c = {k: v for k, v in _claims(**claims).items() if v is not None}
    with pytest.raises(TokenError):
        _verifier().verify(_token(c))


def test_wrong_signature_unknown_kid_and_hs256_are_rejected():
    v = _verifier()
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(TokenError):
        v.verify(_token(key=other))
    with pytest.raises(TokenError):
        v.verify(_token(kid="nope"))
    with pytest.raises(TokenError):
        v.verify(jwt.encode(_claims(), "x" * 40, algorithm="HS256", headers={"kid": "cf1"}))
    with pytest.raises(TokenError):
        v.verify("not-a-jwt")


def test_team_domain_may_be_a_bare_team_name():
    s = _settings(cf_access_team_domain="hermi")
    assert AccessVerifier(s, fetch=_jwks()).verify(_token()).email


def test_cf_access_mode_without_config_fails_closed():
    s = _settings(cf_access_team_domain=None)
    with pytest.raises(TokenError):
        AccessVerifier(s, fetch=_jwks()).verify(_token())


def test_dev_signer_mints_a_token_the_same_verifier_accepts():
    s = _settings(admin_auth_mode="dev", cf_access_team_domain=None, cf_access_aud=None)
    tok = mint_access_token(s, "Founder@Example.com")
    assert AccessVerifier(s).verify(tok).email == "founder@example.com"
    claims = jwt.decode(tok, options={"verify_signature": False})
    assert claims["iss"].startswith("https://") and isinstance(claims["aud"], list) and claims["type"] == "app"


def test_dev_signer_follows_configured_team_and_audience():
    s = _settings(admin_auth_mode="dev")
    claims = jwt.decode(mint_access_token(s, "a@example.com"), options={"verify_signature": False})
    assert claims["iss"] == ISS and claims["aud"] == [AUD]


def test_dev_signer_and_verifier_are_refused_outside_local_and_ci():
    s = _settings(environment="staging", admin_auth_mode="dev")
    with pytest.raises(AuthModeError):
        mint_access_token(s, "a@example.com")
    with pytest.raises(AuthModeError):
        AccessVerifier(s).verify("x")


def test_signer_needs_dev_mode():
    with pytest.raises(AuthModeError):
        mint_access_token(_settings(admin_auth_mode="cf_access"), "a@example.com")


def test_customer_token_is_not_an_admin_assertion_and_the_reverse():
    s = _settings(admin_auth_mode="dev", auth_mode="dev")
    customer = mint_dev_token(s, "11111111-1111-1111-1111-111111111111", email="a@example.com")
    with pytest.raises(TokenError):
        AccessVerifier(s).verify(customer)
    with pytest.raises(TokenError):
        TokenVerifier(s).verify(mint_access_token(s, "a@example.com"))
