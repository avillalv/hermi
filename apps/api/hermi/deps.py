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
from hermi.errors import ApiError
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


def _identity_user(request: Request, token: VerifiedToken) -> AuthUser | None:
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
        user = _identity_user(request, token)
        if user is None:
            raise ApiError(
                401,
                "unauthenticated",
                "Finish sign-up to continue.",
                {"WWW-Authenticate": "Bearer"},
            )
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
