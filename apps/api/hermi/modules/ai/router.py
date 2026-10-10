# ruff: noqa: E501
"""AI one-shot actions (04 section 5.12): explain, packing list, draft day and draft trip, and agent runs (5.13).

Each route is an editor route behind the `ai` gate. The Idempotency-Key header is required by the middleware and is part
of the credit reservation key, so a retry never charges twice. Nothing here saves trip data: results are previews."""

import asyncio
import json
import threading
import time
import uuid
from collections import Counter
from collections.abc import AsyncIterator
from datetime import date, datetime
from typing import Annotated, Any, Literal

import anyio.to_thread
from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy import text

from hermi.db import request_transaction
from hermi.deps import ROLE_RANK, CurrentUser, DbSession, TripAccess, require_trip
from hermi.errors import ApiError, NotFound
from hermi.modules.ai import agent_runs, research
from hermi.modules.ai.features import drafts, explain, packing_list, recheck
from hermi.modules.ai.features.base import flag_runtime
from hermi.modules.collaboration.schemas import Attribution
from hermi.modules.itinerary.router import via_item
from hermi.modules.trips.notes import via_note
from hermi.pagination import decode_offset, encode_offset
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


class ResearchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: Literal["destination_brief", "events_and_closures", "reservations_needed", "getting_around", "seasonal_notes"] = "destination_brief"
    question: Text300 | None = None  # a custom question bypasses the shared cache
    # shortcut: accepted (04 5.12) and ignored. Ceiling: scope does not narrow the research, which always covers the destination
    # for the trip dates. Trigger: when the research prompt takes a scope.
    scope: Literal["destination", "dates", "lodging"] | None = None


def _common(request: Request, user: CurrentUser, key: str) -> dict:
    rate_limit.hit(request.app.state.engine, "ai", str(user.id))
    return {
        "settings": request.app.state.settings,
        "flags": flag_runtime(request.app),
        "user_id": user.id,
        "idempotency_key": key,
    }


@router.post("/trips/{trip_id}/ai/explain")
def explain_route(
    body: ExplainIn,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")],
    key: Idem,
) -> dict:
    ref = body.context.model_dump(mode="json", exclude_none=True) if body.context else {}
    done = explain.execute(
        session,
        trip_id=access.trip.id,
        question=body.question,
        subject_ref=ref,
        **_common(request, user, key),
    )
    return {**done.output, "run_id": str(done.run_id), "credits": done.receipt.public()}


def _recheck(kind: Literal["note", "item"], target_id: uuid.UUID, request: Request, session, user, access, key: str) -> dict:
    """04 5.14: one fetch of the stored source and one Haiku call. Editors and owners at any age; the `ai` gate runs inside."""
    return recheck.execute(session, kind=kind, target_id=target_id, trip_id=access.trip.id, **_common(request, user, key))


@router.post("/notes/{note_id}/recheck")
def recheck_note_route(
    note_id: uuid.UUID, request: Request, session: DbSession, user: CurrentUser, access: Annotated[TripAccess, via_note("editor")], key: Idem
) -> dict:
    return _recheck("note", note_id, request, session, user, access, key)


@router.post("/items/{item_id}/recheck")
def recheck_item_route(
    item_id: uuid.UUID, request: Request, session: DbSession, user: CurrentUser, access: Annotated[TripAccess, via_item("editor")], key: Idem
) -> dict:
    return _recheck("item", item_id, request, session, user, access, key)


@router.post("/trips/{trip_id}/ai/packing-list")
def packing_list_route(
    body: PackingIn,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")],
    key: Idem,
) -> dict:
    done = packing_list.execute(
        session, trip_id=access.trip.id, preferences=body.preferences, **_common(request, user, key)
    )
    return {**done.output, "run_id": str(done.run_id), "credits": done.receipt.public()}


@router.post("/trips/{trip_id}/ai/draft-day")
def draft_day_route(
    body: DraftDayIn,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")],
    key: Idem,
) -> dict:
    done = drafts.draft_day(
        session,
        trip_id=access.trip.id,
        day=body.day,
        preferences=body.preferences,
        pace=body.pace,
        interests=body.interests,
        **_common(request, user, key),
    )
    return {**done.output, "run_id": str(done.run_id), "credits": done.receipt.public()}


