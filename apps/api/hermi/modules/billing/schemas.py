# ruff: noqa: E501  (long comments)
"""04 section 5.19 `Entitlements`. `limits` is the whole `plans.limits` object of the tier, a superset of the five documented keys."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

Status = Literal[
    "none",
    "active",
    "in_trial",
    "in_grace",
    "billing_retry",
    "paused",
    "expired",
    "refunded",
    "revoked",
]


class TripPassOut(BaseModel):
    id: uuid.UUID
    product: Literal["trip_pass"] = "trip_pass"
    source: Literal["purchase", "import_reward"]  # an admin comp reads as "purchase"; refund logic must check the source column
    trip_id: uuid.UUID | None
    starts_at: datetime | None
    expires_at: datetime | None
    status: Literal["unapplied", "active", "expired", "refunded"]
    live_checks_left: int | None
    collaborators_max: int


class CreditGrantOut(BaseModel):
    kind: Literal["monthly", "promo", "trip_pass", "purchase", "adjustment"]
    remaining: int
    expires_at: datetime | None
    trip_id: uuid.UUID | None


class CreditBalance(BaseModel):
    total: int
    monthly: int
    trip_pass: int
    purchased: int
    spend_order: list[str] = ["monthly", "promo", "trip_pass", "adjustment", "purchase"]
    grants: list[CreditGrantOut]
    next_monthly_grant_at: datetime | None
    blocked: bool


class Usage(BaseModel):
    active_trips: int


class Flags(BaseModel):
    agent_runs: bool
    taster_available: bool
    import_reward_available: bool


class Entitlements(BaseModel):
    tier: Literal["free", "plus"]
    source: Literal["none", "subscription", "comp"]
    product_id: str | None
    status: Status
    valid_until: datetime | None
    auto_renew: bool | None
    store: Literal["apple"] | None
    manage_subscription_url: str | None
    cancel_url: str | None
    limits: dict[str, Any]
    usage: Usage
    trip_passes: list[TripPassOut]
    flags: Flags
    credits: CreditBalance
