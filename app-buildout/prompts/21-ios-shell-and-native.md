# Prompt 21: iOS app shell and native features

Phase 1 build, step 21 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Wrap the web app with Capacitor (bundled), add native plugins, Sign in with Apple, App Attest, in-app purchases, universal links for invites, APNs push and notification preferences.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-080 | Capacitor shell, signing and CI |
| WF-081 | Native plugins |
| WF-082 | Sign in with Apple native |
| WF-083 | App Attest and device trust |
| WF-084 | Purchases in the app |
| WF-085 | Universal links and invite flow |
| WF-086 | APNs, devices and push |
| WF-087 | Notification preferences UI |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/02-architecture.md` (4.4 web and iOS differences)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (sections 5.2, 6.1, 6.27, 6.29 and 9.3, and any other section named by its tickets' `Kit:` lines)
- `app-buildout/phase-1-launch/design/README.md`
- `app-buildout/context/business-plan/07-local-to-app-store.md`
- `app-buildout/phase-1-launch/design/DESIGN-LANGUAGE.md` (safe areas, tab bar, sheets)

## Notes

- Code, config, fastlane lanes and the CI workflow are written here; builds run on a GitHub macOS runner (see `knowledge/ios-builds-on-ci.md`). Skip Xcode and pod steps locally, verify the web build still passes, and record each device step in `HUMAN_TASKS.md`.
- Owner verification pending: WF-080 to WF-087 (everything that needs the owner's iPhone, Apple Developer account or signing: the app launching on a device against staging, a signed build from CI, Sign in with Apple on device, App Attest on a real device, sandbox purchases and Restore on a second device, a universal link from Messages, and a push arriving on a device within 30 minutes of the check).
- The plan sets `gate: month-4`.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Enroll in the Apple Developer Program, create the app ID, capabilities and certificates.
- Install the build from the GitHub macOS runner on your iPhone, run it, and test Sign in with Apple, purchases in the sandbox and push (device checks only; the build runs on the runner, see `knowledge/ios-builds-on-ci.md`).

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P21: iOS app shell and native features` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
