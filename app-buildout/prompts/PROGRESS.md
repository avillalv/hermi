# Phase 1 progress

The build's memory. Every autopilot session updates this file in its pull request, and the next session resumes from here (see [AUTOPILOT.md](AUTOPILOT.md)). The driver runs the units in order: S1 to S3, then prompts 01 to 28, then the final check.

## Current prompt

06 in progress on `phase1/p06-web-app-and-trips`. Steps in order:

1. WF-017: `npm run gen:api` for real (`hermi.tools.dump_openapi` to `apps/web/src/lib/api/openapi.json`, `openapi-typescript` to `schema.d.ts`), `client.ts` on `openapi-fetch` (bearer only, one refresh on 401 then sign-out, `ApiError` from problem+json, the 04 section 7 headers), `env.ts`, CORS origins and a preflight test. Vitest client tests on a mock server.
2. WF-130.1: `packages/tokens` gets `hermi.css` verbatim next to `tokens.css` (values from 05 section 2); Logo from `app-buildout/brand/`, `generate_logo.py` extended for transparent lockups, light wordmark and web icons in `apps/web/public/`.
3. WF-130.2: Playwright (Chromium, WebKit), kit fixture, frozen clock, fonts routed to the bundled files, pixelmatch in one run, `kit-metrics`, `npm run test:kit` and `npm run test:e2e`; stylelint `declaration-strict-value`.
4. WF-130.3: React wrappers in `apps/web/src/components/kit/` emitting the `h-` classes (Logo, RoutePattern, ticket, sheet, tab bar, section strip as `nav` with `aria-current`), component parity for every `components.html` block.
5. WF-130.4: React Router 7 and the scrolling shell in `apps/web/src/shell/` (strip, sheet, tab bar, rail 768 to 1199 px, 248 px sidebar from 1200 px, placeholder tabs), layout tests at 390 to 1440 px, fonts and network check, focus rings.
6. WF-018.1: sign-in screens (Apple, Google, email code via supabase-js; persona picker when `AUTH_MODE=dev` via `POST /v1/dev/session`), sign-out clears state, `locales/en.json`, Playwright smoke flow 1.
7. WF-018.2: auth guard (signed-out visits go to Welcome per 05 6.1 or guest mode, with a signed-in fixture for the shell tests), intro, age gate, first-trip wizard, profile sheet (05 6.4), plus `GET` and `POST /v1/trips` so the wizard creates a trip.
8. WF-019.1: rest of the trips and destinations API (04 section 5.4), archive as `PATCH` status, duplicate, trash and restore, `route_policy.py` entries, tenancy and viewer-refused tests.
9. WF-019.2: Trips home (05 6.5) and Overview (6.7) with "Happening now".
10. WF-019.3: edit, archive, duplicate, trash and restore, trip switcher, place autocomplete and destination time zone, Playwright smoke flow 26 and the prompt's sign-in plus create-trip smoke test.

Risks: 04 has no duplicate endpoint; WF-019.1 adds `POST /v1/trips/{id}/duplicate` with a `DECISIONS.md` row. The wizard needs trip creation before WF-019, so WF-018.2 carries the create and list routes. New dependencies, all named in the stack (README, 02, 04): react-router, openapi-fetch, openapi-typescript, @supabase/supabase-js, @playwright/test, pixelmatch, stylelint. Paths: the ticket says `brand/generate_logo.py`, the file is `app-buildout/brand/`; 04 says `frontend/src/lib/api/`, 02 and the roadmap say `apps/web/`. The kit still calls the section strip a `tablist`; 05 (`nav`) wins and parity tests must allow it. Every new route goes in `apps/api/tests/route_policy.py`.

