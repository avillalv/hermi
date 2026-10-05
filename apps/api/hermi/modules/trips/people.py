# ruff: noqa: E501  (long SQL strings)
"""People (travelers) and trip travelers (04 sections 5.6 and 5.7). WF-024.1.

A person is a first name, a color and home airports. No birthdate, no email. Removing a person from a trip or deleting them
removes the `trip_people` row only; trips, members and other travelers stay.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.billing import service as billing
from hermi.modules.collaboration.schemas import (
    Attribution,
    Member,
    Person,
    PersonIn,
    TravelerLink,
    TravelersIn,
)

router = APIRouter(tags=["people"])

MAX_PEOPLE = 30
_COLS = "id, owner_user_id, linked_user_id, name, color::text AS color, home_airports::text[] AS home_airports, is_self"


def _invalid(field: str, msg: str) -> ApiError:
    return ApiError(
        422,
        "validation_failed",
        msg,
        extra={"errors": [{"field": field, "code": "invalid", "message": msg}]},
    )


def _out(row, me: uuid.UUID) -> Person:
    return Person(
        id=row["id"],
        name=row["name"],
        color=row["color"],
        home_airports=row["home_airports"] or [],
        linked_user_id=row["linked_user_id"],
        is_me=row["linked_user_id"] == me or (row["is_self"] and row["owner_user_id"] == me),
    )


def _own(session: Session, person_id: uuid.UUID, me: uuid.UUID):
    """The person row when the caller owns it: 404 when not visible, 403 when visible but someone else's."""
    row = (
        session.execute(text(f"SELECT {_COLS} FROM people WHERE id = :i"), {"i": person_id})
        .mappings()
        .first()
    )
    if row is None:
        raise NotFound()
    if row["owner_user_id"] != me:
        raise ApiError(403, "insufficient_role", "You do not have permission to do that.")
    return row


def trip_travelers(session: Session, trip_id: uuid.UUID, me: uuid.UUID) -> list[Person]:
    """The people on a trip (`trip_people`), in the order PUT /trips/{id}/travelers returns them. Row-level security applies as for GET /people."""
    rows = session.execute(
        text(
            f"SELECT {_COLS} FROM people WHERE id IN (SELECT person_id FROM trip_people WHERE trip_id = :t) ORDER BY is_self DESC, created_at, id"
        ),
        {"t": trip_id},
    ).mappings()
    return [_out(r, me) for r in rows]


@router.get("/people", response_model=list[Person])
def list_people(user: CurrentUser, session: DbSession) -> list[Person]:
    # Row-level security returns the caller's own people plus those on trips they belong to (co-members only).
    rows = session.execute(
        text(
            f"SELECT {_COLS} FROM people ORDER BY owner_user_id = :me DESC, is_self DESC, created_at, id"
        ),
        {"me": user.id},
    ).mappings()
    return [_out(r, user.id) for r in rows]


@router.post("/people", response_model=Person, status_code=201)
def create_person(
    body: PersonIn, user: CurrentUser, session: DbSession, response: Response
) -> Person:
    # shortcut: two parallel creates can pass the cap together; lock the users row (FOR UPDATE) if that ever shows up.
    if (
        session.execute(
            text("SELECT count(*) FROM people WHERE owner_user_id = :u"), {"u": user.id}
        ).scalar_one()
        >= MAX_PEOPLE
    ):
        raise _invalid("name", f"You can add up to {MAX_PEOPLE} travelers.")
    row = (
        session.execute(
            text(
                f"INSERT INTO people (owner_user_id, name, color, home_airports) VALUES (:u, :n, :c, :a) RETURNING {_COLS}"
            ),
            {"u": user.id, "n": body.name, "c": body.color, "a": body.home_airports},
        )
        .mappings()
        .one()
    )
    response.headers["Location"] = f"/v1/people/{row['id']}"
    return _out(row, user.id)


@router.put("/people/{person_id}", response_model=Person)
def update_person(
    person_id: uuid.UUID, body: PersonIn, user: CurrentUser, session: DbSession
) -> Person:
    row = _own(session, person_id, user.id)
    # shortcut: a person linked to another user can only be edited by that user, but row-level security lets only the owner
    # update `people`, so nobody can yet; add a definer function for the linked user's name and airports edit when a screen needs it.
    if row["linked_user_id"] not in (None, user.id):
        raise ApiError(
            403, "insufficient_role", "This traveler is linked to a member, who can edit them."
        )
    row = (
        session.execute(
            text(
                f"UPDATE people SET name = :n, color = :c, home_airports = :a WHERE id = :i RETURNING {_COLS}"
            ),
            {"i": person_id, "n": body.name, "c": body.color, "a": body.home_airports},
        )
        .mappings()
        .one()
    )
    return _out(row, user.id)


