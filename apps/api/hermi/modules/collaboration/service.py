# ruff: noqa: E501  (long SQL strings)
"""Members, invites, share links, leave and transfer (04 sections 5.4, 5.6 and 5.15). WF-025.1 and WF-025.2.

Raw SQL under row-level security, like the people module. Redeeming an invite and handing over ownership go through the
definer functions from 0004; the public preview through preview_trip_invite (0019).
"""

import hashlib
import secrets
import uuid

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from hermi import db
from hermi.deps import TripAccess
from hermi.errors import ApiError, NotFound
from hermi.modules.billing import service as billing
from hermi.modules.collaboration.schemas import (
    Attribution,
    Invite,
    InvitePreview,
    Member,
    Presentation,
    Redact,
    SharedTrip,
    ShareLink,
)
from hermi.modules.trips import service as trips_service

# The invite and join slot lock, a transaction-level advisory lock per trip. A row lock would not do: a join's trip_members
# insert holds FOR KEY SHARE on the trip (FOR UPDATE would deadlock two joins), and FOR NO KEY UPDATE is filtered by the
# trips_update RLS policy for viewers, so it takes no lock for them. The advisory lock ignores RLS and clashes with neither.
LOCK_TRIP = "SELECT pg_advisory_xact_lock(hashtextextended(CAST(:t AS text) || '/collab', 0))"
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


def _no_slot(session: Session, limit: int) -> ApiError:
    """402 for a full trip. A paid owner at their ceiling has nothing to buy, so no paywall hint then."""
    top = limit > billing.limit_of(billing.billing_free(session), "collaborators")
    msg = (
        f"This trip has {limit} collaborators. Remove one to make room."
        if top
        else f"Free trips have {limit} collaborator. Upgrade to Plus or a Trip Pass to add more, or share a read-only link for free."
    )
    return billing.paywall_error("collaborators", limit, msg, upsell=not top)


def reconcile_collaborators(session: Session, trip_id: uuid.UUID) -> bool:
    """Lapse handling (WF-026). When the owner's plan or pass no longer covers the members, those beyond the limit
    (latest joined first) become viewers. Nobody is removed. Returns the `limited` banner flag. Only the owner's
    session can write, so a collaborator's read just reports the flag."""
    # shortcut: lazy demotion. It runs only when the owner reads the trip, the trip list or the members, so extras keep editor
    # rights until then. Upgrade to a billing webhook or a worker sweep when plan lapses become events.
    _, limits = billing.trip_limits(session, trip_id)
    max_collab = billing.limit_of(limits, "collaborators")
    members = session.execute(text("SELECT count(*) FROM trip_members WHERE trip_id = :t AND role <> 'owner'"), {"t": trip_id}).scalar_one()
    if members <= max_collab:
        return False
    session.execute(
        text(
            "UPDATE trip_members SET role = 'viewer' WHERE trip_id = :t AND role = 'editor' AND user_id NOT IN "
            "(SELECT user_id FROM trip_members WHERE trip_id = :t AND role <> 'owner' ORDER BY joined_at, user_id LIMIT :n)"
        ),
        {"t": trip_id, "n": max_collab},
    )
    return True


def create_invite(session: Session, access: TripAccess, user_id: uuid.UUID, body, web_url: str) -> Invite:
    if access.role != "owner" and not (body.role == "viewer" and access.trip.editors_can_invite):
        raise ApiError(403, "insufficient_role", "You do not have permission to do that.")
    # The trip row lock makes two concurrent invites count one after the other, so the slot check below cannot be raced.
    # shortcut: the 20 open and 30 a day counts live here until the rate-limit layer lands (WF-028).
    session.execute(text(LOCK_TRIP), {"t": access.trip.id})
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
    caps = trips_service.trip_capabilities(session, access.trip)
    if not caps.can_invite:
        raise _no_slot(session, caps.max_collaborators)
    # An open link may only admit as many people as there are free slots, so one link cannot slip past a Free trip's limit.
    max_uses = min(body.max_uses, max(caps.max_collaborators - caps.collaborators_used, 1))
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
                "m": 1 if body.email else max_uses,
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
    # A link can outlive the plan that issued it: lock the trip and refuse a join that would pass the limit (rolls the redeem back).
    session.execute(text(LOCK_TRIP), {"t": trip_id})
    _, limits = billing.trip_limits(session, trip_id)
    limit = billing.limit_of(limits, "collaborators")
    members = session.execute(text("SELECT count(*) FROM trip_members WHERE trip_id = :t AND role <> 'owner'"), {"t": trip_id}).scalar_one()
    if members > limit:
        raise _no_slot(session, limit)
    if person_id:  # best effort: a traveler that is not on the trip is ignored, the join stands
        session.execute(text("SELECT link_my_traveler(:t, :p)"), {"t": trip_id, "p": person_id})
    return trip_id


