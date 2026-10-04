"""Trip members, invites, share links and people (03 5.4, 5.5), as in 0004_trips_people."""

import uuid
from datetime import datetime

from sqlalchemy import CHAR, Boolean, ForeignKey, Integer, LargeBinary, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hermi.modules.base import Base

_ts = TIMESTAMP(timezone=True)
_now = text("now()")
_uuid7 = text("uuidv7()")

TRIP_ROLES = ("owner", "editor", "viewer")
TripRole = ENUM(*TRIP_ROLES, name="trip_role", create_type=False)


class TripMember(Base):
    __tablename__ = "trip_members"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(TripRole)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    joined_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class TripInvite(Base):
    __tablename__ = "trip_invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary)
    role: Mapped[str] = mapped_column(TripRole, server_default=text("'editor'"))
    email: Mapped[str | None] = mapped_column(CITEXT)
    max_uses: Mapped[int] = mapped_column(SmallInteger, server_default=text("1"))
    use_count: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    expires_at: Mapped[datetime] = mapped_column(
        _ts, server_default=text("now() + interval '7 days'")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(_ts)
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    accepted_at: Mapped[datetime | None] = mapped_column(_ts)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class TripShareLink(Base):
    __tablename__ = "trip_share_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    token_hash: Mapped[bytes] = mapped_column(LargeBinary)
    redact_address: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    redact_prices: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    redact_notes: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    redact_people: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    indexable: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    expires_at: Mapped[datetime] = mapped_column(
        _ts, server_default=text("now() + interval '90 days'")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(_ts)
    view_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_viewed_at: Mapped[datetime | None] = mapped_column(_ts)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class Person(Base):
    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    linked_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(Text)
    color: Mapped[str] = mapped_column(CHAR(7), server_default=text("'#FF5E7E'"))
    home_airports: Mapped[list[str]] = mapped_column(ARRAY(CHAR(3)), server_default=text("'{}'"))
    is_self: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    updated_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class TripPerson(Base):
    __tablename__ = "trip_people"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), primary_key=True
    )
    added_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
