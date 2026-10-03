# Prompt 28: Store listing, review notes, submission and launch

Phase 1 build, step 28 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Prepare the App Store listing and privacy labels, the review notes and demo account, and everything for submission and launch; then run the final Phase 1 completion check. WF-129 (status page polish) is on the cut list: do it only if there is room.

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

- Write the listing text, screenshots plan, privacy label answers and review notes as files in `docs/launch/`. Submitting is the owner's step.
- Finish with the Phase 1 completion check in `00-orchestrator.md` and write `docs/gates/phase-1-complete.md`.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Take the screenshots on a Mac, fill in App Store Connect, submit for review, and respond to App Review.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P28: Store listing, review notes, submission and launch` is merged into `main`.
