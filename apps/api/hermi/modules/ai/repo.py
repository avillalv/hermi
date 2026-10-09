# ruff: noqa: E501  (long SQL strings)
"""SQL for AI runs (03 section 5.6). Runs as the API role: RLS applies and the caller must be able to edit the trip."""

import uuid

from psycopg import errors as pgerr
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermi.errors import ApiError

_ONE_ACTIVE_AGENT = "uq_runs_one_active_agent"

_INSERT_RUN = text(
    """INSERT INTO runs (trip_id, user_id, kind, action, params, prompt, model, provider, prompt_version)
       VALUES (:trip_id, :user_id, CAST(:kind AS run_kind), CAST(:action AS ai_action), CAST(:params AS jsonb),
               :prompt, :model, :provider, :prompt_version)
       RETURNING id"""
)


def admit_run(
    session: Session,
    *,
    trip_id: uuid.UUID,
    user_id: uuid.UUID,
    kind: str,
    action: str | None = None,
    params: str = "{}",
    prompt: str | None = None,
    model: str | None = None,
    provider: str = "anthropic_api",
    prompt_version: str | None = None,
) -> uuid.UUID:
    """Insert a queued run. The unique partial index uq_runs_one_active_agent is the admission lock: a second
    queued or running fare_hunt or deep_research for the account fails here, even under concurrency, and the API
    answers 409 run_already_active. The insert runs in a savepoint so the caller's transaction stays usable."""
    try:
        with session.begin_nested():
            return session.execute(
                _INSERT_RUN,
                {
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "kind": kind,
                    "action": action,
                    "params": params,
                    "prompt": prompt,
                    "model": model,
                    "provider": provider,
                    "prompt_version": prompt_version,
                },
            ).scalar_one()
    except IntegrityError as e:
        orig = e.orig
        if isinstance(orig, pgerr.UniqueViolation) and orig.diag.constraint_name == _ONE_ACTIVE_AGENT:
            active = session.execute(
                text(
                    "SELECT id FROM runs WHERE user_id = :u AND status IN ('queued', 'running') "
                    "AND kind IN ('fare_hunt', 'deep_research') ORDER BY queued_at LIMIT 1"
                ),
                {"u": user_id},
            ).scalar()
            raise ApiError(
                409,
                "run_already_active",
                "An agent run is already in progress. Wait for it to finish.",
                extra={"active_run_id": str(active) if active else None},
            ) from e
        raise
