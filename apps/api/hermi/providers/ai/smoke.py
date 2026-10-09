# ruff: noqa: E501
"""`hermi ai-smoke` (06 section 2.7): one no-tool call and one capped web-tool call through the claude_cli provider.
It uses the owner's subscription, so tests run it only against the fake `claude`."""

from collections.abc import Callable

from hermi.providers.ai.base import ProviderRequest
from hermi.providers.ai.claude_cli import ClaudeCliProvider, CliRunFailed

SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


async def _smoke(p: ClaudeCliProvider, model: str, out: Callable[[str], None]) -> int:
    def ask(text: str, **extra) -> ProviderRequest:
        return ProviderRequest(
            model=model, system="You are a terse test fixture.", max_tokens=200,
            messages=[{"role": "user", "content": text}], **extra,
        )  # fmt: skip

    try:
        r = await p.single_call(
            ask('Reply with {"ok": true}.', output_schema=SCHEMA, extra={"stop_micro": 100_000})
        )
        out(f"no tools: ok, {r.text}, ${r.cost_usd_micros / 1e6:.4f} notional")
        caps = {"max_searches": 1, "max_fetches": 1}
        o = await p.agent_run(
            ask("Search the web once for the newest Python release, then answer in one line.", extra=caps),
            max_turns=6, stop_micro=250_000,
        )  # fmt: skip
        run = p.last_run
        out(
            f"web tools: {o.stop}, {run.searches} search, {run.fetches} fetch "
            f"(caps {caps['max_searches']}/{caps['max_fetches']}), {len(run.evidence.found)} links, "
            f"${o.cost_usd_micros / 1e6:.4f} notional"
        )
    except CliRunFailed as e:
        out(f"failed ({e.status}): {e}")
        return 1
    return 0


def run_smoke(p: ClaudeCliProvider, model: str, out: Callable[[str], None] = print) -> int:
    import asyncio

    return asyncio.run(_smoke(p, model, out))
