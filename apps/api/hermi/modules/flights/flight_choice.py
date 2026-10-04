"""The flight picked for a trip. Its departure and return become the trip's dates, and stay
that way: the dates change only by choosing another flight (or clearing the choice).

With several routes (say, each traveler flying from home), the trip runs from the first chosen
departure to the last return. A one-way flight that leaves after the first departure is the way
home; a single one-way flight sets only the start. Pure logic: callers load and store the rows.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

DATES_FROM_FLIGHT = (
    "The trip's dates come from the flight you chose. To change them, choose another flight on the "
    "Flights page, or clear your choice there."
)


class ChoiceError(ValueError):
    """The fare can't be the trip's flight (it's another route's, or it has already left)."""


class DatesFromFlight(ValueError):
    """A trip edit would move its dates away from the chosen flight's."""


@dataclass(frozen=True)
class ChosenFlight:
    route_id: object
    origin: str
    destination: str
    depart_date: date
    return_date: date | None
    airlines: list[str]


@dataclass(frozen=True)
class FlightDates:
    start: date
    end: date | None
    flights: list[ChosenFlight]


def flight_dates(chosen: Iterable[ChosenFlight]) -> FlightDates | None:
    flights = sorted(chosen, key=lambda f: f.depart_date)
    if not flights:
        return None
    start = flights[0].depart_date
    ends = [f.return_date for f in flights if f.return_date is not None]
    ends += [f.depart_date for f in flights if f.return_date is None and f.depart_date > start]
    return FlightDates(start=start, end=max(ends) if ends else None, flights=flights)


def trip_end(dates: FlightDates, current_end: date | None) -> date:
    """The trip's end after applying flight dates: the flights' end, else a valid current one."""
    if dates.end is not None:
        return dates.end
    if current_end is None or current_end < dates.start:
        return dates.start
    return current_end


def check_dates(dates: FlightDates | None, start: date | None, end: date | None) -> None:
    """Refuse dates that differ from the chosen flights' (the end is free if no flight sets it)."""
    if dates is None:
        return
    if start != dates.start or (dates.end is not None and end != dates.end):
        raise DatesFromFlight(DATES_FROM_FLIGHT)


def check_choice(quote_route_id: object, route_id: object, depart_date: date, today: date) -> None:
    """Refuse a fare that belongs to another route or has already left."""
    if quote_route_id != route_id:
        raise ChoiceError("That price isn't one of this route's. Refresh the page and try again.")
    if depart_date < today:
        raise ChoiceError("That flight has already left. Choose one that departs today or later.")
