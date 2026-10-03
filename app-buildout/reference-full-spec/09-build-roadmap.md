# 09: Build roadmap

Part of the [Hermi build specification](../README.md). The README's shared decisions, tier codes, credit codes and table names are final; this file sequences the work.

This file has two halves. The first is the milestones: what each stage is for, how long it takes, and how you know it is done. The second is an ordered backlog of 114 tickets (WF-001 to WF-114), each small enough for one Claude Code session. A section at the end explains how to work through it with Claude Code.

Effort assumes one developer with Claude Code working 25 to 35 focused hours a week (part time; halve the calendar if full time). Paths follow the repository layout in [02-architecture.md](02-architecture.md) section 2 (`apps/api`, `apps/worker`, `apps/web`, `apps/ios`, `packages/shared`, `packages/tokens`, `infra/`, `docs/`); if a path here differs from that tree, 02 wins. Spec references use the file numbers in the README table.

## 1. Milestones

| Milestone | Duration | Calendar (part time) | Tickets |
|---|---|---|---|
| M0 validate | 2 to 4 weeks | Before week 1 | WF-001 to WF-003 |
| Phase 0 foundations | 3 to 4 weeks | Weeks 1 to 4 | WF-004 to WF-024 |
| Phase 1 hosted web beta | 6 to 8 weeks | Weeks 5 to 12 | WF-025 to WF-073 |
| Phase 2 iOS TestFlight | 5 to 7 weeks | Weeks 13 to 19 | WF-074 to WF-090 (including Family, WF-077) and WF-114 (Group Trip Pass) |
| Phase 3 public launch | 3 to 4 weeks | Weeks 20 to 23 | WF-091 to WF-100 |
| Phase 4 growth | Ongoing | Week 24 on | WF-101 to WF-113 |

Do not start a phase until the previous exit criteria are met. The biggest schedule risk is Phase 1 (tenancy and entitlements), not the mobile work.

### M0: validate

- **Goal:** learn whether anyone wants this before rewriting anything. No app code changes beyond a landing page.
- **Duration:** 2 to 4 weeks.
- **Exit criteria:** landing page live with waitlist; 10 user interviews done against a "yes" signal written down before the first call; price and paywall copy tested (Trip Pass $9.99, Plus $5.99 a month or $39.99 a year); provider terms questions answered (SerpApi, Geoapify, Travelpayouts). If there is no clear signal, stop and keep the app personal.

### Phase 0: foundations

- **Goal:** make the codebase safe to open up and move AI off the owner's personal subscription. Nothing user-facing changes.
- **Duration:** 3 to 4 weeks.
- **Exit criteria:** agents run on the Claude Messages API with metering (`ai_usage`, `credit_ledger`, ceilings); Docker image builds; CI green on Linux; a merge to `main` deploys to staging in under 10 minutes; one agent run finishes within its $0.80 cap on staging; scheduled agents are off in hosted mode; kill switches work.

### Phase 1: hosted web beta

- **Goal:** a real product on the web that strangers can sign up for, payments off (upgrade screens show "coming with the app"), proving the core loop and unit economics.
- **Duration:** 6 to 8 weeks.
- **Exit criteria:** accounts, sharing, entitlements and ledger working; zero cross-tenant leaks in automated tests; AI cost per active user within the modeled ceilings; admin console has audit, users, kill switches and AI spend; restore-from-backup drill done once; spend alerts fire in a drill; mobile web usable on iPhone Safari; axe clean and the token contrast test green, including `--tp-edge` and `--tp-warning-ink`; the owner's data migrated; 50 to 200 beta users invited and 4-week retention measured and recorded.

### Phase 2: iOS TestFlight

- **Goal:** a native app that passes the "not a website" test, with purchases working in sandbox for every product sold at launch (`plus`, `family`, `trip_pass`, `group_trip_pass`, credit packs; `pro` stays behind `tier_pro`).
- **Duration:** 5 to 7 weeks.
- **Exit criteria:** Capacitor app bundled (no `server.url`), purchases, push, account deletion, offline trip viewing; crash-free sessions at least 99.5 percent over 100 or more sessions; every sandbox purchase scenario passes (purchase, cancel, upgrade Plus to Family, refund, restore on a second device, billing retry, Trip Pass and Group Trip Pass each bound to a trip); polls and manual cost splitting work on every tier and pass that includes them; a trip fully browsable in airplane mode on a real device; self-check against App Review Guidelines 4.2, 4.8, 5.1.1(v), 3.1.2 and 1.2.

### Phase 3: public launch

- **Goal:** approved, live, with support and monitoring ready.
- **Duration:** 3 to 4 weeks, including one or two review cycles of 1 to 4 days.
- **Exit criteria:** App Review passed; support inbox, macros and FAQ live; load test at 10 times expected launch traffic done; runbooks and status page in place; crash-free at least 99.5 percent, API error rate under 1 percent, and no P0 in the first 72 hours after release.

### Phase 4: growth

- **Goal:** widen revenue without widening risk, in this order as the data allows: Stripe group payments, concierge, Pro, Hermi for Advisors, printed trip books, LiteAPI booking, Android and SEO pages. Family and the Group Trip Pass are already on sale from launch (Phase 2 tickets).
- **Duration:** ongoing, each item 1 to 6 weeks.
- **Exit criteria per item:** D30 retention at least 15 percent, free-to-paid conversion 3 to 5 percent, monthly subscriber churn under 8 percent, LTV to CAC above 3 (targets, not gates). Pro launches only when measured agent cost is $0.60 or less per run over 200 runs, or over 15 percent of Plus payers buy agent-run credits. The **kill rule** applies: at month 9 after launch, if under 1 percent of monthly users pay and affiliate income is under $0.20 per monthly user per year, stop investing and keep it as a personal tool. The admin overview tracks both numbers from launch.
- **Scope note:** launch scope follows the README: `free`, `plus`, `family`, `trip_pass`, `group_trip_pass` and credit packs are sold at launch, and `pro` stays behind the `tier_pro` flag until its gate. So the Family plan (WF-077), households (WF-038), polls and manual cost splitting (WF-045, gated by WF-051) and the Group Trip Pass with the room-block request (WF-114) are built before the TestFlight and listing tickets. Phase 4 keeps only Stripe group payments (WF-102, for `group_trip_pass` and `pro`), advisors, print, LiteAPI and Pro.

## 2. Critical path

The single longest chain of dependencies; a slip anywhere on it moves the launch date.

```
WF-004 scaffold -> WF-007 CI -> WF-008 Docker -> WF-011 migrations -> WF-012 identity schema
  -> WF-013 AI schema -> WF-015 metering -> WF-016 ledger -> WF-017 ceilings -> WF-018 queue
  -> WF-019 Claude client -> WF-020 agent loop -> WF-023 breakers            (Phase 0 gate)
  -> WF-028 JWT -> WF-029 data access -> WF-030 RLS -> WF-031 leak tests -> WF-051 entitlements
  -> WF-052 paywall logic -> WF-071 to 073 data migration and beta           (Phase 1 gate)
  -> WF-074 RevenueCat webhook -> WF-075 credit grants -> WF-080 Capacitor shell
  -> WF-082 Sign in with Apple -> WF-083 purchases -> WF-089 TestFlight
  -> WF-090 purchase matrix (also needs WF-077 Family and WF-114 Group Trip Pass, built in parallel after WF-075 and WF-076)
  -> WF-096 listing -> WF-097 review notes -> WF-100 submit and launch       (Phase 3 gate)
```

Launch-scope products (Family, Group Trip Pass, polls and cost splitting) hang off the critical path: WF-038 feeds WF-077, WF-045 and WF-051 feed WF-114, and all of them must finish before WF-090 so the purchase matrix and review screenshots cover every product sold at launch.

Long-lead items that are off the code path but on the calendar path: Apple Developer enrollment (days to weeks; start in Phase 0), Paid Applications Agreement and tax forms, a Mac or Xcode Cloud, Travelpayouts approval, Viator and Stay22 approvals, and App Review itself.

## 3. Parallelizable tracks

| Track | Tickets | Can start | Notes |
|---|---|---|---|
| A Platform and data | WF-004 to 011, 012, 025 to 027 | Day 1 | Blocks everything else at first |
| B AI and metering | WF-013 to 024, 049 to 050 | After WF-011 | The Phase 0 gate |
| C Tenancy and auth | WF-028 to 033 | After WF-012 | Needs WF-014 flags only for rate-limit switches |
| D Product modules | WF-037 to 048 | After WF-029 | Modules are independent; run 2 or 3 sessions at once on separate branches |
| E Frontend platform | WF-034 to 036, 087, 088 | After WF-028 | Can use mocked API until C finishes |
| F Monetization | WF-051, 052, 074 to 078, 114 | After WF-016 | Web beta shows the waitlist paywall only; Family and Group Trip Pass are built here for launch |
| G Affiliate | WF-053 to 055, 099, 101 | After WF-029 | Start the Travelpayouts application in Phase 0 |
| H Admin console | WF-056 to 063, 079, 091 to 095 | After WF-014 and WF-027 | Overview and users can be built against seeded data |
| I Notifications and privacy | WF-064 to 067, 085 to 086 | After WF-028 | Deletion and export are App Review requirements |
| J Observability and ops | WF-068 to 071, 098 | After WF-009 | Restore drill before Phase 1 gate |
| K iOS (needs a Mac) | WF-080 to 084, 087 to 090 | After WF-034 and WF-035 | Only the Mac-bound steps wait on hardware |

Two to three Claude Code sessions can run in parallel when their tickets touch different modules. Never run two tickets in parallel that both add an Alembic migration; they would create two heads (WF-011 makes CI fail on multiple heads).

## 4. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Owner ticket |
|---|---|---|---|---|---|
| 1 | No demand | Medium | High | M0 gate before any rewrite; kill rule at month 9 | WF-003, WF-058 |
| 2 | Cross-tenant data leak | Low | Severe | Data access layer, RLS, automated leak tests, security review before the Phase 1 gate | WF-029 to WF-031 |
| 3 | AI cost overrun or runaway agent | Medium | High | Hard stops, ceilings, reserve then settle, breakers, kill switches, alerts | WF-015 to WF-023, WF-062, WF-063 |
| 4 | SerpApi terms or legal action blocks live fares | Medium | Medium | Provider interface, `serpapi_live_fares` flag, cached Travelpayouts baseline, Skyscanner Partners application | WF-003, WF-040 |
| 5 | App Review rejection (4.2, 3.1.2, 5.1.1(v), 1.2, privacy labels) | Medium | Medium | Native features, offline, Restore, deletion, report and block, tested review notes, TestFlight self-check | WF-081 to WF-090, WF-097 |
| 6 | Entitlement mismatch or double credit grant | Medium | Medium | Idempotent webhooks keyed on transaction id, nightly reconcile, replay tool | WF-074, WF-075, WF-079 |
| 7 | Affiliate disclosure or tracking failure | Low | High | Disclosure component with tests, disclosure audit, no ranking by commission test, no fetching of Airbnb, Vrbo or Booking.com pages | WF-053, WF-054, WF-094 |
| 8 | No Mac available | Certain | Medium | Buy a Mac mini or use Xcode Cloud in Phase 0 planning | WF-080 |
| 9 | WebView jank on maps and calendar | Medium | Medium | Simplify the phone calendar, cluster markers, profile early | WF-036, WF-042, WF-043 |
| 10 | Migration error on the owner's data | Low | Medium | Dry run, row counts, idempotent importer, backup before import | WF-072 |
| 11 | Solo bus factor and burnout | High | High | Strict gates; cut Android, widgets and Phase 4 before cutting quality; runbooks | WF-098 |
| 12 | Policy churn (external links, AI disclosure, age assurance) | High | Medium | In-app purchase only at launch, re-read guidelines before each submission | WF-097, WF-100 |
| 13 | Provider or Supabase Auth outage | Medium | Medium | Stale-data banners, queue and retry, breaker half-open probes, runbooks | WF-023, WF-098 |
| 14 | The owner's current Trip Planner breaks while Hermi is built | Low | Low | Hermi is a new repository with hosted-only code (02 section 1.1); the existing app keeps running from its own repository until the one-off data import (WF-072, 03 section 12) | WF-004 |

