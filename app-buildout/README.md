# Hermi: build specification

Written 2026-09-30. This folder is everything needed to build Hermi, a collaborative trip
planner for iOS and the web that earns money from subscriptions, trip passes, AI credits,
affiliate commissions and a concierge booking lane, without ads and without making the product
worse for free users.

It is written to be handed to a developer (or to Claude Code) with no other context, and it is
self-contained: copy this whole folder into a new repository and start with
[prompts/KICKOFF.md](prompts/KICKOFF.md). The business reasoning behind each decision is in
[context/](context/business-plan/README.md).

![Hermi logo](brand/hermi-logo-preview.png)

## What Hermi is

Hermi helps couples, families and friend groups plan a trip together: pick dates and flights,
shortlist and vote on places to stay, plan each day, and walk through the plan in a full-screen
presentation. AI agents hunt fares and research events, and every fact they save links to the page
it came from. The design language is "two routes, one trip": a warm paper ground, deep ink, a sky
blue brand, two traveler routes in pink and yellow that meet at a plane, and a logo of an H made
of two dotted routes with a plane as the crossbar.

Positioning line: **Plan together. Know the fare.**

## How to use this folder

The build is split into three phases. **Build Phase 1 first and only Phase 1**: it is a complete,
polished app you can publish to the App Store about six months after you start, already earning from
subscriptions, trip passes, credit packs and affiliate links. Phases 2 and 3 are self-contained
feature packs you add afterwards, one at a time.

| Folder | When | What it is |
|---|---|---|
| [phase-1-launch/](phase-1-launch/README.md) | Months 1 to 6 | The full specification for the launch app: product, architecture, database, API, UI, AI, monetization, admin, a month-by-month roadmap with tickets, and quality and launch. Everything needed and nothing more. |
| [phase-2-growth/](phase-2-growth/README.md) | Months 7 to 12 | Feature packs: Family plan, Group Trip Pass with polls and cost splitting, comments, email-forward import, flight status alerts, Pro with scheduled agents, the concierge lane, direct affiliate programs, native Android, memories and sharing cards |
| [phase-3-scale/](phase-3-scale/README.md) | Year 2 and later | Feature packs: Stripe group payments, Hermi for Advisors, partner guides, printed trip books, in-app hotel booking (LiteAPI), white-label and API, card and loyalty offers |
| [brand/](brand/BRAND.md) | Now | Logo files, colors, type, icon rules |
| [phase-1-launch/design/](phase-1-launch/design/README.md) | Now | The visual design kit for Phase 1: tokens, component classes, screen mockups and their PNGs |
| [prompts/](prompts/README.md) | Now | The 28 build prompts that build all of Phase 1 in order, the orchestrator rules, and the kickoff prompt ([prompts/KICKOFF.md](prompts/KICKOFF.md)) |
| [context/](context/business-plan/README.md) | Background | The business plan and competitive analysis this build came from, so this folder stands alone in a new repository |
| [reference-full-spec/](reference-full-spec/01-product-spec.md) | Reference only | The original all-phases specification the phase folders were cut from. Do not build from it; the phase folders are current. |

Each feature pack says exactly what it adds to the Phase 1 database, API, screens, billing and admin,
so it can be built on top without rereading everything.

Competitive context for these choices (TripIt, Trippy, Wanderlog and others) is in
[context/competitive-analysis/](context/competitive-analysis/README.md).

## Shared decisions (every file follows these)

### Tiers and products

| Code | Name | Price (US) | Store product | Key limits |
|---|---|---|---|---|
| `free` | Free | $0 | none | 2 active trips, 1 cached-fare route per trip, 12 credits a month, one lifetime deep agent run ("taster"), 1 cached-fare alert, invite 1 collaborator per trip (so couples plan free), offline reading, joins others' trips free |
| `plus` | Plus | $5.99 a month, $39.99 a year | auto-renewing subscription, group `hermi_membership` | unlimited trips (fair use 25), 3 live routes checked daily within 120 days of departure, 60 credits a month, can invite collaborators |
| `family` | Family | $8.99 a month, $59.99 a year | auto-renewing subscription, same group | Plus for up to 6 household members, 150 pooled credits, 5 live routes |
| `pro` | Pro (launches later) | $11.99 a month, $99 a year | auto-renewing subscription, same group | 240 credits, 6 live routes, scheduled agent routines, priority queue |
| `trip_pass` | Trip Pass | $9.99 | non-renewing subscription, 90 days | one trip: 2 live routes, max 60 live checks, 40 credits (a pool for the trip), up to 6 collaborators |
| `group_trip_pass` | Group Trip Pass | $19.99 | non-renewing subscription, 90 days | one trip: up to 12 travelers, 80 credits, polls, cost splitting, room-block request |
| `credits_50` / `credits_150` / `credits_400` | Credit packs | $2.99 / $6.99 / $14.99 | consumable | purchased credits last 12 months and are spent last |
| `advisor_seat` | Hermi for Advisors (year 2) | $29 a seat a month, $24 annual | Stripe on the web, not the App Store | client workspaces, branded presentations, proposals, commission tracking |

