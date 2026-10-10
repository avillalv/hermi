# ruff: noqa: E501  (long SQL strings)
"""The shared research cache (06 section 8, 03 section 5.6): keys, TTLs, reads, the single-flight lease, the write with
its poisoning checks, the report path and the hit rate.

Everything here takes a session the caller owns and never commits. Reads and writes of `shared_research_cache` run as the
system login: the table holds only public facts keyed by public inputs and no policy lets a person read or write it
directly. The key is a hash of public inputs only (kind, topic, destination place id, rounded window, prompt version, model),
so user text cannot reach it.
"""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

KIND_RESEARCH = "ai_research"
KIND_BRIEF = "destination_brief"
TOPICS = ("destination_brief", "events_and_closures", "reservations_needed", "getting_around", "seasonal_notes")

_TTL_DAYS = {"destination_brief": 30, "events_and_closures": 7, "reservations_needed": 14, "getting_around": 14, "seasonal_notes": 14}
SOON_DAYS = 14  # an events entry for a window that starts within this many days lives 2 days, not 7


def kind_for(topic: str) -> str:
    return KIND_BRIEF if topic == "destination_brief" else KIND_RESEARCH


def _monday_on_or_before(d: date) -> date:
    return d - timedelta(days=d.weekday())


def round_window(start: date, end: date) -> tuple[date, date]:
    """Start rounds down and end rounds up to the week boundary (Monday), so near-identical trips share an entry."""
    return _monday_on_or_before(start), end + timedelta(days=-end.weekday() % 7)


def cache_key(
    *, kind: str, topic: str, place_id: str, window_start: date, window_end: date, prompt_version: str, model: str
) -> str:
    """sha256(kind | topic | place_id | round_start | round_end | prompt_version | model) (06 section 8.2). The topic must be
    on the fixed list: the key is the one place a free-text topic could be smuggled into a shared entry."""
    if topic not in TOPICS:
        raise ValueError(f"unknown research topic {topic!r}")
    start, end = round_window(window_start, window_end)
    raw = "|".join((kind, topic, place_id, start.isoformat(), end.isoformat(), prompt_version, model))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ttl(topic: str, window_start: date, today: date | None = None) -> timedelta:
    today = today or datetime.now(UTC).date()
    if topic == "events_and_closures" and (window_start - today).days < SOON_DAYS:
        return timedelta(days=2)
    return timedelta(days=_TTL_DAYS[topic])


# --- reads --------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    key: str
    response: dict[str, Any]
    sources: list[dict[str, Any]]
    fetched_at: datetime
    expires_at: datetime
    stale_until: datetime
    flagged: bool
    # shortcut: nothing purges entries past stale_until here; they stay until rewritten. Ceiling: dead rows only cost storage,
    # and a flagged one must stay anyway. Trigger: `retention_sweep` (WF-092) deletes unflagged rows past stale_until.
    state: str  # fresh, stale (served with its age and refreshed), gone (expired past stale), flagged (never served)

    @property
    def age_days(self) -> int:
        return max((datetime.now(UTC) - self.fetched_at).days, 0)


_GET = text(
    "SELECT key, response, sources, fetched_at, expires_at, stale_until, flagged_at, now() AS now FROM shared_research_cache WHERE key = :k"
)


def lookup(session: Session, key: str) -> Entry | None:
    """The entry and what may be done with it. A flagged entry is not served, not rewritten and not purged."""
    r = session.execute(_GET, {"k": key}).one_or_none()
    if r is None:
        return None
    if r.flagged_at is not None:
        state = "flagged"
    elif r.expires_at > r.now:
        state = "fresh"
    elif r.stale_until > r.now:
        state = "stale"
    else:
        state = "gone"
    return Entry(r.key, dict(r.response), list(r.sources), r.fetched_at, r.expires_at, r.stale_until, r.flagged_at is not None, state)


def bump_hit(session: Session, key: str) -> None:
    session.execute(text("UPDATE shared_research_cache SET hit_count = hit_count + 1, last_hit_at = now() WHERE key = :k"), {"k": key})


# --- the write ----------------------------------------------------------------------------------------------------


def store(
    session: Session,
    *,
    key: str,
    kind: str,
    provider: str,
    params: dict[str, Any],
    response: dict[str, Any],
    sources: list[dict[str, Any]],
    model: str,
    prompt_version: str,
    ttl_for: timedelta,
    run_id: uuid.UUID | None,
    cost_usd_micros: int,
) -> bool:
    """Insert or replace an entry that is expired or past stale. A flagged entry is never rewritten (the WHERE clause), and
    a fresh one is left to the run that made it. Returns whether a row was written. `stale_until` is expires_at plus one TTL."""
    body = json.dumps(response, ensure_ascii=False, sort_keys=True)
    r = session.execute(
        text(
            """INSERT INTO shared_research_cache (key, kind, provider, params, response, sources, response_bytes, model, prompt_version,
                                                  fetched_at, expires_at, stale_until, run_id, cost_usd_micros)
               VALUES (:k, :kind, :p, CAST(:params AS jsonb), CAST(:resp AS jsonb), CAST(:src AS jsonb), :n, :m, :v,
                       now(), now() + :ttl, now() + :ttl * 2, :run, :cost)
               ON CONFLICT (key) DO UPDATE SET
                 kind = EXCLUDED.kind, provider = EXCLUDED.provider, params = EXCLUDED.params, response = EXCLUDED.response,
                 sources = EXCLUDED.sources, response_bytes = EXCLUDED.response_bytes, model = EXCLUDED.model,
                 prompt_version = EXCLUDED.prompt_version, fetched_at = EXCLUDED.fetched_at, expires_at = EXCLUDED.expires_at,
                 stale_until = EXCLUDED.stale_until, run_id = EXCLUDED.run_id, cost_usd_micros = EXCLUDED.cost_usd_micros
               WHERE shared_research_cache.flagged_at IS NULL AND shared_research_cache.expires_at <= now()"""
        ),
        {
            "k": key, "kind": kind, "p": provider, "params": json.dumps(params), "resp": body, "src": json.dumps(sources),
            "n": len(body.encode("utf-8")), "m": model, "v": prompt_version, "ttl": ttl_for, "run": run_id, "cost": cost_usd_micros,
        },
    )
    return r.rowcount == 1


