# ruff: noqa: E501  (long SQL strings and docstrings)
"""Guest AI (04 section 5.1, 10 section 2.4, WF-062.1): App Attest challenge and attestation, and the one guest AI route.

A guest has no token and no users row. The device's App Attest key is the identity: the challenge nonce is single use, the
attestation stores the key in `device_attestations`, and each `POST /guest/ai/draft-day` carries an assertion whose counter
must be higher than the stored one. Spend comes from `guest_allowances` through `spend_guest_allowance()`, never from
`credit_grants`. Nothing else is stored for the guest: no user, trip, run, usage or consent row.

Single-use state (challenge nonces, and the guest idempotency marker) lives in `rate_limit_counters`, which has no migration
cost: a nonce is a row with count 0 that its one consumer flips to 1, and `window_start` carries its expiry.
"""

import asyncio
import logging
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from hermi import db
from hermi.config import NotConfigured
from hermi.errors import ApiError
from hermi.modules.ai import client as ai_client
from hermi.modules.ai.features import drafts
from hermi.modules.ai.features.base import FAILED, flag_runtime, parse_output
from hermi.modules.credits import service as credit_service
from hermi.modules.notifications.waitlist import client_ip
from hermi.providers.ai.base import ProviderRefused
from hermi.security import attest, rate_limit

log = logging.getLogger("hermi.guest_ai")
router = APIRouter(tags=["guest"])

NONCE_MINUTES = 5
MAX_BODY = 1024 * 1024
ACTION = "draft_day"
Text300 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class AttestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key_id: Annotated[str, StringConstraints(min_length=1, max_length=256)]
    attestation: Annotated[str, StringConstraints(min_length=1, max_length=65536)]
    nonce: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class Challenge(BaseModel):
    nonce: str
    expires_at: str


class GuestDraftDayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ]
    day: date | None = None
    preferences: Text300 | None = None


def _invalid() -> ApiError:
    return ApiError(422, "attestation_invalid", "We could not check this device. Try again.")


def _unauthenticated() -> ApiError:
    return ApiError(401, "unauthenticated", "Sign in to keep going.")


def _unavailable() -> ApiError:
    return ApiError(503, "feature_disabled", "This is not available right now.")


def _guest_mode(request: Request) -> None:
    """The `guest_mode` flag (02 section 9) turns all three guest routes off together."""
    if not flag_runtime(request.app).evaluate("guest_mode"):
        raise _unavailable()


def _verifier(settings):
    try:
        return attest.verifier_for(settings)
    except NotConfigured as e:
        raise _unavailable() from e


# --- challenge and attestation ----------------------------------------------------------------------------------------


@router.post("/devices/attest/challenge", response_model=Challenge)
def challenge(request: Request) -> Challenge:
    _guest_mode(request)
    engine = request.app.state.engine
    rate_limit.hit(
        engine, "write_ip", client_ip(request)
    )  # shortcut: shares write_ip (600 a minute); give attestation its own class, with its seed row, if abuse shows it
    nonce = secrets.token_urlsafe(32)
    expires = datetime.now(UTC) + timedelta(minutes=NONCE_MINUTES)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO rate_limit_counters (bucket, window_start, count) VALUES (:b, :e, 0)"
            ),
            {"b": f"attest_nonce:{rate_limit.digest(nonce)}", "e": expires},
        )
    return Challenge(nonce=nonce, expires_at=expires.isoformat())


@router.post(
    "/devices/attest", status_code=204, responses={422: {"description": "attestation_invalid"}}
)
def attest_device(body: AttestIn, request: Request) -> None:
    _guest_mode(request)
    engine = request.app.state.engine
    settings = request.app.state.settings
    rate_limit.hit(
        engine, "write_ip", client_ip(request)
    )  # shortcut: shares write_ip (600 a minute); give attestation its own class, with its seed row, if abuse shows it
    verifier = _verifier(settings)
    with (
        engine.begin() as conn
    ):  # the nonce is spent whether or not the attestation verifies: one try per challenge
        spent = conn.execute(
            text(
                "UPDATE rate_limit_counters SET count = 1 WHERE bucket = :b AND count = 0 AND window_start > now() "
                "RETURNING 1"
            ),
            {"b": f"attest_nonce:{rate_limit.digest(body.nonce)}"},
        ).first()
    if spent is None:
        raise _invalid()
    try:
        key = verifier.verify_attestation(
            key_id=body.key_id, attestation=body.attestation, nonce=body.nonce
        )
    except attest.AttestError as e:
        raise _invalid() from e
    except NotConfigured as e:
        raise _unavailable() from e
    with db.system_session(
        "device_attest", settings=settings, route="POST /v1/devices/attest"
    ) as s:
        stored = s.execute(
            text(
                "INSERT INTO device_attestations (key_id, public_key, counter, environment) VALUES (:k, :p, 0, :e) "
                "ON CONFLICT (key_id) DO NOTHING RETURNING 1"
            ),
            {"k": body.key_id, "p": key.public_key, "e": key.environment},
        ).first()
    if stored is None:  # a key attests once; a second attestation would reset its counter
        raise _invalid()


