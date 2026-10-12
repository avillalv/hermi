# ruff: noqa: E501  (long comments)
"""The /v1/admin router (08 section 2.1): its own OpenAPI tag, its own dependency chain (Cloudflare Access assertion, then
an enabled admin row, then the permission, then a 2FA session) and its own rate limits. `X-Robots-Tag: noindex` is added by
AdminHeadersMiddleware so errors carry it too."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from hermi.modules.admin import admin_users, auth
from hermi.modules.admin.admin_users import Email
from hermi.modules.admin.identity import write_guard
from hermi.security.jwt import mint_access_token

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(write_guard)])
router.include_router(auth.router)
router.include_router(admin_users.router)
# Mounted by main.create_app only when ADMIN_AUTH_MODE=dev and ENVIRONMENT is local or ci (absent from every other OpenAPI).
dev_router = APIRouter(prefix="/dev", tags=["dev"])


class DevAdminIn(BaseModel):
    email: Email


class DevAdminOut(BaseModel):
    assertion: str


@dev_router.post("/admin-session", response_model=DevAdminOut, include_in_schema=False)
def dev_admin_session(body: DevAdminIn, request: Request) -> DevAdminOut:
    """The fake-Access signer: an assertion the admin routes verify with the real code. Send it as Cf-Access-Jwt-Assertion."""
    return DevAdminOut(assertion=mint_access_token(request.app.state.settings, body.email))
