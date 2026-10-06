# ruff: noqa: E501  (long SQL strings)
"""A small Trip Planner database in the shape of the 8 revisions under .reference/trip-planner. It holds every table the importer reads or keeps;
it omits only the ones it never touches (airports, fx_rates, places_cache, route_price_insights, worker_heartbeat)."""

DDL = """
CREATE SCHEMA {s};
SET search_path = {s};
CREATE TABLE people (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name varchar(60) NOT NULL, color varchar(7) NOT NULL, home_airports varchar(3)[] NOT NULL DEFAULT '{{}}', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE trips (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name varchar(120) NOT NULL, start_date date, end_date date, status varchar(12) NOT NULL DEFAULT 'planning', home_currency varchar(3) NOT NULL, notes text NOT NULL DEFAULT '', interests text[] NOT NULL DEFAULT '{{}}', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE trip_travelers (trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, person_id integer NOT NULL REFERENCES people ON DELETE CASCADE, PRIMARY KEY (trip_id, person_id));
CREATE TABLE trip_destinations (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, position integer NOT NULL, name varchar(120) NOT NULL, region varchar(120), country varchar(120), country_code varchar(2), kind varchar(20), lat double precision NOT NULL, lon double precision NOT NULL, timezone varchar(64), bbox double precision[], geoapify_place_id text, summary text, wiki_url text, image_url text, image_file text, info_status varchar(12) NOT NULL DEFAULT 'pending', info_updated_at timestamptz);
CREATE TABLE flight_routes (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, label varchar(80), origin_codes varchar(3)[] NOT NULL, destination_codes varchar(3)[] NOT NULL, trip_type varchar(12) NOT NULL DEFAULT 'round_trip', depart_from date NOT NULL, depart_to date NOT NULL, return_from date, return_to date, min_nights integer, max_nights integer, adults integer NOT NULL DEFAULT 1, children integer NOT NULL DEFAULT 0, cabin varchar(16) NOT NULL DEFAULT 'economy', max_stops integer, sources varchar(20)[] NOT NULL DEFAULT '{{serpapi,travelpayouts}}', alert_price numeric(12,2), active boolean NOT NULL DEFAULT true, chosen_quote_id bigint, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE flight_quotes (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, route_id integer NOT NULL REFERENCES flight_routes ON DELETE CASCADE, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, run_id uuid, source varchar(20) NOT NULL, confidence varchar(12) NOT NULL, origin varchar(3) NOT NULL, destination varchar(3) NOT NULL, depart_date date NOT NULL, return_date date, price_total numeric(12,2) NOT NULL, currency varchar(3) NOT NULL, price_home numeric(12,2), home_currency varchar(3) NOT NULL, passengers integer NOT NULL, airlines varchar(60)[] NOT NULL DEFAULT '{{}}', stops_out integer, stops_back integer, duration_out_min integer, duration_back_min integer, depart_at_local varchar(25), flight_numbers jsonb, segments jsonb, booking_url text, source_url text, source_domain varchar(120), observed_at timestamptz NOT NULL, suspect boolean NOT NULL DEFAULT false, hidden boolean NOT NULL DEFAULT false, dedupe_key varchar(64) NOT NULL, raw jsonb, created_at timestamptz NOT NULL DEFAULT now());
ALTER TABLE flight_routes ADD FOREIGN KEY (chosen_quote_id) REFERENCES flight_quotes ON DELETE SET NULL;
CREATE TABLE itinerary_days (trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, day date NOT NULL, title varchar(120) NOT NULL DEFAULT '', notes text NOT NULL DEFAULT '', destination_id integer REFERENCES trip_destinations ON DELETE SET NULL, updated_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (trip_id, day));
CREATE TABLE activities (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, day date, start_time time, end_time time, title varchar(200) NOT NULL, category varchar(20) NOT NULL DEFAULT 'other', status varchar(12) NOT NULL DEFAULT 'idea', location_name varchar(200), address text, lat double precision, lon double precision, url text, notes text NOT NULL DEFAULT '', place_provider varchar(20), place_id text, place_data jsonb, flight_quote_id bigint REFERENCES flight_quotes ON DELETE CASCADE, version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE lodging_options (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, title varchar(300) NOT NULL, url text, url_normalized text, site varchar(60), check_in date, check_out date, guests integer, price_total numeric(12,2), price_per_night numeric(12,2), currency varchar(3), price_home_total numeric(12,2), photos jsonb NOT NULL DEFAULT '[]', location_name varchar(300), lat double precision, lon double precision, bedrooms integer, beds integer, baths numeric(4,1), rating numeric(3,2), review_count integer, notes text NOT NULL DEFAULT '', pros text NOT NULL DEFAULT '', cons text NOT NULL DEFAULT '', status varchar(12) NOT NULL DEFAULT 'candidate', favorite boolean NOT NULL DEFAULT false, added_via varchar(12) NOT NULL, run_id uuid, raw jsonb, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE lodging_votes (lodging_id integer NOT NULL REFERENCES lodging_options ON DELETE CASCADE, person_id integer NOT NULL REFERENCES people ON DELETE CASCADE, created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (lodging_id, person_id));
CREATE TABLE agent_notes (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, run_id uuid, title varchar(160) NOT NULL, body text NOT NULL, urls text[] NOT NULL DEFAULT '{{}}', created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE routines (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, name varchar(80) NOT NULL, kind varchar(20) NOT NULL, enabled boolean NOT NULL DEFAULT true, schedule_cron varchar(100) NOT NULL, timezone varchar(64) NOT NULL, catch_up boolean NOT NULL DEFAULT true, config jsonb NOT NULL DEFAULT '{{}}', last_slot_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE runs (id uuid PRIMARY KEY, routine_id integer REFERENCES routines ON DELETE SET NULL, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, kind varchar(20) NOT NULL, trigger varchar(12) NOT NULL, status varchar(12) NOT NULL DEFAULT 'queued', params jsonb NOT NULL DEFAULT '{{}}', queued_at timestamptz NOT NULL DEFAULT now(), started_at timestamptz, finished_at timestamptz, pid integer, exit_code integer, prompt text, argv_redacted jsonb, summary text, report jsonb, error text, accepted_count integer NOT NULL DEFAULT 0, rejected_count integer NOT NULL DEFAULT 0, input_tokens integer, output_tokens integer, cost_usd_est numeric(10,4), cancel_requested boolean NOT NULL DEFAULT false, log_path text);
CREATE TABLE run_events (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs ON DELETE CASCADE, seq integer NOT NULL, ts timestamptz NOT NULL DEFAULT now(), type varchar(20) NOT NULL, tool_name varchar(80), summary text NOT NULL, payload jsonb);
CREATE TABLE ingest_rejections (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs ON DELETE CASCADE, entity varchar(30) NOT NULL, item jsonb NOT NULL, errors jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE api_calls (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, provider varchar(20) NOT NULL, endpoint varchar(60) NOT NULL, run_id uuid, units integer NOT NULL DEFAULT 1, cached boolean NOT NULL DEFAULT false, status_code integer, ok boolean NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE activity_suggestions (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, trip_id integer NOT NULL REFERENCES trips ON DELETE CASCADE, run_id uuid, mode varchar(12) NOT NULL, title varchar(200) NOT NULL, category varchar(20) NOT NULL, description text NOT NULL DEFAULT '', why text NOT NULL DEFAULT '', timing_note text NOT NULL DEFAULT '', day date, start_time time, duration_min integer, location_name varchar(200), url text, sources text[] NOT NULL DEFAULT '{{}}', status varchar(12) NOT NULL DEFAULT 'new', activity_id integer, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE app_settings (key varchar(100) PRIMARY KEY, value jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE alembic_version (version_num varchar(32) NOT NULL);
"""

