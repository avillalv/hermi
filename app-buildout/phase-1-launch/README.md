# Phase 1: the launch app (months 1 to 6)

Part of the [Hermi build specification](../README.md). Written 2026-09-30.

Phase 1 is a complete, polished Hermi that a solo developer working with Claude Code can build in
about six months and publish to the App Store (and the web). It earns money from day one:
subscriptions, trip passes, credit packs and affiliate links. Everything else waits for
[Phase 2](../phase-2-growth/README.md) or [Phase 3](../phase-3-scale/README.md).

## Scope

### In Phase 1

| Area | What ships |
|---|---|
| Accounts | Sign in with Apple, Google and email code (Supabase Auth); guest mode that is claimed on sign-up; onboarding with "Coming from TripIt or Wanderlog?"; profile, settings, data export, in-app account deletion |
| Switching | Import a trip from a calendar file or calendar feed (TripIt single-trip export or iCal feed, Google Calendar) and from pasted booking confirmations (Haiku extracts flights, stays and reservations); first import earns a free Trip Pass for that trip |
| Trips | Trips, destinations, travelers (`people`), dates, currency, archive, duplicate |
| Collaboration | Roles (owner, editor, viewer), invite links, share links; Free owners invite 1 collaborator per trip, Plus and Trip Pass up to 6; hearts on stays and places; activity log |
| Flights | Routes, cached fares (Travelpayouts), live fares behind a provider interface (SerpApi behind a flag), price history, chosen flight, price alerts, and the booked-fare drop alert ("you paid $X, it is now $Y; check the airline's change and credit rules") |
| Stays | Shortlist, pasted links (never fetched for Airbnb, Vrbo or Booking.com), hearts, compare, rental search (behind the SerpApi flag), "Book via partner" |
| Plan | Day-by-day itinerary, drag and drop, places search and details (Geoapify, Wikipedia), map, ideas list |
| Evidence | Notes with sources; every AI-found fact shows "Found on [site], checked [date]" |
| Present | Full-screen presentation mode, shareable read-only link, PDF export (Free adds a small footer) |
| Before you go | Checklist with official visa and entry links first, then labeled partner items (eSIM, insurance referral, transfers, bookings) |
| AI | `explain`, `draft_day`, `draft_trip`, `research`, `agent_run` (manual fare hunt and deep research), the one-time taster, packing list, booking import; shared research cache; credits and ceilings |
| Offline | Trips readable offline on every tier; edits queue and sync |
| Calendar | Live calendar subscription feed per trip |
| Notifications | Push (APNs) and email for price drops, invites, run results, pre-trip reminders |
| Money | Free, Plus (monthly and annual, 7-day trial on annual), Trip Pass, credit packs via RevenueCat; paywalls; affiliate links through `/go/{click_id}` with Travelpayouts, Stay22 and Viator; nightly conversion import |
| Admin | Overview dashboard, users, subscriptions and store transactions, credits and AI spend, kill switches, feature flags, affiliate revenue, support inbox, provider and system health, audit log, basic content reports |
| Platforms | Web app and iOS app (Capacitor, bundled). Android users get the web app until Phase 2. |
| Growth basics | Public sample trips and shared-trip pages for search, honest comparison pages (`/vs/...`), referral credits, App Store listing |

### Added from the competitive analysis

These come from [../context/competitive-analysis/win-plan.md](../context/competitive-analysis/win-plan.md)
section 9 and are part of Phase 1:

