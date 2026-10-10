# ruff: noqa: E501  (long SQL strings and docstrings)
"""POST /v1/me/claim (04 section 5.1, F-ACC-3, WF-062.1): the guest's one local trip becomes the caller's own trip, once.

Guest data never reaches the server before this call. The rows are inserted as the caller from the request payload (RLS, 03
section 6.1.1), so the payload can never name another owner. `claim_id` is the idempotency key: the first result is stored in
`idempotency_keys` (key `claim:<claim_id>`, 30 days) in the same transaction as the import, so a double submit, sequential or
parallel, returns the first result with `Idempotent-Replay: true` and imports nothing twice. Counts are counted here, never read
from the payload. A claim over the tier's active trip limit is archived, not dropped.
"""

import hashlib
import json
import uuid
from datetime import UTC, date, datetime, time
from typing import Annotated, Literal

from fastapi import APIRouter, Request, Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi import analytics
from hermi.deps import CurrentUser, DbSession
from hermi.errors import ApiError
from hermi.modules.auth import guest
from hermi.modules.billing import service as billing
from hermi.modules.collaboration.activity import record
from hermi.modules.trips import repo
from hermi.modules.trips.schemas import DestinationIn

router = APIRouter(tags=["trips"])

KEEP_DAYS = 30
Category = Literal["sights", "museum", "food", "nature", "nightlife", "shopping", "travel", "other"]
Status = Literal["idea", "planned", "booked"]
Str = Annotated[str, StringConstraints(strip_whitespace=True)]


def _both(lat: float | None, lon: float | None) -> None:
    if (lat is None) != (lon is None):
        raise ValueError("Give both latitude and longitude, or neither.")


