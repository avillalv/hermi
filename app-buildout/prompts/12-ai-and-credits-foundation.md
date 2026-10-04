# Prompt 12: AI schema, flags, metering, credits, ceilings, jobs and email

Phase 1 build, step 12 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Build the plumbing every AI feature needs: feature flags and kill switches, metering with price constants, the credit ledger with reserve and settle, spend ceilings and daily budgets, the job queue with worker lanes, and the notification and email service.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-041 | AI, credit and run schema |
| WF-042 | Feature flags and kill switches |
| WF-043 | AI metering and price constants |
| WF-044 | Credit ledger service |
| WF-045 | Spend ceilings and budget service |
| WF-046 | Job queue and worker lanes |
| WF-131 | AI provider seam |
| WF-047 | Notification service and email |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/06-ai-agents-spec.md` (metering, ceilings)
- `app-buildout/phase-1-launch/07-monetization-spec.md` (credits)
- `app-buildout/phase-1-launch/02-architecture.md` (5, 13)
- `app-buildout/phase-1-launch/README.md` (settled values)
- `app-buildout/context/business-plan/03-ai-features-and-costs.md`

## Notes

- No real Claude calls yet: use a fake Anthropic client in tests. Ceilings and credit prices come from seed data.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- None for this prompt.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P12: AI schema, flags, metering, credits, ceilings, jobs and email` is merged into `main`.
