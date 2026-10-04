# Prompt 27: Security review, load test, runbooks and the Verify release gate

Phase 1 build, step 27 of 28. Follow `app-buildout/prompts/AUTOPILOT.md` and `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (the driver merges).

## Goal

Run the security review and fix findings, load test and write the runbooks, and complete the evals and release gate for Verify this plan.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-110 | Security review and penetration test fixes |
| WF-112 | Load test and runbooks |
| WF-119 | Verify this plan: evals and release gate |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/10-quality-security-launch.md` (security, runbooks)
- `app-buildout/phase-1-launch/06-ai-agents-spec.md` (evals)

## Notes

- Use the security-review skill if it is available. Fix every high and medium finding in this prompt. The WF-110 review scope includes the `claude_cli` guard and the never-fetch constant `BLOCKED_HOSTS`.
- Tests and load runs use the native PostgreSQL 18 setup and the `.env` from `npm run setup`, with `AI_PROVIDER=fake`; no Docker is needed.
- Evals: live runs only with `EVALS_LIVE=1` and `--max-usd`, through `npm run evals` with `--provider`; results are certified only on `anthropic_api`, and CLI numbers are provisional.
- Owner verification pending: WF-110 (the optional external penetration test, if commissioned), WF-112 (each runbook exercised once against the real staging and production accounts) and WF-119 (the live eval run on a real key and the gate result recorded in the Month 6 review).

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Optionally commission an external penetration test.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P27: Security review, load test, runbooks and the Verify release gate` is ready with the `e2e` label and the `PROGRESS.md` row says Done; the driver merges it after `ci` passes.
