# ruff: noqa: E501
"""WF-053.1: the agent runs API over the real schema, the real roles and the fake provider.

Rows are arranged with the system login. Routes run as the app login (RLS applies). The worker side is the real `run_agent`
job driven in process with a scripted provider, so start, stream, cancel, settle and the taster are tested end to end.
No network and no real model."""

import json
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import Settings
from hermi.main import create_app
from hermi.modules.admin.flags import FlagRuntime, Snapshot, Switch
from hermi.modules.ai import router as ai_router
from hermi.modules.ai.metering import Usage
from hermi.providers.ai import ProviderResult
from hermi.security.jwt import mint_dev_token
from hermi_worker.jobs import run_agent

URL = "https://example.com/lisbon-events"
NOTE = {
    "title": "Marathon closes the riverfront",
    "body": "The marathon closes the riverfront road on 9 May.",
    "urls": [URL],
    "topic": "events",
}
FINISH = {
    "status": "ok",
    "summary": "Found one note.",
    "sources_checked": ["example.com"],
    "issues": [],
}


def engaged(*keys):
    return FlagRuntime(lambda: Snapshot(switches={k: Switch(k, True) for k in keys}), ttl=0)


def tool(name, args, tid="t1"):
    return {"type": "tool_use", "id": tid, "name": name, "input": args}


SEARCH = [
    {
        "type": "server_tool_use",
        "id": "s1",
        "name": "web_search",
        "input": {"query": "lisbon events"},
    },
    {
        "type": "web_search_tool_result",
        "tool_use_id": "s1",
        "content": [{"type": "web_search_result", "url": URL, "title": "Events"}],
    },
]


class Stub:
    """A scripted model: one (content, cost) per turn, the last repeated. `on_call(n)` runs before turn n answers."""

    name = "fake"

    def __init__(self, settings, script, on_call=None):
        self.model, self.script, self.on_call, self.calls = (
            settings.ai_model_main,
            script,
            on_call,
            0,
        )

    async def single_call(self, req):
        self.calls += 1
        if self.on_call:
            self.on_call(self.calls)
        content, cost = self.script[min(self.calls - 1, len(self.script) - 1)]
        stop = "tool_use" if any(b["type"] == "tool_use" for b in content) else "pause_turn"
        return ProviderResult(
            "fake", self.model, content, stop, Usage(input_tokens=100, output_tokens=20), cost
        )


SAVE_THEN_FINISH = [
    (SEARCH + [tool("add_note", NOTE)], 100_000),
    ([tool("finish_run", FINISH)], 100_000),
]
FINISH_ONLY = [([tool("finish_run", FINISH)], 10_000)]


@pytest.fixture
def settings(db_urls):
    return Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        ai_provider="fake",
        providers_mode="fake",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
    )


@pytest.fixture(autouse=True)
def _dispose_system_engines():
    yield
    db.dispose_system_engines()


@pytest.fixture
def client(db_urls, settings, monkeypatch):
    monkeypatch.setattr(ai_router, "POLL_SECONDS", 0.05)
    with TestClient(create_app(settings), raise_server_exceptions=False) as c:
        c.settings = settings
        yield c


@pytest.fixture
def worker_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["system"]), pool_size=4, max_overflow=2)
    yield e
    e.dispose()


def person(client, conn, *, plus=False, credits=60, consent=True):
    """A signed-in user (bootstrapped through the API), optionally Plus with a monthly grant, with a trip. -> (headers, uid, trip_id)."""
    sub = uuid.uuid4().hex
    h = {
        "Authorization": "Bearer "
        + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")
    }
    r = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "USD"}, headers=h
    )
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    if consent:
        conn.execute(
            "INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', '1', true)",
            (uid,),
        )
    if plus:
        conn.execute(
            "UPDATE entitlements SET tier_code = 'plus', source = 'comp', valid_until = NULL WHERE user_id = %s",
            (uid,),
        )
        conn.execute(
            "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key) VALUES (%s, 'monthly', %s, %s, to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'))",
            (uid, credits, credits),
        )
    tid = conn.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency, start_date, end_date) VALUES (%s, 'Lisbon', 'USD', '2027-05-01', '2027-05-05') RETURNING id",
        (uid,),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO trip_destinations (trip_id, position, name, country, lat, lon) VALUES (%s, 0, 'Lisbon', 'Portugal', 38.7, -9.1)",
        (tid,),
    )
    return h, uid, str(tid)


