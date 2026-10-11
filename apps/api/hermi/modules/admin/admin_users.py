# ruff: noqa: E501  (long SQL)
"""Admin users and roles (08 section 8: GET and POST /admin-users, PATCH /admin-users/{id}). Owner only.

Step-up 2FA on role changes (08 section 2.2) arrives with WF-058.2; the routes are the audited writes it will guard.
"""

import json
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import ApiError, NotFound
from hermi.modules.admin import permissions
from hermi.modules.admin.identity import (
    AdminPrincipal,
    admin_transaction,
    idempotency_key,
    require,
)
from hermi.pagination import decode_offset, encode_offset

router = APIRouter(prefix="/admin-users")
Role = Literal[*permissions.ROLES]  # the five 08 roles, one list
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)]
Email = Annotated[str, StringConstraints(strip_whitespace=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$")]
MANAGE = "admin_users.manage"

_SELECT = (
    "SELECT a.user_id, u.email::text AS email, a.role::text AS role, a.mfa_enrolled, a.created_by, a.disabled_at, a.created_at "
    "FROM admin_users a JOIN users u ON u.id = a.user_id"
)


class AdminUserOut(BaseModel):
    user_id: uuid.UUID
    email: str
    role: Role
    mfa_enrolled: bool
    created_by: uuid.UUID | None
    disabled_at: datetime | None
    created_at: datetime


class AdminUserList(BaseModel):
    items: list[AdminUserOut]
    next_cursor: str | None


class Written(BaseModel):
    """Every admin write answers with its result and the audit row id (08 section 8)."""

    result: AdminUserOut
    audit_id: str


class InviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: Email
    role: Role
    reason: Reason


class PatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role | None = None
    disabled: bool | None = Field(default=None, description="true disables the admin, false enables again")
    reason: Reason


def _snapshot(row) -> dict:
    return {"role": row["role"], "disabled": row["disabled_at"] is not None}


def _audit(s: Session, request: Request, admin: AdminPrincipal, *, action: str, target: uuid.UUID, before, after, reason: str) -> str:
    """shortcut: written inline, like flags.py. WF-059 moves this into the audit writer (redaction, denied rows)."""
    return str(
        s.execute(
            text(
                "INSERT INTO audit_log (actor_user_id, actor_type, actor_role, action, entity_type, entity_id, before, after, reason, "
                "request_id, user_agent, retention_class) VALUES (:actor, 'admin', CAST(:role AS admin_role), :action, 'admin_user', :target, "
                "CAST(:before AS jsonb), CAST(:after AS jsonb), :reason, :rid, :ua, 'extended') RETURNING id"
            ),
            {
                "actor": admin.user_id,
                "role": admin.role,
                "action": action,
                "target": str(target),
                "before": None if before is None else json.dumps(before),
                "after": json.dumps(after),
                "reason": reason,
                "rid": getattr(request.state, "request_id", None),
                "ua": (request.headers.get("user-agent") or "")[:200] or None,
            },
        ).scalar_one()
    )


def _load(s: Session, user_id: uuid.UUID, *, lock: bool = False):
    return s.execute(text(_SELECT + " WHERE a.user_id = :u" + (" FOR UPDATE OF a" if lock else "")), {"u": user_id}).mappings().first()


@router.get("", response_model=AdminUserList)
def list_admin_users(
    request: Request,
    _: Annotated[AdminPrincipal, require(MANAGE)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> AdminUserList:
    offset = decode_offset(cursor)
    with admin_transaction(request) as s:
        rows = s.execute(
            text(_SELECT + " ORDER BY a.created_at, a.user_id LIMIT :n OFFSET :o"), {"n": limit + 1, "o": offset}
        ).mappings().all()
    more = len(rows) > limit
    return AdminUserList(items=[AdminUserOut(**r) for r in rows[:limit]], next_cursor=encode_offset(offset + limit) if more else None)


@router.post("", response_model=Written, status_code=201)
def invite_admin_user(
    body: InviteIn,
    request: Request,
    admin: Annotated[AdminPrincipal, require(MANAGE, write=True)],
    _key: Annotated[str, Depends(idempotency_key)],
) -> Written:
    """Give an existing account an admin role. There is no sign-up path to admin: the person needs a Hermi account, and
    still signs in through Cloudflare Access (08 section 2.2). 2FA enrolment and activation arrive with WF-058.2."""
    with admin_transaction(request) as s:
        uid = s.execute(
            text("SELECT id FROM users WHERE email = :e AND deleted_at IS NULL AND status = 'active'"), {"e": body.email.lower()}
        ).scalar()
        if uid is None:
            raise ApiError(422, "account_required", "That person needs a Hermi account first. Ask them to sign in to the app once.")
        inserted = s.execute(
            text(
                "INSERT INTO admin_users (user_id, role, created_by) VALUES (:u, CAST(:r AS admin_role), :by) "
                "ON CONFLICT (user_id) DO NOTHING RETURNING user_id"
            ),
            {"u": uid, "r": body.role, "by": admin.user_id},
        ).first()
        if inserted is None:
            raise ApiError(409, "already_admin", "That person already has an admin role. Change it instead.")
        row = _load(s, uid)
        audit_id = _audit(
            s, request, admin, action="admin_user.invite", target=uid, before=None, after=_snapshot(row), reason=body.reason
        )
        out = AdminUserOut(**row)
    return Written(result=out, audit_id=audit_id)


@router.patch("/{user_id}", response_model=Written)
def patch_admin_user(
    user_id: uuid.UUID,
    body: PatchIn,
    request: Request,
    admin: Annotated[AdminPrincipal, require(MANAGE, write=True)],
    _key: Annotated[str, Depends(idempotency_key)],
) -> Written:
    """Change one thing: the role, or enabled versus disabled. An admin cannot change their own row, so the last owner
    can never lock the console out."""
    if (body.role is None) == (body.disabled is None):
        raise ApiError(
            422,
            "validation_failed",
            "Some fields need another look.",
            extra={"errors": [{"field": "role", "code": "one_of", "message": "Send either role or disabled."}]},
        )
    if user_id == admin.user_id:
        raise ApiError(409, "cannot_modify_self", "You cannot change your own admin access.")
    with admin_transaction(request) as s:
        before = _load(s, user_id, lock=True)
        if before is None:
            raise NotFound()
        owners_left = s.execute(
            text(
                "SELECT count(*) FROM admin_users WHERE role = 'owner' AND disabled_at IS NULL AND user_id <> :u"
            ),
            {"u": user_id},
        ).scalar_one()
        leaves_owner = before["role"] == "owner" and before["disabled_at"] is None and (
            (body.role is not None and body.role != "owner") or body.disabled is True
        )
        if leaves_owner and owners_left == 0:
            raise ApiError(409, "last_owner", "There must be at least one enabled owner.")
        if body.role is not None:
            action = "admin_user.role_change"
            s.execute(
                text("UPDATE admin_users SET role = CAST(:r AS admin_role) WHERE user_id = :u"), {"r": body.role, "u": user_id}
            )
        else:
            action = "admin_user.disable" if body.disabled else "admin_user.enable"
            s.execute(
                text("UPDATE admin_users SET disabled_at = CASE WHEN :d THEN coalesce(disabled_at, now()) END WHERE user_id = :u"),
                {"d": body.disabled, "u": user_id},
            )
        after = _load(s, user_id)
        audit_id = _audit(
            s, request, admin, action=action, target=user_id, before=_snapshot(before), after=_snapshot(after), reason=body.reason
        )
        out = AdminUserOut(**after)
    request.app.state.admin_directory.invalidate(user_id)  # this process stops honouring the old role at once
    return Written(result=out, audit_id=audit_id)