| Feature | Effort | Beats |
|---|---|---|
| "Verify this plan": paste an itinerary from ChatGPT, Gemini, Layla or Mindtrip; Hermi checks each place, opening hours and price with sources and marks what it could not confirm (`verify_plan`, 1 credit per checked item, capped per run: 5 on Free, 12 on Plus and Trip Pass) | M | Every AI planner |
| Imports named for each rival: TripIt, Tripsy and Wanderlog entries on the import screen, and Google Maps saved-list import (pasted list link or exported file; never scraped) | S to M | TripIt, Tripsy, Wanderlog |
| Evidence freshness: a "may be out of date" flag after 14 days and a one-tap recheck | S | AI planners |
| Trust pages: "How we earn" (every affiliate partner and that nothing is ranked by commission), a plain billing page, and a one-tap cancel link in the app | S | Wanderlog, Layla, Tripsy |
| Public status page and a "Synced N seconds ago" indicator | S | Wanderlog, Tripsy |
| Android web-app install guide and testing on Android Chrome | S | Tripsy, TripIt Pro |

Early Phase 2 (first items after launch): "paste your group chat" to draft a plan (answers Trippy),
and repair-a-day when plans change. Email-forward import is decided at the month 4 review based on
how pasted imports perform in the beta.

### Settled values (all Phase 1 files use these)

