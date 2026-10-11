# ruff: noqa: E501
"""Eval harness: saved pages in, a scripted (fake) or real model, the real agent loop, and ingest style evidence rules.

One path for every provider (06 section 10): `python -m tests.evals --provider fake|anthropic_api|claude_cli`.
`fake` replays each case's scripted model answer, reads no env file and makes no network call. A live provider needs
`EVALS_LIVE=1` and `--max-usd`, and the run stops when its spend reaches the cap. Only `anthropic_api` can certify.

shortcut: the fixtures are seed sets (a handful of cases per suite), not the 150/50/40 page sets of the spec, and the
research judge is a substring check, not a Haiku call. Ceiling: gate numbers on seeds prove the harness and the
evidence code, not model accuracy. Upgrade trigger: the owner labels the full sets and adds them to fixtures/.
"""

import argparse
import asyncio
import json
import math
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from hermi.modules.ai.ingest import normalize_url, price_grounded, price_in_bounds, source_problem
from hermi.modules.ai.metering import Usage
from hermi.providers.ai.base import ProviderResult
from hermi_worker.agents.loop import AgentLoop, Hooks, RunOutcome
from hermi_worker.agents.prompts import SYSTEM
from hermi_worker.agents.spec import AgentSpec
from hermi_worker.agents.tools import ToolContext, ToolOutput

from .suites import SUITES, score

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_MODEL = "claude-test-main"
PROVIDERS = ("fake", "anthropic_api", "claude_cli")
AGENT_RUN_GATE_USD = 0.80
RESEARCH_GATE_USD = 0.16  # research p95 per run (06 section 10)
COST_GROUP = {"research_grounding": "research", "refusals": "research"}  # every other suite is an agent (fare) run
COST_GATES = {"agent": AGENT_RUN_GATE_USD, "research": RESEARCH_GATE_USD}
# Full set sizes (06 section 10). A suite below its size is a seed set and cannot certify. rule_compliance and
# evidence_labels have no count in the spec: their fixture marks itself with "full_set": true on a case.
FULL_SET_SIZES = {"fare_extraction": 150, "abstention": 50, "research_grounding": 40, "injection": 30, "refusals": 40}


def is_seed_set(suite: str, cases: list[dict[str, Any]]) -> bool:
    if suite in FULL_SET_SIZES:
        return len(cases) < FULL_SET_SIZES[suite]
    return not any(c.get("full_set") for c in cases)
DEFAULT_CONTEXT: dict[str, Any] = {
    "routes": {"R1": {"origins": ["JFK"], "dests": ["LIS"], "adults": 2}},
    "window": ["2027-03-01", "2027-03-31"],
    "rates": {"USD": 1, "EUR": 0.92, "GBP": 0.79, "JPY": 150},  # units of the currency per USD
    "today": "2027-02-01",
}


def percentile(values: list[float], q: float) -> float:
    """Nearest rank: the smallest value with at least q of the sample at or below it. 0 for no values."""
    if not values:
        return 0.0
    s = sorted(values)
    return s[max(0, math.ceil(q * len(s)) - 1)]


# --- ingest style checks (pure) -------------------------------------------------------------------------------------


def check_quote(q: dict[str, Any], ctx: dict[str, Any], pages: dict[str, str]) -> list[str]:
    """Reason codes why a quote is refused, empty when it passes. `pages` maps normalized fetched URLs to their text."""
    errs: list[str] = []
    url = str(q.get("source_url", ""))
    if source_problem(url):
        errs.append("source")
    elif normalize_url(url) not in pages:
        errs.append("not_opened")
    route = ctx["routes"].get(q.get("route_ref"))
    if route is None:
        errs.append("route")
    elif q.get("passengers") not in (1, route["adults"]):
        errs.append("passengers")
    try:
        d = date.fromisoformat(str(q.get("depart_date")))
        if not date.fromisoformat(ctx["window"][0]) <= d <= date.fromisoformat(ctx["window"][1]):
            errs.append("window")
    except ValueError:
        errs.append("date")
    cur = str(q.get("currency", ""))
    rate = ctx["rates"].get(cur)
    if rate is None:
        errs.append("currency")
    try:
        price = Decimal(str(q.get("price_total")))
        if normalize_url(url) in pages and not price_grounded(pages[normalize_url(url)], price):
            errs.append("ungrounded")
        elif rate is not None and not price_in_bounds(price, int(q.get("passengers") or 0), Decimal(str(rate))):
            errs.append("bounds")
    except (InvalidOperation, ValueError):
        errs.append("price")
    return errs


# --- one case -----------------------------------------------------------------------------------------------------------


