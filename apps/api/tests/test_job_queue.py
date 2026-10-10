# ruff: noqa: E501  (long SQL strings)
"""WF-046.1: the Procrastinate queue. Real PostgreSQL, the worker login for arranging rows, AI_PROVIDER=fake (conftest)."""

import asyncio
import os
import signal
import subprocess
import sys
import threading
import time

import procrastinate
import pytest
from procrastinate.jobs import Job
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from hermi import db, jobs
from hermi.config import Settings
from hermi.errors import ApiError
from hermi.providers import ProviderError
from hermi_worker import app as worker_app
from hermi_worker import retry
from hermi_worker.jobs import (
    maintain_partitions,
    purge_trash,
    reap_stale_jobs,
    release_stale_reservations,
)


def run_async(coro):
    return asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)


@pytest.fixture
def settings(db_urls):
    return Settings(_env_file=None, environment="ci", database_url_system=db_urls["system"])


@pytest.fixture
def clean_queue(system_conn):
    for t in ("procrastinate_events", "procrastinate_periodic_defers", "procrastinate_jobs", "procrastinate_workers"):
        system_conn.execute(f"DELETE FROM {t}")


@pytest.fixture
def app(settings, clean_queue):
    a = worker_app.build_app(settings)
    yield a
    a.sqlalchemy_engine.dispose()
    a.fairness_engine.dispose()


def statuses(conn, name):
    return conn.execute("SELECT status::text, attempts FROM procrastinate_jobs WHERE task_name = %s ORDER BY id", (name,)).fetchall()


async def drain(app, workers=1, **opts):
    """Run `workers` workers on one lane until the queue is empty."""
    async with app.open_async():
        ws = [
            app._worker(queues=["api"], name=f"w{i}", concurrency=2, wait=False, install_signal_handlers=False, listen_notify=False, **opts)
            for i in range(workers)
        ]
        await asyncio.gather(*(w.run() for w in ws))


# --- registry -------------------------------------------------------------------------------------------------------


def test_the_catalogue_jobs_plus_the_reaper(app):
    names = {n for n in app.tasks if not n.startswith(("builtin:", "procrastinate."))}
    assert names - worker_app.INFRA_TASKS == {
        "release_stale_reservations", "maintain_partitions", "purge_trash",
        "send_email", "send_predeparture_reminder", "build_digest", "send_trial_ending_reminder", "run_agent",
    }  # fmt: skip
    assert names & worker_app.INFRA_TASKS == {"reap_stale_jobs"}
    assert {n: t.queue for n, t in app.tasks.items() if n in names} == {
        "release_stale_reservations": "api",
        "maintain_partitions": "batch",
        "purge_trash": "batch",
        "send_email": "notify",
        "send_predeparture_reminder": "notify",
        "build_digest": "notify",
        "send_trial_ending_reminder": "notify",
        "run_agent": "ai",
        "reap_stale_jobs": "batch",
    }
    assert set(jobs.JOB_LANES) == names - worker_app.INFRA_TASKS


def test_periodic_schedules_only_on_the_leader(db_urls, clean_queue):
    off = worker_app.build_app(Settings(_env_file=None, environment="ci", database_url_system=db_urls["system"], scheduler_enabled=False))
    on = worker_app.build_app(Settings(_env_file=None, environment="ci", database_url_system=db_urls["system"], scheduler_enabled=True))
    try:
        assert off.periodic_registry.periodic_tasks == {}
        crons = {k[0]: p.cron for k, p in on.periodic_registry.periodic_tasks.items()}
        assert crons == {
            "release_stale_reservations": "*/5 * * * *",
            "maintain_partitions": "30 2 * * *",
            "purge_trash": "30 4 * * *",
            "send_predeparture_reminder": "0 * * * *",
            "build_digest": "5 * * * *",
            "send_trial_ending_reminder": "10 * * * *",
            "reap_stale_jobs": "* * * * *",
        }
    finally:
        off.sqlalchemy_engine.dispose()
        on.sqlalchemy_engine.dispose()


def test_concurrency_comes_from_settings():
    s = Settings(_env_file=None, environment="ci", worker_concurrency_api=30, worker_concurrency_ai=6, worker_concurrency_notify=50, worker_concurrency_batch=2)
    assert [worker_app.concurrency(s, lane) for lane in jobs.LANES] == [30, 6, 50, 2]


