# Phase 1 build prompts

These prompts build all of Hermi Phase 1 in 28 steps, after three setup prompts (S1 to S3) that fix
the specification. The autopilot runs them in order, one pull request each. Start it with
[KICKOFF.md](KICKOFF.md).

| File | Purpose |
|---|---|
| [KICKOFF.md](KICKOFF.md) | How to start, watch, stop and resume the autopilot, plus your one-time setup |
| [AUTOPILOT.md](AUTOPILOT.md) | The creation prompt appended to every autopilot session: modes, stop list, owner verification pending |
| [00-orchestrator.md](00-orchestrator.md) | The rulebook: models, subagents, the driver's unit flow, gates, stop conditions |
| [S1-spec-runtime.md](S1-spec-runtime.md) | Setup prompt 1, run before 01: fix the runtime spec (README, 02, 03, 04, 06, 08) |
| [S2-spec-product-ui.md](S2-spec-product-ui.md) | Setup prompt 2, run before 01: fix the product and UI spec (01, 05, 07, 10, design kit, brand) |
| [S3-spec-roadmap-prompts.md](S3-spec-roadmap-prompts.md) | Setup prompt 3, run before 01: fix the roadmap, the prompts and the lint |
| [PROGRESS.md](PROGRESS.md) | Status of every prompt; the build's memory between sessions |
| [HUMAN_TASKS.md](HUMAN_TASKS.md) | Things only you can do (accounts, keys, iOS signing, App Store), in order |
| [DECISIONS.md](DECISIONS.md) | Judgement calls made during the build |

## Autopilot

The autopilot is a Node driver (`scripts/autopilot/run.mjs`) that runs one fresh Claude Code session
for every plan, ticket and ship step, in this order: S1 to S3, prompts 01 to 28, then a final check.
Sonnet 5.5 writes the code, Opus 5.5 plans and reviews, and the driver merges each pull request after
the check named `ci` has passed and every Opus verdict it needs is in (every ticket, plus the final gate
and any ci-fix or late ship change). Session rules are in
[AUTOPILOT.md](AUTOPILOT.md) and build rules in [00-orchestrator.md](00-orchestrator.md).

## The 3 setup prompts

They run before prompt 01 and fix the specification, one file group per ticket.

| # | Prompt | Tickets |
|---|---|---|
| S1 | [Spec fixes, runtime (README, 02, 03, 04, 06, 08)](S1-spec-runtime.md) | S1.1, S1.2, S1.3, S1.4, S1.5, S1.6, S1.7 |
| S2 | [Spec fixes, product and UI (01, 05, 07, 10, design kit, brand)](S2-spec-product-ui.md) | S2.1, S2.2, S2.3, S2.4, S2.5 |
| S3 | [Spec fixes, roadmap, prompts and lint](S3-spec-roadmap-prompts.md) | S3.1, S3.2, S3.3, S3.4, S3.5 |

## The 28 prompts

| # | Prompt | Tickets |
|---|---|---|
| 01 | [Repository foundation, CI and landing page](01-repo-foundation.md) | WF-001, WF-002, WF-003, WF-004, WF-006, WF-007, WF-008, WF-010 |
| 02 | [Port reusable code from the old Trip Planner](02-port-reusable-modules.md) | WF-005 |
| 03 | [Staging and production environments](03-deploy-environments.md) | WF-009 |
| 04 | [Database foundation and schemas](04-database-foundation.md) | WF-011, WF-012, WF-020, WF-021, WF-022 |
| 05 | [Sign-in, tenancy and row-level security](05-auth-and-tenancy.md) | WF-013, WF-014, WF-015, WF-016 |
| 06 | [Web app platform, sign-in and trips](06-web-app-and-trips.md) | WF-017, WF-018, WF-019 |
| 07 | [Entitlements, travelers, invites and roles](07-entitlements-and-collaboration.md) | WF-023, WF-024, WF-025, WF-026, WF-027, WF-028 |
| 08 | [Currency, cached fares and price alerts](08-fares-and-alerts.md) | WF-029, WF-030, WF-031 |
| 09 | [Itinerary, places, map, stays and notes](09-plan-and-stays.md) | WF-032, WF-033, WF-034, WF-035 |
| 10 | [Responsive layout, observability and sync indicator](10-layout-observability-sync.md) | WF-036, WF-037, WF-038, WF-039, WF-125 |
| 11 | [Import the owner's existing Trip Planner data](11-owner-data-migration.md) | WF-040 |
| 12 | [AI schema, flags, metering, credits, ceilings, jobs and email](12-ai-and-credits-foundation.md) | WF-041, WF-042, WF-043, WF-044, WF-045, WF-046, WF-047 |
| 13 | [Claude features, agent loop, research, evidence and guest mode](13-ai-features.md) | WF-048, WF-049, WF-050, WF-053, WF-054, WF-055, WF-120, WF-062 |
| 14 | [Scheduler, live fares, breakers and evals](14-live-fares-scheduler-evals.md) | WF-051, WF-052, WF-056, WF-057 |
| 15 | [Admin console foundation](15-admin-foundation.md) | WF-058, WF-059, WF-060, WF-061 |
| 16 | [RevenueCat, credit grants, Trip Pass and paywalls](16-purchases-and-paywalls.md) | WF-063, WF-064, WF-065, WF-066, WF-076 |
| 17 | [Affiliate redirect, link builders, conversions and checklist](17-affiliate-and-checklist.md) | WF-067, WF-068, WF-069, WF-070 |
| 18 | [Switching imports and the first-import Trip Pass](18-switching-imports.md) | WF-071, WF-072, WF-073, WF-074, WF-121, WF-122 |
| 19 | [Verify this plan and the booked-fare drop alert](19-verify-plan-and-booked-fare.md) | WF-116, WF-117, WF-118, WF-075 |
| 20 | [Admin users, subscriptions, overview and affiliate revenue](20-admin-essentials.md) | WF-077, WF-078, WF-079, WF-099 |
| 21 | [iOS app shell and native features](21-ios-shell-and-native.md) | WF-080, WF-081, WF-082, WF-083, WF-084, WF-085, WF-086, WF-087 |
| 22 | [Offline, calendar feed, presentation and calendar polling](22-offline-calendar-present.md) | WF-088, WF-089, WF-090, WF-091, WF-123 |
| 23 | [Account deletion, export, settings, onboarding and accessibility](23-account-and-compliance.md) | WF-092, WF-093, WF-094, WF-095, WF-096 |
| 24 | [Performance polish, analytics, status, tests and TestFlight](24-polish-analytics-beta.md) | WF-097, WF-098, WF-100, WF-126, WF-101, WF-102, WF-103 |
| 25 | [Public pages, referrals, comparison pages, trust pages and Android web](25-growth-and-trust-pages.md) | WF-106, WF-107, WF-108, WF-109, WF-124, WF-127, WF-128 |
| 26 | [Admin support, user actions, flags and health](26-admin-launch.md) | WF-105, WF-113, WF-114 |
| 27 | [Security review, load test, runbooks and the Verify release gate](27-hardening.md) | WF-110, WF-112, WF-119 |
| 28 | [Store listing, review notes, submission and launch](28-launch.md) | WF-104, WF-111, WF-115, WF-129 |

The order follows `../phase-1-launch/09-build-roadmap.md` and every ticket's dependencies were
checked against it: no prompt needs a ticket from a later prompt. All 129 Phase 1 tickets are
covered; WF-122 and WF-129 are on the roadmap's cut list and are built only if there is room.
