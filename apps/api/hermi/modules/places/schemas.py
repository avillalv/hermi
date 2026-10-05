"""Places API shapes (04 section 5.11). `Place` is `PlaceOut` from `providers/schemas.py`."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from hermi.modules.collaboration.schemas import Attribution
from hermi.providers.schemas import ActivityCategory, PlaceOut

ATTRIBUTION = "Powered by Geoapify, © OpenStreetMap contributors"
WIKI_ATTRIBUTION = "Text from Wikipedia, CC BY-SA 4.0"


class PlaceSearchResult(BaseModel):
    places: list[PlaceOut]
    cached: bool
    sorted_by: Literal["relevance", "distance"]
    attribution: str = ATTRIBUTION


class Wiki(BaseModel):
    title: str
    extract: str
    url: str | None
    image_url: str | None
    attribution: str = WIKI_ATTRIBUTION


class PlaceDetails(PlaceOut):
    wiki: Wiki | None = None
    attribution: str = ATTRIBUTION


class SavedPlaceRef(BaseModel):
    """A saved place. Looser than `Place`: a manual place can lack coordinates, and the
    provider can be `manual` or `viator`."""

    provider: str
    id: str
    name: str
    category: ActivityCategory
    kinds: list[str] = []
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    website: str | None = None
    local_name: str | None = None
    opening_hours: str | None = None
    phone: str | None = None
    wikidata: str | None = None
    wikipedia: str | None = None
    has_details: bool = False


class SavedPlace(BaseModel):
    id: uuid.UUID
    place: SavedPlaceRef
    note: str | None
    added_by: Attribution | None
    created_at: datetime


class SavedPlacePage(BaseModel):
    items: list[SavedPlace]
    next_cursor: str | None
    has_more: bool
    attribution: str = ATTRIBUTION


class SavedPlaceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    place_id: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    note: Annotated[str, StringConstraints(max_length=1000)] | None = None
