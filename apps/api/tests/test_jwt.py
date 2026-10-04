# ruff: noqa: E501  (long SQL strings and comments)
"""WF-013.1: token verification against a local JWKS, the algorithm allowlist and the dev mode refusal (04 section 1.2)."""

import base64
import json
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from hermi.config import Settings
from hermi.security import jwt as hjwt
from hermi.security.jwt import AuthModeError, TokenError, TokenVerifier, mint_dev_token

ISS, AUD = "https://abc.supabase.co/auth/v1", "authenticated"
EC_KEY = ec.generate_private_key(ec.SECP256R1())
RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _settings(**kw) -> Settings:
    base = {
        "environment": "ci",
        "auth_mode": "supabase",
        "supabase_jwt_issuer": ISS,
        "supabase_jwt_audience": AUD,
        "supabase_jwks_url": "https://abc.supabase.co/jwks",
    }
    return Settings(_env_file=None, **{**base, **kw})


def _jwk(key, kid, alg):
    algo = ECAlgorithm if alg == "ES256" else RSAAlgorithm
    return {**algo.to_jwk(key.public_key(), as_dict=True), "kid": kid, "alg": alg, "use": "sig"}


class Jwks:
    """A local JWKS the verifier fetches from; counts fetches and can change its keys."""

    def __init__(self, *keys):
        self.keys, self.fetches = list(keys), 0

    def __call__(self):
        self.fetches += 1
        return {"keys": self.keys}


def _claims(**over):
    now = int(time.time())
    return {"iss": ISS, "aud": AUD, "sub": "sub-1", "iat": now, "exp": now + 600, **over}


def _token(claims=None, key=EC_KEY, alg="ES256", kid="k1"):
    return jwt.encode(claims or _claims(), key, algorithm=alg, headers={"kid": kid})


@pytest.fixture
def jwks():
    return Jwks(_jwk(EC_KEY, "k1", "ES256"), _jwk(RSA_KEY, "k2", "RS256"))


@pytest.fixture
def verifier(jwks):
    return TokenVerifier(_settings(), fetch=jwks)


def _code(verifier, token):
    with pytest.raises(TokenError) as e:
        verifier.verify(token)
    return e.value.code


def test_valid_es256_and_rs256_tokens(verifier):
    v = verifier.verify(_token(_claims(email="a@example.com", app_metadata={"provider": "apple"})))
    assert (v.subject, v.provider, v.email) == ("sub-1", "apple", "a@example.com")
    assert verifier.verify(_token(key=RSA_KEY, alg="RS256", kid="k2")).provider == "email"


def test_expired_token_is_token_expired(verifier):
    assert _code(verifier, _token(_claims(exp=int(time.time()) - 120))) == "token_expired"


def test_thirty_seconds_of_skew_is_allowed(verifier):
    verifier.verify(_token(_claims(exp=int(time.time()) - 10)))
    verifier.verify(_token(_claims(nbf=int(time.time()) + 10)))
    assert _code(verifier, _token(_claims(nbf=int(time.time()) + 120))) == "unauthenticated"


@pytest.mark.parametrize("over", [{"aud": "someone-else"}, {"iss": "https://evil.example/auth/v1"}])
def test_wrong_audience_and_issuer(verifier, over):
    assert _code(verifier, _token(_claims(**over))) == "unauthenticated"


@pytest.mark.parametrize("drop", ["exp", "sub", "iss", "aud"])
def test_required_claims(verifier, drop):
    c = _claims()
    del c[drop]
    assert _code(verifier, _token(c)) == "unauthenticated"


def test_tampered_payload_and_signature(verifier):
    h, p, s = _token().split(".")
    pad = lambda x: x + "=" * (-len(x) % 4)  # noqa: E731
    body = json.loads(base64.urlsafe_b64decode(pad(p)))
    body["sub"] = "someone-else"
    p2 = base64.urlsafe_b64encode(json.dumps(body).encode()).rstrip(b"=").decode()
    assert _code(verifier, f"{h}.{p2}.{s}") == "unauthenticated"
    assert _code(verifier, f"{h}.{p}.{s[:-4]}AAAA") == "unauthenticated"
    assert _code(verifier, "not-a-jwt") == "unauthenticated"


def test_signed_by_another_key_with_a_known_kid(verifier):
    other = ec.generate_private_key(ec.SECP256R1())
    assert _code(verifier, _token(key=other)) == "unauthenticated"