## 5. Backlog

Conventions for every ticket:

- **Heading:** `WF-NNN title [phase, size, needs ...]`. Sizes: S (about 2 hours), M (half a day), L (a day; never larger, split instead).
- **Definition of done (DoD)**, applied to every ticket and written once here. Each ticket's Done line adds only what is extra.
  1. The change is on a branch, reviewed against the ticket's acceptance list, and merged to `main` through a pull request; one commit per ticket, message `WF-NNN title`.
  2. `npm run lint` and `npm test` pass locally and in CI. The tests named in the ticket exist and fail without the change.
  3. If any route or schema changed: `npm run gen:api` was run and the regenerated `apps/web/src/lib/api/schema.d.ts` is committed.
  4. If any model or migration changed: the migration follows `.claude/rules/database-migrations.md` (expand and contract, one head, tested from empty and from the previous revision).
  5. New environment variables are documented in `.env.example`; no secrets in the repo.
  6. UI copy follows the copy rules (sentence case, plain verbs, no em dashes) and the Hermi design tokens.
  7. The work respects the non-negotiable rules in the README (no ranking by commission, no fetching Airbnb, Vrbo or Booking.com pages, sources on every AI fact).

### E0 M0 validate

#### WF-001 Name, domain and email [M0, S, needs none]
- Description: confirm the name Hermi: run a trademark search in classes 9, 39 and 42 and get an attorney's opinion on the Hermio and Hermès risks listed in [../brand/BRAND.md](../brand/BRAND.md); reserve "Hermi: Group Trip Planner" in App Store Connect (the bare name is taken); buy `hermi.world` (and `heyhermi.com` as a redirect); set up `support@`, `no-reply@` and the Resend sending domain with SPF, DKIM and DMARC. Spec: [02-architecture.md](02-architecture.md).
- Accept: domain resolves through Cloudflare; a test email from `no-reply@hermi.world` passes SPF, DKIM and DMARC; the name decision, the trademark search result, the attorney's opinion and the reserved App Store name are saved in `docs/adr/0001-name.md`.
- Touches: `docs/adr/`, `infra/cloudflare/dns.md` (record list).
- Tests: a script `infra/scripts/check-mail-auth` that queries the DNS records and exits non-zero if any is missing.
- Done: DoD plus the decision recorded and the script run against the live domain.

#### WF-002 Landing page and waitlist [M0, M, needs WF-001]
- Description: a static page on Cloudflare Pages with the positioning line "Plan together. Know the fare.", the logo, a waitlist form (email plus "who do you plan trips with"), and a privacy note. Waitlist entries land in a table or Resend audience.
- Accept: form submit stores one entry per email (duplicates ignored); confirmation email sent; page scores 90 or more on Lighthouse mobile; no ad or tracking SDKs; privacy text links to a policy page.
- Touches: `apps/web/landing/` (static page deployed to Cloudflare Pages), a small `POST /v1/waitlist` route in `apps/api/hermi/modules/notifications/`.
- Tests: route accepts valid email, rejects invalid, dedupes, rate limits; Playwright submit flow.
- Done: DoD plus page live on the production domain.

#### WF-003 Interview kit, price test and terms checklist [M0, S, needs WF-002]
- Description: write the interview script, the written "yes" signal, the paywall and price test cards (Trip Pass $9.99; Plus $5.99 a month or $39.99 a year), and the provider terms checklist (SerpApi terms and the Google lawsuit, Geoapify caching terms, Travelpayouts rates and app eligibility).
- Accept: 10 interviews logged with outcome; each terms question has an answer or an owner and a date; a go or no-go decision record exists.
- Touches: `docs/validation/`.
- Tests: none (documentation); checklist reviewed by the owner.
- Done: DoD plus a signed decision record. A "no-go" stops the backlog here.

### E1 Repository, CI, Docker and environments

#### WF-004 Scaffold the repository [P0, M, needs WF-003]
- Description: create the Hermi monorepo with the tree in [02-architecture.md](02-architecture.md) section 2: `apps/api` (Python 3.13, uv, FastAPI), `apps/worker`, `apps/web` (Vite, React 19, TanStack Query, Tailwind 4), `packages/shared`, `packages/tokens`, `packages/eslint-config`, `infra/`, `.github/` (workflows and Dependabot), `docs/` (`apps/ios` arrives in WF-080), a uv workspace and npm workspaces, root `package.json` scripts (`setup`, `start`, `dev`, `test`, `lint`, `format`, `gen:api`), `.env.example`, a project `CLAUDE.md` and `.claude/rules/` stubs (database migrations, agent routines, frontend).
- Accept: `npm run setup && npm test && npm run lint` pass on a clean clone on Linux and Windows; `GET /health/live` returns 200.
- Touches: repo root (`package.json`, `pyproject.toml`), `apps/api/pyproject.toml`, `apps/web/package.json`, `packages/`, `infra/`, `.github/`, `.claude/`.
- Tests: one pytest for the health route, one vitest smoke render.
- Done: DoD plus the README explains setup in under 10 lines.

#### WF-005 Port reusable modules [P0, L, needs WF-004]
- Description: copy and adapt from the Trip Planner repo the modules that carry over: flight route and fare logic, itinerary and lodging logic, presentation mode, Hermi design tokens (into `packages/tokens`: the plumbing and neutral names are ported, and every value plus the new tokens come from [05-ui-ux-spec.md](05-ui-ux-spec.md) section 2), Travelpayouts, Geoapify, Wikipedia and Frankfurter providers, evidence rules in `services/agent_ingest.py`, and agent prompts. Leave behind passcode auth, the Claude CLI runner, the MCP bridge, APScheduler, Windows scripts and Tailscale sharing. Follow the module map in [02-architecture.md](02-architecture.md).
- Accept: ported modules import cleanly and keep their original unit tests passing; a `docs/porting-map.md` lists each source file and its new home; no Windows-only code in `apps/` or `packages/`.
- Touches: `apps/api/hermi/providers/`, `apps/api/hermi/modules/*/service.py` (ported logic), `packages/tokens/`, `apps/web/src/lib/`.
- Tests: the original tests for each ported module, adapted; a test that greps for forbidden imports (`subprocess` Claude CLI, `apscheduler`).
- Done: DoD plus the porting map reviewed.

#### WF-006 Typed configuration and environments [P0, M, needs WF-004]
- Description: a settings module (`config.py`, the only place environment variables are read) with `ENVIRONMENT` (`local`, `ci`, `preview`, `staging`, `production`) as in 02 section 7. The app refuses to start without the required secrets for its environment, keeps scheduled agents off until the `scheduled_agent_routines` flag is on, and tests refuse to run when `ENVIRONMENT=production`. There is no personal or single-household mode: the Windows-only and passcode paths of the old Trip Planner are not carried over (02 section 1.1).
- Accept: settings load from env with typed validation; missing required secrets fail fast with a clear message listing names only; `.env.example` lists every variable.
- Touches: `apps/api/hermi/config.py`, `.env.example`, `apps/api/tests/test_config.py`.
- Tests: settings matrix (each environment), refusal when production, required-secret errors.
- Done: DoD plus `.env.example` checked against `config.py` in CI.

#### WF-007 CI pipeline [P0, M, needs WF-004]
- Description: GitHub Actions `ci.yml` in `.github/workflows/` (the only place GitHub runs workflows from; the 02 repository tree puts them there): lint, tests with a `postgres:18` service, OpenAPI drift check, migration test from empty and from the previous release, image build; `e2e.yml` for the Playwright smoke test.
- Accept: a PR with a failing test, lint error, API drift or two Alembic heads turns CI red; a clean PR is green in under 10 minutes.
- Touches: `.github/workflows/ci.yml`, `.github/workflows/e2e.yml`.
- Tests: a deliberately broken branch for each check (recorded in the PR).
- Done: DoD plus branch protection requires CI on `main`.

#### WF-008 Docker image, compose and health endpoints [P0, M, needs WF-007]
- Description: multi-stage Dockerfile (`node:22` builds the web, `python:3.13-slim` with `uv sync --frozen --no-dev`, non-root), commands `api`, `worker`, `scheduler`, `migrate`; `infra/docker/compose.yml` (Postgres 18, Mailpit, MinIO); `/health/live` and `/health/ready` (database reachable, migrations at head).
- Accept: `docker compose up` serves the API; image runs as non-root; ready fails when migrations are behind; image scanned with Trivy in CI.
- Touches: `infra/docker/Dockerfile`, `infra/docker/compose.yml`, `apps/api/hermi/main.py` (health routes).
- Tests: readiness test with a stale migration; container smoke test in CI.
- Done: DoD plus image size noted in the PR.

#### WF-009 Render and Cloudflare environments and deploy workflows [P0, L, needs WF-008]
- Description: `infra/render/render.yaml` for API, worker and Postgres 18 (PITR) for staging and production; pre-deploy migration command with an advisory lock; Cloudflare DNS, TLS and WAF, Pages for the web build; `deploy-staging.yml` (on merge) and `deploy-prod.yml` (manual approval, promote the same image digest, rollback on failed health check). Spec: [02-architecture.md](02-architecture.md).
- Accept: a merge to `main` reaches staging with migrations applied in under 10 minutes; production deploy needs approval; secrets live only in platform env groups.
- Touches: `infra/render/render.yaml`, `.github/workflows/deploy-*.yml`, `infra/cloudflare/`.
- Tests: post-deploy smoke test script; a forced failing health check triggers rollback (recorded).
- Done: DoD plus separate Anthropic workspace keys for staging and production.

#### WF-010 Security scanning workflows [P0, S, needs WF-007]
- Description: `security.yml` (pip-audit, npm audit, gitleaks, CodeQL, Trivy), Dependabot grouped weekly, GitHub secret scanning and push protection.
- Accept: a planted fake secret is caught by gitleaks in a test branch; workflows run weekly and on PR.
- Touches: `.github/workflows/security.yml`, `.github/dependabot.yml`.
- Tests: the planted-secret branch (not merged).
- Done: DoD plus findings triaged.

### E2 Database and migrations

#### WF-011 Migration framework and database roles [P0, M, needs WF-008]
- Description: Alembic on Postgres 18 with `lock_timeout` and `statement_timeout`, an advisory lock around `upgrade head`, a check for multiple heads, UUIDv7 helper, and the roles from [03-database-schema.md](03-database-schema.md) section 6.1: `hermi_owner` (owns objects, runs migrations), `hermi_app` (the API, subject to RLS), `hermi_worker` (jobs, bypasses RLS) and `hermi_admin` for the admin API (see [08-admin-control-center.md](08-admin-control-center.md)). Write the expand and contract policy into `.claude/rules/database-migrations.md`.
- Accept: migrations run from empty and from the previous revision; two heads fail CI; `hermi_app` cannot run DDL; the rules file documents the policy.
- Touches: `apps/api/hermi/migrations/`, `apps/api/hermi/db.py`, `.claude/rules/database-migrations.md`.
- Tests: migration-from-empty test, head-count test, role privilege tests.
- Done: DoD plus the rules file updated.

