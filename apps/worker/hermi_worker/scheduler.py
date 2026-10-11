# ruff: noqa: E501
"""The scheduler loop (02 section 5.2): leader election, the 30 second route scan, the periodic jobs and the heartbeat.

It enqueues work and never runs it. One process holds pg_try_advisory_lock(0x57415946) on a dedicated connection for as long
as it leads; standbys retry every 10 seconds. A dropped connection frees the lock and the next standby takes over. The
periodic cron jobs live in `app.scheduled_registry` (not the lane workers' own registry) and are deferred only while leading.
"""

import asyncio
import logging
import time

import httpx
import psycopg
from procrastinate.periodic import PeriodicDeferrer
from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.db import make_engine, psycopg_url
from hermi_worker.jobs import scan_due_routes

log = logging.getLogger(__name__)

LOCK_KEY = 0x57415946
SCAN_SECONDS = 30.0
RETRY_SECONDS = 10.0
HEARTBEAT_SECONDS = 60.0


class Election:
    """A dedicated autocommit connection that owns the advisory lock for the leader's lifetime."""

    def __init__(self, url: str):
        self.url = url
        self._conn: psycopg.Connection | None = None

    def try_acquire(self) -> bool:
        if self._conn is not None:
            return self.alive()
        conn = psycopg.connect(self.url, autocommit=True, connect_timeout=5)
        if conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0]:
            self._conn = conn
            return True
        conn.close()
        return False

    def alive(self) -> bool:
        """False once the connection is gone, which also means the lock is gone: leadership is dropped."""
        if self._conn is None:
            return False
        try:
            self._conn.execute("SELECT 1")
            return True
        except psycopg.Error:
            self.release()
            return False

    def release(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.close()  # closing the session frees the lock
            except psycopg.Error:
                pass


def leader_present(url: str) -> bool:
    """True when some session holds the scheduler lock. The heartbeat the health endpoint exposes; readable by any login."""
    with psycopg.connect(psycopg_url(url), connect_timeout=2) as conn:
        return conn.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype = 'advisory' AND granted AND classid = %s AND objid = %s AND objsubid = 1)",
            (LOCK_KEY >> 32, LOCK_KEY & 0xFFFFFFFF),
        ).fetchone()[0]


def _scan(engine) -> dict[str, int]:
    with Session(engine) as session:
        result = scan_due_routes.run(session)
        session.commit()
        return result


def _ping(url: str) -> None:
    try:
        httpx.get(url, timeout=5)
    except httpx.HTTPError:
        log.warning("scheduler heartbeat ping failed")


async def _sleep(stop: asyncio.Event, seconds: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except TimeoutError:
        pass


async def run(app, settings: Settings, stop: asyncio.Event, *, tick: float = SCAN_SECONDS, retry: float = RETRY_SECONDS) -> None:
    """Elect, then scan every `tick` seconds while leading. `app` must be open. Returns when `stop` is set."""
    url = psycopg_url(settings.require("DATABASE_URL_SYSTEM"))
    election = Election(url)
    engine = make_engine(url, pool_size=1, max_overflow=1)
    heartbeat = settings.betterstack_heartbeat_scheduler
    last_ping = 0.0
    try:
        while not stop.is_set():
            try:
                leading = await asyncio.to_thread(election.try_acquire)
            except psycopg.Error:
                log.warning("scheduler election failed, retrying")
                leading = False
            if not leading:
                await _sleep(stop, retry)
                continue
            log.info("scheduler leader elected")
            registry = getattr(app, "scheduled_registry", None)
            periodic = None
            try:
                if registry is not None and registry.periodic_tasks:
                    deferrer = PeriodicDeferrer(registry=registry, **app.periodic_defaults)
                    periodic = asyncio.create_task(deferrer.worker(), name="scheduled-deferrer")
            except Exception:  # periodic jobs are down until the next election; the route scan still runs
                log.exception("scheduled deferrer failed to start")
            try:
                while not stop.is_set() and await asyncio.to_thread(election.alive):
                    started = time.monotonic()
                    try:
                        result = await asyncio.to_thread(_scan, engine)
                        log.info("scheduler tick", extra={**result, "duration_ms": int((time.monotonic() - started) * 1000)})
                    except Exception:  # a bad tick must not end leadership; the next one retries
                        log.exception("scheduler tick failed")
                    if heartbeat and time.monotonic() - last_ping >= HEARTBEAT_SECONDS:
                        last_ping = time.monotonic()
                        await asyncio.to_thread(_ping, heartbeat.get_secret_value())
                    await _sleep(stop, tick)
            finally:
                if periodic is not None:
                    periodic.cancel()
                    (outcome,) = await asyncio.gather(periodic, return_exceptions=True)
                    if isinstance(outcome, Exception):
                        log.error("scheduled deferrer ended with an error", exc_info=outcome)
                await asyncio.to_thread(election.release)
                log.info("scheduler leadership ended")
    finally:
        engine.dispose()
