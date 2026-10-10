# ruff: noqa: E501
"""AgentLoop (06 sections 2.3 and 6.4): the hand-written multi-turn tool loop.

One loop for every backend. On `anthropic_api` and `fake` it drives `provider.single_call` turn by turn, so it can check
cancel, deadline and dollars between turns and run the client tools in-process. On `claude_cli` the CLI runs its own
loop; this class passes the caps and the cancel flag down, maps its stops to ours and saves the final JSON through the
same handlers (the stream counters and the blocked host check live in providers/ai/claude_cli.py).

Stops and what each leaves behind: everything a handler already saved stays. `final_status` maps a stop and the saved
count to the run status and failure code. Credits and the runs row are the job's business (jobs/run_agent.py).
"""

import asyncio
import contextlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from hermi.modules.ai.metering import Usage
from hermi.providers.ai.base import AiProvider, ProviderRequest, ProviderResult, add_usage
from hermi.providers.ai.claude_cli import CliRunFailed
from hermi_worker.agents.prompts import NUDGE
from hermi_worker.agents.spec import MAX_TOKENS_CEILING, AgentSpec
from hermi_worker.agents.tools import (
    CLI_FINAL_SCHEMA,
    Block,
    Emit,
    Evidence,
    Handler,
    ToolContext,
    ToolExecutor,
    blocked_url,
    check_schema,
    tool_defs,
)

# Why a run ended. `finished` is the only clean one.
STOPS = (
    "finished", "no_finish", "cancelled", "deadline", "spend_limit", "turn_limit", "search_cap", "fetch_cap",
    "blocked_domain", "refusal", "max_tokens", "model_mismatch", "invalid_tool_input",
)  # fmt: skip
_LIMIT_STOPS = {"turn_limit", "search_cap", "fetch_cap", "spend_limit", "no_finish", "max_tokens", "blocked_domain", "invalid_tool_input"}


def final_status(stop: str, saved: int) -> tuple[str, str | None]:
    """(run status, failure_code) for a stop and the number of items saved (accepted quotes plus notes). A run that
    saved nothing is failed `nothing_saved` and refunded; a run that saved something keeps it, marked partial."""
    match stop:
        case "finished":
            return ("succeeded", None) if saved else ("failed", "nothing_saved")
        case "cancelled":
            return "cancelled", "cancelled"
        case "deadline":
            return "timed_out", None if saved else "nothing_saved"
        case "refusal":
            return "failed", "refused"
        case "model_mismatch":
            return "failed", "model_mismatch"
        case s if s in _LIMIT_STOPS:
            code = "budget_stop" if s == "spend_limit" else s
            return ("partial", code) if saved else ("failed", "nothing_saved")
    raise ValueError(f"unknown stop {stop!r}")


@dataclass
class Hooks:
    """What the loop needs from its caller. All are cheap and synchronous; the job backs them with the database."""

    is_cancelled: Callable[[], bool] = lambda: False  # also the job's heartbeat: called about once a second
    emit: Emit = lambda *a, **k: None  # emit(type, summary, payload=None, tool_name=None) -> a run_events row
    on_response: Callable[[int, ProviderResult], None] = lambda turn, result: None  # meter one response (record_usage)
    clock: Callable[[], float] = time.monotonic
    poll_seconds: float = 1.0  # how often a call in flight is checked for cancel and deadline


@dataclass
class RunOutcome:
    stop: str
    status: str
    failure_code: str | None
    turns: int
    searches: int
    fetches: int
    cost_usd_micros: int
    usage: Usage
    accepted: int
    rejected: int
    report: Block | None
    evidence: Evidence
    messages: list[dict[str, Any]] = field(default_factory=list)
    last: ProviderResult | None = None

    @property
    def saved(self) -> int:
        return self.accepted


class _Stop(Exception):
    def __init__(self, stop: str) -> None:
        self.stop = stop