#### WF-012 Identity and trips schema [P0, M, needs WF-011]
- Description: migration for `users`, `auth_identities`, `devices`, `households`, `household_members`, `trips`, `trip_members`, `trip_invites`, `trip_share_links`, `trip_destinations`, `people` (with `owner_user_id`, `linked_user_id`), `trip_people`, `activity_log`, `support_tickets`, `idempotency_keys` (the 24 hour replay store for `Idempotency-Key`). `trips` carries `version`, `editors_can_invite` and `calendar_token_hash`; `users` carries the `suspended` status and the column-level update grant of 03 section 6.1. UUIDv7 public ids, `timestamptz`, money as integer minor units. DDL in [03-database-schema.md](03-database-schema.md).
- Accept: migration applies cleanly; constraints and indexes match 03; models and Pydantic schemas exist.
- Touches: `apps/api/hermi/migrations/versions/`, `apps/api/hermi/modules/{auth,trips,collaboration,billing}/models.py`.
- Tests: constraint tests (unique member per trip, valid roles), schema-vs-DDL comparison test.
- Done: DoD plus seed data for two test users and a shared trip.

#### WF-013 AI, credit and run schema [P0, M, needs WF-012]
- Description: migration for `routines` (with `next_run_at`), `runs`, `run_events`, `ai_usage`, `credit_ledger`, `credit_grants`, `credit_debts`, `credit_action_prices`, `provider_calls`, `provider_call_rollups`, `shared_research_cache`; the unique partial index `uq_runs_one_active_agent` behind the one-agent-run-per-account admission check; `idempotency_key` uniques; the credit functions of 03 section 5.13 (`reserve_credits`, `settle_credits`, `record_credit_debt`, `settle_credit_debt`, `ensure_free_monthly_grant`, `ensure_taster_grant`).
- Accept: migration applies; a second concurrent agent run for one account is refused at admission by `uq_runs_one_active_agent` (409 `run_already_active`); ledger idempotency key unique; `reserve_credits` refuses an account with a credit debt.
- Touches: `apps/api/hermi/migrations/versions/`, `apps/api/hermi/modules/ai/models.py`, `modules/credits/models.py`.
- Tests: concurrency test for the one-run-per-account admission check; duplicate idempotency key rejected.
- Done: DoD plus costs stored as micro-dollars.

#### WF-014 Feature flags and kill switches [P0, M, needs WF-012]
- Description: migration for `feature_flags` (`key`, `kind`, `enabled`, `rollout_pct`, `rules`, `variants`) and `kill_switches` (`key`, `engaged`, `reason`, `engaged_by`, `engaged_at`, `expires_at`, `expiry_notified_at`, `auto_rule`; admin-set switches must carry an expiry, `user:<id>` keys are per-account holds); a runtime that evaluates flags (cached 5 seconds per process, invalidated by `NOTIFY`) and **fails closed** for paid calls if the tables cannot be read. Seed keys are in [03-database-schema.md](03-database-schema.md) section 11.5; the console that edits them is in [08-admin-control-center.md](08-admin-control-center.md).
- Accept: flipping `ai.all` blocks AI calls within 5 seconds; engaging or clearing a switch writes `audit_log`; unreadable table blocks paid calls.
- Touches: `apps/api/hermi/modules/admin/flags.py`, `apps/api/hermi/migrations/versions/`, `packages/shared/src/flags.ts`.
- Tests: evaluation rules (percent, tier, platform), fail-closed test, audit test.
- Done: DoD plus a practice drill written in `docs/runbooks/kill-switches.md`.

### E3 AI metering and agents (Phase 0 gate)

#### WF-015 AI metering and price table [P0, M, needs WF-013]
- Description: a versioned price constant in `ai/pricing.py` (06 section 6.1; not a database table) holding the model prices (Claude Haiku 4.5 `claude-haiku-4-5`, Claude Sonnet 5.5 `claude-sonnet-5-5`, web search per use) and a metering wrapper that converts `response.usage` (input, output, cache read and write, web searches) into micro-dollars and writes an `ai_usage` row in the same transaction as the run event. Spec: [06-ai-agents-spec.md](06-ai-agents-spec.md).
- Accept: cost matches a hand calculation for 5 sample responses; Batch calls are halved on tokens; `provider_calls` records SerpApi and Geoapify spend with account and trip.
- Touches: `apps/api/hermi/modules/ai/metering.py`, `modules/ai/pricing.py`.
- Tests: table-driven cost tests, rollback test (no usage row if the event insert fails).
- Done: DoD plus price table never edited in place.

#### WF-016 Credit ledger service [P0, L, needs WF-013]
- Description: reserve, settle, refund, expire and adjust operations on `credit_ledger` with `credit_grants`; spend order (allowance, pass credits, purchased credits oldest first); `SELECT ... FOR UPDATE` on the balance; lazy monthly grants (Free 12, Plus 60, Family 150, Pro 240); purchased credits expire after 12 months. Action prices: `explain` 1, `live_search` 1, `draft_day` 1, `draft_trip` 4, `research` 8 (1 from cache), `agent_run` 40 (8 from cache).
- Accept: parallel reservations never overspend; a failed or empty action is refunded; a stopped agent run is billed pro rata with an 8 credit minimum; negative balance after a refund blocks new actions.
- Touches: `apps/api/hermi/modules/credits/`, `packages/shared/src/credits.ts`.
- Tests: concurrency test with 20 parallel reservations; every ledger `kind`; expiry; spend order.
- Done: DoD plus balance shown from the ledger, never cached without a version.

#### WF-017 Spend ceilings and budget service [P0, L, needs WF-016]
- Description: per-account monthly and daily provider-spend ceilings (Free $0.25 and $0.05, Plus $2.25 and $0.40, Family $3.40 pooled, Trip Pass $1.80, Group Trip Pass $3.60, Pro $5.50 and $1.25), reserve-then-settle in one transaction with the job enqueue, the agent-run admission rule (month headroom of $0.80 even above the daily budget), and cached data still working when a ceiling is hit. Generalizes the old single SerpApi cap.
- Accept: a ceiling stops paid work but never cached reads; a run is admitted with $0.80 monthly headroom even if the day is exhausted, and then blocks other paid actions that day; ledger unreadable means refuse.
- Touches: `apps/api/hermi/modules/credits/budget.py`.
- Tests: boundary tests per tier, admission rule, fail-closed test.
- Done: DoD plus ceilings read from settings (changeable by [08](08-admin-control-center.md)).

#### WF-018 Job queue and worker lanes [P0, L, needs WF-013]
- Description: Procrastinate on Postgres with lanes `api`, `ai`, `notify`; per-account concurrency caps (Free 2, Plus 4, Pro 8), fair claim by least recently served account, retries with backoff and jitter, dead-letter state, stale-heartbeat reaper, graceful SIGTERM; `runs` remains the user-visible record.
- Accept: a job enqueued in the same transaction as its budget reservation; 2 workers never run a job twice; a killed worker's job is requeued; a busy account cannot starve others.
- Touches: `apps/api/hermi/jobs.py`, `apps/worker/hermi_worker/app.py`, `apps/worker/hermi_worker/jobs/`.
- Tests: two-worker test, reaper test, fairness test, retry classification test.
- Done: DoD plus queue depth and oldest job age exposed to health endpoints.

#### WF-019 Claude client and single-call features [P0, M, needs WF-015, WF-016]
- Description: a Messages API client with prompt caching layout (tools, system, task, volatile tail), model allowlist, `max_tokens` per feature, and the single-call actions `explain` (Haiku), `packing_list` and `booking_import` (Haiku, 1 credit each in the `explain` price class, run kinds `packing_list` and `booking_import`, endpoints `POST /trips/{id}/ai/packing-list` and `/ai/booking-import`, personal data redacted before the call), `draft_day`, `draft_trip` (Sonnet) with schema-validated output and source links.
- Accept: each action reserves, calls, meters, settles; outputs fail validation closed; AI output is labeled as a suggestion; the kill switch blocks calls.
- Touches: `apps/api/hermi/modules/ai/client.py`, `modules/ai/features/`.
- Tests: recorded-response tests with a fake client; hard-stop tests ($0.01, $0.03, $0.10); kill switch tests (`ai.all`, `ai.explain`, `ai.packing`, `ai.import`, `ai.draft`); booking import sends placeholders, never names or references.
- Done: DoD plus prompt cache read ratio logged.

#### WF-020 Agent loop [P0, L, needs WF-019, WF-017]
- Description: the multi-turn agent on the Messages API with server web search and fetch tools and in-process client tools `submit_flight_quotes`, `add_note`, `finish_run`. Caps: 20 turns, 10 searches, 10 fetches, `medium` effort, 8 minutes, $0.80 hard stop, one run at a time. Keep evidence rules (fares must be seen on a page during the run) and blocked domains Airbnb, Vrbo and Booking.com enforced in the fetch tool. Port the prompts from the old `agent_ingest.py` rules.
- Accept: a run stops at each cap and keeps saved work, marked `partial`; a fare without page evidence is rejected; blocked domains never fetched; prompt-injection test pages cannot write outside the account.
- Touches: `apps/worker/hermi_worker/agents/` (`AgentLoop`, tools, prompts), `apps/api/hermi/modules/ai/ingest.py`, `modules/ai/context.py`, `apps/worker/hermi_worker/jobs/run_agent.py`.
- Tests: fake-tool loop tests for every cap; evidence tests; blocked-domain tests; injection fixtures.
- Done: DoD plus a manual staging run under $0.80 recorded.

#### WF-021 Research action and shared cache [P0, M, needs WF-020]
- Description: the `research` action (5 searches, 8 fetches, $0.16) with `shared_research_cache` keyed by destination, rounded window, topic and prompt version; single-flight advisory lock; hits cost 1 credit, cold requests 8; poisoning defenses (validators, instruction-like text classifier, report flag sets `flagged`); jobs with free-text instructions bypass the cache.
- Accept: 50 concurrent requests for one key cause one model run; no user text enters a shared prompt; flagged entries are not served.
- Touches: `apps/api/hermi/modules/ai/research.py`, `modules/ai/cache.py`.
- Tests: single-flight test, bypass test, flagged entry test, credit pricing test.
- Done: DoD plus hit rate computed from `ai_usage.cache_hit`.

#### WF-022 Scheduler [P0, M, needs WF-018]
- Description: one leader (advisory lock) scans `routines.next_run_at` every 30 to 60 seconds with `FOR UPDATE SKIP LOCKED`, enqueues due jobs with a stable per-routine jitter, advances the slot, and only schedules API price checks and batch scans; scheduled agents are off until Pro (`scheduled_agent_routines` flag).
- Accept: two schedulers never double-fire; an outage fires one check, not twelve; no agent job is ever scheduled while the flag is off; live routes are checked daily within 120 days of departure within tier limits.
- Touches: `apps/worker/hermi_worker/scheduler.py`, `apps/worker/hermi_worker/jobs/scan_due_routines.py`.
- Tests: two-leader test, jitter stability test, misfire test, flag test.
- Done: DoD plus scheduler heartbeat exposed.

#### WF-023 Global breakers and usage reconciliation [P0, M, needs WF-014, WF-017]
- Description: automatic breakers (80 percent of daily Anthropic budget turns off Free AI, 95 percent stops all but paid, 90 percent of SerpApi quota narrows live checks, provider error-rate trips), a daily job that pulls the Anthropic usage and cost admin API and compares it with `ai_usage` (alert above 3 percent), and the alert rules in [08](08-admin-control-center.md) section 10.
- Accept: a simulated spend surge trips the right breaker and pages; reconciliation gap alert fires in a drill; breakers are logged to `audit_log` as `system` once that table exists (WF-027).
- Touches: `apps/api/hermi/modules/ai/breakers.py`, `apps/worker/hermi_worker/jobs/reconcile_anthropic_usage.py`.
- Tests: threshold tests, half-open probe test, reconciliation diff test.
- Done: DoD plus the Phase 0 gate checklist run and recorded.

#### WF-024 Evals and run-cost measurement [P0, M, needs WF-020]
- Description: an eval harness for agent and research quality (source present, fares verified, refusals, injection resistance) and a script that reports real cost per run over a window (needed for the Pro gate of 200 runs at $0.60 or less).
- Accept: `npm run evals` runs against fixtures with a fake client and optionally live on a low-limit key; cost report prints mean, p95 and count of runs.
- Touches: `apps/worker/tests/evals/`, `infra/scripts/run_cost_report.py`.
- Tests: the harness has its own self-test with known outputs.
- Done: DoD plus eval results saved in `docs/evals/`.

