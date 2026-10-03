# Pack 06: Pro tier and scheduled agent routines

Part of [Phase 2: growth](README.md). Written 2026-09-30. Source definitions:
[01 F-AI-7](../reference-full-spec/01-product-spec.md), [03 sections 5.11 and 11.1](../reference-full-spec/03-database-schema.md),
[04 section 5.13](../reference-full-spec/04-api-spec.md), [06 section 5.10](../reference-full-spec/06-ai-agents-spec.md),
[07 sections 2.1, 5.5 and 7](../reference-full-spec/07-monetization-spec.md), [08 section 6.6](../reference-full-spec/08-admin-control-center.md),
roadmap tickets WF-078 and WF-105 in [09](../reference-full-spec/09-build-roadmap.md).

| Item | Value |
|---|---|
| Build order | 8 (build dark in month 11, sell in month 12 only if the gate is met) |
| Flags | `tier_pro` (hides the tier and products), `scheduled_agent_routines` (scheduler skips agent kinds while off) |
| Needs from Phase 1 | Agent runs (`fare_hunt`, `deep_research`), credits and ceilings, scheduler with `scan_due_routines`, shared research cache, price checks, feature flags, admin flags screen, RevenueCat, notifications |
| Gate | Mean agent cost of $0.60 or less per run over 200 runs, or over 15 percent of Plus payers buying agent-run credits ([09 section 1](../reference-full-spec/09-build-roadmap.md), [08 section 6.6](../reference-full-spec/08-admin-control-center.md)) |
| Tickets | P2-055 to P2-064 |
| Tier and products | `pro`, `hermi_pro_monthly` ($11.99), `hermi_pro_annual` ($99) |

## 1. Goal and why now

**Goal.** Sell a top tier to the people who use the product hardest: 240 credits a month (one month
rolls over), 6 live routes, 12 collaborators and travelers, priority queue, and scheduled agent routines
that watch fares or research a destination on a schedule and send one digest when something changes.

**Why now.**

- Phase 1 agents are manual and cost 40 credits a run. Deal hunters (persona P4) run the same hunt
  again and again; a schedule is the natural upgrade and the reason for a higher price.
- Pro is the anchor that makes Plus look fair. It is priced well above rivals' annual plans ($99 against
  Wanderlog Pro $39.99 and TripIt Pro $49, reported, verify; [business plan](../context/business-plan/01-business-plan.md)
  open question 3), so it launches only when the economics are proven, not on a date.
- Everything it needs already exists dark from Phase 1 (routines table, scheduler, priority on runs); this
  pack finishes, tests and sells it.
- Honest framing: 240 credits is 6 full agent runs (40 each) or 30 cache-served runs (8 each) a month.
  A daily agent routine is a maximum cadence, not a promise; the product shows the credit cost of a
  schedule before saving it.

## 2. User stories and acceptance criteria

### F-AI-7 Scheduled routines (Pro), verbatim from the full product spec

- Story: As a `pro` user, I want a fare hunt or research to run on a schedule, so that I hear
  about new findings without asking.
- Acceptance:
  - A routine (`routines`) has a trip, kind (hunt fares or research), and cadence up to once per
    day with at least 12 hours between runs; up to 3 per trip.
  - Each scheduled run costs 40 credits (`agent_run`) from the routine owner's balance and uses
    the same caps; scheduled work uses the shared cache first.
  - A routine pauses itself when credits run out, the ceiling hits, or the trip is in the past,
    and says why.
  - Notification digest after each run with what changed, never more than one per routine per
    day.
  - Hidden and disabled for all other tiers until `pro` launches; `pro` is built behind a
    feature flag. Non-Pro users who open the Routines screen see a sample result from the
    shared cache and the credit-based manual alternative.
- Tier: `pro` only. Credits: `agent_run` 40 per run.

### Stories added by this pack

