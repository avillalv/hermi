# ruff: noqa: E501  (long SQL strings)
"""Rental search through SerpApi (WF-052.1; 04 section 5.9). Behind the same flag, kill switch, cache, single flight,
ceiling and credit as live flights (`modules/flights/live.py`).

Results are Google Hotels vacation rentals from Google's licensed partners, fetched through SerpApi's own API. Nothing
here opens an Airbnb, Vrbo or Booking.com page, and a result link is stored as text only. The shared entry lives in
`shared_research_cache` with kind `rentals` (03 section 11.5), keyed by the normalized search, so it holds public inputs
and public listings only. Sorting is by price or rating and never by commission; `sorted_by` states it.
"""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import ApiError
from hermi.modules.admin.flags import FlagRuntime
from hermi.modules.ai import cache
from hermi.modules.ai.pricing import price_version
from hermi.modules.flights import fares, live
from hermi.modules.flights.live import ENDPOINT_RENTALS, LiveResult, rental_search_key
from hermi.providers import serpapi

SORTS = {"price": "price, lowest first", "rating": "rating, highest first"}
KIND = "rentals"
_PLACE_MAX = 120


def _minor_or_none(sys: Session, value: Decimal | None, currency: str) -> int | None:
    return fares._minor(sys, value, 1, currency) if value is not None else None


def sort_offers(offers: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    """Price (per night, lowest first) or rating (highest first). A missing value goes last. Ties break on title."""
    if sort == "rating":
        return sorted(offers, key=lambda o: (o["rating"] is None, -(o["rating"] or 0), o["title"]))
    return sorted(
        offers,
        key=lambda o: (
            o["price_per_night_minor"] is None,
            o["price_per_night_minor"] or 0,
            o["title"],
        ),
    )


def search_live_rentals(
    api: Session,
    *,
    settings,
    flags: FlagRuntime,
    user_id: uuid.UUID,
    trip_id: uuid.UUID,
    place: str,
    check_in: date,
    check_out: date,
    adults: int,
    children: int,
    currency: str,
    idempotency_key: str,
    sort: str = "price",
    provider_client: serpapi.ClientPair | None = None,
    wait_seconds: float = 30.0,
    poll_seconds: float = 0.25,
) -> LiveResult:
    """`data` is `{"offers": [...], "currency": "USD", "sorted_by": "price, lowest first"}`; prices are integer minor units.
    The caller passes the trip's destination label as `place`, not free text."""
    place = " ".join(place.split())
    currency = currency.upper()
    if sort not in SORTS:
        raise ApiError(422, "invalid_request", "Sort by price or rating.")
    if not place or len(place) > _PLACE_MAX or len(currency) != 3 or not currency.isalpha():
        raise ApiError(422, "invalid_request", "Check the place and currency.")
    if check_out <= check_in or not (1 <= adults <= 9 and 0 <= children <= 8):
        raise ApiError(422, "invalid_request", "Check the dates and guests.")
    key = rental_search_key(
        place, check_in, check_out, adults=adults, children=children, currency=currency
    )

    def finish(response: dict[str, Any]) -> dict[str, Any]:
        return {
            "offers": sort_offers(response["offers"], sort),
            "currency": response["currency"],
            "sorted_by": SORTS[sort],
        }

    def read(sys: Session) -> tuple[Any, datetime, int] | None:
        entry = cache.lookup(sys, key)
        if (
            entry is None or entry.state != "fresh"
        ):  # stale or flagged is not served: a miss is a new, paid search
            return None
        cache.bump_hit(sys, key)
        age = int(
            sys.execute(
                text("SELECT EXTRACT(EPOCH FROM now() - :f)::int"), {"f": entry.fetched_at}
            ).scalar_one()
        )
        return entry.response, entry.fetched_at, max(age, 0)

    def fetch(api_key: str, client: serpapi.Client) -> list[serpapi.RentalOffer]:
        return serpapi.search_rentals(
            client,
            api_key,
            place=place,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            currency=currency,
        )

    def write(sys: Session, found: list[serpapi.RentalOffer], now: datetime) -> dict[str, Any]:
        offers = [
            {
                "title": o.title,
                "link": o.link,
                "site": o.site,
                "kind": o.kind,
                "price_per_night_minor": _minor_or_none(sys, o.price_per_night, currency),
                "price_total_minor": _minor_or_none(sys, o.price_total, currency),
                "rating": float(o.rating) if o.rating is not None else None,
                "review_count": o.review_count,
                "lat": o.lat,
                "lon": o.lon,
                "sleeps": o.sleeps,
                "bedrooms": o.bedrooms,
                "photos": o.photos,
                "property_token": o.property_token,
            }
            for o in found
        ]
        response = {"offers": offers, "currency": currency}
        cache.store(
            sys,
            key=key,
            kind=KIND,
            provider=live.PROVIDER,
            params={
                "place": place,
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "adults": adults,
                "children": children,
                "currency": currency,
            },
            response=json.loads(json.dumps(response)),
            sources=[],
            model=ENDPOINT_RENTALS,
            prompt_version="1",
            ttl_for=live.CACHE_TTL,
            run_id=None,
            cost_usd_micros=price_version().provider_call_micros[live.PROVIDER],
        )
        return response

    out = live.run_live_search(
        api,
        settings=settings,
        flags=flags,
        user_id=user_id,
        trip_id=trip_id,
        idempotency_key=idempotency_key,
        key=key,
        endpoint=ENDPOINT_RENTALS,
        route="POST /v1/trips/{trip_id}/lodging/rental-search",
        read=read,
        fetch=fetch,
        write=write,
        is_empty=lambda response: not response["offers"],
        provider_client=provider_client,
        wait_seconds=wait_seconds,
        poll_seconds=poll_seconds,
    )
    return LiveResult(
        finish(out.data), out.cached, out.checked_at, out.age_seconds, out.credits_charged
    )
