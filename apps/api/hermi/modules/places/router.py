# ruff: noqa: E501  (long SQL strings)
"""Places (04 section 5.11): search and detail through `places_cache`, and the trip's saved places (the ideas list).

Results are ranked by relevance and distance only, never by commission. Search is limited to 30 a minute (`places_search`) and to
`places_searches_per_day` provider calls a day; a cached result is free and keeps working past the daily cap. Saving a place reads
the cache and never calls a provider. Every response carries the OpenStreetMap and Wikipedia attributions.
"""

import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import text

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.collaboration.activity import record
from hermi.modules.collaboration.schemas import Attribution
from hermi.modules.places import service
from hermi.modules.places.schemas import (
    ATTRIBUTION,
    PlaceDetails,
    PlaceSearchResult,
    SavedPlace,
    SavedPlaceIn,
    SavedPlacePage,
    SavedPlaceRef,
    Wiki,
)
from hermi.pagination import decode_offset, encode_offset
from hermi.providers import geoapify
from hermi.providers.schemas import PlaceOut
from hermi.security import rate_limit

router = APIRouter(tags=["places"])

_PREFIX = "geoapify:"
_EXTRA = ("kinds", "local_name", "opening_hours", "phone", "wikidata", "wikipedia", "has_details")


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "validation_failed", "Some fields need another look.", extra={"errors": [{"field": field, "code": "invalid", "message": message}]})


def _out(place: PlaceOut) -> PlaceOut:
    return place.model_copy(update={"id": _PREFIX + place.id})


def _geoapify_id(place_id: str) -> str:
    if not place_id.startswith(_PREFIX) or len(place_id) == len(_PREFIX):
        raise _invalid("place_id", "Use a place id from a search, like geoapify:abc.")
    return place_id[len(_PREFIX):]


@router.get("/places/search", response_model=PlaceSearchResult)
def search(
    request: Request,
    user: CurrentUser,
    session: DbSession,
    q: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=30)] = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    radius_m: Annotated[int, Query(ge=100, le=50000)] = 5000,
    destination_id: uuid.UUID | None = None,
    trip_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
) -> PlaceSearchResult:
    settings, engine = request.app.state.settings, request.app.state.engine
    rate_limit.hit(engine, "places_search", str(user.id))
    if category is not None and category not in geoapify.SEARCH_KINDS:
        raise _invalid("category", "Pick one of: " + ", ".join(geoapify.SEARCH_KINDS) + ".")
    if not q and not category:
        raise _invalid("q", "Type a place name or pick a category.")
    area = None
    if destination_id is not None:
        row = session.execute(
            text("SELECT lat, lon, bbox, geoapify_place_id, country_code::text FROM trip_destinations WHERE id = :d AND (CAST(:t AS uuid) IS NULL OR trip_id = :t)"),
            {"d": destination_id, "t": trip_id},
        ).first()
        if row is None:
            raise NotFound()
        lat, lon = lat if lat is not None else row[0], lon if lon is not None else row[1]
        area = geoapify.Area(place_id=row[3], bbox=tuple(row[2]) if row[2] else None, country_code=row[4] if row[4] and not row[3] and not row[2] else None)
    if lat is None or lon is None:
        raise _invalid("lat", "Send lat and lon, or a destination_id.")
    lat, lon = round(lat, 3), round(lon, 3)
    key = service.key_of("geoapify", "places_search", q or "", category or "", lat, lon, radius_m, area)
    cached = service.read(settings, user.id, key)
    hit = cached is not None
    if cached is None:
        service.check_quota(engine, user.id, service.daily_limit(session, user.id, trip_id))
        found = service.fetch_search(settings, q, category, lat, lon, radius_m, area)
        service.spend(engine, user.id)  # only a call that reached the provider counts
        cached = [p.model_dump(mode="json") for p in found]
        service.write(settings, user.id, key, "geoapify", "places_search", cached, ATTRIBUTION)
        service.cache_places(settings, user.id, found)
    places = [_out(PlaceOut(**p)) for p in cached[:limit]]
    return PlaceSearchResult(places=places, cached=hit, sorted_by="relevance" if q else "distance")


