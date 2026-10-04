"""Trips, destinations and the activity feed (03 section 5.4), as in 0004_trips_people."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Identity,
    Integer,
    LargeBinary,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hermi.modules.base import Base

_ts = TIMESTAMP(timezone=True)
_now = text("now()")
_uuid7 = text("uuidv7()")

TRIP_STATUSES = ("planning", "booked", "done", "archived")
TripStatus = ENUM(*TRIP_STATUSES, name="trip_status", create_type=False)


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(TripStatus, server_default=text("'planning'"))
    home_currency: Mapped[str] = mapped_column(CHAR(3))
    notes: Mapped[str] = mapped_column(Text, server_default=text("''"))
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    ai_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    show_book_slide: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    editors_can_invite: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    calendar_token_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    archived_at: Mapped[datetime | None] = mapped_column(_ts)
    deleted_at: Mapped[datetime | None] = mapped_column(_ts)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    updated_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class TripDestination(Base):
    __tablename__ = "trip_destinations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str | None] = mapped_column(CHAR(2))
    kind: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str | None] = mapped_column(Text)
    bbox: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    geoapify_place_id: Mapped[str | None] = mapped_column(Text)
    wikidata_id: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    wiki_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)
    image_attribution: Mapped[str | None] = mapped_column(Text)
    image_license: Mapped[str | None] = mapped_column(Text)
    info_status: Mapped[str] = mapped_column(Text, server_default=text("'pending'"))
    info_updated_at: Mapped[datetime | None] = mapped_column(_ts)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    verb: Mapped[str] = mapped_column(Text)
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    summary: Mapped[str] = mapped_column(Text, server_default=text("''"))
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