class GuestPlace(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ref: Str | None = Field(
        default=None, max_length=64
    )  # the guest app's local key, so items can point at the place
    name: Str = Field(min_length=1, max_length=200)
    category: Category = "other"
    address: Str | None = Field(default=None, max_length=500)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    website: Str | None = Field(default=None, max_length=2000, pattern=r"^https?://")
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _ll(self) -> "GuestPlace":
        _both(self.lat, self.lon)
        return self


class GuestItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    title: Str = Field(min_length=1, max_length=200)
    day: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    sort_order: float = Field(default=0, ge=-1e9, le=1e9)
    category: Category = "other"
    status: Status = "idea"
    location_name: Str | None = Field(default=None, max_length=200)
    address: Str | None = Field(default=None, max_length=500)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    url: Str | None = Field(default=None, max_length=2000, pattern=r"^https?://")
    notes: str = Field(default="", max_length=5000)
    place_ref: Str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _shape(self) -> "GuestItem":
        _both(self.lat, self.lon)
        if self.day is None and self.start_time is not None:
            raise ValueError("A time needs a day.")
        if self.start_time is None and self.end_time is not None:
            raise ValueError("An end time needs a start time.")
        return self


class GuestDay(BaseModel):
    model_config = ConfigDict(extra="ignore")
    day: date
    title: str = Field(default="", max_length=120)


class GuestPerson(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Str = Field(min_length=1, max_length=60)


class TripJson(BaseModel):
    """The guest app's local trip document, validated like TripCreate plus the guest caps (1 trip, 200 items)."""

    model_config = ConfigDict(extra="ignore")
    name: Str = Field(min_length=1, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    home_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    notes: str = Field(default="", max_length=10000)
    destinations: list[DestinationIn] = Field(default_factory=list, max_length=12)
    days: list[GuestDay] = Field(default_factory=list, max_length=400)
    places: list[GuestPlace] = Field(default_factory=list, max_length=200)
    items: list[GuestItem] = Field(default_factory=list, max_length=200)
    people: list[GuestPerson] = Field(default_factory=list, max_length=20)

    @field_validator("destinations")
    @classmethod
    def _no_ids(cls, v: list[DestinationIn]) -> list[DestinationIn]:
        for d in v:
            d.id = None  # a guest names no server rows
        return v

    @model_validator(mode="after")
    def _shape(self) -> "TripJson":
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Give both dates, or neither.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("The end date must be on or after the start date.")
        refs = [p.ref for p in self.places if p.ref]
        if len(refs) != len(set(refs)):
            raise ValueError("Place references must be unique.")
        if any(i.place_ref is not None and i.place_ref not in refs for i in self.items):
            raise ValueError("An item points at a place that is not in the trip.")
        return self


class ClaimIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trip: TripJson
    claim_id: uuid.UUID
    merge: bool | None = None
    attest_key_id: Str | None = Field(
        default=None, max_length=256
    )  # the device key whose guest AI use counts on this claim


class ClaimResult(BaseModel):
    trip_id: uuid.UUID | None
    people_imported: int
    items_imported: int
    archived: bool = False  # the trip was over the active trip limit and is kept archived


def _json(v) -> str | None:
    return None if v is None else json.dumps(v)


def _import(session: Session, user_id: uuid.UUID, t: TripJson) -> ClaimResult:
    over = billing.count_active_owned(session, user_id) >= billing.limit_of(
        billing.user_limits(session, user_id), "active_trips"
    )
    values: dict = {
        "name": t.name,
        "start_date": t.start_date,
        "end_date": t.end_date,
        "notes": t.notes,
        "home_currency": t.home_currency or repo.user_home_currency(session, user_id),
    }
    if over:
        values.update(status="archived", archived_at=datetime.now(UTC))
    have = {
        n.casefold()
        for n in session.scalars(
            text("SELECT name FROM people WHERE owner_user_id = :u"), {"u": user_id}
        )
    }
    new_people = []
    for p in t.people:
        if p.name.casefold() not in have:
            have.add(p.name.casefold())
            new_people.append(p.name)
    people_ids = [
        session.execute(
            text("INSERT INTO people (owner_user_id, name) VALUES (:u, :n) RETURNING id"),
            {"u": user_id, "n": n},
        ).scalar_one()
        for n in new_people
    ]
    travelers = [*repo.my_person_ids(session, user_id)[:1], *people_ids]
    dests = [
        {k: v for k, v in d.model_dump().items() if k != "id" and v is not None}
        for d in t.destinations
    ]
    trip = repo.create_trip(session, user_id, values, dests, list(dict.fromkeys(travelers)))
    days = {d.day: d.title for d in t.days}
    for i in t.items:
        if i.day is not None:
            days.setdefault(i.day, "")
    for day, title in sorted(days.items()):
        session.execute(
            text(
                "INSERT INTO itinerary_days (trip_id, day, title, updated_by) VALUES (:t, :d, :title, :u)"
            ),
            {"t": trip.id, "d": day, "title": title, "u": user_id},
        )
    place_ids: dict[str, uuid.UUID] = {}
    for n, p in enumerate(t.places):
        place_ids[p.ref or f"#{n}"] = session.execute(
            text(
                "INSERT INTO saved_places (trip_id, place_provider, place_id, name, category, address, lat, lon, website, note, saved_by) "
                "VALUES (:t, 'manual', :pid, :n, CAST(:c AS item_category), :a, :lat, :lon, :w, :note, :u) RETURNING id"
            ),
            {
                "t": trip.id,
                "pid": f"guest-{n}",
                "n": p.name,
                "c": p.category,
                "a": p.address,
                "lat": p.lat,
                "lon": p.lon,
                "w": p.website,
                "note": p.note,
                "u": user_id,
            },
        ).scalar_one()
    for n, i in enumerate(t.items):
        session.execute(
            text(
                "INSERT INTO itinerary_items (trip_id, day, start_time, end_time, sort_order, title, category, status, location_name, address, lat, lon, url, notes, "
                "       saved_place_id, source, created_by, updated_by) "
                "VALUES (:t, :d, :st, :et, :so, :title, CAST(:c AS item_category), CAST(:s AS item_status), :ln, :a, :lat, :lon, :url, :notes, :sp, 'manual', :u, :u)"
            ),
            {
                "t": trip.id,
                "d": i.day,
                "st": i.start_time,
                "et": i.end_time,
                "so": i.sort_order or n,
                "title": i.title,
                "c": i.category,
                "s": i.status,
                "ln": i.location_name,
                "a": i.address,
                "lat": i.lat,
                "lon": i.lon,
                "url": i.url,
                "notes": i.notes,
                "sp": place_ids.get(i.place_ref) if i.place_ref else None,
                "u": user_id,
            },
        )
    record(
        session, trip.id, user_id, "created", "trip", trip.id, "created the trip from a guest trip"
    )
    return ClaimResult(
        trip_id=trip.id, people_imported=len(people_ids), items_imported=len(t.items), archived=over
    )


@router.post(
    "/me/claim",
    response_model=ClaimResult,
    responses={
        409: {
            "description": "state_conflict: the account already has trips and `merge` was not given"
        }
    },
)
def claim_guest_trip(
    body: ClaimIn, request: Request, response: Response, user: CurrentUser, session: DbSession
) -> ClaimResult:
    key = f"claim:{body.claim_id}"
    digest = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    mine = session.execute(
        text(
            "INSERT INTO idempotency_keys (user_id, key, method, path, request_hash, expires_at) "
            "VALUES (:u, :k, 'POST', '/v1/me/claim', :h, now() + make_interval(days => :d)) "
            "ON CONFLICT (user_id, key) DO NOTHING RETURNING 1"
        ),
        {"u": user.id, "k": key, "h": digest, "d": KEEP_DAYS},
    ).first()
    if (
        mine is None
    ):  # a concurrent first request has committed by now: the insert waited on its row
        first = session.execute(
            text(
                "SELECT response -> 'body' FROM idempotency_keys WHERE user_id = :u AND key = :k AND state = 'completed'"
            ),
            {"u": user.id, "k": key},
        ).scalar_one_or_none()
        if first is None:
            raise ApiError(
                409,
                "idempotency_in_progress",
                "That request is still running.",
                {"Retry-After": "1"},
            )
        response.headers["Idempotent-Replay"] = "true"
        return ClaimResult(**first)

    trips = session.execute(
        text("SELECT count(*) FROM trips WHERE owner_user_id = :u AND deleted_at IS NULL"),
        {"u": user.id},
    ).scalar_one()
    if trips and body.merge is None:
        people = session.execute(
            text("SELECT count(*) FROM people WHERE owner_user_id = :u AND NOT is_self"),
            {"u": user.id},
        ).scalar_one()
        raise ApiError(
            409,
            "state_conflict",
            f"You already have {trips} {'trip' if trips == 1 else 'trips'}. Add this one too?",
            extra={"counts": {"trips": trips, "people": people}},
        )
    result = (
        _import(session, user.id, body.trip)
        if body.merge is not False
        else ClaimResult(trip_id=None, people_imported=0, items_imported=0)
    )
    session.execute(
        text(
            "UPDATE idempotency_keys SET state = 'completed', status_code = 200, response = CAST(:r AS jsonb) "
            "WHERE user_id = :u AND key = :k"
        ),
        {
            "u": user.id,
            "k": key,
            "r": json.dumps({"body": json.loads(result.model_dump_json()), "headers": {}}),
        },
    )
    guest.count_against_free(request.app.state.settings, user.id, body.attest_key_id)
    analytics.capture(
        "guest_claimed",
        user.id,
        {"trip_count_bucket": "1" if result.trip_id else "0"},
        opted_out=request.headers.get("sec-gpc") == "1",
    )
    return result
