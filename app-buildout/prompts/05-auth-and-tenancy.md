# Prompt 05: Sign-in, tenancy and row-level security

Phase 1 build, step 5 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Verify Supabase JWTs, provision users through `bootstrap_user`, build the tenant-scoped data access layer and `require_trip`, enable row-level security, and prove no user can read another user's data.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-013 | JWT verification and user provisioning |
| WF-014 | Tenant-scoped data access layer |
| WF-015 | Row-level security |
| WF-016 | Cross-tenant leak tests |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/04-api-spec.md` (sections 1 and 5.1)
- `app-buildout/phase-1-launch/03-database-schema.md` (section 6, security)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (tenant isolation tests)
- `app-buildout/context/business-plan/04-users-and-accounts.md`

## Notes

- Tests use locally signed JWTs with a test JWKS, so no Supabase account is needed to pass CI.
- The cross-tenant leak test must hit every route that exists, and must be written so new routes are picked up automatically.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create the Supabase project, enable Apple, Google and email-code sign-in, and add its keys.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P05: Sign-in, tenancy and row-level security` is merged into `main`.