@router.post("/trips/{trip_id}/ai/draft-trip", status_code=202)
def draft_trip_route(
    body: DraftTripIn,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")],
    key: Idem,
) -> dict:
    """04 shapes this as a polled job. shortcut: it runs inline (one call, seconds) and returns the finished job, so a
    client that polls sees status `done` at once. Ceiling: a call that outlives the request timeout. Trigger: the AI job
    table and GET /ai/jobs/{id}, which no ticket in this step builds."""
    done = drafts.draft_trip(
        session,
        trip_id=access.trip.id,
        from_day=body.from_day,
        preferences=body.style,
        pace=body.pace,
        interests=body.interests,
        **_common(request, user, key),
    )
    return {
        "id": str(done.run_id),
        "kind": "draft_trip",
        "status": "done",
        "result": done.output,
        "error_code": None,
        "credits": done.receipt.public(),
    }


@router.post("/trips/{trip_id}/ai/research", status_code=202)
def research_route(
    body: ResearchIn,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")],
    key: Idem,
) -> dict:
    """04 5.12 `ResearchJob`. Same inline shortcut as draft-trip: the executor commits and returns the finished job (a cache
    hit charges 1 and reports `from_cache`). Its notes are saved to the trip with their sources, as in an agent run.
    shortcut: it runs inline, holding a request thread for up to the 90 s cache wait. Ceiling: concurrent research requests
    against the threadpool size. Trigger: move it to a job on the `ai` lane and poll GET /ai/jobs/{id}."""
    done = research.execute(
        session,
        trip_id=access.trip.id,
        topic=body.topic,
        question=body.question or None,
        **_common(request, user, key),
    )
    return {
        "id": str(done.run_id),
        "kind": "research",
        "status": "done",
        "result": done.output,
        "error_code": None,
        "credits": done.receipt.public(),
    }


# --- agent runs (04 section 5.13) -----------------------------------------------------------------------------------


class AgentRunStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["fare_hunt", "deep_research"]
    route_ids: list[uuid.UUID] | None = None  # fare_hunt: 1 to 3 routes of the trip
    topic: str | None = None  # deep_research, up to 300 characters
    instructions: str | None = None  # up to 2000 characters, untrusted text


class CreditReceipt(BaseModel):
    action: str
    reserved: int
    charged: int | None
    from_cache: bool
    balance_after: int | None
    reservation_id: uuid.UUID | None


class AgentRun(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    kind: Literal["fare_hunt", "deep_research"]
    status: Literal[
        "queued",
        "running",
        "succeeded",
        "partial",
        "failed",
        "timed_out",
        "cancelled",
        "interrupted",
    ]
    started_by: Attribution | None
    params: dict[str, Any]
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    summary: str | None
    error_code: str | None
    accepted_count: int
    rejected_count: int
    turns_used: int | None
    searches_used: int | None
    fetches_used: int | None
    from_cache: bool
    is_taster: bool
    credits: CreditReceipt | None  # the starter's receipt; other members see none
    cancel_requested: bool
    events_url: str


class AgentRunDetail(AgentRun):
    cost_usd_micros: int | None = None  # the starter only


class AgentRunPage(BaseModel):
    items: list[AgentRun]
    next_cursor: str | None
    has_more: bool


class RunEvent(BaseModel):
    seq: int
    ts: str
    type: Literal[
        "run.started",
        "turn",
        "tool.search",
        "tool.fetch",
        "fare.saved",
        "note.saved",
        "fare.rejected",
        "budget",
        "warning",
        "run.finished",
    ]
    tool_name: str | None
    summary: str
    payload: dict[str, Any] | None


class AgentRunPreview(BaseModel):
    kind: Literal["fare_hunt", "deep_research"]
    credits: int  # what this start costs the person: 0 on the taster
    price: int  # the table price, shown once the taster is spent
    taster: bool
    taster_used: bool
    balance: int
    sufficient: bool
    from_cache: bool


class AgentTaster(BaseModel):
    used: bool
    used_at: datetime | None
    run_id: uuid.UUID | None
    available: bool
    credits: int


def _via_run(min_role: str):
    """Depends() resolving the trip of a run id, then the same `require_trip` check (404 for a stranger, 403 for a low role)."""
    check = require_trip(min_role).dependency

    def access(session: DbSession, run_id: uuid.UUID) -> TripAccess:
        trip_id = session.execute(
            text(
                "SELECT trip_id FROM runs WHERE id = :i AND kind IN ('fare_hunt', 'deep_research')"
            ),
            {"i": run_id},
        ).scalar()
        if trip_id is None:
            raise NotFound()
        return check(trip_id, session)

    access.__require_trip__ = min_role  # type: ignore[attr-defined]
    return Depends(access)


@router.get("/trips/{trip_id}/agent-runs/preview", response_model=AgentRunPreview)
def agent_runs_preview(
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")],
    kind: Literal["fare_hunt", "deep_research"] = "deep_research",
) -> dict:
    return agent_runs.preview(session, user_id=user.id, trip_id=access.trip.id, kind=kind)


@router.post("/trips/{trip_id}/agent-runs", status_code=202, response_model=AgentRun)
def agent_runs_start(
    body: AgentRunStart,
    request: Request,
    response: Response,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("editor")],
    key: Idem,
) -> dict:
    c = _common(request, user, key)
    rid = agent_runs.start(
        session,
        settings=c["settings"],
        flags=c["flags"],
        user_id=user.id,
        trip_id=access.trip.id,
        idempotency_key=key,
        kind=body.kind,
        route_ids=body.route_ids,
        topic=body.topic,
        instructions=body.instructions,
    )
    response.headers["Location"] = f"/v1/agent-runs/{rid}"
    return agent_runs.detail(session, rid, user.id)


