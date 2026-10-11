# ruff: noqa: E501
"""scan_due_routes: the leader's 30 second scan of flight_routes.next_check_at (02 section 5.2 steps 2 and 3).

Not a Procrastinate job: the scheduler loop calls run() every tick, because cron cannot go below a minute. It enqueues one
`check_fare_route` per due route and moves next_check_at to the next daily slot strictly after now, so an outage fires one
check and slots never stack. Eligibility, the kill switch and budget reservation arrive with WF-051.2.
"""

import logging
import uuid
import zlib
from datetime import UTC, datetime, timedelta

from procrastinate.exceptions import AlreadyEnqueued
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.jobs import enqueue

log = logging.getLogger(__name__)

CHECK_JOB = "check_fare_route"
LIMIT = 500
JITTER_WINDOW_SECONDS = 60 * 60
PRIORITY = 5  # paid live-route checks (hermi.jobs, "Fair claim")

_DUE = text(
    """SELECT id FROM flight_routes WHERE active AND next_check_at IS NOT NULL AND next_check_at <= :now
       ORDER BY next_check_at LIMIT :n FOR UPDATE SKIP LOCKED"""
)


def jitter_seconds(route_id: uuid.UUID) -> int:
    """Stable per route and per process: crc32 of the id bytes (python's hash() is salted per process)."""
    return zlib.crc32(route_id.bytes) % JITTER_WINDOW_SECONDS


def next_slot(route_id: uuid.UUID, now: datetime) -> datetime:
    """The first daily slot (00:00 UTC plus the route's jitter) strictly after now."""
    midnight = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    slot = midnight + timedelta(seconds=jitter_seconds(route_id))
    return slot if slot > now else slot + timedelta(days=1)


def run(session: Session, now: datetime | None = None, limit: int = LIMIT) -> dict[str, int]:
    """Enqueue the due routes and advance their slots, in the caller's transaction (the caller commits).
    Returns {"due", "enqueued", "skipped_already_queued"}."""
    now = now or datetime.now(UTC)
    ids = [r[0] for r in session.execute(_DUE, {"now": now, "n": limit})]
    out = {"due": len(ids), "enqueued": 0, "skipped_already_queued": 0}
    for rid in ids:
        try:
            with session.begin_nested():  # a duplicate queueing lock must not poison the scan's transaction
                enqueue(session, CHECK_JOB, queueing_lock=f"{CHECK_JOB}:{rid}", priority=PRIORITY, route_id=str(rid))
            out["enqueued"] += 1
        except AlreadyEnqueued:
            out["skipped_already_queued"] += 1  # a check is still waiting; the slot still advances
        session.execute(text("UPDATE flight_routes SET next_check_at = :t WHERE id = :id"), {"t": next_slot(rid, now), "id": rid})
    return out
