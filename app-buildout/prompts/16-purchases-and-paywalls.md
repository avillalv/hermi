# Prompt 16: RevenueCat, credit grants, Trip Pass and paywalls

Phase 1 build, step 16 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Wire RevenueCat webhooks and reconciliation, credit grants and refund reversals, Trip Pass binding, the paywall logic and screens, and a sandbox purchase harness.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-063 | RevenueCat webhook and reconcile |
| WF-064 | Credit grants and refund reversal |
| WF-065 | Trip Pass binding |
| WF-066 | Paywall logic and screens |
| WF-076 | Sandbox purchase harness |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/07-monetization-spec.md`
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (section 8 paywalls and section 6.26 credits and subscription)
- `app-buildout/phase-1-launch/04-api-spec.md` (billing, webhooks)
- `app-buildout/phase-1-launch/design/screens/07-paywall.html` (the paywall screen)

## Notes

- Phase 1 has no web purchases: the web paywall says "Upgrade in the iOS app". Webhook handling is idempotent through `webhook_events`.
- Tests use recorded RevenueCat webhook payloads.
- WF-063 runs as sub-steps: `WF-063.1` webhook and `WF-063.2` reconcile.
- Skip Xcode and pod steps locally; iOS builds run on GitHub macOS runners (`knowledge/ios-builds-on-ci.md`).
- Owner verification pending: WF-076 (each product purchased in the sandbox unlocks the right entitlement within seconds against staging, and the product metadata entered in App Store Connect; both need a device and the owner's accounts).
- The plan sets `gate: month-3`.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create the App Store Connect products (Plus monthly and annual, Trip Pass, three credit packs) and the RevenueCat project, and add its keys.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P16: RevenueCat, credit grants, Trip Pass and paywalls` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