| ID | Story | Acceptance |
|---|---|---|
| PRO-1 | As a Pro user, I create a routine with a clear cost. | The create sheet shows "About 160 credits a month at this schedule. Your allowance is 240." before saving. Saving is never blocked by the estimate; a routine that cannot run is paused with a reason. |
| PRO-2 | As a Pro user, a routine tells me why it stopped. | `paused_reason` values: `no_credits` ("Paused: not enough credits"), `ceiling` ("Paused: monthly limit reached, resumes on the 1st"), `trip_past`, `owner_lapsed`, `kill_switch`, `user`. Resuming after the cause clears is one tap and automatic for `no_credits` and `ceiling` when the month turns. |
| PRO-3 | As a Pro user, I get one digest per routine per day. | After a run the digest says what changed (new fares within 15 percent of the cheapest known, price moves, new notes with sources) or "Nothing new". Never more than one per routine per day; quiet hours respected. |
| PRO-4 | As a Pro user, my jobs run first. | Runs from Pro accounts carry higher `priority` with aging so Plus and Free jobs are never starved; per account concurrency cap for Pro is 8. |
| PRO-5 | As a Pro user, unused credits roll over once. | At each grant, unspent `monthly` credits convert to an `adjustment` grant (note `rollover`) capped at 240 and expiring at the end of the new period. |
| PRO-6 | As a Plus or Free user, I see what Pro does without being nagged. | The Routines screen shows a sample result from the shared cache and the manual alternative ("Run once, 40 credits"). Pro appears in Compare plans and paywalls only after launch. |
| PRO-7 | As the business, Pro cannot launch early. | The admin flag screen blocks enabling `tier_pro` until the gate numbers are met, unless the owner overrides with a typed reason. |
| PRO-8 | As a Plus and above user, I get a weekly digest. | `digest` (06 section 5.10): Haiku 4.5 via Batch, one call per active trip, a short plain text summary of price movement, new notes and upcoming deadlines from data already in the database (no web), about $0.003 each, included with Plus and up, not sold. |
| PRO-9 | As a Pro user, I upgrade and downgrade safely. | Upgrades (Plus or Family to Pro) apply immediately with the grant difference; downgrades apply at renewal; on lapse routines pause with `owner_lapsed`, data stays. |

Pro limits from its plan row: 50 active trips (fair use), 8 routes per trip, 6 live routes, 6 price
alerts, 12 collaborators and 12 travelers, 200 place searches a day, 240 credits a month,
`scheduled_routines`, `priority_queue`, `credit_rollover_cap` 240, `group_payments` true (effective in
Phase 3), monthly provider-spend ceiling $5.50 and daily budget $1.25.

## 3. Database additions

Migration `0022_pro_routines`. Phase 1 has no
`routines` table and no routine kinds: [Phase 1 03 section 1.1](../phase-1-launch/03-database-schema.md)
lists `routines`, `runs.routine_id`, `runs.priority`, the `routine_kind` type, the run kinds `price_check`
and `batch_scan`, the run triggers `schedule` and `catch_up`, the `pro` plan row, the Pro limit keys and the
Pro flags as dropped; Phase 1's daily live-route checks are a worker job driven by `flight_routes`, not a
routine, and `scan_due_routines` only enqueues those. Definitions are reused from
[the full 03 section 5.11](../reference-full-spec/03-database-schema.md).