# --- guest draft day --------------------------------------------------------------------------------------------------


def _paywall() -> dict:
    return {
        "reason": "credits",
        "offer_url": "/v1/paywall/offer?reason=credits",
        "free_path": "Create a free account to keep going, or plan the day yourself",
    }


def _authenticate(s, verifier, key_id: str, assertion: str, data: bytes) -> None:
    """Verify the assertion against the stored key and advance the counter in one conditional UPDATE: a replayed or
    lower counter updates no row and is 401, two requests with the same counter cannot both pass."""
    row = s.execute(
        text("SELECT public_key, counter FROM device_attestations WHERE key_id = :k"), {"k": key_id}
    ).first()
    if row is None:
        raise _unauthenticated()
    try:
        a = verifier.verify_assertion(
            key_id=key_id, public_key=bytes(row.public_key), assertion=assertion, client_data=data
        )
    except attest.AttestError as e:
        raise _unauthenticated() from e
    won = s.execute(
        text(
            "UPDATE device_attestations SET counter = :c WHERE key_id = :k AND counter < :c RETURNING 1"
        ),
        {"c": a.counter, "k": key_id},
    ).first()
    if won is None:
        raise _unauthenticated()


def _marker(key_id: str, idem: str) -> str:
    return f"guest_idem:{rate_limit.digest(key_id + '|' + idem)}"


@router.post("/guest/ai/draft-day")
async def guest_draft_day(request: Request) -> dict:
    h = request.headers
    key_id, assertion, idem = (
        h.get("x-attest-key-id"),
        h.get("x-attest-assertion"),
        h.get("idempotency-key"),
    )
    _guest_mode(request)
    flags = flag_runtime(request.app)
    # kill switches first: a paused feature must not move a counter or a credit. ai.free_tier covers guests (they are Free).
    keys = [drafts.DAY_SPEC.kill_key]
    if request.app.state.settings.ai_provider == "anthropic_api":
        keys.append("provider.anthropic")
    flags.ensure_paid_allowed(*keys, tier="free")
    if not key_id or not assertion or len(key_id) > 256 or len(assertion) > 65536:
        raise _unauthenticated()
    if idem is None:
        raise ApiError(400, "idempotency_key_required", "Send an Idempotency-Key header.")
    if not 8 <= len(idem) <= 128:
        raise RequestValidationError(
            [
                {
                    "loc": ("header", "Idempotency-Key"),
                    "type": "string_length",
                    "msg": "Use 8 to 128 characters.",
                }
            ]
        )
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise ApiError(413, "payload_too_large", "That request is too large.")
    return await run_in_threadpool(_run, request, key_id, assertion, idem, raw)


