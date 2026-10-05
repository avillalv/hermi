# ruff: noqa: E501  (long comments)
"""Postgres rate limits (10 section 2.3, WF-028) on `rate_limit_counters`.

Counters are fixed windows, one row per (bucket, window_start). A route class is one entry in ROUTE_CLASSES:
`name: (limit, window_seconds)`. The limits are editable without a deploy or restart in the `setting_rate_limits`
row of `feature_flags` (JSON `{class: limit}`, read with a short cache). A missing or malformed row, or a class
missing from it, falls back to the built-in value. Every limited response is the shared 429 with `Retry-After`.

shortcut: a fixed window lets a burst of up to 2x the limit through across a window edge. Upgrade to a real token
bucket (count plus refill timestamp) when abuse shows it.
"""

import hashlib
import time
from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from hermi.deps import CurrentUser
from hermi.errors import ApiError
from hermi.modules.notifications.waitlist import client_ip

MINUTE, HOUR, DAY = 60, 3600, 86400
# Starting values, tuned from data (the seed row mirrors the limits). The caller picks the scope: a user id, an IP or a token.
ROUTE_CLASSES: dict[str, tuple[int, int]] = {
    "ai": (30, HOUR),
    "places_search": (30, MINUTE),
    "outbound": (60, HOUR),
    "import_preview": (
        20,
        DAY,
    ),  # ICS file, pasted text, Google Maps file, pasted places, all together
    "import_ics_feed": (5, DAY),
    "import_confirm": (30, DAY),
    "link_preview": (20, HOUR),
    "export": (1, DAY),
    "delete": (1, DAY),
    "signup_ip": (5, DAY),  # new accounts per IP
    "share_view": (60, MINUTE),  # per token
    "share_view_ip": (120, MINUTE),
    "read_user": (600, MINUTE),
    "read_ip": (1200, MINUTE),
    "write_user": (120, MINUTE),
    "write_ip": (600, MINUTE),
}
SETTING_KEY = "setting_rate_limits"
CACHE_TTL = 30.0  # seconds a limits read is reused, so an admin edit lands within half a minute
TEST_LIMITS: dict[
    str, int
] = {}  # TEST-ONLY hook, never set in app code: beats the row (conftest lifts signup_ip)
_cache: tuple[float, dict] | None = None

# shortcut: a short built-in list of well-known throwaway domains (subdomains match too). Ceiling: new services slip
# through. Upgrade to a maintained list file in the repo or a vendor feed when abuse shows it.
DISPOSABLE_DOMAINS = frozenset(
    "mailinator.com guerrillamail.com guerrillamail.net guerrillamail.org sharklasers.com grr.la 10minutemail.com "
    "10minutemail.net tempmail.com temp-mail.org temp-mail.io tempmailo.com throwawaymail.com yopmail.com yopmail.net "
    "trashmail.com trashmail.net getnada.com nada.email maildrop.cc dispostable.com fakeinbox.com mailnesia.com "
    "mintemail.com moakt.com emailondeck.com burnermail.io mohmal.com spamgourmet.com mytemp.email tempail.com "
    "discard.email dropmail.me inboxkitten.com mailcatch.com spambox.us getairmail.com tmail.ws".split()
)


def reset_cache() -> None:
    global _cache
    _cache = None


def _stored(conn) -> dict:
    global _cache
    if _cache and time.monotonic() < _cache[0]:
        return _cache[1]
    try:
        rules = conn.execute(
            text("SELECT rules FROM feature_flags WHERE key = :k AND enabled"), {"k": SETTING_KEY}
        ).scalar()
    except Exception:  # a failed read must never take the API down; the built-in values stay
        rules = None
    rules = rules if isinstance(rules, dict) else {}
    _cache = (time.monotonic() + CACHE_TTL, rules)
    return rules


def limit_for(name: str, stored: dict | None = None) -> tuple[int, int]:
    limit, window = ROUTE_CLASSES[name]
    v = {**(stored or {}), **TEST_LIMITS}.get(name)
    return (
        (v, window)
        if isinstance(v, int) and not isinstance(v, bool) and v >= 0
        else (limit, window)
    )


def hit(engine, name: str, key: str, *, clock: Callable[[], float] = time.time) -> None:
    """Count one request for `key` in `name`. Raises the 429 when the window is over its limit."""
    now = clock()
    with (
        engine.connect() as conn
    ):  # its own connection, so a failed read cannot poison the counter transaction
        limit, window = limit_for(name, _stored(conn))
    start = int(now // window) * window
    with engine.begin() as conn:
        count = conn.execute(
            text(
                "INSERT INTO rate_limit_counters (bucket, window_start, count) VALUES (:b, to_timestamp(:s), 1) "
                "ON CONFLICT (bucket, window_start) DO UPDATE SET count = rate_limit_counters.count + 1 RETURNING count"
            ),
            {"b": f"{name}:{key}", "s": start},
        ).scalar_one()
    if count > limit:
        retry = max(1, int(start + window - now + 0.999))
        raise ApiError(
            429,
            "rate_limited",
            "You are doing that too fast. Try again in a moment.",
            {"Retry-After": str(retry)},
        )


def digest(secret: str) -> str:
    """A bucket key for a secret such as a share token, so the raw value is never stored."""
    return hashlib.sha256(secret.encode()).hexdigest()[:24]


def is_disposable(email: str) -> bool:
    parts = email.rsplit("@", 1)[-1].strip().lower().split(".")
    return any(".".join(parts[i:]) in DISPOSABLE_DOMAINS for i in range(len(parts)))


def check_signup(request: Request, email: str | None) -> None:
    """Refuse a throwaway email, then count a new account against its IP for the day. Called only when the
    identity has no account yet, so sign-ins never count. A bootstrap that fails later still counts (it is abuse
    control, not accounting)."""
    if email and is_disposable(email):
        raise RequestValidationError(
            [
                {
                    "loc": ("token", "email"),
                    "type": "value_error",
                    "msg": "Use a permanent email address to create an account.",
                }
            ]
        )
    # The IP is client_ip(): the socket peer unless the peer is in TRUSTED_PROXY_CIDRS. Behind Render the peer is
    # Render's proxy, so until its range (and Cloudflare's) is trusted every signup shares one IP and one bucket.
    hit(request.app.state.engine, "signup_ip", client_ip(request))


def rate_limited(name: str):
    """FastAPI dependency: `Depends(rate_limited("ai"))` limits per signed-in user for that route class."""
    ROUTE_CLASSES[name]  # fail at import, not on the first request, when the class is misspelled

    def dependency(request: Request, user: CurrentUser) -> None:
        hit(request.app.state.engine, name, str(user.id))

    return Depends(dependency)
