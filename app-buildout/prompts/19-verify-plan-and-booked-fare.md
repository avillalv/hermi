# Prompt 19: Verify this plan and the booked-fare drop alert

Phase 1 build, step 19 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Ship "Verify this plan" (schema, endpoints, item checks, verdicts, credit settlement and screens) and the booked-fare drop alert.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-116 | Verify this plan: schema, endpoints and reading a pasted plan |
| WF-117 | Verify this plan: item checks, verdicts and credit settlement |
| WF-118 | Verify this plan: screens |
| WF-075 | Booked-fare drop alert |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/06-ai-agents-spec.md` (5.11 verify_plan, 5.12 recheck)
- `app-buildout/phase-1-launch/04-api-spec.md` (5.30)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (6.38)
- `app-buildout/phase-1-launch/README.md` (settled values)
- `app-buildout/context/competitive-analysis/win-plan.md`
- `app-buildout/phase-1-launch/design/components.html` and `app-buildout/phase-1-launch/design/screens/05-fare-detail.html` (component classes for the verify screens, fare detail for the booked fare)

## Notes

- Verdicts are decided in code; a green or amber item must carry a cited page and date.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P19: Verify this plan and the booked-fare drop alert` is merged into `main`.
