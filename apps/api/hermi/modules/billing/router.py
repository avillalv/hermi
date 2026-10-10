# ruff: noqa: E501  (long SQL strings)
"""GET /v1/me/entitlements, GET /v1/me/credits and GET /v1/me/credits/ledger (04 section 5.19)."""

import base64
import hashlib
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import text

from hermi.deps import CurrentUser, DbSession
from hermi.errors import ApiError, NotFound
from hermi.modules.billing import service
from hermi.modules.billing.schemas import CreditsNow, Entitlements, LedgerPage
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


def _decode_ledger_cursor(value: str | None) -> tuple[datetime, int] | None:
    """Keyset cursor: the (created_at, id) of the last row of the previous page. A bad one is the 422 on `cursor`."""
    if not value:
        return None
    try:
        at, row_id = base64.urlsafe_b64decode(value.encode()).decode().split("|")
        return datetime.fromisoformat(at), int(row_id)
    except ValueError:
        raise ApiError(
            422, "validation_failed", "Some fields need another look.",
            extra={"errors": [{"field": "cursor", "code": "invalid", "message": "That page cursor is not valid."}]},
        ) from None


@router.get("/me/credits/ledger", response_model=LedgerPage)
def get_ledger(
    user: CurrentUser,
    session: DbSession,
    kind: Literal["grant", "reserve", "settle", "refund", "expire", "clawback", "adjust"] | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> dict:
    """The caller's own `credit_ledger` rows, newest first. `kind` filters `entry_type`. Paged by (created_at, id), so a
    spend that lands between two pages never repeats or skips a row."""
    after = _decode_ledger_cursor(cursor)
    rows = (
        session.execute(
            text(
                "SELECT id, reservation_id, created_at AS at, entry_type::text AS kind, delta, charged, action::text AS action, trip_id, run_id, note "
                "FROM credit_ledger WHERE user_id = :u AND (CAST(:k AS text) IS NULL OR entry_type::text = :k) "
                "AND (CAST(:ts AS timestamptz) IS NULL OR (created_at, id) < (CAST(:ts AS timestamptz), CAST(:i AS bigint))) "
                "ORDER BY created_at DESC, id DESC LIMIT :n"
            ),
            {"u": user.id, "k": kind, "n": limit + 1, "ts": after[0] if after else None, "i": after[1] if after else None},
        )
        .mappings()
        .all()
    )
    more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if more:
        last = page[-1]
        next_cursor = base64.urlsafe_b64encode(f"{last['at'].isoformat()}|{last['id']}".encode()).decode()
    return {"items": page, "next_cursor": next_cursor, "has_more": more}
