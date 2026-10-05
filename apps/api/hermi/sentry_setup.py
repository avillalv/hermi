"""Sentry for the API and the worker. Off without SENTRY_DSN; sends no PII (10 section 2.2)."""

import sentry_sdk

from hermi.logging_setup import mask

_DROP_REQUEST = ("query_string", "cookies", "data", "env")


def scrub_event(event: dict, hint: dict | None = None) -> dict:
    """before_send: opaque user id only, no query string, cookies or body, secrets, emails,
    feed URLs and prompts masked everywhere else (headers included)."""
    user = event.get("user")
    if user is not None:
        event["user"] = {"id": user["id"]} if user.get("id") else {}
    req = event.get("request")
    if isinstance(req, dict):
        for k in _DROP_REQUEST:
            req.pop(k, None)
        # A concrete path can carry an invite or feed token: keep the route template or nothing.
        tx = event.get("transaction")
        if isinstance(tx, str) and tx.startswith("/"):
            req["url"] = tx
        else:
            req.pop("url", None)
    return mask(event)


def _scrub_breadcrumb(crumb: dict, hint: dict | None = None) -> dict:
    return mask(crumb)


def init_sentry(
    dsn: str | None, *, release: str, environment: str, transport=None
) -> bool:
    """Start Sentry when a DSN is set. Returns whether it started."""
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        release=release,
        environment=environment,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=0,
        before_send=scrub_event,
        before_breadcrumb=_scrub_breadcrumb,
        transport=transport,
    )
    return True
