# Prompt 09: Itinerary, places, map, stays and notes

Phase 1 build, step 9 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Build the day-by-day itinerary with calendar and ICS export, places search and map, the stays shortlist with hearts and compare, and notes with sources.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-032 | Itinerary, calendar view and ICS export |
| WF-033 | Places and map |
| WF-034 | Lodging, hearts and compare |
| WF-035 | Notes with sources |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/01-product-spec.md` (plan, places, stays, notes)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (plan, stays)
- `app-buildout/phase-1-launch/04-api-spec.md` (itinerary, places, lodging, notes)
- `app-buildout/phase-1-launch/design/screens/04-plan-day.html` and `app-buildout/phase-1-launch/design/screens/06-stays-vote.html` (the plan day and stays vote screens)

## Notes

- Never fetch Airbnb, Vrbo or Booking.com pages, including for previews. Pasted links are stored exactly as pasted.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create a Geoapify account and key.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P09: Itinerary, places, map, stays and notes` is merged into `main`.
