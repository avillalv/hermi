"""Pydantic read schemas for the plan catalog (03 section 5.3)."""

from pydantic import BaseModel, ConfigDict


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    kind: str
    name: str
    rank: int
    limits: dict
    monthly_credits: int
    credits_granted: int
    credits_valid_days: int | None
    duration_days: int | None
    is_active: bool
    sort_order: int


class StoreProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: str
    plan_code: str
    period: str
    price_minor: int
    currency: str
    trial_days: int
    is_active: bool
