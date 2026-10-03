# Prompt 02: Port reusable code from the old Trip Planner

Phase 1 build, step 2 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Bring over the modules the architecture marks as reuse or adapt (providers, fare logic, itinerary and lodging logic, evidence rules, design tokens), adapted to the new layout, with their tests. Port the token plumbing and names only; every value comes from 05 section 2 (the Hermi palette), never from the old repo's `index.css`.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-005 | Port reusable modules |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/02-architecture.md` (section 14, mapping the existing code)
- `app-buildout/phase-1-launch/09-build-roadmap.md` (WF-005)
- `app-buildout/phase-1-launch/design/tokens.css` (the token names and values to port; it mirrors 05 section 2)

## Notes

- The base code is the Trip Planner repository, https://github.com/avillalv/trip-planner (backend/ and frontend/). It should already be cloned read-only at `.reference/trip-planner/` (see `00-orchestrator.md`, "Base code"). Port from it with `git log`/blame available for context; never push to it. If it cannot be cloned, write the modules fresh from the specs and note that in PROGRESS.md.
- Read `knowledge/trip-planner-base.md` first: what to reuse, adapt and drop, and where each piece lives.
- Never port the Claude Code CLI runner, the MCP bridge, APScheduler, passcode auth or Windows scripts.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- If the session cannot clone the Trip Planner repository (it is private), start the build session with both `hermi` and `trip-planner` selected, or attach `trip-planner` read-only.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P02: Port reusable code from the old Trip Planner` is merged into `main`.
