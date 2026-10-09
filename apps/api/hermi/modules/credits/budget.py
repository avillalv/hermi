# ruff: noqa: E501  (long SQL strings)
"""Provider-spend ceilings and admission (WF-045; 03 section 7.4, 06 sections 6.4 and 6.5). Nothing here commits.

`admit` is the one entry point for a paid action: it takes the per-account advisory lock (and the trip's second when a Trip
Pass is active), counts spend under that lock, refuses with 429 provider_budget_exhausted when the ceiling is hit, and only
then reserves credits. The lock is released at COMMIT, after the reserve, so two parallel starts cannot both pass on the
same headroom. Ceilings are read from `plans.limits` on every call (`monthly_ceiling_micros`, `daily_ceiling_micros`), so an
admin edit applies at once. Anything unreadable refuses (503 ai_unavailable): paid work fails closed. Cached data is never
checked here: a read that spends no provider money does not call this module.

Spend is settled cost plus the hard stop of every open reservation, for the UTC calendar month and day. An open reservation
is its `ai_usage` row in state `reserved`, or, when no usage row exists yet, its open `credit_ledger` reserve rows. The Trip Pass
sum covers every member, so an API session calls the definer function `trip_pass_spend_micros` (migration 0024), as it calls
`my_provider_spend_micros` for provider cost; a worker session reads the tables. Purchased credits spent this month raise the
account's monthly ceiling by 20,000 each; no other credit does.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from hermi.errors import ApiError
from hermi.modules.credits import service

DAY_EXEMPT = {"agent_run", "verify_plan"}  # admitted on month headroom alone; their spend still counts toward the day
_PAUSED = "Saved data and cached fares still work."

_PASS_FUNDED = """NOT EXISTS (SELECT 1 FROM trip_passes p WHERE p.trip_id = {t} AND p.status = 'active'
                        AND {c} >= p.starts_at AND {c} < p.expires_at)"""
_SPEND = """
SELECT coalesce(sum(micros), 0)::bigint, coalesce(sum(micros) FILTER (WHERE created_at >= :ds), 0)::bigint FROM (
  SELECT u.created_at,
         CASE WHEN u.state = 'reserved'
              THEN GREATEST(u.cost_usd_micros, cap.hard_stop_micros * CASE WHEN u.action = 'verify_plan' THEN u.credits_reserved ELSE 1 END)
              ELSE u.cost_usd_micros END AS micros
    FROM ai_usage u JOIN credit_action_prices cap ON cap.action = u.action
   WHERE {usage} AND u.state <> 'released' AND u.created_at >= :ms
     AND NOT EXISTS (SELECT 1 FROM credit_ledger l JOIN credit_grants g ON g.id = l.grant_id
                      WHERE l.reservation_id = u.reservation_id AND g.period_key = 'taster')
  UNION ALL
  SELECT o.created_at, cap.hard_stop_micros * CASE WHEN o.action = 'verify_plan' THEN o.credits ELSE 1 END
    FROM (SELECT l.reservation_id, min(l.created_at) AS created_at, (array_agg(l.action))[1] AS action, (array_agg(l.trip_id))[1] AS trip_id,
                 sum(-l.delta) AS credits, coalesce(bool_or(g.period_key = 'taster'), false) AS taster
            FROM credit_ledger l LEFT JOIN credit_grants g ON g.id = l.grant_id
           WHERE {ledger} AND l.entry_type = 'reserve' AND l.created_at >= :ms
             AND NOT EXISTS (SELECT 1 FROM credit_ledger s WHERE s.reservation_id = l.reservation_id AND s.entry_type = 'settle')
             AND NOT EXISTS (SELECT 1 FROM ai_usage a WHERE a.reservation_id = l.reservation_id)
           GROUP BY l.reservation_id) o
    JOIN credit_action_prices cap ON cap.action = o.action
   WHERE NOT o.taster {o_pass}
) s"""
_ACTOR = _SPEND.format(
    usage="u.user_id = :u AND " + _PASS_FUNDED.format(t="u.trip_id", c="u.created_at"),
    ledger="l.user_id = :u",
    o_pass="AND " + _PASS_FUNDED.format(t="o.trip_id", c="o.created_at"),
)
_IN_WINDOW = "EXISTS (SELECT 1 FROM trip_passes p WHERE p.trip_id = :t AND p.status = 'active' AND {c} >= p.starts_at AND {c} < p.expires_at)"
_PASS = _SPEND.format(  # the worker's copy of trip_pass_spend_micros (migration 0024), which the API role calls instead
    usage="u.trip_id = :t AND " + _IN_WINDOW.format(c="u.created_at"), ledger="l.trip_id = :t AND " + _IN_WINDOW.format(c="l.created_at"), o_pass=""
)
_PURCHASED_RAISE = """
SELECT coalesce(-sum(l.delta), 0)::bigint FROM credit_ledger l JOIN credit_grants g ON g.id = l.grant_id
 WHERE l.user_id = :u AND g.kind = 'purchase' AND l.entry_type IN ('reserve', 'refund') AND l.created_at >= :ms"""
PURCHASED_CREDIT_MICROS = 20_000  # the cost value of a purchased credit (03 section 7.4)


def _lock(session: Session, key: str) -> None:
    session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": key})


def _app_user(session: Session) -> bool:
    return session.execute(text("SELECT app_user_id()")).scalar_one() is not None


def _provider_spend(session: Session, user_id: uuid.UUID, since: datetime) -> int:
    """Non-Claude provider cost since `since`. The API role goes through the definer wrapper; the worker reads the table."""
    if _app_user(session):
        return int(session.execute(text("SELECT my_provider_spend_micros(:s)"), {"s": since}).scalar_one())
    return int(
        session.execute(
            text("SELECT coalesce(sum(cost_usd_micros), 0) FROM provider_calls WHERE user_id = :u AND provider <> 'anthropic' AND cost_usd_micros IS NOT NULL AND created_at >= :s"),
            {"u": user_id, "s": since},
        ).scalar_one()
    )


def _sums(session: Session, user_id: uuid.UUID, trip_id: uuid.UUID | None, *, payer_pass: bool, ms: datetime, ds: datetime) -> tuple[int, int]:
    """(month, day) spend of the payer: the pass (every member, by trip) or the account (its own, pass work left out)."""
    if payer_pass and _app_user(session):  # RLS shows an API session only its own rows: the definer function sums every member
        month, day = session.execute(text("SELECT month_micros, day_micros FROM trip_pass_spend_micros(:t, :ms, :ds)"), {"t": trip_id, "ms": ms, "ds": ds}).one()
        return int(month), int(day)
    month, day = session.execute(text(_PASS if payer_pass else _ACTOR), {"u": user_id, "t": trip_id, "ms": ms, "ds": ds}).one()
    if not payer_pass:
        month += _provider_spend(session, user_id, ms)
        day += _provider_spend(session, user_id, ds)
    return int(month), int(day)


def _unavailable() -> ApiError:
    return ApiError(503, "ai_unavailable", "This is paused for a moment. Try again soon.")


def check(
    session: Session,
    *,
    user_id: uuid.UUID,
    trip_id: uuid.UUID | None,
    action: str,
    items: int = 1,
    taster: bool = False,
    cached: bool = False,
    now: datetime | None = None,
) -> None:
    """Take the locks, then raise 429 provider_budget_exhausted if the action's hard stop does not fit the month, or the day
    (an agent run and a plan check skip the day). A taster run (own $0.80 allowance) and cached work spend no ceiling.
    Call it in the transaction that reserves, before the reserve."""
    if taster or cached:
        return
    now = (now or datetime.now(UTC)).astimezone(UTC)
    ms, ds = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), now.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        _lock(session, f"ceiling:{user_id}")
        has_pass = trip_id is not None and session.execute(
            text("SELECT EXISTS (SELECT 1 FROM trip_passes WHERE trip_id = :t AND status = 'active' AND starts_at <= :n AND expires_at > :n)"), {"t": trip_id, "n": now}
        ).scalar_one()
        if has_pass:
            _lock(session, f"ceiling:trip:{trip_id}")
            limits = session.execute(text("SELECT limits FROM plans WHERE code = 'trip_pass'")).scalar_one()
        else:
            limits = session.execute(
                text(
                    "SELECT pl.limits FROM plans pl LEFT JOIN entitlements e ON e.user_id = :u AND (e.valid_until IS NULL OR e.valid_until > :n) "
                    "WHERE pl.code = coalesce(e.tier_code, 'free')"
                ),
                {"u": user_id, "n": now},
            ).scalar_one()
        # shortcut: the tier's plans.limits only. Ceiling: an entitlements.limits override is not merged. Trigger: the admin console writes per-user overrides.
        month_ceiling, day_ceiling = int(limits["monthly_ceiling_micros"]), int(limits["daily_ceiling_micros"])
        hard = int(session.execute(text("SELECT hard_stop_micros FROM credit_action_prices WHERE action = CAST(:a AS ai_action)"), {"a": action}).scalar_one())
        hard *= items if action == "verify_plan" else 1
        month, day = _sums(session, user_id, trip_id, payer_pass=bool(has_pass), ms=ms, ds=ds)
        if not has_pass:  # purchased credits spent this month raise the account's ceiling by their cost value; no other credit does
            month_ceiling += PURCHASED_CREDIT_MICROS * int(session.execute(text(_PURCHASED_RAISE), {"u": user_id, "ms": ms}).scalar_one())
    except (SQLAlchemyError, KeyError, TypeError, ValueError) as e:
        raise _unavailable() from e
    payer = "pass" if has_pass else "account"
    if month + hard > month_ceiling:
        resets = (ms + timedelta(days=32)).replace(day=1)
        raise ApiError(429, "provider_budget_exhausted", f"AI is paused until {resets.day} {resets:%b}. {_PAUSED}", extra={"scope": "month", "payer": payer, "resets_at": resets.isoformat()})
    if action not in DAY_EXEMPT and day + hard > day_ceiling:
        resets = ds + timedelta(days=1)
        raise ApiError(429, "provider_budget_exhausted", f"AI is paused until tomorrow. {_PAUSED}", extra={"scope": "day", "payer": payer, "resets_at": resets.isoformat()})


def admit(
    session: Session,
    *,
    user_id: uuid.UUID,
    trip_id: uuid.UUID | None,
    action: str,
    idempotency_key: str,
    run_id: uuid.UUID | None = None,
    cached: bool = False,
    items: int = 1,
) -> service.Reservation:
    """Ceiling check, then the credit reserve, in the caller's transaction (the caller enqueues its job in it too).
    A retry with the same key returns the original reservation without a second check. A run that the taster covers whole
    is checked against the taster allowance, not the ceiling (06 section 5.9)."""
    replay = session.execute(
        text("SELECT 1 FROM credit_ledger WHERE idempotency_key = :k AND entry_type = 'reserve' LIMIT 1"), {"k": idempotency_key}
    ).first()
    if not replay:
        _lock(session, f"ceiling:{user_id}")  # before the taster read, so two parallel runs cannot both see the taster whole
        taster = (
            action == "agent_run"
            and not cached
            and session.execute(
                text("SELECT EXISTS (SELECT 1 FROM credit_grants WHERE user_id = :u AND period_key = 'taster' AND remaining >= :p)"),
                {"u": user_id, "p": service.table_price(session, action)},
            ).scalar_one()
        )
        check(session, user_id=user_id, trip_id=trip_id, action=action, items=items, taster=taster, cached=cached)
    return service.reserve(
        session, user_id=user_id, trip_id=trip_id, action=action, idempotency_key=idempotency_key, run_id=run_id, cached=cached, items=items
    )
