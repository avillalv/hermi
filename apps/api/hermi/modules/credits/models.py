"""Credit tables (03 section 5.13). Column names and types match migration 0006_billing_credits.

The app role cannot write these tables directly; writes go through the SQL functions in repo.py.
CreditActionPrice lives in modules.catalog.models (migration 0003).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Identity, Integer, Text, text
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hermi.modules.base import Base
from hermi.modules.catalog.models import AiAction

_ts = TIMESTAMP(timezone=True)
_now = text("now()")
_uuid7 = text("uuidv7()")

CREDIT_GRANT_KINDS = ("monthly", "promo", "trip_pass", "purchase", "adjustment")
CREDIT_ENTRY_TYPES = ("grant", "reserve", "settle", "refund", "expire", "clawback", "adjust")
CreditGrantKind = ENUM(*CREDIT_GRANT_KINDS, name="credit_grant_kind", create_type=False)
CreditEntryType = ENUM(*CREDIT_ENTRY_TYPES, name="credit_entry_type", create_type=False)


class CreditGrant(Base):
    __tablename__ = "credit_grants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(CreditGrantKind)
    credits: Mapped[int] = mapped_column(Integer)
    remaining: Mapped[int] = mapped_column(Integer)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    restricted_action: Mapped[str | None] = mapped_column(AiAction)
    period_key: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(_ts)
    store_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("store_transactions.id", ondelete="SET NULL")
    )  # store_transactions has no model yet, so the type is explicit
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    grant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("credit_grants.id", ondelete="SET NULL")
    )
    entry_type: Mapped[str] = mapped_column(CreditEntryType)
    delta: Mapped[int] = mapped_column(Integer)
    charged: Mapped[int | None] = mapped_column(Integer)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str | None] = mapped_column(AiAction)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    trip_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    usage_id: Mapped[int | None] = mapped_column(ForeignKey("ai_usage.id", ondelete="SET NULL"))
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class CreditDebt(Base):
    __tablename__ = "credit_debts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    amount: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
