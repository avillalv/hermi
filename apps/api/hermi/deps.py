# ruff: noqa: E501  (long comments and SQL)
"""Request dependencies: the bearer token, the signed-in user and the per-request database transaction (02 section 3)."""

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.db import request_transaction
from hermi.errors import ApiError, NotFound
from hermi.logging_setup import bind
from hermi.modules.collaboration.models import TripMember
from hermi.modules.trips import repo as trips_repo
from hermi.modules.trips.models import Trip
from hermi.security.jwt import TokenError, VerifiedToken


@dataclass(frozen=True)
class AuthUser:
    id: uuid.UUID
    status: str


def verified_token(request: Request) -> VerifiedToken:
    """A valid bearer token. Needs no users row, so POST /me/bootstrap (WF-013.2) can use it."""
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    try:
        if scheme.lower() != "bearer" or not token.strip():
            raise TokenError()
        return request.app.state.verifier.verify(token.strip())
    except TokenError as e:
        raise ApiError(
            401,
            e.code,
            "Your session ended. Sign in again."
            if e.code == "token_expired"
            else "Sign in to continue.",
            {"WWW-Authenticate": "Bearer"},
        ) from None


def identity_user(request: Request, token: VerifiedToken) -> AuthUser | None:
    # app.user_id is not set yet and row-level security hides auth_identities, so the lookup is a definer function.
    with request.app.state.engine.connect() as conn:
        row = conn.execute(
            text("SELECT user_id, status FROM resolve_identity(:p, :s)"),
            {"p": token.provider, "s": token.subject},
        ).first()
    return AuthUser(row[0], row[1]) if row else None


def user_dependency(*, allow_pending_deletion: bool = False) -> Callable[..., AuthUser]:
    def current_user(
        request: Request, token: Annotated[VerifiedToken, Depends(verified_token)]
    ) -> AuthUser:
        user = identity_user(request, token)
        if user is None:
            raise ApiError(
                401,
                "unauthenticated",
                "Finish sign-up to continue.",
                {"WWW-Authenticate": "Bearer"},
            )
        bind(user_id=str(user.id))
        if user.status == "pending_deletion" and allow_pending_deletion:
            return user
        if user.status == "pending_deletion":
            raise ApiError(
                403,
                "account_pending_deletion",
                "This account is scheduled for deletion. You can cancel that.",
            )
        if user.status != "active":
            raise ApiError(403, "account_inactive", "This account is not active. Contact support.")
        return user

    return current_user


CurrentUser = Annotated[AuthUser, Depends(user_dependency())]
# For the routes that still work in the 30 day grace period (GET /me, POST /me/deletion/cancel).
CurrentUserOrPendingDeletion = Annotated[
    AuthUser, Depends(user_dependency(allow_pending_deletion=True))
]


def _db_session(request: Request, user: CurrentUser) -> Iterator[Session]:
    with request_transaction(request.app.state.engine, user.id) as session:
        yield session


def _db_session_grace(request: Request, user: CurrentUserOrPendingDeletion) -> Iterator[Session]:
    with request_transaction(request.app.state.engine, user.id) as session:
        yield session


DbSession = Annotated[Session, Depends(_db_session)]
# The same transaction for the routes that still work in the grace period (GET /me, POST /me/deletion/cancel).
DbSessionOrPendingDeletion = Annotated[Session, Depends(_db_session_grace)]


ROLE_RANK = {"viewer": 0, "editor": 1, "owner": 2}


@dataclass(frozen=True)
class TripAccess:
    trip: Trip
    member: TripMember
    role: str
    capabilities: frozenset[str]


def capabilities_for(role: str) -> frozenset[str]:
    rank = ROLE_RANK[role]
    return frozenset(c for c, need in (("can_edit", 1), ("can_manage", 2)) if rank >= need)


def require_trip(min_role: str = "viewer", *, trashed: bool = False):
    """Depends() for a route with {trip_id}: the caller's TripAccess, 404 when not a member or the trip is in trash,
    403 insufficient_role when the role is below min_role (02 section 3 step 5, 04 section 1.2).

    The route path must name the parameter `{trip_id}`; a child-id route resolves the child, then calls
    trips_repo with its trip id. `trashed=True` finds only trips in the trash (the restore route) and never a live one."""
    if min_role not in ROLE_RANK:
        raise ValueError(f"min_role must be one of {sorted(ROLE_RANK)}")

    def access(trip_id: uuid.UUID, session: DbSession) -> TripAccess:
        user_id = session.execute(text("SELECT app_user_id()")).scalar()
        found = trips_repo.get_trip_with_member(session, trip_id, user_id, trashed=trashed)
        if found is None:
            raise NotFound()
        trip, member = found
        if ROLE_RANK[member.role] < ROLE_RANK[min_role]:
            raise ApiError(403, "insufficient_role", "You do not have permission to do that.")
        return TripAccess(trip, member, member.role, capabilities_for(member.role))

    access.__require_trip__ = min_role  # the route walk in tests/test_tenancy.py looks for this
    return Depends(access)
