# Prompt 23: Account deletion, export, settings, onboarding and accessibility

Phase 1 build, step 23 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Ship in-app account deletion, data export, settings with consents and legal pages, the "Coming from TripIt or Wanderlog?" onboarding question, and the accessibility, i18n base and privacy manifest.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-092 | Account deletion |
| WF-093 | Data export |
| WF-094 | Settings, consents and legal pages |
| WF-095 | Onboarding: switching question |
| WF-096 | Accessibility, i18n base and privacy manifest |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/01-product-spec.md`
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (sections 6.25 and 6.28 settings, account and data screens, 6.1 onboarding, and 2.3 and 9 accessibility)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (privacy and compliance)
- `app-buildout/phase-1-launch/design/DESIGN-LANGUAGE.md` and `app-buildout/phase-1-launch/design/components.html` (accessibility rules, and component classes for settings and onboarding)

## Notes

- Legal pages are drafts marked for lawyer review.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Have the privacy policy and terms reviewed by a lawyer.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P23: Account deletion, export, settings, onboarding and accessibility` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