### E4 Schema completion

#### WF-025 Planning schema [P1, M, needs WF-012]
- Description: migration for `flight_routes`, `fare_observations`, `trip_fare_links`, `chosen_flights`, `price_alerts`, `itinerary_days`, `itinerary_items`, `places_cache`, `saved_places`, `lodging_options`, `lodging_votes`, `polls`, `poll_votes`, `expenses`, `expense_shares`, `payment_collections` (used from Phase 4), `settlements`, `checklist_items`, `notes`, `route_price_insights`. Rows that two people edit carry `version` (03 convention 11).
- Accept: migration applies; every trip-scoped table has `trip_id` for RLS; indexes on common lookups.
- Touches: `apps/api/hermi/migrations/versions/`, `apps/api/hermi/modules/{flights,itinerary,places,lodging,trips,collaboration,groups}/models.py`.
- Tests: schema-vs-DDL test; foreign key and cascade tests.
- Done: DoD.

#### WF-026 Billing and revenue schema [P1, M, needs WF-012]
- Description: migration for `plans`, `store_products`, `subscriptions`, `entitlements`, `trip_passes`, `store_transactions`, `webhook_events`, `affiliate_programs`, `affiliate_link_templates`, `link_clicks`, `affiliate_conversions` (unique on program and network transaction id), `affiliate_payouts`, `concierge_requests`, `room_block_requests`, `partner_guides`, `print_orders`, `advisor_orgs`, `advisor_seats`, `advisor_clients`.
- Accept: migration applies; uniqueness on store transaction id and webhook event id; advisor tables exist but are unused.
- Touches: `apps/api/hermi/migrations/versions/`, `apps/api/hermi/modules/{billing,affiliate,concierge,advisors}/models.py`.
- Tests: uniqueness and idempotency constraint tests.
- Done: DoD.

#### WF-027 Operations schema and seed data [P1, M, needs WF-012]
- Description: migration for `admin_users`, `audit_log` (append only, update and delete rejected by trigger; `retention_class` of 03 section 8), `content_reports`, `support_tickets`, `consents`, `data_exports`, `deletion_requests`, `rate_limit_counters`, `airports`, `fx_rates`; seed airports and the default plans, store products, credit prices, flags and kill switches (03 section 11). Product analytics stay in PostHog, so there is no `analytics_events` table.
- Accept: `audit_log` rejects `UPDATE` and `DELETE`; seeds are idempotent.
- Touches: `apps/api/hermi/migrations/versions/`, `apps/api/hermi/modules/{admin,auth,flights}/models.py`, `apps/api/hermi/seed/`.
- Tests: trigger test, seed idempotency test.
- Done: DoD.

### E5 Auth, tenancy and security

#### WF-028 JWT verification and user provisioning [P1, M, needs WF-012]
- Description: verify Supabase JWTs (signature by JWKS with `kid`, issuer, audience, expiry), map `sub` to `users` and `auth_identities`, create the user on first sign-in, and retire the passcode path in hosted mode. Spec: [04-api-spec.md](04-api-spec.md).
- Accept: expired, wrong-audience and tampered tokens get 401; first request creates exactly one user under concurrency; Apple "Hide My Email" addresses are accepted.
- Touches: `apps/api/hermi/security/jwt.py`, `apps/api/hermi/modules/auth/`, `apps/api/hermi/deps.py`.
- Tests: token matrix with a local JWKS, concurrent first-login test.
- Done: DoD plus `SUPABASE_URL` documented.

#### WF-029 Tenant-scoped data access layer [P1, L, needs WF-028, WF-025]
- Description: one data-access layer every route uses: `require_trip_access(user, trip_id, min_role)` from `trip_members`, owner and household checks, and query helpers that always filter by tenant. No route queries trip tables directly.
- Accept: all existing routes use the layer; a lint rule or test fails if a route imports a trip model directly; roles `owner`, `editor`, `viewer` enforced.
- Touches: `apps/api/hermi/deps.py` (`require_trip`), `apps/api/hermi/db.py`, every module's `repo.py` and `router.py`.
- Tests: permission matrix tests per role and endpoint.
- Done: DoD.

#### WF-030 Row-level security [P1, M, needs WF-029]
- Description: Postgres RLS as a second lock: policies on trip-scoped tables keyed to a session variable set per request (`app.user_id`), the `hermi_app` role subject to RLS, `hermi_admin` with explicit admin policies.
- Accept: a query with no session variable returns zero rows; a forced bug (app check removed) still cannot read another tenant's data.
- Touches: `apps/api/hermi/migrations/versions/`, `apps/api/hermi/db.py` (set variable per transaction).
- Tests: policy tests that bypass the app layer and query as `hermi_app`.
- Done: DoD plus policy list documented.

#### WF-031 Cross-tenant leak tests [P1, M, needs WF-030]
- Description: an automated suite that creates two accounts and tries to read, write and delete the other's trip, run, place, expense, credit balance, webhook and export through every route (generated from the OpenAPI schema).
- Accept: every route returns 403 or 404 for the wrong tenant; the suite runs in CI and fails on any new unprotected route.
- Touches: `apps/api/tests/tenancy/`.
- Tests: the suite itself, plus a mutation check (remove one guard and see it fail).
- Done: DoD plus recorded as the Phase 1 gate evidence.

#### WF-032 Invites, roles and share links [P1, M, needs WF-029]
- Description: invite by link (`trip_invites`), accept, roles, leave, transfer ownership, and read-only `trip_share_links` with revoke; invitees join free and get the trip's capabilities on that trip.
- Accept: expired and used invites fail; owner cannot be removed without transfer; revoked link stops working immediately; Free collaborators limit follows the entitlement resolver once WF-051 lands.
- Touches: `apps/api/hermi/modules/collaboration/`, `apps/web/src/routes/invite/`.
- Tests: invite lifecycle tests, role change tests, link revoke test.
- Done: DoD.

#### WF-033 Rate limits and abuse controls [P1, M, needs WF-028, WF-014]
- Description: a Postgres token bucket per account and route class (AI endpoints 10 a minute, places search 30, outbound 60 an hour), Cloudflare rules on auth and public routes, signup limits (5 accounts per IP per day), disposable-email blocking, `Retry-After` on 429.
- Accept: limits enforced per route class; limits configurable by settings; 429 bodies use the shared error format.
- Touches: `apps/api/hermi/security/rate_limit.py`, `infra/cloudflare/rules.md`.
- Tests: bucket tests with a fake clock, signup velocity test.
- Done: DoD.

### E6 Frontend platform

