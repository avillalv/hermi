"""0010_itinerary_lodging: itinerary days, saved places, itinerary items, lodging options and the two heart tables (03 sections 5.13 and 5.14).

The SQL is the DDL of 5.13 and 5.14, verbatim.
Grants, row-level security and policies land in 0014_rls. No grant is given here.

Revision ID: 0010_itinerary_lodging
Revises: 0009_flights
"""

from alembic import op

revision = "0010_itinerary_lodging"
# 03 section 10 lists the parents of this revision; the chain is linear, so the parent is 0009_flights (one head).
down_revision = "0009_flights"
branch_labels = None
depends_on = None

UP = r"""
CREATE TYPE item_status   AS ENUM ('idea', 'planned', 'booked');
CREATE TYPE item_category AS ENUM ('sights', 'museum', 'food', 'nature', 'nightlife', 'shopping', 'travel', 'other');

CREATE TABLE itinerary_days (
  trip_id         uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  day             date NOT NULL,
  title           text NOT NULL DEFAULT '' CHECK (char_length(title) <= 120),
  notes           text NOT NULL DEFAULT '',
  destination_id  uuid REFERENCES trip_destinations (id) ON DELETE SET NULL,
  updated_by      uuid REFERENCES users (id) ON DELETE SET NULL,
  version         integer NOT NULL DEFAULT 1,
  updated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (trip_id, day)
);
SELECT add_version_trigger('itinerary_days');
SELECT add_updated_at_trigger('itinerary_days');

CREATE TABLE saved_places (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id         uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  place_provider  text NOT NULL,                              -- geoapify, viator, manual
  place_id        text NOT NULL,
  name            text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 200),
  category        item_category NOT NULL DEFAULT 'other',
  address         text,
  lat             double precision,
  lon             double precision,
  website         text,
  note            text NOT NULL DEFAULT '',
  place_data      jsonb,                                      -- fields the UI shows (hours, phone); not a full provider payload
  saved_by        uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_saved_places_lat_lon CHECK ((lat IS NULL) = (lon IS NULL)),
  CONSTRAINT uq_saved_places_trip_place UNIQUE (trip_id, place_provider, place_id),
  CONSTRAINT uq_saved_places_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_saved_places_trip ON saved_places (trip_id, created_at DESC);

CREATE TABLE itinerary_items (
  id                     uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  day                    date,                                -- null = idea with no day yet
  start_time             time,                                -- wall-clock at the destination
  end_time               time,                                -- at or before start_time means it runs past midnight
  sort_order             double precision NOT NULL DEFAULT 0, -- order within a day for untimed items
  title                  text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
  category               item_category NOT NULL DEFAULT 'other',
  status                 item_status NOT NULL DEFAULT 'idea',
  location_name          text,
  address                text,
  lat                    double precision,
  lon                    double precision,
  url                    text,
  notes                  text NOT NULL DEFAULT '',
  estimated_cost_minor   bigint CHECK (estimated_cost_minor IS NULL OR estimated_cost_minor >= 0),
  cost_currency          currency_code,
  saved_place_id         uuid,
  place_provider         text,
  place_id               text,
  place_data             jsonb,
  source                 text NOT NULL DEFAULT 'manual',      -- where the item came from; AI drafts stay flagged after the user accepts them
  check_url              text,                                -- evidence: the page the item's hours or price were checked on (plan verification); null for items with no AI evidence
  checked_at             timestamptz,                         -- the day that page was seen; older than 14 days shows "May be out of date" and offers a recheck
  import_id              uuid REFERENCES trip_imports (id) ON DELETE SET NULL,   -- the import that created this item
  import_uid             text,                                -- calendar event UID or hash of the parsed booking; de-duplicates re-imports
  created_by             uuid REFERENCES users (id) ON DELETE SET NULL,
  updated_by             uuid REFERENCES users (id) ON DELETE SET NULL,
  version                integer NOT NULL DEFAULT 1,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (saved_place_id, trip_id) REFERENCES saved_places (id, trip_id) ON DELETE SET NULL (saved_place_id),
  CONSTRAINT ck_itinerary_items_source CHECK (source IN ('manual', 'place_search', 'ai_draft', 'agent', 'import', 'verify_plan')),
  CONSTRAINT ck_itinerary_items_check CHECK ((check_url IS NULL) = (checked_at IS NULL)),
  CONSTRAINT uq_itinerary_items_id_trip UNIQUE (id, trip_id),
  CONSTRAINT ck_itinerary_items_times_need_day CHECK (day IS NOT NULL OR start_time IS NULL),
  CONSTRAINT ck_itinerary_items_end_needs_start CHECK (start_time IS NOT NULL OR end_time IS NULL),
  CONSTRAINT ck_itinerary_items_lat_lon CHECK ((lat IS NULL) = (lon IS NULL)),
  CONSTRAINT ck_itinerary_items_cost CHECK ((estimated_cost_minor IS NULL) = (cost_currency IS NULL)),
  CONSTRAINT ck_itinerary_items_import CHECK (import_uid IS NULL OR source = 'import')
);
CREATE INDEX ix_itinerary_items_trip_day ON itinerary_items (trip_id, day, start_time NULLS LAST, sort_order);
CREATE INDEX ix_itinerary_items_updated ON itinerary_items (trip_id, updated_at DESC);      -- updated_since polling
CREATE UNIQUE INDEX uq_itinerary_items_import_uid ON itinerary_items (trip_id, import_uid) WHERE import_uid IS NOT NULL;
CREATE INDEX ix_itinerary_items_import ON itinerary_items (import_id) WHERE import_id IS NOT NULL;
SELECT add_version_trigger('itinerary_items');
SELECT add_updated_at_trigger('itinerary_items');

CREATE TYPE lodging_status AS ENUM ('candidate', 'shortlisted', 'booked', 'rejected');

CREATE TABLE lodging_options (
  id                    uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id               uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  title                 text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 300),
  url                   text,                                   -- exactly as the user pasted it
  url_normalized        text,                                   -- query string stripped, for duplicate detection
  site                  text,
  check_in              date,
  check_out             date,
  guests                smallint,
  price_total_minor     bigint CHECK (price_total_minor IS NULL OR price_total_minor >= 0),
  price_per_night_minor bigint CHECK (price_per_night_minor IS NULL OR price_per_night_minor >= 0),
  currency              currency_code,
  photos                jsonb NOT NULL DEFAULT '[]'::jsonb,
  location_name         text,
  lat                   double precision,
  lon                   double precision,
  bedrooms              smallint,
  beds                  smallint,
  baths                 numeric(4,1),
  rating                numeric(3,2),
  review_count          integer,
  notes                 text NOT NULL DEFAULT '',
  pros                  text NOT NULL DEFAULT '',
  cons                  text NOT NULL DEFAULT '',
  status                lodging_status NOT NULL DEFAULT 'candidate',
  favorite              boolean NOT NULL DEFAULT false,
  added_via             text NOT NULL,
  program_id            uuid REFERENCES affiliate_programs (id) ON DELETE SET NULL,   -- partner the stay came from (search results)
  run_id                uuid REFERENCES runs (id) ON DELETE SET NULL,
  import_id             uuid REFERENCES trip_imports (id) ON DELETE SET NULL,   -- the import that created this stay
  created_by            uuid REFERENCES users (id) ON DELETE SET NULL,
  updated_by            uuid REFERENCES users (id) ON DELETE SET NULL,
  version               integer NOT NULL DEFAULT 1,
  raw                   jsonb,                                  -- nulled after 30 days
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_lodging_options_added_via CHECK (added_via IN ('bookmarklet', 'paste', 'partner_search', 'agent', 'manual', 'import')),
  CONSTRAINT ck_lodging_options_dates CHECK (check_out IS NULL OR check_in IS NULL OR check_out > check_in),
  CONSTRAINT ck_lodging_options_lat_lon CHECK ((lat IS NULL) = (lon IS NULL)),
  CONSTRAINT ck_lodging_options_price_currency CHECK ((price_total_minor IS NULL AND price_per_night_minor IS NULL) OR currency IS NOT NULL),
  CONSTRAINT uq_lodging_options_id_trip UNIQUE (id, trip_id)
);
CREATE UNIQUE INDEX uq_lodging_options_trip_url ON lodging_options (trip_id, url_normalized) WHERE url_normalized IS NOT NULL;
CREATE INDEX ix_lodging_options_trip ON lodging_options (trip_id, status, created_at DESC);
CREATE INDEX ix_lodging_options_import ON lodging_options (import_id) WHERE import_id IS NOT NULL;
SELECT add_version_trigger('lodging_options');
SELECT add_updated_at_trigger('lodging_options');

CREATE TABLE lodging_votes (                                  -- a heart on a stay, by a traveler; user_id attributes it to an account
  lodging_id   uuid NOT NULL,
  trip_id      uuid NOT NULL,
  person_id    uuid NOT NULL,
  user_id      uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (lodging_id, person_id),
  FOREIGN KEY (lodging_id, trip_id) REFERENCES lodging_options (id, trip_id) ON DELETE CASCADE,
  FOREIGN KEY (trip_id, person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE CASCADE
);
CREATE INDEX ix_lodging_votes_trip ON lodging_votes (trip_id);

CREATE TABLE saved_place_votes (                              -- a heart on a saved place, by a traveler
  saved_place_id  uuid NOT NULL,
  trip_id         uuid NOT NULL,
  person_id       uuid NOT NULL,
  user_id         uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (saved_place_id, person_id),
  FOREIGN KEY (saved_place_id, trip_id) REFERENCES saved_places (id, trip_id) ON DELETE CASCADE,
  FOREIGN KEY (trip_id, person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE CASCADE
);
CREATE INDEX ix_saved_place_votes_trip ON saved_place_votes (trip_id);
"""

DOWN = r"""
DROP TABLE saved_place_votes;
DROP TABLE lodging_votes;
DROP TABLE lodging_options;
DROP TABLE itinerary_items;
DROP TABLE saved_places;
DROP TABLE itinerary_days;
DROP TYPE lodging_status;
DROP TYPE item_category;
DROP TYPE item_status;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
