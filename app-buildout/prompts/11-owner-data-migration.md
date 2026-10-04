# Prompt 11: Import the owner's existing Trip Planner data

Phase 1 build, step 11 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Build the one-off importer that moves the owner's existing trips from the old Trip Planner database into Hermi accounts, with a dry run and a report.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-040 | Migrate the owner's existing data |
| WF-133 | Demo seed, sample trips and Discover |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/03-database-schema.md` (legacy import mapping)
- `app-buildout/phase-1-launch/02-architecture.md` (14.3)
- `app-buildout/phase-1-launch/09-build-roadmap.md` (WF-040)

## Notes

- Build and test it against a fixture dump. Running it on the real data is the owner's step.
- Owner verification pending: WF-040 (the owner's real data import and both owners claiming it through the emailed one-time link).
- `hermi seed --demo` starts here (WF-133); later ship sessions extend it.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Back up the old Trip Planner database, then run `hermi import-legacy --source-db <url> --primary-email <email> --partner-email <email>` as a dry run and then for real against staging (a direct database copy, no export file). Both owners claim their data through the emailed one-time link (`POST /me/legacy-claim`).

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P11: Import the owner's existing Trip Planner data` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
