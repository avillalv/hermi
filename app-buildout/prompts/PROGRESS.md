# Phase 1 progress

The build's memory. Every autopilot session updates this file in its pull request, and the next session resumes from here (see [AUTOPILOT.md](AUTOPILOT.md)). The driver runs the units in order: S1 to S3, then prompts 01 to 28, then the final check.

## Current prompt

01, repository foundation, CI and landing page (branch `phase1/p01-repo-foundation`).

Steps, in order (one session each):

1. WF-001 Name, domain and email: `docs/adr/0001-name.md` (trademark search checklist, provisional name decision), DNS and mail record list in `infra/cloudflare/rules.md`, `infra/scripts/check-mail-auth` (takes a domain, exits non-zero on a missing record). `Done (docs)` plus a provisional "go" row in `DECISIONS.md`.
2. WF-003 Interview kit, price test and terms checklist: `docs/validation/` (interview script, written "yes" signal, price test cards, switching question, provider terms checklist). `Done (docs)` plus a provisional "go" row in `DECISIONS.md`.
3. WF-004.1 Scaffold, monorepo skeleton: the 02 section 2 tree (`apps/api` FastAPI on uv, `apps/worker`, `apps/web` Vite, React 19, TanStack Query, Tailwind 4, `packages/shared`, `packages/tokens`, `packages/eslint-config`, `infra/`, `docs/`), uv and npm workspaces, `.python-version` (3.13), Node 22 pin, `posix_only` marker, Selector loop in `cli.py`, `GET /health/live`, root scripts `test`, `lint`, `format`, `test:api`, `test:web` and placeholder node scripts for the rest. Tests: pytest health route, vitest smoke render.
4. WF-004.2 Scaffold, local run tooling: node scripts `setup`, `db:init` (runs `infra/db/bootstrap.sql` as `postgres` via `pgpass.conf`, finds the PostgreSQL 18 `bin`), `doctor` (never prints values), `dev` (API 8100, Vite 5173, `envDir: '../..'`, `uv run --no-sync`), `start`, base `.env.example`, Playwright config with `test:e2e` and `test:e2e:smoke`, README setup in under 10 lines, `.claude/skills/run-hermi-locally/SKILL.md`, and the verified Commands section in `CLAUDE.md`. Ported from the Trip Planner `scripts/setup.mjs` and `setup_db.py`.
5. WF-006 Typed configuration: `apps/api/hermi/config.py` (only reader of env), full `.env.example` from 02 section 7, refusal matrix with one test per rule, `.env.example` vs `config.py` check.
6. WF-007 CI pipeline: rewrite `.github/workflows/ci.yml` (keep the always-running `ci` job and its "Autopilot tests" step), `e2e.yml`, nightly `windows-latest`, `scripts/check-copy.mjs`, stylelint `declaration-strict-value`, `jsx-a11y`, OpenAPI drift, Alembic two-heads check.
7. WF-008 Docker and health: `infra/docker/Dockerfile` (multi-stage, non-root), `infra/docker/compose.yml` (optional), `/health/ready` (database, migrations at head, `ai_provider`), container smoke and Trivy in CI.
8. WF-010 Security scanning: `.github/workflows/security.yml` (pip-audit, npm audit, gitleaks, CodeQL, Trivy, non-blocking audits), `.github/dependabot.yml` grouped weekly.
9. WF-002 Landing page and waitlist (UI): static page in `apps/web/public/`, `POST /v1/waitlist` in `apps/api/hermi/modules/notifications/` (validation, in-memory dedupe, rate limit, Resend audience only when `RESEND_API_KEY` is set, console or file email otherwise), privacy policy page, Playwright submit flow. Kit: 05 6.1, `design/screens/01-welcome.html`.

Tests: `npm run lint`, `npm run test:api`, `npm run test:web`, and `npm run test:e2e:smoke` from WF-004.2 on; the dash grep before every docs commit.

Risks: WF-004 is split because one session would touch many modules and well over 600 lines. Steps 3 and 4 must leave every root script runnable (placeholders exit 0 with a message until their ticket lands) so the `ci` job stays green. No migrations exist yet, so `/health/ready` and the Alembic checks must handle "no revisions" cleanly; Alembic itself arrives in WF-011 (prompt 04), so WF-008 may need a minimal Alembic environment, record that choice in `DECISIONS.md`. Docker is not available locally: the compose and container checks run only in CI. All dependencies (S1 to S3) are Done.

Owner-pending items: WF-001 (trademark opinion, domain purchase, Apple enrollment, App Store name; `HUMAN_TASKS.md` row 23), WF-003 (interviews, price test, signed decision; row 28), WF-002 "page live on the production domain" (domain and Cloudflare Pages account), WF-007 branch protection requiring `ci`, WF-010 secret scanning and push protection (row 3).

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
| 01 | [Repository foundation, CI and landing page](01-repo-foundation.md) | WF-001, WF-003, WF-004, WF-006, WF-007, WF-008, WF-010, WF-002 | In progress (phase1/p01-repo-foundation) |
| 02 | [Port reusable code from the old Trip Planner](02-port-reusable-modules.md) | WF-005 | Not started |
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
