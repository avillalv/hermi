# ruff: noqa: E501  (long signatures and comments)
"""Member, invite, leave and transfer routes (04 sections 5.4 and 5.6). WF-025.1. Share links are WF-025.2."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Request, Response
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.modules.collaboration import service
from hermi.modules.collaboration.schemas import (
    Invite,
    InviteAccept,
    InviteCreate,
    InvitePreview,
    Member,
    MemberRolePatch,
    TransferIn,
)
from hermi.modules.trips import repo
from hermi.modules.trips.router import full_trip
from hermi.modules.trips.schemas import Trip

router = APIRouter(tags=["collaboration"])

Token = Annotated[str, Path(min_length=1, max_length=128)]


def _trip_for(session: Session, trip_id: uuid.UUID, me: uuid.UUID) -> Trip:
    trip, member = repo.get_trip_with_member(session, trip_id, me)
    return full_trip(session, trip, member.role, me)


@router.get("/trips/{trip_id}/members", response_model=list[Member])
def list_members(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession) -> list[Member]:
    return service.list_members(session, access.trip.id)


@router.patch("/trips/{trip_id}/members/{user_id}", response_model=Member)
def set_member_role(
    user_id: uuid.UUID, body: MemberRolePatch, access: Annotated[TripAccess, require_trip("owner")], session: DbSession
) -> Member:
    return service.set_role(session, access, user_id, body.role)


@router.delete("/trips/{trip_id}/members/{user_id}", status_code=204)
def remove_member(user_id: uuid.UUID, access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> Response:
    service.remove_member(session, access, user_id)
    return Response(status_code=204)


@router.post("/trips/{trip_id}/leave", status_code=204)
def leave_trip(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession) -> Response:
    service.leave(session, access)
    return Response(status_code=204)


@router.post("/trips/{trip_id}/transfer", response_model=Trip)
def transfer_trip(body: TransferIn, access: Annotated[TripAccess, require_trip("owner")], user: CurrentUser, session: DbSession) -> Trip:
    service.transfer(session, access.trip.id, body.new_owner_id)
    return _trip_for(session, access.trip.id, user.id)


@router.get("/trips/{trip_id}/invites", response_model=list[Invite], response_model_exclude={"__all__": {"url"}})
def list_invites(access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> list[Invite]:
    return service.list_invites(session, access.trip.id)


@router.post("/trips/{trip_id}/invites", response_model=Invite, status_code=201)
def create_invite(
    body: InviteCreate, access: Annotated[TripAccess, require_trip("editor")], user: CurrentUser, session: DbSession, request: Request
) -> Invite:
    return service.create_invite(session, access, user.id, body, request.app.state.settings.public_web_url)


@router.delete("/trips/{trip_id}/invites/{invite_id}", status_code=204)
def revoke_invite(invite_id: uuid.UUID, access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> Response:
    service.revoke_invite(session, access.trip.id, invite_id)
    return Response(status_code=204)


@router.get("/invites/{token}", response_model=InvitePreview)
def preview_invite(token: Token, request: Request, response: Response) -> InvitePreview:
    # shortcut: no per-IP rate limit yet (04 5.6 says rate limited); WF-028 adds the limiter. The token is 128 bits, so guessing is not the risk.
    response.headers["Cache-Control"] = "no-store"
    return service.preview(request.app.state.engine, token)


@router.post("/invites/{token}/accept", response_model=Trip)
def accept_invite(token: Token, body: InviteAccept, user: CurrentUser, session: DbSession) -> Trip:
    trip_id = service.accept(session, token, body.person_id)
    return _trip_for(session, trip_id, user.id)
