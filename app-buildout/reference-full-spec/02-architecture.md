# 02. Architecture

Part of the [Hermi build specification](../README.md). Shared names, tiers and the table list come from the README and win over anything here. Written 2026-09-30.

This file says how Hermi is put together: the services, the repository, the backend modules, how a request and a job flow through the system, every configuration value, every third-party service, and what to keep from the existing Trip Planner code. The database DDL is in [03-database-schema.md](03-database-schema.md), routes in [04-api-spec.md](04-api-spec.md), AI behavior in [06-ai-agents-spec.md](06-ai-agents-spec.md), money in [07-monetization-spec.md](07-monetization-spec.md), and testing and security in [10-quality-security-launch.md](10-quality-security-launch.md).

## 1. System overview

Hermi is one Python codebase that runs as three process types (API, worker, scheduler) from one Docker image, one PostgreSQL 18 database, and two clients (a React web app and the same app bundled into an iOS shell with Capacitor). There is no Redis at launch, no microservices, and no second database. State lives in Postgres and in Cloudflare R2 object storage. Everything else is stateless.

```mermaid
flowchart LR
    subgraph Clients
        IOS["iOS app (Capacitor, bundled)"]
        WEB["Web app (React SPA)"]
        ADM["Admin console (same SPA, /admin)"]
    end

    SB["Supabase Auth (sign-in only)"]
    CF["Cloudflare: DNS, TLS, WAF, rate rules"]
    PAGES["Cloudflare Pages: web build"]

    IOS -->|"sign in"| SB
    WEB -->|"sign in"| SB
    IOS -->|"HTTPS, bearer JWT"| CF
    WEB --> CF
    ADM --> CF
    CF --> PAGES
    CF -->|"api.hermi.world"| API

    subgraph Render
        API["API service (FastAPI)"]
        WK["Worker service (lanes: api, ai, notify, batch)"]
        SCH["Scheduler service (one leader)"]
        PRE["Pre-deploy: alembic upgrade head"]
    end

    API --> PG[("PostgreSQL 18: app data, job queue, caches, ledgers")]
    WK --> PG
    SCH --> PG
    PRE --> PG
    API --> R2[("Cloudflare R2: uploads, exports, dumps")]
    WK --> R2

    WK --> ANTH["Anthropic Messages API and Batch API"]
    WK --> DATA["Fare, place, FX and affiliate providers"]
    WK --> APNS["APNs"]
    WK --> MAIL["Resend"]

    RC["RevenueCat webhooks"] --> API
    STR["Stripe webhooks"] --> API
    AFF["Affiliate network reports"] --> WK
    API --> SEN["Sentry, logs, PostHog"]
    WK --> SEN
```

### 1.1 Design rules

1. The API never does slow work. Anything that calls Anthropic, loops over providers, sends push or email, builds an export or renders a PDF is a job.
2. Every job is safe to run twice. Every job has an idempotency key (section 5.1).
3. One code path per rule. Entitlement checks, credit charges, tenant checks and kill switches are each one function, called from routes and jobs alike.
4. The client never decides anything about money, limits or permissions. It displays what `GET /me/entitlements` and `TripOut.capabilities` return.
5. Postgres is the only system of record. Caches can be dropped without data loss.
6. Hosted-only code. The personal Windows mode of the old Trip Planner is not carried into Hermi (section 14).

### 1.2 Processes

| Process | Command | Scales by | Holds state |
|---|---|---|---|
| `api` | `hermi api` (uvicorn, 2 workers per container) | Request rate and p95 latency | None |
| `worker` | `hermi worker --lanes api,ai,notify,batch` | Queue depth and oldest job age, per lane | None |
| `scheduler` | `hermi scheduler` | Always 1 active (advisory lock), 2 instances for failover | None |
| `migrate` | `hermi migrate` | One-off, pre-deploy | None |
| `admin` | Part of `api`, routes under `/admin`, separate auth | With `api` | None |

At launch the scheduler runs inside one worker process (flag `SCHEDULER_ENABLED=true` on that service only). It becomes its own service when the worker is scaled past one instance.

## 2. Repository layout

One monorepo, one Git history. JS workspaces (npm) for the TypeScript packages, `uv` workspace for Python.

```
hermi/
  .github/                        GitHub reads workflows only from here
    workflows/                    ci.yml, e2e.yml, evals.yml, security.yml, deploy-staging.yml, deploy-prod.yml, ios.yml
    dependabot.yml                weekly grouped updates (not a workflow)
  apps/
    api/                          FastAPI service and all backend modules
      pyproject.toml
      hermi/
        main.py                   app factory, router wiring, middleware
        cli.py                    hermi api | worker | scheduler | migrate | openapi
        config.py                 pydantic-settings, the only place env vars are read
        db.py                     engine, session, RLS session variable
        deps.py                   CurrentUser, DbSession, require_trip, require_admin
        errors.py                 error types and the problem+json handler
        logging.py                JSON logs, redaction, request ids
        security/                 jwt.py, rate_limit.py, ssrf.py, attest.py, signing.py
        modules/
          auth/  trips/  collaboration/  flights/  lodging/  itinerary/
          places/  ai/  billing/  credits/  affiliate/  concierge/
          groups/  notifications/  admin/  advisors/
        providers/                one file per third party (section 8)
        migrations/               Alembic env and versions
        seed/                     airports, affiliate_programs, feature_flags defaults
      tests/
    worker/                       job definitions and the scheduler
      hermi_worker/
        app.py                    Procrastinate app, lanes, retry strategies
        jobs/                     one file per job (section 5.1)
        scheduler.py              leader election, next_run_at scanner
        agents/                   AgentLoop, tools, prompts, evals hooks
      tests/
    web/                          React 19 + Vite SPA (also the Capacitor bundle)
      src/
        app/  routes/  components/  lib/  features/
        lib/api/                  generated client and schema.d.ts
      e2e/                        Playwright
      public/
    ios/                          Capacitor iOS project
      App/                        Xcode project, Info.plist, entitlements
      plugins/                    small local Swift plugins
      fastlane/
  packages/
    shared/                       TypeScript types, enums, constants used by web and ios
      src/
        entitlements.ts           tier and capability names
        credits.ts                action codes and credit prices
        events.ts                 analytics event names and property types
        flags.ts                  feature flag and kill switch keys
    tokens/                       design tokens (colors, type, spacing), CSS and TS
    eslint-config/                shared lint config
  infra/
    docker/
      Dockerfile
      compose.yml                 local Postgres 18, Mailpit, MinIO
    render/
      render.yaml                 services, cron, env groups, Postgres
    cloudflare/
      rules.md                    WAF and rate rules as reviewed text
      aasa.json                   apple-app-site-association
    scripts/
      restore-drill.sh  rotate-keys.md  seed-staging.py
  docs/
    spec/                         this build specification (copied from business-plan/app-buildout)
    runbooks/                     one file per runbook in 10-quality-security-launch.md
    adr/                          architecture decision records
  .env.example                    every variable in section 7
  package.json                    workspaces, root scripts
  pyproject.toml                  uv workspace (apps/api, apps/worker)
  CLAUDE.md
```

Rules for the tree:

- `apps/worker` imports from `apps/api` (`hermi.modules.*`) and never the other way. Business rules live in the modules; the worker only schedules and runs them.
- `packages/shared` is the only place constants are duplicated between Python and TypeScript. A CI step (`npm run gen:shared`) generates `credits.ts`, `entitlements.ts` and `flags.ts` from Python enums, and fails on drift.
- `apps/web` has no knowledge of Capacitor except in `src/lib/native/`, which is a thin adapter that returns no-ops on the web.
- Root scripts: `npm run dev` (api, worker, web with reload), `npm test`, `npm run lint`, `npm run format`, `npm run gen:api` (OpenAPI to `apps/web/src/lib/api/schema.d.ts`, committed), `npm run test:e2e`, `npm run ios:sync`.

## 3. Backend module boundaries

Each module under `apps/api/hermi/modules/<name>/` has the same five files: `router.py` (HTTP only), `service.py` (business rules, takes a session and a `Actor`), `repo.py` (queries), `schemas.py` (Pydantic in and out) and `models.py` (SQLAlchemy). A module may call another module's `service.py`, never its `repo.py` or `models.py`, except through the read-only `*_refs` helpers listed below. Import direction is enforced by `import-linter` in CI.

