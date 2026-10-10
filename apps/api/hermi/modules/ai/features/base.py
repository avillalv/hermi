# ruff: noqa: E501
"""The one-shot action engine (06 sections 3.3, 6.3 and 7): gate, admit, call, validate, meter, settle.

Admission runs as the caller (RLS): gate, ceiling check, credit reserve and the queued `runs` row, committed before the
call so a worker-level session can see the reservation. Everything after the call runs in a SystemSession ("ai_single_call"):
the app role may not write `ai_usage` or update `runs`. Exactly one settlement happens per action: the full price when the
output validated, a full refund for a refusal, a bad output, a spend stop, a wrong model or an error. Nothing is saved
by an action: the output is a preview labeled as a suggestion.
"""

import asyncio
import hashlib
import json
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import NotConfigured
from hermi.errors import ApiError
from hermi.modules.admin.flags import FlagRuntime, engine_loader
from hermi.modules.ai import client as ai_client
from hermi.modules.ai.client import CallSpec
from hermi.modules.ai.metering import MeterContext, record_usage
from hermi.modules.ai.policy import blocked_domain
from hermi.modules.ai.repo import admit_run
from hermi.modules.credits import budget, service
from hermi.providers.ai.base import AiProvider, ProviderRefused, ProviderResult

log = logging.getLogger("hermi.ai")

LABEL = "AI suggestion, check details before booking"  # 06 section 12.4
FAILED = "We could not do that one. Nothing was charged."
_URL = re.compile(r"https?://([^\s/\"')>]+)", re.IGNORECASE)


@dataclass(frozen=True)
class FeatureSpec:
    call: CallSpec
    action: str  # the credit action (ai_action) the price and hard stop come from
    run_kind: str  # runs.kind
    kill_key: str  # the feature's kill switch
    hard_stop_micros: int  # per call; explain, draft_day and draft_trip equal credit_action_prices
    prompt_version: str = "1"

    @property
    def code(self) -> str:
        return self.call.code


@dataclass(frozen=True)
class Receipt:
    action: str
    reserved: int
    charged: int
    balance_after: int | None
    reservation_id: uuid.UUID | None  # None on a free repeat: nothing was reserved
    from_cache: bool = False

    def public(self) -> dict[str, Any]:
        return {
            "action": self.action, "reserved": self.reserved, "charged": self.charged, "from_cache": self.from_cache,
            "balance_after": self.balance_after, "reservation_id": str(self.reservation_id) if self.reservation_id else None,
        }


@dataclass(frozen=True)
class Done:
    run_id: uuid.UUID
    output: Any  # validated, placeholders restored, shaped by the feature's `finish`
    receipt: Receipt


# --- gate ---------------------------------------------------------------------------------------------------------


def flag_runtime(app) -> FlagRuntime:
    """One per process, built on first use from the app engine (the API login can read both flag tables)."""
    rt = getattr(app.state, "flags", None)
    if rt is None:
        rt = app.state.flags = FlagRuntime(engine_loader(app.state.engine))
    return rt


def gate(
    session: Session, flags: FlagRuntime, spec: FeatureSpec, *, user_id: uuid.UUID, trip_id: uuid.UUID, provider: str
) -> None:
    """The `ai` gate (04 section 1.8): kill switches, consent and the trip toggle. All fail closed."""
    if flags.switch_engaged("ai.all") or flags.switch_engaged(spec.kill_key):  # before consent: a stop is a stop
        raise ApiError(503, "feature_disabled", "This is paused for a moment. Try again soon.")
    row = session.execute(
        text(
            "SELECT t.ai_enabled, coalesce(e.tier_code, 'free') AS tier, "
            " coalesce((SELECT c.granted FROM consents c WHERE c.user_id = :u AND c.kind = 'ai_processing' "
            "           ORDER BY c.created_at DESC, c.id DESC LIMIT 1), false) AS consent "
            "FROM trips t LEFT JOIN entitlements e ON e.user_id = :u AND (e.valid_until IS NULL OR e.valid_until > now()) "
            "WHERE t.id = :t"
        ),
        {"u": user_id, "t": trip_id},
    ).one()
    if not row.consent:
        raise ApiError(403, "ai_consent_required", "Allow AI processing to use this.")
    if not row.ai_enabled:
        raise ApiError(403, "ai_disabled_for_trip", "AI is turned off for this trip.")
    keys = [spec.kill_key]
    if provider == "anthropic_api":
        keys.append("provider.anthropic")
    flags.ensure_paid_allowed(*keys, user_id=user_id, tier=row.tier)