@router.get("/places/{place_id}", response_model=PlaceDetails)
def details(request: Request, place_id: str, user: CurrentUser, session: DbSession) -> PlaceDetails:
    settings, engine, gid = request.app.state.settings, request.app.state.engine, _geoapify_id(place_id)
    place = service.cached_place(settings, user.id, gid)
    if place is None or not place.has_details:
        try:
            service.check_quota(engine, user.id, service.daily_limit(session, user.id, None))
        except ApiError:
            if place is None:
                raise
            # over the daily cap: a cached basic place still opens, with no provider call
            fetched, spent = None, False
        else:
            fetched, spent = service.fetch_details(settings, gid), True
            service.spend(engine, user.id)
        if spent:
            if fetched is None and place is None:
                raise NotFound("We could not find that place.")
            # no details from the provider: keep the row marked as looked up, so later opens skip the provider
            place = (fetched or place).model_copy(update={"has_details": True})
            service.cache_places(settings, user.id, [place])
    wiki = service.cached_wiki(settings, user.id, place)
    return PlaceDetails(**_out(place).model_dump(), wiki=Wiki(**wiki) if wiki else None)


# --- saved places (the ideas list) ---

_SELECT = (
    "SELECT s.id, s.place_provider, s.place_id, s.name, s.category::text AS category, s.address, s.lat, s.lon, s.website, s.note, s.place_data, s.saved_by, s.created_at, "
    "NULLIF(p.display_name, '') AS added_name FROM saved_places s LEFT JOIN trip_member_profiles p ON p.trip_id = s.trip_id AND p.user_id = s.saved_by "
)


def _saved(r) -> SavedPlace:
    extra = r["place_data"] or {}
    ref = SavedPlaceRef(
        provider=r["place_provider"], id=(_PREFIX + r["place_id"]) if r["place_provider"] == "geoapify" else r["place_id"], name=r["name"], category=r["category"],
        address=r["address"], lat=r["lat"], lon=r["lon"], website=r["website"], **{k: extra[k] for k in _EXTRA if extra.get(k) is not None},
    )
    return SavedPlace(
        id=r["id"], place=ref, note=r["note"] or None, created_at=r["created_at"],
        added_by=Attribution(id=r["saved_by"], display_name=r["added_name"]) if r["saved_by"] else None,
    )


@router.get("/trips/{trip_id}/saved-places", response_model=SavedPlacePage)
def list_saved(
    access: Annotated[TripAccess, require_trip("viewer")],
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> SavedPlacePage:
    start = decode_offset(cursor)
    rows = session.execute(
        text(_SELECT + "WHERE s.trip_id = :t ORDER BY s.created_at DESC, s.id DESC LIMIT :n OFFSET :o"), {"t": access.trip.id, "n": limit + 1, "o": start}
    ).mappings().all()
    more = len(rows) > limit
    nxt = encode_offset(start + limit) if more else None
    return SavedPlacePage(items=[_saved(r) for r in rows[:limit]], next_cursor=nxt, has_more=more)


@router.post("/trips/{trip_id}/saved-places", response_model=SavedPlace, status_code=201)
def save_place(body: SavedPlaceIn, request: Request, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession) -> SavedPlace:
    gid = _geoapify_id(body.place_id)
    place = service.cached_place(request.app.state.settings, user.id, gid)
    if place is None:
        raise ApiError(404, "place_not_found", "Search for that place again, then save it.")
    tid = access.trip.id
    extra = {k: v for k, v in place.model_dump().items() if k in _EXTRA and v not in (None, [], False)}
    new_id = session.execute(
        text(
            """INSERT INTO saved_places (trip_id, place_provider, place_id, name, category, address, lat, lon, website, note, place_data, saved_by)
               VALUES (:t, 'geoapify', :pid, :name, :cat, :addr, :lat, :lon, :web, :note, CAST(:pd AS jsonb), :u)
               ON CONFLICT (trip_id, place_provider, place_id) DO NOTHING RETURNING id"""
        ),
        {"t": tid, "pid": gid, "name": place.name[:200], "cat": place.category, "addr": place.address, "lat": place.lat, "lon": place.lon, "web": place.website,
         "note": body.note or "", "pd": json.dumps(extra), "u": user.id},
    ).scalar()
    if new_id is None:  # saved before: idempotent on trip and place
        new_id = session.execute(text("SELECT id FROM saved_places WHERE trip_id = :t AND place_provider = 'geoapify' AND place_id = :pid"), {"t": tid, "pid": gid}).scalar_one()
    else:
        record(session, tid, user.id, "added", "saved_place", new_id, "saved a place")
    return _saved(session.execute(text(_SELECT + "WHERE s.id = :i"), {"i": new_id}).mappings().one())


@router.delete("/trips/{trip_id}/saved-places/{saved_id}", status_code=204)
def delete_saved(saved_id: uuid.UUID, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession) -> Response:
    gone = session.execute(text("DELETE FROM saved_places WHERE id = :i AND trip_id = :t RETURNING id"), {"i": saved_id, "t": access.trip.id}).scalar()
    if gone is None:
        raise NotFound()
    record(session, access.trip.id, user.id, "removed", "saved_place", saved_id, "removed a saved place")
    return Response(status_code=204)
