# ruff: noqa: E501  (long SQL and comments)
"""Admin identity for /v1/admin (08 sections 2.2, 2.3 and 9).

The request pipeline: verify the `Cf-Access-Jwt-Assertion` header (the same code in `cf_access` and `dev` mode), map the
verified email to a users row with an enabled admin_users row, check the permission, then the per-admin rate limit.
Customer bearer tokens are never read here and this header is never read by the customer dependencies, so neither
identity opens the other routes. hermi_app cannot read admin_users, so lookups run on the admin engine.
"""

import logging
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from hermi.errors import ApiError
from hermi.logging_setup import bind
from hermi.modules.admin import permissions, sessions
from hermi.modules.notifications.waitlist import client_ip
from hermi.security import rate_limit
from hermi.security.jwt import TokenError

log = logging.getLogger("hermi.admin")
ASSERTION_HEADER = "cf-access-jwt-assertion"
CACHE_TTL = 30.0  # seconds; a disabled admin is out within this, well inside the 60 the spec allows (08 section 2.2)


@dataclass(frozen=True)
class AdminPrincipal:
    user_id: uuid.UUID
    email: str
    role: str
    mfa_enrolled: bool


class AdminDirectory:
    """email -> enabled admin, read from the admin engine and cached for 30 seconds. Only hits are cached, so an
    identity with no row is looked up (and logged) every time and a new grant works at once."""

    def __init__(self, engine: Callable[[], Engine | None], *, clock: Callable[[], float] = time.monotonic, ttl: float = CACHE_TTL):
        self._engine, self._clock, self._ttl = engine, clock, ttl
        self._cache: dict[str, tuple[float, AdminPrincipal]] = {}
        self._lock = threading.Lock()

    def lookup(self, email: str) -> AdminPrincipal | None:
        key, now = email.strip().lower(), self._clock()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now < hit[0]:
                return hit[1]
        engine = self._engine()
        if engine is None:
            raise ApiError(503, "admin_unavailable", "The admin console is not available right now.")
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT u.id, u.email::text, a.role::text, a.mfa_enrolled FROM users u JOIN admin_users a ON a.user_id = u.id "
                    "WHERE u.email = :e AND u.deleted_at IS NULL AND u.status = 'active' AND a.disabled_at IS NULL"
                ),
                {"e": key},
            ).first()
        with self._lock:
            if row is None:
                self._cache.pop(key, None)
                return None
            principal = AdminPrincipal(row[0], row[1].lower(), row[2], row[3])
            self._cache[key] = (now + self._ttl, principal)
            return principal

    def invalidate(self, user_id: uuid.UUID | None = None) -> None:
        """Drop one admin (or all) from this process cache. Other processes still wait out their 30 seconds."""
        with self._lock:
            for k in [k for k, (_, p) in self._cache.items() if user_id is None or p.user_id == user_id]:
                del self._cache[k]


def _audit_denied(request: Request, subject: str | None) -> None:
    """One `denied` audit row for an identity that passed Access but is not an enabled admin. Own transaction on the
    admin engine; the entity is the Access subject, never the email. A failed write is logged, never blocks the 403."""
    try:
        with Session(request.app.state.admin_engine) as s:
            s.execute(
                text(
                    "INSERT INTO audit_log (actor_user_id, actor_type, action, entity_type, entity_id, result, error_code, "
                    "request_id, user_agent, retention_class) VALUES (NULL, 'admin', 'admin_session.denied', 'access_identity', "
                    ":sub, 'denied', 'admin_not_enabled', :rid, :ua, 'extended')"
                ),
                {
                    "sub": subject,
                    "rid": getattr(request.state, "request_id", None),
                    "ua": (request.headers.get("user-agent") or "")[:200] or None,
                },
            )
            s.commit()
    except Exception:
        log.exception("admin denied audit write failed")


def _count_failure(request: Request) -> None:
    """One failed-login count for this client IP (a bad assertion or an identity with no admin row). Over the limit the
    401 or 403 becomes a 429 with Retry-After and an alert log line (08 section 9 rule 5). A counter fault never hides the
    real answer."""
    engine = request.app.state.admin_engine
    if engine is None:
        return
    try:
        rate_limit.hit(engine, "admin_auth_fail_ip", client_ip(request))
    except ApiError as e:
        if e.status == 429:
            log.warning("admin_login_lockout", extra={"rate_class": "admin_auth_fail_ip"})
            raise
    except Exception:
        log.exception("admin failed-login counter failed")


def admin_principal(request: Request) -> AdminPrincipal:
    """The enabled admin behind a valid Access assertion. 401 for a missing or bad assertion, 403 for an identity that
    passed Access but has no enabled admin row (and an alert log line, 08 section 2.2)."""
    token = request.headers.get(ASSERTION_HEADER, "").strip()
    try:
        if not token:
            raise TokenError()
        who = request.app.state.access_verifier.verify(token)
    except TokenError as e:
        # No token content in the log.
        log.warning("admin_assertion_rejected", extra={"reason": e.code, "had_token": bool(token)})
        _count_failure(request)
        raise ApiError(
            401, e.code, "Your session ended. Sign in again." if e.code == "token_expired" else "Sign in to continue."
        ) from None
    admin = request.app.state.admin_directory.lookup(who.email)
    if admin is None:
        # The alert rule watches this logger and message (08 section 10). No email in the log line.
        log.warning("admin_identity_denied", extra={"access_subject": who.subject, "reason": "no_enabled_admin_row"})
        _audit_denied(request, who.subject)
        _count_failure(request)
        raise ApiError(403, "admin_not_enabled", "This account does not have admin access.")
    bind(admin_id=str(admin.user_id), admin_role=admin.role)
    return admin


