# Prompt 06: Web app platform, sign-in and trips

Phase 1 build, step 6 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Stand up the React web app with the design tokens and logo, the generated API client with bearer auth, the sign-in and first-trip wizard, and the trips module end to end.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-017 | Web API client, environment config and bearer auth |
| WF-130 | Kit port, shell and kit tests |
| WF-018 | Sign-in and first-trip wizard |
| WF-019 | Trips module |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (design system, navigation, sign-in, trips home, create trip)
- `app-buildout/phase-1-launch/04-api-spec.md` (trips)
- `app-buildout/phase-1-launch/01-product-spec.md` (accounts and trips features)
- `app-buildout/brand/BRAND.md`
- `app-buildout/phase-1-launch/design/README.md`, `app-buildout/phase-1-launch/design/DESIGN-LANGUAGE.md`, `app-buildout/phase-1-launch/design/components.html`, `app-buildout/phase-1-launch/design/screens/01-welcome.html`, `app-buildout/phase-1-launch/design/screens/02-trips-home.html` and `app-buildout/phase-1-launch/design/screens/03-trip-overview.html` (the visual kit: rules, component classes, and the welcome, trips home and trip overview screens)

## Notes

- Use the brand files in `app-buildout/brand/`: `brand/hermi-logo.svg` (light lockup), `brand/hermi-logo-dark.svg` (dark lockup) and `brand/hermi-mark.svg` (favicon and avatars). Port the token plumbing and names only; every value comes from 05 section 2 (the Hermi palette), never from the old repo's `index.css`. Copy rules: sentence case, plain verbs, no em dashes.
- Add a Playwright smoke test for sign-in (with a test login) and creating a trip.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P06: Web app platform, sign-in and trips` is merged into `main`.
