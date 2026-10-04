"""0005_ai: runs, events, usage, provider calls, shared research cache (03 sections 5.6, 7.4 and 9) and Procrastinate's schema.

Procrastinate's own schema is vendored in sql/procrastinate_3_10_0.sql (library version 3.10.0, verbatim from its schema.sql).
03 section 9 also creates link_clicks partitions and the maintain_partitions, drop_old_log_partitions and partition_default_rows
objects; link_clicks arrives in 0008 and those three land in 0014_rls, so only the generic helpers and the first partitions of
provider_calls and run_events are made here. The EXECUTE grant on my_provider_spend_micros is kept with it (7.4), as 0004 did.
The two partition helpers stay owned by hermi_owner here: 0014 makes them SECURITY DEFINER, re-owns them and the
parents to hermi_definer and revokes PUBLIC, once (03 section 9), so the later link_clicks partitions can still be made.
The GRANT EXECUTE on procrastinate_defer_jobs_v1 is in 6.1 and lands in 0014_rls with the other grants.

Revision ID: 0005_ai
Revises: 0004_trips_people
"""

from pathlib import Path

from alembic import op

revision = "0005_ai"
# 03 section 10 lists 0003 and 0004 as parents; the chain is linear, so the parent is 0004 (one head).
down_revision = "0004_trips_people"
branch_labels = None
depends_on = None

PROCRASTINATE_SQL = Path(__file__).resolve().parent.parent / "sql" / "procrastinate_3_10_0.sql"

