# ruff: noqa: E501
"""WF-049.1: the run_agent job against the real schema: claim, run events, metering, settlement, cancel, caps from
credit_action_prices, and the replay guard. The model is a scripted stub; the tool handlers are fakes."""

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import Settings
from hermi.modules.ai.metering import Usage
from hermi.modules.credits import service
from hermi.providers import ProviderError
from hermi.providers.ai import ProviderResult
from hermi_worker.agents.tools import ToolOutput
from hermi_worker.jobs import run_agent

START = 80
FINISH = {"status": "ok", "summary": "Found one note.", "sources_checked": ["example.com"], "issues": []}
NOTE = {"title": "T", "body": "B", "urls": ["https://example.com/a"], "topic": "events"}


@pytest.fixture
def settings(db_urls):
    return Settings(_env_file=None, environment="ci", auth_mode="dev", ai_provider="fake", providers_mode="fake", database_url=db_urls["app"], database_url_system=db_urls["system"])


@pytest.fixture
def engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["system"]), pool_size=4, max_overflow=2)
    yield e
    e.dispose()


def tool(name, args, tid="t1"):
    return {"type": "tool_use", "id": tid, "name": name, "input": args}


class Stub:
    name = "fake"

    def __init__(self, settings, script, *, fail=None):
        self.model, self.script, self.fail, self.calls = settings.ai_model_main, script, fail, 0

    async def single_call(self, req):
        self.calls += 1
        if self.fail:
            raise self.fail
        content, cost = self.script[min(self.calls - 1, len(self.script) - 1)]
        stop = "tool_use" if any(b["type"] == "tool_use" for b in content) else "pause_turn"
        return ProviderResult("fake", self.model, content, stop, Usage(input_tokens=100, output_tokens=20), cost)


@pytest.fixture
def world(system_conn, make_user, engine):
    uid, _ = make_user()
    system_conn.execute("INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, 'plus', 'comp')", (uid,))
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key) VALUES (%s, 'monthly', %s, %s, to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'))",
        (uid, START, START),
    )
    tid = system_conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'Lisbon', 'USD') RETURNING id", (uid,)).fetchone()[0]
    return {"uid": uid, "tid": tid, "conn": system_conn}


def queue_run(world, engine, kind="fare_hunt", params=None) -> uuid.UUID:
    """A queued run with its reservation, the way admission leaves it."""
    c = world["conn"]
    rid = c.execute(
        "INSERT INTO runs (trip_id, user_id, kind, action, params, provider) VALUES (%s, %s, %s, 'agent_run', %s::jsonb, 'fake') RETURNING id",
        (world["tid"], world["uid"], kind, json.dumps(params or {"task": {"routes": []}})),
    ).fetchone()[0]
    with Session(engine) as s:
        service.reserve(s, user_id=world["uid"], trip_id=world["tid"], action="agent_run", idempotency_key=f"{world['uid']}:agent_run:{uuid.uuid4().hex}", run_id=rid)
        s.commit()
    return rid


def handlers(world=None, on_note=None):
    saved = []

    def add_note(args, ctx):
        saved.append(args)
        if on_note:
            on_note()
        return ToolOutput({"status": "accepted"}, accepted=1)

    return {"add_note": add_note}, saved


def go(engine, settings, rid, provider, h=None, **kw):
    with Session(engine) as s:
        return run_agent.run(s, settings, str(rid), provider=provider, handlers=h, poll_seconds=0.05, **kw)


def row(conn, rid):
    return conn.execute(
        "SELECT status::text, failure_code, turns_used, searches_used, fetches_used, accepted_count, cost_usd_micros, finished_at IS NOT NULL, report FROM runs WHERE id = %s", (rid,)
    ).fetchone()


def balance(conn, uid):
    return conn.execute("SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = %s", (uid,)).fetchone()[0]


def charged(conn, rid):
    return conn.execute("SELECT charged FROM credit_ledger WHERE run_id = %s AND entry_type = 'settle'", (rid,)).fetchone()[0]


