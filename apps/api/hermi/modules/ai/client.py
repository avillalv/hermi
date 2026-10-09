# ruff: noqa: E501
"""The AI client facade (06 section 2.2): thin pass-throughs to a provider from the factory. Per-feature logic
(prompts, schemas, reservations) lives in modules/ai/features (WF-048)."""

from hermi.providers.ai import AgentOutcome, AiProvider, ProviderRequest, ProviderResult
from hermi.providers.ai.base import ToolRunner


async def single_call(provider: AiProvider, req: ProviderRequest) -> ProviderResult:
    return await provider.single_call(req)


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
