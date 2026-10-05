# ruff: noqa: E501  (long SQL strings)
"""Itinerary days and items (04 section 5.10) and the ICS file export (04 section 5.29 content rules).

Every write runs through RLS (editors and the owner write, viewers cannot), and the router checks the role first, so a viewer gets 403.
`/items/{item_id}` carries no trip id: `_via_item` resolves the item's trip, then runs the same `require_trip` check as every trip route.
Items list in the order day, start time, `sort_order`, id, with no-day items last; reorder and move renumber `sort_order` from 1.
"""

import base64
import hashlib
import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.collaboration.activity import record
from hermi.modules.collaboration.schemas import Attribution
from hermi.modules.flights.schemas import Money
from hermi.modules.itinerary import ics
from hermi.modules.itinerary.schemas import (
    BulkIn,
    Category,
    Day,
    DayItemRef,
    DayUpdate,
    Item,
    ItemIn,
    ItemPage,
    ItemUpdate,
    MoveIn,
    ReorderIn,
    check_times,
)
from hermi.security.preconditions import resolve_version, version_conflict

router = APIRouter(tags=["itinerary"])

_SELECT = (
    "SELECT i.id, i.trip_id, i.title, i.day, i.start_time, i.end_time, i.category::text AS category, i.status::text AS status, i.location_name, i.address, "
    "i.lat, i.lon, i.url, i.notes, i.estimated_cost_minor, i.cost_currency::text AS cost_currency, i.sort_order, i.version, i.source, i.place_provider, "
    "i.place_id, i.place_data, i.created_by, i.created_at, i.updated_at, NULLIF(p.display_name, '') AS added_name "
    "FROM itinerary_items i LEFT JOIN trip_member_profiles p ON p.trip_id = i.trip_id AND p.user_id = i.created_by "
)
_ORDER = " ORDER BY i.day NULLS LAST, i.start_time NULLS LAST, i.sort_order, i.id"
_MAX_RANGE_DAYS = 800  # shortcut: a trip longer than this lists only its first 800 dates in GET /days (items outside still show). Upgrade: paginate days.
_COPY = ("id", "trip_id", "title", "day", "start_time", "end_time", "category", "status", "location_name", "address", "lat", "lon", "url", "notes",
         "sort_order", "version", "source", "place_provider", "place_id", "place_data", "created_at", "updated_at")


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "validation_failed", "Some fields need another look.", extra={"errors": [{"field": field, "code": "invalid", "message": message}]})


def _item(r) -> Item:
    return Item(
        **{k: r[k] for k in _COPY},
        cost=Money(amount_minor=r["estimated_cost_minor"], currency=r["cost_currency"]) if r["estimated_cost_minor"] is not None else None,
        bookable=False,  # shortcut: tickets offers (Viator match) arrive with the places and affiliate tickets
        added_by=Attribution(id=r["created_by"], display_name=r["added_name"]) if r["created_by"] else None,
    )


def _items(session: Session, trip_id: uuid.UUID, ids: list[uuid.UUID]) -> list[Item]:
    """The rows for `ids`, in the order of `ids`."""
    rows = {r["id"]: r for r in session.execute(text(_SELECT + "WHERE i.trip_id = :t AND i.id = ANY(:ids)"), {"t": trip_id, "ids": ids}).mappings()}
    return [_item(rows[i]) for i in ids if i in rows]


def _get(session: Session, trip_id: uuid.UUID, item_id: uuid.UUID) -> Item:
    found = _items(session, trip_id, [item_id])
    if not found:
        raise NotFound()
    return found[0]


def _day_items(session: Session, trip_id: uuid.UUID, day: date | None, exclude: uuid.UUID | None = None) -> list[Item]:
    rows = session.execute(
        text(_SELECT + "WHERE i.trip_id = :t AND i.day IS NOT DISTINCT FROM :d AND i.id IS DISTINCT FROM :x" + _ORDER),
        {"t": trip_id, "d": day, "x": exclude},
    ).mappings()
    return [_item(r) for r in rows]


def _via_item(min_role: str):
    """Depends() resolving the trip of an item id (404 when not visible), then the role check (403 below `min_role`)."""
    check = require_trip(min_role).dependency

    def access(session: DbSession, item_id: uuid.UUID) -> TripAccess:
        trip_id = session.execute(text("SELECT trip_id FROM itinerary_items WHERE id = :i"), {"i": item_id}).scalar()
        if trip_id is None:
            raise NotFound()
        return check(trip_id, session)

    access.__require_trip__ = min_role
    return Depends(access)


