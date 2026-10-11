#!/usr/bin/env python3
# ruff: noqa: E501
"""Real cost per agent run over a window (WF-057; 06 section 10 "Cost and latency"; 10 section 1.5).

Reads `runs.cost_usd_micros` (equal to the run's `ai_usage.cost_usd_micros` sum, 06 section 10 gate 3) for finished runs
and prints count, mean, p50, p95 and max in USD, the distinct routes the fare hunts covered, and the gate result.
Read only: the connection is a read-only transaction. It never reads .env; pass the URL or export it.

  uv run --no-sync python infra/scripts/run_cost_report.py --days 14 --min-runs 50 --min-routes 10
  uv run --no-sync python infra/scripts/run_cost_report.py --since 2027-03-01 --until 2027-03-15 --provider anthropic_api

Exit 0 when p95 is under --gate-usd (default 0.80, the agent run gate) and the optional minimums are met, 1 when a gate
fails, 2 on bad input or no database, 3 when the window holds no runs.

shortcut: numbers from `--provider claude_cli` are notional (a subscription, not metered) and provisional; only
`anthropic_api` runs certify the gate (06 section 10). The report says so and does not hide the mix.
"""

import argparse
import json
import math
import os
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

AGENT_KINDS = ("fare_hunt", "deep_research")
DEFAULT_GATE_USD = 0.80
FINISHED = ("succeeded", "partial", "failed", "timed_out", "cancelled", "interrupted")

SQL = """
SELECT r.cost_usd_micros,
       r.kind::text,
       r.provider,
       r.params -> 'route_ids' AS route_ids,
       (SELECT sum(u.cost_usd_micros) FROM ai_usage u WHERE u.run_id = r.id) AS usage_micros
  FROM runs r
 WHERE r.finished_at >= %(since)s AND r.finished_at < %(until)s
   AND r.status::text = ANY(%(statuses)s)
   AND NOT r.served_from_cache
   AND r.kind::text = ANY(%(kinds)s)
   AND (%(provider)s::text IS NULL OR r.provider = %(provider)s)
"""


def percentile(sorted_values: Sequence[float], q: float) -> float:
    """Nearest rank on an ascending list: the smallest value with at least q of the sample at or below it."""
    if not sorted_values:
        return 0.0
    return sorted_values[max(0, math.ceil(q * len(sorted_values)) - 1)]


def summarize(costs_micros: Sequence[int]) -> dict[str, Any]:
    """Count, mean, p50, p95 and max of per-run cost, in USD (micro-dollars divided by one million)."""
    usd = sorted(c / 1_000_000 for c in costs_micros)
    n = len(usd)
    return {
        "count": n,
        "mean_usd": sum(usd) / n if n else 0.0,
        "p50_usd": percentile(usd, 0.50),
        "p95_usd": percentile(usd, 0.95),
        "max_usd": usd[-1] if n else 0.0,
    }


def evaluate(summary: Mapping[str, Any], routes: int, *, gate_usd: float, min_runs: int = 0, min_routes: int = 0) -> list[str]:
    """The reasons the measurement fails, empty when it passes. p95 must be under the gate, as 06 section 10 says."""
    out = []
    if summary["count"] and summary["p95_usd"] >= gate_usd:
        out.append(f"p95 ${summary['p95_usd']:.4f} is not under ${gate_usd:.2f}")
    if summary["count"] < min_runs:
        out.append(f"{summary['count']} runs, need {min_runs}")
    if routes < min_routes:
        out.append(f"{routes} routes, need {min_routes}")
    return out


def route_ids(values: Sequence[Any]) -> set[str]:
    """Distinct route ids from the `params.route_ids` of fare hunt runs (a list, or null)."""
    return {str(r) for v in values if isinstance(v, list) for r in v}