| Module | Owns (tables) | Responsibility | May call |
|---|---|---|---|
| `auth` | `users`, `auth_identities`, `devices`, `consents`, `data_exports`, `deletion_requests` | JWT verification, user bootstrap on first sign-in, guest claim, devices, consent records, account deletion and export orchestration, App Attest | `notifications`, `credits` (grant on signup) |
| `trips` | `trips`, `trip_destinations`, `people`, `trip_people`, `checklist_items`, `notes` | Trip CRUD, templates, traveler profiles, checklists, trash and restore, capabilities computed per trip (`trip_capabilities()`) | `billing` (entitlements), `collaboration` |
| `collaboration` | `trip_members`, `trip_invites`, `trip_share_links`, `polls`, `poll_votes`, `activity_log` | Roles, invites, share links, polls (plus, family, pro and both passes), activity feed, optimistic concurrency helpers, ownership transfer | `trips`, `notifications` |
| `flights` | `flight_routes`, `fare_observations`, `trip_fare_links`, `chosen_flights`, `price_alerts`, `route_price_insights`, `airports`, `fx_rates` | Routes, fare ingest and dedup, cached-fare alerts, live-check scheduling inputs, chosen flight, FX conversion | `ai` (fare hunt), `credits`, `affiliate`, `providers` |
| `lodging` | `lodging_options`, `lodging_votes` | Shortlist, pasted-link previews (no Airbnb, Vrbo or Booking.com fetches), votes, compare, rental search | `places`, `affiliate`, `providers` |
| `itinerary` | `itinerary_days`, `itinerary_items` | Days and items, ordering, times and time zones, conflicts, presentation data, calendar feed (ICS) | `places`, `trips` |
| `places` | `places_cache`, `saved_places` | Geoapify search and details, Wikipedia summaries, map data, cache expiry per provider terms | `providers` |
| `ai` | `routines`, `runs`, `run_events`, `ai_usage`, `provider_calls`, `shared_research_cache` | `AgentLoop`, tool definitions, prompts, evidence rules, run lifecycle, metering, shared research cache, AI consent check, kill switches for AI | `credits`, `flights`, `trips`, `providers.anthropic` |
| `billing` | `plans`, `store_products`, `subscriptions`, `entitlements`, `trip_passes`, `store_transactions`, `webhook_events`, `households`, `household_members` | RevenueCat and Stripe webhooks, entitlement computation, Trip Pass binding, Family household, restore and reconcile | `credits` |
| `credits` | `credit_ledger`, `credit_grants`, `credit_debts`, `credit_action_prices` | The only writer of credits: grants, reserve, settle, refund, expiry, pooled Family balance, spend ceilings | none (leaf) |
| `affiliate` | `affiliate_programs`, `affiliate_link_templates`, `link_clicks`, `affiliate_conversions`, `affiliate_payouts`, `partner_guides` | Link building from stored templates, the `/go/{click_id}` redirect, disclosure flags, conversion import, revenue reports | `providers` |
| `concierge` | `concierge_requests`, `room_block_requests` | "Have a human book this" requests, advisor assignment, status, consent and disclosure, seller-of-travel gating by region | `notifications`, `advisors` |
| `groups` | `expenses`, `expense_shares`, `payment_collections`, `settlements` | Manual cost splitting and balances (every paid tier and both passes, plus Free users on trips that have them), currency handling; settle-up through Stripe only for `group_trip_pass` and `pro`, Phase 4 (never In-App Purchase) | `billing` (Stripe), `trips` |
| `notifications` | `devices` (read), notification preference and delivery rows | Push, email, digest building, preference checks, quiet hours, collapse ids, unsubscribe | `providers.apns`, `providers.resend` |
| `admin` | `admin_users`, `feature_flags`, `kill_switches`, `audit_log`, `support_tickets`, `content_reports` | Admin console API, feature flags, kill switches, support tools, audit writes | every service (through audited functions) |
| `advisors` | `advisor_orgs`, `advisor_seats`, `advisor_clients`, `print_orders` | Advisor workspaces, client trips, proposals, seat billing on Stripe, commission tracking | `trips`, `billing`, `affiliate` |

Cross-cutting code (not modules): `security/` (owns `rate_limit_counters` and `idempotency_keys`), `deps.py`, `errors.py`, `logging.py`, `providers/`. The analytics helper `analytics.capture(event, props)` lives in `hermi/analytics.py` and validates names against `packages/shared/src/events.ts`.

Boundary rules that tests enforce:

- Only `credits.service` writes `credit_ledger` and `credit_grants`. Only `billing.service` writes `entitlements`, `subscriptions`, `trip_passes` and `store_transactions`. A grep-based test fails on any other writer.
- Only `providers/*` import `httpx` or the Anthropic SDK. Modules call provider classes, which record a `provider_calls` row for every outbound call (provider, endpoint, cost units, latency, status, cached).
- Only `affiliate.service` builds outbound partner URLs. Templates come from `affiliate_link_templates`. No other module concatenates a partner URL.
- No module imports `worker`. Jobs are deferred through `jobs.enqueue(name, **args)` in `hermi/jobs.py`, which is a thin wrapper over Procrastinate's `defer_async` that uses the caller's transaction.

## 4. Request lifecycle

### 4.1 Authenticated request

1. **Edge.** Cloudflare terminates TLS, applies WAF and per-IP rate rules, and forwards to Render. The origin accepts traffic only from Cloudflare (authenticated origin pulls). `TRUSTED_PROXY_CIDRS` makes `X-Forwarded-For` trustworthy.
2. **Middleware order.** Request id (`X-Request-Id`, generated if absent) then access log start, CORS (explicit origins, including `capacitor://localhost`), body size limit (1 MB JSON, uploads go to R2 by signed URL), kill-switch check for maintenance mode, then the route.
3. **Authentication.** Dependency `CurrentUser` reads `Authorization: Bearer <jwt>` (web also accepts the `hermi_session` cookie set by `POST /auth/session`). It verifies the Supabase JWT: signature against the cached JWKS (selected by `kid`, refreshed on unknown `kid` at most once per minute), `iss` equals `SUPABASE_JWT_ISSUER`, `aud` equals `SUPABASE_JWT_AUDIENCE`, `exp` and `nbf` with 30 seconds of skew. It then maps `sub` through `auth_identities` to a `users` row, creating the user and the "Me" person on first sight in one transaction. A user whose status is not `active` gets 403 `account_inactive` (`suspended` or `deleted`), and `pending_deletion` gets 403 `account_pending_deletion` so the app can offer recovery (04 section 1.2).
4. **Session variable.** `DbSession` opens a transaction and runs `SELECT set_config('app.user_id', :uuid, true)` (transaction-local). Row-level security policies on trip-owned tables read `current_setting('app.user_id')`. The API database role has no `BYPASSRLS`. Jobs that act for a user set the same variable; system jobs use a separate role `hermi_worker` with `BYPASSRLS` (see [03-database-schema.md](03-database-schema.md) section 6.1).
5. **Tenant check.** Every route with a `trip_id` depends on `require_trip(trip_id, min_role)`. It returns a `TripAccess(trip, member, role, capabilities)` object, or raises `NotFound` (404, never 403) when the user is not a member or the trip is in trash. `min_role` is one of `viewer`, `editor`, `owner`. Routes that take a child id (an itinerary item, a lodging option) resolve the child, join up to its trip and then call the same function. No route calls `session.get(Model, id)` on a tenant table. A CI test walks `app.routes` and fails if a path with an id parameter does not resolve through `require_trip` or is not on the public allowlist.
6. **Entitlement and credit checks.** Routes that cost money call `entitlements.require(capability, trip)` first (402 with a `paywall` body naming the upsell, never a bare error), then `credits.reserve(user, action, trip)` for AI actions. Both are service calls, not decorators, so the order is visible in the code.
7. **Handler and response.** The handler returns a Pydantic model. Mutations on editable rows use `If-Match` with the row version; a mismatch returns 409 with the latest row. Lists support `updated_since` and ETag for cheap polling.
8. **Errors.** One handler renders `application/problem+json`: `type`, `title`, `status`, `code` (stable string), `detail`, `request_id`. Unhandled errors return a generic 500 body and go to Sentry with the request id.
9. **Log line.** One JSON line per request: `ts`, `level`, `service`, `env`, `release`, `request_id`, `user_id` (opaque UUID), `route` (template, not raw path), `status`, `latency_ms`, `bytes`. No bodies, no query strings with tokens.

### 4.2 Public and special requests