# --- output checks ------------------------------------------------------------------------------------------------


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)


def clean_output(payload: Any) -> None:
    """No partner links or blocked hosts in AI text (06 section 4.3 item 8, non-negotiable 3). Raises ValueError."""
    for s in _strings(payload):
        if "/go/" in s:
            raise ValueError("partner link in output")
        for m in _URL.finditer(s):
            if blocked_domain(m.group(1).split(":")[0]):
                raise ValueError("blocked host in output")


def parse_output(model: type[BaseModel], result: ProviderResult) -> BaseModel:
    """Fail closed: not JSON, not the schema, or a forbidden link is an invalid output. Raises ValueError."""
    try:
        data = json.loads(result.text)
        clean_output(data)
        return model.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError) as e:
        raise ValueError("invalid output") from e


def already_settled(api: Session, key: str) -> bool:
    """True when this idempotency key's reservation already settled or refunded (a retry must not call the provider again)."""
    return bool(
        api.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM credit_ledger r WHERE r.idempotency_key = :k AND r.entry_type = 'reserve' "
                " AND EXISTS (SELECT 1 FROM credit_ledger s WHERE s.reservation_id = r.reservation_id AND s.entry_type IN ('settle', 'refund')))"
            ),
            {"k": key},
        ).scalar_one()
    )


# --- the action ---------------------------------------------------------------------------------------------------


