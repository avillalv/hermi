"""AI run and usage tables (03 section 5.6). Column names and types match migration 0005_ai.

Costs are integer micro-dollars (*_micros).
CreditActionPrice lives in modules.catalog.models (migration 0003).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from hermi.modules.base import Base
from hermi.modules.catalog.models import AiAction

_ts = TIMESTAMP(timezone=True)
_now = text("now()")
_uuid7 = text("uuidv7()")

RUN_KINDS = (
    "fare_hunt",
    "deep_research",
    "research_question",
    "draft_trip",
    "draft_day",
    "explain",
    "packing_list",
    "booking_import",
    "verify_extract",
    "verify_plan",
    "recheck",
)
RUN_STATUSES = (
    "queued",
    "running",
    "succeeded",
    "partial",
    "failed",
    "timed_out",
    "cancelled",
    "interrupted",
)
AI_PROVIDERS = ("anthropic_api", "claude_cli", "fake")

RunKind = ENUM(*RUN_KINDS, name="run_kind", create_type=False)
RunTrigger = ENUM("manual", name="run_trigger", create_type=False)
RunStatus = ENUM(*RUN_STATUSES, name="run_status", create_type=False)
UsageState = ENUM("reserved", "settled", "released", name="usage_state", create_type=False)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=_uuid7
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(RunKind)
    action: Mapped[str | None] = mapped_column(AiAction)
    trigger: Mapped[str] = mapped_column(RunTrigger, server_default=text("'manual'"))
    status: Mapped[str] = mapped_column(RunStatus, server_default=text("'queued'"))
    params: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    prompt: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text, server_default=text("'anthropic_api'"))
    prompt_version: Mapped[str | None] = mapped_column(Text)
    queued_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    started_at: Mapped[datetime | None] = mapped_column(_ts)
    finished_at: Mapped[datetime | None] = mapped_column(_ts)
    worker_id: Mapped[str | None] = mapped_column(Text)
    heartbeat_at: Mapped[datetime | None] = mapped_column(_ts)
    summary: Mapped[str | None] = mapped_column(Text)
    report: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    failure_code: Mapped[str | None] = mapped_column(Text)
    accepted_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    rejected_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    turns_used: Mapped[int | None] = mapped_column(SmallInteger)
    searches_used: Mapped[int | None] = mapped_column(SmallInteger)
    fetches_used: Mapped[int | None] = mapped_column(SmallInteger)
    cost_usd_micros: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    served_from_cache: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    cache_key: Mapped[str | None] = mapped_column(CHAR(64))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class RunEvent(Base):
    """Partitioned by month on ts, so the primary key is (id, ts)."""

    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    seq: Mapped[int] = mapped_column(Integer)
    ts: Mapped[datetime] = mapped_column(_ts, primary_key=True, server_default=_now)
    type: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict | None] = mapped_column(JSONB)


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    trip_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("trips.id", ondelete="SET NULL"))
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(AiAction)
    model: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text, server_default=text("'anthropic_api'"))
    input_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    output_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cache_read_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    cache_write_tokens: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    web_searches: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    via_batch: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    cost_usd_micros: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    credits_reserved: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    credits_charged: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    state: Mapped[str] = mapped_column(UsageState, server_default=text("'reserved'"))
    cache_hit: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    idempotency_key: Mapped[str] = mapped_column(Text, unique=True)
    purpose: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    settled_at: Mapped[datetime | None] = mapped_column(_ts)


class ProviderCall(Base):
    """Partitioned by month on created_at. A log: no foreign keys."""

    __tablename__ = "provider_calls"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    provider: Mapped[str] = mapped_column(Text)
    endpoint: Mapped[str] = mapped_column(Text)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    trip_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    units: Mapped[Decimal] = mapped_column(Numeric(12, 3), server_default=text("1"))
    cost_usd_micros: Mapped[int | None] = mapped_column(BigInteger)
    cached: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    cache_layer: Mapped[str | None] = mapped_column(Text)
    ok: Mapped[bool] = mapped_column(Boolean)
    status_code: Mapped[int | None] = mapped_column(SmallInteger)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    request_hash: Mapped[str | None] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(_ts, primary_key=True, server_default=_now)


class ProviderCallRollup(Base):
    __tablename__ = "provider_call_rollups"

    month: Mapped[date] = mapped_column(Date, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, primary_key=True)
    calls: Mapped[int] = mapped_column(BigInteger)
    cached_calls: Mapped[int] = mapped_column(BigInteger)
    failed_calls: Mapped[int] = mapped_column(BigInteger)
    units: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    cost_usd_micros: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))


class SharedResearchCache(Base):
    __tablename__ = "shared_research_cache"

    key: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    params: Mapped[dict] = mapped_column(JSONB)
    response: Mapped[dict] = mapped_column(JSONB)
    sources: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    response_bytes: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    model: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    expires_at: Mapped[datetime] = mapped_column(_ts)
    stale_until: Mapped[datetime] = mapped_column(_ts)
    hit_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_hit_at: Mapped[datetime | None] = mapped_column(_ts)
    run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"))
    cost_usd_micros: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    report_count: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    flagged_at: Mapped[datetime | None] = mapped_column(_ts)
