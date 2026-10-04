# ruff: noqa: E501  (long SQL strings)
"""SQL for sign-in provisioning (03 sections 5.1 and 6.4). Every statement runs as the API role (RLS applies) except
grant_persona, which the dev routes call with the system login."""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def bootstrap_user(
    session: Session,
    *,
    provider: str,
    subject: str,
    email: str,
    email_is_relay: bool,
    display_name: str | None,
    provider_subject: str | None,
) -> tuple[uuid.UUID, bool]:
    """The definer function: one users, auth_identities, "Me" people and entitlements row, idempotent and race safe."""
    row = session.execute(
        text(
            "SELECT user_id, created FROM bootstrap_user(:p, :s, CAST(:e AS citext), :r, :n, :ps)"
        ),
        {
            "p": provider,
            "s": subject,
            "e": email,
            "r": email_is_relay,
            "n": display_name,
            "ps": provider_subject,
        },
    ).one()
    return row[0], row[1]


def as_user(session: Session, user_id: uuid.UUID) -> None:
    """Make the rest of this transaction run as the user (the same setting request_transaction makes)."""
    session.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": str(user_id)})


def update_profile(session: Session, user_id: uuid.UUID, values: dict) -> None:
    """Only the columns the app role may update (03 section 6.1), and only the ones the client sent."""
    cols = ("locale", "timezone", "home_currency", "home_airports")
    sets = {k: v for k, v in values.items() if k in cols and v is not None}
    if sets:
        session.execute(
            text("UPDATE users SET " + ", ".join(f"{k} = :{k}" for k in sets) + " WHERE id = :id"),
            {**sets, "id": user_id},
        )


def ensure_referral_code(session: Session) -> None:
    """my_referral_code() creates the caller's code on first use; it needs app.user_id, so call as_user first."""
    session.execute(text("SELECT my_referral_code()"))


def me_row(session: Session, user_id: uuid.UUID):
    return (
        session.execute(
            text(
                "SELECT u.id, u.email::text AS email, u.email_is_relay, u.display_name, u.locale, u.timezone, "
                "       u.home_currency::text AS home_currency, u.home_airports::text[] AS home_airports, "
                "       u.status::text AS status, coalesce(e.tier_code, 'free') AS tier, p.id AS me_person_id "
                "  FROM users u LEFT JOIN entitlements e ON e.user_id = u.id "
                "  LEFT JOIN people p ON p.owner_user_id = u.id AND p.is_self "
                " WHERE u.id = :id"
            ),
            {"id": user_id},
        )
        .mappings()
        .one()
    )


def current_consents(session: Session, user_id: uuid.UUID) -> list[dict]:
    """The latest row per kind, kept only when granted."""
    rows = session.execute(
        text(
            "SELECT kind, version, accepted_at FROM ("
            "  SELECT DISTINCT ON (kind) kind, version, granted, created_at AS accepted_at "
            "    FROM consents WHERE user_id = :id ORDER BY kind, created_at DESC, id DESC) c "
            " WHERE granted ORDER BY kind"
        ),
        {"id": user_id},
    ).mappings()
    return [dict(r) for r in rows]


def grant_persona(conn, user_id: uuid.UUID, *, tier: str, is_admin: bool) -> None:
    """Dev only, on the system login: the app role cannot write entitlements or admin_users (03 section 6.1)."""
    if tier != "free":
        conn.execute(
            text(
                "UPDATE entitlements SET tier_code = :t, source = 'comp', "
                "       limits = (SELECT limits FROM plans WHERE code = :t), computed_at = now() "
                " WHERE user_id = :u"
            ),
            {"t": tier, "u": user_id},
        )
    if is_admin:
        conn.execute(
            text(
                "INSERT INTO admin_users (user_id, role) VALUES (:u, 'owner') ON CONFLICT DO NOTHING"
            ),
            {"u": user_id},
        )