```sql
CREATE TYPE routine_kind AS ENUM ('price_check', 'batch_scan', 'fare_hunt', 'deep_research');
ALTER TYPE run_kind    ADD VALUE 'price_check';     -- each ADD VALUE is its own migration step
ALTER TYPE run_kind    ADD VALUE 'batch_scan';
ALTER TYPE run_trigger ADD VALUE 'schedule';
ALTER TYPE run_trigger ADD VALUE 'catch_up';

CREATE TABLE routines (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id         uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  owner_user_id   uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,     -- who is billed for the checks
  name            text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
  kind            routine_kind NOT NULL,
  enabled         boolean NOT NULL DEFAULT true,
  schedule_cron   text NOT NULL,                                               -- 5-field cron evaluated in timezone
  timezone        text NOT NULL,
  catch_up        boolean NOT NULL DEFAULT true,
  config          jsonb NOT NULL DEFAULT '{}'::jsonb,
  last_slot_at    timestamptz,
  next_run_at     timestamptz,
  paused_reason   text,                                                        -- added by this pack: why a routine is paused
  paused_at       timestamptz,
  last_digest_at  timestamptz,                                                 -- digest throttle: one per routine per day
  last_run_id     uuid,
  version         integer NOT NULL DEFAULT 1,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_routines_paused_reason
    CHECK (paused_reason IS NULL OR paused_reason IN ('no_credits', 'ceiling', 'trip_past', 'owner_lapsed', 'kill_switch', 'user'))
);
CREATE INDEX ix_routines_due ON routines (next_run_at) WHERE enabled;
CREATE INDEX ix_routines_trip ON routines (trip_id);
CREATE INDEX ix_routines_owner ON routines (owner_user_id);
SELECT add_version_trigger('routines');
SELECT add_updated_at_trigger('routines');
-- Agent kinds (fare_hunt, deep_research) are rejected by the API unless the owner's entitlement has scheduled_routines.
-- The 12 hour minimum gap between runs and the cron shape are validated by the API, not by a column constraint.

-- runs: the routine link and the Pro priority (03 section 5.11)
ALTER TABLE runs ADD COLUMN routine_id uuid REFERENCES routines (id) ON DELETE SET NULL;
ALTER TABLE runs ADD COLUMN priority smallint NOT NULL DEFAULT 0;                -- Pro jumps the queue
DROP INDEX ix_runs_queue;
CREATE INDEX ix_runs_queue ON runs (priority DESC, queued_at) WHERE status = 'queued';
CREATE INDEX ix_runs_routine ON runs (routine_id, queued_at DESC) WHERE routine_id IS NOT NULL;
-- uq_runs_one_active_agent (one agent run at a time per account, scheduled or manual) already exists from Phase 1 and needs no change.

-- Row-level security: trip-child policies (members read; owner and editors write), added to the generated loop of 03 section 6.4.
ALTER TABLE routines ENABLE ROW LEVEL SECURITY;
CREATE POLICY routines_select ON routines FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY routines_insert ON routines FOR INSERT WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY routines_update ON routines FOR UPDATE USING (can_edit_trip(trip_id)) WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY routines_delete ON routines FOR DELETE USING (can_edit_trip(trip_id));
```

Plan row and products (from [03 section 11.1 and 11.2](../reference-full-spec/03-database-schema.md)). Phase 1 does not seed
the `pro` row at all, so this migration inserts it hidden behind `tier_pro`; the launch step activates it:

```sql
INSERT INTO plans (code, kind, name, rank, monthly_credits, credits_granted, credits_valid_days, duration_days, feature_flag_key, is_active, sort_order, limits) VALUES
('pro', 'tier', 'Pro', 40, 240, 0, NULL, NULL, 'tier_pro', false, 30,
 '{"active_trips":50,"active_trips_bonus":0,"routes_per_trip":8,"live_routes":6,"live_window_days":120,"price_alerts":6,"live_alerts":true,
   "collaborators":12,"travelers_per_trip":12,"can_invite":true,"saved_lodging_per_trip":100,"lodging_compare":4,
   "places_searches_per_day":200,"polls":true,"cost_splitting":true,"room_block_request":false,"group_payments":true,
   "hide_presentation_footer":true,"scheduled_routines":true,"priority_queue":true,"credit_rollover_cap":240,"taster_agent_runs":0,
   "monthly_ceiling_micros":5500000,"daily_ceiling_micros":1250000}')
ON CONFLICT (code) DO NOTHING;

INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('hermi_pro_monthly',   'apple', 'pro', 'month', 1199, 'USD', 0, false),     -- set is_active = true at the launch step
('hermi_pro_annual',    'apple', 'pro', 'year',  9900, 'USD', 0, false)
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('tier_pro',                 'Sell and show the Pro tier',              false, 100, '{}', '{}'),
('scheduled_agent_routines', 'Scheduled agent routines (Pro only)',     false, 100, '{"tiers":["pro"]}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO kill_switches (key, description) VALUES
('ai.routines', 'Stop scheduled routines only (manual agent runs keep working)')
ON CONFLICT (key) DO NOTHING;
-- Phase 1 seeds serpapi_live_fares for plus and trip_pass only; Pro gets live tracking too.
UPDATE feature_flags SET rules = jsonb_set(rules, '{tiers}', rules -> 'tiers' || '["pro"]'::jsonb) WHERE key = 'serpapi_live_fares';
-- Notification kinds added to the ck_notifications_kind swap: routine_digest, routine_paused.
```

