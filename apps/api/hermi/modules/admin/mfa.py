# ruff: noqa: E501  (long SQL)
"""Admin second factors (08 section 2.2): TOTP, WebAuthn passkeys and recovery codes, on the admin engine.

`mfa_enrolled` turns true when an admin holds a confirmed passkey (or TOTP as the fallback) and a recovery code set, and
is only ever set here, never cleared: using up the codes must not reopen enrolment to a bare Access identity.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from urllib.parse import urlsplit

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from hermi.config import NotConfigured
from hermi.errors import ApiError
from hermi.modules.admin import sessions
from hermi.modules.admin.identity import AdminPrincipal
from hermi.security import fieldcrypt, totp, webauthn

log = logging.getLogger("hermi.admin")
ISSUER = "Hermi admin"
RECOVERY_CODES = 10
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0, O, 1 or I


def rp(request: Request) -> tuple[str, str]:
    """(origin, rpId) of the admin console; the rpId is the origin's host."""
    origin = request.app.state.settings.admin_web_origin.rstrip("/")
    return origin, urlsplit(origin).hostname or "localhost"


def _unavailable() -> ApiError:
    return ApiError(503, "admin_unavailable", "Two-factor sign-in is not available right now.")


def refresh_enrolled(request: Request, user_id: uuid.UUID) -> bool:
    """Set `mfa_enrolled` when both halves exist; returns the value after. Never clears it."""
    with sessions.engine(request).begin() as c:
        row = c.execute(
            text(
                "UPDATE admin_users SET mfa_enrolled = true WHERE user_id = :u AND NOT mfa_enrolled "
                "AND EXISTS (SELECT 1 FROM admin_credentials WHERE user_id = :u AND confirmed_at IS NOT NULL) "
                "AND EXISTS (SELECT 1 FROM admin_recovery_codes WHERE user_id = :u AND used_at IS NULL) RETURNING true"
            ),
            {"u": user_id},
        ).first()
        if row:
            return True
        return bool(c.execute(text("SELECT mfa_enrolled FROM admin_users WHERE user_id = :u"), {"u": user_id}).scalar())


def factors(request: Request, user_id: uuid.UUID) -> dict:
    with sessions.engine(request).connect() as c:
        rows = c.execute(
            text(
                "SELECT kind, count(*) FILTER (WHERE confirmed_at IS NOT NULL) FROM admin_credentials WHERE user_id = :u GROUP BY kind"
            ),
            {"u": user_id},
        ).all()
        left = c.execute(
            text("SELECT count(*) FROM admin_recovery_codes WHERE user_id = :u AND used_at IS NULL"), {"u": user_id}
        ).scalar_one()
    by = dict(rows)
    return {"passkeys": by.get("webauthn", 0), "totp": by.get("totp", 0) > 0, "recovery_codes_left": left}


# --- TOTP --------------------------------------------------------------------------------------------------


def totp_begin(request: Request, admin: AdminPrincipal) -> tuple[str, str]:
    settings = request.app.state.settings
    secret = totp.new_secret()
    try:
        sealed = fieldcrypt.seal(settings, secret, admin.user_id.bytes)
    except (NotConfigured, fieldcrypt.FieldCryptError):
        log.error("admin_totp_unavailable", extra={"reason": "field_encryption_key"})
        raise _unavailable() from None
    with sessions.engine(request).begin() as c:
        c.execute(text("DELETE FROM admin_credentials WHERE user_id = :u AND kind = 'totp' AND confirmed_at IS NULL"), {"u": admin.user_id})
        c.execute(
            text("INSERT INTO admin_credentials (user_id, kind, label, secret_enc) VALUES (:u, 'totp', 'Authenticator app', :s)"),
            {"u": admin.user_id, "s": sealed},
        )
    return totp.b32(secret), totp.otpauth_uri(secret, admin.email, ISSUER)


