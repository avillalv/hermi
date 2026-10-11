# ruff: noqa: E501  (long SQL strings)
"""Live fare search through SerpApi (WF-052.1; 04 sections 5.8 and 5.9, 02 section 3, 08 section 6.5).

`run_live_search` is the one engine for both live searches (flights here, rentals in `modules/lodging/rentals.py`):

1. Gate: kill switch `provider.serpapi`, then flag `serpapi_live_fares` (default off), both fail closed. No provider call
   is made and a typed `feature_disabled` is raised.
2. Shared cache: a result under 6 hours old is free for everyone and says so (`cached`, `checked_at`, `age_seconds`).
   A hit never touches ceilings or credits. It writes a `provider_calls` row with `cached = true` for the hit rate.
3. Single flight: a miss takes a session-level advisory lease on the canonical key. The holder runs the one provider
   call; everyone else waits without a connection or a reservation and is then served from the cache, free.
4. The holder checks the month quota, then `budget.admit` (account ceiling, then the 1 credit `live_search` reserve),
   calls SerpApi, writes the result and its `provider_calls` row at the price constant, and settles. A failure, or an
   empty result, charges nothing. Failures are never cached.

Cache reads and writes run as a system session (purpose `fare_refresh`): the API login cannot write `fare_observations`
or `shared_research_cache`, and a hit must be visible across users. Nothing here fetches an Airbnb, Vrbo or Booking.com
page; the only host is SerpApi's API (`providers/serpapi.py`).
"""

import hashlib
import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import product
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import NotConfigured
from hermi.errors import ApiError, NotFound
from hermi.modules.admin.flags import Ctx, FlagRuntime
from hermi.modules.ai import cache
from hermi.modules.ai.features.base import already_settled
from hermi.modules.ai.metering import record_provider_spend
from hermi.modules.credits import budget, service
from hermi.modules.flights import fares
from hermi.providers import ProviderError, serpapi

log = logging.getLogger("hermi.live_search")

PROVIDER = "serpapi"
FLAG = "serpapi_live_fares"
KILL_KEY = "provider.serpapi"
ACTION = "live_search"
CACHE_TTL = timedelta(hours=6)  # 04 section 5.8 and 5.9: a result under 6 hours old is free
ENDPOINT_FLIGHTS = "google_flights"
ENDPOINT_RENTALS = "google_hotels"
PURPOSE = "fare_refresh"  # one reviewed SystemSession purpose for the live search cache fill (03 section 6.6)
QUOTA_SETTING = "setting_serpapi_monthly_quota"
_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class LiveResult:
    data: Any
    cached: bool  # served from the shared cache: no provider call, nothing charged
    checked_at: datetime  # when the provider was asked
    age_seconds: int  # 0 for a fresh call
    credits_charged: int  # 0 or 1 (`live_search`)


# --- the canonical keys -------------------------------------------------------------------------------------------


def _norm_codes(codes: list[str] | tuple[str, ...]) -> str:
    return ",".join(sorted({c.strip().upper() for c in codes if c.strip()}))


