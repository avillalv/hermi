# ruff: noqa: E501
"""run_agent: lane ai, an event job carrying only `run_id` (02 section 5.1). Runs one fare hunt or deep research.

The job claims a `queued` run (anything else is skipped, so a retry or a duplicate never replays tool writes), marks it
`running`, drives hermi_worker.agents.loop.AgentLoop with the caps from credit_action_prices, writes `run_events` and the
per-response metering as it goes (each committed, so the SSE tail and a crash both see them), then settles exactly once:
the full reservation when something was saved, pro rata when the person stopped it, nothing otherwise (06 section 6.3).

What WF-049.2 plugs in: `handlers` (the evidence rules and the account scoped writes behind `submit_flight_quotes` and
`add_note`) and `build_task` (the run context). With the defaults a run saves nothing and is refunded.
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.config import NotConfigured, Settings
from hermi.modules.ai.metering import MeterContext, record_usage
from hermi.modules.credits import service
from hermi.providers import ProviderError
from hermi.providers.ai import FakeProvider, ProviderRefused, get_provider
from hermi.providers.ai.base import AiProvider, ProviderResult
from hermi.providers.ai.claude_cli import CliRunFailed
from hermi_worker.agents import prompts
from hermi_worker.agents.loop import AgentLoop, Hooks, RunOutcome
from hermi_worker.agents.spec import AgentSpec
from hermi_worker.agents.tools import Handler
from hermi_worker.retry import classify

NAME = "run_agent"
LANE = "ai"
SCHEDULE = None  # event job, no cron
RETRIES = 2  # transient only, and only before the first response: a started run is never replayed
ARGS = ("run_id",)
NEEDS_ATTEMPTS = True  # app.py passes `attempts` (earlier tries) so the last one can fail closed

HEARTBEAT_SECONDS = 15
FAKE_SCENARIO = "agent_finish"  # the recorded response the fake backend replays: finish_run, nothing saved

log = logging.getLogger(__name__)

TaskBuilder = Callable[[Session, "RunRow"], str]

_RUN = text(
    """SELECT r.status::text AS status, r.kind::text AS kind, r.user_id, r.trip_id, r.params, r.cancel_requested,
              t.name AS trip_name, u.email
         FROM runs r JOIN trips t ON t.id = r.trip_id LEFT JOIN users u ON u.id = r.user_id WHERE r.id = :id"""
)
_RESERVATION = text(
    """SELECT reservation_id, idempotency_key, -sum(delta) AS reserved FROM credit_ledger
        WHERE run_id = :id AND entry_type = 'reserve' GROUP BY reservation_id, idempotency_key LIMIT 1"""
)
_CAPS = text("SELECT hard_stop_micros, max_turns, max_searches, max_fetches FROM credit_action_prices WHERE action = 'agent_run'")
_NEXT_SEQ = text("SELECT coalesce(max(seq), 0) + 1 FROM run_events WHERE run_id = :id")
_EVENT = text(
    """INSERT INTO run_events (run_id, trip_id, seq, type, tool_name, summary, payload)
       VALUES (:id, :trip, :seq, :type, :tool, :summary, CAST(:payload AS jsonb))"""
)


class RunRow:
    """The run as the job read it. `params` carries the task: `task` (the RunContext JSON), `topic`, `instructions`."""

    def __init__(self, run_id: uuid.UUID, row) -> None:
        self.id, self.status, self.kind = run_id, row.status, row.kind
        self.user_id, self.trip_id, self.trip_name, self.email = row.user_id, row.trip_id, row.trip_name, row.email
        self.params = row.params if isinstance(row.params, dict) else json.loads(row.params or "{}")
        self.cancel_requested = row.cancel_requested


def default_task(session: Session, run: RunRow) -> str:
    """shortcut: the prompt from what the API stored in runs.params. Ceiling: it trusts that the admitting endpoint built
    the RunContext (route aliases, cheapest known fares). Trigger: WF-049.2 builds it from the database in context.py."""
    p = run.params
    spec = _spec(session, run.kind, "")
    return prompts.task_prompt(
        run.kind, trip_name=run.trip_name, task_json=json.dumps(p.get("task", {}), indent=2),
        today=datetime.now(UTC).date().isoformat(), run_short_id=str(run.id)[-8:],
        max_searches=spec.max_searches, max_fetches=spec.max_fetches,
        topic=p.get("topic"), instructions=p.get("instructions"),
    )  # fmt: skip


def _spec(session: Session, kind: str, model: str) -> AgentSpec:
    """The caps come from credit_action_prices so an admin edit takes effect at once; a missing row or a null column
    keeps the spec default."""
    caps = session.execute(_CAPS).one_or_none()
    limits = {}
    if caps:
        named = {"stop_micro": caps.hard_stop_micros, "max_turns": caps.max_turns, "max_searches": caps.max_searches, "max_fetches": caps.max_fetches}
        limits = {k: int(v) for k, v in named.items() if v is not None}
    return AgentSpec(model=model, system=prompts.SYSTEM, kind=kind, allowed_models=frozenset({model}) if model else frozenset(), **limits)


def _provider(settings: Settings, email: str | None) -> AiProvider:
    # The worker runs beside the API on the same machine: claude_cli passes its guard only for ENVIRONMENT=local, a
    # dev/allow-listed user and a loopback bind, and the factory re-checks all three here.
    p = get_provider(settings, email, bind_host="127.0.0.1")
    return FakeProvider(FAKE_SCENARIO) if isinstance(p, FakeProvider) else p


def _fail_closed(session: Session, run_id: uuid.UUID, res, code: str, emit) -> str:
    """The run could not start: close it and give the whole reservation back."""
    service.refund(session, res.reservation_id)
    session.execute(
        text(
            "UPDATE runs SET status = 'failed', finished_at = now(), failure_code = :c, error = :c, reservation_id = :r WHERE id = :id"
        ),
        {"c": code, "r": res.reservation_id, "id": run_id},
    )
    session.commit()
    emit("result", f"failed: {code}", {"status": "failed", "stop": "error", "accepted": 0, "credits_charged": 0, "failure_code": code})
    return f"failed:{code}"


def run(
    session: Session,
    settings: Settings,
    run_id: str,
    *,
    provider: AiProvider | None = None,
    handlers: dict[str, Handler] | None = None,
    build_task: TaskBuilder = default_task,
    poll_seconds: float = 1.0,
    attempts: int = 0,
) -> str:
    """Returns done:<status>, skipped:<status>, missing, or failed:<code>. Keyword arguments are for tests and WF-049.2."""
    rid = uuid.UUID(run_id)
    row = session.execute(_RUN, {"id": rid}).one_or_none()
    if row is None:
        return "missing"
    r = RunRow(rid, row)
    if r.status != "queued":
        return f"skipped:{r.status}"  # running means this is a replay or the reaper owns it; never run tools twice
    res = session.execute(_RESERVATION, {"id": rid}).one_or_none()
    if res is None:
        session.execute(
            text("UPDATE runs SET status = 'failed', finished_at = now(), failure_code = 'internal_error', error = 'no_reservation' WHERE id = :id"),
            {"id": rid},
        )
        session.commit()
        return "failed:no_reservation"
    reserved, key = int(res.reserved), res.idempotency_key
    if r.cancel_requested:  # stopped in the queue: nothing was used, nothing is charged
        service.settle_stopped_agent_run(session, res.reservation_id, turns_used=0, called_tools=False)
        session.execute(
            text("UPDATE runs SET status = 'cancelled', finished_at = now(), failure_code = 'cancelled', reservation_id = :r WHERE id = :id"),
            {"id": rid, "r": res.reservation_id},
        )
        session.commit()
        return "done:cancelled"

    def emit(type_: str, summary: str, payload: dict | None = None, tool_name: str | None = None) -> None:
        seq = session.execute(_NEXT_SEQ, {"id": rid}).scalar_one()
        session.execute(
            _EVENT,
            {"id": rid, "trip": r.trip_id, "seq": seq, "type": type_, "tool": tool_name, "summary": summary[:300], "payload": json.dumps(payload) if payload is not None else None},
        )
        session.commit()

    try:
        provider = provider or _provider(settings, r.email)
    except (NotConfigured, ProviderRefused):
        return _fail_closed(session, rid, res, "feature_disabled", emit)

    session.execute(
        text(
            "UPDATE runs SET status = 'running', started_at = now(), heartbeat_at = now(), worker_id = :w, reservation_id = :r, "
            "provider = :p, model = :m, prompt_version = :v WHERE id = :id"
        ),
        {"id": rid, "w": f"{LANE}:{uuid.uuid4().hex[:8]}", "r": res.reservation_id, "p": provider.name, "m": settings.ai_model_main, "v": prompts.PROMPT_VERSION},
    )
    session.commit()

    spec = _spec(session, r.kind, settings.ai_model_main)

    engine = session.get_bind()  # the cancel flag and heartbeat use their own short sessions: the CLI path polls from a thread
    beat = {"at": 0.0}

    def is_cancelled() -> bool:
        with Session(engine) as s, s.begin():
            if time.monotonic() - beat["at"] >= HEARTBEAT_SECONDS:
                beat["at"] = time.monotonic()
                s.execute(text("UPDATE runs SET heartbeat_at = now() WHERE id = :id"), {"id": rid})
            return bool(s.execute(text("SELECT cancel_requested FROM runs WHERE id = :id"), {"id": rid}).scalar())

    def on_response(turn: int, result: ProviderResult) -> None:
        ctx = MeterContext(
            action="agent_run", idempotency_key=key, provider=result.provider, model=result.model, user_id=r.user_id,
            trip_id=r.trip_id, run_id=rid, reservation_id=res.reservation_id,
        )  # fmt: skip
        record_usage(session, ctx, result.usage, cost_micros=result.cost_usd_micros, turn=turn, stop_reason=result.stop_reason,
                     stop_category=(result.stop_details or {}).get("category"))  # fmt: skip
        session.commit()

    loop = AgentLoop(
        provider, spec, handlers or {}, Hooks(is_cancelled=is_cancelled, emit=emit, on_response=on_response, poll_seconds=poll_seconds)
    )
    outcome: RunOutcome | None = None
    failure: str | None = None
    try:
        outcome = asyncio.run(loop.run(build_task(session, r)))
    except Exception as e:
        if classify(e) == "transient" and loop.turns == 0 and loop.exec.accepted == 0:
            session.rollback()
            if attempts < RETRIES:
                # nothing was sent or saved: put the run back and let Procrastinate retry it
                session.execute(text("UPDATE runs SET status = 'queued', started_at = NULL WHERE id = :id"), {"id": rid})
                session.commit()
                raise
            # the last attempt: no retry will come, so a `queued` row would lock the account (admission rule c)
            log.warning("run_agent_failed", extra={"run": str(rid), "error": type(e).__name__})
            return _fail_closed(session, rid, res, "provider_error", emit)
        session.rollback()
        failure = "provider_timeout" if isinstance(e, TimeoutError) else "provider_error"
        # a ProviderError message may carry request or page text: the type only, except the CLI's own mapped explanation
        detail = str(e)[:300] if isinstance(e, CliRunFailed) else None
        emit("error", type(e).__name__, {"kind": "provider_error", "detail": detail})
        log.warning("run_agent_failed", extra={"run": str(rid), "error": type(e).__name__})
        if not isinstance(e, ProviderError | TimeoutError | ConnectionError):
            # type only: an unexpected exception's message may carry page or request text
            log.error("run_agent_unexpected", extra={"run": str(rid), "error": type(e).__name__})

    saved = outcome.accepted if outcome else loop.exec.accepted
    if outcome is not None:
        status, code, stop = outcome.status, outcome.failure_code, outcome.stop
    else:  # an error after the first response keeps what was saved
        status, code, stop = ("partial", failure, "error") if saved else ("failed", failure, "error")
    turns = outcome.turns if outcome else loop.turns

    usage_id = session.execute(text("SELECT id FROM ai_usage WHERE idempotency_key = :k"), {"k": key}).scalar()
    if usage_id is not None:
        session.execute(text("UPDATE ai_usage SET credits_reserved = :n WHERE id = :i"), {"n": reserved, "i": usage_id})
    if status == "cancelled":
        charged = service.settle_stopped_agent_run(session, res.reservation_id, turns_used=turns, called_tools=turns > 0, usage_id=usage_id)
    elif saved > 0 and status in ("succeeded", "partial", "timed_out"):
        charged = reserved
        service.settle(session, res.reservation_id, reserved, usage_id)
    else:
        charged = 0
        service.refund(session, res.reservation_id, usage_id)

    report = {"report": loop.exec.report, "stop": stop, "searches": loop.searches, "fetches": loop.fetches, "credits_charged": charged}
    session.execute(
        text(
            "UPDATE runs SET status = CAST(:s AS run_status), finished_at = now(), turns_used = :t, searches_used = :se, fetches_used = :fe, "
            "accepted_count = :a, rejected_count = :rj, failure_code = :c, error = :c, summary = :sum, report = CAST(:rep AS jsonb), "
            "input_tokens = :i, output_tokens = :o WHERE id = :id"
        ),
        {
            "s": status, "t": turns, "se": loop.searches, "fe": loop.fetches, "a": saved, "rj": loop.exec.rejected, "c": code,
            "sum": ((loop.exec.report or {}).get("summary") or "")[:2000] or None, "rep": json.dumps(report),
            "i": loop.usage.input_tokens, "o": loop.usage.output_tokens, "id": rid,
        },
    )  # fmt: skip
    session.commit()
    emit("result", f"{status}: {stop}", {"status": status, "stop": stop, "accepted": saved, "credits_charged": charged})
    log.info("run_agent_done", extra={"run": str(rid), "status": status, "stop": stop, "turns": turns, "cost_usd_micros": loop.cost})
    return f"done:{status}"

