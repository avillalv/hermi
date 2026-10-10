# ruff: noqa: E501  (long SQL strings)
"""Agent runs (04 section 5.13, 06 sections 5.7 to 5.9): admission, reads, cancel, the event stream shape, the taster and the
watchdog. The run itself is the worker's `run_agent` job; this module only admits it and reads what it wrote.

Admission runs as the caller (RLS) in the request transaction: the one-active-run index, the ceiling check, the credit reserve
and the queued `runs` row commit together with the job. The API login may only set `runs.cancel_requested`, so the two
writes it cannot make (stop a queued run, close a run whose worker is gone) run in a SystemSession ("agent_run_control").
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi import db, jobs
from hermi.errors import ApiError, NotFound
from hermi.modules.ai.features.base import gate
from hermi.modules.ai.repo import admit_run
from hermi.modules.ai.research import sanitize
from hermi.modules.billing.paywall import TRIGGERS
from hermi.modules.credits import budget, service
from hermi.modules.credits import repo as credit_repo

log = logging.getLogger("hermi.agent_runs")

KINDS = ("fare_hunt", "deep_research")
KILL_KEY = "ai.agent_runs"
MAX_ROUTES = 3
TOPIC_MAX, INSTRUCTIONS_MAX = 300, 2_000
WATCHDOG_SECONDS = (
    8 * 60 + 60
)  # the loop's own 8 minute deadline plus a minute of grace for its settlement
LOST_SECONDS = (
    5 * 60
)  # no heartbeat for this long in the ai lane: the worker is gone (06 section 6.3 item 4)
TRIGGER = "out_of_credits_agent"

_ACTIVE = ("queued", "running")

RUN_SELECT = """
SELECT r.id, r.trip_id, r.kind::text AS kind, r.status::text AS status, r.user_id, NULLIF(p.display_name, '') AS starter_name,
       r.params, r.queued_at, r.started_at, r.finished_at, r.summary, r.failure_code, r.accepted_count, r.rejected_count,
       r.turns_used, r.searches_used, r.fetches_used, r.served_from_cache, r.cancel_requested, r.cost_usd_micros,
       (SELECT coalesce(sum(-l.delta), 0) FROM credit_ledger l WHERE l.run_id = r.id AND l.entry_type = 'reserve')::int AS reserved,
       (SELECT s.charged FROM credit_ledger s WHERE s.run_id = r.id AND s.entry_type = 'settle' ORDER BY s.id DESC LIMIT 1) AS charged,
       (SELECT l.reservation_id FROM credit_ledger l WHERE l.run_id = r.id AND l.entry_type = 'reserve' LIMIT 1) AS reservation_id,
       EXISTS (SELECT 1 FROM credit_ledger l JOIN credit_grants g ON g.id = l.grant_id
                WHERE l.run_id = r.id AND l.entry_type = 'reserve' AND g.period_key = 'taster') AS is_taster
  FROM runs r LEFT JOIN trip_member_profiles p ON p.trip_id = r.trip_id AND p.user_id = r.user_id
"""


# --- start -------------------------------------------------------------------------------------------------------


def _tier(api: Session, user_id: uuid.UUID) -> str:
    return api.execute(
        text(
            "SELECT coalesce((SELECT e.tier_code FROM entitlements e WHERE e.user_id = :u AND (e.valid_until IS NULL OR e.valid_until > now()) LIMIT 1), 'free')"
        ),
        {"u": user_id},
    ).scalar_one()


def _spendable(api: Session, user_id: uuid.UUID, trip_id: uuid.UUID) -> int:
    """Credits an agent run could draw without the taster: own grants and the trip's pass pool (07 section 5.4)."""
    return int(
        api.execute(
            text(
                """SELECT coalesce(sum(g.remaining), 0) FROM credit_grants g
                    WHERE g.remaining > 0 AND (g.expires_at IS NULL OR g.expires_at > now()) AND g.period_key IS DISTINCT FROM 'taster'
                      AND ((g.user_id = :u AND g.trip_id IS NULL)
                           OR (g.kind = 'trip_pass' AND g.trip_id = :t
                               AND EXISTS (SELECT 1 FROM trip_members m WHERE m.trip_id = :t AND m.user_id = :u AND m.role IN ('owner', 'editor'))))
                      AND (g.restricted_action IS NULL OR g.restricted_action = 'agent_run')"""
            ),
            {"u": user_id, "t": trip_id},
        ).scalar_one()
    )


