# ruff: noqa: E501  (long comments and docstrings)
"""Pydantic read schemas for the identity tables (03 section 5.1)."""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    email_is_relay: bool
    display_name: str
    locale: str
    timezone: str
    home_currency: str
    home_airports: list[str]
    country_code: str | None
    status: Literal["active", "suspended", "pending_deletion", "deleted"]
    hide_booking_links: bool
    created_at: datetime


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: Literal["ios", "android", "web"]
    device_name: str | None
    app_version: str | None
    os_version: str | None
    last_seen_at: datetime
    revoked_at: datetime | None


# --- WF-013.2: sign-in bootstrap and GET /me (04 section 5.1) ------------------------------------------------------


class LegacyClaimIn(BaseModel):
    token: str = Field(min_length=16, max_length=200)


class BootstrapIn(BaseModel):
    """BootstrapIn of 04 section 5.1. `device`, `claim` and `referral_code` arrive with WF-040 and the referral ticket;
    unknown fields are ignored, as 04 section 1.1 asks of clients and servers alike."""

    display_name: str | None = Field(default=None, max_length=60)
    locale: str | None = Field(default=None, max_length=35)
    timezone: str | None = Field(default=None, max_length=64)
    home_airports: list[str] | None = Field(default=None, max_length=5)
    home_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    age_confirmed: bool

    @field_validator("home_airports")
    @classmethod
    def _iata(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and not all(re.fullmatch(r"[A-Z]{3}", a) for a in v):
            raise ValueError("Use 3 letter airport codes.")
        return v


class ConsentOut(BaseModel):
    kind: str
    version: str
    accepted_at: datetime


ConsentKind = Literal["terms", "privacy", "ai_processing", "marketing_email", "push_notifications", "analytics"]


class ConsentIn(BaseModel):
    """PUT /me/consents/{kind} (04 section 5.2). `version` names the policy or consent text the person saw."""

    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9._-]+$")
    granted: bool


class Consent(BaseModel):
    kind: ConsentKind
    version: str
    granted: bool
    accepted_at: datetime


Tier = Literal["free", "plus"]  # 04 type Tier; Phase 2 adds more, additively


class Me(BaseModel):
    id: uuid.UUID
    email: str | None
    email_is_relay: bool
    display_name: str | None
    locale: str
    timezone: str
    home_currency: str
    home_airports: list[str]
    status: Literal["active", "pending_deletion"]
    tier: Tier
    me_person_id: uuid.UUID
    consents: list[ConsentOut]
    flags: dict[str, bool]
    min_client_version: str
    server_time: datetime


Persona = Literal["free", "plus", "admin"]


class PersonaOut(BaseModel):
    persona: Persona
    label: str
    email: str
    tier: Tier
    is_admin: bool


class DevSessionIn(BaseModel):
    persona: Persona


class DevSessionOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int
    persona: Persona
