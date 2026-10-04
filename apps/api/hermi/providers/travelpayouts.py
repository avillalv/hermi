"""Cached fares from the Aviasales Data API (Travelpayouts).

These are prices other Aviasales users found in the last few days, so they cost nothing to
fetch and cover whole months at once, which makes them a good scan of flexible dates. Prices
are per adult.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx

from hermi.providers import ProviderError

BASE_URL = "https://api.travelpayouts.com/aviasales/v3"
SITE_URL = "https://www.aviasales.com"
_SEARCH_DATE = re.compile(r"search_date=(\d{2})(\d{2})(\d{4})")


@dataclass(frozen=True)
class CachedFare:
    origin: str
    destination: str
    depart_date: date
    return_date: date | None
    price_per_adult: Decimal
    currency: str
    airline: str | None
    flight_number: str | None
    stops_out: int | None
    stops_back: int | None
    duration_out_min: int | None
    duration_back_min: int | None
    depart_at_local: str | None
    link: str | None
    found_at: datetime | None
    raw: dict[str, Any] = field(repr=False, compare=False)


def _found_at(link: str | None) -> datetime | None:
    """When an Aviasales user saw this fare, from the link's search_date=DDMMYYYY."""
    match = _SEARCH_DATE.search(link or "")
    if not match:
        return None
    day, month, year = (int(g) for g in match.groups())
    try:
        return datetime(year, month, day, 12, tzinfo=UTC)
    except ValueError:
        return None


def _local(value: str | None) -> tuple[date | None, str | None]:
    """'2026-11-10T11:30:00-08:00' -> (date(2026, 11, 10), '2026-11-10 11:30')."""
    if not value:
        return None, None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None, None
    return parsed.date(), parsed.strftime("%Y-%m-%d %H:%M")


def to_fare(row: dict[str, Any], currency: str) -> CachedFare | None:
    depart_date, depart_local = _local(row.get("departure_at"))
    return_date, _ = _local(row.get("return_at"))
    price = row.get("price")
    if depart_date is None or not price:
        return None
    link = row.get("link")
    return CachedFare(
        origin=(row.get("origin_airport") or row.get("origin") or "").upper(),
        destination=(row.get("destination_airport") or row.get("destination") or "").upper(),
        depart_date=depart_date,
        return_date=return_date,
        price_per_adult=Decimal(str(price)),
        currency=currency.upper(),
        airline=row.get("airline"),
        flight_number=f"{row['airline']} {row['flight_number']}"
        if row.get("airline") and row.get("flight_number")
        else None,
        stops_out=row.get("transfers"),
        stops_back=row.get("return_transfers") if return_date else None,
        duration_out_min=row.get("duration_to") or None,
        duration_back_min=row.get("duration_back") or None,
        depart_at_local=depart_local,
        link=f"{SITE_URL}{link}" if link else None,
        found_at=_found_at(link),
        raw=row,
    )


def prices_for_dates(
    client: httpx.Client,
    token: str,
    *,
    origin: str,
    destination: str,
    departure_month: str,
    return_month: str | None,
    currency: str,
    direct_only: bool = False,
    limit: int = 1000,
) -> list[CachedFare]:
    """Cheapest cached fares for a month (YYYY-MM); one-way when return_month is None."""
    params: dict[str, Any] = {
        "origin": origin,
        "destination": destination,
        "departure_at": departure_month,
        "one_way": "true" if return_month is None else "false",
        "direct": "true" if direct_only else "false",
        "currency": currency.lower(),
        "sorting": "price",
        "unique": "false",
        "limit": limit,
        "page": 1,
    }
    if return_month:
        params["return_at"] = return_month
    try:
        response = client.get(
            f"{BASE_URL}/prices_for_dates", params=params, headers={"X-Access-Token": token}
        )
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError(f"Travelpayouts request failed: {exc}") from exc
    if not body.get("success", False):
        reason = str(body.get("error") or "no reason given")[:200]
        raise ProviderError(f"Travelpayouts returned an error: {reason}")
    fares = (to_fare(row, body.get("currency") or currency) for row in body.get("data") or [])
    return [f for f in fares if f is not None]
