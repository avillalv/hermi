# ruff: noqa: E501  (long SQL strings and comments)
"""Place lookups through `places_cache` (03 section 5.5): 1 week TTL, the provider only on a miss.

Providers: Geoapify (search, details) and Wikipedia (summary), both by API; no page is ever scraped. `PROVIDERS_MODE=fake`
(the default, local dev and CI) serves recorded fixtures with no network, but still goes through the cache and the quota, so
the same code paths run. Tests patch `fetch_search`, `fetch_details` and `fetch_wiki` to count provider calls.
"""

import hashlib
import json
import time
import uuid

import httpx
from sqlalchemy import text

from hermi.db import system_session
from hermi.errors import ApiError
from hermi.modules.billing import service as billing
from hermi.modules.places.schemas import ATTRIBUTION, WIKI_ATTRIBUTION
from hermi.providers import ProviderError, geoapify
from hermi.providers.schemas import PlaceOut
from hermi.providers.wikipedia import WikipediaClient
from hermi.security import rate_limit

CACHE_DAYS = 7
UNAVAILABLE = ApiError(503, "provider_unavailable", "Place search is not working right now. Add it by hand and we will match it later.")
DAY_LIMIT_MSG = "You have reached today's {n} place searches. Saved places still work. Searches reset at midnight."


def key_of(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p).strip().lower() for p in parts).encode()).hexdigest()


def read(settings, user_id, key: str) -> dict | list | None:
    with system_session("places_cache", settings=settings, route="places", caller=str(user_id)) as s:
        row = s.execute(text("UPDATE places_cache SET hit_count = hit_count + 1 WHERE key = :k AND expires_at > now() RETURNING response"), {"k": key}).first()
    return row[0] if row else None


def write(settings, user_id, key: str, provider: str, kind: str, response: object, attribution: str, *, keep_detailed: bool = False) -> None:
    """Upsert. `keep_detailed` leaves a live row that already holds details alone (a search result must not downgrade it)."""
    guard = " WHERE NOT (places_cache.expires_at > now() AND places_cache.response @> '{\"has_details\": true}')" if keep_detailed else ""
    with system_session("places_cache", settings=settings, route="places", caller=str(user_id)) as s:
        s.execute(
            text(
                "INSERT INTO places_cache (key, provider, kind, response, attribution, expires_at) "
                "VALUES (:k, :p, :kind, CAST(:r AS jsonb), :a, now() + make_interval(days => :d)) "
                "ON CONFLICT (key) DO UPDATE SET response = EXCLUDED.response, fetched_at = now(), expires_at = EXCLUDED.expires_at" + guard
            ),
            {"k": key, "p": provider, "kind": kind, "r": json.dumps(response), "a": attribution, "d": CACHE_DAYS},
        )


# --- the daily quota (`places_searches_per_day`): only provider calls count, cached results keep working ---

def _window() -> int:
    return int(time.time() // rate_limit.DAY) * rate_limit.DAY


def daily_limit(session, user_id, trip_id: uuid.UUID | None) -> int:
    limit = billing.limit_of(billing.user_limits(session, user_id), "places_searches_per_day")
    if trip_id is not None:
        limit = max(limit, billing.limit_of(billing.trip_limits(session, trip_id)[1], "places_searches_per_day"))
    return limit


def check_quota(engine, user_id, limit: int) -> None:
    with engine.connect() as conn:
        used = conn.execute(
            text("SELECT coalesce(sum(count), 0) FROM rate_limit_counters WHERE bucket = :b AND window_start = to_timestamp(:s)"),
            {"b": f"places_day:{user_id}", "s": _window()},
        ).scalar_one()
    if used >= limit:
        retry = max(1, _window() + rate_limit.DAY - int(time.time()))
        raise ApiError(429, "quota_exceeded", DAY_LIMIT_MSG.format(n=limit), {"Retry-After": str(retry)})


def spend(engine, user_id) -> None:
    # shortcut: check then spend is not atomic, so parallel misses can overshoot by a few. Fine for a cost cap.
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO rate_limit_counters (bucket, window_start, count) VALUES (:b, to_timestamp(:s), 1) ON CONFLICT (bucket, window_start) DO UPDATE SET count = rate_limit_counters.count + 1"),
            {"b": f"places_day:{user_id}", "s": _window()},
        )


# --- providers (patched in tests) ---

