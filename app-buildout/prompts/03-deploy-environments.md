# Prompt 03: Staging and production environments

Phase 1 build, step 3 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Describe the hosted environments as code: Render blueprint, Cloudflare rules, deploy workflows for staging and production with migrations as a pre-deploy step, and point-in-time recovery (PITR) set in `render.yaml`. The restore drill is WF-039 in prompt 10, not here.

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

- Everything that needs an account (Render, Cloudflare, Supabase, domains) is written as configuration and documented steps. Deploy workflows must skip cleanly with a clear message when secrets are absent, so CI stays green. `infra/render/render.yaml` pins `AI_PROVIDER=anthropic_api`, and deploy jobs gate on repository variables.
- Owner verification pending: WF-009 (the Render and Cloudflare accounts, and the criteria that need them: a merge to `main` reaches staging with migrations applied in under 10 minutes, production deploy needs approval, secrets live only in platform env groups, and separate Anthropic workspace keys for staging and production).

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create the Render and Cloudflare accounts and add the deploy secrets to GitHub Actions and the Render env groups as listed in `.env.example` and set the repository variable that turns deploys on (`HUMAN_TASKS.md`, Render and Cloudflare row). Supabase is optional here (its keys go in `.env` for local sign-in).
- Run the first staging deploy and check the WF-009 criteria above (`HUMAN_TASKS.md`, same Render and Cloudflare row).

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P03: Staging and production environments` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
