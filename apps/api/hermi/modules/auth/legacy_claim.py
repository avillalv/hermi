# ruff: noqa: E501  (long docstrings and SQL)
"""Legacy claim links (04 section 5.1, WF-040): the importer mints a token per pre-created owner, the owner redeems it once."""

import hashlib
import secrets
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

CLAIM_DAYS = 7


def hash_token(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def create_claim(session: Session, user_id: uuid.UUID) -> str:
    """Store a claim for a legacy users row and return the raw token for the emailed link. Runs on the system login:
    the table is closed to the API role. The token is never stored, only its sha256."""
    token = secrets.token_urlsafe(32)
    session.execute(
        text(
            "INSERT INTO legacy_claims (user_id, token_hash, expires_at) VALUES (:u, :h, now() + make_interval(days => :d))"
        ),
        {"u": user_id, "h": hash_token(token), "d": CLAIM_DAYS},
    )
    return token


def redeem(
    session: Session,
    token: str,
    *,
    provider: str,
    subject: str,
    email: str | None,
    email_is_relay: bool,
    provider_subject: str | None,
) -> uuid.UUID | None:
    """The definer function: the claimed user id, or None for an unknown, used or expired token."""
    return session.execute(
        text("SELECT redeem_legacy_claim(:h, :p, :s, CAST(:e AS citext), :r, :ps)"),
        {
            "h": hash_token(token),
            "p": provider,
            "s": subject,
            "e": email,
            "r": email_is_relay,
            "ps": provider_subject,
        },
    ).scalar()


def email_pending(session: Session, email: str) -> bool:
    return bool(
        session.execute(
            text("SELECT legacy_claim_pending(CAST(:e AS citext))"), {"e": email}
        ).scalar()
    )
