# ruff: noqa: E501
"""WF-051.1: scheduler leader election and the due-route scan. Real PostgreSQL, the worker login, AI_PROVIDER=fake (conftest)."""

import asyncio
import os
import subprocess
import sys
import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import Settings
from hermi_worker import app as worker_app
from hermi_worker import scheduler
from hermi_worker.jobs import scan_due_routes

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)


def run_async(coro):
    return asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)


@pytest.fixture
def clean_queue(system_conn):
    for t in ("procrastinate_events", "procrastinate_periodic_defers", "procrastinate_jobs", "procrastinate_workers"):
        system_conn.execute(f"DELETE FROM {t}")


@pytest.fixture
def sys_session(db_urls):
    engine = create_engine(db.psycopg_url(db_urls["system"]))
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
def make_route(system_conn, make_user):
    system_conn.execute("DELETE FROM flight_routes")  # earlier tests leave due routes behind
    uid, _ = make_user()
    trip = system_conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (uid,)).fetchone()[0]

    def make(next_check_at=None, active=True):
        return system_conn.execute(
            """INSERT INTO flight_routes (trip_id, origin_codes, destination_codes, depart_from, depart_to, return_from, return_to,
                                          is_live, next_check_at, active)
               VALUES (%s, '{LIS}', '{NRT}', '2027-01-10', '2027-01-20', '2027-01-25', '2027-01-30', true, %s, %s) RETURNING id""",
            (trip, next_check_at, active),
        ).fetchone()[0]

    return make


def _jobs(conn):
    return conn.execute("SELECT args->>'route_id', queue_name, priority FROM procrastinate_jobs WHERE task_name = 'check_fare_route'").fetchall()


def _settings(db_urls):
    return Settings(_env_file=None, environment="ci", database_url_system=db_urls["system"], scheduler_enabled=True)


def _dispose(*apps):
    for a in apps:
        a.sqlalchemy_engine.dispose()
        a.fairness_engine.dispose()


# --- jitter and slots ---------------------------------------------------------------------------------------------------


def test_jitter_is_stable_across_calls_and_processes_and_within_the_window():
    rid = uuid.UUID("0197f1c2-8a3b-7c4d-9e5f-0123456789ab")
    first = scan_due_routes.jitter_seconds(rid)
    assert first == scan_due_routes.jitter_seconds(uuid.UUID(str(rid))) and 0 <= first < 3600
    code = f"import uuid; from hermi_worker.jobs.scan_due_routes import jitter_seconds as j; print(j(uuid.UUID('{rid}')))"
    out = [
        subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, env={**os.environ, "PYTHONHASHSEED": str(s)}).stdout.strip()
        for s in (1, 2)
    ]
    assert out == [str(first)] * 2  # not python's salted hash()
    assert len({scan_due_routes.jitter_seconds(uuid.uuid4()) for _ in range(50)}) > 25


