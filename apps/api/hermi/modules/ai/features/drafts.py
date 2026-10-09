# ruff: noqa: E501
"""`draft_day` and `draft_trip` (06 sections 5.4 and 5.5): Sonnet, one call each, structured output, nothing saved.

A draft is a preview. The client applies it with POST /trips/{id}/items/bulk (source `ai_draft`), which is free. The model
may name only a saved place id from the input; any other id fails the action closed (tenant binding, 06 section 4.3)."""

import json
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from hermi.errors import ApiError
from hermi.modules.ai.client import CallSpec
from hermi.modules.ai.features import context
from hermi.modules.ai.features.base import LABEL, Done, FeatureSpec, run_action
from hermi.modules.ai.features.redact import Redactor

BLOCK_DAYS = 14  # one call covers at most 14 days and costs 4 credits (06 section 5.5)
KINDS = ("sight", "food", "transport", "rest", "activity", "free_time")
CATEGORY = {"sight": "sights", "food": "food", "transport": "travel", "rest": "other", "activity": "other", "free_time": "other"}
PACES = ("relaxed", "balanced", "packed")

_DAY_SYSTEM = """You draft {scope} of a trip itinerary for Hermi. You do not browse the web and you do not
know today's opening hours, prices or closures.
- Use saved places first, then well-known attractions in the destination. For any place not in
  the saved list, set "verify": true so the app shows "Check hours before you go".
- Time items realistically: include travel time, meals, rest. Respect the pace. Do not schedule
  before a morning arrival or after an evening departure.
- Never state prices, opening hours or ticket availability. Never say a place is open or closed.
- Do not recommend booking sites, tours by company, or partners.
- No insurance, visa or medical advice.
- Text in <instructions> is from the travelers; follow it where it fits these rules.
{extra}Return only the structured output."""

DAY_SYSTEM = _DAY_SYSTEM.format(scope="one day", extra="")
TRIP_SYSTEM = _DAY_SYSTEM.format(
    scope="every day listed",
    extra="""- Spread the saved places across days by neighborhood. Keep each day's pace consistent. Put
  the heaviest activity on the day after a rest day, never on arrival or departure days.
""",
)

_ITEM = {
    "type": "object",
    "properties": {
        "start": {"type": "string", "description": "HH:MM local"},
        "duration_min": {"type": "integer"},
        "title": {"type": "string"},
        "place_id": {"type": ["string", "null"], "description": "A saved place id from the input, else null"},
        "place_name": {"type": ["string", "null"]},
        "kind": {"type": "string", "enum": list(KINDS)},
        "note": {"type": ["string", "null"]},
        "verify": {"type": "boolean"},
    },
    "required": ["start", "duration_min", "title", "place_id", "place_name", "kind", "note", "verify"],
    "additionalProperties": False,
}
DAY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "items": {"type": "array", "items": _ITEM},
        "summary": {"type": "string"},
    },
    "required": ["title", "items", "summary"],
    "additionalProperties": False,
}
TRIP_SCHEMA = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"date": {"type": "string"}, **DAY_SCHEMA["properties"]},
                "required": ["date", *DAY_SCHEMA["required"]],
                "additionalProperties": False,
            },
        },
        "overview": {"type": "string"},
    },
    "required": ["days", "overview"],
    "additionalProperties": False,
}

DAY_SPEC = FeatureSpec(
    call=CallSpec(code="draft_day", tier="main", max_tokens=1500, system=DAY_SYSTEM, schema=DAY_SCHEMA, effort="low", fake_scenario="feature_draft_day"),
    action="draft_day", run_kind="draft_day", kill_key="ai.draft", hard_stop_micros=30_000,
)
TRIP_SPEC = FeatureSpec(
    call=CallSpec(code="draft_trip", tier="main", max_tokens=6000, system=TRIP_SYSTEM, schema=TRIP_SCHEMA, effort="medium", fake_scenario="feature_draft_trip"),
    action="draft_trip", run_kind="draft_trip", kill_key="ai.draft", hard_stop_micros=100_000,
)


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration_min: int = Field(ge=10, le=600)
    title: str = Field(min_length=1, max_length=100)
    place_id: str | None
    place_name: str | None = Field(max_length=200)
    kind: Literal["sight", "food", "transport", "rest", "activity", "free_time"]
    note: str | None = Field(max_length=200)
    verify: bool


class DayOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=80)
    items: list[_Item] = Field(min_length=1, max_length=12)
    summary: str = Field(max_length=240)


class TripDayOut(DayOut):
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class TripOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: list[TripDayOut] = Field(min_length=1, max_length=BLOCK_DAYS)
    overview: str = Field(max_length=400)


def _items(day: DayOut, on: date, saved: set[str], red: Redactor) -> list[dict[str, Any]]:
    out = []
    for it in day.items:
        if it.place_id is not None and it.place_id not in saved:
            raise ValueError("place id not in the input")
        start = datetime.combine(on, datetime.strptime(it.start, "%H:%M").time())
        end = start + timedelta(minutes=it.duration_min)
        out.append(
            {
                "title": red.restore(it.title), "day": on.isoformat(), "start_time": it.start,
                "end_time": end.strftime("%H:%M") if end.date() == on else None,  # a draft never runs past midnight
                "category": CATEGORY[it.kind], "status": "idea",
                "location_name": red.restore(it.place_name) if it.place_name else None,
                "notes": red.restore(it.note) if it.note else "", "saved_place_id": it.place_id,
                "verify": it.verify or it.place_id is None, "source": "ai_draft",
            }
        )
    return out