| Route class | Auth | Notes |
|---|---|---|
| `GET /health/live`, `/health/ready` | none | Ready checks database, migration head, queue reachability |
| `GET /go/{click_id}` | none | Never takes a URL from the request. Looks up a `link_clicks` row created by an authenticated call, builds the destination from `affiliate_link_templates`, logs, and 302s. Unknown or expired id goes to the trip page, never elsewhere |
| `GET /shared/{token}` | token | Read-only trip view with redaction flags, per-token throttle |
| `POST /webhooks/revenuecat`, `/webhooks/stripe`, `/webhooks/resend`, `/webhooks/supabase-auth` | signature | Verify, insert into `webhook_events` by provider event id, return 200 fast, process in a job (section 5.1) |
| `POST /auth/session`, `GET /me` | JWT | Session bootstrap |
| `/admin/*` | admin session | Separate middleware: SSO, 2FA, IP allowlist optional, every call writes `audit_log` |
| `GET /i/{token}` | none | Universal link landing, JSON for the app, HTML for the web fallback |

### 4.3 Row-level security in detail

RLS is the second lock, not the first. Policies exist on: `trips`, `trip_members`, `trip_destinations`, `trip_people`, `flight_routes`, `chosen_flights`, `price_alerts`, `itinerary_days`, `itinerary_items`, `saved_places`, `lodging_options`, `lodging_votes`, `polls`, `poll_votes`, `expenses`, `expense_shares`, `payment_collections`, `settlements`, `checklist_items`, `notes`, `routines`, `runs`, `run_events`. The standard policy is `EXISTS (SELECT 1 FROM trip_members m WHERE m.trip_id = <table>.trip_id AND m.user_id = current_setting('app.user_id')::uuid)`. User-owned tables (`devices`, `people` by `owner_user_id`, `consents`, `credit_ledger`, `credit_debts`, `idempotency_keys`) use a direct `user_id = current_setting(...)` policy; `content_reports` (insert and read your own) and `partner_guides` (published rows only) have their own policies. A test connects as the API role with no variable set and expects zero rows from every table with a policy. DDL is in [03-database-schema.md](03-database-schema.md).

### 4.4 Web and iOS differences

| Concern | Web | iOS (Capacitor) |
|---|---|---|
| Token storage | HttpOnly Secure SameSite=Lax cookie via `POST /auth/session` | Supabase session in the Keychain through a secure-storage plugin; bearer header |
| Origin | `https://app.hermi.world` | `capacitor://localhost` |
| CSRF | `X-Hermi: 1` header plus `Origin` check, cookie requests only | Not applicable (bearer) |
| API base URL | `VITE_API_BASE_URL` | Same, compiled into the bundle |
| Push | None at launch | APNs token registered at `POST /devices` |
| Purchases | Upgrade screen explains the app; no web checkout for digital goods | RevenueCat over StoreKit 2 |

## 5. Background jobs: how they run

Queue: Procrastinate on the application database. Four lanes (Procrastinate queues): `api` (short provider calls, 20 to 50 concurrent per worker), `ai` (Claude calls, 4 to 10 concurrent), `notify` (push and email, high concurrency), `batch` (polling and bulk work, 2 concurrent). User-visible work has a row in `runs` (status, events, cancel flag) and the job carries only `run_id`. Non-user jobs have no `runs` row; their history is Procrastinate's own job table plus a `job_heartbeats` view.

Common rules:

- **Fair claim.** Jobs carry `priority` (interactive 10, paid scheduled 5, free scheduled 1) and a per-account concurrency cap (Free 2, Plus and Family 4, Pro 8). One agent run at a time per account, enforced by a partial unique index on running agent runs.
- **Queueing locks.** A job with a `queueing_lock` collapses duplicates while one is waiting. A `lock` serializes jobs with the same key while running.
- **Reaper.** Workers heartbeat every 15 seconds. The `reap_stale_jobs` job requeues anything whose heartbeat is older than 2 minutes (5 for the `ai` lane).
- **Shutdown.** On SIGTERM a worker stops claiming, lets jobs finish up to 60 seconds (`ai` jobs checkpoint and requeue), and exits.
- **Dead letters.** A job that exhausts retries is marked `failed`, appears in the admin console, and raises an alert when the count in a lane passes 5 in an hour.
- **Retry classes.** `transient` = 429, 5xx, timeouts, connection errors: exponential backoff with jitter (base 30 seconds, factor 2, cap 15 minutes), honoring `Retry-After`. `permanent` = 4xx other than 429, validation, budget exhausted, consent missing: no retry. `none` = do not retry, the next scheduled tick covers it.

### 5.1 Job catalogue

Times are UTC unless marked local. "Key" is the idempotency key: a second run with the same key does nothing (enforced by a unique index or `ON CONFLICT DO NOTHING`).

| Job | Lane | Trigger | Schedule | Idempotency key | Retries |
|---|---|---|---|---|---|
| `scan_due_routines` | api | Scheduler tick | Every 30 seconds (leader only) | `routines.last_slot_at` advanced in the same transaction | none |
| `check_fare_route` | api | Routine tick, user "refresh", trip pass start | Live routes daily within 120 days of departure, jittered in a 60 minute window by hash of route id | `(route_id, provider, time_bucket_6h)` on `provider_calls` | transient x5 |
| `refresh_cached_fares` | api | Scheduler | Every 6 hours for routes with `price_alerts` or free cached-fare tracking | `(route_id, bucket_6h)` | transient x5 |
| `evaluate_price_alerts` | notify | After `check_fare_route` or `refresh_cached_fares` writes `fare_observations` | Event | `(alert_id, observation_id)` | transient x3 |
| `run_ai_action` | ai | User action (`explain`, `live_search`, `draft_day`, `draft_trip`, `research`) | Event | `Idempotency-Key` header, unique per user | transient x2, refunds credits on final failure |
| `run_agent` | ai | User action or Pro routine | Event; Pro routines by `next_run_at` | `run_id` | transient x2 at turn boundaries only, never replays tool writes |
| `warm_research_cache` | batch | Scheduler | Nightly 03:10 local to the US East region, Anthropic Batch API | `(destination, month, interest_bucket, model, prompt_version)` | transient x5 |
| `collect_batch_results` | batch | Scheduler | Every 10 minutes while a batch is open | `batch_id` | transient x10 |
| `settle_ai_usage` | ai | End of `run_ai_action` or `run_agent` | Event | `run_id` | transient x5 |
| `reap_stale_jobs` | batch | Scheduler | Every minute | none (idempotent by nature) | none |
| `process_webhook_event` | api | Row inserted in `webhook_events` | Event | `(provider, provider_event_id)` unique | transient x10 over 24 hours |
| `reconcile_entitlements` | api | Scheduler | Every 6 hours, plus on demand from admin; calls RevenueCat REST for users with recent activity | `(user_id, day)` | transient x5 |
| `grant_monthly_credits` | api | Scheduler | Every hour; grants at each subscriber's monthly anniversary (annual plans) and at calendar month start for comped and advisor entitlements. Free accounts are not in this job: their 12 credits are written lazily on first use (`ensure_free_monthly_grant`, 03 section 5.13) | `(user_id, kind, period_key)` unique on `credit_grants` | transient x5 |
| `expire_credits` | api | Scheduler | Daily 02:00 | `(credit_grant_id)` | transient x3 |
| `expire_trip_passes` | api | Scheduler | Every 15 minutes | `(trip_pass_id, 'expired')` | transient x3 |
| `send_push` | notify | Event | Event | `(user_id, alert_id_or_event_id, channel)` unique | transient x5, 410 deletes the `devices` token |
| `send_email` | notify | Event | Event | `(user_id, template, dedupe_key)` unique | transient x5 |
| `build_digest` | notify | Scheduler | Hourly; sends at 08:00 local per user, max 1 per hour per trip | `(user_id, trip_id, date)` | transient x3 |
| `poll_invites_cleanup` | api | Scheduler | Daily 04:00 | none | none |
| `import_affiliate_conversions` | api | Scheduler | Nightly 05:00 per network (Travelpayouts, Viator, Stay22, direct programs as added) | `(program_id, network_txn_id)` unique on `affiliate_conversions` | transient x5 |
| `refresh_fx_rates` | api | Scheduler | Daily 06:00 (Frankfurter) | `(base, date)` unique on `fx_rates` | transient x5 |
| `refresh_places_cache` | api | Lazy on read, sweep daily 03:30 | Delete expired rows per provider terms | `place_key` | none |
| `export_user_data` | batch | `POST /me/export` | Event; max 1 per day per user | `data_exports.id` | transient x3; 7 day link |
| `delete_account` | batch | `POST /me/delete` then 30 day timer | Event then day 30 | `deletion_requests.id` and a checklist row per step | transient x10, each step idempotent |
| `purge_trash` | batch | Scheduler | Daily 04:30; hard deletes trips deleted more than 30 days ago | `(trip_id)` | transient x3 |
| `retention_sweep` | batch | Scheduler | Daily 05:30; invites older than 30 days, IP hashing after 30 days, prompt content older than 30 days, `run_events` payloads older than 14 days, analytics older than 90 days, audit rows by `retention_class` (03 section 8) | `(table, day)` | transient x3 |
| `purge_idempotency_keys` | api | Scheduler | Hourly; deletes `idempotency_keys` past `expires_at` | none | none |
| `expire_kill_switches` | api | Scheduler | Every minute; disengages switches past `kill_switches.expires_at`, writes `audit_log` as `system`, and warns the owner 15 minutes before expiry (08 section 6.5) | `(key, expires_at)` | none |
| `ai_spend_guard` | api | Scheduler | Every 5 minutes; sums `ai_usage`, trips the global circuit breaker, raises alerts | `(bucket_5m)` | none |
| `reconcile_anthropic_usage` | batch | Scheduler | Daily 06:30; pulls the Anthropic usage and cost admin API and compares it with `ai_usage` (alert above 3 percent) | `(date)` | transient x3 |
| `provider_quota_check` | api | Scheduler | Every 30 minutes (SerpApi account API, Geoapify, Travelpayouts rate limits) | `(provider, bucket_30m)` | none |
| `build_concierge_digest` | notify | Scheduler | Hourly; notifies advisors of new or stale `concierge_requests` | `(request_id, state)` | transient x3 |
| `send_group_settle_reminders` | notify | Scheduler | Daily 15:00 local; only for `settlements` the user opted into | `(settlement_id, date)` | transient x3 |
| `db_dump_offsite` | batch | Scheduler | Weekly, Sunday 03:00; encrypted `pg_dump` to R2 backups bucket, 90 day lifecycle | `(week)` | transient x3, alert on failure |
| `heartbeat_ping` | api | Scheduler | Every minute; pings Better Stack heartbeat URLs for scheduler and queue | none | none |

