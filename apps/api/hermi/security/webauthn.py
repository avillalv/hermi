# ruff: noqa: E501  (long comments)
"""WebAuthn registration and assertion checks on `cryptography` and a small CBOR reader (08 section 2.2).

Scope, on purpose: ES256 (P-256) and RS256 keys; attestation `none` and `packed` self attestation (we ask the browser for
`none`, so a full attestation chain with x5c is refused, not trusted blind). Both ceremonies require user presence and
user verification, the rpId hash, the origin and the single-use server challenge. The caller issues and consumes the
challenge; this module is pure (no database).

shortcut: no passkey backup-state checks and no FIDO metadata lookups. Ceiling: we cannot tell a hardware key from a
synced passkey. Add the BE/BS flag policy if the owner wants hardware-only admins.
"""

import base64
import hashlib
import hmac
import json
import struct

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

FLAG_UP, FLAG_UV, FLAG_AT = 0x01, 0x04, 0x40
COSE_ES256, COSE_RS256 = -7, -257


class WebAuthnError(Exception):
    """`code` is a short machine reason for logs; callers show one generic message."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64u_decode(s: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    except (ValueError, TypeError):
        raise WebAuthnError("bad_base64") from None


# --- CBOR: definite lengths only, which is all WebAuthn uses -------------------------------------------------


def cbor_decode(data: bytes, pos: int = 0, depth: int = 0) -> tuple[object, int]:
    if depth > 8 or pos >= len(data):
        raise WebAuthnError("bad_cbor")
    head = data[pos]
    major, info = head >> 5, head & 0x1F
    pos += 1
    if info < 24:
        arg = info
    elif info in (24, 25, 26, 27):
        n = 1 << (info - 24)
        if pos + n > len(data):
            raise WebAuthnError("bad_cbor")
        arg, pos = int.from_bytes(data[pos : pos + n], "big"), pos + n
    else:
        raise WebAuthnError("bad_cbor")  # indefinite length or reserved
    if major == 0:
        return arg, pos
    if major == 1:
        return -1 - arg, pos
    if major in (2, 3):
        if pos + arg > len(data):
            raise WebAuthnError("bad_cbor")
        raw = data[pos : pos + arg]
        if major == 2:
            return raw, pos + arg
        try:
            return raw.decode("utf-8"), pos + arg
        except UnicodeDecodeError:
            raise WebAuthnError("bad_cbor") from None
    if major in (4, 5):
        if arg > 64:
            raise WebAuthnError("bad_cbor")
        if major == 4:
            out = []
            for _ in range(arg):
                v, pos = cbor_decode(data, pos, depth + 1)
                out.append(v)
            return out, pos
        m: dict = {}
        for _ in range(arg):
            k, pos = cbor_decode(data, pos, depth + 1)
            v, pos = cbor_decode(data, pos, depth + 1)
            try:
                m[k] = v
            except TypeError:
                raise WebAuthnError("bad_cbor") from None
        return m, pos
    if major == 7 and info in (20, 21, 22):
        return {20: False, 21: True, 22: None}[info], pos
    raise WebAuthnError("bad_cbor")


# --- keys and signatures -----------------------------------------------------------------------------------


def _cose_to_spki(cose: dict) -> bytes:
    """A COSE_Key (ES256 or RS256) as DER SubjectPublicKeyInfo, which is what we store."""
    try:
        if cose.get(1) == 2 and cose.get(3) == COSE_ES256 and cose.get(-1) == 1:
            x, y = cose[-2], cose[-3]
            if len(x) != 32 or len(y) != 32:
                raise WebAuthnError("bad_key")
            key = ec.EllipticCurvePublicNumbers(int.from_bytes(x, "big"), int.from_bytes(y, "big"), ec.SECP256R1()).public_key()
        elif cose.get(1) == 3 and cose.get(3) == COSE_RS256:
            n, e = cose[-1], cose[-2]
            key = rsa.RSAPublicNumbers(int.from_bytes(e, "big"), int.from_bytes(n, "big")).public_key()
            if key.key_size < 2048:
                raise WebAuthnError("weak_key")
        else:
            raise WebAuthnError("unsupported_algorithm")
    except (KeyError, TypeError, ValueError):
        raise WebAuthnError("bad_key") from None
    return key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def _verify_sig(spki: bytes, signature: bytes, message: bytes) -> None:
    key = serialization.load_der_public_key(spki)
    try:
        if isinstance(key, ec.EllipticCurvePublicKey):
            key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        elif isinstance(key, rsa.RSAPublicKey):
            key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
        else:
            raise WebAuthnError("unsupported_algorithm")
    except InvalidSignature:
        raise WebAuthnError("bad_signature") from None


# --- shared checks -----------------------------------------------------------------------------------------


def _client_data(raw: bytes, *, type_: str, challenge: bytes, origin: str) -> None:
    try:
        cd = json.loads(raw.decode("utf-8"))
        got_challenge = b64u_decode(cd["challenge"])
        got_type, got_origin = cd["type"], cd["origin"]
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        raise WebAuthnError("bad_client_data") from None
    if got_type != type_:
        raise WebAuthnError("wrong_type")
    if not hmac.compare_digest(got_challenge, challenge):
        raise WebAuthnError("wrong_challenge")
    if not hmac.compare_digest(str(got_origin).encode(), origin.encode()) or cd.get("crossOrigin") is True:
        raise WebAuthnError("wrong_origin")


def _auth_data_head(auth_data: bytes, rp_id: str) -> tuple[int, int]:
    if len(auth_data) < 37:
        raise WebAuthnError("bad_auth_data")
    if not hmac.compare_digest(auth_data[:32], hashlib.sha256(rp_id.encode()).digest()):
        raise WebAuthnError("wrong_rp")
    flags = auth_data[32]
    if not flags & FLAG_UP:
        raise WebAuthnError("user_not_present")
    if not flags & FLAG_UV:
        raise WebAuthnError("user_not_verified")
    return flags, struct.unpack(">I", auth_data[33:37])[0]


# --- ceremonies --------------------------------------------------------------------------------------------


def verify_registration(*, client_data_json: bytes, attestation_object: bytes, challenge: bytes, origin: str, rp_id: str) -> tuple[bytes, bytes, int]:
    """-> (credential_id, public key as DER SPKI, sign count). Raises WebAuthnError."""
    _client_data(client_data_json, type_="webauthn.create", challenge=challenge, origin=origin)
    att, end = cbor_decode(attestation_object)
    if end != len(attestation_object) or not isinstance(att, dict):
        raise WebAuthnError("bad_attestation")
    auth_data, fmt, stmt = att.get("authData"), att.get("fmt"), att.get("attStmt")
    if not isinstance(auth_data, bytes) or not isinstance(stmt, dict):
        raise WebAuthnError("bad_attestation")
    flags, count = _auth_data_head(auth_data, rp_id)
    if not flags & FLAG_AT or len(auth_data) < 55:
        raise WebAuthnError("no_credential")
    cred_len = struct.unpack(">H", auth_data[53:55])[0]
    if cred_len == 0 or cred_len > 1023 or len(auth_data) < 55 + cred_len:
        raise WebAuthnError("bad_auth_data")
    cred_id = auth_data[55 : 55 + cred_len]
    cose, _ = cbor_decode(auth_data, 55 + cred_len)  # extensions (ED flag) may follow; not read
    if not isinstance(cose, dict):
        raise WebAuthnError("bad_key")
    spki = _cose_to_spki(cose)
    if fmt == "none":
        if stmt:
            raise WebAuthnError("bad_attestation")
    elif fmt == "packed":
        if "x5c" in stmt or "ecdaaKeyId" in stmt:
            raise WebAuthnError("unsupported_attestation")  # chain trust needs a root list we do not keep
        if stmt.get("alg") != cose.get(3) or not isinstance(stmt.get("sig"), bytes):
            raise WebAuthnError("bad_attestation")
        _verify_sig(spki, stmt["sig"], auth_data + hashlib.sha256(client_data_json).digest())
    else:
        raise WebAuthnError("unsupported_attestation")
    return cred_id, spki, count


def verify_assertion(
    *, client_data_json: bytes, authenticator_data: bytes, signature: bytes, challenge: bytes, origin: str, rp_id: str, spki: bytes, stored_count: int
) -> int:
    """-> the new sign count to store. Raises WebAuthnError, including when the counter did not advance (cloned key)."""
    _client_data(client_data_json, type_="webauthn.get", challenge=challenge, origin=origin)
    _flags, count = _auth_data_head(authenticator_data, rp_id)
    _verify_sig(spki, signature, authenticator_data + hashlib.sha256(client_data_json).digest())
    if (count or stored_count) and count <= stored_count:
        raise WebAuthnError("counter_not_advanced")  # an authenticator that always sends 0 is allowed (both zero)
    return count