def run_action(
    api: Session,
    *,
    settings,
    flags: FlagRuntime,
    spec: FeatureSpec,
    user_id: uuid.UUID,
    trip_id: uuid.UUID,
    idempotency_key: str,
    task: str,
    out_model: type[BaseModel],
    finish: Callable[[Any], Any],
    route: str,
    items: int = 1,
    params: dict[str, Any] | None = None,
    provider: AiProvider | None = None,
    free: Callable[[Any], bool] | None = None,
    repeat: bool = False,
    repeat_hours: int = 6,
) -> Done:
    """`free` says a validated output is not charged (a recheck that could not read the page). `finish` runs on the validated output (restore names, check ids, shape the response) and raises ValueError to
    fail the action closed. `provider` is for tests (a stub); the product path takes it from AI_PROVIDER.
    `repeat` makes an identical request (same user, trip, action and input) within `repeat_hours` (6; the packing list 168) return the earlier output free
    (01 F-AI-1, F-AI-2): the output is kept in `runs.report` for that window and no credit is reserved."""
    try:
        provider = provider or ai_client.provider_for(settings, spec.call)
    except (NotConfigured, ProviderRefused) as e:  # no key or not allowed here: off, before any reservation
        raise ApiError(503, "feature_disabled", "This is not available right now.") from e
    gate(api, flags, spec, user_id=user_id, trip_id=trip_id, provider=provider.name)
    req = ai_client.build_request(settings, spec.call, task)
    key = f"{user_id}:{spec.code}:{idempotency_key}"
    # A retry on a key whose reservation already settled or refunded (the idempotency layer frees the key on a 5xx)
    # must not call the provider again: admit() would skip the ceiling check and settle() would be a no-op.
    if already_settled(api, key):
        raise ApiError(409, "idempotency_key_reused", "That request was already handled. Start it again with a new key.")
    if repeat:
        same = hashlib.sha256(task.encode()).hexdigest()
        params = {**(params or {}), "repeat": same}
        hit = api.execute(
            text(
                "SELECT id, report -> 'output' AS output FROM runs WHERE trip_id = :t AND user_id = :u AND kind = CAST(:k AS run_kind) "
                "AND status = 'succeeded' AND params ->> 'repeat' = :h AND report ? 'output' "
                "AND finished_at > now() - make_interval(hours => :w) ORDER BY finished_at DESC LIMIT 1"
            ),
            {"t": trip_id, "u": user_id, "k": spec.run_kind, "h": same, "w": repeat_hours},
        ).first()
        if hit is not None:
            left = int(api.execute(text("SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = :u"), {"u": user_id}).scalar_one())
            return Done(hit.id, hit.output, Receipt(spec.action, 0, 0, left, None, from_cache=True))
    run_id = admit_run(
        api, trip_id=trip_id, user_id=user_id, kind=spec.run_kind, action=spec.action, params=json.dumps(params or {}),
        model=req.model, provider=provider.name, prompt_version=spec.prompt_version,
    )
    res = budget.admit(api, user_id=user_id, trip_id=trip_id, action=spec.action, idempotency_key=key, run_id=run_id, items=items)
    api.commit()  # the reservation must be visible to the system session

    result: ProviderResult | None = None
    failure: str | None = None
    output: Any = None
    ratio: float | None = None
    charged = 0
    balance: int | None = None
    try:
        started = datetime.now(UTC)
        try:
            result = asyncio.run(ai_client.single_call(provider, req))
        except Exception as e:  # SDK, network or provider error: the text may carry request data, so log the type only
            log.warning("ai_call_failed", extra={"feature": spec.code, "error": type(e).__name__})
            failure = "provider_error"

        if result is not None:
            if result.model not in ai_client.allowed_models(settings, spec.call.tier):
                failure = "model_mismatch"
                log.error("ai_model_mismatch", extra={"feature": spec.code, "model": result.model})
            elif result.stop_reason == "refusal":
                failure = "refused"
            elif result.cost_usd_micros >= spec.hard_stop_micros:
                failure = "spend_limit"
            elif result.stop_reason == "max_tokens":
                failure = "max_tokens"
            else:
                try:
                    output = finish(parse_output(out_model, result))
                except ValueError:
                    failure = "invalid_output"

        ratio = ai_client.cache_read_ratio(result) if result else None
        with db.system_session("ai_single_call", settings=settings, route=route, caller=str(user_id)) as sys:
            usage_id = None
            if result is not None:
                ctx = MeterContext(
                    action=spec.action, idempotency_key=key, provider=result.provider, model=result.model, user_id=user_id,
                    trip_id=trip_id, run_id=run_id, reservation_id=res.id,
                )
                record_usage(
                    sys, ctx, result.usage, cost_micros=result.cost_usd_micros, stop_reason=result.stop_reason,
                    stop_category=(result.stop_details or {}).get("category"),
                )
                usage_id = sys.execute(text("SELECT id FROM ai_usage WHERE idempotency_key = :k"), {"k": key}).scalar_one()
                sys.execute(text("UPDATE ai_usage SET credits_reserved = :n WHERE id = :i"), {"n": res.amount, "i": usage_id})
            charged = res.amount if failure is None and not (free and free(output)) else 0
            service.settle(sys, res.id, charged, usage_id)
            report = {"cache_read_ratio": ratio, "label": LABEL if failure is None else None}
            if repeat and failure is None:
                report["output"] = output
            sys.execute(
                text(
                    "UPDATE runs SET status = CAST(:s AS run_status), started_at = :st, finished_at = now(), turns_used = 1, "
                    "failure_code = :f, error = :f, reservation_id = :r, report = CAST(:rep AS jsonb), model = :m, "
                    "input_tokens = :i, output_tokens = :o WHERE id = :id"
                ),
                {
                    "s": "succeeded" if failure is None else "failed", "st": started, "f": failure, "r": res.id,
                    "rep": json.dumps(report), "m": result.model if result else req.model, "id": run_id,
                    "i": result.usage.input_tokens if result else None, "o": result.usage.output_tokens if result else None,
                },
            )
            balance = int(
                sys.execute(text("SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = :u"), {"u": user_id}).scalar_one()
            )
    except BaseException:
        _abort(settings, route, user_id, res.id, run_id)
        raise
    if result is not None:
        log.info(
            "ai_call",
            extra={
                "feature": spec.code, "model": result.model, "provider": result.provider, "cache_read_ratio": ratio,
                "cost_usd_micros": result.cost_usd_micros, "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens, "cache_read_tokens": result.usage.cache_read_tokens,
                "outcome": failure or "ok",
            },
        )
    if failure is not None or output is None:
        refused = failure == "refused"
        raise ApiError(422 if refused else 502, "ai_refused" if refused else "ai_failed", FAILED, extra={"run_id": str(run_id)})
    return Done(run_id, output, Receipt(spec.action, res.amount, charged, balance, res.id))


def _abort(settings, route: str, user_id: uuid.UUID, reservation_id: uuid.UUID, run_id: uuid.UUID) -> None:
    """Anything unexpected after the reservation committed: release it in full and close the run, so nothing waits
    for the 30 minute sweeper. Settle is idempotent, so this is safe when the main path already settled."""
    try:
        with db.system_session("ai_single_call", settings=settings, route=route, caller=str(user_id)) as sys:
            service.settle(sys, reservation_id, 0, None)
            sys.execute(
                text("UPDATE runs SET status = 'failed', finished_at = now(), failure_code = 'internal_error', error = 'internal_error' WHERE id = :id AND status = 'queued'"),
                {"id": run_id},
            )
    except Exception as e:  # the sweeper is the backstop
        log.error("ai_abort_failed", extra={"error": type(e).__name__})
