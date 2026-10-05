# ruff: noqa: E501  (long SQL strings and comments)
"""Entitlement resolver (WF-023.1, 03 section 7.1, 07 section 2).

Every limit comes from the `plans.limits` seed, never from a constant here. A missing key means "not granted" (0 or false).
Plan limits and missing entitlements are 402 with a `paywall` hint (04 section 2.2); 403 stays for role, account and consent.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import ApiError
from hermi.modules.billing.paywall import TRIGGERS
from hermi.modules.billing.schemas import (
    CreditBalance,
    CreditGrantOut,
    Entitlements,
    Flags,
    TripPassOut,
    Usage,
)

# The paywall trigger a limit key fires (04 section 2.2, 07 section 6.2); reason and free path come from `paywall.TRIGGERS`.
_PAYWALLS = {"active_trips": "third_trip", "collaborators": "invite", "routes_per_trip": "second_route", "live_routes": "track_live"}


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
    row = session.execute(
        text("SELECT sources, limits FROM trip_effective_limits(:t)"), {"t": trip_id}
    ).first()
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
    trigger = _PAYWALLS[key]
    reason, free_path = TRIGGERS[trigger].reason, TRIGGERS[trigger].free_path
    return ApiError(
        402,
        "limit_reached",
        message,
        extra={
            "paywall": {
                "trigger": trigger,
                "reason": reason,
                "offer_url": f"/v1/paywall/offer?reason={reason}",
                "free_path": free_path,
            }
        },
    )


def require_active_trip_slot(session: Session, user_id: uuid.UUID) -> None:
    """402 `limit_reached` when the owner already has `active_trips` active trips. `user_id` must be the caller (the RLS-scoped session's user)."""
    limits = user_limits(session, user_id)
    limit = limit_of(limits, "active_trips")
    if count_active_owned(session, user_id) >= limit:
        if limit > limit_of(
            billing_free(session), "active_trips"
        ):  # a paid tier at its fair-use ceiling: no upsell
            raise paywall_error(
                "active_trips",
                limit,
                f"You have {limit} active trips. Archive one to make room.",
                upsell=False,
            )
        raise paywall_error(
            "active_trips",
            limit,
            f"You have {limit} active trips. Archive one to make room, or upgrade.",
        )


CANCEL_URL = (
    "https://apps.apple.com/account/subscriptions"  # 07 section 7.11: Apple's own subscription page
)


def get_entitlements(session: Session, user_id: uuid.UUID) -> Entitlements:
    """04 section 5.19. Read only, never calls Apple. A lapsed tier reads as Free (`user_limits` agrees). Pass limits are per trip, so they are listed, not merged."""
    e = (
        session.execute(
            text(
                "SELECT e.tier_code, e.source, e.valid_until, e.in_grace, s.product_id, s.status::text AS sub_status, s.auto_renew "
                "  FROM entitlements e LEFT JOIN subscriptions s ON s.id = e.subscription_id WHERE e.user_id = :u"
            ),
            {"u": user_id},
        )
        .mappings()
        .first()
    )
    live = (
        bool(e)
        and e["tier_code"] != "free"
        and (e["valid_until"] is None or e["valid_until"] > datetime.now(UTC))
    )
    limits = user_limits(session, user_id)
    status = (
        e["sub_status"]
        if live and e["sub_status"]
        else ("active" if live else ("expired" if e and e["tier_code"] != "free" else "none"))
    )
    passes = (
        session.execute(
            text(
                "SELECT id, source, trip_id, starts_at, expires_at, status::text AS status, live_checks_max - live_checks_used AS left_, collaborators_max "
                "  FROM trip_passes WHERE purchaser_user_id = :u ORDER BY created_at DESC"
            ),
            {"u": user_id},
        )
        .mappings()
        .all()
    )
    grants = (
        session.execute(
            text(
                "SELECT kind::text AS kind, remaining, expires_at, trip_id FROM credit_grants "
                " WHERE user_id = :u AND remaining > 0 AND (expires_at IS NULL OR expires_at > now()) ORDER BY expires_at NULLS LAST"
            ),
            {"u": user_id},
        )
        .mappings()
        .all()
    )
    by_kind = lambda k: sum(g["remaining"] for g in grants if g["kind"] == k)  # noqa: E731
    blocked = bool(
        session.execute(
            text("SELECT 1 FROM credit_debts WHERE user_id = :u AND amount > 0"), {"u": user_id}
        ).first()
    )
    taster_spent = session.execute(
        text(
            "SELECT 1 FROM credit_grants WHERE user_id = :u AND period_key = 'taster' AND remaining = 0"
        ),
        {"u": user_id},
    ).first()
    taster = limit_of(limits, "taster_agent_runs") > 0 and not taster_spent
    reward_used = session.execute(
        text("SELECT 1 FROM trip_imports WHERE user_id = :u AND reward_granted_at IS NOT NULL"),
        {"u": user_id},
    ).first()
    return Entitlements(
        tier="plus" if live else "free",
        source=e["source"] if live else "none",
        product_id=e["product_id"] if live else None,
        status=status,
        valid_until=e["valid_until"] if live else None,
        auto_renew=e["auto_renew"] if live and e["source"] == "subscription" else None,
        store="apple" if live and e["source"] == "subscription" else None,
        manage_subscription_url=CANCEL_URL if live and e["source"] == "subscription" else None,
        cancel_url=CANCEL_URL if live and e["source"] == "subscription" else None,
        limits=limits,
        usage=Usage(active_trips=count_active_owned(session, user_id)),
        trip_passes=[
            TripPassOut(
                id=p["id"],
                source="import_reward" if p["source"] == "import_reward" else "purchase",
                trip_id=p["trip_id"],
                starts_at=p["starts_at"],
                expires_at=p["expires_at"],
                status=p["status"],
                live_checks_left=p["left_"],
                collaborators_max=p["collaborators_max"],
            )
            for p in passes
        ],
        # shortcut: Free gets no agent runs beyond the taster; the paid-tier flag follows the tier until the agent gate (WF-0xx) owns it.
        flags=Flags(
            agent_runs=live or taster,
            taster_available=taster,
            import_reward_available=not reward_used,
        ),
        credits=CreditBalance(
            total=sum(g["remaining"] for g in grants),
            monthly=by_kind("monthly"),
            trip_pass=by_kind("trip_pass"),
            purchased=by_kind("purchase"),
            grants=[CreditGrantOut(**g) for g in grants],
            next_monthly_grant_at=None,  # shortcut: no monthly grants until the ledger lands; add the date in WF-044
            blocked=blocked,
        ),
    )


def require_traveler_slots(
    session: Session, trip_id: uuid.UUID | None, count: int, user_id: uuid.UUID | None = None
) -> None:
    """402 `limit_reached`, reason `traveler_limit`, when `count` travelers exceed `travelers_per_trip` (04 section 5.7).
    An existing trip uses its merged limits; a trip not created yet (`trip_id` None) uses the owner's `user_id` tier.
    The reason sets no trigger (04 section 5.20), so the hint has none."""
    limits = trip_limits(session, trip_id)[1] if trip_id else user_limits(session, user_id)
    limit = limit_of(limits, "travelers_per_trip")
    if count > limit:
        raise ApiError(
            402,
            "limit_reached",
            f"A trip can have {limit} travelers on your plan.",
            extra={
                "paywall": {
                    "reason": "traveler_limit",
                    "offer_url": "/v1/paywall/offer?reason=traveler_limit",
                    "free_path": f"Keep {limit} travelers on this trip",
                }
            },
        )


def require_route_limits(
    session: Session, trip_id: uuid.UUID, *, origins: int, destinations: int, live: bool, other_routes: int, other_live: int
) -> None:
    """402 `limit_reached` when a flight route breaks `airports_per_side`, `routes_per_trip` or (live mode) `live_routes`
    on the trip's merged limits (04 section 5.8). `other_*` count the trip's other routes, so an edit does not count itself."""
    limits = trip_limits(session, trip_id)[1]
    per_side = limit_of(limits, "airports_per_side")
    if max(origins, destinations) > per_side:  # no PaywallHint reason exists for this limit (04 section 2.2), so no hint
        raise paywall_error("airports_per_side", per_side, f"A route can have {per_side} airports on each side on your plan.", upsell=False)
    routes = limit_of(limits, "routes_per_trip")
    if other_routes >= routes:
        raise paywall_error("routes_per_trip", routes, f"A trip can track {routes} flight routes on your plan.")
    if live and other_live >= limit_of(limits, "live_routes"):
        raise paywall_error("live_routes", limit_of(limits, "live_routes"), "Live tracking needs a free live route slot.")
