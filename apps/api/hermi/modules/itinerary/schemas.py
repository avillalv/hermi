# ruff: noqa: E501  (long constraint lines)
"""Itinerary shapes (04 section 5.10)."""

import uuid
from datetime import date, datetime, time
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from hermi.modules.collaboration.schemas import Attribution
from hermi.modules.flights.schemas import Money

Category = Literal["sights", "museum", "food", "nature", "nightlife", "shopping", "travel", "other"]
Status = Literal["idea", "planned", "booked"]
MAX_BULK = 50


class MoneyIn(BaseModel):
    amount_minor: int = Field(ge=0, le=10**12)
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class PlaceIn(BaseModel):
    provider: Literal["geoapify"]
    id: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    data: dict[str, Any] | None = None


def check_times(day: date | None, start: time | None, end: time | None) -> None:
    if start is not None and day is None:
        raise ValueError("A time needs a day.")
    if end is not None and start is None:
        raise ValueError("An end time needs a start time.")
    if start is not None and end is not None and end < start:
        raise ValueError("The end time cannot be before the start time.")


class _Fields(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    location_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    url: Annotated[str, StringConstraints(max_length=2000)] | None = None
    notes: Annotated[str, StringConstraints(max_length=4000)] = ""
    cost: MoneyIn | None = None
    place: PlaceIn | None = None
    version: int | None = None


class ItemIn(_Fields):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    category: Category
    status: Status = "idea"

    @model_validator(mode="after")
    def _times(self) -> Self:
        check_times(self.day, self.start_time, self.end_time)
        if (self.lat is None) != (self.lon is None):
            raise ValueError("Send both lat and lon, or neither.")
        return self


class ItemUpdate(BaseModel):
    """Partial<ItemIn>: only the fields sent change (`model_fields_set`). The merged row is checked in the router."""

    model_config = ConfigDict(extra="ignore")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    category: Category | None = None
    status: Status | None = None
    day: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    location_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    url: Annotated[str, StringConstraints(max_length=2000)] | None = None
    notes: Annotated[str, StringConstraints(max_length=4000)] | None = None
    cost: MoneyIn | None = None
    version: int | None = None

    @model_validator(mode="after")
    def _not_null(self) -> Self:
        for f in ("title", "category", "status", "notes"):  # these columns are NOT NULL
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} cannot be null.")
        return self


class BulkIn(BaseModel):
    items: Annotated[list[ItemIn], Field(min_length=1, max_length=MAX_BULK)]
    source: Literal["ai_draft", "import"] | None = None


class Item(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    title: str
    day: date | None
    start_time: time | None
    end_time: time | None
    category: Category
    status: Status
    location_name: str | None
    address: str | None
    lat: float | None
    lon: float | None
    url: str | None
    notes: str
    cost: Money | None
    sort_order: float
    version: int
    source: Literal["manual", "place_search", "ai_draft", "agent", "import", "verify_plan"]
    place_provider: str | None
    place_id: str | None
    place_data: dict[str, Any] | None
    bookable: bool
    added_by: Attribution | None
    created_at: datetime
    updated_at: datetime


class ItemPage(BaseModel):
    items: list[Item]
    next_cursor: str | None
    has_more: bool


class DayUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Annotated[str, StringConstraints(max_length=120)] | None = None
    notes: Annotated[str, StringConstraints(max_length=4000)] | None = None
    destination_id: uuid.UUID | None = None
    version: int | None = None

    @model_validator(mode="after")
    def _not_null(self) -> Self:
        for f in ("title", "notes"):
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} cannot be null.")
        return self


class DayItemRef(BaseModel):
    title: str
    start_time: time | None


class Day(BaseModel):
    day: date
    title: str
    notes: str
    destination_id: uuid.UUID | None
    destination_name: str | None
    timezone: str | None
    in_trip: bool
    item_count: int
    version: int
    first: DayItemRef | None
    last: DayItemRef | None


class ReorderIn(BaseModel):
    ids: list[uuid.UUID]
    version_map: dict[uuid.UUID, int] | None = None


class MoveIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    day: date | None
    before_id: uuid.UUID | None = None
    start_time: time | None = None
    version: int | None = None