@dataclass
class CaseResult:
    id: str
    suite: str
    expect: dict[str, Any]
    case: dict[str, Any]
    stop: str = ""
    status: str = ""
    failure_code: str | None = None
    submitted: int = 0  # quote items the model sent, accepted or not
    notes_submitted: int = 0
    reasons: list[list[str]] = field(default_factory=list)  # one list per refused item
    saved: list[dict[str, Any]] = field(default_factory=list)  # accepted items: kind, source_url, checked_at, values
    altered_retry: bool = False
    cost_micros: int = 0
    turns: int = 0
    evidence_urls: set[str] = field(default_factory=set)

    @property
    def accepted_quotes(self) -> list[dict[str, Any]]:
        return [s for s in self.saved if s["kind"] == "quote"]

    @property
    def accepted_notes(self) -> list[dict[str, Any]]:
        return [s for s in self.saved if s["kind"] == "note"]


def _tool(n: str, args: dict[str, Any], tid: str) -> dict[str, Any]:
    return {"type": "tool_use", "id": tid, "name": n, "input": args}


def _quote_input(q: dict[str, Any]) -> dict[str, Any]:
    return {
        "route_ref": q.get("route", "R1"), "origin": q.get("origin", "JFK"), "destination": q.get("dest", "LIS"),
        "depart_date": q.get("dep", "2027-03-10"), "return_date": q.get("ret", "2027-03-17"), "price_total": q["price"],
        "currency": q.get("cur", "USD"), "passengers": q.get("pax", 1), "airlines": q.get("airlines", []),
        "stops_outbound": None, "stops_return": None, "duration_outbound_min": None, "source_url": q["url"],
        "seen_on": None, "notes": None,
    }  # fmt: skip


def script_from_case(case: dict[str, Any]) -> list[ProviderResult]:
    """The scripted model: each round is one response (optional page fetch, quotes, notes), then finish_run."""
    m = case["model"]
    cost = int(m.get("cost_micros", 0))

    def resp(content: list[dict[str, Any]], stop: str) -> ProviderResult:
        return ProviderResult(provider="fake", model=FAKE_MODEL, content=content, stop_reason=stop, usage=Usage(input_tokens=10, output_tokens=5), cost_usd_micros=cost)  # fmt: skip

    if m.get("refuse"):
        return [resp([{"type": "text", "text": "I cannot help with that."}], "refusal")]
    out: list[ProviderResult] = []
    for i, rnd in enumerate(m.get("rounds", [])):
        blocks: list[dict[str, Any]] = []
        if f := rnd.get("fetch"):
            blocks += [
                {"type": "server_tool_use", "id": f"f{i}", "name": "web_fetch", "input": {"url": f}},
                {"type": "web_fetch_tool_result", "tool_use_id": f"f{i}", "content": {"type": "web_fetch_result", "url": f, "content": {"type": "document", "source": {"type": "text", "data": rnd.get("text", "")}}}},
            ]  # fmt: skip
        if rnd.get("quotes"):
            blocks.append(_tool("submit_flight_quotes", {"quotes": [_quote_input(q) for q in rnd["quotes"]]}, f"q{i}"))
        for j, n in enumerate(rnd.get("notes", [])):
            blocks.append(_tool("add_note", {"topic": "other", **n}, f"n{i}{j}"))
        out.append(resp(blocks, "tool_use" if any(b["type"] == "tool_use" for b in blocks) else "pause_turn"))
    finish = {"status": "ok", "summary": "Done.", "sources_checked": [], "issues": []}
    out.append(resp([_tool("finish_run", finish, "fin")], "tool_use"))
    return out


class ScriptedProvider:
    """The fake Messages client: replays a case's scripted responses, the last one repeating. No network."""

    name = "fake"

    def __init__(self, script: list[ProviderResult]) -> None:
        self.script, self.calls = script, 0

    async def single_call(self, req: Any) -> ProviderResult:
        r = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        return r


class _NoSession:
    """check_note reads the affiliate host list through a session; evals have no partner programs."""

    def execute(self, *_: Any, **__: Any) -> list[Any]:
        return []


def task_text(case: dict[str, Any]) -> str:
    pages = "\n".join(f'<page url="{p["url"]}">\n{p["text"]}\n</page>' for p in case.get("pages", []))
    return f"{case['task']}\n\nSaved pages you may use (they are the only pages; cite their url):\n{pages}"