The launch step is a single audited change in the admin console: `plans.is_active = true` for `pro`,
`store_products.is_active = true` for the two products, `tier_pro` on.

Gate queries (shown on the admin flag screen):

```sql
-- Mean measured cost of the last 200 completed uncached agent runs (target: at most $0.60).
SELECT count(*) AS runs, round(avg(cost_usd_micros) / 1000000.0, 3) AS mean_usd
  FROM (SELECT cost_usd_micros FROM runs
         WHERE kind IN ('fare_hunt', 'deep_research') AND status IN ('succeeded', 'partial')
           AND served_from_cache = false
         ORDER BY finished_at DESC LIMIT 200) r;

-- Share of Plus payers who bought agent-run credit packs in the last 90 days (target: above 15 percent).
WITH plus_payers AS (
  SELECT DISTINCT user_id FROM subscriptions WHERE plan_code = 'plus' AND status IN ('active', 'in_trial', 'in_grace')
), buyers AS (
  SELECT DISTINCT t.user_id FROM store_transactions t
   WHERE t.kind = 'credit_pack' AND t.status = 'purchased' AND t.purchased_at > now() - interval '90 days'
)
SELECT (SELECT count(*) FROM plus_payers p JOIN buyers b USING (user_id))::numeric
       / NULLIF((SELECT count(*) FROM plus_payers), 0) AS share;
```

(The second query counts credit pack buyers; refine it to packs spent on `agent_run` through
`credit_ledger.action` when the ledger has enough history.)

Rollover (07 section 5.5): before each new monthly grant, unspent `monthly` credits of the Pro allowance
convert to an `adjustment` grant (note `rollover`) capped at `plans.limits.credit_rollover_cap` (240);
rolled credits expire at the end of the new period. The `grant_monthly_credits` job implements it with a
`period_key` that makes it idempotent.

## 4. API additions

From [04 section 5.13](../reference-full-spec/04-api-spec.md), verbatim:

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/routines` | viewer | `pro` to see details, others get `[]` | none to `Routine[]` | |
| `POST /trips/{trip_id}/routines` | editor | `pro` | `RoutineCreate` to 201 `Routine` | Scheduled agent routines are a Pro feature. Non-Pro gets 403 `entitlement_required`, reason `routines`. Schedule minimum is daily. The scheduler enqueues due routines; each firing charges the routine's creator 40 credits. A firing with too few credits is skipped and the owner is notified. |
| `GET /routines/{routine_id}` | viewer | `pro` | none to `Routine` | |
| `PATCH /routines/{routine_id}` | creator or owner | versioned | `RoutineUpdate` to `Routine` | |
| `DELETE /routines/{routine_id}` | creator or owner | none | 204 | Cancels queued firings. |
| `POST /routines/{routine_id}/run` | editor | `pro`, `credits(40)` | `Idempotency-Key` to 202 `AgentRun` | Runs now, with `trigger: "manual"`. |

```ts
type RoutineCreate = {
  name: string; kind: "fare_hunt" | "deep_research"; schedule_cron: string; timezone: string
  enabled?: boolean; catch_up?: boolean
  config: { route_ids?: Uuid[]; topic?: string; instructions?: string }
}
type RoutineUpdate = Partial<RoutineCreate> & { version?: number }
type Routine = RoutineCreate & {
  id: Uuid; trip_id: Uuid; version: number; next_run_at: string | null
  last_run: AgentRun | null; owner: Attribution             // routines.owner_user_id
}
```

Additions in this pack:

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /routines/{routine_id}/preview-cost` | editor | `pro` | `{ schedule_cron, kind }` to `{ runs_per_month: number, credits_per_month: { uncached: number, cached: number }, allowance: number }` | The estimate in PRO-1; no side effects. |
| `POST /routines/{routine_id}/resume` | creator or owner | `pro` | none to `Routine` | Clears `paused_reason` when the cause is gone; `409 state_conflict` otherwise with the reason. |
| `GET /trips/{trip_id}/routines/sample` | viewer | none | none to `{ sample: RunOutputs \| null, manual_run: { credits: 40, cached_credits: 8 } }` | The sample from `shared_research_cache` for non-Pro users; no private data. |
| `Routine` fields | | | `paused_reason: string \| null`, `paused_at`, `next_digest_after` | Extends the type above. |

