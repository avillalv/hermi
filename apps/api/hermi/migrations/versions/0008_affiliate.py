"""0008_affiliate: affiliate programs, link templates, clicks, conversions, payouts and revenue views (03 section 5.10).

The SQL is the DDL of 03 section 5.10, verbatim, plus the first link_clicks partitions (03 section 9, as 0005 did for
provider_calls and run_events). maintain_partitions() and drop_old_log_partitions() land in 0014_rls, which also re-owns the
parent and its partitions to hermi_definer. No grant is given on any partition. Seed programs are 0015_seed.

Revision ID: 0008_affiliate
Revises: 0007_imports_referrals
"""

from alembic import op

revision = "0008_affiliate"
# 03 section 10 lists 0003 as the parent; the chain is linear, so the parent is 0007 (one head).
down_revision = "0007_imports_referrals"
branch_labels = None
depends_on = None

UP = r"""
CREATE TYPE program_status AS ENUM ('planned', 'applied', 'active', 'paused', 'closed');

CREATE TABLE affiliate_programs (
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  code                      text NOT NULL,                     -- stable slug, e.g. travelpayouts_aviasales
  network                   text NOT NULL,
  name                      text NOT NULL,
  category                  text NOT NULL,
  status                    program_status NOT NULL DEFAULT 'planned',
  marker_or_id              text,                              -- our public publisher id or marker (not a secret)
  hosts                     text[] NOT NULL DEFAULT '{}',      -- destination hosts templates may point at
  commission_model          text,                              -- e.g. 'percent_of_booking', 'per_action', 'per_click'
  commission_note           text,                              -- reported rate, marked "verify" until read on the network page
  cookie_days               smallint,
  subid_param               text,                              -- query parameter that carries our sub-id
  subid_max_len             smallint,
  campaign_param            text,                              -- second static field for the surface label
  terms_url                 text,
  api_credentials_ref       text,                              -- NAME of the environment variable, never the secret
  disclosure_text           text NOT NULL DEFAULT 'We earn a commission if you book here.',
  extra_disclosure_text     text,                              -- partner-mandated line (for example Booking.com)
  countries_allowed         country_code2[],                   -- null = everywhere
  countries_blocked         country_code2[] NOT NULL DEFAULT '{}',
  feature_flag_key          text,                              -- per-partner kill via feature_flags / kill_switches (no foreign key)
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_affiliate_programs_code UNIQUE (code),
  CONSTRAINT ck_affiliate_programs_network CHECK (network IN ('travelpayouts', 'stay22', 'viator')),
  CONSTRAINT ck_affiliate_programs_category CHECK (category IN (
    'flights', 'lodging', 'tours', 'cars', 'transfers', 'trains', 'esim', 'insurance',
    'compensation', 'luggage', 'restaurants', 'visas', 'money', 'other')),
  CONSTRAINT ck_affiliate_programs_no_airbnb CHECK (array_to_string(hosts, ',') !~* 'airbnb')
);
CREATE INDEX ix_affiliate_programs_active ON affiliate_programs (category) WHERE status = 'active';
SELECT add_updated_at_trigger('affiliate_programs');

CREATE TABLE affiliate_link_templates (
  id                     uuid PRIMARY KEY DEFAULT uuidv7(),
  program_id             uuid NOT NULL REFERENCES affiliate_programs (id) ON DELETE CASCADE,
  kind                   text NOT NULL,
  surface                text,                                  -- null = any surface
  variant                text NOT NULL DEFAULT 'default',       -- A/B cell name
  weight                 smallint NOT NULL DEFAULT 100 CHECK (weight BETWEEN 0 AND 1000),
  template               text NOT NULL,                         -- placeholders: {marker} {sub_id} {short_id} {campaign} {dest} {dest_enc} {origin} {destination} {depart} {return} {adults} {checkin} {checkout} {guests} {lat} {lon}
  required_placeholders  text[] NOT NULL DEFAULT '{}',
  active                 boolean NOT NULL DEFAULT true,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_affiliate_link_templates_kind CHECK (kind IN ('search', 'deeplink', 'widget', 'map')),
  CONSTRAINT ck_affiliate_link_templates_https CHECK (template ~ '^https://[a-z0-9.-]+/'),
  CONSTRAINT ck_affiliate_link_templates_no_url_param CHECK (template !~* '[?&](url|redirect|next|u)=\{dest')   -- destinations are validated hosts only
);
CREATE UNIQUE INDEX uq_affiliate_link_templates_cell ON affiliate_link_templates (program_id, kind, COALESCE(surface, ''), variant);
SELECT add_updated_at_trigger('affiliate_link_templates');

-- Partitioned by month on created_at (section 9). No foreign keys to or from users, trips or conversions.
CREATE TABLE link_clicks (
  id                   uuid NOT NULL DEFAULT uuidv7(),
  click_id             text NOT NULL,                              -- random 128-bit, base62, about 22 chars; also the sub-id we send
  short_id             text,                                       -- 8 to 12 chars for networks with short sub-id limits
  user_id              uuid,
  trip_id              uuid,
  program_id           uuid NOT NULL REFERENCES affiliate_programs (id) ON DELETE RESTRICT,
  template_id          uuid REFERENCES affiliate_link_templates (id) ON DELETE SET NULL,
  entity_type          text,                                       -- fare, lodging_option, itinerary_item, saved_place, checklist_item
  entity_id            uuid,
  checklist_item_kind  text,
  surface              text NOT NULL,                              -- lodging_shortlist, chosen_flight, itinerary_day, checklist, presentation, ...
  variant              text,
  destination_url      text NOT NULL,
  opened_in            text,
  created_at           timestamptz NOT NULL DEFAULT now(),         -- when /api/outbound minted it
  clicked_at           timestamptz,                                -- when /go was hit; null if never opened
  redirect_status      smallint,
  country              country_code2,
  platform             text,
  app_version          text,
  tier_code            text,                                       -- the clicker's effective tier or pass when the click was minted (free, plus, trip_pass), so free versus paid earnings are reportable (07 8.7)
  ip_hash              text,                                       -- salted hash, salt rotated monthly; no advertising id, no device id
  PRIMARY KEY (id, created_at),
  CONSTRAINT ck_link_clicks_opened_in CHECK (opened_in IS NULL OR opened_in IN ('sfsvc', 'safari', 'web', 'android_tab'))
) PARTITION BY RANGE (created_at);
-- Lookups always add a created_at bound (a click is valid for about 10 minutes), so partition pruning applies.
CREATE UNIQUE INDEX uq_link_clicks_click_id ON link_clicks (click_id, created_at);
CREATE UNIQUE INDEX uq_link_clicks_short_id ON link_clicks (short_id, created_at) WHERE short_id IS NOT NULL;
CREATE INDEX ix_link_clicks_program_time ON link_clicks (program_id, created_at);
CREATE INDEX ix_link_clicks_user_time ON link_clicks (user_id, created_at) WHERE user_id IS NOT NULL;
CREATE INDEX ix_link_clicks_surface_time ON link_clicks (surface, created_at);

CREATE TABLE affiliate_conversions (
  id                     uuid PRIMARY KEY DEFAULT uuidv7(),
  program_id             uuid NOT NULL REFERENCES affiliate_programs (id) ON DELETE RESTRICT,
  network                text NOT NULL,
  network_txn_id         text NOT NULL,                           -- Travelpayouts action id, Impact action id, Stay22 booking id, Viator booking ref
  network_click_ref      text,
  sub_id_returned        text,                                    -- what the network echoed back
  click_id               text,                                    -- set when matched; no FK (link_clicks is partitioned)
  match_status           text NOT NULL DEFAULT 'unmatched',
  user_id                uuid REFERENCES users (id) ON DELETE SET NULL,          -- copied from the click at match time
  trip_id                uuid,
  surface                text,
  status                 text NOT NULL DEFAULT 'pending',
  network_status_raw     text,                                    -- processing, paid, cancelled (Travelpayouts); pending, locked, reversed (Impact)
  product_type           text,                                    -- flight, stay, tour, car, transfer, esim, insurance, compensation
  product_ref            text,
  booking_value_minor    bigint,
  booking_currency       currency_code,
  commission_minor       bigint,
  commission_currency    currency_code,
  booked_at              timestamptz,
  travel_date            date,
  checkout_date          date,                                    -- stays pay after check-out
  approved_at            timestamptz,
  paid_at                timestamptz,
  reversal_at            timestamptz,
  click_lag_hours        numeric(10,2),
  status_history         jsonb NOT NULL DEFAULT '[]'::jsonb,
  raw                    jsonb,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_affiliate_conversions_match CHECK (match_status IN ('matched', 'unmatched')),
  CONSTRAINT ck_affiliate_conversions_status CHECK (status IN ('pending', 'approved', 'rejected', 'paid')),
  CONSTRAINT uq_affiliate_conversions_txn UNIQUE (program_id, network_txn_id)        -- nightly pulls upsert on this
);
CREATE INDEX ix_affiliate_conversions_click ON affiliate_conversions (click_id) WHERE click_id IS NOT NULL;
CREATE INDEX ix_affiliate_conversions_status ON affiliate_conversions (program_id, status);
CREATE INDEX ix_affiliate_conversions_booked ON affiliate_conversions (booked_at);
CREATE INDEX ix_affiliate_conversions_unmatched ON affiliate_conversions (created_at) WHERE match_status = 'unmatched';
SELECT add_updated_at_trigger('affiliate_conversions');

CREATE TABLE affiliate_payouts (
  id            uuid PRIMARY KEY DEFAULT uuidv7(),
  program_id    uuid NOT NULL REFERENCES affiliate_programs (id) ON DELETE RESTRICT,
  period_start  date NOT NULL,
  period_end    date NOT NULL,
  amount_minor  bigint NOT NULL CHECK (amount_minor >= 0),
  currency      currency_code NOT NULL,
  received_at   timestamptz,
  reference     text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_affiliate_payouts_period CHECK (period_end >= period_start)
);
CREATE INDEX ix_affiliate_payouts_program ON affiliate_payouts (program_id, period_end DESC);

-- Internal reporting (admin console only). Refresh nightly after the conversion pull.
CREATE MATERIALIZED VIEW revenue_by_month AS
SELECT date_trunc('month', booked_at) AS month, commission_currency AS currency, status,
       count(*) AS bookings, sum(commission_minor) AS commission_minor
  FROM affiliate_conversions WHERE booked_at IS NOT NULL
 GROUP BY 1, 2, 3;
CREATE UNIQUE INDEX uq_revenue_by_month ON revenue_by_month (month, currency, status);

CREATE MATERIALIZED VIEW revenue_by_surface AS
SELECT date_trunc('month', booked_at) AS month, COALESCE(surface, 'unknown') AS surface, commission_currency AS currency,
       count(*) AS bookings, sum(commission_minor) AS commission_minor
  FROM affiliate_conversions WHERE booked_at IS NOT NULL AND status IN ('approved', 'paid')
 GROUP BY 1, 2, 3;
CREATE UNIQUE INDEX uq_revenue_by_surface ON revenue_by_surface (month, surface, currency);

CREATE MATERIALIZED VIEW revenue_by_partner AS
SELECT date_trunc('month', c.booked_at) AS month, p.code AS program, c.commission_currency AS currency,
       count(*) AS bookings, sum(c.commission_minor) AS commission_minor
  FROM affiliate_conversions c JOIN affiliate_programs p ON p.id = c.program_id
 WHERE c.booked_at IS NOT NULL AND c.status IN ('approved', 'paid')
 GROUP BY 1, 2, 3;
CREATE UNIQUE INDEX uq_revenue_by_partner ON revenue_by_partner (month, program, currency);
-- Revenue per monthly active user divides revenue_by_month by the MAU count from PostHog in the admin API.

SELECT ensure_month_partitions('link_clicks', 3);
"""

DOWN = r"""
DROP MATERIALIZED VIEW revenue_by_partner;
DROP MATERIALIZED VIEW revenue_by_surface;
DROP MATERIALIZED VIEW revenue_by_month;
DROP TABLE affiliate_payouts;
DROP TABLE affiliate_conversions;
DROP TABLE link_clicks;
DROP TABLE affiliate_link_templates;
DROP TABLE affiliate_programs;
DROP TYPE program_status;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