async def run_case(case: dict[str, Any], suite: str, provider: Any, model: str, *, stop_micro: int, live: bool) -> CaseResult:
    from hermi.modules.ai.ingest import check_note  # lazy: keeps `--help` fast

    ctx = {**DEFAULT_CONTEXT, **case.get("context", {})}
    res = CaseResult(case["id"], suite, case.get("expect", {}), case)
    pages = {normalize_url(p["url"]): p["text"] for p in case.get("pages", [])}
    seen: dict[tuple[str, str], tuple[str, str]] = {}  # (route, depart) -> (price, currency) of an earlier refusal

    def submit(args: dict[str, Any], tctx: ToolContext) -> ToolOutput:
        known = {**pages, **{normalize_url(u): t for u, t in tctx.evidence.fetched.items()}}
        results, acc, rej = [], 0, 0
        for i, q in enumerate(args["quotes"]):
            res.submitted += 1
            key = (str(q["route_ref"]), str(q["depart_date"]))
            errs = check_quote(q, ctx, known)
            if key in seen and seen[key] != (q["price_total"], q["currency"]):
                res.altered_retry = True
                errs = [*errs, "altered_retry"]
            if errs:
                res.reasons.append(errs)
                seen.setdefault(key, (q["price_total"], q["currency"]))
                rej += 1
                results.append({"index": i, "status": "rejected", "errors": errs})
            else:
                acc += 1
                res.saved.append({"kind": "quote", "source_url": q["source_url"], "checked_at": ctx["today"], "price": q["price_total"], "currency": q["currency"]})
                results.append({"index": i, "status": "accepted"})
        return ToolOutput({"results": results}, accepted=acc, rejected=rej)

    def add_note(args: dict[str, Any], tctx: ToolContext) -> ToolOutput:
        res.notes_submitted += 1
        errs, title, body, urls = check_note(_NoSession(), args, tctx.evidence)  # type: ignore[arg-type]
        if errs:
            res.reasons.append(errs)
            return ToolOutput({"status": "rejected", "errors": errs}, is_error=True, rejected=1)
        res.saved.append({"kind": "note", "source_url": urls[0], "urls": urls, "checked_at": ctx["today"], "title": title, "body": body})
        return ToolOutput({"status": "accepted"}, accepted=1)

    spec = AgentSpec(
        model=model, system=SYSTEM, allowed_models=frozenset({model}), stop_micro=stop_micro,
        max_searches=0 if live else 10, max_fetches=0 if live else 10, max_turns=8,
    )  # fmt: skip
    loop = AgentLoop(provider, spec, {"submit_flight_quotes": submit, "add_note": add_note}, Hooks(poll_seconds=0.05))
    for p in case.get("pages", []):  # the saved pages count as opened pages in both modes
        loop.evidence.fetched[p["url"]] = p["text"]
    out: RunOutcome = await loop.run(task_text(case))
    res.stop, res.status, res.failure_code = out.stop, out.status, out.failure_code
    res.cost_micros, res.turns = out.cost_usd_micros, out.turns
    res.evidence_urls = {*out.evidence.found, *out.evidence.fetched}
    return res


# --- guards, suites and the report -----------------------------------------------------------------------------------


def guard(provider: str, max_usd: float | None, env: Mapping[str, str]) -> str | None:
    """A reason to refuse before any call, or None. Only `fake` runs without the live switch and a spend cap."""
    if provider not in PROVIDERS:
        return f"unknown provider {provider!r}; use one of {', '.join(PROVIDERS)}"
    if provider == "fake":
        return None
    if env.get("EVALS_LIVE") != "1":
        return f"--provider {provider} is a live run: set EVALS_LIVE=1 to allow it. No call was made."
    if max_usd is None or max_usd <= 0:
        return f"--provider {provider} needs --max-usd greater than 0 (use a low-limit key). No call was made."
    return None


def load_cases(suite: str, fixtures: Path = FIXTURES) -> list[dict[str, Any]]:
    path = fixtures / f"{suite}.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _live_provider(name: str) -> tuple[Any, str]:
    os.environ["AI_PROVIDER"] = name
    from hermi.config import load_settings
    from hermi.providers.ai.factory import get_provider

    s = load_settings(bind_host="127.0.0.1")
    return get_provider(s, bind_host="127.0.0.1"), s.ai_model_main