def test_saved_note_and_finish_settles_in_full_and_writes_events(world, engine, settings):
    rid = queue_run(world, engine)
    h, saved = handlers()
    p = Stub(settings, [([tool("add_note", NOTE)], 100_000), ([tool("finish_run", FINISH)], 150_000)])
    assert go(engine, settings, rid, p, h) == "done:succeeded"
    c = world["conn"]
    status, code, turns, _, _, accepted, cost, finished, report = row(c, rid)
    assert (status, code, turns, accepted, cost, finished) == ("succeeded", None, 2, 1, 250_000, True)
    assert report["report"] == FINISH and report["stop"] == "finished" and report["credits_charged"] == 40
    assert charged(c, rid) == 40 and balance(c, world["uid"]) == START - 40
    usage = c.execute("SELECT action::text, provider, cost_usd_micros, credits_reserved, credits_charged, state::text FROM ai_usage WHERE run_id = %s", (rid,)).fetchall()
    assert usage == [("agent_run", "fake", 250_000, 40, 40, "settled")]
    events = c.execute("SELECT type, summary FROM run_events WHERE run_id = %s ORDER BY seq", (rid,)).fetchall()
    types = [t for t, _ in events]
    assert types.count("tool_use") == 2 and types.count("tool_result") == 2 and types[-1] == "result"
    assert types.count("info") >= 3  # two usage events and the stop
    assert [s for t, s in events if s == "usage"] == ["usage", "usage"]
    assert c.execute("SELECT status::text, heartbeat_at IS NOT NULL, model FROM runs WHERE id = %s", (rid,)).fetchone() == ("succeeded", True, settings.ai_model_main)


def test_nothing_saved_is_failed_and_refunded_in_full(world, engine, settings):
    rid = queue_run(world, engine)
    out = go(engine, settings, rid, Stub(settings, [([tool("finish_run", FINISH)], 10_000)]), {})
    c = world["conn"]
    assert out == "done:failed" and row(c, rid)[:2] == ("failed", "nothing_saved")
    assert charged(c, rid) == 0 and balance(c, world["uid"]) == START


def test_dollar_stop_keeps_saved_work_partial_and_charges_in_full(world, engine, settings):
    rid = queue_run(world, engine)
    h, saved = handlers()
    p = Stub(settings, [([tool("add_note", NOTE)], 450_000)])
    assert go(engine, settings, rid, p, h) == "done:partial"
    c = world["conn"]
    assert row(c, rid)[:2] == ("partial", "budget_stop") and len(saved) == 2 and p.calls == 2
    assert charged(c, rid) == 40


def test_caps_come_from_credit_action_prices(world, engine, settings):
    c = world["conn"]
    old = c.execute("SELECT max_turns FROM credit_action_prices WHERE action = 'agent_run'").fetchone()[0]
    c.execute("UPDATE credit_action_prices SET max_turns = 3 WHERE action = 'agent_run'")
    try:
        rid = queue_run(world, engine)
        h, saved = handlers()
        p = Stub(settings, [([tool("add_note", NOTE)], 0)])
        assert go(engine, settings, rid, p, h) == "done:partial"
        assert row(c, rid)[:3] == ("partial", "turn_limit", 3) and p.calls == 3
    finally:
        c.execute("UPDATE credit_action_prices SET max_turns = %s WHERE action = 'agent_run'", (old,))


def test_cancel_flag_stops_between_turns_and_charges_pro_rata(world, engine, settings):
    rid = queue_run(world, engine)
    c = world["conn"]
    h, saved = handlers(on_note=lambda: c.execute("UPDATE runs SET cancel_requested = true WHERE id = %s", (rid,)))
    p = Stub(settings, [([tool("add_note", NOTE)], 1_000)])
    assert go(engine, settings, rid, p, h) == "done:cancelled"
    assert row(c, rid)[:3] == ("cancelled", "cancelled", 1) and p.calls == 1 and len(saved) == 1
    paid = charged(c, rid)
    assert 8 <= paid < 40  # pro rata by turns used, 8 credit minimum
    assert balance(c, world["uid"]) == START - paid


def test_cancel_while_queued_charges_nothing_and_never_calls_the_provider(world, engine, settings):
    rid = queue_run(world, engine)
    c = world["conn"]
    c.execute("UPDATE runs SET cancel_requested = true WHERE id = %s", (rid,))
    p = Stub(settings, [([tool("finish_run", FINISH)], 0)])
    assert go(engine, settings, rid, p, {}) == "done:cancelled"
    assert p.calls == 0 and charged(c, rid) == 0 and balance(c, world["uid"]) == START


