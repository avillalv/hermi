# ruff: noqa: E501  (long constraint lines)
"""Route and fare shapes (04 section 5.8). `Fare.id` is the trip_fare_links id; fare_observations.id is never exposed."""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, model_validator

Iata = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
MAX_DAYS_OUT = 330  # 01 section 5.8 validation
Cabin = Literal["economy", "premium_economy", "business", "first"]


class Money(BaseModel):
    amount_minor: int
    currency: str


class RouteIn(BaseModel):
    label: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    origin_codes: list[Iata] = Field(min_length=1, max_length=4)
    destination_codes: list[Iata] = Field(min_length=1, max_length=4)
    trip_type: Literal["round_trip", "one_way"] = "round_trip"
    depart_from: date
    depart_to: date
    return_from: date | None = None
    return_to: date | None = None
    min_nights: int | None = Field(default=None, ge=1, le=60)
    max_nights: int | None = Field(default=None, ge=1, le=60)
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=8)
    cabin: Cabin = "economy"
    max_stops: Literal[0, 1, 2] | None = None
    mode: Literal["cached", "live"] = "cached"
    active: bool = True
    version: int | None = None

    @model_validator(mode="after")
    def _shape(self) -> Self:
        def bad(msg: str) -> ValueError:
            return ValueError(msg)

        today = datetime.now(UTC).date()
        if self.depart_to < today:
            raise bad("The window must not be in the past.")
        if max(self.depart_to, self.return_to or self.depart_to) > today + timedelta(days=MAX_DAYS_OUT):
            raise bad(f"Dates can be at most {MAX_DAYS_OUT} days from today.")
        if self.depart_to < self.depart_from:
            raise bad("The last departure must be on or after the first.")
        if (self.return_from is None) != (self.return_to is None):
            raise bad("Give both return dates, or neither.")
        if (self.min_nights is None) != (self.max_nights is None):
            raise bad("Give both nights, or neither.")
        if self.return_from and self.return_to and self.return_to < self.return_from:
            raise bad("The last return must be on or after the first.")
        if self.min_nights and self.max_nights and self.max_nights < self.min_nights:
            raise bad("The longest stay must be at least the shortest.")
        if self.trip_type == "one_way" and (self.return_from or self.min_nights):
            raise bad("A one-way flight has no return.")
        if self.trip_type == "round_trip" and (self.return_from is None) == (self.min_nights is None):
            raise bad("Give a return window or a number of nights.")
        if len(set(self.origin_codes)) != len(self.origin_codes) or len(set(self.destination_codes)) != len(self.destination_codes):
            raise bad("Each airport can be listed once.")
        return self


class Route(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    label: str | None
    origin_codes: list[str]
    destination_codes: list[str]
    trip_type: str
    depart_from: date
    depart_to: date
    return_from: date | None
    return_to: date | None
    min_nights: int | None
    max_nights: int | None
    adults: int
    children: int
    cabin: str
    max_stops: int | None
    mode: Literal["cached", "live"]
    active: bool
    version: int
    chosen_fare_id: uuid.UUID | None = None
    booked: None = None
    last_checked_at: datetime | None
    next_live_check_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class Fare(BaseModel):
    id: uuid.UUID
    route_id: uuid.UUID
    source: str
    confidence: str
    origin: str
    destination: str
    depart_date: date
    return_date: date | None
    price: Money
    price_home: Money | None = None
    passengers: int
    airlines: list[str]
    stops_out: int | None
    stops_back: int | None
    duration_out_min: int | None
    duration_back_min: int | None
    depart_at_local: str | None
    flight_numbers: list[str] | None
    book_offer: None = None
    airline_search_url: str | None = None
    source_url: str | None
    observed_at: datetime
    age_label: str
    suspect: bool
    hidden: bool


class FarePage(BaseModel):
    items: list[Fare]
    next_cursor: str | None
    has_more: bool


class RouteSummary(BaseModel):
    route_id: uuid.UUID
    cheapest: Fare | None
    last_checked_at: datetime | None
    fare_count: int
    chosen: Fare | None
    chosen_latest: Fare | None


class PricePoint(BaseModel):
    day: date
    source: str
    price: Money


class PriceHistory(BaseModel):
    currency: str
    points: list[PricePoint]
    google: list[dict] = []  # Google price insights arrive with the live fares provider (WF-031); empty for cached routes
    typical_low: Money | None = None
    typical_high: Money | None = None
    price_level: Literal["low", "typical", "high"] | None = None


class DateGridCell(BaseModel):
    fare_id: uuid.UUID
    depart_date: date
    return_date: date | None
    price: Money
    source: str
    observed_at: datetime


class FarePatch(BaseModel):
    hidden: bool | None = None
    suspect: bool | None = None

    @model_validator(mode="after")
    def _one(self) -> Self:
        if self.hidden is None and self.suspect is None:
            raise ValueError("Send hidden, suspect or both.")
        return self


class MoneyIn(BaseModel):
    amount_minor: int = Field(gt=0, le=10**12)
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class ChoiceIn(BaseModel):
    fare_id: uuid.UUID
    paid: MoneyIn | None = None
    booked_at: AwareDatetime | None = None


class BookedIn(BaseModel):
    booked: bool
    paid: MoneyIn | None = None
    booked_at: AwareDatetime | None = None
