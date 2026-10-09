"""One JSON line per log record on stderr, extra fields included. Idempotent."""

import json
import logging
import re
import sys
from contextvars import ContextVar

_STD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}
_KEY = re.compile(r"key|secret|token|password|authorization|cookie|dsn", re.I)
_SECRET = re.compile(
    r"Bearer\s+[\w.~+/=-]+"
    r"|eyJ[\w-]+\.eyJ[\w-]+\.[\w-]*"
    r"|(?<!\w)sk[-_][\w-]{6,}"
    r"|(?i:[\w-]*(?:key|token|secret|password)[\w-]*)=[^&\s\"',;]+"
    # Emails, calendar feed URLs (the token is in the path) and our own feed route.
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|(?:(?:webcal|https?)://|/v1/calendar/)[^\s\"',;]*\.ics[^\s\"',;]*"
    r"|/(?:v1/)?(?:invites?|shared|claim)/[^\s/{}\"',;?#]+"
    r"|webcal://[^\s\"',;]+"
    r"|https?://[^/\s]*icloud\.com/published/[^\s\"',;]+"
)
# Prompts and feed URLs may appear at DEBUG only (10 section 2.2).
_DEBUG_ONLY_KEY = re.compile(r"prompt|feed_?url", re.I)
# The waitlist has no table in Phase 1: its log line is the signup record (WF-002), so its
# `email` field is the one email that stays. Every other logger has emails masked.
_RECORD_LOGGERS = {"hermi.waitlist"}
_static: dict[str, str] = {}  # service, env, release: on every line (02 section 9)
_CTX_KEYS = ("request_id", "job_id", "run_id", "user_id")
# One mutable dict per request or job, so a bind inside a threadpool dependency is seen by the
# middleware that logs after it.
_ctx: ContextVar[dict | None] = ContextVar("hermi_log_ctx", default=None)


def bind(**fields: str) -> None:
    """Add request_id, job_id, run_id or user_id (opaque UUID, never an email) to every log line."""
    ctx = _ctx.get()
    if ctx is None:
        ctx = {}
        _ctx.set(ctx)
    ctx.update({k: v for k, v in fields.items() if k in _CTX_KEYS and v})
    import sentry_sdk  # no-ops until Sentry is initialised

    if "request_id" in ctx:
        sentry_sdk.set_tag("request_id", ctx["request_id"])
    if "user_id" in ctx:
        sentry_sdk.set_user({"id": ctx["user_id"]})


def clear_context() -> None:
    _ctx.set(None)


def mask(v, key="", debug=False):
    """Redact secret keys and secret-shaped strings. Prompts and feed URLs survive only at DEBUG."""
    if _KEY.search(key) or (not debug and _DEBUG_ONLY_KEY.search(key)):
        return "[redacted]"
    if isinstance(v, str):
        return _SECRET.sub("[redacted]", v)
    if isinstance(v, dict):
        return {k: mask(x, str(k), debug) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [mask(x, "", debug) for x in v]
    if v is None or isinstance(v, (int, float, bool)):
        return v
    return _SECRET.sub("[redacted]", str(v))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": self.formatTime(record), "level": record.levelname, "logger": record.name}
        out["msg"] = record.getMessage()
        out.update(_static)
        out.update(_ctx.get() or {})
        out.update({k: v for k, v in record.__dict__.items() if k not in _STD})
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        debug = (record.levelno or logging.INFO) <= logging.DEBUG
        out = {k: mask(v, k if k not in ("msg", "exc") else "", debug) for k, v in out.items()}
        if record.name in _RECORD_LOGGERS and "email" in out:
            out["email"] = record.__dict__["email"]
        return json.dumps(out, default=str)


def setup_logging(level: str, *, service: str = "", env: str = "", release: str = "") -> None:
    _static.clear()
    fields = {"service": service, "env": env, "release": release}
    _static.update({k: v for k, v in fields.items() if v})
    root = logging.getLogger()
    for h in [h for h in root.handlers if getattr(h, "_hermi", False)]:
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stderr)
    handler._hermi = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper() if level.upper() in logging._nameToLevel else "INFO")
    # httpx logs full request URLs at INFO, and provider keys travel in query strings.
    for name in ("httpx", "httpcore", "httpx2", "httpcore2"):
        logging.getLogger(name).setLevel(logging.WARNING)