def taster_state(api: Session, user_id: uuid.UUID, *, tier: str | None = None) -> dict[str, Any]:
    """The lifetime deep run (06 section 5.9). A free account gets the one-time grant at its first offer; `available` is
    Free only (reserve_credits enforces the same since 0026). `used` is a grant that
    is short of its price: spent, or held by a run in flight. A failed run that saved nothing is refunded in full, so it reads
    unused again (01 F-AI-6)."""
    tier = tier or _tier(api, user_id)
    price = service.table_price(api, "agent_run")
    if tier == "free":
        credit_repo.ensure_taster_grant(api, user_id)
    grant = api.execute(
        text(
            "SELECT remaining FROM credit_grants WHERE user_id = :u AND period_key = 'taster' AND kind = 'promo'"
        ),
        {"u": user_id},
    ).one_or_none()
    used = grant is not None and grant.remaining < price
    used_at = run_id = None
    if used:
        row = api.execute(
            text(
                """SELECT l.created_at, l.run_id FROM credit_ledger l JOIN credit_grants g ON g.id = l.grant_id
                    WHERE g.user_id = :u AND g.period_key = 'taster' AND l.entry_type = 'reserve' ORDER BY l.id DESC LIMIT 1"""
            ),
            {"u": user_id},
        ).one_or_none()
        used_at, run_id = (row.created_at, row.run_id) if row else (None, None)
    return {
        "available": tier == "free" and grant is not None and not used,
        "used": used,
        "used_at": used_at,
        "run_id": run_id,
        "credits": price,
    }


def preview(api: Session, *, user_id: uuid.UUID, trip_id: uuid.UUID, kind: str) -> dict[str, Any]:
    """What a start would cost, before it is asked (05 6.16 confirm step). The taster is deep research only (06 section 5.9)."""
    tier = _tier(api, user_id)
    price = service.table_price(api, "agent_run")
    credit_repo.ensure_free_monthly_grant(api, user_id)
    taster = taster_state(api, user_id, tier=tier)
    free_run = kind == "deep_research" and taster["available"]
    spendable = _spendable(api, user_id, trip_id)
    return {
        "kind": kind,
        "credits": 0 if free_run else price,
        "price": price,
        "taster": free_run,
        "taster_used": taster["used"],
        "balance": spendable,
        "sufficient": free_run or spendable >= price,
        "from_cache": False,
    }


def _paywall(reason: str) -> dict[str, str]:
    return {
        "trigger": TRIGGER,
        "reason": reason,
        "offer_url": f"/v1/paywall/offer?reason={reason}",
        "free_path": TRIGGERS[TRIGGER].free_path,
    }


