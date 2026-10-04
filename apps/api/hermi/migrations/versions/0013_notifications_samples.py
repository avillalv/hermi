"""0013_notifications_samples: notifications, sample trips, plan verification (03 sections 5.18, 5.19, 5.20).

The SQL is the DDL of those sections, verbatim. One comment colon is written with a backslash so SQLAlchemy text() reads no bind.
Grants, row-level security and policies land in 0014_rls. No grant is given here.

Revision ID: 0013_notifications_samples
Revises: 0012_admin_privacy
"""

from alembic import op

revision = "0013_notifications_samples"
down_revision = "0012_admin_privacy"
branch_labels = None
depends_on = None

UP = r"""
CREATE TABLE notifications (
  id             uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id        uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  trip_id        uuid REFERENCES trips (id) ON DELETE CASCADE,
  kind           text NOT NULL,
  dedupe_key     text NOT NULL,                                      -- e.g. 'booked_drop:<chosen_flight_id>:<current_minor>', 'reminder:<trip_id>\:7d'
  title          text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 120),
  body           text NOT NULL DEFAULT '' CHECK (char_length(body) <= 400),
  payload        jsonb NOT NULL DEFAULT '{}'::jsonb,                 -- deep link target and the numbers the message shows
  want_push      boolean NOT NULL DEFAULT true,
  want_email     boolean NOT NULL DEFAULT false,
  push_sent_at   timestamptz,
  email_sent_at  timestamptz,
  read_at        timestamptz,
  created_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_notifications_kind CHECK (kind IN (
    'price_drop', 'booked_fare_drop', 'trip_invite', 'invite_accepted', 'run_finished',
    'import_finished', 'pre_trip_reminder', 'referral_reward', 'import_reward',
    'calendar_changes', 'calendar_poll_stopped', 'verify_finished')),
  CONSTRAINT uq_notifications_dedupe UNIQUE (user_id, dedupe_key)
);
CREATE INDEX ix_notifications_user ON notifications (user_id, created_at DESC);
CREATE INDEX ix_notifications_unread ON notifications (user_id) WHERE read_at IS NULL;
CREATE INDEX ix_notifications_outbox ON notifications (created_at)
  WHERE (want_push AND push_sent_at IS NULL) OR (want_email AND email_sent_at IS NULL);

CREATE TABLE sample_trips (
  id                 uuid PRIMARY KEY DEFAULT uuidv7(),
  slug               text NOT NULL CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  trip_id            uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  title              text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 120),
  summary            text NOT NULL DEFAULT '',
  country_code       country_code2,
  cover_image_url    text,
  cover_attribution  text,
  tags               text[] NOT NULL DEFAULT '{}',                    -- the Beach, City, Mountains and Food chips of the gallery (05 section 6.23) filter on it
  suits              text,                                            -- the "who it suits" line on a gallery card
  status             text NOT NULL DEFAULT 'draft',
  sort_order         smallint NOT NULL DEFAULT 0,
  published_at       timestamptz,
  created_by         uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_sample_trips_slug UNIQUE (slug),
  CONSTRAINT uq_sample_trips_trip UNIQUE (trip_id),
  CONSTRAINT ck_sample_trips_status CHECK (status IN ('draft', 'published', 'archived')),
  CONSTRAINT ck_sample_trips_published CHECK (status <> 'published' OR published_at IS NOT NULL)
);
CREATE INDEX ix_sample_trips_published ON sample_trips (sort_order, published_at DESC) WHERE status = 'published';
SELECT add_updated_at_trigger('sample_trips');

CREATE TABLE plan_verifications (
  id                 uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id            uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  user_id            uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,         -- who pasted it and pays the credits
  source_label       text NOT NULL DEFAULT 'other',                                 -- what the person says wrote it; shown, never trusted
  status             text NOT NULL DEFAULT 'extracting',
  content_hash       char(64),                                                      -- sha256 of the redacted text, to warn about checking the same plan twice
  extract_run_id     uuid REFERENCES runs (id) ON DELETE SET NULL,                  -- the verify_extract run
  check_run_id       uuid REFERENCES runs (id) ON DELETE SET NULL,                  -- the latest verify_plan run
  items_found        smallint NOT NULL DEFAULT 0,
  items_selected     smallint NOT NULL DEFAULT 0,
  green_count        smallint NOT NULL DEFAULT 0,
  amber_count        smallint NOT NULL DEFAULT 0,
  red_count          smallint NOT NULL DEFAULT 0,
  unchecked_count    smallint NOT NULL DEFAULT 0,
  error_code         text,                                                          -- nothing_found, too_long, provider_error, refused
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  completed_at       timestamptz,
  expires_at         timestamptz NOT NULL DEFAULT now() + interval '30 days',
  CONSTRAINT ck_plan_verifications_label CHECK (source_label IN ('chatgpt', 'gemini', 'layla', 'mindtrip', 'other')),
  CONSTRAINT ck_plan_verifications_status CHECK (status IN ('extracting', 'review', 'checking', 'done', 'failed', 'discarded')),
  CONSTRAINT ck_plan_verifications_counts CHECK (green_count + amber_count + red_count <= items_selected AND items_selected <= items_found),
  CONSTRAINT uq_plan_verifications_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_plan_verifications_trip ON plan_verifications (trip_id, created_at DESC);
CREATE INDEX ix_plan_verifications_user ON plan_verifications (user_id, created_at DESC);
CREATE INDEX ix_plan_verifications_expiry ON plan_verifications (expires_at);
SELECT add_updated_at_trigger('plan_verifications');

CREATE TABLE plan_verification_items (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  verification_id     uuid NOT NULL,
  trip_id             uuid NOT NULL,                                                -- copy of the verification's trip, keeps RLS cheap
  position            smallint NOT NULL,                                            -- order in the pasted plan
  day_label           text CHECK (day_label IS NULL OR char_length(day_label) <= 60),   -- as written, for example "Day 2"
  planned_day         date,                                                         -- set when the plan names a date or the trip has dates
  planned_start       time,
  name                text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 200),
  category            item_category NOT NULL DEFAULT 'other',
  claimed_hours       text CHECK (claimed_hours IS NULL OR char_length(claimed_hours) <= 120),   -- hours the plan states, as text
  claimed_price_minor bigint CHECK (claimed_price_minor IS NULL OR claimed_price_minor >= 0),
  claimed_currency    currency_code,
  selected            boolean NOT NULL DEFAULT false,                               -- chosen for checking (within the per-run cap)
  verdict             text NOT NULL DEFAULT 'unchecked',                            -- green: confirmed; amber: differs or partly confirmed; red: could not be found
  reason_code         text,                                                         -- not_found, hours_differ, price_differ, closed_at_planned_time, partly_confirmed, blocked_source, over_cap, budget_stop, provider_error
  reason              text CHECK (reason IS NULL OR char_length(reason) <= 300),    -- one plain sentence for the screen
  exists_result       text,                                                         -- confirmed, differs, unconfirmed
  hours_result        text,                                                         -- confirmed, differs, unconfirmed, not_claimed
  price_result        text,                                                         -- confirmed, differs, unconfirmed, not_claimed
  place_provider      text,
  place_id            text,
  place_name          text,                                                         -- the name the source uses, which may differ from the plan
  lat                 double precision,
  lon                 double precision,
  found_hours         text,
  found_price_minor   bigint CHECK (found_price_minor IS NULL OR found_price_minor >= 0),
  found_currency      currency_code,
  source_url          text,                                                         -- the page the finding was seen on (the evidence label)
  source_domain       text,
  seen_at             timestamptz,                                                  -- the day that page was seen
  from_cache          boolean NOT NULL DEFAULT false,                               -- served from shared_research_cache (kind place_check)
  include_in_import   boolean NOT NULL DEFAULT false,                               -- green on by default; amber on after the person looks; red off
  imported_item_id    uuid,
  FOREIGN KEY (verification_id, trip_id) REFERENCES plan_verifications (id, trip_id) ON DELETE CASCADE,
  FOREIGN KEY (imported_item_id, trip_id) REFERENCES itinerary_items (id, trip_id) ON DELETE SET NULL (imported_item_id),
  CONSTRAINT uq_plan_verification_items_pos UNIQUE (verification_id, position),
  CONSTRAINT ck_plan_verification_items_verdict CHECK (verdict IN ('green', 'amber', 'red', 'unchecked')),
  CONSTRAINT ck_plan_verification_items_evidence CHECK (verdict NOT IN ('green', 'amber') OR (source_url IS NOT NULL AND seen_at IS NOT NULL)),
  CONSTRAINT ck_plan_verification_items_checked CHECK (verdict = 'unchecked' OR selected),
  CONSTRAINT ck_plan_verification_items_claim_price CHECK ((claimed_price_minor IS NULL) = (claimed_currency IS NULL)),
  CONSTRAINT ck_plan_verification_items_found_price CHECK ((found_price_minor IS NULL) = (found_currency IS NULL)),
  CONSTRAINT ck_plan_verification_items_lat_lon CHECK ((lat IS NULL) = (lon IS NULL))
);
CREATE INDEX ix_plan_verification_items_verification ON plan_verification_items (verification_id, position);
CREATE INDEX ix_plan_verification_items_trip ON plan_verification_items (trip_id);
"""

DOWN = r"""
DROP TABLE plan_verification_items;
DROP TABLE plan_verifications;
DROP TABLE sample_trips;
DROP TABLE notifications;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
