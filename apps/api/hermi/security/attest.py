# ruff: noqa: E501  (long comments)
"""App Attest verification (04 section 5.1, 10 section 2.4, WF-062.1) behind one interface.

`FakeVerifier` is deterministic and selected when `PROVIDERS_MODE=fake` (config already refuses that outside local and ci).
`AppleVerifier` is the live one: CBOR, the certificate chain to the Apple App Attest root, the nonce, the App ID hash and the
key id for an attestation; the signature, App ID hash and counter for an assertion. It needs `APPLE_TEAM_ID` and
`APPLE_BUNDLE_ID`, and the root certificate below.

Replay protection is not here: the route advances the stored counter in one statement and consumes the challenge once.
"""

import base64
import hashlib
import struct
from dataclasses import dataclass
from typing import Any, Protocol

from hermi.config import NotConfigured, Settings

# shortcut: Apple's App Attest root CA is not vendored yet, so the live verifier refuses every attestation (503, guest AI off)
# until the owner pastes the PEM of "Apple App Attestation Root CA" (apple.com/certificateauthority) here.
# Upgrade trigger: the first TestFlight build, together with the owner's real-device check.
APPLE_APP_ATTEST_ROOT_PEM = ""

CLIENT_DATA_SEPARATOR = b"\n"


class AttestError(Exception):
    """The attestation or assertion failed verification (never carries request data)."""


@dataclass(frozen=True)
class AttestedKey:
    public_key: bytes  # stored in device_attestations.public_key
    environment: str  # 'development' or 'production'


@dataclass(frozen=True)
class Assertion:
    counter: int


class AttestVerifier(Protocol):
    def verify_attestation(self, *, key_id: str, attestation: str, nonce: str) -> AttestedKey: ...

    def verify_assertion(
        self, *, key_id: str, public_key: bytes, assertion: str, client_data: bytes
    ) -> Assertion: ...


def client_data(idempotency_key: str, body: bytes) -> bytes:
    """What the app hashes into an assertion for POST /guest/ai/draft-day: the Idempotency-Key, a newline and the raw body.
    It binds the assertion to one request, so a captured assertion cannot carry another body."""
    return idempotency_key.encode() + CLIENT_DATA_SEPARATOR + body


# --- fake -------------------------------------------------------------------------------------------------------------


def fake_public_key(key_id: str) -> bytes:
    return hashlib.sha256(b"pub|" + key_id.encode()).digest()


def fake_attestation(key_id: str, nonce: str) -> str:
    return "fake1." + hashlib.sha256(f"attest|{key_id}|{nonce}".encode()).hexdigest()


def fake_assertion(key_id: str, counter: int, data: bytes) -> str:
    digest = hashlib.sha256(
        b"assert|" + key_id.encode() + b"|" + str(counter).encode() + b"|" + data
    ).hexdigest()
    return f"fake1.{counter}.{digest}"


class FakeVerifier:
    """Accepts exactly what `fake_attestation` and `fake_assertion` produce. The public key is derived from the key id, so the
    key id is bound to the stored key, and the assertion digest is bound to the key id, counter and request."""

    def verify_attestation(self, *, key_id: str, attestation: str, nonce: str) -> AttestedKey:
        if not key_id or attestation != fake_attestation(key_id, nonce):
            raise AttestError("attestation")
        return AttestedKey(fake_public_key(key_id), "development")

    def verify_assertion(
        self, *, key_id: str, public_key: bytes, assertion: str, client_data: bytes
    ) -> Assertion:
        parts = assertion.split(".")
        if (
            len(parts) != 3
            or parts[0] != "fake1"
            or not parts[1].isdigit()
            or public_key != fake_public_key(key_id)
        ):
            raise AttestError("assertion")
        counter = int(parts[1])
        if assertion != fake_assertion(key_id, counter, client_data):
            raise AttestError("assertion")
        return Assertion(counter)


# --- live -------------------------------------------------------------------------------------------------------------


def _cbor(buf: bytes, pos: int = 0, depth: int = 0) -> tuple[Any, int]:
    """The subset of CBOR an attestation object uses: unsigned and negative ints, byte and text strings, arrays and maps,
    definite lengths only. Anything else raises AttestError."""
    if depth > 8 or pos >= len(buf):
        raise AttestError("cbor")
    head = buf[pos]
    major, info = head >> 5, head & 0x1F
    pos += 1
    if info < 24:
        n = info
    elif info in (24, 25, 26, 27):
        size = 1 << (info - 24)
        if pos + size > len(buf):
            raise AttestError("cbor")
        n = int.from_bytes(buf[pos : pos + size], "big")
        pos += size
    else:
        raise AttestError("cbor")
    if major == 0:
        return n, pos
    if major == 1:
        return -1 - n, pos
    if major in (2, 3):
        if pos + n > len(buf):
            raise AttestError("cbor")
        raw = buf[pos : pos + n]
        return (raw if major == 2 else raw.decode("utf-8", "strict")), pos + n
    if major in (4, 5):
        if n > 16:
            raise AttestError("cbor")
        items: list[Any] = []
        for _ in range(n * (2 if major == 5 else 1)):
            v, pos = _cbor(buf, pos, depth + 1)
            items.append(v)
        if major == 4:
            return items, pos
        keys = items[0::2]
        if not all(isinstance(k, str) for k in keys):
            raise AttestError("cbor")
        return dict(zip(keys, items[1::2], strict=True)), pos
    raise AttestError("cbor")


