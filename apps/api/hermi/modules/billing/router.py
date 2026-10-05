"""GET /v1/me/entitlements (04 section 5.19)."""

import hashlib

from fastapi import APIRouter, Request, Response

from hermi.deps import CurrentUser, DbSession
from hermi.modules.billing import service
from hermi.modules.billing.schemas import Entitlements

router = APIRouter(tags=["billing"])


@router.get("/me/entitlements", response_model=Entitlements)
def get_entitlements(request: Request, response: Response, user: CurrentUser, session: DbSession):
    body = service.get_entitlements(session, user.id)
    etag = '"' + hashlib.sha256(body.model_dump_json().encode()).hexdigest()[:16] + '"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return body
