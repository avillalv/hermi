# ruff: noqa: E501  (long SQL strings)
"""Calls to the credit SQL functions (03 section 5.13). The app role cannot write the credit tables directly;
these functions do it with the definer's rights and check the caller. Grants: ensure_free_monthly_grant,
ensure_taster_grant, reserve_credits and settle_credits are open to the API and the worker; record_credit_debt
and settle_credit_debt are worker only."""

import uuid

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from hermi.errors import ApiError

INSUFFICIENT_SQLSTATE = "WF402"  # a short balance, and a credit debt (message 'credit_debt')


def ensure_free_monthly_grant(session: Session, user_id: uuid.UUID) -> None:
    session.execute(text("SELECT ensure_free_monthly_grant(:u)"), {"u": user_id})


def ensure_taster_grant(session: Session, user_id: uuid.UUID) -> None:
    session.execute(text("SELECT ensure_taster_grant(:u)"), {"u": user_id})


def reserve_credits(
    session: Session,
    *,
    user_id: uuid.UUID,
    trip_id: uuid.UUID | None,
    amount: int,
    action: str,
    run_id: uuid.UUID | None,
    idempotency_key: str,
) -> uuid.UUID:
    """Reserve the price atomically; replaying the same idempotency key returns the original reservation.
    Both a short balance and a credit debt raise 402 insufficient_credits; a debt adds blocked=true."""
    try:
        with session.begin_nested():
            return session.execute(
                text("SELECT reserve_credits(:u, :t, :n, CAST(:a AS ai_action), :r, :k)"),
                {"u": user_id, "t": trip_id, "n": amount, "a": action, "r": run_id, "k": idempotency_key},
            ).scalar_one()
    except DBAPIError as e:
        if getattr(e.orig, "sqlstate", None) != INSUFFICIENT_SQLSTATE:
            raise
        if e.orig.diag.message_primary == "credit_debt":
            raise ApiError(
                402,
                "insufficient_credits",
                "Your balance is below zero after a refund. Buy credits or wait for your next monthly credits.",
                extra={"blocked": True},
            ) from e
        balance = session.execute(
            text("SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = :u"),
            {"u": user_id},
        ).scalar_one()
        raise ApiError(
            402,
            "insufficient_credits",
            "You do not have enough credits for this.",
            extra={"credits": {"needed": amount, "balance": int(balance)}},
        ) from e


def settle_credits(
    session: Session, reservation_id: uuid.UUID, charged: int, usage_id: int | None = None
) -> int:
    """Charge `charged` credits and return the rest to their grants (0 releases). Returns the credits returned."""
    return session.execute(
        text("SELECT settle_credits(:r, :c, :u)"),
        {"r": reservation_id, "c": charged, "u": usage_id},
    ).scalar_one()


def record_credit_debt(session: Session, user_id: uuid.UUID, credits: int, idempotency_key: str) -> None:
    """Worker role only. A replayed key records the debt once."""
    session.execute(
        text("SELECT record_credit_debt(:u, :c, :k)"),
        {"u": user_id, "c": credits, "k": idempotency_key},
    )


def settle_credit_debt(session: Session, user_id: uuid.UUID) -> int:
    """Worker role only. Pays the debt from the user's grants; returns the credits repaid."""
    return session.execute(text("SELECT settle_credit_debt(:u)"), {"u": user_id}).scalar_one()
