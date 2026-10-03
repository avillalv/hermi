# Prompt 04: Database foundation and schemas

Phase 1 build, step 4 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Set up Alembic, the database roles and every Phase 1 table, type, function, policy and seed in dependency order, exactly as the Phase 1 schema specifies.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-011 | Migration framework and database roles |
| WF-012 | Identity and trips schema |
| WF-020 | Operations schema and seed data |
| WF-021 | Planning schema |
| WF-022 | Billing and revenue schema |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/03-database-schema.md` (all of it)
- `.claude/rules/database-migrations.md`

## Notes

- Load the SQL through Alembic migrations, one migration per ticket, in the order of 03 section 10. Tests run against a real Postgres 18 (Docker), connecting as `hermi_app`, never as the owner role.
- Never let two migrations share a parent: this prompt creates a linear chain.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P04: Database foundation and schemas` is merged into `main`.
