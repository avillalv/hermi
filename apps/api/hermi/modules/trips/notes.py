# ruff: noqa: E501  (long SQL strings)
"""Notes (04 section 5.14): user notes on a trip, a day or an item, with optional source links.

Sources come from `notes.urls`: a link is stored as pasted and never fetched. `stale` is an agent note checked more than 14 days ago.
Private notes are author-only: row-level security hides them from everyone else (so every route 404s for them), and they are never
written to the activity feed. `/notes/{id}` carries no trip id: `_via_note` resolves the trip, then runs the same `require_trip` check.
Stay notes need no route here: a stay keeps its own `notes` text in 5.9 (`notes` has no lodging column, and this step adds no migration).
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.collaboration.activity import record
from hermi.modules.collaboration.schemas import Attribution
from hermi.modules.lodging import service as links
from hermi.pagination import decode_offset, encode_offset
from hermi.security.preconditions import resolve_version, version_conflict

router = APIRouter(tags=["notes"])

STALE_DAYS = 14
_SELECT = (
    "SELECT n.id, n.trip_id, n.kind::text AS kind, n.title, n.body, n.urls, n.day, n.itinerary_item_id AS item_id, n.is_private, n.pinned, n.run_id, n.checked_at, "
    f"(n.kind = 'agent' AND n.checked_at < now() - interval '{STALE_DAYS} days') AS stale, n.version, n.author_user_id, NULLIF(p.display_name, '') AS author_name, n.created_at, n.updated_at "
    "FROM notes n LEFT JOIN trip_member_profiles p ON p.trip_id = n.trip_id AND p.user_id = n.author_user_id "
)


class Source(BaseModel):
    url: str
    title: str | None = None
    fetched_at: datetime
    site: str | None = None  # the host without "www."


class NoteIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)] | None = None
    body: Annotated[str, StringConstraints(max_length=10000)] | None = None
    pinned: bool | None = None
    is_private: bool | None = None
    day: date | None = None
    item_id: uuid.UUID | None = None
    source_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    version: int | None = None


class Note(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    kind: Literal["user", "agent"]
    title: str
    body: str
    pinned: bool
    is_private: bool
    day: date | None
    item_id: uuid.UUID | None
    version: int
    author: Attribution | None
    run_id: uuid.UUID | None
    sources: list[Source]
    checked_at: datetime
    stale: bool
    created_at: datetime
    updated_at: datetime


class NotePage(BaseModel):
    items: list[Note]
    next_cursor: str | None
    has_more: bool


class Evidence(BaseModel):
    note_id: uuid.UUID
    run_id: uuid.UUID | None
    sources: list[Source]
    excerpt: str | None
    checked_at: datetime
    stale: bool
    stale_after_days: int = STALE_DAYS


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "validation_failed", "Some fields need another look.", extra={"errors": [{"field": field, "code": "invalid", "message": message}]})


def _sources(r) -> list[Source]:
    return [Source(url=u, fetched_at=r["checked_at"], site=links.site_of(u)) for u in r["urls"]]


def _out(r) -> Note:
    return Note(
        **{k: r[k] for k in ("id", "trip_id", "kind", "title", "body", "pinned", "is_private", "day", "item_id", "version", "run_id", "checked_at", "stale", "created_at", "updated_at")},
        author=Attribution(id=r["author_user_id"], display_name=r["author_name"]) if r["author_user_id"] else None,
        sources=_sources(r),
    )


def _row(session: Session, note_id: uuid.UUID):
    r = session.execute(text(_SELECT + "WHERE n.id = :i"), {"i": note_id}).mappings().first()
    if r is None:
        raise NotFound()
    return r


def _via_note(min_role: str):
    """Depends() resolving the trip of a note id. Row-level security hides other people's private notes, so they are a 404 here."""
    check = require_trip(min_role).dependency

    def access(session: DbSession, note_id: uuid.UUID) -> TripAccess:
        trip_id = session.execute(text("SELECT trip_id FROM notes WHERE id = :i"), {"i": note_id}).scalar()
        if trip_id is None:
            raise NotFound()
        return check(trip_id, session)

    access.__require_trip__ = min_role
    return Depends(access)


def _check_url(url: str | None) -> None:
    if url and (problem := links.url_problem(url)):
        raise _invalid("source_url", problem)


def _check_item(session: Session, trip_id: uuid.UUID, item_id: uuid.UUID | None) -> None:
    if item_id and session.execute(text("SELECT 1 FROM itinerary_items WHERE id = :i AND trip_id = :t"), {"i": item_id, "t": trip_id}).first() is None:
        raise _invalid("item_id", "That item is not on this trip.")


