# ruff: noqa: E501
"""check_fare_route: lane api, one due live route, enqueued by scan_due_routes (02 section 5.2).

Eligibility first (07 section 4: live routes are checked daily, within `live_window_days` of departure, on the owner's tier or
an active trip pass with checks left). An ineligible route returns a named skip reason, which the worker's "job done" log line
carries; scan_due_routes has already moved its next_check_at. An eligible route is refreshed through `fares.refresh_route`, then
one `evaluate_price_alerts` is queued when it has alerts.

shortcut: the refresh uses the cached provider and does not spend a pass check; the SerpApi live call and the spend arrive with
WF-052. Upgrade trigger: WF-052.
"""

import uuid
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.config import NotConfigured, Settings
from hermi.modules.flights import fares
from hermi_worker.jobs import evaluate_price_alerts

NAME = "check_fare_route"
LANE = "api"
SCHEDULE = None
RETRIES = 5
ARGS = ("route_id",)

_ROUTE = text(
    """SELECT r.is_live, r.active, r.depart_from, r.depart_to,
              coalesce((SELECT (pl.limits->>'live_window_days')::int FROM trips t
                          LEFT JOIN entitlements e ON e.user_id = t.owner_user_id AND (e.valid_until IS NULL OR e.valid_until > :now)
                          JOIN plans pl ON pl.code = coalesce(e.tier_code, 'free')
                         WHERE t.id = r.trip_id), 0) AS tier_window,
              (SELECT (pl.limits->>'live_window_days')::int FROM trip_passes p JOIN plans pl ON pl.code = p.plan_code
                WHERE p.trip_id = r.trip_id AND p.status = 'active' AND :now >= p.starts_at AND :now < p.expires_at) AS pass_window,
              (SELECT p.live_checks_max - p.live_checks_used FROM trip_passes p
                WHERE p.trip_id = r.trip_id AND p.status = 'active' AND :now >= p.starts_at AND :now < p.expires_at) AS pass_checks_left
         FROM flight_routes r WHERE r.id = :r"""
)


def skip_reason(row, today: date) -> str | None:
    """The named reason a route is not checked today, or None when it is eligible."""
    if not row["active"]:
        return "inactive"
    if not row["is_live"]:
        return "not_live"
    if row["depart_to"] < today:
        return "departed"
    tier, pass_window, left = row["tier_window"] or 0, row["pass_window"] or 0, row["pass_checks_left"]
    window = max(tier, pass_window)
    if window == 0:
        return "no_live_window"
    if tier == 0 and left is not None and left <= 0:  # only the pass grants live checks, and it is spent
        return "pass_checks_used"
    if (max(row["depart_from"], today) - today).days > window:
        return "outside_window"
    return None


def run(session: Session, settings: Settings, route_id: str, client: httpx.Client | None = None, token: str = "", now: datetime | None = None) -> str:
    """Returns "checked", "not_configured" (no provider key), "gone" (no such route) or a skip reason (see skip_reason)."""
    now = now or datetime.now(UTC)
    rid = uuid.UUID(route_id)
    row = session.execute(_ROUTE, {"r": rid, "now": now}).mappings().first()
    if row is None:
        return "gone"
    if reason := skip_reason(row, now.date()):
        return reason
    own = client is None
    if own:
        try:
            token, client = fares.provider_for(settings)
        except NotConfigured:
            return "not_configured"
    try:
        result = fares.refresh_route(session, rid, client=client, token=token, now=now)
    finally:
        if own:
            client.close()
    if result.linked:
        evaluate_price_alerts.enqueue_for_route(session, rid)
    return "checked"
