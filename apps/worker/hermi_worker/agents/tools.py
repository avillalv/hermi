# ruff: noqa: E501
"""Tools of an agent run (06 sections 2.4 and 2.5): the two server tools with the blocked list generated from policy,
the in-process client tools `submit_flight_quotes`, `add_note` and `finish_run`, and the executor.

The handlers of `get_task`, `lookup_airports`, `submit_flight_quotes` and `add_note` are injected callbacks (jobs/run_agent.py
binds them to the runs row and the evidence rules of hermi.modules.ai.ingest). The loop owns `finish_run`. Input is validated against the tool's schema before any
handler runs, because streamed partial JSON can be truncated (2.3 rule 7).
"""

import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from hermi.modules.ai.policy import api_blocked_domains, blocked_domain
from hermi_worker.agents.spec import AgentSpec

Block = dict[str, Any]
Emit = Callable[..., None]  # emit(type, summary, payload=None, tool_name=None)


def host_of(url: str) -> str:
    """The lowercase host of a URL, with or without a scheme. Empty when there is none."""
    try:
        return (urlsplit(url if "//" in url else f"//{url}").hostname or "").lower()
    except ValueError:
        return ""


def blocked_url(url: str) -> str | None:
    """The blocked brand a URL belongs to (subdomains and any ending), or None."""
    return blocked_domain(host_of(url))


# --- tool definitions ---------------------------------------------------------------------------------------------

_QUOTE_ITEM = {
    "type": "object",
    "properties": {
        "route_ref": {"type": "string", "description": "The route reference from the task, such as R1."},
        "origin": {"type": "string", "description": "Departure airport IATA code; one of the route's origins."},
        "destination": {"type": "string", "description": "Arrival airport IATA code; one of the route's destinations."},
        "depart_date": {"type": "string", "format": "date"},
        "return_date": {"type": ["string", "null"], "format": "date", "description": "Required for round trips; null for one way."},
        "price_total": {"type": "string", "description": "The price exactly as the page showed it, digits and decimal point only, for example 412.00."},
        "currency": {"type": "string", "description": "ISO 4217 code of the currency shown, for example USD, EUR, JPY."},
        "passengers": {"type": "integer", "minimum": 1, "maximum": 17, "description": "Travelers the price covers: the route's party size, or 1 if the page shows a per-person price."},
        "airlines": {"type": "array", "items": {"type": "string", "maxLength": 60}, "maxItems": 6},
        "stops_outbound": {"type": ["integer", "null"], "minimum": 0, "maximum": 4},
        "stops_return": {"type": ["integer", "null"], "minimum": 0, "maximum": 4},
        "duration_outbound_min": {"type": ["integer", "null"], "minimum": 30, "maximum": 4000},
        "source_url": {"type": "string", "maxLength": 2000, "description": "The exact page that showed this price."},
        "seen_on": {"type": ["string", "null"], "maxLength": 80, "description": "The site's name, for example Kayak or united.com."},
        "notes": {"type": ["string", "null"], "maxLength": 300},
    },
    "required": [
        "route_ref", "origin", "destination", "depart_date", "return_date", "price_total", "currency", "passengers",
        "airlines", "stops_outbound", "stops_return", "duration_outbound_min", "source_url", "seen_on", "notes",
    ],
    "additionalProperties": False,
}  # fmt: skip

SUBMIT_FLIGHT_QUOTES: Block = {
    "name": "submit_flight_quotes",
    "description": "Saves fares you saw on a web page during this run. Each item is checked on its own. The reply marks each item accepted, rejected (with reasons) or duplicate. Submit in small batches as you find fares.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "quotes": {"type": "array", "minItems": 1, "maxItems": 50, "items": _QUOTE_ITEM}
        },
        "required": ["quotes"],
        "additionalProperties": False,
    },
}

_NOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 160},
        "body": {
            "type": "string",
            "minLength": 1,
            "maxLength": 4000,
            "description": "Plain text. No markdown links, no instructions to the reader.",
        },
        "urls": {
            "type": "array",
            "items": {"type": "string", "maxLength": 2000},
            "minItems": 1,
            "maxItems": 10,
        },
        "topic": {
            "type": "string",
            "enum": [
                "events",
                "closures",
                "reservations",
                "transport",
                "weather",
                "neighborhoods",
                "food",
                "safety_notice",
                "other",
            ],
        },
    },
    "required": ["title", "body", "urls", "topic"],
    "additionalProperties": False,
}

