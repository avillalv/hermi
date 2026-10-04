# Phase 1 progress

The build's memory. Every autopilot session updates this file in its pull request, and the next session resumes from here (see [AUTOPILOT.md](AUTOPILOT.md)). The driver runs the units in order: S1 to S3, then prompts 01 to 28, then the final check.

## Current prompt

S2, spec fixes, product and UI (branch `spec/s2-spec-product-ui`). Documents only, no code.

Steps, in order (one session each):

1. S2.1.1 UI and UX spec, tokens and rules: items 1 to 8 and 11 to 13 (font stacks, machine-readable token tables, `--tp-ticket`, heat-ink and `--viz-band` with contrast rows, solid focus ring, Secondary button mapping, kit precedence line, 1200 px sidebar, section 6 state rule, section strip as `nav`, Dynamic Type, portrait on phones) in `05-ui-ux-spec.md`.
2. S2.1.2 UI and UX spec, screens: items 9, 10 and 14 to 19 (Discover sample trips gallery, Overview "Happening now", disclosure snapshot, credit pool display, Delete my AI history, guest local data, import and calendar feed wording, 402 limits) in `05-ui-ux-spec.md`.
3. S2.2 Design kit and brand (`design/tokens.css`, `design/components.html`, `DESIGN-LANGUAGE.md`, `design/README.md`, `brand/BRAND.md`).
4. S2.3 Product spec (`01-product-spec.md`).
5. S2.4 Monetization spec (`07-monetization-spec.md`).
6. S2.5.1 Quality, security and launch, testing: items 1 to 3 (integration test rules, evals, smoke flows mapped to the journeys).
7. S2.5.2 Quality, security and launch, the rest: items 4 to 11 (security controls, never-fetch test, privacy, analytics catalogue, alerts, launch checklist tags, calendar feed token, no `routines`).

Tests: `node scripts/spec-lint.mjs` and the dash grep before every commit; `opus-reviewer` checks every fix by its number and that nothing outside the ticket's file group changed. The S2.2 reviewer diffs 05 section 2 against `tokens.css` (design-token-sync rule).

Risks: S2.1 and S2.5 are split because of their size; each half must stay within its own items and both halves edit the same file. S2.2 depends on S2.1.1 values. The S1 follow-ups for these files are covered here: 01 and 10 mirror the 04 section 5.26 imports limits table (S2.3 item 7, S2.5 item 8) and 07 section 5.4 states the taster-first rule (S2.4 item 2). Names a fix does not give are chosen once and recorded in `DECISIONS.md`.

Owner-pending items: none.

## Setup prompts

Status values: `Not started`, `In progress (<branch>)`, `In review (#<pr>)`, `Done (#<pr>)`, `Stopped (<reason>)`.

| # | Prompt | Tickets | Status |
|---|---|---|---|
| S1 | [Spec fixes, runtime (README, 02, 03, 04, 06, 08)](S1-spec-runtime.md) | S1.1, S1.2, S1.3, S1.4, S1.5, S1.6, S1.7 | Done (#5) |
| S2 | [Spec fixes, product and UI (01, 05, 07, 10, design kit, brand)](S2-spec-product-ui.md) | S2.1, S2.2, S2.3, S2.4, S2.5 | In progress (spec/s2-spec-product-ui) |
| S3 | [Spec fixes, roadmap, prompts and lint](S3-spec-roadmap-prompts.md) | S3.1, S3.2, S3.3, S3.4, S3.5 | Not started |

## Prompts

Same status values as above.

| # | Prompt | Tickets | Status |
|---|---|---|---|
| 01 | [Repository foundation, CI and landing page](01-repo-foundation.md) | WF-001, WF-002, WF-003, WF-004, WF-006, WF-007, WF-008, WF-010 | Not started |
| 02 | [Port reusable code from the old Trip Planner](02-port-reusable-modules.md) | WF-005 | Not started |
| 03 | [Staging and production environments](03-deploy-environments.md) | WF-009 | Not started |
| 04 | [Database foundation and schemas](04-database-foundation.md) | WF-011, WF-012, WF-020, WF-021, WF-022 | Not started |
| 05 | [Sign-in, tenancy and row-level security](05-auth-and-tenancy.md) | WF-013, WF-014, WF-015, WF-016 | Not started |
| 06 | [Web app platform, sign-in and trips](06-web-app-and-trips.md) | WF-017, WF-018, WF-019 | Not started |
| 07 | [Entitlements, travelers, invites and roles](07-entitlements-and-collaboration.md) | WF-023, WF-024, WF-025, WF-026, WF-027, WF-028 | Not started |
| 08 | [Currency, cached fares and price alerts](08-fares-and-alerts.md) | WF-029, WF-030, WF-031 | Not started |
| 09 | [Itinerary, places, map, stays and notes](09-plan-and-stays.md) | WF-032, WF-033, WF-034, WF-035 | Not started |
| 10 | [Responsive layout, observability and sync indicator](10-layout-observability-sync.md) | WF-036, WF-037, WF-038, WF-039, WF-125 | Not started |
| 11 | [Import the owner's existing Trip Planner data](11-owner-data-migration.md) | WF-040 | Not started |
| 12 | [AI schema, flags, metering, credits, ceilings, jobs and email](12-ai-and-credits-foundation.md) | WF-041, WF-042, WF-043, WF-044, WF-045, WF-046, WF-047 | Not started |
| 13 | [Claude features, agent loop, research, evidence and guest mode](13-ai-features.md) | WF-048, WF-049, WF-050, WF-053, WF-054, WF-055, WF-120, WF-062 | Not started |
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

- S2.1.1 follow-up for S2.2: the kit still calls the section strip a `tablist` (`design/DESIGN-LANGUAGE.md` near lines 179 and 236, `design/components.html` near 919 and 932, `h-strip` in `design/screens/` 03, 04, 06, 07, 08); 05 now says `nav` with `aria-current="page"`. Align the kit markup and wording.
- S1.5 follow-ups: 03 needs a place for the hashed legacy claim token (`POST /me/legacy-claim`, WF-040): a small table or columns on the pre-created legacy `users` row; 04 section 5.1 carries a note to remove once 03 has it. 03 `clear_my_ai_history` (line near 2906) only nulls run content, while 04 `DELETE /me/ai-history` deletes `runs`, `run_events` and AI notes; align 03. 01, 02 and 10 must mirror the 04 5.26 imports limits table. 03 gives `link_clicks.redirect_status` no value set; 04 defines it as the HTTP status sent (add a DECISIONS row if kept).
- S1.4 follow-ups: `bootstrap_user()` (03 section 6) needs a sixth parameter `p_provider_subject text` that writes `auth_identities.provider_subject`, with the ALTER, REVOKE and GRANT lines in 6.1 and 6.1.1 updated, and 04 `/me/bootstrap` passes it (S1.5 or an S1.3 round before the S1 merge). 04 must use `device_attestations`, `guest_allowances`, `spend_guest_allowance` and the guest endpoints. 08 line 278 must say `serpapi_live_fares` is off (S1.7). 07 section 5.4 needs a one-line match for the taster-first rule for `agent_run`. The `credit_grants_select` policy (6.4) must let trip members see `trip_pass` grants.

## Measured numbers

| Measure | Value | When |
|---|---|---|
| Average agent run cost (target at most $0.60) | not measured | |
| Crash-free sessions in beta (target above 99.5%) | not measured | |
