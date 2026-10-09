# ruff: noqa: E501  (long SQL strings)
"""Credit ledger service (WF-044; 03 section 5.8, 07 section 5). The reserve and settle rules (spend order, FOR UPDATE on
the grants, the trip pool, the taster's own grant, the caller check, idempotency) live in the SQL functions of migration
0006; repo.py calls them. This module adds prices, the balance read, the stopped-run charge and the worker-side writes
(adjustments, expiry, the stale sweep). Nothing here commits.

API callers (hermi_app, RLS) use reserve, settle, refund and balance. Worker callers (system session) use the rest:
the app role cannot write credit_grants or credit_ledger."""

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.modules.credits import prices, repo


@dataclass(frozen=True)
class Reservation:
    id: uuid.UUID
    amount: int


@dataclass(frozen=True)
class Balance:
    available: int  # what this actor can spend on this action now
    blocked: bool  # a refund left the account in credit debt
    version: int  # newest credit_ledger id for the user; a cached balance is valid only for the version it carries


def table_price(session: Session, action: str, *, cached: bool = False, items: int = 1) -> int:
    """The price from credit_action_prices (03 section 7.3), so an admin edit takes effect at once."""
    credits, from_cache = session.execute(
        text("SELECT credits, credits_cached FROM credit_action_prices WHERE action = CAST(:a AS ai_action)"), {"a": action}
    ).one()
    return (from_cache if cached and from_cache is not None else credits) * items


def reserve(
    session: Session,
    *,
    user_id: uuid.UUID,
    trip_id: uuid.UUID | None,
    action: str,
    idempotency_key: str,
    run_id: uuid.UUID | None = None,
    cached: bool = False,
    items: int = 1,
) -> Reservation:
    """Lazy Free allowance, then reserve the action's price. Raises 402 insufficient_credits (blocked=true on debt)."""
    amount = table_price(session, action, cached=cached, items=items)
    repo.ensure_free_monthly_grant(session, user_id)
    rid = repo.reserve_credits(
        session, user_id=user_id, trip_id=trip_id, amount=amount, action=action, run_id=run_id, idempotency_key=idempotency_key
    )
    return Reservation(rid, amount)


def settle(session: Session, reservation_id: uuid.UUID, charged: int, usage_id: int | None = None) -> int:
    """Charge `charged` (capped at the reserve) and return the rest. Replaying a settled reservation returns 0."""
    return repo.settle_credits(session, reservation_id, charged, usage_id)


def refund(session: Session, reservation_id: uuid.UUID, usage_id: int | None = None) -> int:
    """A failed, refused, timed out or empty action: give everything back to the grants it came from."""
    return repo.settle_credits(session, reservation_id, 0, usage_id)


def settle_stopped_agent_run(
    session: Session, reservation_id: uuid.UUID, *, turns_used: int, called_tools: bool = True, usage_id: int | None = None
) -> int:
    """Pro rata by turns used (table max_turns), 8 credit minimum, 0 if stopped in the queue. A run paid from the taster
    is charged in full (the taster stays spent) unless it was stopped in the queue. Returns the credits charged;
    a replay returns 0."""
    if session.execute(
        text("SELECT EXISTS (SELECT 1 FROM credit_ledger WHERE reservation_id = :r AND entry_type = 'settle')"), {"r": reservation_id}
    ).scalar_one():
        return 0
    reserved, from_taster = session.execute(
        text(
            """SELECT coalesce(sum(-l.delta), 0), coalesce(bool_or(g.period_key = 'taster'), false)
                 FROM credit_ledger l LEFT JOIN credit_grants g ON g.id = l.grant_id
                WHERE l.reservation_id = :r AND l.entry_type = 'reserve'"""
        ),
        {"r": reservation_id},
    ).one()
    full, max_turns = session.execute(
        text("SELECT credits, max_turns FROM credit_action_prices WHERE action = 'agent_run'")
    ).one()
    if from_taster and called_tools:
        charged = int(reserved)
    else:
        charged = min(prices.agent_run_charge(turns_used, called_tools=called_tools, max_turns=max_turns or prices.AGENT_RUN_MAX_TURNS, full=full), int(reserved))
    repo.settle_credits(session, reservation_id, charged, usage_id)
    return charged


