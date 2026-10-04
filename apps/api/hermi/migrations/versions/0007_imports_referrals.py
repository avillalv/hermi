"""0007_imports_referrals: trip imports and referrals (03 section 5.9).

The SQL is the DDL of 03 section 5.9, verbatim. Grants, RLS and the definer ownership of the functions land in 0014_rls.
The functions read feature_flags (0012_admin_privacy) at call time only, so they are created here before that table exists.

Revision ID: 0007_imports_referrals
Revises: 0006_billing_credits
"""

from alembic import op

revision = "0007_imports_referrals"
# 03 section 10 lists 0005 and 0006 as parents; the chain is linear, so the parent is 0006 (one head).
down_revision = "0006_billing_credits"
branch_labels = None
depends_on = None

UP = r"""
CREATE TABLE trip_imports (
  id                     uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id                uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  trip_id                uuid REFERENCES trips (id) ON DELETE SET NULL,      -- the trip the items were written to; set when applied; null if the trip was deleted later
  source                 text NOT NULL,                                      -- the input method
  origin                 text NOT NULL DEFAULT 'other',                      -- the entry used on the import screen; instructions and metrics only
  status                 text NOT NULL DEFAULT 'received',
  source_name            text CHECK (source_name IS NULL OR char_length(source_name) <= 200),   -- file name, or the feed's host for ics_feed; never a full feed URL
  content_hash           char(64),                                           -- sha256 of the file or pasted text, to warn about importing the same thing twice
  uid_set_hash           char(64),                                           -- sha256 (hex) of the sorted set of source UIDs of the import, set by the worker with the preview; with identity_hashes (5.8) it stops a deleted and re-created account earning the first-import pass again with the same calendar
  run_id                 uuid REFERENCES runs (id) ON DELETE SET NULL,       -- the Haiku extraction run for pasted_text (kind booking_import)
  flights_found          smallint NOT NULL DEFAULT 0,
  stays_found            smallint NOT NULL DEFAULT 0,
  reservations_found     smallint NOT NULL DEFAULT 0,
  other_found            smallint NOT NULL DEFAULT 0,
  places_found           smallint NOT NULL DEFAULT 0,                        -- Google Maps and pasted places: ideas with no day
  items_found            integer GENERATED ALWAYS AS (flights_found + stays_found + reservations_found + other_found + places_found) STORED,
  items_applied          integer NOT NULL DEFAULT 0,                         -- written to the trip after the user confirmed the preview
  flights_applied        smallint NOT NULL DEFAULT 0,                        -- of those, flights and stays: the reward needs at least one of them
  stays_applied          smallint NOT NULL DEFAULT 0,
  items_skipped          integer NOT NULL DEFAULT 0,                         -- unchecked in the preview
  items_duplicate        integer NOT NULL DEFAULT 0,                         -- matched an existing item by import_uid or by title, day and time
  preview                jsonb,                                              -- parsed items awaiting confirmation; nulled 7 days after the import
  error_code             text,                                               -- unreadable_file, no_events, feed_unreachable, nothing_found, provider_error, blocked_source
  error                  text,
  reward_granted_at      timestamptz,                                        -- set by grant_import_reward(); once per user
  reward_pass_id         uuid REFERENCES trip_passes (id) ON DELETE SET NULL,
  -- Opt-in "Keep checking this calendar" (ics_feed only): polled every 6 hours, changes shown as a preview the person confirms.
  poll_enabled           boolean NOT NULL DEFAULT false,
  next_poll_at           timestamptz,                                        -- set when polling is switched on; the worker moves it 6 hours on after each poll
  last_polled_at         timestamptz,
  last_content_hash      char(64),                                           -- sha256 of the feed body at the last successful poll; an equal hash means nothing changed
  consecutive_failures   smallint NOT NULL DEFAULT 0,                        -- reset on success; the third in a row switches polling off
  feed_url_enc           bytea,                                              -- the feed URL, encrypted; kept only while polling is on, see the paragraph above
  pending_changes        jsonb,                                              -- the diff awaiting confirmation: {added, changed, removed}; never applied automatically
  pending_changes_at     timestamptz,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  completed_at           timestamptz,
  CONSTRAINT ck_trip_imports_source CHECK (source IN ('ics_file', 'ics_feed', 'pasted_text', 'maps_file', 'places_text')),
  CONSTRAINT ck_trip_imports_origin CHECK (origin IN ('tripit', 'tripsy', 'wanderlog', 'google_calendar', 'google_maps', 'other')),
  CONSTRAINT ck_trip_imports_status CHECK (status IN ('received', 'parsing', 'review', 'applied', 'failed', 'discarded')),
  CONSTRAINT ck_trip_imports_counts CHECK (items_applied + items_skipped + items_duplicate <= items_found),
  CONSTRAINT ck_trip_imports_applied CHECK (status <> 'applied' OR completed_at IS NOT NULL),
  CONSTRAINT ck_trip_imports_reward CHECK (reward_granted_at IS NULL OR status = 'applied'),
  CONSTRAINT ck_trip_imports_applied_split CHECK (flights_applied + stays_applied <= items_applied),
  CONSTRAINT ck_trip_imports_feed_url CHECK (feed_url_enc IS NULL OR source = 'ics_feed'),
  CONSTRAINT ck_trip_imports_poll CHECK (NOT poll_enabled OR (source = 'ics_feed' AND status = 'applied' AND feed_url_enc IS NOT NULL AND next_poll_at IS NOT NULL))
);
-- The first applied import earns the free Trip Pass, once per user for life.
CREATE UNIQUE INDEX uq_trip_imports_one_reward ON trip_imports (user_id) WHERE reward_granted_at IS NOT NULL;
CREATE INDEX ix_trip_imports_user ON trip_imports (user_id, created_at DESC);
CREATE INDEX ix_trip_imports_trip ON trip_imports (trip_id) WHERE trip_id IS NOT NULL;
CREATE INDEX ix_trip_imports_hash ON trip_imports (user_id, content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX ix_trip_imports_cleanup ON trip_imports (created_at) WHERE preview IS NOT NULL OR (feed_url_enc IS NOT NULL AND NOT poll_enabled);
CREATE INDEX ix_trip_imports_poll_due ON trip_imports (next_poll_at) WHERE poll_enabled;     -- the 6-hourly calendar poll job
SELECT add_updated_at_trigger('trip_imports');

-- Grants the once-per-user import reward: a 90 day Trip Pass on the imported trip plus its 40 pass credits.
-- Returns the new trip_passes.id, or NULL when the import does not qualify (nothing is consumed in that case).
-- Called by the worker after the import is applied. The reward switch and minimum item count are the feature_flags setting 'setting_import_reward'.
-- Conditions: at least 3 items applied including a flight or a stay, a verified email, no active pass on the trip, no active Plus, once per user.
CREATE FUNCTION grant_import_reward(p_import uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_imp trip_imports%ROWTYPE; v_plan plans%ROWTYPE; v_min integer; v_enabled boolean; v_pass uuid;
BEGIN
  SELECT * INTO v_imp FROM trip_imports WHERE id = p_import FOR UPDATE;
  IF NOT FOUND OR v_imp.status <> 'applied' OR v_imp.trip_id IS NULL OR v_imp.reward_granted_at IS NOT NULL THEN
    RETURN NULL;
  END IF;
  SELECT enabled, COALESCE((rules ->> 'min_items_applied')::integer, 3) INTO v_enabled, v_min
    FROM feature_flags WHERE key = 'setting_import_reward';
  IF NOT COALESCE(v_enabled, false) OR v_imp.items_applied < GREATEST(COALESCE(v_min, 3), 3) THEN RETURN NULL; END IF;
  -- At least one flight or stay among the applied items (place ideas and other events alone do not qualify).
  IF v_imp.flights_applied + v_imp.stays_applied < 1 THEN RETURN NULL; END IF;
  -- A verified email, and no active Plus (a Plus owner already has the capabilities a pass would add).
  IF NOT EXISTS (SELECT 1 FROM users WHERE id = v_imp.user_id AND email_verified_at IS NOT NULL AND deleted_at IS NULL) THEN RETURN NULL; END IF;
  IF EXISTS (SELECT 1 FROM entitlements WHERE user_id = v_imp.user_id AND tier_code = 'plus' AND (valid_until IS NULL OR valid_until > now())) THEN RETURN NULL; END IF;
  -- The importer must own a live trip: a pass is bound to a trip its purchaser owns.
  IF NOT EXISTS (SELECT 1 FROM trips WHERE id = v_imp.trip_id AND owner_user_id = v_imp.user_id AND deleted_at IS NULL) THEN RETURN NULL; END IF;
  -- Once per user for life, and once per person: a deleted and re-created account is caught by the identity and UID-set hashes (5.8).
  IF EXISTS (SELECT 1 FROM trip_imports WHERE user_id = v_imp.user_id AND reward_granted_at IS NOT NULL) THEN RETURN NULL; END IF;
  IF EXISTS (SELECT 1 FROM identity_hashes WHERE kind = 'import_reward' AND hash IN (SELECT identity_hashes_for(v_imp.user_id)))
     OR (v_imp.uid_set_hash IS NOT NULL AND EXISTS (SELECT 1 FROM identity_hashes WHERE kind = 'import_uids' AND hash = decode(v_imp.uid_set_hash, 'hex')))
  THEN RETURN NULL; END IF;
  -- A trip that already has an active pass has the capabilities; keep the reward for the next import.
  IF EXISTS (SELECT 1 FROM trip_passes WHERE trip_id = v_imp.trip_id AND status = 'active') THEN RETURN NULL; END IF;

  SELECT * INTO v_plan FROM plans WHERE code = 'trip_pass' AND is_active;
  IF NOT FOUND THEN RETURN NULL; END IF;
  INSERT INTO trip_passes (trip_id, purchaser_user_id, plan_code, source, expires_at, credits_granted)
  VALUES (v_imp.trip_id, v_imp.user_id, 'trip_pass', 'import_reward', now() + make_interval(days => v_plan.duration_days), v_plan.credits_granted)
  RETURNING id INTO v_pass;
  INSERT INTO credit_grants (user_id, kind, credits, remaining, trip_id, period_key, expires_at)
  VALUES (v_imp.user_id, 'trip_pass', v_plan.credits_granted, v_plan.credits_granted, v_imp.trip_id,
          'import_reward:' || v_imp.id, now() + make_interval(days => COALESCE(v_plan.credits_valid_days, v_plan.duration_days)));
  UPDATE trip_imports SET reward_granted_at = now(), reward_pass_id = v_pass WHERE id = v_imp.id;
  INSERT INTO identity_hashes (hash, kind) SELECT identity_hashes_for(v_imp.user_id), 'import_reward'
  ON CONFLICT DO NOTHING;
  IF v_imp.uid_set_hash IS NOT NULL THEN
    INSERT INTO identity_hashes (hash, kind) VALUES (decode(v_imp.uid_set_hash, 'hex'), 'import_uids') ON CONFLICT DO NOTHING;
  END IF;
  RETURN v_pass;
EXCEPTION WHEN unique_violation THEN
  RETURN NULL;                                   -- a concurrent call already granted the reward
END $$;

-- Switches "Keep checking this calendar" on or off for the caller's own applied feed import (the API runs as the caller). Returns true when the state changed.
-- Turning it on needs a stored feed URL and fewer than 3 polled feeds; turning it off deletes the stored URL and any pending changes.
CREATE FUNCTION set_import_polling(p_import uuid, p_enabled boolean) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_me uuid := app_user_id(); v_imp trip_imports%ROWTYPE;
BEGIN
  IF v_me IS NULL THEN RETURN false; END IF;
  SELECT * INTO v_imp FROM trip_imports WHERE id = p_import AND user_id = v_me FOR UPDATE;
  IF NOT FOUND OR v_imp.source <> 'ics_feed' THEN RETURN false; END IF;
  IF p_enabled THEN
    IF v_imp.poll_enabled OR v_imp.status <> 'applied' OR v_imp.feed_url_enc IS NULL OR v_imp.trip_id IS NULL THEN RETURN false; END IF;
    IF (SELECT count(*) FROM trip_imports WHERE user_id = v_me AND poll_enabled) >= 3 THEN RETURN false; END IF;
    UPDATE trip_imports SET poll_enabled = true, next_poll_at = now() + interval '6 hours', consecutive_failures = 0 WHERE id = p_import;
  ELSE
    IF NOT v_imp.poll_enabled THEN RETURN false; END IF;
    UPDATE trip_imports SET poll_enabled = false, next_poll_at = NULL, feed_url_enc = NULL, pending_changes = NULL, pending_changes_at = NULL WHERE id = p_import;
  END IF;
  RETURN true;
END $$;

CREATE TABLE referral_codes (
  user_id      uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
  code         text NOT NULL,                                   -- 8 characters from an alphabet without 0, O, 1, I; public, not a secret
  disabled_at  timestamptz,                                     -- set by an admin to stop abuse
  created_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_referral_codes_code UNIQUE (code),
  CONSTRAINT ck_referral_codes_code CHECK (code ~ '^[A-Z0-9]{6,12}$')
);

CREATE TABLE referral_rewards (
  id                   uuid PRIMARY KEY DEFAULT uuidv7(),
  code                 text NOT NULL,                           -- the code that was entered (kept even if the code is later disabled)
  referrer_user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  referee_user_id      uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  status               text NOT NULL DEFAULT 'pending',         -- pending: code entered; qualified: referee did the qualifying thing; granted: credits given; rejected: abuse or ineligible
  referrer_credits     integer NOT NULL DEFAULT 0 CHECK (referrer_credits >= 0),   -- amounts snapshotted from setting_referral_credits when the code was redeemed
  referee_credits      integer NOT NULL DEFAULT 0 CHECK (referee_credits >= 0),
  referrer_grant_id    uuid REFERENCES credit_grants (id) ON DELETE SET NULL,
  referee_grant_id     uuid REFERENCES credit_grants (id) ON DELETE SET NULL,
  reject_reason        text,
  referrer_capped      boolean NOT NULL DEFAULT false,          -- the referrer hit the 30-day or calendar-year cap, so only the referee was paid
  created_at           timestamptz NOT NULL DEFAULT now(),
  qualified_at         timestamptz,
  granted_at           timestamptz,
  CONSTRAINT uq_referral_rewards_referee UNIQUE (referee_user_id),          -- a person can be referred once
  CONSTRAINT ck_referral_rewards_distinct CHECK (referrer_user_id <> referee_user_id),
  CONSTRAINT ck_referral_rewards_status CHECK (status IN ('pending', 'qualified', 'granted', 'rejected')),
  CONSTRAINT ck_referral_rewards_granted CHECK (status <> 'granted' OR granted_at IS NOT NULL)
);
CREATE INDEX ix_referral_rewards_referrer ON referral_rewards (referrer_user_id, status, granted_at DESC);
CREATE INDEX ix_referral_rewards_queue ON referral_rewards (created_at) WHERE status IN ('pending', 'qualified');

-- Creates the user's referral code on first use (worker and internal callers).
CREATE FUNCTION ensure_referral_code(p_user uuid) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_code text; v_alpha constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; i integer;
BEGIN
  SELECT code INTO v_code FROM referral_codes WHERE user_id = p_user;
  IF FOUND THEN RETURN v_code; END IF;
  LOOP
    v_code := '';
    FOR i IN 1..8 LOOP
      v_code := v_code || substr(v_alpha, 1 + floor(random() * 32)::integer, 1);
    END LOOP;
    BEGIN
      INSERT INTO referral_codes (user_id, code) VALUES (p_user, v_code);
      RETURN v_code;
    EXCEPTION WHEN unique_violation THEN
      SELECT code INTO v_code FROM referral_codes WHERE user_id = p_user;
      IF FOUND THEN RETURN v_code; END IF;      -- another call created this user's code
    END;                                        -- otherwise the random code collided: try another
  END LOOP;
END $$;

-- The API's entry points run as the caller (app.user_id) so a user can only act for themselves.
CREATE FUNCTION my_referral_code() RETURNS text
LANGUAGE sql SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT ensure_referral_code(app_user_id()) WHERE app_user_id() IS NOT NULL
$$;

-- The caller enters a friend's code. Returns the new referral_rewards.id, or NULL when the code is unknown, disabled,
-- their own, too late (the account is older than 14 days), or they were already referred. The API answers all of those the same way.
CREATE FUNCTION redeem_referral(p_code text) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_me uuid := app_user_id(); v_code text := upper(btrim(p_code)); v_referrer uuid; v_cfg jsonb; v_id uuid;
BEGIN
  IF v_me IS NULL THEN RETURN NULL; END IF;
  SELECT user_id INTO v_referrer FROM referral_codes WHERE code = v_code AND disabled_at IS NULL;
  IF v_referrer IS NULL OR v_referrer = v_me THEN RETURN NULL; END IF;
  IF NOT EXISTS (SELECT 1 FROM users WHERE id = v_me AND created_at > now() - interval '14 days') THEN RETURN NULL; END IF;
  SELECT rules INTO v_cfg FROM feature_flags WHERE key = 'setting_referral_credits' AND enabled;
  IF v_cfg IS NULL THEN RETURN NULL; END IF;
  INSERT INTO referral_rewards (code, referrer_user_id, referee_user_id, referrer_credits, referee_credits)
  VALUES (v_code, v_referrer, v_me, COALESCE((v_cfg ->> 'referrer')::integer, 0), COALESCE((v_cfg ->> 'referee')::integer, 0))
  ON CONFLICT (referee_user_id) DO NOTHING
  RETURNING id INTO v_id;
  RETURN v_id;
END $$;

-- Gives both people their credits once the row is 'qualified' (worker only): 20 credits each, expiring after 12 months. The referee always gets
-- theirs; the referrer gets theirs until they reach 5 paid rewards in a rolling 30 days or 10 in the calendar year (UTC). The numbers are the
-- setting_referral_credits rules referrer_monthly_cap, referrer_yearly_cap and expiry_months; none of them is a ceiling raise (06 6.5).
-- Returns true when the row was granted. Replays do nothing: each grant is keyed by period_key 'referral:<id>'.
CREATE FUNCTION grant_referral_reward(p_reward uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  r referral_rewards%ROWTYPE; v_cap30 integer; v_capyear integer; v_months integer; v_recent integer; v_year integer;
  v_g_referrer uuid; v_g_referee uuid; v_ok boolean;
BEGIN
  SELECT * INTO r FROM referral_rewards WHERE id = p_reward FOR UPDATE;
  IF NOT FOUND OR r.status <> 'qualified' THEN RETURN false; END IF;
  SELECT COALESCE((rules ->> 'referrer_monthly_cap')::integer, 5), COALESCE((rules ->> 'referrer_yearly_cap')::integer, 10),
         COALESCE((rules ->> 'expiry_months')::integer, 12)
    INTO v_cap30, v_capyear, v_months FROM feature_flags WHERE key = 'setting_referral_credits';
  -- Only rewards where the referrer was actually paid count toward their caps.
  SELECT count(*) FILTER (WHERE granted_at > now() - interval '30 days'),
         count(*) FILTER (WHERE granted_at >= date_trunc('year', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC')
    INTO v_recent, v_year
    FROM referral_rewards
   WHERE referrer_user_id = r.referrer_user_id AND status = 'granted' AND NOT referrer_capped;
  v_ok := v_recent < COALESCE(v_cap30, 5) AND v_year < COALESCE(v_capyear, 10);

  IF r.referee_credits > 0 THEN
    INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key, expires_at)
    VALUES (r.referee_user_id, 'promo', r.referee_credits, r.referee_credits, 'referral:' || r.id, now() + make_interval(months => COALESCE(v_months, 12)))
    ON CONFLICT (user_id, kind, period_key) WHERE user_id IS NOT NULL AND period_key IS NOT NULL DO NOTHING
    RETURNING id INTO v_g_referee;
    IF v_g_referee IS NOT NULL THEN
      INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, note) VALUES (r.referee_user_id, v_g_referee, 'grant', r.referee_credits, 'referral reward');
    END IF;
  END IF;
  IF r.referrer_credits > 0 AND v_ok THEN
    INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key, expires_at)
    VALUES (r.referrer_user_id, 'promo', r.referrer_credits, r.referrer_credits, 'referral:' || r.id, now() + make_interval(months => COALESCE(v_months, 12)))
    ON CONFLICT (user_id, kind, period_key) WHERE user_id IS NOT NULL AND period_key IS NOT NULL DO NOTHING
    RETURNING id INTO v_g_referrer;
    IF v_g_referrer IS NOT NULL THEN
      INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, note) VALUES (r.referrer_user_id, v_g_referrer, 'grant', r.referrer_credits, 'referral reward');
    END IF;
  END IF;
  UPDATE referral_rewards SET status = 'granted', granted_at = now(), referrer_grant_id = v_g_referrer, referee_grant_id = v_g_referee,
         referrer_capped = (r.referrer_credits > 0 AND NOT v_ok) WHERE id = r.id;
  RETURN true;
END $$;
"""

DOWN = r"""
DROP FUNCTION grant_referral_reward(uuid);
DROP FUNCTION redeem_referral(text);
DROP FUNCTION my_referral_code();
DROP FUNCTION ensure_referral_code(uuid);
DROP TABLE referral_rewards;
DROP TABLE referral_codes;
DROP FUNCTION set_import_polling(uuid, boolean);
DROP FUNCTION grant_import_reward(uuid);
DROP TABLE trip_imports;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
