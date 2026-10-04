"""One JSON line per log record on stderr, extra fields included. Idempotent."""

import json
import logging
import sys

_STD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": self.formatTime(record), "level": record.levelname, "logger": record.name}
        out["msg"] = record.getMessage()
        out.update({k: v for k, v in record.__dict__.items() if k not in _STD})
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def setup_logging(level: str) -> None:
    root = logging.getLogger()
    for h in [h for h in root.handlers if getattr(h, "_hermi", False)]:
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stderr)
    handler._hermi = True  # type: ignore[attr-defined]
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper() if level.upper() in logging._nameToLevel else "INFO")
    # httpx logs full request URLs at INFO, and provider keys travel in query strings.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