def _check_routes(api: Session, trip_id: uuid.UUID, route_ids: list[uuid.UUID]) -> None:
    n = api.execute(
        text(
            "SELECT count(*) FROM flight_routes WHERE trip_id = :t AND id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"t": trip_id, "ids": [str(i) for i in dict.fromkeys(route_ids)]},
    ).scalar_one()
    if n != len(set(route_ids)):
        raise _invalid("route_ids", "Choose routes that are on this trip.")


def _invalid(field: str, message: str) -> ApiError:
    return ApiError(
        422,
        "validation_failed",
        "Some fields need another look.",
        extra={"errors": [{"field": field, "code": "invalid", "message": message}]},
    )


def start(
    api: Session,
    *,
    settings,
    flags,
    user_id: uuid.UUID,
    trip_id: uuid.UUID,
    idempotency_key: str,
    kind: str,
    route_ids: list[uuid.UUID] | None = None,
    topic: str | None = None,
    instructions: str | None = None,
) -> uuid.UUID:
    """Gate, validate, admit and enqueue one run in the caller's transaction (the request commits it). Returns the run id."""
    gate(
        api,
        flags,
        SimpleNamespace(kill_key=KILL_KEY),
        user_id=user_id,
        trip_id=trip_id,
        provider=settings.ai_provider,
    )  # type: ignore[arg-type]
    if kind not in KINDS:
        raise _invalid("kind", "Choose fare_hunt or deep_research.")
    params: dict[str, Any] = {}
    if kind == "fare_hunt":
        if not route_ids or len(set(route_ids)) > MAX_ROUTES:
            raise _invalid("route_ids", f"Choose 1 to {MAX_ROUTES} routes.")
        _check_routes(api, trip_id, route_ids)
        params["route_ids"] = [str(i) for i in dict.fromkeys(route_ids)]
    elif topic and len(topic.strip()) > TOPIC_MAX:
        raise _invalid("topic", f"Keep the topic under {TOPIC_MAX} characters.")
    if topic and kind == "deep_research":
        params["topic"] = sanitize(topic, TOPIC_MAX)
    if instructions and len(instructions.strip()) > INSTRUCTIONS_MAX:
        raise _invalid(
            "instructions", f"Keep the instructions under {INSTRUCTIONS_MAX} characters."
        )
    if instructions:
        params["instructions"] = sanitize(instructions, INSTRUCTIONS_MAX)

    sweep(
        settings, api, user_id=user_id
    )  # a run whose worker died must not hold the account's one slot
    tier = _tier(api, user_id)
    price = service.table_price(api, "agent_run")
    credit_repo.ensure_free_monthly_grant(api, user_id)
    taster = taster_state(api, user_id, tier=tier)
    free_run = kind == "deep_research" and taster["available"]
    # The taster is the lifetime deep run of a Free account, so a fare hunt never rides on it (06 section 5.9).
    if not free_run and tier == "free" and _spendable(api, user_id, trip_id) < price:
        reason = "agent_taster_used" if taster["used"] else "credits"
        raise ApiError(
            402,
            "payment_required" if reason == "agent_taster_used" else "insufficient_credits",
            "You do not have enough credits for this.",
            extra={
                "paywall": _paywall(reason),
                "credits": {"needed": price, "balance": _spendable(api, user_id, trip_id)},
            },
        )
    rid = admit_run(
        api,
        trip_id=trip_id,
        user_id=user_id,
        kind=kind,
        action="agent_run",
        params=json.dumps(params),
        provider=settings.ai_provider,
        model=settings.ai_model_main,
    )
    try:
        budget.admit(
            api,
            user_id=user_id,
            trip_id=trip_id,
            action="agent_run",
            idempotency_key=f"{user_id}:agent_run:{idempotency_key}",
            run_id=rid,
        )
    except ApiError as e:
        if e.code == "insufficient_credits":
            e.extra.setdefault("paywall", _paywall("credits"))
        raise
    jobs.enqueue(
        api,
        "run_agent",
        account_id=user_id,
        plan="free" if tier == "free" else "plus",
        priority=10,
        run_id=str(rid),
    )
    return rid


# --- reads -------------------------------------------------------------------------------------------------------


def run_row(api: Session, run_id: uuid.UUID):
    row = (
        api.execute(text(RUN_SELECT + " WHERE r.id = :id"), {"id": run_id}).mappings().one_or_none()
    )
    if row is None:
        raise NotFound()
    return row


def run_out(row, viewer_id: uuid.UUID, *, balance_after: int | None = None) -> dict[str, Any]:
    """04 `AgentRun`. The receipt, the taster mark and the cost belong to the starter."""
    starter = row["user_id"] == viewer_id
    params = {
        k: v
        for k, v in (row["params"] or {}).items()
        if k in ("route_ids", "topic", "instructions")
    }
    if not starter:
        params.pop(
            "instructions", None
        )  # prompts only for the starter and the owner (04 section 5.13)
    return {
        "id": row["id"],
        "trip_id": row["trip_id"],
        "kind": row["kind"],
        "status": row["status"],
        "started_by": {"id": row["user_id"], "display_name": row["starter_name"]}
        if row["user_id"]
        else None,
        "params": params,
        "queued_at": row["queued_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "summary": row["summary"],
        "error_code": row["failure_code"],
        "accepted_count": row["accepted_count"],
        "rejected_count": row["rejected_count"],
        "turns_used": row["turns_used"],
        "searches_used": row["searches_used"],
        "fetches_used": row["fetches_used"],
        "from_cache": row["served_from_cache"],
        "is_taster": bool(row["is_taster"]) and starter,
        "credits": {
            "action": "agent_run",
            "reserved": row["reserved"],
            "charged": row["charged"],
            "from_cache": row["served_from_cache"],
            "balance_after": balance_after,
            "reservation_id": row["reservation_id"],
        }
        if starter
        else None,
        "cancel_requested": row["cancel_requested"],
        "events_url": f"/v1/agent-runs/{row['id']}/stream",
    }


def detail(api: Session, run_id: uuid.UUID, viewer_id: uuid.UUID) -> dict[str, Any]:
    row = run_row(api, run_id)
    after = None
    if row["user_id"] == viewer_id:
        after = service.balance(
            api, viewer_id, trip_id=row["trip_id"], action="agent_run"
        ).available
    out = run_out(row, viewer_id, balance_after=after)
    if row["user_id"] == viewer_id:
        out["cost_usd_micros"] = row["cost_usd_micros"]
    return out


def list_runs(
    api: Session,
    trip_id: uuid.UUID,
    viewer_id: uuid.UUID,
    *,
    status: str | None,
    kind: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], bool]:
    rows = (
        api.execute(
            text(
                RUN_SELECT
                + """ WHERE r.trip_id = :t AND r.kind IN ('fare_hunt', 'deep_research')
               AND (CAST(:s AS text) IS NULL OR r.status::text = :s) AND (CAST(:k AS text) IS NULL OR r.kind::text = :k)
             ORDER BY r.queued_at DESC, r.id DESC LIMIT :n OFFSET :o"""
            ),
            {"t": trip_id, "s": status, "k": kind, "n": limit + 1, "o": offset},
        )
        .mappings()
        .all()
    )
    return [run_out(r, viewer_id) for r in rows[:limit]], len(rows) > limit


# --- events ------------------------------------------------------------------------------------------------------

_BUDGET_STOPS = {"spend_limit", "turn_limit", "search_cap", "fetch_cap", "deadline"}
_SEARCH_TOOLS = {"web_search"}
_FETCH_TOOLS = {"web_fetch"}


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def event_of(row, receipt: dict[str, Any] | None) -> dict[str, Any] | None:
    """Map one `run_events` row to the 04 `RunEvent`, or None for rows a client has no use for (tool results, model text, the
    stop row, bare tool calls). Usage payloads carry cost, so only the turn number leaves the server."""
    t, payload, tool = row["type"], row["payload"] or {}, row["tool_name"]
    kind = payload.get("kind") if isinstance(payload, dict) else None
    name: str | None = None
    out: dict[str, Any] | None = payload if isinstance(payload, dict) else None
    summary = row["summary"]
    if t == "info" and kind == "usage":
        name, out, summary = (
            "turn",
            {"turn": payload.get("turn")},
            f"Turn {payload.get('turn')}" if payload.get("turn") else "Turn",
        )
    elif t == "info" and kind == "fare_saved":
        name = "fare.saved"
    elif t == "info" and kind == "note_saved":
        name = "note.saved"
    elif t == "info" and kind == "stop" and payload.get("stop") in _BUDGET_STOPS:
        name, summary = "budget", f"Stopped: {payload.get('stop')}"
    elif t == "tool_use" and tool in _SEARCH_TOOLS:
        name = "tool.search"
    elif t == "tool_use" and tool in _FETCH_TOOLS:
        name = "tool.fetch"
    elif t == "rejection":
        name = "fare.rejected"
    elif t in ("warning", "error"):
        name = "warning"
        out = {k: v for k, v in payload.items() if k in ("kind", "error_code", "brand")} or None
    elif t == "result":
        name = "run.finished"
        out = {
            "status": payload.get("status"),
            "stop": payload.get("stop"),
            "accepted": payload.get("accepted"),
            "credits": receipt,
        }
    if name is None:
        return None
    return {
        "seq": row["seq"],
        "ts": _iso(row["ts"]),
        "type": name,
        "tool_name": tool,
        "summary": summary,
        "payload": out,
    }


def started_event(row) -> dict[str, Any] | None:
    """`run.started` has no row of its own: it is read from `runs.started_at`, always as seq 0."""
    if row["started_at"] is None:
        return None
    return {
        "seq": 0,
        "ts": _iso(row["started_at"]),
        "type": "run.started",
        "tool_name": None,
        "summary": "Run started",
        "payload": {"kind": row["kind"]},
    }


def receipt_of(row, *, starter: bool) -> dict[str, Any] | None:
    if not starter:
        return None
    return {"reserved": row["reserved"], "charged": row["charged"], "balance_after": None}


_EVENTS = text(
    """SELECT seq, ts, type, tool_name, summary, payload FROM run_events
        WHERE run_id = :r AND seq > :after
          AND (type IN ('rejection', 'warning', 'error', 'result')
               OR (type = 'tool_use' AND tool_name IN ('web_search', 'web_fetch'))
               OR (type = 'info' AND payload ->> 'kind' IN ('usage', 'fare_saved', 'note_saved')
                   OR type = 'info' AND payload ->> 'kind' = 'stop' AND payload ->> 'stop' IN ('spend_limit', 'turn_limit', 'search_cap', 'fetch_cap', 'deadline')))
        ORDER BY seq LIMIT :n"""
)  # only rows a client can show, so a long run of hidden rows never fills a page and stalls `after_seq`


def events_after(
    api: Session, run_id: uuid.UUID, after: int, limit: int, viewer_id: uuid.UUID
) -> tuple[list[dict[str, Any]], Any, int]:
    """Events past `after` in order (seq 0 is `run.started`), the run row, and the highest raw seq read (the cursor to
    resume from). The run row is read after the events so a `run.finished` always carries the settled receipt."""
    rows = list(api.execute(_EVENTS, {"r": run_id, "after": max(after, 0), "n": limit}).mappings())
    row = run_row(api, run_id)
    receipt = receipt_of(row, starter=row["user_id"] == viewer_id)
    out: list[dict[str, Any]] = []
    if after < 0 and (s := started_event(row)):
        out.append(s)
    for r in rows:
        if (e := event_of(r, receipt)) is not None:
            out.append(e)
    cursor = max([after, *(r["seq"] for r in rows)])
    terminal = row["status"] not in _ACTIVE
    if terminal and not any(e["type"] == "run.finished" for e in out):
        # a run closed without a result row (stopped in the queue by an older path): the stream still ends with one
        last = api.execute(
            text("SELECT coalesce(max(seq), 0) FROM run_events WHERE run_id = :r"), {"r": run_id}
        ).scalar_one()
        if (
            last >= after
            and not api.execute(
                text("SELECT 1 FROM run_events WHERE run_id = :r AND type = 'result' LIMIT 1"),
                {"r": run_id},
            ).first()
        ):
            out.append(
                {
                    "seq": last + 1,
                    "ts": _iso(row["finished_at"] or datetime.now(UTC)),
                    "type": "run.finished",
                    "tool_name": None,
                    "summary": row["summary"] or row["status"],
                    "payload": {
                        "status": row["status"],
                        "stop": row["failure_code"],
                        "accepted": row["accepted_count"],
                        "credits": receipt,
                    },
                }
            )
    return out, row, cursor


# --- cancel and the watchdog -------------------------------------------------------------------------------------


def _emit_result(
    sys: Session,
    run_id: uuid.UUID,
    trip_id: uuid.UUID,
    status: str,
    stop: str,
    accepted: int,
    charged: int,
) -> None:
    seq = sys.execute(
        text("SELECT coalesce(max(seq), 0) + 1 FROM run_events WHERE run_id = :r"), {"r": run_id}
    ).scalar_one()
    sys.execute(
        text(
            """INSERT INTO run_events (run_id, trip_id, seq, type, summary, payload)
               VALUES (:r, :t, :s, 'result', :sum, CAST(:p AS jsonb))"""
        ),
        {
            "r": run_id,
            "t": trip_id,
            "s": seq,
            "sum": f"{status}: {stop}",
            "p": json.dumps(
                {"status": status, "stop": stop, "accepted": accepted, "credits_charged": charged}
            ),
        },
    )


def _reservation(sys: Session, run_id: uuid.UUID):
    return sys.execute(
        text(
            "SELECT reservation_id FROM credit_ledger WHERE run_id = :r AND entry_type = 'reserve' LIMIT 1"
        ),
        {"r": run_id},
    ).scalar()


def cancel_queued(settings, run_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Stop a run that no worker has claimed: closed at once, nothing charged, the taster returned (04 5.13). The job stays in
    the queue and is skipped when it is claimed, because the run is no longer `queued`. A run already claimed is left to the loop."""
    with db.system_session(
        "agent_run_control",
        settings=settings,
        route="POST /v1/agent-runs/{run_id}/cancel",
        caller=str(user_id),
    ) as sys:
        row = sys.execute(
            text(
                """UPDATE runs SET status = 'cancelled', finished_at = now(), failure_code = 'cancelled', error = 'cancelled', cancel_requested = true
                    WHERE id = :id AND status = 'queued' RETURNING trip_id"""
            ),
            {"id": run_id},
        ).one_or_none()
        if row is None:
            return
        res = _reservation(sys, run_id)
        if res is not None:
            service.settle_stopped_agent_run(sys, res, turns_used=0, called_tools=False)
            sys.execute(
                text("UPDATE runs SET reservation_id = :r WHERE id = :id"), {"r": res, "id": run_id}
            )
        _emit_result(sys, run_id, row.trip_id, "cancelled", "cancelled", 0, 0)


_STALE = text(
    """SELECT id FROM runs WHERE status = 'running' AND kind IN ('fare_hunt', 'deep_research')
          AND (started_at < now() - make_interval(secs => :w) OR heartbeat_at < now() - make_interval(secs => :l))
          AND (CAST(:u AS uuid) IS NULL OR user_id = :u) AND (CAST(:r AS uuid) IS NULL OR id = :r)"""
)


def sweep(
    settings,
    api: Session,
    *,
    user_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    watchdog_s: int = WATCHDOG_SECONDS,
    lost_s: int = LOST_SECONDS,
) -> int:
    """The watchdog (06 section 2.3 rule 6 and 6.3 item 4). The loop stops itself at 8 minutes; this closes what a dead worker
    left: a run running past 8 minutes (and a minute) is `timed_out`, a run silent for 5 minutes is `interrupted`
    (`worker_lost`). Saved work keeps the full charge on a timeout; anything else is refunded and the taster returns.
    It runs lazily on start and on reads, with a cheap check as the caller so a SystemSession opens only when needed."""
    ids = [
        r for (r,) in api.execute(_STALE, {"w": watchdog_s, "l": lost_s, "u": user_id, "r": run_id})
    ]
    n = 0
    for rid in ids:
        with db.system_session(
            "agent_run_control",
            settings=settings,
            route="agent_run_watchdog",
            caller=str(user_id) if user_id else None,
        ) as sys:
            n += _close_stale(sys, rid, watchdog_s)
    return n


def _close_stale(sys: Session, rid: uuid.UUID, watchdog_s: int) -> int:
    row = sys.execute(
        text(
            """SELECT trip_id, (started_at < now() - make_interval(secs => :w)) AS overdue,
                      (SELECT count(*) FROM fare_observations f WHERE f.run_id = runs.id)
                    + (SELECT count(*) FROM notes n WHERE n.run_id = runs.id) AS saved
                 FROM runs WHERE id = :id AND status = 'running' FOR UPDATE"""
        ),
        {"id": rid, "w": watchdog_s},
    ).one_or_none()
    if row is None:
        return 0
    status, code = ("timed_out", "timed_out") if row.overdue else ("interrupted", "worker_lost")
    saved = int(row.saved)
    res = _reservation(sys, rid)
    charged = 0
    if res is not None:
        reserved = int(
            sys.execute(
                text(
                    "SELECT coalesce(sum(-delta), 0) FROM credit_ledger WHERE reservation_id = :r AND entry_type = 'reserve'"
                ),
                {"r": res},
            ).scalar_one()
        )
        if status == "timed_out" and saved > 0:
            charged = reserved
            service.settle(sys, res, reserved)
        else:
            service.refund(sys, res)
    sys.execute(
        text(
            """UPDATE runs SET status = CAST(:s AS run_status), finished_at = now(), failure_code = :c, error = :c, accepted_count = :a,
                      reservation_id = coalesce(:r, reservation_id) WHERE id = :id"""
        ),
        {"s": status, "c": code, "a": saved, "r": res, "id": rid},
    )
    _emit_result(
        sys,
        rid,
        row.trip_id,
        status,
        "deadline" if status == "timed_out" else "worker_lost",
        saved,
        charged,
    )
    log.warning("agent_run_closed", extra={"run": str(rid), "status": status})
    return 1
