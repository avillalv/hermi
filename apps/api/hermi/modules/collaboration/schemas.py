"""Pydantic read schemas for membership, invites, share links and people (03 sections 5.4, 5.5).

Token hashes are never exposed.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
