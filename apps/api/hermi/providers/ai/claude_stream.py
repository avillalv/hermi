# ruff: noqa: E501
"""Parses `claude -p --output-format stream-json` (06 section 2.7): init facts, tool counters, the result event and
the evidence the run saw. Ported from the Trip Planner stream parser, without the MCP prefix or the log summaries.
No process handling here; claude_cli.py owns that."""

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from hermi.modules.ai.policy import blocked_domain

WEB_TOOLS = ("WebSearch", "WebFetch")
_LINKS = re.compile(r"Links:\s*(\[.*\])")


@dataclass
class StreamState:
    version: str | None = None
    model: str | None = None
    tools: list[str] = field(default_factory=list)
    mcp_servers: list[Any] = field(default_factory=list)
    api_key_source: str | None = None
    models_seen: set[str] = field(default_factory=set)
    result: dict[str, Any] | None = None
    tool_names: dict[str, str] = field(default_factory=dict)
    searches: int = 0
    fetches: int = 0
    inited: bool = False


@dataclass
class EvidenceCollector:
    """URLs the run really showed: `fetched` (WebFetch inputs) and `found` (WebSearch result links)."""

    fetched: set[str] = field(default_factory=set)
    found: set[str] = field(default_factory=set)

    def add_search_result(self, text: str) -> None:
        # On 2.1.288 the links are a JSON array on one line after `Links:`, not markdown.
        if not (m := _LINKS.search(text)):
            return
        try:
            items = json.loads(m.group(1))
        except ValueError:
            return
        self.found.update(
            i["url"] for i in items if isinstance(i, dict) and isinstance(i.get("url"), str)
        )


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"
        )
    return ""


class StreamParser:
    """Feed it stdout lines. `violation` is set to `cap_exceeded` or `blocked_domain` (with `problem`) the moment
    the stream breaks a cap or fetches a blocked host; the runner then kills the process tree."""

    def __init__(self, max_searches: int, max_fetches: int) -> None:
        self.state = StreamState()
        self.evidence = EvidenceCollector()
        self.events: list[dict[str, Any]] = []
        self.max_searches, self.max_fetches = max_searches, max_fetches
        self.violation: str | None = None
        self.problem: str | None = None

    def _violate(self, code: str, problem: str) -> None:
        if self.violation is None:
            self.violation, self.problem = code, problem

    def feed(self, line: str) -> None:
        try:
            event = json.loads(line)
        except ValueError:
            return
        if not isinstance(event, dict):
            return
        self.events.append(event)
        match event.get("type"):
            case "system" if event.get("subtype") == "init":
                s = self.state
                s.inited = True
                s.version = event.get("claude_code_version")
                s.model = event.get("model")
                s.tools = list(event.get("tools") or [])
                s.mcp_servers = list(event.get("mcp_servers") or [])
                s.api_key_source = event.get("apiKeySource")
            case "assistant":
                self._assistant(event)
            case "user":
                self._user(event)
            case "result":
                self.state.result = event

    def _assistant(self, event: dict[str, Any]) -> None:
        if self.violation:
            return  # the run is being killed; later lines are not counted or kept as evidence
        msg = event.get("message") or {}
        if (model := msg.get("model")) and model != "<synthetic>":
            self.state.models_seen.add(model)
        for block in msg.get("content") or []:
            if block.get("type") != "tool_use":
                continue
            name, args = str(block.get("name", "")), block.get("input") or {}
            self.state.tool_names[block.get("id", "")] = name
            if name == "WebSearch":
                self.state.searches += 1
                if self.state.searches > self.max_searches:
                    self._violate("cap_exceeded", f"The run tried more than {self.max_searches} web searches.")
            elif name == "WebFetch":
                url = str(args.get("url", ""))
                host = (urlsplit(url).hostname or "") if url else ""
                if brand := blocked_domain(host):
                    self._violate("blocked_domain", f"The run tried to open a {brand} page, which is never allowed.")
                    continue  # a blocked URL is never evidence
                self.evidence.fetched.add(url)
                self.state.fetches += 1
                if self.state.fetches > self.max_fetches:
                    self._violate("cap_exceeded", f"The run tried more than {self.max_fetches} page fetches.")

    def _user(self, event: dict[str, Any]) -> None:
        content = (event.get("message") or {}).get("content")
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_result" and not block.get("is_error"):
                if self.state.tool_names.get(block.get("tool_use_id", "")) == "WebSearch":
                    self.evidence.add_search_result(_text(block.get("content")))
