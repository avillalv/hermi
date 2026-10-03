# Prompt 20: Admin users, subscriptions, overview and affiliate revenue

Phase 1 build, step 20 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Add the admin users screens, subscriptions and store transactions with webhook replay, the overview dashboard with metric rollups, and affiliate revenue screens.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-077 | Admin users: read, search, reveal |
| WF-078 | Admin subscriptions, store transactions and webhook replay |
| WF-079 | Admin overview and metric rollups |
| WF-099 | Admin affiliate revenue screens |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/08-admin-control-center.md`

## Notes

- No raw personal data in lists; reveal actions are audited.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P20: Admin users, subscriptions, overview and affiliate revenue` is merged into `main`.
