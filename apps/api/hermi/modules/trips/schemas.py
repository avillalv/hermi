# ruff: noqa: E501  (long comments and docstrings)
"""Pydantic read schemas for trips (03 section 5.4)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


# --- WF-018.2: GET /trips and POST /trips (04 section 5.4) ---------------------------------------------------------


class DestinationIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    region: str | None = Field(default=None, max_length=200)
    country: str | None = Field(default=None, max_length=200)
    country_code: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")
    kind: str | None = Field(default=None, max_length=50)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=64)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    geoapify_place_id: str | None = Field(default=None, max_length=200)


class TripCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_date: date | None = None
    end_date: date | None = None
    home_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    notes: str = Field(default="", max_length=10000)
    destinations: list[DestinationIn] = Field(default_factory=list, max_length=12)
    traveler_ids: list[uuid.UUID] | None = Field(default=None, max_length=20)
    template: Literal["blank", "city_break", "road_trip", "beach_week"] | None = None  # accepted, not used yet

    @field_validator("name")
    @classmethod
    def _trim(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Give your trip a name.")
        return v

    @model_validator(mode="after")
    def _dates(self) -> "TripCreate":
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("Give both dates, or neither.")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("The end date must be on or after the start date.")
        return self


class Trip(BaseModel):
    """The first slice of 04 `Trip`: GET one and the rest of the fields arrive with WF-019.1."""

    id: uuid.UUID
    version: int
    name: str
    status: Literal["planning", "booked", "done", "archived"]
    start_date: date | None
    end_date: date | None
    home_currency: str
    notes: str
    destinations: list[TripDestinationOut]
    my_role: Literal["owner", "editor", "viewer"]
    ai_enabled: bool
    editors_can_invite: bool
    created_at: datetime
    updated_at: datetime


class TripSummary(BaseModel):
    id: uuid.UUID
    version: int
    name: str
    status: Literal["planning", "booked", "done", "archived"]
    start_date: date | None
    end_date: date | None
    cover: None = None  # covers arrive with the destination image job
    my_role: Literal["owner", "editor", "viewer"]
    member_count: int
    updated_at: datetime
    destinations_label: str
    limited: bool = False


class TripPage(BaseModel):
    items: list[TripSummary]
    next_cursor: str | None
    has_more: bool
