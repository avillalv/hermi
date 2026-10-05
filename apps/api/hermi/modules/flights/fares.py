# ruff: noqa: E501  (long SQL strings)
"""Cached fares for a route: Travelpayouts through the provider_calls ledger, a 6 hour shared cache, deduped observations.

Cached fares are free for every tier, so nothing here touches credits. Observations are shared by every trip (03 section 5.11):
one row per fare query (origin, destination and dates as asked, cabin, party, stops), and each route links to the rows it can see
through `trip_fare_links`. Writes use a worker or system session: the API login cannot write `fare_observations`.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import product
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.modules.ai.provider_calls import metered, record_provider_call, request_hash
from hermi.modules.flights.planner import RouteWindow, date_pairs
from hermi.providers import ProviderError, travelpayouts
from hermi.providers.travelpayouts import CachedFare

CACHE_TTL = timedelta(hours=6)  # 04 section 5.8: a fresh observation under 6 hours is served from the shared cache
MAX_QUERIES = 24  # shortcut: provider requests per refresh (airport pairs times month pairs). Ceiling: a 4 by 4 airport route over many months is trimmed. Upgrade: spread the rest over later refreshes.
ENDPOINT = "/aviasales/v3/prices_for_dates"

provider_for = travelpayouts.client_for
# shortcut: prices are requested in USD for every route. Ceiling: a non-USD trip sees USD fares. Upgrade: pass the trip's home currency when price_home lands.


@dataclass(frozen=True)
class RefreshResult:
    cached: bool  # true when no provider request was needed
    linked: int  # observations this route sees after the refresh
    requests: int  # provider requests made


def _months(first: date, last: date) -> list[str]:
    out, d = [], first.replace(day=1)
    while d <= last:
        out.append(d.strftime("%Y-%m"))
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def search_key(origin: str, destination: str, depart: date, ret: date | None, route: dict[str, Any]) -> str:
    """sha256 of the normalized fare query (03 section 5.11), with the codes as asked so a city and its airports share one row."""
    parts = [origin, destination, depart.isoformat(), ret.isoformat() if ret else "", route["cabin"], str(route["adults"]), str(route["children"]), "" if route["max_stops"] is None else str(route["max_stops"])]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _minor(session: Session, price: Decimal, party: int, currency: str) -> int:
    exponent = session.execute(text("SELECT currency_exponent(:c)"), {"c": currency}).scalar_one()
    return int((price * party * (Decimal(10) ** exponent)).to_integral_value(ROUND_HALF_UP))


def _window(route: dict[str, Any]) -> RouteWindow:
    return RouteWindow(route["trip_type"], route["depart_from"], route["depart_to"], route["return_from"], route["return_to"], route["min_nights"], route["max_nights"])


def _upsert(session: Session, route: dict[str, Any], key: str, fare: CachedFare, now: datetime) -> int | None:
    minor = _minor(session, fare.price_per_adult, route["adults"] + route["children"], fare.currency)
    if minor <= 0:
        return None
    return session.execute(
        text(
            """INSERT INTO fare_observations (search_key, origin, destination, depart_date, return_date, cabin, adults, children, stops_max, source,
                 confidence, currency, price_total_minor, airlines, stops_out, stops_back, duration_out_min, duration_back_min, depart_at_local,
                 flight_numbers, deep_link_template, source_domain, observed_at, expires_at, raw)
               VALUES (:key, :o, :d, :dep, :ret, :cabin, :adults, :children, :stops, 'travelpayouts', 'cached', :cur, :minor, :airlines, :so, :sb,
                 :dout, :dback, :local, CAST(:fn AS jsonb), :link, 'aviasales.com', :seen, :expires, CAST(:raw AS jsonb))
               ON CONFLICT (search_key, source, observed_at) DO UPDATE SET expires_at = EXCLUDED.expires_at
               RETURNING id"""
        ),
        {
            "key": key, "o": fare.origin, "d": fare.destination, "dep": fare.depart_date, "ret": fare.return_date, "cabin": route["cabin"],
            "adults": route["adults"], "children": route["children"], "stops": route["max_stops"], "cur": fare.currency, "minor": minor,
            "airlines": [fare.airline] if fare.airline else [], "so": fare.stops_out, "sb": fare.stops_back, "dout": fare.duration_out_min,
            "dback": fare.duration_back_min, "local": fare.depart_at_local, "fn": json.dumps([fare.flight_number] if fare.flight_number else None),
            "link": fare.link, "seen": fare.found_at or now, "expires": now + CACHE_TTL, "raw": json.dumps(fare.raw),
        },
    ).scalar_one()


def _fresh(session: Session, keys: list[str], now: datetime) -> dict[str, int]:
    """The newest unexpired observation per search key."""
    rows = session.execute(
        text(
            """SELECT DISTINCT ON (search_key) search_key, id FROM fare_observations
                WHERE search_key = ANY(:keys) AND source = 'travelpayouts' AND expires_at > :now
                ORDER BY search_key, observed_at DESC"""
        ),
        {"keys": keys, "now": now},
    )
    return {k: i for k, i in rows}


def refresh_route(session: Session, route_id: uuid.UUID, *, client: httpx.Client, token: str, now: datetime | None = None, currency: str = "usd") -> RefreshResult:
    """Fetch cached fares for the route's window (or reuse unexpired shared observations) and link them to the route.

    Every provider request goes through the ledger. A provider failure raises ProviderError and leaves the route unchanged.
    Cabins other than economy have no cached fares, so such a route is linked to nothing."""
    now = now or datetime.now(UTC)
    route = session.execute(text("SELECT id, trip_id, origin_codes::text[] AS origin_codes, destination_codes::text[] AS destination_codes, trip_type::text AS trip_type, depart_from, depart_to, return_from, return_to, min_nights, max_nights, adults, children, cabin::text AS cabin, max_stops FROM flight_routes WHERE id = :r"), {"r": route_id}).mappings().first()
    if route is None:
        raise LookupError(f"no route {route_id}")
    route = dict(route)
    pairs = date_pairs(_window(route), now.date())
    if route["cabin"] != "economy" or not pairs:
        return RefreshResult(True, 0, 0)

    one_way = route["trip_type"] == "one_way"
    dep_months = _months(pairs[0][0], pairs[-1][0])
    ret_months = [None] if one_way else _months(min(r for _, r in pairs if r), max(r for _, r in pairs if r))
    allowed = set(pairs)
    linked: dict[str, int] = {}  # search key -> observation id
    requests = 0
    for origin, dest in product(route["origin_codes"], route["destination_codes"]):
        keys = {search_key(origin, dest, d, r, route): (d, r) for d, r in pairs}
        # shortcut: one unexpired observation anywhere in the window counts as a hit for the whole airport pair, so a partial hit
        # can leave other date pairs up to 6 h stale-or-missing. Upgrade: track coverage per query once the ledger lookup is cheap.
        fresh = _fresh(session, list(keys), now)
        if fresh:
            record_provider_call(session, provider="travelpayouts", endpoint=ENDPOINT, ok=True, cost_usd_micros=0, cached=True, cache_layer="db", trip_id=route["trip_id"], request_hash=request_hash("travelpayouts", ENDPOINT, {"o": origin, "d": dest, "trip": route["trip_id"]}))
            linked.update(fresh)
            continue
        for dep_month, ret_month in product(dep_months, ret_months):
            if requests >= MAX_QUERIES:
                break
            params = {"origin": origin, "destination": dest, "departure_month": dep_month, "return_month": ret_month, "currency": currency, "direct_only": route["max_stops"] == 0}
            found = metered(
                session, "travelpayouts", ENDPOINT, lambda p=params: travelpayouts.prices_for_dates(client, token, **p),
                params=params, cost_usd_micros=0, trip_id=route["trip_id"],
            )
            requests += 1
            best: dict[str, CachedFare] = {}
            for fare in sorted(found, key=lambda f: f.price_per_adult):  # cheapest first, so the first fare per query wins
                pair = (fare.depart_date, fare.return_date)
                stops = max(fare.stops_out or 0, fare.stops_back or 0)
                if pair not in allowed or (route["max_stops"] is not None and stops > route["max_stops"]):
                    continue
                best.setdefault(search_key(origin, dest, *pair, route), fare)
            for key, fare in best.items():
                obs_id = _upsert(session, route, key, fare, now)
                if obs_id:
                    linked[key] = obs_id
    if linked:
        session.execute(
            text("INSERT INTO trip_fare_links (trip_id, route_id, observation_id) SELECT :t, :r, unnest(CAST(:ids AS bigint[])) ON CONFLICT (route_id, observation_id) DO NOTHING"),
            {"t": route["trip_id"], "r": route_id, "ids": list(linked.values())},
        )
    session.execute(text("UPDATE flight_routes SET last_checked_at = :now WHERE id = :r"), {"now": now, "r": route_id})
    return RefreshResult(requests == 0, len(linked), requests)


__all__ = ["CACHE_TTL", "ProviderError", "RefreshResult", "provider_for", "refresh_route", "search_key"]
