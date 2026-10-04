"""0009_flights: flight routes, shared fare observations, trip links, chosen flights, price insights, the booked-fare drop view and price alerts (03 sections 5.11 and 5.12).

The SQL is the DDL of 5.11 and 5.12, verbatim. The view booked_fare_drops is security_invoker, so the RLS of 0014_rls applies to its callers.
Grants, row-level security and policies land in 0014_rls. No grant is given here.

Revision ID: 0009_flights
Revises: 0008_affiliate
"""

from alembic import op

revision = "0009_flights"
# 03 section 10 lists 0003 and 0005 as the parents; the chain is linear, so the parent is 0008 (one head).
down_revision = "0008_affiliate"
branch_labels = None
depends_on = None

UP = r"""
CREATE TYPE cabin_class     AS ENUM ('economy', 'premium_economy', 'business', 'first');
CREATE TYPE trip_type       AS ENUM ('round_trip', 'one_way');
CREATE TYPE fare_confidence AS ENUM ('live', 'cached', 'indicative');   -- live: real-time search; cached: other travelers' recent search; indicative: agent saw it on a page

CREATE TABLE flight_routes (
  id                 uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id            uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  label              text,
  origin_codes       iata_code[] NOT NULL CHECK (cardinality(origin_codes) BETWEEN 1 AND 4),
  destination_codes  iata_code[] NOT NULL CHECK (cardinality(destination_codes) BETWEEN 1 AND 4),
  trip_type          trip_type NOT NULL DEFAULT 'round_trip',
  depart_from        date NOT NULL,
  depart_to          date NOT NULL,
  return_from        date,
  return_to          date,
  min_nights         smallint,
  max_nights         smallint,
  adults             smallint NOT NULL DEFAULT 1,
  children           smallint NOT NULL DEFAULT 0,
  cabin              cabin_class NOT NULL DEFAULT 'economy',
  max_stops          smallint,                              -- null = any number of stops
  sources            text[] NOT NULL DEFAULT '{travelpayouts}',
  alert_price_minor  bigint CHECK (alert_price_minor IS NULL OR alert_price_minor > 0),
  alert_currency     currency_code,
  is_live            boolean NOT NULL DEFAULT false,        -- live (paid-source) tracking; capped by entitlement live_routes
  live_enabled_at    timestamptz,
  last_checked_at    timestamptz,
  next_check_at      timestamptz,                           -- when the scheduler should check this route next; null when the route is not scheduled
  active             boolean NOT NULL DEFAULT true,
  created_by         uuid REFERENCES users (id) ON DELETE SET NULL,
  version            integer NOT NULL DEFAULT 1,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_flight_routes_depart_window CHECK (depart_to >= depart_from),
  CONSTRAINT ck_flight_routes_passengers CHECK (adults BETWEEN 1 AND 9 AND children BETWEEN 0 AND 8),
  CONSTRAINT ck_flight_routes_return_pair CHECK ((return_from IS NULL) = (return_to IS NULL)),
  CONSTRAINT ck_flight_routes_nights_pair CHECK ((min_nights IS NULL) = (max_nights IS NULL)),
  CONSTRAINT ck_flight_routes_return_rule CHECK (
    (trip_type = 'one_way' AND return_from IS NULL AND min_nights IS NULL) OR
    (trip_type = 'round_trip' AND ((return_from IS NULL) <> (min_nights IS NULL)))),
  CONSTRAINT ck_flight_routes_alert_currency CHECK ((alert_price_minor IS NULL) = (alert_currency IS NULL)),
  CONSTRAINT ck_flight_routes_sources CHECK (sources <@ ARRAY['travelpayouts', 'serpapi', 'licensed', 'agent', 'manual']),
  CONSTRAINT uq_flight_routes_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_flight_routes_trip ON flight_routes (trip_id);
CREATE INDEX ix_flight_routes_live_due ON flight_routes (last_checked_at NULLS FIRST) WHERE is_live AND active;
CREATE INDEX ix_flight_routes_due ON flight_routes (next_check_at) WHERE next_check_at IS NOT NULL;
SELECT add_version_trigger('flight_routes');
SELECT add_updated_at_trigger('flight_routes');

CREATE TABLE fare_observations (
  id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  search_key           char(64) NOT NULL,                   -- sha256 of the normalized query
  origin               iata_code NOT NULL,                  -- single airports; multi-airport routes expand
  destination          iata_code NOT NULL,
  depart_date          date NOT NULL,
  return_date          date,
  cabin                cabin_class NOT NULL DEFAULT 'economy',
  adults               smallint NOT NULL DEFAULT 1,
  children             smallint NOT NULL DEFAULT 0,
  stops_max            smallint,
  source               text NOT NULL,
  confidence           fare_confidence NOT NULL,
  currency             currency_code NOT NULL,
  price_total_minor    bigint NOT NULL CHECK (price_total_minor > 0),   -- for the whole party
  airlines             text[] NOT NULL DEFAULT '{}',
  stops_out            smallint,
  stops_back           smallint,
  duration_out_min     integer,
  duration_back_min    integer,
  depart_at_local      text,                                -- as shown by the source, e.g. "2026-11-05 11:30"
  flight_numbers       jsonb,
  deep_link_template   text,                                -- provider link, wrapped through /go at click time
  source_url           text,                                -- page where the fare was seen (required for agent rows)
  source_domain        text,
  run_id               uuid REFERENCES runs (id) ON DELETE SET NULL,   -- internal only, never exposed by the API
  observed_at          timestamptz NOT NULL,
  expires_at           timestamptz NOT NULL,                -- end of the cache window for this observation
  raw                  jsonb,                               -- nulled after 14 days (terms risk)
  created_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_fare_observations_source CHECK (source IN ('serpapi', 'travelpayouts', 'licensed', 'agent', 'manual')),
  CONSTRAINT ck_fare_observations_agent_evidence CHECK (source <> 'agent' OR source_url IS NOT NULL),
  CONSTRAINT uq_fare_observations_search UNIQUE (search_key, source, observed_at)
);
CREATE INDEX ix_fare_observations_lookup
  ON fare_observations (origin, destination, depart_date, return_date, cabin, observed_at DESC);
CREATE INDEX ix_fare_observations_key_fresh ON fare_observations (search_key, expires_at DESC);
CREATE INDEX ix_fare_observations_observed ON fare_observations (observed_at);   -- retention sweeps

CREATE TABLE trip_fare_links (                               -- a trip route's view of a shared observation
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id         uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  route_id        uuid NOT NULL,
  observation_id  bigint NOT NULL REFERENCES fare_observations (id) ON DELETE CASCADE,
  hidden          boolean NOT NULL DEFAULT false,
  suspect         boolean NOT NULL DEFAULT false,
  linked_at       timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (route_id, trip_id) REFERENCES flight_routes (id, trip_id) ON DELETE CASCADE,
  CONSTRAINT uq_trip_fare_links_route_obs UNIQUE (route_id, observation_id)
);
CREATE INDEX ix_trip_fare_links_route ON trip_fare_links (route_id, linked_at DESC);
CREATE INDEX ix_trip_fare_links_trip ON trip_fare_links (trip_id);

CREATE TABLE chosen_flights (                                -- the flight picked for a route; its dates become the trip's dates
  id                 uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id            uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  route_id           uuid NOT NULL,
  observation_id     bigint REFERENCES fare_observations (id) ON DELETE SET NULL,
  -- Snapshot, so the choice survives pruning of the observation.
  origin             iata_code NOT NULL,
  destination        iata_code NOT NULL,
  depart_date        date NOT NULL,
  return_date        date,
  price_total_minor  bigint NOT NULL CHECK (price_total_minor > 0),
  currency           currency_code NOT NULL,
  airlines           text[] NOT NULL DEFAULT '{}',            -- sorted, so the booked-fare drop view can compare them
  flight_numbers     jsonb,                                   -- as on the observation; the booked-fare drop view matches on it
  adults             smallint NOT NULL DEFAULT 1,             -- party size of the chosen fare (the price is for the whole party)
  children           smallint NOT NULL DEFAULT 0,
  source             text NOT NULL,
  observed_at        timestamptz NOT NULL,
  deep_link_template text,
  chosen_by          uuid REFERENCES users (id) ON DELETE SET NULL,
  chosen_at          timestamptz NOT NULL DEFAULT now(),
  cabin              cabin_class NOT NULL DEFAULT 'economy',  -- of the chosen fare, so the booked-fare drop alert compares like with like
  booked_at          timestamptz,                             -- set when the user marks it booked (checklist item flights_booked)
  booked_by          uuid REFERENCES users (id) ON DELETE SET NULL,   -- who booked it; the booked-fare drop alert is sent to them
  paid_minor         bigint CHECK (paid_minor IS NULL OR paid_minor > 0),   -- integer minor units (with paid_currency): what the user paid for the whole party, typed by them or read from an imported confirmation
  paid_currency      currency_code,                           -- the currency they paid in; current prices are converted to it at read time
  paid_source        text,                                    -- manual or import
  drop_alert_enabled boolean NOT NULL DEFAULT true,           -- the user can turn the booked-fare drop alert off for this flight
  last_drop_notified_at     timestamptz,
  last_drop_notified_minor  bigint,                           -- lowest current price (in paid_currency) already announced; the next alert needs a lower one
  FOREIGN KEY (route_id, trip_id) REFERENCES flight_routes (id, trip_id) ON DELETE CASCADE,
  CONSTRAINT ck_chosen_flights_paid CHECK ((paid_minor IS NULL) = (paid_currency IS NULL)),
  CONSTRAINT ck_chosen_flights_paid_booked CHECK (paid_minor IS NULL OR booked_at IS NOT NULL),
  CONSTRAINT ck_chosen_flights_paid_source CHECK (paid_source IS NULL OR (paid_minor IS NOT NULL AND paid_source IN ('manual', 'import'))),
  CONSTRAINT uq_chosen_flights_route UNIQUE (route_id)
);
CREATE INDEX ix_chosen_flights_trip ON chosen_flights (trip_id);
CREATE INDEX ix_chosen_flights_drop_watch ON chosen_flights (depart_date) WHERE paid_minor IS NOT NULL AND drop_alert_enabled;   -- the nightly booked-fare drop scan

CREATE TABLE route_price_insights (                          -- Google price level and typical range, shared by market
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  origin              iata_code NOT NULL,
  destination         iata_code NOT NULL,
  depart_date         date NOT NULL,
  return_date         date,
  currency            currency_code NOT NULL,
  lowest_price_minor  bigint,
  price_level         text CHECK (price_level IN ('low', 'typical', 'high')),
  typical_low_minor   bigint,
  typical_high_minor  bigint,
  history             jsonb NOT NULL DEFAULT '[]'::jsonb,      -- [[unix_seconds, price_minor], ...]
  observed_at         timestamptz NOT NULL,
  expires_at          timestamptz NOT NULL
);
CREATE UNIQUE INDEX uq_route_price_insights_key
  ON route_price_insights (origin, destination, depart_date, COALESCE(return_date, DATE '0001-01-01'), currency);

CREATE VIEW booked_fare_drops WITH (security_invoker = true) AS
SELECT c.id                AS chosen_flight_id,
       c.trip_id,
       c.route_id,
       c.booked_by         AS user_id,
       c.paid_minor,
       c.paid_currency,
       cur.observation_id,
       cur.source,
       cur.confidence,
       cur.observed_at,
       cur.current_minor,
       c.paid_minor - cur.current_minor                                         AS drop_minor,
       round(100.0 * (c.paid_minor - cur.current_minor) / c.paid_minor, 1)    AS drop_pct,
       c.last_drop_notified_minor,
       c.last_drop_notified_at
  FROM chosen_flights c
  JOIN trips t ON t.id = c.trip_id AND t.deleted_at IS NULL
  CROSS JOIN LATERAL (
        SELECT o.id AS observation_id, o.source, o.confidence, o.observed_at,
               fx_convert_minor(o.price_total_minor, o.currency, c.paid_currency) AS current_minor
          FROM trip_fare_links l
          JOIN fare_observations o ON o.id = l.observation_id
         WHERE l.route_id = c.route_id AND NOT l.hidden AND NOT l.suspect
           AND o.origin = c.origin AND o.destination = c.destination
           AND o.depart_date = c.depart_date AND o.return_date IS NOT DISTINCT FROM c.return_date
           AND o.cabin = c.cabin
           AND o.airlines = c.airlines                                 -- same airline, same flight numbers, same party size:
           AND o.flight_numbers IS NOT DISTINCT FROM c.flight_numbers  -- a different flight or a different party is not a drop
           AND o.adults = c.adults AND o.children = c.children
           AND o.observed_at > now() - interval '48 hours'
         ORDER BY o.observed_at DESC
         LIMIT 1) cur
 WHERE c.paid_minor IS NOT NULL AND c.drop_alert_enabled AND c.booked_by IS NOT NULL
   AND c.depart_date >= CURRENT_DATE
   AND cur.current_minor IS NOT NULL AND cur.current_minor < c.paid_minor;

CREATE TABLE price_alerts (
  id                          uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                     uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  route_id                    uuid NOT NULL,
  user_id                     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,   -- who is notified
  threshold_minor             bigint NOT NULL CHECK (threshold_minor > 0),
  currency                    currency_code NOT NULL,
  basis                       text NOT NULL DEFAULT 'cached' CHECK (basis IN ('cached', 'live')),
  channel_push                boolean NOT NULL DEFAULT true,
  channel_email               boolean NOT NULL DEFAULT false,
  active                      boolean NOT NULL DEFAULT true,
  last_evaluated_at           timestamptz,
  last_notified_at            timestamptz,
  last_notified_price_minor   bigint,
  created_at                  timestamptz NOT NULL DEFAULT now(),
  updated_at                  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (route_id, trip_id) REFERENCES flight_routes (id, trip_id) ON DELETE CASCADE,
  CONSTRAINT uq_price_alerts_route_user UNIQUE (route_id, user_id)
);
CREATE INDEX ix_price_alerts_active ON price_alerts (route_id) WHERE active;
CREATE INDEX ix_price_alerts_user ON price_alerts (user_id);
SELECT add_updated_at_trigger('price_alerts');
"""

DOWN = r"""
DROP TABLE price_alerts;
DROP VIEW booked_fare_drops;
DROP TABLE route_price_insights;
DROP TABLE chosen_flights;
DROP TABLE trip_fare_links;
DROP TABLE fare_observations;
DROP TABLE flight_routes;
DROP TYPE fare_confidence;
DROP TYPE trip_type;
DROP TYPE cabin_class;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
