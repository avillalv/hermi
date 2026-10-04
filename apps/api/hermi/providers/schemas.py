"""Shapes the data providers return to the rest of the API."""

from typing import Literal

from pydantic import BaseModel

ActivityCategory = Literal[
    "sights", "museum", "food", "nature", "nightlife", "shopping", "travel", "other"
]


class DestinationSuggestion(BaseModel):
    """A place a trip can go, as found by Geoapify."""

    label: str
    name: str
    region: str | None
    country: str | None
    country_code: str | None
    kind: str
    lat: float
    lon: float
    timezone: str | None
    bbox: list[float] | None
    geoapify_place_id: str | None


class PlaceOut(BaseModel):
    """A place from a search, with whatever details the provider already returned."""

    provider: Literal["geoapify"]
    id: str
    name: str
    # The name in the local language, when it differs.
    local_name: str | None = None
    category: ActivityCategory
    kinds: list[str]
    address: str | None = None
    lat: float
    lon: float
    distance_m: int | None = None
    website: str | None = None
    opening_hours: str | None = None
    phone: str | None = None
    wikidata: str | None = None
    wikipedia: str | None = None
    # False when only the basics came back (text search); details need their own lookup.
    has_details: bool = False
