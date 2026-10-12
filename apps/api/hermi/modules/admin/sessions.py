# ruff: noqa: E501  (long SQL and comments)
"""The admin 2FA session (08 section 2.2): a random cookie whose HMAC is a row in admin_sessions.

8 hours absolute, 30 minutes idle, step-up fresh for 5 minutes. The row is read on every request, so ending it (sign out,
disable) takes effect at once; the admin lookup around it caches for 30 seconds, which is the 60 second bound in 08.
The cookie is `HttpOnly`, `Secure`, `SameSite=Strict`, host-only (no Domain) and `Path=/v1/admin`, so a browser never
sends it to a customer route. Customer routes read only the Authorization bearer, so the cookie opens nothing there.
Also holds the single use WebAuthn challenges. All time comes from `app.state.admin_clock` so tests can move it.
"""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Request, Response
from sqlalchemy import text

from hermi.errors import ApiError

COOKIE = "hermi_admin_session"
ABSOLUTE = timedelta(hours=8)
IDLE = timedelta(minutes=30)
FRESH = timedelta(minutes=5)
CHALLENGE_TTL = timedelta(minutes=5)


@dataclass(frozen=True)
class AdminSession:
    id: uuid.UUID
    user_id: uuid.UUID
    expires_at: datetime
    last_seen_at: datetime
    stepup_at: datetime | None
    method: str = ""
    created_at: datetime | None = None

    def fresh_until(self) -> datetime | None:
        return self.stepup_at + FRESH if self.stepup_at else None

    def is_fresh(self, now: datetime) -> bool:
        until = self.fresh_until()
        return until is not None and now <= until

    def break_glass_open(self, now: datetime) -> bool:
        """A recovery code session may re-enrol factors (and nothing else) for 5 minutes after it opened."""
        return self.method == "recovery" and self.created_at is not None and now <= self.created_at + FRESH


def now(request: Request) -> datetime:
    return request.app.state.admin_clock()


def engine(request: Request):
    e = request.app.state.admin_engine
    if e is None:
        raise ApiError(503, "admin_unavailable", "The admin console is not available right now.")
    return e


def token_hash(request: Request, token: str) -> bytes:
    secret = request.app.state.settings.admin_session_secret
    key = secret.get_secret_value().encode() if secret else b""
    return hmac.new(key, token.encode(), hashlib.sha256).digest()


def start(request: Request, response: Response, user_id: uuid.UUID, method: str) -> AdminSession:
    """A new session. A passkey or TOTP sign-in is already fresh (that check counts as the step-up). A recovery code
    is not a step-up factor, so a break-glass session starts stale (stepup_at NULL) and every X action asks for 428."""
    t = now(request)
    fresh = method != "recovery"
    token = secrets.token_urlsafe(32)
    with engine(request).begin() as c:
        c.execute(text("DELETE FROM admin_sessions WHERE expires_at < :t"), {"t": t})
        row = c.execute(
            text(
                "INSERT INTO admin_sessions (user_id, token_hash, method, created_at, last_seen_at, expires_at, stepup_at, user_agent) "
                "VALUES (:u, :h, :m, :t, :t, :x, :s, :ua) RETURNING id"
            ),
            {
                "u": user_id,
                "h": token_hash(request, token),
                "m": method,
                "t": t,
                "x": t + ABSOLUTE,
                "s": t if fresh else None,
                "ua": (request.headers.get("user-agent") or "")[:200] or None,
            },
        ).scalar_one()
    response.set_cookie(
        COOKIE, token, max_age=int(ABSOLUTE.total_seconds()), path="/v1/admin", httponly=True, secure=True, samesite="strict"
    )
    return AdminSession(row, user_id, t + ABSOLUTE, t, t if fresh else None, method, t)


def current(request: Request, user_id: uuid.UUID, *, touch: bool = True) -> AdminSession | None:
    """The live session for this cookie and admin, or None (no cookie, unknown, another admin's, expired, idle).
    `touch` slides the idle clock; the session endpoint reads without sliding it."""
    token = request.cookies.get(COOKIE)
    if not token or len(token) > 128:
        return None
    t = now(request)
    params = {"h": token_hash(request, token), "u": user_id, "t": t, "idle": t - IDLE}
    sql = (
        "SELECT id, user_id, expires_at, last_seen_at, stepup_at, method, created_at FROM admin_sessions "
        "WHERE token_hash = :h AND user_id = :u AND expires_at > :t AND last_seen_at > :idle"
    )
    if touch:
        sql = (
            "UPDATE admin_sessions SET last_seen_at = :t WHERE token_hash = :h AND user_id = :u AND expires_at > :t AND last_seen_at > :idle "
            "RETURNING id, user_id, expires_at, last_seen_at, stepup_at, method, created_at"
        )
    with engine(request).begin() as c:
        row = c.execute(text(sql), params).first()
    return AdminSession(*row) if row else None


def mark_fresh(request: Request, session: AdminSession) -> None:
    with engine(request).begin() as c:
        c.execute(text("UPDATE admin_sessions SET stepup_at = :t WHERE id = :i"), {"t": now(request), "i": session.id})


def end(request: Request, response: Response, user_id: uuid.UUID) -> None:
    token = request.cookies.get(COOKIE)
    if token and len(token) <= 128:
        with engine(request).begin() as c:
            c.execute(
                text("DELETE FROM admin_sessions WHERE token_hash = :h AND user_id = :u"),
                {"h": token_hash(request, token), "u": user_id},
            )
    response.delete_cookie(COOKIE, path="/v1/admin", httponly=True, secure=True, samesite="strict")


# --- single use WebAuthn challenges ------------------------------------------------------------------------


def issue_challenge(request: Request, user_id: uuid.UUID, purpose: str) -> tuple[uuid.UUID, bytes]:
    t, challenge = now(request), secrets.token_bytes(32)
    with engine(request).begin() as c:
        c.execute(text("DELETE FROM admin_auth_challenges WHERE user_id = :u AND expires_at < :t"), {"u": user_id, "t": t})
        cid = c.execute(
            text(
                "INSERT INTO admin_auth_challenges (user_id, purpose, challenge, expires_at) VALUES (:u, :p, :c, :x) RETURNING id"
            ),
            {"u": user_id, "p": purpose, "c": challenge, "x": t + CHALLENGE_TTL},
        ).scalar_one()
    return cid, challenge


def consume_challenge(request: Request, user_id: uuid.UUID, purpose: str, challenge_id: uuid.UUID) -> bytes | None:
    """The challenge bytes, once. A second call, another admin, another purpose or an expired one gets None."""
    with engine(request).begin() as c:
        row = c.execute(
            text(
                "DELETE FROM admin_auth_challenges WHERE id = :i AND user_id = :u AND purpose = :p AND expires_at > :t RETURNING challenge"
            ),
            {"i": challenge_id, "u": user_id, "p": purpose, "t": now(request)},
        ).first()
    return bytes(row[0]) if row else None