### 5.2 Scheduler design

The scheduler is a loop inside `hermi_worker/scheduler.py`. It enqueues work; it never runs it.

1. **Leader election.** On start it tries `pg_try_advisory_lock(0x57415946)` on a dedicated connection. The holder is the leader; others sleep 10 seconds and retry. If the leader's connection drops, the lock frees and a standby takes over within 10 seconds.
2. **Routine scan.** Every 30 seconds the leader runs `SELECT id FROM routines WHERE enabled AND next_run_at <= now() ORDER BY next_run_at LIMIT 500 FOR UPDATE SKIP LOCKED`. For each row it checks the kill switch for the routine's kind, checks the account's budget (reserve in the same transaction), inserts a `runs` row (`trigger = 'schedule'`), defers the job, and advances `next_run_at` to the next cron slot after now (never stacking missed slots). An outage of a day fires one check, not many.
3. **Jitter.** `next_run_at` = cron slot plus `hash(routine_id) mod window`, window 60 minutes for daily checks. This spreads load and is stable per routine.
4. **Periodic jobs.** Fixed-schedule jobs in section 5.1 use Procrastinate periodic tasks registered on the leader only, so they never double-fire. Each has the `slot` timestamp as its lock key.
5. **Live-route eligibility.** A route is scheduled only if the trip's best capability allows it (Plus 3, Family 5, Pro 6, Trip Pass 2 per trip, Group Trip Pass 2 per trip), the departure is within 120 days, and the trip pass has live checks left (60 max). When eligibility ends, `next_run_at` is cleared and the route keeps its last fares.
6. **Scheduled agents.** Off for everyone until Pro. Flag `scheduled_agent_routines` defaults off. The scan skips `routines.kind IN ('fare_hunt', 'deep_research')` while the flag is off.
7. **Observability.** Each tick writes `scheduler_ticks` metrics (due count, enqueued, skipped by reason, tick duration). A heartbeat URL is pinged each minute; a missing ping for 3 minutes pages.

### 5.3 Provider call flow inside a job

```
job starts -> set app.user_id (or system role) -> load run row -> check kill switch and consent
  -> cache lookup by cache_key (provider_calls / shared_research_cache / fare_observations bucket)
  -> hit: return, record provider_calls(cached=true)
  -> miss: take queueing lock on cache_key, call provider, record provider_calls(cost_units, latency, status)
  -> write results in one transaction -> settle credits and spend -> emit run_events -> enqueue notifications
```

## 6. Caching layers

There is no Redis at launch. Every layer below is in Postgres, in process memory, or at the edge.

| Layer | What | Where | Key | TTL | Invalidation |
|---|---|---|---|---|---|
| Edge static | Web build, fonts, images, brand assets | Cloudflare CDN and Pages | Content hash in file name | 1 year immutable for hashed assets, `no-cache` for `index.html` | Deploy |
| Edge API | Public GETs only: `GET /share/{token}` JSON, AASA file, partner guides | Cloudflare | URL | 60 seconds, `stale-while-revalidate` 5 minutes | Purge by tag on share link revoke |
| Client query cache | Trip data | TanStack Query, persisted to IndexedDB (SQLite in phase 2) | Query key prefixed by user id | `gcTime` 30 days, `staleTime` 30 seconds on shared trips | Sign-out clears; `updated_since` poll merges |
| JWKS | Supabase signing keys | Process memory | `kid` | 1 hour, refresh on unknown `kid` (max 1 per minute) | Key rotation |
| Feature flags and kill switches | `feature_flags`, `kill_switches` | Process memory per instance | Flag key | 5 seconds | `NOTIFY flags_changed` from admin writes refreshes at once |
| Entitlement cache | Computed tier and capabilities | `entitlements` table (`tier_code`, `limits`) plus per-request memo | `user_id` | Recomputed on each webhook and on `reconcile_entitlements` | Webhook processing |
| Fare and lodging provider results | Provider responses | `provider_calls` (`request_hash`, `cached`) plus `fare_observations` and `places_cache` | `sha256(provider, endpoint, normalized_params, time_bucket)` | Flights 6 hours, lodging and places 24 hours, FX 24 hours | Expiry sweep |
| Places | Geoapify and Wikipedia results | `places_cache` | provider id | Per provider terms (`expires_at`) | Sweep job |
| AI shared research | Public web research only | `shared_research_cache` | `(destination, month, interest_bucket, model, prompt_version)` | 7 days | Prompt version bump; admin purge |
| Anthropic prompt cache | System prompt, tool definitions, trip context prefix | Anthropic side | Prefix | 5 minutes, refreshed on use | Automatic |
| Rate limit counters | Token buckets | Postgres table `rate_limit_counters` (unlogged) | `(subject, route_class)` | Sliding window | Redis replaces at about 10k MAU |

Rules: the shared caches hold only public facts (prices, places, web research), never notes, itineraries or names. A cache hit costs the user the lower credit price where the README says so (`research` 1 credit, `agent_run` 8 credits). Cache hit rate is tracked per provider and per AI action; the target above 60 percent at 10k MAU.

## 7. Configuration

All configuration is environment variables, read once in `config.py` through `pydantic-settings`. Missing required values fail startup with a list of names (never values). Nothing outside `config.py` reads `os.environ`. `.env` is for local use only and is gitignored; `.env.example` lists every variable with a fake value and is updated in the same pull request that adds a variable.

### 7.1 Environment variables

"Secret" means the value must never appear in the repo, logs or client bundle. Public client values are prefixed `VITE_` and are safe in the bundle but still documented.

**Core**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `ENVIRONMENT` | `local`, `ci`, `preview`, `staging`, `production`. Tests refuse to run when `production` | `staging` | No |
| `RELEASE_SHA` | Git SHA of the image, tagged onto logs, Sentry and metrics | `a1b2c3d` | No |
| `LOG_LEVEL` | Log verbosity | `INFO` | No |
| `PORT` | API listen port | `8000` | No |
| `PUBLIC_API_URL` | Public base URL of the API, used in links and webhooks | `https://api.hermi.world` | No |
| `PUBLIC_WEB_URL` | Public web app URL, used in emails and invites | `https://app.hermi.world` | No |
| `CORS_ALLOWED_ORIGINS` | Comma list of allowed origins, including Capacitor | `https://app.hermi.world,capacitor://localhost` | No |
| `TRUSTED_PROXY_CIDRS` | Networks whose `X-Forwarded-For` is trusted | `173.245.48.0/20,...` | No |
| `API_DOCS_ENABLED` | Serves `/docs` (off in production) | `false` | No |
| `SCHEDULER_ENABLED` | Whether this process runs the scheduler loop | `true` | No |
| `WORKER_LANES` | Lanes this worker serves | `api,ai,notify,batch` | No |
| `WORKER_CONCURRENCY_API` / `_AI` / `_NOTIFY` / `_BATCH` | Concurrent jobs per lane | `30` / `6` / `50` / `2` | No |