UP = r"""
CREATE TYPE run_kind     AS ENUM ('fare_hunt', 'deep_research', 'research_question', 'draft_trip', 'draft_day', 'explain',
                                  'packing_list', 'booking_import',    -- priced as 'explain'
                                  'verify_extract',                    -- reads a pasted plan into items (priced as 'explain')
                                  'verify_plan',                       -- checks the selected items, 1 credit each (action 'verify_plan')
                                  'recheck');                          -- one-tap evidence recheck (priced as 'explain'); platform work (digest, cache_warm, classifier, eval) has no run
CREATE TYPE run_trigger  AS ENUM ('manual');                          -- Phase 1 runs are always started by a person
CREATE TYPE run_status   AS ENUM ('queued', 'running', 'succeeded', 'partial', 'failed', 'timed_out', 'cancelled', 'interrupted');
CREATE TYPE usage_state  AS ENUM ('reserved', 'settled', 'released');

CREATE TABLE runs (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id           uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  user_id           uuid REFERENCES users (id) ON DELETE SET NULL,           -- who is charged
  kind              run_kind NOT NULL,
  action            ai_action,                                               -- credit action this run was priced as
  trigger           run_trigger NOT NULL DEFAULT 'manual',
  status            run_status NOT NULL DEFAULT 'queued',
  params            jsonb NOT NULL DEFAULT '{}'::jsonb,
  prompt            text,                                                    -- nulled after 30 days
  model             text,
  provider          text NOT NULL DEFAULT 'anthropic_api',                   -- who ran it; the cost of a 'claude_cli' run is notional (a subscription, not metered)
  prompt_version    text,
  queued_at         timestamptz NOT NULL DEFAULT now(),
  started_at        timestamptz,
  finished_at       timestamptz,
  worker_id         text,
  heartbeat_at      timestamptz,                                             -- the worker stamps it every 15 seconds while running; the reaper interrupts runs silent for 2 minutes (5 in the ai lane)
  summary           text,
  report            jsonb,                                                   -- kept 12 months
  error             text,                                                    -- operator-facing detail (scrubbed of user text)
  failure_code      text,                                                    -- stable code the API returns as error_code: worker_lost, provider_error, provider_timeout, budget_stop, refused, cancelled, nothing_saved
  accepted_count    integer NOT NULL DEFAULT 0,
  rejected_count    integer NOT NULL DEFAULT 0,
  input_tokens      integer,
  output_tokens     integer,
  turns_used        smallint,
  searches_used     smallint,
  fetches_used      smallint,
  cost_usd_micros   bigint NOT NULL DEFAULT 0,
  served_from_cache boolean NOT NULL DEFAULT false,
  cache_key         char(64),                                                -- shared_research_cache.key when cached or stored
  reservation_id    uuid,                                                    -- credit_ledger.reservation_id
  cancel_requested  boolean NOT NULL DEFAULT false,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_runs_provider CHECK (provider IN ('anthropic_api', 'claude_cli', 'fake')),
  CONSTRAINT ck_runs_finished CHECK (status IN ('queued', 'running') OR finished_at IS NOT NULL),
  CONSTRAINT uq_runs_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_runs_queue ON runs (queued_at) WHERE status = 'queued';
CREATE INDEX ix_runs_trip ON runs (trip_id, queued_at DESC);
CREATE INDEX ix_runs_user ON runs (user_id, queued_at DESC);
-- One agent run at a time per account (fare hunts and deep research); a second insert fails and the API answers 409 run_already_active.
CREATE UNIQUE INDEX uq_runs_one_active_agent ON runs (user_id)
  WHERE status IN ('queued', 'running') AND kind IN ('fare_hunt', 'deep_research') AND user_id IS NOT NULL;
CREATE INDEX ix_runs_active_user ON runs (user_id) WHERE status IN ('queued', 'running');   -- admission checks for other concurrent runs (research, drafts)
CREATE INDEX ix_runs_reaper ON runs (heartbeat_at) WHERE status = 'running';

-- Partitioned by month on ts. Primary key must include the partition key.
CREATE TABLE run_events (
  id          bigint GENERATED ALWAYS AS IDENTITY,
  run_id      uuid NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
  trip_id     uuid NOT NULL,                                                 -- copy of runs.trip_id, keeps RLS cheap (no FK)
  seq         integer NOT NULL,
  ts          timestamptz NOT NULL DEFAULT now(),
  type        text NOT NULL,
  tool_name   text,
  summary     text NOT NULL,
  payload     jsonb,
  PRIMARY KEY (id, ts),
  CONSTRAINT ck_run_events_type CHECK (type IN ('info', 'warning', 'error', 'tool_use', 'tool_result', 'text', 'result', 'rejection')),
  CONSTRAINT uq_run_events_run_seq UNIQUE (run_id, seq, ts)
) PARTITION BY RANGE (ts);
CREATE INDEX ix_run_events_run ON run_events (run_id, seq);

CREATE TABLE ai_usage (
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id             uuid REFERENCES users (id) ON DELETE SET NULL,
  trip_id             uuid REFERENCES trips (id) ON DELETE SET NULL,
  run_id              uuid REFERENCES runs (id) ON DELETE SET NULL,
  action              ai_action NOT NULL,
  model               text,
  provider            text NOT NULL DEFAULT 'anthropic_api',                 -- the cost of a 'claude_cli' row is notional (a subscription, not metered)
  input_tokens        integer NOT NULL DEFAULT 0,
  output_tokens       integer NOT NULL DEFAULT 0,
  cache_read_tokens   integer NOT NULL DEFAULT 0,
  cache_write_tokens  integer NOT NULL DEFAULT 0,
  web_searches        smallint NOT NULL DEFAULT 0,
  via_batch           boolean NOT NULL DEFAULT false,
  cost_usd_micros     bigint NOT NULL DEFAULT 0,                             -- Claude cost (tokens and web-search fees); other providers' per-call costs are in provider_calls
  credits_reserved    integer NOT NULL DEFAULT 0,
  credits_charged     integer NOT NULL DEFAULT 0,
  state               usage_state NOT NULL DEFAULT 'reserved',
  cache_hit           boolean NOT NULL DEFAULT false,                        -- served from shared_research_cache
  reservation_id      uuid,
  idempotency_key     text NOT NULL,                                         -- user actions: '{user_id}:{Idempotency-Key header}'; platform rows: 'warm:{key}', 'digest:{trip_id}:{week}', 'eval:{suite}:{case}'
  purpose             text,                                                  -- platform work with no user and no credit action (06 section 1); its rows borrow the closest action ('research' for cache_warm, 'explain' otherwise)
  created_at          timestamptz NOT NULL DEFAULT now(),
  settled_at          timestamptz,
  CONSTRAINT uq_ai_usage_idempotency UNIQUE (idempotency_key),
  CONSTRAINT ck_ai_usage_purpose CHECK (purpose IS NULL OR (purpose IN ('digest', 'cache_warm', 'classifier', 'eval') AND user_id IS NULL)),
  CONSTRAINT ck_ai_usage_provider CHECK (provider IN ('anthropic_api', 'claude_cli', 'fake')),
  CONSTRAINT ck_ai_usage_charged CHECK (credits_charged <= credits_reserved),
  CONSTRAINT ck_ai_usage_settled CHECK (state = 'reserved' OR settled_at IS NOT NULL)
);
CREATE INDEX ix_ai_usage_user_time ON ai_usage (user_id, created_at DESC);      -- daily and monthly ceiling sums
CREATE INDEX ix_ai_usage_stale ON ai_usage (created_at) WHERE state = 'reserved';
CREATE INDEX ix_ai_usage_run ON ai_usage (run_id) WHERE run_id IS NOT NULL;

-- Partitioned by month on created_at. Not referenced by any foreign key.
CREATE TABLE provider_calls (
  id               bigint GENERATED ALWAYS AS IDENTITY,
  provider         text NOT NULL,                                            -- anthropic, serpapi, travelpayouts, geoapify, wikimedia, viator, stay22, frankfurter, resend, apns
  endpoint         text NOT NULL,
  user_id          uuid,                                                     -- no foreign keys: this is a log
  trip_id          uuid,
  run_id           uuid,
  units            numeric(12,3) NOT NULL DEFAULT 1,
  cost_usd_micros  bigint,                                                   -- our cost for the call; null if free, unknown, or provider = 'anthropic' (that cost lives in ai_usage)
  cached           boolean NOT NULL DEFAULT false,
  cache_layer      text,
  ok               boolean NOT NULL,
  status_code      smallint,
  latency_ms       integer,
  request_hash     char(64),                                                 -- the cache key, for dedup analytics
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (id, created_at),
  CONSTRAINT ck_provider_calls_cache_layer CHECK (cache_layer IS NULL OR cache_layer IN ('db', 'memory', 'provider'))
) PARTITION BY RANGE (created_at);
CREATE INDEX ix_provider_calls_provider_time ON provider_calls (provider, created_at);
CREATE INDEX ix_provider_calls_user_time ON provider_calls (user_id, provider, created_at) WHERE user_id IS NOT NULL;

-- Monthly rollup kept after the raw provider_calls partitions are dropped (cost analytics and the cache hit rate per provider; section 9).
CREATE TABLE provider_call_rollups (
  month         date NOT NULL,
  provider      text NOT NULL,
  endpoint      text NOT NULL,
  calls         bigint NOT NULL,
  cached_calls  bigint NOT NULL,
  failed_calls  bigint NOT NULL,
  units         numeric(14,3) NOT NULL,
  cost_usd_micros bigint NOT NULL DEFAULT 0,
  PRIMARY KEY (month, provider, endpoint)
);

CREATE TABLE shared_research_cache (                         -- derived research shared across users; public-input facts only
  key             char(64) PRIMARY KEY,                       -- sha256 of kind, normalized destination, month, prompt_version, model
  kind            text NOT NULL,
  provider        text NOT NULL,
  params          jsonb NOT NULL,                             -- normalized input, for debugging and invalidation
  response        jsonb NOT NULL,
  sources         jsonb NOT NULL DEFAULT '[]'::jsonb,         -- source URLs the facts came from
  response_bytes  integer NOT NULL DEFAULT 0,
  model           text,
  prompt_version  text,
  fetched_at      timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz NOT NULL,
  stale_until     timestamptz NOT NULL,                       -- stale-while-revalidate window
  hit_count       integer NOT NULL DEFAULT 0,
  last_hit_at     timestamptz,
  run_id          uuid REFERENCES runs (id) ON DELETE SET NULL,  -- the run that created the entry
  cost_usd_micros bigint NOT NULL DEFAULT 0,                  -- what creating it cost (the first requester's run)
  report_count    smallint NOT NULL DEFAULT 0,                -- distinct reporters (content_reports); three set flagged_at
  flagged_at      timestamptz,                                -- never served and never overwritten until an admin clears it; the key then runs uncached at the normal price
  CONSTRAINT ck_shared_research_cache_kind CHECK (kind IN ('ai_research', 'destination_brief', 'visa_summary', 'neighborhoods', 'rentals', 'agent_result', 'place_check')),
  CONSTRAINT ck_shared_research_cache_window CHECK (stale_until >= expires_at)
);
CREATE INDEX ix_shared_research_cache_kind_exp ON shared_research_cache (kind, expires_at);
CREATE INDEX ix_shared_research_cache_purge ON shared_research_cache (stale_until) WHERE flagged_at IS NULL;

CREATE FUNCTION ensure_month_partitions(p_table regclass, p_months_ahead integer DEFAULT 3) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE v_name text; v_month date; v_child text; n integer := 0;
BEGIN
  SELECT relname INTO v_name FROM pg_class WHERE oid = p_table;
  EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %s DEFAULT', v_name || '_default', p_table);
  FOR i IN -1 .. p_months_ahead LOOP
    v_month := (date_trunc('month', now() AT TIME ZONE 'UTC') + make_interval(months => i))::date;
    v_child := v_name || '_' || to_char(v_month, 'YYYY_MM');
    IF to_regclass(v_child) IS NULL THEN
      EXECUTE format('CREATE TABLE %I PARTITION OF %s FOR VALUES FROM (%L) TO (%L)',
        v_child, p_table,
        v_month::text || ' 00:00:00+00',
        (v_month + interval '1 month')::date::text || ' 00:00:00+00');
      n := n + 1;
    END IF;
  END LOOP;
  RETURN n;
END $$;

-- Drops partitions whose month is older than p_keep_months (by name suffix YYYY_MM, which sorts as text).
CREATE FUNCTION drop_old_partitions(p_table regclass, p_keep_months integer) RETURNS integer
LANGUAGE plpgsql AS $$
DECLARE r record; v_cut text; n integer := 0;
BEGIN
  v_cut := to_char((date_trunc('month', now() AT TIME ZONE 'UTC') - make_interval(months => p_keep_months))::date, 'YYYY_MM');
  FOR r IN SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = p_table LOOP
    IF right(r.relname, 7) ~ '^\d{4}_\d{2}$' AND right(r.relname, 7) < v_cut THEN
      EXECUTE format('DROP TABLE %I', r.relname);
      n := n + 1;
    END IF;
  END LOOP;
  RETURN n;
END $$;

SELECT ensure_month_partitions('provider_calls', 3);
SELECT ensure_month_partitions('run_events', 3);

CREATE FUNCTION my_provider_spend_micros(since timestamptz) RETURNS bigint
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id();
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  RETURN COALESCE((SELECT sum(cost_usd_micros) FROM provider_calls
                    WHERE user_id = v_me AND provider <> 'anthropic' AND cost_usd_micros IS NOT NULL AND created_at >= since), 0);
END $$;
ALTER FUNCTION my_provider_spend_micros(timestamptz) OWNER TO hermi_definer;
REVOKE EXECUTE ON FUNCTION my_provider_spend_micros(timestamptz) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION my_provider_spend_micros(timestamptz) TO hermi_app;
"""

