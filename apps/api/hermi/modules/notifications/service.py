# ruff: noqa: E501
"""The notification service (WF-047): rows, preferences, quiet hours, mutes, email delivery, unsubscribe and the three scheduled producers.

A notification row is the outbox entry and the in-app inbox entry (03 section 5.18). `create` inserts it with ON CONFLICT on
(user_id, dedupe_key), so a retried or repeated job never makes a second row, and enqueues `send_email`. `deliver_email` takes the
row lock, checks the gates, sends, and stamps `email_sent_at` in one transaction, so a retried send_email never mails twice (and
Resend gets the row id as its Idempotency-Key for the crash between the send and the commit). Push delivery is WF-086.
"""

import base64
import hashlib
import hmac
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi import jobs
from hermi.config import Settings
from hermi.modules.notifications import email, templates

log = logging.getLogger("hermi.notifications")

DEFAULT_QUIET = (time(22, 0), time(8, 0))
PREDEPARTURE_HOUR, DIGEST_HOUR = 9, 8  # local hour from which the hourly scan may create the notification (02 section 5.1)
SCOPES = ("marketing", "all")
KILL_SWITCH_RETRY = timedelta(minutes=15)


# --- creating rows ---------------------------------------------------------------------------------------------------


def create(
    session: Session,
    *,
    user_id: uuid.UUID,
    kind: str,
    dedupe_key: str,
    title: str,
    body: str = "",
    payload: dict | None = None,
    trip_id: uuid.UUID | None = None,
    want_push: bool = True,
    want_email: bool = True,
) -> uuid.UUID | None:
    """Insert one notification and queue its email. Returns the id, or None when (user_id, dedupe_key) already exists."""
    if kind not in templates.KINDS:
        raise ValueError(f"unknown notification kind {kind!r}")
    nid = session.execute(
        text(
            "INSERT INTO notifications (user_id, trip_id, kind, dedupe_key, title, body, payload, want_push, want_email) "
            "VALUES (:u, :t, :k, :d, :title, :body, CAST(:p AS jsonb), :wp, :we) "
            "ON CONFLICT (user_id, dedupe_key) DO NOTHING RETURNING id"
        ),
        {"u": user_id, "t": trip_id, "k": kind, "d": dedupe_key, "title": title[:120], "body": body[:400], "p": json.dumps(payload or {}), "wp": want_push, "we": want_email},
    ).scalar()
    if nid is not None and want_email:
        jobs.enqueue(session, "send_email", notification_id=str(nid))
    return nid


# --- preferences -----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Prefs:
    email_enabled: bool = True
    email_off: tuple[str, ...] = ()
    push_off: tuple[str, ...] = ()
    quiet_enabled: bool = True
    quiet_start: time = DEFAULT_QUIET[0]
    quiet_end: time = DEFAULT_QUIET[1]


def load_prefs(session: Session, user_id: uuid.UUID) -> Prefs:
    r = session.execute(
        text("SELECT email_enabled, email_off, push_off, quiet_enabled, quiet_start, quiet_end FROM notification_preferences WHERE user_id = :u"),
        {"u": user_id},
    ).first()
    if r is None:
        return Prefs()
    return Prefs(r[0], tuple(r[1]), tuple(r[2]), r[3], r[4], r[5])


def has_marketing_consent(session: Session, user_id: uuid.UUID) -> bool:
    """The latest marketing_email consent row decides. No row means no consent."""
    r = session.execute(
        text("SELECT granted FROM consents WHERE user_id = :u AND kind = 'marketing_email' ORDER BY created_at DESC, id DESC LIMIT 1"),
        {"u": user_id},
    ).scalar()
    return bool(r)


def is_muted(session: Session, user_id: uuid.UUID, trip_id: uuid.UUID | None) -> bool:
    if trip_id is None:
        return False
    return session.execute(text("SELECT 1 FROM trip_notification_mutes WHERE user_id = :u AND trip_id = :t"), {"u": user_id, "t": trip_id}).first() is not None


def zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def quiet_release(now: datetime, tz: str | None, prefs: Prefs) -> datetime | None:
    """When `now` is inside the person's quiet hours, the UTC time they end; otherwise None."""
    if not prefs.quiet_enabled or prefs.quiet_start == prefs.quiet_end:
        return None
    local = now.astimezone(zone(tz))
    t, s, e = local.time(), prefs.quiet_start, prefs.quiet_end
    inside = s <= t < e if s < e else (t >= s or t < e)
    if not inside:
        return None
    end = local.replace(hour=e.hour, minute=e.minute, second=0, microsecond=0)
    if end <= local:
        end += timedelta(days=1)
    return end.astimezone(UTC)


# --- unsubscribe links -----------------------------------------------------------------------------------------------


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _sig(secret: str, payload: str) -> str:
    return _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()[:16])


def sign_unsubscribe(settings: Settings, user_id: uuid.UUID, scope: str) -> str:
    """A signed token for one user and one scope. No expiry: an old email must still unsubscribe (CAN-SPAM)."""
    payload = f"{user_id}.{scope}"
    return f"{_b64(payload.encode())}.{_sig(settings.require('UNSUBSCRIBE_SECRET'), payload)}"


def verify_unsubscribe(settings: Settings, token: str) -> tuple[uuid.UUID, str] | None:
    try:
        raw, sig = token.split(".")
        payload = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode()
        user, scope = payload.split(".")
        uid = uuid.UUID(user)
    except ValueError:
        return None
    if scope not in SCOPES or not hmac.compare_digest(sig, _sig(settings.require("UNSUBSCRIBE_SECRET"), payload)):
        return None
    return uid, scope


def unsubscribe_url(settings: Settings, user_id: uuid.UUID, scope: str) -> str:
    return f"{settings.public_api_url.rstrip('/')}/v1/unsubscribe?t={sign_unsubscribe(settings, user_id, scope)}"


def apply_unsubscribe(session: Session, user_id: uuid.UUID, scope: str) -> bool:
    """Idempotent. 'marketing' withdraws the marketing_email consent; 'all' also switches email off. False for an unknown user."""
    if session.execute(text("SELECT 1 FROM users WHERE id = :u"), {"u": user_id}).first() is None:
        return False
    if has_marketing_consent(session, user_id):
        session.execute(
            text("INSERT INTO consents (user_id, kind, version, granted, source) VALUES (:u, 'marketing_email', 'unsubscribe-link', false, 'email')"),
            {"u": user_id},
        )
    if scope == "all":
        session.execute(
            text("INSERT INTO notification_preferences (user_id, email_enabled) VALUES (:u, false) ON CONFLICT (user_id) DO UPDATE SET email_enabled = false"),
            {"u": user_id},
        )
    return True


# --- email delivery --------------------------------------------------------------------------------------------------


def _skip(session: Session, nid: uuid.UUID, why: str) -> str:
    """The email will never go: clear want_email so the row leaves the outbox. The in-app entry stays."""
    session.execute(text("UPDATE notifications SET want_email = false WHERE id = :id"), {"id": nid})
    return f"skipped:{why}"


