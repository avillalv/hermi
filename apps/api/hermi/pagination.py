# ruff: noqa: E501  (long strings)
"""Offset page cursors shared by list routes: unsigned base64 of the next offset."""

import base64

from hermi.errors import ApiError


def decode_offset(value: str | None) -> int:
    """The offset a cursor holds (0 for none). A bad cursor is the 422 `validation_failed` on `cursor`."""
    if not value:
        return 0
    try:
        n = int(base64.urlsafe_b64decode(value.encode()).decode())
        if n < 0 or n > 10**9:
            raise ValueError
        return n
    except ValueError:
        raise ApiError(
            422, "validation_failed", "Some fields need another look.",
            extra={"errors": [{"field": "cursor", "code": "invalid", "message": "That page cursor is not valid."}]},
        ) from None


def encode_offset(n: int) -> str:
    return base64.urlsafe_b64encode(str(n).encode()).decode()
