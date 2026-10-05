# ruff: noqa: E501  (long constraint lines)
"""Pydantic read schemas for membership, invites, share links and people (03 sections 5.4, 5.5).

Token hashes are never exposed.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Role = Literal["owner", "editor", "viewer"]


class TripMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trip_id: uuid.UUID
    user_id: uuid.UUID
    role: Role
    joined_at: datetime


class TripInviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    role: Literal["editor", "viewer"]
    email: str | None
    max_uses: int
    use_count: int
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime


class TripShareLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    redact_address: bool
    redact_prices: bool
    redact_notes: bool
    redact_people: bool
    indexable: bool
    expires_at: datetime
    revoked_at: datetime | None
    view_count: int
    last_viewed_at: datetime | None
    created_at: datetime


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    linked_user_id: uuid.UUID | None
    name: str
    color: str
    home_airports: list[str]
    is_self: bool


# --- 04 sections 5.6 and 5.7 -------------
# A traveler is a name, a color and home airports. No birthdate and no email, on purpose.

Iata = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class PersonIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    color: Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
    home_airports: Annotated[list[Iata], Field(max_length=6)] = []


class Person(PersonIn):
    id: uuid.UUID
    linked_user_id: uuid.UUID | None
    is_me: bool


class TravelersIn(BaseModel):
    person_ids: Annotated[list[uuid.UUID], Field(min_length=1)]


class TravelerLink(BaseModel):
    person_id: uuid.UUID


class Attribution(BaseModel):
    id: uuid.UUID
    display_name: str | None  # None means "Former member"


class Member(BaseModel):
    user_id: uuid.UUID
    display_name: str | None
    role: Role
    person_id: uuid.UUID | None
    joined_at: datetime
    invited_by: Attribution | None


# --- 04 section 5.6: invites, roles, transfer ----------------------------------------------


class MemberRolePatch(BaseModel):
    role: Literal["editor", "viewer"]  # "owner" is a 422: use transfer


class InviteCreate(BaseModel):
    role: Literal["editor", "viewer"]
    email: Annotated[str, StringConstraints(strip_whitespace=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$")] | None = None
    max_uses: Annotated[int, Field(ge=1, le=6)] = 1
    expires_in_days: Annotated[int, Field(ge=1, le=14)] = 7


class Invite(BaseModel):
    id: uuid.UUID
    role: Literal["editor", "viewer"]
    email: str | None
    url: str | None = None  # only in the create response
    uses_left: int
    expires_at: datetime
    created_at: datetime
    status: Literal["pending", "used", "expired", "revoked"]


class InvitePreview(BaseModel):
    trip_name: str
    cover_url: str | None
    inviter_name: str
    role: Literal["editor", "viewer"]


class InviteAccept(BaseModel):
    person_id: uuid.UUID | None = None


class TransferIn(BaseModel):
    new_owner_id: uuid.UUID


# --- 04 sections 5.6 and 5.15: share links and the shared trip -------------------------------


class Redact(BaseModel):
    hotel_address: bool = True
    prices: bool = True
    notes: bool = True
    people: bool = True


class ShareLinkCreate(BaseModel):
    expires_in_days: Annotated[int, Field(ge=1, le=365)] = 90
    redact: Redact = Redact()
    show_book_slide: bool = True
    indexable: bool = False


class RedactPatch(BaseModel):
    hotel_address: bool | None = None
    prices: bool | None = None
    notes: bool | None = None
    people: bool | None = None


class ShareLinkPatch(BaseModel):
    expires_in_days: Annotated[int, Field(ge=1, le=365)] | None = None
    redact: RedactPatch | None = None
    show_book_slide: bool | None = None
    indexable: bool | None = None


class ShareLink(BaseModel):
    id: uuid.UUID
    url: str | None = None  # only in the create response
    redact: Redact
    show_book_slide: bool
    indexable: bool
    created_at: datetime
    expires_at: datetime
    view_count: int
    revoked_at: datetime | None


class SharedItem(BaseModel):
    id: uuid.UUID
    start_time: str | None
    end_time: str | None
    title: str
    category: str
    status: str
    location_name: str | None
    address: str | None  # null when the address is redacted
    lat: float | None
    lon: float | None
    url: str | None
    notes: str
    estimated_cost_minor: int | None  # null when prices are redacted
    cost_currency: str | None
    source: str  # evidence is never redacted: where the item came from and the page it was checked on
    check_url: str | None
    checked_at: datetime | None


class SharedDay(BaseModel):
    day: str
    title: str
    notes: str
    destination_name: str | None
    items: list[SharedItem]


class SharedStay(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    check_in: str | None
    check_out: str | None
    location_name: str | None  # null when the address is redacted
    lat: float | None
    lon: float | None
    price_total_minor: int | None
    price_per_night_minor: int | None
    currency: str | None


class SharedDestination(BaseModel):
    name: str
    region: str | None
    country: str | None
    country_code: str | None


class SharedTripHead(BaseModel):
    id: uuid.UUID
    name: str
    start_date: str | None
    end_date: str | None
    cover: str | None
    destinations: list[SharedDestination]
    travelers: list[str]


class Presentation(BaseModel):
    trip: SharedTripHead
    days: list[SharedDay]
    flights: list[dict] = []
    stays: list[SharedStay]
    weather: list[dict] | None = None
    checklist: dict[str, int] = {"done": 0, "total": 0}
    book_slide_enabled: bool
    generated_at: datetime


class SharedCta(BaseModel):
    label: Literal["Get the app to edit"] = "Get the app to edit"
    url: str


class SharedTrip(BaseModel):
    trip_name: str
    presentation: Presentation
    cta: SharedCta
    book_slide: list[dict] | None = None
