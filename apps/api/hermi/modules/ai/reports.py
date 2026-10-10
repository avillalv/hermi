# ruff: noqa: E501  (long SQL strings)
"""POST /v1/reports (04 section 5.14): "Report a problem" on an agent note or an AI answer, and the thumbs down on AI output.

The write goes through `file_content_report` (0014), which checks the caller can see the target, copies the cache key from the
run, expires a reported cache entry and flags it at three distinct reporters. One report per person per target: a repeat
returns the first report's id and creates nothing. The moderation queue screen is WF-106."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator
from sqlalchemy import text

from hermi.deps import CurrentUser, DbSession
from hermi.errors import NotFound
from hermi.security import rate_limit

router = APIRouter(tags=["reports"])


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    reason: Literal["spam", "harmful", "wrong_info", "copyright", "privacy"]
    detail: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""

    @model_validator(mode="after")
    def _one_target(self) -> "ReportIn":
        if (self.note_id is None) == (self.run_id is None):
            raise ValueError("Send exactly one of note_id and run_id.")
        return self


class ReportOut(BaseModel):
    id: uuid.UUID


@router.post("/reports", status_code=201, response_model=ReportOut)
def create_report(body: ReportIn, request: Request, response: Response, user: CurrentUser, session: DbSession) -> dict:
    target_type, col, ref = ("agent_note", "note_id", body.note_id) if body.note_id else ("ai_answer", "run_id", body.run_id)
    # shortcut: read then insert with no unique index, so two concurrent posts from one person can both file a report.
    # Upgrade trigger: duplicates seen in the queue. Fix: a partial unique index on (reporter_user_id, run_id) and (reporter_user_id, note_id), then ON CONFLICT.
    # The own-row read policy hides everyone else's reports, so this finds only this person's earlier report.
    prior = session.execute(
        text(f"SELECT id FROM content_reports WHERE reporter_user_id = :u AND {col} = :r ORDER BY created_at LIMIT 1"),  # noqa: S608 (col is one of two literals)
        {"u": user.id, "r": ref},
    ).scalar()
    if prior is not None:
        response.status_code = 200
        return {"id": prior}
    rate_limit.hit(request.app.state.engine, "report", str(user.id))
    seen = session.execute(
        text("SELECT EXISTS (SELECT 1 FROM runs WHERE id = :r AND trip_id IN (SELECT visible_trip_ids()))")
        if body.run_id
        else text("SELECT EXISTS (SELECT 1 FROM notes WHERE id = :r AND kind = 'agent' AND NOT is_private AND trip_id IN (SELECT visible_trip_ids()))"),
        {"r": ref},
    ).scalar()
    if not seen:
        raise NotFound()
    rid = session.execute(
        text("SELECT file_content_report(:t, :r, :reason, :d)"),
        {"t": target_type, "r": str(ref), "reason": body.reason, "d": body.detail},
    ).scalar_one()
    return {"id": rid}