@router.delete("/people/{person_id}", status_code=204)
def delete_person(person_id: uuid.UUID, user: CurrentUser, session: DbSession) -> Response:
    row = _own(session, person_id, user.id)
    only = session.execute(
        text(
            "SELECT 1 FROM trip_people tp JOIN trips t ON t.id = tp.trip_id "
            " WHERE tp.person_id = :p AND t.owner_user_id <> :me AND t.deleted_at IS NULL "
            "   AND NOT EXISTS (SELECT 1 FROM trip_people o WHERE o.trip_id = tp.trip_id AND o.person_id <> tp.person_id) LIMIT 1"
        ),
        {"p": person_id, "me": user.id},
    ).first()
    if row["is_self"]:
        raise ApiError(409, "state_conflict", "Your own traveler cannot be removed.")
    if only:
        raise ApiError(
            409,
            "state_conflict",
            "This traveler cannot be removed while they are the only traveler on a trip you do not own.",
        )
    # trip_people rows cascade from people. shortcut: lodging_votes and saved_place_votes reference trip_people with ON DELETE
    # CASCADE (0010), so a vote by a removed traveler goes with them until a later migration keeps it as "Former traveler".
    session.execute(text("DELETE FROM people WHERE id = :i"), {"i": person_id})
    return Response(status_code=204)


@router.put("/trips/{trip_id}/travelers", response_model=list[Person])
def set_travelers(
    body: TravelersIn,
    access: Annotated[TripAccess, require_trip("editor")],
    user: CurrentUser,
    session: DbSession,
) -> list[Person]:
    ids = list(dict.fromkeys(body.person_ids))
    ok = session.execute(
        text(
            "SELECT count(*) FROM people WHERE id = ANY(:ids) AND (owner_user_id = :me "
            "   OR id IN (SELECT person_id FROM trip_people WHERE trip_id = :t))"
        ),
        {"ids": ids, "me": user.id, "t": access.trip.id},
    ).scalar_one()
    if ok != len(ids):
        raise _invalid("person_ids", "One of the travelers is not yours to add.")
    billing.require_traveler_slots(session, access.trip.id, len(ids))
    session.execute(
        text("DELETE FROM trip_people WHERE trip_id = :t AND NOT (person_id = ANY(:ids))"),
        {"t": access.trip.id, "ids": ids},
    )
    session.execute(
        text(
            "INSERT INTO trip_people (trip_id, person_id, added_by) SELECT :t, x, :u FROM unnest(CAST(:ids AS uuid[])) x ON CONFLICT DO NOTHING"
        ),
        {"t": access.trip.id, "u": user.id, "ids": ids},
    )
    return trip_travelers(session, access.trip.id, user.id)


def _member(session: Session, access: TripAccess, me: uuid.UUID) -> Member:
    def name(uid):  # null only when the user left the trip (04 section 2.1: "Former member")
        return session.execute(
            text(
                "SELECT NULLIF(display_name, '') FROM trip_member_profiles WHERE trip_id = :t AND user_id = :u"
            ),
            {"t": access.trip.id, "u": uid},
        ).scalar()

    pid = session.execute(
        text(
            "SELECT p.id FROM people p JOIN trip_people tp ON tp.person_id = p.id WHERE tp.trip_id = :t AND p.linked_user_id = :me LIMIT 1"
        ),
        {"t": access.trip.id, "me": me},
    ).scalar()
    by = access.member.invited_by
    return Member(
        user_id=me,
        display_name=name(me),
        role=access.role,
        person_id=pid,
        joined_at=access.member.joined_at,
        invited_by=Attribution(id=by, display_name=name(by)) if by else None,
    )


@router.put("/trips/{trip_id}/members/me/traveler", response_model=Member)
def link_traveler(
    body: TravelerLink,
    access: Annotated[TripAccess, require_trip("viewer")],
    user: CurrentUser,
    session: DbSession,
) -> Member:
    """Which traveler are you? Sets `people.linked_user_id` through link_my_traveler (a person links to one user per trip)."""
    if not session.execute(
        text("SELECT link_my_traveler(:t, :p)"), {"t": access.trip.id, "p": body.person_id}
    ).scalar():
        raise _invalid("person_id", "That traveler cannot be linked to you.")
    return _member(session, access, user.id)


@router.delete("/trips/{trip_id}/members/me/traveler", status_code=204)
def unlink_traveler(
    access: Annotated[TripAccess, require_trip("viewer")], session: DbSession
) -> Response:
    session.execute(text("SELECT unlink_my_traveler(:t)"), {"t": access.trip.id})
    return Response(status_code=204)
