# Phase 1 orchestrator

This file tells the orchestrating Claude Code session how to build all of Hermi Phase 1 by running
the prompts in this folder in order, one pull request per prompt, until Phase 1 is complete.

## Where things are

| Path | What it is |
|---|---|
| `app-buildout/README.md` | Shared decisions: tiers, credits, stack, table names, non-negotiable rules |
| `app-buildout/phase-1-launch/` | The Phase 1 specification (01 to 10). The source of truth for what to build. |
| `app-buildout/phase-1-launch/09-build-roadmap.md` | Every ticket (WF-001 to WF-129) with dependencies, acceptance criteria, files and tests |
| `app-buildout/context/` | Business plan and competitive analysis: the reasons behind decisions. Read when a spec says "why". |
| `app-buildout/brand/` | Logo files and brand guide |
| `app-buildout/phase-1-launch/design/` | Visual design kit: tokens, component classes, screen mockups and PNGs. Read its README before any UI work. |
| `app-buildout/prompts/01-*.md` to `28-*.md` | The build prompts, run in number order |
| `app-buildout/prompts/PROGRESS.md` | The build's memory: which prompts are done, decisions, notes. Update it in every PR. |
| `app-buildout/prompts/HUMAN_TASKS.md` | Steps only the owner can do (accounts, keys, Mac builds, App Store). Add to it; never block on it. |
| `app-buildout/prompts/DECISIONS.md` | Judgement calls made during the build, with the reason and how to reverse them |
| `app-buildout/phase-2-growth/`, `phase-3-scale/`, `reference-full-spec/` | Not part of this build. Do not implement anything from them. |
| `.reference/trip-planner/` | Read-only clone of the base code (see "Base code" below). Gitignored. |
| `CLAUDE.md`, `.claude/rules/`, `knowledge/`, `.claude/skills/`, `findings/` | The context-kit-v2 layout (see "Context system" below) |

The application code lives at the repository root in the layout from
`phase-1-launch/02-architecture.md` section 2 (`apps/`, `packages/`, `infra/`, `.github/`, `docs/`).
The spec stays in `app-buildout/`; do not copy it to `docs/spec/`.

Precedence when documents disagree: `app-buildout/README.md`, then `phase-1-launch/README.md`
(including its "Settled values"), then the topic spec (01 to 08, 10), then `09-build-roadmap.md`.

For how the UI looks, the token values in `phase-1-launch/05-ui-ux-spec.md` section 2 win, then `phase-1-launch/design/`, then the ASCII wireframes in 05 section 6. For what the UI does and says (behavior, states, copy, events), 05 wins.

## Base code: the Trip Planner repository

Hermi is built on the existing Trip Planner app, https://github.com/avillalv/trip-planner. It is
not part of this repository. At the start of every session, before any prompt:

1. If `.reference/trip-planner/` does not exist, clone it there read-only:
   `git clone --depth 50 https://github.com/avillalv/trip-planner .reference/trip-planner`
   (`.reference/` is in `.gitignore`). If the clone is refused because the repository is private,
   the session needs access to it: in Claude Code on the web, start the session with both
   `hermi` and `trip-planner` selected; otherwise ask the owner. If it still cannot be cloned,
   continue from the specs and note it in `PROGRESS.md`.
2. If it exists, `git -C .reference/trip-planner pull --ff-only` to pick up the latest.
3. Never commit to, push to, or edit files in `.reference/trip-planner/`. Copy what you port into
   the Hermi layout and adapt it there.

`knowledge/trip-planner-base.md` says what to reuse, adapt and drop, and
`phase-1-launch/02-architecture.md` section 14 maps every module.

## Context system (context-kit-v2)

This repository uses the context-kit-v2 plugin (enabled in `.claude/settings.json`): a three-tier
layout (`CLAUDE.md`, `.claude/rules/`, `knowledge/` and `.claude/skills/`), a lean ruleset injected
into every session and subagent, automatic skill capture, and graph tools. Use it to keep tokens low:

