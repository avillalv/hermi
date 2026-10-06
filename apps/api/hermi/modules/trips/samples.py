# ruff: noqa: E501  (long SQL strings and comments)
"""Public sample trips (04 section 5.28, WF-133.2): list, read-only detail and "Use this plan" copy.

A sample trip is an ordinary trip owned by the Hermi content account, so the app role cannot read it: reads and the copy source
go through the `sample_read` system session, and the copy itself is written by the caller's own RLS session."""

import json
from datetime import date, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from hermi import analytics, db
from hermi.deps import CurrentUser, DbSession
from hermi.errors import NotFound
from hermi.modules.billing import service as billing
from hermi.modules.collaboration.activity import record
from hermi.modules.collaboration.schemas import Presentation
from hermi.modules.collaboration.service import build_presentation
from hermi.modules.notifications.waitlist import client_ip
from hermi.modules.trips import repo
from hermi.modules.trips.router import COPIED_DESTINATION_FIELDS, _my_travelers, full_trip
from hermi.modules.trips.schemas import Trip
from hermi.pagination import decode_offset, encode_offset
from hermi.security.rate_limit import hit

router = APIRouter(tags=["public"])

Slug = Annotated[str, Path(min_length=1, max_length=120, pattern="^[a-z0-9]+(-[a-z0-9]+)*$")]
CACHE = "public, max-age=3600"


class SampleCover(BaseModel):
    image_url: str
    destination_name: str
    attribution: str | None


class SampleTripSummary(BaseModel):
    slug: str
    title: str
    destination_name: str
    days: int
    summary: str
    cover: SampleCover | None
    tags: list[str]
    suits: str


class SampleTripPage(BaseModel):
    items: list[SampleTripSummary]
    next_cursor: str | None
    has_more: bool


class SampleCta(BaseModel):
    label: Literal["Plan your own"] = "Plan your own"
    url: str


class SampleTrip(BaseModel):
    slug: str
    label: Literal["Sample trip"] = "Sample trip"
    title: str
    summary: str
    presentation: Presentation
    book_slide: None = None
    cta: SampleCta
    updated_at: str


class SampleCopy(BaseModel):
    start_date: date | None = None


def _json(v) -> str | None:
    return None if v is None else json.dumps(v)


