"""Geoapify: destination search for trips, and places to do near a destination (OpenStreetMap data).

Destination search: autocomplete is good at partial words ("Kyo" to Kyoto) but ranks some full names
poorly ("Bali" misses Indonesia); full-text search is the opposite. We query both in parallel and
merge, which costs two of the free daily credits per lookup.

Places: category searches ("museums") use the Places API, which returns hours, website and Wikipedia
links (1 credit per 20 places). Free-text searches ("ramen") use the Geocoding API, which
returns only the basics; details come from Place Details on request (1 credit each). Geoapify
allows storing results.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from hermi.providers import ProviderError
from hermi.providers.schemas import DestinationSuggestion, PlaceOut

log = logging.getLogger(__name__)

BASE_URL = "https://api.geoapify.com/v1/geocode"
# Result types that are never trip destinations.
EXCLUDED_KINDS = {"street", "postcode", "building", "unknown"}
# Named points (islands, parks, landmarks) must be reasonably well known to be suggested.
MIN_AMENITY_IMPORTANCE = 0.3
CACHE_SECONDS = 3600

# shortcut: in-process cache (about 500 entries, 1 hour) stands in for the provider_calls cache
# (WF-043). Upgrade when workers run as more than one process.
_cache: dict[str, tuple[float, list[DestinationSuggestion]]] = {}


def _importance(result: dict[str, Any]) -> float:
    value = (result.get("rank") or {}).get("importance")
    return 0.5 if value is None else float(value)


def to_suggestion(result: dict[str, Any]) -> DestinationSuggestion | None:
    kind = result.get("result_type") or "unknown"
    if kind in EXCLUDED_KINDS:
        return None
    if kind == "amenity" and _importance(result) < MIN_AMENITY_IMPORTANCE:
        return None
    name = result.get("name") or result.get("city") or result.get("state") or result.get("country")
    if not name or result.get("lat") is None or result.get("lon") is None:
        return None

    country = result.get("country")
    state = result.get("state")
    bbox = result.get("bbox")
    return DestinationSuggestion(
        label=result.get("formatted") or name,
        name=name,
        region=state if state and state != name else None,
        country=country,
        country_code=(result.get("country_code") or "").upper() or None,
        kind=kind,
        lat=float(result["lat"]),
        lon=float(result["lon"]),
        timezone=(result.get("timezone") or {}).get("name"),
        bbox=[bbox["lon1"], bbox["lat1"], bbox["lon2"], bbox["lat2"]] if bbox else None,
        geoapify_place_id=result.get("place_id"),
    )


def merge_results(
    query: str, results: list[dict[str, Any]], limit: int = 8
) -> list[DestinationSuggestion]:
    """Dedupe results from both endpoints; exact name matches rank first, then well-known places."""
    seen: set[tuple[str, str | None, float, float]] = set()
    ranked: list[tuple[bool, float, DestinationSuggestion]] = []
    wanted = query.strip().lower()
    for result in results:
        suggestion = to_suggestion(result)
        if suggestion is None:
            continue
        key = (
            suggestion.name.lower(),
            suggestion.country_code,
            round(suggestion.lat, 1),
            round(suggestion.lon, 1),
        )
        if key in seen:
            continue
        seen.add(key)
        ranked.append((suggestion.name.lower() == wanted, _importance(result), suggestion))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [suggestion for _, _, suggestion in ranked[:limit]]


async def search_destinations(
    query: str, api_key: str, client: httpx.AsyncClient
) -> list[DestinationSuggestion]:
    cache_key = query.strip().lower()
    cached = _cache.get(cache_key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]

    params = {"text": query, "format": "json", "limit": 6, "lang": "en", "apiKey": api_key}
    responses = await asyncio.gather(
        client.get(f"{BASE_URL}/search", params=params),
        client.get(f"{BASE_URL}/autocomplete", params=params),
        return_exceptions=True,
    )
    results: list[dict[str, Any]] = []
    failures = 0
    for response in responses:
        if isinstance(response, BaseException) or response.status_code != 200:
            failures += 1
            continue
        results.extend(response.json().get("results", []))
    if failures == len(responses):
        raise ProviderError("Geoapify didn't respond. Check GEOAPIFY_API_KEY and the connection.")

    suggestions = merge_results(query, results)
    if len(_cache) > 500:
        _cache.clear()
    _cache[cache_key] = (time.monotonic(), suggestions)
    return suggestions


# --- Places ---

PLACES_URL = "https://api.geoapify.com/v2/places"
GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
DETAILS_URL = "https://api.geoapify.com/v2/place-details"
PAGE_SIZE = 20

# The search chips, as Geoapify categories.
SEARCH_KINDS: dict[str, str] = {
    "restaurants": "catering.restaurant,catering.fast_food",
    "cafes": "catering.cafe",
    "museums": "entertainment.museum,entertainment.culture",
    "landmarks": "tourism.sights,tourism.attraction",
    "viewpoints": "tourism.attraction.viewpoint",
    "parks": "leisure.park,national_park",
    "beaches": "beach",
    "nightlife": "catering.bar,catering.pub,adult.nightclub",
    "shopping": "commercial.shopping_mall,commercial.marketplace,commercial.department_store",
}

# Geoapify categories → the activity category (color and icon in the day view). First match wins.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("museum", ("entertainment.museum", "entertainment.culture")),
    ("nightlife", ("catering.bar", "catering.pub", "catering.biergarten", "adult.nightclub")),
    ("food", ("catering",)),
    ("nature", ("leisure.park", "national_park", "beach", "natural")),
    ("shopping", ("commercial",)),
    ("travel", ("public_transport", "airport", "railway")),
    ("sights", ("tourism", "religion", "heritage", "entertainment", "leisure")),
]


def activity_category(kinds: list[str]) -> str:
    for category, prefixes in CATEGORY_RULES:
        if any(kind == p or kind.startswith(p + ".") for kind in kinds for p in prefixes):
            return category
    return "other"


@dataclass(frozen=True)
class Area:
    """A whole destination to search, like all of Costa Rica, not a circle around its middle."""

    place_id: str | None = None
    # [west, south, east, north], used when there's no place id.
    bbox: tuple[float, ...] | None = None
    # Set for a country: text searches filter by it.
    country_code: str | None = None


# Without a boundary or box, "the whole area" falls back to this circle.
WIDE_RADIUS_M = 80_000


def _where(lat: float, lon: float, radius_m: int, area: Area | None, text: bool) -> dict[str, str]:
    """Where to look: a circle, or a whole area. Results nearest the center come first."""
    bias = f"proximity:{lon},{lat}"
    if area is not None:
        if text and area.country_code:
            return {"filter": f"countrycode:{area.country_code.lower()}", "bias": bias}
        # Place boundaries work for category search; text search takes the bounding box.
        if area.place_id and not text:
            return {"filter": f"place:{area.place_id}", "bias": bias}
        if area.bbox:
            west, south, east, north = area.bbox
            return {"filter": f"rect:{west},{south},{east},{north}", "bias": bias}
        radius_m = max(radius_m, WIDE_RADIUS_M)
    return {"filter": f"circle:{lon},{lat},{radius_m}", "bias": bias}


def kind_request(
    kind: str, lat: float, lon: float, radius_m: int, offset: int = 0, area: Area | None = None
) -> tuple[str, dict[str, Any]]:
    params = {
        "categories": SEARCH_KINDS[kind],
        **_where(lat, lon, radius_m, area, text=False),
        "limit": PAGE_SIZE,
        "offset": offset,
        "lang": "en",
    }
    return PLACES_URL, params


def text_request(
    text: str, lat: float, lon: float, radius_m: int, area: Area | None = None
) -> tuple[str, dict[str, Any]]:
    where = _where(lat, lon, radius_m, area, text=True)
    params = {"text": text, "type": "amenity", **where, "limit": PAGE_SIZE}
    return GEOCODE_URL, {**params, "lang": "en", "format": "json"}


# Destination kinds the geocoder can be asked for directly.
GEOCODE_TYPES = {"country", "state", "city", "county", "postcode", "locality"}


def place_request(
    name: str, kind: str | None, country_code: str | None, lat: float, lon: float
) -> tuple[str, dict[str, Any]]:
    """Find a destination's own Geoapify id (for one saved before ids were kept)."""
    params: dict[str, Any] = {
        "text": name,
        "bias": f"proximity:{lon},{lat}",
        "limit": 1,
        "format": "json",
    }
    if kind in GEOCODE_TYPES:
        params["type"] = kind
    if country_code:
        params["filter"] = f"countrycode:{country_code.lower()}"
    return GEOCODE_URL, params