- **Where knowledge goes.** Never grow `CLAUDE.md` on your own; it is capped at 200 lines. Knowledge
  that applies to certain files goes in `.claude/rules/<topic>.md` with narrow `paths`; reference
  goes in `knowledge/` with a row in `knowledge/INDEX.md`; a procedure that repeats becomes a skill
  (skill capture writes it and reports one line).
- **Before reading widely,** locate first: `knowledge/INDEX.md`, then the spec section, then the code.
- **Before a pull request,** run `/blast-radius --diff` and check the downstream files are covered by
  tests.
- **Long investigations** record conclusions with `/finding`, so they survive compaction.
- **At each month gate,** run `/context-graph --code` and `/context-init only audit, do not propose
  moves yet`, and include both results in the gate file. Fix any rule whose `paths` match nothing.
- If the plugin is not active (`/context-init` is unknown), install it once with
  `/plugin marketplace add https://github.com/avillalv/context-kit-v2.git` then
  `/plugin install context-kit-v2@context-kit-v2`, and restart the session.

## Subagents

Defined in `.claude/agents/`:

| Agent | Model | Use for |
|---|---|---|
| `sonnet-researcher` | Sonnet | Read-only: spec lookups, reading the Trip Planner base, finding existing code. Returns conclusions, not file dumps. |
| `sonnet-coder` | Sonnet | Implements exactly one ticket, tests first, runs lint and tests, reports a diffstat and results. |
| `opus-reviewer` | Opus | Read-only adversarial review of a ticket's diff against its acceptance criteria and the rules. |

## Models

- **The orchestrator (this session) runs on Claude Opus 5.5.** It plans each prompt, makes judgement
  calls, reviews every diff against the acceptance criteria and the rules, and decides when a prompt is
  done.
- **All research and all coding go to subagents on Claude Sonnet 5.5** (the Agent tool with the Sonnet
  model). Research subagents read specs and existing code and report back conclusions. Coding
  subagents implement one ticket at a time, tests first.
- The orchestrator may make small fixes itself (a failing lint line, a PR description), but features,
  migrations and tests are written by Sonnet subagents and reviewed by the orchestrator.
- Inside the product, the models are fixed by the spec (`claude-haiku-4-5` and `claude-sonnet-5-5`);
  do not confuse the build models with the product's models.

## The loop (repeat until Phase 1 is complete)

1. **Find the next prompt.** Read `PROGRESS.md`. The next prompt is the lowest-numbered one not marked
   done. If a prompt is marked in progress, resume it: check its branch and open PR first.
2. **Sync.** `git checkout main && git pull`. Create the branch `phase1/pNN-<slug>` (the slug is the
   prompt file name without the number and extension).
3. **Plan (Opus).** Read the prompt file, then each ticket in `09-build-roadmap.md`, then the files
   the prompt lists under "Read before starting" (send long reads to a Sonnet research subagent and
   ask for a summary of what matters for these tickets). Check every ticket's dependencies are done.
   Write a short plan for the prompt at the top of `PROGRESS.md` under "Current prompt": tickets in
   order, files, tests, risks.
4. **Build (Sonnet), one ticket at a time, in the prompt's order.** For each ticket, give a Sonnet
   coding subagent: the ticket text, the relevant spec excerpts, the repository rules (`CLAUDE.md`,
   `.claude/rules/`), and the instruction to write the failing tests first, then the code, then run
   `npm run lint` and `npm test` and report the output. Never run two tickets that add database
   migrations at the same time. Independent tickets that touch different modules and add no
   migrations may run in parallel subagents.
5. **Review (Opus).** Read the diff for each ticket. Check it against the acceptance criteria, the
   security rules, the naming in `03-database-schema.md`, and the non-negotiable rules. Run the checks
   yourself. Send anything wrong back to a Sonnet subagent with specific instructions. Commit each
   ticket separately with the message `WF-0NN <title>`.
