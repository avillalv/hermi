# ruff: noqa: E501  (long SQL strings)
"""The run context of an agent run (06 sections 2.5 and 4.2), built from the database.

The model never sees an id. Routes get per-run references `R1`, `R2` ... mapped to `flight_routes.id` in `runs.params.route_map`;
the map is rebuilt and validated against the run's own trip here, so what the admitting endpoint (or a client) wrote into
`runs.params` is only a hint about which routes to include. Everything else in the task is read from the tables.
"""

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.modules.ai.policy import api_blocked_domains

MAX_ROUTES = 3  # a run covers one to three routes (06 section 5.7)
MAX_AIRPORT_MATCHES = 8

_PARAMS = text("SELECT params, kind::text AS kind FROM runs WHERE id = :r AND trip_id = :t")
_TRIP = text(
    """SELECT t.name, t.start_date, t.end_date, t.home_currency::text AS home_currency,
              (SELECT count(*) FROM trip_members m WHERE m.trip_id = t.id) AS travelers
         FROM trips t WHERE t.id = :t AND t.deleted_at IS NULL"""
)
_DESTINATIONS = text(
    "SELECT name, region, country FROM trip_destinations WHERE trip_id = :t ORDER BY position LIMIT 10"
)
_ROUTES = """SELECT id, label, origin_codes::text[] AS origins, destination_codes::text[] AS dests, trip_type::text AS trip_type,
                    depart_from, depart_to, return_from, return_to, min_nights, max_nights, adults, children, cabin::text AS cabin, max_stops
               FROM flight_routes WHERE trip_id = :t AND active {filter} ORDER BY created_at, id"""
_CHEAPEST = text(
    """SELECT o.price_total_minor, o.currency::text AS currency, o.adults + o.children AS passengers, o.origin::text AS origin,
              o.destination::text AS destination, o.depart_date, o.return_date, o.airlines, o.observed_at,
              currency_exponent(o.currency::text) AS exponent
         FROM trip_fare_links l JOIN fare_observations o ON o.id = l.observation_id
        WHERE l.trip_id = :t AND l.route_id = :r AND NOT l.hidden AND NOT l.suspect AND o.observed_at > now() - interval '30 days'
        ORDER BY fx_convert_minor(o.price_total_minor, o.currency::text, :home) NULLS LAST, o.observed_at DESC LIMIT 1"""
)


@dataclass(frozen=True)
class RunContext:
    task: dict[str, Any]  # the JSON the model reads: trip, routes, blocked_domains
    route_map: dict[str, str]  # R1 -> flight_routes.id, in this trip, active
    kind: str


def blocked_domains() -> list[str]:
    """The list shown to the model, generated from policy (never typed twice)."""
    return sorted(d for d in api_blocked_domains() if not d.startswith("www."))


def _uuid(v: Any) -> uuid.UUID | None:
    try:
        return v if isinstance(v, uuid.UUID) else uuid.UUID(str(v))
    except (ValueError, TypeError, AttributeError):
        return None


def _money(minor: int, exponent: int) -> str:
    return f"{Decimal(minor).scaleb(-exponent):.{exponent}f}"


def _day(d: date | None) -> str | None:
    return d.isoformat() if d else None