Validation: `schedule_cron` must produce at least 12 hours between slots; at most 3 routines per trip
(`403 limit_reached`, reason `routines`); `route_ids` must belong to the trip; `kind` of `price_check` or
`batch_scan` is reserved for the system. The entitlement error for non-Pro is `403 entitlement_required`
with reason `routines` (the paywall trigger `routine`).

**Scheduler and worker behavior** ([02 sections 5.1 and 5.2](../reference-full-spec/02-architecture.md), [06 section
5.10](../reference-full-spec/06-ai-agents-spec.md)):

- The leader scans `routines.next_run_at` every 30 seconds with `FOR UPDATE SKIP LOCKED`, checks the
  kill switches (`ai.routines`, `ai.agent_runs`, `ai.all`), checks the account budget (reserve in the
  same transaction), inserts a `runs` row (`trigger = 'schedule'`), defers the job in the `ai` lane at
  scheduled priority (scans in the `batch` lane) with stable jitter 0 to 20 minutes, and advances
  `next_run_at` to the next cron slot after now. Missed slots never stack: an outage of a day fires one
  check.
- The scheduler skips `fare_hunt` and `deep_research` routines while `scheduled_agent_routines` is off
  (the Phase 1 behavior) and pauses the routine with `kill_switch` when a switch is engaged.
- Interactive priority is 10, paid scheduled 5, free scheduled 1; Pro runs use a higher base priority with
  aging so nothing starves; per account concurrency cap Pro 8 (Free 2, Plus and Family 4).
- A run is admitted when the month has $0.80 of headroom even if the daily budget is lower; its spend
  still counts toward the day. The daily allowance for scheduled jobs is the monthly headroom divided by
  the days left ([06 section 6.5](../reference-full-spec/06-ai-agents-spec.md)); the app says which routines will run less
  often.
- After a finished run: if results changed, enqueue one digest (throttled by `last_digest_at` to one per
  routine per day); a run that saved nothing and failed for Hermi's reasons refunds its credits.
- Pause rules: balance under 40 (8 when a cache hit is likely) sets `no_credits`; no $0.80 monthly
  headroom sets `ceiling`; trip end date in the past sets `trip_past`; owner entitlement without
  `scheduled_routines` sets `owner_lapsed`.

## 5. UI screens and paywall triggers

1. **Routines** (trip section under Flights and AI activity). For Pro: list of up to 3 routines with
   name, kind, schedule in words ("Every day at 08:00"), status chip (Running, Paused: not enough
   credits), last result and next run; [New routine]. For everyone else (before and after launch): the
   sample result card and "Run once, 40 credits" manual alternative; Pro is named only after launch.
2. **New routine sheet.** Kind (Hunt fares, Research), routes or topic, schedule (every day, every 2
   days, weekly, custom with the 12 hour minimum), time zone, "Catch up after downtime", live credit
   estimate ("About 160 credits a month at this schedule. Your allowance is 240.") and the honesty
   line "Runs use the shared cache first, which costs 8 credits instead of 40."
3. **Routine detail.** Run history with the evidence rows (fares with source and date seen), digest
   settings, [Run now, 40 credits], Pause, Delete, and the pause reason with its fix.
4. **Plan and credits.** Pro appears in Compare plans only after launch: "$11.99 a month or $99 a year,
   240 credits, 6 live routes, scheduled routines, priority queue"; credit balance shows rolled-over
   credits with their expiry.
5. **Notification.** Digest push and email: "Lisbon fare hunt: 2 new fares, lowest $412" (facts, no
   emoji); setting "Routine digests".

States. Loading skeleton rows. Empty (Pro): "No routines yet", "Watch a route or a topic and we will
tell you what changed.", [New routine]. Error: "We could not save this routine. Your other routines
are unchanged." Paused: reason and [Resume]. Offline: read only. No permission: viewers see results, not
controls. Limit: "You have 3 routines on this trip."

