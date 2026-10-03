# Prompt 01: Repository foundation, CI and landing page

Phase 1 build, step 1 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Create the Hermi monorepo skeleton exactly as the architecture tree describes, with working lint, test and format commands, CI, Docker for local Postgres, health endpoints, security scanning, the project CLAUDE.md and rules, and a static landing page with a waitlist form. WF-001 and WF-003 are business tasks: produce their documents and checklists, and record the parts only the owner can do.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-001 | Name, domain and email |
| WF-002 | Landing page and waitlist |
| WF-003 | Interview kit, price test and terms checklist |
| WF-004 | Scaffold the repository |
| WF-006 | Typed configuration and environments |
| WF-007 | CI pipeline |
| WF-008 | Docker image, compose and health endpoints |
| WF-010 | Security scanning workflows |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/README.md`
- `app-buildout/phase-1-launch/02-architecture.md` (sections 1, 2, 7, 9 to 11)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (section 1, testing layers)
- `app-buildout/README.md` (non-negotiable rules)
- `app-buildout/context/business-plan/01-business-plan.md` (M0 validate)
- `app-buildout/phase-1-launch/design/README.md`, `app-buildout/phase-1-launch/design/tokens.css` and `app-buildout/phase-1-launch/design/screens/01-welcome.html` (the brand look for the landing page)

## Notes

- `CLAUDE.md` already exists, set up by context-kit-v2 (`/context-init`) with a `## Context layout` section. Extend it, do not replace it, and keep it under 200 lines: add the verified Commands section once the scaffold's commands actually run. Put conditional knowledge in `.claude/rules/` with narrow `paths` frontmatter (database migrations for `apps/api/hermi/migrations/**` and `apps/api/hermi/**/models*.py`; frontend copy and styling for `apps/web/src/**`; AI and worker code for `apps/worker/**` and `apps/api/hermi/modules/ai/**`), reference material in `knowledge/` with a row in `knowledge/INDEX.md`, and repeatable procedures as skills in `.claude/skills/`.
- The architecture tree mentions `docs/spec/`: the spec stays in `app-buildout/` at the repo root instead. Do not copy it.
- Pin tool versions: Python 3.13 with uv, Node 22 LTS, PostgreSQL 18 in Docker. Write `.env.example` with every variable from 02 section 7, values empty.
- The landing page can be a static page in `apps/web/public/` or a tiny separate route; the waitlist form posts to a stub endpoint that stores emails in a table later (store to a log until WF-012 exists).

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Buy or confirm the domain and create the support email (WF-001).
- Run the 10 interviews and the price test with the kit from WF-003.
- Create the GitHub repository settings: branch protection on main that allows the orchestrator to merge after CI passes.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P01: Repository foundation, CI and landing page` is merged into `main`.
