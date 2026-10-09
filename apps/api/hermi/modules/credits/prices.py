# ruff: noqa: E501
"""Mirror of the credit seed (03 section 11.3, 07 section 5). Runtime prices and max turns come from the
credit_action_prices table (service.reserve and settle_stopped_agent_run read it); these constants exist only so a test
can keep the seed, the plans seed and packages/shared/src/credits.ts equal."""

import math

ACTION_CREDITS: dict[str, tuple[int, int | None]] = {  # action: (credits, credits from the shared cache or None)
    "explain": (1, None),
    "live_search": (1, None),
    "draft_day": (1, None),
    "draft_trip": (4, None),
    "research": (8, 1),
    "agent_run": (40, 8),
    "verify_plan": (1, None),  # per checked item
}
MONTHLY_CREDITS = {"free": 12, "plus": 60}
TASTER_CREDITS = ACTION_CREDITS["agent_run"][0]
AGENT_RUN_MINIMUM_CHARGE = 8
PURCHASED_CREDITS_VALID_MONTHS = 12
AGENT_RUN_MAX_TURNS = 20


def price(action: str, *, cached: bool = False, items: int = 1) -> int:
    full, from_cache = ACTION_CREDITS[action]
    return (from_cache if cached and from_cache is not None else full) * items


def agent_run_charge(
    turns_used: int, *, called_tools: bool = True, max_turns: int = AGENT_RUN_MAX_TURNS, full: int = ACTION_CREDITS["agent_run"][0]
) -> int:
    """Credits for a stopped agent run: 0 if cancelled in the queue, else pro rata by turns used with an 8 minimum
    (settle_credits caps the charge at what was reserved)."""
    if not called_tools:
        return 0
    return max(AGENT_RUN_MINIMUM_CHARGE, math.ceil(full * max(turns_used, 0) / max_turns))