def _decode(b64: str) -> dict:
    try:
        raw = base64.b64decode(b64, validate=True)
        obj, end = _cbor(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise AttestError("cbor") from e
    if end != len(raw) or not isinstance(obj, dict):
        raise AttestError("cbor")
    return obj


class AppleVerifier:
    def __init__(self, team_id: str, bundle_id: str, *, allow_development: bool = True):
        self.allow_development = (
            allow_development  # false in production: a development key is a debug build
        )
        self.app_id_hash = hashlib.sha256(f"{team_id}.{bundle_id}".encode()).digest()

    def verify_attestation(self, *, key_id: str, attestation: str, nonce: str) -> AttestedKey:
        from cryptography import x509
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization

        if not APPLE_APP_ATTEST_ROOT_PEM:
            raise NotConfigured("APPLE_APP_ATTEST_ROOT_PEM")
        obj = _decode(attestation)
        stmt, auth = obj.get("attStmt"), obj.get("authData")
        if (
            obj.get("fmt") != "apple-appattest"
            or not isinstance(stmt, dict)
            or not isinstance(auth, bytes)
            or len(auth) < 55
        ):
            raise AttestError("format")
        chain = stmt.get("x5c")
        if (
            not isinstance(chain, list)
            or len(chain) != 2
            or not all(isinstance(c, bytes) for c in chain)
        ):
            raise AttestError("chain")
        try:
            leaf, inter = (x509.load_der_x509_certificate(c) for c in chain)
            root = x509.load_pem_x509_certificate(APPLE_APP_ATTEST_ROOT_PEM.encode())
            leaf.verify_directly_issued_by(inter)
            inter.verify_directly_issued_by(root)
            ext = leaf.extensions.get_extension_for_oid(
                x509.ObjectIdentifier("1.2.840.113635.100.8.2")
            ).value.value  # type: ignore[attr-defined]
            point = leaf.public_key().public_bytes(
                serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
            )  # type: ignore[call-arg]
        except (
            ValueError,
            TypeError,
            InvalidSignature,
            x509.ExtensionNotFound,
            AttributeError,
        ) as e:
            raise AttestError("chain") from e
        client_hash = hashlib.sha256(nonce.encode()).digest()
        if len(ext) < 32 or ext[-32:] != hashlib.sha256(auth + client_hash).digest():
            raise AttestError("nonce")
        try:
            key_hash = base64.b64decode(key_id, validate=True)
        except ValueError as e:
            raise AttestError("key_id") from e
        if key_hash != hashlib.sha256(point).digest():
            raise AttestError("key_id")
        cred_len = struct.unpack(">H", auth[53:55])[0]
        if (
            auth[:32] != self.app_id_hash
            or struct.unpack(">I", auth[33:37])[0] != 0
            or auth[55 : 55 + cred_len] != key_hash
        ):
            raise AttestError("auth_data")
        aaguid = auth[37:53]
        env = (
            "production"
            if aaguid == b"appattest" + bytes(7)
            else "development"
            if aaguid == b"appattestdevelop"
            else None
        )
        if env is None or (env == "development" and not self.allow_development):
            raise AttestError("aaguid")
        return AttestedKey(point, env)

    def verify_assertion(
        self, *, key_id: str, public_key: bytes, assertion: str, client_data: bytes
    ) -> Assertion:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        obj = _decode(assertion)
        sig, auth = obj.get("signature"), obj.get("authenticatorData")
        if (
            not isinstance(sig, bytes)
            or not isinstance(auth, bytes)
            or len(auth) < 37
            or auth[:32] != self.app_id_hash
        ):
            raise AttestError("assertion")
        nonce = hashlib.sha256(auth + hashlib.sha256(client_data).digest()).digest()
        try:
            key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public_key)
            key.verify(sig, nonce, ec.ECDSA(hashes.SHA256()))
        except (ValueError, InvalidSignature) as e:
            raise AttestError("signature") from e
        return Assertion(struct.unpack(">I", auth[33:37])[0])


def verifier_for(settings: Settings) -> AttestVerifier:
    """Fake in `PROVIDERS_MODE=fake`; the Apple verifier otherwise. Raises NotConfigured without the app identity."""
    if settings.providers_mode == "fake":
        return FakeVerifier()
    if not settings.apple_team_id or not settings.apple_bundle_id:
        raise NotConfigured("APPLE_TEAM_ID and APPLE_BUNDLE_ID")
    return AppleVerifier(
        settings.apple_team_id,
        settings.apple_bundle_id,
        allow_development=settings.environment != "production",
    )
