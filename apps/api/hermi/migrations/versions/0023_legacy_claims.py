"""0023_legacy_claims: one-time claim links for the pre-created legacy owner accounts (04 section 5.1, WF-040).

The importer pre-creates each owner's users row with no auth_identities row and emails a link carrying a random token.
Only sha256(token) is stored. The table is closed to the API role (no grant, row-level security with no policy), like
identity_hashes: the API reaches it through two definer functions. redeem_legacy_claim attaches the signed-in identity to
the legacy users row and marks the token used. legacy_claim_pending tells bootstrap that an email belongs to a legacy row
that nobody has claimed yet, so it answers 409 email_in_use instead of making a second account.

Revision ID: 0023_legacy_claims
Revises: 0022_vote_tombstone
"""

from alembic import op

revision = "0023_legacy_claims"
down_revision = "0022_vote_tombstone"
branch_labels = None
depends_on = None

REDEEM = "redeem_legacy_claim(bytea, text, text, citext, boolean, text)"
PENDING = "legacy_claim_pending(citext)"

UP = rf"""
CREATE TABLE legacy_claims (
  id          uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  token_hash  bytea NOT NULL,                                       -- sha256 of the raw token; the token itself is never stored
  expires_at  timestamptz NOT NULL DEFAULT now() + interval '7 days',
  used_at     timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_legacy_claims_token UNIQUE (token_hash)
);
CREATE INDEX ix_legacy_claims_user ON legacy_claims (user_id);
ALTER TABLE legacy_claims ENABLE ROW LEVEL SECURITY;  ALTER TABLE legacy_claims FORCE ROW LEVEL SECURITY;
REVOKE ALL ON legacy_claims FROM hermi_app;
GRANT UPDATE ON legacy_claims TO hermi_definer;

-- Returns the claimed user id, or null for an unknown, used or expired token. A retry by the identity that already
-- redeemed the token gets the same user back. Another identity, or one that already has an account, is an error.
CREATE FUNCTION redeem_legacy_claim(p_hash bytea, p_provider text, p_subject text, p_email citext,
                                    p_email_is_relay boolean, p_provider_subject text)
RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  c record;
  v_owner uuid;
BEGIN
  SELECT * INTO c FROM legacy_claims WHERE token_hash = p_hash FOR UPDATE;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT ai.user_id INTO v_owner FROM auth_identities ai WHERE ai.provider = p_provider AND ai.subject = p_subject;
  IF c.used_at IS NOT NULL THEN
    IF v_owner = c.user_id THEN RETURN v_owner; END IF;
    RETURN NULL;
  END IF;
  IF c.expires_at <= now() THEN RETURN NULL; END IF;
  IF v_owner IS NOT NULL THEN
    RAISE EXCEPTION 'identity_has_account' USING ERRCODE = '23505';
  END IF;
  INSERT INTO auth_identities (user_id, provider, subject, provider_subject, email, email_is_relay, last_login_at)
  VALUES (c.user_id, p_provider, p_subject, p_provider_subject, p_email, coalesce(p_email_is_relay, false), now());
  UPDATE legacy_claims SET used_at = now() WHERE id = c.id;
  RETURN c.user_id;
END $$;
ALTER FUNCTION {REDEEM} OWNER TO hermi_definer;
REVOKE ALL ON FUNCTION {REDEEM} FROM PUBLIC;
GRANT EXECUTE ON FUNCTION {REDEEM} TO hermi_app;

CREATE FUNCTION legacy_claim_pending(p_email citext) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM users u JOIN legacy_claims c ON c.user_id = u.id
                  WHERE u.email = p_email AND NOT EXISTS (SELECT 1 FROM auth_identities ai WHERE ai.user_id = u.id))
$$;
ALTER FUNCTION {PENDING} OWNER TO hermi_definer;
REVOKE ALL ON FUNCTION {PENDING} FROM PUBLIC;
GRANT EXECUTE ON FUNCTION {PENDING} TO hermi_app;
"""

DOWN = f"""
DROP FUNCTION {PENDING};
DROP FUNCTION {REDEEM};
DROP TABLE legacy_claims;
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UP)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DOWN)
