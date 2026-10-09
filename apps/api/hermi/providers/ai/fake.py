# ruff: noqa: E501
"""The fake backend: replays recorded Messages responses from fixtures/. No network, no spend."""

import json
from pathlib import Path

from hermi.modules.ai.metering import usage_from_response
from hermi.providers.ai.base import (
    AgentOutcome,
    ProviderRequest,
    ProviderResult,
    ToolRunner,
    agent_loop,
)

FIXTURES = Path(__file__).parent / "fixtures"


def result_from_message(msg: dict, provider: str, cost: int) -> ProviderResult:
    usage = msg.get("usage") or {}
    return ProviderResult(
        provider=provider,
        model=msg.get("model", ""),
        content=list(msg.get("content") or []),
        stop_reason=msg["stop_reason"],
        usage=usage_from_response(usage),
        cost_usd_micros=cost,
        server_tool_use=dict(usage.get("server_tool_use") or {}),
        stop_details=msg.get("stop_details"),
    )


class FakeProvider:
    name = "fake"

    def __init__(self, script: str | list[str] = "end_turn") -> None:
        """A fixture name repeats forever; a list is replayed in order (the last one then repeats)."""
        self._script = [script] if isinstance(script, str) else list(script)
        self.calls: list[ProviderRequest] = []

    async def single_call(self, req: ProviderRequest) -> ProviderResult:
        self.calls.append(req)
        scenario = self._script.pop(0) if len(self._script) > 1 else self._script[0]
        msg = json.loads((FIXTURES / f"{scenario}.json").read_text(encoding="utf-8"))
        return result_from_message(msg, self.name, 0)

    async def agent_run(
        self,
        req: ProviderRequest,
        *,
        max_turns: int = 20,
        stop_micro: int = 800_000,
        run_tool: ToolRunner | None = None,
    ) -> AgentOutcome:
        return await agent_loop(self.single_call, req, max_turns, stop_micro, run_tool)
