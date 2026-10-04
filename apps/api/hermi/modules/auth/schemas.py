"""Pydantic read schemas for the identity tables (03 section 5.1)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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
