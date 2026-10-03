# Prompt 24: Performance polish, analytics, status, tests and TestFlight

Phase 1 build, step 24 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Polish performance and empty states, add every Phase 1 analytics event, uptime alerts and the public status summary with the in-app banner, Maestro tests and the TestFlight pipeline, the sandbox purchase matrix, and the beta operations report.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-097 | Performance and empty-state polish |
| WF-098 | Analytics events for Phase 1 |
| WF-100 | Uptime, alerts and status page |
| WF-126 | Public status summary and in-app status banner |
| WF-101 | Maestro tests and TestFlight pipeline |
| WF-102 | Sandbox purchase matrix |
| WF-103 | Beta operations and metrics report |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/10-quality-security-launch.md`
- `app-buildout/phase-1-launch/05-ui-ux-spec.md`
- `app-buildout/phase-1-launch/09-build-roadmap.md` (month 5 exit)
- `app-buildout/phase-1-launch/design/` (the whole kit, starting with its README.md; compare each built screen with its PNG in `app-buildout/phase-1-launch/design/png/`)

## Notes

- Performance targets and crash-free targets are in 10; measure them, do not assume them.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Invite 30 TestFlight beta testers and run the beta for at least two weeks.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P24: Performance polish, analytics, status, tests and TestFlight` is merged into `main`.
