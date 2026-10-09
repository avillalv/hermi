# ruff: noqa: E501
"""reap_stale_jobs: infrastructure, not a catalogue job. Lane batch, every minute (02 section 5, 5.1).

Requeues jobs left in `doing` by a worker whose heartbeat is older than 2 minutes (5 for the ai lane). Workers heartbeat every 15 seconds.
A requeue counts as an attempt (Procrastinate adds one on retry). A job with no retry strategy, or one that has used its retries,
is finished as `failed` instead, so a job that keeps killing its worker cannot loop forever. The reaper itself has no retries:
the next minute covers it.
"""

import logging
from datetime import UTC, datetime, timedelta

from procrastinate.jobs import Status

from hermi_worker.retry import backoff_seconds

NAME = "reap_stale_jobs"
LANE = "batch"
SCHEDULE = "* * * * *"
STALE_SECONDS = {"ai": 300}
DEFAULT_STALE_SECONDS = 120

log = logging.getLogger(__name__)


async def run(app) -> int:
    """Returns the number of jobs requeued (jobs finished as failed are logged, not counted)."""
    job_manager = app.job_manager
    n = 0
    for lane in ("api", "ai", "notify", "batch"):
        seconds = STALE_SECONDS.get(lane, DEFAULT_STALE_SECONDS)
        for job in await job_manager.get_stalled_jobs(queue=lane, seconds_since_heartbeat=seconds):
            task = app.tasks.get(job.task_name)
            strategy = task.retry_strategy if task else None
            retries = getattr(strategy, "retries", None)
            extra = {"stale_job_id": job.id, "task": job.task_name, "lane": lane, "attempts": job.attempts}
            if retries is None or job.attempts >= retries:
                await job_manager.finish_job_by_id_async(job.id, status=Status.FAILED, delete_job=False)
                log.error("stale job out of retries, marked failed", extra=extra)
                continue
            retry_at = datetime.now(UTC) + timedelta(seconds=backoff_seconds(job.attempts))
            await job_manager.retry_job_by_id_async(job.id, retry_at)
            log.warning("requeued a stale job", extra=extra)
            n += 1
    return n
