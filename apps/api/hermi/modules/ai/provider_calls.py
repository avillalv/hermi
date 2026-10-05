# ruff: noqa: E501
"""The provider_calls ledger writer (03 section 7.3). One row per outbound provider call, hit or miss.

Callers pass their own session so the row commits with their work. cost_usd_micros is None for a free or
unknown cost, and always None for provider = 'anthropic' (that cost lives in ai_usage).
"""

import hashlib
import logging
import time
import uuid
from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.providers import ProviderError

log = logging.getLogger(__name__)

_INSERT = text(
    """INSERT INTO provider_calls (provider, endpoint, user_id, trip_id, run_id, units, cost_usd_micros, cached,
         cache_layer, ok, status_code, latency_ms, request_hash)
       VALUES (:provider, :endpoint, :user_id, :trip_id, :run_id, :units, :cost_usd_micros, :cached,
         :cache_layer, :ok, :status_code, :latency_ms, :request_hash)"""
)


def request_hash(provider: str, endpoint: str, params: dict[str, object] | None = None) -> str:
    """The cache key shape (sha256 of provider, endpoint and sorted params), for dedup analytics."""
    parts = [provider, endpoint, *(f"{k}={params[k]}" for k in sorted(params or {}))]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def record_provider_call(
    session: Session,
    *,
    provider: str,
    endpoint: str,
    ok: bool,
    units: float = 1,
    cost_usd_micros: int | None = None,
    cached: bool = False,
    cache_layer: str | None = None,
    status_code: int | None = None,
    latency_ms: int | None = None,
    request_hash: str | None = None,
    user_id: uuid.UUID | None = None,
    trip_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
) -> None:
    session.execute(
        _INSERT,
        {
            "provider": provider,
            "endpoint": endpoint,
            "user_id": user_id,
            "trip_id": trip_id,
            "run_id": run_id,
            "units": units,
            "cost_usd_micros": cost_usd_micros,
            "cached": cached,
            "cache_layer": cache_layer,
            "ok": ok,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "request_hash": request_hash,
        },
    )


def metered[T](
    session: Session,
    provider: str,
    endpoint: str,
    call: Callable[[], T],
    *,
    params: dict[str, object] | None = None,
    **fixed: object,
) -> T:
    """Run a provider call, time it and record it (ok or failed), then return its result or re-raise.

    A success row joins the caller's transaction. A failure row is written in its own short transaction, so the
    caller's pending work is neither committed nor lost with a rollback, and a ledger fault never hides the error.
    """
    started = time.perf_counter()
    status: int | None = None
    ok = False
    try:
        result = call()
        ok, status = True, 200
        return result
    except ProviderError as exc:
        status = exc.status_code
        raise
    finally:
        row = {
            "provider": provider,
            "endpoint": endpoint,
            "ok": ok,
            "status_code": status,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "request_hash": request_hash(provider, endpoint, params),
        } | {k: v for k, v in fixed.items() if k not in {"ok", "status_code", "latency_ms", "request_hash"}}
        if ok:
            record_provider_call(session, **row)  # type: ignore[arg-type]
        else:
            try:
                with Session(bind=session.get_bind()) as own, own.begin():
                    record_provider_call(own, **row)  # type: ignore[arg-type]
            except Exception:
                log.warning("provider_calls failure row not written", exc_info=True)
