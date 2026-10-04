# Prompt 04: Database foundation and schemas

Phase 1 build, step 4 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Set up Alembic and the database roles, and land `0001` to `0015` of 03 section 10: every Phase 1 table, type, function, policy and seed in dependency order, exactly as the Phase 1 schema specifies.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-011 | Migration framework and database roles |
| WF-012 | Identity and trips schema |
| WF-022 | Billing and revenue schema |
| WF-021 | Planning schema |
| WF-020 | Operations schema and seed data |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/03-database-schema.md` (all of it)
- `.claude/rules/database-migrations.md`

## Notes

- Load the SQL through Alembic migrations in the order of 03 section 10, one linear chain. Each ticket takes one contiguous range, in ticket order: WF-011 `0001`; WF-012 `0002` to `0004`; WF-022 `0005` to `0008`; WF-021 `0009` to `0011`; WF-020 `0012` to `0015`. A ticket may run as sub-steps (for example `WF-022.1` for `0005` and `0006`, `WF-022.2` for `0007` and `0008`).
- Tests run on native PostgreSQL 18 (CI: the `postgres:18` service) and connect as `hermi_api_login`, never as `hermi_app` (a group role) or the owner. Roles come from `npm run db:init`, not from a migration; migrations log in as `hermi_migrate_login` and never `CREATE ROLE`.
- Never let two migrations share a parent: this prompt creates a linear chain.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P04: Database foundation and schemas` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
