# ruff: noqa: E501
"""The AI client facade (06 section 2.2). Thin pass-throughs to a provider from the factory, plus the one-shot request
builder every single-call feature uses: the prompt caching layout (tools, system with a breakpoint, task, volatile
tail), the model allowlist and `max_tokens` per feature. Per-feature logic (prompts, schemas, reservations) lives in
modules/ai/features (WF-048)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal

from hermi.config import Settings
from hermi.providers.ai import (
    AgentOutcome,
    AiProvider,
    FakeProvider,
    ProviderRequest,
    ProviderResult,
    get_provider,
)
from hermi.providers.ai.base import ToolRunner

ModelTier = Literal["fast", "main"]


@dataclass(frozen=True)
class CallSpec:
    """What a one-shot feature asks of the client."""

    code: str  # AI feature code (06 section 1): explain, packing_list, draft_day, draft_trip
    tier: ModelTier  # fast = Haiku (AI_MODEL_FAST), main = Sonnet (AI_MODEL_MAIN)
    max_tokens: int
    system: str
    schema: dict[str, Any]
    effort: str | None = None  # Sonnet only: Haiku has no effort control
    fake_scenario: str | None = None  # the recorded response the fake backend replays


def model_id(settings: Settings, tier: ModelTier) -> str:
    return settings.ai_model_fast if tier == "fast" else settings.ai_model_main


def allowed_models(settings: Settings, tier: ModelTier) -> frozenset[str]:
    """The per-feature allowlist asserted against `response.model` (06 section 6.7)."""
    return frozenset({model_id(settings, tier)})


def build_request(
    settings: Settings, spec: CallSpec, task: str, *, today: date | None = None
) -> ProviderRequest:
    """Render order is tools, system, messages, and any byte change in a prefix invalidates what follows. So the
    static system prompt carries the breakpoint, the task comes next and the date, the only volatile part, goes last."""
    tail = f"<today>{(today or datetime.now(UTC).date()).isoformat()}</today>"
    return ProviderRequest(
        model=model_id(settings, spec.tier),
        system=[{"type": "text", "text": spec.system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": [{"type": "text", "text": task}, {"type": "text", "text": tail}]}],
        max_tokens=spec.max_tokens,
        tools=[],  # one-shot features declare none: a model with no tools cannot browse or write
        output_schema=spec.schema,
        extra={"output_config": {"effort": spec.effort}} if spec.effort else {},
    )


def provider_for(settings: Settings, spec: CallSpec, user_email: str | None = None) -> AiProvider:
    """The backend for this call. `fake` replays the feature's recorded response."""
    p = get_provider(settings, user_email, bind_host="0.0.0.0")  # an ASGI start does not know its host: claude_cli refused
    if isinstance(p, FakeProvider) and spec.fake_scenario:
        return FakeProvider(spec.fake_scenario)
    return p


def cache_read_ratio(result: ProviderResult) -> float | None:
    """cache_read / (cache_read + cache_write + input), the number 06 section 7.3 alerts on. None with no input."""
    u = result.usage
    total = u.cache_read_tokens + u.cache_write_tokens + u.input_tokens
    return round(u.cache_read_tokens / total, 4) if total else None


async def _close(provider: AiProvider) -> None:
    aclose = getattr(provider, "aclose", None)
    if aclose is not None:
        await aclose()


async def single_call(provider: AiProvider, req: ProviderRequest) -> ProviderResult:
    """The per-call provider owns its SDK client, so it is closed when the call ends."""
    try:
        return await provider.single_call(req)
    finally:
        await _close(provider)


async def agent_run(
    provider: AiProvider,
    req: ProviderRequest,
    *,
    max_turns: int = 20,
    stop_micro: int = 800_000,
    run_tool: ToolRunner | None = None,
) -> AgentOutcome:
    return await provider.agent_run(
        req, max_turns=max_turns, stop_micro=stop_micro, run_tool=run_tool
    )