def build_run_context(
    session: Session,
    run_id: uuid.UUID,
    trip_id: uuid.UUID,
    *,
    route_ids: list[uuid.UUID] | None = None,
    today: date | None = None,
) -> RunContext:
    """The context for `run_id`, scoped to `trip_id` (both from the runs row). Creates and stores the route map the first
    time; a later call keeps the same aliases. `route_ids` narrows the routes on the first call only."""
    params_row = session.execute(_PARAMS, {"r": run_id, "t": trip_id}).one_or_none()
    if params_row is None:
        raise LookupError("run not found for this trip")
    params = (
        params_row.params
        if isinstance(params_row.params, dict)
        else json.loads(params_row.params or "{}")
    )
    trip = session.execute(_TRIP, {"t": trip_id}).one_or_none()
    if trip is None:
        raise LookupError("trip not found")
    all_routes = session.execute(text(_ROUTES.format(filter="")), {"t": trip_id}).mappings().all()
    by_id = {str(r["id"]): r for r in all_routes}

    trip_routes = {
        str(i)
        for (i,) in session.execute(
            text("SELECT id FROM flight_routes WHERE trip_id = :t"), {"t": trip_id}
        )
    }
    stored = params.get("route_map")
    # a stored map is trusted only in its own shape: exactly R1..Rn, n at most MAX_ROUTES, string ids
    shaped = (
        isinstance(stored, dict)
        and 0 < len(stored) <= MAX_ROUTES
        and set(stored) == {f"R{n}" for n in range(1, len(stored) + 1)}
        and all(isinstance(v, str) for v in stored.values())
        and all(
            v in trip_routes for v in stored.values()
        )  # an id from another trip is never trusted
    )
    if shaped:
        # a route that went inactive mid-run drops its alias; the others keep theirs (never renumbered)
        route_map = {ref: stored[ref] for ref in sorted(stored) if stored[ref] in by_id}
    else:
        wanted = (
            route_ids
            if route_ids is not None
            else [u for u in map(_uuid, params.get("route_ids") or []) if u]
        )
        pool = (
            [by_id[str(i)] for i in dict.fromkeys(wanted) if str(i) in by_id]
            if wanted
            else all_routes
        )
        route_map = {f"R{n}": str(r["id"]) for n, r in enumerate(pool[:MAX_ROUTES], 1)}
        session.execute(
            text(
                "UPDATE runs SET params = jsonb_set(params, '{route_map}', CAST(:m AS jsonb), true) WHERE id = :r AND trip_id = :t"
            ),
            {"m": json.dumps(route_map), "r": run_id, "t": trip_id},
        )

    home = trip.home_currency
    routes = []
    for ref, rid in route_map.items():
        r = by_id[rid]
        known = session.execute(_CHEAPEST, {"t": trip_id, "r": rid, "home": home}).one_or_none()
        both = r["return_from"] is not None
        routes.append({
            "ref": ref, "label": r["label"], "origins": list(r["origins"]), "destinations": list(r["dests"]), "trip_type": r["trip_type"],
            "depart_from": _day(r["depart_from"]), "depart_to": _day(r["depart_to"]),
            "nights": [r["min_nights"], r["max_nights"]] if r["min_nights"] is not None else None,
            "return_window": {"from": _day(r["return_from"]), "to": _day(r["return_to"])} if both else None,
            "passengers": r["adults"] + r["children"], "adults": r["adults"], "children": r["children"],
            "cabin": r["cabin"], "max_stops": r["max_stops"],
            "cheapest_known": None if known is None else {
                "price_total": _money(known.price_total_minor, known.exponent), "currency": known.currency, "passengers": known.passengers,
                "origin": known.origin, "destination": known.destination, "depart_date": _day(known.depart_date),
                "return_date": _day(known.return_date), "airlines": list(known.airlines or []),
                "seen_at": known.observed_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ"),
            },
        })  # fmt: skip
    dests = [
        {"name": d.name, "region": d.region, "country": d.country}
        for d in session.execute(_DESTINATIONS, {"t": trip_id})
    ]
    task = {
        "trip": {
            "name": trip.name, "start_date": _day(trip.start_date), "end_date": _day(trip.end_date), "destinations": dests,
            "travelers": int(trip.travelers), "home_currency": home,
        },
        "routes": routes,
        "date_rules": "Departure must fall inside the route's depart window and not be in the past. Round trips need a return that fits "
        "the nights range or the return window. One way routes take no return date. Today is " + (today or datetime.now(UTC).date()).isoformat() + ".",
        "blocked_domains": blocked_domains(),
    }  # fmt: skip
    return RunContext(task, route_map, params_row.kind)


def lookup_airports(session: Session, query: str) -> list[dict[str, str | None]]:
    """Up to 8 airports whose code, city or name matches `query`; the airports table is public reference data."""
    q = query.strip().lower()
    like = "%" + re.sub(r"([\\%_])", r"\\\1", q) + "%"
    rows = session.execute(
        text(
            """SELECT iata::text AS code, name, city, country_code::text AS country FROM airports
                WHERE lower(iata::text) = :q OR lower(city) LIKE :p ESCAPE '\\' OR lower(name) LIKE :p ESCAPE '\\'
                ORDER BY (lower(iata::text) = :q) DESC, (lower(city) = :q) DESC, (kind = 'large_airport') DESC, iata LIMIT :n"""
        ),
        {"q": q, "p": like, "n": MAX_AIRPORT_MATCHES},
    )
    return [{"code": r.code, "name": r.name, "city": r.city, "country": r.country} for r in rows]
