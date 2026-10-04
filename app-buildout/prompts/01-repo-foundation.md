# Prompt 01: Repository foundation, CI and landing page

Phase 1 build, step 1 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Create the Hermi monorepo skeleton exactly as the architecture tree describes, with working lint, test and format commands, CI, native PostgreSQL 18 locally (Docker is optional), health endpoints, security scanning, and a static landing page with a waitlist form. WF-001 and WF-003 are business tasks: produce their documents and checklists (`Done (docs)`) with a provisional "go" in `DECISIONS.md`, and record the parts only the owner can do.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-001 | Name, domain and email |
| WF-003 | Interview kit, price test and terms checklist |
| WF-004 | Scaffold the repository |
| WF-006 | Typed configuration and environments |
| WF-007 | CI pipeline |
| WF-008 | Docker image, compose and health endpoints |
| WF-010 | Security scanning workflows |
| WF-002 | Landing page and waitlist |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/README.md`
- `app-buildout/phase-1-launch/02-architecture.md` (sections 1, 2, 7, 9 to 11)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (section 1, testing layers)
- `app-buildout/README.md` (non-negotiable rules)
- `app-buildout/context/business-plan/01-business-plan.md` (M0 validate)
- `app-buildout/phase-1-launch/design/README.md`, `app-buildout/phase-1-launch/design/tokens.css` and `app-buildout/phase-1-launch/design/screens/01-welcome.html` (the brand look for the landing page)

## Notes

- The context layout already exists (`CLAUDE.md`, `.claude/rules/`, `.claude/skills/`, `.claude/agents/`, `knowledge/`), set up by `context-kit` 0.10.0 (`/context-init`). This prompt and WF-004 do not create `CLAUDE.md` or rule stubs: they add only the verified Commands section to `CLAUDE.md` once the scaffold's commands run (keep it under 200 lines), extend an existing rule when a new path needs it, and create the skill `.claude/skills/run-hermi-locally/SKILL.md` as `AUTOPILOT.md` describes.
- The architecture tree mentions `docs/spec/`: the spec stays in `app-buildout/` at the repo root instead. Do not copy it.
- Pin tool versions: Python 3.13 with uv, Node 22 LTS, native PostgreSQL 18 locally (no Docker needed; CI uses a `postgres:18` service). Create `.python-version` containing `3.13`. Write `.env.example` with every variable from 02 section 7, local-ready: it runs the app with no keys (`AI_PROVIDER=claude_cli`), and optional keys are empty.
- The landing page can be a static page in `apps/web/public/` or a tiny separate route; the waitlist route logs each entry (deduplicated in memory) and adds it to the Resend audience when `RESEND_API_KEY` is set. There is no waitlist table in Phase 1.
- WF-004 creates the root scripts named in the WF-004 ticket (`setup`, `start`, `dev`, `test`, `lint`, `format`, `gen:api`, `gen:shared`, `test:api`, `test:web`, `test:e2e`, `test:e2e:smoke`, `test:kit`, `evals`, `db:init`, `doctor`, `smoke:live`), as node scripts that run on Windows and Linux. WF-007 rewrites the placeholder `.github/workflows/ci.yml`: it keeps the always-running job named exactly `ci` and its "Autopilot tests" step.
- Owner verification pending: WF-001 (trademark opinion, domain, Apple enrollment, App Store name), WF-003 (the interviews, the price test and the signed decision) and the WF-002 Done criterion "page live on the production domain" (it needs the domain and the Cloudflare Pages account, `HUMAN_TASKS.md`).

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Domain, support email and name checks (WF-001): see the rows in `HUMAN_TASKS.md`.
- Run the 10 interviews and the price test with the kit from WF-003 (`HUMAN_TASKS.md`).
- Branch protection on `main`: see `HUMAN_TASKS.md` (do it before the autopilot starts).
- `pgpass.conf` so `npm run db:init` can reach PostgreSQL 18 as `postgres` (`HUMAN_TASKS.md`).

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P01: Repository foundation, CI and landing page` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