#### WF-034 Web API client, environment config and bearer auth [P1, M, needs WF-028]
- Description: `client.ts` with `VITE_API_BASE_URL`, `Authorization` middleware, one refresh attempt on 401, CORS origins for web, staging and Capacitor, and public keys (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_REVENUECAT_KEY_IOS`, `VITE_SENTRY_DSN`, `VITE_POSTHOG_KEY`) documented.
- Accept: the client works against staging; 401 triggers refresh then sign-out; no cookies used for hosted mode.
- Touches: `apps/web/src/lib/api/client.ts`, `apps/web/src/lib/env.ts`, `apps/api/hermi/main.py` (CORS).
- Tests: vitest client tests with a mock server; CORS preflight test.
- Done: DoD.

#### WF-035 Sign-in and onboarding screens [P1, M, needs WF-034]
- Description: Sign in with Apple, Google and email code screens; three-screen intro; "Create your first trip" wizard (destination, dates, who is going); a sample trip to explore. Spec: [05-ui-ux-spec.md](05-ui-ux-spec.md).
- Accept: new user reaches a created trip in under 2 minutes; sign-out clears state; copy follows the rules.
- Touches: `apps/web/src/routes/auth/`, `apps/web/src/routes/onboarding/`.
- Tests: component tests, Playwright sign-in with a test identity.
- Done: DoD.

#### WF-036 Responsive layout, empty and error states [P1, L, needs WF-034]
- Description: bottom tab bar under 768 px (Trips, Itinerary, Flights, Lodging, More), safe areas, 44 pt targets, 16 px inputs, bottom sheets for dialogs, empty states with one action, error states (offline, 401, out of credits, 429, maintenance, forced update).
- Accept: every main route works at 390 px wide; no horizontal scroll; Playwright mobile project (iPhone 15 profile) passes.
- Touches: `apps/web/src/app/` (layout), `apps/web/src/routes/errors.tsx`, `apps/web/playwright.config.ts`.
- Tests: mobile viewport smoke test, axe checks in light and dark, and the contrast unit test over the token pairs in [05-ui-ux-spec.md](05-ui-ux-spec.md) section 2.3, including the added `--tp-edge` (control borders) and `--tp-warning-ink` (small warning text).
- Done: DoD.

### E7 Product modules

#### WF-037 Trips module and limits [P1, M, needs WF-029]
- Description: trips CRUD, archive, active-trip limits (Free 2; Plus fair use 25), trip switcher.
- Accept: creating a third active trip on Free returns an entitlement error with the paywall code; archived trips do not count.
- Touches: `apps/api/hermi/modules/trips/`, `apps/web/src/routes/trips/`.
- Tests: CRUD, limit, archive tests; tenancy cases.
- Done: DoD.

#### WF-038 People, households and Family members [P1, M, needs WF-029]
- Description: `people` with `owner_user_id` and `linked_user_id`, households and household members, invite to household (used by Family in WF-077, which is built before launch).
- Accept: a person can be linked to a user; household membership limited to 6; removal handled.
- Touches: `apps/api/hermi/modules/trips/` (people), `apps/api/hermi/modules/billing/` (households).
- Tests: link, unlink, limit tests.
- Done: DoD.

#### WF-039 Cached fares module [P1, M, needs WF-029, WF-005]
- Description: flight routes and Travelpayouts cached fares as the free baseline, fare observations and links to trips, chosen flight.
- Accept: Free gets 1 cached-fare route per trip; cached reads never spend credits; observations dedupe.
- Touches: `apps/api/hermi/modules/flights/`, `apps/api/hermi/providers/travelpayouts.py`.
- Tests: provider mocked tests, limit tests, dedupe tests.
- Done: DoD.

#### WF-040 Live flight provider and search cache [P1, L, needs WF-039, WF-017, WF-014]
- Description: a provider interface with SerpApi behind the `serpapi_live_fares` flag, a canonical search key and shared `provider_calls` result cache (6 hours for fares), single-flight, per-account ceiling checks, `live_search` costs 1 credit, a cached result under 6 hours old is free and says so.
- Accept: 10 users searching one route cause one provider call; flag off hides live search; provider kill switch works; no Airbnb, Vrbo or Booking.com fetches.
- Touches: `apps/api/hermi/providers/serpapi.py`, `apps/api/hermi/modules/flights/` (search cache).
- Tests: dedupe test, flag test, ceiling test, provider error test.
- Done: DoD.

#### WF-041 Price alerts [P1, M, needs WF-039]
- Description: `price_alerts` on cached fares (1 on Free, more with live routes), scheduler check, drop detection, notification request to the notify lane.
- Accept: alert triggers once per drop; duplicate notifications blocked by unique key; limit per tier enforced.
- Touches: `apps/api/hermi/modules/flights/`, `apps/worker/hermi_worker/jobs/evaluate_price_alerts.py`, `apps/web/src/routes/flights/`.
- Tests: threshold tests, idempotent notification test.
- Done: DoD.

#### WF-042 Itinerary and calendar [P1, L, needs WF-029]
- Description: itinerary days and items, calendar view with a phone-friendly list mode and a "Move to..." sheet, conflict hints, ICS export.
- Accept: day reorder works on web and phone; ICS file imports into Apple Calendar; edits by viewers rejected.
- Touches: `apps/api/hermi/modules/itinerary/`, `apps/web/src/routes/itinerary/`.
- Tests: CRUD and role tests, ICS golden file, component tests.
- Done: DoD.

#### WF-043 Places and map [P1, M, needs WF-029]
- Description: Geoapify search with `places_cache`, saved places, MapLibre map with clustering, "Open in Apple Maps" handoff, attributions (OpenStreetMap, Wikimedia).
- Accept: repeated searches hit the cache; places search rate limited at 30 a minute; map remains smooth with 200 markers.
- Touches: `apps/api/hermi/modules/places/`, `apps/web/src/routes/places/`.
- Tests: cache tests, rate limit test, marker clustering test.
- Done: DoD.

#### WF-044 Lodging and votes [P1, M, needs WF-029]
- Description: lodging options, pasted links, votes. Pasted links stay exactly as pasted; the server never fetches Airbnb, Vrbo or Booking.com pages; a separate labeled "Book via partner" button is built from the URL text only.
- Accept: no outbound request to those domains in tests (network blocked in test); votes counted once per member; sort order is stated and never by commission.
- Touches: `apps/api/hermi/modules/lodging/`, `apps/web/src/routes/lodging/`.
- Tests: network-blocked test, vote tests, link preservation test.
- Done: DoD.

#### WF-045 Polls and expenses [P1, M, needs WF-029]
- Description: polls and votes; expenses, shares and balances (who owes whom) and manual "mark as paid" settlements as bookkeeping only; included in `plus`, `family`, `pro`, `trip_pass` and `group_trip_pass` and available to Free users on trips that have them (the gate is the resolver in WF-051); real payment collection through Stripe comes in WF-102 (Phase 4).
- Accept: balances are correct to the minor unit across currencies; polls close; viewers cannot vote if role forbids.
- Touches: `apps/api/hermi/modules/collaboration/` (polls), `apps/api/hermi/modules/groups/` (expenses and balances), `apps/web/src/routes/group/`.
- Tests: split arithmetic property tests, poll tests.
- Done: DoD.

#### WF-046 Checklist and notes [P1, M, needs WF-029]
- Description: "Before you go" `checklist_items` (at least half unmonetized; visas link to official sites first; insurance uses insurer-approved copy only; AI gives no insurance, visa or legal advice), trip notes, and the after-trip "Was your flight delayed?" prompt.
- Accept: checklist templates generated by destination; at least half of the items have no partner link; copy reviewed against [08-affiliate-revenue.md](../context/business-plan/08-affiliate-revenue.md) rules.
- Touches: `apps/api/hermi/modules/trips/` (checklist and notes), `apps/web/src/routes/checklist/`.
- Tests: template tests (ratio of monetized items), copy lint for forbidden advice phrases.
- Done: DoD.

#### WF-047 Present mode and public share pages [P1, M, needs WF-032]
- Description: full-screen presentation with a swipe story view in portrait and wake lock, and a read-only public share page from `trip_share_links` with Open Graph tags and report link.
- Accept: share page shows no private notes or email; report link creates a moderation item (WF-092); present mode works offline once cached.
- Touches: `apps/web/src/routes/present/`, `apps/api/hermi/modules/collaboration/` (share links), `apps/api/hermi/modules/itinerary/` (presentation data).
- Tests: privacy test on share payload, Playwright present-mode test.
- Done: DoD.

#### WF-048 Currency and FX [P1, S, needs WF-027]
- Description: a daily Frankfurter job into `fx_rates`; money display in original and converted currency; integer minor units everywhere.
- Accept: conversion rounds consistently; stale rates show a notice.
- Touches: `apps/worker/hermi_worker/jobs/refresh_fx_rates.py`, `apps/web/src/lib/money.ts`.
- Tests: conversion tests, stale-rate test.
- Done: DoD.

#### WF-049 Agent runs API and UI [P1, M, needs WF-020, WF-029]
- Description: start, stream events (server-sent events), cancel and list runs; one at a time per account; credit preview before start; results saved as notes and fares with source links.
- Accept: a second start while one runs returns a clear error; cancel stops at the next checkpoint and settles pro rata; events show sources.
- Touches: `apps/api/hermi/modules/ai/router.py`, `apps/web/src/routes/agents/`.
- Tests: API tests, SSE test, cancel test.
- Done: DoD.

#### WF-050 AI consent, labels and reports [P1, S, needs WF-049]
- Description: first-use consent ("Your trip details and questions are sent to Anthropic to generate suggestions") stored in `consents` with timestamp, an AI off toggle, "AI suggestion, check details before booking" labels, thumbs up or down that doubles as report.
- Accept: no AI call without consent; toggle off blocks AI; reports create moderation items.
- Touches: `apps/web/src/components/ai/`, `apps/api/hermi/modules/auth/` (consents).
- Tests: consent gating test, report creation test.
- Done: DoD.

### E8 Entitlements, credits and paywalls

#### WF-051 Entitlement resolver and limit enforcement [P1, L, needs WF-016, WF-026, WF-037]
- Description: a resolver that returns a trip's capabilities as the best of its owner's tier and any pass on that trip; enforces limits from the tier table (trips, routes, credits, collaborators, travelers, and the group tools `polls`, `cost_splitting`, `room_block_request`); `GET /v1/me/entitlements`; charges credits to the person who starts the action.
- Accept: every limited route calls the resolver; Plus with a Trip Pass takes the higher limit; invitees get the owner's tier on that trip only; polls and manual cost splitting are allowed for every paid tier, both passes and Free invitees on such trips, and a Free owner's own trip gets the `group_tools` paywall code; the room-block request and more than 8 travelers need `group_trip_pass`.
- Touches: `apps/api/hermi/modules/billing/` (resolver), `apps/api/hermi/modules/trips/service.py` (`trip_capabilities()`), `packages/shared/src/entitlements.ts`.
- Tests: table-driven tier and pass tests, invitee tests.
- Done: DoD.

#### WF-052 Paywall logic and waitlist screens [P1, M, needs WF-051, WF-035]
- Description: server-decided paywall moments (Trip Pass first when a trip is within 120 days, annual Plus first with 2 or more active trips, credit packs when credits run out, `group_tools` for a Free owner's polls and splitting, `group_pass` for the room-block request or a ninth traveler; `collect_payments` is added with WF-102), and in web beta a "coming with the app" waitlist screen; paywall anti-patterns avoided (no fake urgency; free path visible).
- Accept: paywall code returned by the server drives the screen; waitlist capture works; Plus annual shown first with the trial only on annual.
- Touches: `apps/web/src/routes/paywall/`, `apps/api/hermi/modules/billing/router.py`.
- Tests: decision table tests, component tests.
- Done: DoD.

### E9 Affiliate

#### WF-053 Outbound API and redirect [P1, M, needs WF-026, WF-029]
- Description: `POST /v1/outbound` (checks trip access, picks program by flags, geography and cell, inserts `link_clicks`, returns `/go/{click_id}`) and `GET /go/{click_id}` (fresh under 10 minutes, single use, 302 from a stored template, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`). No open redirects; user id, trip id and email never in URLs.
- Accept: expired, reused or unknown ids fail safely; no `url=` parameter path exists; repeat clicks within 30 seconds deduped; 60 an hour rate limit.
- Touches: `apps/api/hermi/modules/affiliate/router.py`, `modules/affiliate/service.py`.
- Tests: redirect tests, open-redirect attack tests, dedupe test.
- Done: DoD.

#### WF-054 Link builders, disclosure and placements [P1, L, needs WF-053]
- Description: link template builders for Travelpayouts, Viator and Stay22; a shared `PartnerButton` component that always renders "We earn a commission if you book here.", an "Ad" label on UK and EU storefronts, sort explanations on lists, a "Hide booking links" setting; placements on lodging, flights, things to do, cars and eSIM cards; Airbnb listings get plain links only.
- Accept: a component test fails if a partner button renders without disclosure; no list sorts by commission (a test checks ordering code); all placements go through `/go`.
- Touches: `apps/web/src/components/partner-button.tsx`, `apps/api/hermi/modules/affiliate/`.
- Tests: disclosure snapshot tests, ordering test, country label test.
- Done: DoD plus placement map in `docs/affiliate-placements.md`.

#### WF-055 Conversion import [P1, M, needs WF-053]
- Description: nightly jobs that pull Travelpayouts booking statistics and payments (later Impact, Awin), idempotent upsert on program and network transaction id with status history, match by sub-id, and track the unmatched share.
- Accept: a rerun changes nothing; status transitions (pending, approved, rejected, paid) recorded; unmatched share computed; failure alerts.
- Touches: `apps/worker/hermi_worker/jobs/import_affiliate_conversions.py`.
- Tests: fixture payloads, idempotency test, unmatched share test.
- Done: DoD.

### E10 Admin control center (first pieces)

#### WF-056 Admin foundation [P1, L, needs WF-027, WF-028]
- Description: `admin.hermi.world` route group (excluded from the iOS build), `/v1/admin` router, Cloudflare Access JWT check, `admin_users`, WebAuthn and TOTP 2FA with step-up, roles and the permission table, admin DB role, rate limits, strict CSP. Spec: [08-admin-control-center.md](08-admin-control-center.md) sections 2, 3 and 9.
- Accept: customer tokens rejected on admin and the reverse; unknown identities get 403; permission matrix test passes; disabled admin loses access in 60 seconds.
- Touches: `apps/api/hermi/modules/admin/`, `apps/web/src/routes/admin/`, `infra/cloudflare/` (access policy or docs).
- Tests: role by route matrix test, step-up tests, session expiry tests.
- Done: DoD plus Cloudflare Access configured and documented.

#### WF-057 Audit log service and screen [P1, M, needs WF-056]
- Description: `audit_log` writer used in the same transaction as every admin write, redaction, `denied` rows, nightly hash chain to R2 object lock, and the audit viewer.
- Accept: each admin write yields one row with before and after and reason; update and delete rejected; viewer filters work.
- Touches: `apps/api/hermi/modules/admin/audit.py`, `apps/web/src/routes/admin/audit/`.
- Tests: atomicity test (failed action leaves no row pair mismatch), redaction test.
- Done: DoD.

#### WF-058 Admin overview and metric rollups [P1, L, needs WF-056, WF-051]
- Description: rollup jobs every 5 minutes and the overview (MAU, DAU, signups, trials, conversions, MRR, revenue by stream, AI spend versus budget, affiliate clicks and EPC, alerts, kill rule card), with stale-data indicators. Spec: [08](08-admin-control-center.md) section 6.1.
- Accept: each tile matches a hand query on seeded data; stale rollups warn; the kill rule numbers are correct.
- Touches: `apps/api/hermi/modules/admin/overview.py`, `apps/worker/hermi_worker/jobs/rollups.py`, `apps/web/src/routes/admin/overview/`.
- Tests: rollup tests with fixtures, tile rendering tests.
- Done: DoD.

#### WF-059 Admin users: read, search, reveal [P1, M, needs WF-056, WF-057]
- Description: search by email hash, id and other keys, masked list, profile tabs, per-record reveal with reason and rate limit.
- Accept: no raw email or name in any list response; reveal audited; search never returns partial PII matches.
- Touches: `apps/api/hermi/modules/admin/users.py`, `apps/web/src/routes/admin/users/`.
- Tests: serializer masking scan test, reveal limit test.
- Done: DoD.

#### WF-060 Admin user actions [P1, L, needs WF-059, WF-016]
- Description: grant credits, extend a pass, comp a subscription (RevenueCat promotional API), force sign-out, start export, queue or process deletion, hold AI; role limits and confirmation tiers.
- Accept: limits enforced (for example support 50 credits a grant); each action audited with before and after; comp does not stack on a paid subscription.
- Touches: `apps/api/hermi/modules/admin/user_actions.py`.
- Tests: limit tests per role, audit tests, idempotency tests.
- Done: DoD.

