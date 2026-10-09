# ruff: noqa: E501
"""AI one-shot actions (04 section 5.12): explain, packing list, draft day and draft trip.

Each route is an editor route behind the `ai` gate. The Idempotency-Key header is required by the middleware and is part
of the credit reservation key, so a retry never charges twice. Nothing here saves trip data: results are previews."""

import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, ConfigDict, StringConstraints

from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.modules.ai.features import drafts, explain, packing_list
from hermi.modules.ai.features.base import flag_runtime
from hermi.security import rate_limit

router = APIRouter(tags=["ai"])

Text300 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Idem = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]


class ExplainContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: uuid.UUID | None = None
    lodging_id: uuid.UUID | None = None
    place_id: Annotated[str, StringConstraints(max_length=200)] | None = None


class ExplainIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    context: ExplainContext | None = None


class PackingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferences: Text300 | None = None


class DraftDayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    day: date
    preferences: Text300 | None = None
    replace: bool = False
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    interests: list[Annotated[str, StringConstraints(max_length=40)]] | None = None


class DraftTripIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    style: Text300 | None = None
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"
    interests: list[Annotated[str, StringConstraints(max_length=40)]] | None = None
    from_day: date | None = None  # drafts at most 14 days from here; the trip start when absent


def _common(request: Request, user: CurrentUser, key: str) -> dict:
    rate_limit.hit(request.app.state.engine, "ai", str(user.id))
    return {
        "settings": request.app.state.settings, "flags": flag_runtime(request.app),
        "user_id": user.id, "idempotency_key": key,
    }


@router.post("/trips/{trip_id}/ai/explain")
def explain_route(
    body: ExplainIn, request: Request, session: DbSession, user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")], key: Idem,
) -> dict:
    ref = body.context.model_dump(mode="json", exclude_none=True) if body.context else {}
    done = explain.execute(session, trip_id=access.trip.id, question=body.question, subject_ref=ref, **_common(request, user, key))
    return {**done.output, "credits": done.receipt.public()}


@router.post("/trips/{trip_id}/ai/packing-list")
def packing_list_route(
    body: PackingIn, request: Request, session: DbSession, user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")], key: Idem,
) -> dict:
    done = packing_list.execute(session, trip_id=access.trip.id, preferences=body.preferences, **_common(request, user, key))
    return {**done.output, "credits": done.receipt.public()}


@router.post("/trips/{trip_id}/ai/draft-day")
def draft_day_route(
    body: DraftDayIn, request: Request, session: DbSession, user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")], key: Idem,
) -> dict:
    done = drafts.draft_day(
        session, trip_id=access.trip.id, day=body.day, preferences=body.preferences, pace=body.pace,
        interests=body.interests, **_common(request, user, key),
    )
    return {**done.output, "credits": done.receipt.public()}


@router.post("/trips/{trip_id}/ai/draft-trip", status_code=202)
def draft_trip_route(
    body: DraftTripIn, request: Request, session: DbSession, user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")], key: Idem,
) -> dict:
    """04 shapes this as a polled job. shortcut: it runs inline (one call, seconds) and returns the finished job, so a
    client that polls sees status `done` at once. Ceiling: a call that outlives the request timeout. Trigger: the AI job
    table and GET /ai/jobs/{id}, which no ticket in this step builds."""
    done = drafts.draft_trip(
        session, trip_id=access.trip.id, from_day=body.from_day, preferences=body.style, pace=body.pace,
        interests=body.interests, **_common(request, user, key),
    )
    return {
        "id": str(done.run_id), "kind": "draft_trip", "status": "done", "result": done.output, "error_code": None,
        "credits": done.receipt.public(),
    }
