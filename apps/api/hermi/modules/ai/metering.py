# ruff: noqa: E501  (long SQL strings)
"""Provider-neutral AI metering (06 sections 1 and 6.2).

record_usage adds a response's tokens and cost to the action's ai_usage row (one row per metered action, unique
idempotency_key) and to runs.cost_usd_micros, and writes a run_events 'info' row with payload.kind = 'usage', all in
the caller's session. Nothing here commits: if any statement fails the caller's transaction rolls back, so there is
never a usage row without its event. Runs as the worker login. A replayed response is not deduplicated here; the
caller meters each response once.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.modules.ai.pricing import model_price, price_version
from hermi.modules.ai.provider_calls import record_provider_call


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_5m_tokens: int = 0
    cache_write_1h_tokens: int = 0
    web_searches: int = 0

    @property
    def cache_write_tokens(self) -> int:
        return self.cache_write_5m_tokens + self.cache_write_1h_tokens


def _get(o: object, name: str) -> object:
    return o.get(name) if isinstance(o, dict) else getattr(o, name, None)


def _n(o: object, name: str) -> int:
    return int(_get(o, name) or 0)  # type: ignore[call-overload]


def usage_from_response(usage: object) -> Usage:
    """Read an Anthropic `response.usage` (object or dict). Missing parts count as 0; a flat
    cache_creation_input_tokens with no split is a 5-minute write."""
    cc = _get(usage, "cache_creation")
    if cc is not None:
        w5, w1 = _n(cc, "ephemeral_5m_input_tokens"), _n(cc, "ephemeral_1h_input_tokens")
    else:
        w5, w1 = _n(usage, "cache_creation_input_tokens"), 0
    stu = _get(usage, "server_tool_use")
    return Usage(
        input_tokens=_n(usage, "input_tokens"),
        output_tokens=_n(usage, "output_tokens"),
        cache_read_tokens=_n(usage, "cache_read_input_tokens"),
        cache_write_5m_tokens=w5,
        cache_write_1h_tokens=w1,
        web_searches=_n(stu, "web_search_requests") if stu is not None else 0,
    )


def cost_usd_micros(usage: Usage, model: str, batch: bool = False, on: date | None = None) -> int:
    """anthropic_api cost in micro-dollars, rounded half up. Batch discounts tokens only; searches are full price."""
    p, v = model_price(model, on), price_version(on)
    numerator = (  # micro-dollars times tokens
        usage.input_tokens * p.input
        + usage.cache_write_5m_tokens * p.write_5m
        + usage.cache_write_1h_tokens * p.write_1h
        + usage.cache_read_tokens * p.read
        + usage.output_tokens * p.output
    )
    den = 1_000_000
    if batch:
        numerator *= v.batch_num
        den *= v.batch_den
    return (2 * numerator + den) // (2 * den) + usage.web_searches * v.web_search_micros


def cli_cost_micros(total_cost_usd: float) -> int:
    """claude_cli: the stream's total_cost_usd in micro-dollars. Notional (a subscription pays)."""
    return round(total_cost_usd * 1_000_000)


@dataclass(frozen=True)
class MeterContext:
    action: str  # an ai_action value
    idempotency_key: str
    provider: str = "anthropic_api"  # anthropic_api, claude_cli or fake
    model: str | None = None
    user_id: uuid.UUID | None = None
    trip_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    reservation_id: uuid.UUID | None = None
    via_batch: bool = False
    purpose: str | None = None  # platform work only
    cache_hit: bool = False  # served from shared_research_cache (06 section 6.3 item 8)


_UPSERT_USAGE = text(
    """INSERT INTO ai_usage (user_id, trip_id, run_id, action, model, provider, input_tokens, output_tokens,
         cache_read_tokens, cache_write_tokens, web_searches, via_batch, cost_usd_micros, reservation_id,
         idempotency_key, purpose, cache_hit)
       VALUES (:user_id, :trip_id, :run_id, CAST(:action AS ai_action), :model, :provider, :input, :output, :read,
         :write, :searches, :batch, :cost, :reservation_id, :key, :purpose, :cache_hit)
       ON CONFLICT (idempotency_key) DO UPDATE SET
         input_tokens = ai_usage.input_tokens + EXCLUDED.input_tokens,
         output_tokens = ai_usage.output_tokens + EXCLUDED.output_tokens,
         cache_read_tokens = ai_usage.cache_read_tokens + EXCLUDED.cache_read_tokens,
         cache_write_tokens = ai_usage.cache_write_tokens + EXCLUDED.cache_write_tokens,
         web_searches = ai_usage.web_searches + EXCLUDED.web_searches,
         cost_usd_micros = ai_usage.cost_usd_micros + EXCLUDED.cost_usd_micros"""
)
_BUMP_RUN = text("UPDATE runs SET cost_usd_micros = cost_usd_micros + :cost WHERE id = :run_id RETURNING trip_id")
_NEXT_SEQ = text("SELECT coalesce(max(seq), 0) + 1 FROM run_events WHERE run_id = :run_id")
_INSERT_EVENT = text(
    """INSERT INTO run_events (run_id, trip_id, seq, type, summary, payload)
       VALUES (:run_id, :trip_id, :seq, 'info', 'usage', CAST(:payload AS jsonb))"""
)