VIEW = """
-- Worker liveness for the non-user jobs (02 section 5): one row per registered Procrastinate worker.
CREATE VIEW job_heartbeats AS
SELECT id AS worker_id, last_heartbeat, EXTRACT(EPOCH FROM now() - last_heartbeat)::double precision AS seconds_since_heartbeat
  FROM procrastinate_workers;
"""

DOWN = r"""
DROP VIEW job_heartbeats;
DROP FUNCTION my_provider_spend_micros(timestamptz);
DROP TABLE shared_research_cache;
DROP TABLE provider_call_rollups;
DROP TABLE provider_calls;
DROP TABLE ai_usage;
DROP TABLE run_events;
DROP TABLE runs;
DROP FUNCTION drop_old_partitions(regclass, integer);
DROP FUNCTION ensure_month_partitions(regclass, integer);
DROP TYPE usage_state;
DROP TYPE run_status;
DROP TYPE run_trigger;
DROP TYPE run_kind;
DO $$ DECLARE f regprocedure; BEGIN
  FOR f IN SELECT p.oid::regprocedure FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace AND p.proname LIKE 'procrastinate\_%' LOOP
    EXECUTE 'DROP FUNCTION ' || f || ' CASCADE';
  END LOOP;
END $$;
DROP TABLE procrastinate_events, procrastinate_periodic_defers, procrastinate_jobs, procrastinate_workers;
DROP TYPE procrastinate_job_to_defer_v1;
DROP TYPE procrastinate_job_event_type;
DROP TYPE procrastinate_job_status;
"""


def upgrade() -> None:
    op.execute(UP)
    op.execute(PROCRASTINATE_SQL.read_text(encoding="utf-8"))
    op.execute(VIEW)


def downgrade() -> None:
    op.execute(DOWN)