# --- retry classes --------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("exc", "kind"),
    [
        (ProviderError("x", status_code=429), "transient"),
        (ProviderError("x", status_code=503), "transient"),
        (ProviderError("x", status_code=404), "permanent"),
        (ProviderError("x", status_code=400), "permanent"),
        (ApiError(402, "budget_exhausted", "no"), "permanent"),
        (ApiError(429, "rate_limited", "slow"), "transient"),
        (TimeoutError(), "transient"),
        (ConnectionResetError(), "transient"),
        (ValueError("bad input"), "permanent"),
        (RuntimeError("bug"), "permanent"),
        (asyncio.CancelledError(), "transient"),
        (procrastinate.exceptions.JobAborted(), "transient"),
    ],
)
def test_classify(exc, kind):
    assert retry.classify(exc) == kind


def test_backoff_is_exponential_jittered_capped_and_honors_retry_after():
    assert retry.backoff_seconds(0, rng=lambda: 1.0) == 30
    assert retry.backoff_seconds(0, rng=lambda: 0.0) == 15
    assert retry.backoff_seconds(1, rng=lambda: 1.0) == 60
    assert retry.backoff_seconds(10, rng=lambda: 1.0) == 900
    assert retry.backoff_seconds(0, retry_after=120, rng=lambda: 1.0) == 120


def _job(attempts):
    return Job(id=1, queue="api", lock=None, queueing_lock=None, task_name="t", task_kwargs={}, attempts=attempts)


def test_strategy_retries_transient_up_to_the_limit_then_gives_up():
    s = retry.HermiRetry(3, rng=lambda: 1.0)
    err = ProviderError("x", status_code=503)
    assert [s.get_retry_decision(exception=err, job=_job(a)) is not None for a in range(5)] == [True, True, True, False, False]
    assert s.get_retry_decision(exception=ProviderError("x", status_code=404), job=_job(0)) is None


def test_exhausted_and_permanent_jobs_end_failed_and_transient_ones_are_rescheduled(app, system_conn):
    @app.task(name="t_perm", queue="api", retry=retry.HermiRetry(3))
    def t_perm():
        raise ApiError(402, "budget_exhausted", "no")

    @app.task(name="t_trans", queue="api", retry=retry.HermiRetry(3))
    def t_trans():
        raise ProviderError("x", status_code=503)

    @app.task(name="t_dead", queue="api", retry=retry.HermiRetry(0))
    def t_dead():
        raise ProviderError("x", status_code=503)

    async def go():
        async with app.open_async():
            for t in (t_perm, t_trans, t_dead):
                await t.defer_async()
        await drain(app)

    run_async(go())
    assert statuses(system_conn, "t_perm") == [("failed", 1)]
    assert statuses(system_conn, "t_dead") == [("failed", 1)]
    assert statuses(system_conn, "t_trans") == [("todo", 1)]
    wait = system_conn.execute("SELECT extract(epoch FROM scheduled_at - now()) FROM procrastinate_jobs WHERE task_name = 't_trans'").fetchone()[0]
    assert 10 < wait <= 30


# --- same transaction enqueue --------------------------------------------------------------------------------------


@pytest.fixture
def app_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]))
    yield e
    e.dispose()


def test_enqueue_rolls_back_with_the_callers_transaction(app_engine, system_conn, clean_queue):
    with Session(app_engine) as s:
        s.execute(text("SELECT 1"))
        jobs.enqueue(s, "purge_trash")
        s.rollback()
    assert statuses(system_conn, "purge_trash") == []
    with Session(app_engine) as s:
        job_id = jobs.enqueue(s, "release_stale_reservations", queueing_lock="rsr")
        assert statuses(system_conn, "release_stale_reservations") == []  # not visible before commit
        s.commit()
    row = system_conn.execute("SELECT id, queue_name, status::text FROM procrastinate_jobs WHERE task_name = 'release_stale_reservations'").fetchone()
    assert row == (job_id, "api", "todo")


