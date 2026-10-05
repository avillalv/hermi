# ruff: noqa: E501  (long comments and docstrings)
"""Trip routes (04 section 5.4) and destination routes (5.5).

Archive is PATCH status=archived (owner). Duplicate is POST /trips/{id}/duplicate, which 04 lacks (PROGRESS risk note, WF-019.1).
"""

import base64
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.billing import service as billing
from hermi.modules.trips import repo
from hermi.modules.trips.schemas import (
    DestinationIn,
    DestinationOrder,
    DestinationPatch,
    Trip,
    TripCreate,
    TripDestinationOut,
    TripDuplicate,
    TripPage,
    TripSummary,
    TripUpdate,
)
from hermi.security.preconditions import resolve_version, version_conflict

router = APIRouter(tags=["trips"])

MAX_DESTINATIONS = 12
OWNER_ONLY_FIELDS = {"status", "ai_enabled", "editors_can_invite"}
COPIED_DESTINATION_FIELDS = ("name", "region", "country", "country_code", "kind", "lat", "lon", "timezone", "bbox", "geoapify_place_id")


def _encode(at: datetime, id_: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{at.isoformat()}|{id_}".encode()).decode()


def _decode(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        at, _, id_ = base64.urlsafe_b64decode(cursor.encode()).decode().partition("|")
        return datetime.fromisoformat(at), uuid.UUID(id_)
    except ValueError:
        raise ApiError(400, "bad_request", "That page cursor is not valid. Start from the first page.") from None


def _full(session: Session, trip, role: str) -> Trip:
    return Trip(
        **{k: getattr(trip, k) for k in Trip.model_fields if k not in ("destinations", "my_role")},
        destinations=[TripDestinationOut.model_validate(d) for d in repo.destinations_of(session, trip.id)],
        my_role=role,
    )


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "validation_failed", message, extra={"errors": [{"field": field, "code": "invalid", "message": message}]})


def _check_trip_limit(session: Session, user_id: uuid.UUID) -> None:
    billing.require_active_trip_slot(session, user_id)


def _my_travelers(session: Session, user_id: uuid.UUID, asked: list[uuid.UUID] | None) -> list[uuid.UUID]:
    mine = repo.my_person_ids(session, user_id)
    people = asked if asked is not None else mine[:1]
    if not set(people) <= set(mine):
        raise _invalid("traveler_ids", "One of the travelers is not yours to add.")
    return list(dict.fromkeys(people))


@router.get("/trips", response_model=TripPage)
def list_trips(
    user: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
    status: Annotated[str | None, Query(pattern="^(planning|booked|done|archived)$")] = None,
) -> TripPage:
    # shortcut: no include=joined,owned or updated_since filters and no ETag yet; both roles are always listed.
    rows = repo.list_summaries(session, user.id, limit=limit, after=_decode(cursor) if cursor else None, status=status)
    page = rows[:limit]
    more = len(rows) > limit
    return TripPage(
        items=[TripSummary(**r) for r in page],
        next_cursor=_encode(page[-1]["updated_at"], page[-1]["id"]) if more else None,
        has_more=more,
    )


@router.post("/trips", response_model=Trip, status_code=201)
def create_trip(body: TripCreate, user: CurrentUser, session: DbSession, response: Response) -> Trip:
    _check_trip_limit(session, user.id)
    people = _my_travelers(session, user.id, body.traveler_ids)
    trip = repo.create_trip(
        session,
        user.id,
        {
            "name": body.name,
            "start_date": body.start_date,
            "end_date": body.end_date,
            "notes": body.notes,
            "home_currency": body.home_currency or repo.user_home_currency(session, user.id),
        },
        [d.model_dump(exclude_none=True, exclude={"id"}) for d in body.destinations],
        people,
    )
    response.headers["Location"] = f"/v1/trips/{trip.id}"
    return _full(session, trip, "owner")


@router.get("/trips/{trip_id}", response_model=Trip)
def get_trip(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession, response: Response) -> Trip:
    response.headers["ETag"] = f'"{access.trip.version}"'
    return _full(session, access.trip, access.role)


@router.patch("/trips/{trip_id}", response_model=Trip)
def update_trip(
    body: TripUpdate,
    request: Request,
    access: Annotated[TripAccess, require_trip("editor")],
    user: CurrentUser,
    session: DbSession,
    response: Response,
) -> Trip:
    trip, sent = access.trip, body.model_fields_set
    if access.role != "owner" and sent & OWNER_ONLY_FIELDS:
        raise ApiError(403, "insufficient_role", "You do not have permission to do that.")
    version = resolve_version(request, body.version)
    if body.status in ("planning", "booked") and trip.status in ("done", "archived"):
        _check_trip_limit(session, trip.owner_user_id)  # un-archiving takes an active slot again
    values: dict = {"updated_at": text("now()")}
    for f in ("name", "notes", "home_currency", "status", "ai_enabled", "editors_can_invite"):
        if f in sent:
            values[f] = getattr(body, f)
    if "status" in sent:
        values["archived_at"] = text("now()") if body.status == "archived" else None
    start = body.start_date if "start_date" in sent else trip.start_date
    end = body.end_date if "end_date" in sent else trip.end_date
    if (start is None) != (end is None):
        raise _invalid("start_date", "Give both dates, or neither.")
    if start and end and end < start:
        raise _invalid("end_date", "The end date must be on or after the start date.")
    if sent & {"start_date", "end_date"}:
        values["start_date"], values["end_date"] = start, end
    people = _my_travelers(session, user.id, body.traveler_ids) if body.traveler_ids is not None else None
    if not repo.update_trip(session, trip, version, values):
        raise version_conflict(_full(session, trip, access.role).model_dump(mode="json"))
    # shortcut: changing dates does not re-derive itinerary_days yet; the itinerary module (WF-032) owns days and hooks in here.
    if body.destinations is not None and not repo.replace_destinations(
        session, trip.id, [d.model_dump(exclude_unset=True) for d in body.destinations]
    ):
        raise _invalid("destinations", "One of the destinations is not part of this trip.")
    if people is not None:
        repo.sync_my_travelers(session, trip.id, user.id, people)
    response.headers["ETag"] = f'"{trip.version}"'
    return _full(session, trip, access.role)


@router.delete("/trips/{trip_id}", status_code=204)
def delete_trip(access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> Response:
    repo.trash_trip(session, access.trip.id)
    return Response(status_code=204)


@router.post("/trips/{trip_id}/restore", response_model=Trip)
def restore_trip(access: Annotated[TripAccess, require_trip("owner", trashed=True)], session: DbSession) -> Trip:
    if not repo.in_trash_window(session, access.trip.id):
        raise NotFound()  # past 30 days the purge job is about to remove it
    if access.trip.status in ("planning", "booked"):
        _check_trip_limit(session, access.trip.owner_user_id)  # a restored active trip takes a slot again
    repo.restore_trip(session, access.trip)
    return _full(session, access.trip, "owner")


@router.post("/trips/{trip_id}/duplicate", response_model=Trip, status_code=201)
def duplicate_trip(
    access: Annotated[TripAccess, require_trip("owner")],
    user: CurrentUser,
    session: DbSession,
    response: Response,
    body: TripDuplicate | None = None,
) -> Trip:
    """F-TRP-6: a new trip owned by the caller. Never copies members, notes or agent output.

    shortcut: only destinations are copied. Itinerary items, lodging candidates and the checklist follow when their modules
    exist (WF-032, WF-040, WF-044)."""
    body = body or TripDuplicate()
    src = access.trip
    _check_trip_limit(session, user.id)
    start = end = None
    if body.start_date is not None:
        if not (src.start_date and src.end_date):
            raise _invalid("start_date", "The trip you are copying has no dates to shift.")
        start, end = body.start_date, body.start_date + (src.end_date - src.start_date)
    trip = repo.create_trip(
        session,
        user.id,
        {"name": body.name or f"{src.name} (copy)"[:120], "start_date": start, "end_date": end, "notes": "", "home_currency": src.home_currency},
        [{k: getattr(d, k) for k in COPIED_DESTINATION_FIELDS if getattr(d, k) is not None} for d in repo.destinations_of(session, src.id)],
        _my_travelers(session, user.id, None),
    )
    response.headers["Location"] = f"/v1/trips/{trip.id}"
    return _full(session, trip, "owner")


# --- Destinations (04 section 5.5) ----------------------------------------------------------------------------------


@router.get("/trips/{trip_id}/destinations", response_model=list[TripDestinationOut])
def list_destinations(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession):
    return repo.destinations_of(session, access.trip.id)


@router.post("/trips/{trip_id}/destinations", response_model=TripDestinationOut, status_code=201)
def add_destination(body: DestinationIn, access: Annotated[TripAccess, require_trip("editor")], session: DbSession):
    # shortcut: the summary and image fetch is not enqueued (info_status stays pending) until the destination job lands (WF-032),
    # and PATCH does not set the cover from the first destination image until then either (WF-032).
    # shortcut: two parallel adds can pass the cap together; lock the trip row (SELECT ... FOR UPDATE) if that ever shows up.
    if len(repo.destinations_of(session, access.trip.id)) >= MAX_DESTINATIONS:
        raise _invalid("destinations", f"A trip can have up to {MAX_DESTINATIONS} destinations.")
    return repo.add_destination(session, access.trip.id, body.model_dump(exclude_none=True, exclude={"id"}))


@router.put("/trips/{trip_id}/destinations/order", response_model=list[TripDestinationOut])
def order_destinations(body: DestinationOrder, access: Annotated[TripAccess, require_trip("editor")], session: DbSession):
    if not repo.order_destinations(session, access.trip.id, body.ids):
        raise _invalid("ids", "Send every destination of the trip exactly once.")
    return repo.destinations_of(session, access.trip.id)


@router.patch("/trips/{trip_id}/destinations/{destination_id}", response_model=TripDestinationOut)
def update_destination(
    destination_id: uuid.UUID, body: DestinationPatch, access: Annotated[TripAccess, require_trip("editor")], session: DbSession
):
    row = repo.get_destination(session, access.trip.id, destination_id)
    if row is None:
        raise NotFound()
    for k in body.model_fields_set:
        setattr(row, k, getattr(body, k))
    session.flush()
    session.refresh(row)
    return row


@router.delete("/trips/{trip_id}/destinations/{destination_id}", status_code=204)
def delete_destination(destination_id: uuid.UUID, access: Annotated[TripAccess, require_trip("editor")], session: DbSession) -> Response:
    row = repo.get_destination(session, access.trip.id, destination_id)
    if row is None:
        raise NotFound()
    repo.remove_destination(session, row)
    return Response(status_code=204)
