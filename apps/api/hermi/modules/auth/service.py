# ruff: noqa: E501  (long comments and docstrings)
"""Sign-in provisioning and the dev personas (04 sections 1.2 and 5.1)."""

import uuid
from datetime import UTC, datetime

from fastapi.exceptions import RequestValidationError
from sqlalchemy import Engine
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import Settings
from hermi.errors import ApiError
from hermi.modules.auth import legacy_claim, repo
from hermi.modules.auth.schemas import BootstrapIn, DevSessionOut, LegacyClaimIn, Me, PersonaOut
from hermi.security.jwt import VerifiedToken, mint_dev_token

RELAY_DOMAIN = "@privaterelay.appleid.com"
# shortcut: no client gate yet and no flag evaluation. Replace both with the feature_flags read when the admin
# console (08) lands, and the real minimum version when the first iOS build ships.
MIN_CLIENT_VERSION = "0.0.0"
SERVED_STATUSES = (
    "active",
    "pending_deletion",
)  # a pending deletion can still sign in to cancel it
DEV_TTL_SECONDS = 3600
_ME_COLUMNS = (
    "id",
    "email",
    "email_is_relay",
    "locale",
    "timezone",
    "home_currency",
    "home_airports",
    "status",
    "tier",
    "me_person_id",
)


def _invalid(where: str, field: str, msg: str) -> RequestValidationError:
    """The 04 section 3 validation_failed problem, with the field named in errors[]."""
    return RequestValidationError([{"loc": (where, field), "type": "value_error", "msg": msg}])


def _provider_subject(token: VerifiedToken) -> str | None:
    """The upstream Apple or Google id, which survives deleting the account (03 5.8). Email has none."""
    # shortcut: read from user_metadata, which a Supabase user can edit, so a user could blank or swap it to dodge the
    # identity_hashes check. Upgrade when the Auth hook (POST /webhooks/supabase) or the admin identities[] lookup lands:
    # read provider_subject and the relay flag from there, never from the token's user_metadata.
    if token.provider not in ("apple", "google"):
        return None
    meta = token.claims.get("user_metadata") or {}
    value = meta.get("provider_id") or meta.get("sub")
    return value if isinstance(value, str) and value else None


def _is_relay(token: VerifiedToken) -> bool:
    meta = token.claims.get("user_metadata") or {}
    return bool(
        (token.email or "").lower().endswith(RELAY_DOMAIN)
        or meta.get("is_private_email") in (True, "true")
    )


def get_me(session: Session, user_id: uuid.UUID, r: RowMapping | None = None) -> Me:
    r = r or repo.me_row(session, user_id)
    return Me(
        **{k: r[k] for k in _ME_COLUMNS},
        display_name=r["display_name"] or None,
        consents=repo.current_consents(session, user_id),
        flags={},
        min_client_version=MIN_CLIENT_VERSION,
        server_time=datetime.now(UTC),
    )


def bootstrap(engine: Engine, token: VerifiedToken, body: BootstrapIn) -> tuple[Me, bool]:
    """Create the account on first sign-in. Returns (Me, created). The only path a JWT without a users row can take."""
    if not body.age_confirmed:
        raise _invalid("body", "age_confirmed", "Confirm your age to create an account.")
    if not token.email:
        raise _invalid("token", "email", "Your sign-in method did not share an email address.")
    with Session(engine) as session:
        try:
            user_id, created = repo.bootstrap_user(
                session,
                provider=token.provider,
                subject=token.subject,
                email=token.email,
                email_is_relay=_is_relay(token),
                display_name=body.display_name,
                provider_subject=_provider_subject(token),
            )
            repo.as_user(session, user_id)
            if created:
                repo.update_profile(session, user_id, body.model_dump())
                repo.ensure_referral_code(session)
            row = repo.me_row(session, user_id)
            if row["status"] not in SERVED_STATUSES:
                raise ApiError(
                    403, "account_inactive", "This account is not active. Contact support."
                )
            me = get_me(session, user_id, row)
            session.commit()
        except IntegrityError as e:
            session.rollback()
            diag = getattr(e.orig, "diag", None)
            if (
                getattr(e.orig, "sqlstate", None) != "23505"
                or diag.constraint_name != "uq_users_email"
            ):
                raise
            # The race of one identity is settled inside bootstrap_user, so this is another account's email.
            with Session(engine) as check:
                if legacy_claim.email_pending(check, token.email):
                    raise ApiError(
                        409,
                        "email_in_use",
                        "Your account is waiting for you. Open the claim link we emailed you.",
                        extra={"legacy_claim_pending": True},
                    ) from None
            raise ApiError(
                409,
                "email_in_use",
                "That email already has an account. Sign in with the method you used before.",
            ) from None
    return me, created


def redeem_legacy_claim(engine: Engine, token: VerifiedToken, body: LegacyClaimIn) -> Me:
    """Attach the signed-in identity to the legacy users row (04 section 5.1). 410 for an unknown, used or expired token."""
    with Session(engine) as session:
        try:
            user_id = legacy_claim.redeem(
                session,
                body.token,
                provider=token.provider,
                subject=token.subject,
                email=token.email,
                email_is_relay=_is_relay(token),
                provider_subject=_provider_subject(token),
            )
        except IntegrityError:
            session.rollback()
            raise ApiError(
                409,
                "email_in_use",
                "This sign-in already has an account. Sign out and use the one from your claim email.",
            ) from None
        if user_id is None:
            raise ApiError(
                410,
                "claim_link_expired",
                "This claim link has expired or was already used. Ask for a new link.",
            )
        repo.as_user(session, user_id)
        row = repo.me_row(session, user_id)
        if row["status"] not in SERVED_STATUSES:
            raise ApiError(403, "account_inactive", "This account is not active. Contact support.")
        me = get_me(session, user_id, row)
        session.commit()
    return me


# --- dev personas ---------------------------------------------------------------------------------------------------

PERSONAS: dict[str, PersonaOut] = {
    p.persona: p
    for p in (
        PersonaOut(
            persona="free", label="Free user", email="free@hermi.test", tier="free", is_admin=False
        ),
        PersonaOut(
            persona="plus", label="Plus user", email="plus@hermi.test", tier="plus", is_admin=False
        ),
        PersonaOut(
            persona="admin", label="Admin", email="admin@hermi.test", tier="free", is_admin=True
        ),
    )
}


def dev_session(settings: Settings, engine: Engine, persona: str) -> DevSessionOut:
    """Make sure all three personas exist (through bootstrap, like a real sign-in), then mint a token for one."""
    for p in PERSONAS.values():
        token = VerifiedToken(f"dev-persona-{p.persona}", "email", p.email, {})
        me, _ = bootstrap(engine, token, BootstrapIn(display_name=p.label, age_confirmed=True))
        with db.system_session(
            "dev_session", settings=settings, route="POST /v1/dev/session"
        ) as system:
            repo.grant_persona(system, me.id, tier=p.tier, is_admin=p.is_admin)
    return DevSessionOut(
        access_token=mint_dev_token(
            settings,
            f"dev-persona-{persona}",
            email=PERSONAS[persona].email,
            ttl_seconds=DEV_TTL_SECONDS,
        ),
        token_type="bearer",
        expires_in=DEV_TTL_SECONDS,
        persona=persona,
    )
