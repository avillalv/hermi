# ruff: noqa: E501  (long SQL strings)
"""Lodging (04 section 5.9): saved stays, hearts, compare and link parsing.

The server never fetches Airbnb, Vrbo or Booking.com pages (or any stay page) and never rewrites a pasted link: `url` is stored as typed.
Lists are sorted by what the caller asks for (`created`, `price`, `rating`, `votes`) and the response says which, never by commission.
`/lodging/{option_id}` carries no trip id: `_via_option` resolves the stay's trip, then runs the same `require_trip` check as every trip route.
"""

import json
import math
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.collaboration.activity import record
from hermi.modules.collaboration.schemas import Attribution
from hermi.modules.flights.schemas import Money
from hermi.modules.lodging import service
from hermi.modules.lodging.schemas import (
    CompareRow,
    LinkParse,
    Lodging,
    LodgingCompare,
    LodgingIn,
    LodgingPage,
    LodgingUpdate,
    ParseLinkIn,
    Sort,
    Status,
    Vote,
    VoteIn,
    VoteSummary,
)
from hermi.pagination import decode_offset, encode_offset
from hermi.security.preconditions import resolve_version, version_conflict

router = APIRouter(tags=["lodging"])

_NIGHTS = "(l.check_out - l.check_in)"
# Effective prices: what the user typed, or the other one divided or multiplied by the nights.
_TOTAL = f"COALESCE(l.price_total_minor, l.price_per_night_minor * {_NIGHTS})"
_PER_NIGHT = f"COALESCE(l.price_per_night_minor, round(l.price_total_minor::numeric / NULLIF({_NIGHTS}, 0))::bigint)"
_SELECT = (
    "SELECT l.id, l.trip_id, l.title, l.url, l.site, l.check_in, l.check_out, l.guests, l.currency::text AS currency, l.photos, l.location_name, l.lat, l.lon, "
    "l.bedrooms, l.beds, l.baths::float8 AS baths, l.rating::float8 AS rating, l.review_count, l.notes, l.pros, l.cons, l.status::text AS status, l.favorite, "
    "l.added_via, l.version, l.created_by, l.created_at, l.updated_at, NULLIF(p.display_name, '') AS added_name, "
    f"{_NIGHTS} AS nights, {_TOTAL} AS total_minor, {_PER_NIGHT} AS per_night_minor, "
    f"fx_convert_minor({_TOTAL}, l.currency::text, :home) AS home_total_minor, fx_convert_minor({_PER_NIGHT}, l.currency::text, :home) AS home_pn_minor, "
    "(SELECT count(*) FROM lodging_votes v WHERE v.lodging_id = l.id) AS hearts "
    "FROM lodging_options l LEFT JOIN trip_member_profiles p ON p.trip_id = l.trip_id AND p.user_id = l.created_by "
)
_ORDER = {
    "created": "l.created_at DESC, l.id",
    "price": "home_pn_minor ASC NULLS LAST, l.created_at DESC, l.id",
    "rating": "l.rating DESC NULLS LAST, l.created_at DESC, l.id",
    "votes": "hearts DESC, l.created_at DESC, l.id",
}


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(422, "validation_failed", "Some fields need another look.", extra={"errors": [{"field": field, "code": "invalid", "message": message}]})


def _money(minor, currency) -> Money | None:
    return Money(amount_minor=minor, currency=currency) if minor is not None and currency else None


def _out(r, votes: list[Vote]) -> Lodging:
    return Lodging(
        **{k: r[k] for k in ("id", "trip_id", "title", "url", "site", "check_in", "check_out", "nights", "guests", "location_name", "lat", "lon", "bedrooms", "beds", "baths",
                             "rating", "review_count", "notes", "pros", "cons", "status", "favorite", "added_via", "version", "created_at", "updated_at")},
        photos=r["photos"] or [],
        price_total=_money(r["total_minor"], r["currency"]),
        price_per_night=_money(r["per_night_minor"], r["currency"]),
        price_home_total=_money(r["home_total_minor"], r["home"]),
        votes=votes,
        vote_summary=VoteSummary(hearts=len(votes)),
        added_by=Attribution(id=r["created_by"], display_name=r["added_name"]) if r["created_by"] else None,
    )