def test_unknown_kid_refetches_at_most_once_a_minute(jwks):
    now = [1000.0]
    v = TokenVerifier(_settings(), fetch=jwks, clock=lambda: now[0])
    v.verify(_token())
    assert jwks.fetches == 1
    now[0] += 5
    assert _code(v, _token(kid="rotated")) == "unauthenticated"
    assert jwks.fetches == 1  # too soon: no refetch
    new = ec.generate_private_key(ec.SECP256R1())
    jwks.keys.append(_jwk(new, "rotated", "ES256"))
    now[0] += 60
    v.verify(_token(key=new, kid="rotated"))
    assert jwks.fetches == 2
    now[0] += 61
    assert _code(v, _token(kid="nope")) == "unauthenticated"
    assert jwks.fetches == 3


def test_jwks_is_cached_for_an_hour(jwks):
    now = [0.0]
    v = TokenVerifier(_settings(), fetch=jwks, clock=lambda: now[0])
    for _ in range(3):
        v.verify(_token())
    assert jwks.fetches == 1
    now[0] += 3601
    v.verify(_token())
    assert jwks.fetches == 2


def test_jwks_fetch_failure_is_a_401_not_a_crash():
    def boom():
        raise OSError("down")

    assert _code(TokenVerifier(_settings(), fetch=boom), _token()) == "unauthenticated"


def test_stale_keys_are_refused_after_24_hours_of_failed_refetches(jwks):
    now, down = [0.0], [False]

    def fetch():
        if down[0]:
            raise OSError("down")
        return jwks()

    v = TokenVerifier(_settings(), fetch=fetch, clock=lambda: now[0])
    v.verify(_token())
    down[0] = True
    now[0] += 3601 * 6  # six hours of failures: cached keys still serve
    v.verify(_token())
    now[0] += 3600 * 18
    assert _code(v, _token()) == "unauthenticated"
    down[0] = False
    now[0] += 61
    v.verify(_token())  # recovers on the next good fetch


def test_http_fetch_uses_no_redirects_and_caps_the_body(monkeypatch):
    seen = {}

    def get(url, **kw):
        seen.update(kw)
        return httpx.Response(200, content=b'{"keys": []}', request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", get)
    assert hjwt._http_fetch("https://abc.supabase.co/jwks") == {"keys": []}
    assert seen == {"timeout": 5, "follow_redirects": False}
    big = b" " * (hjwt.JWKS_MAX_BYTES + 1)
    monkeypatch.setattr(
        httpx, "get", lambda url, **kw: httpx.Response(200, content=big, request=httpx.Request("GET", url))
    )
    with pytest.raises(TokenError):
        hjwt._http_fetch("https://abc.supabase.co/jwks")


def test_algorithm_none_is_rejected(verifier):
    b64 = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()  # noqa: E731
    token = f"{b64({'alg': 'none', 'kid': 'k1'})}.{b64(_claims())}."
    assert _code(verifier, token) == "unauthenticated"


def test_hs256_mismatch_is_rejected(verifier):
    token = jwt.encode(
        _claims(),
        "a-shared-secret-of-sufficient-length-32b",
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    assert _code(verifier, token) == "unauthenticated"


def test_es256_header_with_an_rsa_key_is_rejected(verifier):
    token = jwt.encode(
        _claims(), RSA_KEY, algorithm="RS256", headers={"kid": "k1"}
    )  # k1 is an EC key
    assert _code(verifier, token) == "unauthenticated"


def test_unknown_provider_is_rejected(verifier):
    assert (
        _code(verifier, _token(_claims(app_metadata={"provider": "github"}))) == "unauthenticated"
    )


# --- dev mode ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("env", ["local", "ci"])
def test_dev_tokens_round_trip_in_local_and_ci(env):
    s = _settings(environment=env, auth_mode="dev")
    v = TokenVerifier(s).verify(mint_dev_token(s, "dev-1", provider="apple", email="d@example.com"))
    assert (v.subject, v.provider, v.email) == ("dev-1", "apple", "d@example.com")


def test_dev_token_is_not_accepted_in_supabase_mode():
    dev = _settings(auth_mode="dev")
    token = mint_dev_token(dev, "dev-1")
    assert (
        _code(TokenVerifier(_settings(supabase_jwks_url=None), fetch=Jwks()), token)
        == "unauthenticated"
    )


@pytest.mark.parametrize("env", ["preview", "staging", "production"])
def test_dev_mode_is_refused_at_verify_and_mint_time_outside_local_and_ci(env):
    s = _settings(environment=env, auth_mode="dev")
    token = mint_dev_token(_settings(auth_mode="dev"), "dev-1")
    with pytest.raises(AuthModeError):
        TokenVerifier(s).verify(token)
    with pytest.raises(AuthModeError):
        mint_dev_token(s, "dev-1")


def test_only_this_module_imports_pyjwt():
    from pathlib import Path

    root = Path(hjwt.__file__).parents[1]
    offenders = [
        p.name
        for p in root.rglob("*.py")
        if p != Path(hjwt.__file__) and "import jwt" in p.read_text("utf-8")
    ]
    assert offenders == []
