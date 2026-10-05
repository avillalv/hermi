# ruff: noqa: E501
"""refresh_cached_fares: refreshes Travelpayouts cached fares for active routes not checked in the last 6 hours (04 section 5.8).

Free for every tier and never spends credits. shortcut: no queue yet, so nothing enqueues a refresh on route create; POST /flights/refresh covers a new route and the runtime
applies SCHEDULE. Ceiling: a route made without a manual refresh waits for the next run. Upgrade trigger: the WF-051 queue.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.config import NotConfigured
from hermi.db import make_engine
from hermi.modules.flights import fares
from hermi.providers import ProviderError

log = logging.getLogger(__name__)

NAME = "refresh_cached_fares"
SCHEDULE = "17 */6 * * *"
RETRIES = 3
BATCH = 200
_DUE = text(
    """SELECT id FROM flight_routes WHERE active AND depart_to >= :today AND (last_checked_at IS NULL OR last_checked_at < :stale)
       ORDER BY last_checked_at NULLS FIRST LIMIT :n"""
)


def run(settings, client=None, token: str = "", now: datetime | None = None) -> int:
    """Returns the number of routes refreshed; 0 when Travelpayouts is not configured."""
    now = now or datetime.now(UTC)
    own = client is None
    if own:
        try:
            token, client = fares.provider_for(settings)
        except NotConfigured:
            return 0
    engine = make_engine(settings.require("DATABASE_URL_SYSTEM"), pool_size=1, max_overflow=1)  # the ledger's failure row uses a second connection
    done = 0
    try:
        with Session(engine) as session:
            due = [r[0] for r in session.execute(_DUE, {"today": now.date(), "stale": now - fares.CACHE_TTL, "n": BATCH})]
            for route_id in due:
                try:
                    fares.refresh_route(session, route_id, client=client, token=token, now=now)
                    session.commit()
                    done += 1
                except ProviderError:
                    session.rollback()
                    log.warning("cached fares refresh failed for a route", extra={"route_id": str(route_id)})
        return done
    finally:
        engine.dispose()
        if own:
            client.close()
