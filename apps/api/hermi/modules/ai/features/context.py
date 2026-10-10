# ruff: noqa: E501
"""What a one-shot feature may send (06 section 12.1), read as the caller so row-level security applies.

Names are returned apart from the data, only to build the Redactor. Notes, expenses, emails and other members never
enter a context."""

import uuid
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import NotFound


def trip_basics(session: Session, trip_id: uuid.UUID) -> dict:
    t = session.execute(text("SELECT start_date, end_date FROM trips WHERE id = :t"), {"t": trip_id}).one_or_none()
    if t is None:
        raise NotFound()
    dests = session.execute(
        text("SELECT name, country FROM trip_destinations WHERE trip_id = :t ORDER BY position"), {"t": trip_id}
    ).all()
    travelers = session.execute(text("SELECT count(*) FROM trip_people WHERE trip_id = :t"), {"t": trip_id}).scalar_one()
    days = (t.end_date - t.start_date).days + 1 if t.start_date and t.end_date else None
    return {
        "destinations": [d.name for d in dests],
        "countries": sorted({d.country for d in dests if d.country}),
        "start_date": t.start_date.isoformat() if t.start_date else None,
        "end_date": t.end_date.isoformat() if t.end_date else None,
        "days": days,
        "travelers": max(int(travelers), 1),
    }


def person_names(session: Session, trip_id: uuid.UUID, user_id: uuid.UUID) -> list[str]:
    """Every name that must never reach a prompt: the trip's people, the members' trip profiles and the caller."""
    rows = session.execute(
        text(
            "SELECT p.name FROM trip_people tp JOIN people p ON p.id = tp.person_id WHERE tp.trip_id = :t "
            "UNION SELECT display_name FROM trip_member_profiles WHERE trip_id = :t AND display_name <> '' "
            "UNION SELECT display_name FROM users WHERE id = :u AND display_name IS NOT NULL"
        ),
        {"t": trip_id, "u": user_id},
    )
    return [r[0] for r in rows if r[0]]


def activity_categories(session: Session, trip_id: uuid.UUID) -> list[str]:
    return list(
        session.execute(
            text("SELECT DISTINCT category::text FROM itinerary_items WHERE trip_id = :t ORDER BY 1"), {"t": trip_id}
        ).scalars()
    )


def day_items(session: Session, trip_id: uuid.UUID, day: date) -> list[dict]:
    rows = session.execute(
        text(
            "SELECT title, category::text AS category, start_time, end_time FROM itinerary_items "
            "WHERE trip_id = :t AND day = :d ORDER BY start_time NULLS LAST, sort_order"
        ),
        {"t": trip_id, "d": day},
    )
    return [
        {
            "title": r.title, "category": r.category,
            "start": r.start_time.strftime("%H:%M") if r.start_time else None,
            "end": r.end_time.strftime("%H:%M") if r.end_time else None,
        }
        for r in rows
    ]


def saved_places(session: Session, trip_id: uuid.UUID, limit: int = 12) -> list[dict]:
    rows = session.execute(
        text("SELECT id, name, category::text AS category FROM saved_places WHERE trip_id = :t ORDER BY created_at LIMIT :n"),
        {"t": trip_id, "n": limit},
    )
    return [{"id": str(r.id), "name": r.name, "category": r.category} for r in rows]


def explain_subject(session: Session, trip_id: uuid.UUID, ctx: dict) -> dict | None:
    """The one thing the question is about, by the id the client sent, always inside this trip. No notes."""
    if item := ctx.get("item_id"):
        r = session.execute(
            text("SELECT title, category::text AS category, location_name, start_time FROM itinerary_items WHERE id = :i AND trip_id = :t"),
            {"i": item, "t": trip_id},
        ).one_or_none()
        if r is None:
            raise NotFound()
        return {"type": "itinerary_item", "title": r.title, "category": r.category, "location": r.location_name,
                "start": r.start_time.strftime("%H:%M") if r.start_time else None}
    if lodging := ctx.get("lodging_id"):
        r = session.execute(
            text("SELECT title, location_name, price_per_night_minor, currency::text AS currency FROM lodging_options WHERE id = :i AND trip_id = :t"),
            {"i": lodging, "t": trip_id},
        ).one_or_none()
        if r is None:
            raise NotFound()
        return {"type": "lodging", "title": r.title, "location": r.location_name,
                "price_per_night_minor": r.price_per_night_minor, "currency": r.currency}
    if place := ctx.get("place_id"):
        r = session.execute(
            text("SELECT name, category::text AS category, address FROM saved_places WHERE trip_id = :t AND (place_id = :p OR id::text = :p)"),
            {"t": trip_id, "p": place},
        ).first()
        if r is None:
            raise NotFound()
        return {"type": "place", "name": r.name, "category": r.category, "address": r.address}
    return None