def test_blocked_fetch_stops_the_run_and_keeps_what_was_saved(world, engine, settings):
    rid = queue_run(world, engine)
    h, saved = handlers()
    blocked = [{"type": "server_tool_use", "id": "f", "name": "web_fetch", "input": {"url": "https://www.airbnb.com/rooms/9"}}]
    p = Stub(settings, [([tool("add_note", NOTE)], 0), (blocked, 0)])
    assert go(engine, settings, rid, p, h) == "done:partial"
    c = world["conn"]
    assert row(c, rid)[:2] == ("partial", "blocked_domain") and len(saved) == 1 and charged(c, rid) == 40
    assert c.execute("SELECT count(*) FROM run_events WHERE run_id = %s AND type = 'error'", (rid,)).fetchone()[0] == 1


def test_a_run_that_is_not_queued_is_skipped_so_tools_never_replay(world, engine, settings):
    rid = queue_run(world, engine)
    world["conn"].execute("UPDATE runs SET status = 'running', started_at = now() WHERE id = %s", (rid,))
    p = Stub(settings, [([tool("finish_run", FINISH)], 0)])
    assert go(engine, settings, rid, p, {}) == "skipped:running" and p.calls == 0
    assert go(engine, settings, uuid.uuid4(), p, {}) == "missing"


def test_transient_error_before_any_response_requeues_the_run_and_raises(world, engine, settings):
    rid = queue_run(world, engine)
    p = Stub(settings, [], fail=ProviderError("busy", status_code=503))
    with pytest.raises(ProviderError):
        go(engine, settings, rid, p, {})
    c = world["conn"]
    assert row(c, rid)[0] == "queued" and balance(c, world["uid"]) == START - 40  # still reserved for the retry


def test_transient_error_on_the_last_attempt_fails_closed_and_refunds(world, engine, settings):
    rid = queue_run(world, engine)
    p = Stub(settings, [], fail=ProviderError("busy", status_code=503))
    assert go(engine, settings, rid, p, {}, attempts=run_agent.RETRIES) == "failed:provider_error"
    c = world["conn"]
    assert row(c, rid)[:2] == ("failed", "provider_error") and balance(c, world["uid"]) == START
    assert c.execute("SELECT type, summary FROM run_events WHERE run_id = %s ORDER BY seq", (rid,)).fetchall() == [
        ("result", "failed: provider_error")
    ]


def test_provider_not_configured_fails_closed_with_a_terminal_event(world, engine, settings, monkeypatch):
    from hermi.config import NotConfigured

    def refuse(*a, **kw):
        raise NotConfigured("off")

    monkeypatch.setattr(run_agent, "get_provider", refuse)
    rid = queue_run(world, engine)
    assert go(engine, settings, rid, None) == "failed:feature_disabled"
    c = world["conn"]
    assert row(c, rid)[:2] == ("failed", "feature_disabled") and balance(c, world["uid"]) == START
    assert c.execute("SELECT type, summary FROM run_events WHERE run_id = %s ORDER BY seq", (rid,)).fetchall() == [
        ("result", "failed: feature_disabled")
    ]


def test_running_row_records_the_prompt_version(world, engine, settings):
    from hermi_worker.agents.prompts import PROMPT_VERSION

    rid = queue_run(world, engine)
    h, _ = handlers()
    go(engine, settings, rid, Stub(settings, [([tool("finish_run", FINISH)], 0)]), h)
    assert world["conn"].execute("SELECT prompt_version FROM runs WHERE id = %s", (rid,)).fetchone()[0] == PROMPT_VERSION


def test_permanent_error_fails_the_run_and_refunds(world, engine, settings):
    rid = queue_run(world, engine)
    p = Stub(settings, [], fail=ProviderError("bad request", status_code=400))
    assert go(engine, settings, rid, p, {}) == "done:failed"
    c = world["conn"]
    assert row(c, rid)[:2] == ("failed", "provider_error") and balance(c, world["uid"]) == START


def test_fake_backend_runs_to_the_end_with_no_handlers(world, engine, settings):
    rid = queue_run(world, engine)
    assert go(engine, settings, rid, None) == "done:failed"  # the recorded finish_run, nothing saved
    c = world["conn"]
    assert row(c, rid)[:3] == ("failed", "nothing_saved", 1) and balance(c, world["uid"]) == START
    assert c.execute("SELECT provider FROM runs WHERE id = %s", (rid,)).fetchone()[0] == "fake"
