# ruff: noqa: E501  (long SQL strings and comments)
"""Trip capabilities (04 section 2.3, 03 section 7.1): the best of the owner's tier and any active pass on the trip."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import NotFound
from hermi.modules.billing import service as billing
from hermi.modules.trips.models import Trip
from hermi.modules.trips.schemas import Capabilities


def trip_capabilities(session: Session, trip: Trip) -> Capabilities:
    """Capabilities of `trip` for any member (invitees get the owner's tier on this trip only). 404 when the caller is not a member."""
    sources, limits = billing.trip_limits(session, trip.id)
    if not sources:
        raise NotFound()
    codes = [s.split(":", 1)[1] for s in sources]
    # shortcut: the highest plans.rank wins the label. Ceiling: two sources only (tier and one pass); revisit if a tier can stack.
    top = session.execute(text("SELECT code FROM plans WHERE code = ANY(:c) ORDER BY rank DESC LIMIT 1"), {"c": codes}).scalar_one()
    used = session.execute(
        text(
            "SELECT (SELECT count(*) FROM trip_members WHERE trip_id = :t AND role <> 'owner'), "
            "       (SELECT COALESCE(sum(max_uses - use_count), 0) FROM trip_invites WHERE trip_id = :t AND revoked_at IS NULL AND expires_at > now() AND use_count < max_uses), "
            "       (SELECT count(*) FROM flight_routes WHERE trip_id = :t AND is_live AND active)"
        ),
        {"t": trip.id},
    ).one()
    members, pending, live_used = used
    p = session.execute(
        text(
            "SELECT expires_at, live_checks_max - live_checks_used FROM trip_passes "
            "WHERE trip_id = :t AND status = 'active' AND now() >= starts_at AND now() < expires_at"
        ),
        {"t": trip.id},
    ).first()
    max_collab = billing.limit_of(limits, "collaborators")
    # shortcut: agent_enabled is the owner's trip switch only; the consent check joins it when the agent module lands (WF-050).
    return Capabilities(
        effective_tier=top,
        source="trip_pass" if top == "trip_pass" else "owner_tier",
        can_invite=bool(limits.get("can_invite")) and members + pending < max_collab,
        collaborators_used=members + pending,
        max_collaborators=max_collab,
        live_routes_max=billing.limit_of(limits, "live_routes"),
        live_routes_used=live_used,
        live_checks_left=p[1] if p else None,
        agent_enabled=trip.ai_enabled,
        limited=members > max_collab,
        pass_expires_at=p[0] if p else None,
    )
