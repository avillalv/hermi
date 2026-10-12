# ruff: noqa: E501  (long lines)
"""A software WebAuthn authenticator for tests: builds the attestation and assertion bytes a browser would return
(ES256 and RS256 keys; formats none and packed self attestation), so the verifier runs its real code."""

import hashlib
import json
import os
import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa

from hermi.security.webauthn import b64u


def cbor(v) -> bytes:
    def head(major: int, n: int) -> bytes:
        if n < 24:
            return bytes([major << 5 | n])
        for info, size in ((24, 1), (25, 2), (26, 4), (27, 8)):
            if n < 1 << (8 * size):
                return bytes([major << 5 | info]) + n.to_bytes(size, "big")
        raise ValueError(n)

    if isinstance(v, bool):
        return bytes([0xF5 if v else 0xF4])
    if isinstance(v, int):
        return head(0, v) if v >= 0 else head(1, -1 - v)
    if isinstance(v, bytes):
        return head(2, len(v)) + v
    if isinstance(v, str):
        return head(3, len(v.encode())) + v.encode()
    if isinstance(v, list):
        return head(4, len(v)) + b"".join(cbor(x) for x in v)
    if isinstance(v, dict):
        return head(5, len(v)) + b"".join(cbor(k) + cbor(x) for k, x in v.items())
    raise TypeError(type(v))


class Authenticator:
    def __init__(self, *, alg: str = "ES256", rp_id: str = "localhost", origin: str = "http://localhost:5173", sign_count: int = 0):
        self.alg, self.rp_id, self.origin, self.count = alg, rp_id, origin, sign_count
        self.credential_id = os.urandom(32)
        self.key = ec.generate_private_key(ec.SECP256R1()) if alg == "ES256" else rsa.generate_private_key(65537, 2048)

    # -- helpers --
    def _cose(self) -> dict:
        pub = self.key.public_key()
        if self.alg == "ES256":
            n = pub.public_numbers()
            return {1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")}
        n = pub.public_numbers()
        return {1: 3, 3: -257, -1: n.n.to_bytes(256, "big"), -2: n.e.to_bytes(3, "big")}

    def _sign(self, data: bytes) -> bytes:
        if self.alg == "ES256":
            return self.key.sign(data, ec.ECDSA(hashes.SHA256()))
        return self.key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    def _client_data(self, typ: str, challenge: bytes, origin: str | None) -> bytes:
        return json.dumps({"type": typ, "challenge": b64u(challenge), "origin": origin or self.origin, "crossOrigin": False}).encode()

    # -- ceremonies --
    def register(
        self, challenge: bytes, *, fmt: str = "none", flags: int = 0x45, origin: str | None = None, rp_id: str | None = None,
        typ: str = "webauthn.create", bad_sig: bool = False,
    ) -> dict:
        """flags default 0x45 = user present + user verified + attested credential data."""
        cd = self._client_data(typ, challenge, origin)
        auth = (
            hashlib.sha256((rp_id or self.rp_id).encode()).digest()
            + bytes([flags])
            + struct.pack(">I", self.count)
            + b"\x00" * 16
            + struct.pack(">H", len(self.credential_id))
            + self.credential_id
            + cbor(self._cose())
        )
        stmt: dict = {}
        if fmt == "packed":
            sig = self._sign(auth + hashlib.sha256(cd).digest())
            if bad_sig:
                sig = sig[:-1] + bytes([sig[-1] ^ 1])
            stmt = {"alg": -7 if self.alg == "ES256" else -257, "sig": sig}
        obj = cbor({"fmt": fmt, "attStmt": stmt, "authData": auth})
        return {"client_data_json": b64u(cd), "attestation_object": b64u(obj)}

    def assert_(
        self, challenge: bytes, *, flags: int = 0x05, origin: str | None = None, rp_id: str | None = None,
        typ: str = "webauthn.get", count: int | None = None, credential_id: bytes | None = None,
        bad_sig: bool = False, sign_challenge: bytes | None = None,
    ) -> dict:
        """`sign_challenge`: put `challenge` in the client data but sign over another one (a different challenge in the signed bytes)."""
        self.count = self.count + 1 if count is None else count
        cd = self._client_data(typ, challenge, origin)
        auth = hashlib.sha256((rp_id or self.rp_id).encode()).digest() + bytes([flags]) + struct.pack(">I", self.count)
        signed_cd = self._client_data(typ, sign_challenge, origin) if sign_challenge is not None else cd
        sig = self._sign(auth + hashlib.sha256(signed_cd).digest())
        if bad_sig:
            sig = sig[:-1] + bytes([sig[-1] ^ 1])
        return {
            "credential_id": b64u(credential_id or self.credential_id),
            "client_data_json": b64u(cd),
            "authenticator_data": b64u(auth),
            "signature": b64u(sig),
        }
