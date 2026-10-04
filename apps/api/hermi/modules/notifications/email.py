"""Minimal email sender with console, file and resend backends (EMAIL_BACKEND)."""

import json
import logging
import urllib.request
import uuid
from pathlib import Path

from hermi.config import Settings

log = logging.getLogger("hermi.email")
OUTBOX_DIR = Path(".data/outbox")
RESEND_URL = "https://api.resend.com"


def _resend_post(key: str, path: str, body: dict) -> None:
    req = urllib.request.Request(
        RESEND_URL + path,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10).close()  # noqa: S310 (fixed https host)


def send(settings: Settings, to: str, subject: str, text: str) -> None:
    msg = {"from": settings.email_from, "to": to, "subject": subject, "text": text}
    key = settings.resend_api_key.get_secret_value() if settings.resend_api_key else None
    if settings.email_backend == "resend" and key:
        _resend_post(key, "/emails", {**msg, "to": [to]})
    elif settings.email_backend == "file":
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        (OUTBOX_DIR / f"{uuid.uuid4().hex}.json").write_text(json.dumps(msg))
    else:
        log.info("email %s", json.dumps(msg))


def add_contact(settings: Settings, email: str) -> None:
    """Add to the Resend audience (contacts) when RESEND_API_KEY is set."""
    if settings.resend_api_key:
        _resend_post(
            settings.resend_api_key.get_secret_value(),
            "/contacts",
            {"email": email, "unsubscribed": False},
        )
