# ruff: noqa: E501
"""Enqueue background jobs (02 section 5). The API names a job and its arguments; the worker package owns the code.

enqueue() writes the job row through the caller's own connection, so it commits or rolls back with the caller's transaction
(a budget reservation and its job stand or fall together). No module here imports the worker.
"""

import procrastinate
from procrastinate.sync_psycopg_connector import SyncPsycopgConnector
from sqlalchemy.orm import Session

LANES = ("api", "ai", "notify", "batch")

# Job name -> lane. Add a row when a job is registered in the worker; enqueue refuses a name that is not here.
JOB_LANES = {
    "release_stale_reservations": "api",
    "maintain_partitions": "batch",
    "purge_trash": "batch",
}

# The connector never opens a pool: every defer passes the caller's connection.
_app = procrastinate.App(connector=SyncPsycopgConnector())


def enqueue(
    session: Session,
    name: str,
    *,
    queueing_lock: str | None = None,
    lock: str | None = None,
    priority: int = 0,
    **args,
) -> int:
    """Defer job `name` inside the session's transaction. Returns the job id. Raises procrastinate AlreadyEnqueued when a job
    with the same queueing_lock is waiting."""
    deferrer = _app.configure_task(
        name,
        queue=JOB_LANES[name],
        queueing_lock=queueing_lock,
        lock=lock,
        priority=priority,
        connection=session.connection().connection.driver_connection,
    )
    return deferrer.defer(**args)
