# ruff: noqa: E501
"""evaluate_price_alerts: lane notify, event job (02 section 5.1). Runs after a fare refresh wrote observations for a route.

Each active alert of the route goes through `alerts.evaluate_alert`: the pure drop rule, a conditional UPDATE and the notification
unique key make it fire once per drop, and the notification service queues the email on this lane. A queueing lock per route
keeps a burst of refreshes to one waiting evaluation.
"""

import uuid

from procrastinate.exceptions import AlreadyEnqueued
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.jobs import enqueue
from hermi.modules.flights import alerts

NAME = "evaluate_price_alerts"
LANE = "notify"
SCHEDULE = None  # event job, no cron
RETRIES = 3
ARGS = ("route_id",)


def run(session: Session, settings: Settings, route_id: str) -> int:
    """Returns the number of alerts that fired."""
    ids = session.execute(text("SELECT id FROM price_alerts WHERE route_id = :r AND active ORDER BY id"), {"r": uuid.UUID(route_id)}).scalars().all()
    return sum(alerts.evaluate_alert(session, i) is not None for i in ids)


def enqueue_for_route(session: Session, route_id: uuid.UUID) -> bool:
    """Queue one evaluation when the route has an active alert and none is already waiting. In the caller's transaction."""
    if not session.execute(text("SELECT EXISTS (SELECT 1 FROM price_alerts WHERE route_id = :r AND active)"), {"r": route_id}).scalar_one():
        return False
    try:
        with session.begin_nested():  # a duplicate queueing lock must not poison the caller's transaction
            enqueue(session, NAME, queueing_lock=f"{NAME}:{route_id}", route_id=str(route_id))
    except AlreadyEnqueued:
        return False
    return True
