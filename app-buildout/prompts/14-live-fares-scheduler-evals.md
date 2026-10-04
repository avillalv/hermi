# Prompt 14: Scheduler, live fares, breakers and evals

Phase 1 build, step 14 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Add the scheduler and price-check jobs, the live flight provider behind a flag with a search cache, global circuit breakers and usage reconciliation, and the evals with run-cost measurement.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-051 | Scheduler and price-check jobs |
| WF-052 | Live flight provider and search cache |
| WF-056 | Global breakers and usage reconciliation |
| WF-057 | Evals and run-cost measurement |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/02-architecture.md` (5.2 scheduler)
- `app-buildout/phase-1-launch/06-ai-agents-spec.md` (evals)
- `app-buildout/context/business-plan/06-database-and-data-integrations.md` (SerpApi risk)

## Notes

- Live fares stay behind `serpapi_live_fares` and default off, because of the legal risk noted in the context files.
- WF-057 runs live only with `EVALS_LIVE=1`, `--max-usd` and `--provider`; the numbers are certified only on `anthropic_api`.
- Owner verification pending: WF-057 (the 50 run cost measurement on a real key across at least 10 routes, p95 under $0.80).

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Decide whether to enable SerpApi on staging, and if so put `SERPAPI_API_KEY` in `.env` (see `HUMAN_TASKS.md`).
- Run the 50 run eval on at least 10 routes with `EVALS_LIVE=1 npm run evals -- --provider anthropic_api --max-usd <cap>` (`HUMAN_TASKS.md` row 21) and record the p95 cost (it must be under $0.80).

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P14: Scheduler, live fares, breakers and evals` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
