# ruff: noqa: E501  (long SQL strings)
"""0028_admin_2fa: admin second factors, recovery codes, sessions and challenges (WF-058.2, 08 section 2.2).

Four tables next to admin_users (03 section 5.16): `admin_credentials` (WebAuthn public keys and the encrypted TOTP
secret), `admin_recovery_codes` (salted hashes, single use), `admin_sessions` (the server side of the 8 hour absolute,
30 minute idle cookie, plus the step-up time) and `admin_auth_challenges` (single use WebAuthn challenges). Like
admin_users they are closed to hermi_app and hermi_worker by grants, not row-level security; hermi_admin reads and writes them.

Revision ID: 0028_admin_2fa
Revises: 0027_credit_balance_definer
"""

from alembic import op

revision = "0028_admin_2fa"
down_revision = "0027_credit_balance_definer"
branch_labels = None
depends_on = None

UP = r"""
CREATE TABLE admin_credentials (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id         uuid NOT NULL REFERENCES admin_users (user_id) ON DELETE CASCADE,
  kind            text NOT NULL,
  label           text NOT NULL DEFAULT '',
  credential_id   bytea,                                           -- webauthn: the authenticator's credential id
  public_key      bytea,                                           -- webauthn: DER SubjectPublicKeyInfo (ES256 or RS256)
  sign_count      bigint NOT NULL DEFAULT 0,                       -- webauthn: last signature counter seen
  secret_enc      bytea,                                           -- totp: AES-256-GCM sealed secret (FIELD_ENCRYPTION_KEY), bound to user_id
  last_used_step  bigint,                                          -- totp: last accepted 30 second counter, so a code works once
  confirmed_at    timestamptz,                                     -- null while a TOTP enrolment waits for its first code
  last_used_at    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_admin_credentials_kind CHECK (kind IN ('webauthn', 'totp')),
  CONSTRAINT ck_admin_credentials_shape CHECK (
    (kind = 'webauthn' AND credential_id IS NOT NULL AND public_key IS NOT NULL AND secret_enc IS NULL)
    OR (kind = 'totp' AND secret_enc IS NOT NULL AND credential_id IS NULL AND public_key IS NULL))
);
CREATE INDEX ix_admin_credentials_user ON admin_credentials (user_id);
CREATE UNIQUE INDEX ux_admin_credentials_credential_id ON admin_credentials (credential_id) WHERE kind = 'webauthn';
CREATE UNIQUE INDEX ux_admin_credentials_totp_pending ON admin_credentials (user_id) WHERE kind = 'totp' AND confirmed_at IS NULL;

CREATE TABLE admin_recovery_codes (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id     uuid NOT NULL REFERENCES admin_users (user_id) ON DELETE CASCADE,
  salt        bytea NOT NULL,
  code_hash   bytea NOT NULL,                                      -- sha256(salt || normalized code); the code itself is shown once
  used_at     timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_admin_recovery_codes_user ON admin_recovery_codes (user_id);

CREATE TABLE admin_sessions (
  id            uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id       uuid NOT NULL REFERENCES admin_users (user_id) ON DELETE CASCADE,
  token_hash    bytea NOT NULL UNIQUE,                             -- HMAC-SHA256 of the cookie value; the cookie is never stored
  method        text NOT NULL,                                     -- webauthn, totp or recovery
  created_at    timestamptz NOT NULL,
  last_seen_at  timestamptz NOT NULL,                              -- idle clock: 30 minutes
  expires_at    timestamptz NOT NULL,                              -- absolute clock: created_at + 8 hours
  stepup_at     timestamptz,                                       -- last fresh WebAuthn or TOTP check: valid 5 minutes
  user_agent    text,
  CONSTRAINT ck_admin_sessions_method CHECK (method IN ('webauthn', 'totp', 'recovery'))
);
CREATE INDEX ix_admin_sessions_user ON admin_sessions (user_id);
CREATE INDEX ix_admin_sessions_expires ON admin_sessions (expires_at);

CREATE TABLE admin_auth_challenges (
  id          uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id     uuid NOT NULL REFERENCES admin_users (user_id) ON DELETE CASCADE,
  purpose     text NOT NULL,
  challenge   bytea NOT NULL,
  expires_at  timestamptz NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_admin_auth_challenges_purpose CHECK (purpose IN ('register', 'signin', 'stepup'))
);
CREATE INDEX ix_admin_auth_challenges_user ON admin_auth_challenges (user_id);

-- rls-exempt: admin_credentials (closed to hermi_app and hermi_worker by grants, like admin_users)
-- rls-exempt: admin_recovery_codes (closed to hermi_app and hermi_worker by grants, like admin_users)
-- rls-exempt: admin_sessions (closed to hermi_app and hermi_worker by grants, like admin_users)
-- rls-exempt: admin_auth_challenges (closed to hermi_app and hermi_worker by grants, like admin_users)
-- Closed to the API and the worker (no job has a reason to read a credential or a session): the default privileges
-- gave both roles these tables, so take them back. hermi_admin keeps its default SELECT and gets the writes.
REVOKE ALL ON admin_credentials, admin_recovery_codes, admin_sessions, admin_auth_challenges FROM hermi_app, hermi_worker;
GRANT INSERT, UPDATE, DELETE ON admin_credentials, admin_recovery_codes, admin_sessions, admin_auth_challenges TO hermi_admin;
"""

DOWN = r"""
DROP TABLE admin_auth_challenges;
DROP TABLE admin_sessions;
DROP TABLE admin_recovery_codes;
DROP TABLE admin_credentials;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