Group tools (Phase 2): polls and manual cost splitting are in every paid plan (`plus`, `family`, `pro`) and
both passes; Free users use them on trips that have them. The Group Trip Pass adds up to 12 travelers
and the room-block request. Collecting money through Stripe (Phase 3) is for `group_trip_pass` and `pro`.

Phases: Phase 1 sells `free`, `plus`, `trip_pass` and the credit packs. `family`,
`group_trip_pass` (with polls, manual cost splitting and the room-block request) and `pro` arrive in
Phase 2. Stripe group payments, `advisor_seat`, print and LiteAPI arrive in Phase 3. The tier table
above is the full ladder; each phase folder says which rows it builds.

Rules: a trip's capabilities are the best of its owner's tier and any pass on that trip.
Invitees join free and get the trip's capabilities on that trip. AI credits are charged to the
person who starts the action (Family draws from the household pool). Trip Pass credits are a pool for that trip. Apple Family Sharing is off.

### AI credits

1 credit is a budget of up to $0.02 of provider spend.

| Action code | Credits | Hard stop |
|---|---|---|
| `explain` (Haiku short answer) | 1 | $0.01 |
| `live_search` (flight or rental) | 1 | $0.02 |
| `draft_day` | 1 | $0.03 |
| `draft_trip` | 4 | $0.10 |
| `research` | 8 (1 from shared cache) | $0.16; 5 searches, 8 fetches |
| `agent_run` (fare hunt or deep research) | 40 (8 from shared cache) | $0.80; 20 turns, 10 searches, 10 fetches, one at a time |

`verify_plan` (Verify this plan) is billed per checked item at 1 credit, with the hard stop $0.02 per item; reading the pasted plan is an `explain`. Taster stop: $0.80.

Monthly provider-spend ceilings: Free $0.25 (plus the one-time taster), Plus $2.25, Family $3.40
pooled, Trip Pass $1.80, Group Trip Pass $3.60, Pro $5.50. Daily: Free $0.05, Plus, Family and
passes $0.40, Pro $1.25. An agent run is admitted if the month has $0.80 of headroom, even above
the daily budget. Cached data always keeps working. Models: Claude Haiku 4.5 (`claude-haiku-4-5`)
for short answers and page summaries, Claude Sonnet 5.5 (`claude-sonnet-5-5`) for drafting,
research and agents.

### Money that is not a subscription

- **Affiliate links** on every tier, same places, clearly labeled "We earn a commission if you
  book here." All outbound partner links go through `/go/{click_id}`. Launch networks:
  Travelpayouts, Viator partner API, Stay22; direct affiliate programs (Expedia Group for Vrbo,
  Booking.com, Skyscanner, Airalo, GetYourGuide) are Phase 2. Phase 1 launches with Travelpayouts,
  the Viator partner API and Stay22 only. Airbnb has no program: plain links only, and
  pasted listing links are never rewritten. The server never fetches Airbnb, Vrbo or Booking.com
  pages.
- **Concierge**: an optional "Have a human book this" request on stays, cruises and complex trips,
  fulfilled by an advisor under a host travel agency. Users get perks; Hermi earns the agency
  commission. Always optional and disclosed.
- **Group payments**: cost splitting and collection for real-world trip costs through Stripe
  (never Apple In-App Purchase, never for digital features).
- **Later**: in-app hotel booking via LiteAPI, labeled partner guides, printed trip books,
  Hermi for Advisors, white-label.
- **Never**: banner ads, selling user data, ranking anything by commission, lifetime plans.

### Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, uv |
| Database | PostgreSQL 18 on Render, point-in-time recovery, row-level security as a second layer |
| Jobs | Procrastinate (Postgres-backed queue); a scheduler process that enqueues due live fare checks |
| Web and mobile client | React 19, Vite, React Router 7, TanStack Query, Tailwind CSS 4, Radix and shadcn components, MapLibre, FullCalendar, Recharts; wrapped for iOS with Capacitor (bundled, not a remote URL) |
| Auth | Supabase Auth for sign-in only (Sign in with Apple, Google, email code); our own `users` table |
| Payments | RevenueCat over StoreKit 2 for the app; Stripe for the web (advisors, group payments, print) |
| AI | Anthropic Claude Messages API with tool use, server web search and web fetch tools, behind an `AiProvider` seam with three backends: `anthropic_api` (staging and production), `claude_cli` (the owner's own `claude` CLI, local development only) and `fake` (tests and CI), selected by `AI_PROVIDER` |
| Hosting | Render (API, worker, scheduler, Postgres) behind Cloudflare (DNS, WAF, R2 storage, Pages for the web app) |
| Observability | Sentry, structured JSON logs, Better Stack uptime, PostHog product analytics (no ad SDKs) |
| Email and push | Resend for email, APNs direct for push |

### Core entities (table names used everywhere)

`users`, `auth_identities`, `devices`, `households`, `household_members`, `trips`,
`trip_members`, `trip_invites`, `trip_share_links`, `trip_destinations`, `people`,
`trip_people`, `flight_routes`, `fare_observations`, `trip_fare_links`, `chosen_flights`,
`price_alerts`, `itinerary_days`, `itinerary_items`, `places_cache`, `saved_places`,
`lodging_options`, `lodging_votes`, `polls`, `poll_votes`, `expenses`, `expense_shares`,
`settlements`, `checklist_items`, `notes`, `routines`, `runs`, `run_events`, `ai_usage`,
`credit_ledger`, `credit_grants`, `provider_calls`, `shared_research_cache`, `subscriptions`,
`entitlements`, `trip_passes`, `store_transactions`, `webhook_events`, `affiliate_programs`,
`affiliate_link_templates`, `link_clicks`, `affiliate_conversions`, `concierge_requests`,
`room_block_requests`, `partner_guides`, `print_orders`, `advisor_orgs`, `advisor_seats`,
`advisor_clients`, `feature_flags`, `kill_switches`, `admin_users`, `audit_log`,
`support_tickets`, `consents`, `data_exports`, `deletion_requests`, `analytics_events`
(optional, if not only in PostHog), `airports`, `fx_rates`.

Public identifiers are UUIDv7. Money is stored as integer minor units plus an ISO 4217 currency.
Provider spend is stored in micro-dollars. All timestamps are `timestamptz` in UTC.

### Non-negotiable rules

1. No banner ads, no dark patterns, no fake urgency. The free path is always visible.
2. Never rank search results, lists or suggestions by commission.
3. The server never fetches Airbnb, Vrbo or Booking.com pages, and uses no scrapers.
4. Every AI-found fact carries the source URL it came from; fares must be seen on a page during
   the run.
5. AI never gives insurance, visa or legal advice; it links to official sources.
6. Account deletion in the app, data export on every tier, and no data held hostage on downgrade.
7. Secrets only in environment variables, never in the repo.
8. No UI copy with em dashes; sentence case; plain verbs (see [phase-1-launch/05-ui-ux-spec.md](phase-1-launch/05-ui-ux-spec.md)).

## Reusing the existing Trip Planner code

Hermi is built on top of the existing **Trip Planner** repository, [https://github.com/avillalv/trip-planner](https://github.com/avillalv/trip-planner) (`backend/`,
`frontend/`), a working single-household app. Build sessions clone it read-only to
`.reference/trip-planner/` (gitignored) and port from it; never modify it. Much of it
carries over: flight route and fare logic, itinerary and lodging features, presentation mode,
the design token plumbing (not its passport colors, which the Hermi palette replaces),
Travelpayouts, Geoapify, Wikipedia and Frankfurter providers, the evidence rules in
`services/agent_ingest.py`, and the agent prompts. The Claude Code CLI runner is adapted as the dev-only `claude_cli` provider (the runner, stream parser, environment stripping, fake `claude` for tests and the smoke script), and the old setup scripts are adapted into `npm run setup` and `npm run db:init`. What does not carry over: passcode auth, the MCP bridge (`agent_bridge/`), APScheduler and Tailscale sharing. [phase-1-launch/02-architecture.md](phase-1-launch/02-architecture.md) maps each module.