@router.get("/trips/{trip_id}/agent-runs", response_model=AgentRunPage)
def agent_runs_list(
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, require_trip("viewer")],
    status: str | None = None,
    kind: Literal["fare_hunt", "deep_research"] | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> dict:
    start = decode_offset(cursor)
    items, more = agent_runs.list_runs(
        session, access.trip.id, user.id, status=status, kind=kind, limit=limit, offset=start
    )
    return {
        "items": items,
        "next_cursor": encode_offset(start + limit) if more else None,
        "has_more": more,
    }


@router.get("/agent-runs/{run_id}", response_model=AgentRunDetail)
def agent_runs_get(
    run_id: uuid.UUID,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, _via_run("viewer")],
) -> dict:
    agent_runs.sweep(request.app.state.settings, session, run_id=run_id)
    return agent_runs.detail(session, run_id, user.id)


@router.get("/agent-runs/{run_id}/events", response_model=list[RunEvent])
def agent_runs_events(
    run_id: uuid.UUID,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, _via_run("viewer")],
    after_seq: Annotated[int, Query(ge=-1)] = -1,
    limit: Annotated[int, Query(ge=1, le=200)] = 200,
) -> list[dict]:
    """The polling fallback. `after_seq` -1 (the default) starts at `run.started`, which is seq 0."""
    agent_runs.sweep(request.app.state.settings, session, run_id=run_id)
    return agent_runs.events_after(session, run_id, after_seq, limit, user.id)[0]


@router.post("/agent-runs/{run_id}/cancel", response_model=AgentRun)
def agent_runs_cancel(
    run_id: uuid.UUID,
    request: Request,
    session: DbSession,
    user: CurrentUser,
    access: Annotated[TripAccess, _via_run("editor")],
    key: Idem,
) -> dict:
    """Sets the flag the loop checks at every checkpoint. A run still in the queue is closed at once and costs nothing."""
    settings = request.app.state.settings
    agent_runs.sweep(settings, session, run_id=run_id)
    row = agent_runs.run_row(session, run_id)
    if row["user_id"] != user.id and ROLE_RANK[access.role] < ROLE_RANK["owner"]:
        raise ApiError(
            403,
            "insufficient_role",
            "Only the person who started this run, or the trip owner, can stop it.",
        )
    if row["status"] not in ("queued", "running"):
        raise ApiError(409, "state_conflict", "This run has already finished.")
    session.execute(text("UPDATE runs SET cancel_requested = true WHERE id = :i"), {"i": run_id})
    if row["status"] == "queued":
        session.commit()  # the flag is visible to a worker that claims the run right now
        session.execute(
            text("SELECT set_config('app.user_id', :u, true)"), {"u": str(user.id)}
        )  # transaction-local: renew it
        agent_runs.cancel_queued(settings, run_id, user.id)
    return agent_runs.detail(session, run_id, user.id)


