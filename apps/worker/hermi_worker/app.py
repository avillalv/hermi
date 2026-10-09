# ruff: noqa: E501
"""The Procrastinate app: the three catalogue jobs and the reaper, bound to the worker login (DATABASE_URL_SYSTEM)."""

import asyncio
import logging

import procrastinate
from procrastinate.job_context import JobContext
from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.db import make_engine, psycopg_url
from hermi.jobs import JOB_LANES, LANES
from hermi_worker import fairness
from hermi_worker.jobs import (
    build_digest,
    maintain_partitions,
    purge_trash,
    reap_stale_jobs,
    release_stale_reservations,
    send_email,
    send_predeparture_reminder,
    send_trial_ending_reminder,
)
from hermi_worker.observability import job_context
from hermi_worker.retry import HermiRetry

log = logging.getLogger(__name__)

# The registered business jobs. The queue names in hermi.jobs.JOB_LANES must match (a test checks it).
JOBS = (
    release_stale_reservations,
    maintain_partitions,
    purge_trash,
    send_email,
    send_predeparture_reminder,
    build_digest,
    send_trial_ending_reminder,
)
INFRA_TASKS = frozenset({reap_stale_jobs.NAME})


def build_app(settings: Settings) -> procrastinate.App:
    """Periodic schedules are registered only when SCHEDULER_ENABLED, so one process (the leader) defers them."""
    url = psycopg_url(settings.require("DATABASE_URL_SYSTEM"))
    app = procrastinate.App(connector=procrastinate.PsycopgConnector(conninfo=url))
    engine = make_engine(url, pool_size=2, max_overflow=2)
    app.sqlalchemy_engine = engine  # disposed by the runner at exit
    app.fairness_engine = fairness.install(app, url, pool_size=len(LANES))  # disposed by the runner at exit

    for mod in JOBS:
        assert JOB_LANES[mod.NAME] == mod.LANE, f"hermi.jobs.JOB_LANES disagrees with {mod.NAME}"

        def body(context: JobContext, timestamp: int | None = None, *, _mod=mod, **_args):
            # `timestamp` is the slot of a periodic run; other arguments are the caller's and the job body decides what it needs.
            with job_context(str(context.job.id)), Session(engine) as session:
                # A job that declares ARGS takes the settings and those named job arguments; the others take the session only.
                if hasattr(_mod, "ARGS"):
                    result = _mod.run(session, settings, **{k: _args[k] for k in _mod.ARGS})
                else:
                    result = _mod.run(session)
                session.commit()
                log.info("job done", extra={"job": _mod.NAME, "result": result})
                return result

        task = app.task(name=mod.NAME, queue=mod.LANE, retry=HermiRetry(mod.RETRIES), pass_context=True)(body)
        # The per-slot lock key of 02 section 5.2 is the unique (task, periodic_id, timestamp) row in procrastinate_periodic_defers.
        # The leader election and scheduler loop land in WF-051; until then SCHEDULER_ENABLED picks the one process that registers these.
        if settings.scheduler_enabled and mod.SCHEDULE:
            app.periodic_registry.register_task(task, cron=mod.SCHEDULE, periodic_id="", configure_kwargs={})

    async def reap(context: JobContext, timestamp: int | None = None) -> int:
        with job_context(str(context.job.id)):
            return await reap_stale_jobs.run(app)

    task = app.task(name=reap_stale_jobs.NAME, queue=reap_stale_jobs.LANE, pass_context=True)(reap)
    if settings.scheduler_enabled:
        app.periodic_registry.register_task(task, cron=reap_stale_jobs.SCHEDULE, periodic_id="", configure_kwargs={})
    return app


def concurrency(settings: Settings, lane: str) -> int:
    return getattr(settings, f"worker_concurrency_{lane}")


async def run_workers(app: procrastinate.App, settings: Settings, lanes: list[str], *, install_signals: bool = True) -> None:
    """One Procrastinate worker per lane, each with its own concurrency, until SIGTERM or SIGINT. On a signal the workers stop
    claiming, give running jobs up to 60 seconds, and unregister."""
    async with app.open_async():
        workers = [
            # shortcut: private Procrastinate API, because app.run_worker_async runs a single worker and we need one per lane
            # with its own concurrency. Ceiling: breaks on a Procrastinate bump past 3.10; re-check this call when upgrading.
            app._worker(
                queues=[lane],
                name=lane,
                concurrency=concurrency(settings, lane),
                install_signal_handlers=False,  # one handler for all lanes, below
                shutdown_graceful_timeout=60,
                update_heartbeat_interval=15,
                stalled_worker_timeout=max(reap_stale_jobs.STALE_SECONDS.values()),  # at start a worker prunes workers silent this long, so it never hides a job from the reaper's per-lane limit
            )
            for lane in lanes
        ]
        loop = asyncio.get_running_loop()

        def stop() -> None:
            for w in workers:
                w.stop()

        if install_signals:
            _on_signals(loop, stop)
        await asyncio.gather(*(w.run() for w in workers))


def _on_signals(loop: asyncio.AbstractEventLoop, stop) -> None:
    import signal

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop)
        except NotImplementedError:  # Windows: the loop has no signal API; Ctrl+C reaches us through signal.signal
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop))