def _next_order(session: Session, trip_id: uuid.UUID, day: date | None) -> float:
    # shortcut: two parallel creates on one day can get the same sort_order; the id breaks the tie. Lock the trip row if that ever shows up.
    return session.execute(text("SELECT COALESCE(max(sort_order), 0) + 1 FROM itinerary_items WHERE trip_id = :t AND day IS NOT DISTINCT FROM :d"), {"t": trip_id, "d": day}).scalar_one()


def _insert(session: Session, trip_id: uuid.UUID, user_id: uuid.UUID, body: ItemIn, source: str | None, order: float) -> uuid.UUID:
    saved_id = None
    place_data = json.dumps(body.place.data) if body.place and body.place.data is not None else None
    if body.place is not None:
        p = body.place
        session.execute(
            text(
                """INSERT INTO saved_places (trip_id, place_provider, place_id, name, category, address, lat, lon, website, place_data, saved_by)
                   VALUES (:t, :pp, :pid, :name, :cat, :addr, :lat, :lon, :web, CAST(:pd AS jsonb), :u)
                   ON CONFLICT (trip_id, place_provider, place_id) DO NOTHING"""
            ),
            {"t": trip_id, "pp": p.provider, "pid": p.id, "name": body.title, "cat": body.category, "addr": body.address, "lat": body.lat, "lon": body.lon,
             "web": body.url, "pd": place_data, "u": user_id},
        )
        saved_id = session.execute(text("SELECT id FROM saved_places WHERE trip_id = :t AND place_provider = :pp AND place_id = :pid"), {"t": trip_id, "pp": p.provider, "pid": p.id}).scalar_one()
    return session.execute(
        text(
            """INSERT INTO itinerary_items (trip_id, day, start_time, end_time, sort_order, title, category, status, location_name, address, lat, lon, url, notes,
                   estimated_cost_minor, cost_currency, saved_place_id, place_provider, place_id, place_data, source, created_by, updated_by)
               VALUES (:t, :day, :st, :et, :ord, :title, :cat, :status, :loc, :addr, :lat, :lon, :url, :notes, :cost, :cur, :sp, :pp, :pid, CAST(:pd AS jsonb), :src, :u, :u)
               RETURNING id"""
        ),
        {
            "t": trip_id, "day": body.day, "st": body.start_time, "et": body.end_time, "ord": order, "title": body.title, "cat": body.category, "status": body.status,
            "loc": body.location_name, "addr": body.address, "lat": body.lat, "lon": body.lon, "url": body.url, "notes": body.notes,
            "cost": body.cost.amount_minor if body.cost else None, "cur": body.cost.currency if body.cost else None,
            "sp": saved_id, "pp": body.place.provider if body.place else None, "pid": body.place.id if body.place else None,
            "pd": place_data, "src": source or ("place_search" if body.place else "manual"), "u": user_id,
        },
    ).scalar_one()


# --- items ----------------------------------------------------------------------------------------------------------------


def _cursor(value: str | None) -> int:
    if not value:
        return 0
    try:
        n = int(base64.urlsafe_b64decode(value.encode()).decode())
        if n < 0 or n > 10**9:
            raise ValueError
        return n
    except ValueError:
        raise _invalid("cursor", "That page cursor is not valid.") from None


@router.get("/trips/{trip_id}/items", response_model=ItemPage)
def list_items(
    access: Annotated[TripAccess, require_trip("viewer")],
    session: DbSession,
    day: date | None = None,
    unscheduled: bool = False,
    category: Category | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    updated_since: datetime | None = None,
) -> ItemPage:
    # shortcut: the cursor is an offset (unsigned base64). A write between two page fetches can shift a row across the page edge; keyset paging if that matters.
    start = _cursor(cursor)
    rows = session.execute(
        text(
            _SELECT + """WHERE i.trip_id = :t AND (CAST(:day AS date) IS NULL OR i.day = :day) AND (NOT :uns OR i.day IS NULL)
                         AND (CAST(:cat AS text) IS NULL OR i.category::text = :cat) AND (CAST(:since AS timestamptz) IS NULL OR i.updated_at > :since)"""
            + _ORDER + " LIMIT :n OFFSET :o"
        ),
        {"t": access.trip.id, "day": day, "uns": unscheduled, "cat": category, "since": updated_since, "n": limit + 1, "o": start},
    ).mappings().all()
    more = len(rows) > limit
    nxt = base64.urlsafe_b64encode(str(start + limit).encode()).decode() if more else None
    return ItemPage(items=[_item(r) for r in rows[:limit]], next_cursor=nxt, has_more=more)


