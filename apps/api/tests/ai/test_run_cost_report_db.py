# ruff: noqa: E501
"""WF-057: infra/scripts/run_cost_report.py reads real runs and ai_usage rows, and its connection cannot write."""

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest

SCRIPT = Path(__file__).resolve().parents[4] / "infra" / "scripts" / "run_cost_report.py"
spec = importlib.util.spec_from_file_location("run_cost_report", SCRIPT)
rcr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcr)


def test_fetch_reads_finished_runs_with_usage_and_the_connection_is_read_only(system_conn, make_user, db_urls):
    uid, _ = make_user()
    tid = system_conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'Lisbon', 'USD') RETURNING id", (uid,)).fetchone()[0]
    ids = []
    for kind, cost, routes in (("fare_hunt", 300_000, ["r1", "r2"]), ("deep_research", 120_000, [])):
        rid = system_conn.execute(
            "INSERT INTO runs (trip_id, user_id, kind, action, status, params, provider, started_at, finished_at, cost_usd_micros) "
            "VALUES (%s, %s, %s, 'agent_run', 'succeeded', %s::jsonb, 'anthropic_api', now(), now(), %s) RETURNING id",
            (tid, uid, kind, json.dumps({"route_ids": routes}), cost),
        ).fetchone()[0]
        system_conn.execute(
            "INSERT INTO ai_usage (user_id, trip_id, run_id, action, provider, cost_usd_micros, idempotency_key) VALUES (%s, %s, %s, 'agent_run', 'anthropic_api', %s, %s)",
            (uid, tid, rid, cost, f"{uid}:cost-report:{rid}"),
        )
        ids.append(rid)
    now = datetime.now(UTC)
    rows = rcr.fetch(db_urls["system"], now - timedelta(hours=1), now + timedelta(hours=1), rcr.AGENT_KINDS, "anthropic_api")
    assert sorted(int(r["cost_usd_micros"]) for r in rows) == [120_000, 300_000]
    assert all(int(r["usage_micros"]) == int(r["cost_usd_micros"]) for r in rows)
    assert rcr.route_ids([r["route_ids"] for r in rows if r["kind"] == "fare_hunt"]) == {"r1", "r2"}
    assert rcr.fetch(db_urls["system"], now - timedelta(hours=1), now + timedelta(hours=1), ["fare_hunt"], "claude_cli") == []

    with rcr.connect(db_urls["system"]) as c, pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        c.execute("UPDATE runs SET cost_usd_micros = 0 WHERE id = %s", (ids[0],))