def window(days: int | None, since: str | None, until: str | None, now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(UTC)
    end = _when(until) if until else now
    start = _when(since) if since else end - timedelta(days=days if days is not None else 14)
    if start >= end:
        raise ValueError("--since must be before --until")
    return start, end


def _when(s: str) -> datetime:
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def connect(url: str) -> Any:
    """A psycopg connection whose transaction is read only: any write is refused by the server."""
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://", 1), row_factory=dict_row)
    conn.read_only = True
    return conn


def fetch(url: str, start: datetime, end: datetime, kinds: Sequence[str], provider: str | None) -> list[dict[str, Any]]:
    with connect(url) as conn:
        cur = conn.execute(SQL, {"since": start, "until": end, "statuses": list(FINISHED), "kinds": list(kinds), "provider": provider})
        return list(cur.fetchall())


def build_report(rows: Sequence[Mapping[str, Any]], start: datetime, end: datetime, args: argparse.Namespace) -> dict[str, Any]:
    summary = summarize([int(r["cost_usd_micros"]) for r in rows])
    routes = route_ids([r["route_ids"] for r in rows if r["kind"] == "fare_hunt"])
    providers = sorted({r["provider"] for r in rows})
    mismatched = sum(1 for r in rows if r["usage_micros"] is not None and int(r["usage_micros"]) != int(r["cost_usd_micros"]))
    failures = evaluate(summary, len(routes), gate_usd=args.gate_usd, min_runs=args.min_runs, min_routes=args.min_routes)
    return {
        "since": start.isoformat(), "until": end.isoformat(), "kinds": list(args.kind or AGENT_KINDS), "providers": providers,
        **summary, "routes": len(routes), "usage_mismatch_runs": mismatched, "gate_usd": args.gate_usd,
        "certifiable": providers == ["anthropic_api"], "failures": failures, "passed": bool(rows) and not failures,
    }  # fmt: skip


def render(rep: Mapping[str, Any]) -> str:
    lines = [
        f"runs {rep['since'][:10]} to {rep['until'][:10]}, kinds {', '.join(rep['kinds'])}, providers {', '.join(rep['providers']) or 'none'}",
        f"count {rep['count']}  routes {rep['routes']}",
        f"mean ${rep['mean_usd']:.4f}  p50 ${rep['p50_usd']:.4f}  p95 ${rep['p95_usd']:.4f}  max ${rep['max_usd']:.4f}",
        f"gate: p95 under ${rep['gate_usd']:.2f} -> {'PASS' if rep['passed'] else 'FAIL'}",
    ]
    if rep["usage_mismatch_runs"]:
        lines.append(f"warning: {rep['usage_mismatch_runs']} runs where runs.cost_usd_micros differs from the ai_usage sum")
    if not rep["certifiable"] and rep["providers"]:
        lines.append("provisional: the window holds runs not served by anthropic_api; only anthropic_api numbers certify the gate")
    lines += [f"fail: {f}" for f in rep["failures"]]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    ap = argparse.ArgumentParser(description="Real cost per agent run over a window (read only).")
    ap.add_argument("--days", type=int, help="the last N days (default 14)")
    ap.add_argument("--since", help="ISO date or time, UTC when no zone")
    ap.add_argument("--until", help="ISO date or time, default now")
    ap.add_argument("--kind", action="append", help=f"run kind, repeatable (default {' and '.join(AGENT_KINDS)})")
    ap.add_argument("--provider", choices=("anthropic_api", "claude_cli", "fake"), help="only runs served by this backend")
    ap.add_argument("--database-url", help="default: DATABASE_URL_SYSTEM, then DATABASE_URL, from the environment")
    ap.add_argument("--gate-usd", type=float, default=DEFAULT_GATE_USD)
    ap.add_argument("--min-runs", type=int, default=0, help="fail below this many runs (the staging measurement uses 50)")
    ap.add_argument("--min-routes", type=int, default=0, help="fail below this many distinct fare hunt routes (10)")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    a = ap.parse_args(argv)
    url = a.database_url or env.get("DATABASE_URL_SYSTEM") or env.get("DATABASE_URL")
    if not url:
        print("run_cost_report: no database. Pass --database-url or set DATABASE_URL_SYSTEM.", file=sys.stderr)
        return 2
    try:
        start, end = window(a.days, a.since, a.until)
        rows = fetch(url, start, end, a.kind or AGENT_KINDS, a.provider)
    except ValueError as e:
        print(f"run_cost_report: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # a connection or SQL error: say what, never print the URL
        print(f"run_cost_report: could not read runs: {type(e).__name__}", file=sys.stderr)
        return 2
    rep = build_report(rows, start, end, a)
    print(json.dumps(rep, indent=2) if a.json else render(rep))
    if not rows:
        return 3
    return 0 if rep["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
