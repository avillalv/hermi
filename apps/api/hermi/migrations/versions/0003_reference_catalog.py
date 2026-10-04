"""0003_reference_catalog: airports, FX, places cache, plan catalog (03 sections 5.2 and 5.3).

Grants, row-level security and policies land in 0014_rls. Seed data lands in 0015_seed.

Revision ID: 0003_reference_catalog
Revises: 0002_identity
"""

from alembic import op

revision = "0003_reference_catalog"
down_revision = "0002_identity"
branch_labels = None
depends_on = None

UP = """
CREATE TABLE airports (                                          -- seeded from OurAirports (public domain)
  iata          iata_code PRIMARY KEY,
  icao          char(4),
  name          text NOT NULL,
  city          text,
  country_code  country_code2 NOT NULL,
  region_code   text,
  lat           double precision NOT NULL,
  lon           double precision NOT NULL,
  timezone      text,
  kind          text NOT NULL,
  CONSTRAINT ck_airports_kind CHECK (kind IN ('large_airport', 'medium_airport', 'small_airport'))
);
CREATE INDEX ix_airports_country ON airports (country_code);
CREATE INDEX ix_airports_city ON airports (lower(city));

CREATE TABLE fx_rates (                                          -- ECB reference rates via Frankfurter, units per 1 EUR
  currency    currency_code PRIMARY KEY,
  per_eur     numeric(20,8) NOT NULL CHECK (per_eur > 0),
  rate_date   date NOT NULL,
  fetched_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE places_cache (                                      -- provider API responses (Geoapify, Wikipedia, link metadata); AI research lives in shared_research_cache
  key         char(64) PRIMARY KEY,                              -- sha256 of provider, endpoint, normalized params
  provider    text NOT NULL,
  kind        text NOT NULL,
  response    jsonb NOT NULL,
  attribution text,                                              -- required attribution (OpenStreetMap, Wikipedia CC BY-SA)
  fetched_at  timestamptz NOT NULL DEFAULT now(),
  expires_at  timestamptz NOT NULL,
  hit_count   integer NOT NULL DEFAULT 0,
  CONSTRAINT ck_places_cache_provider CHECK (provider IN ('geoapify', 'wikimedia', 'viator', 'link_preview')),
  CONSTRAINT ck_places_cache_kind CHECK (kind IN ('autocomplete', 'geocode', 'places_search', 'place_detail', 'wiki_summary', 'product_search', 'link_preview'))
);
CREATE INDEX ix_places_cache_expires ON places_cache (expires_at);
CREATE INDEX ix_places_cache_provider_kind ON places_cache (provider, kind, expires_at);

-- Converts a minor-unit amount between currencies with the stored ECB rates. Returns NULL when either rate is missing,
-- so a caller never shows a made-up number. EUR is the base and has no row. Used at read time only; converted amounts are never stored.
CREATE FUNCTION fx_convert_minor(p_minor bigint, p_from text, p_to text) RETURNS bigint
LANGUAGE plpgsql STABLE AS $$
DECLARE v_from numeric; v_to numeric;
BEGIN
  IF p_from = p_to THEN RETURN p_minor; END IF;
  v_from := CASE WHEN p_from = 'EUR' THEN 1 ELSE (SELECT per_eur FROM fx_rates WHERE currency = p_from) END;
  v_to   := CASE WHEN p_to   = 'EUR' THEN 1 ELSE (SELECT per_eur FROM fx_rates WHERE currency = p_to) END;
  IF v_from IS NULL OR v_to IS NULL THEN RETURN NULL; END IF;
  RETURN round(p_minor::numeric / power(10, currency_exponent(p_from)) / v_from * v_to * power(10, currency_exponent(p_to)))::bigint;
END $$;

CREATE TYPE ai_action AS ENUM ('explain', 'live_search', 'draft_day', 'draft_trip', 'research', 'agent_run', 'verify_plan');   -- verify_plan is priced per checked item (11.3)

CREATE TABLE plans (
  code                 text PRIMARY KEY,                  -- Phase 1: free, plus, trip_pass, credits_50, credits_150, credits_400
  kind                 text NOT NULL,
  name                 text NOT NULL,
  rank                 smallint NOT NULL DEFAULT 0,        -- orders tiers for "best of" comparisons
  limits               jsonb NOT NULL DEFAULT '{}'::jsonb, -- numbers and booleans only (see section 11)
  monthly_credits      integer NOT NULL DEFAULT 0,         -- allowance granted each month (tiers)
  credits_granted      integer NOT NULL DEFAULT 0,         -- one-time credits (passes and packs)
  credits_valid_days   integer,                            -- expiry of those credits
  duration_days        integer,                            -- passes: 90
  feature_flag_key     text,                               -- plan is sellable only when this flag is on (no foreign key)
  is_active            boolean NOT NULL DEFAULT true,
  sort_order           smallint NOT NULL DEFAULT 0,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_plans_kind CHECK (kind IN ('tier', 'pass', 'credit_pack')),
  CONSTRAINT ck_plans_pass_duration CHECK (kind <> 'pass' OR duration_days IS NOT NULL)
);
SELECT add_updated_at_trigger('plans');

CREATE TABLE store_products (                               -- one row per purchasable SKU
  product_id        text PRIMARY KEY,                       -- App Store product id
  store             text NOT NULL,
  plan_code         text NOT NULL REFERENCES plans (code) ON DELETE RESTRICT,
  period            text NOT NULL,
  price_minor       bigint NOT NULL CHECK (price_minor >= 0),
  currency          currency_code NOT NULL DEFAULT 'USD',   -- US price; Apple regional tiers are set in App Store Connect
  trial_days        smallint NOT NULL DEFAULT 0,
  is_active         boolean NOT NULL DEFAULT true,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_store_products_store CHECK (store = 'apple'),                 -- no web purchases in Phase 1; Phase 2 widens this with web billing
  CONSTRAINT ck_store_products_period CHECK (period IN ('month', 'year', 'once'))
);
CREATE INDEX ix_store_products_plan ON store_products (plan_code);

CREATE TABLE credit_action_prices (
  action               ai_action PRIMARY KEY,
  credits              integer NOT NULL CHECK (credits > 0),
  credits_cached       integer CHECK (credits_cached IS NULL OR credits_cached > 0),     -- price when served from shared_research_cache
  hard_stop_micros     bigint NOT NULL CHECK (hard_stop_micros > 0),                      -- enforced spend ceiling for one action
  max_turns            smallint,
  max_searches         smallint,
  max_fetches          smallint,
  model                text,
  updated_at           timestamptz NOT NULL DEFAULT now()
);
"""

DOWN = """
DROP TABLE credit_action_prices;
DROP TABLE store_products;
DROP TABLE plans;
DROP TYPE ai_action;
DROP FUNCTION fx_convert_minor(bigint, text, text);
DROP TABLE places_cache;
DROP TABLE fx_rates;
DROP TABLE airports;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