# --- single flight ------------------------------------------------------------------------------------------------


class Lease:
    """A session-level advisory lock on `hashtextextended(key, 0)` held on its own connection (no column, 06 section 8.4).
    It outlives the caller's transaction and dies with the process, so a crashed run frees the key by itself."""

    def __init__(self, engine: Engine, key: str) -> None:
        self._engine, self._key = engine, key
        self._conn: Connection | None = None

    def acquire(self) -> bool:
        conn = self._engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        try:
            got = conn.execute(text("SELECT pg_try_advisory_lock(hashtextextended(:k, 0))"), {"k": self._key}).scalar_one()
        except BaseException:
            conn.close()
            raise
        if got:
            self._conn = conn
        else:
            conn.close()
        return bool(got)

    def release(self) -> None:
        conn, self._conn = self._conn, None
        if conn is None:
            return
        try:
            conn.execute(text("SELECT pg_advisory_unlock(hashtextextended(:k, 0))"), {"k": self._key})
        except BaseException:
            conn.invalidate()  # closing the connection frees the lock
            raise
        finally:
            conn.close()


# --- poisoning checks ---------------------------------------------------------------------------------------------

_PHONE = re.compile(r"(?<![\w.])(?:\+\d{1,3}[\s.-]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,4}){2,4}|\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4})(?![\w])")
_PROMO = re.compile(
    r"(?i)\b(?:book(?:ing)? (?:now|today|direct(?:ly)?)|reserve now|buy now|order now|click here|call (?:us )?now|act now|limited[- ]time|"
    r"(?:promo|coupon|discount|voucher|referral) code|use code|save \d+ ?(?:%|percent)|\d+ ?% off|best price guarantee|sign up (?:now|today)|subscribe (?:now|today))\b"
)
_INSTRUCTION = re.compile(
    r"(?i)\b(?:ignore (?:all |any |the )?(?:previous|prior|above|earlier)|disregard (?:all |the |any )?(?:previous|prior|above|rules|instructions)|"
    r"system prompt|you (?:must|should) (?:now )?(?:recommend|tell|say|always)|as an ai|do not (?:mention|tell|reveal)|"
    r"new instructions|override (?:the )?(?:rules|instructions)|always recommend|only recommend)\b"
)
_AFFILIATE_QUERY = re.compile(r"(?i)[?&](?:aff(?:iliate)?(?:_?id)?|affid|partner(?:_?id)?|ref(?:errer|id)?|tag|utm_[a-z]+|clickid|subid)=")


def instruction_like(text_: str, affiliate_hosts: frozenset[str] = frozenset()) -> str | None:
    """The rule-based half of the poisoning classifier (06 section 8.5): a reason when the text reads like an instruction to
    the model or a promotion (phone numbers, "book now" phrasing, affiliate domains), else None. The Haiku pass is the other half."""
    if _INSTRUCTION.search(text_):
        return "instruction_like"
    if _PROMO.search(text_):
        return "promotional"
    if _PHONE.search(text_):
        return "phone_number"
    if _AFFILIATE_QUERY.search(text_):
        return "tracking_link"
    low = text_.lower()
    for h in affiliate_hosts:
        if h and h in low:
            return "affiliate_domain"
    return None


# --- reports ------------------------------------------------------------------------------------------------------


def report_entry(session: Session, cache_key_: str, *, reason: str = "wrong_info", detail: str = "") -> uuid.UUID:
    """A person reports a cached answer. The definer function `file_content_report` (0014) records the report, expires the
    entry at once so it is no longer served and re-runs on the next request, counts distinct reporters per key into
    `report_count` and sets `flagged_at` at the third. Runs as the caller (`app.user_id` must be set). The endpoint and
    the control are WF-054."""
    return session.execute(
        text("SELECT file_content_report('research_cache', :k, :r, :d)"), {"k": cache_key_, "r": reason, "d": detail}
    ).scalar_one()


# --- hit rate -----------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class HitRate:
    hits: int
    misses: int

    @property
    def rate(self) -> float | None:
        total = self.hits + self.misses
        return round(self.hits / total, 4) if total else None


def hit_rate(session: Session, *, since: datetime | None = None, user_id: uuid.UUID | None = None) -> HitRate:
    """Research hit rate from `ai_usage.cache_hit` (06 section 8.5, 09 WF-050). A bypass or an uncached run for a flagged
    key has no `runs.cache_key` and is not counted; a miss is a cache-eligible run that ran the model. Platform rows
    (warming, classifier) have no user and are left out."""
    r = session.execute(
        text(
            """SELECT count(*) FILTER (WHERE u.cache_hit) AS hits, count(*) FILTER (WHERE NOT u.cache_hit) AS misses
                 FROM ai_usage u JOIN runs r ON r.id = u.run_id
                WHERE u.action = 'research' AND u.purpose IS NULL AND u.state = 'settled' AND r.cache_key IS NOT NULL
                  AND (CAST(:since AS timestamptz) IS NULL OR u.created_at >= :since)
                  AND (CAST(:u AS uuid) IS NULL OR u.user_id = :u)"""
        ),
        {"since": since, "u": user_id},
    ).one()
    return HitRate(int(r.hits), int(r.misses))