Paywall trigger (already in the Phase 1 table, hidden until Pro launches):

| Trigger id | When it fires | Headline | What it gives on this trip | Free path (equal weight) | Leading offer |
|---|---|---|---|---|---|
| `routine` | Start a scheduled agent routine without the Pro tier | "Run this on a schedule" | A sample result from the shared cache, one manual run for 40 credits | "Run once, 40 credits" | Credits, then Pro once launched |

After launch `choose_offering` for `routine` returns the Pro offering with the sample and the manual run
as the free path. Copy never says "unlimited AI" or "unlimited live tracking".

## 6. Monetization and App Store products

| Product ID | Type | Price (US) | Duration | Group and level | Trial | Entitlement |
|---|---|---|---|---|---|---|
| `hermi_pro_monthly` | Auto-renewing subscription | $11.99 | 1 month | `hermi_membership`, level 1 | none | `pro` |
| `hermi_pro_annual` | Auto-renewing subscription | $99.00 | 1 year | `hermi_membership`, level 1 | none | `pro` |

- Products are created in App Store Connect and RevenueCat in month 10 but stay inactive until the gate
  is met and the flag is turned on; they join the `hermi_membership` group at level 1 (above Family 2
  and Plus 3). Submit with an app version; complete metadata and review screenshot.
- Upgrades (Plus or Family to Pro) apply immediately with the difference grant (Plus 60 to Pro 240
  grants 180); downgrades apply at renewal (07 sections 7.3 and 7.4); lapse pauses routines
  (`owner_lapsed`) and keeps data.
- Credits and economics: allowance 240 a month, rollover cap 240, ceiling $5.50 a month and $1.25 a day.
  The pricing model's margin for Pro is thin only if the ceiling is hit every month, which the usage
  pattern makes unlikely ([09 revenue expansion](../context/business-plan/09-revenue-expansion.md) section 2). Scans are
  not sold and run inside the Pro ceiling.
- The launch gate is a business decision, not a date. Record the numbers in the admin flag screen at
  launch. If neither condition is met by the end of Phase 2, Pro stays dark and credit packs carry the
  agent-heavy users; the decision moves to Phase 3.
- Experiments after launch: Pro price test ($99 versus lower) follows the experiment rules (separate
  product ids, at least 4 weeks and 1,000 views per arm).

## 7. Admin additions

- **Feature flags (08 section 6.6).** The `tier_pro` toggle shows both gate numbers (mean cost over the
  last 200 runs and the Plus payer credit-pack share) and blocks enabling until one is met, unless the
  owner overrides with a typed reason; audit entry records the numbers. `scheduled_agent_routines` can be
  staged by rollout percent and tier rule.
- **Users.** Routines list with status, pause reason, next run, last digest; actions: pause or resume a
  routine, cancel queued firings (audited).
- **System health (08 section 6.14).** Scheduler heartbeat, routines overdue, runs by priority, queue age
  per lane, scan versus agent counts, digests sent.
- **Credits and AI spend.** Pro pool and rollover grants in the bucket view; scheduled spend separated
  from manual spend; AI spend alert at 95 percent of the Pro monthly ceiling for any account (notify).
- **Kill switches.** `ai.routines` added; `ai.batch` already pauses scans and digests.
- **Overview.** MRR split includes Pro; revenue by stream; Pro gate card until launch.
- **Alert rules.** Scheduler idle over 3 minutes (page, existing), routine runs per hour above 3 times the
  trailing p95 (notify), a routine that failed 3 runs in a row auto-pauses and lists in admin.

## 8. AI additions

Scheduled work reuses the Phase 1 agents ([06 sections 5.7 and 5.8](../reference-full-spec/06-ai-agents-spec.md)) and adds the
scan and the digest.

