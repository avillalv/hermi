"""0012_admin_privacy: admin and privacy tables (03 sections 5.16, 5.17).

The SQL is the DDL of those sections, verbatim. No comment colon needs escaping.
Grants, row-level security and policies land in 0014_rls. No grant is given here.

Revision ID: 0012_admin_privacy
Revises: 0011_checklist_notes
"""

from alembic import op

revision = "0012_admin_privacy"
down_revision = "0011_checklist_notes"
branch_labels = None
depends_on = None

UP = r"""
CREATE TYPE admin_role AS ENUM ('owner', 'support', 'finance', 'engineer', 'content');

CREATE TABLE admin_users (
  user_id       uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
  role          admin_role NOT NULL,
  mfa_enrolled  boolean NOT NULL DEFAULT false,
  created_by    uuid REFERENCES users (id) ON DELETE SET NULL,
  disabled_at   timestamptz,                                      -- an admin is enabled while disabled_at is null; setting it ends every session within 60 seconds (08 2.2)
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE feature_flags (
  key            text PRIMARY KEY,                               -- lowercase snake_case, e.g. serpapi_live_fares
  kind           text NOT NULL DEFAULT 'flag',                   -- flag, experiment (key starts with exp_) or setting (key starts with setting_; the value is in rules)
  description    text NOT NULL DEFAULT '',
  enabled        boolean NOT NULL DEFAULT false,                 -- master switch
  rollout_pct    smallint NOT NULL DEFAULT 100 CHECK (rollout_pct BETWEEN 0 AND 100),
  rules          jsonb NOT NULL DEFAULT '{}'::jsonb,             -- {"tiers": [...], "countries": [...], "user_ids": [...], "platforms": [...], "min_app_version": "1.2.0", "max_app_version": "1.9.9"}; settings keep their value here
  variants       jsonb NOT NULL DEFAULT '{}'::jsonb,             -- A/B cells and weights; assignment = hash(key, user_id), so no assignment table
  updated_by     uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_feature_flags_key CHECK (key ~ '^[a-z][a-z0-9_]{1,62}$'),
  CONSTRAINT ck_feature_flags_kind CHECK (kind IN ('flag', 'experiment', 'setting')),
  CONSTRAINT ck_feature_flags_kind_prefix CHECK (kind = CASE WHEN key LIKE 'exp\_%' THEN 'experiment' WHEN key LIKE 'setting\_%' THEN 'setting' ELSE 'flag' END)
);
SELECT add_updated_at_trigger('feature_flags');

CREATE TABLE kill_switches (                                    -- engaged = the feature is OFF for everyone, immediately
  key            text PRIMARY KEY,                               -- ai.all, ai.free_tier, provider.serpapi, affiliate.all, affiliate.<program code>, signups, ...
                                                                 -- 'user:<users.id>' is a per-account hold: AI and live actions stop for that user only (08 6.2); these rows are created on demand, never seeded
  description    text NOT NULL DEFAULT '',
  engaged        boolean NOT NULL DEFAULT false,
  reason         text,
  engaged_by     uuid REFERENCES users (id) ON DELETE SET NULL,  -- the admin; null when an automatic breaker (auto_rule) engaged it
  engaged_at     timestamptz,
  expires_at     timestamptz,                                    -- mandatory for an admin-set switch (08 6.5): a scheduler job disengages it then and writes audit_log as 'system'
  expiry_notified_at timestamptz,                                -- the 15-minute warning to the owner went out
  auto_rule      jsonb,                                          -- e.g. {"metric": "anthropic_daily_spend_micros", "gte": 40000000}
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_kill_switches_key CHECK (key ~ '^([a-z][a-z0-9_]*(\.[a-z0-9_]+)+|[a-z][a-z0-9_]*|user:[0-9a-f-]{36})$'),
  CONSTRAINT ck_kill_switches_engaged CHECK (NOT engaged OR engaged_at IS NOT NULL),
  -- An admin-set switch needs an expiry. "Until cleared" (null) is allowed only for a provider switch during an incident, and the API lets only the owner pick it.
  CONSTRAINT ck_kill_switches_expiry CHECK (NOT engaged OR engaged_by IS NULL OR expires_at IS NOT NULL OR key LIKE 'provider.%'),
  CONSTRAINT ck_kill_switches_expiry_after CHECK (expires_at IS NULL OR engaged_at IS NULL OR expires_at > engaged_at)
);
CREATE INDEX ix_kill_switches_expiry ON kill_switches (expires_at) WHERE engaged AND expires_at IS NOT NULL;

CREATE TABLE audit_log (                                        -- append-only
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_user_id   uuid REFERENCES users (id) ON DELETE SET NULL,
  actor_type      text NOT NULL,
  action          text NOT NULL,                                 -- user.suspend, credits.adjust, flag.update, kill_switch.engage, refund.issue, ...
  entity_type     text,
  entity_id       text,
  before          jsonb,
  after           jsonb,
  reason          text,
  actor_role      admin_role,                                    -- the admin's role at the time of the action
  impersonation_id uuid,                                         -- set on every row written during an impersonation session (08 6.2)
  result          text NOT NULL DEFAULT 'ok',                    -- denied attempts are logged too
  error_code      text,
  user_agent      text,
  ip_hash         text,
  request_id      text,
  retention_class text NOT NULL DEFAULT 'standard',              -- extended for money, security and control actions (credits.*, refund.*, comp.*, admin_user.*, killswitch.*, impersonation.*, deletion.*, settings.*); prefixes listed in 08 4.2
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_audit_log_actor_type CHECK (actor_type IN ('user', 'admin', 'system', 'worker')),
  CONSTRAINT ck_audit_log_result CHECK (result IN ('ok', 'denied', 'error')),
  CONSTRAINT ck_audit_log_retention CHECK (retention_class IN ('standard', 'extended'))
);
CREATE INDEX ix_audit_log_entity ON audit_log (entity_type, entity_id, created_at DESC);
CREATE INDEX ix_audit_log_actor ON audit_log (actor_user_id, created_at DESC) WHERE actor_user_id IS NOT NULL;
CREATE INDEX ix_audit_log_time ON audit_log (retention_class, created_at);   -- retention sweeps
CREATE INDEX ix_audit_log_impersonation ON audit_log (impersonation_id) WHERE impersonation_id IS NOT NULL;

-- Append-only. hermi_app, hermi_worker and hermi_admin have no UPDATE, DELETE or TRUNCATE privilege on this table (6.1); this trigger is the second lock.
-- The one exception is retention_sweep() (8), a SECURITY DEFINER function owned by hermi_definer: it may delete a row only after the row's retention
-- period has passed (13 months standard, 7 years extended). The trigger function is not SECURITY DEFINER, so current_user is the caller's role, which is
-- hermi_definer only inside a definer function. The transaction-local setting is set by retention_sweep() alone and is a second condition, not the gate.
CREATE FUNCTION audit_log_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND current_user = 'hermi_definer'
     AND current_setting('hermi.audit_purge', true) = 'on'
     AND OLD.created_at < now() - (CASE OLD.retention_class WHEN 'extended' THEN interval '7 years' ELSE interval '13 months' END)
  THEN
    RETURN OLD;
  END IF;
  RAISE EXCEPTION 'audit_log is append-only';
END $$;
CREATE TRIGGER trg_audit_log_immutable BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
CREATE FUNCTION audit_log_no_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'audit_log is append-only'; END $$;
CREATE TRIGGER trg_audit_log_no_truncate BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_log_no_truncate();

CREATE TABLE support_tickets (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id             uuid REFERENCES users (id) ON DELETE SET NULL,
  trip_id             uuid REFERENCES trips (id) ON DELETE SET NULL,
  email               citext,
  subject             text NOT NULL CHECK (char_length(subject) BETWEEN 1 AND 200),
  category            text NOT NULL DEFAULT 'other',
  status              text NOT NULL DEFAULT 'open',
  priority            text NOT NULL DEFAULT 'normal',
  source              text NOT NULL DEFAULT 'in_app',
  assigned_admin_id   uuid REFERENCES users (id) ON DELETE SET NULL,
  messages            jsonb NOT NULL DEFAULT '[]'::jsonb,           -- [{at, from: user|admin, body}], one thread per ticket; a console reply is an entry with from: admin
  internal_notes      jsonb NOT NULL DEFAULT '[]'::jsonb,           -- [{at, admin_id, body}], never shown to the user (08 6.11)
  tags                text[] NOT NULL DEFAULT '{}',
  app_version         text,
  platform            text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  resolved_at         timestamptz,
  CONSTRAINT ck_support_tickets_category CHECK (category IN ('billing', 'credits', 'account', 'bug', 'affiliate', 'privacy', 'other')),
  CONSTRAINT ck_support_tickets_status CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
  CONSTRAINT ck_support_tickets_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  CONSTRAINT ck_support_tickets_source CHECK (source IN ('in_app', 'email', 'admin')),
  CONSTRAINT ck_support_tickets_contact CHECK (user_id IS NOT NULL OR email IS NOT NULL)
);
CREATE INDEX ix_support_tickets_queue ON support_tickets (status, priority, created_at) WHERE status IN ('open', 'pending');
CREATE INDEX ix_support_tickets_user ON support_tickets (user_id, created_at DESC) WHERE user_id IS NOT NULL;
CREATE INDEX ix_support_tickets_tags ON support_tickets USING gin (tags);
SELECT add_updated_at_trigger('support_tickets');

-- Reports on shared trips and AI content (08 6.12, 06 8.5). The reporter is never shown to the reported user.
-- A report on a research answer carries the run or note it came from and, when the run used the shared cache, its cache_key (no foreign key: the entry may be purged).
-- The report handler counts distinct reporters per cache_key, stores the count in shared_research_cache.report_count and sets flagged_at at three.
CREATE TABLE content_reports (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  reporter_user_id  uuid REFERENCES users (id) ON DELETE SET NULL,     -- null for a report from a public share page
  target_type       text NOT NULL,
  share_link_id     uuid REFERENCES trip_share_links (id) ON DELETE SET NULL,
  note_id           uuid REFERENCES notes (id) ON DELETE SET NULL,
  run_id            uuid REFERENCES runs (id) ON DELETE SET NULL,
  cache_key         char(64),
  reason            text NOT NULL,
  detail            text NOT NULL DEFAULT '' CHECK (char_length(detail) <= 1000),
  status            text NOT NULL DEFAULT 'open',
  action            text,                                               -- what the moderator did
  handled_by        uuid REFERENCES users (id) ON DELETE SET NULL,
  handled_at        timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_content_reports_target CHECK (target_type IN ('shared_trip', 'agent_note', 'ai_answer', 'research_cache')),
  CONSTRAINT ck_content_reports_target_ref CHECK (
    (target_type = 'shared_trip' AND share_link_id IS NOT NULL) OR
    (target_type = 'agent_note' AND note_id IS NOT NULL) OR
    (target_type = 'ai_answer' AND run_id IS NOT NULL) OR
    (target_type = 'research_cache' AND cache_key IS NOT NULL)),
  CONSTRAINT ck_content_reports_reason CHECK (reason IN ('spam', 'harmful', 'wrong_info', 'copyright', 'privacy')),
  CONSTRAINT ck_content_reports_status CHECK (status IN ('open', 'dismissed', 'actioned', 'escalated')),
  CONSTRAINT ck_content_reports_action CHECK (action IS NULL OR action IN ('dismiss', 'hide', 'disable_link', 'flag_cache', 'ask_edit', 'warn', 'suspend_sharing', 'escalate')),
  CONSTRAINT ck_content_reports_handled CHECK (status IN ('open', 'escalated') OR handled_at IS NOT NULL)
);
CREATE INDEX ix_content_reports_queue ON content_reports (status, created_at) WHERE status IN ('open', 'escalated');
CREATE INDEX ix_content_reports_cache ON content_reports (cache_key) WHERE cache_key IS NOT NULL;
CREATE INDEX ix_content_reports_reporter ON content_reports (reporter_user_id, created_at DESC) WHERE reporter_user_id IS NOT NULL;

CREATE TABLE consents (
  id          uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  kind        text NOT NULL,
  version     text NOT NULL,                                     -- version of the policy or consent text shown
  granted     boolean NOT NULL,                                  -- false = revoked
  source      text NOT NULL DEFAULT 'app',
  ip_hash     text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_consents_kind CHECK (kind IN ('terms', 'privacy', 'ai_processing', 'marketing_email', 'push_notifications', 'analytics')),
  CONSTRAINT ck_consents_source CHECK (source IN ('app', 'web', 'email', 'admin'))
);
CREATE INDEX ix_consents_current ON consents (user_id, kind, created_at DESC);

CREATE TABLE data_exports (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id         uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  status          text NOT NULL DEFAULT 'requested',
  format          text NOT NULL DEFAULT 'zip_json_pdf',
  asset_key       text,                                          -- object key in R2; link expires in 7 days
  size_bytes      bigint,
  download_count  integer NOT NULL DEFAULT 0,
  error           text,
  requested_at    timestamptz NOT NULL DEFAULT now(),
  ready_at        timestamptz,
  expires_at      timestamptz,
  CONSTRAINT ck_data_exports_status CHECK (status IN ('requested', 'processing', 'ready', 'expired', 'failed'))
);
CREATE INDEX ix_data_exports_user ON data_exports (user_id, requested_at DESC);
CREATE INDEX ix_data_exports_expiry ON data_exports (expires_at) WHERE status = 'ready';

CREATE TABLE deletion_requests (
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id                   uuid NOT NULL,                        -- no foreign key: survives the user's hard purge
  email_hash                text,                                 -- salted hash, to recognize a returning address without keeping it
  status                    text NOT NULL DEFAULT 'pending',
  reason                    text,
  checklist                 jsonb NOT NULL DEFAULT '{}'::jsonb,   -- per-step state: sessions, apple_revoke, push, invites, trips, purge, backups
  apple_token_revoked_at    timestamptz,
  requested_at              timestamptz NOT NULL DEFAULT now(),
  scheduled_purge_at        timestamptz NOT NULL DEFAULT now() + interval '30 days',
  cancelled_at              timestamptz,
  completed_at              timestamptz,
  CONSTRAINT ck_deletion_requests_status CHECK (status IN ('pending', 'grace', 'purging', 'completed', 'cancelled'))
);
CREATE UNIQUE INDEX uq_deletion_requests_open ON deletion_requests (user_id) WHERE status IN ('pending', 'grace', 'purging');
CREATE INDEX ix_deletion_requests_due ON deletion_requests (scheduled_purge_at) WHERE status IN ('pending', 'grace');

-- Postgres-backed rate limits (no Redis until about 10k MAU). Unlogged: losing counters on a crash is acceptable.
CREATE UNLOGGED TABLE rate_limit_counters (
  bucket        text NOT NULL,                                   -- e.g. 'login_code\:ip:203.0.113.9'
  window_start  timestamptz NOT NULL,
  count         integer NOT NULL DEFAULT 1,
  PRIMARY KEY (bucket, window_start)
);
CREATE INDEX ix_rate_limit_counters_window ON rate_limit_counters (window_start);

-- Replay store for the Idempotency-Key header (04 section 1.6): one row per user and key, kept 24 hours.
-- Credit spends also carry the key in ai_usage.idempotency_key and credit_ledger.idempotency_key, so a retry can never charge twice even if this row is lost.
CREATE TABLE idempotency_keys (
  user_id        uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  key            text NOT NULL CHECK (char_length(key) BETWEEN 8 AND 128),
  method         text NOT NULL,
  path           text NOT NULL,                                    -- the resolved request path without the query string
  request_hash   char(64) NOT NULL,                                -- sha256 of the canonical body; the same key with another body is 422 idempotency_key_reused
  state          text NOT NULL DEFAULT 'in_progress',              -- in_progress answers 409 idempotency_in_progress with Retry-After: 1
  status_code    smallint,
  response       jsonb,                                            -- the original response body, replayed with Idempotent-Replay: true
  created_at     timestamptz NOT NULL DEFAULT now(),
  expires_at     timestamptz NOT NULL DEFAULT now() + interval '24 hours',
  PRIMARY KEY (user_id, key),
  CONSTRAINT ck_idempotency_keys_state CHECK (state IN ('in_progress', 'completed')),
  CONSTRAINT ck_idempotency_keys_done CHECK (state = 'in_progress' OR status_code IS NOT NULL)
);
CREATE INDEX ix_idempotency_keys_expiry ON idempotency_keys (expires_at);
"""

DOWN = r"""
DROP TABLE idempotency_keys;
DROP TABLE rate_limit_counters;
DROP TABLE deletion_requests;
DROP TABLE data_exports;
DROP TABLE consents;
DROP TABLE content_reports;
DROP TABLE support_tickets;
DROP TRIGGER trg_audit_log_no_truncate ON audit_log;
DROP TRIGGER trg_audit_log_immutable ON audit_log;
DROP TABLE audit_log;
DROP FUNCTION audit_log_no_truncate();
DROP FUNCTION audit_log_immutable();
DROP TABLE kill_switches;
DROP TABLE feature_flags;
DROP TABLE admin_users;
DROP TYPE admin_role;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
