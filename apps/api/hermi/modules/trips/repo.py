"""Trip queries. Each filters by membership of the given user (RLS is the second lock, 02 s4.3)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from hermi.modules.collaboration.models import TripMember
from hermi.modules.trips.models import Trip


def get_trip_with_member(
    session: Session, trip_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[Trip, TripMember] | None:
    """The trip and the user's membership row, or None when not a member or the trip is in trash."""
    row = session.execute(
        select(Trip, TripMember)
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(Trip.id == trip_id, TripMember.user_id == user_id, Trip.deleted_at.is_(None))
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
