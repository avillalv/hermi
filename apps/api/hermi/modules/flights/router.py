# ruff: noqa: E501  (long SQL strings)
"""Flight routes and their cached fares (04 section 5.8). Paths sit under /trips/{trip_id} so every id route resolves through require_trip.

Fares are written by the refresh in `fares.py` (worker role). The API only reads them, through `trip_fare_links`.
"""

import base64
import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.config import NotConfigured
from hermi.db import system_session
from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.billing import service as billing
from hermi.modules.collaboration.activity import record
from hermi.modules.flights import fares as fares_service
from hermi.modules.flights.schemas import Fare, FarePage, Money, Route, RouteIn
from hermi.providers import ProviderError
from hermi.security import rate_limit
from hermi.security.preconditions import resolve_version, version_conflict

router = APIRouter(tags=["flights"])

_ROUTE = (
    "id, trip_id, label, origin_codes::text[] AS origin_codes, destination_codes::text[] AS destination_codes, trip_type::text AS trip_type, "
    "depart_from, depart_to, return_from, return_to, min_nights, max_nights, adults, children, cabin::text AS cabin, max_stops, "
    "CASE WHEN is_live THEN 'live' ELSE 'cached' END AS mode, active, version, last_checked_at, created_at, updated_at"
)
_FIELDS = ("label", "origin_codes", "destination_codes", "trip_type", "depart_from", "depart_to", "return_from", "return_to", "min_nights", "max_nights", "adults", "children", "cabin", "max_stops", "active")


def _values(body: RouteIn) -> dict:
    return {**body.model_dump(include=set(_FIELDS)), "live": body.mode == "live"}


def _get(session: Session, trip_id: uuid.UUID, route_id: uuid.UUID) -> Route:
    row = session.execute(text(f"SELECT {_ROUTE} FROM flight_routes WHERE id = :r AND trip_id = :t"), {"r": route_id, "t": trip_id}).mappings().first()
    if row is None:
        raise NotFound()
    return Route(**row)


def _others(session: Session, trip_id: uuid.UUID, exclude: uuid.UUID | None) -> tuple[int, int]:
    return tuple(  # type: ignore[return-value]
        session.execute(
            text("SELECT count(*), count(*) FILTER (WHERE is_live) FROM flight_routes WHERE trip_id = :t AND id IS DISTINCT FROM :x"),
            {"t": trip_id, "x": exclude},
        ).one()
    )


def _check(session: Session, trip_id: uuid.UUID, body: RouteIn, exclude: uuid.UUID | None = None, was_live: bool = False) -> None:
    routes, live = _others(session, trip_id, exclude)
    # shortcut: the 120 day live window (`live_window_days`) is not checked here. Live fares arrive with WF-031, which owns that gate.
    billing.require_route_limits(
        session, trip_id, origins=len(body.origin_codes), destinations=len(body.destination_codes),
        live=body.mode == "live" and not was_live, other_routes=routes, other_live=live,
    )


@router.get("/trips/{trip_id}/routes", response_model=list[Route])
def list_routes(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession) -> list[Route]:
    rows = session.execute(text(f"SELECT {_ROUTE} FROM flight_routes WHERE trip_id = :t ORDER BY created_at, id"), {"t": access.trip.id}).mappings()
    return [Route(**r) for r in rows]