def test_enqueue_refuses_unknown_names_and_duplicate_queueing_locks(app_engine, clean_queue):
    with Session(app_engine) as s:
        with pytest.raises(KeyError):
            jobs.enqueue(s, "no_such_job")
        jobs.enqueue(s, "purge_trash", queueing_lock="k")
        with pytest.raises(procrastinate.exceptions.AlreadyEnqueued):
            jobs.enqueue(s, "purge_trash", queueing_lock="k")


# --- running jobs ---------------------------------------------------------------------------------------------------


def test_two_workers_never_run_a_job_twice(app, system_conn):
    ran = []
    lock = threading.Lock()

    @app.task(name="t_once", queue="api")
    def t_once(n):
        time.sleep(0.05)
        with lock:
            ran.append(n)

    async def go():
        async with app.open_async():
            for n in range(20):
                await t_once.defer_async(n=n)
        await drain(app, workers=2)

    run_async(go())
    assert sorted(ran) == list(range(20))
    assert len(statuses(system_conn, "t_once")) == 20
    assert {s for s, _ in statuses(system_conn, "t_once")} == {"succeeded"}


def test_graceful_stop_lets_the_running_job_finish_and_claims_nothing_new(app, system_conn):
    started = threading.Event()

    @app.task(name="t_slow", queue="api")
    def t_slow():
        started.set()
        time.sleep(1.0)

    async def go():
        async with app.open_async():
            await t_slow.defer_async()
            w = app._worker(queues=["api"], name="g", concurrency=1, install_signal_handlers=False, shutdown_graceful_timeout=30, listen_notify=False)
            run = asyncio.create_task(w.run())
            while not started.is_set():
                await asyncio.sleep(0.02)
            w.stop()
            await t_slow.defer_async()  # arrives after the stop request
            await asyncio.wait_for(run, 20)

    run_async(go())
    assert statuses(system_conn, "t_slow") == [("succeeded", 1), ("todo", 0)]
    assert system_conn.execute("SELECT count(*) FROM procrastinate_workers").fetchone()[0] == 0


@pytest.mark.posix_only
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
def test_sigterm_stops_the_worker_process_cleanly(db_urls, system_conn, clean_queue):
    env = {**os.environ, "ENVIRONMENT": "ci", "DATABASE_URL_SYSTEM": db_urls["system"], "SCHEDULER_ENABLED": "false"}
    p = subprocess.Popen([sys.executable, "-c", "from hermi.cli import main; main(['worker', '--lanes', 'batch'])"], env=env)
    try:
        for _ in range(100):
            if system_conn.execute("SELECT count(*) FROM procrastinate_workers").fetchone()[0] == 1:
                break
            time.sleep(0.1)
        else:
            pytest.fail("the worker never registered")
        p.send_signal(signal.SIGTERM)
        assert p.wait(timeout=20) == 0
        assert system_conn.execute("SELECT count(*) FROM procrastinate_workers").fetchone()[0] == 0
    finally:
        if p.poll() is None:
            p.kill()


# --- reaper ---------------------------------------------------------------------------------------------------------


def _doing_job(conn, queue, worker_id):
    return conn.execute(
        "INSERT INTO procrastinate_jobs (queue_name, task_name, status, worker_id, attempts) VALUES (%s, 'purge_trash', 'doing', %s, 0) RETURNING id",
        (queue, worker_id),
    ).fetchone()[0]


def test_reaper_requeues_jobs_of_stale_workers_with_a_longer_limit_for_ai(app, system_conn):
    def worker(age):
        return system_conn.execute("INSERT INTO procrastinate_workers (last_heartbeat) VALUES (now() - make_interval(secs => %s)) RETURNING id", (age,)).fetchone()[0]

    fresh, three_min, six_min = worker(10), worker(180), worker(360)
    ids = {
        "fresh": _doing_job(system_conn, "api", fresh),
        "api_stale": _doing_job(system_conn, "api", three_min),
        "ai_3min": _doing_job(system_conn, "ai", three_min),
        "ai_6min": _doing_job(system_conn, "ai", six_min),
    }

    async def reap():
        async with app.open_async():
            return await reap_stale_jobs.run(app)

    assert run_async(reap()) == 2
    st = dict(system_conn.execute("SELECT id, status::text FROM procrastinate_jobs").fetchall())
    assert {k: st[v] for k, v in ids.items()} == {"fresh": "doing", "api_stale": "todo", "ai_3min": "doing", "ai_6min": "todo"}
    assert system_conn.execute("SELECT attempts FROM procrastinate_jobs WHERE id = %s", (ids["api_stale"],)).fetchone()[0] == 1


