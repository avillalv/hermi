# ruff: noqa: E501  (long comments and SQL)
"""Bearer token verification (02 section 3 step 3, 04 section 1.2). Only module that imports PyJWT.

`supabase` mode checks Supabase JWTs against the cached JWKS. `dev` mode checks tokens signed by a key
pair generated in this process (so a restart ends dev sessions), served as a local JWKS. Dev mode is
refused outside `local` and `ci`: config.py refuses it at startup and this module again at verify and
mint time.
"""

import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from hermi.config import LOCAL_ENVIRONMENTS, Settings

ALGORITHMS = ["RS256", "ES256"]  # never `none`, never HS*: a key mismatch must fail, not downgrade
LEEWAY_SECONDS = 30
JWKS_TTL_SECONDS = 3600
JWKS_MIN_REFETCH_SECONDS = 60
JWKS_FETCH_TIMEOUT_SECONDS = 5
JWKS_MAX_BYTES = 256 * 1024
JWKS_MAX_STALE_SECONDS = 24 * 3600  # hard ceiling on serving keys after refetches keep failing
DEV_ISSUER = "hermi-dev"
DEV_AUDIENCE = "authenticated"
PROVIDERS = frozenset({"apple", "google", "email"})  # auth_identities.provider (03 section 3)


class TokenError(Exception):
    """The token is not acceptable. `code` is the 04 section 3 error code (401)."""

    def __init__(self, code: str = "unauthenticated"):
        super().__init__(code)
        self.code = code


class AuthModeError(RuntimeError):
    """AUTH_MODE=dev outside local and ci."""


@dataclass(frozen=True)
class VerifiedToken:
    subject: str
    provider: str
    email: str | None
    claims: dict


def _refuse_dev_outside_local(settings: Settings) -> None:
    if settings.auth_mode == "dev" and settings.environment not in LOCAL_ENVIRONMENTS:
        raise AuthModeError("AUTH_MODE=dev is refused outside local and ci")


class _DevKeys:
    def __init__(self) -> None:
        self.private = ec.generate_private_key(ec.SECP256R1())
        self.kid = "dev-" + uuid.uuid4().hex[:12]

    def jwks(self) -> dict:
        jwk = ECAlgorithm.to_jwk(self.private.public_key(), as_dict=True)
        return {"keys": [{**jwk, "kid": self.kid, "use": "sig", "alg": "ES256"}]}


_dev_keys: _DevKeys | None = None
_dev_lock = threading.Lock()


def _dev() -> _DevKeys:
    global _dev_keys
    with _dev_lock:
        if _dev_keys is None:
            _dev_keys = _DevKeys()
        return _dev_keys


def mint_dev_token(
    settings: Settings,
    subject: str,
    *,
    provider: str = "email",
    email: str | None = None,
    ttl_seconds: int = 3600,
) -> str:
    """A bearer token for the dev routes (WF-013.2). Same claim shape as a Supabase token."""
    if settings.auth_mode != "dev":
        raise AuthModeError("Dev tokens need AUTH_MODE=dev")
    _refuse_dev_outside_local(settings)
    keys, now = _dev(), int(time.time())
    claims = {
        "iss": DEV_ISSUER,
        "aud": DEV_AUDIENCE,
        "sub": subject,
        "iat": now,
        "exp": now + ttl_seconds,
        "app_metadata": {"provider": provider},
    }
    if email:
        claims["email"] = email
    return jwt.encode(claims, keys.private, algorithm="ES256", headers={"kid": keys.kid})


def _http_fetch(url: str) -> dict:
    # The URL is our own configuration (SUPABASE_JWKS_URL), never user input. https, or loopback.
    if not url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise TokenError("unauthenticated")
    # No redirects, a hard timeout and a size cap. shortcut: the body is read whole before the cap check; the
    # 5 second timeout and our own config URL bound it. Stream it if the JWKS host ever becomes untrusted.
    r = httpx.get(url, timeout=JWKS_FETCH_TIMEOUT_SECONDS, follow_redirects=False)
    r.raise_for_status()
    if len(r.content) > JWKS_MAX_BYTES:
        raise TokenError("unauthenticated")
    return r.json()


class TokenVerifier:
    """Verifies bearer tokens. `fetch` and `clock` let tests serve a local JWKS and move time."""

    def __init__(
        self,
        settings: Settings,
        fetch: Callable[[], dict] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._settings = settings
        self._fetch = fetch
        self._clock = clock
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at: float | None = None  # last attempt, ok or not
        self._ok_at: float | None = None  # last successful fetch
        self._lock = threading.Lock()

    def _source(self) -> dict:
        if self._fetch:
            return self._fetch()
        if self._settings.auth_mode == "dev":
            return _dev().jwks()
        return _http_fetch(self._settings.require("SUPABASE_JWKS_URL"))

    def _key(self, kid: str) -> jwt.PyJWK:
        with self._lock:
            now = self._clock()
            age = None if self._fetched_at is None else now - self._fetched_at
            stale = age is None or age >= JWKS_TTL_SECONDS
            unknown = kid not in self._keys
            if stale or (unknown and age >= JWKS_MIN_REFETCH_SECONDS):
                try:
                    keys = jwt.PyJWKSet.from_dict(self._source()).keys
                except TokenError:
                    raise
                except (
                    Exception
                ):  # network, JSON or key errors: keep serving the cached keys if any
                    keys = None
                self._fetched_at = now  # a failed refetch also waits a minute before the next try
                if keys is not None:
                    self._keys = {k.key_id: k for k in keys if k.key_id}
                    self._ok_at = now
            if self._ok_at is None or now - self._ok_at >= JWKS_MAX_STALE_SECONDS:
                self._keys = {}
                raise TokenError()
            try:
                return self._keys[kid]
            except KeyError:
                raise TokenError() from None

    def verify(self, token: str) -> VerifiedToken:
        s = self._settings
        _refuse_dev_outside_local(s)
        if s.auth_mode == "dev":
            issuer, audience = DEV_ISSUER, DEV_AUDIENCE
        else:
            issuer, audience = s.require("SUPABASE_JWT_ISSUER"), s.require("SUPABASE_JWT_AUDIENCE")
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if header.get("alg") not in ALGORITHMS or not isinstance(kid, str):
                raise TokenError()
            claims = jwt.decode(
                token,
                self._key(kid),  # the PyJWK itself, so PyJWT also enforces the JWK alg
                algorithms=ALGORITHMS,
                audience=audience,
                issuer=issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
        except jwt.ExpiredSignatureError:
            raise TokenError("token_expired") from None
        except (
            jwt.PyJWTError,
            TypeError,
            ValueError,
        ):  # TypeError: the token's alg does not fit the key type
            raise TokenError() from None
        subject = claims["sub"]
        provider = (claims.get("app_metadata") or {}).get("provider", "email")
        if not isinstance(subject, str) or not subject or provider not in PROVIDERS:
            raise TokenError()
        email = claims.get("email")
        return VerifiedToken(subject, provider, email if isinstance(email, str) else None, claims)
