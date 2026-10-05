# ruff: noqa: E501  (long SQL strings)
"""The chosen flight of a route and "Mark as booked" with the price paid (04 section 5.8).

A choice copies the fare into `chosen_flights`, so it survives pruning of the shared observation. What the traveler paid is private:
it is never written to the activity feed and no read here returns it (the booked-fare read arrives with WF-075).
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.collaboration.activity import record
from hermi.modules.flights.flight_choice import (
    ChoiceError,
    ChosenFlight,
    check_choice,
    flight_dates,
    trip_end,
)
from hermi.modules.flights.reads import _check_route
from hermi.modules.flights.schemas import BookedIn, ChoiceIn, MoneyIn
from hermi.modules.trips.router import full_trip
from hermi.modules.trips.schemas import Trip

router = APIRouter(tags=["flights"])


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "validation_failed", message, extra={"errors": [{"field": field, "code": "invalid", "message": message}]})


def _check_paid(session: Session, paid: MoneyIn | None, booked_at: datetime | None, fare_currency: str) -> None:
    """The currency must be the fare's own or have a rate (EUR is the base), so the drop alert can compare later. A booking date is never in the future."""
    if paid is not None and paid.currency not in ("EUR", fare_currency) and session.execute(text("SELECT 1 FROM fx_rates WHERE currency = :c"), {"c": paid.currency}).first() is None:
        raise _invalid("paid.currency", "We do not have rates for that currency yet. Pick another one.")
    # the 1 day of slack covers a traveler whose clock is ahead of UTC
    if booked_at is not None and booked_at > datetime.now(UTC) + timedelta(days=1):
        raise _invalid("booked_at", "The booking date cannot be in the future.")


def _sync_dates(session: Session, trip_id: uuid.UUID) -> None:
    """A trip with no dates takes them from its chosen flights; dates the traveler set stay as they are."""
    rows = session.execute(text("SELECT route_id, origin, destination, depart_date, return_date, airlines FROM chosen_flights WHERE trip_id = :t"), {"t": trip_id}).all()
    dates = flight_dates([ChosenFlight(*r) for r in rows])
    if dates is not None:
        session.execute(
            text("UPDATE trips SET start_date = :s, end_date = :e WHERE id = :t AND start_date IS NULL AND end_date IS NULL"),
            {"s": dates.start, "e": trip_end(dates, None), "t": trip_id},
        )


def _trip(session: Session, access: TripAccess, user: CurrentUser, response: Response) -> Trip:
    session.refresh(access.trip)
    response.headers["ETag"] = f'"{access.trip.version}"'
    return full_trip(session, access.trip, access.role, user.id)


