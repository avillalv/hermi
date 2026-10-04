from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from hermi.modules.flights.planner import (
    PlannerInput,
    RouteWindow,
    date_pairs,
    pick_live_searches,
    spread,
)

NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)
D = date


def route(**overrides) -> RouteWindow:
    values = {
        "trip_type": "round_trip",
        "depart_from": D(2026, 11, 5),
        "depart_to": D(2026, 11, 7),
        "min_nights": 7,
        "max_nights": 8,
        "return_from": None,
        "return_to": None,
    }
    values.update(overrides)
    return RouteWindow(**values)


def test_nights_range_pairs() -> None:
    assert date_pairs(route(), D(2026, 9, 26)) == [
        (D(2026, 11, 5), D(2026, 11, 12)),
        (D(2026, 11, 5), D(2026, 11, 13)),
        (D(2026, 11, 6), D(2026, 11, 13)),
        (D(2026, 11, 6), D(2026, 11, 14)),
        (D(2026, 11, 7), D(2026, 11, 14)),
        (D(2026, 11, 7), D(2026, 11, 15)),
    ]


def test_return_window_pairs_never_return_before_departing() -> None:
    r = route(
        min_nights=None, max_nights=None, return_from=D(2026, 11, 6), return_to=D(2026, 11, 7)
    )

    assert date_pairs(r, D(2026, 9, 26)) == [
        (D(2026, 11, 5), D(2026, 11, 6)),
        (D(2026, 11, 5), D(2026, 11, 7)),
        (D(2026, 11, 6), D(2026, 11, 7)),
    ]


def test_one_way_and_past_departures() -> None:
    one_way = route(trip_type="one_way", min_nights=None, max_nights=None)

    assert date_pairs(one_way, D(2026, 11, 6)) == [(D(2026, 11, 6), None), (D(2026, 11, 7), None)]
    assert date_pairs(one_way, D(2026, 12, 1)) == []


def test_spread_covers_the_whole_window() -> None:
    items = [(D(2026, 11, day), None) for day in range(1, 11)]

    picked = spread(items, 3)

    assert len(picked) == 3
    assert picked[0][0] < D(2026, 11, 4) and picked[-1][0] > D(2026, 11, 7)


def test_priorities_best_then_cheap_cached_then_unchecked() -> None:
    pairs = date_pairs(route(), D(2026, 9, 26))
    best = pairs[4]
    cheap = pairs[2]
    plan = PlannerInput(
        pairs=pairs,
        cached_prices={cheap: Decimal(600), pairs[3]: Decimal(900)},
        last_live_check={best: NOW - timedelta(hours=12), pairs[3]: NOW - timedelta(hours=1)},
        best_live_pair=best,
    )

    picks = pick_live_searches(plan, allowance=3, now=NOW)

    assert picks[0] == best
    assert picks[1] == cheap
    assert pairs[3] not in picks  # checked an hour ago
    assert len(picks) == 3


def test_recently_checked_pairs_are_left_alone() -> None:
    pairs = date_pairs(route(), D(2026, 9, 26))
    plan = PlannerInput(
        pairs=pairs,
        cached_prices={},
        last_live_check={p: NOW - timedelta(hours=2) for p in pairs},
        best_live_pair=pairs[0],
    )

    assert pick_live_searches(plan, allowance=5, now=NOW) == []


def day(offset: int) -> date:
    return date(2026, 9, 26) + timedelta(days=offset)


def test_the_chosen_flight_is_checked_first_even_outside_the_window() -> None:
    window = [(day(40), day(47)), (day(41), day(48))]
    chosen = (day(30), day(37))
    plan = PlannerInput(
        pairs=window, cached_prices={}, last_live_check={}, best_live_pair=None, chosen_pair=chosen
    )

    picks = pick_live_searches(plan, 2, NOW)
    assert picks[0] == chosen and len(picks) == 2  # then the window, as before
    recent = PlannerInput(
        pairs=window,
        cached_prices={},
        last_live_check={chosen: NOW - timedelta(hours=1)},
        best_live_pair=None,
        chosen_pair=chosen,
    )
    assert chosen not in pick_live_searches(recent, 2, NOW)
