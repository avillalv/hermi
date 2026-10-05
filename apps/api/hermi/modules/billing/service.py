# ruff: noqa: E501  (long SQL strings and comments)
"""Entitlement resolver (WF-023.1, 03 section 7.1, 07 section 2).

Every limit comes from the `plans.limits` seed, never from a constant here. A missing key means "not granted" (0 or false).
Plan limits and missing entitlements are 402 with a `paywall` hint (04 section 2.2); 403 stays for role, account and consent.
"""

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import ApiError

# (trigger, reason, free_path) per limit key that can fire a paywall (04 section 2.2, 07 section 6.2).
_PAYWALLS = {
    "active_trips": ("third_trip", "trip_limit", "Archive a trip or join trips other people plan"),
}


def user_limits(session: Session, user_id: uuid.UUID) -> dict[str, Any]:
    """`plans.limits` of the user's current tier (Free when the entitlement is missing or lapsed). The owner's own view, for limits that have no trip yet."""
    row = session.execute(
        text(
            "SELECT pl.limits FROM plans pl "
            "  LEFT JOIN entitlements e ON e.user_id = :u AND (e.valid_until IS NULL OR e.valid_until > now()) "
            " WHERE pl.code = coalesce(e.tier_code, 'free')"
        ),
        {"u": user_id},
    ).scalar()
    return row or {}


def trip_limits(session: Session, trip_id: uuid.UUID) -> tuple[list[str], dict[str, Any]]:
    """(sources, merged limits) for a trip the caller is a member of: the best of the owner's tier and any active pass,
    per key. Invitees get the owner's tier on that trip only. ([], {}) when the trip is not visible to the caller."""
    row = session.execute(text("SELECT sources, limits FROM trip_effective_limits(:t)"), {"t": trip_id}).first()
    return (list(row[0]), row[1]) if row and row[1] else ([], {})


def limit_of(limits: dict[str, Any], key: str) -> int:
    """A numeric limit; absent means not granted (0)."""
    return int(limits.get(key) or 0)


def billing_free(session: Session) -> dict[str, Any]:
    """`plans.limits` of the Free tier."""
    return session.execute(text("SELECT limits FROM plans WHERE code = 'free'")).scalar() or {}


def count_active_owned(session: Session, user_id: uuid.UUID) -> int:
    """03 section 7.5: owned, not in trash, planning or booked, and no active pass on the trip (the pass raises the limit by 1)."""
    return session.execute(
        text(
            "SELECT count(*) FROM trips t WHERE t.owner_user_id = :u AND t.deleted_at IS NULL "
            "   AND t.status IN ('planning', 'booked') "
            "   AND NOT EXISTS (SELECT 1 FROM trip_passes p WHERE p.trip_id = t.id AND p.status = 'active' "
            "                    AND now() >= p.starts_at AND now() < p.expires_at)"
        ),
        {"u": user_id},
    ).scalar_one()


def paywall_error(key: str, limit: int, message: str, *, upsell: bool = True) -> ApiError:
    """402 `limit_reached`, with the PaywallHint for a limit key unless `upsell` is false (nothing to sell: the top tier hit its fair-use ceiling)."""
    if not upsell:
        return ApiError(402, "limit_reached", message)
    trigger, reason, free_path = _PAYWALLS[key]
    return ApiError(
        402,
        "limit_reached",
        message,
        extra={"paywall": {"trigger": trigger, "reason": reason, "offer_url": f"/v1/paywall/offer?reason={reason}", "free_path": free_path}},
    )


def require_active_trip_slot(session: Session, user_id: uuid.UUID) -> None:
    """402 `limit_reached` when the owner already has `active_trips` active trips. `user_id` must be the caller (the RLS-scoped session's user)."""
    limits = user_limits(session, user_id)
    limit = limit_of(limits, "active_trips")
    if count_active_owned(session, user_id) >= limit:
        if limit > limit_of(billing_free(session), "active_trips"):  # a paid tier at its fair-use ceiling: no upsell
            raise paywall_error("active_trips", limit, f"You have {limit} active trips. Archive one to make room.", upsell=False)
        raise paywall_error("active_trips", limit, f"You have {limit} active trips. Archive one to make room, or upgrade.")
