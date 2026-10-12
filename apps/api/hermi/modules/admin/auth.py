# ruff: noqa: E501  (long SQL and comments)
"""/v1/admin/auth: the 2FA session, step-up and enrolment (08 sections 2.2 and 8).

Every route here sits behind Cloudflare Access plus an enabled admin row (the same chain as the rest of /v1/admin).
Sign-in and enrolment ask for no 2FA session (that is what they create); everything else in /v1/admin does (identity.require).
Failures all answer 401 `two_factor_failed` with one message, so a caller learns nothing about which factor exists.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text

from hermi.errors import ApiError
from hermi.modules.admin import mfa, permissions, sessions
from hermi.modules.admin.identity import AdminPrincipal, _count_failure, require, require_session
from hermi.modules.notifications.waitlist import client_ip
from hermi.security import rate_limit
from hermi.security.webauthn import WebAuthnError

log = logging.getLogger("hermi.admin")
router = APIRouter(prefix="/auth")


class AdminIdentity(BaseModel):
    user_id: str
    email: str
    role: str
    mfa_enrolled: bool


class TwoFactor(BaseModel):
    enrolled: bool
    fresh: bool  # a WebAuthn or TOTP check inside the last 5 minutes on this session


class Factors(BaseModel):
    passkeys: int
    totp: bool
    recovery_codes_left: int


class AdminSession(BaseModel):
    admin: AdminIdentity
    permissions: dict[str, str]  # name -> level (R, r, W, X) for every permission the role holds
    two_factor: TwoFactor
    signed_in: bool  # a live 2FA session cookie (8 h absolute, 30 min idle)
    expires_at: datetime | None
    fresh_until: datetime | None
    factors: Factors


def _view(request: Request, admin: AdminPrincipal, session: sessions.AdminSession | None) -> AdminSession:
    now = sessions.now(request)
    return AdminSession(
        admin=AdminIdentity(user_id=str(admin.user_id), email=admin.email, role=admin.role, mfa_enrolled=admin.mfa_enrolled),
        permissions=permissions.for_role(admin.role),
        two_factor=TwoFactor(enrolled=admin.mfa_enrolled, fresh=bool(session and session.is_fresh(now))),
        signed_in=session is not None,
        expires_at=session.expires_at if session else None,
        fresh_until=session.fresh_until() if session and session.is_fresh(now) else None,
        factors=Factors(**mfa.factors(request, admin.user_id)),
    )


def _audit(request: Request, admin: AdminPrincipal, action: str, *, result: str = "ok", error_code: str | None = None, after: dict | None = None) -> None:
    """shortcut: written inline like admin_users.py. WF-059 moves it into the audit writer. Best effort: a failed write is
    logged and never blocks (or fakes) the sign-in itself."""
    try:
        with sessions.engine(request).begin() as c:
            c.execute(
                text(
                    "INSERT INTO audit_log (actor_user_id, actor_type, actor_role, action, entity_type, entity_id, after, result, error_code, "
                    "request_id, user_agent, retention_class) VALUES (:a, 'admin', CAST(:role AS admin_role), :action, 'admin_user', :e, "
                    "CAST(:after AS jsonb), :res, :err, :rid, :ua, 'extended')"
                ),
                {
                    "a": admin.user_id,
                    "role": admin.role,
                    "action": action,
                    "e": str(admin.user_id),
                    "after": json.dumps(after) if after else None,
                    "res": result,
                    "err": error_code,
                    "rid": getattr(request.state, "request_id", None),
                    "ua": (request.headers.get("user-agent") or "")[:200] or None,
                },
            )
    except Exception:
        log.exception("admin auth audit write failed")


def _failed() -> ApiError:
    return ApiError(401, "two_factor_failed", "That did not work. Check it and try again.")


def _enrol_guard(request: Request, admin: AdminPrincipal) -> None:
    """Enrolling the first factors needs only the Access identity (the invitee signs in through SSO and registers, 08 2.2).
    Once enrolled, adding or replacing a factor needs a live session with a fresh step-up (428 otherwise). A recovery code
    session is never a step-up, but it may do this one thing in its first 5 minutes (break-glass re-enrolment, 08 2.2)."""
    if admin.mfa_enrolled:
        require_session(request, admin, fresh=True, break_glass=True)


def _enrolled(request: Request, admin: AdminPrincipal) -> dict:
    now = mfa.refresh_enrolled(request, admin.user_id)
    request.app.state.admin_directory.invalidate(admin.user_id)
    return {"mfa_enrolled": now}


# --- session -----------------------------------------------------------------------------------------------


@router.get("/session", response_model=AdminSession)
def session(request: Request, admin: Annotated[AdminPrincipal, require("auth.session", two_factor=False)]) -> AdminSession:
    """Who is signed in and whether 2FA is done and fresh. Reading it does not keep the session alive."""
    return _view(request, admin, sessions.current(request, admin.user_id, touch=False) if admin.mfa_enrolled else None)


class Assertion(BaseModel):
    credential_id: str = Field(max_length=1400)  # base64url, as the browser returns them
    client_data_json: str = Field(max_length=4096)
    authenticator_data: str = Field(max_length=4096)
    signature: str = Field(max_length=2048)


class Proof(BaseModel):
    method: Literal["webauthn", "totp", "recovery"]
    challenge_id: uuid.UUID | None = None
    assertion: Assertion | None = None
    code: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _shape(self):
        if self.method == "webauthn" and (self.challenge_id is None or self.assertion is None):
            raise ValueError("A passkey check needs challenge_id and assertion.")
        if self.method != "webauthn" and not (self.code or "").strip():
            raise ValueError("Send the code.")
        return self


class Challenge(BaseModel):
    purpose: Literal["signin", "stepup"]


class ChallengeOut(BaseModel):
    challenge_id: str
    public_key: dict  # PublicKeyCredentialRequestOptions, base64url fields


@router.post("/webauthn/options", response_model=ChallengeOut)
def webauthn_options(
    body: Challenge, request: Request, admin: Annotated[AdminPrincipal, require("auth.signin", write=True, two_factor=False)]
) -> ChallengeOut:
    if not admin.mfa_enrolled:
        raise ApiError(403, "mfa_enrollment_required", "Set up two-factor sign-in to continue.")
    if body.purpose == "stepup":
        require_session(request, admin)
    cid, options = mfa.assertion_options(request, admin, body.purpose)
    return ChallengeOut(challenge_id=str(cid), public_key=options)


def _prove(request: Request, admin: AdminPrincipal, body: Proof, purpose: str) -> str:
    """Check the second factor and return the method that passed, or raise the one generic 401."""
    try:
        if body.method == "webauthn":
            a = body.assertion
            mfa.assertion_verify(
                request,
                admin.user_id,
                purpose,
                body.challenge_id,
                credential_id=a.credential_id,
                client_data_json=a.client_data_json,
                authenticator_data=a.authenticator_data,
                signature=a.signature,
            )
            return "webauthn"
        if body.method == "totp":
            if mfa.totp_check(request, admin.user_id, body.code):
                return "totp"
        elif purpose == "signin":  # a recovery code opens a session; it is not a step-up factor
            left = mfa.recovery_consume(request, admin.user_id, body.code)
            if left is not None:
                # Break-glass (08 2.2): the alert rule pages the owner on this logger and message.
                log.warning("admin_break_glass", extra={"admin_id": str(admin.user_id), "admin_role": admin.role, "codes_left": left})
                _audit(request, admin, "admin_session.break_glass", after={"codes_left": left})
                return "recovery"
    except WebAuthnError as e:
        log.warning("admin_2fa_failed", extra={"admin_id": str(admin.user_id), "method": body.method, "reason": e.code})
        _audit(request, admin, f"admin_session.{purpose}", result="denied", error_code=e.code)
        _count_failure(request)  # the per-IP failed-login limit (10 section 2.3); over it this is a 429
        raise _failed() from None
    log.warning("admin_2fa_failed", extra={"admin_id": str(admin.user_id), "method": body.method, "reason": "no_match"})
    _audit(request, admin, f"admin_session.{purpose}", result="denied", error_code="no_match")
    _count_failure(request)
    raise _failed()


@router.post("/signin", response_model=AdminSession)
def signin(
    body: Proof,
    request: Request,
    response: Response,
    admin: Annotated[AdminPrincipal, require("auth.signin", write=True, rate="admin_signin", two_factor=False)],
) -> AdminSession:
    """The second step of sign-in: a passkey assertion, a TOTP code or a recovery code opens the 2FA session (cookie)."""
    if not admin.mfa_enrolled:
        raise ApiError(403, "mfa_enrollment_required", "Set up two-factor sign-in to continue.")
    try:
        rate_limit.hit(request.app.state.admin_engine, "admin_signin_ip", client_ip(request))
    except ApiError as e:
        if e.status == 429:
            log.warning("admin_2fa_lockout", extra={"rate_class": "admin_signin_ip", "admin_id": str(admin.user_id)})
        raise
    method = _prove(request, admin, body, "signin")
    s = sessions.start(request, response, admin.user_id, method)
    _audit(request, admin, "admin_session.signin", after={"method": method})
    return _view(request, admin, s)


@router.post("/stepup", response_model=AdminSession)
def stepup(
    body: Proof,
    request: Request,
    admin: Annotated[AdminPrincipal, require("auth.stepup", write=True, rate="admin_stepup")],
) -> AdminSession:
    """A fresh WebAuthn or TOTP check on a live session; valid 5 minutes. 10 attempts an hour, then 429 and an alert."""
    s = sessions.current(request, admin.user_id, touch=False)
    if s is None:  # the dependency just saw it; it ended in between
        raise ApiError(401, "two_factor_required", "Confirm it is you to continue.")
    method = _prove(request, admin, body, "stepup")
    sessions.mark_fresh(request, s)
    _audit(request, admin, "admin_session.stepup", after={"method": method})
    return _view(request, admin, sessions.current(request, admin.user_id, touch=False))


@router.post("/signout", status_code=204)
def signout(request: Request, response: Response, admin: Annotated[AdminPrincipal, require("auth.signout", write=True, two_factor=False)]) -> Response:
    sessions.end(request, response, admin.user_id)
    response.status_code = 204
    return response


# --- enrolment ---------------------------------------------------------------------------------------------


class RegisterOptions(BaseModel):
    challenge_id: str
    public_key: dict  # PublicKeyCredentialCreationOptions, base64url fields


class RegisterIn(BaseModel):
    challenge_id: uuid.UUID
    client_data_json: str = Field(max_length=4096)
    attestation_object: str = Field(max_length=8192)
    label: str = Field(default="Passkey", max_length=60)


class Enrolled(BaseModel):
    mfa_enrolled: bool


@router.post("/webauthn/register/options", response_model=RegisterOptions)
def register_options(request: Request, admin: Annotated[AdminPrincipal, require("auth.enrol", write=True, two_factor=False)]) -> RegisterOptions:
    _enrol_guard(request, admin)
    cid, options = mfa.register_options(request, admin)
    return RegisterOptions(challenge_id=str(cid), public_key=options)


@router.post("/webauthn/register/verify", response_model=Enrolled)
def register_verify(
    body: RegisterIn, request: Request, admin: Annotated[AdminPrincipal, require("auth.enrol", write=True, two_factor=False)]
) -> Enrolled:
    _enrol_guard(request, admin)
    try:
        mfa.register_verify(request, admin, body.challenge_id, body.client_data_json, body.attestation_object, body.label.strip() or "Passkey")
    except WebAuthnError as e:
        log.warning("admin_passkey_registration_failed", extra={"admin_id": str(admin.user_id), "reason": e.code})
        raise ApiError(422, "registration_failed", "We could not register that passkey. Try again.") from None
    _audit(request, admin, "admin_credential.enrol", after={"kind": "webauthn"})
    return Enrolled(**_enrolled(request, admin))


class TotpBegin(BaseModel):
    secret: str  # base32, shown once for manual entry
    otpauth_uri: str


class CodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=16)


@router.post("/totp/enrol", response_model=TotpBegin)
def totp_enrol(request: Request, admin: Annotated[AdminPrincipal, require("auth.enrol", write=True, two_factor=False)]) -> TotpBegin:
    """Start a TOTP enrolment (the fallback factor). It counts only after `/totp/confirm` accepts a first code."""
    _enrol_guard(request, admin)
    secret, uri = mfa.totp_begin(request, admin)
    return TotpBegin(secret=secret, otpauth_uri=uri)


@router.post("/totp/confirm", response_model=Enrolled)
def totp_confirm(body: CodeIn, request: Request, admin: Annotated[AdminPrincipal, require("auth.enrol", write=True, two_factor=False)]) -> Enrolled:
    _enrol_guard(request, admin)
    if not mfa.totp_confirm(request, admin.user_id, body.code):
        log.warning("admin_totp_confirm_failed", extra={"admin_id": str(admin.user_id)})
        raise ApiError(422, "registration_failed", "That code did not match. Check the time on your phone and try again.")
    _audit(request, admin, "admin_credential.enrol", after={"kind": "totp"})
    return Enrolled(**_enrolled(request, admin))


class RecoveryCodes(BaseModel):
    codes: list[str]  # shown once; only salted hashes are kept
    mfa_enrolled: bool


@router.post("/recovery-codes", response_model=RecoveryCodes)
def recovery_codes(request: Request, admin: Annotated[AdminPrincipal, require("auth.enrol", write=True, two_factor=False)]) -> RecoveryCodes:
    """A new set of 10 single-use codes; any earlier set stops working. Print them and keep them offline."""
    _enrol_guard(request, admin)
    codes = mfa.recovery_generate(request, admin.user_id)
    _audit(request, admin, "admin_credential.recovery_codes", after={"count": len(codes)})
    return RecoveryCodes(codes=codes, **_enrolled(request, admin))
