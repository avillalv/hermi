# ruff: noqa: E501  (long SQL strings)
"""Trip queries. Each filters by membership of the given user (RLS is the second lock, 02 s4.3)."""

import uuid
from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

import hermi.modules.auth.models  # noqa: F401  (registers `users` for the foreign keys)
from hermi.modules.collaboration.models import TripMember, TripPerson
from hermi.modules.trips.models import Trip, TripDestination


def get_trip_with_member(
    session: Session, trip_id: uuid.UUID, user_id: uuid.UUID, *, trashed: bool = False
) -> tuple[Trip, TripMember] | None:
    """The trip and the user's membership row, or None when not a member or the trip is in trash.

    trashed=True looks only at trips in the trash (restore) instead of only at live ones."""
    row = session.execute(
        select(Trip, TripMember)
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(
            Trip.id == trip_id,
            TripMember.user_id == user_id,
            Trip.deleted_at.is_not(None) if trashed else Trip.deleted_at.is_(None),
        )
    ).first()
    return (row[0], row[1]) if row else None


def list_my_trips(session: Session, user_id: uuid.UUID) -> list[Trip]:
    return list(
        session.scalars(
            select(Trip)
            .join(TripMember, TripMember.trip_id == Trip.id)
            .where(TripMember.user_id == user_id, Trip.deleted_at.is_(None))
            .order_by(Trip.created_at.desc())
        )
    )


# --- WF-018.2 ---------------------------------------------------------------------------------------------------------


def user_home_currency(session: Session, user_id: uuid.UUID) -> str:
    return session.execute(text("SELECT home_currency::text FROM users WHERE id = :u"), {"u": user_id}).scalar_one()


