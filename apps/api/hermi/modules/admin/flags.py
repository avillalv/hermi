# ruff: noqa: E501  (long SQL strings and docstrings)
"""Feature flags and kill switches (03 section 5.17, 08 section 6.5): models, audited writes and the cached runtime.

Reads run as any role (the API login can SELECT both tables). Writes run as a role that may write kill_switches and
insert audit_log (the admin console login, the worker or the system session): the API login cannot.
"""

import hashlib
import json
import logging
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

import psycopg
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from hermi.errors import ApiError, NotFound

log = logging.getLogger("hermi.flags")
CHANNEL = "hermi_flags"  # NOTIFY payload is the changed key
TTL_SECONDS = 5.0
PAID_TIERS = {"plus", "trip_pass"}


@dataclass(frozen=True)
class Flag:
    key: str
    kind: str
    enabled: bool
    rollout_pct: int
    rules: Mapping
    variants: Mapping


@dataclass(frozen=True)
class Switch:
    key: str
    engaged: bool
    expires_at: datetime | None = None
    reason: str | None = None
    engaged_by: uuid.UUID | None = None
    engaged_at: datetime | None = None
    auto_rule: Mapping | None = None


@dataclass(frozen=True)
class Snapshot:
    flags: Mapping[str, Flag] = field(default_factory=dict)
    switches: Mapping[str, Switch] = field(default_factory=dict)


@dataclass(frozen=True)
class Ctx:
    """Who is asking. A missing value never matches a rule that names values."""

    user_id: uuid.UUID | None = None
    tier: str | None = None
    platform: str | None = None
    country: str | None = None
    app_version: str | None = None


# --- repository ---------------------------------------------------------------------------------------------------


def load_snapshot(session: Session) -> Snapshot:
    flags = {
        r.key: Flag(r.key, r.kind, r.enabled, r.rollout_pct, r.rules or {}, r.variants or {})
        for r in session.execute(
            text("SELECT key, kind, enabled, rollout_pct, rules, variants FROM feature_flags")
        )
    }
    switches = {
        r.key: Switch(r.key, r.engaged, r.expires_at, r.reason, r.engaged_by, r.engaged_at, r.auto_rule)
        for r in session.execute(
            text("SELECT key, engaged, expires_at, reason, engaged_by, engaged_at, auto_rule FROM kill_switches")
        )
    }
    return Snapshot(flags, switches)


def engine_loader(engine: Engine) -> Callable[[], Snapshot]:
    def load() -> Snapshot:
        with Session(engine) as s:
            return load_snapshot(s)

    return load


def _audit(session: Session, *, action: str, key: str, actor_type: str, actor_user_id, reason, before, after) -> None:
    session.execute(
        text(
            """INSERT INTO audit_log (actor_user_id, actor_type, action, entity_type, entity_id, before, after, reason, retention_class)
               VALUES (:actor, :atype, :action, 'kill_switch', :key, CAST(:before AS jsonb), CAST(:after AS jsonb), :reason, 'extended')"""
        ),
        {
            "actor": actor_user_id,
            "atype": actor_type,
            "action": action,
            "key": key,
            "before": json.dumps(before, default=str),
            "after": json.dumps(after, default=str),
            "reason": reason,
        },
    )


def _state(session: Session, key: str) -> dict | None:
    row = session.execute(
        text("SELECT engaged, reason, expires_at, engaged_by FROM kill_switches WHERE key = :k FOR UPDATE"), {"k": key}
    ).one_or_none()
    return None if row is None else dict(row._mapping)


def engage_switch(
    session: Session,
    key: str,
    *,
    actor_type: str,
    reason: str,
    actor_user_id: uuid.UUID | None = None,
    expires_at: datetime | None = None,
) -> None:
    """Engage (or create, for user:<id> holds) a switch, write audit_log and NOTIFY, all in the caller's transaction.

    An admin-set switch needs an expiry (ck_kill_switches_expiry); only provider.* may go without one. The caller commits."""
    if actor_type == "admin" and expires_at is None and not key.startswith("provider."):
        raise ApiError(422, "expiry_required", "A manual switch needs an expiry.")
    before = _state(session, key)
    session.execute(
        text(
            """INSERT INTO kill_switches (key, engaged, reason, engaged_by, engaged_at, expires_at, expiry_notified_at)
               VALUES (:k, true, :reason, :by, now(), :exp, NULL)
               ON CONFLICT (key) DO UPDATE SET engaged = true, reason = :reason, engaged_by = :by, engaged_at = now(),
                 expires_at = :exp, expiry_notified_at = NULL"""
        ),
        {"k": key, "reason": reason, "by": actor_user_id if actor_type == "admin" else None, "exp": expires_at},
    )
    after = {"engaged": True, "reason": reason, "expires_at": expires_at}
    _audit(session, action="killswitch.engage", key=key, actor_type=actor_type, actor_user_id=actor_user_id, reason=reason, before=before, after=after)
    session.execute(text("SELECT pg_notify(:c, :k)"), {"c": CHANNEL, "k": key})