def _run(request: Request, key_id: str, assertion: str, idem: str, raw: bytes) -> dict:
    settings = request.app.state.settings
    engine = request.app.state.engine
    rate_limit.hit(engine, "write_ip", client_ip(request))
    verifier = _verifier(settings)
    spec = drafts.DAY_SPEC
    route = "POST /v1/guest/ai/draft-day"
    period = (
        ""  # the UTC month the credit was spent in, read from the database clock with the spend
    )
    marker = _marker(key_id, idem)
    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    with db.system_session(
        "guest_ai", settings=settings, route=route, caller=f"key:{rate_limit.digest(key_id)[:8]}"
    ) as s:
        _authenticate(s, verifier, key_id, assertion, attest.client_data(idem, raw))
        used_marker = s.execute(
            text(
                "INSERT INTO rate_limit_counters (bucket, window_start, count) VALUES (:b, :w, 1) ON CONFLICT DO NOTHING RETURNING 1"
            ),
            {"b": marker, "w": day_start},
        ).first()
        if used_marker is None:
            raise ApiError(
                409,
                "idempotency_key_reused",
                "That request was already handled. Start it again with a new key.",
            )
    try:
        try:
            body = GuestDraftDayIn.model_validate_json(raw)
        except ValidationError as e:
            raise RequestValidationError(e.errors()) from e
        rate_limit.hit(engine, "ai", f"guest:{key_id[:64]}")
        try:
            provider = ai_client.provider_for(settings, spec.call)
        except (NotConfigured, ProviderRefused) as e:
            raise _unavailable() from e
        with db.system_session("guest_ai", settings=settings, route=route) as s:
            price = credit_service.table_price(s, ACTION)
            limit = int(
                s.execute(
                    text("SELECT monthly_credits FROM plans WHERE code = 'free'")
                ).scalar_one()
            )
            ok = s.execute(
                text("SELECT spend_guest_allowance(:k, :n, :l)"),
                {"k": key_id, "n": price, "l": limit},
            ).scalar_one()
            period, used = s.execute(
                text(
                    "SELECT p.k, coalesce((SELECT credits_used FROM guest_allowances WHERE key_id = :k AND period_key = p.k), 0) "
                    "FROM (SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM') AS k) p"
                ),
                {"k": key_id},
            ).one()
            used = int(used)
        if not ok:
            raise ApiError(
                402,
                "insufficient_credits",
                "You have used this month's guest credits. Create a free account to keep going.",
                extra={
                    "credits": {"needed": price, "balance": max(limit - used, 0)},
                    "paywall": _paywall(),
                },
            )
    except BaseException:
        _release(settings, route, key_id, marker, 0, period, day_start)
        raise

    try:
        task, finish = drafts.guest_request(
            body.destination, body.day or datetime.now(UTC).date(), body.preferences
        )
        req = ai_client.build_request(settings, spec.call, task)
        output, failure = None, None
        try:
            result = asyncio.run(ai_client.single_call(provider, req))
        except Exception as e:  # SDK, network or provider error: log the type only, the text may carry request data
            log.warning("guest_ai_call_failed", extra={"error": type(e).__name__})
            result, failure = None, "provider_error"
        if result is not None:
            if result.model not in ai_client.allowed_models(settings, spec.call.tier):
                failure = "model_mismatch"
            elif result.stop_reason == "refusal":
                failure = "refused"
            elif result.cost_usd_micros >= spec.hard_stop_micros:
                failure = "spend_limit"
            elif result.stop_reason == "max_tokens":
                failure = "max_tokens"
            else:
                try:
                    output = finish(parse_output(drafts.DayOut, result))
                except ValueError:
                    failure = "invalid_output"
    except BaseException:
        _release(settings, route, key_id, marker, price, period, day_start)
        raise
    if failure is not None or output is None:
        _release(settings, route, key_id, marker, price, period, day_start)
        refused = failure == "refused"
        raise ApiError(422 if refused else 502, "ai_refused" if refused else "ai_failed", FAILED)
    log.info(
        "guest_ai_call",
        extra={
            "feature": spec.code,
            "model": result.model,
            "cost_usd_micros": result.cost_usd_micros,
            "stop_reason": result.stop_reason,
            "outcome": "ok",
        },
    )
    return {
        **output,
        "run_id": None,
        "credits": {
            "action": ACTION,
            "reserved": price,
            "charged": price,
            "from_cache": False,
            "balance_after": max(limit - used, 0),
            "reservation_id": None,
        },
    }


def _release(
    settings, route: str, key_id: str, marker: str, credits: int, period: str, day_start: datetime
) -> None:
    """Return the credit (when one was spent) and free the Idempotency-Key, so the guest can retry. Never raises."""
    try:
        with db.system_session("guest_ai", settings=settings, route=route) as s:
            if credits and period:
                s.execute(
                    text(
                        "UPDATE guest_allowances SET credits_used = greatest(credits_used - :n, 0) "
                        "WHERE key_id = :k AND period_key = :p"
                    ),
                    {"n": credits, "k": key_id, "p": period},
                )
            s.execute(
                text("DELETE FROM rate_limit_counters WHERE bucket = :b AND window_start = :w"),
                {"b": marker, "w": day_start},
            )
    except Exception as e:  # the daily sweep of rate_limit_counters is the backstop
        log.error("guest_ai_release_failed", extra={"error": type(e).__name__})


def count_against_free(settings, user_id, key_id: str | None) -> int:
    """F-ACC-2: what a device's guest AI spent this month counts against the account's Free monthly credits when the guest
    claims. Debits the caller's Free `monthly` grant by the key's `guest_allowances.credits_used` (read here, never from the
    client), capped at what the grant still holds, with an `adjust` ledger row keyed by key and month so one key is counted
    once. Runs on the guest_ai SystemSession: the app role cannot write grants. Returns the credits debited."""
    if not key_id:
        return 0
    with db.system_session(
        "guest_ai", settings=settings, route="POST /v1/me/claim", caller=str(user_id)
    ) as s:
        s.execute(text("SELECT ensure_free_monthly_grant(:u)"), {"u": user_id})
        taken = s.execute(
            text(
                "WITH p AS (SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM') AS k), "
                "g AS (SELECT id, remaining FROM credit_grants, p WHERE user_id = :u AND kind = 'monthly' AND period_key = p.k FOR UPDATE OF credit_grants), "
                "take AS (SELECT g.id, least(coalesce((SELECT credits_used FROM guest_allowances, p "
                "                                      WHERE key_id = :k AND period_key = p.k), 0), g.remaining) AS n FROM g), "
                "led AS (INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, idempotency_key, note) "
                "        SELECT :u, take.id, 'adjust', -take.n, 'guest_key:' || :k || ':' || (SELECT k FROM p), 'guest AI counted on claim' "
                "          FROM take WHERE take.n > 0 ON CONFLICT DO NOTHING RETURNING grant_id, -delta AS n) "
                "UPDATE credit_grants SET remaining = remaining - led.n FROM led WHERE credit_grants.id = led.grant_id RETURNING led.n"
            ),
            {"u": user_id, "k": key_id},
        ).scalar_one_or_none()
    return int(taken or 0)
