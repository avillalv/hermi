# Phase 1 progress

The build's memory. Every autopilot session updates this file in its pull request, and the next session resumes from here (see [AUTOPILOT.md](AUTOPILOT.md)). The driver runs the units in order: S1 to S3, then prompts 01 to 28, then the final check.

## Current prompt

05, sign-in, tenancy and row-level security (branch `phase1/p05-auth-and-tenancy`). The API has only `/health` and the waitlist today: no `/v1` router, no `deps.py`, no JWT code, no request session and no `repo.py` anywhere, so this prompt builds the request path from scratch. Six steps, one session each:

1. WF-013.1 Token verification and the request path: `apps/api/hermi/security/jwt.py` (JWKS by `kid`, cached 1 hour, refetch at most once a minute on an unknown `kid`; `iss`, `aud`, `exp`, `nbf` with 30 s skew, `sub`; algorithm allowlist that rejects `none` and mismatches; `AUTH_MODE=dev` local key pair and local JWKS, refused outside `local` and `ci` in `config.py` and again at verify time), the app engine and per-request transaction in `db.py` that calls `assert_app_login_is_safe` at startup and runs `set_config('app.user_id', ..., true)`, `apps/api/hermi/deps.py` (`DbSession`, `CurrentUser` resolving `auth_identities(provider, subject)`, `403 account_inactive` and `account_pending_deletion`), the `/v1` router and the 04 section 1.4 problem+json handler (422 becomes `validation_failed`). `0016_bootstrap_subject`: `bootstrap_user` gains the sixth parameter `p_provider_subject text` that writes `auth_identities.provider_subject` (S1.4 note), with REVOKE and GRANT redone, plus the 03 section 6 edit in the same commit. New dependency PyJWT with `cryptography`: the step asks `opus-judge` first and records the `DECISIONS.md` row. Tests: the token matrix with a local JWKS (expired, wrong audience, wrong issuer, tampered, unknown `kid`), the algorithm allowlist test, dev mode refused outside `local` and `ci`, migration head and round trip.
2. WF-013.2 Provisioning: `modules/auth/{router,service,repo}.py` with `POST /v1/me/bootstrap` (201 new, 200 existing, 409 `email_in_use`, creates the "Me" `people` row, `identity_hashes` check so a re-created account gets no second taster or first-import pass) and `GET /v1/me`; dev routes `GET /v1/dev/personas` and `POST /v1/dev/session` (mounted only when `AUTH_MODE=dev` and the environment is `local` or `ci`, absent from the production OpenAPI), the first dev session creates the Free, Plus and admin personas through the same bootstrap path; `SUPABASE_URL` documented in `.env.example` and `knowledge/`. Passcode code was never ported (P02), so "retire the passcode path" is a check that nothing references it. Tests: dev persona and session route tests, identity-hash test, concurrent first-login test (exactly one user), Apple "Hide My Email" relay address accepted.
3. WF-014 Data access layer: `require_trip_access(user, trip_id, min_role)` and the `require_trip` dependency in `deps.py` (non-member `404 not_found`, low role `403 insufficient_role`), `repo.py` for `auth`, `trips` and `collaboration` with tenant-filtered helpers, the one-constant `SystemSession` allowlist (03 section 6.6 purposes) with its test, the static test in the style of `tests/test_forbidden_imports.py` that fails when a `router.py` imports a trip model or calls `session.get(` outside a `repo.py` (stands in for import-linter, `DECISIONS.md` row), and the `app.routes` walk that fails when a route with a `trip_id` lacks `require_trip`. No trip routes exist yet (WF-019 builds them), so the permission matrix runs against `/v1/me` and a test-only router mounted in the test app for each role.
4. WF-015 RLS wiring: confirm `app.user_id` is set per transaction and never leaks across pooled connections, the startup refusal (superuser, `BYPASSRLS`, table owner or owner member) with its test, `FORCE` verification on every RLS table, policy tests as `hermi_api_login` that bypass the app layer (no session variable gives zero rows; the forced bug test removes the app check and still cannot read another tenant), and the policy list documented in `knowledge/`.
5. WF-016.1 Middleware in `apps/api/hermi/security/`: `Idempotency-Key` (required on credit or money POSTs with `400 idempotency_key_required`, honored on the others, 24 hour replay from `idempotency_keys`, keyed per user) and `If-Match` or body `version` (`428 precondition_required`, `409 version_conflict` with `current`), with tests on test-only routes.
6. WF-016.2 The suite in `apps/api/tests/tenancy/`: shared fixtures for users A, B and viewer C plus a shared trip, `tests/route_policy.py` classifying every route (`tenant`, `user_scoped`, `public`, `token_feed`, `webhook`, `admin`), the OpenAPI-driven walk of 10 section 1.3 items 1 to 9 (wrong tenant 403 or 404, viewer writes 403 or 404, no token 401 outside the public allowlist, sentinel strings, the direct database pass as the API role), failure on any unclassified route, and the mutation check (remove one guard, the suite fails). Recorded as Month 1 gate evidence in `knowledge/`.

Tests each step: `npm run lint`, `npm run test:api`, `npm run test:web` against native PostgreSQL 18. Routes change in WF-013 and later, so each such step runs `npm run gen:api`. No web user flow changes, so no e2e smoke (WF-017 and WF-018 wire the web sign-in in prompt 06).

Risks:
- New dependency: no JWT library is named in the stack. PyJWT with `cryptography` needs an `opus-judge` decision in WF-013.1 before it is added.
- 03 disagreement: `auth_identities.provider_subject` says `bootstrap_user` sets it, but the 03 and `0014_rls` function has five parameters. WF-013.1 adds `0016_bootstrap_subject` (expand only) and edits 03 section 6 in the same commit with a `DECISIONS.md` row; `0014` is merged, so it is not edited.
- `assert_app_login_is_safe` exists in `db.py` but nothing calls it; WF-013.1 wires it when it opens the app engine, WF-015 adds the refusal test.
- import-linter is not installed; WF-014 uses an AST test like `test_forbidden_imports.py` unless `opus-judge` approves adding import-linter.
- With almost no routes, the leak suite proves little until features land; it must pick up new routes automatically, so later prompts only classify routes in `route_policy.py`.
- `tests/conftest.py` has no shared database fixtures; module fixtures in the P04 tests set `app.user_id` by hand. WF-013.1 adds shared fixtures that later steps reuse.
- Dependencies: WF-012 and WF-020 are merged (#15); prompts 01 to 04 are Done.

Owner-pending items: none. Owner-only step (optional real Supabase sign-in, `AUTH_MODE=supabase`) becomes a `HUMAN_TASKS.md` row in WF-013.2.

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
| 05 | [Sign-in, tenancy and row-level security](05-auth-and-tenancy.md) | WF-013, WF-014, WF-015, WF-016 | In progress (phase1/p05-auth-and-tenancy) |
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