def clear_switch(
    session: Session, key: str, *, actor_type: str, actor_user_id: uuid.UUID | None = None, reason: str | None = None
) -> None:
    before = _state(session, key)
    if before is None:
        raise NotFound("We could not find that switch.")
    session.execute(
        text("UPDATE kill_switches SET engaged = false, expires_at = NULL, expiry_notified_at = NULL WHERE key = :k"), {"k": key}
    )
    after = {"engaged": False}
    _audit(session, action="killswitch.clear", key=key, actor_type=actor_type, actor_user_id=actor_user_id, reason=reason, before=before, after=after)
    session.execute(text("SELECT pg_notify(:c, :k)"), {"c": CHANNEL, "k": key})


# --- evaluation ---------------------------------------------------------------------------------------------------


def _version(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split(".") if p.isdigit())


def _bucket(key: str, user_id: uuid.UUID) -> int:
    """Stable 0 to 99 bucket for (flag key, user): the same user always lands in the same cell."""
    return int.from_bytes(hashlib.sha256(f"{key}:{user_id}".encode()).digest()[:8], "big") % 100


def evaluate_flag(flag: Flag, ctx: Ctx) -> bool:
    """Master switch, then every rule that is set (all must match), then the percent rollout."""
    if not flag.enabled:
        return False
    r = flag.rules
    for rule, value in (("tiers", ctx.tier), ("platforms", ctx.platform), ("countries", ctx.country)):
        if r.get(rule) and value not in r[rule]:
            return False
    if r.get("user_ids") and (ctx.user_id is None or str(ctx.user_id) not in r["user_ids"]):
        return False
    for rule, ok in (("min_app_version", lambda a, b: a >= b), ("max_app_version", lambda a, b: a <= b)):
        if r.get(rule):
            try:
                if ctx.app_version is None or not ok(_version(ctx.app_version), _version(r[rule])):
                    return False
            except (TypeError, ValueError):
                return False
    if flag.rollout_pct >= 100:
        return True
    return ctx.user_id is not None and _bucket(flag.key, ctx.user_id) < flag.rollout_pct


# --- runtime ------------------------------------------------------------------------------------------------------


class FlagRuntime:
    """One per process. Holds a snapshot for `ttl` seconds; a NOTIFY (see start_listener) drops it early.

    A failed read keeps the last good snapshot for flag reads, but paid calls refuse (fail closed)."""

    def __init__(self, loader: Callable[[], Snapshot], *, clock: Callable[[], float] = time.time, ttl: float = TTL_SECONDS):
        self._loader, self._clock, self._ttl = loader, clock, ttl
        self._good = Snapshot()
        self._expires = float("-inf")
        self._readable = False
        self._lock = threading.Lock()

    def invalidate(self) -> None:
        self._expires = float("-inf")

    def _snapshot(self) -> tuple[Snapshot, bool]:
        with self._lock:
            now = self._clock()
            if now >= self._expires:
                try:
                    self._good, self._readable = self._loader(), True
                except Exception:
                    log.exception("flags_unreadable")
                    self._readable = False
                self._expires = now + self._ttl
            return self._good, self._readable

    def evaluate(self, key: str, ctx: Ctx | None = None) -> bool:
        flag = self._snapshot()[0].flags.get(key)
        return flag is not None and evaluate_flag(flag, ctx or Ctx())

    def _engaged(self, snap: Snapshot, key: str) -> bool:
        s = snap.switches.get(key)
        return bool(s and s.engaged and (s.expires_at is None or s.expires_at.timestamp() > self._clock()))

    def switch_engaged(self, key: str) -> bool:
        return self._engaged(self._snapshot()[0], key)

    def ensure_paid_allowed(self, *feature_keys: str, user_id: uuid.UUID | None = None, tier: str | None = None) -> None:
        """Raise 503 ai_unavailable before a paid call when ai.all, a named feature switch, the tier switch or the
        user's hold is engaged, or when the tables cannot be read."""
        snap, readable = self._snapshot()
        keys = ["ai.all", *feature_keys]
        if tier is not None:
            keys.append("ai.all_but_paid" if tier not in PAID_TIERS else "")
            if tier == "free":
                keys.append("ai.free_tier")
        if user_id is not None:
            keys.append(f"user:{user_id}")
        if not readable or any(k and self._engaged(snap, k) for k in keys):
            raise ApiError(503, "ai_unavailable", "This is paused for a moment. Try again soon.")

    def paid_allowed(self, *feature_keys: str, **kw) -> bool:
        try:
            self.ensure_paid_allowed(*feature_keys, **kw)
        except ApiError:
            return False
        return True


class Listener:
    def __init__(self, thread: threading.Thread, stop: threading.Event):
        self._thread, self._stop = thread, stop

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


def start_listener(dsn: str, runtime: FlagRuntime) -> Listener:
    """LISTEN on the flags channel and drop the cache on every NOTIFY. If the connection fails it retries every 5
    seconds; meanwhile the TTL still bounds staleness to `ttl`."""
    stop = threading.Event()

    def run() -> None:
        while not stop.is_set():
            try:
                with psycopg.connect(dsn, autocommit=True) as conn:
                    conn.execute(f"LISTEN {CHANNEL}")
                    while not stop.is_set():
                        for _ in conn.notifies(timeout=0.5):
                            runtime.invalidate()
                            if stop.is_set():
                                break
            except Exception:
                log.warning("flags_listener_down", exc_info=True)
                stop.wait(5)

    t = threading.Thread(target=run, name="flags-listener", daemon=True)
    t.start()
    return Listener(t, stop)