#### WF-061 Admin impersonation [P1, M, needs WF-060]
- Description: consent request to the user (in-app and email), 15 minute read-only token with `imp` claim, banner, per-page audit, "Support access log" in the user's Settings.
- Accept: no consent means no session; any non-GET is rejected; expiry enforced; the user can see the log.
- Touches: `apps/api/hermi/modules/admin/impersonation.py`, `apps/web/src/routes/settings/support-access.tsx`.
- Tests: consent flow tests, write-block test, expiry test.
- Done: DoD.

#### WF-062 Admin kill switches and breakers [P1, M, needs WF-056, WF-014, WF-023]
- Description: the switches screen with state, expiry and effect counts, confirmation dialog with typed key and step-up, mandatory expiry, auto-expiry notification, breaker history.
- Accept: every manual off has an expiry; `ai.all` off blocks AI within 5 seconds; expiry writes a `system` audit row; drill recorded.
- Touches: `apps/api/hermi/modules/admin/killswitches.py`, `apps/web/src/routes/admin/killswitches/`.
- Tests: expiry and fail-closed tests, UI confirmation tests.
- Done: DoD plus a timed drill (under 30 seconds to stop AI).

#### WF-063 Admin credits and AI spend [P1, L, needs WF-056, WF-015, WF-017]
- Description: spend by feature, tier and model, top spenders, ceiling hits, runaway detection, live runs, cancel a run, reconciliation gap, cache hit rates.
- Accept: a seeded runaway appears in the list; cancel settles pro rata; numbers match `ai_usage`.
- Touches: `apps/api/hermi/modules/admin/ai_spend.py`, `apps/web/src/routes/admin/ai-spend/`.
- Tests: detection rule tests, cancel test.
- Done: DoD.

### E11 Notifications, privacy and observability

#### WF-064 Notification service and email [P1, M, needs WF-018]
- Description: a `notify` lane service with preferences by type, quiet hours, per-trip mute, unique keys per user and alert, Resend email templates (deletion confirmation, invite, weekly digest), unsubscribe handling.
- Accept: a retried job never sends twice; quiet hours defer; marketing needs opt-in.
- Touches: `apps/api/hermi/modules/notifications/`.
- Tests: dedupe test, quiet hours test, preference test.
- Done: DoD.

#### WF-065 Account deletion [P1, M, needs WF-028, WF-064]
- Description: in-app deletion request, 14 to 30 day grace, hard delete of trip data and files, transfer or delete shared trips, delete the Supabase Auth user, revoke the Sign in with Apple token, warning that an Apple subscription is not cancelled.
- Accept: after the sweep no row in any table references the user; shared trips transfer or delete as chosen; the confirmation email is sent; backups purge on their cycle (documented).
- Touches: `apps/api/hermi/modules/auth/` (deletion), `apps/worker/hermi_worker/jobs/delete_account.py`.
- Tests: end-to-end deletion test over all tables, grace cancel test.
- Done: DoD.

#### WF-066 Data export [P1, M, needs WF-065]
- Description: "Export my data" as JSON plus ICS through a job, stored in R2, emailed link with 24 hour expiry, available on every tier.
- Accept: export includes all user-owned data; link expires; another user cannot fetch it.
- Touches: `apps/api/hermi/modules/auth/` (export), `apps/worker/hermi_worker/jobs/export_user_data.py`.
- Tests: completeness test, expiry test, authorization test.
- Done: DoD.

#### WF-067 Consents and legal pages [P1, S, needs WF-050]
- Description: privacy policy, terms, affiliate disclosure, AI disclaimer, licenses screen (data attributions), links in Settings; consent history.
- Accept: pages public and linked from Settings and sign-in; policy names Anthropic and affiliate click logging.
- Touches: `apps/web/src/routes/legal/`.
- Tests: link presence tests.
- Done: DoD plus counsel review noted or explicitly deferred.

#### WF-068 Sentry and structured logs [P1, S, needs WF-009]
- Description: JSON logs with `request_id`, `job_id`, `run_id`, opaque `user_id`; Sentry in API, worker and web with PII scrubbing; `RedactSecrets` covers `Authorization` and `x-api-key`; prompts never logged above DEBUG.
- Accept: a thrown error reaches Sentry with release and environment; a log scan test finds no emails or tokens.
- Touches: `apps/api/hermi/logging.py`, `apps/web/src/lib/sentry.ts`.
- Tests: redaction tests.
- Done: DoD.

#### WF-069 PostHog analytics [P1, S, needs WF-035]
- Description: events `signup`, `trip_created`, `first_itinerary_item`, `ai_used`, `paywall_viewed`, `purchase_started`, `purchase_completed`, `restore_tapped`, `push_opt_in`, `invite_sent`, `invite_accepted`; session replay off or masked; opt-out respected; no ad SDKs.
- Accept: events fire once; opt-out stops all events; event catalog in `docs/analytics.md` matches [10-quality-security-launch.md](10-quality-security-launch.md).
- Touches: `apps/web/src/lib/analytics.ts`, `apps/api/hermi/analytics.py`, `packages/shared/src/events.ts`.
- Tests: event firing tests, opt-out test.
- Done: DoD.

#### WF-070 Uptime, alerts and status page [P1, M, needs WF-068]
- Description: probes on `/health/ready` from two regions, a synthetic sign-in and trip-load check, heartbeat monitors (scheduler, nightly jobs, queue), public status page, alert routing (phone for outage, data loss risk and spend runaway only).
- Accept: stopping the worker in staging raises a page within 5 minutes; status page live.
- Touches: `infra/render/render.yaml` (heartbeats), `docs/runbooks/`.
- Tests: drill recorded.
- Done: DoD.

#### WF-071 Backups and restore drill [P1, M, needs WF-009]
- Description: PITR enabled, daily snapshots, a weekly encrypted `pg_dump` to R2 in another account, and a scripted restore to a scratch database with the smoke test run against it.
- Accept: restore completes within the 1 hour RTO target; the drill is repeated quarterly (calendar entry).
- Touches: `infra/render/` (backup settings), `infra/scripts/restore-drill.sh`.
- Tests: the drill itself.
- Done: DoD plus drill result in `docs/runbooks/restore.md`.

#### WF-072 Migrate the owner's existing data [P1, L, needs WF-025, WF-029]
- Description: export from the local Trip Planner database, transform (UUIDs, `owner_user_id`, `linked_user_id`, money to minor units), import into hosted with a dry run, row-count and checksum verification, and a manual walk-through of each trip. Back up both sides first.
- Accept: dry run reports zero unmapped rows; counts match per table; both owners sign in and see their trips; the import is idempotent.
- Touches: `infra/scripts/import_trip_planner.py`, `docs/runbooks/owner-migration.md`.
- Tests: import run against a fixture copy of a real-shaped database, idempotency test.
- Done: DoD plus the old install kept read-only for 30 days.

#### WF-073 Beta operations and retention report [P1, M, needs WF-058, WF-069]
- Description: invite tooling for 50 to 200 waitlist users, a weekly feedback loop, and a retention report (week 1 and week 4) with AI cost per active user against ceilings.
- Accept: invites can be issued in batches; the report produces the Phase 1 gate numbers.
- Touches: `apps/api/hermi/modules/admin/invites.py`, `infra/scripts/retention_report.py`.
- Tests: cohort calculation tests.
- Done: DoD plus the gate review recorded.

### E12 RevenueCat and purchases (Phase 2)

#### WF-074 RevenueCat webhook and reconcile [P2, L, needs WF-026, WF-051]
- Description: `POST /v1/webhooks/revenuecat` (secret header, idempotent on event id in `webhook_events`), `entitlements` and `subscriptions` updates, `POST /v1/purchases/sync`, nightly reconcile against the RevenueCat REST API, `app_user_id` linked to the account UUID.
- Accept: replayed webhooks change nothing; grace, billing retry, expiry and refund handled; reconcile flags mismatches; sync unlocks instantly before the webhook arrives.
- Touches: `apps/api/hermi/modules/billing/revenuecat.py`, `apps/worker/hermi_worker/jobs/reconcile_entitlements.py`.
- Tests: fixture event suite, replay test, out-of-order test.
- Done: DoD.

#### WF-075 Credit grants and refund reversal [P2, M, needs WF-074, WF-016]
- Description: monthly allowance grants on renewal (subscribers) or calendar month (Free), pack grants `credits_50`, `credits_150`, `credits_400` keyed by store transaction id (12 month expiry, spent last), `REFUND` reversal allowing negative balance.
- Accept: a transaction id grants exactly once; a refund reverses the grant and blocks AI until positive; ledger history shows each step.
- Touches: `apps/api/hermi/modules/billing/grants.py`.
- Tests: duplicate event test, refund test, expiry test.
- Done: DoD.

#### WF-076 Trip Pass binding [P2, M, needs WF-074]
- Description: `trip_pass` non-renewing subscription handling, buy then pick a trip, transaction recorded in `store_transactions` (`kind = 'pass'`) and, once a trip is known, in `trip_passes`, 90 days from binding, an unapplied pass waiting in Settings (`GET /v1/me/passes`), `POST /v1/me/passes/{pass_id}/bind` and `POST /v1/me/passes/{pass_id}/move` (once, `move_count`); limits (2 live routes, 60 live checks, 40 credits, 6 collaborators, polls and manual cost splitting).
- Accept: a pass binds to exactly one trip; expiry handled on the server; pass shown in trip settings; a second apply attempt is refused.
- Touches: `apps/api/hermi/modules/billing/passes.py`, `apps/web/src/routes/trip-settings/`.
- Tests: bind, expire, move-once tests; a Group Trip Pass bound over an active Trip Pass marks the old pass `upgraded` (07 section 7.9).
- Done: DoD.

#### WF-077 Family plan [P2, L, needs WF-038, WF-075]
- Description: `family` tier with up to 6 household members invited in the app, 150 pooled credits, pooled ceiling $3.40, 5 live routes; Apple Family Sharing stays off.
- Accept: pooled credits spend in order across members; member removal keeps history; seventh member refused; the `family` plan is sellable at launch (no flag; `plans.is_active` only).
- Touches: `apps/api/hermi/modules/billing/family.py`, `apps/web/src/routes/household/`.
- Tests: pooled spend concurrency test, membership limit test.
- Done: DoD.

#### WF-078 Pro behind a flag [P2, M, needs WF-051, WF-022]
- Description: `pro` entitlement (240 credits, 6 live routes, scheduled agent routines, priority queue with aging) built and dark behind `tier_pro` and `scheduled_agent_routines`; products added to the same subscription group in a later step.
- Accept: with the flag off nothing is visible and no scheduled agent runs; with it on for a test user, routines run within ceilings.
- Touches: `apps/api/hermi/modules/billing/pro.py`, `apps/worker/hermi_worker/scheduler.py`.
- Tests: flag off/on tests, priority aging test.
- Done: DoD.

#### WF-079 Admin subscriptions and webhook replay [P2, M, needs WF-074, WF-056]
- Description: the subscriptions screen, RevenueCat sync status, failed webhook list, dry-run replay, reconcile button, refund reversal visibility. Spec: [08](08-admin-control-center.md) section 6.3.
- Accept: a failed event can be replayed without double grants; mismatches listed; Stripe refund action limited by role.
- Touches: `apps/api/hermi/modules/admin/billing.py`, `apps/web/src/routes/admin/subscriptions/`.
- Tests: replay idempotency test, permission tests.
- Done: DoD.

