# Prompt 07: Entitlements, travelers, invites and roles

Phase 1 build, step 7 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Build the entitlement resolver and limit enforcement for Free, Plus and Trip Pass, travelers, invites and roles with the Free one-collaborator rule, share links, the activity feed, and rate limits.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-023 | Entitlement resolver and limit enforcement |
| WF-024 | People (travelers) |
| WF-025 | Invites, roles and share links |
| WF-026 | Free owners invite 1 collaborator |
| WF-027 | Activity log and feed |
| WF-028 | Rate limits and abuse controls |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/07-monetization-spec.md` (entitlement resolution)
- `app-buildout/phase-1-launch/01-product-spec.md` (collaboration)
- `app-buildout/phase-1-launch/04-api-spec.md` (members, invites, share links)
- `app-buildout/phase-1-launch/README.md` (settled values)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` sections 6.8, 6.21 and 6.24, and `app-buildout/phase-1-launch/design/README.md`

## Notes

- Limits come from the `plans` seed, never from constants scattered in code.
- The plan sets `gate: month-1`: the month 1 gate (after prompt 06) runs in this prompt's ship session.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P07: Entitlements, travelers, invites and roles` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
