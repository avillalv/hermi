"""0002_identity: users, auth identities, device attestations, guest allowances, devices (03 section 5.1).

Grants, row-level security and policies land in 0014_rls.

Revision ID: 0002_identity
Revises: 0001_setup
"""

from alembic import op

revision = "0002_identity"
down_revision = "0001_setup"
branch_labels = None
depends_on = None

UP = """
CREATE TYPE user_status AS ENUM ('active', 'suspended', 'pending_deletion', 'deleted');

CREATE TABLE users (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  email               citext NOT NULL,                          -- may be an Apple relay address
  email_is_relay      boolean NOT NULL DEFAULT false,
  email_verified_at   timestamptz,                              -- set at sign-in when the provider proved the address (Apple, Google or an email code); A condition of the import reward (5.9)
  display_name        text NOT NULL DEFAULT '' CHECK (char_length(display_name) <= 80),
  locale              text NOT NULL DEFAULT 'en-US',
  timezone            text NOT NULL DEFAULT 'UTC',
  home_currency       currency_code NOT NULL DEFAULT 'USD',
  home_airports       iata_code[] NOT NULL DEFAULT '{}',
  country_code        country_code2,                            -- storefront or detected, drives "Ad" labels
  status              user_status NOT NULL DEFAULT 'active',    -- 'suspended' is an owner decision in the admin console (08 6.12); the API answers 403 account_inactive
  hide_booking_links  boolean NOT NULL DEFAULT false,           -- Settings: "Hide booking links"
  prefs               jsonb NOT NULL DEFAULT '{}'::jsonb,       -- per-user settings (replaces app_settings per-user keys) and the paywall frequency state (07 6.5); never a place for state another user or a job must read
  last_seen_at        timestamptz,
  suspended_at        timestamptz,                              -- set with status 'suspended'
  sharing_suspended_at timestamptz,                             -- moderation: no new share links or invites (08 6.12); the account still works
  pack_purchases_blocked_until timestamptz,                     -- refund-abuse block (07 5.6); written by the billing service, the app role cannot update it
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  deleted_at          timestamptz,
  CONSTRAINT ck_users_deleted CHECK (status <> 'deleted' OR deleted_at IS NOT NULL),
  CONSTRAINT ck_users_suspended CHECK (status <> 'suspended' OR suspended_at IS NOT NULL)
);
CREATE UNIQUE INDEX uq_users_email ON users (email) WHERE deleted_at IS NULL;
CREATE INDEX ix_users_status ON users (status) WHERE status <> 'active';
SELECT add_updated_at_trigger('users');

CREATE TABLE auth_identities (
  id                          uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id                     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  provider                    text NOT NULL,
  subject                     text NOT NULL,                     -- Supabase user id (JWT sub) or provider subject
  provider_subject            text,                              -- the upstream Apple or Google subject (the identity's id in the Supabase user object); null for email. Unlike subject it survives deleting and re-creating the account, so it feeds identity_hashes (5.8). Set by bootstrap_user() at sign-in
  email                       citext,
  email_is_relay              boolean NOT NULL DEFAULT false,
  provider_refresh_token_enc  bytea,                             -- Apple refresh token, encrypted, for revoke on deletion
  created_at                  timestamptz NOT NULL DEFAULT now(),
  last_login_at               timestamptz,
  CONSTRAINT ck_auth_identities_provider CHECK (provider IN ('apple', 'google', 'email')),
  CONSTRAINT uq_auth_identities_provider_subject UNIQUE (provider, subject)
);
CREATE INDEX ix_auth_identities_user ON auth_identities (user_id);

-- Guests have no users row: a guest's App Attest key lives only here. No direct grant to hermi_app;
-- the attest endpoints write it through a definer function or an allowlisted SystemSession (04 section 5.1).
CREATE TABLE device_attestations (
  key_id        text PRIMARY KEY,                                -- App Attest key id
  public_key    bytea NOT NULL,
  counter       bigint NOT NULL DEFAULT 0,                       -- last assertion counter seen
  environment   text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_device_attestations_env CHECK (environment IN ('development', 'production'))
);

-- Guest AI under F-ACC-2: one row per attestation key and calendar month (UTC). Written only through a definer function.
CREATE TABLE guest_allowances (
  key_id        text NOT NULL REFERENCES device_attestations (key_id) ON DELETE CASCADE,
  period_key    text NOT NULL CHECK (period_key ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),   -- YYYY-MM
  credits_used  integer NOT NULL DEFAULT 0 CHECK (credits_used >= 0),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (key_id, period_key)
);
SELECT add_updated_at_trigger('guest_allowances');

-- The only writer of guest_allowances. Spends p_credits from the key's allowance for the current UTC month when the month's total stays within
-- p_limit (the Free monthly credits for guests, read from plans by the caller); returns false and changes nothing otherwise. A guest has no users row,
-- so there is no app_user_id() to check: the caller is the allowlisted SystemSession that verified the App Attest assertion (04 section 5.1),
-- and EXECUTE is granted to hermi_worker only.
CREATE FUNCTION spend_guest_allowance(p_key_id text, p_credits integer, p_limit integer) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_period text := to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM');
BEGIN
  IF p_credits <= 0 OR p_limit < 0 THEN RAISE EXCEPTION 'invalid amount' USING ERRCODE = '22023'; END IF;
  INSERT INTO guest_allowances (key_id, period_key, credits_used) VALUES (p_key_id, v_period, 0) ON CONFLICT DO NOTHING;
  UPDATE guest_allowances SET credits_used = credits_used + p_credits
   WHERE key_id = p_key_id AND period_key = v_period AND credits_used + p_credits <= p_limit;
  RETURN FOUND;
END $$;
ALTER FUNCTION spend_guest_allowance(text, integer, integer) OWNER TO hermi_definer;
REVOKE EXECUTE ON FUNCTION spend_guest_allowance(text, integer, integer) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION spend_guest_allowance(text, integer, integer) TO hermi_worker;

CREATE TABLE devices (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id             uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  platform            text NOT NULL,
  device_name         text,
  push_token          text,                                      -- APNs token; null until permission is granted
  push_environment    text,
  app_version         text,
  os_version          text,
  refresh_token_hash  bytea,                                     -- session refresh token hash, for "sign out everywhere"
  attestation_key_id  text REFERENCES device_attestations (key_id) ON DELETE SET NULL,   -- App Attest key id; null for web and for devices not yet attested
  last_seen_at        timestamptz NOT NULL DEFAULT now(),
  revoked_at          timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_devices_platform CHECK (platform IN ('ios', 'android', 'web')),
  CONSTRAINT ck_devices_push_env CHECK (push_environment IS NULL OR push_environment IN ('sandbox', 'production'))
);
CREATE UNIQUE INDEX uq_devices_push_token ON devices (platform, push_token) WHERE push_token IS NOT NULL AND revoked_at IS NULL;
CREATE INDEX ix_devices_user ON devices (user_id) WHERE revoked_at IS NULL;
"""

DOWN = """
DROP TABLE devices;
DROP FUNCTION spend_guest_allowance(text, integer, integer);
DROP TABLE guest_allowances;
DROP TABLE device_attestations;
DROP TABLE auth_identities;
DROP TABLE users;
DROP TYPE user_status;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
