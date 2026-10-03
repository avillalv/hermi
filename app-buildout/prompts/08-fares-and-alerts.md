# Prompt 08: Currency, cached fares and price alerts

Phase 1 build, step 8 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Add currency and FX, the cached fares module on Travelpayouts, price history, and price alerts on cached fares.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-029 | Currency and FX |
| WF-030 | Cached fares module |
| WF-031 | Price alerts on cached fares |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/01-product-spec.md` (flights)
- `app-buildout/phase-1-launch/04-api-spec.md` (flights)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (flights screens)
- `app-buildout/context/business-plan/06-database-and-data-integrations.md` (providers)
- `app-buildout/phase-1-launch/design/screens/05-fare-detail.html` (the fare detail screen)

## Notes

- Provider calls go through the provider interface and the `provider_calls` ledger. Tests use recorded fixtures, never live APIs.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create a Travelpayouts account, get the API token and affiliate marker.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P08: Currency, cached fares and price alerts` is merged into `main`.
