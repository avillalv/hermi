# ruff: noqa: E501
"""refresh_cached_fares: refreshes Travelpayouts cached fares for active routes not checked in the last 6 hours (04 section 5.8).

Free for every tier and never spends credits. A leader-scheduled job on lane api (SCHEDULE). It picks routes stale for 6 hours, so
a double run in the same bucket does nothing, and after each refresh it queues one evaluate_price_alerts for a route with alerts.
shortcut: nothing enqueues a refresh on route create; POST /flights/refresh covers a new route. Ceiling: a route made without a
manual refresh waits for the next run.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.config import NotConfigured
from hermi.modules.flights import fares
from hermi.providers import ProviderError
from hermi_worker.jobs import evaluate_price_alerts

log = logging.getLogger(__name__)

NAME = "refresh_cached_fares"
LANE = "api"
SCHEDULE = "17 */6 * * *"
RETRIES = 5
ARGS = ()
BATCH = 200
_DUE = text(
    """SELECT id FROM flight_routes WHERE active AND depart_to >= :today AND (last_checked_at IS NULL OR last_checked_at < :stale)
       ORDER BY last_checked_at NULLS FIRST LIMIT :n"""
)


def run(session: Session, settings, client=None, token: str = "", now: datetime | None = None) -> int:
    """Returns the number of routes refreshed; 0 when Travelpayouts is not configured. Commits after each route."""
    now = now or datetime.now(UTC)
    own = client is None
    if own:
        try:
            token, client = fares.provider_for(settings)
        except NotConfigured:
            return 0
    done = 0
    try:
        due = [r[0] for r in session.execute(_DUE, {"today": now.date(), "stale": now - fares.CACHE_TTL, "n": BATCH})]
        for route_id in due:
            try:
                result = fares.refresh_route(session, route_id, client=client, token=token, now=now)
                if result.linked:
                    evaluate_price_alerts.enqueue_for_route(session, route_id)
                session.commit()
                done += 1
            except ProviderError:
                session.rollback()
                log.warning("cached fares refresh failed for a route", extra={"route_id": str(route_id)})
        return done
    finally:
        if own:
            client.close()
