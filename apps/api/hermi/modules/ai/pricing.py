# ruff: noqa: E501
"""Versioned provider prices (06 section 6.1). A constant, not a table.

Never edit a version in place: a price change adds a new PriceVersion with a later effective_from and keeps the
old ones, so a cost can be recomputed for any date. Old ai_usage rows are never recomputed. Prices are micro-dollars
(USD * 1e6): per million tokens for models, per call for the rest.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from datetime import date as Date
from types import MappingProxyType


@dataclass(frozen=True)
class ModelPrice:
    input: int
    write_5m: int
    write_1h: int
    read: int
    output: int  # output includes thinking tokens


@dataclass(frozen=True)
class PriceVersion:
    version: str
    effective_from: Date
    models: Mapping[str, ModelPrice]
    web_search_micros: int  # per search; Batch never discounts it
    batch_num: int  # Batch discounts tokens only, by batch_num / batch_den
    batch_den: int
    provider_call_micros: Mapping[str, int]  # non-LLM providers, per call, for provider_calls.cost_usd_micros


_V1 = PriceVersion(
    version="2026-09-30",
    effective_from=Date(2026, 9, 30),
    models=MappingProxyType(
        {
            "claude-sonnet-5-5": ModelPrice(2_000_000, 2_500_000, 4_000_000, 200_000, 10_000_000),
            "claude-haiku-4-5": ModelPrice(1_000_000, 1_250_000, 2_000_000, 100_000, 5_000_000),
        }
    ),
    web_search_micros=10_000,
    batch_num=1,
    batch_den=2,
    # shortcut: planning estimates (SerpApi $75 per 5,000 searches; Geoapify a pay-as-you-go rate), not invoiced prices.
    # Ceiling: ceilings and budgets use these numbers. Trigger: the first invoice; then add a new version.
    provider_call_micros=MappingProxyType({"serpapi": 15_000, "geoapify": 500}),
)

# Oldest first. Add a new version at the end; never change an existing one.
PRICE_VERSIONS: tuple[PriceVersion, ...] = (_V1,)


def price_version(on: Date | None = None) -> PriceVersion:
    """The version in force on a date (today in UTC if None): the latest whose effective_from is not after it."""
    on = on or datetime.now(UTC).date()
    current = [v for v in PRICE_VERSIONS if v.effective_from <= on]
    if not current:
        raise LookupError(f"no price version effective on {on}")
    return current[-1]


def model_price(model: str, on: Date | None = None) -> ModelPrice:
    try:
        return price_version(on).models[model]
    except KeyError:
        raise LookupError(f"no price for model {model!r}") from None
