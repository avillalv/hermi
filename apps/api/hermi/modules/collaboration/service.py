# ruff: noqa: E501  (long SQL strings)
"""Members, invites, leave and transfer (04 sections 5.4 and 5.6). WF-025.1.

Raw SQL under row-level security, like the people module. Redeeming an invite and handing over ownership go through the
definer functions from 0004; the public preview through preview_trip_invite (0019).
"""

import hashlib
import secrets
import uuid

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from hermi.deps import TripAccess
from hermi.errors import ApiError, NotFound
from hermi.modules.billing import service as billing
from hermi.modules.collaboration.schemas import Attribution, Invite, InvitePreview, Member
from hermi.modules.trips import service as trips_service

MAX_PENDING_INVITES = 20
MAX_INVITES_PER_DAY = 30
RANK = {"viewer": 0, "editor": 1, "owner": 2}


def token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def _expired() -> ApiError:
    return ApiError(410, "invite_expired", "This invite is no longer valid. Ask for a new one.")


# --- members ---------------------------------------------------------------------------------


def list_members(session: Session, trip_id: uuid.UUID) -> list[Member]:
    rows = session.execute(
        text(
            "SELECT m.user_id, NULLIF(m.display_name, '') AS display_name, m.role, tm.joined_at, tm.invited_by, "
            "       NULLIF(ip.display_name, '') AS inviter_name, "
            "       (SELECT p.id FROM people p JOIN trip_people tp ON tp.person_id = p.id "
            "         WHERE tp.trip_id = m.trip_id AND p.linked_user_id = m.user_id LIMIT 1) AS person_id "
            "  FROM trip_member_profiles m JOIN trip_members tm ON tm.trip_id = m.trip_id AND tm.user_id = m.user_id "
            "  LEFT JOIN trip_member_profiles ip ON ip.trip_id = tm.trip_id AND ip.user_id = tm.invited_by "
            " WHERE m.trip_id = :t ORDER BY tm.joined_at, m.user_id"
        ),
        {"t": trip_id},
    ).mappings()
    return [
        Member(
            user_id=r["user_id"],
            display_name=r["display_name"],
            role=r["role"],
            person_id=r["person_id"],
            joined_at=r["joined_at"],
            invited_by=Attribution(id=r["invited_by"], display_name=r["inviter_name"]) if r["invited_by"] else None,
        )
        for r in rows
    ]


def _member_or_404(session: Session, trip_id: uuid.UUID, user_id: uuid.UUID) -> Member:
    found = next((m for m in list_members(session, trip_id) if m.user_id == user_id), None)
    if found is None:
        raise NotFound()
    return found


def set_role(session: Session, access: TripAccess, user_id: uuid.UUID, role: str) -> Member:
    target = _member_or_404(session, access.trip.id, user_id)
    if target.role == "owner":
        raise ApiError(409, "state_conflict", "The owner's role changes by transferring the trip.")
    if RANK[role] > RANK[target.role] and trips_service.trip_capabilities(session, access.trip).limited:
        # A trip over its collaborator slots keeps its members as viewers until the owner makes room or upgrades.
        raise billing.paywall_error("collaborators", billing.limit_of(billing.trip_limits(session, access.trip.id)[1], "collaborators"), "This trip has more collaborators than your plan allows. Remove one or upgrade to give more access.")
    session.execute(text("UPDATE trip_members SET role = :r WHERE trip_id = :t AND user_id = :u"), {"r": role, "t": access.trip.id, "u": user_id})
    return _member_or_404(session, access.trip.id, user_id)


def remove_member(session: Session, access: TripAccess, user_id: uuid.UUID) -> None:
    target = _member_or_404(session, access.trip.id, user_id)
    if target.role == "owner":
        raise ApiError(409, "state_conflict", "Transfer the trip before removing its owner.")
    # shortcut: the link is cleared only on travelers the owner owns (row-level security); one owned by another member stays linked to a user who is gone.
    session.execute(
        text("UPDATE people SET linked_user_id = NULL WHERE linked_user_id = :u AND id IN (SELECT person_id FROM trip_people WHERE trip_id = :t)"),
        {"u": user_id, "t": access.trip.id},
    )
    session.execute(text("DELETE FROM trip_members WHERE trip_id = :t AND user_id = :u"), {"t": access.trip.id, "u": user_id})


def leave(session: Session, access: TripAccess) -> None:
    if access.role == "owner":
        raise ApiError(409, "state_conflict", "Transfer the trip to someone else before you leave it.")
    session.execute(text("SELECT unlink_my_traveler(:t)"), {"t": access.trip.id})
    session.execute(text("DELETE FROM trip_members WHERE trip_id = :t AND user_id = :u"), {"t": access.trip.id, "u": access.member.user_id})


