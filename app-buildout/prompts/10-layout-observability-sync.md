# Prompt 10: Responsive layout, observability and sync indicator

Phase 1 build, step 10 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Finish responsive layout with empty and error states, add Sentry and structured logs, the PostHog base, backups and a restore drill, and the sync indicator.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-036 | Responsive layout, empty and error states |
| WF-037 | Sentry and structured logs |
| WF-038 | PostHog analytics base |
| WF-039 | Backups and restore drill |
| WF-125 | "Synced N seconds ago" indicator |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (layout, states; sections 5.2, 5.3, 4.15 to 4.18 and 6.41)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (observability)
- `app-buildout/phase-1-launch/02-architecture.md` (4.5 sync indicator)
- `app-buildout/phase-1-launch/design/DESIGN-LANGUAGE.md` (layout, sheets, tab bar, empty and loading states)

## Notes

- Analytics never include personal data: follow the event catalogue in 10 section 4.
- Owner verification pending: WF-039 (the restore drill on the real Render and R2 backups finishes within the 1 hour RTO, and the quarterly calendar entry exists). The build writes the drill script and `docs/runbooks/restore.md`.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create Sentry and PostHog projects and put `SENTRY_DSN`, `VITE_SENTRY_DSN`, `POSTHOG_KEY`, `VITE_POSTHOG_KEY` and `POSTHOG_HOST` in `.env` (see `HUMAN_TASKS.md`).
- Run `infra/scripts/restore-drill.sh` against the real Render and R2 backups, confirm the restore finishes within the 1 hour RTO, record the result in `docs/runbooks/restore.md`, and add the quarterly drill to your calendar.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P10: Responsive layout, observability and sync indicator` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
