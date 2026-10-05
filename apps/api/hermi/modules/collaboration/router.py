# ruff: noqa: E501  (long signatures and comments)
"""Member, invite, leave and transfer routes (04 sections 5.4 and 5.6). WF-025.1. Share links and the shared trip are WF-025.2."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query, Request, Response
from sqlalchemy.orm import Session

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.modules.collaboration import activity, service
from hermi.modules.collaboration.schemas import (
    ActivityPage,
    Invite,
    InviteAccept,
    InviteCreate,
    InvitePreview,
    Member,
    MemberRolePatch,
    SharedTrip,
    ShareLink,
    ShareLinkCreate,
    ShareLinkPatch,
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
    service.reconcile_collaborators(session, access.trip.id)
    return service.list_members(session, access.trip.id)


@router.get("/trips/{trip_id}/activity", response_model=ActivityPage)
def trip_activity(
    access: Annotated[TripAccess, require_trip("viewer")],
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: str | None = None,
) -> ActivityPage:
    return activity.feed(session, access.trip.id, limit, cursor)


@router.patch("/trips/{trip_id}/members/{user_id}", response_model=Member)
def set_member_role(
    user_id: uuid.UUID, body: MemberRolePatch, access: Annotated[TripAccess, require_trip("owner")], session: DbSession
) -> Member:
    member = service.set_role(session, access, user_id, body.role)
    activity.record(session, access.trip.id, access.member.user_id, "role_changed", "member", user_id, f"made a member {body.role}")
    return member


@router.delete("/trips/{trip_id}/members/{user_id}", status_code=204)
def remove_member(user_id: uuid.UUID, access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> Response:
    activity.record(session, access.trip.id, access.member.user_id, "removed", "member", user_id, "removed a member")
    service.remove_member(session, access, user_id)
    return Response(status_code=204)


@router.post("/trips/{trip_id}/leave", status_code=204)
def leave_trip(access: Annotated[TripAccess, require_trip("viewer")], session: DbSession) -> Response:
    activity.record(session, access.trip.id, access.member.user_id, "left", "member", access.member.user_id, "left the trip")
    service.leave(session, access)
    return Response(status_code=204)


@router.post("/trips/{trip_id}/transfer", response_model=Trip)
def transfer_trip(body: TransferIn, access: Annotated[TripAccess, require_trip("owner")], user: CurrentUser, session: DbSession) -> Trip:
    service.transfer(session, access.trip.id, body.new_owner_id)
    activity.record(session, access.trip.id, user.id, "transferred", "trip", access.trip.id, "transferred the trip to another member")
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
    activity.record(session, trip_id, user.id, "joined", "member", user.id, "joined the trip")
    return _trip_for(session, trip_id, user.id)


@router.get("/trips/{trip_id}/share-links", response_model=list[ShareLink])
def list_share_links(access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> list[ShareLink]:
    return service.list_share_links(session, access.trip.id)


@router.post("/trips/{trip_id}/share-links", response_model=ShareLink, status_code=201)
def create_share_link(
    body: ShareLinkCreate, access: Annotated[TripAccess, require_trip("owner")], user: CurrentUser, session: DbSession, request: Request
) -> ShareLink:
    return service.create_share_link(session, access, user.id, body, request.app.state.settings.public_web_url)


@router.patch("/trips/{trip_id}/share-links/{link_id}", response_model=ShareLink)
def update_share_link(link_id: uuid.UUID, body: ShareLinkPatch, access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> ShareLink:
    return service.update_share_link(session, access.trip.id, link_id, body)


@router.delete("/trips/{trip_id}/share-links/{link_id}", status_code=204)
def revoke_share_link(link_id: uuid.UUID, access: Annotated[TripAccess, require_trip("owner")], session: DbSession) -> Response:
    service.revoke_share_link(session, access.trip.id, link_id)
    return Response(status_code=204)


@router.get("/shared/{token}", response_model=SharedTrip)
def shared_trip(token: Token, request: Request, response: Response) -> SharedTrip:
    # shortcut: no per-IP and per-token limit yet (04 5.6); WF-028 adds the limiter.
    page, indexable = service.view_shared(request.app.state.settings, token)
    response.headers["Cache-Control"] = "public, max-age=60"
    if not indexable:
        response.headers["X-Robots-Tag"] = "noindex"
    return page
