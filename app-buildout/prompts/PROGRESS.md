# Phase 1 progress

The build's memory. Every autopilot session updates this file in its pull request, and the next session resumes from here (see [AUTOPILOT.md](AUTOPILOT.md)). The driver runs the units in order: S1 to S3, then prompts 01 to 28, then the final check.

## Current prompt

02, port reusable code from the old Trip Planner (branch `phase1/p02-port-reusable-modules`). Base code: `.reference/trip-planner/` (public, cloned read-only).

Steps, in order (one session each):

1. WF-005.1 Providers and flight logic: `apps/api/hermi/providers/` (`__init__.py` with `ProviderError` and `NotConfigured` from `config.py`, `travelpayouts.py`, `geoapify.py` merged with `geoapify_places.py`, `wikipedia.py`, `frankfurter.py`), the pydantic schemas they need, and the DB-free flight and fare logic into `apps/api/hermi/modules/flights/` (`planner.py` from `search_planner.py`, the pure helpers of `quotes.py` and `flight_choice.py`, `fx` conversion). Move `httpx` from the dev group to runtime dependencies (only `providers/*` import it). Tests: the adapted `test_flight_providers`, `test_search_planner` and the pure parts of `test_quotes` and `test_flight_choice`, with the JSON fixtures; the forbidden-imports test (`subprocess` only in `providers/ai/claude_cli.py`, `apscheduler` nowhere, no Windows-only code in `apps/` or `packages/`).
2. WF-005.2 Tokens, fonts and web lib (UI plumbing, no screen): `packages/tokens` (`tokens.css` equal to `design/tokens.css`, `theme.css`, TS exports, the old `--tp-*` plumbing with every value from 05 section 2, including `--tp-edge`, `--tp-warning-ink`, `--tp-sky`), the three `@fontsource-variable` packages (`fredoka`, `atkinson-hyperlegible-next`, `atkinson-hyperlegible-mono`), wired into `apps/web`. A vitest test parses 05 sections 2.1 to 2.3, asserts they equal `tokens.css` and recomputes every WCAG ratio. Port the reusable `frontend/src/lib` helpers (`dates`, `money`, `currencies`, `format`, `timezones`, `geo`, `itinerary-time`) with their tests into `apps/web/src/lib/`. Kit: none, follow DL section 11.
3. WF-005.3 Evidence rules and never-fetch list: `apps/api/hermi/modules/ai/policy.py` (`BLOCKED_HOSTS` = `airbnb`, `vrbo`, `booking`, registrable-label match, no setting can change it, plus generators for the API `blocked_domains` list and the CLI `--disallowedTools` rules of 06 section 2.7), `apps/api/hermi/security/ssrf.py` (imports it), `modules/ai/ingest.py` (the pure parts of `agent_ingest.py`: `blocked_domain`, `source_problem`, price bounds, item validators, `IngestRejection`), `modules/ai/prompts.py` (from `worker/agents/prompts.py`, tools section dropped, versioned). Tests: the four hosts `airbnb.co.kr`, `www.airbnb.co.uk`, `vrbo.com`, `secure.booking.com`; generator output; ingest validators from `test_agent_api`. Also `docs/porting-map.md` (every source file and its new home, or the ticket that ports it later) and the completed `knowledge/trip-planner-base.md`.

Tests: `npm run lint`, `npm run test:api`, `npm run test:web` each step; no user flow changes, so no e2e smoke; the dash grep before docs commits.

