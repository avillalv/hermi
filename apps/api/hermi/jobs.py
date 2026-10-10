# ruff: noqa: E501
"""Enqueue background jobs (02 section 5). The API names a job and its arguments; the worker package owns the code.

enqueue() writes the job row through the caller's own connection, so it commits or rolls back with the caller's transaction
(a budget reservation and its job stand or fall together). No module here imports the worker.
"""

from datetime import datetime

import procrastinate
from procrastinate.sync_psycopg_connector import SyncPsycopgConnector
from sqlalchemy.orm import Session

LANES = ("api", "ai", "notify", "batch")

# Job name -> lane. Add a row when a job is registered in the worker; enqueue refuses a name that is not here.
JOB_LANES = {
    "release_stale_reservations": "api",
    "maintain_partitions": "batch",
    "purge_trash": "batch",
    "send_email": "notify",
    "send_predeparture_reminder": "notify",
    "build_digest": "notify",
    "send_trial_ending_reminder": "notify",
    "run_agent": "ai",
}

# Priorities and per-account concurrency caps (02 section 5, "Fair claim"). The worker claims by priority (interactive 10, paid live-route checks 5, free cached-fare
# refreshes 1, passed by the caller), then least recently served account, and never runs more than the job's account_cap jobs of one account at once (hermi_worker.fairness).
ACCOUNT_CAPS = {"free": 2, "plus": 4}

# The connector never opens a pool: every defer passes the caller's connection.
_app = procrastinate.App(connector=SyncPsycopgConnector())


def enqueue(
    session: Session,
    name: str,
    *,
    queueing_lock: str | None = None,
    lock: str | None = None,
    priority: int = 0,
    account_id: str | None = None,
    plan: str | None = None,
    schedule_at: datetime | None = None,
    **args,
) -> int:
    """Defer job `name` inside the session's transaction. Returns the job id. Raises procrastinate AlreadyEnqueued when a job
    with the same queueing_lock is waiting. A job for a user's account passes account_id and the account's plan ("free" or
    "plus"): they ride in the job args as account_id and account_cap, which the fair claim reads. Jobs without account_id
    (system jobs) are never capped."""
    if account_id is not None:
        if plan not in ACCOUNT_CAPS:
            raise ValueError(f"plan must be one of {sorted(ACCOUNT_CAPS)} when account_id is given")
        args.update(account_id=str(account_id), account_cap=ACCOUNT_CAPS[plan])
    deferrer = _app.configure_task(
        name,
        queue=JOB_LANES[name],
        queueing_lock=queueing_lock,
        lock=lock,
        priority=priority,
        schedule_at=schedule_at,
        connection=session.connection().connection.driver_connection,
    )
    return deferrer.defer(**args)
