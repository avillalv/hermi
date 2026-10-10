# ruff: noqa: E501
"""The anthropic_api backend: the Messages API with tools and server tools (06 sections 2.2 to 2.4).

The client is injected (tests pass a stub, never the network). The default is the `anthropic` SDK async client,
imported lazily because only this package may import it.
"""

from dataclasses import replace
from typing import Any

from hermi.modules.ai.metering import cost_usd_micros
from hermi.providers import NotConfigured, ProviderError
from hermi.providers.ai.base import (
    AgentOutcome,
    ProviderRequest,
    ProviderResult,
    ToolRunner,
    agent_loop,
)
from hermi.providers.ai.fake import result_from_message


def default_client(api_key: str) -> Any:
    try:
        import anthropic
    except ImportError as e:
        raise NotConfigured("the anthropic package is not installed") from e
    return anthropic.AsyncAnthropic(api_key=api_key, max_retries=2)


class AnthropicApiProvider:
    name = "anthropic_api"

    def __init__(self, client: Any) -> None:
        self._client = client

    async def aclose(self) -> None:
        """Close the SDK client (its HTTP pool). Injected stubs without `close` are left alone."""
        close = getattr(self._client, "close", None)
        if close is not None:
            await close()

    async def single_call(self, req: ProviderRequest) -> ProviderResult:
        clash = {"model", "max_tokens", "messages"} & req.extra.keys()
        if clash:
            raise ProviderError(f"extra must not override {sorted(clash)}")
        kw: dict[str, Any] = {
            **req.extra,
            "model": req.model,
            "max_tokens": req.max_tokens,
            "messages": req.messages,
        }
        if req.system is not None:
            kw["system"] = req.system
        if req.tools:
            kw["tools"] = req.tools
        if req.output_schema is not None:
            # merged, so a caller's effort in extra["output_config"] survives
            kw["output_config"] = {
                **kw.get("output_config", {}),
                "format": {"type": "json_schema", "schema": req.output_schema},
            }
        msg = await self._client.messages.create(**kw)
        msg = msg if isinstance(msg, dict) else msg.model_dump()
        r = result_from_message({**msg, "model": msg.get("model") or req.model}, self.name, 0)
        return replace(r, cost_usd_micros=cost_usd_micros(r.usage, r.model))

    async def agent_run(
        self,
        req: ProviderRequest,
        *,
        max_turns: int = 20,
        stop_micro: int = 800_000,
        run_tool: ToolRunner | None = None,
    ) -> AgentOutcome:
        return await agent_loop(self.single_call, req, max_turns, stop_micro, run_tool)