@router.get("/public/sample-trips", response_model=SampleTripPage)
def list_sample_trips(
    request: Request,
    response: Response,
    destination: Annotated[str | None, Query(max_length=120)] = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> SampleTripPage:
    hit(request.app.state.engine, "read_ip", client_ip(request))
    offset = decode_offset(cursor)
    with db.system_session("sample_read", settings=request.app.state.settings, route="GET /v1/public/sample-trips") as s:
        rows = (
            s.execute(
                text(
                    "SELECT st.slug, st.title, st.summary, st.cover_image_url, st.cover_attribution, st.tags, coalesce(st.suits, '') AS suits, "
                    "       coalesce(d.name, '') AS destination_name, "
                    "       (SELECT count(*) FROM itinerary_days x WHERE x.trip_id = st.trip_id) AS days "
                    "  FROM sample_trips st LEFT JOIN trip_destinations d ON d.trip_id = st.trip_id AND d.position = 0 "
                    " WHERE st.status = 'published' "
                    "   AND (CAST(:tag AS text) IS NULL OR CAST(:tag AS text) = ANY(st.tags)) "
                    "   AND (CAST(:dest AS text) IS NULL OR EXISTS (SELECT 1 FROM trip_destinations y WHERE y.trip_id = st.trip_id AND strpos(lower(y.name), lower(CAST(:dest AS text))) > 0)) "
                    " ORDER BY st.sort_order, st.published_at DESC, st.id LIMIT :n OFFSET :o"
                ),
                {"tag": tag, "dest": destination, "n": limit + 1, "o": offset},
            )
            .mappings()
            .all()
        )
    page = rows[:limit]
    response.headers["Cache-Control"] = CACHE
    more = len(rows) > limit
    return SampleTripPage(
        items=[
            SampleTripSummary(
                slug=r["slug"],
                title=r["title"],
                destination_name=r["destination_name"],
                days=r["days"],
                summary=r["summary"],
                cover=SampleCover(image_url=r["cover_image_url"], destination_name=r["destination_name"], attribution=r["cover_attribution"]) if r["cover_image_url"] else None,
                tags=list(r["tags"]),
                suits=r["suits"],
            )
            for r in page
        ],
        next_cursor=encode_offset(offset + limit) if more else None,
        has_more=more,
    )


@router.get("/public/sample-trips/{slug}", response_model=SampleTrip)
def get_sample_trip(slug: Slug, request: Request, response: Response) -> SampleTrip:
    hit(request.app.state.engine, "read_ip", client_ip(request))
    settings = request.app.state.settings
    with db.system_session("sample_read", settings=settings, route="GET /v1/public/sample-trips/{slug}") as s:
        st = (
            s.execute(
                text("SELECT slug, title, summary, trip_id, updated_at FROM sample_trips WHERE slug = :s AND status = 'published'"),
                {"s": slug},
            )
            .mappings()
            .first()
        )
        if st is None:
            raise NotFound()
        # no people, no notes, no stay addresses; item prices stay as example prices and updated_at is the date they were observed
        pres = build_presentation(s, st["trip_id"], redact_address=True, redact_prices=False, redact_notes=True, redact_people=True, show_book_slide=False)
    pres.trip.travelers = []
    response.headers["Cache-Control"] = CACHE
    return SampleTrip(
        slug=st["slug"],
        title=st["title"],
        summary=st["summary"],
        presentation=pres,
        cta=SampleCta(url=settings.public_web_url.rstrip("/")),
        updated_at=st["updated_at"].isoformat(),
    )


def _read_source(settings, slug: str) -> dict:
    """The sample's destinations, days, saved places and items as plain rows (enum columns as text), or 404."""
    with db.system_session("sample_read", settings=settings, route="POST /v1/public/sample-trips/{slug}/copy") as s:
        st = (
            s.execute(
                text(
                    "SELECT st.title, t.id AS trip_id, t.start_date, t.end_date FROM sample_trips st JOIN trips t ON t.id = st.trip_id "
                    " WHERE st.slug = :s AND st.status = 'published'"
                ),
                {"s": slug},
            )
            .mappings()
            .first()
        )
        if st is None:
            raise NotFound()

        def rows(sql: str) -> list[dict]:
            return [dict(r) for r in s.execute(text(sql), {"t": st["trip_id"]}).mappings()]

        return {
            **st,
            "destinations": rows("SELECT id, " + ", ".join(COPIED_DESTINATION_FIELDS) + " FROM trip_destinations WHERE trip_id = :t ORDER BY position"),
            "days": rows("SELECT day, title, destination_id FROM itinerary_days WHERE trip_id = :t ORDER BY day"),
            "places": rows(
                "SELECT id, place_provider, place_id, name, category::text AS category, address, lat, lon, website, place_data "
                "FROM saved_places WHERE trip_id = :t ORDER BY created_at, id"
            ),
            "items": rows(
                "SELECT day, start_time, end_time, sort_order, title, category::text AS category, status::text AS status, location_name, address, lat, lon, url, "
                "       saved_place_id, place_provider, place_id, place_data FROM itinerary_items WHERE trip_id = :t AND day IS NOT NULL ORDER BY day, sort_order, id"
            ),
        }


@router.post("/public/sample-trips/{slug}/copy", response_model=Trip, status_code=201)
def copy_sample_trip(slug: Slug, body: SampleCopy, request: Request, user: CurrentUser, session: DbSession, response: Response) -> Trip:
    """"Use this plan": days, items and saved places become an ordinary trip owned by the caller. Never flights, fares, prices or notes."""
    src = _read_source(request.app.state.settings, slug)
    billing.require_active_trip_slot(session, user.id)  # the same gate as POST /trips: 402 limit_reached with the third_trip paywall
    delta = timedelta(0) if body.start_date is None or src["start_date"] is None else body.start_date - src["start_date"]
    shift = lambda d: None if d is None else d + delta  # noqa: E731
    trip = repo.create_trip(
        session,
        user.id,
        {"name": src["title"][:120], "start_date": shift(src["start_date"]), "end_date": shift(src["end_date"]), "notes": "", "home_currency": repo.user_home_currency(session, user.id)},
        [{k: v for k, v in d.items() if k != "id" and v is not None} for d in src["destinations"]],
        _my_travelers(session, user.id, None),
    )
    dest_ids = {old["id"]: new.id for old, new in zip(src["destinations"], repo.destinations_of(session, trip.id), strict=True)}
    for d in src["days"]:
        session.execute(
            text("INSERT INTO itinerary_days (trip_id, day, title, destination_id, updated_by) VALUES (:t, :d, :title, :dest, :u)"),
            {"t": trip.id, "d": shift(d["day"]), "title": d["title"], "dest": dest_ids.get(d["destination_id"]), "u": user.id},
        )
    place_ids = {}
    for p in src["places"]:
        place_ids[p["id"]] = session.execute(
            text(
                "INSERT INTO saved_places (trip_id, place_provider, place_id, name, category, address, lat, lon, website, place_data, saved_by) "
                "VALUES (:t, :pp, :pid, :n, CAST(:c AS item_category), :a, :lat, :lon, :w, CAST(:pd AS jsonb), :u) RETURNING id"
            ),
            {"t": trip.id, "pp": p["place_provider"], "pid": p["place_id"], "n": p["name"], "c": p["category"], "a": p["address"], "lat": p["lat"], "lon": p["lon"],
             "w": p["website"], "pd": _json(p["place_data"]), "u": user.id},
        ).scalar_one()
    for i in src["items"]:  # no cost, no notes, no check evidence: those are the sample author's, not the caller's
        session.execute(
            text(
                "INSERT INTO itinerary_items (trip_id, day, start_time, end_time, sort_order, title, category, status, location_name, address, lat, lon, url, "
                "       saved_place_id, place_provider, place_id, place_data, source, created_by, updated_by) "
                "VALUES (:t, :d, :st, :et, :so, :title, CAST(:c AS item_category), CAST(:s AS item_status), :ln, :a, :lat, :lon, :url, :sp, :pp, :pid, CAST(:pd AS jsonb), 'manual', :u, :u)"
            ),
            {"t": trip.id, "d": shift(i["day"]), "st": i["start_time"], "et": i["end_time"], "so": i["sort_order"], "title": i["title"], "c": i["category"], "s": "planned" if i["status"] == "booked" else i["status"],
             "ln": i["location_name"], "a": i["address"], "lat": i["lat"], "lon": i["lon"], "url": i["url"], "sp": place_ids.get(i["saved_place_id"]),
             "pp": i["place_provider"], "pid": i["place_id"], "pd": _json(i["place_data"]), "u": user.id},
        )
    record(session, trip.id, user.id, "created", "trip", trip.id, "created the trip from a sample trip")
    analytics.capture("sample_trip_copied", user.id, {"slug": slug, "was_guest": False}, opted_out=request.headers.get("sec-gpc") == "1")
    response.headers["Location"] = f"/v1/trips/{trip.id}"
    return full_trip(session, trip, "owner", user.id)
