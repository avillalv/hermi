# ruff: noqa: E501  (long comments and SQL)
"""GET /geo/destinations (04 section 5.5): destination typeahead over Geoapify geocoding, cached in `places_cache`.

Only the Geoapify API is called (providers/geoapify.py), never a scraped page.
"""

import hashlib
import json
import time
from collections import defaultdict, deque
from typing import Annotated

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from hermi.db import system_session
from hermi.deps import CurrentUser
from hermi.errors import ApiError
from hermi.providers import ProviderError
from hermi.providers.geoapify import search_destinations
from hermi.providers.schemas import DestinationSuggestion

router = APIRouter(tags=["geo"])

CACHE_DAYS = 7
ATTRIBUTION = "OpenStreetMap contributors, Geoapify"
QUOTA_PER_HOUR = 120  # provider lookups per user per hour; cache hits are free
# shortcut: in-process counters, so the quota is per API process, and the check and the later charge are not atomic (concurrent lookups can overshoot by a few).  Move to rate_limit_counters when the API runs as more than one process or the overshoot matters.
_used: dict[str, deque[float]] = defaultdict(deque)


def _key(query: str) -> str:
    return hashlib.sha256(f"geoapify|autocomplete|{query.strip().lower()}".encode()).hexdigest()


def _read(settings, user_id, key: str) -> list[dict] | None:
    with system_session("places_cache", settings=settings, route="GET /v1/geo/destinations", caller=str(user_id)) as s:
        row = s.execute(
            text("UPDATE places_cache SET hit_count = hit_count + 1 WHERE key = :k AND expires_at > now() RETURNING response"), {"k": key}
        ).first()
    return row[0] if row else None


def _write(settings, user_id, key: str, items: list[dict]) -> None:
    with system_session("places_cache", settings=settings, route="GET /v1/geo/destinations", caller=str(user_id)) as s:
        s.execute(
            text(
                "INSERT INTO places_cache (key, provider, kind, response, attribution, expires_at) "
                "VALUES (:k, 'geoapify', 'autocomplete', CAST(:r AS jsonb), :a, now() + make_interval(days => :d)) "
                "ON CONFLICT (key) DO UPDATE SET response = EXCLUDED.response, fetched_at = now(), expires_at = EXCLUDED.expires_at"
            ),
            {"k": key, "r": json.dumps(items), "a": ATTRIBUTION, "d": CACHE_DAYS},
        )


def _check_quota(user_id) -> None:
    now, used = time.monotonic(), _used[str(user_id)]
    while used and now - used[0] > 3600:
        used.popleft()
    if len(used) >= QUOTA_PER_HOUR:
        raise ApiError(429, "rate_limited", "You are searching too fast. Try again in a few minutes.", {"Retry-After": str(int(3600 - (now - used[0])) + 1)})


def _charge(user_id) -> None:
    _used[str(user_id)].append(time.monotonic())


def _fixture(code: str, name: str, region: str | None, country: str, cc: str, lat: float, lon: float, tz: str) -> DestinationSuggestion:
    return DestinationSuggestion(
        label=f"{name}, {country}", name=name, region=region, country=country, country_code=cc, kind="city",
        lat=lat, lon=lon, timezone=tz, bbox=None, geoapify_place_id=f"fixture-{code}",
    )


# Recorded rows served when PROVIDERS_MODE=fake (local dev, CI): no network, no quota, no cache write.
FAKE_DESTINATIONS = [
    _fixture("lisbon", "Lisbon", "Lisbon", "Portugal", "PT", 38.7223, -9.1393, "Europe/Lisbon"),
    _fixture("porto", "Porto", "Porto", "Portugal", "PT", 41.1579, -8.6291, "Europe/Lisbon"),
    _fixture("tokyo", "Tokyo", "Tokyo", "Japan", "JP", 35.6762, 139.6503, "Asia/Tokyo"),
    _fixture("newyork", "New York", "New York", "United States", "US", 40.7128, -74.006, "America/New_York"),
]


@router.get("/geo/destinations", response_model=list[DestinationSuggestion])
async def destinations(
    request: Request,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=2, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=8)] = 8,
) -> list[DestinationSuggestion]:
    settings, key = request.app.state.settings, _key(q)
    if settings.providers_mode == "fake":
        needle = q.strip().lower()
        return [d for d in FAKE_DESTINATIONS if needle in d.label.lower()][:limit]
    cached = await run_in_threadpool(_read, settings, user.id, key)
    if cached is None:
        if settings.geoapify_api_key is None:
            raise ApiError(503, "provider_unavailable", "We could not search places right now. Try again in a moment.")
        _check_quota(user.id)  # refused before any provider call
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                found = await search_destinations(q, settings.geoapify_api_key.get_secret_value(), client)
        except ProviderError:
            raise ApiError(503, "provider_unavailable", "We could not search places right now. Try again in a moment.") from None
        _charge(user.id)  # only a lookup that reached the provider counts
        cached = [d.model_dump(mode="json") for d in found]
        await run_in_threadpool(_write, settings, user.id, key, cached)
    return [DestinationSuggestion(**d) for d in cached[:limit]]