def _load(session: Session, trip, where: str, params: dict, order: str = "l.created_at DESC, l.id", tail: str = "", extra: dict | None = None) -> list[Lodging]:
    rows = session.execute(text(_SELECT + f"WHERE l.trip_id = :t AND {where} ORDER BY {order} {tail}"), {"t": trip.id, "home": trip.home_currency, **params, **(extra or {})}).mappings().all()
    ids = [r["id"] for r in rows]
    votes: dict[uuid.UUID, list[Vote]] = {i: [] for i in ids}
    if ids:
        for v in session.execute(text("SELECT lodging_id, user_id, person_id FROM lodging_votes WHERE lodging_id = ANY(:ids) ORDER BY created_at, id"), {"ids": ids}).mappings():
            votes[v["lodging_id"]].append(Vote(user_id=v["user_id"], person_id=v["person_id"]))
    return [_out({**r, "home": trip.home_currency}, votes[r["id"]]) for r in rows]


def _get(session: Session, trip, option_id: uuid.UUID) -> Lodging:
    found = _load(session, trip, "l.id = :i", {"i": option_id})
    if not found:
        raise NotFound()
    return found[0]


def _via_option(min_role: str):
    """Depends() resolving the trip of a stay id (404 when not visible), then the role check (403 below `min_role`)."""
    check = require_trip(min_role).dependency

    def access(session: DbSession, option_id: uuid.UUID) -> TripAccess:
        trip_id = session.execute(text("SELECT trip_id FROM lodging_options WHERE id = :i"), {"i": option_id}).scalar()
        if trip_id is None:
            raise NotFound()
        return check(trip_id, session)

    access.__require_trip__ = min_role
    return Depends(access)


@contextmanager
def _conflicts(session: Session):
    """A race past the pre-checks hits a unique index (one Booked stay, duplicate link): the same 409 as the checks give."""
    try:
        with session.begin_nested():  # a savepoint, so the request transaction survives for the error response
            yield
    except IntegrityError:
        raise ApiError(409, "state_conflict", "Another stay is already booked, or that link is already saved. Refresh and try again.") from None


def _check_url(url: str | None) -> None:
    if url and (problem := service.url_problem(url)):
        raise _invalid("url", problem)


def _check_stay(merged: dict) -> None:
    if merged["check_in"] and merged["check_out"] and merged["check_out"] <= merged["check_in"]:
        raise _invalid("check_out", "Check out must be after check in.")
    if (merged["lat"] is None) != (merged["lon"] is None):
        raise _invalid("lat", "Send both lat and lon, or neither.")


def _prices(total, per_night, kept_total=None, kept_per_night=None, kept_currency=None):
    """(total minor, per night minor, currency) from the sent Money values; an unsent one keeps its stored value when the currency still matches."""
    sent = [m for m in (total, per_night) if m is not None]
    if len({m.currency for m in sent}) > 1:
        raise _invalid("price_per_night", "Use one currency for the total and the nightly price.")
    currency = sent[0].currency if sent else kept_currency
    if sent and kept_currency not in (None, currency):
        kept_total = kept_per_night = None  # a new currency makes the stored amounts meaningless
    return (
        total.amount_minor if total is not None else kept_total,
        per_night.amount_minor if per_night is not None else kept_per_night,
        currency if (total or per_night or kept_total is not None or kept_per_night is not None) else None,
    )


