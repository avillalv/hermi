# Prompt 28: Store listing, review notes, submission and launch

Phase 1 build, step 28 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Prepare the App Store listing and privacy labels, the review notes and demo account, and everything for submission and launch; then run the final Phase 1 completion check. WF-122 is built; only WF-129 (status page polish) is on the cut list: do it only if there is room.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-104 | Store listing and privacy labels |
| WF-111 | Review notes and demo account |
| WF-115 | Submission, review handling and launch |
| WF-129 | Status page polish |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (App Store submission)
- `app-buildout/context/business-plan/07-local-to-app-store.md`
- `app-buildout/phase-1-launch/09-build-roadmap.md` (month 6 exit)

## Notes

- Write the listing text, screenshots plan, privacy label answers and review notes as files in `docs/store/` (as WF-104 and WF-111 say), and keep `docs/launch/` for the launch plan (WF-115). Submitting is the owner's step.
- Owner verification pending: WF-104 (App Store Connect fields, screenshots from real builds and privacy labels entered), WF-111 (a fresh device signs in with the demo account against production) and WF-115 (submission, App Review, approval, and the first 72 hours of crash-free and error-rate numbers).
- Finish with the Phase 1 completion check in `00-orchestrator.md` and write `docs/gates/phase-1-complete.md`.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Take the screenshots from the GitHub macOS runner build (see `knowledge/ios-builds-on-ci.md`) on your iPhone, fill in App Store Connect, submit for review, and respond to App Review.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P28: Store listing, review notes, submission and launch` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