def test_reaper_fails_stale_jobs_that_are_out_of_retries_and_requeues_the_rest(app, system_conn):
    w = system_conn.execute("INSERT INTO procrastinate_workers (last_heartbeat) VALUES (now() - interval '10 minutes') RETURNING id").fetchone()[0]

    def doing(task, attempts):
        return system_conn.execute(
            "INSERT INTO procrastinate_jobs (queue_name, task_name, status, worker_id, attempts) VALUES ('api', %s, 'doing', %s, %s) RETURNING id", (task, w, attempts)
        ).fetchone()[0]

    # purge_trash is registered with HermiRetry(3); an unregistered task has no strategy
    spent, fresh, unknown = doing("purge_trash", 3), doing("purge_trash", 0), doing("t_unregistered", 0)

    async def reap():
        async with app.open_async():
            return await reap_stale_jobs.run(app)

    assert run_async(reap()) == 1
    st = dict(system_conn.execute("SELECT id, status::text FROM procrastinate_jobs").fetchall())
    assert (st[spent], st[fresh], st[unknown]) == ("failed", "todo", "failed")
    assert system_conn.execute("SELECT scheduled_at > now() FROM procrastinate_jobs WHERE id = %s", (fresh,)).fetchone()[0]


def test_worker_command_rejects_unknown_lanes(settings):
    from hermi_worker import runner

    with pytest.raises(SystemExit, match="unknown lane bogus"):
        runner.run(settings, "api,bogus")


# --- job bodies -----------------------------------------------------------------------------------------------------


@pytest.fixture
def sys_session(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["system"]))
    with Session(e) as s:
        yield s
    e.dispose()


def test_the_body_passes_attempts_only_to_jobs_that_declare_needs_attempts(app, monkeypatch):
    from types import SimpleNamespace

    from hermi_worker.jobs import run_agent as run_agent_job
    from hermi_worker.jobs import send_email as send_email_job

    seen = []
    monkeypatch.setattr(run_agent_job, "run", lambda *a, **kw: seen.append(("run_agent", kw)) or "ok")
    monkeypatch.setattr(send_email_job, "run", lambda *a, **kw: seen.append(("send_email", kw)) or "ok")
    ctx = SimpleNamespace(job=SimpleNamespace(id=1, attempts=2))
    app.tasks["run_agent"].func(ctx, run_id="x")
    app.tasks["send_email"].func(ctx, notification_id="n")
    assert seen == [("run_agent", {"run_id": "x", "attempts": 2}), ("send_email", {"notification_id": "n"})]


def test_release_stale_reservations_job_calls_the_credit_service(sys_session):
    assert release_stale_reservations.run(sys_session) == 0
    assert (release_stale_reservations.NAME, release_stale_reservations.LANE, release_stale_reservations.RETRIES) == ("release_stale_reservations", "api", 3)


def test_maintain_partitions_job_runs_and_stays_quiet_without_default_partition_rows(sys_session, caplog):
    maintain_partitions.run(sys_session)
    assert not [r for r in caplog.records if r.levelname == "ERROR"]


def test_purge_trash_job_hard_deletes_trips_trashed_over_30_days_ago(sys_session, make_user, system_conn):
    uid, _ = make_user()

    def trip(deleted):
        return system_conn.execute(
            f"INSERT INTO trips (owner_user_id, name, home_currency, deleted_at) VALUES (%s, 'T', 'USD', {deleted}) RETURNING id", (uid,)
        ).fetchone()[0]

    old, recent, live = trip("now() - interval '31 days'"), trip("now() - interval '3 days'"), trip("NULL")
    assert purge_trash.run(sys_session) == 1
    sys_session.commit()
    left = {r[0] for r in system_conn.execute("SELECT id FROM trips WHERE owner_user_id = %s", (uid,)).fetchall()}
    assert left == {recent, live} and old not in left
