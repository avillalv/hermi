# Database and data integrations

Part of the [business plan](README.md). The decisions of record in the README override anything here.

Written 2026-09-30, updated for Hermi's revenue lanes (Family, Group Trip Pass, concierge, advisors, print, Stripe). Scope: schema, tenancy, migrations, data providers, caching, affiliate tracking, retention. Related files: [02-pricing-tiers.md](02-pricing-tiers.md) (tiers and credits), [03-ai-features-and-costs.md](03-ai-features-and-costs.md) (AI cost and controls), [04-users-and-accounts.md](04-users-and-accounts.md) (sign-in, sharing, deletion), [05-infrastructure.md](05-infrastructure.md) (hosting and jobs), [07-local-to-app-store.md](07-local-to-app-store.md) (purchases and roadmap).

Several provider sites (serpapi.com, geoapify.com, duffel.com) could not be read directly on 2026-09-30, so their pricing and terms come from search summaries. Anything not read on a primary page is labeled "reported, verify" with the date checked.

## 1. Current schema

The app uses Alembic (7 migrations in `backend/tripplanner/migrations/versions/`, applied at `serve` startup after a backup). Every table is single-household: no user or tenant column anywhere. `trips` is the root; almost everything hangs off `trip_id` with `ON DELETE CASCADE`.

| Table | One-line description | Target scope |
|---|---|---|
| `people` | Two named travelers (name, color, home airports) | Kept. Gains `owner_user_id` and `linked_user_id` |
| `trips` | Trip root: name, status, home currency, notes | Tenant (owned by a user, shared via `trip_members`) |
| `trip_travelers` | Association trip to people | Tenant, unchanged |
| `trip_destinations` | Destinations with Geoapify id, bbox, Wikipedia summary and image | Tenant row; enrichment fields come from the shared cache |
| `flight_routes` | A watched route: origin and destination code arrays, pax, cabin, sources, alert price, chosen quote | Tenant (trip) |
| `flight_quotes` | One observed fare per check (price, currency, airline, booking URL, dedupe_key, raw JSONB) | Tenant view over a shared observation (2.6) |
| `route_price_insights` | Google price level, typical range, history JSONB per route | Shared (keyed by market, not trip) |
| `fx_rates` | EUR-based rates from Frankfurter | Global |
| `airports` | OurAirports seed (IATA, name, city, country, kind) | Global reference |
| `itinerary_days` | Per-trip day title, notes, destination | Tenant |
| `activities` | Itinerary items with place provider, id, data JSONB, optimistic `version` | Tenant |
| `places_cache` | Key to response JSONB with `expires_at` (Geoapify, Wikipedia, SerpApi rentals) | Global; becomes `shared_research_cache` |
| `lodging_options` | Candidate stays with URL, price, photos, notes, status; unique per trip and normalized URL | Tenant |
| `lodging_votes` | Person votes on lodging | Tenant |
| `routines` | Scheduled jobs per trip (cron, timezone, config) | Tenant |
| `runs` | One agent or check execution (status, prompt, report, cost_usd_est, log_path) | Tenant |
| `run_events` | Streamed events per run | Tenant (high volume, partition or TTL) |
| `agent_notes` | Findings the agent saved to a trip with sources | Tenant |
| `ingest_rejections` | Agent output rejected by validation | Tenant (or ops only) |
| `api_calls` | Provider, endpoint, units, cached, ok, status_code, timestamp; used by the SerpApi budget | Global ops ledger; gains account attribution (2.5) |
| `app_settings` | Key/value JSONB (SerpApi cap, account sync) | Split: global config vs per-user prefs |
| `worker_heartbeat` | Single-row worker liveness | Global ops |

Observations that shape the design:
- `flight_quotes` stores `price_home` and `home_currency` per row. That is per-user presentation data mixed into a provider observation. Convert at read time, or keep it as a derived column on the tenant side only.
- `flight_quotes.raw` and `lodging_options.raw` hold provider payloads. Storing raw SerpApi or Google payloads long term is a terms risk (section 4), so retention is short.
- `run_events` and `runs.report` are the biggest growth tables at scale and need retention (section 7).
- `places_cache` already proves the pattern (hash key, provider, JSONB, TTL). Generalize it instead of inventing a second cache.

## 2. Target schema

### 2.1 Tenancy model

The tenant is the **user account**, and **trips are shared through membership**. Two narrow group structures sit beside that, and neither grants access to trips by itself: `households` (a Family plan pool, up to 6 people, section 2.9) and `advisor_orgs` (Hermi for Advisors, section 2.10). A "household" of two people planning one trip is still just a trip with two members.

The existing `people` table stays. A person is a traveler on a trip even if they never sign in (a child, a friend). It gains two columns, and access control moves to a new `trip_members` table:

- `people.owner_user_id`: the account that created and manages this person row.
- `people.linked_user_id`: set when the person is a real account (an invitee who joined, or the owner's own profile person). Null for travelers without accounts.
- `trip_members` decides who can open a trip. `people` and `trip_travelers` describe who is travelling. The two are joined only through `people.linked_user_id`.

Scoping rule for every table:
- **Global (no tenant column):** `airports`, `fx_rates`, `shared_research_cache`, `fare_observations`, `route_price_insights`, `partner_guides` (public once live), the plan catalog.
- **Trip-scoped (access via `trip_members`):** everything that today has `trip_id`, plus `polls`, `poll_votes`, `expenses`, `expense_shares`, `settlements`, `concierge_requests` and `room_block_requests` (the last two visible only to the requester and the trip owner). Do not add `user_id` to these; check membership through the trip. Keeping `trip_id` on children keeps queries and RLS policies cheap.
- **Account-scoped:** `users`, `people` (by `owner_user_id`), `user_devices`, `subscriptions`, `trip_passes`, `entitlements`, `store_transactions`, `print_orders`, `ai_usage`, `credit_grants`, `user_prefs`.
- **Household-scoped:** `households`, `household_members`, and the pooled `credit_grants` row. **Org-scoped:** `advisor_orgs`, `advisor_seats`, `advisor_clients`.

### 2.2 Identity and sharing tables

Sign-in is Supabase Auth only (Sign in with Apple, Google, email code). Our own `users` table lives in our own Postgres and holds the Supabase user id; see [04-users-and-accounts.md](04-users-and-accounts.md).

```sql
users (
  id uuid pk default gen_random_uuid(),
  auth_subject text unique,         /* Supabase Auth user id (JWT sub) */
  email text, email_is_relay bool,  /* Apple private relay is common */
  display_name text, home_currency char(3), locale text,
  created_at timestamptz, deleted_at timestamptz  /* soft delete then hard purge */
)
people (                            /* existing table, two new columns */
  id, name, color, home_airports,
  owner_user_id uuid references users,   /* not null after backfill */
  linked_user_id uuid references users null,
  unique (owner_user_id, linked_user_id)
)
user_devices (id, user_id fk, apns_token, platform, last_seen_at)  /* push for fare alerts */
trip_members (
  trip_id fk, user_id fk, role text check (role in ('owner','editor','viewer')),
  joined_at, primary key (trip_id, user_id)
)
invites (
  id, trip_id fk, invited_by fk users, token_hash text unique,  /* store hash only */
  role text, email text null, expires_at, accepted_by fk users null, accepted_at
)
```
- Joining a trip creates a `trip_members` row and, if the user has no person row yet, a `people` row with `linked_user_id` set, plus a `trip_travelers` row. Existing `trip_travelers` rows and `lodging_votes.person_id` keep working unchanged.
- Example, "who is on this trip and which of them have accounts":
  ```sql
  select p.id, p.name, p.linked_user_id, m.role
  from trip_travelers tt
  join people p on p.id = tt.person_id
  left join trip_members m on m.trip_id = tt.trip_id and m.user_id = p.linked_user_id
  where tt.trip_id = :trip_id;
  ```
- Add `owner_user_id` to `trips` for the free-tier trip limit (2 active) and for billing attribution. Only the trip owner pays; invitees join free and get the owner's tier on that trip.
- Invites use link tokens (Universal Links on iOS); store only a hash, 7 day expiry, single use.

### 2.3 Subscriptions, Trip Pass and entitlements

Apple is the source of truth. Sync through **RevenueCat webhooks** over StoreKit 2 (it handles receipt validation, grace periods, refunds, and Android later), with our own tables as a read model. Products: Plus and Family, each monthly and annual (7-day trial on annual only, one subscription group), Trip Pass and Group Trip Pass (non-renewing), three credit packs. Pro (formerly Premium) is built behind a flag and launches later (see [02-pricing-tiers.md](02-pricing-tiers.md)).

```sql
subscriptions (                   /* Plus and Family now; Pro rows only once the flag is on */
  id, user_id fk, provider text default 'revenuecat',
  original_transaction_id text unique, product_id text,
  tier text check (tier in ('plus','family','pro')),
  household_id uuid null,        /* set for family: the payer's subscription backs this household */
  status text,   /* active, in_grace, billing_retry, expired, refunded, revoked */
  period_start, period_end, auto_renew bool, environment text,  /* sandbox | production */
  last_event_at, raw_last_event jsonb
)
trip_passes (                     /* non-renewing subscription in StoreKit, bound to a trip here */
  id, trip_id fk, purchaser_user_id fk, original_transaction_id text unique,
  pass_type text default 'trip',  /* 'trip' or 'group' (Group Trip Pass) */
  travelers_max smallint,         /* 6 collaborators for trip, 12 travelers for group */
  credits_total smallint,         /* 40 for trip, 80 for group */
  starts_at, expires_at,          /* 90 days */
  live_routes_max smallint default 2, live_checks_max smallint default 60,
  live_checks_used smallint default 0, collaborators_max smallint default 6,
  status text                     /* active, expired, refunded */
)
entitlements (
  user_id pk fk, tier text default 'free', source_subscription_id fk null,
  valid_until timestamptz,
  limits jsonb,   /* snapshot: active_trips, live_routes, credits_per_month, collaborators */
  updated_at
)
webhook_events (id text pk /* provider event id */, provider, /* revenuecat, stripe */ received_at, processed_at, payload jsonb)
store_transactions (              /* immutable purchase ledger across Apple and Stripe */
  id uuid pk, user_id fk, provider text,           /* 'apple' | 'stripe' */
  kind text,                                       /* subscription, non_renewing, consumable, one_time, invoice, refund */
  product_id text, provider_txn_id text, original_txn_id text null,
  amount_minor bigint, currency char(3), tax_minor bigint default 0,
  status text,                                     /* completed, refunded, disputed, reversed */
  trip_id fk null, household_id fk null, advisor_org_id fk null,
  print_order_id fk null, settlement_id fk null,   /* what the money was for, one of these */
  environment text, occurred_at timestamptz, raw jsonb,
  unique (provider, provider_txn_id)
)
```
- `store_transactions` is the record that grants, passes, print orders and advisor invoices point back to, and it is what refunds and finance reports read. It is append-only apart from `status`. `subscriptions` stays the current-state read model; this table is the history. Apple rows come from RevenueCat, Stripe rows from the `stripe_event` job ([05-infrastructure.md](05-infrastructure.md) section 5.6).
- **Effective tier on a trip** is the higher of the owner's tier and any active `trip_passes` row for that trip. Invitees are evaluated against the trip owner, never their own tier, for trip features (live routes, collaborators).
- Limits by tier (from the README): Free 2 active trips, 1 cached-fare route per trip, 12 credits a month, one lifetime deep agent run (taster), 1 alert on cached fares. Plus unlimited trips (fair use 25), 3 live routes checked daily within 120 days of departure, 60 credits a month. Family is Plus for up to 6 household members with 150 pooled credits and 5 live routes. Trip Pass 2 live routes, at most 60 live checks, 40 credits, up to 6 collaborators, 90 days. Group Trip Pass the same shape with up to 12 travelers, 80 credits, polls, cost splitting and the room-block request. Pro (flagged off) 6 live routes, 240 credits a month.
- A Family member's `entitlements` row is derived from `household_members` (active) and the household's subscription, so leaving a household changes one row and the tier follows.
- The pass is bound to the trip on the server: the purchase flow sends `trip_id`, the webhook writes `trip_passes`, and a pass cannot move to another trip.
- `webhook_events.id` as primary key gives idempotency: insert first, skip on conflict.
- The backend reads `entitlements` and `trip_passes` only and never calls Apple on a request. A nightly reconcile job re-pulls RevenueCat for users whose `valid_until` is near.
- `limits jsonb` is derived from a plan constant in code, so changing a quota needs no migration.

### 2.4 AI credit ledger

**One credit is a budget of up to $0.02 of provider spend** (Claude, SerpApi, Geoapify). Users are charged a fixed number of credits per action, not per token:

| Action | Credits |
|---|---|
| Haiku explain | 1 |
| Live flight or rental search | 1 |
| Itinerary day | 1 |
| Whole-trip draft | 4 |
| Research question | 8 (1 if served from the shared cache) |
| Deep agent run | 40 (8 from the shared cache), hard stop at $0.80. Free gets one lifetime taster run, shared cache first |

Two tables hold usage, plus a grants table:

```sql
ai_usage (                              /* append-only, partition by month */
  id bigint identity, user_id fk, trip_id fk null, run_id uuid null,
  feature text,                          /* 'explain','search','itinerary_day','trip_draft','research','agent_run' */
  model text, input_tokens int, output_tokens int,
  cache_read_tokens int, cache_write_tokens int, via_batch bool default false,
  cost_usd_micros bigint,                /* what it cost us: Claude plus provider calls */
  credits_reserved int, credits_charged int,
  state text,                            /* 'reserved','settled','released' */
  cache_hit bool default false,          /* shared research cache: charged 1 credit */
  idempotency_key text unique, created_at timestamptz, settled_at timestamptz
)
credit_grants (
  id, user_id fk null, household_id fk null,    /* exactly one of the two; household for Family's pooled 150 */
  kind text,                             /* 'monthly','household','trip_pass','purchase','promo','taster' */
  credits int, remaining int, trip_id fk null,   /* trip_pass grants only spend on that trip */
  expires_at, source_txn text
)
```
- **Reserve, then settle.** Before an action starts, reserve its full credit price in one atomic statement (`UPDATE credit_grants ... WHERE remaining >= :n`, spending in the order below) and insert an `ai_usage` row in state `reserved`. When the work finishes, settle: mark `settled`, set `credits_charged`, and record `cost_usd_micros`. If the action fails before delivering a result, mark it `released` and return the credits. A sweeper releases reservations older than the run cap (agent runs cap at 20 turns and $0.80). This prevents overspend under concurrency without long locks.
- **Spend order:** monthly grants first, then Trip Pass grants (for that trip), then purchased packs last. Purchased credits last 12 months (packs: 50, 150, 400).
- Monthly reset is a new grant row (Free 12, Plus 60, Family 150 to the household), never a mutation of history. Purchased packs are always personal, never pooled. `credit_ledger` holds the append-only deltas (grant, reserve, settle, release, expire) with `user_id`, `household_id` when pooled, `grant_id` and `ai_usage_id`, so who spent what from a pool is always visible; the per-member share cap (60 percent of the pool) is checked against it inside the reserve statement. Balance is `sum(remaining)` over unexpired grants, which is cheap because each user has a handful of rows.
- **Who pays:** the account that starts the action. On a shared trip, an invitee's AI actions spend the invitee's credits. A Family member spends the household pool first. A pass's credits spend only on its trip.
- `cost_usd_micros` against `credits_charged * 20000` is the margin check: if settled cost regularly exceeds the $0.02 unit per credit, the prices in [02-pricing-tiers.md](02-pricing-tiers.md) are wrong. Deep agent runs and research questions enforce their own hard stops ($0.80 and $0.16) inside the worker, see [03-ai-features-and-costs.md](03-ai-features-and-costs.md).
- `runs.cost_usd_est` stays as an operational number; `ai_usage` is the billing-grade record.

### 2.5 Provider call ledger and account ceilings

Rename and extend `api_calls` to `provider_calls`, keeping the existing columns so `serpapi_budget.py` keeps working during the transition.

```sql
provider_calls (
  id bigint identity, provider text, endpoint text,
  user_id uuid null, trip_id int null, run_id uuid null,
  units numeric default 1, cost_usd_micros bigint null,   /* our cost for the call */
  cached bool, cache_layer text null,   /* 'db','memory','provider' */
  ok bool, status_code int, latency_ms int,
  request_hash text,                    /* the cache key, for dedup analytics */
  created_at timestamptz
) partition by range (created_at);      /* monthly */
create index on provider_calls (provider, created_at);
create index on provider_calls (user_id, provider, created_at);
```
The quota manager has three scopes:
1. **Global provider cap** from the plan we pay for (replaces the constant 240; keep the daily fair-share logic in `serpapi_budget.py`).
2. **Per-account provider-spend ceiling**, summed from `provider_calls.cost_usd_micros` and `ai_usage.cost_usd_micros` for the acting account:

   | Tier | Monthly ceiling | Daily ceiling |
   |---|---|---|
   | Free | $0.25 | $0.05 |
   | Plus | $2.25 | $0.40 |
   | Family | $3.40 pooled per household | $0.40 pooled |
   | Trip Pass | $1.80 per pass | $0.40 |
   | Group Trip Pass | $3.60 per pass | $0.40 |
   | Pro (later) | $5.50 | $1.25 |

   Cached data keeps working when a ceiling is hit. A credit balance never overrides a ceiling.
3. **Credit reservation** (2.4), checked first because it is the user-visible limit.

Counting with `sum(cost_usd_micros)` over one month partition is fine to about 1M rows a month. Until Redis is added (about 10k MAU) keep counters in Postgres and reconcile from this table; after that, hot counters can live in Redis. Rows with `cached=true` stay because the cache hit rate is the key business metric.

### 2.6 Shared caches and fare observations

**`shared_research_cache`** (generalized `places_cache`):
```sql
shared_research_cache (
  key char(64) pk,              /* sha256 of normalized request */
  kind text,                    /* 'geo_search','wiki','rentals','ai_research','destination_brief' */
  provider text, params jsonb,  /* normalized input, for debugging and invalidation */
  response jsonb, response_bytes int,
  fetched_at, expires_at, stale_until,   /* stale-while-revalidate window */
  hit_count int default 0, last_hit_at,
  model text null, prompt_version text null   /* AI entries: bump version to invalidate */
)
create index on shared_research_cache (kind, expires_at);
```
AI research entries hold only content derived from public facts (destination briefs, "best areas to stay", visa-free summaries), never a user's private notes or trip data. Key on normalized destination, month and prompt version, never on user text. A hit on a research question costs the user 1 credit instead of 8. The batch API warms this cache offline (see [03-ai-features-and-costs.md](03-ai-features-and-costs.md)).

**`fare_observations`** (the main dedup win; the source of truth instead of per-trip copies):
```sql
fare_observations (
  id bigint identity,
  origin char(3), destination char(3),            /* single airports; multi-airport routes expand */
  depart_date date, return_date date null,
  cabin text, adults smallint, children smallint, stops_max smallint,
  source text, confidence text,                    /* 'serpapi_live' | 'travelpayouts_cache' */
  currency char(3), price_total numeric(12,2),
  airlines text[], stops smallint, duration_min int,
  deep_link_template text,                         /* provider link, wrapped at click time */
  observed_at timestamptz, expires_at timestamptz,
  search_key char(64)                              /* hash of the full normalized query */
) partition by range (observed_at);
create index on fare_observations (origin, destination, depart_date, return_date, cabin, observed_at desc);
create unique index on fare_observations (search_key, source, observed_at);
```
- `flight_quotes` becomes a thin tenant table: `route_id`, `observation_id`, and the user-specific fields (`hidden`, `suspect`, `price_home`, chosen flag). A quote row costs a few dozen bytes instead of a JSONB blob.
- Lookup order for a route check: (1) a fresh `fare_observations` row for `search_key` within TTL, (2) Travelpayouts cache (free), (3) a live provider (SerpApi behind its flag, later a licensed source) only if the route is live-tracked for that trip, the account is under its ceiling, and no fresh observation exists. Step 1 turns 1,000 users watching LHR to JFK next June into one live call per TTL window.
- Free-tier routes and alerts use cached fares only. Live routes are a Plus or Trip Pass feature; a live search or check costs 1 credit and counts toward the Trip Pass 60-check limit (`live_checks_used`).
- Redistribution caveat: sharing an observation between users of our own app is internal reuse, but show it as "price seen at [time] from [source]", never as a bookable guarantee (see section 4).

### 2.7 Tenant columns and indexes

| Table | Change |
|---|---|
| `trips` | add `owner_user_id uuid not null`, index `(owner_user_id, status)`, `deleted_at`, and nullable `advisor_org_id` for trips created in an advisor workspace |
| `trip_members` (advisor rows) | add nullable `advisor_org_id`; an advisor is an `editor` row carrying it |
| `people` | add `owner_user_id`, `linked_user_id`; index `(linked_user_id)` |
| `trip_members` | pk `(trip_id, user_id)`, secondary index `(user_id, trip_id)` (the "my trips" query) |
| all trip-child tables | keep `trip_id` index; add composite indexes where lists are sorted, for example `(trip_id, created_at desc)` |
| `routines` | add `owner_user_id` (who is billed for the checks) and `kind` (`price_check`, `batch_scan`, `agent`); the `agent` kind is rejected until Pro launches; index `(enabled, next_run_at)` |
| `runs` | add `user_id`; index `(user_id, queued_at desc)`; partition or TTL for `run_events` |
| `api_calls` to `provider_calls` | as above |
| `app_settings` | keep for global config; move per-user settings to `user_prefs (user_id, key, value)` |

Add an opaque UUID `public_id` (UUIDv7) to `trips` and other exposed entities before launch. Sequential integer ids in URLs and API paths invite enumeration, and non-colliding ids make merging or sharding later easier. Internal joins can keep bigint identity; expose only `public_id`.

### 2.8 Row-level security: yes, as a second layer

Enable Postgres RLS on all tenant tables, but do not rely on it alone. Application-level authorization (a dependency that loads the trip and checks membership) stays the primary control.

Why:
- One missing `WHERE trip_id IN (...)` in a future endpoint is the most likely cause of a cross-tenant leak. RLS turns that into an empty result instead of an incident.
- Policies are short because every child table has `trip_id`.

```sql
alter table activities enable row level security;
alter table activities force row level security;
create policy tenant_isolation on activities
  using (trip_id in (select trip_id from trip_members where user_id = current_setting('app.user_id')::uuid));

create policy owner_or_shared on people
  using (owner_user_id = current_setting('app.user_id')::uuid
         or id in (select person_id from trip_travelers
                   where trip_id in (select visible_trip_ids())));
```
Per request, the app runs `SET LOCAL app.user_id = '<uuid>'` inside the transaction (this works with PgBouncer transaction pooling because it is `LOCAL`). Workers and admin jobs use a separate role with `BYPASSRLS` and must set trip and user context explicitly.

Costs and mitigations:
- A policy subquery per row can slow scans. Use the `(user_id, trip_id)` index on `trip_members` and a `SECURITY DEFINER` helper `visible_trip_ids()` marked `STABLE`.
- The test suite must run once as a restricted role (pytest today runs as owner, which silently bypasses RLS). Add a "tenant A cannot see tenant B" test per table, generated from `Base.metadata`.
- Global tables get no RLS, but the app role gets `SELECT` only on them; writes go through the worker role.

### 2.9 Households and group trips

```sql
households (
  id uuid pk, name text,
  payer_user_id uuid references users,          /* holds the Family subscription */
  subscription_id fk null,
  status text check (status in ('active','grace','ended')),
  member_limit smallint default 6,
  member_share_cap_pct smallint default 60,     /* max share of the pool one member may spend */
  created_at, ended_at
)
household_members (
  household_id fk, user_id fk,
  role text check (role in ('payer','member')),
  status text check (status in ('invited','active','left','removed')),
  invited_by fk users, invite_token_hash text null,
  joined_at, left_at,
  primary key (household_id, user_id)
)
create unique index one_active_household on household_members (user_id) where status = 'active';
```
- The 6-member limit, the 30 day cooldown after leaving (read from `left_at`) and the cap of 4 membership changes per rolling 30 days are enforced in the service in one transaction, backed by the partial unique index so a race cannot put someone in two households. Rules: [04-users-and-accounts.md](04-users-and-accounts.md) section 3.6.
- RLS: a member sees their own household and its active members' display names and usage totals, nothing of their trips. Only the payer can write.

```sql
polls (
  id uuid pk, trip_id fk, created_by fk users,
  question text, kind text,                     /* single, multi, date, place */
  options jsonb,                                /* [{id, label, ref}] where ref can point to a lodging option or place */
  status text check (status in ('open','closed')), closes_at null,
  winning_option_id text null, created_at
)
poll_votes (
  poll_id fk, person_id fk,                     /* a traveler, with or without an account */
  voted_by fk users null,                       /* the account that cast it */
  option_id text, created_at,
  primary key (poll_id, person_id, option_id)
)
expenses (
  id uuid pk, trip_id fk, created_by fk users,
  paid_by_person_id fk people, description text, category text,
  amount_minor bigint, currency char(3),
  trip_amount_minor bigint null, fx_rate numeric null,   /* converted to the trip currency at entry */
  split_mode text,                              /* equal, shares, exact, percent */
  incurred_on date, status text default 'active', /* active, voided */
  created_at, version int                       /* optimistic concurrency like activities */
)
expense_shares (
  expense_id fk, person_id fk, share_minor bigint, primary key (expense_id, person_id)
)
settlements (
  id uuid pk, trip_id fk,
  from_person_id fk, to_person_id fk,
  amount_minor bigint, currency char(3),
  method text,                                  /* manual, stripe, written_off */
  status text,                                  /* proposed, pending, paid, failed, written_off */
  stripe_payment_intent text null, store_transaction_id fk null,
  created_by fk users, settled_at null, created_at
)
```
- Polls and expenses belong to a trip with an active Group Trip Pass (enforced by `trip_capabilities`). Balances are computed from `expense_shares` minus `settlements`, never stored. After the pass expires the rows stay readable and exportable and only settling stays writable ([04-users-and-accounts.md](04-users-and-accounts.md) section 3.7).
- Money is integer minor units plus currency, like every other money column. Stripe collection is a phase 4 feature and needs a legal decision first ([05-infrastructure.md](05-infrastructure.md) section 5.6); until then `method` is `manual` or `written_off`.

### 2.10 Concierge, room blocks, guides, print and advisors

```sql
concierge_requests (
  id uuid pk, trip_id fk, requester_user_id fk users,
  kind text,                                    /* stay, cruise, complex_trip, other */
  status text,                                  /* submitted, in_progress, quoted, booked, cancelled, closed */
  payload jsonb, payload_hash text,             /* exactly what the user consented to share */
  consent_id fk consents,
  host_agency text, supplier text null, booking_ref text null,
  booking_value_minor bigint null, commission_minor bigint null, currency char(3) null,
  commission_status text null,                  /* pending, confirmed, paid, reversed */
  perks text null, travel_date date null, purge_after date,   /* 13 months after travel */
  created_at, updated_at
)
room_block_requests (
  id uuid pk, trip_id fk, requester_user_id fk users, consent_id fk consents,
  destination text, check_in date, check_out date, rooms smallint, group_size smallint,
  budget_minor bigint null, currency char(3) null, contact_email text,
  status text, host_agency text, hotel_name text null, booking_ref text null,
  commission_minor bigint null, commission_status text null,
  payload_hash text, purge_after date, created_at, updated_at
)
partner_guides (
  id uuid pk, partner_name text, partner_type text,   /* tourism_board, hotel_brand, other */
  destination_ref text, title text, slug text unique,
  body_key text,                                /* R2 key of the authored guide */
  sponsor_label text, disclosure_text text,     /* "Sponsored by ..." shown on every page */
  status text,                                  /* draft, live, ended */
  starts_at, ends_at, fee_minor bigint null, currency char(3) null,
  store_transaction_id fk null, created_at
)
print_orders (
  id uuid pk, user_id fk, trip_id fk,
  product text,                                 /* trip_book, poster */
  options jsonb, pdf_key text null,
  status text,                                  /* draft, paid, rendering, submitted, in_production, shipped, delivered, failed, refunded */
  vendor text, vendor_order_id text null, tracking_url text null,
  shipping_address jsonb, address_purge_after date null,
  subtotal_minor bigint, shipping_minor bigint, tax_minor bigint, total_minor bigint, currency char(3),
  stripe_checkout_session text unique, store_transaction_id fk null,
  created_at, paid_at, shipped_at, delivered_at
)
advisor_orgs (
  id uuid pk, name text, owner_user_id fk users,
  stripe_customer text unique, stripe_subscription text null,
  billing_interval text,                        /* month, year */
  status text,                                  /* trialing, active, past_due, read_only, cancelled */
  branding jsonb, created_at
)
advisor_seats (
  id uuid pk, org_id fk, user_id fk null, email text,
  role text check (role in ('owner','advisor')),
  status text check (status in ('invited','active','ended')),
  invited_at, activated_at, ended_at
)
advisor_clients (
  id uuid pk, org_id fk, advisor_seat_id fk,
  client_user_id fk null, client_email text,
  status text check (status in ('invited','active','ended')),
  consent_id fk consents null, private_notes text,   /* org-private, never returned to the client */
  created_at, ended_at,
  unique (org_id, advisor_seat_id, client_email)
)
```
- **Concierge and room blocks** are a small human work queue, not a booking system. The payload is a snapshot of what the user saw and agreed to share ([04-users-and-accounts.md](04-users-and-accounts.md) section 3.9), and `purge_after` drives the retention job. Commission fields are filled from the host agency's statement and are deliberately separate from `affiliate_conversions`, which are click-matched.
- **Partner guides** are labeled content. They are never joined into ranked lists or search results, and no column carries a ranking weight; the placement rule is a product rule tested in the ranking code.
- **Print orders** hold a shipping address, which is personal data: it is purged 90 days after delivery and never copied into logs or analytics.
- **Advisor tables**: access to a client trip is always through `trip_members` (the advisor's `editor` row with `advisor_org_id`). `advisor_clients` records the relationship and consent; it does not open any trip. `private_notes` and commission tracking are org-scoped with RLS on `org_id` via `advisor_seats`, and are never exposed on a client-facing route. A seat whose `status='ended'`, or an org whose status is `cancelled`, resolves to no advisor rows in `trip_members` at query time, so access ends at once.
- RLS for this group: requests visible to the requester and trip owner; `print_orders` to the owner; advisor tables to active seats of the org, with `advisor_clients` narrowed to the seat holder unless the org owner is viewing the roster; `partner_guides` readable by all once `live`.

## 3. Migration strategy

Postgres is managed by Render with point-in-time recovery (see [05-infrastructure.md](05-infrastructure.md)). Migrations stay in Alembic.

### 3.1 The existing household becomes the first account

1. **Expand.** Migration `0008_users_and_tenancy`: create `users`, `trip_members`, `invites`, `subscriptions`, `trip_passes`, `entitlements`, ledgers. Add nullable `owner_user_id` to `trips`, `people`, `runs`, `routines`, and nullable `linked_user_id` to `people`. No behavior change; the local app keeps working.
2. **Backfill** (separate idempotent revision, in batches). Create `users` rows for the two existing people (emails from config or prompted at first login). Set `people.owner_user_id` to the primary user and `people.linked_user_id` to each person's own user. Set every existing trip's `owner_user_id` to the primary user and insert `trip_members` rows for both (owner and editor). `trip_travelers` is left as is. Fold existing `flight_quotes` into `fare_observations` only when `source` is a provider, dropping or trimming `raw`. Keep the original quote rows during a soak period.
3. **Contract.** After the backfill is verified: `SET NOT NULL` via a `NOT VALID` check constraint then `VALIDATE CONSTRAINT` (no long lock), then enable RLS.
4. **Account claiming.** On first sign-in, if the email or a one-time claim code matches the legacy household, attach the `users` row to it. For a personal install this can be a CLI command: `trip-planner claim-household --email ...`. If the hosted service starts empty and the founders simply import their trips, use the JSON export and import path instead (export is also a user feature).
5. **Cutover.** Restore the local dump into managed Postgres (`pg_dump --format=custom`, `pg_restore`), run migrations, run the backfill, verify row counts per table, then flip.

### 3.2 Zero-downtime rules for every later migration

Add these as a checklist in `.claude/rules/database-migrations.md` (the maintainer decides whether to add):
- **Expand, migrate, contract.** Never rename or drop a column in the same release that stops using it. Two deploys minimum.
- New columns are nullable or have constant defaults (instant on Postgres 11+). Backfill in batches of about 5,000 rows outside the DDL transaction.
- `CREATE INDEX CONCURRENTLY`; in Alembic use `op.get_context().autocommit_block()`.
- Add foreign keys and checks `NOT VALID`, then `VALIDATE CONSTRAINT` separately.
- Set `lock_timeout = '3s'` and `statement_timeout` in migration sessions; retry on lock timeout instead of queueing behind a long query.
- Migrations run as a **pre-deploy step**, one job before the new API and worker start, not at server start. Startup migration is right for a desktop install and wrong for several replicas racing. Use `pg_advisory_lock` as a guard regardless.
- Old and new app versions must both work against the intermediate schema. CI test: run the previous release's tests against the new schema.
- Partition `run_events`, `provider_calls`, `ai_usage`, `fare_observations` by month at creation; retire old data by dropping partitions.
- Render Postgres has no branching, so test risky migrations against a restored copy of the latest backup.

The `CLAUDE.md` rule still applies: read `.claude/rules/database-migrations.md` before any model or migration change, and run `npm run gen:api` after API schema changes.

### 3.3 Schema work by roadmap phase

| Phase | Schema work |
|---|---|
| M0: validate | None. Waitlist data lives outside the app database. |
| 0: foundations | Move to Postgres with the pre-deploy migration job. `provider_calls`, `ai_usage` metering (with `user_id` nullable until phase 1), `shared_research_cache`. |
| 1: hosted web beta | Migration `0008` and backfill, `users`, `trip_members`, `invites`, `entitlements`, `credit_grants`, `fare_observations`, RLS with restricted-role tests, account ceilings. |
| 1: hosted web beta (affiliate part) | `affiliate_programs`, `link_clicks` and the `/go/<click_id>` redirect from the start, so clicks are logged before the iOS app exists. |
| 2: iOS TestFlight | `user_devices`, `subscriptions`, `trip_passes` (with `pass_type`), `webhook_events`, `store_transactions`, credit pack grants, `households` and `household_members`, `polls`, `poll_votes`, `expenses`, `expense_shares`, `settlements`, data export, `checklist_items`. The `concierge_requests` and `room_block_requests` tables are created here too, behind a flag until the host agency is signed. |
| 3: public launch | Account deletion purge job, retention jobs (including concierge and print purges), monthly restore drill, nightly `affiliate_conversions` import per network. Concierge and room-block requests go live in phase 3 if the host agency is signed, otherwise phase 4. |
| 4: growth | Stripe live (group payment collection, `settlements` via Stripe), `advisor_orgs`, `advisor_seats`, `advisor_clients` and the advisor role marker on `trips` and `trip_members`, `print_orders`, `partner_guides`; Pro flag on (`pro` subscriptions, agent routines), Redis counters, `public_id` pages for shared trips, self-hosted places at scale, Android products. |

## 4. Data provider review

Confidence legend: **V** = read on a primary source; **S** = secondary source or search summary (reported, verify); **U** = unverified (site blocked or not found). Everything other than V was checked on 2026-09-30 and must be verified before launch.

| Provider | Used for | Current plan | Paid pricing | Cost per call | Commercial use and redistribution | Confidence |
|---|---|---|---|---|---|---|
| SerpApi (Google Flights, Google Hotels rentals) | Live fares, price insights, rentals | Free, 250/mo (app caps at 240) | Starter $25 (1,000), Developer $75 (5,000), Production $150 (15,000), Big Data $275 (30,000), Searcher $725 (100k), Volume $1,475 (250k) | $0.015 to $0.025 at low tiers, about $0.0072 at 100k, $0.0059 at 250k | API use is allowed; Google's content rights are the open question (4.1) | S, reported, verify (2026-09-30) |
| Travelpayouts / Aviasales Data API | Cached cheapest fares; also the launch affiliate network (flights, Booking.com, Agoda, Trip.com and Hostelworld stays, cars, transfers, tours, eSIM, insurance) | Data API token (free) | Free; earns commission | $0 | Data API reported open with no MAU threshold; Search API reported to need 50,000 MAU and conversion targets | S, reported, verify (2026-09-30) |
| Geoapify | Autocomplete, geocoding, places | Free 3,000 request credits a day | API 10 $59/mo (10k/day), API 25 $109, API 50 $179, API 100 $299, API 250 $609, Custom from $860 | About $0.0002 to $0.002 per request depending on plan | Free plan is for testing and small use with attribution; storage and caching rules not verified | S and U |
| Wikipedia, Wikidata, Commons | Destination summaries and hero images | Public API, no key | Free; Wikimedia Enterprise for high-volume commercial reuse | $0 | Text CC BY-SA 4.0 (attribution and share-alike); images have per-file licenses; identifying User-Agent required | V (Wikimedia docs via search summary) |
| Frankfurter | FX (ECB reference rates) | Free, no key | Free, self-hostable | $0 | Open for commercial use | S |
| Link previews (`providers/link_preview.py`) | Title, description, photo of a pasted URL, user-initiated | Direct fetch of the user's URL | n/a | $0 | User-initiated only. **Must be disabled for airbnb.*, vrbo.* and booking.* domains (and their short-link and regional variants) before the hosted launch:** the hosted server never fetches those pages, not even for a user-requested preview; for those hosts it shows only what the user typed or the bookmarklet sent. Storing third-party photos is a copyright risk: hotlink, or store a thumbnail plus source link | Own code review |
| Stay22 | Lodging affiliate: link conversion, map widget, later Direct Travel API | Publisher account (verify app terms) | Free; publisher share about 30% of Stay22's commission (reported) | $0 | Does not cover Airbnb (reported); Direct Travel API access is contact-based | S, reported, verify (2026-09-30) |
| Viator partner API | Things to do: search, product data, deep links | Self-service partner API (affiliate) | Free; commission per booking (reported about 8%) | $0 | Product content and image reuse limits to be read in the partner terms | S, reported, verify (2026-09-30) |
| Expedia Group affiliate (on Impact) | Vrbo, Expedia, Hotels.com deep links and conversion reporting | Apply from month 3 | Free; commission per booking (Vrbo reported about 2 to 6%) | $0 | App eligibility to be confirmed in the program terms; Rapid API is out of scope at our scale | S, reported, verify (2026-09-30) |
| Booking.com affiliate | Lodging deep links and conversion reporting | Current network unconfirmed (reported: moved from a direct program to Awin, then Awin reported ending in 2026); check the Affiliate Partner Center before applying. Until then Booking.com is available through Travelpayouts | Free; about 4% reported | $0 | Apps allowed with the mandatory disclosure line (reported) | S, reported, verify (2026-09-30) |
| OurAirports | Airport reference | Bundled seed | Free | $0 | Public domain (per the seed's docstring) | S |

"Geoapify request credits" are provider quota units and are unrelated to the user-facing AI credits, although Geoapify spend counts toward the $0.02 credit budget of an action.

### 4.1 SerpApi and Google Flights: the main risk

- SerpApi scrapes Google. Google sued SerpApi on 2025-12-19 in N.D. Cal. under DMCA section 1201, alleging circumvention of its SearchGuard bot protection ([IPWatchdog](https://ipwatchdog.com/2025/12/26/google-sues-serpapi-parasitic-scraping-circumvention-protection-measures/)). The later timeline is reported by a secondary source only (reported, verify on the docket; checked 2026-09-30): core claims dismissed 2026-07-20, narrower claims refiled 2026-08-10, second motion to dismiss filed 2026-08-25 ([ScrapeBadger summary](https://scrapebadger.com/blog/google-sued-a-scraper-under-copyright-law-and-lost-heres-what-the-serpapi-ruling-actually-says)).
- SerpApi reports a "U.S. Legal Shield" (up to $2M) on the Production and Big Data plans only, excluding claims that arise from how the customer uses the data, and covering U.S. claims in U.S. courts (reported, verify; [SerpApi legal](https://serpapi.com/legal), checked 2026-09-30).
- Google Flights terms do not grant programmatic access. Google could send a cease-and-desist or block SerpApi's upstream access at any time.

Assessment: personal use at 240 searches a month is low risk. A paid product that displays Google Flights fares to thousands of paying users is **high risk**: it depends on an upstream Google is litigating against, on content we do not license, and Apple guideline 5.2 review could pull the app on a third-party complaint. SerpApi's resale terms are unverified.

**Decision of record:** SerpApi is the live-fare source **behind a feature flag at launch, with the legal risk flagged**, and a licensed source (Skyscanner Partners) is applied for now. Mitigations:
1. SerpApi is never the only flight source: Travelpayouts cached fares are the free baseline for every tier.
2. Flights sit behind a provider interface (the `sources` array on `flight_routes` already points this way), so SerpApi turns off by config.
3. Live fares are shown as "price check" hints with a link out, not as bookable inventory.
4. Buy Production ($150) at minimum while it stays, for the legal shield.
5. Move the main live path to a licensed source before scaling past 1k MAU.

### 4.2 Flight source alternatives

| Option | Access | Cost | Fit |
|---|---|---|---|
| Duffel (Flights API) | Self-serve. Reported, verify (primary page blocked): $3.00 per confirmed order, $2.00 per paid ancillary, 1% of order value for managed content, excess-search fee above a 1,500:1 search-to-book ratio ([Duffel pricing](https://duffel.com/pricing)) | Per order | Built for **booking**: you become seller of record with payments, refunds and servicing. Poor fit for a planner that links out. Not chosen |
| Amadeus Self-Service | **Shut down** (reported, verify; checked 2026-09-30): keys disabled 2026-07-17, signups paused since spring 2026, only Enterprise contracts remain ([PhocusWire](https://www.phocuswire.com/amadeus-shut-down-self-service-apis-portal-developers), [Tripgic](https://www.tripgic.com/playbook/amadeus-api-shutdown-migration/)) | n/a | Not available. Removed from the plan |
| Kiwi Tequila | Invitation-only B2B since 2024; via Travelpayouts it reportedly needs 50,000 MAU (reported, verify; [guide](https://phptravels.com/blog/comprehensive-guide-to-flights-api-integration)) | n/a | Not available at launch |
| Skyscanner Partners API | Partner-only, application, roughly 5,000 monthly users minimum and manual approval (reported, verify; checked 2026-09-30; [summary](https://www.travelpayouts.com/blog/skyscanner-flights-api/)) | Free to approved partners, paid by commission | The licensed live source we want (redirect model). **Applied for now**; approval not guaranteed |
| Travelpayouts Data API | Self-serve token | Free | Cached fares reported to cover the last 48 hours to 7 days of Aviasales user searches. The free baseline for all tiers: hints plus affiliate link. Coverage and freshness vary |
| Travelpayouts Search API (real time) | Reported to need 50,000 MAU, with 9% search-to-click and 5% click-to-purchase floors, user-initiated searches only (reported, verify; checked 2026-09-30; [requirements](https://support.travelpayouts.com/hc/en-us/articles/210995808-Requirements-for-Aviasales-Flight-Search-API-access)) | Free; commission | Not usable at 1k or 10k MAU |
| Ignav flight search API | Self-serve; 1,000 free then about $2.00 per 1,000 successful requests (vendor claim, unverified; [docs](https://ignav.com/docs/amadeus-self-service-shutdown)) | Low | Worth a proof of concept; first ask for the upstream data source and resale terms |

Final flight data setup: **Travelpayouts Data API as the free baseline for all tiers; SerpApi behind a feature flag for live routes at launch; Skyscanner Partners applied for now as the licensed live source.**

### 4.3 Places alternatives

- **Geoapify (current):** free 3,000 credits a day, paid from $59/mo. OSM-based, good value; attribute OpenStreetMap (ODbL) and Geoapify. Storage terms not verified: ask in writing (`places_cache` stores 7 days).
- **Google Places (New):** Text Search Pro about $32 per 1,000 after 5,000 free a month (reported, verify; [pricing](https://developers.google.com/maps/billing-and-pricing/pricing)). Best quality at 10x to 100x the cost; `place_id` may be stored but other content has caching limits. Only for a rare detail lookup.
- **Foursquare Places:** Pro free for 500 calls then $15 per 1,000 (reported, verify; pricing change 2026-06-01; [pricing](https://foursquare.com/pricing/)). Caching policy not verified.
- **Overture Maps or self-hosted OSM (Photon, Pelias):** infra only, ODbL share-alike on derived databases. Viable at 100k MAU.

Stay on Geoapify at 1k and 10k MAU (upgrading the plan as needed), get written confirmation on caching and storage, and keep the `places` interface swappable so Foursquare or self-hosted Photon can take autocomplete at 100k MAU.

### 4.4 Affiliate networks

Affiliate links (lodging first, then tours, flights, cars, transfers, eSIM, insurance, post-trip compensation) are the free-tier income and appear on every tier in the same places; there are no banner ads. The full program research and placement map are in [08-affiliate-revenue.md](08-affiliate-revenue.md).

| Network | Flights | Lodging | Access | Notes |
|---|---|---|---|---|
| Travelpayouts (Aviasales and many brands) | About 1.1% to 1.5% of booking value (reported, verify; flights are thin-margin everywhere) | Booking.com, Agoda, Trip.com, Hostelworld, Vrbo and others, by program | Instant signup | **Launch network.** One dashboard, one payout, a statistics API for bookings; also carries cars, transfers, tours, eSIM and insurance |
| Stay22 | n/a | Link conversion for Booking.com, Expedia, Hotels.com, Vrbo (not Airbnb); maps | Self-serve publisher signup | Lodging challenger to Travelpayouts; A/B against it |
| Viator partner API | n/a | n/a (things to do) | Self-service | Launch route for activities; GetYourGuide follows by direct application |
| Expedia Group (Impact) | n/a | Vrbo, Expedia, Hotels.com | Application, from month 3 | The only legal route to Vrbo commission with real rates |
| Skyscanner (Impact or partner API) | Commission on redirects and bookings; approval needed | Hotels via partners | Application | Licensed data plus attribution |
| Booking.com affiliate | n/a | Yes | Current network unconfirmed; Travelpayouts meanwhile | Outbound links only; our rule against fetching Booking pages is unaffected because deep links are links, not fetches. Rapid API and the Connectivity API are not used. |
| Airbnb | n/a | No program an app can join | n/a | Plain link, never converted or tracked |
| GetYourGuide, Klook | n/a | Activities | Direct application from month 3 | Fits itinerary activities; higher rates than flights |

### 4.5 Stripe, LiteAPI and other revenue-lane integrations

| Integration | Used for | When | Data we keep | Notes |
|---|---|---|---|---|
| Stripe (Checkout, Billing, Tax, possibly Connect) | Web payments: group trip payments, Hermi for Advisors seats, print orders, partner guide invoices | Phase 4 live (test mode from phase 2) | Stripe customer, subscription and payment intent ids, amounts, status. No card data. All of it lands in `store_transactions` and the tables that point to it | Card data stays with Stripe (Checkout is hosted). Fees reported at about 2.9% plus $0.30 per card charge and about 0.7% on Billing invoices (verify). Webhooks, idempotency and reconciliation: [05-infrastructure.md](05-infrastructure.md) section 5.6. Stripe is a processor: add it to the privacy policy and the DPA list. Group payment collection needs counsel first (money transmission) |
| LiteAPI (Nuitee) | In-app hotel search and booking as merchant of record, 5 to 15% margin (reported, verify) | Year 2 or later, only after click data shows strong booking intent | A later migration adds a `hotel_bookings` table and LiteAPI ids; nothing is created now | Put it behind the same provider interface as flights and lodging. Read its terms on content caching, photos and who handles refunds and support before building. It would sit beside the affiliate links, never replace them, and never rank by margin |
| Print-on-demand vendor | Trip books and posters | Phase 4 | Vendor order id, tracking, the address (purged at 90 days) | Candidates: Printful, Prodigi, Gelato (verify current terms, quality and shipping regions). Send only the rendered PDF and the address |
| Host travel agency (for example Fora) | Fulfills concierge and room-block requests | Phase 3 or 4 | The request payload and commission statement rows | A recipient of consented data, not a data provider. The host agreement must cover data protection, retention, seller-of-travel registration and commission reporting |

The Booking, Airbnb and Vrbo rules are unaffected: none of these integrations fetches their pages.

## 5. Caching and dedup strategy

Every provider call goes through one `cached_call(kind, normalized_params, ttl, fetch_fn)` helper. It hashes params, checks `shared_research_cache` (with stale-while-revalidate), coalesces concurrent identical requests (single-flight via advisory lock on the key), records a `provider_calls` row, and only then calls out. Today `places.py` does this for Geoapify and rentals; the in-process dict in `providers/geoapify.py` (500 entries, lost on restart, not shared across replicas) moves behind the same helper, backed by Postgres first and by Redis for hot autocomplete once Redis exists (about 10k MAU).

| Provider or data | Cache key (normalized) | TTL | Shared? | Notes |
|---|---|---|---|---|
| SerpApi flights | origin set, destination set, depart, return, cabin, pax, stops, currency | 12 h for dates within 60 days, 24 h for 60 to 180 days, 72 h beyond | Yes: identical `search_key` from any user reuses one observation | Convert to the user's currency at read time; request in USD or EUR |
| Travelpayouts | origin, destination, month or date, one-way flag | 6 h (upstream cache is 48 h to 7 days) | Yes | Free, so use it first and use it to decide whether a paid call is worth it (skip if the cheapest cached fare is far above the alert price) |
| SerpApi rentals | destination, dates, guests, filters | 12 h (current `RENTALS_TTL`); 24 h for month-out dates | Yes | Store only fields the UI shows; drop `raw` after 30 days |
| Geoapify autocomplete | lowercased query, locale, bias | 30 days for named places; 7 days for POI search | Yes | Store `place_id`, name, coordinates; debounce on client (300 ms, min 3 chars) |
| Geoapify places search | rounded bbox or center plus categories | 7 days (current) | Yes | Round to about a 1 km grid at city zoom |
| Wikipedia summary and image | wikidata id | 30 days (current) | Yes | Store attribution and license with the entry (CC BY-SA) |
| FX | currency pair | 12 h (current), refresh on ECB publish (about 16:00 CET on working days) | Global | Add a "rates as of" stamp in the UI |
| AI research (Claude) | kind, normalized destination, month, prompt_version, model | 30 to 90 days (visa rules 30, "top neighborhoods" 90) | Yes, public-input facts only | Never key on user text or cache content derived from private trip notes |
| Link preview | normalized URL | 7 days | Yes (public metadata) | Do not store photos; hotlink or resize once |

Scheduled work is API price checks plus cheap batch scans (batch API for offline jobs such as cache warming, nightly digests and scheduled fare scans), never scheduled agents before Pro.

### Quota scaling with users

Planning estimates, not measurements; validate with `provider_calls.cached` once live. Assumptions: a Plus payer has 3 live routes checked daily within 120 days of departure, at most 90 checks a month, and about 45 in practice because routes are only live near departure; a Trip Pass buyer averages about 20 checks a month (60 maximum over 90 days); a Free user makes about 3 one-credit live searches a month. Payers are 4% of MAU on Plus and 1.5% on Trip Pass, Free live users are 20% of MAU. Dedup hit rate is 40% at 1k, 65% at 10k and 80% at 100k MAU. Family and Group Trip Pass buyers are a small share at launch and are excluded, and Pro is excluded until it launches.

| MAU | Plus / Trip Pass / Free live users | Gross live searches a month | After dedup | SerpApi plan | Est. cost a month |
|---|---|---|---|---|---|
| 1,000 | 40 / 15 / 200 | 2,700 | about 1,620 | Developer (5,000) | $75 (Production $150 for the legal shield) |
| 10,000 | 400 / 150 / 2,000 | 27,000 | about 9,450 | Production (15,000) | $150 |
| 100,000 | 4,000 / 1,500 / 20,000 | 270,000 | about 54,000 | Searcher (100k) | about $725 |

At 100k MAU the licensed source should already carry most live traffic. The per-account ceilings bound the worst case: at $0.015 to $0.025 a search, the Plus monthly ceiling of $2.25 allows roughly 90 to 150 SerpApi searches, in line with the 90-check maximum. Geoapify autocomplete is the bigger quota risk: 100,000 MAU at about 10 keystroke calls per planning session and 3 sessions a month is about 3M calls a month, which lands on the API 100 to API 250 plans ($299 to $609 a month) even with debouncing, unless caching absorbs it or autocomplete moves to a self-hosted engine.

## 6. Affiliate integration

Goal: outbound booking links that earn commission and attribute revenue to a user, trip and surface without tracking anything the App Store privacy label cannot support. Program research, placement map, disclosure and revenue estimates are in [08-affiliate-revenue.md](08-affiliate-revenue.md); this section is the data and service design.

Flow:
1. The user taps a partner button (for example "Book on Vrbo") on a fare, stay, activity or checklist item.
2. The app calls `POST /api/outbound` with `{entity_type, entity_id, surface, trip_id}`. The server checks trip access, picks the program (feature flags, geography, A/B cell), inserts a `link_clicks` row and returns `https://<host>/go/<click_id>`. The `click_id` is a random 128-bit id (base62, about 22 characters), never derived from the user or trip.
3. The app opens that URL in `SFSafariViewController` (not an embedded WKWebView with injected JS).
4. `GET /go/<click_id>` checks the row is fresh (about 10 minutes, not used twice), records `clicked_at`, and returns **HTTP 302** to a URL built from the stored `affiliate_programs.base_url_template`, our affiliate id, the per-click **sub-id** and the destination. It sends `Cache-Control: no-store` and `Referrer-Policy: no-referrer`, and never renders a page, so there is no third-party script, pixel or cookie from us.
5. A nightly worker job per network pulls conversions and matches them to clicks by sub-id.

Redirect rules:
- **No open redirects.** The redirect target is only ever built from a stored template plus a validated destination for that program's own hosts. There is no `url=` parameter, and `/go/<click_id>` accepts only ids we minted.
- **The sub-id is random per click.** It carries no user id, trip id, email or device id. The join from conversion to click to user and trip happens only in our database. Where a network limits sub-id length (Travelpayouts `sub_id` is text, limit reported, verify), use an 8 to 12 character `short_id` with a unique index. A second static field (Stay22 `campaign`, Impact `subId2`) carries the surface label only.
- Rate-limit `/api/outbound` per user (about 60 an hour), dedupe repeat clicks within 30 seconds, and require the authenticated app call to mint a click id.
- Airbnb URLs never go through `/go`; they open as plain links. Pasted listings stay exactly as pasted; a separate "Book via partner" button builds a partner link from the URL text without fetching the page.

```sql
affiliate_programs (id, network text,   /* travelpayouts, impact, stay22, viator, direct */
                    program text, base_url_template text, marker_or_id text,
                    hosts text[],        /* destination hosts this template may point at */
                    commission_model text, cookie_days int, subid_param text, subid_max_len int,
                    campaign_param text null, terms_url text, api_credentials_ref text,
                    disclosure_text text, active bool)
link_clicks (
  id uuid pk, click_id text unique,    /* random, base62, the sub-id we send */
  short_id text null unique,           /* for networks with short sub-id limits */
  user_id fk null, trip_id fk null, program_id fk,
  entity_type text, entity_id bigint,  /* flight quote, lodging option, activity, checklist item */
  checklist_item_kind text null, surface text, program_variant text null,   /* A/B cell */
  destination_url text, opened_in text,          /* sfsvc or safari */
  created_at, clicked_at null, redirect_status int,
  country text, platform text, app_version text,
  ip_hash text                          /* salted, rotated monthly; no advertising id, no device id */
)
affiliate_conversions (
  id, program_id fk, network text,
  network_txn_id text,                 /* Travelpayouts action id, Impact action id, Stay22 booking id, Viator booking ref */
  network_click_ref text null,         /* click or tracking id the network assigned */
  sub_id_returned text null,           /* what the network echoed back */
  click_id text null fk,               /* set when matched; null if the network did not pass the sub-id back */
  match_status text,                   /* matched, unmatched */
  status text,                         /* pending, approved, rejected, paid */
  network_status_raw text,             /* processing, paid, cancelled (Travelpayouts); pending, locked, reversed (Impact) */
  product_type text, product_ref text null,   /* flight, stay, tour; Viator product code, Stay22 partner, Impact campaign */
  booking_value numeric, currency char(3), commission numeric, commission_currency char(3),
  booked_at, travel_date null,         /* check-in or tour date; stays pay after check-out */
  checkout_date null, approved_at, paid_at, reversal_at null,
  clicks_lag_hours numeric, status_history jsonb, raw jsonb,
  unique (program_id, network_txn_id)
)
affiliate_payouts (id, program_id, period, amount, currency, received_at, reference)
checklist_items (id, trip_id fk, kind text, status text,   /* todo, done, skipped, not_needed */
                 due_on date null, done_at null, program_id fk null, created_at)
```
- Conversion pulls run nightly and upsert idempotently on `(program_id, network_txn_id)`: the Travelpayouts statistics and payments API first, then the Impact Actions API for Expedia Group, Stay22 and Viator reports, and later any direct network. Each pull records status changes (pending, approved, rejected, paid) in `status_history`.
- Match to clicks by sub-id. Unmatched conversions are a health metric: above 10% means a tracking break. Alert when clicks drop more than 50% day over day, when redirect 4xx or 5xx exceeds 1%, or when a conversion pull fails.
- `checklist_items` stores the "Before you go" checklist state per trip (documents, visas, insurance, eSIM, transfers and similar). Only items that link to a partner create `link_clicks` rows, and the checklist itself works without any partner. The after-trip "Was your flight delayed?" prompt reads trip dates and flights, and creates no table of its own.
- Materialized views `revenue_by_month`, `revenue_by_surface`, `revenue_by_partner` and `revenue_per_mau` join conversions to clicks to users. Revenue per MAU shows whether affiliate income covers free-tier costs; the kill rule in the README is under $0.20 per monthly user per year (annualized). These are for an internal admin page, not the user app.
- Store only a hashed IP and no advertising identifier. Disclose affiliate links in-app ("We earn a commission if you book here.") next to every partner button, with an "Ad" label on UK and EU storefronts.
- **The hosted server never fetches Airbnb, Vrbo or Booking.com pages.** That includes the existing user-triggered preview in `backend/tripplanner/providers/link_preview.py`, which must be disabled for those domains before hosted launch (a host denylist, checked after redirects). Partner links for those hosts are built from the URL text only, never from page content.
- Booking physical travel outside the app is not subject to In-App Purchase, so the affiliate redirect is compliant. Plus, Family, Trip Pass, Group Trip Pass and credit packs must use StoreKit (see [07-local-to-app-store.md](07-local-to-app-store.md)). Stripe carries only real-world money and web software (section 4.5).
- Model affiliate income as a floor, not the plan: $0.10 / $0.60 / $1.50 per MAU per year (conservative / base / optimistic); see [01-business-plan.md](01-business-plan.md).

## 7. Retention, backups, analytics

### Retention

| Data | Retention | Reason |
|---|---|---|
| Account and trip data | While the account is active; hard purge 30 days after a deletion request | Apple requires in-app account deletion (guideline 5.1.1(v)); GDPR and CCPA |
| `run_events` | 30 days (partition drop); `runs.report` 12 months | Largest growth table; debugging value decays fast |
| `concierge_requests`, `room_block_requests` | Payload deleted 13 months after the travel date; commission fields and booking reference kept for tax records | Commission reconciliation and disputes; consent limits the payload |
| `print_orders.shipping_address` | 90 days after delivery; totals and vendor id kept as purchase records | Personal data, needed only for delivery problems |
| `store_transactions`, `settlements` | Financial records, 7 years (check local tax advice); settlement names anonymized when a member leaves | Disputes, tax |
| Household usage rows | 90 days after a household ends | Lets a resubscribe restore state |
| `advisor_clients.private_notes` | Until the org deletes them or the org closes (then 90 days) | The org owns them |
| `flight_quotes` and `fare_observations.raw` | Drop `raw` after 14 days; keep price history (date, price, source) 24 months | Price history is product value; raw payloads are a terms risk |
| `shared_research_cache` | Purge at `stale_until`; cap size per kind | Limits how long third-party content is held |
| `provider_calls` | 13 months, then monthly rollups | Cost analytics |
| `ai_usage`, `credit_grants`, `trip_passes`, `subscriptions` | 7 years for financial records tied to purchases (check local tax advice); otherwise 25 months | Disputes, refunds |
| Webhook events | 12 months | Reconciliation with Apple |
| Logs | 30 days | Privacy |

Data export: `GET /api/me/export` returns a JSON archive of the user's trips. It is required by GDPR and is a trust signal.

### Backups

- Managed Postgres on Render with PITR (window depends on the plan; verify), plus a daily logical `pg_dump` to Cloudflare R2, a separate provider from the database host, for provider-failure and operator-error cases.
- Replace `services/backups.py` (backup before migrate, to local disk) with a snapshot before each production migration and an automated **monthly restore drill** into a scratch instance with a row-count smoke test. An untested backup is not a backup.
- Target RPO 5 minutes (PITR) and RTO 1 hour at 10k MAU. Add a read replica and a standby region with the AWS or Google Cloud move (around 50k MAU or $1,500 a month).
- Encrypt at rest (managed default). Column-level encryption is not needed in v1 because the app stores no payment data and no passport numbers; do not add passport or document storage without a separate security review.

### Analytics

- Product analytics with a client event SDK (PostHog is self-hostable with a generous free tier) for funnels: onboarding, first trip, paywall view, purchase, first live search. Keep it anonymous by default and use first-party analytics only, so no App Tracking Transparency prompt is needed.
- Server-side business events go to an `events` table (`id, ts, user_id, name, props jsonb`), partitioned monthly and read from a replica or the same Postgres; a warehouse only at 100k MAU.
- Metrics the schema must answer from day one: cache hit rate per provider, provider cost per active user, AI cost per active user by tier, credits consumed vs granted, credit-to-dollar margin (2.4), free to paid conversion, Trip Pass share of paid purchases, affiliate click to conversion, and the share of live searches served from `fare_observations`.
- Sentry for backend and iOS crashes, scrubbing trip content and free-text notes.

## Where this plan changed the initial idea

1. **Own migration system.** The repo already uses Alembic. The change is when it runs: a single pre-deploy job with an advisory lock instead of server start (3.2).
2. **Amadeus Self-Service and Kiwi Tequila as flight options.** Amadeus Self-Service is reported shut down (2026-07-17, reported, verify) and Kiwi is invitation-only. Both are removed.
3. **Duffel as a search replacement.** Duffel is priced and built around booking orders. It does not fit a planner that links out and would change compliance, support and payments scope. Not chosen.
4. **SerpApi as the scaling path for live fares.** Final decision: SerpApi runs behind a feature flag at launch with the legal risk flagged (an earlier draft limited it to the top tier, now called Pro), Travelpayouts cached fares are the free baseline, and Skyscanner Partners is applied for now. Cost is not the issue; legal exposure is.
5. **Row-level security.** Yes, but as a second layer behind app checks, with a restricted DB role in tests, because worker and admin roles bypass it.
6. **Tenant model.** User plus trip membership stays the core. Households (Family pooling only) and advisor orgs were added later and never grant trip access by themselves, so the rule still holds. An earlier draft replaced `people` with a `travelers` table; the final decision keeps `people` and adds `owner_user_id` and `linked_user_id`, with membership in `trip_members`.
7. **Travelpayouts as a fare source.** Its cached data suits "cheap dates" hints but is stale by design and must not be shown as a live price. Its real-time Search API reportedly needs 50,000 MAU (reported, verify), so it cannot replace SerpApi at 1k or 10k.
8. **Quotas and credits.** Per-tier live-search allowances were replaced by the README's credit unit ($0.02 of provider spend, reserve then settle) and per-account provider-spend ceilings. A Trip Pass table was added (with a Group Trip Pass type), pooled household grants were added for Family, and scheduled agents stay off until Pro.
9. **Database host.** Render managed Postgres with PITR replaces the earlier list of options to evaluate (Neon and others), and Redis waits until about 10k MAU.

## Provider-terms risks and unverified items

- **High:** SerpApi scraping Google Flights and Hotels; resale terms unverified; Google v. SerpApi timeline from secondary sources (reported, verify, 2026-09-30).
- **Medium:** Stripe fees, Connect suitability and money-transmission exposure for group payments; LiteAPI and print vendor terms. All from secondary sources or unread (reported, verify).
- **Medium:** Geoapify terms on caching, storing results, and commercial use of the free plan were not read. Get written confirmation and use a paid plan before launch.
- **Medium:** Wikipedia text is CC BY-SA: show attribution and a license link next to each summary; check per-image Commons licenses before using hero images commercially.
- **Medium:** Google Places and Foursquare storage limits are unverified; relevant only if we switch.
- **Medium:** Travelpayouts terms and thresholds (user-initiated searches only, "Book" button rules, 50,000 MAU and conversion floors for the Search API) come from search summaries (reported, verify, 2026-09-30). Read the full agreement before integrating.
- **Low:** Frankfurter (ECB data) and OurAirports (public domain per its docstring) look fine; confirm there is no attribution duty.
- Not verified at all: the Duffel primary pricing page, Skyscanner commission rates and user minimum, per-program affiliate commission tables, Ignav data provenance, the Amadeus shutdown date on a primary page.
