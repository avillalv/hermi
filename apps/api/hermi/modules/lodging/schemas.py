# ruff: noqa: E501  (long constraint lines)
"""Lodging shapes (04 section 5.9)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from hermi.modules.collaboration.schemas import Attribution
from hermi.modules.flights.schemas import Money
from hermi.modules.itinerary.schemas import MoneyIn

Status = Literal["candidate", "shortlisted", "booked", "rejected"]
AddedVia = Literal["paste", "bookmarklet", "partner_search", "agent", "manual"]
Sort = Literal["created", "price", "rating", "votes"]
Small = Annotated[int, Field(ge=0, le=1000)]
Text = Annotated[str, StringConstraints(max_length=4000)]


class _Fields(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: Annotated[str, StringConstraints(strip_whitespace=False, max_length=2000)] | None = None
    check_in: date | None = None
    check_out: date | None = None
    guests: Annotated[int, Field(ge=1, le=100)] | None = None
    price_total: MoneyIn | None = None
    price_per_night: MoneyIn | None = None
    photos: list[Annotated[str, StringConstraints(max_length=2000)]] | None = Field(default=None, max_length=30)
    location_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    bedrooms: Small | None = None
    beds: Small | None = None
    baths: Annotated[float, Field(ge=0, le=99)] | None = None
    rating: Annotated[float, Field(ge=0, le=5)] | None = None
    review_count: Annotated[int, Field(ge=0, le=10**7)] | None = None
    notes: Text | None = None
    pros: Text | None = None
    cons: Text | None = None
    status: Status | None = None
    favorite: bool | None = None
    version: int | None = None


class LodgingIn(_Fields):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    added_via: AddedVia | None = None  # default: paste when there is a url, else manual


class LodgingUpdate(_Fields):
    """Partial<LodgingIn>: only the fields sent change (`model_fields_set`). The merged row is checked in the router."""

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)] | None = None

    @model_validator(mode="after")
    def _not_null(self) -> Self:
        for f in ("title", "notes", "pros", "cons", "status", "favorite", "photos"):  # these columns are NOT NULL
            if f in self.model_fields_set and getattr(self, f) is None:
                raise ValueError(f"{f} cannot be empty.")
        return self


class Vote(BaseModel):
    user_id: uuid.UUID | None  # None: the account is gone
    person_id: uuid.UUID | None  # None: no linked traveler, or the traveler was removed ("Former traveler")


class VoteSummary(BaseModel):
    hearts: int


class Lodging(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    title: str
    url: str | None  # exactly as pasted
    site: str | None
    check_in: date | None
    check_out: date | None
    nights: int | None
    guests: int | None
    price_total: Money | None
    price_per_night: Money | None
    price_home_total: Money | None
    photos: list[str]
    location_name: str | None
    lat: float | None
    lon: float | None
    bedrooms: int | None
    beds: int | None
    baths: float | None
    rating: float | None
    review_count: int | None
    notes: str
    pros: str
    cons: str
    status: Status
    favorite: bool
    added_via: str
    version: int
    votes: list[Vote]
    vote_summary: VoteSummary
    added_by: Attribution | None
    created_at: datetime
    updated_at: datetime


class LodgingPage(BaseModel):
    items: list[Lodging]
    next_cursor: str | None
    has_more: bool
    sorted_by: str


class CompareRow(BaseModel):
    key: str
    label: str
    values: list[str | int | float | None]


class LodgingCompare(BaseModel):
    columns: list[uuid.UUID]
    rows: list[CompareRow]
    home_currency: str


class ParseLinkIn(BaseModel):
    model_config = ConfigDict(extra="ignore")

    url: Annotated[str, StringConstraints(max_length=2000)]
    check_in: date | None = None
    check_out: date | None = None
    guests: Annotated[int, Field(ge=1, le=100)] | None = None
    fetch: bool = False


class LinkParse(BaseModel):
    url: str
    site: str | None
    fetch_allowed: Literal[False] = False
    check_in: date | None
    check_out: date | None
    guests: int | None
    listing_id: str | None
    title: None = None
    photos: list[str] = []
    description: None = None
    note: str


class VoteIn(BaseModel):
    voted: bool