Risks: the flight, itinerary, lodging, presentation and ingest services in the base code import SQLAlchemy models and sessions, and Hermi has no database until WF-011 (prompt 04). So only DB-free logic is ported now; the DB-bound parts (itinerary, lodging, places, presentation and the deck, `quotes` queries, `routes`) are listed in the porting map against WF-029, WF-032, WF-033, WF-034 and WF-091, as 09 allows ("the rest may land as each feature ticket needs it"); record that in `DECISIONS.md`. `link_preview`, `serpapi*`, the CLI runner, the MCP bridge, APScheduler, passcode auth and the Windows scripts are not ported. New dependencies (`httpx` at runtime, the three font packages) are named by the architecture and the ticket. The token test lives in `apps/web` (vitest) because `packages/tokens` has no test script. Dependencies: WF-004 is merged (#8).

Owner-pending items: none. The Trip Planner repository is public and clones without access, so the prompt's owner-only clone step is not needed; ship notes this instead of adding a `HUMAN_TASKS.md` row.

## Setup prompts

Status values: `Not started`, `In progress (<branch>)`, `In review (#<pr>)`, `Done (#<pr>)`, `Stopped (<reason>)`.

| # | Prompt | Tickets | Status |
|---|---|---|---|
| S1 | [Spec fixes, runtime (README, 02, 03, 04, 06, 08)](S1-spec-runtime.md) | S1.1, S1.2, S1.3, S1.4, S1.5, S1.6, S1.7 | Done (#5) |
| S2 | [Spec fixes, product and UI (01, 05, 07, 10, design kit, brand)](S2-spec-product-ui.md) | S2.1, S2.2, S2.3, S2.4, S2.5 | Done (#6) |
| S3 | [Spec fixes, roadmap, prompts and lint](S3-spec-roadmap-prompts.md) | S3.1, S3.2, S3.3, S3.4, S3.5 | Done (#7) |

## Prompts

Same status values as above.

| # | Prompt | Tickets | Status |
|---|---|---|---|
| 01 | [Repository foundation, CI and landing page](01-repo-foundation.md) | WF-001, WF-003, WF-004, WF-006, WF-007, WF-008, WF-010, WF-002 | Done (#8) |
| 02 | [Port reusable code from the old Trip Planner](02-port-reusable-modules.md) | WF-005 | In progress (phase1/p02-port-reusable-modules) |
| 03 | [Staging and production environments](03-deploy-environments.md) | WF-009 | Not started |
| 04 | [Database foundation and schemas](04-database-foundation.md) | WF-011, WF-012, WF-022, WF-021, WF-020 | Not started |
| 05 | [Sign-in, tenancy and row-level security](05-auth-and-tenancy.md) | WF-013, WF-014, WF-015, WF-016 | Not started |
| 06 | [Web app platform, sign-in and trips](06-web-app-and-trips.md) | WF-017, WF-130, WF-018, WF-019 | Not started |
| 07 | [Entitlements, travelers, invites and roles](07-entitlements-and-collaboration.md) | WF-023, WF-024, WF-025, WF-026, WF-027, WF-028 | Not started |
| 08 | [Currency, cached fares and price alerts](08-fares-and-alerts.md) | WF-029, WF-030, WF-031 | Not started |
| 09 | [Itinerary, places, map, stays and notes](09-plan-and-stays.md) | WF-032, WF-033, WF-034, WF-035 | Not started |
| 10 | [Responsive layout, observability and sync indicator](10-layout-observability-sync.md) | WF-036, WF-037, WF-038, WF-039, WF-125 | Not started |
| 11 | [Import the owner's existing Trip Planner data](11-owner-data-migration.md) | WF-040, WF-133 | Not started |
| 12 | [AI schema, flags, metering, credits, ceilings, jobs and email](12-ai-and-credits-foundation.md) | WF-041, WF-042, WF-043, WF-044, WF-045, WF-046, WF-131, WF-047 | Not started |
| 13 | [Claude features, agent loop, research, evidence and guest mode](13-ai-features.md) | WF-048, WF-049, WF-050, WF-053, WF-054, WF-055, WF-120, WF-132, WF-062 | Not started |
| 14 | [Scheduler, live fares, breakers and evals](14-live-fares-scheduler-evals.md) | WF-051, WF-052, WF-056, WF-057 | Not started |
| 15 | [Admin console foundation](15-admin-foundation.md) | WF-058, WF-059, WF-060, WF-061 | Not started |
| 16 | [RevenueCat, credit grants, Trip Pass and paywalls](16-purchases-and-paywalls.md) | WF-063, WF-064, WF-065, WF-066, WF-076 | Not started |
| 17 | [Affiliate redirect, link builders, conversions and checklist](17-affiliate-and-checklist.md) | WF-067, WF-068, WF-069, WF-070 | Not started |
| 18 | [Switching imports and the first-import Trip Pass](18-switching-imports.md) | WF-071, WF-072, WF-073, WF-074, WF-121, WF-122 | Not started |
| 19 | [Verify this plan and the booked-fare drop alert](19-verify-plan-and-booked-fare.md) | WF-116, WF-117, WF-118, WF-075 | Not started |
| 20 | [Admin users, subscriptions, overview and affiliate revenue](20-admin-essentials.md) | WF-077, WF-078, WF-079, WF-099 | Not started |
| 21 | [iOS app shell and native features](21-ios-shell-and-native.md) | WF-080, WF-081, WF-082, WF-083, WF-084, WF-085, WF-086, WF-087 | Not started |
| 22 | [Offline, calendar feed, presentation and calendar polling](22-offline-calendar-present.md) | WF-088, WF-089, WF-090, WF-091, WF-123 | Not started |
| 23 | [Account deletion, export, settings, onboarding and accessibility](23-account-and-compliance.md) | WF-092, WF-093, WF-094, WF-095, WF-096 | Not started |
| 24 | [Performance polish, analytics, status, tests and TestFlight](24-polish-analytics-beta.md) | WF-097, WF-098, WF-100, WF-126, WF-101, WF-102, WF-103 | Not started |
| 25 | [Public pages, referrals, comparison pages, trust pages and Android web](25-growth-and-trust-pages.md) | WF-106, WF-107, WF-108, WF-109, WF-124, WF-127, WF-128 | Not started |
| 26 | [Admin support, user actions, flags and health](26-admin-launch.md) | WF-105, WF-113, WF-114 | Not started |
| 27 | [Security review, load test, runbooks and the Verify release gate](27-hardening.md) | WF-110, WF-112, WF-119 | Not started |
| 28 | [Store listing, review notes, submission and launch](28-launch.md) | WF-104, WF-111, WF-115, WF-129 | Not started |

## Notes for later prompts

Things a later prompt must know (a helper that exists, a pattern to reuse, a known limitation).

- S3 ship review follow-ups: (1) prompt 14 line 38 gives the live evals command in Bash form; the owner uses PowerShell, so point at `HUMAN_TASKS.md` row 21 instead. (2) Prompt 10 Owner-only steps name `VITE_SENTRY_DSN` and `VITE_POSTHOG_KEY`, `HUMAN_TASKS.md` row 13 lists other variables; make them equal. (3) Prompts 18, 22, 24, 25 and 27 have an "Owner verification pending" note (WF-121, WF-088 and 089, WF-100 to 102, WF-127 and 128, WF-112) that their Owner-only steps section does not list; add a bullet each.
- S2.1.1 follow-up for S2.2: the kit still calls the section strip a `tablist` (`design/DESIGN-LANGUAGE.md` near lines 179 and 236, `design/components.html` near 919 and 932, `h-strip` in `design/screens/` 03, 04, 06, 07, 08); 05 now says `nav` with `aria-current="page"`. Align the kit markup and wording.
- S1.5 follow-ups: 03 needs a place for the hashed legacy claim token (`POST /me/legacy-claim`, WF-040): a small table or columns on the pre-created legacy `users` row; 04 section 5.1 carries a note to remove once 03 has it. 03 `clear_my_ai_history` (line near 2906) only nulls run content, while 04 `DELETE /me/ai-history` deletes `runs`, `run_events` and AI notes; align 03. 01, 02 and 10 must mirror the 04 5.26 imports limits table. 03 gives `link_clicks.redirect_status` no value set; 04 defines it as the HTTP status sent (add a DECISIONS row if kept).
- S1.4 follow-ups: `bootstrap_user()` (03 section 6) needs a sixth parameter `p_provider_subject text` that writes `auth_identities.provider_subject`, with the ALTER, REVOKE and GRANT lines in 6.1 and 6.1.1 updated, and 04 `/me/bootstrap` passes it (S1.5 or an S1.3 round before the S1 merge). 04 must use `device_attestations`, `guest_allowances`, `spend_guest_allowance` and the guest endpoints. 08 line 278 must say `serpapi_live_fares` is off (S1.7). 07 section 5.4 needs a one-line match for the taster-first rule for `agent_run`. The `credit_grants_select` policy (6.4) must let trip members see `trip_pass` grants.

## Measured numbers

| Measure | Value | When |
|---|---|---|
| Average agent run cost (target at most $0.60) | not measured | |
| Crash-free sessions in beta (target above 99.5%) | not measured | |
