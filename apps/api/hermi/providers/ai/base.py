# ruff: noqa: E501
"""The AiProvider seam (06 section 2.7). Backends return provider-neutral results, so metering writes the same
ai_usage and runs rows whichever backend served the call (cost in micro-dollars, `provider` names the backend)."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, fields, replace
from typing import Any, Literal, Protocol

from hermi.modules.ai.metering import Usage
from hermi.providers import ProviderError

Block = dict[str, Any]
Message = dict[str, Any]
ToolRunner = Callable[
    [Block], Awaitable[Block]
]  # runs one client tool_use block, returns a tool_result block
Stop = Literal[
    "end_turn",
    "refusal",
    "turn_limit",
    "spend_limit",
    "max_tokens",
    "stop_sequence",
    "tool_use",
    "unknown",
]


class ProviderRefused(ProviderError):
    """The guard refused this provider for this call (claude_cli outside its allowed conditions)."""


@dataclass(frozen=True)
class ProviderRequest:
    model: str  # a full model id from config
    messages: list[Message]
    max_tokens: int
    system: str | list[Block] | None = None
    tools: list[Block] = field(
        default_factory=list
    )  # client tools and server tools, passed through
    output_schema: dict[str, Any] | None = None  # structured output through output_config.format
    extra: dict[str, Any] = field(
        default_factory=dict
    )  # other Messages API parameters, passed through


@dataclass(frozen=True)
class ProviderResult:
    provider: str  # anthropic_api, claude_cli or fake
    model: str
    content: list[Block]
    stop_reason: str
    usage: Usage
    cost_usd_micros: int  # notional for claude_cli, 0 for fake
    server_tool_use: dict[str, int] = field(default_factory=dict)  # e.g. {"web_search_requests": 2}
    stop_details: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        return "".join(b.get("text", "") for b in self.content if b.get("type") == "text")


@dataclass(frozen=True)
class AgentOutcome:
    stop: Stop
    result: ProviderResult  # the last response
    turns: int
    usage: Usage  # summed over turns
    cost_usd_micros: int
    messages: list[Message]  # full history, assistant content unedited


class AiProvider(Protocol):
    name: str

    async def single_call(self, req: ProviderRequest) -> ProviderResult: ...

    async def agent_run(
        self,
        req: ProviderRequest,
        *,
        max_turns: int = 20,
        stop_micro: int = 800_000,
        run_tool: ToolRunner | None = None,
    ) -> AgentOutcome: ...


def add_usage(a: Usage, b: Usage) -> Usage:
    return Usage(**{f.name: getattr(a, f.name) + getattr(b, f.name) for f in fields(Usage)})


async def agent_loop(
    call: Callable[[ProviderRequest], Awaitable[ProviderResult]],
    req: ProviderRequest,
    max_turns: int,
    stop_micro: int,
    run_tool: ToolRunner | None,
) -> AgentOutcome:
    """The provider-level turn loop: resend on pause_turn, run client tools, stop on refusal, turns or spend.
    Dollar check between turns (06 section 2.3). Cancel, deadline and ingest belong to the caller (WF-049)."""
    messages = list(req.messages)
    usage, cost = Usage(), 0
    r: ProviderResult | None = None
    for turn in range(1, max_turns + 1):
        r = await call(replace(req, messages=list(messages)))
        usage, cost = add_usage(usage, r.usage), cost + r.cost_usd_micros
        messages.append({"role": "assistant", "content": r.content})
        if r.stop_reason == "refusal":
            return AgentOutcome("refusal", r, turn, usage, cost, messages)
        if cost >= stop_micro:
            return AgentOutcome("spend_limit", r, turn, usage, cost, messages)
        if r.stop_reason == "tool_use" and run_tool:
            results = [await run_tool(b) for b in r.content if b.get("type") == "tool_use"]
            messages.append({"role": "user", "content": results})
        elif r.stop_reason != "pause_turn":
            known = ("end_turn", "max_tokens", "stop_sequence", "tool_use")
            stop = (
                r.stop_reason if r.stop_reason in known else "unknown"
            )  # tool_use here: no run_tool given
            return AgentOutcome(stop, r, turn, usage, cost, messages)  # type: ignore[arg-type]
    assert r is not None
    return AgentOutcome("turn_limit", r, max_turns, usage, cost, messages)