def _totp_claim(request: Request, user_id: uuid.UUID, code: str, *, pending: bool) -> bool:
    """Check `code` against the admin's TOTP secret and claim its counter so it cannot be used twice."""
    t = sessions.now(request)
    cond = "confirmed_at IS NULL" if pending else "confirmed_at IS NOT NULL"
    with sessions.engine(request).begin() as c:
        rows = c.execute(
            text(f"SELECT id, secret_enc, last_used_step FROM admin_credentials WHERE user_id = :u AND kind = 'totp' AND {cond}"),
            {"u": user_id},
        ).all()
        for cred_id, sealed, last in rows:
            try:
                secret = fieldcrypt.unseal(request.app.state.settings, sealed, user_id.bytes)
            except (NotConfigured, fieldcrypt.FieldCryptError):
                log.error("admin_totp_unavailable", extra={"reason": "cannot_open_secret"})
                continue
            counter = totp.match(secret, code, t.timestamp())
            if counter is None or (last is not None and counter <= last):
                continue
            claimed = c.execute(
                text(
                    "UPDATE admin_credentials SET last_used_step = :n, last_used_at = :t, confirmed_at = coalesce(confirmed_at, :t) "
                    "WHERE id = :i AND (last_used_step IS NULL OR last_used_step < :n) RETURNING id"
                ),
                {"n": counter, "t": t, "i": cred_id},
            ).first()
            if claimed:
                if pending:  # the new secret replaces any earlier confirmed one
                    c.execute(
                        text("DELETE FROM admin_credentials WHERE user_id = :u AND kind = 'totp' AND id <> :i"),
                        {"u": user_id, "i": cred_id},
                    )
                return True
    return False


def totp_confirm(request: Request, user_id: uuid.UUID, code: str) -> bool:
    return _totp_claim(request, user_id, code, pending=True)


def totp_check(request: Request, user_id: uuid.UUID, code: str) -> bool:
    return _totp_claim(request, user_id, code, pending=False)


# --- recovery codes ----------------------------------------------------------------------------------------