**Database**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `DATABASE_URL` | App role connection (DML only, no `BYPASSRLS`) | `postgresql+psycopg://hermi_api_login:...@host/hermi` | Yes |
| `DATABASE_URL_SYSTEM` | System role for jobs that cross tenants | `postgresql+psycopg://hermi_worker_login:...` | Yes |
| `MIGRATION_DATABASE_URL` | DDL role, used only by `migrate` | `postgresql+psycopg://hermi_owner:...` | Yes |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | Pool size per process | `10` / `5` | No |
| `DATABASE_STATEMENT_TIMEOUT_MS` | Per-statement timeout (the migration role overrides) | `15000` | No |
| `TEST_DATABASE_URL` | Test database; CI and local only | `postgresql+psycopg://hermi:...@localhost/hermi_test` | Yes |
| `REDIS_URL` | Empty until Redis is added (about 10k MAU) | empty | Yes |

**Identity and device trust**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `SUPABASE_URL` | Supabase project URL | `https://abc.supabase.co` | No |
| `SUPABASE_JWKS_URL` | Signing keys for JWT verification | `https://abc.supabase.co/auth/v1/.well-known/jwks.json` | No |
| `SUPABASE_JWT_ISSUER` / `SUPABASE_JWT_AUDIENCE` | Expected `iss` and `aud` | `https://abc.supabase.co/auth/v1` / `authenticated` | No |
| `SUPABASE_SERVICE_ROLE_KEY` | Delete users on account deletion, admin lookups | `eyJ...` | Yes |
| `SUPABASE_AUTH_HOOK_SECRET` | Verifies Supabase Auth hook calls | `whsec_...` | Yes |
| `APPLE_TEAM_ID` / `APPLE_BUNDLE_ID` | App identity for App Attest and Apple APIs | `ABCDE12345` / `world.hermi.ios` | No |
| `APPLE_SIGNIN_KEY_ID` / `APPLE_SIGNIN_PRIVATE_KEY` | Sign in with Apple key, used to revoke tokens on deletion | `K1234` / PEM | Key id no, key yes |
| `APPLE_APP_ATTEST_ENV` | `development` or `production` attestation | `production` | No |
| `GUEST_TOKEN_SECRET` | Signs guest claim tokens for `POST /me/claim` | random 32 bytes | Yes |
| `FIELD_ENCRYPTION_KEY` | Encrypts rare sensitive fields (Apple refresh token) | base64 32 bytes | Yes |

**AI**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | One workspace per environment with a spend limit | `sk-ant-...` | Yes |
| `AI_MODEL_FAST` | Haiku model id | `claude-haiku-4-5` | No |
| `AI_MODEL_MAIN` | Sonnet model id | `claude-sonnet-5-5` | No |
| `AI_GLOBAL_DAILY_CAP_USD` | Circuit breaker for total daily spend | `150` | No |
| `AI_ALERT_DAILY_MULTIPLIER` | Alert when daily spend passes this times the 7 day average | `1.5` | No |
| `PROMPT_VERSION` | Current prompt set, part of shared cache keys | `2026-10-01.1` | No |

**Payments**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `REVENUECAT_WEBHOOK_SECRET` | Authorizes RevenueCat webhook calls | random | Yes |
| `REVENUECAT_API_KEY` | REST key for reconcile | `sk_...` | Yes |
| `VITE_REVENUECAT_KEY_IOS` | Public SDK key for iOS | `appl_...` | No |
| `STRIPE_SECRET_KEY` | Stripe API (advisors, group payments, print) | `sk_live_...` | Yes |
| `STRIPE_WEBHOOK_SECRET` | Verifies Stripe webhooks | `whsec_...` | Yes |
| `STRIPE_ADVISOR_PRICE_ID` | Advisor seat price | `price_...` | No |

**Data, affiliate and travel providers**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `TRAVELPAYOUTS_TOKEN` | Cached fares API | random | Yes |
| `TRAVELPAYOUTS_MARKER` | Affiliate marker (appears in partner URLs) | `123456` | No |
| `VIATOR_API_KEY` | Viator partner API | random | Yes |
| `STAY22_AID` | Stay22 affiliate id | `hermi` | No |
| `SERPAPI_API_KEY` | Live fares and rentals, behind flag `serpapi_live_fares` | random | Yes |
| `SERPAPI_MONTHLY_CAP` | Global search cap | `5000` | No |
| `GEOAPIFY_API_KEY` | Places and geocoding | random | Yes |
| `WIKIMEDIA_CONTACT` | Required contact for Wikipedia API | `support@hermi.world` | No |
| `FRANKFURTER_BASE_URL` | FX rates | `https://api.frankfurter.dev` | No |
| `LITEAPI_KEY` | Later: in-app hotel booking | empty until used | Yes |
| `AFFILIATE_DIRECT_*` | Keys for direct programs added from month 3, one per program | empty | Yes |

**Messaging, storage, observability**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `RESEND_API_KEY` / `RESEND_WEBHOOK_SECRET` | Email send and bounce webhooks | `re_...` / `whsec_...` | Yes |
| `EMAIL_FROM` | From address | `Hermi <hello@hermi.world>` | No |
| `UNSUBSCRIBE_SECRET` | Signs one-click unsubscribe links | random | Yes |
| `APNS_KEY_ID` / `APNS_TEAM_ID` / `APNS_PRIVATE_KEY` | Token-based APNs auth | `K5678` / `ABCDE12345` / PEM | Key id and team no, key yes |
| `APNS_TOPIC` / `APNS_USE_SANDBOX` | Bundle id topic, sandbox switch | `world.hermi.ios` / `false` | No |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | R2 S3 credentials | random | Id no, others yes |
| `R2_BUCKET_UPLOADS` / `R2_BUCKET_EXPORTS` / `R2_BUCKET_BACKUPS` | Buckets | `hermi-uploads` | No |
| `SENTRY_DSN` / `VITE_SENTRY_DSN` | Error reporting (DSN is not sensitive but is configured per environment) | `https://...@sentry.io/1` | No |
| `SENTRY_AUTH_TOKEN` | CI only: upload source maps and dSYMs | `sntrys_...` | Yes |
| `POSTHOG_KEY` / `VITE_POSTHOG_KEY` / `POSTHOG_HOST` | Product analytics | `phc_...` / `https://us.i.posthog.com` | No |
| `BETTERSTACK_SOURCE_TOKEN` | Log shipping | random | Yes |
| `BETTERSTACK_HEARTBEAT_SCHEDULER` / `_QUEUE` | Heartbeat URLs | `https://uptime.betterstack.com/api/v1/heartbeat/...` | Yes (URL is a bearer) |
| `ALERT_WEBHOOK_URL` | Chat channel for alerts | `https://hooks.slack.com/...` | Yes |

**Admin and web client**

| Name | Purpose | Example | Secret |
|---|---|---|---|
| `ADMIN_OIDC_ISSUER` / `ADMIN_OIDC_CLIENT_ID` / `ADMIN_OIDC_CLIENT_SECRET` | Company SSO for the admin console | `https://accounts.google.com` | Secret only for the last |
| `ADMIN_ALLOWED_DOMAIN` | Only this email domain may sign in to admin | `hermi.world` | No |
| `ADMIN_SESSION_SECRET` | Signs admin session cookies | random | Yes |
| `ADMIN_IP_ALLOWLIST` | Optional CIDR list for `/admin` | empty | No |
| `VITE_API_BASE_URL` | API origin used by the web and iOS bundles | `https://api.hermi.world` | No |
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | Client sign-in | `https://abc.supabase.co` / `eyJ...` | No (anon key is public by design) |
| `VITE_APP_ENV` | Shown in the settings footer and Sentry | `production` | No |

### 7.2 Rules

- Separate values per environment. Never reuse a production key in staging, preview or CI.
- Production secrets live in Render environment groups (`hermi-prod-shared`, `hermi-prod-api`, `hermi-prod-worker`). GitHub holds only deploy credentials through OIDC and the `SENTRY_AUTH_TOKEN`.
- `config.py` exposes `settings.public_dict()` for the `GET /config` route (minimum app version, enabled feature keys), which never includes a secret field. A unit test asserts every field marked secret is excluded.
- Redaction: the log filter masks any value whose key matches `key|secret|token|password|authorization|cookie|dsn` and any JWT-shaped string.

## 8. Third-party services

