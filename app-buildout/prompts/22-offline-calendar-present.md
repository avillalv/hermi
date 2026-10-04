# Prompt 22: Offline, calendar feed, presentation and calendar polling

Phase 1 build, step 22 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Add offline reading and the edit queue, the calendar subscription feed, presentation mode with the read-only share view and PDF export, and opt-in calendar polling with change preview.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-088 | Offline reading |
| WF-089 | Offline edit queue |
| WF-090 | Calendar subscription feed |
| WF-091 | Presentation mode, read-only share view and PDF export |
| WF-123 | Keep checking this calendar: opt-in polling and change preview |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/01-product-spec.md` (offline, calendar, present)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (sections 6.19, 6.30, 6.31 and 6.33)
- `app-buildout/phase-1-launch/02-architecture.md` (5.4, 5.5)
- `app-buildout/phase-1-launch/README.md` (settled values: polling every 6 hours)
- `app-buildout/phase-1-launch/design/DESIGN-LANGUAGE.md` and `app-buildout/phase-1-launch/design/components.html` (rules and component classes for the screens this prompt adds)

## Notes

- Calendar tokens and feed URLs are secrets: never log them.
- Owner verification pending: WF-088 and WF-089 (a full trip browsable in airplane mode on a device on Free and Plus, and queued edits syncing on reconnect and surviving an app restart on a device).

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P22: Offline, calendar feed, presentation and calendar polling` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