- **Scan (`routine_scan`, Batch).** One request per route and window: server tools with 6 searches and 3
  fetches, effort `low`, the fare-hunt system prompt with a shortened task, output through the strict
  quotes schema in structured output (Batch cannot hold a multi-turn loop), then the same `submit_quotes`
  validators including provenance against the result blocks returned in the batch response. Internal stop
  $0.15. `custom_id = scan:{route_id}:{window}:{date}`; `pause_turn` results are resubmitted in the next
  batch. A scan runs when API prices moved by more than 5 percent or the window is under 45 days away,
  not on a fixed clock. Scans are not sold; they run inside the Pro ceiling.
- **Agent routine (`routine_agent`).** Same as a manual `fare_hunt` or `deep_research` with
  `runs.routine_id` set: 20 turns, 10 searches, 10 fetches, hard stop $0.80, 40 credits (8 from shared
  cache), one at a time per account. The evidence rules are unchanged: every fare must have been seen on
  a page during the run, every note links its source URL.
- **Scan prompt guide (verbatim replacement for "How to search"):**

```text
## How to search
- Check this one route and date window only. Use at most {max_searches} searches and
  {max_fetches} fetches.
- Return every fare you can ground on a page that shows specific dates. Return an empty list if
  you find none. Do not estimate.
- Compare with cheapest_known; include a fare only if it is within 15% of it or lower.
```

- **Weekly digest (`digest`).** Haiku 4.5 via Batch, one call per active trip for Plus and above, no web,
  inputs are prices, dates and agent note titles only (06 section 12.1: never names or free-text notes),
  about $0.003 each.
- **Output.** Accepted quotes update `fare_observations` and may trigger `price_alerts`; notes appear under
  "Found by AI" with sources. Evals from Phase 1 cover routines (source present, fares verified,
  injection resistance); add a scan-specific set and a cost report script over 200 runs (needed for the
  gate).
- Kill switches honored: `ai.all`, `ai.agent_runs`, `ai.routines`, `ai.batch`, `provider.anthropic`,
  model routing switches.

## 9. Analytics events

| Event | Properties | When fired |
|---|---|---|
| `routine_created` | `kind` (`fare_hunt`, `deep_research`), `cadence_bucket` (`daily`, `every_2_days`, `weekly`, `custom`), `est_credits_bucket` | Routine saved |
| `routine_run_started` | `kind`, `trigger` (`schedule`, `manual`, `catch_up`), `from_cache` (bool) | Run admitted (server side) |
| `routine_run_finished` | `kind`, `outcome` (`ok`, `partial`, `failed`, `refunded`), `changed` (bool) | Run settled |
| `routine_paused` | `reason` (`routines.paused_reason`) | Pause set |
| `routine_resumed` | `reason_cleared` | Resume |
| `routine_digest_sent` | `channel` | Digest delivered |
| `routine_sample_viewed` | `tier` | Non-Pro sample shown |
| `pro_gate_checked` | `mean_cost_bucket`, `pack_share_bucket`, `passed` (bool) | Admin opens the gate card (server side) |

Existing events used: `paywall_viewed {placement: routine}`, `purchase_started {product: pro}`,
`subscription_started`, `subscription_changed`, `ai_action_started` and `ai_action_completed` with
`feature` values `routine_scan` and `routine_agent`.

## 10. Tests

- Flag matrix: with both flags off nothing is visible and no scheduled agent runs; with `tier_pro` on
  for a test user routines run within ceilings; `scheduled_agent_routines` alone cannot expose Pro.
- Scheduler: stable jitter, no stacking of missed slots, one firing after a one day outage, kill switch
  pauses with reason, advisory-lock leader failover, 5,000 synthetic routines load.
- Budget and pauses: reserve in the same transaction, `no_credits`, `ceiling` and `trip_past` pauses,
  auto resume at month start, refund on failed and nothing-saved runs.
- Priority and concurrency: Pro jumps the queue with aging; per account concurrency cap; one agent run at
  a time per account across manual and scheduled runs (`run_already_active`).
- Validation: 12 hour minimum gap, 3 routines per trip, routes belong to the trip, non-Pro gets
  `entitlement_required` with reason `routines`.
- Scan: strict schema, provenance validators, 15 percent rule, `pause_turn` resubmission, internal stop
  $0.15.
- Digest throttle: at most one per routine per day; quiet hours; no content from private notes.
- Rollover: cap 240, expiry at period end, idempotent grant.
- Purchase matrix: Pro monthly and annual purchase, Plus to Pro upgrade grant of 180, Family to Pro,
  downgrade at renewal, refund clawback, restore, lapse pauses routines.
