# ruff: noqa: E501
"""SerpApi (Google Flights and Google Hotels vacation rentals) behind the live provider interface (02 section 3, WF-052).

This is the only module that talks to SerpApi, and it talks only to SerpApi's own API host. It never opens a listing or
airline page, and an Airbnb, Vrbo or Booking.com address that appears in a result is plain text, never followed.

Failures raise `SerpApiError` (a `ProviderError`) with a stable `code`; an empty result is not a failure. Prices come back
as Decimal in the requested currency. `client_for` picks the real client, the recorded fixtures (PROVIDERS_MODE=fake, no
key) or raises NotConfigured.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from hermi.providers import ProviderError

SEARCH_URL = "https://serpapi.com/search.json"
MAX_BYTES = 2_000_000  # 02 section 5.4: every outbound call has a response size limit
TRAVEL_CLASS = {"economy": 1, "premium_economy": 2, "business": 3, "first": 4}


Client = (
    httpx.Client
)  # re-exported so modules type a client without importing httpx (outbound-requests rule)
ClientPair = tuple[str, httpx.Client]  # (api key, client)


class SerpApiError(ProviderError):
    """`code`: provider_error (default), rate_limited (429), quota_exhausted (plan out of searches) or bad_key (401, 403)."""

    def __init__(
        self, message: str, *, code: str = "provider_error", status_code: int | None = None
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.code = code


@dataclass(frozen=True)
class FlightOffer:
    origin: str
    destination: str
    price_total: Decimal  # the whole party, as SerpApi prices it
    airlines: list[str]
    stops_out: int
    duration_out_min: int | None
    depart_at_local: str | None
    flight_numbers: list[str]
    raw: dict[str, Any] = field(repr=False, compare=False)


@dataclass(frozen=True)
class FlightSearch:
    offers: list[FlightOffer]  # cheapest first
    google_flights_url: str | None


@dataclass(frozen=True)
class RentalOffer:
    title: str
    link: str | None  # text only, never fetched
    site: str | None
    kind: str | None
    price_total: Decimal | None
    price_per_night: Decimal | None
    rating: Decimal | None
    review_count: int | None
    lat: float | None
    lon: float | None
    sleeps: int | None
    bedrooms: int | None
    photos: list[str]
    property_token: str | None


def stops_param(max_stops: int | None) -> int:
    """Our max stops to SerpApi `stops`: 0 any, 1 nonstop, 2 up to one stop, 3 up to two."""
    return 0 if max_stops is None else min(max_stops, 2) + 1


def google_flights_url(
    origins: list[str], destinations: list[str], depart: date, ret: date | None
) -> str:
    text = f"Flights from {','.join(origins)} to {','.join(destinations)} on {depart.isoformat()}"
    if ret:
        text += f" through {ret.isoformat()}"
    return f"https://www.google.com/travel/flights?q={quote(text)}"


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except InvalidOperation:
        return None


def _get(client: httpx.Client, params: dict[str, Any], api_key: str) -> dict[str, Any]:
    """One search. Returns the JSON body, or {} when Google has no results. Raises SerpApiError."""
    try:
        with client.stream("GET", SEARCH_URL, params={**params, "api_key": api_key}) as response:
            chunks, size = [], 0
            for (
                chunk
            ) in response.iter_bytes():  # cut while streaming, so a huge body is never held whole
                size += len(chunk)
                if size > MAX_BYTES:
                    raise SerpApiError(
                        "SerpApi response too large", status_code=response.status_code
                    )
                chunks.append(chunk)
            status = response.status_code
    except (
        httpx.HTTPError
    ) as exc:  # the message can carry the request URL, and so the key: the type only
        raise SerpApiError(f"SerpApi request failed: {type(exc).__name__}") from None
    try:
        body = json.loads(b"".join(chunks))
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    if status == 200 and not body.get("error"):
        return body
    message = str(body.get("error") or f"HTTP {status}")[:200]
    if "hasn't returned any results" in message:
        return {}
    if status == 429:
        code = "rate_limited"
    elif status in (401, 403):
        code = "bad_key"
    elif re.search(r"out of searches|plan.*(limit|exceeded)|run out", message, re.IGNORECASE):
        code = "quota_exhausted"
    else:
        code = "provider_error"
    raise SerpApiError(f"SerpApi: {message}", code=code, status_code=status)


def _items(body: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    """The result items under `keys`. A body whose lists hold anything but objects is a provider error (so the call is metered)."""
    out: list[dict[str, Any]] = []
    for k in keys:
        value = body.get(k) or []
        if not isinstance(value, list) or not all(isinstance(i, dict) for i in value):
            raise SerpApiError(f"SerpApi: malformed {k}", status_code=200)
        out.extend(value)
    return out


def to_offer(item: dict[str, Any]) -> FlightOffer | None:
    legs = item.get("flights") or []
    price = _decimal(item.get("price"))
    if not legs or price is None or price <= 0:
        return None
    first, last = legs[0].get("departure_airport") or {}, legs[-1].get("arrival_airport") or {}
    return FlightOffer(
        origin=str(first.get("id", "")).upper(),
        destination=str(last.get("id", "")).upper(),
        price_total=price,
        airlines=list(dict.fromkeys(leg["airline"] for leg in legs if leg.get("airline"))),
        stops_out=len(item.get("layovers") or []),
        duration_out_min=item.get("total_duration"),
        depart_at_local=first.get("time"),
        flight_numbers=[leg["flight_number"] for leg in legs if leg.get("flight_number")],
        raw={
            k: item[k]
            for k in ("flights", "layovers", "total_duration", "price", "type")
            if k in item
        },  # no tokens or logos
    )


def search_flights(
    client: httpx.Client,
    api_key: str,
    *,
    origins: list[str],
    destinations: list[str],
    depart_date: date,
    return_date: date | None,
    adults: int,
    children: int,
    cabin: str,
    max_stops: int | None,
    currency: str,
) -> FlightSearch:
    params: dict[str, Any] = {
        "engine": "google_flights",
        "departure_id": ",".join(origins),
        "arrival_id": ",".join(destinations),
        "outbound_date": depart_date.isoformat(),
        "type": 1 if return_date else 2,
        "travel_class": TRAVEL_CLASS.get(cabin, 1),
        "stops": stops_param(max_stops),
        "adults": adults,
        "children": children,
        "currency": currency.upper(),
        "sort_by": 2,  # price
        "hl": "en",
        "gl": "us",
    }
    if return_date:
        params["return_date"] = return_date.isoformat()
    body = _get(client, params, api_key)
    try:
        offers = sorted(
            (
                o
                for o in map(to_offer, _items(body, "best_flights", "other_flights"))
                if o is not None
            ),
            key=lambda o: o.price_total,
        )
    except (AttributeError, TypeError, KeyError) as exc:
        raise SerpApiError(
            f"SerpApi: malformed result ({type(exc).__name__})", status_code=200
        ) from None
    meta = body.get("search_metadata")
    return FlightSearch(offers, meta.get("google_flights_url") if isinstance(meta, dict) else None)


def to_rental(item: dict[str, Any]) -> RentalOffer | None:
    name = item.get("name")
    if not name:
        return None
    details = [str(d) for d in item.get("essential_info") or []]

    def count(pattern: str) -> int | None:
        for d in details:
            m = re.fullmatch(pattern, d.strip(), flags=re.IGNORECASE)
            if m:
                return int(m.group(1))
        return None

    gps = item.get("gps_coordinates") or {}
    rating = _decimal(item.get("overall_rating"))
    sources = [p.get("source") for p in item.get("prices") or [] if p.get("source")]
    images = (i.get("original_image") or i.get("thumbnail") for i in item.get("images") or [])
    return RentalOffer(
        title=str(name)[:200],
        link=item.get("link") or None,
        site=sources[0] if sources else item.get("source"),
        kind=item.get("type") or next((d for d in details if not re.search(r"\d", d)), None),
        price_total=_decimal((item.get("total_rate") or {}).get("extracted_lowest")),
        price_per_night=_decimal((item.get("rate_per_night") or {}).get("extracted_lowest")),
        rating=rating.quantize(Decimal("0.01")) if rating is not None else None,
        review_count=item.get("reviews"),
        lat=gps.get("latitude"),
        lon=gps.get("longitude"),
        sleeps=count(r"sleeps (\d+)"),
        bedrooms=count(r"(\d+) bedrooms?"),
        photos=[u for u in images if u][:3],
        property_token=item.get("property_token"),
    )


def search_rentals(
    client: httpx.Client,
    api_key: str,
    *,
    place: str,
    check_in: date,
    check_out: date,
    adults: int,
    children: int,
    currency: str,
) -> list[RentalOffer]:
    """Google Hotels with vacation_rentals on: results from Google's licensed rental partners. `ads` are ignored."""
    params: dict[str, Any] = {
        "engine": "google_hotels",
        "q": place,
        "check_in_date": check_in.isoformat(),
        "check_out_date": check_out.isoformat(),
        "adults": adults,
        "children": children,
        "currency": currency.upper(),
        "vacation_rentals": "true",
        "hl": "en",
        "gl": "us",
    }
    body = _get(client, params, api_key)
    try:
        return [o for o in map(to_rental, _items(body, "properties")) if o is not None]
    except (AttributeError, TypeError, KeyError) as exc:
        raise SerpApiError(
            f"SerpApi: malformed result ({type(exc).__name__})", status_code=200
        ) from None