def details_request(place_id: str) -> tuple[str, dict[str, Any]]:
    return DETAILS_URL, {"id": place_id, "features": "details", "lang": "en"}


def fetch(client: httpx.Client, url: str, params: dict[str, Any], api_key: str) -> dict[str, Any]:
    try:
        response = client.get(url, params={**params, "apiKey": api_key})
    except httpx.HTTPError as exc:
        raise ProviderError("Couldn't reach Geoapify. Check the connection.") from exc
    if response.status_code in (401, 403):
        raise ProviderError("Geoapify refused the API key. Check GEOAPIFY_API_KEY.")
    if response.status_code == 429:
        raise ProviderError("The daily Geoapify credits are used up. Searches work again tomorrow.")
    if response.status_code != 200:
        raise ProviderError(
            f"Geoapify returned an error ({response.status_code}). Try again in a moment."
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("Geoapify sent a response that couldn't be read.") from exc


def _address(props: dict[str, Any], name: str) -> str | None:
    # With a name, address_line1 repeats it and line 2 is the street address.
    if props.get("address_line1") == name and props.get("address_line2"):
        return props["address_line2"]
    return props.get("formatted") or props.get("address_line2")


def _text(*values: Any) -> str | None:
    """The first value given, as text. OpenStreetMap tags pass through as-is, so a phone number
    can arrive as a number."""
    for value in values:
        if value is not None and value != "":
            return str(value)
    return None


def _distance(props: dict[str, Any]) -> int | None:
    value = props.get("distance")
    return round(value) if isinstance(value, int | float) else None


def from_feature(props: dict[str, Any]) -> PlaceOut | None:
    """A Places API or Place Details feature: hours, website and wiki links when known."""
    local = props.get("name")
    name = (props.get("name_international") or {}).get("en") or local or props.get("address_line1")
    if (
        not name
        or props.get("lat") is None
        or props.get("lon") is None
        or not props.get("place_id")
    ):
        return None
    raw = (props.get("datasource") or {}).get("raw") or {}
    wiki = props.get("wiki_and_media") or {}
    contact = props.get("contact") or {}
    kinds = list(props.get("categories") or [])
    return PlaceOut(
        provider="geoapify",
        id=props["place_id"],
        name=name,
        local_name=local if local and local != name else None,
        category=activity_category(kinds),
        kinds=kinds,
        address=_address(props, name),
        lat=float(props["lat"]),
        lon=float(props["lon"]),
        distance_m=_distance(props),
        website=_text(props.get("website"), raw.get("website")),
        opening_hours=_text(props.get("opening_hours"), raw.get("opening_hours")),
        phone=_text(contact.get("phone"), raw.get("phone")),
        wikidata=_text(wiki.get("wikidata"), raw.get("wikidata")),
        wikipedia=_text(wiki.get("wikipedia"), raw.get("wikipedia")),
        has_details=True,
    )


def from_geocode(result: dict[str, Any]) -> PlaceOut | None:
    """A Geocoding result: name, address, and location only."""
    name = result.get("name") or result.get("address_line1")
    if (
        not name
        or result.get("lat") is None
        or result.get("lon") is None
        or not result.get("place_id")
    ):
        return None
    local = (result.get("other_names") or {}).get("name")
    kinds = [result["category"]] if result.get("category") else []
    return PlaceOut(
        provider="geoapify",
        id=result["place_id"],
        name=name,
        local_name=local if local and local != name else None,
        category=activity_category(kinds),
        kinds=kinds,
        address=_address(result, name),
        lat=float(result["lat"]),
        lon=float(result["lon"]),
        distance_m=_distance(result),
        has_details=False,
    )


def _each(
    items: list[dict[str, Any]], parse: Callable[[dict[str, Any]], PlaceOut | None]
) -> list[PlaceOut]:
    """Parse each result, skipping any that can't be read, so one odd place can't sink a search."""
    places = []
    for item in items:
        try:
            place = parse(item)
        except (ValidationError, TypeError, ValueError) as exc:
            log.warning("Skipped a Geoapify place that couldn't be read: %s", exc)
            continue
        if place is not None:
            places.append(place)
    return places


def parse_places(data: dict[str, Any]) -> list[PlaceOut]:
    return _each([f.get("properties") or {} for f in data.get("features") or []], from_feature)


def parse_geocode(data: dict[str, Any]) -> list[PlaceOut]:
    return _each(list(data.get("results") or []), from_geocode)


def parse_details(data: dict[str, Any]) -> PlaceOut | None:
    features = data.get("features") or []
    return from_feature(features[0].get("properties") or {}) if features else None
