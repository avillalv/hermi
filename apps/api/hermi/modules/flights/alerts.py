# ruff: noqa: E501  (long SQL strings)
"""Price alerts on cached fares (04 section 5.8, WF-031.1): the pure drop rule and the idempotent trigger.

Delivery is not here (WF-047) and neither is the scheduled check (WF-051): `evaluate_alert` records a trigger and returns it.
"""

import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Trigger:
    alert_id: uuid.UUID
    price_minor: int
    currency: str


def detect_drop(prices: Iterable[int | None], threshold_minor: int, last_notified_minor: int | None) -> int | None:
    """The cheapest price when it is at or under the target and lower than the last price we told about, else None.
    `prices` are in the alert's currency; None (a fare with no rate) is skipped."""
    cheapest = min((p for p in prices if p is not None), default=None)
    if cheapest is None or cheapest > threshold_minor:
        return None
    if last_notified_minor is not None and cheapest >= last_notified_minor:
        return None
    return cheapest


def evaluate_alert(session: Session, alert_id: uuid.UUID) -> Trigger | None:
    """Evaluate one active alert over its route's visible cached fares. Returns the trigger once per drop.

    The conditional UPDATE is the first gate: of two concurrent evaluations of the same price only one gets a row back.
    The notifications unique key (user_id, dedupe_key) is the second: a reset alert never tells about the same price twice."""
    alert = session.execute(
        text("SELECT route_id, trip_id, user_id, channel_push, channel_email, threshold_minor, currency::text AS currency, last_notified_price_minor FROM price_alerts WHERE id = :a AND active FOR UPDATE"),
        {"a": alert_id},
    ).mappings().first()
    if alert is None:
        return None
    prices = session.execute(
        text(
            """SELECT fx_convert_minor(o.price_total_minor, o.currency::text, :c) FROM trip_fare_links l
                 JOIN fare_observations o ON o.id = l.observation_id
                WHERE l.route_id = :r AND NOT l.hidden AND NOT l.suspect
                  AND o.expires_at > now() AND o.depart_date >= CURRENT_DATE AND o.confidence = 'cached'"""
        ),
        {"r": alert["route_id"], "c": alert["currency"]},
    ).scalars().all()
    session.execute(text("UPDATE price_alerts SET last_evaluated_at = now() WHERE id = :a"), {"a": alert_id})
    price = detect_drop(prices, alert["threshold_minor"], alert["last_notified_price_minor"])
    if price is None:
        return None
    won = session.execute(
        text(
            """UPDATE price_alerts SET last_notified_at = now(), last_notified_price_minor = :p
                WHERE id = :a AND active AND (last_notified_price_minor IS NULL OR last_notified_price_minor > :p) RETURNING id"""
        ),
        {"a": alert_id, "p": price},
    ).first()
    if won is None:
        return None
    # The unique (user_id, dedupe_key) is the second gate: a reset alert never tells about the same price twice.
    exponent = session.execute(text("SELECT currency_exponent(:c)"), {"c": alert["currency"]}).scalar_one()
    shown = f"{Decimal(price).scaleb(-exponent):.{exponent}f}"
    sent = session.execute(
        text(
            """INSERT INTO notifications (user_id, trip_id, kind, dedupe_key, title, body, payload, want_push, want_email)
                VALUES (:u, :t, 'price_drop', :k, 'Price drop', :b, CAST(:pl AS jsonb), :push, :email)
                ON CONFLICT (user_id, dedupe_key) DO NOTHING RETURNING id"""
        ),
        {"u": alert["user_id"], "t": alert["trip_id"], "k": f"price_drop:{alert_id}:{price}", "b": f"A fare is down to {shown} {alert['currency']}.",
         "pl": json.dumps({"alert_id": str(alert_id), "route_id": str(alert["route_id"]), "price_minor": price, "currency": alert["currency"]}),
         "push": alert["channel_push"], "email": alert["channel_email"]},
    ).first()
    return Trigger(alert_id, price, alert["currency"]) if sent else None
