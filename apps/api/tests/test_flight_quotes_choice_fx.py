"""Pure fare, flight choice and currency logic (no database)."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from hermi.modules.flights import fx
from hermi.modules.flights.flight_choice import (
    ChoiceError,
    ChosenFlight,
    DatesFromFlight,
    check_choice,
    check_dates,
    flight_dates,
    trip_end,
)
from hermi.modules.flights.quotes import (
    NewQuote,
    dedupe_key,
    is_duplicate,
    is_suspect,
    median_per_person,
)

NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)


def quote(price: int, **overrides) -> NewQuote:
    values = {
        "source": "travelpayouts",
        "confidence": "live",
        "origin": "LAX",
        "destination": "NRT",
        "depart_date": date(2026, 11, 5),
        "return_date": date(2026, 11, 12),
        "price_total": Decimal(price),
        "currency": "USD",
        "passengers": 2,
        "observed_at": NOW,
        "airlines": ["ANA"],
    }
    values.update(overrides)
    return NewQuote(**values)


def test_dedupe_key_ignores_airline_order_and_separates_departure_times() -> None:
    a = quote(1200, airlines=["ANA", "JAL"])
    b = quote(1200, airlines=["JAL", "ANA"])
    c = quote(1200, airlines=["ANA", "JAL"], depart_at_local="2026-11-05 11:30")

    assert dedupe_key("r1", a) == dedupe_key("r1", b)
    assert dedupe_key("r1", a) != dedupe_key("r1", c)
    assert dedupe_key("r1", a) != dedupe_key("r2", a)
    assert dedupe_key("r1", quote(1200)) == dedupe_key(
        "r1", quote(1200, price_total=Decimal("1200.00"))
    )


def test_same_fare_within_12_hours_is_a_duplicate() -> None:
    assert is_duplicate([NOW], NOW + timedelta(hours=6))
    assert not is_duplicate([NOW], NOW + timedelta(hours=13))
    assert not is_duplicate([], NOW)


def test_wildly_off_prices_are_flagged_suspect() -> None:
    median = median_per_person([Decimal(p) for p in (500, 520, 540, 560, 580)])

    assert median == Decimal(540)
    assert not is_suspect(Decimal(600), median)
    assert is_suspect(Decimal(100), median)
    assert is_suspect(Decimal(5000), median)
    assert median_per_person([Decimal(500)] * 4) is None
    assert not is_suspect(Decimal(1), None)


def flight(route: str, depart: date, ret: date | None) -> ChosenFlight:
    return ChosenFlight(route, "LAX", "NRT", depart, ret, ["ANA"])


def test_a_chosen_round_trip_sets_the_trips_dates() -> None:
    dates = flight_dates([flight("a", date(2026, 11, 5), date(2026, 11, 12))])

    assert dates is not None and (dates.start, dates.end) == (date(2026, 11, 5), date(2026, 11, 12))
    assert flight_dates([]) is None


def test_two_one_way_flights_set_the_start_and_the_end() -> None:
    out = flight("a", date(2026, 11, 5), None)
    home = flight("b", date(2026, 11, 12), None)

    dates = flight_dates([home, out])

    assert dates is not None and (dates.start, dates.end) == (date(2026, 11, 5), date(2026, 11, 12))
    assert [f.route_id for f in dates.flights] == ["a", "b"]
    only_out = flight_dates([out])
    assert only_out is not None and only_out.end is None


def test_trip_end_keeps_a_valid_current_end() -> None:
    dates = flight_dates([flight("a", date(2026, 11, 5), None)])
    assert dates is not None
    assert trip_end(dates, None) == date(2026, 11, 5)
    assert trip_end(dates, date(2026, 11, 1)) == date(2026, 11, 5)
    assert trip_end(dates, date(2026, 11, 9)) == date(2026, 11, 9)


def test_dates_stay_with_the_chosen_flight() -> None:
    dates = flight_dates([flight("a", date(2026, 11, 5), date(2026, 11, 12))])

    check_dates(dates, date(2026, 11, 5), date(2026, 11, 12))
    check_dates(None, date(2026, 1, 1), None)
    with pytest.raises(DatesFromFlight):
        check_dates(dates, date(2026, 11, 6), date(2026, 11, 12))


def test_only_this_routes_upcoming_fares_can_be_chosen() -> None:
    today = date(2026, 9, 26)
    check_choice("a", "a", today, today)
    with pytest.raises(ChoiceError, match="isn't one of this route's"):
        check_choice("b", "a", today, today)
    with pytest.raises(ChoiceError, match="already left"):
        check_choice("a", "a", today - timedelta(days=1), today)


def test_rates_refresh_every_12_hours() -> None:
    assert fx.needs_refresh(None, NOW)
    assert not fx.needs_refresh(NOW - timedelta(hours=11), NOW)
    assert fx.needs_refresh(NOW - timedelta(hours=12), NOW)


def test_local_currency_by_country() -> None:
    assert fx.local_currency("jp") == "JPY"
    assert fx.local_currency("BG") == "EUR"
    assert fx.local_currency(None) is None