def deliver_email(session: Session, settings: Settings, notification_id: uuid.UUID, *, now: datetime | None = None) -> str:
    """Send the email of one notification row. Returns sent, already_sent, deferred, blocked, missing or skipped:<why>.
    The caller commits. Never mails twice: the row is locked until the commit and email_sent_at is checked under the lock."""
    now = now or datetime.now(UTC)
    n = (
        session.execute(
            text(
                "SELECT n.id, n.user_id, n.trip_id, n.kind, n.title, n.body, n.payload, n.want_email, n.email_sent_at, u.email, u.timezone, u.status::text AS status "
                "FROM notifications n JOIN users u ON u.id = n.user_id WHERE n.id = :id FOR UPDATE OF n"
            ),
            {"id": notification_id},
        )
        .mappings()
        .first()
    )
    if n is None:
        return "missing"
    if n["email_sent_at"] is not None:
        return "already_sent"
    k = templates.KINDS.get(n["kind"])
    if not n["want_email"] or k is None:
        return "skipped:not_wanted"
    if session.execute(text("SELECT engaged FROM kill_switches WHERE key = 'email.all'")).scalar():
        jobs.enqueue(session, "send_email", schedule_at=now + KILL_SWITCH_RETRY, notification_id=str(n["id"]))
        return "blocked"  # held, and looked at again in 15 minutes
    if n["status"] != "active" and not (k.urgent and n["status"] == "pending_deletion"):
        return _skip(session, n["id"], "inactive_user")
    prefs = load_prefs(session, n["user_id"])
    if not k.urgent and (not prefs.email_enabled or n["kind"] in prefs.email_off):
        return _skip(session, n["id"], "preference")
    if k.category == "marketing" and not templates.POSTAL_ADDRESS:
        return _skip(session, n["id"], "no_postal_address")  # shortcut: dropped, not held; fine while no producer emits marketing kinds; revisit before the first lifecycle producer ships or set POSTAL_ADDRESS first. CAN-SPAM wants it in the footer; owner-pending
    if k.category == "marketing" and not has_marketing_consent(session, n["user_id"]):
        return _skip(session, n["id"], "no_marketing_consent")
    if is_muted(session, n["user_id"], n["trip_id"]):
        return _skip(session, n["id"], "trip_muted")
    if not k.urgent:
        release = quiet_release(now, n["timezone"], prefs)
        if release is not None:
            jobs.enqueue(session, "send_email", schedule_at=release, notification_id=str(n["id"]))
            return "deferred"

    scope = "marketing" if k.category == "marketing" else "all"
    unsub = unsubscribe_url(settings, n["user_id"], scope)
    subject, body_text, body_html = templates.render(
        n["kind"], title=n["title"], body=n["body"], payload=n["payload"], base_url=settings.public_web_url, unsubscribe_url=unsub
    )
    if settings.email_backend == "resend":
        settings.require("RESEND_API_KEY")  # without a key the sender would fall back to the log and the mail would be lost
    headers = {"List-Unsubscribe": f"<{unsub}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"} if n["kind"] != "account_deleted" else None
    email.send(settings, n["email"], subject, body_text, html=body_html, headers=headers, idempotency_key=f"notification-{n['id']}")
    session.execute(text("UPDATE notifications SET email_sent_at = :now WHERE id = :id"), {"now": now, "id": n["id"]})
    return "sent"


# --- scheduled producers (each deduplicated per user and trip by the row's dedupe_key) ---------------------------------


def queue_predeparture_reminders(session: Session, now: datetime | None = None) -> int:
    """The 7-day pre-departure reminder, from 09:00 local on the day that is 7 days before the start date."""
    now = now or datetime.now(UTC)
    today = now.date()
    rows = session.execute(
        text(
            "SELECT t.id AS trip_id, t.name, t.start_date, u.id AS user_id, u.timezone "
            "FROM trips t JOIN trip_members m ON m.trip_id = t.id JOIN users u ON u.id = m.user_id "
            "WHERE t.deleted_at IS NULL AND t.archived_at IS NULL AND u.status = 'active' AND u.deleted_at IS NULL "
            "  AND t.start_date BETWEEN :d0 AND :d1 "
            "  AND NOT EXISTS (SELECT 1 FROM trip_notification_mutes x WHERE x.trip_id = t.id AND x.user_id = u.id)"
        ),
        {"d0": today + timedelta(days=6), "d1": today + timedelta(days=8)},  # one day either side covers every time zone
    ).mappings().all()
    made = 0
    for r in rows:
        local = now.astimezone(zone(r["timezone"]))
        if local.date() + timedelta(days=7) != r["start_date"] or local.hour < PREDEPARTURE_HOUR:
            continue
        nid = create(
            session,
            user_id=r["user_id"],
            trip_id=r["trip_id"],
            kind="pre_trip_reminder",
            dedupe_key=f"reminder:{r['trip_id']}:7d",
            title=f"{r['name']} starts in 7 days",
            body="Check your checklist, documents and bookings while there is still time.",
            payload={"url": f"/trips/{r['trip_id']}"},
        )
        made += nid is not None
    return made


