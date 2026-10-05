# ruff: noqa: E501  (long comments, docstrings and SQL)
"""Server side analytics (10 section 4). The catalogue lives once, in packages/shared/src/events.ts; `npm run gen:shared`
writes analytics_catalogue.json from it and a test fails on drift. `capture` rejects unknown names, unknown properties
and values the catalogue does not allow, and drops the event when the user opted out. No PII: users.id only."""

import json
import logging
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Protocol

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.config import Settings

log = logging.getLogger(__name__)
_data = json.loads(
    (Path(__file__).with_name("analytics_catalogue.json")).read_text(encoding="utf-8")
)
CATALOGUE: dict[str, dict[str, Any]] = _data["events"]
COMMON: dict[str, Any] = _data["common"]
MAX_STR = (
    64  # codes and buckets only; anything longer or containing "@" looks like free text or an email
)


class AnalyticsError(ValueError):
    """A call site broke the catalogue. A programming error, never a user error."""


class Sink(Protocol):
    def send(self, event: dict[str, Any]) -> None: ...


class MemorySink:
    """The sink when POSTHOG_KEY is unset (local, CI, tests): keeps the last events so tests can read them."""

    def __init__(self) -> None:
        self.events: deque[dict[str, Any]] = deque(maxlen=1000)

    def send(self, event: dict[str, Any]) -> None:
        self.events.append(event)


class PostHogSink:
    """POST {host}/capture/. One worker thread so a slow PostHog never blocks a request; failures are logged, not raised."""

    def __init__(self, key: str, host: str) -> None:
        self._key, self._url = key, host.rstrip("/") + "/capture/"
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="posthog")

    def send(self, event: dict[str, Any]) -> None:
        self._pool.submit(self._post, event)

    def _post(self, event: dict[str, Any]) -> None:
        try:
            httpx.post(
                self._url, json={"api_key": self._key, **event}, timeout=3.0
            ).raise_for_status()
        except httpx.HTTPError as e:
            log.warning(
                "analytics send failed: %s", type(e).__name__
            )  # shortcut: dropped, no retry; add a queue if loss matters


_sink: Sink = MemorySink()
_base: dict[str, Any] = {}


def set_sink(sink: Sink) -> None:
    global _sink
    _sink = sink


def configure(settings: Settings) -> None:
    """Called once by create_app. With no POSTHOG_KEY the sink stays in memory."""
    global _base
    _base = {k: v for k, v in {"env": settings.environment, "app_version": settings.release_sha}.items() if v}
    key = settings.posthog_key
    # CI and tests (environment "ci") never reach PostHog, even with POSTHOG_KEY exported in the shell.
    live = key and settings.environment != "ci"
    set_sink(PostHogSink(key, settings.posthog_host) if live else MemorySink())


def _check(kind: Any, value: Any, where: str) -> None:
    ok: bool
    if kind == "bool":
        ok = isinstance(value, bool)
    elif kind == "int":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif kind == "str":
        ok = isinstance(value, str) and len(value) <= MAX_STR and "@" not in value
    elif kind == "strs":
        ok = isinstance(value, list) and all(
            isinstance(v, str) and len(v) <= MAX_STR and "@" not in v for v in value
        )
    else:
        ok = value in kind
    if not ok:
        raise AnalyticsError(f"{where}: value not allowed")


def capture(
    name: str,
    distinct_id: uuid.UUID | str,
    properties: dict[str, Any] | None = None,
    *,
    opted_out: bool = False,
) -> bool:
    """Validate, then send. Returns False when dropped for an opt-out. Raises AnalyticsError on a catalogue breach."""
    spec = CATALOGUE.get(name)
    if spec is None:
        raise AnalyticsError(f"unknown event {name!r}")
    props = properties or {}
    for key, value in props.items():
        kind = spec.get(key, COMMON.get(key))
        if kind is None:
            raise AnalyticsError(f"{name}: unknown property {key!r}")
        _check(kind, value, f"{name}.{key}")
    try:
        did = str(uuid.UUID(str(distinct_id)))
    except ValueError:
        raise AnalyticsError("distinct_id must be a users.id UUID") from None
    if opted_out:
        return False  # dropped, never queued
    _sink.send({"event": name, "distinct_id": did, "properties": {**_base, **props}})
    return True


def is_opted_out(session: Session, user_id: uuid.UUID) -> bool:
    """The user's latest 'analytics' consent row says not granted (Settings, Privacy). No row means not opted out."""
    granted = session.execute(
        text(
            "SELECT granted FROM consents WHERE user_id = :u AND kind = 'analytics' ORDER BY created_at DESC, id DESC LIMIT 1"
        ),
        {"u": user_id},
    ).scalar()
    return granted is False
