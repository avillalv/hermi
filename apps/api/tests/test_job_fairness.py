# ruff: noqa: E501, F811
"""WF-046.2: fair claim (least recently served account, per-account caps) and queue depth on health. Real PostgreSQL."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.test_job_queue import (  # noqa: F401  (fixtures)
    app,
    app_engine,
    clean_queue,
    run_async,
    settings,
)

from hermi import db, health, jobs
from hermi.config import load_settings
from hermi.main import create_app
from hermi_worker import fairness


def put(engine, n, account, plan="free", priority=0, name="purge_trash"):
    with Session(engine) as s:
        ids = [
            jobs.enqueue(s, name, priority=priority, account_id=account, plan=plan)
            for _ in range(n)
        ]
        s.commit()
    return ids


def claim_all(app, queue, n):
    async def go():
        got = []
        for _ in range(n):
            j = await app.job_manager.fetch_job(queues=[queue], worker_id=None)
            got.append(j and j.id)
        return got

    return run_async(go())


def finish(conn, job_id):
    conn.execute("UPDATE procrastinate_jobs SET status = 'succeeded' WHERE id = %s", (job_id,))


def test_a_busy_account_does_not_starve_another_account(app, app_engine, system_conn):
    busy = put(app_engine, 10, "A")
    (other,) = put(app_engine, 1, "B")
    first_two = claim_all(app, "batch", 2)
    assert first_two == [busy[0], other]  # B's only job is served second, not eleventh


def test_least_recently_served_account_goes_first_after_each_claim(app, app_engine, system_conn):
    a = put(app_engine, 6, "A", plan="plus")
    b = put(app_engine, 6, "B", plan="plus")
    got = claim_all(app, "batch", 6)
    assert got == [a[0], b[0], a[1], b[1], a[2], b[2]]


def test_per_account_cap_free_2_and_plus_4_and_a_finished_job_frees_a_slot(
    app, app_engine, system_conn
):
    free = put(app_engine, 5, "F", plan="free")
    got = claim_all(app, "batch", 3)
    assert got == [free[0], free[1], None]
    finish(system_conn, free[0])
    assert claim_all(app, "batch", 1) == [free[2]]

    system_conn.execute("DELETE FROM procrastinate_jobs")
    plus = put(app_engine, 6, "P", plan="plus")
    got = claim_all(app, "batch", 5)
    assert got == [*plus[:4], None]


def test_cap_holds_across_lanes_and_other_accounts_still_run(app, app_engine, system_conn):
    put(app_engine, 2, "A", name="release_stale_reservations")  # lane api, fills A's two slots
    (a_batch,) = put(app_engine, 1, "A")
    (b_batch,) = put(app_engine, 1, "B")
    assert len(claim_all(app, "api", 2)) == 2
    assert claim_all(app, "batch", 2) == [b_batch, None]
    assert system_conn.execute(
        "SELECT status::text FROM procrastinate_jobs WHERE id = %s", (a_batch,)
    ).fetchone() == ("todo",)


def test_priority_beats_fairness_and_jobs_without_an_account_are_never_capped(
    app, app_engine, system_conn
):
    low = put(app_engine, 1, "A", priority=1)
    high = put(app_engine, 1, "B", priority=10)
    assert claim_all(app, "batch", 2) == [high[0], low[0]]
    with Session(app_engine) as s:
        ids = [jobs.enqueue(s, "purge_trash") for _ in range(5)]
        s.commit()
    assert claim_all(app, "batch", 5) == ids


def test_enqueue_requires_a_known_plan_with_an_account(app_engine, clean_queue):
    import pytest

    with Session(app_engine) as s:
        for kw in ({"plan": "gold"}, {}):
            with pytest.raises(ValueError):
                jobs.enqueue(s, "purge_trash", account_id="A", **kw)


def test_claim_without_a_queue_filter_takes_any_lane(app, app_engine, system_conn):
    (j,) = put(app_engine, 1, "A")
    job = fairness.claim(app.fairness_engine, None, None)
    assert job and job.id == j


def test_the_claim_waits_for_the_advisory_lock_so_a_cap_cannot_be_overrun(
    app, app_engine, system_conn, db_urls
):
    import threading
    import time

    import psycopg

    put(app_engine, 1, "A")
    got = []
    with psycopg.connect(db.psycopg_url(db_urls["system"])) as holder:  # another claimer, mid-claim
        holder.execute("SELECT pg_advisory_xact_lock(%s)", (fairness._LOCK_KEY,))
        t = threading.Thread(
            target=lambda: got.append(fairness.claim(app.fairness_engine, ["batch"], None))
        )
        t.start()
        time.sleep(0.5)
        assert got == [] and t.is_alive()  # blocked on the lock, nothing claimed
        holder.commit()
    t.join(5)
    assert got and got[0] is not None


def test_concurrent_claims_never_exceed_the_cap(app, app_engine, system_conn):
    import threading

    put(app_engine, 8, "A", plan="free")
    barrier = threading.Barrier(6)
    got = []

    def go():
        barrier.wait()
        got.append(fairness.claim(app.fairness_engine, ["batch"], None))

    ts = [threading.Thread(target=go) for _ in range(6)]
    [t.start() for t in ts]
    [t.join(10) for t in ts]
    assert len([g for g in got if g]) == 2


# --- queue depth and oldest job age on health -----------------------------------------------------------------------


def test_queue_stats_reports_depth_and_oldest_age_per_lane(
    db_urls, app_engine, system_conn, clean_queue
):
    # read through the API's own login, which is what /health/queue uses
    stats = health.queue_stats(db_urls["app"])
    assert stats == {lane: {"depth": 0, "oldest_age_seconds": 0} for lane in jobs.LANES}
    (old,) = put(app_engine, 1, "A")
    put(app_engine, 2, "B")
    put(app_engine, 1, "C", name="release_stale_reservations")
    system_conn.execute(
        "UPDATE procrastinate_events SET at = now() - interval '90 seconds' WHERE job_id = %s",
        (old,),
    )
    stats = health.queue_stats(db_urls["app"])
    assert stats["batch"]["depth"] == 3
    assert 89 <= stats["batch"]["oldest_age_seconds"] <= 120
    assert stats["api"]["depth"] == 1
    assert stats["ai"] == {"depth": 0, "oldest_age_seconds": 0}
    # a running job and a job scheduled for later are not waiting
    system_conn.execute("UPDATE procrastinate_jobs SET status = 'doing' WHERE id = %s", (old,))
    system_conn.execute(
        "UPDATE procrastinate_jobs SET scheduled_at = now() + interval '1 hour' WHERE task_name = 'release_stale_reservations'"
    )
    stats = health.queue_stats(db_urls["app"])
    assert stats["batch"]["depth"] == 2 and stats["api"]["depth"] == 0


def test_health_queue_endpoint_and_ready_semantics_unchanged(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:s3cret@db/h")
    monkeypatch.setattr(health, "probe_db", lambda u: "abc")
    monkeypatch.setattr(health, "expected_head", lambda: "abc")
    stats = {lane: {"depth": 1, "oldest_age_seconds": 5} for lane in jobs.LANES}
    monkeypatch.setattr(health, "queue_stats", lambda url: stats)
    health._queue_cache.clear()
    c = TestClient(create_app(load_settings(bind_host="127.0.0.1")))
    assert c.get("/health/queue").json() == {"status": "ok", "lanes": stats}
    assert c.get("/health/ready").json() == {
        "status": "ok",
        "database": "ok",
        "migrations": "ok",
        "ai_provider": "fake",
    }

    def boom(url):
        raise RuntimeError("postgresql://u:s3cret@db")

    health._queue_cache.clear()
    calls = []
    monkeypatch.setattr(health, "queue_stats", lambda url: calls.append(1) or stats)
    c.get("/health/queue")
    c.get("/health/queue")
    assert len(calls) == 1  # cached
    health._queue_cache.clear()
    monkeypatch.setattr(health, "queue_stats", boom)
    r = c.get("/health/queue")
    assert r.status_code == 503 and r.json() == {"status": "fail"} and "s3cret" not in r.text
    assert c.get("/health/ready").status_code == 200  # a queue problem never fails readiness