def record_usage(
    session: Session,
    ctx: MeterContext,
    usage: Usage,
    *,
    cost_micros: int | None = None,
    request_id: str | None = None,
    turn: int | None = None,
    stop_reason: str | None = None,
    stop_category: str | None = None,
) -> int:
    """Meter one response and return its cost in micro-dollars. `cost_micros` overrides the token calculation
    (claude_cli reports its own cost; fake is free). With a run_id it also bumps runs.cost_usd_micros and writes
    the usage event."""
    if cost_micros is None:
        if ctx.provider == "claude_cli":
            raise ValueError("claude_cli has no price table: pass cost_micros (cli_cost_micros(total_cost_usd))")
        cost_micros = cost_usd_micros(usage, ctx.model or "", ctx.via_batch) if ctx.provider == "anthropic_api" else 0
    session.execute(
        _UPSERT_USAGE,
        {
            "user_id": ctx.user_id, "trip_id": ctx.trip_id, "run_id": ctx.run_id, "action": ctx.action,
            "model": ctx.model, "provider": ctx.provider, "input": usage.input_tokens, "output": usage.output_tokens,
            "read": usage.cache_read_tokens, "write": usage.cache_write_tokens, "searches": usage.web_searches,
            "batch": ctx.via_batch, "cost": cost_micros, "reservation_id": ctx.reservation_id,
            "key": ctx.idempotency_key, "purpose": ctx.purpose, "cache_hit": ctx.cache_hit,
        },
    )
    if ctx.run_id is not None:
        # The runs UPDATE also locks the row, so concurrent writers get distinct event seq numbers.
        run_trip = session.execute(_BUMP_RUN, {"cost": cost_micros, "run_id": ctx.run_id}).scalar_one()
        seq = session.execute(_NEXT_SEQ, {"run_id": ctx.run_id}).scalar_one()
        payload = {
            "kind": "usage", "request_id": request_id, "turn": turn, "provider": ctx.provider, "model": ctx.model,
            "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
            "cache_read_tokens": usage.cache_read_tokens, "cache_write_5m_tokens": usage.cache_write_5m_tokens,
            "cache_write_1h_tokens": usage.cache_write_1h_tokens, "web_searches": usage.web_searches,
            "via_batch": ctx.via_batch, "cost_usd_micros": cost_micros, "stop_reason": stop_reason,
            "stop_category": stop_category,
        }
        session.execute(_INSERT_EVENT, {"run_id": ctx.run_id, "trip_id": run_trip, "seq": seq, "payload": json.dumps(payload)})
    return cost_micros


def record_provider_spend(
    session: Session,
    provider: str,
    endpoint: str,
    *,
    ok: bool = True,
    cached: bool = False,
    units: float = 1,
    user_id: uuid.UUID | None = None,
    trip_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    cache_layer: str | None = None,
    status_code: int | None = None,
    latency_ms: int | None = None,
    request_hash: str | None = None,
) -> int | None:
    """Write a provider_calls row for a paid non-LLM provider (SerpApi, Geoapify) at the price constant, attributed
    to the account and trip. A failed or cached call costs nothing, stored as null (03 section 7.3). Returns the
    cost in micro-dollars, or None."""
    unit = price_version().provider_call_micros[provider]
    cost = round(unit * units) if ok and not cached else None
    record_provider_call(
        session, provider=provider, endpoint=endpoint, ok=ok, units=units, cost_usd_micros=cost, cached=cached,
        user_id=user_id, trip_id=trip_id, run_id=run_id, cache_layer=cache_layer, status_code=status_code,
        latency_ms=latency_ms, request_hash=request_hash,
    )
    return cost