@router.put("/trips/{trip_id}/routes/{route_id}/choice", response_model=Trip)
def choose(route_id: uuid.UUID, body: ChoiceIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Trip:
    """Choose a fare for the route. Choosing the same fare again changes nothing (idempotent). Another flight replaces the choice and drops any booking of the old one.
    `paid` or `booked_at` also marks the flight booked."""
    _check_route(session, access.trip.id, route_id)
    fare = session.execute(
        text("SELECT l.route_id, l.observation_id, o.depart_date, o.currency FROM trip_fare_links l JOIN fare_observations o ON o.id = l.observation_id WHERE l.id = :f AND l.trip_id = :t"),
        {"f": body.fare_id, "t": access.trip.id},
    ).first()
    if fare is None:
        raise NotFound()
    try:
        check_choice(fare.route_id, route_id, fare.depart_date, datetime.now(UTC).date())
    except ChoiceError as e:
        raise _invalid("fare_id", str(e)) from None
    _check_paid(session, body.paid, body.booked_at, fare.currency)
    booked = body.paid is not None or body.booked_at is not None
    session.execute(
        text(
            """INSERT INTO chosen_flights (trip_id, route_id, observation_id, origin, destination, depart_date, return_date, price_total_minor, currency, airlines,
                 flight_numbers, adults, children, source, observed_at, deep_link_template, cabin, chosen_by, booked_at, booked_by, paid_minor, paid_currency, paid_source)
               SELECT :t, :r, o.id, o.origin, o.destination, o.depart_date, o.return_date, o.price_total_minor, o.currency, ARRAY(SELECT unnest(o.airlines) ORDER BY 1),
                 o.flight_numbers, o.adults, o.children, o.source, o.observed_at, o.deep_link_template, o.cabin, :u,
                 CASE WHEN :booked THEN COALESCE(CAST(:at AS timestamptz), now()) END, CASE WHEN :booked THEN :u END, CAST(:pm AS bigint), CAST(:pc AS text), CASE WHEN CAST(:pm AS bigint) IS NOT NULL THEN 'manual' END
                 FROM fare_observations o WHERE o.id = :obs
               ON CONFLICT (route_id) DO UPDATE SET observation_id = EXCLUDED.observation_id, origin = EXCLUDED.origin, destination = EXCLUDED.destination,
                 depart_date = EXCLUDED.depart_date, return_date = EXCLUDED.return_date, price_total_minor = EXCLUDED.price_total_minor, currency = EXCLUDED.currency,
                 airlines = EXCLUDED.airlines, flight_numbers = EXCLUDED.flight_numbers, adults = EXCLUDED.adults, children = EXCLUDED.children, source = EXCLUDED.source,
                 observed_at = EXCLUDED.observed_at, deep_link_template = EXCLUDED.deep_link_template, cabin = EXCLUDED.cabin, chosen_by = EXCLUDED.chosen_by, chosen_at = now(),
                 booked_at = CASE WHEN (chosen_flights.observation_id IS NOT DISTINCT FROM EXCLUDED.observation_id AND NOT :booked) THEN chosen_flights.booked_at ELSE EXCLUDED.booked_at END,
                 booked_by = CASE WHEN (chosen_flights.observation_id IS NOT DISTINCT FROM EXCLUDED.observation_id AND NOT :booked) THEN chosen_flights.booked_by ELSE EXCLUDED.booked_by END,
                 paid_minor = CASE WHEN (chosen_flights.observation_id IS NOT DISTINCT FROM EXCLUDED.observation_id AND NOT :booked) THEN chosen_flights.paid_minor ELSE EXCLUDED.paid_minor END,
                 paid_currency = CASE WHEN (chosen_flights.observation_id IS NOT DISTINCT FROM EXCLUDED.observation_id AND NOT :booked) THEN chosen_flights.paid_currency ELSE EXCLUDED.paid_currency END,
                 paid_source = CASE WHEN (chosen_flights.observation_id IS NOT DISTINCT FROM EXCLUDED.observation_id AND NOT :booked) THEN chosen_flights.paid_source ELSE EXCLUDED.paid_source END,
                 last_drop_notified_at = CASE WHEN (chosen_flights.observation_id IS NOT DISTINCT FROM EXCLUDED.observation_id AND NOT :booked) THEN chosen_flights.last_drop_notified_at END,
                 last_drop_notified_minor = CASE WHEN (chosen_flights.observation_id IS NOT DISTINCT FROM EXCLUDED.observation_id AND NOT :booked) THEN chosen_flights.last_drop_notified_minor END"""
        ),
        {
            "t": access.trip.id, "r": route_id, "obs": fare.observation_id, "u": user.id, "booked": booked, "at": body.booked_at,
            "pm": body.paid.amount_minor if body.paid else None, "pc": body.paid.currency if body.paid else None,
        },
    )
    _sync_dates(session, access.trip.id)
    record(session, access.trip.id, user.id, "chose", "flight", route_id, "chose a flight")
    if booked:
        record(session, access.trip.id, user.id, "booked", "flight", route_id, "marked a flight as booked")
    return _trip(session, access, user, response)


@router.delete("/trips/{trip_id}/routes/{route_id}/choice", response_model=Trip)
def clear_choice(route_id: uuid.UUID, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Trip:
    """Clears the choice. The trip's dates stay as they are."""
    _check_route(session, access.trip.id, route_id)
    if session.execute(text("DELETE FROM chosen_flights WHERE route_id = :r AND trip_id = :t RETURNING 1"), {"r": route_id, "t": access.trip.id}).first():
        record(session, access.trip.id, user.id, "removed", "flight", route_id, "cleared the chosen flight")
    return _trip(session, access, user, response)


@router.post("/trips/{trip_id}/routes/{route_id}/choice/booked", response_model=Trip)
def mark_booked(route_id: uuid.UUID, body: BookedIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Trip:
    """Mark the chosen flight as booked, with what was paid when sent. `booked: false` clears all of it.
    `paid: null` clears only the amount; leaving `paid` out keeps it."""
    _check_route(session, access.trip.id, route_id)
    current = session.execute(text("SELECT currency FROM chosen_flights WHERE route_id = :r AND trip_id = :t"), {"r": route_id, "t": access.trip.id}).scalar()
    if current is None:
        raise ApiError(409, "state_conflict", "Choose a flight first, then mark it as booked.")
    if not body.booked:
        session.execute(
            text("UPDATE chosen_flights SET booked_at = NULL, booked_by = NULL, paid_minor = NULL, paid_currency = NULL, paid_source = NULL WHERE route_id = :r"),
            {"r": route_id},
        )
        record(session, access.trip.id, user.id, "updated", "flight", route_id, "marked a flight as not booked")
        return _trip(session, access, user, response)
    _check_paid(session, body.paid, body.booked_at, current)
    set_paid = "paid" in body.model_fields_set
    session.execute(
        text(
            """UPDATE chosen_flights SET booked_at = COALESCE(CAST(:at AS timestamptz), booked_at, now()), booked_by = :u,
                 paid_minor = CASE WHEN :set THEN CAST(:pm AS bigint) ELSE paid_minor END, paid_currency = CASE WHEN :set THEN CAST(:pc AS text) ELSE paid_currency END,
                 paid_source = CASE WHEN :set THEN CASE WHEN CAST(:pm AS bigint) IS NOT NULL THEN 'manual' END ELSE paid_source END,
                 last_drop_notified_at = CASE WHEN :set THEN NULL ELSE last_drop_notified_at END, last_drop_notified_minor = CASE WHEN :set THEN NULL ELSE last_drop_notified_minor END
               WHERE route_id = :r"""
        ),
        {"r": route_id, "at": body.booked_at, "u": user.id, "set": set_paid, "pm": body.paid.amount_minor if body.paid else None, "pc": body.paid.currency if body.paid else None},
    )
    record(session, access.trip.id, user.id, "booked", "flight", route_id, "marked a flight as booked")
    return _trip(session, access, user, response)