6. **Record.** Update `PROGRESS.md` (mark tickets done, note anything the next prompts must know),
   `HUMAN_TASKS.md` (owner-only steps from the prompt, plus anything discovered) and `DECISIONS.md`.
   Run `npm run gen:api` if routes changed and commit the generated types.
7. **Pull request.** Push the branch and open a pull request titled `Phase 1 / PNN: <prompt title>`
   with: the tickets done, how each was verified (paste the test summary), new owner tasks, decisions,
   and anything deferred. Use the `gh` CLI if it is installed and authenticated, otherwise the GitHub
   MCP tools.
8. **CI.** Wait for CI on the pull request. If it fails, find the root cause, fix it on the branch
   (through a Sonnet subagent for anything beyond a one-line fix), push, and wait again. Never skip,
   disable or weaken a test to get green. Three failed fix attempts on the same failure is a stop
   condition.
9. **Merge.** When CI is green, squash-merge the pull request into `main`, delete the branch, then
   `git checkout main && git pull`.
10. **Reset context.** Claude Code cannot run `/compact` on itself. Instead: keep the orchestrator's
    working memory small. After a merge, rely on `PROGRESS.md` rather than the conversation, give the
    next prompt's subagents fresh instructions, and let automatic context compaction handle the rest.
    If the session ends or is restarted, the kickoff prompt resumes from `PROGRESS.md`.
11. **Month gates.** After prompts 06, 11, 15, 20 and 24 (the ends of months 1 to 5 in
    `09-build-roadmap.md`), run that month's exit checklist and write the result to
    `docs/gates/month-N.md` in the next prompt's pull request. If the gate shows serious slippage, apply
    the cut list from `09-build-roadmap.md` section 4 and record it in `DECISIONS.md`.
12. **Continue** with the next prompt without waiting for the owner.

## Rules for every prompt

- Follow `CLAUDE.md` and `.claude/rules/` once prompt 01 has created them.
- No secrets in the repository. Missing API keys or accounts never block a prompt: build against
  fakes, recorded fixtures and feature flags, make tests pass without the key, and add the setup step
  to `HUMAN_TASKS.md`.
- Never fetch Airbnb, Vrbo or Booking.com pages; no scraper libraries; never rank by commission; no
  banner ads; no em dashes in UI copy or docs.
- Work that needs macOS (Xcode builds, device runs, signing) is written and committed, and the device
  steps go to `HUMAN_TASKS.md`. The web build and tests must still pass.
- Do not implement anything from Phase 2 or Phase 3.
- Small judgement calls (naming, library choice within the stack, a default value the spec does not
  give): decide, record in `DECISIONS.md`, continue.
- Do not use destructive git commands on `main` (no force push, no history rewrite).

## Stop conditions (stop, write the reason in PROGRESS.md, and report to the owner)

- Merging is impossible (no permission, branch protection that needs a human review).
- The same CI failure survives three fix attempts.
- A spec conflict whose choice is expensive to reverse (money handling, security, data model changes
  that later prompts depend on) and is not settled by the precedence order above.
- An action would spend real money beyond ordinary development API usage, or would touch production
  data.
- Anything that needs the owner's legal or business decision (listed in `HUMAN_TASKS.md`) blocks a
  ticket completely and no flag or fake can stand in for it.

## Phase 1 completion check (after prompt 28)

Phase 1 is complete when all of these are true. Write the result to `docs/gates/phase-1-complete.md`:

1. Every ticket in `09-build-roadmap.md` not on the cut list is done and merged (the cut-list tickets
   WF-122 and WF-129 are done or recorded as cut in `DECISIONS.md`).
2. `npm run lint`, `npm test`, `npm run test:e2e` and the evals pass on `main`.
3. The month 6 exit checklist in `09-build-roadmap.md` passes, except items that are owner-only steps,
   which are listed in `HUMAN_TASKS.md`.
4. `HUMAN_TASKS.md` is complete and ordered, so the owner can finish accounts, keys, the Mac build,
   TestFlight and App Store submission from it alone.
5. `PROGRESS.md` shows all 28 prompts done.
