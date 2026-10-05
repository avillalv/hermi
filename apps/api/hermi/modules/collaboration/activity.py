# ruff: noqa: E501  (long comments and SQL)
"""Trip activity feed (WF-027.1): `record` writes one activity_log row, `feed` reads a keyset page (03 section 5.4, 05 section 6.24).

Summaries never carry a person's name (the actor is a separate field, so "Deleted user" and renames stay right) and never carry
note text. Anything private is not written at all: the table has no per-viewer column, so a private row could not be hidden later.
"""

import base64
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import ApiError
from hermi.modules.collaboration.schemas import ActivityActor, ActivityItem, ActivityPage


def record(
    session: Session,
    trip_id: uuid.UUID,
    actor_id: uuid.UUID,
    verb: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    summary: str = "",
    *,
    private: bool = False,
) -> int | None:
    """Insert in the caller's transaction (RLS: actor must be the caller and a member, so log before a leave or removal)."""
    if private:
        return None
    return session.execute(
        text(
            "INSERT INTO activity_log (trip_id, actor_user_id, verb, entity_type, entity_id, summary) "
            "VALUES (:t, :a, :v, :e, :i, :s) RETURNING id"
        ),
        {"t": trip_id, "a": actor_id, "v": verb, "e": entity_type, "i": entity_id, "s": summary[:300]},
    ).scalar_one()


# shortcut: the cursor is unsigned base64 of the last id (harmless, RLS still scopes rows). Upgrade: HMAC-signed 24h cursor per 04 line 91.
def _decode(cursor: str) -> int:
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except ValueError:
        raise ApiError(400, "bad_request", "That page cursor is not valid. Start from the first page.") from None


def feed(session: Session, trip_id: uuid.UUID, limit: int, cursor: str | None) -> ActivityPage:
    rows = session.execute(
        text(
            "SELECT a.id, a.verb, a.entity_type, a.entity_id, a.summary, a.created_at, a.actor_user_id, "
            "       NULLIF(p.display_name, '') AS name"
            "  FROM activity_log a LEFT JOIN trip_member_profiles p ON p.trip_id = a.trip_id AND p.user_id = a.actor_user_id "
            " WHERE a.trip_id = :t AND (CAST(:c AS bigint) IS NULL OR a.id < :c) ORDER BY a.id DESC LIMIT :n"
        ),
        {"t": trip_id, "c": _decode(cursor) if cursor else None, "n": limit + 1},
    ).mappings().all()
    page = rows[:limit]
    items = [
        ActivityItem(
            verb=r["verb"],
            entity_type=r["entity_type"],
            entity_id=r["entity_id"],
            summary=r["summary"],
            at=r["created_at"],
            actor=ActivityActor(
                id=r["actor_user_id"],
                display_name="Deleted user" if r["actor_user_id"] is None else r["name"] or "Former member",
            ),
        )
        for r in page
    ]
    more = len(rows) > limit
    return ActivityPage(items=items, next_cursor=base64.urlsafe_b64encode(str(page[-1]["id"]).encode()).decode() if more else None, has_more=more)