def run_all(
    suites: list[str], *, provider: str, max_usd: float | None = None, fixtures: Path = FIXTURES,
    factory: Callable[[str], tuple[Any, str]] | None = None,
) -> dict[str, Any]:  # fmt: skip
    """Run the suites and build the report. `factory` is for tests: it replaces the real provider of a live run."""
    live = provider != "fake"
    cap = round((max_usd or 0) * 1_000_000)
    spent, stopped = 0, None
    real, model = (None, FAKE_MODEL)
    if live:
        real, model = (factory or _live_provider)(provider)
    report_suites = []
    run_costs: dict[str, list[int]] = {"agent": [], "research": []}
    for name in suites:
        results: list[CaseResult] = []
        cases = load_cases(name, fixtures)
        for c in cases:
            if live and spent >= cap:
                stopped = "max_usd"
                break
            prov = real if live else ScriptedProvider(script_from_case(c))
            stop_micro = min(800_000, cap - spent) if live else 800_000
            r = asyncio.run(run_case(c, name, prov, model, stop_micro=stop_micro, live=live))
            spent += r.cost_micros
            run_costs[COST_GROUP.get(name, "agent")].append(r.cost_micros)
            results.append(r)
        metrics = score(name, results)
        report_suites.append({
            "name": name, "cases": len(cases), "completed": len(results), "seed": is_seed_set(name, cases),
            "cost_usd": sum(r.cost_micros for r in results) / 1e6, "metrics": metrics,
            "passed": all(m["passed"] for m in metrics) and len(results) == len(cases),
        })  # fmt: skip
    cost: dict[str, Any] = {}
    for group, micros in run_costs.items():
        usd = [m / 1e6 for m in micros]
        cost[group] = {
            "runs": len(usd), "mean_usd": sum(usd) / len(usd) if usd else 0.0, "p50_usd": percentile(usd, 0.5),
            "p95_usd": percentile(usd, 0.95), "gate_usd": COST_GATES[group],
            # fake spends nothing, so there is no gate to read; a live group with no runs has nothing to fail
            "passed": (percentile(usd, 0.95) < COST_GATES[group]) if live else None,
        }  # fmt: skip
    seed_sets = any(s["seed"] for s in report_suites)
    passed = all(s["passed"] for s in report_suites) and all(c["passed"] is not False for c in cost.values()) and stopped is None
    return {
        "provider": provider,
        "certified": provider == "anthropic_api" and passed and not seed_sets,
        "provisional": provider == "claude_cli",
        "seed_sets": seed_sets,  # any suite below its full set size cannot certify
        "stopped": stopped, "max_usd": max_usd, "spent_usd": spent / 1e6,
        "suites": report_suites, "cost": cost, "passed": passed,
    }  # fmt: skip


def render(report: dict[str, Any]) -> str:
    if report["certified"]:
        tag = "certified"
    elif report["provisional"]:
        tag = "provisional (claude_cli)"
    elif report["seed_sets"]:
        tag = "not certified (seed sets)"
    else:
        tag = "not certified"
    lines = [f"evals: provider={report['provider']} {tag} spent=${report['spent_usd']:.4f}" + (f" stopped={report['stopped']}" if report["stopped"] else "")]
    for s in report["suites"]:
        lines.append(f"{'PASS' if s['passed'] else 'FAIL'} {s['name']} ({s['completed']}/{s['cases']} cases, ${s['cost_usd']:.4f})")
        for m in s["metrics"]:
            lines.append(f"       {m['name']}: {m['value']:.3f} (gate {m['op']} {m['gate']}) n={m['n']} {'ok' if m['passed'] else 'FAILED'}")
    for group, c in report["cost"].items():
        gate = "no spend, gate not read" if c["passed"] is None else ("ok" if c["passed"] else "FAILED")
        lines.append(f"cost {group}: runs={c['runs']} mean=${c['mean_usd']:.4f} p50=${c['p50_usd']:.4f} p95=${c['p95_usd']:.4f} (gate < ${c['gate_usd']:.2f}) {gate}")
    if report["seed_sets"]:
        lines.append("seed sets: gate numbers on seeds prove the harness, not model accuracy")
    lines.append(f"RESULT: {'PASS' if report['passed'] else 'FAIL'}")
    return "\n".join(lines)


def main(argv: list[str], env: Mapping[str, str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="npm run evals", description="Agent and research evals (06 section 10).", allow_abbrev=False)
    ap.add_argument("--provider", default="fake", choices=PROVIDERS)
    ap.add_argument("--max-usd", type=float, default=None, help="live runs only: stop when spend reaches this")
    ap.add_argument("--suite", action="append", choices=sorted(SUITES), help="repeatable; default all")
    ap.add_argument("--out", help="write the JSON report here")
    a = ap.parse_args(argv)
    if reason := guard(a.provider, a.max_usd, os.environ if env is None else env):
        print(f"evals refused: {reason}", file=sys.stderr)
        return 2
    report = run_all(a.suite or sorted(SUITES), provider=a.provider, max_usd=a.max_usd)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(render(report))
    return 0 if report["passed"] else 1