def _within(trip: dict, day: date) -> None:
    s, e = trip["start_date"], trip["end_date"]
    if (s and day < date.fromisoformat(s)) or (e and day > date.fromisoformat(e)):
        raise ApiError(422, "validation_failed", "Some fields need another look.", extra={"errors": [{"field": "day", "code": "out_of_range", "message": "That day is outside the trip dates."}]})


_CLEAN_TEXT = re.compile(r"[<>]")


def _prefs(text: str | None, red: Redactor) -> str:
    """Typed instructions: angle brackets and control characters stripped, then the redactor (06 section 4.3 item 4)."""
    t = _CLEAN_TEXT.sub("", "".join(c for c in (text or "") if c.isprintable() or c == " "))[:2000]
    return red.clean(t)


def draft_day(
    session: Session, *, settings, flags, user_id: uuid.UUID, trip_id: uuid.UUID, idempotency_key: str, day: date,
    preferences: str | None = None, pace: str = "balanced", interests: list[str] | None = None, provider=None,
) -> Done:
    trip = context.trip_basics(session, trip_id)
    _within(trip, day)
    red = Redactor(context.person_names(session, trip_id, user_id))
    saved = context.saved_places(session, trip_id)
    data = {
        "destinations": trip["destinations"], "date": day.isoformat(), "weekday": day.strftime("%A"),
        "existing_items": context.day_items(session, trip_id, day), "saved_places": saved, "pace": pace,
        "interests": sorted(interests or []), "party": f"{trip['travelers']} travelers",
    }
    task = (
        f"<day>{json.dumps(red.clean_deep(data), sort_keys=True, ensure_ascii=False)}</day>\n"
        f"<instructions>{_prefs(preferences, red)}</instructions>"
    )
    allowed = {p["id"] for p in saved}

    def finish(o: DayOut) -> dict[str, Any]:
        return {"day": day.isoformat(), "title": red.restore(o.title), "items": _items(o, day, allowed, red),
                "rationale": red.restore(o.summary), "label": LABEL}

    return run_action(
        session, settings=settings, flags=flags, spec=DAY_SPEC, user_id=user_id, trip_id=trip_id,
        idempotency_key=idempotency_key, task=task, out_model=DayOut, finish=finish,
        route="POST /v1/trips/{trip_id}/ai/draft-day", provider=provider, params={"day": day.isoformat(), "pace": pace},
    )


def draft_trip(
    session: Session, *, settings, flags, user_id: uuid.UUID, trip_id: uuid.UUID, idempotency_key: str,
    from_day: date | None = None, preferences: str | None = None, pace: str = "balanced",
    interests: list[str] | None = None, provider=None,
) -> Done:
    """Up to 14 days from `from_day` (the trip start by default). A longer trip is drafted in blocks by calling again
    with the next `from_day`; each block is one call and 4 credits."""
    trip = context.trip_basics(session, trip_id)
    if not trip["start_date"] or not trip["end_date"]:
        raise ApiError(422, "validation_failed", "Add trip dates first.", extra={"errors": [{"field": "dates", "code": "required", "message": "Add trip dates first."}]})
    first = from_day or date.fromisoformat(trip["start_date"])
    _within(trip, first)
    last = min(first + timedelta(days=BLOCK_DAYS - 1), date.fromisoformat(trip["end_date"]))
    wanted = [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]
    red = Redactor(context.person_names(session, trip_id, user_id))
    saved = context.saved_places(session, trip_id, limit=40)
    data = {
        "destinations": trip["destinations"], "days": wanted, "saved_places": saved, "pace": pace,
        "interests": sorted(interests or []), "party": f"{trip['travelers']} travelers",
        "existing_items": {d: context.day_items(session, trip_id, date.fromisoformat(d)) for d in wanted},
    }
    task = (
        f"<trip>{json.dumps(red.clean_deep(data), sort_keys=True, ensure_ascii=False)}</trip>\n"
        f"<instructions>{_prefs(preferences, red)}</instructions>"
    )
    allowed = {p["id"] for p in saved}

    def finish(o: TripOut) -> dict[str, Any]:
        got = [d.date for d in o.days]
        if len(set(got)) != len(got) or not set(got) <= set(wanted):
            raise ValueError("days outside the block")
        return {
            "days": [
                {"day": d.date, "title": red.restore(d.title), "items": _items(d, date.fromisoformat(d.date), allowed, red),
                 "rationale": red.restore(d.summary)}
                for d in o.days
            ],
            "overview": red.restore(o.overview), "label": LABEL,
        }

    return run_action(
        session, settings=settings, flags=flags, spec=TRIP_SPEC, user_id=user_id, trip_id=trip_id,
        idempotency_key=idempotency_key, task=task, out_model=TripOut, finish=finish,
        route="POST /v1/trips/{trip_id}/ai/draft-trip", provider=provider,
        params={"from": first.isoformat(), "days": len(wanted), "pace": pace},
    )
