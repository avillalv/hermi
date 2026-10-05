# ruff: noqa: E501  (long comments and docstrings)
"""Auth routes: POST /v1/me/bootstrap, GET /v1/me and the dev routes (04 sections 1.2 and 5.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from hermi import analytics
from hermi.deps import (
    CurrentUserOrPendingDeletion,
    DbSessionOrPendingDeletion,
    identity_user,
    verified_token,
)
from hermi.errors import ApiError
from hermi.modules.auth import service
from hermi.modules.auth.schemas import BootstrapIn, DevSessionIn, DevSessionOut, Me, PersonaOut
from hermi.security import rate_limit
from hermi.security.jwt import VerifiedToken

router = APIRouter(tags=["auth"])
# Mounted by main.create_app only when AUTH_MODE=dev and ENVIRONMENT is local or ci, so it is not in the production OpenAPI.
dev_router = APIRouter(prefix="/dev", tags=["dev"])


@router.post(
    "/me/bootstrap",
    response_model=Me,
    status_code=201,
    responses={200: {"model": Me, "description": "The account already existed"}},
)
def bootstrap(
    body: BootstrapIn,
    request: Request,
    response: Response,
    token: Annotated[VerifiedToken, Depends(verified_token)],
) -> Me:
    if request.app.state.engine is None:
        raise ApiError(500, "internal_error", "Something went wrong on our side. Try again.")
    if identity_user(request, token) is None:
        rate_limit.check_signup(request, token.email)
    me, created = service.bootstrap(request.app.state.engine, token, body)
    response.status_code = 201 if created else 200
    if created:
        # shortcut: invite, referral and guest claim are not part of bootstrap yet (WF-040, referral ticket), so those
        # three are False. Fill them in when those fields land.
        analytics.capture(
            "signup_completed",
            me.id,
            {
                "method": "email_code" if token.provider == "email" else token.provider,
                "from_invite": False,
                "from_referral": False,
                "was_guest": False,
                "tier": me.tier,
                "is_guest": False,
            },
            opted_out=request.headers.get("sec-gpc") == "1",  # Global Privacy Control (10 section 4)
        )
    return me


@router.get("/me", response_model=Me)
def get_me(user: CurrentUserOrPendingDeletion, session: DbSessionOrPendingDeletion) -> Me:
    return service.get_me(session, user.id)


@dev_router.get("/personas", response_model=list[PersonaOut])
def personas() -> list[PersonaOut]:
    return list(service.PERSONAS.values())


@dev_router.post("/session", response_model=DevSessionOut)
def session(body: DevSessionIn, request: Request) -> DevSessionOut:
    return service.dev_session(request.app.state.settings, request.app.state.engine, body.persona)
