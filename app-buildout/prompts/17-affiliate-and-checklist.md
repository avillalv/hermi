# Prompt 17: Affiliate redirect, link builders, conversions and checklist

Phase 1 build, step 17 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Build the outbound redirect with click logging, the link builders with disclosure and placements for Travelpayouts, Stay22 and Viator, the nightly conversion import, and the Before you go checklist.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-067 | Outbound API and redirect |
| WF-068 | Link builders, disclosure and placements |
| WF-069 | Conversion import |
| WF-070 | Checklist "Before you go" |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/context/business-plan/08-affiliate-revenue.md`
- `app-buildout/phase-1-launch/07-monetization-spec.md` (affiliate)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (sections 4.13 and 6.20: affiliate cards, checklist)
- `app-buildout/phase-1-launch/design/components.html` and `app-buildout/phase-1-launch/design/screens/05-fare-detail.html` (provider rows and the disclosure line)

## Notes

- Every partner button shows "We earn a commission if you book here." Never rank by commission. No open redirects: only stored templates.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Apply to Stay22 and the Viator partner program and add their IDs.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P17: Affiliate redirect, link builders, conversions and checklist` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