| Service | Purpose | Failure behavior |
|---|---|---|
| Supabase Auth | Sign-in (Apple, Google, email code), JWT issuing | Existing sessions keep working (JWKS cached, tokens verified locally). New sign-ins fail with a friendly screen and a status link. Email code delivery goes through Resend SMTP |
| Anthropic Claude API | All AI features | Non-urgent `ai` lane pauses on repeated 429 or 5xx; users see "queued, we will finish this when the service recovers" and credits stay reserved up to 30 minutes, then release. Cached data keeps working. Kill switch `ai.all` |
| Anthropic Batch API | Cache warming | Missed night means stale research; the next night catches up |
| Render | Compute and Postgres | Multi-instance API survives one instance loss. Regional outage: status page, restore plan in the runbook |
| Cloudflare (DNS, WAF, Pages, R2) | Edge, web hosting, storage | Pages outage: the iOS app still works because it is bundled. R2 outage: uploads and exports fail with retry, trips keep working |
| RevenueCat | Purchases, entitlement events | Webhook backlog delays unlock; `POST /purchases/sync` gives instant unlock for the buyer. Outage: entitlements come from our own table, so nothing locks. Reconcile job catches up |
| Stripe | Advisor seats, group payments, print orders | Payment buttons show "temporarily unavailable"; no digital feature depends on it |
| Travelpayouts | Cached fares and affiliate network | Fare cards show last observation with its age; alerts pause; affiliate links still work |
| SerpApi | Live fares and rentals, flag `serpapi_live_fares` | Flag off or quota out: live checks fall back to cached fares and say so; credits are not charged for an empty result |
| Geoapify | Places and geocoding | Serve `places_cache`; search shows "search is limited right now"; manual place entry still works |
| Wikipedia and Wikimedia | Destination summaries and photos | Skip the summary; no error shown |
| Frankfurter | FX rates | Use the last stored `fx_rates` row, show its date |
| Viator, Stay22, other affiliate networks | Affiliate link templates, tours | Card hidden if the program's kill switch is on. Links are templates, so a provider outage only breaks the partner page |
| APNs | Push | Retry transient errors; 410 deletes the device token; the in-app feed still shows the alert |
| Resend | Email (invites, receipts, digests, auth codes) | Retry; invites can also be shared as links; if down over 30 minutes switch `EMAIL_PROVIDER` to the standby SES account (manual) |
| Sentry | Errors | Errors log locally; the app is unaffected |
| PostHog | Product analytics | Events dropped after a short local buffer; nothing user-visible |
| Better Stack | Logs, uptime, heartbeats, status page | Logs also stay in Render for 7 days |
| App Store Connect, TestFlight, Xcode Cloud | Release and review | Releases delayed; server stays backward compatible with the last 3 app versions |
| Apple App Attest / DeviceCheck | Free-credit abuse control | If unavailable, fall back to stricter IP and email limits and halve free AI for unattested devices; never block normal use |

## 9. Environments

| Environment | Purpose | Hosting | Data | Third parties |
|---|---|---|---|---|
| `local` | Development | `docker compose` (Postgres 18, Mailpit, MinIO) or native Postgres; `npm run dev` | Seed data from `apps/api/hermi/seed` and `infra/scripts/seed-staging.py` | Provider fakes by default (`PROVIDERS_MODE=fake`); Anthropic dev key with a $5 limit only when testing AI |
| `ci` | Tests | GitHub Actions with a `postgres:18` service | Ephemeral | All mocked; contract tests use recorded fixtures |
| `preview` | One per pull request | Render preview (API plus worker, small Postgres) | Seed data | Sandbox keys; separate Supabase project; APNs sandbox |
| `staging` | Release rehearsal, TestFlight backend | Render, same shape as production, smaller sizes | Synthetic, never a copy of production | Separate Anthropic workspace with a $50 monthly limit; App Store sandbox; Stripe test mode; RevenueCat sandbox |
| `production` | Users | Render plus Cloudflare | Real | Separate workspace and keys for every service |

Rules: staging and production have separate Supabase projects, R2 buckets, Sentry projects and PostHog projects. Only the image digest is promoted from staging to production; configuration is never copied automatically. The test suite and e2e seed refuse to start when `ENVIRONMENT=production` or when the database name does not end in `_test` for test runs.

## 10. CI/CD pipeline

GitHub Actions, one workflow per concern, all in `.github/workflows/` at the repository root (GitHub runs workflows from nowhere else). Production deploys use OIDC, never stored cloud keys.

| Workflow | Trigger | Steps |
|---|---|---|
| `ci.yml` | Pull request | 1. Install (`uv sync --frozen`, `npm ci`). 2. `npm run lint` (ruff, import-linter, oxlint, tsc). 3. `npm test` with a `postgres:18` service (pytest and vitest). 4. OpenAPI drift: `npm run gen:api` then `git diff --exit-code` on `schema.d.ts`; shared constants drift check. 5. Tenant-isolation suite (section 1.3 of [10-quality-security-launch.md](10-quality-security-launch.md)). 6. Migration test: from empty, and from the last released revision; single Alembic head. 7. Build the Docker image. 8. Trivy scan. |
| `e2e.yml` | Pull request labeled `e2e`, nightly | Playwright against the built image with the e2e seed (desktop and iPhone viewport projects) |
| `evals.yml` | Changes under `agents/`, prompts, or model config; weekly | AI evals through the Batch API; blocks merge on a gate miss |
| `security.yml` | Weekly and on pull request | `pip-audit`, `npm audit`, `gitleaks`, CodeQL, Trivy |
| `deploy-staging.yml` | Merge to `main` | Build and push image tagged with the commit SHA, deploy staging (pre-deploy migration runs), smoke test, post result to chat |
| `deploy-prod.yml` | Manual approval on a tag | Promote the same image digest (no rebuild), snapshot Postgres if the release has a migration, pre-deploy migration, rolling deploy, post-deploy smoke test, automatic rollback if `/health/ready` fails for 2 minutes |
| `ios.yml` | Tag `ios-*` or manual | Mac runner or Xcode Cloud: `npm run build`, `cap sync ios`, archive, upload to TestFlight, upload dSYMs to Sentry |
| `.github/dependabot.yml` (configuration, not a workflow) | Continuous | Weekly grouped updates |

Branching: trunk based. Short-lived branches, squash merge, `main` is always deployable. Every merge to `main` deploys staging automatically. A production release is a tag `vYYYY.MM.DD.N`.

## 11. Docker image

One multi-stage `infra/docker/Dockerfile`:

1. `node:22-slim` stage: `npm ci`, build `apps/web` (used only for the optional self-host image and e2e; production web ships from Cloudflare Pages).
2. `python:3.13-slim` builder stage: install `uv`, `uv sync --frozen --no-dev` for `apps/api` and `apps/worker` into `/app/.venv`.
3. Final `python:3.13-slim` stage, pinned by digest: copies the venv and source, creates a non-root user `hermi` (uid 10001), read-only root filesystem compatible (writes only to `/tmp`), no compilers, `HEALTHCHECK` on `/health/live`.
4. Entry point `hermi`; the platform sets the command: `api`, `worker --lanes ...`, `scheduler`, `migrate`.

The image contains no secrets and no `.env`. Build arguments are limited to `RELEASE_SHA`. Trivy fails the build on fixable high or critical findings.

## 12. Migrations as pre-deploy

- Alembic. Migrations run as a Render pre-deploy command (`hermi migrate`) using `MIGRATION_DATABASE_URL`. New instances take traffic only after it succeeds. The command takes `pg_advisory_lock(0x4d494752)` so two deploys cannot race.
- Expand and contract. Release N adds nullable columns and new tables; release N+1 writes both and backfills in a batched job; release N+2 drops the old column. Old and new code must both work against the schema during a rolling deploy.
- Safety: `lock_timeout = 5s`, `statement_timeout = 60s` for DDL, `CREATE INDEX CONCURRENTLY` for large tables, no data backfills inside Alembic.
- Rollback means rolling forward with a fix, or a point-in-time restore. Down migrations exist for development only. A manual Render Postgres snapshot is taken before any release that contains a migration touching more than a trivial table.
- CI fails on multiple heads, on a migration that has no corresponding model change, and when `alembic upgrade head` followed by `alembic check` reports drift.
- Seed data (airports, `affiliate_programs`, default `feature_flags`) loads through idempotent `hermi seed`, run after migrate in the same pre-deploy command.

## 13. Feature flags and kill switches

Both live in Postgres (`feature_flags`, `kill_switches`), are cached 5 seconds per process, and change instantly through `NOTIFY`. Only admins change them, through the admin console, and each change writes `audit_log`. A flag may target a percentage, a tier, a user list, a country, a platform or an app version range (`rules`: `tiers`, `countries`, `user_ids`, `platforms`, `min_app_version`, `max_app_version`). Clients read the enabled set from `GET /config`; the server always re-checks. The keys and defaults below are exactly the seed in [03-database-schema.md](03-database-schema.md) section 11.5; if they ever differ, 03 wins and this table is corrected.

