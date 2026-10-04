"""Pydantic read schemas for trips (03 section 5.4)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    start_date: date | None
    end_date: date | None
    status: Literal["planning", "booked", "done", "archived"]
    home_currency: str
    notes: str
    cover_image_url: str | None
    ai_enabled: bool
    show_book_slide: bool
    editors_can_invite: bool
    version: int
    archived_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TripDestinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    position: int
    name: str
    region: str | None
    country: str | None
    country_code: str | None
    kind: str | None
    lat: float
    lon: float
    timezone: str | None
    info_status: Literal["pending", "ready", "not_found", "failed", "skipped"]


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    verb: str
    entity_type: str
    entity_id: uuid.UUID | None
    summary: str
    created_at: datetime
