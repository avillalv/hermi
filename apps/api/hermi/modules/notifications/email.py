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


def _resend_post(key: str, path: str, body: dict, idempotency_key: str | None = None) -> None:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if idempotency_key:  # Resend answers a repeated key with the first result: no double send
        headers["Idempotency-Key"] = idempotency_key
    req = urllib.request.Request(RESEND_URL + path, data=json.dumps(body).encode(), headers=headers)
    urllib.request.urlopen(req, timeout=10).close()  # noqa: S310 (fixed https host)


def send(
    settings: Settings,
    to: str,
    subject: str,
    text: str,
    *,
    html: str | None = None,
    headers: dict[str, str] | None = None,
    idempotency_key: str | None = None,
) -> None:
    msg = {"from": settings.email_from, "to": to, "subject": subject, "text": text}
    if html:
        msg["html"] = html
    if headers:
        msg["headers"] = headers
    key = settings.resend_api_key.get_secret_value() if settings.resend_api_key else None
    if settings.email_backend == "resend" and key:
        _resend_post(key, "/emails", {**msg, "to": [to]}, idempotency_key=idempotency_key)
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