@router.post("/trips/{trip_id}/items", response_model=Item, status_code=201)
def create_item(body: ItemIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Item:
    tid = access.trip.id
    new_id = _insert(session, tid, user.id, body, None, _next_order(session, tid, body.day))
    record(session, tid, user.id, "added", "item", new_id, "added an itinerary item")
    response.headers["Location"] = f"/v1/items/{new_id}"
    item = _get(session, tid, new_id)
    response.headers["ETag"] = f'"{item.version}"'
    return item


@router.post("/trips/{trip_id}/items/bulk", response_model=list[Item], status_code=201)
def bulk_items(body: BulkIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession) -> list[Item]:
    """One transaction: any failure rolls every item back (the request transaction). The source applies to all items."""
    tid, orders, ids = access.trip.id, {}, []
    for it in body.items:
        if it.day not in orders:
            orders[it.day] = _next_order(session, tid, it.day)
        ids.append(_insert(session, tid, user.id, it, body.source, orders[it.day]))
        orders[it.day] += 1
    record(session, tid, user.id, "added", "item", None, f"added {len(ids)} itinerary items")
    return _items(session, tid, ids)


@router.get("/items/{item_id}", response_model=Item)
def get_item(item_id: uuid.UUID, access: Annotated[TripAccess, _via_item("viewer")], session: DbSession, response: Response) -> Item:
    item = _get(session, access.trip.id, item_id)
    response.headers["ETag"] = f'"{item.version}"'
    return item


_PATCHABLE = ("title", "category", "status", "day", "start_time", "end_time", "location_name", "address", "lat", "lon", "url", "notes")


@router.patch("/items/{item_id}", response_model=Item)
def update_item(
    item_id: uuid.UUID, body: ItemUpdate, request: Request, access: Annotated[TripAccess, _via_item("editor")], user: CurrentUser, session: DbSession, response: Response
) -> Item:
    version = resolve_version(request, body.version)
    tid = access.trip.id
    cur = _get(session, tid, item_id)
    sent = body.model_fields_set
    merged = {f: getattr(body, f) if f in sent else getattr(cur, f) for f in _PATCHABLE}
    try:
        check_times(merged["day"], merged["start_time"], merged["end_time"])
    except ValueError as e:
        raise _invalid("start_time", str(e)) from None
    if (merged["lat"] is None) != (merged["lon"] is None):
        raise _invalid("lat", "Send both lat and lon, or neither.")
    sets = {f: merged[f] for f in _PATCHABLE if f in sent}
    if "cost" in sent:
        sets["estimated_cost_minor"], sets["cost_currency"] = (body.cost.amount_minor, body.cost.currency) if body.cost else (None, None)
    if "day" in sent and merged["day"] != cur.day:
        sets["sort_order"] = _next_order(session, tid, merged["day"])  # a moved item goes to the end of its new day
    sets["updated_by"] = user.id
    assignments = ", ".join(f"{c} = :{c}" for c in sets)  # the column names come from the whitelist above, never from the client
    row = session.execute(
        text(f"UPDATE itinerary_items SET {assignments} WHERE id = :id AND trip_id = :t AND version = :v RETURNING id"), {**sets, "id": item_id, "t": tid, "v": version}
    ).first()
    if row is None:
        raise version_conflict(_get(session, tid, item_id).model_dump(mode="json"))
    record(session, tid, user.id, "updated", "item", item_id, "changed an itinerary item")
    item = _get(session, tid, item_id)
    response.headers["ETag"] = f'"{item.version}"'
    return item


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: uuid.UUID, request: Request, access: Annotated[TripAccess, _via_item("editor")], user: CurrentUser, session: DbSession) -> Response:
    version = resolve_version(request)
    tid = access.trip.id
    if session.execute(text("DELETE FROM itinerary_items WHERE id = :id AND trip_id = :t AND version = :v RETURNING id"), {"id": item_id, "t": tid, "v": version}).first() is None:
        raise version_conflict(_get(session, tid, item_id).model_dump(mode="json"))
    record(session, tid, user.id, "removed", "item", item_id, "removed an itinerary item")
    return Response(status_code=204)


def _renumber(session: Session, tid: uuid.UUID, order: list[Item]) -> None:
    """sort_order = position from 1, written only where it differs (so an untouched row keeps its version)."""
    for pos, it in enumerate(order, start=1):
        if it.sort_order != pos:
            session.execute(text("UPDATE itinerary_items SET sort_order = :o WHERE id = :i AND trip_id = :t"), {"o": float(pos), "i": it.id, "t": tid})


