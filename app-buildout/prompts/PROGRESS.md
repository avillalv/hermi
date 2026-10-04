# Phase 1 progress

The build's memory. Every autopilot session updates this file in its pull request, and the next session resumes from here (see [AUTOPILOT.md](AUTOPILOT.md)). The driver runs the units in order: S1 to S3, then prompts 01 to 28, then the final check.

## Current prompt

04, database foundation and schemas (branch `phase1/p04-database-foundation`). Lands 03 section 10 `0001` to `0015` as one linear Alembic chain, one revision group per step, in the prompt's ticket order (which is also the revision order). Eleven steps, one session each:

1. WF-011 Migration framework and roles: add SQLAlchemy 2, Alembic and Procrastinate (all in the README stack) to `apps/api/pyproject.toml`; `apps/api/alembic.ini`, `apps/api/hermi/migrations/` (`env.py` logging in as `hermi_migrate_login` via `MIGRATION_DATABASE_URL`, `lock_timeout` and `statement_timeout`, `pg_advisory_lock` around `upgrade head`, `NAMING_CONVENTION` of 03 section 2), `0001_setup` (03 section 3 plus the role check that stops with "run `npm run db:init`"), `apps/api/hermi/db.py` (engines, the startup check that the app login is no superuser, `BYPASSRLS`, owner or owner member), a Python UUIDv7 helper, `hermi migrate` in `cli.py` (replaces the placeholder), pytest database fixtures (`TEST_DATABASE_URL` app login, `TEST_DATABASE_URL_SYSTEM`, `TEST_MIGRATION_DATABASE_URL`), `bootstrap.sql` idempotency check, the expand and contract policy in `.claude/rules/database-migrations.md`. Tests: migration from empty, head count, role privileges (`hermi_app` cannot run DDL), role missing.
2. WF-012.1 `0002_identity` and `0003_reference_catalog` (03 sections 5.1 to 5.3) with models in `modules/auth/models.py` and the reference and catalog models.
3. WF-012.2 `0004_trips_people` (5.4, 5.5: owner-member trigger, `redeem_trip_invite`, `transfer_trip_owner`) with `modules/{trips,collaboration}/models.py`, Pydantic schemas, and the reusable schema-vs-DDL comparison test. Constraint tests (unique member per trip, valid roles).
4. WF-022.1 `0005_ai` (5.6, the section 9 partition functions and first partitions, Procrastinate's schema from the installed library's SQL, the `job_heartbeats` view).
5. WF-022.2 `0006_billing_credits` (5.7, 5.8: append-only `credit_ledger` trigger, credit functions) with `modules/billing/models.py`. Tests: uniqueness of store transaction id and webhook event id, one active pass per trip, ledger rejects `UPDATE` and `DELETE`.
6. WF-022.3 `0007_imports_referrals` and `0008_affiliate` (5.9, 5.10, materialized views) with `modules/affiliate/models.py`.
7. WF-021.1 `0009_flights` (5.11, 5.12) with `modules/flights/models.py`.
8. WF-021.2 `0010_itinerary_lodging` and `0011_checklist_notes` (5.13 to 5.15) with `modules/{itinerary,places,lodging,trips}/models.py`. Foreign key and cascade tests.
9. WF-020.1 `0012_admin_privacy` and `0013_notifications_samples` (5.16 to 5.20, append-only `audit_log` trigger) with `modules/{admin,notifications}/models.py`. Trigger test.
10. WF-020.2 `0014_rls` (all of section 6, the section 8 retention and purge functions, the section 9 maintenance functions, `trip_member_profiles`, the `SECURITY DEFINER` ownership loop, `SELECT` on `alembic_version` for the app login so `/health/ready` reads it). The 03 section 6.5 grants-and-RLS test as `hermi_api_login`.
11. WF-020.3 `0015_seed` (section 11, `ON CONFLICT DO NOTHING`), `apps/api/hermi/seed/` and `hermi seed` (setup runs `hermi seed --demo` once the folder exists, so `--demo` must exist and do nothing harmful until WF-133), the two test users and a shared trip as pytest fixtures, seed idempotency test, and the whole-chain test (one head, no 03 table, type or function missing, round trip `downgrade base` then `upgrade head`).

Tests each step: `npm run lint`, `npm run test:api`, `npm run test:web` against native PostgreSQL 18; no user flow changes, so no e2e smoke. CI already runs `db:init`, the single-head check and the round trip once `apps/api/alembic.ini` exists.

Risks:
- Grants and policies: 03 section 10 puts every grant and policy in `0014`, while `.claude/rules/database-migrations.md` says they land with the table. 03 wins for `0001` to `0014`; tables added after `0014` carry their own (03 line 3833). Until step 10, tests read the catalog as `hermi_migrate_login`, not through the app login. WF-011 clarifies the rules file.
- 03 open items the steps must settle with a `DECISIONS.md` row and a 03 edit in the same commit: `bootstrap_user` takes a sixth parameter `p_provider_subject` (S1.4 note); `credit_grants_select` lets trip members see `trip_pass` grants; seven `SECURITY DEFINER` functions have grants but no body in 03 (`request_account_deletion`, `cancel_account_deletion`, `advance_trip_import`, `link_my_traveler`, `file_content_report`, `clear_run_content`, `clear_my_ai_history`), written in `0014`, with `clear_my_ai_history` matching 04 (deletes runs, run events and AI notes); `link_clicks.redirect_status` is the HTTP status sent.
- The hashed legacy claim token (WF-040, prompt 11) has no table in 03; not invented here, left for prompt 11.
- Procrastinate's schema SQL is vendored from the pinned library version; a later upgrade of the library needs its own migration.
- `0014` is about 800 lines of SQL in one revision; if review stalls, the step splits by policy group into sub-steps of the same revision file.
- Dependencies: WF-008 is merged (#8); prompts 01 to 03 are Done.

Owner-pending items: none for this prompt.

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
| 04 | [Database foundation and schemas](04-database-foundation.md) | WF-011, WF-012, WF-022, WF-021, WF-020 | In progress (phase1/p04-database-foundation) |
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