def my_person_ids(session: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    """The people rows the caller owns (the travelers they may put on a trip), "Me" first."""
    return list(
        session.scalars(
            text("SELECT id FROM people WHERE owner_user_id = :u ORDER BY is_self DESC, created_at"), {"u": user_id}
        )
    )


def create_trip(session: Session, user_id: uuid.UUID, values: dict, destinations: list[dict], people: list[uuid.UUID]) -> Trip:
    """Inserts the trip (trg_trips_add_owner_member adds the owner row), its destinations and its traveler links."""
    trip = Trip(owner_user_id=user_id, **values)
    session.add(trip)
    session.flush()
    for i, d in enumerate(destinations):
        session.add(TripDestination(trip_id=trip.id, position=i, **d))
    for pid in people:
        session.add(TripPerson(trip_id=trip.id, person_id=pid, added_by=user_id))
    session.flush()
    session.refresh(trip)
    return trip


def destinations_of(session: Session, trip_id: uuid.UUID) -> list[TripDestination]:
    return list(session.scalars(select(TripDestination).where(TripDestination.trip_id == trip_id).order_by(TripDestination.position)))


def list_summaries(session: Session, user_id: uuid.UUID, *, limit: int, after: tuple[datetime, uuid.UUID] | None, status: str | None):
    """Keyset page of the caller's trips (owned and joined), newest activity first. Returns up to limit + 1 rows."""
    sql = (
        "SELECT t.id, t.version, t.name, t.status::text AS status, t.start_date, t.end_date, m.role::text AS my_role, "
        "       (SELECT count(*) FROM trip_members x WHERE x.trip_id = t.id) AS member_count, t.updated_at, "
        "       coalesce((SELECT string_agg(d.name, ', ' ORDER BY d.position) FROM trip_destinations d WHERE d.trip_id = t.id), '') AS destinations_label "
        "  FROM trips t JOIN trip_members m ON m.trip_id = t.id AND m.user_id = :u "
        " WHERE t.deleted_at IS NULL"
    )
    args: dict = {"u": user_id, "n": limit + 1}
    if status:
        sql += " AND t.status = :s"
        args["s"] = status
    if after:
        sql += " AND (t.updated_at, t.id) < (:at, :id)"
        args["at"], args["id"] = after
    sql += " ORDER BY t.updated_at DESC, t.id DESC LIMIT :n"
    return list(session.execute(text(sql), args).mappings())


# --- WF-019.1 ---------------------------------------------------------------------------------------------------------


def update_trip(session: Session, trip: Trip, version: int, values: dict) -> bool:
    """Writes `values` (never empty, so the version trigger always bumps) when the row is still at `version`.
    False means someone else got there first (409)."""
    done = session.execute(
        update(Trip).where(Trip.id == trip.id, Trip.version == version).values(**values).returning(Trip.id),
        execution_options={"synchronize_session": False},
    ).first()
    session.refresh(trip)
    return done is not None


def sync_my_travelers(session: Session, trip_id: uuid.UUID, user_id: uuid.UUID, people: list[uuid.UUID]) -> None:
    """Replaces the travelers the caller owns on the trip; travelers other members added stay."""
    session.execute(
        text("DELETE FROM trip_people WHERE trip_id = :t AND person_id IN (SELECT id FROM people WHERE owner_user_id = :u)"),
        {"t": trip_id, "u": user_id},
    )
    for pid in people:
        session.add(TripPerson(trip_id=trip_id, person_id=pid, added_by=user_id))
    session.flush()


def replace_destinations(session: Session, trip_id: uuid.UUID, items: list[dict]) -> bool:
    """Makes the trip's destinations `items`, in that order. An item with an `id` updates that row; one without is new;
    rows not named are removed. False when an id is not a destination of this trip."""
    have = {d.id: d for d in destinations_of(session, trip_id)}
    named = [i["id"] for i in items if i.get("id") is not None]
    if len(named) != len(set(named)) or any(i not in have for i in named):
        return False
    keep = {i["id"] for i in items if i.get("id") is not None}
    for gone in set(have) - keep:
        session.delete(have[gone])
    session.flush()
    for pos, i in enumerate(items):
        fields = {k: v for k, v in i.items() if k != "id"}
        if i.get("id") is None:
            session.add(TripDestination(trip_id=trip_id, position=pos, **fields))
        else:
            row = have[i["id"]]
            for k, v in fields.items():
                setattr(row, k, v)  # only the fields the client sent change; a field left out keeps its value, an explicit null clears it
            row.position = pos
    session.flush()
    return True


def get_destination(session: Session, trip_id: uuid.UUID, destination_id: uuid.UUID) -> TripDestination | None:
    return session.scalars(
        select(TripDestination).where(TripDestination.trip_id == trip_id, TripDestination.id == destination_id)
    ).first()


def add_destination(session: Session, trip_id: uuid.UUID, values: dict) -> TripDestination:
    """Appends at the end. The caller has checked the cap of 12."""
    pos = session.execute(
        text("SELECT coalesce(max(position) + 1, 0) FROM trip_destinations WHERE trip_id = :t"), {"t": trip_id}
    ).scalar_one()
    row = TripDestination(trip_id=trip_id, position=pos, **values)
    session.add(row)
    session.flush()
    session.refresh(row)
    return row


def remove_destination(session: Session, row: TripDestination) -> None:
    """Deletes it and closes the gap; days that pointed at it fall back to null by the foreign key."""
    trip_id = row.trip_id
    session.delete(row)
    session.flush()
    for pos, d in enumerate(destinations_of(session, trip_id)):
        d.position = pos
    session.flush()


def order_destinations(session: Session, trip_id: uuid.UUID, ids: list[uuid.UUID]) -> bool:
    have = {d.id: d for d in destinations_of(session, trip_id)}
    if len(ids) != len(have) or set(ids) != set(have):
        return False
    for pos, i in enumerate(ids):
        have[i].position = pos
    session.flush()
    return True


def trash_trip(session: Session, trip_id: uuid.UUID) -> None:
    """Soft delete (04 5.4): revokes invites and share links and disables the calendar feed token.
    shortcut: active agent runs are not cancelled here (the agent module owns `runs`); wire it when WF-050 lands."""
    session.execute(update(Trip).where(Trip.id == trip_id).values(deleted_at=text("now()"), calendar_token_hash=None))
    for table in ("trip_invites", "trip_share_links"):
        session.execute(text(f"UPDATE {table} SET revoked_at = now() WHERE trip_id = :t AND revoked_at IS NULL"), {"t": trip_id})


def restore_trip(session: Session, trip: Trip) -> None:
    session.execute(update(Trip).where(Trip.id == trip.id).values(deleted_at=None))
    session.refresh(trip)


def in_trash_window(session: Session, trip_id: uuid.UUID) -> bool:
    return bool(
        session.execute(
            text("SELECT deleted_at > now() - interval '30 days' FROM trips WHERE id = :t"), {"t": trip_id}
        ).scalar()
    )