DATA = """
SET search_path = {s};
INSERT INTO people (name, color, home_airports, created_at) VALUES
  ('Ana', '#FF5E7E', '{{SFO}}', '2025-01-10 10:00+00'), ('Ben', '#2E7DF6', '{{OAK,SJC}}', '2025-01-10 10:05+00'), ('Cy', '#12B886', '{{}}', '2025-03-01 09:00+00');
INSERT INTO trips (name, start_date, end_date, status, home_currency, notes, created_at, updated_at) VALUES
  ('Costa Rica', '2026-11-05', '2026-11-15', 'booked', 'USD', 'Pack rain gear', '2025-06-01 12:00+00', '2025-06-02 12:00+00'),
  ('Japan', NULL, NULL, 'planning', 'JPY', '', '2025-07-01 12:00+00', '2025-07-01 12:00+00'),
  ('Old trip', '2024-05-01', '2024-05-05', 'archived', 'EUR', '', '2024-01-01 12:00+00', '2024-06-01 12:00+00');
INSERT INTO trip_travelers VALUES (1,1),(1,2),(1,3),(2,1),(2,2),(3,1);
INSERT INTO trip_destinations (trip_id, position, name, country_code, lat, lon, timezone, bbox, image_url, image_file, info_status) VALUES
  (1, 0, 'La Fortuna', 'CR', 10.47, -84.64, 'America/Costa_Rica', '{{-84.7,10.4,-84.6,10.5}}', 'https://img.example.com/a.jpg', '/data/a.jpg', 'ready'),
  (1, 1, 'Manuel Antonio', 'CR', 9.39, -84.14, 'America/Costa_Rica', NULL, NULL, NULL, 'pending');
INSERT INTO flight_routes (trip_id, label, origin_codes, destination_codes, trip_type, depart_from, depart_to, min_nights, max_nights, adults, children, cabin, max_stops, sources, alert_price, created_at) VALUES
  (1, 'SFO to SJO', '{{SFO,OAK}}', '{{SJO}}', 'round_trip', '2026-11-01', '2026-11-08', 5, 8, 2, 0, 'economy', 1, '{{serpapi,travelpayouts}}', 650.50, '2025-06-03 12:00+00'),
  (2, 'SFO to TYO', '{{SFO}}', '{{HND}}', 'one_way', '2026-12-01', '2026-12-10', NULL, NULL, 1, 0, 'premium_economy', NULL, '{{travelpayouts}}', NULL, '2025-07-02 12:00+00');
INSERT INTO flight_quotes (route_id, trip_id, source, confidence, origin, destination, depart_date, return_date, price_total, currency, price_home, home_currency, passengers, airlines, stops_out, flight_numbers, booking_url, source_url, source_domain, observed_at, suspect, hidden, dedupe_key, raw) VALUES
  (1, 1, 'serpapi', 'live', 'SFO', 'SJO', '2026-11-05', '2026-11-15', 612.34, 'USD', 612.34, 'USD', 2, '{{United}}', 1, '["UA123"]', 'https://book.example.com/x', NULL, NULL, '2026-09-01 08:00+00', false, false, 'dk-1', '{{"secret": "raw"}}'),
  (1, 1, 'travelpayouts', 'cached', 'SFO', 'SJO', '2026-11-05', '2026-11-15', 640.00, 'USD', 640.00, 'USD', 2, '{{Avianca}}', 1, NULL, NULL, NULL, NULL, '2026-09-02 08:00+00', false, false, 'dk-2', NULL),
  (1, 1, 'agent', 'indicative', 'SFO', 'SJO', '2026-11-06', '2026-11-15', 700.00, 'USD', 700.00, 'USD', 2, '{{}}', NULL, NULL, NULL, NULL, NULL, '2026-09-03 08:00+00', false, false, 'dk-3', NULL),
  (1, 1, 'agent', 'indicative', 'SFO', 'SJO', '2026-11-07', '2026-11-15', 520.10, 'USD', 520.10, 'USD', 2, '{{}}', NULL, NULL, NULL, 'https://example.com/fare', 'example.com', '2026-09-04 08:00+00', true, true, 'dk-4', NULL),
  (1, 1, 'serpapi', 'live', 'SFO', 'SJO', '2026-11-05', '2026-11-15', 612.34, 'USD', 612.34, 'USD', 2, '{{United}}', 1, NULL, NULL, NULL, NULL, '2026-09-01 08:00+00', false, false, 'dk-1', NULL),
  (2, 2, 'travelpayouts', 'cached', 'SFO', 'HND', '2026-12-05', NULL, 90000, 'JPY', 90000, 'JPY', 1, '{{ANA}}', 0, NULL, NULL, NULL, NULL, '2026-09-05 08:00+00', false, false, 'dk-5', NULL);
INSERT INTO flight_routes (trip_id, label, origin_codes, destination_codes, trip_type, depart_from, depart_to, min_nights, max_nights, sources, chosen_quote_id) VALUES
  (1, 'Agent pick', '{{SFO}}', '{{LIR}}', 'round_trip', '2026-11-01', '2026-11-08', 5, 8, '{{agent}}', 3);
UPDATE flight_routes SET chosen_quote_id = 1 WHERE id = 1;
INSERT INTO itinerary_days (trip_id, day, title, notes, destination_id) VALUES (1, '2026-11-06', 'Arenal', 'Volcano day', 1), (1, '2026-11-07', '', 'Rest', NULL);
INSERT INTO activities (trip_id, day, start_time, end_time, title, category, status, location_name, lat, lon, place_provider, place_id, version, created_at) VALUES
  (1, '2026-11-06', '09:00', '11:00', 'Volcano hike', 'nature', 'planned', 'Arenal', 10.46, -84.70, 'geoapify', 'g1', 1, '2025-06-05 12:00+00'),
  (1, NULL, NULL, NULL, 'Try gallo pinto', 'food', 'idea', NULL, NULL, NULL, NULL, NULL, 1, '2025-06-05 12:05+00'),
  (1, '2026-11-06', NULL, NULL, 'Hot springs', 'other', 'booked', NULL, NULL, NULL, NULL, NULL, 3, '2025-06-05 12:10+00');
INSERT INTO lodging_options (trip_id, title, url, url_normalized, check_in, check_out, price_total, price_per_night, currency, photos, status, favorite, added_via, raw, created_at) VALUES
  (1, 'Treehouse', 'https://example.com/l1', 'https://example.com/l1', '2026-11-06', '2026-11-11', 1234.56, 246.91, 'USD', '["https://img.example.com/1.jpg"]', 'shortlisted', true, 'serpapi', '{{"raw": 1}}', '2025-06-06 12:00+00'),
  (2, 'Ryokan', NULL, NULL, NULL, NULL, 150000, 30000, 'JPY', '[]', 'candidate', false, 'manual', NULL, '2025-07-03 12:00+00'),
  (1, 'No price yet', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '[]', 'candidate', false, 'paste', NULL, '2025-06-06 12:05+00'),
  (1, 'Currency missing', NULL, NULL, NULL, NULL, 100.00, NULL, NULL, '[]', 'candidate', false, 'bookmarklet', NULL, '2025-06-06 12:10+00');
INSERT INTO lodging_votes (lodging_id, person_id) VALUES (1,1),(1,2),(1,3),(2,1);
INSERT INTO agent_notes (trip_id, title, body, urls, created_at) VALUES
  (1, 'ANA sale', 'Ends Oct 3', '{{https://example.com/sale}}', '2025-08-01 12:00+00'),
  (1, 'Rumor', 'Maybe cheaper in May', '{{}}', '2025-08-02 12:00+00');
INSERT INTO routines (trip_id, name, kind, schedule_cron, timezone) VALUES (1, 'Daily fares', 'flight_api', '0 7 * * *', 'UTC');
INSERT INTO runs (id, routine_id, trip_id, kind, trigger, status, queued_at, started_at, finished_at, pid, exit_code, prompt, summary, report, accepted_count, input_tokens, output_tokens, cost_usd_est, log_path) VALUES
  ('00000000-0000-4000-8000-000000000001', NULL, 1, 'flight_agent', 'manual', 'succeeded', now() - interval '40 days', now() - interval '40 days', now() - interval '40 days' + interval '3 minutes', 4242, 0, 'secret prompt', 'Found 2 fares', '{{"found": 2}}', 2, 1000, 500, 0.1234, '/logs/1.log'),
  ('00000000-0000-4000-8000-000000000002', NULL, 1, 'research_agent', 'manual', 'partial', now() - interval '3 days', now() - interval '3 days', now() - interval '3 days' + interval '1 minute', NULL, NULL, NULL, 'Some sources', NULL, 0, NULL, NULL, NULL, NULL),
  ('00000000-0000-4000-8000-000000000003', 1, 1, 'flight_api', 'schedule', 'succeeded', now() - interval '2 days', now() - interval '2 days', now() - interval '2 days', NULL, NULL, NULL, NULL, NULL, 0, NULL, NULL, NULL, NULL),
  ('00000000-0000-4000-8000-000000000004', NULL, 1, 'itinerary_agent', 'manual', 'succeeded', now() - interval '2 days', now() - interval '2 days', now() - interval '2 days', NULL, NULL, NULL, NULL, NULL, 0, NULL, NULL, NULL, NULL),
  ('00000000-0000-4000-8000-000000000005', NULL, 2, 'flight_agent', 'manual', 'running', now() - interval '1 days', now() - interval '1 days', NULL, 99, NULL, NULL, NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO run_events (run_id, seq, ts, type, tool_name, summary) VALUES
  ('00000000-0000-4000-8000-000000000001', 1, now() - interval '40 days', 'info', NULL, 'old event'),
  ('00000000-0000-4000-8000-000000000002', 1, now() - interval '3 days', 'info', NULL, 'recent a'),
  ('00000000-0000-4000-8000-000000000002', 2, now() - interval '3 days' + interval '10 seconds', 'tool_use', 'search', 'recent b'),
  ('00000000-0000-4000-8000-000000000005', 1, now() - interval '1 days', 'text', NULL, 'recent c'),
  ('00000000-0000-4000-8000-000000000003', 1, now() - interval '2 days', 'info', NULL, 'scheduled run event');
INSERT INTO ingest_rejections (run_id, entity, item, errors, created_at) VALUES
  ('00000000-0000-4000-8000-000000000002', 'quote', '{{"price": -1}}', '[{{"loc": "price"}}]', now() - interval '3 days'),
  ('00000000-0000-4000-8000-000000000001', 'quote', '{{}}', '[]', now() - interval '40 days');
INSERT INTO api_calls (provider, endpoint, units, cached, status_code, ok, created_at) VALUES
  ('serpapi', 'google_flights', 1, false, 200, true, now() - interval '1 days'),
  ('geoapify', 'geocode', 1, true, 200, true, now() - interval '20 days'),
  ('serpapi', 'google_hotels', 2, false, 429, false, now() - interval '200 days'),
  ('serpapi', 'google_flights', 1, false, 200, true, now() - interval '14 months');
INSERT INTO activity_suggestions (trip_id, mode, title, category) VALUES (1, 'brainstorm', 'Zip line', 'nature'), (1, 'surprise', 'Night market', 'food');
INSERT INTO app_settings VALUES ('home_currency', '"EUR"', now()), ('serpapi_monthly_cap', '250', now());
INSERT INTO alembic_version VALUES ('0008');
"""
