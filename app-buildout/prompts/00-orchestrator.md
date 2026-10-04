# Phase 1 orchestrator

This file is the rulebook for building all of Hermi Phase 1 by running the prompts in this folder in order, one pull request per prompt, until Phase 1 is complete. The autopilot driver (`scripts/autopilot/run.mjs`) runs them, as `AUTOPILOT.md` describes: a fresh Claude Code session for every plan, ticket and ship, so nothing depends on one long conversation. A person can follow the same flow by hand.

## Where things are

| Path | What it is |
|---|---|
| `app-buildout/README.md` | Shared decisions: tiers, credits, stack, table names, non-negotiable rules |
| `app-buildout/phase-1-launch/` | The Phase 1 specification (01 to 10). The source of truth for what to build. |
| `app-buildout/phase-1-launch/09-build-roadmap.md` | Every ticket (WF-001 to WF-133) with dependencies, acceptance criteria, files and tests |
| `app-buildout/context/` | Business plan and competitive analysis: the reasons behind decisions. Read when a spec says "why". |
| `app-buildout/brand/` | Logo files and brand guide |
| `app-buildout/phase-1-launch/design/` | Visual design kit: tokens, component classes, screen mockups and PNGs. Read its README before any UI work. |
| `app-buildout/prompts/AUTOPILOT.md` | The creation prompt appended to every autopilot session: the modes, the stop list, owner verification pending |
| `app-buildout/prompts/S1-*.md` to `S3-*.md` | The setup prompts that fix the specification. They run before prompt 01. |
| `app-buildout/prompts/01-*.md` to `28-*.md` | The build prompts, run in number order |
| `app-buildout/prompts/PROGRESS.md` | The build's memory: which prompts are done, decisions, notes. Update it in every PR. |
| `app-buildout/prompts/HUMAN_TASKS.md` | Steps only the owner can do (accounts, keys, iOS signing, App Store). Add to it; never block on it. |
| `app-buildout/prompts/DECISIONS.md` | Judgement calls made during the build, with the reason and how to reverse them |
| `app-buildout/phase-2-growth/`, `phase-3-scale/`, `reference-full-spec/` | Not part of this build. Do not implement anything from them. |
| `scripts/autopilot/` | The driver, its settings and its guard hooks. Sessions never edit it. |
| `.autopilot/` | Gitignored runtime state: `state.json` (the driver's), `plans/`, `logs/`, `stop.json` |
| `.reference/trip-planner/` | Read-only clone of the base code (see "Base code" below). Gitignored. |
| `CLAUDE.md`, `.claude/rules/`, `.claude/agents/`, `.claude/skills/`, `knowledge/`, `findings/` | The context-kit 0.10.0 layout (see "Context system" below) |

The application code lives at the repository root in the layout from
`phase-1-launch/02-architecture.md` section 2 (`apps/`, `packages/`, `infra/`, `.github/`, `docs/`).
The spec stays in `app-buildout/`; do not copy it to `docs/spec/`.

Precedence when documents disagree: `app-buildout/README.md`, then `phase-1-launch/README.md`
(including its "Settled values"), then the topic spec (01 to 08, 10), then `09-build-roadmap.md`.

For how the UI looks, the token values in `phase-1-launch/05-ui-ux-spec.md` section 2 win, then `phase-1-launch/design/`, then the ASCII wireframes in 05 section 6. For what the UI does and says (behavior, states, copy, events), 05 wins.

## Base code: the Trip Planner repository

Hermi is built on the existing Trip Planner app, https://github.com/avillalv/trip-planner. It is
not part of this repository. At the start of every plan session, before planning:

1. If `.reference/trip-planner/` does not exist, clone it there read-only:
   `git clone --depth 50 https://github.com/avillalv/trip-planner .reference/trip-planner`
   (`.reference/` is in `.gitignore`). If it cannot be cloned, continue from the specs and note it
   in `PROGRESS.md`.
2. If it exists, `git -C .reference/trip-planner pull --ff-only` to pick up the latest.
3. Never commit to, push to, or edit files in `.reference/trip-planner/`. Copy what you port into
   the Hermi layout and adapt it there.

`knowledge/trip-planner-base.md` says what to reuse, adapt and drop, and
`phase-1-launch/02-architecture.md` section 14 maps every module.

## Context system (context-kit 0.10.0)

This repository uses the context-kit plugin, version 0.10.0, from the marketplace
`avillalv-es/context-kit`. It is installed on the owner's machine; the build never installs or
updates plugins, so there is no `/plugin install` anywhere in the loop. It provides a three-tier
layout (`CLAUDE.md`, `.claude/rules/`, `knowledge/` and `.claude/skills/`), a lean ruleset injected
into every session and subagent, and skills that sessions call with the Skill tool:
`context-kit:blast-radius`, `context-kit:finding`, `context-kit:context-graph` and
`context-kit:context-init`. The `CLAUDE.md` sections "PR train" and "Context sync" do not apply to
autopilot sessions, except that gate and final sessions run the context-sync check and routing in
the foreground.

- **Where knowledge goes.** Never grow `CLAUDE.md` on your own; it is capped at 200 lines. Knowledge
  that applies to certain files goes in `.claude/rules/<topic>.md` with narrow `paths`; reference
  goes in `knowledge/` with a row in `knowledge/INDEX.md`; a procedure that repeats becomes a skill
  (`context-kit:skill-capture` writes it and reports one line).
- **Before reading widely,** locate first: `knowledge/INDEX.md`, then the spec section, then the code.
- **Before a pull request,** call `context-kit:blast-radius` on the diff and run the tests it names.
  Do the same before committing a structural change (an exported symbol, a file move, a route, a config key).
- **Long investigations** record conclusions with `context-kit:finding`, so they survive the session.
- **At each month gate,** call `context-kit:context-graph` with `--code` and `context-kit:context-init`
  with the arguments `cleanup only audit, do not propose moves yet` (the same as running
  `/context-init cleanup only audit, do not propose moves yet`), and include both results in the gate
  file. Fix any rule whose `paths` match nothing.

## Subagents

Defined in `.claude/agents/`. A PreToolUse guard allows only these four, plus `general-purpose` and
`Explore` on Sonnet (context-sync routing and read-only searches), and rejects a `model` that does not
match the agent.

| Agent | Model | Use for |
|---|---|---|
| `sonnet-researcher` | Sonnet | Read-only: spec lookups, reading the Trip Planner base, finding existing code. Returns conclusions, not file dumps. |
| `sonnet-coder` | Sonnet | Implements exactly one ticket or sub-step, tests first, runs lint and tests, reports a diffstat and results. Never commits and never edits the status logs. |
| `opus-reviewer` | Opus | Read-only adversarial review of a step's diff against its acceptance criteria and the rules. Ends with `VERDICT: APPROVE <step id>` or `VERDICT: REQUEST_CHANGES <step id>` (the id is also `ship-<unit>` for a ship diff). |
| `opus-judge` | Opus | Read-only decisions: a step rejected three times, a failed ci-fix, a gate verdict, a new dependency. Returns the decision, the reason and how to reverse it. Also gives the `VERDICT: APPROVE FINAL` completeness verdict and reviews a ci-fix diff (`VERDICT: APPROVE ci-fix-<pr>-<n>`). |

## Models

- **Plan and final sessions run on Claude Opus 5.5** (`claude-opus-5-5`). **Ticket, ship and ci-fix
  sessions run on Claude Sonnet 5.5** (`claude-sonnet-5-5`). The driver sets the model and pins the
  aliases with environment variables.
- **All research and all coding go to Sonnet subagents** (`sonnet-researcher`, `sonnet-coder`). Every
  verdict comes from `opus-reviewer` or `opus-judge`; a verdict from anything else does not count and a
  Sonnet session never writes one. If the weekly Opus limit is hit the driver pauses the run;
  judgement never falls back to Sonnet.
- A session may make small fixes itself (a failing lint line, a PR description), but features,
  migrations and tests are written by `sonnet-coder` and reviewed by `opus-reviewer`.
- Inside the product, the models are fixed by the spec (`claude-haiku-4-5` and `claude-sonnet-5-5`);
  do not confuse the build models with the product's models. Product AI is chosen by `AI_PROVIDER`:
  tests, CI and local smoke runs force `fake`, and the owner's local machine may use `claude_cli`.

## The loop (the driver's unit flow)

Units run in this order: S1 to S3, 01 to 28, then FINAL. For each unit:

1. **Pick the unit.** The driver takes the first unit whose `PROGRESS.md` row is not `Done`. A
   `Stopped` row, or a pull request labelled `autopilot:stopped`, halts the run with its reason. Before
   every session the driver runs preflight and cleanup: one running driver, `gh` and `claude` signed
   in, protection on `main` (the `ci` check required, administrators included), the last `ci` run on `main` green (otherwise a ci-fix unit
   runs first), ports 8100 and 5173 free and stray process trees killed, leftover commits pushed, then
   `git stash push -u`, checkout `main` and pull.
2. **Plan (Opus), every unit except FINAL.** Reads the prompt, its tickets and its "Read before starting" list
   (long reads go to `sonnet-researcher`), checks the dependencies are done, marks device and account criteria
   "owner verification pending", writes the plan under "Current prompt" in `PROGRESS.md` and
   `.autopilot/plans/<unit>.json`, creates the branch `phase1/pNN-<slug>` (or `spec/sN-<slug>`) and a
   draft pull request. It resumes safely when the branch or PR already exists.
3. **Ticket (Sonnet), one session per step.** A step is a ticket, or a sub-step `WF-0NN.k` of a large
   one. `sonnet-coder` writes the failing tests first, then the code, then lint and the split suites;
   UI steps run `verify-ui-against-kit`; `opus-reviewer` gives the verdict, and after three rejections
   `opus-judge` decides. The session commits `<step id> <title>` and pushes. Never run two migration
   steps at once; steps are serial.
4. **Ship (Sonnet).** The local run check (`run-hermi-locally`, from prompt 06 on), the month gate when
   due, the records (`PROGRESS.md`, `HUMAN_TASKS.md`, `DECISIONS.md`, `knowledge/`, skills, findings,
   `npm run gen:api`, `hermi seed --demo`), then the `prepare-pr` skill: the pull request leaves draft
   and gets the `e2e` label.
5. **CI and merge (the driver).** It waits until the check named `ci` has passed (no other check counts),
   then looks once more at the pull request (no `stop.json`, no `autopilot:stopped` label, not a
   draft, the `Done (#n)` row intact, nothing changed under `scripts/autopilot/`) and confirms every
   Opus verdict the PR needs, read from the forwarded subagent messages: an `APPROVE` for every step,
   `APPROVE FINAL` from `opus-judge` for the final PR, `APPROVE ci-fix-<pr>-<n>` from `opus-judge` for
   any ci-fix commits (and for every fix PR of a red `main`), and `APPROVE ship-<unit>` from
   `opus-reviewer` when the ship diff changes more than documents, the status logs, `knowledge/`,
   `findings/`, `.claude/skills/`, the generated API types and the seed. Then it squash-merges,
   deletes the branch and pulls `main`. Sessions never merge, force-push or push to `main`. The result
   is read from `gh pr view --json state,mergedAt`, not from a model.
6. **ci-fix (Sonnet).** A red check starts a ci-fix session with the failing log tail. After three
   failures on one pull request the driver stops with the label and `state.json`. A red `main` is fixed
   first on `fix/main-ci-<yyyymmdd>`.
7. **Month gates.** After prompts 06, 11, 15, 20 and 24 (the ends of months 1 to 5 in
   `09-build-roadmap.md`) the gate runs in the ship session of the next prompt (07, 12, 16, 21 and 25)
   with the `month-gate` skill. The checklist is `10-quality-security-launch.md` section 7, split into
   agent-checked items (each with a command and a pass condition) and owner-only items (they become
   `HUMAN_TASKS.md` rows). The result goes to `docs/gates/month-N.md`, `opus-judge` gives the verdict,
   and the context audit runs in the foreground. If the gate shows serious slippage, apply the cut list
   in `09-build-roadmap.md` section 4 and record it in `DECISIONS.md`.
8. **FINAL (Opus).** After prompt 28 the scripted completion check below runs. There is no plan session: the
   single `final` session opens `phase1/final` and its draft pull request itself, and the driver then waits for
   `ci` and merges as in step 5.
9. **Context.** Every session starts empty. State lives in git, GitHub, `PROGRESS.md`,
   `HUMAN_TASKS.md`, `DECISIONS.md` and the driver's `.autopilot/state.json`, never in a conversation.
   There is no `/compact` and no handoff file.

## Rules for every prompt

- Follow `CLAUDE.md` and `.claude/rules/`.
- No secrets in the repository, and never read `.env` (`npm run doctor` reports what is set). Missing
  API keys or accounts never block a prompt: build against fakes, recorded fixtures and feature flags,
  make tests pass without the key, and add the setup step to `HUMAN_TASKS.md` (each key row says exactly
  where it goes, for example "put it in `.env`").
- Owner verification pending. An acceptance criterion that only the owner can verify (a device, an
  account, a store, real money, a human decision) never blocks a ticket: build everything around it,
  list it in the step's `owner_pending`, add one `HUMAN_TASKS.md` row for it and name it in the pull
  request. Business tickets WF-001 and WF-003 produce documents ("Done (docs)") and a provisional "go" in
  `DECISIONS.md`; their real-world parts are owner rows.
- UI tickets start from the kit. The coder brief always includes `design/README.md`,
  `DESIGN-LANGUAGE.md`, the `hermi.css` block and the mockup named in the ticket's `Kit:` line, and the
  step runs the `verify-ui-against-kit` skill.
- The local run check (`run-hermi-locally`) runs in the ship session from prompt 06 on, with
  `AI_PROVIDER=fake` and `SCHEDULER_ENABLED=false` in the process environment.
- Never fetch Airbnb, Vrbo or Booking.com pages; no scraper libraries; never rank by commission; no
  banner ads; no em dashes in UI copy or docs.
- Work that needs macOS (Xcode builds, device runs, signing) is written and committed, and the device
  steps go to `HUMAN_TASKS.md`. iOS builds run on GitHub macOS runners. The web build and tests must
  still pass.
- Do not implement anything from Phase 2 or Phase 3. WF-122 is built; WF-129 is on the cut list and is
  built unless a prompt stopped.
- Small judgement calls (naming, library choice within the stack, a default value the spec does not
  give): decide, record in `DECISIONS.md`, continue.
- Push after every commit. Sessions never merge. Do not use destructive git commands on `main` (no force
  push, no history rewrite).

## Stop conditions (a closed list)

Stop only for these. The session writes `.autopilot/stop.json` with the reason and the exact owner
action, sets its `PROGRESS.md` row to `Stopped (<reason>)` (the owner action as one sentence), pushes,
and labels the pull request `autopilot:stopped`.

- Merging is impossible (no permission, or branch protection that needs a human review).
- Three ci-fix attempts on one pull request fail.
- A spec conflict whose choice is expensive to reverse (money handling, security, data model changes
  that later prompts depend on) and is not settled by the precedence order above.
- An action would spend real money beyond ordinary development API usage, or would touch production
  data.
- The same command is denied twice, or the driver reports repeated denials.
- `gate-failed`: the `month-gate` verdict is `stop`.

Nothing else stops the build. A missing key or account, a business or legal decision, a device step and
a usage limit are not stops (the first three become `HUMAN_TASKS.md` rows; the driver waits out the
fourth). The exact reasons and the procedure are in `AUTOPILOT.md`.

## Phase 1 completion check (the FINAL session, after prompt 28)

Phase 1 is complete when all of these are true. The FINAL session runs them as a script and writes the
result to `docs/gates/phase-1-complete.md`:

1. Every ticket in `09-build-roadmap.md` (WF-001 to WF-133) is done or owner-pending, and every
   owner-pending criterion has a `HUMAN_TASKS.md` row.
2. `npm run lint`, `npm test`, `npm run test:e2e`, `npm run test:kit` and `npm run evals` (fake mode)
   pass, the dash grep prints nothing, and there is a single Alembic head.
3. `npm run setup` works from scratch, and `npm run dev` plus `npm run test:e2e:smoke` pass with dev
   sign-in and `AI_PROVIDER=fake`.
4. `hermi ai-smoke` makes one no-tools call and one capped web-tool call through `claude_cli`, and the
   `npm run doctor` output is attached.
5. The month 6 checklist (`10-quality-security-launch.md` section 7.5) passes for its agent-checked
   items; its owner-only items are in `HUMAN_TASKS.md`.
6. `HUMAN_TASKS.md` is complete and ordered, so the owner can finish accounts, keys, iOS signing,
   TestFlight and App Store submission from it alone, and the owner guide `docs/owner-guide.md` exists.
7. `PROGRESS.md` shows S1 to S3 and all 28 prompts done.
