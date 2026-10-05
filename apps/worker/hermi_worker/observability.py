"""Logging and Sentry for the worker process. The runtime ticket calls start() once at boot and
wraps each job in job_context()."""

from contextlib import contextmanager

import sentry_sdk

from hermi.config import Settings
from hermi.logging_setup import bind, clear_context, setup_logging
from hermi.sentry_setup import init_sentry


def start(settings: Settings) -> bool:
    setup_logging(
        settings.log_level,
        service="worker",
        env=settings.environment,
        release=settings.release_sha,
    )
    return init_sentry(
        settings.sentry_dsn, release=settings.release_sha, environment=settings.environment
    )


@contextmanager
def job_context(job_id: str, run_id: str | None = None):
    clear_context()
    bind(job_id=job_id, run_id=run_id)
    try:
        with sentry_sdk.isolation_scope() as scope:
            scope.set_tag("job_id", job_id)
            if run_id:
                scope.set_tag("run_id", run_id)
            yield
    finally:
        clear_context()