**Feature flags** (release control; default in parentheses)

| Key | Controls |
|---|---|
| `serpapi_live_fares` (on) | Live fare and rental provider (legal risk is flagged; turn it off here if the terms audit goes badly) |
| `tier_pro` (off) | Pro products visible and purchasable |
| `scheduled_agent_routines` (off) | Pro scheduled agent routines |
| `guest_mode` (on) | Local-first guest mode before sign-in |
| `group_tools` (on) | Polls, expenses and settlements |
| `group_payments` (off; Phase 4) | Stripe collection for `group_trip_pass` and `pro` (`rules.fee_bps`, 0) |
| `concierge_requests` (off until seller-of-travel registration is confirmed per region) | Concierge requests |
| `room_block_requests` (on) | Room-block request on Group Trip Pass trips |
| `poll_comments` (off) | Comments and mentions on polls |
| `inapp_hotel_booking` (off) | LiteAPI booking, later |
| `min_app_version` (on, `rules.min_version` 1.0.0) | Forces an update below a version |
| `partner_guides` (off) | Labeled partner guides |
| `print_orders` (off) | Printed trip books |
| `advisor_workspaces` (off) | Advisor seats and workspaces |
| `insurance_cards` (off until legal review) | Insurance referral cards |
| `visa_assist` (off) | Third-party visa service links (the official link is always first) |
| `affiliate_lodging_test` (on) | A/B: Travelpayouts Booking.com versus Stay22 on lodging |
| `link_preview` (on) | User-initiated link preview; hosts on the denylist are never fetched |
| `shared_research_cache` (on) | Shared research cache reads and writes |
| `passkeys` (off) | Passkey sign-in |

Settings are flags with `kind = 'setting'` (keys starting `setting_`, the value in `rules`): `setting_ai_warm_daily_usd` (5), `setting_ai_global_daily_usd` (50) and `setting_serpapi_monthly_quota` (5000). Experiments start with `exp_`.

**Kill switches** (operational control, all off by default; turning one on disables the thing; an admin-set switch always has an expiry, 08 section 6.5)

| Key | Effect |
|---|---|
| `ai.all` | Pauses the `ai` lane; AI buttons show "AI is paused, your plans are safe" |
| `ai.free_tier` | Blocks AI for Free accounts (automatic at 80 percent of the daily Anthropic budget) |
| `ai.all_but_paid` | Blocks AI except for paid tiers (automatic at 95 percent) |
| `ai.agent_runs` | Blocks `agent_run` only |
| `ai.explain`, `ai.draft`, `ai.research`, `ai.taster`, `ai.import`, `ai.packing` | Stops that one AI feature |
| `ai.web_search`, `ai.web_fetch` | Runs without the server web search or fetch tool |
| `ai.model.sonnet`, `ai.model.haiku` | Routes to the other model where the feature allows it, else off |
| `ai.force_haiku` | Uses the fast model for every feature that allows it |
| `ai.batch` | Pauses scans, digests and cache warming |
| `ai.shared_cache_write` | Stops writes to the shared research cache |
| `provider.serpapi`, `provider.travelpayouts`, `provider.geoapify`, `provider.anthropic`, `provider.viator`, `provider.stay22`, `provider.frankfurter`, `provider.stripe` | Disables one provider |
| `affiliate.all` | Turns every partner link off (plain links only) |
| `affiliate.insurance` | Turns insurance referral cards off |
| `affiliate.<program_code>` | Hides one program's cards and stops new clicks for it (one row per `affiliate_programs.code`, seeded from that table) |
| `push.all`, `email.all` | Stops sending |
| `signups` | Stops new account creation (existing users unaffected) |
| `purchases` | Hides paywalls and purchase buttons |
| `webhooks.process` | Keeps receiving webhooks but pauses processing, for a safe replay |
| `maintenance` | Read-only mode: writes return 503 with a friendly body |
| `user:<users.id>` | Per-account AI and live hold; created by an admin on demand, never seeded |

Practice every switch in staging each quarter. Anthropic workspace spend limits are the backstop outside our code.

## 14. Mapping the existing Trip Planner code

Paths are under `backend/tripplanner/` and `frontend/src/` in the current repo. Reuse means copy with small changes; adapt means keep the idea and rewrite for multi-tenant and Hermi names; drop means do not carry over.

### 14.1 Backend

