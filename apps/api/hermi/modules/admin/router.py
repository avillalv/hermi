# ruff: noqa: E501  (long comments)
"""The /v1/admin router (08 section 2.1): its own OpenAPI tag, its own dependency chain (Cloudflare Access assertion, then
an enabled admin row, then the permission) and its own rate limits. `X-Robots-Tag: noindex` is added by
AdminHeadersMiddleware so errors carry it too."""

from typing import Annotated

from fastapi import APIRouter, Request
from pydantic import BaseModel

from hermi.modules.admin import admin_users, permissions
from hermi.modules.admin.admin_users import Email
from hermi.modules.admin.identity import AdminPrincipal, require
from hermi.security.jwt import mint_access_token

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(admin_users.router)
# Mounted by main.create_app only when ADMIN_AUTH_MODE=dev and ENVIRONMENT is local or ci (absent from every other OpenAPI).
dev_router = APIRouter(prefix="/dev", tags=["dev"])


class AdminIdentity(BaseModel):
    user_id: str
    email: str
    role: str
    mfa_enrolled: bool


class TwoFactor(BaseModel):
    enrolled: bool
    fresh: bool  # a WebAuthn or TOTP check inside the last 5 minutes; always false until WF-058.2 lands step-up


class AdminSession(BaseModel):
    admin: AdminIdentity
    permissions: dict[str, str]  # name -> level (R, r, W, X) for every permission the role holds
    two_factor: TwoFactor


@router.get("/auth/session", response_model=AdminSession)
def session(admin: Annotated[AdminPrincipal, require("auth.session")]) -> AdminSession:
    return AdminSession(
        admin=AdminIdentity(user_id=str(admin.user_id), email=admin.email, role=admin.role, mfa_enrolled=admin.mfa_enrolled),
        permissions=permissions.for_role(admin.role),
        two_factor=TwoFactor(enrolled=admin.mfa_enrolled, fresh=False),
    )


class DevAdminIn(BaseModel):
    email: Email


class DevAdminOut(BaseModel):
    assertion: str


@dev_router.post("/admin-session", response_model=DevAdminOut, include_in_schema=False)
def dev_admin_session(body: DevAdminIn, request: Request) -> DevAdminOut:
    """The fake-Access signer: an assertion the admin routes verify with the real code. Send it as Cf-Access-Jwt-Assertion."""
    return DevAdminOut(assertion=mint_access_token(request.app.state.settings, body.email))