def balance(session: Session, user_id: uuid.UUID, *, trip_id: uuid.UUID | None, action: str, price: int | None = None) -> Balance:
    """Spendable credits read from the grants and the ledger every time (03 section 7.2); never cached without `version`.
    Own grants plus the trip's pass pool; the taster counts only for an agent run it covers whole. credit_grants is read as the
    caller: a worker session sees the pool, an API session (RLS, own rows only) sees only its own grants, not another member's pass."""
    price = table_price(session, action) if price is None else price
    available = session.execute(
        text(
            """
SELECT GREATEST(
         COALESCE(sum(g.remaining) FILTER (WHERE g.period_key IS DISTINCT FROM 'taster'), 0),
         CASE WHEN CAST(:action AS text) = 'agent_run' AND COALESCE(sum(g.remaining) FILTER (WHERE g.period_key = 'taster' AND g.user_id = :u), 0) >= :price
              THEN :price ELSE 0 END)::integer
  FROM credit_grants g
 WHERE g.remaining > 0 AND (g.expires_at IS NULL OR g.expires_at > now())
   AND ((g.user_id = :u AND g.trip_id IS NULL)
        OR (g.kind = 'trip_pass' AND g.trip_id = :t
            AND EXISTS (SELECT 1 FROM trip_members m WHERE m.trip_id = :t AND m.user_id = :u AND m.role IN ('owner', 'editor'))))
   AND (g.restricted_action IS NULL OR g.restricted_action = CAST(:action AS ai_action))"""
        ),
        {"u": user_id, "t": trip_id, "action": action, "price": price},
    ).scalar_one()
    blocked = session.execute(
        text("SELECT EXISTS (SELECT 1 FROM credit_debts WHERE user_id = :u AND amount > 0)"), {"u": user_id}
    ).scalar_one()
    version = session.execute(
        text("SELECT coalesce(max(id), 0) FROM credit_ledger WHERE user_id = :u"), {"u": user_id}
    ).scalar_one()
    return Balance(int(available), bool(blocked), int(version))


# ---- worker role only from here (monthly and purchase grants belong to the billing service, WF-064) ----


def adjust(session: Session, user_id: uuid.UUID, credits: int, *, reason: str, actor_user_id: uuid.UUID | None = None) -> uuid.UUID:
    """Support goodwill: an `adjustment` grant valid 12 months (07 section 5.1), an `adjust` ledger row and an audit_log row, in the caller's transaction.
    shortcut: positive amounts only. Ceiling: removing credits is a clawback or a debt (record_credit_debt).
    Trigger: the admin console (08) needs a manual deduction."""
    if credits <= 0 or not reason.strip():
        raise ValueError("an adjustment needs a positive amount and a reason")
    gid = session.execute(
        text("INSERT INTO credit_grants (user_id, kind, credits, remaining, expires_at) VALUES (:u, 'adjustment', :c, :c, now() + interval '12 months') RETURNING id"),
        {"u": user_id, "c": credits},
    ).scalar_one()
    _ledger_grant(session, user_id, gid, credits, "adjust", reason)
    session.execute(
        text(
            """
INSERT INTO audit_log (actor_user_id, actor_type, action, entity_type, entity_id, after, reason, retention_class)
VALUES (CAST(:a AS uuid), CASE WHEN CAST(:a AS uuid) IS NULL THEN 'system' ELSE 'admin' END, 'credits.adjust', 'credit_grant', CAST(:g AS text),
        jsonb_build_object('user_id', CAST(:u AS text), 'credits', CAST(:c AS integer)), :r, 'extended')"""
        ),
        {"a": actor_user_id, "g": gid, "u": user_id, "c": credits, "r": reason},
    )
    repo.settle_credit_debt(session, user_id)
    return gid


def expire_grants(session: Session) -> int:
    """Hourly job: zero grants past expires_at and write their `expire` rows. Returns the grants expired."""
    return session.execute(text("SELECT expire_credit_grants()")).scalar_one()


def release_stale_reservations(session: Session) -> int:
    """Every-minute job: settle abandoned reservations at 0. Returns the number released."""
    return session.execute(text("SELECT release_stale_reservations()")).scalar_one()


def _ledger_grant(session: Session, user_id: uuid.UUID, grant_id: uuid.UUID, credits: int, entry_type: str, note: str) -> None:
    session.execute(
        text(
            "INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, note) "
            "VALUES (:u, :g, CAST(:t AS credit_entry_type), :c, :n)"
        ),
        {"u": user_id, "g": grant_id, "t": entry_type, "c": credits, "n": note},
    )
