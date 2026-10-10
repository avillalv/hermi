# ruff: noqa: E501  (long comments and docstrings)
"""Auth routes: POST /v1/me/bootstrap, GET /v1/me and the dev routes (04 sections 1.2 and 5.1)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text

from hermi import analytics
from hermi.deps import (
    CurrentUser,
    CurrentUserOrPendingDeletion,
    DbSession,
    DbSessionOrPendingDeletion,
    identity_user,
    verified_token,
)
from hermi.errors import ApiError
from hermi.modules.ai import agent_runs
from hermi.modules.auth import guest, repo, service
from hermi.modules.auth.schemas import (
    BootstrapIn,
    Consent,
    ConsentIn,
    ConsentKind,
    DevSessionIn,
    DevSessionOut,
    LegacyClaimIn,
    Me,
    PersonaOut,
)
from hermi.security import rate_limit
from hermi.security.jwt import VerifiedToken

router = APIRouter(tags=["auth"])
# Mounted by main.create_app only when AUTH_MODE=dev and ENVIRONMENT is local or ci, so it is not in the production OpenAPI.
dev_router = APIRouter(prefix="/dev", tags=["dev"])
router.include_router(guest.router)  # App Attest challenge and attestation, and the one guest AI route (WF-062.1)


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
            opted_out=request.headers.get("sec-gpc")
            == "1",  # Global Privacy Control (10 section 4)
        )
    return me


@router.post(
    "/me/legacy-claim", response_model=Me, responses={410: {"description": "claim_link_expired"}}
)
def legacy_claim(
    body: LegacyClaimIn,
    request: Request,
    token: Annotated[VerifiedToken, Depends(verified_token)],
) -> Me:
    """No users row needed, like bootstrap. Attaches the signed-in identity to the pre-created legacy account."""
    if request.app.state.engine is None:
        raise ApiError(500, "internal_error", "Something went wrong on our side. Try again.")
    rate_limit.check_signup(request, None)  # shortcut: shares the signup_ip bucket; give it its own class if claims and signups need different limits
    return service.redeem_legacy_claim(request.app.state.engine, token, body)


@router.get("/me", response_model=Me)
def get_me(user: CurrentUserOrPendingDeletion, session: DbSessionOrPendingDeletion) -> Me:
    return service.get_me(session, user.id)


@router.get("/me/consents", response_model=list[Consent])
def list_consents(user: CurrentUser, session: DbSession) -> list[dict]:
    """The latest row per kind, withdrawals included (04 section 5.2)."""
    return repo.latest_consents(session, user.id)


@router.put("/me/consents/{kind}", response_model=Consent)
def put_consent(
    kind: ConsentKind, body: ConsentIn, request: Request, user: CurrentUser, session: DbSession
) -> dict:
    """Appends a `consents` row. Withdrawing `ai_processing` makes every AI route answer `ai_consent_required` (the gate reads
    the latest row) and stops this person's agent runs (fare hunt and deep research only; inline actions finish and settle on their own) (04 section 5.2). Nothing else is switched off."""
    rate_limit.hit(request.app.state.engine, "write_user", str(user.id))
    row = repo.append_consent(session, user.id, kind, body.version, body.granted)
    if kind == "ai_processing" and not body.granted:
        active = (
            session.execute(
                text(
                    "UPDATE runs SET cancel_requested = true WHERE user_id = :u AND status IN ('queued', 'running') "
                    "AND kind IN ('fare_hunt', 'deep_research') "
                    "RETURNING id, status::text AS status"
                ),
                {"u": user.id},
            )
            .mappings()
            .all()
        )
        queued = [r["id"] for r in active if r["status"] == "queued"]
        if queued:
            session.commit()  # the consent row and the flags are visible to a worker that claims a run right now
            session.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": str(user.id)})
            for rid in queued:
                agent_runs.cancel_queued(request.app.state.settings, rid, user.id)
    return row


@dev_router.get("/personas", response_model=list[PersonaOut])
def personas() -> list[PersonaOut]:
    return list(service.PERSONAS.values())


@dev_router.post("/session", response_model=DevSessionOut)
def session(body: DevSessionIn, request: Request) -> DevSessionOut:
    return service.dev_session(request.app.state.settings, request.app.state.engine, body.persona)
