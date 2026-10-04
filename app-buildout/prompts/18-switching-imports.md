# Prompt 18: Switching imports and the first-import Trip Pass

Phase 1 build, step 18 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Import trips from calendar files and feeds and from pasted confirmations, with rival-named import entries (TripIt, Tripsy, Wanderlog) and pasted places, and grant the first-import Trip Pass under the settled rules. WF-122 (Google Maps export file) is built; only WF-129 is on the cut list.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-071 | Switching import: ICS file |
| WF-072 | Switching import: ICS feed |
| WF-073 | Switching import: pasted confirmations |
| WF-074 | First-import Trip Pass reward |
| WF-121 | Import entries named for TripIt, Tripsy and Wanderlog, and pasted places |
| WF-122 | Google Maps export file import |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/01-product-spec.md` (imports)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (6.30 import screens)
- `app-buildout/phase-1-launch/04-api-spec.md` (5.26 imports)
- `app-buildout/phase-1-launch/02-architecture.md` (5.4 import pipeline and SSRF guard)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (import security)
- `app-buildout/context/competitive-analysis/win-plan.md`

## Notes

- Write the hostile inputs first: the ICS fuzz corpus, the SSRF table and the PII corpus are the specification.
- Google Maps links are never opened; only exported files and pasted place names import.
- Owner verification pending: WF-121 (the rival help-page check dated in `docs/import-sources.md` needs a person reading the live rival pages).

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P18: Switching imports and the first-import Trip Pass` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
