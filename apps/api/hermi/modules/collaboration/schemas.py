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