def test_next_slot_is_strictly_after_now_and_within_a_day():
    rid = uuid.uuid4()
    j = scan_due_routes.jitter_seconds(rid)
    midnight = NOW.replace(hour=0, minute=0)
    for now in (NOW, midnight + timedelta(seconds=j), midnight + timedelta(seconds=j - 1)):
        slot = scan_due_routes.next_slot(rid, now)
        assert now < slot <= now + timedelta(days=1)
        assert (slot - slot.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() == j


# --- scan ---------------------------------------------------------------------------------------------------------------


def test_scan_enqueues_due_routes_only_and_moves_the_slot(sys_session, system_conn, make_route, clean_queue):
    due = make_route(NOW - timedelta(minutes=1))
    later = make_route(NOW + timedelta(hours=1))
    unscheduled = make_route(None)
    inactive = make_route(NOW - timedelta(hours=1), active=False)
    res = scan_due_routes.run(sys_session, now=NOW)
    sys_session.commit()
    assert res["due"] == 1 and res["enqueued"] == 1
    assert _jobs(system_conn) == [(str(due), "api", 5)]
    got = dict(system_conn.execute("SELECT id, next_check_at FROM flight_routes WHERE id IN (%s,%s,%s,%s)", (due, later, unscheduled, inactive)).fetchall())
    assert got[due] == scan_due_routes.next_slot(due, NOW) > NOW
    assert got[later] == NOW + timedelta(hours=1) and got[unscheduled] is None
    assert scan_due_routes.run(sys_session, now=NOW)["due"] == 0 and len(_jobs(system_conn)) == 1


def test_misfire_after_an_outage_fires_one_check_not_twelve(sys_session, system_conn, make_route, clean_queue):
    rid = make_route(NOW - timedelta(days=12))  # twelve missed daily slots
    scan_due_routes.run(sys_session, now=NOW)
    sys_session.commit()
    assert len(_jobs(system_conn)) == 1
    nxt = system_conn.execute("SELECT next_check_at FROM flight_routes WHERE id = %s", (rid,)).fetchone()[0]
    assert NOW < nxt <= NOW + timedelta(days=1)
    scan_due_routes.run(sys_session, now=NOW + timedelta(minutes=1))
    sys_session.commit()
    assert len(_jobs(system_conn)) == 1


def test_scan_takes_at_most_the_limit(sys_session, make_route, clean_queue):
    for _ in range(3):
        make_route(NOW - timedelta(minutes=1))
    assert scan_due_routes.run(sys_session, now=NOW, limit=2)["due"] == 2


def test_concurrent_scans_never_enqueue_a_route_twice(db_urls, system_conn, make_route, clean_queue):
    ids = [make_route(NOW - timedelta(minutes=1)) for _ in range(20)]
    results, engines = [], [create_engine(db.psycopg_url(db_urls["system"])) for _ in range(2)]
    barrier = threading.Barrier(2)

    def go(engine):
        with Session(engine) as s:
            barrier.wait(10)
            results.append(scan_due_routes.run(s, now=NOW, limit=12))
            s.commit()

    ts = [threading.Thread(target=go, args=(e,)) for e in engines]
    [t.start() for t in ts]
    [t.join(30) for t in ts]
    [e.dispose() for e in engines]
    got = [j[0] for j in _jobs(system_conn)]
    assert len(got) == len(set(got)) and set(got) <= {str(i) for i in ids}
    assert sum(r["enqueued"] for r in results) == len(got) and len(got) >= 12


# --- leader election ----------------------------------------------------------------------------------------------------


def test_second_scheduler_never_acquires_while_the_first_holds_the_lock(db_urls):
    url = db.psycopg_url(db_urls["system"])
    a, b = scheduler.Election(url), scheduler.Election(url)
    try:
        assert a.try_acquire() is True
        assert b.try_acquire() is False and b.try_acquire() is False
        assert scheduler.leader_present(url) is True
        a.release()
        assert scheduler.leader_present(url) is False
        assert b.try_acquire() is True  # takes over after release
        assert a.try_acquire() is False
    finally:
        a.release()
        b.release()


def test_a_dropped_connection_drops_leadership(db_urls, system_conn):
    url = db.psycopg_url(db_urls["system"])
    a, other = scheduler.Election(url), scheduler.Election(url)
    try:
        assert a.try_acquire() and a.alive()
        system_conn.execute("SELECT pg_terminate_backend(%s)", (a._conn.info.backend_pid,))
        assert a.alive() is False
        assert other.try_acquire() is True
    finally:
        a.release()
        other.release()


def test_only_the_leader_scans_and_a_standby_takes_over(db_urls, system_conn, make_route, clean_queue):
    url = db.psycopg_url(db_urls["system"])
    due = make_route(datetime.now(UTC) - timedelta(minutes=1))
    app1, app2 = worker_app.build_app(_settings(db_urls)), worker_app.build_app(_settings(db_urls))
    due_again = "UPDATE flight_routes SET next_check_at = now() - interval '1 minute' WHERE id = %s"

    async def wait_for_job():
        for _ in range(60):
            await asyncio.sleep(0.1)
            if _jobs(system_conn):
                return
        raise AssertionError("no job enqueued")

    async def main():
        s1, s2 = asyncio.Event(), asyncio.Event()
        async with app1.open_async(), app2.open_async():
            t1 = asyncio.create_task(scheduler.run(app1, _settings(db_urls), s1, tick=0.2, retry=0.2))
            await wait_for_job()
            await asyncio.sleep(0.3)  # the first tick of the leader is done; start the standby
            t2 = asyncio.create_task(scheduler.run(app2, _settings(db_urls), s2, tick=0.2, retry=0.2))
            system_conn.execute("DELETE FROM procrastinate_jobs WHERE task_name = 'check_fare_route'")
            await asyncio.sleep(1.0)
            assert scheduler.leader_present(url) and not s2.is_set()
            s1.set()
            await t1  # releases the lock
            system_conn.execute("DELETE FROM procrastinate_jobs WHERE task_name = 'check_fare_route'")
            system_conn.execute(due_again, (due,))
            await wait_for_job()  # the standby took over
            s2.set()
            await t2

    try:
        run_async(main())
    finally:
        _dispose(app1, app2)


def test_a_non_leader_fires_nothing(db_urls, system_conn, make_route, clean_queue):
    url = db.psycopg_url(db_urls["system"])
    make_route(datetime.now(UTC) - timedelta(minutes=1))
    holder = scheduler.Election(url)
    assert holder.try_acquire()
    app = worker_app.build_app(_settings(db_urls))

    async def main():
        stop = asyncio.Event()
        async with app.open_async():
            t = asyncio.create_task(scheduler.run(app, _settings(db_urls), stop, tick=0.1, retry=0.1))
            await asyncio.sleep(1.0)
            stop.set()
            await t

    try:
        run_async(main())
        assert _jobs(system_conn) == []
        assert system_conn.execute("SELECT count(*) FROM procrastinate_periodic_defers").fetchone()[0] == 0
    finally:
        holder.release()
        _dispose(app)


def test_periodic_tasks_ride_the_scheduler_not_the_lane_workers(db_urls):
    app = worker_app.build_app(_settings(db_urls))
    try:
        assert app.periodic_registry.periodic_tasks == {}  # the lane workers' own deferrers have nothing to fire
        assert "reap_stale_jobs" in {k[0] for k in app.scheduled_registry.periodic_tasks}
    finally:
        _dispose(app)


def _run_for(app, settings, seconds):
    async def main():
        stop = asyncio.Event()
        async with app.open_async():
            t = asyncio.create_task(scheduler.run(app, settings, stop, tick=0.1, retry=0.1))
            await asyncio.sleep(seconds)
            stop.set()
            await t

    run_async(main())


def test_a_tick_logs_its_metrics(db_urls, make_route, clean_queue, caplog):
    make_route(datetime.now(UTC) - timedelta(minutes=1))
    app = worker_app.build_app(_settings(db_urls))
    try:
        with caplog.at_level("INFO", logger="hermi_worker.scheduler"):
            _run_for(app, _settings(db_urls), 1.0)
    finally:
        _dispose(app)
    ticks = [r for r in caplog.records if r.getMessage() == "scheduler tick"]
    assert ticks and all(hasattr(ticks[0], k) for k in ("due", "enqueued", "skipped_already_queued", "duration_ms"))
    assert (ticks[0].due, ticks[0].enqueued) == (1, 1)


def test_only_the_leader_pings_the_heartbeat_and_the_url_is_never_logged(db_urls, make_route, clean_queue, monkeypatch, caplog):
    url = "https://uptime.example.test/api/heartbeat/SECRETTOKEN123"
    pings = []
    monkeypatch.setattr(scheduler, "_ping", lambda u: pings.append(u))
    settings = Settings(
        _env_file=None, environment="ci", database_url_system=db_urls["system"], scheduler_enabled=True, betterstack_heartbeat_scheduler=url
    )
    app = worker_app.build_app(settings)
    holder = scheduler.Election(db.psycopg_url(db_urls["system"]))
    try:
        assert holder.try_acquire()
        with caplog.at_level("DEBUG"):
            _run_for(app, settings, 0.8)
        assert pings == []  # a non-leader never pings
        holder.release()
        with caplog.at_level("DEBUG"):
            _run_for(app, settings, 0.8)
        assert pings == [url]  # the leader pings once within the minute
    finally:
        holder.release()
        _dispose(app)
    assert "SECRETTOKEN123" not in caplog.text
