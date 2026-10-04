# Prompt 15: Admin console foundation

Phase 1 build, step 15 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Build the admin console foundation: admin sign-in with roles and 2FA (`ADMIN_AUTH_MODE=cf_access|dev` and the first admin through `hermi admin-grant <email>`), the audit log, kill switches and breakers, and credits and AI spend views.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-058 | Admin foundation |
| WF-059 | Audit log service and screen |
| WF-060 | Admin kill switches and breakers |
| WF-061 | Admin credits and AI spend |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/08-admin-control-center.md`
- `app-buildout/phase-1-launch/04-api-spec.md` (admin routes)

## Notes

- Every admin action writes an audit row with before and after. Admin routes have their own role checks and tests.

- WF-058 runs as sub-steps: `WF-058.1` identity and `WF-058.2` 2FA. 08 is the authority for the admin sign-in. `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD` come from the environment; local and `ci` use a fake-Access signer.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Decide the admin access method (Cloudflare Access or another SSO) and set it up, then put `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD` in `.env` and the platform env groups.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P15: Admin console foundation` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