@router.get("/me/agent-taster", response_model=AgentTaster)
def agent_taster(session: DbSession, user: CurrentUser) -> dict:
    return agent_runs.taster_state(session, user.id)


# The stream. shortcut: the per-user cap of 3 open streams is counted in this process. Ceiling: one API instance; behind
# several, a user could hold 3 per instance. Trigger: a second API instance (count in rate_limit_counters then).
MAX_STREAMS = 3
POLL_SECONDS = 0.5
HEARTBEAT_SECONDS = 15.0
_open: Counter = Counter()
_open_runs: set = set()
_open_lock = threading.Lock()


def _stream_access(request: Request, run_id: uuid.UUID, user: CurrentUser) -> uuid.UUID:
    """Viewer on the run's trip, checked in a transaction of its own so no connection is held while the stream is open."""
    with request_transaction(request.app.state.engine, user.id) as s:
        found = s.execute(
            text(
                "SELECT r.trip_id FROM runs r JOIN trip_members m ON m.trip_id = r.trip_id AND m.user_id = :u "
                "WHERE r.id = :i AND r.kind IN ('fare_hunt', 'deep_research')"
            ),
            {"i": run_id, "u": user.id},
        ).scalar()
    if found is None:
        raise NotFound()
    return found


_stream_access.__require_trip__ = "viewer"  # type: ignore[attr-defined]


def _poll(engine, settings, user_id: uuid.UUID, run_id: uuid.UUID, after: int):
    """One blocking read, run on a worker thread: the watchdog check, then the events past `after` and the run row."""
    with request_transaction(engine, user_id) as s:
        agent_runs.sweep(settings, s, run_id=run_id)
        return agent_runs.events_after(s, run_id, after, 200, user_id)


async def _frames(
    engine, settings, user_id: uuid.UUID, run_id: uuid.UUID, after: int
) -> AsyncIterator[str]:
    """Async so an idle stream holds no thread: each read borrows one for its duration only, the wait is `asyncio.sleep`."""
    last_sent = time.monotonic()
    while True:
        events, row, cursor = await anyio.to_thread.run_sync(
            _poll, engine, settings, user_id, run_id, after
        )
        after = max(after, cursor)  # past every row read, shown or not
        for e in events:
            yield f"id: {e['seq']}\nevent: {e['type']}\ndata: {json.dumps(e, default=str)}\n\n"
            last_sent = time.monotonic()
            if e["type"] == "run.finished":
                return
        if row["status"] not in ("queued", "running") and not events:
            return
        if time.monotonic() - last_sent >= HEARTBEAT_SECONDS:
            yield ": heartbeat\n\n"
            last_sent = time.monotonic()
        await asyncio.sleep(POLL_SECONDS)


class _CountedStream(StreamingResponse):
    """Releases the open-stream slot when the response ends for any reason, including a client that left before the first read."""

    def __init__(self, *args, release, **kwargs):
        super().__init__(*args, **kwargs)
        self._release = release

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._release()


@router.get("/agent-runs/{run_id}/stream")
async def agent_runs_stream(
    run_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
    trip: Annotated[uuid.UUID, Depends(_stream_access)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """Server-sent events (04 section 5.13): `id` is the event seq, replay starts after `Last-Event-ID`, a heartbeat comment
    goes out every 15 seconds, and `run.finished` is always last. One stream per run per user, 3 per user."""
    try:
        after = int(last_event_id) if last_event_id not in (None, "") else -1
    except ValueError:
        after = -1
    slot = (user.id, run_id)
    with _open_lock:
        if slot in _open_runs or _open[user.id] >= MAX_STREAMS:
            raise ApiError(
                429,
                "rate_limited",
                "Too many live views are open. Close one and try again.",
                {"Retry-After": "5"},
            )
        _open[user.id] += 1
        _open_runs.add(slot)

    def release() -> None:
        with _open_lock:
            _open[user.id] -= 1
            _open_runs.discard(slot)

    return _CountedStream(
        _frames(request.app.state.engine, request.app.state.settings, user.id, run_id, after),
        release=release,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
