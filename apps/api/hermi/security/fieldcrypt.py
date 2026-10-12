# ruff: noqa: E501  (long comments)
"""Field encryption for rare secrets held in the database (the admin TOTP secret). AES-256-GCM with the key from
FIELD_ENCRYPTION_KEY (base64, 32 bytes). Stored as nonce (12) + ciphertext+tag. `aad` binds a value to its owner, so a
blob copied to another row does not open.

shortcut: one key, no key id and no rotation. Ceiling: rotating the key means re-encrypting rows by hand. Add a one
byte key version prefix when the first rotation is planned.
"""

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from hermi.config import NotConfigured, Settings


class FieldCryptError(Exception):
    pass


def _aead(settings: Settings) -> AESGCM:
    raw = settings.require("FIELD_ENCRYPTION_KEY")  # NotConfigured when unset: the caller degrades
    try:
        key = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise FieldCryptError("FIELD_ENCRYPTION_KEY is not base64") from None
    if len(key) != 32:
        raise FieldCryptError("FIELD_ENCRYPTION_KEY must decode to 32 bytes")
    return AESGCM(key)


def seal(settings: Settings, plaintext: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    return nonce + _aead(settings).encrypt(nonce, plaintext, aad)


def unseal(settings: Settings, blob: bytes, aad: bytes) -> bytes:
    try:
        return _aead(settings).decrypt(bytes(blob[:12]), bytes(blob[12:]), aad)
    except InvalidTag:
        raise FieldCryptError("value did not open") from None


__all__ = ["FieldCryptError", "NotConfigured", "seal", "unseal"]