- Gate: the admin screen blocks enabling until a number passes, override requires a reason and is
  audited.
- Tenant isolation: routines and runs across accounts.

## 11. Tickets

#### P2-055 Routines schema additions and plan seed [S, needs Phase 1 schema]
- Description: migration `0022_pro_routines` (additions above), `pro` plan row, dark products, flags,
  kill switch.
- Accept: empty to head and previous to head pass; with flags off nothing is exposed.

#### P2-056 Routines API and validation [M, needs P2-055]
- Description: CRUD, run now, preview cost, resume, sample endpoint; cron validation with the 12 hour
  gap; per trip limit; entitlement errors.
- Accept: matrix in section 10 passes.
- Touches: `apps/api/hermi/modules/ai/routines.py`.

#### P2-057 Scheduler activation and pause rules [L, needs P2-056, Phase 1 scheduler]
- Description: agent kinds enabled behind `scheduled_agent_routines`, budget reservation, pause reasons
  and auto resume, kill switch handling, catch up.
- Accept: scheduler tests pass; 5,000 synthetic routines load target met.
- Touches: `apps/worker/hermi_worker/scheduler.py`, `jobs/scan_due_routines.py`.

#### P2-058 Scan lane (Batch) [L, needs P2-057]
- Description: `routine_scan` with structured output, validators and provenance, `collect_batch_results`
  handling, `pause_turn` resubmission, internal stop.
- Accept: scan tests pass; scan cost per result reported.

#### P2-059 Priority queue with aging and Pro concurrency [M, needs P2-057]
- Description: priority values, aging, per account cap 8 for Pro, fair claim.
- Accept: no starvation of Plus and Free jobs in simulation.

#### P2-060 Digests and notifications [M, needs P2-057, Phase 1 notifications]
- Description: routine digest (one per routine per day), weekly Haiku digest via Batch for Plus and above,
  settings rows, copy.
- Accept: throttles hold; no private note content sent to Anthropic.

#### P2-061 Routines UI and non-Pro sample [L, needs P2-056]
- Description: Routines list, New routine sheet with credit estimate, detail, pause reasons, sample card,
  states and copy.
- Accept: axe clean; estimate matches the server; no "unlimited" claims.

#### P2-062 Pro plan purchase flow, rollover and lifecycle [L, needs P2-055, Phase 1 RevenueCat webhook]
- Description: activate products behind `tier_pro`, upgrades and downgrades, rollover job, lapse pauses,
  Compare plans and paywall offerings for Pro.
- Accept: purchase matrix in section 10 passes on recorded fixtures.

#### P2-063 Gate tooling and admin [M, needs P2-057]
- Description: cost-per-run report script, gate card and blocking in the flags screen, routine admin
  views, alert rules.
- Accept: gate numbers visible; enabling blocked until met or overridden with a reason.

#### P2-064 Pro launch checklist [S, needs P2-062, P2-063]
- Description: record gate numbers, create and submit App Store products, sandbox matrix, staged rollout
  (staff, 10 percent, 100 percent), pricing page update, support macros.
- Accept: launch happens only with recorded gate numbers; routines run within ceilings during rollout.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Agent cost above $0.60 a run | Gate blocks launch; shared cache first; caps of 20 turns, 10 searches, 10 fetches and $0.80; scans at $0.15 |
| Users expect daily agent runs for 240 credits | Cost estimate before saving, honest copy, cache-first pricing, pause reasons |
| Scheduled load spikes at 08:00 and 20:00 | Stable jitter, lanes, per account caps, priority aging |
| Pro cannibalizes credit packs or Plus | Experiments after launch; gate allows either condition; packs stay on every tier |
| Runaway routines | Hard stops, ceilings, reserve then settle, three failures auto-pause, kill switches |
| Price too high for the market ($99 against rivals at $40 to $50, reported) | Launch only with measured demand; price test with separate product ids; Pro can stay dark |
| Evidence standard slips in scans | Same validators and provenance as manual runs; evals; "Indicative" labels |
