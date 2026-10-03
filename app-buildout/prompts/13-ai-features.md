# Prompt 13: Claude features, agent loop, research, evidence and guest mode

Phase 1 build, step 13 of 28. Follow `app-buildout/prompts/00-orchestrator.md` for how to run this prompt (branch, models, checks, PR, merge, progress).

## Goal

Ship the Claude client and single-call features (explain, drafts, packing list), the agent loop with the evidence rules, research with the shared cache, agent runs with the taster, AI consent and reports, evidence labels with freshness and recheck, and guest mode.

## Tickets, in this order

Each ticket's description, dependencies, acceptance criteria, files and tests are in `app-buildout/phase-1-launch/09-build-roadmap.md`. The acceptance criteria are the definition of done.

| Ticket | Title |
|---|---|
| WF-048 | Claude client and single-call features |
| WF-049 | Agent loop |
| WF-050 | Research action and shared cache |
| WF-053 | Agent runs API, screen and taster |
| WF-054 | AI consent, labels and reports |
| WF-055 | Evidence labels |
| WF-120 | Evidence freshness and one-tap recheck |
| WF-062 | Guest mode and claim |

## Read before starting

- `app-buildout/prompts/PROGRESS.md` (what is already built, decisions made)
- `app-buildout/phase-1-launch/06-ai-agents-spec.md` (all features)
- `app-buildout/phase-1-launch/01-product-spec.md` (AI features)
- `app-buildout/phase-1-launch/05-ui-ux-spec.md` (AI screens)
- `app-buildout/phase-1-launch/04-api-spec.md` (AI endpoints)
- `app-buildout/phase-1-launch/design/screens/08-ai-actions.html` and `app-buildout/phase-1-launch/design/screens/09-agent-run.html` (the AI actions and agent run screens)

## Notes

- Models: `claude-haiku-4-5` for short answers and extraction, `claude-sonnet-5-5` for drafts, research and agents, exactly as 06 says. Read the claude-api skill before writing Anthropic SDK code.
- Every run has a dollar hard stop and turn, search and fetch caps. Blocked domains include Airbnb, Vrbo and Booking.com.
- CI uses a fake client; a manual `npm run evals` uses the real API when a key is present.

## Owner-only steps

Add these to `app-buildout/prompts/HUMAN_TASKS.md` (do not block on them; use fakes, fixtures and flags until they are done):

- Create an Anthropic API key with a monthly spend limit and add it to staging.

## Done when

- Every ticket above meets its acceptance criteria, with the tests the ticket names.
- `npm run lint` and `npm test` pass locally and in CI (and `npm run gen:api` is committed when routes changed, and the e2e smoke test passes when a user flow changed).
- No secrets, no em dashes in UI copy, no fetching of Airbnb, Vrbo or Booking.com pages.
- `PROGRESS.md` and `HUMAN_TASKS.md` are updated.
- The pull request `Phase 1 / P13: Claude features, agent loop, research, evidence and guest mode` is merged into `main`.
