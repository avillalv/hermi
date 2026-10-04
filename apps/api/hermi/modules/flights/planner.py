"""Decide which date pairs get a live (paid-quota) search.

A route's flexible window expands into many date pairs; only a few can be searched live each
run. The planner keeps the trip's chosen flight and the current best pair under watch, then
follows cheap cached fares, then spreads the rest across pairs that haven't been checked, oldest
first.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Literal

DatePair = tuple[date, date | None]


@dataclass(frozen=True)
class RouteWindow:
    """The dates a flight route allows. Round trips set a return window or a nights range."""

    trip_type: Literal["one_way", "round_trip"]
    depart_from: date
    depart_to: date
    return_from: date | None = None
    return_to: date | None = None
    min_nights: int | None = None
    max_nights: int | None = None


WATCH_BEST_EVERY = timedelta(hours=11)
RECHECK_CACHED_AFTER = timedelta(hours=23)


def date_pairs(route: RouteWindow, today: date) -> list[DatePair]:
    """Every (departure, return) the route allows, skipping departures before today."""
    first = max(route.depart_from, today)
    departures = [first + timedelta(days=i) for i in range((route.depart_to - first).days + 1)]
    if route.trip_type == "one_way":
        return [(d, None) for d in departures]
    if route.min_nights is not None and route.max_nights is not None:
        return [
            (d, d + timedelta(days=n))
            for d in departures
            for n in range(route.min_nights, route.max_nights + 1)
        ]
    assert route.return_from is not None and route.return_to is not None
    returns = [
        route.return_from + timedelta(days=i)
        for i in range((route.return_to - route.return_from).days + 1)
    ]
    return [(d, r) for d in departures for r in returns if r > d]


def spread(items: list[DatePair], count: int) -> list[DatePair]:
    """`count` items evenly spaced through the list (so early checks cover the whole window)."""
    if count <= 0 or not items:
        return []
    if count >= len(items):
        return list(items)
    step = len(items) / count
    return [items[int(i * step + step / 2)] for i in range(count)]


@dataclass(frozen=True)
class PlannerInput:
    pairs: list[DatePair]
    cached_prices: dict[DatePair, Decimal]
    last_live_check: dict[DatePair, datetime]
    best_live_pair: DatePair | None
    # The flight picked for the trip: watched first, even if the route's window has since moved.
    chosen_pair: DatePair | None = None


def pick_live_searches(plan: PlannerInput, allowance: int, now: datetime) -> list[DatePair]:
    allowed = set(plan.pairs)
    picks: list[DatePair] = []

    def take(candidates: Iterable[DatePair]) -> None:
        for pair in candidates:
            if len(picks) >= allowance:
                return
            if pair in allowed and pair not in picks:
                picks.append(pair)

    def stale(pair: DatePair, after: timedelta) -> bool:
        checked = plan.last_live_check.get(pair)
        return checked is None or now - checked >= after

    if plan.chosen_pair and allowance > 0 and stale(plan.chosen_pair, WATCH_BEST_EVERY):
        picks.append(plan.chosen_pair)
    if plan.best_live_pair and stale(plan.best_live_pair, WATCH_BEST_EVERY):
        take([plan.best_live_pair])
    cheap_first = sorted(plan.cached_prices, key=lambda p: plan.cached_prices[p])
    take(p for p in cheap_first if stale(p, RECHECK_CACHED_AFTER))
    never_checked = [p for p in plan.pairs if p not in plan.last_live_check and p not in picks]
    take(spread(never_checked, allowance - len(picks)))
    oldest_first = sorted(
        (p for p in plan.pairs if p in plan.last_live_check), key=lambda p: plan.last_live_check[p]
    )
    take(p for p in oldest_first if stale(p, RECHECK_CACHED_AFTER))
    return picks
