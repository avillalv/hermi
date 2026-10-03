# Prompt 03: Staging and production environments

Phase 1 build, step 3 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Describe the hosted environments as code: Render blueprint, Cloudflare rules, deploy workflows for staging and production with migrations as a pre-deploy step, and a restore drill script.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-009 | Render and Cloudflare environments and deploy workflows |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/02-architecture.md` (sections 9 to 12)
- `app-buildout/context/business-plan/05-infrastructure.md`

## Notes

- Everything that needs an account (Render, Cloudflare, Supabase, domains) is written as configuration and documented steps. Deploy workflows must skip cleanly with a clear message when secrets are absent, so CI stays green.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create Render, Cloudflare and Supabase accounts and add their secrets to GitHub Actions and Render as listed in `.env.example`.
- Run the first staging deploy and confirm `/health/ready`.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P03: Staging and production environments` is merged into `main`.