def join(client, conn, tid, role="editor"):
    sub = uuid.uuid4().hex
    h = {
        "Authorization": "Bearer "
        + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")
    }
    uid = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "USD"}, headers=h
    ).json()["id"]
    conn.execute(
        "INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (tid, uid, role)
    )
    return h, uid


def start(client, h, tid, kind="deep_research", key=None, **body):
    return client.post(
        f"/v1/trips/{tid}/agent-runs",
        json={"kind": kind, **body},
        headers={**h, "Idempotency-Key": key or uuid.uuid4().hex},
    )


def work(engine, settings, rid, script, handlers=None, on_call=None):
    """The worker job for one run, in process, on a scripted model."""
    with Session(engine) as s:
        return run_agent.run(
            s,
            settings,
            str(rid),
            provider=Stub(settings, script, on_call),
            handlers=handlers,
            build_task=lambda _s, _r: "task",
            poll_seconds=0.05,
        )


def balance(conn, uid):
    return conn.execute(
        "SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = %s", (uid,)
    ).fetchone()[0]


def frames(text):
    """Parse an SSE body into (id, event, data) and the comment lines."""
    out, comments = [], []
    for block in text.strip().split("\n\n"):
        if block.startswith(":"):
            comments.append(block)
            continue
        f = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((int(f["id"]), f["event"], json.loads(f["data"])))
    return out, comments


# --- start, preview and the one-active rule ----------------------------------------------------------------------------