#### WF-114 Group Trip Pass and room-block request [P2, M, needs WF-076, WF-045, WF-051, WF-064]
- Description: sell `group_trip_pass` ($19.99, 90 days, `hermi_group_trip_pass`) and bind it to one trip like WF-076, with the higher limits from its `plans` row (12 travelers, 11 collaborators, 80 credits, `room_block_request`); the room-block request form writing `room_block_requests` (hotel, dates, rooms, guests, budget, notes, plain disclosure), emailed to the concierge team inbox until the WF-103 queue exists, with its status visible to the requester; flag `room_block_requests` (on at launch) and the same seller-of-travel region gate as concierge ([10-quality-security-launch.md](10-quality-security-launch.md) section 3.8).
- Accept: a pass supports 12 travelers and not a 13th; polls and manual cost splitting work on the trip for every member, including Free invitees; the room-block request needs a Group Trip Pass (otherwise the `group_pass` paywall) and creates no charge or obligation; disclosure is always visible; the request is hidden in regions where concierge is not confirmed.
- Touches: `apps/api/hermi/modules/billing/passes.py`, `apps/api/hermi/modules/concierge/` (room-block requests), `apps/web/src/routes/group/`, `apps/web/src/routes/trip-settings/`.
- Tests: traveler cap test, entitlement tests per tier and pass, room-block entitlement and disclosure tests, bind and move-once test shared with WF-076.
- Done: DoD plus product metadata and review screenshot uploaded for the Group Trip Pass.

### E13 Capacitor iOS shell

#### WF-080 Capacitor shell, signing and CI [P2, L, needs WF-036, Mac or Xcode Cloud]
- Description: `ios/` Capacitor project (bundled, no `server.url`), bundle id with Push, Associated Domains, Sign in with Apple and In-App Purchase, icon and splash from the brand files, signing, Xcode Cloud or Fastlane build, build flag that excludes admin routes.
- Accept: the app launches on a device against staging; the release build contains no admin code; CI produces a signed build.
- Touches: `apps/ios/`, `apps/ios/capacitor.config.ts`, `apps/web/vite.config.ts`.
- Tests: native launch smoke test; bundle inspection script.
- Done: DoD plus Apple Developer and Paid Applications Agreement status noted.

#### WF-081 Native plugins [P2, M, needs WF-080]
- Description: push plugin wiring, share, haptics, status bar, keyboard resize, secure storage (Keychain), in-app review (at most 3 a year, never after an error), app URL open, and `SFSafariViewController` through the Capacitor Browser plugin for affiliate links.
- Accept: each plugin has a web fallback; partner links open in `SFSafariViewController`; attribution loss measured against Safari and recorded.
- Touches: `apps/web/src/lib/native/`, `apps/ios/plugins/`.
- Tests: plugin mock tests, device checklist.
- Done: DoD.

#### WF-082 Sign in with Apple native [P2, M, needs WF-080, WF-028]
- Description: native Apple sign-in exchanged through Supabase, Keychain session storage, "Hide My Email" relay handling, server-to-server notification handling for email changes and deletion.
- Accept: sign in works on device; token revoke on deletion works (tested with WF-065); reviewers can sign in with the demo account.
- Touches: `apps/web/src/lib/native/apple-sign-in.ts`, `apps/api/hermi/modules/auth/apple.py`.
- Tests: exchange tests, notification handler tests.
- Done: DoD.

#### WF-083 Purchases in the app [P2, L, needs WF-074, WF-080]
- Description: `@revenuecat/purchases-capacitor`, `logIn` and `logOut` tied to sign-in, products in App Store Connect (`hermi_plus_monthly`, `hermi_plus_annual` with 7-day trial on annual only, `hermi_family_monthly`, `hermi_family_annual`, `hermi_trip_pass`, `hermi_group_trip_pass`, credit packs; ids as in [03-database-schema.md](03-database-schema.md) section 11.2), paywall purchase flow with price and period first, trial length and after-trial price, Terms and Privacy links, Restore on the paywall and in Settings, sync call after purchase.
- Accept: every sandbox purchase unlocks within seconds; Restore works on a second device; paywall text meets Guideline 3.1.2.
- Touches: `apps/web/src/lib/native/purchases.ts`, `apps/web/src/routes/paywall/`.
- Tests: mocked purchase flow tests; sandbox checklist in WF-090.
- Done: DoD plus product metadata and review screenshots uploaded.

#### WF-084 Universal links and invite flow [P2, M, needs WF-080, WF-032]
- Description: `/.well-known/apple-app-site-association` (JSON, no redirect), routes `/invite/:token`, `/trips/:id`, `/s/:shareId`, `appUrlOpen` routing into React Router, cold start from a deep link tested.
- Accept: tapping an invite in Messages opens the app on the invite screen; without the app it opens the web invite.
- Touches: `infra/cloudflare/aasa.json`, `apps/web/src/lib/native/links.ts`.
- Tests: route mapping tests; device test.
- Done: DoD.

#### WF-085 APNs, devices and price-drop push [P2, M, needs WF-064, WF-081]
- Description: `devices` registration, direct APNs with a `.p8` key over HTTP/2, 410 cleanup, collapse ids, topics (price drop, itinerary reminder, invite accepted, trip starts tomorrow), local notifications for "leave for the airport".
- Accept: a price drop arrives on device within 30 minutes of the check; dead tokens deleted; asking for permission happens after the first alert, not at launch.
- Touches: `apps/api/hermi/providers/apns.py`, `apps/api/hermi/modules/notifications/`, `apps/web/src/lib/native/push.ts`.
- Tests: APNs client tests with a fake, 410 cleanup test.
- Done: DoD.

#### WF-086 Notification preferences UI [P2, S, needs WF-085]
- Description: preference center by type, quiet hours, per-trip mute, batching of price alerts.
- Accept: preferences respected by the service; no marketing push without opt-in.
- Touches: `apps/web/src/routes/settings/notifications.tsx`.
- Tests: component tests, service preference tests.
- Done: DoD.

#### WF-087 Offline cache and mutation queue [P2, L, needs WF-036, WF-080]
- Description: persisted TanStack Query cache for trip-scoped queries (30 day `gcTime`, `offlineFirst`), SQLite for critical data, "Download for offline" with automatic download within 7 days of departure, offline edits for notes, checkmarks and expenses (last write wins per field), offline banner.
- Accept: a full trip is browsable in airplane mode on a device; queued edits sync on reconnect; rejected edits show a toast.
- Touches: `apps/web/src/lib/offline/`, `apps/web/src/app/providers.tsx`.
- Tests: persister tests, mutation replay tests, device test.
- Done: DoD.

#### WF-088 Mobile accessibility, i18n base and privacy manifest [P2, M, needs WF-080]
- Description: VoiceOver labels and focus order, Dynamic Type, reduce motion, axe in Playwright, the contrast unit test over every token pair in [05-ui-ux-spec.md](05-ui-ux-spec.md) section 2.3 including the added `--tp-edge` (control borders, 3 to 1) and `--tp-warning-ink` (small warning text, 4.5 to 1) with Increase Contrast swapping `--tp-rule` and `--tp-edge` to ink, `react-i18next` extraction of copy, `PrivacyInfo.xcprivacy` with required-reason API declarations, Info.plist purpose strings, privacy label answers matching click logging.
- Accept: no axe critical issues; `--tp-edge` and `--tp-warning-ink` pairs pass in light, dark and Increase Contrast; all permission strings present; label answers match the policy.
- Touches: `apps/web/src/lib/i18n/`, `apps/ios/App/PrivacyInfo.xcprivacy`, `packages/tokens/` (contrast test).
- Tests: axe suite, token contrast test, string extraction test.
- Done: DoD.

#### WF-089 Maestro tests and TestFlight pipeline [P2, M, needs WF-080]
- Description: Maestro native smoke flows (sign in, create trip, open offline, purchase in sandbox), automated TestFlight upload with dSYM and source map upload to Sentry, internal testers from week 1 and external from week 4.
- Accept: a tagged build reaches TestFlight automatically; crash reports symbolicated.
- Touches: `apps/ios/fastlane/` or Xcode Cloud workflows, `apps/web/e2e/maestro/`.
- Tests: the Maestro flows.
- Done: DoD.

#### WF-090 Sandbox purchase matrix [P2, M, needs WF-083, WF-077, WF-114]
- Description: run and record every scenario: purchase, cancel, upgrade (Plus to Family), downgrade, refund, restore on a second device, billing retry, Trip Pass and Group Trip Pass each bound to a trip, credit pack grant once, expired pass.
- Accept: each scenario passes or has a fixed bug; results in `docs/qa/purchase-matrix.md`; gate evidence for Phase 2.
- Touches: `docs/qa/`.
- Tests: the matrix.
- Done: DoD.

### E14 Phase 3 admin, launch and listing

#### WF-091 Admin support inbox and macros [P3, L, needs WF-056, WF-064]
- Description: ticket intake (in-app contact with version, device, user id and error id attached; email to support), linking to users, replies via Resend, macros from `admin/macros/*.md`, SLA timers. Spec: [08](08-admin-control-center.md) section 6.11.
- Accept: a ticket links to its user automatically; a reply uses a macro; overdue tickets flag; refund replies prompt an audited action.
- Touches: `apps/api/hermi/modules/admin/support.py`, `apps/web/src/routes/admin/support/`.
- Tests: intake tests, macro rendering tests, SLA tests.
- Done: DoD.

#### WF-092 Admin moderation queue and in-app report [P3, M, needs WF-047, WF-050, WF-056]
- Description: queues for reported shared trips and AI content reports, actions (dismiss, hide, disable link, flag research cache entry, suspend sharing), in-app report and block, 24 hour response alert.
- Accept: a report reaches the queue; disabling a link takes effect immediately; flagged cache entries are not served.
- Touches: `apps/api/hermi/modules/admin/moderation.py`, `apps/web/src/components/report/`.
- Tests: queue tests, action tests.
- Done: DoD.

#### WF-093 Admin flags, experiments, provider and system health [P3, L, needs WF-056, WF-014, WF-069]
- Description: flags and experiments with results and guardrails, provider health (SerpApi, Travelpayouts, Geoapify, Anthropic, Stripe), system health (queues, failures, webhook backlog, deploys), job retry. Spec: [08](08-admin-control-center.md) sections 6.6, 6.13 and 6.14.
- Accept: an experiment cannot touch disclosure or ranking keys; Pro cannot be enabled without the gate unless overridden with a reason; retry is idempotent.
- Touches: `apps/api/hermi/modules/admin/flags.py`, `providers.py`, `system.py`, `apps/web/src/routes/admin/` screens.
- Tests: guardrail tests, results calculation tests.
- Done: DoD.

#### WF-094 Admin affiliate screens, link checker and disclosure audit [P3, L, needs WF-055, WF-056]
- Description: revenue by network, program and placement, conversion import status, cash view, broken link checker (our own redirect and partner tracking domains only, never Airbnb, Vrbo or Booking.com pages), disclosure audit, two-person template approval. Spec: [08](08-admin-control-center.md) section 6.7.
- Accept: a broken template is detected; the checker makes no request to forbidden domains (test); an unapproved template edit cannot go live.
- Touches: `apps/api/hermi/modules/admin/affiliate.py`, `apps/web/src/routes/admin/` screens.
- Tests: checker network-block test, two-person approval test.
- Done: DoD.

#### WF-095 Admin finance reports and settings [P3, L, needs WF-056, WF-058]
- Description: monthly revenue by stream, Apple and Stripe fees, AI and provider cost, gross margin, manual cost entries, month lock, audited CSV export; settings screen (prices display, credit prices, ceilings) with bounds, scheduling and history. Spec: [08](08-admin-control-center.md) sections 6.15 and 6.16.
- Accept: margin matches a hand calculation for one month; CSV has no emails; out-of-bounds settings rejected; history lists before and after.
- Touches: `apps/api/hermi/modules/admin/finance.py`, `settings.py`, `apps/web/src/routes/admin/` screens.
- Tests: fee calculation tests, bounds tests, CSV PII scan test.
- Done: DoD.

#### WF-096 Store listing assets [P3, M, needs WF-089]
- Description: app name "Hermi: Group Trip Planner", subtitle "Plan together. Know the fare.", keywords, promotional text, description, six 6.9 inch screenshots (overview, itinerary on map, price-drop alert, AI plan, offline mode, shared trip), 1024 icon without alpha, age rating questionnaire, privacy labels, localizations (en-US, es, de).
- Accept: all App Store Connect fields complete; screenshots from real builds; privacy labels match the policy and click logging.
- Touches: `docs/store/`.
- Tests: checklist review.
- Done: DoD.