def transfer(session: Session, trip_id: uuid.UUID, new_owner: uuid.UUID) -> None:
    try:
        session.execute(text("SELECT transfer_trip_owner(:t, :n)"), {"t": trip_id, "n": new_owner})
    except DBAPIError as e:
        if getattr(e.orig, "sqlstate", None) != "22023":
            raise
        raise ApiError(
            422,
            "validation_failed",
            "Pick a member of this trip.",
            extra={"errors": [{"field": "new_owner_id", "code": "invalid", "message": "Pick a member of this trip."}]},
        ) from None
    # shortcut: no notification to the two owners yet; send "trip_transferred" when the notifications ticket lands (WF-047).
    session.expire_all()


# --- invites ---------------------------------------------------------------------------------

_INVITE_COLS = (
    "id, role, email, max_uses - use_count AS uses_left, expires_at, created_at, "
    "CASE WHEN revoked_at IS NOT NULL THEN 'revoked' WHEN use_count >= max_uses THEN 'used' "
    "     WHEN expires_at <= now() THEN 'expired' ELSE 'pending' END AS status"
)


def list_invites(session: Session, trip_id: uuid.UUID) -> list[Invite]:
    rows = session.execute(
        text(f"SELECT {_INVITE_COLS} FROM trip_invites WHERE trip_id = :t ORDER BY created_at DESC, id DESC"), {"t": trip_id}
    ).mappings()
    return [Invite(**r) for r in rows]


def create_invite(session: Session, access: TripAccess, user_id: uuid.UUID, body, web_url: str) -> Invite:
    if access.role != "owner" and not (body.role == "viewer" and access.trip.editors_can_invite):
        raise ApiError(403, "insufficient_role", "You do not have permission to do that.")
    # shortcut: counted here until the rate-limit layer lands (WF-028). A race can overshoot by a few; the real ceiling is the slot check of WF-026.
    pending, today = session.execute(
        text(
            "SELECT count(*) FILTER (WHERE trip_id = :t AND revoked_at IS NULL AND expires_at > now() AND use_count < max_uses), "
            "       count(*) FILTER (WHERE invited_by = :u AND created_at > now() - interval '1 day') FROM trip_invites"
        ),
        {"t": access.trip.id, "u": user_id},
    ).one()
    if pending >= MAX_PENDING_INVITES:
        raise ApiError(429, "rate_limited", f"This trip has {MAX_PENDING_INVITES} open invites. Revoke one first.")
    if today >= MAX_INVITES_PER_DAY:
        raise ApiError(429, "rate_limited", "You have sent a lot of invites today. Try again tomorrow.", {"Retry-After": "86400"})
    # Seam for WF-026: the collaborator slot check goes here (trips_service.trip_capabilities(...).can_invite, 402 `limit_reached`, reason `sharing`).
    # shortcut: no email is sent yet (no mail sender exists); the owner shares the url. Send when `email` is set once notifications can mail.
    token = secrets.token_urlsafe(16)  # 128 bits
    row = (
        session.execute(
            text(
                "INSERT INTO trip_invites (trip_id, invited_by, token_hash, role, email, max_uses, expires_at) "
                "VALUES (:t, :u, :h, :r, :e, :m, now() + make_interval(days => :d)) RETURNING " + _INVITE_COLS
            ),
            {
                "t": access.trip.id,
                "u": user_id,
                "h": token_hash(token),
                "r": body.role,
                "e": body.email,
                "m": 1 if body.email else body.max_uses,
                "d": body.expires_in_days,
            },
        )
        .mappings()
        .one()
    )
    return Invite(**row, url=f"{web_url.rstrip('/')}/invite/{token}")


def revoke_invite(session: Session, trip_id: uuid.UUID, invite_id: uuid.UUID) -> None:
    if not session.execute(
        text("UPDATE trip_invites SET revoked_at = COALESCE(revoked_at, now()) WHERE id = :i AND trip_id = :t RETURNING id"),
        {"i": invite_id, "t": trip_id},
    ).first():
        raise NotFound()


def preview(engine: Engine, token: str) -> InvitePreview:
    """Public: no user, so it reads through the definer function. One 410 for every bad token."""
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM preview_trip_invite(:h)"), {"h": token_hash(token)}).mappings().first()
    if row is None:
        raise _expired()
    return InvitePreview(
        trip_name=row["trip_name"], cover_url=row["cover_url"], inviter_name=row["inviter_name"] or "A Hermi member", role=row["role"]
    )


def accept(session: Session, token: str, person_id: uuid.UUID | None) -> uuid.UUID:
    """Redeem for the caller and return the trip id. Free invitees join without a plan: nothing here touches active_trips."""
    try:
        trip_id = session.execute(text("SELECT redeem_trip_invite(:h)"), {"h": token_hash(token)}).scalar_one()
    except DBAPIError as e:
        state = getattr(e.orig, "sqlstate", None)
        if state == "P0001":
            raise _expired() from None
        if state == "23505":
            detail = getattr(getattr(e.orig, "diag", None), "message_detail", None)
            raise ApiError(409, "already_member", "You are already on this trip.", extra={"trip_id": detail}) from None
        raise
    if person_id:  # best effort: a traveler that is not on the trip is ignored, the join stands
        session.execute(text("SELECT link_my_traveler(:t, :p)"), {"t": trip_id, "p": person_id})
    return trip_id
