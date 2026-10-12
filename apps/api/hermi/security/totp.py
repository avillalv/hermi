# ruff: noqa: E501  (long comments)
"""TOTP (RFC 6238) on the standard library: SHA-1, 6 digits, 30 second step (what every authenticator app does).

`match` returns the counter a code belongs to inside the window, so the caller can refuse a counter it has seen
(replay protection lives with the stored `last_used_step`, not here).
"""

import base64
import hashlib
import hmac
import secrets
import struct
from urllib.parse import quote

STEP = 30
DIGITS = 6
WINDOW = 1  # one step either side of now, for clock drift


def new_secret() -> bytes:
    return secrets.token_bytes(20)  # 160 bits, the RFC 4226 recommendation


def b32(secret: bytes) -> str:
    return base64.b32encode(secret).decode().rstrip("=")


def code_for(secret: bytes, counter: int) -> str:
    mac = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = mac[-1] & 0x0F
    return str((struct.unpack(">I", mac[o : o + 4])[0] & 0x7FFFFFFF) % 10**DIGITS).zfill(DIGITS)


def match(secret: bytes, code: str, now: float) -> int | None:
    """The counter whose code equals `code` (within +/- WINDOW steps of `now`), else None. Constant time per candidate."""
    code = "".join(code.split())
    if len(code) != DIGITS or not code.isascii() or not code.isdigit():
        return None
    base, found = int(now // STEP), None
    for c in range(base - WINDOW, base + WINDOW + 1):
        if hmac.compare_digest(code_for(secret, c), code):
            found = c
    return found


def otpauth_uri(secret: bytes, account: str, issuer: str) -> str:
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(account)}?secret={b32(secret)}&issuer={quote(issuer)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP}"
    )