#### WF-097 Review notes and demo account [P3, S, needs WF-090, WF-096]
- Description: a demo account (email and password, not Sign in with Apple) with a loaded trip and a working sandbox purchase path, review notes covering AI, deletion location, push, affiliate links under Guideline 3.1.3(e), no ATT prompt, live servers and a phone number.
- Accept: a fresh device signs in with the demo account against production; Restore, deletion and report paths are visible.
- Touches: `docs/store/review-notes.md`.
- Tests: manual pass on a clean device.
- Done: DoD.

#### WF-098 Load test and runbooks [P3, M, needs WF-070, WF-071]
- Description: load test at 10 times expected launch traffic and 5,000 synthetic routines, runbooks for the top incidents (provider outage, bad deploy, leaked key, runaway AI spend, restore, Supabase Auth outage), on-call alert routing test, status page copy.
- Accept: p95 latency and queue wait within targets; each runbook exercised once; key rotation list complete.
- Touches: `docs/runbooks/`, `infra/scripts/loadtest/`.
- Tests: the load test.
- Done: DoD.

#### WF-099 Direct affiliate application pack [P3, S, needs WF-054, WF-058]
- Description: prepare applications for Expedia Group (Vrbo, Expedia, Hotels.com), Booking.com (confirm its current network), Skyscanner, Airalo and GetYourGuide, with the live app link, screenshots of disclosure and placement, and traffic numbers exported from the admin overview.
- Accept: five application packets ready; submission scheduled for month 3.
- Touches: `docs/affiliate/applications/`.
- Tests: checklist review.
- Done: DoD.

#### WF-100 Submission, review handling and launch [P3, M, needs WF-097, WF-098]
- Description: re-read Apple guidelines on the day, final recheck of open questions (SerpApi status, external purchase rules), submit with manual release, handle up to two review cycles, phased release, launch content (waitlist email, Product Hunt, Reddit), 72-hour monitoring.
- Accept: app approved and live; first 72 hours have no P0; crash-free at least 99.5 percent; API error rate under 1 percent.
- Touches: `docs/launch/`.
- Tests: post-launch smoke test script.
- Done: DoD plus gate review.

### E15 Phase 4 growth

#### WF-101 Direct affiliate adapters [P4, L, needs WF-099, WF-055]
- Description: network adapters and templates for approved direct programs (Impact, Awin or CJ as applicable) added through the provider interface, with conversion import and link checker coverage.
- Accept: each approved program works end to end with a test booking; measured clicks and conversions replace the model's assumptions in the admin view.
- Touches: `apps/api/hermi/modules/affiliate/adapters/`.
- Tests: fixture tests per adapter.
- Done: DoD.

#### WF-102 Stripe group payments [P4, L, needs WF-114, WF-045]
- Description: real-world cost collection through Stripe for trips with `group_trip_pass` or `pro`, behind the `group_payments` flag: payee onboarding, payment requests from `settlements` (`method = 'stripe'`, `stripe_payment_intent_id`), status sync by webhook, and the `collect_payments` paywall for other trips (never Apple In-App Purchase, never for digital features). The Group Trip Pass itself, polls, manual cost splitting and the room-block request ship earlier (WF-045, WF-051, WF-114).
- Accept: a settlement on a `group_trip_pass` or `pro` trip creates a Stripe payment and reflects its status; a trip without either is refused with the `collect_payments` paywall; flag `group_payments` gates the feature; manual "mark as paid" keeps working when the flag is off.
- Touches: `apps/api/hermi/modules/groups/` (Stripe settle-up), `apps/api/hermi/providers/stripe.py`, `apps/api/hermi/modules/billing/` (Stripe webhooks).
- Tests: Stripe fake tests, webhook idempotency, entitlement refusal tests.
- Done: DoD.

#### WF-103 Admin concierge and group payments screens [P4, M, needs WF-102, WF-104]
- Description: concierge queue (status, assignee, SLA, commission record) and group payments and disputes screens. Spec: [08](08-admin-control-center.md) sections 6.8 and 6.9.
- Accept: commission recorded by finance only; disputes show due dates and alert 3 days before.
- Touches: `apps/api/hermi/modules/admin/concierge.py`, `payments.py`, `apps/web/src/routes/admin/` screens.
- Tests: permission tests, SLA tests.
- Done: DoD.

#### WF-104 Concierge flow [P4, M, needs WF-054]
- Description: optional "Have a human book this" on stays, cruises and complex trips, creates a `concierge_requests` row only on explicit tap, disclosure shown, perks listed, status updates by email.
- Accept: no request is created without a tap; disclosure always visible; requester can cancel.
- Touches: `apps/api/hermi/modules/concierge/`, `apps/web/src/routes/concierge/`.
- Tests: creation and cancel tests, disclosure snapshot test.
- Done: DoD.

#### WF-105 Pro launch [P4, M, needs WF-078, WF-024]
- Description: check the gate (mean agent cost of $0.60 or less over 200 runs, or over 15 percent of Plus payers buying agent-run credits), add `pro_monthly` ($11.99) and `pro_annual` ($99) to the `hermi_membership` group, paywall updates, scheduled agent routines on.
- Accept: gate numbers recorded; Pro upgrades apply immediately and downgrades at renewal; ceilings and priority queue verified.
- Touches: `apps/api/hermi/modules/billing/pro.py`, `apps/web/src/routes/paywall/`.
- Tests: upgrade and downgrade flow tests, gate check test.
- Done: DoD.

#### WF-106 Partner guides [P4, L, needs WF-056, WF-054]
- Description: labeled destination guides (`partner_guides`) in the app and the admin editor with review workflow (author cannot approve own guide), sponsor label, versioning and diff. Spec: [08](08-admin-control-center.md) section 6.10.
- Accept: a guide cannot publish without sponsor label and approval; guides never appear in search or ranked lists.
- Touches: `apps/api/hermi/modules/affiliate/` (partner guides), `apps/api/hermi/modules/admin/guides.py`, `apps/web/src/routes/admin/` screens.
- Tests: workflow tests, never-in-search test.
- Done: DoD.

#### WF-107 Hermi for Advisors: organizations, seats, workspaces [P4, L, needs WF-029, WF-065]
- Description: `advisor_orgs`, `advisor_seats`, `advisor_clients`; client trip workspaces, branded presentation mode, proposals, commission tracking; web only.
- Accept: advisor data is isolated by org in RLS; a client sees only their own trips; removing a seat revokes access.
- Touches: `apps/api/hermi/modules/advisors/`, `apps/web/src/routes/advisors/`.
- Tests: tenancy tests for orgs, seat limit tests.
- Done: DoD.

#### WF-108 Advisor billing and admin [P4, M, needs WF-107]
- Description: Stripe subscriptions for `advisor_seat` ($29 a seat a month, $24 annual) on the web only, seat changes, invoices, and admin screens for orgs and seats.
- Accept: seat add and remove prorate correctly; nothing is sold to iOS users through this path; admin shows org status.
- Touches: `apps/api/hermi/modules/advisors/billing.py`, `apps/api/hermi/modules/admin/advisors.py`.
- Tests: Stripe fake tests, proration tests.
- Done: DoD.

#### WF-109 Printed trip books [P4, M, needs WF-047]
- Description: print-on-demand trip books and posters from present mode, ordered on the web through Stripe, `print_orders` with status from the print partner.
- Accept: an order generates a print-ready PDF and tracks status; refunds handled; sold on the web only.
- Touches: `apps/api/hermi/modules/advisors/` (print orders), `apps/web/src/routes/print/`.
- Tests: PDF generation golden test, order state tests.
- Done: DoD.

#### WF-110 LiteAPI hotel booking [P4, L, needs WF-054, WF-102]
- Description: in-app hotel booking through LiteAPI (merchant of record) behind a flag, started only after click data shows strong booking intent; never ranked by margin.
- Accept: booking completes in a sandbox end to end; disclosure shown; list order is explained and independent of margin.
- Touches: `apps/api/hermi/providers/liteapi.py`, `apps/web/src/routes/lodging/book/`.
- Tests: sandbox booking tests, ordering test.
- Done: DoD.

#### WF-111 Android [P4, L, needs WF-089]
- Description: Capacitor Android, Play Billing through RevenueCat, FCM push, App Links, Play listing.
- Accept: core flows pass on a device; purchases work in the Play sandbox.
- Touches: `apps/android/` (sibling of `apps/ios/`), `apps/web/src/lib/native/`.
- Tests: device checklist and Maestro flows.
- Done: DoD.

#### WF-112 SEO public pages [P4, M, needs WF-047]
- Description: server-rendered shareable trip pages and destination guides separate from the SPA, sitemaps, Open Graph, and the report link.
- Accept: pages render without JavaScript; private data never appears; indexing follows trip owner choice.
- Touches: `apps/api/hermi/modules/collaboration/` (public share pages), `apps/web/seo-templates/`.
- Tests: rendering tests, privacy tests.
- Done: DoD.

#### WF-113 Retention loop and experiments [P4, M, needs WF-093, WF-069]
- Description: paywall experiments, win-back offers, lifecycle messages with opt-in, referral, run through the experiments screen with guardrails.
- Accept: each experiment has a hypothesis, sample size and stopping rule; no experiment hides disclosure or weakens the free path.
- Touches: `apps/web/src/routes/paywall/`, `apps/api/hermi/modules/notifications/` (lifecycle messages).
- Tests: assignment stickiness tests, guardrail tests.
- Done: DoD.

## 6. How to work with Claude Code

- **One ticket, one session.** Start a fresh session per ticket. Tell Claude: "Do WF-0NN from `09-build-roadmap.md`. Read the ticket, its dependencies, and the spec files it names first." A ticket that cannot be finished in one session is too big: split it and add the new ticket under the same epic.
- **Keep the session small.** Aim for about 400 changed lines and at most one migration. If context grows long, finish, commit and start a new session rather than continuing.
- **Plan before code.** For L tickets, ask for a short plan (files, tests, risks) and approve it, then build.
- **Tests first.** Write or ask for the failing tests named in the ticket before the implementation. The acceptance criteria are the test list.
- **Always run the checks.** Before declaring done, run `npm run lint` and `npm test` (and `npm run gen:api` when routes changed, the e2e smoke test when a flow changed). Paste the result in the PR. Do not accept "tests should pass".
- **Use Sonnet for subagents.** Any subagent spawned while building this project must use the Sonnet model (`claude-sonnet-5-5`). Use subagents for read-heavy work (searching the spec, reviewing a diff), not for writing migrations.
- **Commit per ticket.** One commit or one small PR per ticket with the message `WF-0NN title`; never mix tickets. Tickets that add migrations merge one at a time.
- **Read the rules first.** Read `.claude/rules/database-migrations.md` before any model or migration change, the agent rules before touching the worker or agent code, and the frontend rules before UI copy or styling.
- **Do not grow the project instructions unprompted.** If something seems worth keeping, say so in one line and let the owner decide. Reference and procedures go in `docs/` or `.claude/skills/`; a procedure that repeats becomes a skill.
- **Safety rules apply in every session.** No secrets in the repo; no fetching of Airbnb, Vrbo or Booking.com pages; no scraper libraries; no ranking by commission; no em dashes in copy.
- **Parallelism.** Run 2 or 3 sessions in parallel only when tickets touch different modules and at most one adds a migration. Use separate branches and merge the migration ticket first.
- **Mac-bound work.** iOS tickets (WF-080 to WF-090) need macOS; do the web and backend parts first and batch the device steps.
- **When stuck.** If acceptance criteria conflict with a spec, stop and ask; the README's shared decisions win, then the topic spec, then this file.
- **Gate reviews.** At each phase exit, run the exit checklist in section 1 as a session of its own and write the result to `docs/gates/phase-N.md` before starting the next phase.
