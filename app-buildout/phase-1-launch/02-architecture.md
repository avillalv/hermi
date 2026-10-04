# 02. Architecture (Phase 1)

Part of the [Hermi build specification](../README.md), [Phase 1: the launch app](README.md). Shared names, tiers and the table list come from the [README](../README.md) and win over anything here. Written 2026-09-30.

This file says how Hermi is put together for the launch app: the services, the repository, the backend modules, how a request and a job flow through the system, every configuration value, every third-party service, and what to keep from the existing Trip Planner code. The database DDL is in [03-database-schema.md](03-database-schema.md), routes in [04-api-spec.md](04-api-spec.md), AI behavior in [06-ai-agents-spec.md](06-ai-agents-spec.md), money in [07-monetization-spec.md](07-monetization-spec.md), the admin console in [08-admin-control-center.md](08-admin-control-center.md), and testing and security in [10-quality-security-launch.md](10-quality-security-launch.md).

Modules, tables and services that belong to Phase 2 or 3 are not built in Phase 1. They appear only as "added in Phase 2 or 3" or "Later: Phase 2 or 3" pointers.

**Phase 1 additions to the shared design.** These names come from 03 and 04; this file only says where they live.

- Tables: `trip_imports`, `referral_codes`, `referral_rewards`, `plan_verifications`, `plan_verification_items`. Columns and views: the evidence freshness columns (`notes.checked_at`, `itinerary_items.check_url`, `itinerary_items.checked_at`), `users.email_verified_at`, the polling columns on `trip_imports`, `trips.calendar_token_hash`, `trip_passes.source` (`purchase`, `import_reward` or `admin`), the booked-fare fields on `chosen_flights` and the view `booked_fare_drops`, `import_id` and `import_uid` on `itinerary_items` and `lodging_options`.
- Public routes: `GET /calendar/{token}.ics`, `GET /public/status` and `GET /public/how-we-earn` (section 4.2). Import, referral, calendar token and plan verification routes are in 04 sections 5.26, 5.27, 5.29 and 5.30.
- Trust and platform additions from the competitive analysis: a public status page hosted outside our own infrastructure (section 8.1), the "Synced N seconds ago" indicator (section 4.5), static trust pages ("How we earn", billing, Android install guide; section 4.5) and plan verification (06 section 5.11).
- Jobs: section 5.1. Import pipeline, SSRF guard, calendar feed and booked-fare alert: sections 5.4 to 5.6.
- Flags, settings and kill switches: section 13.

## 1. System overview

Hermi is one Python codebase that runs as three process types (API, worker, scheduler) from one Docker image, one PostgreSQL 18 database, and two clients (a React web app and the same app bundled into an iOS shell with Capacitor). There is no Redis at launch, no microservices, and no second database. State lives in Postgres and in Cloudflare R2 object storage. Everything else is stateless.

