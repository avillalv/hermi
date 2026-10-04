# ruff: noqa: E501  (long comments and SQL)
"""Version preconditions for versioned writes (04 section 1.7): `If-Match: "<version>"` or a body `version`.

A route that edits a versioned resource (trip, day, item, route, lodging option, note, checklist item) reads its
body, then calls `resolve_version(request, body.version)` inside the handler. It is a plain function, not a
dependency, so the 428 can never fire before the body has been read (a body version alone is enough).
"""

import re

from fastapi import Request

from hermi.errors import ApiError

_STRONG_ETAG = re.compile(r'"([1-9][0-9]{0,9})"')


def resolve_version(request: Request, body_version: int | None = None) -> int:
    """The version the client edited. Header and body may both be sent if they agree.

    428 precondition_required when both are missing. 412 precondition_failed when the header is not a quoted
    positive integer, the body version is below 1, or the two disagree (decision: not a 409, since neither is
    stale, the request is malformed)."""
    raw = request.headers.get("if-match")
    header = None
    if raw is not None:
        m = _STRONG_ETAG.fullmatch(raw.strip())
        if not m:
            raise ApiError(412, "precondition_failed", 'If-Match must look like "3".')
        header = int(m.group(1))
    if body_version is not None and body_version < 1:
        raise ApiError(412, "precondition_failed", "The version must be 1 or more.")
    if header is None and body_version is None:
        raise ApiError(
            428,
            "precondition_required",
            "Send the version you are editing in If-Match or the body.",
        )
    if header is not None and body_version is not None and header != body_version:
        raise ApiError(412, "precondition_failed", "If-Match and the body version differ.")
    return header if header is not None else body_version


def version_conflict(current: dict) -> ApiError:
    """409 version_conflict with the latest resource in `current` (raise it from the resource code)."""
    return ApiError(
        409,
        "version_conflict",
        "Someone else changed this. Keep yours or use theirs.",
        extra={"current": current},
    )
