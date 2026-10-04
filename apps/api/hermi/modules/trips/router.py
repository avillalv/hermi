# ruff: noqa: E501  (long comments and docstrings)
"""Trip routes: GET /v1/trips and POST /v1/trips (04 section 5.4). The rest of the section ships with WF-019.1."""

import base64
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, Response

from hermi.deps import CurrentUser, DbSession
from hermi.errors import ApiError
from hermi.modules.trips import repo
from hermi.modules.trips.schemas import Trip, TripCreate, TripDestinationOut, TripPage, TripSummary

router = APIRouter(tags=["trips"])


def _encode(at: datetime, id_: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{at.isoformat()}|{id_}".encode()).decode()


def _decode(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        at, _, id_ = base64.urlsafe_b64decode(cursor.encode()).decode().partition("|")
        return datetime.fromisoformat(at), uuid.UUID(id_)
    except ValueError:
        raise ApiError(400, "bad_request", "That page cursor is not valid. Start from the first page.") from None


@router.get("/trips", response_model=TripPage)
def list_trips(
    user: CurrentUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
    status: Annotated[str | None, Query(pattern="^(planning|booked|done|archived)$")] = None,
) -> TripPage:
    # shortcut: no include=joined,owned or updated_since filters and no ETag yet (WF-019.1); both roles are always listed.
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
    limit = repo.active_trip_limit(session, user.id)
    if repo.count_active_owned(session, user.id) >= limit:
        raise ApiError(
            402,
            "limit_reached",
            f"You have {limit} active trips. Archive one to make room, or upgrade.",
            extra={
                "paywall": {
                    "trigger": "third_trip",
                    "reason": "trip_limit",
                    "offer_url": "/v1/paywall/offer?reason=trip_limit",
                    "free_path": "Archive a trip or join trips other people plan",
                }
            },
        )
    mine = repo.my_person_ids(session, user.id)
    people = body.traveler_ids if body.traveler_ids is not None else mine[:1]
    if not set(people) <= set(mine):
        raise ApiError(
            422,
            "validation_failed",
            "One of the travelers is not yours to add.",
            extra={"errors": [{"field": "traveler_ids", "code": "invalid", "message": "Use travelers from your own list."}]},
        )
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
        [d.model_dump(exclude_none=True) for d in body.destinations],
        list(dict.fromkeys(people)),
    )
    response.headers["Location"] = f"/v1/trips/{trip.id}"
    return Trip(
        **{k: getattr(trip, k) for k in Trip.model_fields if k not in ("destinations", "my_role")},
        destinations=[TripDestinationOut.model_validate(d) for d in repo.destinations_of(session, trip.id)],
        my_role="owner",
    )