ADD_NOTE: Block = {
    "name": "add_note",
    "description": "Saves one finding as a note with the links it came from. Each note must stand on its own: a specific title, the facts that matter (dates, prices, how to book, deadlines) and the links you used.",
    "strict": True,
    "input_schema": _NOTE_SCHEMA,
}

LOOKUP_AIRPORTS: Block = {
    "name": "lookup_airports",
    "description": "Turns a city or airport name into IATA codes. Returns up to 8 matches with city, country and code.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "minLength": 2, "maxLength": 80}},
        "required": ["query"],
        "additionalProperties": False,
    },
}

GET_TASK: Block = {
    "name": "get_task",
    "description": "Returns the task again: trip summary, routes with their references, date rules, the cheapest price the app already knows for each route, and the blocked site list. Call it if you lose track of the route references.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

_FINISH_PROPS = {
    "status": {"type": "string", "enum": ["ok", "partial", "failed"]},
    "summary": {"type": "string", "minLength": 1, "maxLength": 2000},
    "sources_checked": {
        "type": "array",
        "items": {"type": "string", "maxLength": 300},
        "maxItems": 40,
    },
    "issues": {"type": "array", "items": {"type": "string", "maxLength": 500}, "maxItems": 20},
}

FINISH_RUN: Block = {
    "name": "finish_run",
    "description": "Ends the run with your report. Call it exactly once, last.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": _FINISH_PROPS,
        "required": ["status", "summary", "sources_checked", "issues"],
        "additionalProperties": False,
    },
}

CLIENT_TOOLS: tuple[Block, ...] = (
    SUBMIT_FLIGHT_QUOTES,
    ADD_NOTE,
    LOOKUP_AIRPORTS,
    GET_TASK,
    FINISH_RUN,
)

# The final JSON of a claude_cli run (there are no client tools there): the report plus what to save (06 section 2.5).
CLI_FINAL_SCHEMA: Block = {
    "type": "object",
    "properties": {
        **_FINISH_PROPS,
        "quotes": {"type": "array", "maxItems": 50, "items": _QUOTE_ITEM},
        "notes": {"type": "array", "maxItems": 20, "items": _NOTE_SCHEMA},
    },
    "required": ["status", "summary", "sources_checked", "issues", "quotes", "notes"],
    "additionalProperties": False,
}


def server_tools(spec: AgentSpec, searches: int = 0, fetches: int = 0) -> list[Block]:
    """web_search and web_fetch with the caps and one blocked list, generated from policy (06 section 2.4).
    `max_uses` is what is left of the run's budget after `searches` and `fetches` used so far (the API counts per
    request, 06 section 6.4); a tool with nothing left is left out. `blocked_domains` only: the API forbids
    `allowed_domains` in the same config."""
    blocked = api_blocked_domains()
    out: list[Block] = []
    if (left := spec.max_searches - searches) > 0:
        out.append(
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "max_uses": left,
                "blocked_domains": blocked,
            }
        )
    if (left := spec.max_fetches - fetches) > 0:
        out.append({
            "type": "web_fetch_20260209", "name": "web_fetch", "max_uses": left,
            "max_content_tokens": spec.max_content_tokens, "citations": {"enabled": False}, "blocked_domains": blocked,
        })  # fmt: skip
    return out


def tool_defs(spec: AgentSpec, searches: int = 0, fetches: int = 0) -> list[Block]:
    return [*server_tools(spec, searches, fetches), *CLIENT_TOOLS]


# --- schema check -------------------------------------------------------------------------------------------------

_TYPES: dict[str, Callable[[Any], bool]] = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, int | float) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "null": lambda v: v is None,
}


def check_schema(schema: Block, value: Any, path: str = "input") -> str | None:
    """The first problem with `value` against the JSON Schema subset our tools use, or None. No dependency: the tool
    schemas are ours and use only type, enum, bounds, required, items and additionalProperties."""
    types = schema.get("type")
    if types is not None:
        names = [types] if isinstance(types, str) else types
        if not any(_TYPES[n](value) for n in names):
            return f"{path} must be {' or '.join(names)}"
    if value is None:
        return None
    if "enum" in schema and value not in schema["enum"]:
        return f"{path} must be one of {', '.join(map(str, schema['enum']))}"
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            return f"{path} is too short"
        if len(value) > schema.get("maxLength", len(value)):
            return f"{path} is too long"
    if isinstance(value, int | float) and not isinstance(value, bool):
        if value < schema.get("minimum", value):
            return f"{path} is below {schema['minimum']}"
        if value > schema.get("maximum", value):
            return f"{path} is above {schema['maximum']}"
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            return f"{path} needs at least {schema['minItems']} items"
        if len(value) > schema.get("maxItems", len(value)):
            return f"{path} has more than {schema['maxItems']} items"
        if "items" in schema:
            for i, item in enumerate(value):
                if problem := check_schema(schema["items"], item, f"{path}[{i}]"):
                    return problem
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                return f"{path}.{name} is required"
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in props:
                    return f"{path}.{name} is not allowed"
        for name, sub in props.items():
            if name in value and (problem := check_schema(sub, value[name], f"{path}.{name}")):
                return problem
    return None