_FIXTURES = Path(__file__).parent / "fixtures"
_BY_ENGINE = {
    "google_flights": "serpapi_google_flights.json",
    "google_hotels": "serpapi_vacation_rentals.json",
}


def fixture_client() -> httpx.Client:
    """Answers each engine from a recorded response: PROVIDERS_MODE=fake, an unset key and tests. No network."""

    def handler(request: httpx.Request) -> httpx.Response:
        name = _BY_ENGINE.get(request.url.params.get("engine", ""))
        if name is None:
            return httpx.Response(400, json={"error": "Unsupported engine"})
        return httpx.Response(200, json=json.loads((_FIXTURES / name).read_text(encoding="utf-8")))

    return httpx.Client(transport=httpx.MockTransport(handler))


def client_for(settings) -> tuple[str, httpx.Client]:
    """(api key, client). A key serves live; no key in PROVIDERS_MODE=fake serves the fixtures; otherwise NotConfigured.
    The caller closes the client."""
    key = settings.serpapi_api_key.get_secret_value() if settings.serpapi_api_key else ""
    if key:
        return key, httpx.Client(timeout=httpx.Timeout(20.0, connect=5.0), follow_redirects=False)
    if settings.providers_mode == "fake":
        return "fixture", fixture_client()
    settings.require("SERPAPI_API_KEY")  # raises NotConfigured
    raise AssertionError("unreachable")
