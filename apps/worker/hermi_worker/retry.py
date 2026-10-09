# ruff: noqa: E501
"""Retry classes and the Procrastinate retry strategy (02 section 5).

transient: 429, 5xx, timeouts, connection errors. Backoff 30 s * 2^attempt with jitter, capped at 15 minutes, never sooner than Retry-After.
permanent: other 4xx, validation, budget exhausted, consent missing. No retry. A job with no retries (class none) never reaches here.
"""

import asyncio
import random
from typing import Literal

import procrastinate.exceptions
import psycopg
from procrastinate.retry import BaseRetryStrategy, RetryDecision

from hermi.errors import ApiError

BASE_SECONDS = 30
FACTOR = 2
CAP_SECONDS = 15 * 60

Kind = Literal["transient", "permanent"]


def classify(exc: BaseException) -> Kind:
    """Status codes first (ProviderError.status_code, ApiError.status), then the exception type. An unknown error is permanent:
    a bug fails once and shows in the dead letters instead of repeating."""
    status = getattr(exc, "status_code", None)
    if status is None and isinstance(exc, ApiError):
        status = exc.status
    if isinstance(status, int):
        return "transient" if status == 429 or status >= 500 else "permanent"
    # A cancelled or aborted job was cut off (shutdown, abort request), not wrong, so it runs again.
    transient = (TimeoutError, ConnectionError, psycopg.OperationalError, asyncio.CancelledError, procrastinate.exceptions.JobAborted)
    if isinstance(exc, transient):
        return "transient"
    return "permanent"


def backoff_seconds(attempts: int, retry_after: float | None = None, rng=random.random) -> float:
    """attempts is the number of earlier tries (0 on the first failure). Jitter keeps 50 to 100 percent of the step."""
    step = min(CAP_SECONDS, BASE_SECONDS * FACTOR**attempts)
    wait = step * (0.5 + rng() / 2)
    return max(wait, retry_after or 0)


class HermiRetry(BaseRetryStrategy):
    """`retries` is the x3 or x5 of the job catalogue: the number of retries after the first run."""

    def __init__(self, retries: int, rng=random.random) -> None:
        self.retries, self.rng = retries, rng

    def get_retry_decision(self, *, exception, job):
        if job.attempts >= self.retries or classify(exception) != "transient":
            return None  # the job ends `failed`: the dead letter state
        retry_after = getattr(exception, "retry_after", None)
        return RetryDecision(retry_in={"seconds": backoff_seconds(job.attempts, retry_after, self.rng)})