# --- evidence and the executor ------------------------------------------------------------------------------------


@dataclass
class Evidence:
    """What this run really showed (06 section 2.5 item 6): URLs returned by search and pages fetched, with their text
    for price grounding. Blocked hosts never enter it. `hermi.modules.ai.ingest` builds its provenance and grounding checks on this."""

    found: set[str] = field(default_factory=set)
    fetched: dict[str, str] = field(default_factory=dict)
    # shortcut: pages the claude_cli stream says were fetched, with no document text. Ceiling: their prices cannot be grounded,
    # so ingest accepts them as indicative only (local dev). Trigger: the CLI stream exposing document text.
    unchecked: set[str] = field(default_factory=set)

    def seen(self, url: str) -> bool:
        return url in self.found or url in self.fetched or url in self.unchecked


@dataclass
class ToolContext:
    evidence: Evidence
    emit: Emit
    turn: int = 0


@dataclass(frozen=True)
class ToolOutput:
    content: Any  # a string, or JSON-able data the model reads
    is_error: bool = False
    accepted: int = 0  # items saved by this call (a quote, a note)
    rejected: int = 0


Handler = Callable[[Block, ToolContext], ToolOutput | Awaitable[ToolOutput]]


class ToolExecutor:
    """Runs the client tool_use blocks of one response. Parallel calls run in order and every one gets a tool_result;
    a failure is `is_error: true`, never dropped (2.3 rule 2)."""

    def __init__(self, handlers: dict[str, Handler], ctx: ToolContext) -> None:
        self.handlers, self.ctx = handlers, ctx
        self.finished = False
        self.report: Block | None = None
        self.accepted = 0
        self.rejected = 0
        self.invalid: dict[str, int] = {}  # consecutive invalid inputs per tool

    async def run(self, block: Block) -> Block:
        name, tid = str(block.get("name", "")), block.get("id", "")
        self.ctx.emit("tool_use", f"{name}", {"tool_use_id": tid}, name)
        out = await self._dispatch(name, block.get("input"))
        self.accepted += out.accepted
        self.rejected += out.rejected
        content = (
            out.content if isinstance(out.content, str) else json.dumps(out.content, default=str)
        )
        self.ctx.emit(
            "tool_result", f"{name}: {'error' if out.is_error else 'ok'}",
            {"tool_use_id": tid, "accepted": out.accepted, "rejected": out.rejected}, name,
        )  # fmt: skip
        result: Block = {"type": "tool_result", "tool_use_id": tid, "content": content}
        if out.is_error:
            result["is_error"] = True
        return result

    async def _dispatch(self, name: str, args: Any) -> ToolOutput:
        schema = next((t["input_schema"] for t in CLIENT_TOOLS if t["name"] == name), None)
        if schema is None:
            return ToolOutput(f"{name} is not a tool you have.", is_error=True)
        if problem := check_schema(schema, args):
            self.invalid[name] = self.invalid.get(name, 0) + 1
            return ToolOutput(
                f"Invalid input: {problem}. Fix it and call {name} again.", is_error=True
            )
        self.invalid[name] = 0
        if name == "finish_run":
            if self.finished:
                return ToolOutput("The run is already finished.", is_error=True)
            self.finished, self.report = (
                True,
                dict(args),
            )  # the runner, not the model, sets the final status
            return ToolOutput("Report saved.")
        handler = self.handlers.get(name)
        if handler is None:
            return ToolOutput(f"{name} is not available in this run.", is_error=True)
        try:
            out = handler(args, self.ctx)
            return await out if inspect.isawaitable(out) else out
        except (
            Exception
        ) as e:  # a handler bug must not lose the run; the type only, the text may carry page data
            self.ctx.emit("error", f"{name} failed", {"error": type(e).__name__}, name)
            return ToolOutput(f"{name} failed. Try again later.", is_error=True)
