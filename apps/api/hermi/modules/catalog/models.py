"""Reference data and plan catalog (03 sections 5.2 and 5.3). Migration 0003."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from hermi.modules.base import Base

_ts = TIMESTAMP(timezone=True)
_now = text("now()")

AI_ACTIONS = (
    "explain",
    "live_search",
    "draft_day",
    "draft_trip",
    "research",
    "agent_run",
    "verify_plan",
)
AiAction = ENUM(*AI_ACTIONS, name="ai_action", create_type=False)


class Airport(Base):
    __tablename__ = "airports"

    iata: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    icao: Mapped[str | None] = mapped_column(CHAR(4))
    name: Mapped[str] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    country_code: Mapped[str] = mapped_column(CHAR(2))
    region_code: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str | None] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)


class FxRate(Base):
    __tablename__ = "fx_rates"

    currency: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    per_eur: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    rate_date: Mapped[date] = mapped_column(Date)
    fetched_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class PlacesCache(Base):
    __tablename__ = "places_cache"

    key: Mapped[str] = mapped_column(CHAR(64), primary_key=True)
    provider: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    response: Mapped[dict] = mapped_column(JSONB)
    attribution: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    expires_at: Mapped[datetime] = mapped_column(_ts)
    hit_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class Plan(Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    rank: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    limits: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    monthly_credits: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    credits_granted: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    credits_valid_days: Mapped[int | None] = mapped_column(Integer)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    feature_flag_key: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
    updated_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class StoreProduct(Base):
    __tablename__ = "store_products"

    product_id: Mapped[str] = mapped_column(Text, primary_key=True)
    store: Mapped[str] = mapped_column(Text)
    plan_code: Mapped[str] = mapped_column(ForeignKey("plans.code", ondelete="RESTRICT"))
    period: Mapped[str] = mapped_column(Text)
    price_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(CHAR(3), server_default=text("'USD'"))
    trial_days: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)


class CreditActionPrice(Base):
    __tablename__ = "credit_action_prices"

    action: Mapped[str] = mapped_column(AiAction, primary_key=True)
    credits: Mapped[int] = mapped_column(Integer)
    credits_cached: Mapped[int | None] = mapped_column(Integer)
    hard_stop_micros: Mapped[int] = mapped_column(BigInteger)
    max_turns: Mapped[int | None] = mapped_column(SmallInteger)
    max_searches: Mapped[int | None] = mapped_column(SmallInteger)
    max_fetches: Mapped[int | None] = mapped_column(SmallInteger)
    model: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(_ts, server_default=_now)