```mermaid
flowchart LR
    subgraph Clients
        IOS["iOS app (Capacitor, bundled)"]
        WEB["Web app (React SPA)"]
        ADM["Admin console (same SPA, /admin)"]
        CAL["Calendar apps (subscribed feed)"]
    end

    SB["Supabase Auth (sign-in only)"]
    CF["Cloudflare: DNS, TLS, WAF, rate rules"]
    PAGES["Cloudflare Pages: web build"]

    IOS -->|"sign in"| SB
    WEB -->|"sign in"| SB
    IOS -->|"HTTPS, bearer JWT"| CF
    WEB --> CF
    ADM --> CF
    CAL -->|"GET /calendar/{token}.ics"| CF
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
    WK -->|"SSRF-guarded fetch"| FEEDS["User calendar feeds (ICS)"]
    WK --> APNS["APNs"]
    WK --> MAIL["Resend"]

    RC["RevenueCat webhooks"] --> API
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
7. One AI provider seam. `apps/api/hermi/providers/ai/` holds the `AiProvider` protocol (`single_call`, `agent_run`) and three backends: `anthropic_api`, `claude_cli` and `fake`. `modules/ai/client.py` is a facade that picks the backend through a factory from `AI_PROVIDER`. Metering is provider-neutral: the same `ai_usage` and `runs` rows are written whichever backend served the call, and `ai_usage.provider` and `runs.provider` record which one.

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
  .python-version                 3.13
  .data/                          gitignored local state: storage/, outbox/
  scripts/                        node scripts: setup.mjs, db-init.mjs, doctor.mjs
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
          places/  ai/  billing/  credits/  affiliate/  notifications/  admin/
          imports/  referrals/  verification/
          concierge/                added in Phase 2 or 3
          groups/                   added in Phase 2 or 3
          advisors/                 added in Phase 2 or 3
        providers/                one file per third party (section 8), including feed_fetcher.py
          ai/                     AiProvider protocol and backends: anthropic_api, claude_cli, fake
        migrations/               Alembic env and versions
        seed/                     airports, affiliate_programs, feature_flags defaults
      tests/
    worker/                       job definitions and the scheduler
      hermi_worker/
        app.py                    Procrastinate app, lanes, retry strategies
        jobs/                     one file per job (section 5.1)
        scheduler.py              leader election, route scan (`scan_due_routes`)
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
      compose.yml                 optional: local Postgres 18, Mailpit, MinIO
    db/
      bootstrap.sql               idempotent roles and databases, run by npm run db:init
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
- Local ports: `npm run dev` serves the API on port 8100, bound to `127.0.0.1` (never `0.0.0.0`, because the `claude_cli` guard requires a loopback bind), and the web app on 5173. Vite reads the repo-root `.env` (`envDir: '../..'`).
- Root scripts: `npm run dev` (api, worker, web with reload), `npm test`, `npm run lint`, `npm run format`, `npm run gen:api` (OpenAPI to `apps/web/src/lib/api/schema.d.ts`, committed), `npm run test:e2e`, `npm run ios:sync`.


## 3. Backend module boundaries

Each module under `apps/api/hermi/modules/<name>/` has the same five files: `router.py` (HTTP only), `service.py` (business rules, takes a session and a `Actor`), `repo.py` (queries), `schemas.py` (Pydantic in and out) and `models.py` (SQLAlchemy). A module may call another module's `service.py`, never its `repo.py` or `models.py`, except through the read-only `*_refs` helpers listed below. Import direction is enforced by `import-linter` in CI.

| Module | Owns (tables) | Responsibility | May call |
|---|---|---|---|
| `auth` | `users`, `auth_identities`, `devices`, `consents`, `data_exports`, `deletion_requests` | JWT verification, user bootstrap on first sign-in, guest claim, devices, consent records, account deletion and export orchestration, App Attest | `notifications`, `credits` (grant on signup), `referrals` (attribute a referral code at sign-up) |
| `trips` | `trips`, `trip_destinations`, `people`, `trip_people`, `checklist_items`, `notes` | Trip CRUD, templates, traveler profiles, checklists, trash and restore, capabilities computed per trip (`trip_capabilities()`), calendar token rotation (`trips.calendar_token_hash`) | `billing` (entitlements), `collaboration` |
| `collaboration` | `trip_members`, `trip_invites`, `trip_share_links`, `activity_log` | Roles, invites, share links, activity feed, optimistic concurrency helpers, ownership transfer | `trips`, `notifications` |
| `flights` | `flight_routes`, `fare_observations`, `trip_fare_links`, `chosen_flights`, `price_alerts`, `route_price_insights`, `airports`, `fx_rates` | Routes, fare ingest and dedup, cached-fare alerts, the booked-fare drop alert (section 5.6), live-check scheduling inputs, chosen flight, FX conversion | `ai` (fare hunt), `credits`, `affiliate`, `providers` |
| `lodging` | `lodging_options`, `lodging_votes` | Shortlist, pasted-link previews (no Airbnb, Vrbo or Booking.com fetches), hearts, compare, rental search | `places`, `affiliate`, `providers` |
| `itinerary` | `itinerary_days`, `itinerary_items` | Days and items, ordering, times and time zones, conflicts, presentation data, calendar feed generation (section 5.5) | `places`, `trips` |
| `places` | `places_cache`, `saved_places` | Geoapify search and details, Wikipedia summaries, map data, cache expiry per provider terms | `providers` |
| `ai` | `runs`, `run_events`, `ai_usage`, `provider_calls`, `shared_research_cache` | `AgentLoop`, tool definitions, prompts, evidence rules, run lifecycle, metering, shared research cache, AI consent check, kill switches for AI, the pasted-text booking extraction call that `imports` uses (section 5.4) | `credits`, `flights`, `trips`, `providers.ai` |
| `verification` | `plan_verifications`, `plan_verification_items` | "Verify this plan": start, selection, check, import of verified items, and the one-tap evidence recheck of notes and items (06 sections 5.11 and 5.12) | `ai`, `credits`, `itinerary`, `places`, `trips` |
| `imports` | `trip_imports` | Import pipeline: ICS file, ICS feed fetch and opt-in polling, pasted text, Google Maps export and pasted places; preview, confirm, undo, first-import reward call (section 5.4) | `trips`, `itinerary`, `flights`, `lodging`, `ai`, `billing` (promo pass), `notifications`, `providers.feed_fetcher` |
| `billing` | `plans`, `store_products`, `subscriptions`, `entitlements`, `trip_passes`, `store_transactions`, `webhook_events` | RevenueCat webhooks, entitlement computation, Trip Pass binding, the first-import reward pass (`grant_import_reward()`), restore and reconcile | `credits` |
| `credits` | `credit_ledger`, `credit_grants`, `credit_debts`, `credit_action_prices` | The only writer of credits: grants, reserve, settle, refund, expiry, spend ceilings | none (leaf) |
| `referrals` | `referral_codes`, `referral_rewards` | Referral codes, redeeming a code, qualification, reward grants, abuse checks, reject (07 section 9) | `credits`, `notifications` |
| `affiliate` | `affiliate_programs`, `affiliate_link_templates`, `link_clicks`, `affiliate_conversions`, `affiliate_payouts` | Link building from stored templates, the `/go/{click_id}` redirect, disclosure flags, conversion import, revenue reports | `providers` |
| `notifications` | `devices` (read), notification preference and delivery rows | Push, email, digest building, preference checks, quiet hours, collapse ids, unsubscribe | `providers.apns`, `providers.resend` |
| `admin` | `admin_users`, `feature_flags`, `kill_switches`, `audit_log`, `support_tickets`, `content_reports` | Admin console API, feature flags, kill switches, support tools, audit writes | every service (through audited functions) |

Later: Phase 2 or 3: the `concierge`, `groups` and `advisors` modules, and the households, polls, expenses, settlements, partner guides, print orders and advisor tables they own.

Cross-cutting code (not modules): `security/` (owns `rate_limit_counters` and `idempotency_keys`), `deps.py`, `errors.py`, `logging.py`, `providers/`. The analytics helper `analytics.capture(event, props)` lives in `hermi/analytics.py` and validates names against `packages/shared/src/events.ts`.

Boundary rules that tests enforce:

- Only `credits.service` writes `credit_ledger` and `credit_grants`. Only `billing.service` writes `entitlements`, `subscriptions`, `trip_passes` and `store_transactions`. A grep-based test fails on any other writer.
- Only `providers/*` import `httpx` or the Anthropic SDK. Modules call provider classes (AI calls go through the `modules/ai/client.py` facade, never `providers/ai/*` directly), which record a `provider_calls` row for every outbound call (provider, endpoint, cost units, latency, status, cached).
- Only `affiliate.service` builds outbound partner URLs. Templates come from `affiliate_link_templates`. No other module concatenates a partner URL.
- No module imports `worker`. Jobs are deferred through `jobs.enqueue(name, **args)` in `hermi/jobs.py`, which is a thin wrapper over Procrastinate's `defer_async` that uses the caller's transaction.
- Only `imports.service` writes `trip_imports`. It creates trips and items only by calling the owning module services, never their repositories.
- Only `providers/feed_fetcher.py` and `providers/link_preview.py` fetch a URL that a user supplied, and both go through `security/ssrf.py` (section 5.4). No other code opens a connection to a user-supplied host.

## 4. Request lifecycle

### 4.1 Authenticated request

1. **Edge.** Cloudflare terminates TLS, applies WAF and per-IP rate rules, and forwards to Render. The origin accepts traffic only from Cloudflare (authenticated origin pulls). `TRUSTED_PROXY_CIDRS` makes `X-Forwarded-For` trustworthy.
2. **Middleware order.** Request id (`X-Request-Id`, generated if absent) then access log start, CORS (explicit origins, including `capacitor://localhost`), body size limit (1 MB JSON, uploads go to R2 by signed URL), kill-switch check for maintenance mode, then the route.
3. **Authentication.** Dependency `CurrentUser` reads `Authorization: Bearer <jwt>` (bearer only, for web and iOS; there is no session cookie). It verifies the Supabase JWT: signature against the cached JWKS (selected by `kid`, refreshed on unknown `kid` at most once per minute), `iss` equals `SUPABASE_JWT_ISSUER`, `aud` equals `SUPABASE_JWT_AUDIENCE`, `exp` and `nbf` with 30 seconds of skew. It then maps `sub` through `auth_identities` to a `users` row, creating the user and the "Me" person on first sight in one transaction. With `AUTH_MODE=dev` the API instead accepts tokens signed by a local key pair, served at a local JWKS and minted for seeded personas (Free, Plus, admin) by the dev routes in 04; config refuses `AUTH_MODE=dev` unless `ENVIRONMENT` is `local` or `ci`. A user whose status is not `active` gets 403 `account_inactive` (`suspended` or `deleted`), and `pending_deletion` gets 403 `account_pending_deletion` so the app can offer recovery (04 section 1.2).
4. **Session variable.** `DbSession` opens a transaction and runs `SELECT set_config('app.user_id', :uuid, true)` (transaction-local). Row-level security policies on trip-owned tables read the variable through `app_user_id()` (03 section 6.2). The API database role has no `BYPASSRLS`. Jobs that act for a user set the same variable; system jobs use a separate role `hermi_worker` with `BYPASSRLS` (see [03-database-schema.md](03-database-schema.md) section 6.1).
5. **Tenant check.** Every route with a `trip_id` depends on `require_trip(trip_id, min_role)`. It returns a `TripAccess(trip, member, role, capabilities)` object, or raises `NotFound` (404, never 403) when the user is not a member or the trip is in trash. `min_role` is one of `viewer`, `editor`, `owner`. Routes that take a child id (an itinerary item, a lodging option) resolve the child, join up to its trip and then call the same function. No route calls `session.get(Model, id)` on a tenant table. A CI test walks `app.routes` and fails if a path with an id parameter does not resolve through `require_trip` or is not on the public allowlist.
6. **Entitlement and credit checks.** Routes that cost money call `entitlements.require(capability, trip)` first (402 with a `paywall` body naming the upsell, never a bare error), then `credits.reserve(user, action, trip)` for AI actions. Both are service calls, not decorators, so the order is visible in the code.
7. **Handler and response.** The handler returns a Pydantic model. Mutations on editable rows use `If-Match` with the row version; a mismatch returns 409 with the latest row. Lists support `updated_since` and ETag for cheap polling.
8. **Errors.** One handler renders `application/problem+json`: `type`, `title`, `status`, `code` (stable string), `detail`, `request_id`. Unhandled errors return a generic 500 body and go to Sentry with the request id.
9. **Log line.** One JSON line per request: `ts`, `level`, `service`, `env`, `release`, `request_id`, `user_id` (opaque UUID), `route` (template, not raw path), `status`, `latency_ms`, `bytes`. No bodies, no query strings with tokens.

### 4.2 Public and special requests

| Route class | Auth | Database access | Notes |
|---|---|---|---|
| `GET /health/live`, `/health/ready` | none | API role, no tenant tables | Ready checks database, migration head, queue reachability and reports the AI provider |
| `GET /go/{click_id}` | none | Allowlisted `SystemSession` | Never takes a URL from the request. Looks up a `link_clicks` row created by an authenticated call, builds the destination from `affiliate_link_templates`, logs, and 302s. Unknown or expired id goes to the trip page, never elsewhere |
| `GET /shared/{token}` | token | Allowlisted `SystemSession` | Read-only trip view with redaction flags, per-token throttle |
| `POST /webhooks/revenuecat`, `/webhooks/resend`, `/webhooks/supabase` | signature | Allowlisted `SystemSession` | Verify, insert into `webhook_events` by provider event id, return 200 fast, process in a job (section 5.1) |
| `GET /me` | JWT | API role under RLS | Session bootstrap |
| `/admin/*` | Cloudflare Access plus the admin session | Admin role (`DATABASE_URL_ADMIN`) | Separate middleware: Cloudflare Access (checked in the app by `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD`), the app layer and 2FA as in 08; every call writes `audit_log` |
| `GET /i/{token}` | none | Allowlisted `SystemSession` | Universal link landing, JSON for the app, HTML for the web fallback |
| `GET /calendar/{token}.ics` | token | Allowlisted `SystemSession` | Calendar subscription feed for one trip, read-only, throttled per token (section 5.5) |
| `GET /referrals/{code}` | none | `SECURITY DEFINER` function | Landing data for a referral link (inviter first name and the reward sentence); identical `404` for unknown, disabled and capped codes (04 section 5.27) |
| `GET /public/status`, `GET /public/how-we-earn` | none | API role, public sample pages through a `SECURITY DEFINER` function | Component summary for the in-app banner (the hosted status page is separate, section 8.1) and the data behind the public "How we earn" page (04 section 5.28). Cached 30 seconds and 1 hour |

Public token reads (share links, calendar feed, `/go`, public sample pages) and synchronous writes the API role cannot do directly (invite redemption, owner transfer, deletion requests, claim) use either an allowlisted `SystemSession` or a `SECURITY DEFINER` function that checks `app_user_id()`. A `SystemSession` is opened only by named service functions; the allowlist is one code constant with a test. Every route is tested under the real database roles in CI (the leak suite, 10 section 1.3).

### 4.3 Row-level security in detail

RLS is the second lock, not the first. Policies exist on: `trips`, `trip_members`, `trip_destinations`, `trip_people`, `flight_routes`, `chosen_flights`, `price_alerts`, `itinerary_days`, `itinerary_items`, `saved_places`, `lodging_options`, `lodging_votes`, `checklist_items`, `notes`, `runs`, `run_events`. The standard policy is `EXISTS (SELECT 1 FROM trip_members m WHERE m.trip_id = <table>.trip_id AND m.user_id = app_user_id())`. Tenant tables use `FORCE ROW LEVEL SECURITY` (see 03 section 6). The API and pytest refuse to start when the connected role is a superuser, has `BYPASSRLS`, or owns the tables; test fixtures write through the system connection (`DATABASE_URL_SYSTEM`), never as the owner. User-owned tables (`devices`, `people` by `owner_user_id`, `consents`, `credit_ledger`, `credit_debts`, `idempotency_keys`, `trip_imports`, `referral_codes`) use a direct `user_id = app_user_id()` policy; `referral_rewards` is readable by its referrer and its referee only; `content_reports` (insert and read your own) has its own policy. A test connects as the API role with no variable set and expects zero rows from every table with a policy. DDL is in [03-database-schema.md](03-database-schema.md).

### 4.4 Web and iOS differences

| Concern | Web | iOS (Capacitor) |
|---|---|---|
| Token storage | Supabase session in the browser (supabase-js storage), sent as a bearer header | Supabase session in the Keychain through a secure-storage plugin; bearer header |
| Origin | `https://app.hermi.world` | `capacitor://localhost` |
| CSRF | Not applicable (bearer) | Not applicable (bearer) |
| API base URL | `VITE_API_BASE_URL` | Same, compiled into the bundle |
| Push | None at launch | APNs token registered at `POST /devices` |
| Purchases | None in Phase 1. The paywall says "Upgrade in the iOS app" and links to the App Store; no web checkout, price list or purchase button | RevenueCat over StoreKit 2 |
| Android | Installable web app (manifest, service worker, "Add to Home screen" card on Android Chrome, install guide page) | Not applicable; native Android is Phase 2 |
| Sync state | "Synced N seconds ago" indicator from the last successful sync response (section 4.5) | Same |

### 4.5 Sync indicator and trust pages

**"Synced N seconds ago".** The client keeps one value per trip, `last_synced_at`: the time the last conditional request for that trip returned 200 or 304 (`updated_since` or ETag, 04 section 1.7), or the last queued edit was accepted. The trip header shows "Synced 12 s ago" (seconds under a minute, then minutes, then "Synced Sep 30, 14:05" after an hour), refreshed every 5 seconds on screen. States: `Syncing`, `Synced N s ago`, `Offline, N edits waiting` (the offline edit queue, 01 F-TRV-2) and `Could not sync, retrying` after three failed polls; tapping it runs a sync now. It reads only the client's own clock and response times, so it never claims a sync that did not happen. Screen readers hear a change of state only, never the ticking seconds.

**Static trust pages.** Four pages ship with the web build and are served without sign-in: `/how-we-earn` (renders `GET /public/how-we-earn`), `/billing` ("How billing works", plain text kept in the repository as Markdown and reviewed with every pricing change), `/install/android` (the Android install guide) and `/status` (a redirect to the hosted status page). The app links to each from Settings and the paywall; the iOS app opens them in the in-app browser.

## 5. Background jobs: how they run

Queue: Procrastinate on the application database. Four lanes (Procrastinate queues): `api` (short provider calls, 20 to 50 concurrent per worker), `ai` (Claude calls, 4 to 10 concurrent), `notify` (push and email, high concurrency), `batch` (polling and bulk work, 2 concurrent). The four lanes keep these names everywhere. Local concurrency is 4, 2, 4 and 1 for `api`, `ai`, `notify` and `batch`. `claude_cli` jobs run only on lane `ai` (concurrency 1 or 2), because each job spawns a `claude` process. User-visible work has a row in `runs` (status, events, cancel flag) and the job carries only `run_id`. Non-user jobs have no `runs` row; their history is Procrastinate's own job table plus a `job_heartbeats` view.

Common rules:

- **Fair claim.** Jobs carry `priority` (interactive 10, paid live-route checks 5, free cached-fare refreshes 1) and a per-account concurrency cap (Free 2, Plus 4). One agent run at a time per account, enforced by a partial unique index on running agent runs.
- **Queueing locks.** A job with a `queueing_lock` collapses duplicates while one is waiting. A `lock` serializes jobs with the same key while running.
- **Reaper.** Workers heartbeat every 15 seconds. The `reap_stale_jobs` job requeues anything whose heartbeat is older than 2 minutes (5 for the `ai` lane).
- **Shutdown.** On SIGTERM a worker stops claiming, lets jobs finish up to 60 seconds (`ai` jobs checkpoint and requeue), and exits.
- **Dead letters.** A job that exhausts retries is marked `failed`, appears in the admin console, and raises an alert when the count in a lane passes 5 in an hour.
- **Retry classes.** `transient` = 429, 5xx, timeouts, connection errors: exponential backoff with jitter (base 30 seconds, factor 2, cap 15 minutes), honoring `Retry-After`. `permanent` = 4xx other than 429, validation, budget exhausted, consent missing: no retry. `none` = do not retry, the next scheduled tick covers it.

### 5.1 Job catalogue

Times are UTC unless marked local. "Key" is the idempotency key: a second run with the same key does nothing (enforced by a unique index or `ON CONFLICT DO NOTHING`).

| Job | Lane | Trigger | Schedule | Idempotency key | Retries |
|---|---|---|---|---|---|
| `scan_due_routes` | api | Scheduler tick | Every 30 seconds (leader only) | `flight_routes.next_check_at` advanced in the same transaction | none |
| `check_fare_route` | api | Route scan tick, user "refresh", trip pass start (purchased or import reward) | Live routes daily within 120 days of departure, jittered in a 60 minute window by hash of route id | `(route_id, provider, time_bucket_6h)` on `provider_calls` | transient x5 |
| `refresh_cached_fares` | api | Scheduler | Every 6 hours for routes with `price_alerts` or free cached-fare tracking | `(route_id, bucket_6h)` | transient x5 |
| `evaluate_price_alerts` | notify | After `check_fare_route` or `refresh_cached_fares` writes `fare_observations` | Event | `(alert_id, observation_id)` | transient x3 |
| `run_ai_action` | ai | User action (`explain`, `live_search`, `draft_day`, `draft_trip`, `research`, `packing_list`, `booking_import`, `verify_extract`, `recheck`) | Event | `Idempotency-Key` header, unique per user | transient x2, refunds credits on final failure |
| `run_agent` | ai | User action | Event | `run_id` | transient x2 at turn boundaries only, never replays tool writes |
| `run_verify_plan` | ai | `POST /plan-verifications/{id}/check` | Event; checks up to 4 items at a time, one request per item (06 section 5.11) | `run_id`; each item is written once, so a retry skips items that already have a verdict | transient x2 per item, then the item is `unchecked` with `provider_error` and its credit is refunded |
| `warm_research_cache` | batch | Scheduler | Nightly 03:10 local to the US East region, Anthropic Batch API | `(destination, month, interest_bucket, model, prompt_version)` | transient x5 |
| `collect_batch_results` | batch | Scheduler | Every 10 minutes while a batch is open | `batch_id` | transient x10 |
| `settle_ai_usage` | ai | End of `run_ai_action` or `run_agent` | Event | `run_id` | transient x5 |
| `fetch_import_feed` | api | `POST /imports/ics-feed`, `POST /imports/{id}/refresh`, or `poll_import_feeds` | Event | `(import_id, bucket_15m)` | transient x2; the third consecutive failure marks the import `failed` |
| `poll_import_feeds` | batch | Scheduler | Every 30 minutes (leader only); enqueues `fetch_import_feed` for feeds with `poll_enabled` and `next_poll_at` due, so each feed is read every 6 hours | `(bucket_30m)` | none |
| `evaluate_booked_fare_drops` | notify | Scheduler | Nightly 09:00; reads the view `booked_fare_drops` and sends the alerts (at least 5 percent and 10 US dollars down, once per flight every 7 days) | `notifications.dedupe_key` `booked_drop:{chosen_flight_id}:{current_minor}` | transient x3 |
| `grant_referral_rewards` | api | Scheduler | Every 10 minutes; marks `pending` rewards `qualified` when the referee met the rule, then calls `grant_referral_reward()` | `credit_grants` `period_key` `referral:{reward_id}` | transient x5 |
| `reap_stale_jobs` | batch | Scheduler | Every minute | none (idempotent by nature) | none |
| `release_stale_reservations` | api | Scheduler | Every 5 minutes; releases credit reservations older than the run deadline plus grace | `(reservation_id)` | transient x3 |
| `maintain_partitions` | batch | Scheduler | Daily 02:30; creates upcoming partitions through a definer function and alerts when rows land in a default partition | `(table, month)` | transient x3 |
| `process_webhook_event` | api | Row inserted in `webhook_events` | Event | `(provider, provider_event_id)` unique | transient x10 over 24 hours |
| `reconcile_entitlements` | api | Scheduler | Every 6 hours, plus on demand from admin; calls RevenueCat REST for users with recent activity | `(user_id, day)` | transient x5 |
| `grant_monthly_credits` | api | Scheduler | Every hour; grants at each subscriber's monthly anniversary (annual plans) and at calendar month start for comped entitlements. Free accounts are not in this job: their 12 credits are written lazily on first use (`ensure_free_monthly_grant`, 03 section 5.13) | `(user_id, kind, period_key)` unique on `credit_grants` | transient x5 |
| `expire_credits` | api | Scheduler | Daily 02:00 | `(credit_grant_id)` | transient x3 |
| `expire_trip_passes` | api | Scheduler | Every 15 minutes | `(trip_pass_id, 'expired')` | transient x3 |
| `send_push` | notify | Event | Event | `(user_id, alert_id_or_event_id, channel)` unique | transient x5, 410 deletes the `devices` token |
| `send_email` | notify | Event | Event | `(user_id, template, dedupe_key)` unique | transient x5 |
| `build_digest` | notify | Scheduler | Hourly; the activity digest, sent at 08:00 local per user, max 1 per hour per trip | `(user_id, trip_id, date)`, deduplicated per user and trip | transient x3 |
| `send_predeparture_reminder` | notify | Scheduler | Hourly; the 7-day pre-departure reminder, at 09:00 local per user | `(user_id, trip_id, 'predeparture_7d')`, deduplicated per user and trip | transient x3 |
| `send_trial_ending_reminder` | notify | Scheduler | Hourly; reminds a user 2 days before the annual trial converts (01, 05 section 6) | `(user_id, 'trial_ending', period_key)`, deduplicated per user (a trial is per user) | transient x3 |
| `poll_invites_cleanup` | api | Scheduler | Daily 04:00 | none | none |
| `import_affiliate_conversions` | api | Scheduler | Nightly 05:00 per network (Travelpayouts, Viator, Stay22) | `(program_id, network_txn_id)` unique on `affiliate_conversions` | transient x5 |
| `refresh_fx_rates` | api | Scheduler | Daily 06:00 (Frankfurter) | `(base, date)` unique on `fx_rates` | transient x5 |
| `refresh_places_cache` | api | Lazy on read, sweep daily 03:30 | Delete expired rows per provider terms | `place_key` | none |
| `export_user_data` | batch | `POST /me/export` | Event; max 1 per day per user | `data_exports.id` | transient x3; 7 day link |
| `delete_account` | batch | `POST /me/delete` then 30 day timer | Event then day 30 | `deletion_requests.id` and a checklist row per step | transient x10, each step idempotent |
| `purge_trash` | batch | Scheduler | Daily 04:30; hard deletes trips deleted more than 30 days ago | `(trip_id)` | transient x3 |
| `retention_sweep` | batch | Scheduler | Daily 05:30; invites older than 30 days, IP hashing after 30 days, prompt content older than 30 days, previews, stored feed URLs and plan verifications on the schedule in 03 sections 5.9 and 5.20, `run_events` payloads older than 14 days, analytics older than 90 days, the 12-month purge of `identity_hashes`, audit rows by `retention_class` (03 section 8) | `(table, day)` | transient x3 |
| `purge_idempotency_keys` | api | Scheduler | Hourly; deletes `idempotency_keys` past `expires_at` | none | none |
| `expire_kill_switches` | api | Scheduler | Every minute; disengages switches past `kill_switches.expires_at`, writes `audit_log` as `system`, and warns the owner 15 minutes before expiry (08 section 6.5) | `(key, expires_at)` | none |
| `ai_spend_guard` | api | Scheduler | Every 5 minutes; sums `ai_usage`, trips the global circuit breaker, raises alerts | `(bucket_5m)` | none |
| `reconcile_anthropic_usage` | batch | Scheduler | Daily 06:30; pulls the Anthropic usage and cost admin API and compares it with `ai_usage` (alert above 3 percent) | `(date)` | transient x3 |
| `provider_quota_check` | api | Scheduler | Every 30 minutes (SerpApi account API, Geoapify, Travelpayouts rate limits) | `(provider, bucket_30m)` | none |
| `db_dump_offsite` | batch | Scheduler | Weekly, Sunday 03:00; encrypted `pg_dump` to R2 backups bucket, 90 day lifecycle | `(week)` | transient x3, alert on failure |
| `heartbeat_ping` | api | Scheduler | Every minute; pings Better Stack heartbeat URLs for scheduler and queue | none | none |

**Keyless rule.** A job whose provider key is missing (quota check, heartbeat, usage reconcile, offsite dump, conversions) logs and skips; it never fails the queue.

Later: Phase 2 or 3: concierge digests, group settle reminders and scheduled agent runs are not jobs in Phase 1. `scan_due_routes` only enqueues live fare route checks.

### 5.2 Scheduler design

The scheduler is a loop inside `hermi_worker/scheduler.py`. It enqueues work; it never runs it.

1. **Leader election.** On start it tries `pg_try_advisory_lock(0x57415946)` on a dedicated connection. The holder is the leader; others sleep 10 seconds and retry. If the leader's connection drops, the lock frees and a standby takes over within 10 seconds.
2. **Route scan.** Every 30 seconds the leader scans `flight_routes` where `next_check_at <= now()` with `FOR UPDATE SKIP LOCKED` (limit 500). For each row it checks eligibility (step 5), the kill switch and the account's budget (reserve in the same transaction), inserts the `runs` row (`trigger = 'schedule'`), defers the job, and advances `next_check_at` to the next slot after now (never stacking missed slots). An outage of a day fires one check, not many.
3. **Jitter.** `next_check_at` = slot plus `hash(route_id) mod window`, window 60 minutes for daily checks. This spreads load and is stable per route.
4. **Periodic jobs.** Fixed-schedule jobs in section 5.1 use Procrastinate periodic tasks registered on the leader only, so they never double-fire. Each has the `slot` timestamp as its lock key.
5. **Live-route eligibility.** A route is scheduled only if the trip's best capability allows it (Plus 3, Trip Pass 2 per trip, including an import-reward Trip Pass), the departure is within 120 days, and the trip pass has live checks left (60 max). When eligibility ends, `next_check_at` is cleared and the route keeps its last fares.
6. **Scheduled agents.** Scheduled agents are Phase 2 (Pro) and no kind of them exists in Phase 1. The scan only enqueues live-route checks.
7. **Observability.** Each tick writes `scheduler_ticks` metrics (due count, enqueued, skipped by reason, tick duration). A heartbeat URL is pinged each minute; a missing ping for 3 minutes pages.

### 5.3 Provider call flow inside a job

```
job starts -> set app.user_id (or system role) -> load run row -> check kill switch and consent
  -> cache lookup by cache_key (provider_calls / shared_research_cache / fare_observations bucket)
  -> hit: return, record provider_calls(cached=true)
  -> miss: take queueing lock on cache_key, call provider, record provider_calls(cost_units, latency, status)
  -> write results in one transaction -> settle credits and spend -> emit run_events -> enqueue notifications
```

### 5.4 Import pipeline and the SSRF guard

Imports bring an existing plan into Hermi from a calendar file, a calendar feed, pasted booking text, a Google Maps export or pasted places. The import screen has entries named for TripIt, Tripsy and Wanderlog that route to these same methods with instructions for each; the entry used is stored as `trip_imports.origin`. One rule governs all of them: an import only proposes. Nothing reaches a trip until the user reviews a preview and confirms. Routes, limits and response shapes are in [04-api-spec.md](04-api-spec.md) section 5.26, the table is `trip_imports` (03 section 5.9), and the AI feature is `booking_import` (06 section 5.3).

| Source | Entry (04) | Work | Parsing |
|---|---|---|---|
| ICS file (a TripIt single-trip export, a Google Calendar export, any `.ics`) | `POST /imports/ics-file`, multipart, max 2 MB | Parsed in a size-limited sandbox, inside the request for normal files | A maintained RFC 5545 library; `VEVENT` only; deterministic classification first |
| ICS feed (a TripIt calendar feed, a Google Calendar secret address) | `POST /imports/ics-feed` with an address | Job `fetch_import_feed` (the route returns 202; the client polls `GET /imports/{id}`) | Same parser |
| Pasted booking text | `POST /imports/paste`, text up to 12,000 characters | A `booking_import` run on the `ai` lane | One Haiku call, strict JSON schema, no tools |
| Google Maps saved list (Takeout CSV, GeoJSON or KML) | `POST /imports/maps-file`, multipart, max 5 MB | Parsed in the same sandbox, inside the request | No AI: each title is matched by place search (Geoapify) |
| Pasted places (for example a list copied from Wanderlog or Google Maps) | `POST /imports/places`, text up to 20,000 characters | Inside the request | No AI: one place per line, matched by place search |

**Flow.**

1. **Preview.** The `trip_imports` row moves through `received`, `parsing` and `review`. Candidates are stored in `preview`. The raw file and pasted text are never stored (only the preview and the created rows are kept); a feed address is stored encrypted only while polling is on (below); a Google Maps list link is never fetched, stored or resolved (04 section 5.26, rule 5). Previews are deleted on the schedule in 03 section 5.9.
2. **Confirm.** `POST /imports/{id}/confirm` runs one transaction. It creates the trip when the target is new, then creates `itinerary_items` (flights and reservations, `source = 'import'`) and `lodging_options` (stays) by calling the owning module services, each stamped with `import_id` and `import_uid`, and sets the status to `applied`. A flight with a paid amount can also create a cached-mode route and the booked-fare fields on `chosen_flights`, which starts the booked-fare drop alert (5.6). When the commit succeeds, `imports.service` calls `billing.service.grant_import_reward()` for the free first-import Trip Pass (07 section 10), which applies the settled conditions: at least 3 items including a flight or a stay, a verified email, no active pass on the trip, no active Plus, once per user.
3. **Undo.** Rows an import created carry `import_id`, so one tap removes them.

**Limits.** One table of numbers, mirrored from 04 section 5.26 (the authority; there is no second set):

| Source | Maximum size | Maximum items | Rate limit |
|---|---|---|---|
| ICS file | 2 MB | 500 events; description extraction at most 3 AI calls (18 events) | 20 previews a day |
| ICS feed body | 2 MB | 500 events; description extraction at most 3 AI calls (18 events) | 5 registrations a day, 4 refreshes a day per import; counts toward the 20 previews a day |
| Pasted booking text | 12,000 characters | 1 AI call | 20 previews a day (file, paste and feed together) |
| Google Maps file | 5 MB | 200 places | 20 previews a day |
| Pasted places | 20,000 characters | 200 places | 20 previews a day |

**Import sandbox.** `IMPORT_SANDBOX` is `strict` (POSIX resource limits and a process sandbox) or `timeout_only` (win32 and local: a wall-clock timeout plus a `psutil` memory kill).

**Pasted text and event descriptions.** `ai.service` runs the `booking_import` feature: personal data is replaced with placeholders locally first (06 section 12.3), Haiku (`AI_MODEL_FAST`) is called with no tools at all (no web search, no web fetch), the output must match a strict JSON schema, and every extracted value must appear in the source text. The pasted text is data, never instructions. One call costs 1 credit (the `explain` price, refunded when nothing is recognized) and the kill switch is `ai.import`. The text never appears in logs, `run_events`, Sentry or the shared research cache.

**SSRF guard.** `security/ssrf.py` is the only way to fetch a user-supplied address. Its callers are `providers/feed_fetcher.py` and `providers/link_preview.py`. Rules, in order:

1. Scheme `https` only (`webcal://` is rewritten), port 443 only, no userinfo, the host is a DNS name and not an IP literal, at most 2,048 characters.
2. Refuse the hosts of Airbnb, Vrbo and Booking.com and Hermi's own hosts. The first list is one code constant, `BLOCKED_HOSTS` (06 section 2.4), holding the three brands `airbnb`, `vrbo` and `booking`. A host is blocked when its registrable-domain label equals a brand, with any ending and any subdomain (so `airbnb.co.kr`, `www.airbnb.co.uk`, `vrbo.com` and `secure.booking.com` are refused). The API blocklist and the CLI rules are generated from it, and the stream check stays as a backstop. No setting, flag or admin screen can change it, and one test covers those four hosts. Product rule 3: the user can download the file and upload it instead (`blocked_source`).
3. Resolve DNS ourselves and refuse the fetch if any answer is not a public address: loopback, private (RFC 1918), link-local (including the cloud metadata address 169.254.169.254), carrier-grade NAT `100.64.0.0/10`, multicast, reserved, unspecified, IPv6 loopback, unique local and link-local, and IPv4-mapped, 6to4 or NAT64 forms of any of these.
4. Connect to the validated IP address (pinned), send the original name in SNI and `Host`, and verify the certificate against that name, so DNS cannot change between the check and the connection.
5. Follow at most 3 redirects and revalidate every hop from rule 1.
6. Limits: 5 second connect timeout, 15 second total, body at most 2 MB (streamed and cut, also after decompression), and the body must start with `BEGIN:VCALENDAR`. No cookies and no authorization headers. `User-Agent: HermiCalendarImport/1.0`.
7. The fetch job runs on a worker whose outbound traffic goes through a fixed egress proxy with its own deny rules for private ranges, the database and metadata services, as defense in depth ([10-quality-security-launch.md](10-quality-security-launch.md)).
8. Every attempt writes a `provider_calls` row (provider `feed_fetcher`, host only, status, bytes, blocked reason).
9. The address is stored encrypted with `FIELD_ENCRYPTION_KEY` in `trip_imports.feed_url_enc` because feed addresses often carry a secret token. It is kept only while "Keep checking this calendar" is on. It is shown back as the host plus a masked path and deleted when polling is turned off, on discard, on expiry of an unconfirmed import and on account deletion. Logs and Sentry redact it.
10. A table-driven suite of hostile addresses must all be refused in CI: decimal, octal and hex IPs, IPv6 forms, `localhost` variants, `@` userinfo, unicode hosts, DNS answers that flip to a private address, and redirects to the metadata address. The fake feed host is allowed only when `ENVIRONMENT` is `local` or `ci`.

**Feed polling (opt-in).** After the first preview is confirmed, a person can turn on "Keep checking this calendar" for a feed import. It is off by default and never switched on for them. Polling uses these columns on `trip_imports` (03 section 5.9 defines them): `poll_enabled`, `next_poll_at`, `last_polled_at`, `last_content_hash`, `consecutive_failures`, and `feed_url_enc` and `pending_changes` for the stored address and the diff awaiting review. The switch is the database function `set_import_polling()`, at most 3 polled feeds per person.

- `poll_import_feeds` (batch lane, leader only, every 30 minutes) selects feeds with `poll_enabled` and `next_poll_at <= now()` (`FOR UPDATE SKIP LOCKED`, limit 500) and enqueues `fetch_import_feed` for each. After a fetch the job sets `next_poll_at` to 6 hours later, so each feed is read every 6 hours. Polling stops 7 days after the trip ends. The platform allows at most 60 fetches an hour to one destination host.
- A fetch sends a conditional request and compares the content hash with `last_content_hash`. If events are new or changed, the job builds a change preview (only new, changed and removed events, matched by `import_uid`, the same result as `POST /imports/{id}/refresh`), stores it in `pending_changes` and sends one push and in-app notice: "Your calendar changed: 3 updates to review".
- Polling never applies anything by itself. The person reviews the preview and confirms the changes they want (`POST /imports/{id}/changes/confirm`); removed events are listed, never deleted for them. An unreviewed change preview is deleted after 30 days.
- Three consecutive failures turn polling off, delete the stored address, and tell the user (`calendar_poll_stopped`). The kill switches `import.polling` and `import.all` stop fetches. Polling is one way: Hermi never writes to the user's calendar.

### 5.5 Calendar feed endpoint

A trip can publish a live calendar subscription that phones and desktop calendars refresh on their own (04 section 5.29). It is available on every tier and does not count as a collaborator or a share link.

- **Token.** 256 random bits, stored only as `trips.calendar_token_hash` (SHA-256, unique index `uq_trips_calendar_token`). The URL is returned once, by `POST /trips/{trip_id}/calendar-token`, which also rotates it. Rotating or `DELETE /trips/{trip_id}/calendar-token` stops the old URL at once.
- **Endpoint.** `GET /v1/calendar/{token}.ics` (04 section 5.29 is the authority), served at `https://api.hermi.world/v1/calendar/{token}.ics`. The token is the credential: no JWT, no cookie. Unknown, rotated or disabled tokens and deleted trips return an empty `404`, never `403`. Limits: 120 an hour per token and 600 an hour per IP, and unknown tokens count against the IP limit.
- **Content.** Generated by the `itinerary` module from current rows: timed events in the destination's time zone, all-day events, booked stays from check-in to check-out, and chosen flights, with stable `UID` values, `SEQUENCE` from the row version, `REFRESH-INTERVAL` of one hour and at most 2,000 events. Never included: prices, paid amounts, confirmation numbers, private notes, people, partner links or click ids.
- **HTTP.** `ETag` over the content with `If-None-Match` answered `304`, `Cache-Control: private, max-age=300`, `Referrer-Policy: no-referrer`. Cloudflare does not cache it, because the URL is a bearer secret.
- **Logging.** The access log records only the route template `/v1/calendar/{token}.ics`. `last_fetched_at` is updated at most once a minute.

### 5.6 Booked-fare drop alert

The booked-fare drop alert tells a traveler when the fare for a flight they already booked has fallen, so they can check the airline's change and credit rules. It is a notification, not a refund promise.

- **Setup.** When the user marks a chosen flight booked they can enter what they paid (`chosen_flights.paid_minor`, `paid_currency`, `booked_at`, `booked_by`), or an import fills it. `drop_alert_enabled` is on by default and the user can turn it off per flight. Flag `booked_fare_alerts`. It works on every tier, costs no credits and does not count toward the `price_alerts` cap.
- **Data.** No extra provider calls: it reads the shared `fare_observations` that `refresh_cached_fares` (every 6 hours) and live checks on Plus and passes already write. A match has the same origin, destination, dates, cabin and party size as the chosen flight (04 section 5.8).
- **Job.** `evaluate_booked_fare_drops` (notify lane, nightly at 09:00 UTC, worker role) reads the view `booked_fare_drops`: one row per booked flight with a matching observation from the last 48 hours priced below what the user paid, converted to the paid currency with `fx_convert_minor()`. It applies the thresholds in the setting `setting_booked_fare_drop` (`min_drop_pct` 5, `min_drop_usd` 10 after conversion, `min_days_between` 7), skips a row whose price is not lower than `last_drop_notified_minor` and a flight already alerted in the last 7 days, and writes a `notifications` row with the dedupe key `booked_drop:{chosen_flight_id}:{current_minor}`, which makes a rerun harmless. A missing FX rate skips the row; no made-up number is ever shown.
- **Message.** "You paid $412. It is now $368. Check the airline's change and credit rules." The copy is fixed. It never says a refund or free change is available, it says where and when the price was seen, and it links to the trip screen and the airline's own rules page, never a partner link. Delivery uses `send_push`, then `send_email`, honoring the price-alert preference.
- **Stops.** After departure, when the paid amount is cleared, or when `drop_alert_enabled` is turned off. Kill switches `provider.travelpayouts` (no new observations) and `push.all` apply.

## 6. Caching layers

There is no Redis at launch. Every layer below is in Postgres, in process memory, or at the edge.

| Layer | What | Where | Key | TTL | Invalidation |
|---|---|---|---|---|---|
| Edge static | Web build, fonts, images, brand assets | Cloudflare CDN and Pages | Content hash in file name | 1 year immutable for hashed assets, `no-cache` for `index.html` | Deploy |
| Edge API | Public GETs only: `GET /shared/{token}` JSON, public sample trips, AASA file | Cloudflare | URL | 60 seconds, `stale-while-revalidate` 5 minutes | Purge by tag on share link revoke |
| Client query cache | Trip data | TanStack Query, persisted to IndexedDB (SQLite later if needed) | Query key prefixed by user id | `gcTime` 30 days, `staleTime` 30 seconds on shared trips | Sign-out clears; `updated_since` poll merges |
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

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `ENVIRONMENT` | `local`, `ci`, `preview`, `staging`, `production`. Tests refuse to run when `production` | `staging` | No | `local` |
| `RELEASE_SHA` | Git SHA of the image, tagged onto logs, Sentry and metrics | `a1b2c3d` | No | `dev` |
| `LOG_LEVEL` | Log verbosity | `INFO` | No | `DEBUG` |
| `PORT` | API listen port. The API binds `127.0.0.1` locally, never `0.0.0.0` (section 2) | `8100` | No | `8100` |
| `PUBLIC_API_URL` | Public base URL of the API, used in links and webhooks | `https://api.hermi.world` | No | `http://127.0.0.1:8100` |
| `PUBLIC_WEB_URL` | Public web app URL, used in emails and invites | `https://app.hermi.world` | No | `http://localhost:5173` |
| `CORS_ALLOWED_ORIGINS` | Comma list of allowed origins, including Capacitor | `https://app.hermi.world,capacitor://localhost` | No | `http://localhost:5173` |
| `TRUSTED_PROXY_CIDRS` | Networks whose `X-Forwarded-For` is trusted | `173.245.48.0/20,...` | No | empty |
| `API_DOCS_ENABLED` | Serves `/docs` (off in production) | `false` | No | `true` |
| `SCHEDULER_ENABLED` | Whether this process runs the scheduler loop | `true` | No | `false` in local runs, `true` only to test jobs |
| `WORKER_LANES` | Lanes this worker serves | `api,ai,notify,batch` | No | `api,ai,notify,batch` |
| `WORKER_CONCURRENCY_API` / `_AI` / `_NOTIFY` / `_BATCH` | Concurrent jobs per lane | `30` / `6` / `50` / `2` | No | `4` / `2` / `4` / `1` |

**Database**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `DATABASE_URL` | App role connection (`hermi_api_login`, DML only, no `BYPASSRLS`) | `postgresql+psycopg://hermi_api_login:...@host/hermi` | Yes | `hermi_api_login` on `localhost`, database `hermi` |
| `DATABASE_URL_SYSTEM` | System role for jobs that cross tenants (`hermi_worker_login`) | `postgresql+psycopg://hermi_worker_login:...@host/hermi` | Yes | `hermi_worker_login`, database `hermi` |
| `DATABASE_URL_ADMIN` | Admin console role (`hermi_admin_login`) | `postgresql+psycopg://hermi_admin_login:...@host/hermi` | Yes | `hermi_admin_login`, database `hermi` |
| `MIGRATION_DATABASE_URL` | DDL role, used only by `migrate` (`hermi_migrate_login`, which acts as `hermi_owner`; `hermi_owner` itself is NOLOGIN) | `postgresql+psycopg://hermi_migrate_login:...@host/hermi` | Yes | `hermi_migrate_login`, database `hermi` |
| `DATABASE_POOL_SIZE` / `DATABASE_MAX_OVERFLOW` | Pool size per process | `10` / `5` | No | `5` / `2` |
| `DATABASE_STATEMENT_TIMEOUT_MS` | Per-statement timeout (the migration role overrides) | `15000` | No | `15000` |
| `TEST_DATABASE_URL` | Test database as `hermi_api_login`; CI and local only | `postgresql+psycopg://hermi_api_login:...@localhost/hermi_test` | Yes | `hermi_api_login`, database `hermi_test` |
| `TEST_DATABASE_URL_SYSTEM` | Test database as `hermi_worker_login`; fixtures write through it, never as the owner | `postgresql+psycopg://hermi_worker_login:...@localhost/hermi_test` | Yes | `hermi_worker_login`, database `hermi_test` |
| `TEST_MIGRATION_DATABASE_URL` | Test database as `hermi_migrate_login`; migration tests and role checks | `postgresql+psycopg://hermi_migrate_login:...@localhost/hermi_test` | Yes | `hermi_migrate_login`, database `hermi_test` |
| `REDIS_URL` | Empty until Redis is added (about 10k MAU) | empty | Yes | empty |

**Identity and device trust**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `AUTH_MODE` | `supabase` (verify Supabase JWTs) or `dev` (tokens signed by a local key pair, served at a local JWKS, minted for seeded personas by 04's dev routes). Config refuses `dev` unless `ENVIRONMENT` is `local` or `ci` | `supabase` | No | `dev` |
| `SUPABASE_URL` | Supabase project URL | `https://abc.supabase.co` | No | empty |
| `SUPABASE_JWKS_URL` | Signing keys for JWT verification | `https://abc.supabase.co/auth/v1/.well-known/jwks.json` | No | empty (the local JWKS is used) |
| `SUPABASE_JWT_ISSUER` / `SUPABASE_JWT_AUDIENCE` | Expected `iss` and `aud` | `https://abc.supabase.co/auth/v1` / `authenticated` | No | empty |
| `SUPABASE_SERVICE_ROLE_KEY` | Delete users on account deletion, admin lookups | `eyJ...` | Yes | empty (deletion skips the Supabase call) |
| `SUPABASE_AUTH_HOOK_SECRET` | Verifies Supabase Auth hook calls | `whsec_...` | Yes | empty |
| `APPLE_TEAM_ID` / `APPLE_BUNDLE_ID` | App identity for App Attest and Apple APIs | `ABCDE12345` / `world.hermi.ios` | No | empty |
| `APPLE_SIGNIN_KEY_ID` / `APPLE_SIGNIN_PRIVATE_KEY` | Sign in with Apple key, used to revoke tokens on deletion | `K1234` / PEM | Key id no, key yes | empty |
| `APPLE_APP_ATTEST_ENV` | `development` or `production` attestation | `production` | No | empty |
| `FIELD_ENCRYPTION_KEY` | Encrypts rare sensitive fields (Apple refresh token, calendar feed addresses while polling is on) | base64 32 bytes | Yes | generated by `npm run setup` |

**AI**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `AI_PROVIDER` | Backend for product AI: `anthropic_api`, `claude_cli` or `fake` (guards in section 7.2) | `anthropic_api` | No | `claude_cli` on the owner's machine; `fake` in tests, CI and smoke runs |
| `ANTHROPIC_API_KEY` | One workspace per environment with a spend limit | `sk-ant-...` | Yes | empty |
| `ANTHROPIC_ADMIN_API_KEY` | Usage reconcile against Anthropic's usage report (WF-056) | `sk-ant-admin-...` | Yes | empty (the job logs and skips) |
| `AI_CLI_ALLOWED_EMAILS` | Comma list of users who may use `claude_cli` when `AUTH_MODE` is not `dev` | `me@example.com` | No | empty |
| `AI_CLI_MAX_CONCURRENCY` | Parallel `claude` processes, 1 or 2 | `1` | No | `1` |
| `AI_CLI_SCRATCH_DIR` | Empty working folder for each `claude` call | `.data/ai-scratch` | No | `.data/ai-scratch` |
| `CLAUDE_CLI_PATH` | Dev only, optional path to the native `claude.exe` (renamed from the old `CLAUDE_PATH`) | `C:\Users\me\.local\bin\claude.exe` | No | empty (`find_claude` looks it up) |
| `AI_MODEL_FAST` | Haiku model id (short answers, page summaries, pasted-text import) | `claude-haiku-4-5` | No | `claude-haiku-4-5` |
| `AI_MODEL_MAIN` | Sonnet model id | `claude-sonnet-5-5` | No | `claude-sonnet-5-5` |
| `AI_GLOBAL_DAILY_CAP_USD` | Hard maximum for total daily spend ($150). The flag `setting_ai_global_daily_usd` defaults to 150 and may only lower it | `150` | No | `150` |
| `AI_ALERT_DAILY_MULTIPLIER` | Alert when daily spend passes this times the 7 day average | `1.5` | No | `1.5` |
| `PROMPT_VERSION` | Current prompt set, part of shared cache keys | `2026-10-01.1` | No | `dev` |
| `EVALS_LIVE` | Live evals run only when it is `1` | `0` | No | `0` |

**Payments**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `REVENUECAT_WEBHOOK_SECRET` | Authorizes RevenueCat webhook calls | random | Yes | empty (the dev webhook signs with a fixed local value) |
| `REVENUECAT_API_KEY` | REST key for reconcile | `sk_...` | Yes | empty |
| `VITE_REVENUECAT_KEY_IOS` | Public SDK key for iOS | `appl_...` | No | empty |

**Modes and backends**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `PROVIDERS_MODE` | `fake`: every external data provider returns recorded fixtures (the default in `ci` and `local`). `live`: real calls; a provider with no key raises `NotConfigured`. Required `live` in staging and production | `live` | No | `fake` |
| `STORAGE_BACKEND` | `local` (files under `.data/storage`) or `r2` | `r2` | No | `local` (objects served by the API through signed, expiring URLs) |
| `EMAIL_BACKEND` | `console`, `file` or `resend`. SES stays the manual standby in section 8, not a config value | `resend` | No | `file` (`.data/outbox`) |
| `IMPORT_SANDBOX` | `strict` (POSIX resource limits and a process sandbox) or `timeout_only` (win32 and local: a wall-clock timeout plus a `psutil` memory kill) | `strict` | No | `timeout_only` |

**Data, affiliate and travel providers**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `TRAVELPAYOUTS_TOKEN` | Cached fares API | random | Yes | empty (fixtures) |
| `TRAVELPAYOUTS_MARKER` | Affiliate marker (appears in partner URLs) | `123456` | No | empty |
| `VIATOR_API_KEY` | Viator partner API | random | Yes | empty (fixtures) |
| `STAY22_AID` | Stay22 affiliate id | `hermi` | No | `hermi` |
| `SERPAPI_API_KEY` | Live fares and rentals, behind flag `serpapi_live_fares` | random | Yes | empty |
| `SERPAPI_MONTHLY_CAP` | Global search cap | `5000` | No | `5000` |
| `GEOAPIFY_API_KEY` | Places and geocoding | random | Yes | empty (fixtures) |
| `WIKIMEDIA_CONTACT` | Required contact for Wikipedia API | `support@hermi.world` | No | `dev@localhost` |
| `FRANKFURTER_BASE_URL` | FX rates | `https://api.frankfurter.dev` | No | same (fixtures while `PROVIDERS_MODE=fake`) |

**Messaging, storage, observability**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `RESEND_API_KEY` / `RESEND_WEBHOOK_SECRET` | Email send and bounce webhooks | `re_...` / `whsec_...` | Yes | empty |
| `EMAIL_FROM` | From address | `Hermi <hello@hermi.world>` | No | `Hermi <dev@localhost>` |
| `UNSUBSCRIBE_SECRET` | Signs one-click unsubscribe links | random | Yes | generated by `npm run setup` |
| `APNS_KEY_ID` / `APNS_TEAM_ID` / `APNS_PRIVATE_KEY` | Token-based APNs auth | `K5678` / `ABCDE12345` / PEM | Key id and team no, key yes | empty (push is logged) |
| `APNS_TOPIC` / `APNS_USE_SANDBOX` | Bundle id topic, sandbox switch | `world.hermi.ios` / `false` | No | empty / `true` |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | R2 S3 credentials | random | Id no, others yes | empty |
| `R2_ENDPOINT_URL` | R2 S3 endpoint | `https://<account>.r2.cloudflarestorage.com` | No | empty |
| `R2_BUCKET_UPLOADS` / `R2_BUCKET_EXPORTS` / `R2_BUCKET_BACKUPS` | Buckets | `hermi-uploads` | No | empty |
| `SENTRY_DSN` / `VITE_SENTRY_DSN` | Error reporting (DSN is not sensitive but is configured per environment) | `https://...@sentry.io/1` | No | empty |
| `SENTRY_AUTH_TOKEN` | CI only: upload source maps and dSYMs | `sntrys_...` | Yes | empty |
| `POSTHOG_KEY` / `VITE_POSTHOG_KEY` / `POSTHOG_HOST` | Product analytics | `phc_...` / `https://us.i.posthog.com` | No | empty |
| `BETTERSTACK_SOURCE_TOKEN` | Log shipping | random | Yes | empty |
| `BETTERSTACK_HEARTBEAT_SCHEDULER` / `_QUEUE` | Heartbeat URLs | `https://uptime.betterstack.com/api/v1/heartbeat/...` | Yes (URL is a bearer) | empty (heartbeats skipped) |
| `ALERT_WEBHOOK_URL` | Chat channel for alerts | `https://hooks.slack.com/...` | Yes | empty (alerts log only) |

**Admin and web client**

| Name | Purpose | Example | Secret | Local |
|---|---|---|---|---|
| `ADMIN_AUTH_MODE` | Admin sign-in mode: `cf_access` (Cloudflare Access plus the app layer and 2FA, 08 section 2) or `dev` (local and ci only). The sign-in domain and the IP or device policy are enforced at the Cloudflare Access edge (08 sections 2 and 9), not in the app | `cf_access` | No | `dev` (the fake-Access signer) |
| `CF_ACCESS_TEAM_DOMAIN` / `CF_ACCESS_AUD` | Cloudflare Access team domain and application audience the admin API checks | `hermi.cloudflareaccess.com` / random | No | empty |
| `ADMIN_SESSION_SECRET` | Signs admin session cookies (08 section 2) | random | Yes | generated by `npm run setup` |
| `VITE_API_BASE_URL` | API origin used by the web and iOS bundles | `https://api.hermi.world` | No | `http://127.0.0.1:8100` |
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | Client sign-in | `https://abc.supabase.co` / `eyJ...` | No (anon key is public by design) | empty (dev sign-in) |
| `VITE_APP_ENV` | Shown in the settings footer and Sentry | `production` | No | `local` |
| `STATUS_PAGE_URL` / `VITE_STATUS_PAGE_URL` | The hosted public status page, linked from Settings and the `/status` redirect | `https://status.hermi.world` | No | empty |

`config.py` enforces the Local column: a variable empty in Local is optional, and a missing optional key makes its provider raise `NotConfigured`. Empty is fine in Local for every `SUPABASE_*`, `ANTHROPIC_API_KEY`, `TRAVELPAYOUTS_*`, `GEOAPIFY_API_KEY`, `SERPAPI_*`, `RESEND_*`, `R2_*`, `SENTRY_*`, `POSTHOG_*`, `APNS_*`, `APPLE_*` and `REVENUECAT_*`.

### 7.2 Rules

- Separate values per environment. Never reuse a production key in staging, preview or CI.
- Production secrets live in Render environment groups (`hermi-prod-shared`, `hermi-prod-api`, `hermi-prod-worker`). GitHub holds only deploy credentials through OIDC and the `SENTRY_AUTH_TOKEN`.
- `config.py` exposes `settings.public_dict()` for the `GET /config` route (minimum app version, enabled feature keys), which never includes a secret field. A unit test asserts every field marked secret is excluded.
- Process environment overrides `.env`. `.env.example` is local-ready: it runs the app with no keys, with `AI_PROVIDER=claude_cli`.
- Config refuses these outside `local` and `ci`: `AUTH_MODE=dev`, `ADMIN_AUTH_MODE=dev`, `STORAGE_BACKEND=local`, `EMAIL_BACKEND` other than `resend`, `PROVIDERS_MODE=fake`.
- Config allows `AI_PROVIDER=claude_cli` only when `ENVIRONMENT=local`, the server is bound to loopback (`127.0.0.1`, `::1`, `localhost`) and `AUTH_MODE=dev` or the user is in `AI_CLI_ALLOWED_EMAILS`; the provider factory re-checks the user part on every call. Staging and production need `ANTHROPIC_API_KEY` and `AI_PROVIDER=anthropic_api` (`render.yaml` pins it). `/health/ready` reports the provider.
- Redaction: the log filter masks any value whose key matches `key|secret|token|password|authorization|cookie|dsn` and any JWT-shaped string.

## 8. Third-party services

| Service | Purpose | Failure behavior |
|---|---|---|
| Supabase Auth | Sign-in (Apple, Google, email code), JWT issuing | Existing sessions keep working (JWKS cached, tokens verified locally). New sign-ins fail with a friendly screen and a status link. Email code delivery goes through Resend SMTP. Local: dev sign-in (`AUTH_MODE=dev`) |
| Anthropic Claude API (`anthropic_api`; `claude_cli` is dev only, local replacement below) | All AI features | Non-urgent `ai` lane pauses on repeated 429 or 5xx; users see "queued, we will finish this when the service recovers" and credits stay reserved up to 30 minutes, then release. Cached data keeps working. Kill switch `ai.all`. Local: the owner's `claude` CLI or `fake` |
| Anthropic Batch API | Cache warming | Missed night means stale research; the next night catches up |
| Render | Compute and Postgres | Multi-instance API survives one instance loss. Regional outage: status page, restore plan in the runbook |
| Cloudflare (DNS, WAF, Pages, R2, Access) | Edge, web hosting, storage, admin sign-in (Access plus the app layer and 2FA, 08) | Access outage: the admin console is unreachable, the product is unaffected. Pages outage: the iOS app still works because it is bundled. R2 outage: uploads and exports fail with retry, trips keep working. Local: `.data/storage` for R2, a fake-Access signer for Access |
| RevenueCat | Purchases, entitlement events | Webhook backlog delays unlock; `POST /purchases/sync` gives instant unlock for the buyer. Outage: entitlements come from our own table, so nothing locks. Reconcile job catches up |
| Travelpayouts | Cached fares and affiliate network | Fare cards show last observation with its age; alerts (including booked-fare drop alerts) pause; affiliate links still work |
| SerpApi | Live fares and rentals, flag `serpapi_live_fares` | Flag off or quota out: live checks fall back to cached fares and say so; credits are not charged for an empty result |
| Geoapify | Places and geocoding | Serve `places_cache`; search shows "search is limited right now"; manual place entry still works |
| Wikipedia and Wikimedia | Destination summaries and photos | Skip the summary; no error shown |
| Frankfurter | FX rates | Use the last stored `fx_rates` row, show its date |
| Viator, Stay22, other affiliate networks | Affiliate link templates, tours | Card hidden if the program's kill switch is on. Links are templates, so a provider outage only breaks the partner page |
| APNs | Push | Retry transient errors; 410 deletes the device token; the in-app feed still shows the alert |
| Resend | Email (invites, receipts, digests, auth codes) | Retry; invites can also be shared as links; if down over 30 minutes, move sending to the standby SES account by hand (a manual standby, not a config value). Local: the file outbox (`EMAIL_BACKEND=file`) |
| Sentry | Errors | Errors log locally; the app is unaffected |
| PostHog | Product analytics | Events dropped after a short local buffer; nothing user-visible |
| Better Stack | Logs, uptime, heartbeats, the public status page (section 8.1) | Logs also stay in Render for 7 days; the status page is served by Better Stack, so it stays up when our own services are down |
| App Store Connect, TestFlight | Release and review. Builds run on a GitHub-hosted macOS runner (section 10) | Releases delayed; server stays backward compatible with the last 3 app versions |
| Apple App Attest / DeviceCheck | Free-credit abuse control | If unavailable, fall back to stricter IP and email limits and halve free AI for unattested devices; never block normal use |
| Calendar feed hosts (TripIt, Google Calendar, other addresses users supply) | Import feed polling | The import shows "We could not reach this calendar"; polling turns off after 3 consecutive failures. File and pasted-text imports are unaffected |

### 8.1 Public status page

`status.hermi.world` is a Better Stack status page, hosted outside Render and Cloudflare Pages so that it is reachable during an outage of our own services. It shows five components, each fed by an uptime monitor from outside our network: web app (`GET /` on the web origin), API (`GET /health/ready`), AI features (a synthetic `explain` dry run every 5 minutes that the `ai` lane answers without calling Anthropic, plus the `ai.all` and `provider.anthropic` kill switches), fare data (the freshness of the newest `fare_observations` row) and push (APNs send success rate). Incidents are posted by the owner from the Better Stack dashboard or the admin console's link to it, in plain words with times. The page shows 90 days of uptime per component and offers email updates. The in-app banner comes from `GET /public/status` (04 section 5.28), which mirrors the component states; when the API itself is down the app shows the offline banner and links to the page. The page, the five monitors and the first incident template are the launch scope; subscriber SMS, component history export and custom incident styling are polish that can wait.

## 9. Environments

| Environment | Purpose | Hosting | Data | Third parties |
|---|---|---|---|---|
| `local` | Development | Native PostgreSQL 18 prepared by `npm run db:init` and `npm run setup`; `npm run dev`. Docker compose is optional | Seed data from `apps/api/hermi/seed` and `infra/scripts/seed-staging.py` | Local modes: `AUTH_MODE=dev`, `ADMIN_AUTH_MODE=dev`, `AI_PROVIDER=claude_cli` (the owner's own CLI; `fake` in tests and smoke runs), `PROVIDERS_MODE=fake` (including a fake calendar feed host), `STORAGE_BACKEND=local`, `EMAIL_BACKEND=file` |
| `ci` | Tests | GitHub Actions with a `postgres:18` service | Ephemeral | `AI_PROVIDER=fake`; all mocked; contract tests use recorded fixtures |
| `preview` | One per pull request | Render preview (API plus worker, small Postgres) | Seed data | Sandbox keys; separate Supabase project; APNs sandbox |
| `staging` | Release rehearsal, TestFlight backend | Render, same shape as production, smaller sizes | Synthetic, never a copy of production | Separate Anthropic workspace with a $50 monthly limit; App Store sandbox; RevenueCat sandbox |
| `production` | Users | Render plus Cloudflare | Real | Separate workspace and keys for every service |

Rules: staging and production have separate Supabase projects, R2 buckets, Sentry projects and PostHog projects. Only the image digest is promoted from staging to production; configuration is never copied automatically. The test suite and e2e seed refuse to start when `ENVIRONMENT=production` or when the database name does not end in `_test` for test runs.

### 9.1 Local development on Windows

- psycopg async needs the Selector event loop; `cli.py` sets it on win32. asyncio subprocesses need the Proactor loop, so `claude` is spawned with `Popen` in a thread.
- Use the native `claude.exe`, never a `.cmd` file, and kill the whole process tree (`psutil`).
- A command line is limited to about 32,000 characters: pass prompts on stdin and use `--system-prompt-file`.
- Dev scripts use `uv run --no-sync`. npm scripts are node scripts (or `cross-env`).
- Tests that need POSIX carry the `posix_only` marker and always run in Linux CI.
- Python is 3.13 (`.python-version`). The PDF library must ship wheels for win32 and Linux (`fpdf2`).
- A nightly `windows-latest` job runs the suites.

## 10. CI/CD pipeline

GitHub Actions, one workflow per concern, all in `.github/workflows/` at the repository root (GitHub runs workflows from nowhere else). Production deploys use OIDC, never stored cloud keys. Deploy jobs and live-eval jobs are gated on repository variables, so `main` stays green without secrets.

| Workflow | Trigger | Steps |
|---|---|---|
| `ci.yml` | Pull request | 1. Install (`uv sync --frozen`, `npm ci`). 2. `npm run lint` (ruff, import-linter, oxlint, tsc). 3. `npm test` with a `postgres:18` service (pytest and vitest). 4. OpenAPI drift: `npm run gen:api` then `git diff --exit-code` on `schema.d.ts`; shared constants drift check. 5. Tenant-isolation suite (section 1.3 of [10-quality-security-launch.md](10-quality-security-launch.md)) and the SSRF hostile-address suite (section 5.4). 6. Migration test: from empty, and from the last released revision; single Alembic head. 7. Build the Docker image. 8. Trivy scan. |
| `e2e.yml` | Pull requests labeled `e2e`, and `main` | Playwright against the built image with the e2e seed (desktop and iPhone viewport projects) |
| `evals.yml` | Changes under `agents/`, prompts, or model config; weekly | AI evals through the Batch API; blocks merge on a gate miss. Runs only when the repository variable for live evals is set |
| `security.yml` | Weekly and on pull request | `pip-audit`, `npm audit`, `gitleaks`, CodeQL, Trivy. Dependency audits are non-blocking (report only) |
| `deploy-staging.yml` | Merge to `main` | Build and push image tagged with the commit SHA, deploy staging (pre-deploy migration runs), smoke test, post result to chat |
| `deploy-prod.yml` | Manual approval on a tag | Promote the same image digest (no rebuild), snapshot Postgres if the release has a migration, pre-deploy migration, rolling deploy, post-deploy smoke test, automatic rollback if `/health/ready` fails for 2 minutes |
| `ios.yml` | Tag `ios-*` or manual dispatch (`workflow_dispatch`) | Runs on a GitHub-hosted macOS runner (free for this public repository): `npm run build`, `cap sync ios`, archive, sign through Apple's cloud signing with an App Store Connect API key kept in GitHub Actions secrets, upload to TestFlight, upload dSYMs to Sentry. See [knowledge/ios-builds-on-ci.md](../../knowledge/ios-builds-on-ci.md) |
| `windows.yml` | Nightly | The lint and test suites on `windows-latest` (section 9.1) |
| `ci` (job in `ci.yml`) | Every pull request | The aggregator: `needs` every other job and always runs (`if: always()`); red if any needed job failed or was cancelled. It is the required check |
| `.github/dependabot.yml` (configuration, not a workflow) | Continuous | Weekly grouped updates |

Branching: trunk based. Short-lived branches, squash merge, `main` is always deployable. Every merge to `main` deploys staging automatically. A production release is a tag `vYYYY.MM.DD.N`.

## 11. Docker image

The Docker image and `infra/docker/compose.yml` are optional for local development; the image still builds in CI. One multi-stage `infra/docker/Dockerfile`:

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
| `serpapi_live_fares` (off) | Live fare and rental provider (legal risk is flagged). Stays off until the owner turns it on in the console (03 section 11.5 seeds it off) |
| `guest_mode` (on) | Local-first guest mode before sign-in |
| `min_app_version` (on, `rules.min_version` 1.0.0) | Forces an update below a version |
| `insurance_cards` (off until legal review) | Insurance referral cards |
| `visa_assist` (off) | Third-party visa service links (the official link is always first) |
| `affiliate_lodging_test` (on) | A/B: Travelpayouts Booking.com versus Stay22 on lodging |
| `link_preview` (on) | User-initiated link preview; hosts on the denylist are never fetched |
| `shared_research_cache` (on) | Shared research cache reads and writes |
| `passkeys` (off) | Passkey sign-in |
| `trip_import` (on) | Import from a calendar file, a calendar feed or pasted confirmations |
| `referrals` (on) | Referral codes and referral credits |
| `booked_fare_alerts` (on) | Booked-fare drop alerts |
| `verify_plan` (on) | Verify this plan: check a pasted itinerary place by place |
| `evidence_recheck` (on) | One-tap recheck of evidence older than 14 days |
| `calendar_feed_polling` (on) | Opt-in "Keep checking this calendar" for feed imports |

Settings are flags with `kind = 'setting'` (keys starting `setting_`, the value in `rules`): `setting_ai_warm_daily_usd` (5), `setting_ai_global_daily_usd` (150), `setting_serpapi_monthly_quota` (5000), and the Phase 1 settings `setting_import_reward` (the free Trip Pass for a first qualifying import: `min_items_applied` 3, a flight or a stay, verified email, no active Plus), `setting_referral_credits` (20 credits each side, 12 month expiry, referrer caps 5 per rolling 30 days and 10 per calendar year, the qualifying rule), `setting_booked_fare_drop` (`min_drop_pct` 5, `min_drop_usd` 10, `min_days_between` 7, `max_age_hours` 48) and `setting_calendar_polling` (6 hours, 3 failures, 3 feeds per person). Experiments start with `exp_`. Flags for later phases are added by the phase that ships them.

**Kill switches** (operational control, all off by default; turning one on disables the thing; an admin-set switch always has an expiry, 08 section 6.5)

| Key | Effect |
|---|---|
| `ai.all` | Pauses the `ai` lane; AI buttons show "AI is paused, your plans are safe" |
| `ai.free_tier` | Blocks AI for Free accounts (automatic at 80 percent of the daily Anthropic budget) |
| `ai.all_but_paid` | Blocks AI except for paid tiers (automatic at 95 percent) |
| `ai.agent_runs` | Blocks `agent_run` only |
| `ai.explain`, `ai.draft`, `ai.research`, `ai.taster`, `ai.import`, `ai.packing`, `ai.verify`, `ai.recheck` | Stops that one AI feature (`ai.verify` covers reading and checking a pasted plan, `ai.recheck` the one-tap evidence recheck) |
| `ai.web_search`, `ai.web_fetch` | Runs without the server web search or fetch tool |
| `ai.model.sonnet`, `ai.model.haiku` | Routes to the other model where the feature allows it, else off |
| `ai.force_haiku` | Uses the fast model for every feature that allows it |
| `ai.batch` | Pauses scans, digests and cache warming |
| `ai.shared_cache_write` | Stops writes to the shared research cache |
| `provider.serpapi`, `provider.travelpayouts`, `provider.geoapify`, `provider.anthropic`, `provider.viator`, `provider.stay22`, `provider.frankfurter` | Disables one provider |
| `affiliate.all` | Turns every partner link off (plain links only) |
| `affiliate.insurance` | Turns insurance referral cards off |
| `affiliate.<program_code>` | Hides one program's cards and stops new clicks for it (one row per `affiliate_programs.code`, seeded from that table) |
| `push.all`, `email.all` | Stops sending |
| `signups` | Stops new account creation (existing users unaffected) |
| `purchases` | Hides paywalls and purchase buttons |
| `webhooks.process` | Keeps receiving webhooks but pauses processing, for a safe replay |
| `maintenance` | Read-only mode: writes return 503 with a friendly body |
| `user:<users.id>` | Per-account AI and live hold; created by an admin on demand, never seeded |
| `import.all` | Stops every trip import (files, feeds, pasted text, Google Maps lists), feed polling and the import reward |
| `import.polling` | Stops only the 6-hourly calendar polling; first-time imports keep working |
| `referrals.grant` | Pauses referral credit grants (abuse incident); codes can still be entered |

Practice every switch in staging each quarter. Anthropic workspace spend limits are the backstop outside our code.

## 14. Mapping the existing Trip Planner code

The existing code is the Trip Planner repository, https://github.com/avillalv/trip-planner. Build sessions clone it read-only to `.reference/trip-planner/` (gitignored). Paths are under `backend/tripplanner/` and `frontend/src/` in that repo. Reuse means copy with small changes; adapt means keep the idea and rewrite for multi-tenant and Hermi names; drop means do not carry over.

### 14.1 Backend

| Existing module | Decision | Where it goes | Reason |
|---|---|---|---|
| `config.py` | Adapt | `apps/api/hermi/config.py` | Keep the typed settings pattern; remove passcode, host list, backup and Windows paths; add section 7 variables. Adapt, dev-only: the old `CLAUDE_PATH` becomes `CLAUDE_CLI_PATH` |
| `db.py` | Adapt | `db.py` | Add pool limits, timeouts, TLS, the `app.user_id` session variable (`set_config('app.user_id', ...)`, read by policies through `app_user_id()`, 03 section 6.2) and a system session |
| `main.py` | Adapt | `main.py` | Keep the app factory and router wiring; add CORS, middleware order (section 4), problem+json errors; no SPA serving |
| `spa.py` | Drop | none | The web app ships from Cloudflare Pages |
| `security.py` | Adapt | `security/` | Keep constant-time compare and redaction ideas; replace passcode cookie and loopback trust with JWT verification; rate limits move to Postgres |
| `process.py`, `supervisor.py` | Drop | none | Windows watchdog and local supervisor; the platform restarts containers and migrations are pre-deploy |
| `migrate.py`, `setup_db.py` | Adapt | `cli.py migrate`; `npm run db:init` | Keep the Alembic runner with advisory lock; `setup_db.py` and the old `scripts/setup.mjs` are adapted into `npm run db:init` and `npm run setup` |
| `paths.py` | Drop | none | `%LOCALAPPDATA%` and repo-relative paths; no writable local state |
| `cli.py` | Adapt | `cli.py` | Keep the typer or argparse shape; commands become `api`, `worker`, `scheduler`, `migrate`, `seed`, `openapi`, `admin-grant`, `ai-smoke` |
| `migrations/` (7 revisions) | Drop history, keep `env.py` | `migrations/` | Start Hermi with a new baseline from [03-database-schema.md](03-database-schema.md); the 7 existing revisions are replaced by one baseline plus a one-off data import script |
| `models/base.py` | Adapt | `modules/*/models.py` base | Keep the declarative base; switch to UUIDv7 public ids and `timestamptz` |
| `models/trip.py`, `people.py` | Adapt | `trips`, `people`, `trip_people` | Add `deleted_at`, `owner_user_id`, `linked_user_id` (the UUIDv7 `id` is the public id); `trip_travelers` becomes `trip_people` |
| `models/flights.py` | Adapt | `flight_routes`, `fare_observations`, `trip_fare_links`, `chosen_flights`, `price_alerts` | Logic is sound; add tenant scope, cache keys and alert rows |
| `models/itinerary.py` | Adapt | `itinerary_days`, `itinerary_items` | Rename Activity to item, add created-by, row `version` on all editable rows |
| `models/lodging.py` | Adapt | `lodging_options`, `lodging_votes` | Votes gain `user_id` |
| `models/airport.py` | Reuse | `airports` | Static reference data |
| `models/agents.py`, `automation.py` | Adapt | `runs`, `run_events`, `ai_usage` | Add `user_id`, request ids, cost micro-dollars; drop `pid`, `argv_redacted`, `log_path` |
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
| `services/agent_ingest.py` | Reuse | `modules/ai/ingest.py` | The evidence rules, blocked domains, price bounds and `IngestRejection` are the trust boundary; called in process from tools. Its checks also validate the CLI backend's final JSON |
| `services/agent_context.py` | Adapt | `modules/ai/context.py` | Builds model context from one trip; must read only that trip and exclude private notes and other travelers' names |
| `services/claude_cli.py` | Adapt, dev-only | `providers/ai/claude_cli.py` | Keep `STRIPPED_ENV`, `find_claude`, `auth_status`, `NO_WINDOW`; one local CLI sign-in cannot be multi-tenant, so it never runs outside `local` |
| `services/runs.py` and the old scheduled-run service | Adapt | `modules/ai` | Keep run lifecycle and log events; add budgets, refunds; scheduled agent runs are Phase 2 |
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
| `worker/scheduler.py` | Drop | `apps/worker/scheduler.py` (new) | APScheduler per scheduled agent run double-fires with two instances; replaced by the leader and the `flight_routes.next_check_at` scan (`scan_due_routes`) |
| `worker/jobs/flight_prices.py` | Adapt | `jobs/check_fare_route.py` | Provider call logic carries over; add cache, dedup and idempotency |
| `worker/agents/runner.py`, `stream.py` | Adapt, dev-only | The `claude_cli` backend's runner and stream parser (`providers/ai/`) | Keep Watchdog, StderrDrain, the stdin writer, `psutil` `kill_tree`, `guard_problem` and `explain_failure`. Product agent runs use `AgentLoop` on the Messages API (`agents/loop.py`) |
| `worker/agents/smoke.py` | Adapt, dev-only | `hermi ai-smoke` | The smoke script for the CLI backend; the eval runner is separate |
| `worker/agents/prompts.py` | Adapt | `agents/prompts.py` | Keep `SYSTEM_PROMPT` almost verbatim as the cached prefix; remove the tools section; version it |
| `agent_bridge/` | Drop | none | The CLI backend runs with `--strict-mcp-config` and no MCP servers; tools are in process |
| `tests/conftest.py`, `factories.py` | Adapt | `apps/api/tests` | Keep the test database discipline; add a two-tenant fixture |
| `tests/fake_claude.py` | Adapt, dev-only | The fake `claude` for CLI tests, and the `fake` provider | The Messages API fake replays recorded `server_tool_use`, `pause_turn` and `refusal` fixtures; the fake `claude` for CLI tests emits stream-json events |
| `tests/e2e_seed.py` | Adapt | e2e seed | Two users, one shared trip, one Plus and one Free |
| Other pytest files (`test_trips`, `test_itinerary`, `test_lodging`, `test_flight_*`, `test_quotes`, `test_places`, `test_people`, `test_presentation`, `test_airports_seed`) | Adapt | Module tests | Logic assertions carry over; add auth and tenant arguments |
| `test_auth`, `test_agent_*`, `test_backups`, `test_scheduler`, `test_startup`, `test_spa`, `test_system`, `test_serpapi_budget` | Drop or rewrite | Replaced by new suites | They test removed code; budget and scheduler tests are rewritten for the new designs |

### 14.2 Frontend and tooling

| Existing | Decision | Reason |
|---|---|---|
| `frontend/src/index.css` tokens (the old passport palette) | Adapt | Becomes `packages/tokens`: reuse the token plumbing and the neutral names (`--tp-paper`, `--tp-ink`, `--tp-brand`), but replace every value with the Hermi tokens in 05 section 2; the old values are not ported |
| `components/brand/*` (guilloche, logo, brand mark) | Adapt | Swap the logo and brand mark for the Hermi mark from `brand/`, and replace `guilloche.tsx` with `route-pattern.tsx` (05 section 2.9); the seeded, deterministic approach and its tests carry over |
| `components/ui/*` | Reuse | Radix and shadcn primitives |
| `components/flights/*`, `itinerary/*`, `lodging/*`, `trips/*`, `people/*` | Adapt | Mostly reusable; add role-aware actions, paywall moments, affiliate cards, attribution |
| `components/deck/*`, `routes/present-page.tsx` | Adapt | Presentation mode carries over; add portrait mobile mode |
| `components/agents/*`, `routes/agents/*` | Adapt | Runs, timeline and findings carry over; add credits cost and consent; remove the scheduled agent run UI (scheduled agent runs arrive in Phase 2) |
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
| `scripts/setup.mjs` | Adapt | Becomes `npm run setup` that prepares native PostgreSQL 18 (`npm run db:init`), migrates and seeds |
| Root `package.json` scripts | Adapt | Keep `dev`, `test`, `lint`, `format`, `gen:api`, `test:e2e`; drop `autostart:*`, `share`, `backup`, `restore`, `agent:smoke` |
| `.claude/rules/*`, `knowledge/` | Adapt | Keep the three-tier context layout and the migrations and frontend rules for the new repo; rewrite the agent rules for the API loop |
| `CLAUDE.md` rule "subagents use Sonnet" | Reuse | Build-time rule carries over; not a runtime rule |
| `CLAUDE.md` rule "never fetch Airbnb, Vrbo or Booking pages" | Reuse | Becomes product rule 3 in the README |


### 14.3 One-off data import

A script `infra/scripts/import_trip_planner.py` reads the personal Trip Planner database and creates two `users`, their `trip_members` (owner), `people` with `linked_user_id`, trips, flights, itinerary, lodging and notes with new UUIDs, using the new schema. It is run once, by hand, against staging first. It is not part of the product.

### 14.4 New in Phase 1 (no existing code)

| New code | Where | Notes |
|---|---|---|
| Import pipeline | `modules/imports/`, `jobs/fetch_import_feed.py`, `jobs/poll_import_feeds.py` | Section 5.4 |
| SSRF guard and feed fetcher | `security/ssrf.py`, `providers/feed_fetcher.py` | Also protects `providers/link_preview.py` |
| Calendar feed generator | `modules/itinerary/ical.py`, route `GET /calendar/{token}.ics` | Section 5.5 |
| Booked-fare drop evaluator | `modules/flights/booked_fare.py`, `jobs/evaluate_booked_fare_drops.py` | Section 5.6 |
| Referrals | `modules/referrals/`, `jobs/grant_referral_rewards.py` | 07 section 9 |
| First-import reward pass | `modules/billing/service.py` (calls `grant_import_reward()`) | 07 section 10 |
| AI provider seam | `providers/ai/` | Section 3 |
| Database bootstrap | `infra/db/bootstrap.sql` | Roles and databases, run by `npm run db:init` |
| Dev sign-in | `modules/auth/` (`AUTH_MODE=dev`) | Section 4.1 |
| Fake-Access signer | `modules/admin/` (`ADMIN_AUTH_MODE=dev`) | 08 section 2 |
| CLI commands | `hermi seed --demo`, `hermi admin-grant`, `hermi ai-smoke` | Seed, admin grant, CLI backend smoke |