Owner verification pending: the three "on staging" criteria (WF-017 client, WF-018 under 2 minutes, WF-019 create a trip).

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
| 02 | [Port reusable code from the old Trip Planner](02-port-reusable-modules.md) | WF-005 | Done (#12) |
| 03 | [Staging and production environments](03-deploy-environments.md) | WF-009 | Done (#13) |
| 04 | [Database foundation and schemas](04-database-foundation.md) | WF-011, WF-012, WF-022, WF-021, WF-020 | Done (#15) |
| 05 | [Sign-in, tenancy and row-level security](05-auth-and-tenancy.md) | WF-013, WF-014, WF-015, WF-016 | Done (#17) |
| 06 | [Web app platform, sign-in and trips](06-web-app-and-trips.md) | WF-017, WF-130, WF-018, WF-019 | In progress (phase1/p06-web-app-and-trips) |
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

- WF-130.4 follow-ups: no axe check covers the shell yet (add `@axe-core/playwright` in the ticket that needs it); `routes.tsx` has no catch-all or not-found route; `.shell-trips` placeholder in `shell.css` is declared `display: none` after the 1200px media query so it never shows (move it above, render it between logo and nav when WF-019 builds the trip switcher).
- P05 for later routes: every new route must be classified in `apps/api/tests/route_policy.py` or the tenancy suite in `apps/api/tests/tenancy/` fails; trip routes take `require_trip`; routers never import trip models or call `session.get(` (AST test). `npm run gen:api` is still a stub, so no generated types yet.
- WF-013.2 deferred: `POST /v1/me/bootstrap` does not yet emit `user_signed_up` (analytics ticket in prompt 10), has no 30 per IP per 10 minutes rate limit (04 section 1.8; the rate-limit ticket must add it), and ignores the body fields `device`, `claim` and `referral_code` (WF-040 and the referral ticket). The `email_in_use` case for a pending legacy row is WF-040. `Me.flags` and `min_client_version` are placeholders marked `shortcut:`. Routes that must accept a pending_deletion user use `DbSessionOrPendingDeletion` in `deps.py`.
- S3 ship review follow-ups: (1) prompt 14 line 38 gives the live evals command in Bash form; the owner uses PowerShell, so point at `HUMAN_TASKS.md` row 21 instead. (2) Prompt 10 Owner-only steps name `VITE_SENTRY_DSN` and `VITE_POSTHOG_KEY`, `HUMAN_TASKS.md` row 13 lists other variables; make them equal. (3) Prompts 18, 22, 24, 25 and 27 have an "Owner verification pending" note (WF-121, WF-088 and 089, WF-100 to 102, WF-127 and 128, WF-112) that their Owner-only steps section does not list; add a bullet each.
- S2.1.1 follow-up for S2.2: the kit still calls the section strip a `tablist` (`design/DESIGN-LANGUAGE.md` near lines 179 and 236, `design/components.html` near 919 and 932, `h-strip` in `design/screens/` 03, 04, 06, 07, 08); 05 now says `nav` with `aria-current="page"`. Align the kit markup and wording.
- S1.5 follow-ups: 03 needs a place for the hashed legacy claim token (`POST /me/legacy-claim`, WF-040): a small table or columns on the pre-created legacy `users` row; 04 section 5.1 carries a note to remove once 03 has it. 03 `clear_my_ai_history` (line near 2906) only nulls run content, while 04 `DELETE /me/ai-history` deletes `runs`, `run_events` and AI notes; align 03. 01, 02 and 10 must mirror the 04 5.26 imports limits table. 03 gives `link_clicks.redirect_status` no value set; 04 defines it as the HTTP status sent (add a DECISIONS row if kept).
- P04 follow-ups: the first ticket that opens the app engine must call `hermi.db.assert_app_login_is_safe`; the worker ticket must pin `procrastinate==3.10.0` or newer; models for flights, itinerary, places, lodging, checklist, notes, imports and affiliate belong to their feature tickets (WF-030, 032, 033, 034, 070, 041, 108); the admin console functions of 08 section 6 are left to their ticket; 03 section 6.1.1 should get the final DDL of the seven functions written in 0014.
- S1.4 follow-ups: `bootstrap_user()` (03 section 6) needs a sixth parameter `p_provider_subject text` that writes `auth_identities.provider_subject`, with the ALTER, REVOKE and GRANT lines in 6.1 and 6.1.1 updated, and 04 `/me/bootstrap` passes it (S1.5 or an S1.3 round before the S1 merge). 04 must use `device_attestations`, `guest_allowances`, `spend_guest_allowance` and the guest endpoints. 08 line 278 must say `serpapi_live_fares` is off (S1.7). 07 section 5.4 needs a one-line match for the taster-first rule for `agent_run`. The `credit_grants_select` policy (6.4) must let trip members see `trip_pass` grants.

## Measured numbers

| Measure | Value | When |
|---|---|---|
| Average agent run cost (target at most $0.60) | not measured | |
| Crash-free sessions in beta (target above 99.5%) | not measured | |
- WF-019.2 (for WF-019.3 and later): `/trips/:id/edit` and `/trips/:id/plan` links from Overview have no route yet (blank page until WF-019.3 and the plan ticket). Still to add: ticket-shaped skeletons (4.4) and five Overview skeleton cards (6.7), "Saved offline" chip and card icon, Past toggle for archived trips, Playwright offline and error tests with smoke flow 26, Happening now by destination time zone instead of viewer date. The "Coming from TripIt" empty-state card waits for 6.30. Unused: `overview.sections`, `overview.travelers`, `.overview__row`, `.overview__lead`.
