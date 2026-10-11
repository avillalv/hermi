"""WF-057: the pure math and report of infra/scripts/run_cost_report.py with known outputs. No database."""
# ruff: noqa: E501

import argparse
import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "infra" / "scripts" / "run_cost_report.py"
spec = importlib.util.spec_from_file_location("run_cost_report", SCRIPT)
rcr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcr)


def test_summarize_known_values():
    s = rcr.summarize([100_000 * i for i in range(1, 11)])  # $0.10 .. $1.00
    assert s["count"] == 10 and s["mean_usd"] == pytest.approx(0.55)
    assert (s["p50_usd"], s["p95_usd"], s["max_usd"]) == (0.5, 1.0, 1.0)  # nearest rank
    one = rcr.summarize([123_456])
    assert one["count"] == 1 and one["p95_usd"] == one["mean_usd"] == 0.123456
    assert rcr.summarize([])["count"] == 0 and rcr.summarize([])["p95_usd"] == 0.0


def test_p95_of_fifty_runs_is_the_48th_value():
    costs = [10_000 * i for i in range(1, 51)]  # $0.01 .. $0.50
    assert rcr.summarize(costs)["p95_usd"] == 0.48


def test_gate_is_strictly_under_and_minimums_are_checked():
    ok = rcr.summarize([500_000] * 50)
    assert rcr.evaluate(ok, 10, gate_usd=0.8, min_runs=50, min_routes=10) == []
    hot = rcr.summarize([400_000] * 40 + [800_000] * 10)
    assert "p95 $0.8000 is not under $0.80" in rcr.evaluate(hot, 10, gate_usd=0.8)
    assert rcr.evaluate(ok, 3, gate_usd=0.8, min_routes=10) == ["3 routes, need 10"]
    assert rcr.evaluate(ok, 10, gate_usd=0.8, min_runs=60) == ["50 runs, need 60"]


def test_route_ids_are_distinct_across_fare_hunts():
    assert rcr.route_ids([["a", "b"], ["b", "c"], None, "x"]) == {"a", "b", "c"}


def test_window_defaults_and_order():
    now = datetime(2027, 3, 15, tzinfo=UTC)
    s, e = rcr.window(None, None, None, now)
    assert (e - s).days == 14 and e == now
    s, e = rcr.window(None, "2027-03-01", "2027-03-10")
    assert (s.day, e.day) == (1, 10)
    with pytest.raises(ValueError):
        rcr.window(None, "2027-03-10", "2027-03-01")


def test_report_counts_routes_only_for_fare_hunts_and_flags_mix():
    rows = [
        {"cost_usd_micros": 300_000, "kind": "fare_hunt", "provider": "anthropic_api", "route_ids": ["r1", "r2"], "usage_micros": 300_000},
        {"cost_usd_micros": 100_000, "kind": "deep_research", "provider": "claude_cli", "route_ids": ["r9"], "usage_micros": 90_000},
    ]
    args = argparse.Namespace(gate_usd=0.8, min_runs=0, min_routes=0, kind=None)
    now = datetime(2027, 3, 15, tzinfo=UTC)
    rep = rcr.build_report(rows, now, now, args)
    assert rep["count"] == 2 and rep["routes"] == 2 and rep["usage_mismatch_runs"] == 1
    assert rep["passed"] and not rep["certifiable"] and "provisional" in rcr.render(rep)


def test_main_without_a_database_exits_2_and_never_reads_env_files(capsys):
    assert rcr.main([], env={}) == 2
    assert "no database" in capsys.readouterr().err