_FIXTURES = [
    PlaceOut(provider="geoapify", id="fixture-belem", name="Belem Tower", category="sights", kinds=["tourism.sights"], address="Av. Brasilia, Lisbon", lat=38.6916, lon=-9.2160, website="https://example.org/belem", opening_hours="Tu-Su 10:00-17:30", wikipedia="en:Belem Tower", has_details=True),
    PlaceOut(provider="geoapify", id="fixture-ramen", name="Ramen Alfama", category="food", kinds=["catering.restaurant"], address="Rua de S. Pedro 5, Lisbon", lat=38.7110, lon=-9.1290),
    PlaceOut(provider="geoapify", id="fixture-museu", name="Museu do Azulejo", category="museum", kinds=["entertainment.museum"], address="Rua da Madre de Deus 4, Lisbon", lat=38.7253, lon=-9.1137, has_details=True),
]
_FIXTURE_WIKI = {"Belem Tower": {"title": "Belem Tower", "extract": "The Belem Tower is a fortified tower in Lisbon.", "url": "https://en.wikipedia.org/wiki/Belem_Tower", "image_url": None}}


def _key(settings) -> str:
    if settings.geoapify_api_key is None:
        raise UNAVAILABLE
    return settings.geoapify_api_key.get_secret_value()


def fetch_search(settings, q: str | None, category: str | None, lat: float, lon: float, radius_m: int, area: geoapify.Area | None) -> list[PlaceOut]:
    if settings.providers_mode == "fake":
        needle = (q or "").strip().lower()
        wanted = geoapify.SEARCH_KINDS.get(category or "", "")
        return [p for p in _FIXTURES if (needle in p.name.lower() if needle else any(k.startswith(w.split(".")[0]) for k in p.kinds for w in wanted.split(",")))]
    api_key = _key(settings)
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            if q:
                url, params = geoapify.text_request(q, lat, lon, radius_m, area)
                return geoapify.parse_geocode(geoapify.fetch(client, url, params, api_key))
            url, params = geoapify.kind_request(category or "landmarks", lat, lon, radius_m, 0, area)
            return geoapify.parse_places(geoapify.fetch(client, url, params, api_key))
    except ProviderError:
        raise UNAVAILABLE from None


def fetch_details(settings, geoapify_id: str) -> PlaceOut | None:
    if settings.providers_mode == "fake":
        return next((p.model_copy(update={"has_details": True}) for p in _FIXTURES if p.id == geoapify_id), None)
    api_key = _key(settings)
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            url, params = geoapify.details_request(geoapify_id)
            return geoapify.parse_details(geoapify.fetch(client, url, params, api_key))
    except ProviderError:
        raise UNAVAILABLE from None


def fetch_wiki(settings, place: PlaceOut) -> dict | None:
    """The English Wikipedia lead for a place that carries a `wikipedia` or `wikidata` tag. None when there is none or Wikimedia fails (the summary is optional)."""
    if settings.providers_mode == "fake":
        return _FIXTURE_WIKI.get((place.wikipedia or "").removeprefix("en:"))
    client = WikipediaClient(settings.wikimedia_contact)
    try:
        title = place.wikipedia[3:] if place.wikipedia and place.wikipedia.startswith("en:") else None
        if title is None and place.wikidata:
            title = client.english_title(place.wikidata)
        article = client.article(title) if title else None
    except ProviderError:
        return None
    finally:
        client.close()
    return {"title": article.title, "extract": article.extract, "url": article.page_url, "image_url": article.image_url} if article else None


# --- cached reads used by the router ---

def cache_places(settings, user_id, places: list[PlaceOut]) -> None:
    """Each place by id, so saving or opening one needs no provider call. A search row never replaces a detailed one."""
    for p in places:
        write(settings, user_id, key_of("geoapify", "place", p.id), "geoapify", "place_detail", p.model_dump(mode="json"), ATTRIBUTION, keep_detailed=True)


def cached_place(settings, user_id, geoapify_id: str) -> PlaceOut | None:
    row = read(settings, user_id, key_of("geoapify", "place", geoapify_id))
    return PlaceOut(**row) if isinstance(row, dict) else None


def cached_wiki(settings, user_id, place: PlaceOut) -> dict | None:
    if not (place.wikipedia or place.wikidata):
        return None
    key = key_of("wikimedia", "summary", place.wikipedia or place.wikidata)
    hit = read(settings, user_id, key)
    if hit is not None:
        return hit or None  # {} caches "no article"
    found = fetch_wiki(settings, place)
    write(settings, user_id, key, "wikimedia", "wiki_summary", found or {}, WIKI_ATTRIBUTION)
    return found
