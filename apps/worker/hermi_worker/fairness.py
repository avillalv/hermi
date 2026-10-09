# ruff: noqa: E501
"""Fair claim (02 section 5): replaces Procrastinate's claim query on our own app object, with no schema change.

Order: priority first, then the account served least recently (a job with no account is served as if never served), then queue
order. An account runs at most `account_cap` jobs at once across all lanes (the cap rides in the job args, set by
hermi.jobs.enqueue). Jobs without an `account_id` arg are system jobs: never capped, ordered by priority then id.

The last-served time is the newest 'started' event of any job with the same account_id. The claim runs in one transaction under
an advisory lock so two workers cannot both take an account's last free slot. The lock key is fixed and claims are one short
statement, so the lock is held for milliseconds.

The last-served lookup only looks at events from the last hour; an account idle longer counts as never served.

shortcut: per claim, the ordering scans every waiting job and, for each, the account's started events of the last hour (joined to
jobs by id, no index on args->>'account_id'), all under one global lock. Cost grows with waiting jobs times events per account.
Ceiling: about 10k waiting jobs or claim latency above 50 ms. Upgrade trigger: oldest_age_seconds on /health/queue climbing while
workers are idle; then add a last-served table and an index on args->>'account_id'.
"""

import asyncio

from procrastinate.jobs import Job
from sqlalchemy import text
from sqlalchemy.engine import Engine

from hermi.db import make_engine

_LOCK_KEY = 4604046  # arbitrary, only this claim path takes it

_CLAIM = text("""
WITH candidate AS (
    SELECT jobs.*
      FROM procrastinate_jobs AS jobs
     WHERE jobs.status = 'todo'
       AND (CAST(:queues AS varchar[]) IS NULL OR jobs.queue_name = ANY(CAST(:queues AS varchar[])))
       AND (jobs.scheduled_at IS NULL OR jobs.scheduled_at <= now())
       -- the lock rule of procrastinate_fetch_job_v2: an earlier or higher priority job with the same lock goes first
       AND NOT EXISTS (
            SELECT 1 FROM procrastinate_jobs AS o
             WHERE jobs.lock IS NOT NULL AND o.lock = jobs.lock
               AND (o.status = 'doing'
                    OR (o.status = 'todo' AND (o.priority > jobs.priority OR (o.priority = jobs.priority AND o.id < jobs.id)))))
       -- the account cap
       AND (jobs.args->>'account_id' IS NULL OR (
            SELECT count(*) FROM procrastinate_jobs AS d
             WHERE d.status = 'doing' AND d.args->>'account_id' = jobs.args->>'account_id'
            ) < COALESCE((jobs.args->>'account_cap')::int, 2147483647))
     ORDER BY jobs.priority DESC,
              (SELECT max(e.at) FROM procrastinate_events AS e JOIN procrastinate_jobs AS s ON s.id = e.job_id
                WHERE e.type = 'started' AND e.at > now() - interval '1 hour' AND jobs.args->>'account_id' IS NOT NULL
                  AND s.args->>'account_id' = jobs.args->>'account_id') ASC NULLS FIRST,
              jobs.id ASC
     LIMIT 1
       FOR UPDATE OF jobs SKIP LOCKED
)
UPDATE procrastinate_jobs
   SET status = 'doing', worker_id = :worker_id
  FROM candidate
 WHERE procrastinate_jobs.id = candidate.id
RETURNING procrastinate_jobs.id, procrastinate_jobs.status, procrastinate_jobs.task_name, procrastinate_jobs.priority,
          procrastinate_jobs.lock, procrastinate_jobs.queueing_lock, procrastinate_jobs.args, procrastinate_jobs.scheduled_at,
          procrastinate_jobs.queue_name, procrastinate_jobs.attempts, procrastinate_jobs.worker_id
""")


def claim(engine: Engine, queues, worker_id: int | None) -> Job | None:
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})
        row = (
            conn.execute(
                _CLAIM, {"queues": None if queues is None else list(queues), "worker_id": worker_id}
            )
            .mappings()
            .first()
        )
    return Job.from_row(dict(row)) if row else None


def install(app, url: str, pool_size: int) -> Engine:
    """Make every worker of `app` use the fair claim. It gets its own engine, sized to one claim per lane at a time and never
    overflowing, so claims cannot take connections from the job bodies. The caller disposes it."""
    engine = make_engine(url, pool_size=pool_size, max_overflow=0)

    async def fetch_job(queues, worker_id):
        return await asyncio.to_thread(claim, engine, queues, worker_id)

    app.job_manager.fetch_job = fetch_job
    return engine
