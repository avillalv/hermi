# ruff: noqa: E501
"""What one agent run is allowed to do (06 sections 2.4, 5.7 and 6.4). The caps default to the agent_run row of
credit_action_prices; the job passes the table's numbers so an admin edit takes effect at once."""

from dataclasses import dataclass, field

MAX_TOKENS_CEILING = 16_000  # a max_tokens retry doubles up to this (06 section 3.3)


@dataclass(frozen=True)
class AgentSpec:
    model: str  # a full model id from config (AI_MODEL_MAIN)
    system: str  # the static house rules; carries the cache breakpoint
    kind: str = "fare_hunt"  # fare_hunt or deep_research
    max_turns: int = 20
    max_searches: int = 10
    max_fetches: int = 10
    stop_micro: int = 800_000  # $0.80 hard stop, checked before each turn and after each response
    deadline_s: float = 480.0  # 8 minutes
    effort: str = "medium"
    max_tokens: int = 8_000  # per turn
    max_content_tokens: int = 5_000  # per fetched page
    allowed_models: frozenset[str] = field(default_factory=frozenset)  # asserted against response.model; empty = not checked