@router.post("/trips/{trip_id}/days/{day}/reorder", response_model=list[Item])
def reorder_day(day: date, body: ReorderIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession) -> list[Item]:
    tid = access.trip.id
    current = _day_items(session, tid, day)
    by_id = {i.id: i for i in current}
    stale = any(by_id[i].version != v for i, v in (body.version_map or {}).items() if i in by_id)
    if sorted(body.ids, key=str) != sorted(by_id, key=str) or stale:
        raise version_conflict([i.model_dump(mode="json") for i in current])  # the current order, newest versions
    _renumber(session, tid, [by_id[i] for i in body.ids])
    record(session, tid, user.id, "updated", "day", None, "reordered a day")
    return _items(session, tid, body.ids)


@router.post("/items/{item_id}/move", response_model=list[Item])
def move_item(
    item_id: uuid.UUID, body: MoveIn, request: Request, access: Annotated[TripAccess, _via_item("editor")], user: CurrentUser, session: DbSession
) -> list[Item]:
    version = resolve_version(request, body.version)
    tid = access.trip.id
    cur = _get(session, tid, item_id)
    if cur.version != version:
        raise version_conflict(cur.model_dump(mode="json"))
    target = _day_items(session, tid, body.day, exclude=item_id)
    if body.before_id is None:
        at = len(target)
    else:
        at = next((n for n, i in enumerate(target) if i.id == body.before_id), None)
        if at is None:
            raise _invalid("before_id", "That item is not on the day you are moving to.")
    start, end = cur.start_time, cur.end_time
    if body.day is None:
        start = end = None  # a time needs a day
    elif "start_time" in body.model_fields_set:
        start = body.start_time
        if start is None or (end is not None and end < start):
            end = None
    try:
        check_times(body.day, start, end)
    except ValueError as e:
        raise _invalid("start_time", str(e)) from None
    moved = session.execute(
        text("UPDATE itinerary_items SET day = :d, start_time = :st, end_time = :et, sort_order = :o, updated_by = :u WHERE id = :i AND trip_id = :t AND version = :v RETURNING id"),
        {"d": body.day, "st": start, "et": end, "o": float(at + 1), "u": user.id, "i": item_id, "t": tid, "v": version},
    ).first()
    if moved is None:
        raise version_conflict(_get(session, tid, item_id).model_dump(mode="json"))
    placed = cur.model_copy(update={"sort_order": float(at + 1)})  # already written above
    order = [*target[:at], placed, *target[at:]]
    changed = [i.id for pos, i in enumerate(order, start=1) if i.id != item_id and i.sort_order != pos]
    _renumber(session, tid, order)
    record(session, tid, user.id, "updated", "item", item_id, "moved an itinerary item")
    return _items(session, tid, [item_id, *changed])


# --- days -----------------------------------------------------------------------------------------------------------------


def _build_days(session: Session, trip, since: datetime | None = None) -> list[Day]:
    rows = {
        r["day"]: r
        for r in session.execute(
            text(
                "SELECT d.day, d.title, d.notes, d.destination_id, d.version, d.updated_at, td.name AS dest_name, td.timezone AS dest_tz "
                "FROM itinerary_days d LEFT JOIN trip_destinations td ON td.id = d.destination_id WHERE d.trip_id = :t"
            ),
            {"t": trip.id},
        ).mappings()
    }
    items: dict[date, list] = {}
    touched: set[date] = {d for d, r in rows.items() if since and r["updated_at"] > since}
    for r in session.execute(text("SELECT i.day, i.title, i.start_time, i.updated_at FROM itinerary_items i WHERE i.trip_id = :t AND i.day IS NOT NULL" + _ORDER), {"t": trip.id}).mappings():
        items.setdefault(r["day"], []).append(r)
        if since and r["updated_at"] > since:
            touched.add(r["day"])
    first_tz = session.execute(text("SELECT timezone FROM trip_destinations WHERE trip_id = :t ORDER BY position LIMIT 1"), {"t": trip.id}).scalar()
    in_range: list[date] = []
    if trip.start_date and trip.end_date:
        n = min((trip.end_date - trip.start_date).days + 1, _MAX_RANGE_DAYS)
        in_range = [trip.start_date + timedelta(days=k) for k in range(n)]
    out = []
    for d in sorted({*in_range, *rows, *items}):
        if since and d not in touched:
            continue
        r, its = rows.get(d), items.get(d, [])
        out.append(
            Day(
                day=d, title=r["title"] if r else "", notes=r["notes"] if r else "", destination_id=r["destination_id"] if r else None,
                destination_name=r["dest_name"] if r else None, timezone=(r["dest_tz"] if r else None) or first_tz,
                in_trip=d in in_range or not in_range, item_count=len(its), version=r["version"] if r else 0,
                first=DayItemRef(title=its[0]["title"], start_time=its[0]["start_time"]) if its else None,
                last=DayItemRef(title=its[-1]["title"], start_time=its[-1]["start_time"]) if its else None,
            )
        )
    return out