# --- share links (WF-025.2) ------------------------------------------------------------------

MAX_ACTIVE_SHARE_LINKS = 5
_LINK_COLS = "id, redact_address, redact_prices, redact_notes, redact_people, show_book_slide, indexable, created_at, expires_at, view_count, revoked_at"


def _link(row, url: str | None = None) -> ShareLink:
    return ShareLink(
        id=row["id"],
        url=url,
        redact=Redact(hotel_address=row["redact_address"], prices=row["redact_prices"], notes=row["redact_notes"], people=row["redact_people"]),
        show_book_slide=row["show_book_slide"],
        indexable=row["indexable"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        view_count=row["view_count"],
        revoked_at=row["revoked_at"],
    )


def _check_indexable(indexable: bool, redact: Redact) -> None:
    if indexable and not (redact.people and redact.notes and redact.hotel_address):
        raise ApiError(
            422,
            "validation_failed",
            "A page search engines can list must keep people, notes and hotel address hidden.",
            extra={"errors": [{"field": "indexable", "code": "invalid", "message": "Keep people, notes and hotel address hidden to allow search engines."}]},
        )


def list_share_links(session: Session, trip_id: uuid.UUID) -> list[ShareLink]:
    rows = session.execute(
        text(f"SELECT {_LINK_COLS} FROM trip_share_links WHERE trip_id = :t ORDER BY created_at DESC, id DESC"), {"t": trip_id}
    ).mappings()
    return [_link(r) for r in rows]


def _require_free_slot(session: Session, trip_id: uuid.UUID, excluding: uuid.UUID | None = None) -> None:
    """At most 5 active links per trip. The trip row lock makes two concurrent writers count one after the other."""
    session.execute(text("SELECT 1 FROM trips WHERE id = :t FOR UPDATE"), {"t": trip_id})
    active = session.execute(
        text(
            "SELECT count(*) FROM trip_share_links WHERE trip_id = :t AND revoked_at IS NULL AND expires_at > now() "
            "AND id IS DISTINCT FROM CAST(:x AS uuid)"
        ),
        {"t": trip_id, "x": excluding},
    ).scalar_one()
    if active >= MAX_ACTIVE_SHARE_LINKS:
        raise ApiError(409, "state_conflict", f"This trip has {MAX_ACTIVE_SHARE_LINKS} active share links. Revoke one first.")


def create_share_link(session: Session, access: TripAccess, user_id: uuid.UUID, body, web_url: str) -> ShareLink:
    _check_indexable(body.indexable, body.redact)
    _require_free_slot(session, access.trip.id)
    token = secrets.token_urlsafe(16)  # 128 bits
    row = (
        session.execute(
            text(
                "INSERT INTO trip_share_links (trip_id, created_by, token_hash, redact_address, redact_prices, redact_notes, redact_people, "
                "  show_book_slide, indexable, expires_at) "
                "VALUES (:t, :u, :h, :a, :p, :n, :pe, :b, :i, now() + make_interval(days => :d)) RETURNING " + _LINK_COLS
            ),
            {
                "t": access.trip.id,
                "u": user_id,
                "h": token_hash(token),
                "a": body.redact.hotel_address,
                "p": body.redact.prices,
                "n": body.redact.notes,
                "pe": body.redact.people,
                "b": body.show_book_slide,
                "i": body.indexable,
                "d": body.expires_in_days,
            },
        )
        .mappings()
        .one()
    )
    return _link(row, f"{web_url.rstrip('/')}/s/{token}")


def update_share_link(session: Session, trip_id: uuid.UUID, link_id: uuid.UUID, body) -> ShareLink:
    session.execute(text("SELECT 1 FROM trips WHERE id = :t FOR UPDATE"), {"t": trip_id})
    cur = (
        session.execute(text(f"SELECT {_LINK_COLS} FROM trip_share_links WHERE id = :i AND trip_id = :t FOR UPDATE"), {"i": link_id, "t": trip_id})
        .mappings()
        .first()
    )
    if cur is None:
        raise NotFound()
    if cur["revoked_at"] is not None:
        raise ApiError(409, "state_conflict", "That link is revoked. Create a new one.")
    r = body.redact
    redact = Redact(
        hotel_address=cur["redact_address"] if r is None or r.hotel_address is None else r.hotel_address,
        prices=cur["redact_prices"] if r is None or r.prices is None else r.prices,
        notes=cur["redact_notes"] if r is None or r.notes is None else r.notes,
        people=cur["redact_people"] if r is None or r.people is None else r.people,
    )
    indexable = cur["indexable"] if body.indexable is None else body.indexable
    _check_indexable(indexable, redact)
    if body.expires_in_days is not None and cur["expires_at"] <= session.execute(text("SELECT now()")).scalar_one():
        _require_free_slot(session, trip_id, excluding=link_id)  # extending an expired link makes it active again
    row = (
        session.execute(
            text(
                "UPDATE trip_share_links SET redact_address = :a, redact_prices = :p, redact_notes = :n, redact_people = :pe, indexable = :i, "
                "  show_book_slide = CASE WHEN CAST(:b AS boolean) IS NULL THEN show_book_slide ELSE CAST(:b AS boolean) END, "
                "  expires_at = CASE WHEN CAST(:d AS integer) IS NULL THEN expires_at ELSE now() + make_interval(days => CAST(:d AS integer)) END "
                "WHERE id = :id RETURNING " + _LINK_COLS
            ),
            {"a": redact.hotel_address, "p": redact.prices, "n": redact.notes, "pe": redact.people, "i": indexable, "b": body.show_book_slide, "d": body.expires_in_days, "id": link_id},
        )
        .mappings()
        .one()
    )
    return _link(row)


def revoke_share_link(session: Session, trip_id: uuid.UUID, link_id: uuid.UUID) -> None:
    if not session.execute(
        text("UPDATE trip_share_links SET revoked_at = COALESCE(revoked_at, now()) WHERE id = :i AND trip_id = :t RETURNING id"),
        {"i": link_id, "t": trip_id},
    ).first():
        raise NotFound()


def _t(v) -> str | None:
    return None if v is None else str(v)


def view_shared(settings, token: str) -> tuple[SharedTrip, bool]:
    """Public read for GET /shared/{token}: one statement finds a live link and stamps the view; one 410 for every bad token.
    Returns the page and whether the link is indexable. Redacted fields are nulled here, never sent and hidden later."""
    with db.system_session("share_view", settings=settings, route="GET /v1/shared/{token}") as s:
        link = (
            s.execute(
                text(
                    "UPDATE trip_share_links l SET view_count = view_count + 1, last_viewed_at = now() "
                    " WHERE l.token_hash = :h AND l.revoked_at IS NULL AND l.expires_at > now() "
                    "   AND EXISTS (SELECT 1 FROM trips t WHERE t.id = l.trip_id AND t.deleted_at IS NULL) "
                    "RETURNING l.trip_id, l.redact_address, l.redact_prices, l.redact_notes, l.redact_people, l.show_book_slide, l.indexable"
                ),
                {"h": token_hash(token)},
            )
            .mappings()
            .first()
        )
        if link is None:
            raise ApiError(410, "share_link_revoked", "This link is no longer available. Ask the owner for a new one.")
        tid = {"t": link["trip_id"]}
        trip = s.execute(text("SELECT id, name, start_date, end_date, cover_image_url FROM trips WHERE id = :t"), tid).mappings().one()
        dests = s.execute(text("SELECT name, region, country, country_code FROM trip_destinations WHERE trip_id = :t ORDER BY position"), tid).mappings().all()
        people = (
            s.execute(
                text("SELECT p.name FROM trip_people tp JOIN people p ON p.id = tp.person_id WHERE tp.trip_id = :t ORDER BY p.is_self DESC, p.created_at, p.id"),
                tid,
            )
            .scalars()
            .all()
        )
        days = (
            s.execute(
                text(
                    "SELECT d.day, d.title, d.notes, td.name AS destination_name FROM itinerary_days d "
                    "LEFT JOIN trip_destinations td ON td.id = d.destination_id WHERE d.trip_id = :t ORDER BY d.day"
                ),
                tid,
            )
            .mappings()
            .all()
        )
        items = (
            s.execute(
                text(
                    "SELECT id, day, start_time, end_time, title, category, status, location_name, address, lat, lon, url, notes, "
                    "       estimated_cost_minor, cost_currency, source, check_url, checked_at FROM itinerary_items WHERE trip_id = :t AND day IS NOT NULL "
                    "ORDER BY day, start_time NULLS LAST, sort_order, id"
                ),
                tid,
            )
            .mappings()
            .all()
        )
        stays = (
            s.execute(
                text(
                    "SELECT id, title, status, check_in, check_out, location_name, lat, lon, price_total_minor, price_per_night_minor, currency "
                    "FROM lodging_options WHERE trip_id = :t AND status = 'booked' ORDER BY check_in NULLS LAST, id"
                ),
                tid,
            )
            .mappings()
            .all()
        )
        generated = s.execute(text("SELECT now()")).scalar_one()

    addr, price, note = link["redact_address"], link["redact_prices"], link["redact_notes"]
    by_day: dict[str, list] = {}
    for it in items:
        lodging = it["category"] == "lodging"  # only lodging items carry a place the address flag hides; sights keep their coordinates for the map
        by_day.setdefault(str(it["day"]), []).append(
            {
                "id": it["id"],
                "start_time": _t(it["start_time"]),
                "end_time": _t(it["end_time"]),
                "title": it["title"],
                "category": it["category"],
                "status": it["status"],
                "location_name": None if addr and lodging else it["location_name"],
                "address": None if addr and lodging else it["address"],
                "lat": None if addr and lodging else it["lat"],
                "lon": None if addr and lodging else it["lon"],
                "url": it["url"],
                "notes": "" if note else it["notes"],
                "estimated_cost_minor": None if price else it["estimated_cost_minor"],
                "cost_currency": None if price else it["cost_currency"],
                "source": it["source"],
                "check_url": it["check_url"],
                "checked_at": it["checked_at"],
            }
        )
    day_rows = {str(d["day"]): d for d in days}
    out_days = [
        {
            "day": k,
            "title": day_rows[k]["title"] if k in day_rows else "",
            "notes": "" if note or k not in day_rows else day_rows[k]["notes"],
            "destination_name": day_rows[k]["destination_name"] if k in day_rows else None,
            "items": by_day.get(k, []),
        }
        for k in sorted(set(day_rows) | set(by_day))
    ]
    out_stays = [
        {
            "id": st["id"],
            "title": st["title"],
            "status": st["status"],
            "check_in": _t(st["check_in"]),
            "check_out": _t(st["check_out"]),
            "location_name": None if addr else st["location_name"],
            "lat": None if addr else st["lat"],
            "lon": None if addr else st["lon"],
            "price_total_minor": None if price else st["price_total_minor"],
            "price_per_night_minor": None if price else st["price_per_night_minor"],
            "currency": None if price else st["currency"],
        }
        for st in stays
    ]
    page = SharedTrip(
        trip_name=trip["name"],
        presentation=Presentation(
            trip={
                "id": trip["id"],
                "name": trip["name"],
                "start_date": _t(trip["start_date"]),
                "end_date": _t(trip["end_date"]),
                "cover": trip["cover_image_url"],
                "destinations": [dict(d) for d in dests],
                "travelers": [f"Traveler {i}" for i in range(1, len(people) + 1)] if link["redact_people"] else list(people),
            },
            days=out_days,
            stays=out_stays,
            book_slide_enabled=link["show_book_slide"],
            generated_at=generated,
        ),
        cta={"url": settings.public_web_url.rstrip("/")},
        # shortcut: flights ([]), weather (null) and the checklist (0 of 0) are stubs until the flights, weather and checklist tickets
        # feed the presentation (WF-091 presentation mode); the flights ticket must hide fare prices when redact_prices is on.
        # shortcut: the "Book the plan" offers and the Free-tier "Made with Hermi" footer arrive with the affiliate and presentation tickets.
        book_slide=None,
    )
    return page, link["indexable"]