def test_start_reserves_enqueues_and_returns_the_run(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    r = start(client, h, tid, topic="events and closures", instructions="Skip anything over $100")
    assert r.status_code == 202, r.text
    body = r.json()
    assert (
        body["status"] == "queued"
        and body["kind"] == "deep_research"
        and body["is_taster"] is False
    )
    assert (
        r.headers["location"] == f"/v1/agent-runs/{body['id']}"
        and body["events_url"] == f"/v1/agent-runs/{body['id']}/stream"
    )
    assert (
        body["credits"]["reserved"] == 40
        and body["credits"]["charged"] is None
        and body["started_by"]["id"] == uid
    )
    assert balance(system_conn, uid) == 20
    queued = system_conn.execute(
        "SELECT count(*) FROM procrastinate_jobs WHERE task_name = 'run_agent' AND args->>'run_id' = %s",
        (body["id"],),
    ).fetchone()[0]
    assert queued == 1
    row = system_conn.execute(
        "SELECT params, provider, action::text FROM runs WHERE id = %s", (body["id"],)
    ).fetchone()
    assert row == (
        {"topic": "events and closures", "instructions": "Skip anything over $100"},
        "fake",
        "agent_run",
    )


def test_a_second_start_while_one_is_active_is_a_clear_conflict(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True, credits=100)
    first = start(client, h, tid).json()
    r = start(client, h, tid)
    assert (
        r.status_code == 409
        and r.json()["code"] == "run_already_active"
        and r.json()["active_run_id"] == first["id"]
    )
    assert balance(system_conn, uid) == 60  # the refused start reserved nothing
    # another trip of the same account is the same account: still one at a time
    tid2 = str(
        system_conn.execute(
            "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'Porto', 'USD') RETURNING id",
            (uid,),
        ).fetchone()[0]
    )
    assert start(client, h, tid2).status_code == 409


def test_a_retry_with_the_same_key_replays_and_never_charges_twice(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    a = start(client, h, tid, key="retry-key-0001")
    b = start(client, h, tid, key="retry-key-0001")
    assert a.status_code == 202, a.text
    assert b.status_code == 202, b.text
    assert a.json()["id"] == b.json()["id"] and b.headers.get("idempotent-replay") == "true"
    assert balance(system_conn, uid) == 20


def test_start_gates(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    no_key = client.post(f"/v1/trips/{tid}/agent-runs", json={"kind": "deep_research"}, headers=h)
    assert no_key.status_code == 400
    sh, _ = join(client, system_conn, tid, role="viewer")
    assert start(client, sh, tid).status_code == 403  # a viewer cannot start
    stranger, _, _ = person(client, system_conn, plus=True)
    assert start(client, stranger, tid).status_code == 404
    assert start(client, h, tid, kind="fare_hunt").status_code == 422  # routes are required
    assert (
        start(client, h, tid, kind="fare_hunt", route_ids=[str(uuid.uuid4())]).status_code == 422
    )  # not on this trip
    assert start(client, h, tid, topic="x" * 301).status_code == 422
    assert (
        system_conn.execute("SELECT count(*) FROM runs WHERE trip_id = %s", (tid,)).fetchone()[0]
        == 0
    )


def test_consent_and_kill_switch_are_enforced(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True, consent=False)
    r = start(client, h, tid)
    assert r.status_code == 403 and r.json()["code"] == "ai_consent_required"
    system_conn.execute(
        "INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', '1', true)",
        (uid,),
    )
    client.app.state.flags = engaged("ai.agent_runs")
    r = start(client, h, tid)
    assert r.status_code == 503 and r.json()["code"] == "feature_disabled"


def test_not_enough_credits_is_a_402_with_the_paywall_hint(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True, credits=10)
    r = start(client, h, tid)
    assert r.status_code == 402 and r.json()["code"] == "insufficient_credits"
    assert r.json()["paywall"]["trigger"] == "out_of_credits_agent" and r.json()["credits"] == {
        "needed": 40,
        "balance": 10,
    }
    assert (
        system_conn.execute("SELECT count(*) FROM runs WHERE trip_id = %s", (tid,)).fetchone()[0]
        == 0
    )


def test_preview_shows_the_price_before_start(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True, credits=60)
    r = client.get(f"/v1/trips/{tid}/agent-runs/preview?kind=fare_hunt", headers=h)
    assert r.status_code == 200
    assert r.json() == {
        "kind": "fare_hunt",
        "credits": 40,
        "price": 40,
        "taster": False,
        "taster_used": False,
        "balance": 60,
        "sufficient": True,
        "from_cache": False,
    }


# --- list and read -----------------------------------------------------------------------------------------------------


def test_list_and_read_are_scoped_to_members(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid, topic="markets").json()
    mh, muid = join(client, system_conn, tid, role="viewer")
    page = client.get(f"/v1/trips/{tid}/agent-runs", headers=mh).json()
    assert [i["id"] for i in page["items"]] == [run["id"]] and page["has_more"] is False
    assert (
        page["items"][0]["credits"] is None and "instructions" not in page["items"][0]["params"]
    )  # the receipt is the starter's
    assert (
        client.get(f"/v1/trips/{tid}/agent-runs?status=succeeded", headers=h).json()["items"] == []
    )
    assert client.get(f"/v1/agent-runs/{run['id']}", headers=mh).status_code == 200
    other, _, _ = person(client, system_conn, plus=True)
    assert client.get(f"/v1/trips/{tid}/agent-runs", headers=other).status_code == 404
    assert (
        client.get(f"/v1/agent-runs/{run['id']}", headers=other).status_code == 404
    )  # 404, never 403
    assert client.get(f"/v1/agent-runs/{run['id']}/events", headers=other).status_code == 404
    assert client.get(f"/v1/agent-runs/{run['id']}/stream", headers=other).status_code == 404
    assert (
        client.post(
            f"/v1/agent-runs/{run['id']}/cancel",
            headers={**other, "Idempotency-Key": uuid.uuid4().hex},
        ).status_code
        == 404
    )


# --- a finished run: events, sources and the stream --------------------------------------------------------------------


def test_events_show_sources_and_the_stream_replays_from_last_event_id(
    client, system_conn, worker_engine, settings
):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    assert work(worker_engine, settings, run["id"], SAVE_THEN_FINISH) == "done:succeeded"

    events = client.get(f"/v1/agent-runs/{run['id']}/events", headers=h).json()
    types = [e["type"] for e in events]
    assert types[0] == "run.started" and events[0]["seq"] == 0 and types[-1] == "run.finished"
    assert "tool.search" in types and "turn" in types and "note.saved" in types
    saved = next(e for e in events if e["type"] == "note.saved")
    assert saved["payload"]["source_urls"] == [URL] and saved["summary"].startswith("Saved note")
    assert "cost_usd_micros" not in json.dumps(events)  # usage rows never leak a cost
    fin = events[-1]["payload"]
    assert (
        fin["status"] == "succeeded"
        and fin["credits"]["reserved"] == 40
        and fin["credits"]["charged"] == 40
    )

    r = client.get(f"/v1/agent-runs/{run['id']}/stream", headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    got, _ = frames(r.text)
    assert (
        [g[1] for g in got] == types
        and [g[0] for g in got] == [e["seq"] for e in events]
        and got[-1][1] == "run.finished"
    )
    mid = got[2][0]
    again, _ = frames(
        client.get(
            f"/v1/agent-runs/{run['id']}/stream", headers={**h, "Last-Event-ID": str(mid)}
        ).text
    )
    assert [g[0] for g in again] == [g[0] for g in got if g[0] > mid]
    assert client.get(f"/v1/agent-runs/{run['id']}/events?after_seq={mid}", headers=h).json() == [
        e for e in events if e["seq"] > mid
    ]

    note = system_conn.execute(
        "SELECT kind::text, urls FROM notes WHERE run_id = %s", (run["id"],)
    ).fetchone()
    assert note == ("agent", [URL])  # saved with its source link
    done = client.get(f"/v1/agent-runs/{run['id']}", headers=h).json()
    assert (
        done["status"] == "succeeded"
        and done["accepted_count"] == 1
        and done["credits"]["charged"] == 40
        and done["cost_usd_micros"] == 200_000
    )


def test_the_stream_follows_a_live_run_and_ends_after_run_finished(
    client, system_conn, worker_engine, settings
):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    out = {}
    t = threading.Thread(
        target=lambda: (
            time.sleep(0.4),
            out.update(r=work(worker_engine, settings, run["id"], SAVE_THEN_FINISH)),
        )
    )
    t.start()
    r = client.get(f"/v1/agent-runs/{run['id']}/stream", headers=h)
    t.join()
    got, _ = frames(r.text)
    assert (
        out["r"] == "done:succeeded"
        and got[-1][1] == "run.finished"
        and any(g[1] == "note.saved" for g in got)
    )
    assert (
        ai_router._open[uuid.UUID(uid) if isinstance(uid, str) else uid] == 0
    )  # the open-stream count is released


def test_an_idle_stream_sends_a_heartbeat_comment(client, system_conn, monkeypatch):
    monkeypatch.setattr(ai_router, "HEARTBEAT_SECONDS", 0.1)
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    threading.Timer(
        0.5,
        lambda: client.post(
            f"/v1/agent-runs/{run['id']}/cancel", headers={**h, "Idempotency-Key": uuid.uuid4().hex}
        ),
    ).start()
    got, comments = frames(client.get(f"/v1/agent-runs/{run['id']}/stream", headers=h).text)
    assert comments and comments[0] == ": heartbeat" and got[-1][1] == "run.finished"


# --- cancel ------------------------------------------------------------------------------------------------------------


def test_cancel_in_the_queue_charges_nothing_and_frees_the_account(
    client, system_conn, worker_engine, settings
):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    assert balance(system_conn, uid) == 20
    r = client.post(
        f"/v1/agent-runs/{run['id']}/cancel", headers={**h, "Idempotency-Key": uuid.uuid4().hex}
    )
    assert r.status_code == 200, r.text
    assert (
        r.json()["status"] == "cancelled"
        and r.json()["cancel_requested"] is True
        and r.json()["credits"]["charged"] == 0
    )
    assert balance(system_conn, uid) == 60
    assert (
        work(worker_engine, settings, run["id"], FINISH_ONLY) == "skipped:cancelled"
    )  # the queued job finds nothing to do
    again = client.post(
        f"/v1/agent-runs/{run['id']}/cancel", headers={**h, "Idempotency-Key": uuid.uuid4().hex}
    )
    assert again.status_code == 409 and again.json()["code"] == "state_conflict"
    assert start(client, h, tid).status_code == 202  # the slot is free
    ev = client.get(f"/v1/agent-runs/{run['id']}/events", headers=h).json()
    assert ev[-1]["type"] == "run.finished" and ev[-1]["payload"]["status"] == "cancelled"


def test_cancel_while_running_stops_at_the_next_checkpoint_and_settles_pro_rata(
    client, system_conn, worker_engine, settings
):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    seen = {}

    def cancel_from_the_api(n):
        if n == 2:  # the person taps stop while turn 2 is in flight
            r = client.post(
                f"/v1/agent-runs/{run['id']}/cancel",
                headers={**h, "Idempotency-Key": uuid.uuid4().hex},
            )
            seen.update(
                status=r.status_code,
                run_status=r.json()["status"],
                flagged=r.json()["cancel_requested"],
            )

    script = [(SEARCH + [tool("add_note", NOTE)], 1_000)]
    assert (
        work(worker_engine, settings, run["id"], script, on_call=cancel_from_the_api)
        == "done:cancelled"
    )
    assert seen == {"status": 200, "run_status": "running", "flagged": True}
    done = client.get(f"/v1/agent-runs/{run['id']}", headers=h).json()
    assert (
        done["status"] == "cancelled"
        and done["turns_used"] in (1, 2)
        and done["accepted_count"] >= 1
    )
    charged = done["credits"]["charged"]
    assert (
        8 <= charged < 40 and balance(system_conn, uid) == 60 - charged
    )  # pro rata by turns, 8 credit minimum
    assert (
        system_conn.execute(
            "SELECT count(*) FROM notes WHERE run_id = %s", (run["id"],)
        ).fetchone()[0]
        >= 1
    )  # saved work is kept


def test_only_the_starter_or_the_owner_can_stop_a_run(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    eh, _ = join(client, system_conn, tid, role="editor")
    run = start(client, h, tid).json()
    key = lambda: {"Idempotency-Key": uuid.uuid4().hex}  # noqa: E731
    vh, _ = join(client, system_conn, tid, role="viewer")
    assert (
        client.post(f"/v1/agent-runs/{run['id']}/cancel", headers={**vh, **key()}).status_code
        == 403
    )
    assert (
        client.post(f"/v1/agent-runs/{run['id']}/cancel", headers={**eh, **key()}).status_code
        == 403
    )  # an editor who is not the starter
    assert (
        client.post(f"/v1/agent-runs/{run['id']}/cancel", headers={**h, **key()}).status_code == 200
    )


# --- the taster --------------------------------------------------------------------------------------------------------


def test_the_taster_works_once_then_shows_the_credit_price(
    client, system_conn, worker_engine, settings
):
    h, uid, tid = person(client, system_conn)  # Free
    t = client.get("/v1/me/agent-taster", headers=h).json()
    assert (
        t["available"] is True
        and t["used"] is False
        and t["used_at"] is None
        and t["run_id"] is None
    )
    pre = client.get(f"/v1/trips/{tid}/agent-runs/preview?kind=deep_research", headers=h).json()
    assert pre["taster"] is True and pre["credits"] == 0 and pre["sufficient"] is True
    # the taster is a deep run: a fare hunt does not ride on it
    fh = client.get(f"/v1/trips/{tid}/agent-runs/preview?kind=fare_hunt", headers=h).json()
    assert fh["taster"] is False and fh["credits"] == 40 and fh["sufficient"] is False

    run = start(client, h, tid).json()
    assert run["is_taster"] is True and run["credits"]["reserved"] == 40
    assert (
        client.get("/v1/me/agent-taster", headers=h).json()["used"] is True
    )  # spent while the run is in flight
    assert (
        balance(system_conn, uid) == 12
    )  # the 12 monthly credits are untouched (the taster never reduces credits)

    # a failed run that saved nothing does not consume it
    assert work(worker_engine, settings, run["id"], FINISH_ONLY) == "done:failed"
    t = client.get("/v1/me/agent-taster", headers=h).json()
    assert t["used"] is False and t["available"] is True

    run2 = start(client, h, tid).json()
    assert run2["is_taster"] is True
    assert work(worker_engine, settings, run2["id"], SAVE_THEN_FINISH) == "done:succeeded"
    done = client.get(f"/v1/agent-runs/{run2['id']}", headers=h).json()
    assert done["is_taster"] is True and done["credits"]["charged"] == 40
    t = client.get("/v1/me/agent-taster", headers=h).json()
    assert (
        t["used"] is True and t["available"] is False and t["run_id"] == run2["id"] and t["used_at"]
    )
    assert balance(system_conn, uid) == 12  # still nothing taken from the monthly credits

    pre = client.get(f"/v1/trips/{tid}/agent-runs/preview?kind=deep_research", headers=h).json()
    assert (
        pre["taster"] is False
        and pre["taster_used"] is True
        and pre["credits"] == 40
        and pre["sufficient"] is False
    )
    r = start(client, h, tid)
    assert r.status_code == 402 and r.json()["code"] == "payment_required"
    assert (
        r.json()["paywall"]["reason"] == "agent_taster_used"
        and r.json()["paywall"]["trigger"] == "out_of_credits_agent"
    )


def test_a_free_user_cannot_hunt_fares_on_the_taster(client, system_conn):
    h, uid, tid = person(client, system_conn)
    rid = system_conn.execute(
        "INSERT INTO flight_routes (trip_id, label, origin_codes, destination_codes, depart_from, depart_to, trip_type) VALUES (%s, 'NYC to LIS', '{JFK}', '{LIS}', '2027-05-01', '2027-05-03', 'one_way') RETURNING id",
        (tid,),
    )
    route = str(rid.fetchone()[0])
    r = start(client, h, tid, kind="fare_hunt", route_ids=[route])
    assert r.status_code == 402 and r.json()["code"] == "insufficient_credits"
    assert client.get("/v1/me/agent-taster", headers=h).json()["available"] is True  # untouched


# --- the watchdog ------------------------------------------------------------------------------------------------------


def _running(conn, run_id, *, started_ago, beat_ago):
    conn.execute(
        "UPDATE runs SET status = 'running', started_at = %s, heartbeat_at = %s WHERE id = %s",
        (datetime.now(UTC) - started_ago, datetime.now(UTC) - beat_ago, run_id),
    )


def test_a_run_past_the_deadline_with_saved_work_is_timed_out_and_charged(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True, credits=100)
    run = start(client, h, tid).json()
    _running(
        system_conn, run["id"], started_ago=timedelta(minutes=10), beat_ago=timedelta(seconds=5)
    )
    system_conn.execute(
        "INSERT INTO notes (trip_id, kind, title, body, urls, run_id) VALUES (%s, 'agent', 'T', 'B', %s, %s)",
        (tid, [URL], run["id"]),
    )
    done = client.get(f"/v1/agent-runs/{run['id']}", headers=h).json()
    assert (
        done["status"] == "timed_out"
        and done["error_code"] == "timed_out"
        and done["credits"]["charged"] == 40
        and done["accepted_count"] == 1
    )
    assert balance(system_conn, uid) == 60
    ev = client.get(f"/v1/agent-runs/{run['id']}/events", headers=h).json()
    assert ev[-1]["type"] == "run.finished" and ev[-1]["payload"]["status"] == "timed_out"
    assert start(client, h, tid).status_code == 202  # the account is free again


def test_a_silent_worker_with_nothing_saved_is_interrupted_and_refunded(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    _running(
        system_conn, run["id"], started_ago=timedelta(minutes=6), beat_ago=timedelta(minutes=6)
    )
    # the account's next start closes the dead run first, so it is not refused as active
    r = start(client, h, tid)
    assert r.status_code == 202, r.text
    old = system_conn.execute(
        "SELECT status::text, failure_code FROM runs WHERE id = %s", (run["id"],)
    ).fetchone()
    assert old == ("interrupted", "worker_lost")
    assert balance(system_conn, uid) == 20  # the first run's 40 came back, the second reserved 40


def test_a_healthy_running_run_is_left_alone(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    _running(
        system_conn, run["id"], started_ago=timedelta(minutes=3), beat_ago=timedelta(seconds=10)
    )
    assert client.get(f"/v1/agent-runs/{run['id']}", headers=h).json()["status"] == "running"
    assert start(client, h, tid).status_code == 409


# --- review follow-ups (WF-053.1) --------------------------------------------------------------------------------------


def _route(conn, tid):
    return str(
        conn.execute(
            "INSERT INTO flight_routes (trip_id, label, origin_codes, destination_codes, depart_from, depart_to, trip_type) VALUES (%s, 'NYC to LIS', '{JFK}', '{LIS}', '2027-05-01', '2027-05-03', 'one_way') RETURNING id",
            (tid,),
        ).fetchone()[0]
    )


def _taster_remaining(conn, uid):
    return conn.execute("SELECT remaining FROM credit_grants WHERE user_id = %s AND period_key = 'taster'", (uid,)).fetchone()[0]


def test_a_fare_hunt_never_draws_the_taster_even_for_a_free_user_with_other_credits(client, system_conn):
    h, uid, tid = person(client, system_conn)  # Free
    assert client.get("/v1/me/agent-taster", headers=h).json()["available"] is True  # the grant exists
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, trip_id, kind, credits, remaining) VALUES (%s, %s, 'trip_pass', 50, 50)", (uid, tid)
    )
    system_conn.execute(
        "INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', now() - interval '1 day', now() + interval '30 days', 'active')", (tid,)
    )  # the pass makes the trip the payer, with its own ceiling
    r = start(client, h, tid, kind="fare_hunt", route_ids=[_route(system_conn, tid)])
    assert r.status_code == 202, r.text
    assert r.json()["is_taster"] is False and r.json()["credits"]["reserved"] == 40
    assert _taster_remaining(system_conn, uid) == 40  # untouched
    assert system_conn.execute("SELECT remaining FROM credit_grants WHERE user_id = %s AND kind = 'trip_pass'", (uid,)).fetchone()[0] == 22  # 12 monthly first, then 28 from the pass
    assert client.get("/v1/me/agent-taster", headers=h).json()["available"] is True


def test_a_plus_member_with_a_leftover_taster_is_charged_credits(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, restricted_action, period_key) VALUES (%s, 'promo', 40, 40, 'agent_run', 'taster')", (uid,)
    )
    t = client.get("/v1/me/agent-taster", headers=h).json()
    assert t["available"] is False  # Free only
    r = start(client, h, tid)
    assert r.status_code == 202 and r.json()["is_taster"] is False
    assert _taster_remaining(system_conn, uid) == 40
    assert balance(system_conn, uid) == 40 + 20  # 60 monthly less 40, plus the untouched taster


def test_a_taster_run_gets_the_smaller_caps_and_a_paid_run_the_table_caps(client, system_conn, worker_engine, settings, monkeypatch):
    seen = []
    real = run_agent.AgentLoop

    def spy(provider, spec, *a, **k):
        seen.append(spec)
        return real(provider, spec, *a, **k)

    monkeypatch.setattr(run_agent, "AgentLoop", spy)
    h, uid, tid = person(client, system_conn)
    run = start(client, h, tid).json()
    assert run["is_taster"] is True
    work(worker_engine, settings, run["id"], FINISH_ONLY)
    s = seen[-1]
    assert (s.max_turns, s.max_searches, s.max_fetches, s.stop_micro) == (12, 6, 6, 800_000)

    h2, uid2, tid2 = person(client, system_conn, plus=True)
    run2 = start(client, h2, tid2).json()
    work(worker_engine, settings, run2["id"], FINISH_ONLY)
    s = seen[-1]
    assert (s.max_turns, s.max_searches, s.max_fetches) == (20, 10, 10)


def test_open_streams_do_not_starve_other_routes(client, system_conn, monkeypatch):
    import anyio.to_thread

    def shrink():
        anyio.to_thread.current_default_thread_limiter().total_tokens = 2

    client.portal.call(shrink)  # two threads for the whole app: the old blocking stream would take both
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    heads = [h]
    for _ in range(2):
        mh, _u = join(client, system_conn, tid, role="viewer")
        heads.append(mh)
    out = []
    threads = [threading.Thread(target=lambda hh=hh: out.append(client.get(f"/v1/agent-runs/{run['id']}/stream", headers=hh).status_code)) for hh in heads]
    for t in threads:
        t.start()
    time.sleep(0.6)  # all three are open and idle
    t0 = time.monotonic()
    assert client.get(f"/v1/agent-runs/{run['id']}", headers=h).status_code == 200
    assert client.get("/v1/me/agent-taster", headers=h).status_code == 200
    assert time.monotonic() - t0 < 3
    client.post(f"/v1/agent-runs/{run['id']}/cancel", headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    for t in threads:
        t.join(10)
    assert out == [200, 200, 200]


def test_one_stream_per_run_per_user_and_the_slot_is_released(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    out = []
    t = threading.Thread(target=lambda: out.append(client.get(f"/v1/agent-runs/{run['id']}/stream", headers=h).status_code))
    t.start()
    time.sleep(0.5)
    second = client.get(f"/v1/agent-runs/{run['id']}/stream", headers=h)
    assert second.status_code == 429 and second.json()["code"] == "rate_limited"
    client.post(f"/v1/agent-runs/{run['id']}/cancel", headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    t.join(10)
    assert out == [200] and not ai_router._open_runs
    assert client.get(f"/v1/agent-runs/{run['id']}/stream", headers=h).status_code == 200  # a reconnect is allowed again


def test_hidden_rows_never_stall_the_events_page(client, system_conn):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()
    system_conn.execute(
        "INSERT INTO run_events (run_id, trip_id, seq, type, summary) SELECT %s, %s, g, 'text', 'thinking' FROM generate_series(1, 250) g", (run["id"], tid)
    )
    system_conn.execute(
        "INSERT INTO run_events (run_id, trip_id, seq, type, summary, payload) VALUES (%s, %s, 251, 'info', 'usage', '{\"kind\": \"usage\", \"turn\": 1, \"cost_usd_micros\": 5}')",
        (run["id"], tid),
    )
    got = client.get(f"/v1/agent-runs/{run['id']}/events?after_seq=0&limit=200", headers=h).json()
    assert [e["type"] for e in got] == ["turn"] and got[0]["seq"] == 251 and "cost" not in json.dumps(got)


def test_a_run_closed_by_the_watchdog_mid_flight_is_not_overwritten_by_the_worker(client, system_conn, worker_engine, settings):
    h, uid, tid = person(client, system_conn, plus=True)
    run = start(client, h, tid).json()

    def watchdog_fires(n):
        if n == 1:
            system_conn.execute("UPDATE runs SET started_at = now() - interval '10 minutes' WHERE id = %s", (run["id"],))
            assert client.get(f"/v1/agent-runs/{run['id']}", headers=h).json()["status"] == "timed_out"

    assert work(worker_engine, settings, run["id"], FINISH_ONLY, on_call=watchdog_fires) == "skipped:closed"
    done = client.get(f"/v1/agent-runs/{run['id']}", headers=h).json()
    assert done["status"] == "timed_out" and done["credits"]["charged"] == 0
    assert system_conn.execute("SELECT count(*) FROM run_events WHERE run_id = %s AND type = 'result'", (run["id"],)).fetchone()[0] == 1
    assert balance(system_conn, uid) == 60


def test_a_cancel_between_the_worker_read_and_its_claim_is_not_overwritten(client, system_conn, worker_engine, settings, monkeypatch):
    h, uid, tid = person(client, system_conn)  # Free: the taster pays, so a refund is visible on the grant
    run = start(client, h, tid).json()
    assert run["is_taster"] is True and _taster_remaining(system_conn, uid) == 0
    stub = Stub(settings, FINISH_ONLY)

    def provider_after_the_person_taps_stop(_settings, _email):
        r = client.post(f"/v1/agent-runs/{run['id']}/cancel", headers={**h, "Idempotency-Key": uuid.uuid4().hex})
        assert r.status_code == 200 and r.json()["status"] == "cancelled"
        return stub

    monkeypatch.setattr(run_agent, "_provider", provider_after_the_person_taps_stop)
    with Session(worker_engine) as s:
        out = run_agent.run(s, settings, str(run["id"]), build_task=lambda _s, _r: "task", poll_seconds=0.05)
    assert out == "skipped:closed" and stub.calls == 0
    row = system_conn.execute("SELECT status::text, failure_code FROM runs WHERE id = %s", (run["id"],)).fetchone()
    assert row == ("cancelled", "cancelled")
    assert system_conn.execute("SELECT count(*) FROM run_events WHERE run_id = %s AND type = 'result'", (run["id"],)).fetchone()[0] == 1
    assert _taster_remaining(system_conn, uid) == 40  # returned: it was stopped in the queue
    assert system_conn.execute("SELECT charged FROM credit_ledger WHERE run_id = %s AND entry_type = 'settle'", (run["id"],)).fetchone()[0] == 0