def build_digests(session: Session, now: datetime | None = None) -> int:
    """The activity digest: from 08:00 local, one notification per user and trip per day, if others changed the plan since
    the previous digest (or the last 24 hours)."""
    now = now or datetime.now(UTC)
    day_ago = now - timedelta(hours=24)
    rows = session.execute(
        text(
            "SELECT m.user_id, t.id AS trip_id, t.name, u.timezone, "
            "  (SELECT max(n.created_at) FROM notifications n WHERE n.user_id = u.id AND n.trip_id = t.id AND n.kind = 'activity_digest') AS last_digest "
            "FROM trip_members m JOIN trips t ON t.id = m.trip_id JOIN users u ON u.id = m.user_id "
            "WHERE t.deleted_at IS NULL AND t.archived_at IS NULL AND u.status = 'active' AND u.deleted_at IS NULL "
            "  AND NOT EXISTS (SELECT 1 FROM trip_notification_mutes x WHERE x.trip_id = t.id AND x.user_id = u.id) "
            "  AND EXISTS (SELECT 1 FROM activity_log a WHERE a.trip_id = t.id AND a.actor_user_id IS DISTINCT FROM u.id AND a.created_at > :since)"
        ),
        {"since": day_ago},
    ).mappings().all()
    made = 0
    for r in rows:
        local = now.astimezone(zone(r["timezone"]))
        if local.hour < DIGEST_HOUR:
            continue
        since = max(day_ago, r["last_digest"]) if r["last_digest"] else day_ago
        changes = session.execute(
            text("SELECT summary FROM activity_log WHERE trip_id = :t AND actor_user_id IS DISTINCT FROM :u AND created_at > :since ORDER BY id"),
            {"t": r["trip_id"], "u": r["user_id"], "since": since},
        ).scalars().all()
        if not changes:
            continue
        noun = "change" if len(changes) == 1 else "changes"
        shown = "; ".join(c for c in changes[:5] if c)
        more = f" and {len(changes) - 5} more" if len(changes) > 5 else ""
        nid = create(
            session,
            user_id=r["user_id"],
            trip_id=r["trip_id"],
            kind="activity_digest",
            dedupe_key=f"digest:{r['trip_id']}:{local.date().isoformat()}",
            title=f"Changes on {r['name']}",
            body=f"{len(changes)} {noun}: {shown}{more}." if shown else f"{len(changes)} {noun} since your last update.",
            payload={"url": f"/trips/{r['trip_id']}", "count": len(changes)},
            want_push=False,
        )
        made += nid is not None
    return made


def queue_trial_ending_reminders(session: Session, now: datetime | None = None) -> int:
    """The reminder 2 days before an annual trial converts. One per user and trial period (WF-051 wires the trigger)."""
    now = now or datetime.now(UTC)
    rows = session.execute(
        text(
            "SELECT s.user_id, s.period_end FROM subscriptions s JOIN users u ON u.id = s.user_id "
            "WHERE s.status = 'in_trial' AND s.auto_renew AND u.status = 'active' AND u.deleted_at IS NULL "
            "  AND s.period_end > :now AND s.period_end <= :limit"
        ),
        {"now": now, "limit": now + timedelta(days=2)},
    ).mappings().all()
    made = 0
    for r in rows:
        end = r["period_end"]
        nid = create(
            session,
            user_id=r["user_id"],
            kind="trial_ending",
            dedupe_key=f"trial_ending:{end.date().isoformat()}",
            title="Your free trial ends soon",
            body=f"Your trial ends on {end.day} {end:%b} {end.year}. After that your plan renews unless you cancel first.",
            payload={"url": "/account"},
        )
        made += nid is not None
    return made