| Item | Value |
|---|---|
| Referral credits | 20 credits to each person after the new user's first trip with dates; expire after 12 months; referrer caps 5 per rolling 30 days and 10 per calendar year; referral credits do not raise the spend ceiling |
| Booked-fare drop alert | Fires when the current fare is at least 5% and at least $10 (converted) below what the user paid; at most once per flight every 7 days; never includes a partner link |
| First-import Trip Pass | Once per user; the import must add at least 3 items including a flight or a stay; verified email; the trip has no active pass and the user has no active Plus |
| Calendar feed imports | Opt-in "Keep checking this calendar"; polled every 6 hours; changes are shown as a preview the user confirms, never applied automatically |
| Web purchases | None in Phase 1: the web paywall says "Upgrade in the iOS app". Web billing arrives with Android in Phase 2. |
| Free collaborators | 1 per trip; share links (read-only, with the "Made with Hermi" footer) on every tier |
| Trip Pass credits | The 40 credits are a pool for the trip: every member who may start AI on that trip spends from it, and the pass, not the person who taps, is the payer for the pool's provider-spend ceiling ($1.80 a month) |
| Raw import file | The raw import file (calendar file, Takeout file, pasted text) is never stored. Only the parsed preview and the rows it creates are kept |
| AI daily cap | Global AI daily cap is $150 (setting `setting_ai_global_daily_usd`, environment variable `AI_GLOBAL_DAILY_CAP_USD`). The taster stop is $0.80 |
| HTTP 402 and 403 | A plan limit or a missing entitlement returns HTTP 402 (`limit_reached`, `entitlement_required`, `payment_required`) with a `paywall` hint. HTTP 403 is for role, account state and consent |
| Customer API auth | Bearer only: no cookie session, no CSRF header. `X-Hermi-Client` (`web` or `ios`) is informational. The calendar feed token is in the path: `GET /v1/calendar/{token}.ics` (04 section 5.29 is the authority) |
| Guest data | Local-only until sign-in. `POST /me/claim` carries the trip JSON and a claim id. There is no server-side guest user (`is_guest` and `GUEST_TOKEN_SECRET` are gone) |
| Today and wrap-up | "Today" is a state of the trip Overview ("Happening now"), not a screen. The after-trip wrap-up belongs to the Phase 2 after-trip pack |
| WF-122 and WF-129 | WF-122 (Google Maps export file import) leaves the cut list and is built. WF-129 stays on the cut list |
| Heat-ink tokens | The heat-ink tokens and `--viz-band` are defined in 05 section 2.2 |
| Component looks | `hermi.css` and the mockups in `design/` win over the prose of 05 sections 4 and 6. The token values in 05 section 2 still win over both |
| Product AI provider | Chosen by `AI_PROVIDER`: `anthropic_api` in staging, TestFlight and production; `claude_cli` (the owner's own Claude Code CLI, local machine only, loopback only) behind the flag in local development; `fake` in tests, CI and smoke runs. Config allows `claude_cli` only when `ENVIRONMENT=local`, the server is bound to loopback, and `AUTH_MODE=dev` or the user is in `AI_CLI_ALLOWED_EMAILS` |
| Local development | Native PostgreSQL 18 (no Docker), `AUTH_MODE=dev`, `ADMIN_AUTH_MODE=dev`, `PROVIDERS_MODE=fake`, `STORAGE_BACKEND=local` and `EMAIL_BACKEND=file`; `npm run setup` prepares a machine and `npm run doctor` reports what is set |

### Not in Phase 1

| Feature | Phase |
|---|---|
| Family plan and households | 2 |
| Group Trip Pass, polls, manual cost splitting, room-block requests | 2 |
| Comments on items | 2 |
| Email-forward import (plans@hermi.world) | 2 |
| Flight status, delay and gate alerts | 2 |
| Pro tier and scheduled agent routines | 2 |
| Concierge lane (host agency) | 2 |
| Direct affiliate programs (Expedia Group and Vrbo, Booking.com, Skyscanner, Airalo, GetYourGuide) | 2 |
| Native Android app | 2 |
| After-trip flight compensation prompt, memories and "Year in travel" card | 2 |
| Stripe group payments | 3 |
| Hermi for Advisors | 3 |
| Partner guides, printed trip books, in-app hotel booking (LiteAPI), white-label and API, card and loyalty offers | 3 |

## Month plan

| Month | Goal | Exit |
|---|---|---|
| 1 | Validate and set up: landing page and waitlist, 10 interviews, repo, CI, container image, database, auth, tenancy | Demand signal; a signed-in user can create a trip on staging |
| 2 | Core planning: trips, collaboration, flights (cached), stays, itinerary, places, map | Two people can plan a trip together on the web |
| 3 | AI and credits: Claude API loop, explain, drafts, research, agent runs, taster, ledger, ceilings, shared cache, evidence labels | Agent run cost measured over 50 runs; ceilings enforced |
| 4 | Money: RevenueCat, Plus, Trip Pass, packs, paywalls, affiliate redirect and reporting, checklist; imports; admin essentials | Sandbox purchases work end to end; clicks and conversions tracked |
| 5 | iOS and polish: Capacitor shell, push, offline, calendar feed, presentation, accessibility, performance, onboarding, empty and error states; TestFlight beta | 30 beta testers, crash-free sessions above 99.5% |
| 6 | Launch: App Review, privacy labels, support, monitoring, runbooks, SEO pages, comparison pages, launch campaign | Live on the App Store and web |

## Files

| File | What it specifies |
|---|---|
| [01-product-spec.md](01-product-spec.md) | Phase 1 features as user stories with acceptance criteria, tier matrix |
| [02-architecture.md](02-architecture.md) | Stack, repository layout, services, configuration, reuse of the current code |
| [03-database-schema.md](03-database-schema.md) | Phase 1 PostgreSQL schema, security rules, seed data |
| [04-api-spec.md](04-api-spec.md) | Phase 1 endpoints and webhooks |
| [05-ui-ux-spec.md](05-ui-ux-spec.md) | Design system and every Phase 1 screen |
| [06-ai-agents-spec.md](06-ai-agents-spec.md) | Phase 1 AI features, prompts, tools, metering |
| [07-monetization-spec.md](07-monetization-spec.md) | Phase 1 products, entitlements, credits, paywalls, affiliate system |
| [08-admin-control-center.md](08-admin-control-center.md) | Phase 1 admin console |
| [09-build-roadmap.md](09-build-roadmap.md) | The six-month plan as ordered tickets |
| [10-quality-security-launch.md](10-quality-security-launch.md) | Testing, security, privacy, analytics, App Store submission, runbooks |
| [design/](design/README.md) | The visual design kit: tokens, component classes, screen mockups and their PNGs, the look that [05-ui-ux-spec.md](05-ui-ux-spec.md) describes |