def flight_search_key(
    origins: list[str],
    destinations: list[str],
    depart: date,
    ret: date | None,
    *,
    cabin: str,
    adults: int,
    children: int,
    max_stops: int | None,
    currency: str,
) -> str:
    """sha256 of the normalized search: airports sorted and upper case, dates, cabin, party, stops and currency. Nothing a
    person typed (no trip id, no user id, no route id), so ten users on one route share one key (WF-052)."""
    parts = [
        PROVIDER,
        ENDPOINT_FLIGHTS,
        "v1",
        _norm_codes(origins),
        _norm_codes(destinations),
        depart.isoformat(),
        ret.isoformat() if ret else "",
        cabin.lower(),
        str(adults),
        str(children),
        "" if max_stops is None else str(max_stops),
        currency.upper(),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def rental_search_key(
    place: str, check_in: date, check_out: date, *, adults: int, children: int, currency: str
) -> str:
    """sha256 of the normalized rental search. The place is the destination label (case and spacing folded)."""
    parts = [
        PROVIDER,
        ENDPOINT_RENTALS,
        "v1",
        " ".join(place.casefold().split()),
        check_in.isoformat(),
        check_out.isoformat(),
        str(adults),
        str(children),
        currency.upper(),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# --- gate, quota, errors ------------------------------------------------------------------------------------------


def _paused(reason: str, detail: str) -> ApiError:
    return ApiError(503, "feature_disabled", detail, extra={"reason": reason})


def _tier(api: Session, user_id: uuid.UUID, trip_id: uuid.UUID) -> str:
    """The tier the flag's `tiers` rule sees: a trip with an active pass is `trip_pass`, else the account's tier."""
    return api.execute(
        text(
            """SELECT CASE WHEN EXISTS (SELECT 1 FROM trip_passes p WHERE p.trip_id = :t AND p.status = 'active'
                                         AND now() >= p.starts_at AND now() < p.expires_at) THEN 'trip_pass'
                    ELSE coalesce((SELECT e.tier_code FROM entitlements e WHERE e.user_id = :u AND (e.valid_until IS NULL OR e.valid_until > now())), 'free') END"""
        ),
        {"u": user_id, "t": trip_id},
    ).scalar_one()


def gate(api: Session, flags: FlagRuntime, *, user_id: uuid.UUID, trip_id: uuid.UUID) -> None:
    """Kill switch, then flag. Both fail closed (an unreadable flag table reads as off)."""
    if flags.switch_engaged(KILL_KEY):
        raise _paused(
            "provider_paused",
            "Live search is paused for a moment. Saved and cached fares still work.",
        )
    if not flags.evaluate(FLAG, Ctx(user_id=user_id, tier=_tier(api, user_id, trip_id))):
        raise _paused("flag_off", "Live search is not available yet. Cached fares still work.")


def _check_quota(sys: Session, settings) -> None:
    """Global monthly search quota, the lower of `setting_serpapi_monthly_quota` and SERPAPI_MONTHLY_CAP: refuses before any spend."""
    row = sys.execute(
        text("SELECT (rules ->> 'searches')::int FROM feature_flags WHERE key = :k"),
        {"k": QUOTA_SETTING},
    ).first()
    caps = [settings.serpapi_monthly_cap] + ([int(row[0])] if row and row[0] is not None else [])
    cap = min(caps)  # the console setting can only tighten the env cap
    used = sys.execute(
        text(
            "SELECT count(*) FROM provider_calls WHERE provider = :p AND ok AND NOT cached "
            "AND created_at >= date_trunc('month', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'"
        ),
        {"p": PROVIDER},
    ).scalar_one()
    if used >= cap:
        raise _paused("quota", "Live search is paused until next month. Cached fares still work.")


def _provider_failure(e: ProviderError) -> ApiError:
    code = getattr(e, "code", "provider_error")
    if code in ("rate_limited", "quota_exhausted", "bad_key"):
        return ApiError(
            503,
            "provider_unavailable",
            "We could not run that search right now. Nothing was charged.",
            extra={"reason": code},
        )
    return ApiError(
        502,
        "provider_error",
        "We could not run that search. Nothing was charged.",
        extra={"reason": code},
    )


# --- the engine ---------------------------------------------------------------------------------------------------


Read = Callable[
    [Session], tuple[Any, datetime, int] | None
]  # (data, checked_at, age_seconds) or None on a miss


def run_live_search(
    api: Session,
    *,
    settings,
    flags: FlagRuntime,
    user_id: uuid.UUID,
    trip_id: uuid.UUID,
    idempotency_key: str,
    key: str,
    endpoint: str,
    route: str,
    read: Read,
    fetch: Callable[[str, serpapi.Client], Any],
    write: Callable[[Session, Any, datetime], Any],
    is_empty: Callable[[Any], bool],
    attach: Callable[[Session, Any], None] | None = None,
    counts_pass_check: bool = False,
    provider_client: serpapi.ClientPair | None = None,
    wait_seconds: float = 30.0,
    poll_seconds: float = 0.25,
) -> LiveResult:
    """`read(sys)` returns the fresh shared entry or None. `fetch(api_key, client)` makes the one provider call.
    `write(sys, data, now)` stores it and returns the data in read's shape. `attach(sys, data)` runs on a hit and a miss
    (linking a result to the caller's route). `counts_pass_check` adds one to the trip pass's live checks on a charged call
    (flights only, 04 section 5.8). `provider_client` is for tests; the product path uses `client_for`."""
    if (
        api.execute(text("SELECT 1 FROM trips WHERE id = :t"), {"t": trip_id}).first() is None
    ):  # RLS: a trip the caller cannot see
        raise NotFound()
    gate(api, flags, user_id=user_id, trip_id=trip_id)
    try:
        api_key, client = provider_client or serpapi.client_for(settings)
    except NotConfigured:
        raise _paused(
            "not_configured", "Live search is not available right now. Cached fares still work."
        ) from None
    try:
        return _serve(
            api,
            settings=settings,
            user_id=user_id,
            trip_id=trip_id,
            idem=f"{user_id}:{ACTION}:{idempotency_key}",
            key=key,
            endpoint=endpoint,
            route=route,
            read=read,
            fetch=fetch,
            write=write,
            is_empty=is_empty,
            attach=attach,
            api_key=api_key,
            client=client,
            wait_seconds=wait_seconds,
            poll_seconds=poll_seconds,
            counts_pass_check=counts_pass_check,
        )
    finally:
        if provider_client is None:
            client.close()


def _as_user(api: Session, user_id: uuid.UUID) -> None:
    api.execute(
        text("SELECT set_config('app.user_id', :u, true)"), {"u": str(user_id)}
    )  # the last commit ended the transaction


def _serve(
    api,
    *,
    settings,
    user_id,
    trip_id,
    idem,
    key,
    endpoint,
    route,
    read,
    fetch,
    write,
    is_empty,
    attach,
    api_key,
    client,
    wait_seconds,
    poll_seconds,
    counts_pass_check,
) -> LiveResult:
    # A retry whose reservation already settled must not call the provider again (admit() would skip the ceiling check).
    if already_settled(api, idem):
        raise ApiError(
            409,
            "idempotency_key_reused",
            "That request was already handled. Start it again with a new key.",
        )
    api.commit()  # no connection is held while waiting for another caller's provider call
    engine = api.get_bind()
    deadline = time.monotonic() + wait_seconds

    def hit() -> LiveResult | None:
        with db.system_session(PURPOSE, settings=settings, route=route, caller=str(user_id)) as sys:
            got = read(sys)
            if got is None:
                return None
            data, checked_at, age = got
            if attach:
                attach(sys, data)
            record_provider_spend(
                sys,
                PROVIDER,
                endpoint,
                cached=True,
                cache_layer="db",
                user_id=user_id,
                trip_id=trip_id,
                request_hash=key,
            )
        return LiveResult(data, True, checked_at, age, 0)

    got = hit()
    if got is not None:
        return got
    while True:
        # Waiters poll only the try-lock (no system session): the holder's release is what lets the next caller read the cache.
        lease = cache.Lease(engine, f"{PROVIDER}:{key}")
        if lease.acquire():
            try:
                got = hit()  # the holder before us may have finished
                if got is not None:
                    return got
                return _miss(
                    api,
                    settings=settings,
                    user_id=user_id,
                    trip_id=trip_id,
                    idem=idem,
                    key=key,
                    endpoint=endpoint,
                    route=route,
                    fetch=fetch,
                    write=write,
                    is_empty=is_empty,
                    attach=attach,
                    api_key=api_key,
                    client=client,
                    counts_pass_check=counts_pass_check,
                )
            finally:
                lease.release()
        if time.monotonic() >= deadline:  # nothing was reserved, so nothing is charged
            raise ApiError(
                503,
                "live_search_busy",
                "That search is still running. Try again in a minute. Nothing was charged.",
            )
        time.sleep(poll_seconds)


def _miss(
    api,
    *,
    settings,
    user_id,
    trip_id,
    idem,
    key,
    endpoint,
    route,
    fetch,
    write,
    is_empty,
    attach,
    api_key,
    client,
    counts_pass_check,
) -> LiveResult:
    with db.system_session(PURPOSE, settings=settings, route=route, caller=str(user_id)) as sys:
        _check_quota(sys, settings)
    _as_user(api, user_id)
    res = budget.admit(api, user_id=user_id, trip_id=trip_id, action=ACTION, idempotency_key=idem)
    api.commit()  # the reservation must be visible to the system session

    def refund(failure: ProviderError | None, latency_ms: int | None) -> None:
        try:
            with db.system_session(
                PURPOSE, settings=settings, route=route, caller=str(user_id)
            ) as sys:
                if (
                    failure is not None
                ):  # the ledger row for a failed call, never cached, costs nothing
                    record_provider_spend(
                        sys,
                        PROVIDER,
                        endpoint,
                        ok=False,
                        user_id=user_id,
                        trip_id=trip_id,
                        request_hash=key,
                        status_code=failure.status_code,
                        latency_ms=latency_ms,
                    )
                service.refund(sys, res.id)
        except Exception:  # the stale reservation sweeper is the backstop
            log.error("live_search_refund_failed", exc_info=True)

    started = time.perf_counter()
    try:
        data = fetch(api_key, client)
    except ProviderError as e:
        refund(e, round((time.perf_counter() - started) * 1000))
        raise _provider_failure(e) from e
    except BaseException:
        refund(None, None)
        raise
    latency = round((time.perf_counter() - started) * 1000)
    checked_at = datetime.now(UTC)
    try:
        with db.system_session(PURPOSE, settings=settings, route=route, caller=str(user_id)) as sys:
            out = write(sys, data, checked_at)
            if attach:
                attach(sys, out)
            record_provider_spend(
                sys,
                PROVIDER,
                endpoint,
                user_id=user_id,
                trip_id=trip_id,
                request_hash=key,
                status_code=200,
                latency_ms=latency,
            )
            charged = (
                0 if is_empty(out) else res.amount
            )  # an empty result is not charged, but the call was paid for
            service.settle(sys, res.id, charged)
            if (
                charged and counts_pass_check
            ):  # a trip pass counts its live checks (04 section 5.8, flights only)
                sys.execute(
                    text(
                        "UPDATE trip_passes SET live_checks_used = live_checks_used + 1 WHERE trip_id = :t AND status = 'active' "
                        "AND now() >= starts_at AND now() < expires_at AND live_checks_used < live_checks_max"
                    ),
                    {"t": trip_id},
                )
    except BaseException:
        refund(None, None)
        raise
    return LiveResult(out, False, checked_at, 0, charged)


# --- flights ------------------------------------------------------------------------------------------------------


def _fare_rows(sys: Session, keys: list[str], currency: str) -> list[dict[str, Any]]:
    rows = sys.execute(
        text(
            """SELECT DISTINCT ON (search_key) id AS observation_id, search_key, origin::text AS origin, destination::text AS destination,
                      depart_date, return_date, currency::text AS currency, price_total_minor, airlines, stops_out, duration_out_min,
                      depart_at_local, flight_numbers, deep_link_template AS link, observed_at
                 FROM fare_observations
                WHERE search_key = ANY(:keys) AND source = 'serpapi' AND currency = :cur AND expires_at > now()
                ORDER BY search_key, observed_at DESC"""
        ),
        {"keys": keys, "cur": currency},
    ).mappings()
    return sorted((dict(r) for r in rows), key=lambda r: (r["price_total_minor"], r["search_key"]))


def search_live_flights(
    api: Session,
    *,
    settings,
    flags: FlagRuntime,
    user_id: uuid.UUID,
    trip_id: uuid.UUID,
    route_id: uuid.UUID,
    depart_date: date,
    return_date: date | None,
    currency: str,
    idempotency_key: str,
    provider_client: serpapi.ClientPair | None = None,
    wait_seconds: float = 30.0,
    poll_seconds: float = 0.25,
) -> LiveResult:
    """One live check for one date pair of a route. `data` is the fares (cheapest first, one per asked airport pair),
    already linked to the route. The route-slot and pass-check gates are the caller's (`live_route`, 04 section 5.8).

    shortcut: only the cheapest offer per asked airport pair is stored (the fare view shows one fare per query, 03 section 5.11).
    Ceiling: a second stop count or airline for the same pair is not kept. Upgrade: store the top N when the live view lists them."""
    currency = currency.upper()
    if not _CURRENCY.match(currency):
        raise ApiError(422, "invalid_request", "Use a three letter currency code.")
    r = (
        api.execute(
            text(
                "SELECT origin_codes::text[] AS origins, destination_codes::text[] AS destinations, trip_type::text AS trip_type, adults, children, "
                "cabin::text AS cabin, max_stops FROM flight_routes WHERE id = :r AND trip_id = :t"
            ),
            {"r": route_id, "t": trip_id},
        )
        .mappings()
        .first()
    )
    if r is None:
        raise NotFound()
    if (r["trip_type"] == "one_way") != (return_date is None) or (
        return_date is not None and return_date < depart_date
    ):
        raise ApiError(422, "invalid_request", "Check the dates for this route.")
    spec = dict(r)
    key = flight_search_key(
        spec["origins"],
        spec["destinations"],
        depart_date,
        return_date,
        cabin=spec["cabin"],
        adults=spec["adults"],
        children=spec["children"],
        max_stops=spec["max_stops"],
        currency=currency,
    )
    asked = {  # asked airport pair -> the shared fare query key (the same function the cached refresh uses)
        (o, d): fares.search_key(
            o,
            d,
            depart_date,
            return_date,
            {
                "cabin": spec["cabin"],
                "adults": spec["adults"],
                "children": spec["children"],
                "max_stops": spec["max_stops"],
            },
        )
        for o, d in product(spec["origins"], spec["destinations"])
    }

    def read(sys: Session) -> tuple[Any, datetime, int] | None:
        row = sys.execute(
            text(
                "SELECT created_at, EXTRACT(EPOCH FROM now() - created_at)::int AS age FROM provider_calls "
                "WHERE provider = :p AND endpoint = :e AND request_hash = :k AND ok AND NOT cached "
                "AND created_at > now() - make_interval(secs => :ttl) ORDER BY created_at DESC LIMIT 1"
            ),
            {"p": PROVIDER, "e": ENDPOINT_FLIGHTS, "k": key, "ttl": CACHE_TTL.total_seconds()},
        ).first()
        if row is None:
            return None
        return _fare_rows(sys, list(asked.values()), currency), row.created_at, max(int(row.age), 0)

    def fetch(api_key: str, client: serpapi.Client) -> serpapi.FlightSearch:
        return serpapi.search_flights(
            client,
            api_key,
            origins=spec["origins"],
            destinations=spec["destinations"],
            depart_date=depart_date,
            return_date=return_date,
            adults=spec["adults"],
            children=spec["children"],
            cabin=spec["cabin"],
            max_stops=spec["max_stops"],
            currency=currency,
        )

    def as_asked(code: str, options: list[str]) -> str | None:
        """The offer's airport as the route asked for it (a city code such as TYO covers NRT and HND)."""
        return code if code in options else (options[0] if len(options) == 1 else None)

    def write(sys: Session, found: serpapi.FlightSearch, now: datetime) -> list[dict[str, Any]]:
        best: dict[str, serpapi.FlightOffer] = {}
        for offer in found.offers:  # cheapest first
            o, d = (
                as_asked(offer.origin, spec["origins"]),
                as_asked(offer.destination, spec["destinations"]),
            )
            if (
                o is not None
                and d is not None
                and (spec["max_stops"] is None or offer.stops_out <= spec["max_stops"])
            ):
                best.setdefault(asked[(o, d)], offer)
        link = found.google_flights_url or serpapi.google_flights_url(
            spec["origins"], spec["destinations"], depart_date, return_date
        )
        for k, offer in best.items():
            minor = fares._minor(
                sys, offer.price_total, 1, currency
            )  # SerpApi prices the whole party
            if minor <= 0:
                continue
            sys.execute(
                text(
                    """INSERT INTO fare_observations (search_key, origin, destination, depart_date, return_date, cabin, adults, children, stops_max,
                         source, confidence, currency, price_total_minor, airlines, stops_out, duration_out_min, depart_at_local, flight_numbers,
                         deep_link_template, source_domain, observed_at, expires_at, raw)
                       VALUES (:k, :o, :d, :dep, :ret, :cabin, :adults, :children, :stops, 'serpapi', 'live', :cur, :minor, :airlines, :so, :dout,
                         :local, CAST(:fn AS jsonb), :link, 'google.com', :seen, :exp, CAST(:raw AS jsonb))
                       ON CONFLICT (search_key, source, observed_at) DO NOTHING"""
                ),
                {
                    "k": k,
                    "o": offer.origin,
                    "d": offer.destination,
                    "dep": depart_date,
                    "ret": return_date,
                    "cabin": spec["cabin"],
                    "adults": spec["adults"],
                    "children": spec["children"],
                    "stops": spec["max_stops"],
                    "cur": currency,
                    "minor": minor,
                    "airlines": offer.airlines,
                    "so": offer.stops_out,
                    "dout": offer.duration_out_min,
                    "local": offer.depart_at_local,
                    "fn": json.dumps(offer.flight_numbers),
                    "link": link,
                    "seen": now,
                    "exp": now + CACHE_TTL,
                    "raw": json.dumps(offer.raw, default=str),
                },
            )
        return _fare_rows(sys, list(asked.values()), currency)

    def attach(sys: Session, rows: list[dict[str, Any]]) -> None:
        if rows:
            sys.execute(
                text(
                    "INSERT INTO trip_fare_links (trip_id, route_id, observation_id) SELECT :t, :r, unnest(CAST(:ids AS bigint[])) "
                    "ON CONFLICT (route_id, observation_id) DO NOTHING"
                ),
                {"t": trip_id, "r": route_id, "ids": [x["observation_id"] for x in rows]},
            )
        sys.execute(
            text("UPDATE flight_routes SET last_checked_at = now() WHERE id = :r"), {"r": route_id}
        )

    return run_live_search(
        api,
        settings=settings,
        flags=flags,
        user_id=user_id,
        trip_id=trip_id,
        idempotency_key=idempotency_key,
        key=key,
        endpoint=ENDPOINT_FLIGHTS,
        route="POST /v1/trips/{trip_id}/flights/live-search",
        read=read,
        fetch=fetch,
        write=write,
        is_empty=lambda rows: not rows,
        attach=attach,
        counts_pass_check=True,
        provider_client=provider_client,
        wait_seconds=wait_seconds,
        poll_seconds=poll_seconds,
    )


__all__ = [
    "ACTION",
    "CACHE_TTL",
    "FLAG",
    "KILL_KEY",
    "LiveResult",
    "flight_search_key",
    "gate",
    "rental_search_key",
    "run_live_search",
    "search_live_flights",
]