def _normalize(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


def _digest(salt: bytes, code: str) -> bytes:
    return hashlib.sha256(salt + _normalize(code).encode()).digest()


def recovery_generate(request: Request, user_id: uuid.UUID) -> list[str]:
    """A new set of 10 codes (XXXX-XXXX-XXXX, 60 bits each) replacing any earlier set. Returned once, stored salted and hashed."""
    codes = ["-".join("".join(secrets.choice(_ALPHABET) for _ in range(4)) for _ in range(3)) for _ in range(RECOVERY_CODES)]
    rows = []
    for code in codes:
        salt = secrets.token_bytes(16)
        rows.append({"u": user_id, "s": salt, "h": _digest(salt, code)})
    with sessions.engine(request).begin() as c:
        c.execute(text("DELETE FROM admin_recovery_codes WHERE user_id = :u"), {"u": user_id})
        c.execute(text("INSERT INTO admin_recovery_codes (user_id, salt, code_hash) VALUES (:u, :s, :h)"), rows)
    return codes


def recovery_consume(request: Request, user_id: uuid.UUID, code: str) -> int | None:
    """Burn the code if it is an unused one of this admin. Returns how many codes are left, or None for no match."""
    if len(code) > 64:
        return None
    with sessions.engine(request).begin() as c:
        rows = c.execute(
            text("SELECT id, salt, code_hash FROM admin_recovery_codes WHERE user_id = :u AND used_at IS NULL"), {"u": user_id}
        ).all()
        hit = None
        for rid, salt, h in rows:  # no early exit: the time does not say which code matched
            if hmac.compare_digest(bytes(h), _digest(bytes(salt), code)):
                hit = rid
        if hit is None:
            return None
        used = c.execute(
            text("UPDATE admin_recovery_codes SET used_at = :t WHERE id = :i AND used_at IS NULL RETURNING id"),
            {"t": sessions.now(request), "i": hit},
        ).first()
        if not used:
            return None
        return len(rows) - 1


# --- WebAuthn ----------------------------------------------------------------------------------------------


def register_options(request: Request, admin: AdminPrincipal) -> tuple[uuid.UUID, dict]:
    origin, rp_id = rp(request)
    cid, challenge = sessions.issue_challenge(request, admin.user_id, "register")
    with sessions.engine(request).connect() as c:
        existing = c.execute(
            text("SELECT credential_id FROM admin_credentials WHERE user_id = :u AND kind = 'webauthn'"), {"u": admin.user_id}
        ).scalars()
        exclude = [{"type": "public-key", "id": webauthn.b64u(bytes(x))} for x in existing]
    return cid, {
        "rp": {"id": rp_id, "name": ISSUER},
        "user": {"id": webauthn.b64u(admin.user_id.bytes), "name": admin.email, "displayName": admin.email},
        "challenge": webauthn.b64u(challenge),
        "pubKeyCredParams": [{"type": "public-key", "alg": webauthn.COSE_ES256}, {"type": "public-key", "alg": webauthn.COSE_RS256}],
        "timeout": int(sessions.CHALLENGE_TTL.total_seconds() * 1000),
        "attestation": "none",
        "authenticatorSelection": {"residentKey": "preferred", "userVerification": "required"},
        "excludeCredentials": exclude,
    }


def register_verify(
    request: Request, admin: AdminPrincipal, challenge_id: uuid.UUID, client_data_json: str, attestation_object: str, label: str
) -> None:
    """Raises WebAuthnError (the route maps it to one generic 422)."""
    challenge = sessions.consume_challenge(request, admin.user_id, "register", challenge_id)
    if challenge is None:
        raise webauthn.WebAuthnError("no_challenge")
    origin, rp_id = rp(request)
    cred_id, spki, count = webauthn.verify_registration(
        client_data_json=webauthn.b64u_decode(client_data_json),
        attestation_object=webauthn.b64u_decode(attestation_object),
        challenge=challenge,
        origin=origin,
        rp_id=rp_id,
    )
    try:
        with sessions.engine(request).begin() as c:
            taken = c.execute(
                text("SELECT 1 FROM admin_credentials WHERE kind = 'webauthn' AND credential_id = :c"), {"c": cred_id}
            ).first()
            if taken:
                raise webauthn.WebAuthnError("credential_exists")
            c.execute(
                text(
                    "INSERT INTO admin_credentials (user_id, kind, label, credential_id, public_key, sign_count, confirmed_at) "
                    "VALUES (:u, 'webauthn', :l, :c, :k, :n, :t)"
                ),
                {"u": admin.user_id, "l": label[:60], "c": cred_id, "k": spki, "n": count, "t": sessions.now(request)},
            )
    except IntegrityError:  # two registrations of one credential racing past the SELECT
        raise webauthn.WebAuthnError("credential_exists") from None


def assertion_options(request: Request, admin: AdminPrincipal, purpose: str) -> tuple[uuid.UUID, dict]:
    _origin, rp_id = rp(request)
    cid, challenge = sessions.issue_challenge(request, admin.user_id, purpose)
    with sessions.engine(request).connect() as c:
        ids = c.execute(
            text("SELECT credential_id FROM admin_credentials WHERE user_id = :u AND kind = 'webauthn' AND confirmed_at IS NOT NULL"),
            {"u": admin.user_id},
        ).scalars()
        allow = [{"type": "public-key", "id": webauthn.b64u(bytes(x))} for x in ids]
    return cid, {
        "challenge": webauthn.b64u(challenge),
        "rpId": rp_id,
        "allowCredentials": allow,
        "userVerification": "required",
        "timeout": int(sessions.CHALLENGE_TTL.total_seconds() * 1000),
    }


def assertion_verify(
    request: Request,
    user_id: uuid.UUID,
    purpose: str,
    challenge_id: uuid.UUID,
    *,
    credential_id: str,
    client_data_json: str,
    authenticator_data: str,
    signature: str,
) -> None:
    """Raises WebAuthnError unless the assertion is a fresh one from a passkey this admin enrolled."""
    challenge = sessions.consume_challenge(request, user_id, purpose, challenge_id)
    if challenge is None:
        raise webauthn.WebAuthnError("no_challenge")
    origin, rp_id = rp(request)
    cid = webauthn.b64u_decode(credential_id)
    with sessions.engine(request).begin() as c:
        row = c.execute(
            text(
                "SELECT id, public_key, sign_count FROM admin_credentials "
                "WHERE user_id = :u AND kind = 'webauthn' AND confirmed_at IS NOT NULL AND credential_id = :c"
            ),
            {"u": user_id, "c": cid},
        ).first()
        if row is None:
            raise webauthn.WebAuthnError("unknown_credential")
        new_count = webauthn.verify_assertion(
            client_data_json=webauthn.b64u_decode(client_data_json),
            authenticator_data=webauthn.b64u_decode(authenticator_data),
            signature=webauthn.b64u_decode(signature),
            challenge=challenge,
            origin=origin,
            rp_id=rp_id,
            spki=bytes(row[1]),
            stored_count=row[2],
        )
        moved = c.execute(
            text("UPDATE admin_credentials SET sign_count = :n, last_used_at = :t WHERE id = :i AND sign_count = :old RETURNING id"),
            {"n": new_count, "t": sessions.now(request), "i": row[0], "old": row[2]},
        ).first()
        if not moved:
            raise webauthn.WebAuthnError("counter_race")