@router.get("/trips/{trip_id}/notes", response_model=NotePage)
def list_notes(
    access: Annotated[TripAccess, require_trip("viewer")],
    session: DbSession,
    kind: Literal["user", "agent"] | None = None,
    pinned: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    updated_since: datetime | None = None,
) -> NotePage:
    # shortcut: the cursor is an offset (unsigned base64), as for stays; deleted notes are not returned as tombstones. Upgrade: keyset paging and a tombstone feed.
    start = decode_offset(cursor)
    rows = session.execute(
        text(
            _SELECT + "WHERE n.trip_id = :t AND (CAST(:k AS text) IS NULL OR n.kind::text = :k) AND (CAST(:p AS boolean) IS NULL OR n.pinned = :p) "
            "AND (CAST(:since AS timestamptz) IS NULL OR n.updated_at > :since) ORDER BY n.pinned DESC, n.created_at DESC, n.id LIMIT :n OFFSET :o"
        ),
        {"t": access.trip.id, "k": kind, "p": pinned, "since": updated_since, "n": limit + 1, "o": start},
    ).mappings().all()  # private notes of other users are filtered by row-level security
    more = len(rows) > limit
    return NotePage(items=[_out(r) for r in rows[:limit]], next_cursor=encode_offset(start + limit) if more else None, has_more=more)


@router.post("/trips/{trip_id}/notes", response_model=Note, status_code=201)
def create_note(body: NoteIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Note:
    tid = access.trip.id
    if body.body is None:
        raise _invalid("body", "Write something.")
    _check_url(body.source_url)
    _check_item(session, tid, body.item_id)
    new_id = session.execute(
        text(
            "INSERT INTO notes (trip_id, kind, author_user_id, title, body, urls, day, itinerary_item_id, is_private, pinned) "
            "VALUES (:t, 'user', :u, :title, :body, :urls, :day, :item, COALESCE(:priv, false), COALESCE(:pin, false)) RETURNING id"
        ),
        {"t": tid, "u": user.id, "title": body.title or "", "body": body.body, "urls": [body.source_url] if body.source_url else [], "day": body.day, "item": body.item_id, "priv": body.is_private, "pin": body.pinned},
    ).scalar_one()
    record(session, tid, user.id, "added", "note", new_id, "added a note", private=bool(body.is_private))
    out = _out(_row(session, new_id))
    response.headers["Location"] = f"/v1/notes/{new_id}"
    response.headers["ETag"] = f'"{out.version}"'
    return out


@router.patch("/notes/{note_id}", response_model=Note)
def update_note(note_id: uuid.UUID, body: NoteIn, request: Request, access: Annotated[TripAccess, _via_note("editor")], user: CurrentUser, session: DbSession, response: Response) -> Note:
    version = resolve_version(request, body.version)
    tid, sent = access.trip.id, body.model_fields_set - {"version"}
    cur = _row(session, note_id)
    if cur["author_user_id"] != user.id and access.role != "owner":
        raise ApiError(403, "insufficient_role", "Only the author or the trip owner can change this note.")
    if cur["kind"] == "agent" and sent - {"pinned"}:
        raise _invalid(sorted(sent - {"pinned"})[0], "Found notes can be pinned, not edited.")
    if "is_private" in sent and cur["author_user_id"] != user.id:
        raise ApiError(403, "insufficient_role", "Only the author can make a note private or shared.")
    for f in ("body", "title", "pinned", "is_private"):
        if f in sent and getattr(body, f) is None:
            raise _invalid(f, "That cannot be empty.")
    sets: dict = {f: getattr(body, f) for f in ("title", "body", "pinned", "is_private", "day") if f in sent}
    if "item_id" in sent:
        _check_item(session, tid, body.item_id)
        sets["itinerary_item_id"] = body.item_id
    if "source_url" in sent:
        _check_url(body.source_url)
        sets["urls"] = [body.source_url] if body.source_url else []
    if sets:
        assignments = ", ".join(f"{c} = :{c}" for c in sets)  # the column names come from the whitelist above, never from the client
        row = session.execute(text(f"UPDATE notes SET {assignments} WHERE id = :id AND trip_id = :t AND version = :v RETURNING id"), {**sets, "id": note_id, "t": tid, "v": version}).first()
    else:  # nothing to change still honors the version
        row = session.execute(text("SELECT id FROM notes WHERE id = :id AND trip_id = :t AND version = :v"), {"id": note_id, "t": tid, "v": version}).first()
    if row is None:
        raise version_conflict(_out(cur).model_dump(mode="json"))
    if sets:
        record(session, tid, user.id, "updated", "note", note_id, "changed a note", private=cur["is_private"] or bool(sets.get("is_private")))
    out = _out(_row(session, note_id))
    response.headers["ETag"] = f'"{out.version}"'
    return out


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(note_id: uuid.UUID, access: Annotated[TripAccess, _via_note("editor")], user: CurrentUser, session: DbSession) -> Response:
    cur = _row(session, note_id)
    if cur["author_user_id"] != user.id and access.role != "owner":
        raise ApiError(403, "insufficient_role", "Only the author or the trip owner can delete this note.")
    session.execute(text("DELETE FROM notes WHERE id = :i AND trip_id = :t"), {"i": note_id, "t": access.trip.id})
    record(session, access.trip.id, user.id, "removed", "note", note_id, "removed a note", private=cur["is_private"])
    return Response(status_code=204)


@router.get("/notes/{note_id}/evidence", response_model=Evidence)
def get_evidence(note_id: uuid.UUID, access: Annotated[TripAccess, _via_note("viewer")], session: DbSession) -> Evidence:
    r = _row(session, note_id)
    return Evidence(note_id=r["id"], run_id=r["run_id"], sources=_sources(r), excerpt=None, checked_at=r["checked_at"], stale=r["stale"])