def _doc_text(content: Any) -> str:
    """The text of a web_fetch_result's document, whatever the source shape."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        for key in ("data", "text", "content", "source"):
            if key in content and (t := _doc_text(content[key])):
                return t
    if isinstance(content, list):
        return "\n".join(t for c in content if (t := _doc_text(c)))
    return ""


class AgentLoop:
    def __init__(self, provider: AiProvider, spec: AgentSpec, handlers: dict[str, Handler], hooks: Hooks | None = None, *, initial_cost: int = 0) -> None:
        self.provider, self.spec, self.handlers = provider, spec, handlers
        self.h = hooks or Hooks()
        self.evidence = Evidence()
        self.exec = ToolExecutor(handlers, ToolContext(self.evidence, self.h.emit))
        self.turns = self.searches = self.fetches = 0
        self.cost = initial_cost
        self.usage = Usage()
        self.last: ProviderResult | None = None
        self.messages: list[dict[str, Any]] = []
        self.deadline = 0.0

    # --- public -------------------------------------------------------------------------------------------------

    async def run(self, task: str) -> RunOutcome:
        self.deadline = self.h.clock() + self.spec.deadline_s
        self.messages = [{"role": "user", "content": [{"type": "text", "text": task}]}]
        try:
            if self.provider.name == "claude_cli":
                stop = await self._run_cli()
            else:
                stop = await self._run_api()
        except _Stop as s:
            stop = s.stop
        status, code = final_status(stop, self.exec.accepted)
        self.h.emit("info", f"stopped: {stop}", {"kind": "stop", "stop": stop, "status": status, "failure_code": code})
        return RunOutcome(
            stop, status, code, self.turns, self.searches, self.fetches, self.cost, self.usage, self.exec.accepted,
            self.exec.rejected, self.exec.report, self.evidence, self.messages, self.last,
        )  # fmt: skip

    # --- anthropic_api and fake ---------------------------------------------------------------------------------

    def _request(self, max_tokens: int) -> ProviderRequest:
        s = self.spec
        return ProviderRequest(
            model=s.model,
            # tools, then system with the cache breakpoint, then the task: a byte change in a prefix invalidates what follows (7.2)
            system=[{"type": "text", "text": s.system, "cache_control": {"type": "ephemeral"}}],
            messages=list(self.messages),
            max_tokens=max_tokens,
            tools=tool_defs(s, self.searches, self.fetches),
            extra={"thinking": {"type": "adaptive"}, "output_config": {"effort": s.effort}},
        )

    def _checkpoint(self) -> None:
        if self.h.is_cancelled():
            raise _Stop("cancelled")
        if self.h.clock() >= self.deadline:
            raise _Stop("deadline")
        if self.cost >= self.spec.stop_micro:
            raise _Stop("spend_limit")

    async def _call(self, req: ProviderRequest) -> ProviderResult:
        """One request under a watchdog: a cancel or the deadline ends it mid-flight (06 section 2.3 rule 6)."""
        task = asyncio.ensure_future(self.provider.single_call(req))
        try:
            while True:
                left = self.deadline - self.h.clock()
                done, _ = await asyncio.wait({task}, timeout=max(0.0, min(self.h.poll_seconds, left)))
                if done:
                    return task.result()
                if self.h.is_cancelled():
                    raise _Stop("cancelled")
                if self.h.clock() >= self.deadline:
                    raise _Stop("deadline")
        finally:
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task

    async def _run_api(self) -> str:
        s, max_tokens, retried, nudged = self.spec, self.spec.max_tokens, False, False
        for turn in range(1, s.max_turns + 1):
            self._checkpoint()
            r = await self._call(self._request(max_tokens))
            self.turns, self.last = turn, r
            self.cost += r.cost_usd_micros
            self.usage = add_usage(self.usage, r.usage)
            self.h.on_response(turn, r)
            if s.allowed_models and r.model not in s.allowed_models:
                raise _Stop("model_mismatch")
            if r.stop_reason == "refusal":
                self.messages.append({"role": "assistant", "content": r.content})
                raise _Stop("refusal")
            if brand := self._scan(r):  # before any tool runs: a blocked page is never evidence and never acted on
                self.h.emit("error", f"blocked {brand} page", {"kind": "blocked_domain", "brand": brand})
                raise _Stop("blocked_domain")
            if r.stop_reason == "max_tokens":
                # never run a half-parsed tool input: retry this turn once with a higher cap, else stop
                if retried or max_tokens >= MAX_TOKENS_CEILING:
                    raise _Stop("max_tokens")
                retried, max_tokens = True, min(MAX_TOKENS_CEILING, max_tokens * 2)
                continue
            self.messages.append({"role": "assistant", "content": r.content})  # exactly as returned (rule 1)
            over = self._over_cap()
            calls = [b for b in r.content if b.get("type") == "tool_use"]
            if r.stop_reason == "tool_use" or calls:
                results = [await self.exec.run(b) for b in calls]
                if results:
                    self.messages.append({"role": "user", "content": results})
                if self.exec.finished:
                    return "finished"
                if any(n >= 2 for n in self.exec.invalid.values()):
                    raise _Stop("invalid_tool_input")
                if over:
                    raise _Stop(over)
                continue
            if over:
                raise _Stop(over)
            if r.stop_reason == "pause_turn":
                continue  # the server tool loop hit its iteration cap; resend as is
            if self.exec.finished:
                return "finished"
            if not nudged:
                nudged = True
                self.messages.append({"role": "user", "content": [{"type": "text", "text": NUDGE}]})
                continue
            return "no_finish"
        return "turn_limit"

    def _over_cap(self) -> str | None:
        """A stop to take once this response's tools have run, so saved work is kept (06 section 6.4). The server
        enforces `max_uses`; seeing more than the cap means it let one through, and the run stops."""
        if self.searches > self.spec.max_searches:
            return "search_cap"
        if self.fetches > self.spec.max_fetches:
            return "fetch_cap"
        if self.cost >= self.spec.stop_micro:
            return "spend_limit"
        return None

    def _scan(self, r: ProviderResult) -> str | None:
        """Count server tool use, collect evidence, report server tool errors. Returns a blocked brand when a fetch
        input or a fetched result is on a blocked host (the API list cannot name every country domain)."""
        emit, searches, fetches = self.h.emit, 0, 0
        for b in r.content:
            t = b.get("type")
            if t == "server_tool_use":
                name = b.get("name")
                emit("tool_use", f"{name}", {"tool_use_id": b.get("id"), "server": True}, name)
                if name == "web_search":
                    searches += 1
                elif name == "web_fetch":
                    fetches += 1
                    if brand := blocked_url(str((b.get("input") or {}).get("url", ""))):
                        return self._count(searches, fetches, r, brand)
            elif t == "web_fetch_tool_result":
                c = b.get("content")
                if isinstance(c, dict) and c.get("type") == "web_fetch_result":
                    url = str(c.get("url", ""))
                    if brand := blocked_url(url):  # a redirect can land on a blocked host
                        return self._count(searches, fetches, r, brand)
                    self.evidence.fetched[url] = _doc_text(c.get("content"))
                elif isinstance(c, dict) and c.get("error_code"):
                    emit("warning", f"web_fetch: {c['error_code']}", {"error_code": c["error_code"]}, "web_fetch")
            elif t == "web_search_tool_result":
                c = b.get("content")
                if isinstance(c, list):
                    for item in c:
                        url = str(item.get("url", "")) if isinstance(item, dict) else ""
                        if url and not blocked_url(url):
                            self.evidence.found.add(url)
                elif isinstance(c, dict) and c.get("error_code"):
                    emit("warning", f"web_search: {c['error_code']}", {"error_code": c["error_code"]}, "web_search")
            elif t == "text" and (text := (b.get("text") or "").strip()):
                emit("text", text[:300])
        return self._count(searches, fetches, r, None)

    def _count(self, searches: int, fetches: int, r: ProviderResult, brand: str | None) -> str | None:
        # the usage counter and the blocks can differ (a pause_turn resend); the larger is the safer count
        self.searches += max(searches, r.usage.web_searches)
        self.fetches += fetches
        return brand

    # --- claude_cli ---------------------------------------------------------------------------------------------

    async def _run_cli(self) -> str:
        s = self.spec
        self._checkpoint()
        req = ProviderRequest(
            model=s.model, system=s.system, messages=list(self.messages), max_tokens=s.max_tokens,
            output_schema=CLI_FINAL_SCHEMA,
            extra={
                "max_searches": s.max_searches, "max_fetches": s.max_fetches, "timeout_s": max(1.0, self.deadline - self.h.clock()),
                "is_cancelled": self.h.is_cancelled, "stop_micro": s.stop_micro,
            },
        )  # fmt: skip
        try:
            out = await self.provider.agent_run(req, max_turns=s.max_turns, stop_micro=s.stop_micro)
        except CliRunFailed as e:
            run = e.run
            if run is not None:
                self.searches, self.fetches = run.searches, run.fetches
                self.evidence.found |= {u for u in run.evidence.found if not blocked_url(u)}
            if e.status == "cap_exceeded":
                raise _Stop("search_cap" if self.searches > s.max_searches else "fetch_cap") from e
            stop = {"blocked_domain": "blocked_domain", "timeout": "deadline", "cancelled": "cancelled"}.get(e.status)
            if stop is None:
                raise  # a guard failure, a missing binary, an error result: the job fails and refunds
            raise _Stop(stop) from e
        self.turns, self.last = out.turns, out.result
        self.cost += out.cost_usd_micros
        self.usage = add_usage(self.usage, out.usage)
        self.searches = max(self.searches, out.result.usage.web_searches)
        last = getattr(self.provider, "last_run", None)
        if last is not None:
            self.fetches = last.fetches
            self.evidence.found |= {u for u in last.evidence.found if not blocked_url(u)}
            for u in last.evidence.fetched:
                if blocked_url(u):
                    raise _Stop("blocked_domain")
                self.evidence.fetched.setdefault(u, "")
        self.h.on_response(out.turns, out.result)
        if s.allowed_models and out.result.model not in s.allowed_models:
            raise _Stop("model_mismatch")
        if out.stop in ("spend_limit", "turn_limit", "refusal"):
            raise _Stop(out.stop)
        try:
            final = json.loads(out.result.text)
        except ValueError:
            return "no_finish"
        if not isinstance(final, dict) or check_schema(CLI_FINAL_SCHEMA, final):
            return "no_finish"
        # the same handlers as the tool path, so the evidence rules are written once
        calls: list[Block] = []
        if final["quotes"]:
            calls.append({"id": "cli_quotes", "name": "submit_flight_quotes", "input": {"quotes": final["quotes"]}})
        calls += [{"id": f"cli_note_{i}", "name": "add_note", "input": n} for i, n in enumerate(final["notes"])]
        for c in calls:
            await self.exec.run(c)
        report = {k: final[k] for k in ("status", "summary", "sources_checked", "issues")}
        await self.exec.run({"id": "cli_finish", "name": "finish_run", "input": report})
        return "finished" if self.exec.finished else "no_finish"
