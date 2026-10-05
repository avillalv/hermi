# ruff: noqa: E501  (long SQL strings)
"""price_alerts routes (04 section 5.8). Alerts are personal (RLS: the row's user must be the caller), cached fares only.

`/routes/{route_id}` and `/price-alerts/{alert_id}` carry no trip id, so each resolves its trip and then runs the same
`require_trip` check as every trip route.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.billing import service as billing
from hermi.modules.flights.schemas import Money, PriceAlert, PriceAlertIn, PriceAlertPatch

router = APIRouter(tags=["flights"])

_COLS = "id, route_id, threshold_minor, currency::text AS currency, channel_push, channel_email, active, last_notified_at, last_notified_price_minor"


def _alert(row) -> PriceAlert:
    last = row["last_notified_price_minor"]
    return PriceAlert(
        id=row["id"], route_id=row["route_id"], active=row["active"], last_notified_at=row["last_notified_at"],
        target_price=Money(amount_minor=row["threshold_minor"], currency=row["currency"]),
        notify={"push": row["channel_push"], "email": row["channel_email"]},
        last_notified_price=Money(amount_minor=last, currency=row["currency"]) if last is not None else None,
    )


def _via(table: str):
    """Depends() resolving the trip of a route or alert id (404 when not visible), then the editor check."""
    check = require_trip("editor").dependency

    def access(session: DbSession, route_id: uuid.UUID | None = None, alert_id: uuid.UUID | None = None) -> TripAccess:
        trip_id = session.execute(text(f"SELECT trip_id FROM {table} WHERE id = :i"), {"i": route_id or alert_id}).scalar()
        if trip_id is None:
            raise NotFound()
        return check(trip_id, session)

    access.__require_trip__ = "editor"
    return Depends(access)


def _check_currency(session: Session, currency: str) -> None:
    if currency != "EUR" and session.execute(text("SELECT 1 FROM fx_rates WHERE currency = :c"), {"c": currency}).first() is None:
        raise ApiError(
            422, "validation_failed", "We do not have rates for that currency yet. Pick another one.",
            extra={"errors": [{"field": "target_price.currency", "code": "invalid", "message": "Unsupported currency."}]},
        )


@router.get("/trips/{trip_id}/price-alerts", response_model=list[PriceAlert])
def list_alerts(access: Annotated[TripAccess, require_trip("viewer")], user: CurrentUser, session: DbSession) -> list[PriceAlert]:
    rows = session.execute(text(f"SELECT {_COLS} FROM price_alerts WHERE trip_id = :t AND user_id = :u ORDER BY created_at, id"), {"t": access.trip.id, "u": user.id}).mappings()
    return [_alert(r) for r in rows]


@router.post("/routes/{route_id}/price-alerts", response_model=PriceAlert, status_code=201)
def create_alert(route_id: uuid.UUID, body: PriceAlertIn, access: Annotated[TripAccess, _via("flight_routes")], user: CurrentUser, session: DbSession) -> PriceAlert:
    _check_currency(session, body.target_price.currency)
    dup = ApiError(409, "state_conflict", "You already have a price alert on this route. Change that one instead.")
    if session.execute(text("SELECT 1 FROM price_alerts WHERE route_id = :r AND user_id = :u"), {"r": route_id, "u": user.id}).first():
        raise dup
    # The cap is per account (the account's own tier). A pass raises it on its own trip only, counted there.
    # The booked-fare drop alert is not a row here, so it never counts.
    # shortcut: two parallel creates can pass the cap together; lock the users row if that ever shows up.
    acct = billing.limit_of(billing.user_limits(session, user.id), "price_alerts")
    trip_cap = billing.limit_of(billing.trip_limits(session, access.trip.id)[1], "price_alerts")
    total, here = session.execute(text("SELECT count(*), count(*) FILTER (WHERE trip_id = :t) FROM price_alerts WHERE user_id = :u"), {"u": user.id, "t": access.trip.id}).one()
    if total >= acct and not (trip_cap > acct and here < trip_cap):
        raise billing.paywall_error("price_alerts", max(acct, trip_cap), f"You can have {max(acct, trip_cap)} price alerts on your plan.")
    try:
        with session.begin_nested():
            row = session.execute(
                text(
                    f"""INSERT INTO price_alerts (trip_id, route_id, user_id, threshold_minor, currency, channel_push, channel_email, active)
                        VALUES (:t, :r, :u, :m, :c, :push, :email, :a) RETURNING {_COLS}"""
                ),
                {"t": access.trip.id, "r": route_id, "u": user.id, "m": body.target_price.amount_minor, "c": body.target_price.currency,
                 "push": body.notify.push, "email": body.notify.email, "a": body.active},
            ).mappings().one()
    except IntegrityError:
        raise dup from None
    return _alert(row)


@router.patch("/price-alerts/{alert_id}", response_model=PriceAlert)
def update_alert(alert_id: uuid.UUID, body: PriceAlertPatch, access: Annotated[TripAccess, _via("price_alerts")], user: CurrentUser, session: DbSession) -> PriceAlert:
    sets, params = [], {"i": alert_id, "u": user.id}
    if body.target_price is not None:
        _check_currency(session, body.target_price.currency)
        # a new target starts fresh: the last told price was measured against the old one
        sets += ["threshold_minor = :m", "currency = :c", "last_notified_price_minor = NULL"]
        params |= {"m": body.target_price.amount_minor, "c": body.target_price.currency}
    if body.notify is not None:
        sets += ["channel_push = :push", "channel_email = :email"]
        params |= {"push": body.notify.push, "email": body.notify.email}
    if body.active is not None:
        sets.append("active = :a")
        params["a"] = body.active
    row = session.execute(text(f"UPDATE price_alerts SET {', '.join(sets or ['active = active'])} WHERE id = :i AND user_id = :u RETURNING {_COLS}"), params).mappings().first()
    if row is None:
        raise NotFound()
    return _alert(row)


@router.delete("/price-alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: uuid.UUID, access: Annotated[TripAccess, _via("price_alerts")], user: CurrentUser, session: DbSession) -> Response:
    if session.execute(text("DELETE FROM price_alerts WHERE id = :i AND user_id = :u RETURNING id"), {"i": alert_id, "u": user.id}).first() is None:
        raise NotFound()
    return Response(status_code=204)
