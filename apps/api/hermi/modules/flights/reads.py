# ruff: noqa: E501  (long SQL strings)
"""Cached fare reads for a trip (04 section 5.8): best, summary, price history, the date grid, and hiding or flagging one fare.

Every read is over `trip_fare_links`, so nothing here calls a provider or touches credits. Sorting is by the listed keys only;
no provider or commission input ever changes the order.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import text

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import NotFound
from hermi.modules.collaboration.activity import record
from hermi.modules.flights.fare_view import FARE_COLUMNS, FARE_FROM, fare_of
from hermi.modules.flights.schemas import (
    MAX_DAYS_OUT,
    DateGridCell,
    Fare,
    FarePatch,
    Money,
    PriceHistory,
    PricePoint,
    RouteSummary,
)

router = APIRouter(tags=["flights"])

VISIBLE = "NOT l.hidden AND NOT l.suspect"
_ORDER = {  # whitelist: the value is interpolated into SQL, so it never comes from the client
    "price": "o.price_total_minor, o.observed_at DESC, l.id",
    "duration": "COALESCE(o.duration_out_min, 100000) + COALESCE(o.duration_back_min, 0), o.price_total_minor, l.id",
    "stops": "COALESCE(o.stops_out, 99) + COALESCE(o.stops_back, 0), o.price_total_minor, l.id",
}


def _check_route(session, trip_id: uuid.UUID, route_id: uuid.UUID) -> None:
    if session.execute(text("SELECT 1 FROM flight_routes WHERE id = :r AND trip_id = :t"), {"r": route_id, "t": trip_id}).first() is None:
        raise NotFound()


@router.get("/trips/{trip_id}/flights/best", response_model=list[Fare])
def best_fares(
    access: Annotated[TripAccess, require_trip("viewer")],
    session: DbSession,
    route_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    include_hidden: bool = False,
    sort: Literal["price", "duration", "stops"] = "price",
) -> list[Fare]:
    # Ties on price go to the newest sighting (observed_at DESC), then the link id.
    rows = session.execute(
        text(
            f"""SELECT {FARE_COLUMNS} FROM {FARE_FROM}
                 WHERE l.trip_id = :t AND (CAST(:r AS uuid) IS NULL OR l.route_id = :r) AND (:all OR ({VISIBLE}))
                 ORDER BY {_ORDER[sort]} LIMIT :n"""
        ),
        {"t": access.trip.id, "r": route_id, "all": include_hidden, "n": limit},
    ).mappings()
    return [fare_of(r) for r in rows]


@router.get("/trips/{trip_id}/flights/summary", response_model=list[RouteSummary])
def summary(request: Request, response: Response, access: Annotated[TripAccess, require_trip("viewer")], session: DbSession):
    trip = access.trip.id
    routes = session.execute(text("SELECT id, last_checked_at FROM flight_routes WHERE trip_id = :t ORDER BY created_at, id"), {"t": trip}).all()
    cheapest = {
        r["route_id"]: (r["n"], fare_of(r))
        for r in session.execute(
            text(
                f"""SELECT * FROM (SELECT {FARE_COLUMNS}, row_number() OVER w AS rn, count(*) OVER (PARTITION BY l.route_id) AS n
                      FROM {FARE_FROM} WHERE l.trip_id = :t AND {VISIBLE}
                     WINDOW w AS (PARTITION BY l.route_id ORDER BY o.price_total_minor, o.observed_at DESC, l.id)) x WHERE rn = 1"""
            ),
            {"t": trip},
        ).mappings()
    }
    chosen = {}
    for r in session.execute(
        text(
            f"""SELECT {FARE_COLUMNS} FROM chosen_flights c
                  JOIN trip_fare_links l ON l.route_id = c.route_id AND l.observation_id = c.observation_id
                  JOIN fare_observations o ON o.id = l.observation_id WHERE c.trip_id = :t"""
        ),
        {"t": trip},
    ).mappings():
        chosen[r["route_id"]] = r
    out = []
    for route_id, checked in routes:
        count, top = cheapest.get(route_id, (0, None))
        pick = chosen.get(route_id)
        latest = None
        if pick:  # the newest matching sighting of the chosen flight: same airports, dates, cabin and party
            row = session.execute(
                text(
                    f"""SELECT {FARE_COLUMNS} FROM {FARE_FROM}
                         WHERE l.route_id = :r AND {VISIBLE} AND o.origin = :o AND o.destination = :d AND o.depart_date = :dep
                           AND o.return_date IS NOT DISTINCT FROM :ret AND o.cabin = CAST(:cab AS cabin_class) AND o.adults = :a AND o.children = :k
                         ORDER BY o.observed_at DESC, o.price_total_minor LIMIT 1"""
                ),
                {"r": route_id, "o": pick["origin"], "d": pick["destination"], "dep": pick["depart_date"], "ret": pick["return_date"], "cab": pick["cabin"], "a": pick["adults"], "k": pick["children"]},
            ).mappings().first()
            latest = fare_of(row) if row else None
        out.append(RouteSummary(route_id=route_id, cheapest=top, last_checked_at=checked, fare_count=count, chosen=fare_of(pick) if pick else None, chosen_latest=latest))
    # the age label moves with the clock, so it stays out of the tag
    body = "".join(o.model_dump_json(exclude={"cheapest": {"age_label"}, "chosen": {"age_label"}, "chosen_latest": {"age_label"}}) for o in out)
    etag = '"' + hashlib.sha256(body.encode()).hexdigest()[:16] + '"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return out


@router.get("/trips/{trip_id}/routes/{route_id}/price-history", response_model=PriceHistory)
def price_history(route_id: uuid.UUID, access: Annotated[TripAccess, require_trip("viewer")], session: DbSession) -> PriceHistory:
    """Daily minimum per source in the route's main currency.

    shortcut: typical range and price level stay empty until the live provider writes `route_price_insights` (WF-031);
    the Google points are always empty for cached routes."""
    _check_route(session, access.trip.id, route_id)
    rows = session.execute(
        text(
            f"""WITH cur AS (SELECT o.currency FROM {FARE_FROM} WHERE l.route_id = :r AND {VISIBLE} GROUP BY o.currency ORDER BY count(*) DESC, o.currency LIMIT 1)
                SELECT (o.observed_at AT TIME ZONE 'UTC')::date AS day, o.source, min(o.price_total_minor) AS minor, o.currency
                  FROM {FARE_FROM} JOIN cur ON cur.currency = o.currency
                 WHERE l.route_id = :r AND {VISIBLE} GROUP BY 1, 2, o.currency ORDER BY 1, 2"""
        ),
        {"r": route_id},
    ).mappings().all()
    currency = rows[0]["currency"] if rows else session.execute(text("SELECT home_currency FROM trips WHERE id = :t"), {"t": access.trip.id}).scalar_one()
    return PriceHistory(currency=currency, points=[PricePoint(day=r["day"], source=r["source"], price=Money(amount_minor=r["minor"], currency=currency)) for r in rows])


@router.get("/trips/{trip_id}/routes/{route_id}/date-grid", response_model=list[DateGridCell])
def date_grid(route_id: uuid.UUID, access: Annotated[TripAccess, require_trip("viewer")], session: DbSession) -> list[DateGridCell]:
    """Cheapest fare per departure and return pair, from today to 330 days out."""
    _check_route(session, access.trip.id, route_id)
    today = datetime.now(UTC).date()
    rows = session.execute(
        text(
            f"""SELECT DISTINCT ON (o.depart_date, o.return_date) l.id, o.depart_date, o.return_date, o.price_total_minor, o.currency, o.source, o.observed_at
                  FROM {FARE_FROM}
                 WHERE l.route_id = :r AND {VISIBLE} AND o.depart_date BETWEEN :a AND :b
                 ORDER BY o.depart_date, o.return_date NULLS FIRST, o.price_total_minor, o.observed_at DESC, l.id"""
        ),
        {"r": route_id, "a": today, "b": today + timedelta(days=MAX_DAYS_OUT)},
    ).mappings()
    return [
        DateGridCell(fare_id=r["id"], depart_date=r["depart_date"], return_date=r["return_date"], price=Money(amount_minor=r["price_total_minor"], currency=r["currency"]), source=r["source"], observed_at=r["observed_at"])
        for r in rows
    ]


@router.patch("/trips/{trip_id}/fares/{fare_id}", response_model=Fare)
def patch_fare(fare_id: uuid.UUID, body: FarePatch, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession) -> Fare:
    """Hides or flags a fare for this trip only. The shared observation is never changed or deleted."""
    done = session.execute(
        text("UPDATE trip_fare_links SET hidden = COALESCE(:h, hidden), suspect = COALESCE(:s, suspect) WHERE id = :i AND trip_id = :t RETURNING id"),
        {"h": body.hidden, "s": body.suspect, "i": fare_id, "t": access.trip.id},
    ).first()
    if done is None:
        raise NotFound()
    row = session.execute(text(f"SELECT {FARE_COLUMNS} FROM {FARE_FROM} WHERE l.id = :i"), {"i": fare_id}).mappings().one()
    record(session, access.trip.id, user.id, "updated", "fare", fare_id, "hid or flagged a fare")
    return fare_of(row)