| Existing module | Decision | Where it goes | Reason |
|---|---|---|---|
| `config.py` | Adapt | `apps/api/hermi/config.py` | Keep the typed settings pattern; remove passcode, host list, `CLAUDE_PATH`, backup and Windows paths; add section 7 variables |
| `db.py` | Adapt | `db.py` | Add pool limits, timeouts, TLS, the `app.user_id` session variable and a system session |
| `main.py` | Adapt | `main.py` | Keep the app factory and router wiring; add CORS, middleware order (section 4), problem+json errors; no SPA serving |
| `spa.py` | Drop | none | The web app ships from Cloudflare Pages |
| `security.py` | Adapt | `security/` | Keep constant-time compare and redaction ideas; replace passcode cookie and loopback trust with JWT verification; rate limits move to Postgres |
| `process.py`, `supervisor.py` | Drop | none | Windows watchdog and local supervisor; the platform restarts containers and migrations are pre-deploy |
| `migrate.py`, `setup_db.py` | Adapt, Drop | `cli.py migrate`; setup dropped | Keep the Alembic runner with advisory lock; superuser prompt setup is local-only |
| `paths.py` | Drop | none | `%LOCALAPPDATA%` and repo-relative paths; no writable local state |
| `cli.py` | Adapt | `cli.py` | Keep the typer or argparse shape; commands become `api`, `worker`, `scheduler`, `migrate`, `seed`, `openapi` |
| `migrations/` (7 revisions) | Drop history, keep `env.py` | `migrations/` | Start Hermi with a new baseline from [03-database-schema.md](03-database-schema.md); the 7 existing revisions are replaced by one baseline plus a one-off data import script |
| `models/base.py` | Adapt | `modules/*/models.py` base | Keep the declarative base; switch to UUIDv7 public ids and `timestamptz` |
| `models/trip.py`, `people.py` | Adapt | `trips`, `people`, `trip_people` | Add `deleted_at`, `owner_user_id`, `linked_user_id` (the UUIDv7 `id` is the public id); `trip_travelers` becomes `trip_people` |
| `models/flights.py` | Adapt | `flight_routes`, `fare_observations`, `trip_fare_links`, `chosen_flights`, `price_alerts` | Logic is sound; add tenant scope, cache keys and alert rows |
| `models/itinerary.py` | Adapt | `itinerary_days`, `itinerary_items` | Rename Activity to item, add created-by, row `version` on all editable rows |
| `models/lodging.py` | Adapt | `lodging_options`, `lodging_votes` | Votes gain `user_id` |
| `models/airport.py` | Reuse | `airports` | Static reference data |
| `models/agents.py`, `automation.py` | Adapt | `routines`, `runs`, `run_events`, `ai_usage` | Add `user_id`, `next_run_at`, slot keys, request ids, cost micro-dollars; drop `pid`, `argv_redacted`, `log_path` |
| `models/system.py` | Drop, Adapt | `feature_flags`, `kill_switches`; heartbeat row dropped | `AppSetting` global key value becomes flags; singleton heartbeat replaced by per-instance job heartbeats |
| `api/trips.py`, `itinerary.py`, `lodging.py`, `places.py`, `flights.py`, `people.py`, `geo.py` | Adapt | Module routers | Keep route shapes where they fit [04-api-spec.md](04-api-spec.md); add `require_trip`, UUID ids, `If-Match`, `updated_since`; every route covered by the tenant test |
| `api/agent.py` | Drop | none | Loopback ingest API for the CLI bridge; tools run in process |
| `api/runs.py` | Adapt | `modules/ai/router.py` | Keep run list, detail and cancel; scope to the user and trip |
| `api/auth.py` | Drop | `modules/auth/router.py` (new) | Passcode login replaced by session bootstrap, `/me`, devices, consent, export, delete |
| `api/settings.py` | Adapt | `modules/auth` and `trips` | Global settings become per-user settings; setup checklist becomes onboarding |
| `api/system.py` | Adapt | `health` routes and admin | Claude CLI and PC status dropped; readiness checks and admin status kept |
| `api/deps.py` | Adapt | `deps.py` | Keep `DbSession`; add `CurrentUser`, `require_trip`, `require_admin` |
| `schemas/*` | Adapt | Per-module `schemas.py` | Keep Pydantic shapes; remove integer ids from outputs; add `capabilities`; `schemas/presentation.py` kept for the presentation API |
| `services/trips.py`, `people.py`, `itinerary.py`, `lodging.py`, `places.py` | Adapt | Module `service.py` | Business rules carry over; add scope arguments |
| `services/flight_choice.py`, `quotes.py`, `routes.py` | Reuse / Adapt | `modules/flights/service.py` | Fare normalization, best-option logic and chosen-flight rules are the core; add tenant scope and cache keys |
| `services/search_planner.py` | Adapt | `modules/flights/planner.py` | Date-window planning logic is reusable; budget input becomes per-account ceilings |
| `services/serpapi_budget.py` | Adapt | `modules/credits` and `providers/serpapi.py` | The "spread a quota over remaining days" shape becomes per-account and global budgets |
| `services/agent_ingest.py` | Reuse | `modules/ai/ingest.py` | The evidence rules, blocked domains, price bounds and `IngestRejection` are the trust boundary; called in process from tools |
| `services/agent_context.py` | Adapt | `modules/ai/context.py` | Builds model context from one trip; must read only that trip and exclude private notes and other travelers' names |
| `services/claude_cli.py` | Drop | none | CLI sign-in and PID handling cannot be multi-tenant |
| `services/routines.py`, `runs.py` | Adapt | `modules/ai` | Keep run lifecycle and log events; add next_run_at, budgets, refunds |
| `services/backups.py` | Drop | `db_dump_offsite` job (new) | Windows `pg_dump.exe` and local folder; PITR is primary, weekly off-provider dump is new Linux code |
| `services/system_status.py` | Adapt | `health` and admin status | Replace CLI and heartbeat checks with database, queue and provider checks |
| `services/app_settings.py` | Drop | `feature_flags` | Global key value store replaced by flags and per-user settings |
| `services/enrichment.py`, `airports.py`, `fx.py`, `presentation.py` | Reuse | Module services | Self-contained and tenant-neutral; `fx.py` writes `fx_rates` |
| `providers/travelpayouts.py` | Reuse | `providers/travelpayouts.py` | Plus affiliate marker support |
| `providers/serpapi.py`, `serpapi_rentals.py` | Adapt | `providers/serpapi.py` | Keep behind `serpapi_live_fares`; add `provider_calls` recording and cache keys |
| `providers/geoapify.py`, `geoapify_places.py` | Reuse | `providers/geoapify.py` | Add `provider_calls` and cache expiry |
| `providers/wikipedia.py`, `frankfurter.py` | Reuse | Same names | Small and generic |
| `providers/link_preview.py` | Adapt | `providers/link_preview.py` | Add SSRF protection (resolved IP checks, redirect limits), refuse Airbnb, Vrbo and Booking.com hosts, legal review before scaling |
| `seed/airports.py` | Reuse | `seed/airports.py` | Static data |
| `worker/main.py`, `executor.py` | Drop | `apps/worker/app.py` | Two-second loop and thread pools replaced by Procrastinate lanes |
| `worker/scheduler.py` | Drop | `apps/worker/scheduler.py` (new) | APScheduler per routine double-fires with two instances; replaced by the leader and `next_run_at` scanner |
| `worker/jobs/flight_prices.py` | Adapt | `jobs/check_fare_route.py` | Provider call logic carries over; add cache, dedup and idempotency |
| `worker/agents/runner.py`, `stream.py`, `smoke.py` | Drop, rebuild | `agents/loop.py` | CLI subprocess becomes `AgentLoop` on the Messages API; `smoke.py` idea becomes an eval runner |
| `worker/agents/prompts.py` | Adapt | `agents/prompts.py` | Keep `SYSTEM_PROMPT` almost verbatim as the cached prefix; remove the tools section; version it |
| `agent_bridge/` | Drop | none | MCP stdio bridge; tools are in process |
| `tests/conftest.py`, `factories.py` | Adapt | `apps/api/tests` | Keep the test database discipline; add a two-tenant fixture |
| `tests/fake_claude.py` | Adapt | fake Messages client | Replay recorded `server_tool_use`, `pause_turn` and `refusal` fixtures |
| `tests/e2e_seed.py` | Adapt | e2e seed | Two users, one shared trip, one Plus and one Free |
| Other pytest files (`test_trips`, `test_itinerary`, `test_lodging`, `test_flight_*`, `test_quotes`, `test_places`, `test_people`, `test_presentation`, `test_airports_seed`) | Adapt | Module tests | Logic assertions carry over; add auth and tenant arguments |
| `test_auth`, `test_agent_*`, `test_backups`, `test_scheduler`, `test_startup`, `test_spa`, `test_system`, `test_serpapi_budget` | Drop or rewrite | Replaced by new suites | They test removed code; budget and scheduler tests are rewritten for the new designs |

### 14.2 Frontend and tooling

| Existing | Decision | Reason |
|---|---|---|
| `frontend/src/index.css` tokens | Adapt | Becomes `packages/tokens`; the plumbing and neutral token names are ported, but every value is replaced by the Hermi tokens in [05-ui-ux-spec.md](05-ui-ux-spec.md) section 2 |
| `components/brand/*` (guilloche, logo, brand mark) | Adapt | Swap the logo for the Hermi mark from `brand/` and replace `guilloche.tsx` with `route-pattern.tsx` (05 section 2.9); the tests are rewritten for the new pattern |
| `components/ui/*` | Reuse | Radix and shadcn primitives |
| `components/flights/*`, `itinerary/*`, `lodging/*`, `trips/*`, `people/*` | Adapt | Mostly reusable; add role-aware actions, paywall moments, affiliate cards, attribution |
| `components/deck/*`, `routes/present-page.tsx` | Adapt | Presentation mode carries over; add portrait mobile mode |
| `components/agents/*`, `routes/agents/*` | Adapt | Runs, timeline and findings carry over; add credits cost and consent; remove routine UI until Pro |
| `components/auth/*` | Drop, rebuild | Passcode gate replaced by sign-in and guest flow |
| `components/layout/*` | Adapt | Add bottom tab bar under 768 px; remove PC status indicator |
| `components/common/*` | Reuse | Combobox, error boundary |
| `lib/api/*` | Adapt | Configurable base URL, bearer token, refresh-once on 401, `If-Match` |
| `lib/dates.ts`, `money.ts`, `currencies.ts`, `format.ts`, `timezones.ts`, `geo.ts`, `itinerary-time.ts`, `trip-status.ts`, `price-sources.ts` and their tests | Reuse | Pure logic; money moves to integer minor units where not already |
| `lib/theme*.ts*`, `hooks.ts`, `utils.ts`, `errors.ts` | Reuse / Adapt | Hooks namespace the query cache by user |
| `routes/settings-page.tsx`, `setup-checklist.tsx`, `routes/lodging-import.tsx` | Adapt | Settings becomes account, devices, consent, export, delete; setup checklist becomes onboarding; the bookmarklet stays user-initiated and never server fetched |
| `routes/errors.tsx`, `trips-home.tsx`, `routes/trip/*` | Adapt | Add empty, offline, paywall and out-of-credits states |
| `frontend/e2e`, `playwright.config.ts` | Adapt | Move to `apps/web/e2e`; Chromium and WebKit projects, iPhone viewport |
| `scripts/*.ps1` (autostart, share-tailscale, run-hidden) | Drop | Windows and Tailscale only |
| `scripts/setup.mjs` | Adapt | Becomes `npm run setup` that starts compose, migrates and seeds |
| Root `package.json` scripts | Adapt | Keep `dev`, `test`, `lint`, `format`, `gen:api`, `test:e2e`; drop `autostart:*`, `share`, `backup`, `restore`, `agent:smoke` |
| `.claude/rules/*`, `knowledge/` | Adapt | Keep the three-tier context layout and the migrations and frontend rules for the new repo; rewrite the agent rules for the API loop |
| `CLAUDE.md` rule "subagents use Sonnet" | Reuse | Build-time rule carries over; not a runtime rule |
| `CLAUDE.md` rule "never fetch Airbnb, Vrbo or Booking pages" | Reuse | Becomes product rule 3 in the README |

### 14.3 One-off data import

A script `infra/scripts/import_trip_planner.py` reads the personal Trip Planner database and creates two `users`, their `trip_members` (owner), `people` with `linked_user_id`, trips, flights, itinerary, lodging and notes with new UUIDs, using the new schema. It is run once, by hand, against staging first. It is not part of the product.