def _one_booked(session: Session, trip_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    other = session.execute(text("SELECT id FROM lodging_options WHERE trip_id = :t AND status = 'booked' AND id IS DISTINCT FROM :x"), {"t": trip_id, "x": except_id}).scalar()
    if other is not None:
        raise ApiError(409, "state_conflict", "Another stay is already booked. Change it first.", extra={"booked_id": str(other)})


def _no_duplicate(session: Session, trip_id: uuid.UUID, url: str | None, except_id: uuid.UUID | None = None) -> None:
    norm = service.normalized(url)
    other = session.execute(text("SELECT id FROM lodging_options WHERE trip_id = :t AND url_normalized = :n AND id IS DISTINCT FROM :x"), {"t": trip_id, "n": norm, "x": except_id}).scalar() if norm else None
    if other is not None:
        raise ApiError(409, "state_conflict", "That link is already saved on this trip.", extra={"existing_id": str(other)})


# --- stays ----------------------------------------------------------------------------------------------------------------


@router.get("/trips/{trip_id}/lodging", response_model=LodgingPage)
def list_lodging(
    access: Annotated[TripAccess, require_trip("viewer")],
    session: DbSession,
    status: Status | None = None,
    sort: Sort = "created",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
    updated_since: datetime | None = None,
) -> LodgingPage:
    # shortcut: the cursor is an offset (unsigned base64), as for items; deleted stays are not returned as tombstones yet. Upgrade: keyset paging and a tombstone feed.
    start = decode_offset(cursor)
    rows = _load(
        session, access.trip, "(CAST(:st AS text) IS NULL OR l.status::text = :st) AND (CAST(:since AS timestamptz) IS NULL OR l.updated_at > :since)",
        {"st": status, "since": updated_since}, _ORDER[sort], "LIMIT :n OFFSET :o", {"n": limit + 1, "o": start},
    )
    more = len(rows) > limit
    return LodgingPage(items=rows[:limit], next_cursor=encode_offset(start + limit) if more else None, has_more=more, sorted_by=sort)


@router.post("/trips/{trip_id}/lodging", response_model=Lodging, status_code=201)
def create_lodging(body: LodgingIn, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, response: Response) -> Lodging:
    tid = access.trip.id
    _check_url(body.url)
    _check_stay({"check_in": body.check_in, "check_out": body.check_out, "lat": body.lat, "lon": body.lon})
    total, per_night, currency = _prices(body.price_total, body.price_per_night)
    service.require_slot(session, tid)
    _no_duplicate(session, tid, body.url)
    if body.status == "booked":
        _one_booked(session, tid)
    with _conflicts(session):
        new_id = _insert(session, tid, user.id, body, total, per_night, currency)
    record(session, tid, user.id, "added", "lodging", new_id, "saved a stay")
    response.headers["Location"] = f"/v1/lodging/{new_id}"
    out = _get(session, access.trip, new_id)
    response.headers["ETag"] = f'"{out.version}"'
    return out


def _insert(session: Session, tid: uuid.UUID, user_id: uuid.UUID, body: LodgingIn, total, per_night, currency) -> uuid.UUID:
    return session.execute(
        text(
            """INSERT INTO lodging_options (trip_id, title, url, url_normalized, site, check_in, check_out, guests, price_total_minor, price_per_night_minor, currency, photos,
                   location_name, lat, lon, bedrooms, beds, baths, rating, review_count, notes, pros, cons, status, favorite, added_via, created_by, updated_by)
               VALUES (:t, :title, :url, :norm, :site, :ci, :co, :g, :tot, :pn, :cur, CAST(:photos AS jsonb), :loc, :lat, :lon, :bed, :beds, :baths, :rating, :rc,
                   :notes, :pros, :cons, COALESCE(CAST(:status AS lodging_status), 'candidate'), COALESCE(:fav, false), :via, :u, :u) RETURNING id"""
        ),
        {
            "t": tid, "title": body.title, "url": body.url, "norm": service.normalized(body.url), "site": service.site_of(body.url), "ci": body.check_in, "co": body.check_out,
            "g": body.guests, "tot": total, "pn": per_night, "cur": currency, "photos": json.dumps(body.photos or []), "loc": body.location_name, "lat": body.lat, "lon": body.lon,
            "bed": body.bedrooms, "beds": body.beds, "baths": body.baths, "rating": body.rating, "rc": body.review_count, "notes": body.notes or "", "pros": body.pros or "",
            "cons": body.cons or "", "status": body.status, "fav": body.favorite, "via": body.added_via or ("paste" if body.url else "manual"), "u": user_id,
        },
    ).scalar_one()


@router.get("/trips/{trip_id}/lodging/compare", response_model=LodgingCompare)
def compare(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession, ids: str) -> LodgingCompare:
    trip = access.trip
    try:
        wanted = [uuid.UUID(s.strip()) for s in ids.split(",")]
    except ValueError:
        raise _invalid("ids", "Send stay ids separated by commas.") from None
    if len(set(wanted)) != len(wanted) or not 2 <= len(wanted) <= 4:
        raise _invalid("ids", "Pick 2 to 4 different stays.")
    service.require_compare(session, trip.id, len(wanted))
    by_id = {s.id: s for s in _load(session, trip, "l.id = ANY(:ids)", {"ids": wanted})}
    if len(by_id) != len(wanted):
        raise NotFound()
    cols = [by_id[i] for i in wanted]
    # shortcut: no distance to itinerary anchors (04 section 5.9 lists them); only the first destination centre. Upgrade: add anchor rows when the itinerary marks anchors (WF-034.3 UI asks for them).
    centre = session.execute(text("SELECT lat, lon FROM trip_destinations WHERE trip_id = :t AND lat IS NOT NULL ORDER BY position LIMIT 1"), {"t": trip.id}).first()

    def km(s: Lodging) -> float | None:
        if centre is None or s.lat is None:
            return None
        p1, p2, dl = math.radians(s.lat), math.radians(centre[0]), math.radians(centre[1] - s.lon)
        a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return round(12742 * math.asin(math.sqrt(a)), 1)

    home_pn = {r["id"]: r["home_pn_minor"] for r in session.execute(text(_SELECT + "WHERE l.trip_id = :t AND l.id = ANY(:ids)"), {"t": trip.id, "home": trip.home_currency, "ids": wanted}).mappings()}
    rows = [
        ("title", "Stay", [s.title for s in cols]),
        ("price_per_night", "Price per night", [home_pn[s.id] for s in cols]),
        ("price_total", "Total price", [s.price_home_total.amount_minor if s.price_home_total else None for s in cols]),
        ("rating", "Rating", [s.rating for s in cols]),
        ("bedrooms", "Bedrooms", [s.bedrooms for s in cols]),
        ("beds", "Beds", [s.beds for s in cols]),
        ("baths", "Baths", [s.baths for s in cols]),
        ("distance_to_center_km", "Distance to the center (km)", [km(s) for s in cols]),
        ("votes", "Hearts", [s.vote_summary.hearts for s in cols]),
        ("pros", "Pros", [s.pros for s in cols]),
        ("cons", "Cons", [s.cons for s in cols]),
    ]
    return LodgingCompare(columns=wanted, rows=[CompareRow(key=k, label=lab, values=v) for k, lab, v in rows], home_currency=trip.home_currency)


@router.get("/lodging/{option_id}", response_model=Lodging)
def get_lodging(option_id: uuid.UUID, access: Annotated[TripAccess, _via_option("viewer")], session: DbSession, response: Response) -> Lodging:
    out = _get(session, access.trip, option_id)
    response.headers["ETag"] = f'"{out.version}"'
    return out


_CASTS = {"photos": "jsonb", "status": "lodging_status"}
_PLAIN = ("title", "check_in", "check_out", "guests", "location_name", "lat", "lon", "bedrooms", "beds", "baths", "rating", "review_count", "notes", "pros", "cons", "status", "favorite")


@router.patch("/lodging/{option_id}", response_model=Lodging)
def update_lodging(
    option_id: uuid.UUID, body: LodgingUpdate, request: Request, access: Annotated[TripAccess, _via_option("editor")], user: CurrentUser, session: DbSession, response: Response
) -> Lodging:
    version = resolve_version(request, body.version)
    tid, sent = access.trip.id, body.model_fields_set
    cur = _get(session, access.trip, option_id)
    merged = {f: getattr(body, f) if f in sent else getattr(cur, f) for f in ("check_in", "check_out", "lat", "lon")}
    _check_stay(merged)
    sets: dict = {f: getattr(body, f) for f in _PLAIN if f in sent}
    if "url" in sent:
        _check_url(body.url)
        _no_duplicate(session, tid, body.url, option_id)
        sets.update(url=body.url, url_normalized=service.normalized(body.url), site=service.site_of(body.url))
    if "photos" in sent:
        sets["photos"] = json.dumps(body.photos)
    if sent & {"price_total", "price_per_night"}:
        raw = session.execute(text("SELECT price_total_minor, price_per_night_minor, currency::text FROM lodging_options WHERE id = :i"), {"i": option_id}).one()
        sets["price_total_minor"], sets["price_per_night_minor"], sets["currency"] = _prices(
            body.price_total if "price_total" in sent else None, body.price_per_night if "price_per_night" in sent else None,
            None if "price_total" in sent else raw[0], None if "price_per_night" in sent else raw[1], raw[2],
        )
    if body.status == "booked" and cur.status != "booked":
        _one_booked(session, tid, option_id)
    sets["updated_by"] = user.id
    assignments = ", ".join(f"{c} = CAST(:{c} AS {_CASTS[c]})" if c in _CASTS else f"{c} = :{c}" for c in sets)  # the column names come from the whitelist above, never from the client
    with _conflicts(session):
        row = session.execute(text(f"UPDATE lodging_options SET {assignments} WHERE id = :id AND trip_id = :t AND version = :v RETURNING id"), {**sets, "id": option_id, "t": tid, "v": version}).first()
    if row is None:
        raise version_conflict(cur.model_dump(mode="json"))
    record(session, tid, user.id, "updated", "lodging", option_id, "changed a stay")
    out = _get(session, access.trip, option_id)
    response.headers["ETag"] = f'"{out.version}"'
    return out


@router.delete("/lodging/{option_id}", status_code=204)
def delete_lodging(option_id: uuid.UUID, access: Annotated[TripAccess, _via_option("editor")], user: CurrentUser, session: DbSession) -> Response:
    session.execute(text("DELETE FROM lodging_options WHERE id = :i AND trip_id = :t"), {"i": option_id, "t": access.trip.id})  # the votes go with it (ON DELETE CASCADE)
    record(session, access.trip.id, user.id, "removed", "lodging", option_id, "removed a stay")
    return Response(status_code=204)


@router.put("/lodging/{option_id}/votes/me", response_model=Lodging)
def put_vote(option_id: uuid.UUID, body: VoteIn, access: Annotated[TripAccess, _via_option("viewer")], user: CurrentUser, session: DbSession) -> Lodging:
    """Heart or un-heart as the caller. A viewer may. One heart per member, so repeating a heart changes nothing."""
    tid = access.trip.id
    if body.voted:
        person = session.execute(
            text("SELECT p.id FROM people p JOIN trip_people tp ON tp.person_id = p.id WHERE tp.trip_id = :t AND p.linked_user_id = :u LIMIT 1"), {"t": tid, "u": user.id}
        ).scalar()
        session.execute(
            text("INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (:l, :t, :p, :u) ON CONFLICT DO NOTHING"),
            {"l": option_id, "t": tid, "p": person, "u": user.id},
        )
    else:
        session.execute(text("DELETE FROM lodging_votes WHERE lodging_id = :l AND user_id = :u"), {"l": option_id, "u": user.id})
    return _get(session, access.trip, option_id)


# --- link parsing ---------------------------------------------------------------------------------------------------------


@router.post("/lodging/parse-link", response_model=LinkParse)
def parse_link(body: ParseLinkIn, user: CurrentUser) -> LinkParse:
    """URL text only: no request is made to the host. Airbnb, Vrbo, Booking.com and the Expedia brands are link only, so a `fetch` flag there is `422 blocked_domain`."""
    if problem := service.url_problem(body.url):
        raise _invalid("url", problem)
    if body.fetch and (brand := service.link_only_brand(service.host_of(body.url))):
        raise ApiError(422, "blocked_domain", f"We do not open {brand} pages. Type the details or use the bookmarklet.")
    parsed = service.parse_link(body.url)
    for f in ("check_in", "check_out", "guests"):
        parsed[f] = getattr(body, f) or parsed[f]
    return LinkParse(**parsed, note=service.NOTE)