CurrentAdmin = Annotated[AdminPrincipal, Depends(admin_principal)]


def require_session(
    request: Request, admin: AdminPrincipal, *, fresh: bool = False, touch: bool = True, break_glass: bool = False
) -> sessions.AdminSession:
    """The completed 2FA session behind this request (08 section 2.3: "check session 2FA freshness for the action class").
    403 `mfa_enrollment_required` until the admin is enrolled, 401 `two_factor_required` with no live session, 428
    `stepup_required` when `fresh` and the last WebAuthn or TOTP check is older than 5 minutes. `break_glass` (the enrolment
    routes only) also accepts a recovery code session in its first 5 minutes, so a lost passkey can be replaced."""
    if not admin.mfa_enrolled:
        raise ApiError(403, "mfa_enrollment_required", "Set up two-factor sign-in to continue.")
    session = sessions.current(request, admin.user_id, touch=touch)
    if session is None:
        raise ApiError(401, "two_factor_required", "Confirm it is you to continue.")
    ok = session.is_fresh(sessions.now(request)) or (break_glass and session.break_glass_open(sessions.now(request)))
    if fresh and not ok:
        raise ApiError(
            428, "stepup_required", "Confirm it is you again to do that.", extra={"fresh_seconds": int(sessions.FRESH.total_seconds())}
        )
    return session


def require(name: str, *, write: bool = False, rate: str | None = None, two_factor: bool = True, stepup: bool | None = None):
    """Depends() for an admin route: the caller must hold permission `name` at read (default) or write level, then (unless
    `two_factor=False`, the sign-in and enrolment routes) hold a live 2FA session, then the per-admin rate limit for `rate`
    is counted. Every /v1/admin route uses exactly one; tests/test_admin_permissions.py walks the routes for the marker.

    Step-up (a 2FA check inside 5 minutes, 428 otherwise) applies to a write whose matrix level is `X`, or when the route
    passes `stepup=True` (08 section 2.2 also lists PII reveals and impersonation, which the matrix marks `W`). `X` writes
    count against the 5 a minute `admin_x` class (when the route has no class of its own)."""
    if name not in permissions.KNOWN:
        raise ValueError(f"{name!r} is not in the 08 section 3 matrix")
    need = "write" if write else "read"
    default_rate = rate or ("admin_write" if write else "admin_read")
    rate_limit.ROUTE_CLASSES[default_rate]  # a misspelled class fails at import

    def dependency(request: Request, admin: CurrentAdmin) -> AdminPrincipal:
        if not permissions.permits(admin.role, name, need):
            log.warning("admin_permission_denied", extra={"permission": name, "admin_role": admin.role})
            # 403 names the missing permission (08 section 8).
            raise ApiError(403, "permission_denied", "Your role cannot do that.", extra={"permission": name})
        is_x = write and permissions.level(admin.role, name) == "X"
        if two_factor:
            require_session(request, admin, fresh=stepup if stepup is not None else is_x)
        rate = "admin_x" if is_x and default_rate == "admin_write" else default_rate
        try:
            rate_limit.hit(request.app.state.admin_engine, rate, str(admin.user_id))
        except ApiError as e:
            if e.status == 429 and rate in ("admin_stepup", "admin_signin"):
                # The lockout alert rule watches this logger and message (08 section 9 rule 5).
                log.warning("admin_2fa_lockout", extra={"rate_class": rate, "admin_id": str(admin.user_id)})
            raise
        return admin

    dependency.__admin_permission__ = (name, need, default_rate)
    return Depends(dependency)


def idempotency_key(key: Annotated[str | None, Header(alias="Idempotency-Key")] = None) -> str:
    """Every admin write names its attempt (08 section 8).

    shortcut: the key is required and validated but not stored. The admin writes here are naturally idempotent (a repeat
    of an invite is 409, a repeat of a patch lands on the same state, apart from a second audit row). Store replays in
    idempotency_keys, which is keyed by customer user id, when an admin write that is not repeat-safe lands (WF-059 or later)."""
    k = (key or "").strip()
    if not k:
        raise ApiError(400, "idempotency_key_required", "Send an Idempotency-Key header.")
    if not 8 <= len(k) <= 128:
        raise ApiError(
            422,
            "validation_failed",
            "Some fields need another look.",
            extra={"errors": [{"field": "Idempotency-Key", "code": "string_length", "message": "Use 8 to 128 characters."}]},
        )
    return k


@contextmanager
def admin_transaction(request: Request) -> Iterator[Session]:
    """One transaction on the admin engine: the action and its audit row commit together or not at all (08 section 2.3)."""
    engine = request.app.state.admin_engine
    if engine is None:
        raise ApiError(503, "admin_unavailable", "The admin console is not available right now.")
    with Session(engine) as s:
        try:
            yield s
            s.commit()
        except BaseException:
            s.rollback()
            raise


def write_guard(request: Request, key: Annotated[str | None, Header(alias="Idempotency-Key")] = None) -> None:
    """CSRF defence for the whole /v1/admin router (08 section 9 rule 7): every write must carry an Idempotency-Key,
    a custom header a cross-site form or a no-cors fetch cannot send. Runs before the Access and 2FA checks, so it
    covers sign-in, sign-out and enrolment too. Reads are exempt."""
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        idempotency_key(key)