@router.post("/trips/{trip_id}/routes", response_model=Route, status_code=201)
def create_route(body: RouteIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Route:
    # shortcut: two parallel creates can pass the cap together; lock the trips row (FOR UPDATE) if that ever shows up. A new route gets its first fares from POST /flights/refresh or the next refresh_cached_fares run; enqueue on create waits for the queue (WF-051).
    _check(session, access.trip.id, body)
    row = session.execute(
        text(
            f"""INSERT INTO flight_routes (trip_id, label, origin_codes, destination_codes, trip_type, depart_from, depart_to, return_from, return_to,
                  min_nights, max_nights, adults, children, cabin, max_stops, active, is_live, live_enabled_at, created_by)
                VALUES (:t, :label, :origin_codes, :destination_codes, :trip_type, :depart_from, :depart_to, :return_from, :return_to,
                  :min_nights, :max_nights, :adults, :children, :cabin, :max_stops, :active, :live, CASE WHEN :live THEN now() END, :u)
                RETURNING {_ROUTE}"""
        ),
        {**_values(body), "t": access.trip.id, "u": user.id},
    ).mappings().one()
    record(session, access.trip.id, user.id, "added", "route", row["id"], "added a flight route")
    response.headers["Location"] = f"/v1/trips/{access.trip.id}/routes/{row['id']}"
    return Route(**row)


@router.put("/trips/{trip_id}/routes/{route_id}", response_model=Route)
def update_route(route_id: uuid.UUID, body: RouteIn, request: Request, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession) -> Route:
    version = resolve_version(request, body.version)
    current = _get(session, access.trip.id, route_id)
    _check(session, access.trip.id, body, exclude=route_id, was_live=current.mode == "live")
    row = session.execute(
        text(
            f"""UPDATE flight_routes SET label = :label, origin_codes = :origin_codes, destination_codes = :destination_codes, trip_type = :trip_type,
                  depart_from = :depart_from, depart_to = :depart_to, return_from = :return_from, return_to = :return_to, min_nights = :min_nights,
                  max_nights = :max_nights, adults = :adults, children = :children, cabin = :cabin, max_stops = :max_stops, active = :active,
                  is_live = :live, live_enabled_at = CASE WHEN :live AND NOT is_live THEN now() WHEN NOT :live THEN NULL ELSE live_enabled_at END
                WHERE id = :r AND trip_id = :t AND version = :v RETURNING {_ROUTE}"""
        ),
        {**_values(body), "r": route_id, "t": access.trip.id, "v": version},
    ).mappings().first()
    if row is None:
        raise version_conflict(_get(session, access.trip.id, route_id).model_dump(mode="json"))
    record(session, access.trip.id, user.id, "updated", "route", route_id, "changed a flight route")
    return Route(**row)


@router.delete("/trips/{trip_id}/routes/{route_id}", status_code=204)
def delete_route(route_id: uuid.UUID, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession) -> Response:
    _get(session, access.trip.id, route_id)
    record(session, access.trip.id, user.id, "removed", "route", route_id, "removed a flight route")  # log before the row goes
    session.execute(text("DELETE FROM flight_routes WHERE id = :r AND trip_id = :t"), {"r": route_id, "t": access.trip.id})
    return Response(status_code=204)


def age_label(observed_at: datetime, confidence: str, now: datetime | None = None) -> str:
    """'cached 6 h ago': every fare shows how old it is (05 section 6)."""
    seconds = max(0, int(((now or datetime.now(UTC)) - observed_at).total_seconds()))
    age = "just now" if seconds < 60 else f"{seconds // 60} min ago" if seconds < 3600 else f"{seconds // 3600} h ago" if seconds < 172800 else f"{seconds // 86400} d ago"
    return f"{confidence} {age}"


def _cursor(value: str | None) -> tuple[int, uuid.UUID] | None:
    if not value:
        return None
    try:
        price, link = base64.urlsafe_b64decode(value.encode()).decode().split("|")
        return int(price), uuid.UUID(link)
    except ValueError:
        raise ApiError(422, "validation_failed", "That page cursor is not valid.") from None


@router.get("/trips/{trip_id}/routes/{route_id}/fares", response_model=FarePage)
def list_fares(
    route_id: uuid.UUID,
    access: Annotated[TripAccess, require_trip("viewer")],
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
    source: str | None = None,
    since: datetime | None = None,
) -> FarePage:
    """Every observation linked to the route, cheapest first (04 section 5.8). Cursor is the last price and link id."""
    _get(session, access.trip.id, route_id)
    after = _cursor(cursor)
    rows = session.execute(
        text(
            """SELECT l.id, l.route_id, l.hidden, l.suspect, o.source, o.confidence::text AS confidence, o.origin, o.destination, o.depart_date,
                      o.return_date, o.price_total_minor, o.currency, o.adults, o.children, o.airlines, o.stops_out, o.stops_back,
                      o.duration_out_min, o.duration_back_min, o.depart_at_local, o.flight_numbers, o.source_url, o.observed_at
                 FROM trip_fare_links l JOIN fare_observations o ON o.id = l.observation_id
                WHERE l.route_id = :r AND l.trip_id = :t
                  AND (CAST(:src AS text) IS NULL OR o.source = :src) AND (CAST(:since AS timestamptz) IS NULL OR o.observed_at >= :since)
                  AND (CAST(:p AS bigint) IS NULL OR (o.price_total_minor, l.id) > (CAST(:p AS bigint), CAST(:i AS uuid)))
                ORDER BY o.price_total_minor, l.id LIMIT :n"""
        ),
        {"r": route_id, "t": access.trip.id, "src": source, "since": since, "p": after[0] if after else None, "i": after[1] if after else None, "n": limit + 1},
    ).mappings().all()
    more, page = len(rows) > limit, rows[:limit]
    items = [
        Fare(
            id=r["id"], route_id=r["route_id"], source=r["source"], confidence=r["confidence"], origin=r["origin"], destination=r["destination"],
            depart_date=r["depart_date"], return_date=r["return_date"], price=Money(amount_minor=r["price_total_minor"], currency=r["currency"]),
            passengers=r["adults"] + r["children"], airlines=r["airlines"], stops_out=r["stops_out"], stops_back=r["stops_back"],
            duration_out_min=r["duration_out_min"], duration_back_min=r["duration_back_min"], depart_at_local=r["depart_at_local"],
            flight_numbers=r["flight_numbers"], source_url=r["source_url"], observed_at=r["observed_at"],
            age_label=age_label(r["observed_at"], r["confidence"]), suspect=r["suspect"], hidden=r["hidden"],
        )
        for r in page
    ]
    last = page[-1] if more else None
    nxt = base64.urlsafe_b64encode(f"{last['price_total_minor']}|{last['id']}".encode()).decode() if last else None
    return FarePage(items=items, next_cursor=nxt, has_more=more)


class RefreshIn(BaseModel):
    route_ids: list[uuid.UUID] | None = Field(default=None, max_length=20)


class Job(BaseModel):
    id: uuid.UUID
    status: Literal["queued", "running", "done", "failed"]
    location: str


@router.post("/trips/{trip_id}/flights/refresh", response_model=Job, status_code=202)
def refresh_flights(
    request: Request, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, body: RefreshIn | None = None
) -> Job:
    """Refreshes cached fares for the trip's routes (all active ones when `route_ids` is empty). Never spends credits.

    shortcut: runs inline, one synchronous Travelpayouts call per airport pair and month in the request. Ceiling: a slow provider holds
    the request open (at most 24 calls). Upgrade trigger: the WF-051 queue, which turns this into a queued Job."""
    ids = (body.route_ids if body else None) or None
    rows = session.execute(text("SELECT id FROM flight_routes WHERE trip_id = :t AND active ORDER BY created_at, id"), {"t": access.trip.id}).scalars().all()
    if ids is not None:
        owned = set(session.execute(text("SELECT id FROM flight_routes WHERE trip_id = :t"), {"t": access.trip.id}).scalars())
        if not set(ids) <= owned:
            raise NotFound()
        rows = list(dict.fromkeys(ids))
    rate_limit.hit(request.app.state.engine, "fare_refresh", str(access.trip.id))
    settings = request.app.state.settings
    status = "done"
    try:
        token, client = fares_service.provider_for(settings)
    except NotConfigured:
        raise ApiError(503, "provider_unavailable", "We could not check fares right now. Try again in a moment.") from None
    try:
        with system_session("fare_refresh", settings=settings, route="POST /v1/trips/{trip_id}/flights/refresh", caller=str(user.id)) as sys:
            for route_id in rows:
                try:
                    fares_service.refresh_route(sys, route_id, client=client, token=token)
                    sys.commit()
                except ProviderError:
                    sys.rollback()
                    status = "failed"
    finally:
        client.close()
    return Job(id=uuid.uuid4(), status=status, location=f"/v1/trips/{access.trip.id}/routes")
