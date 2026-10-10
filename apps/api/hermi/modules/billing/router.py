# ruff: noqa: E501  (long SQL strings)
"""GET /v1/me/entitlements and GET /v1/me/credits (04 section 5.19)."""

import hashlib
import uuid
from typing import Literal

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

from hermi.deps import CurrentUser, DbSession
from hermi.errors import NotFound
from hermi.modules.billing import service
from hermi.modules.billing.schemas import CreditsNow, Entitlements
from hermi.modules.credits import repo as credit_repo
from hermi.modules.credits import service as credits

router = APIRouter(tags=["billing"])


@router.get("/me/entitlements", response_model=Entitlements)
def get_entitlements(request: Request, response: Response, user: CurrentUser, session: DbSession):
    body = service.get_entitlements(session, user.id)
    etag = '"' + hashlib.sha256(body.model_dump_json().encode()).hexdigest()[:16] + '"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    response.headers["ETag"] = etag
    return body


@router.get("/me/credits", response_model=CreditsNow)
def get_credits(
    user: CurrentUser,
    session: DbSession,
    trip_id: uuid.UUID | None = None,
    action: Literal["explain", "live_search", "draft_day", "draft_trip", "research", "agent_run", "verify_plan"] = "explain",
) -> CreditsNow:
    """The balance for one action and, with `trip_id`, the Trip Pass pool its role may spend. A trip the caller is not on is 404."""
    if trip_id is not None and not session.execute(
        text("SELECT 1 FROM trip_members WHERE trip_id = :t AND user_id = :u"), {"t": trip_id, "u": user.id}
    ).first():
        raise NotFound
    credit_repo.ensure_free_monthly_grant(session, user.id)  # a Free account sees its allowance before it first spends
    price = credits.table_price(session, action)
    b = credits.balance(session, user.id, trip_id=trip_id, action=action, price=price)
    return CreditsNow(
        **service.credit_balance(session, user.id).model_dump(),
        available=b.available,
        own=b.own,
        pool=b.pool,
        payer=b.payer,
        version=b.version,
    )
