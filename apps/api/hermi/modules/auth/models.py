"""Identity tables (03 section 5.1). Column names and types match migration 0002_identity."""

import uuid
from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Boolean, ForeignKey, Integer, LargeBinary, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, ENUM, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hermi.modules.base import Base

_ts = TIMESTAMP(timezone=True)
_now = text("now()")
_uuid7 = text("uuidv7()")

USER_STATUSES = ("active", "suspended", "pending_deletion", "deleted")
UserStatus = ENUM(*USER_STATUSES, name="user_status", create_type=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    email: Mapped[str] = mapped_column(CITEXT)
    email_is_relay: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    email_verified_at: Mapped[datetime | None] = mapped_column(_ts)
    display_name: Mapped[str] = mapped_column(Text, server_default=text("''"))
    locale: Mapped[str] = mapped_column(Text, server_default=text("'en-US'"))
    timezone: Mapped[str] = mapped_column(Text, server_default=text("'UTC'"))
    home_currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'USD'"))
    home_airports: Mapped[list[str]] = mapped_column(ARRAY(CHAR(3)), server_default=text("'{}'"))
    country_code: Mapped[str | None] = mapped_column(CHAR(2))
    status: Mapped[str] = mapped_column(UserStatus, server_default=text("'active'"))
    hide_booking_links: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    prefs: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    last_seen_at: Mapped[datetime | None] = mapped_column(_ts)
    suspended_at: Mapped[datetime | None] = mapped_column(_ts)
    sharing_suspended_at: Mapped[datetime | None] = mapped_column(_ts)
    pack_purchases_blocked_until: Mapped[datetime | None] = mapped_column(_ts)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    updated_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    deleted_at: Mapped[datetime | None] = mapped_column(_ts)


class AuthIdentity(Base):
    __tablename__ = "auth_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    provider_subject: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(CITEXT)
    email_is_relay: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    provider_refresh_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    last_login_at: Mapped[datetime | None] = mapped_column(_ts)


class DeviceAttestation(Base):
    __tablename__ = "device_attestations"

    key_id: Mapped[str] = mapped_column(Text, primary_key=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    counter: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    environment: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class GuestAllowance(Base):
    __tablename__ = "guest_allowances"

    key_id: Mapped[str] = mapped_column(
        ForeignKey("device_attestations.key_id", ondelete="CASCADE"), primary_key=True
    )
    period_key: Mapped[str] = mapped_column(Text, primary_key=True)
    credits_used: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(Text)
    device_name: Mapped[str | None] = mapped_column(Text)
    push_token: Mapped[str | None] = mapped_column(Text)
    push_environment: Mapped[str | None] = mapped_column(Text)
    app_version: Mapped[str | None] = mapped_column(Text)
    os_version: Mapped[str | None] = mapped_column(Text)
    refresh_token_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    attestation_key_id: Mapped[str | None] = mapped_column(
        ForeignKey("device_attestations.key_id", ondelete="SET NULL")
    )
    last_seen_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    revoked_at: Mapped[datetime | None] = mapped_column(_ts)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