@router.get("/trips/{trip_id}/days", response_model=list[Day])
def list_days(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession, response: Response, updated_since: datetime | None = None) -> list[Day]:
    days = _build_days(session, access.trip, updated_since)
    response.headers["ETag"] = '"' + hashlib.sha256(json.dumps([d.model_dump(mode="json") for d in days]).encode()).hexdigest()[:16] + '"'
    return days


@router.put("/trips/{trip_id}/days/{day}", response_model=Day)
def put_day(day: date, body: DayUpdate, request: Request, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Day:
    tid, sent = access.trip.id, body.model_fields_set
    if body.destination_id is not None and session.execute(text("SELECT 1 FROM trip_destinations WHERE id = :d AND trip_id = :t"), {"d": body.destination_id, "t": tid}).first() is None:
        raise _invalid("destination_id", "That destination is not on this trip.")
    sets = {f: getattr(body, f) for f in ("title", "notes", "destination_id") if f in sent}
    exists = session.execute(text("SELECT 1 FROM itinerary_days WHERE trip_id = :t AND day = :d"), {"t": tid, "d": day}).first() is not None
    if exists:
        version = resolve_version(request, body.version)
        sets["updated_by"] = user.id
        assignments = ", ".join(f"{c} = :{c}" for c in sets)  # whitelisted column names
        row = session.execute(text(f"UPDATE itinerary_days SET {assignments} WHERE trip_id = :t AND day = :d AND version = :v RETURNING version"), {**sets, "t": tid, "d": day, "v": version}).first()
    else:
        cols = {"title": "", "notes": "", "destination_id": None, **sets, "updated_by": user.id}
        row = session.execute(
            text(f"INSERT INTO itinerary_days (trip_id, day, {', '.join(cols)}) VALUES (:t, :d, {', '.join(':' + c for c in cols)}) ON CONFLICT DO NOTHING RETURNING version"),
            {**cols, "t": tid, "d": day},
        ).first()
    current = next(d for d in _build_days(session, access.trip) if d.day == day)
    if row is None:
        raise version_conflict(current.model_dump(mode="json"))
    record(session, tid, user.id, "updated", "day", None, "changed a day")
    response.headers["ETag"] = f'"{current.version}"'
    return current


# --- ICS file -------------------------------------------------------------------------------------------------------------


@router.get("/trips/{trip_id}/itinerary.ics")
def export_ics(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession) -> Response:
    """The trip's itinerary as an iCalendar file (every tier, 01 section 5 export). Not in 04 as its own row; it uses the 5.29 content rules."""
    tid = access.trip.id
    first_tz = session.execute(text("SELECT timezone FROM trip_destinations WHERE trip_id = :t ORDER BY position LIMIT 1"), {"t": tid}).scalar()
    items = [
        dict(r)
        for r in session.execute(
            text(
                "SELECT i.id, i.day, i.start_time, i.end_time, i.title, i.location_name, i.address, i.lat, i.lon, i.url, i.notes, i.status::text AS status, i.version, i.updated_at, "
                "COALESCE(td.timezone, :tz) AS timezone FROM itinerary_items i LEFT JOIN itinerary_days d ON d.trip_id = i.trip_id AND d.day = i.day "
                "LEFT JOIN trip_destinations td ON td.id = d.destination_id WHERE i.trip_id = :t AND i.day IS NOT NULL" + _ORDER
            ),
            {"t": tid, "tz": first_tz},
        ).mappings()
    ]
    stays = [
        dict(r)
        for r in session.execute(
            text("SELECT id, title, check_in, check_out, location_name, lat, lon, version, updated_at FROM lodging_options WHERE trip_id = :t AND status = 'booked' ORDER BY check_in NULLS LAST, id"),
            {"t": tid},
        ).mappings()
    ]
    body = ics.build_calendar(name=access.trip.name, trip_id=str(tid), timezone=first_tz, items=items, stays=stays, stamp=datetime.now(UTC))
    slug = re.sub(r"[^a-z0-9]+", "-", access.trip.name.lower()).strip("-")[:60] or "trip"
    return Response(body.encode(), media_type="text/calendar; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{slug}.ics"'})
