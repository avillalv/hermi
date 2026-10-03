# Kickoff: start (or resume) the Phase 1 build

## Before you paste the prompt

1. Create a new, empty GitHub repository (for example `hermi`) and copy the whole `app-buildout/`
   folder into its root, so the path is `app-buildout/prompts/KICKOFF.md`. Commit and push to `main`.
2. In the repository settings, protect `main` so it requires CI to pass but lets Claude merge its own
   pull requests (do not require a human approval, or the build stops at the first merge).
3. Give the session access to the base code, https://github.com/avillalv/trip-planner. In Claude
   Code on the web, select both `hermi` and `trip-planner` when you start the session. Locally,
   make sure your GitHub login can clone it. The build clones it read-only to `.reference/`.
4. The context-kit-v2 plugin is enabled in `.claude/settings.json`. If Claude Code does not install
   it on its own, run `/plugin marketplace add https://github.com/avillalv/context-kit-v2.git` and
   `/plugin install context-kit-v2@context-kit-v2`, then restart. Check with `/hooks`.
5. Start a Claude Code session on that repository with the **Claude Opus 5.5** model
   (`/model` in the CLI, or the model picker on the web). Opus is the orchestrator; it will start
   Sonnet 5.5 subagents for research and coding.
6. Let it work without stopping for approval on every edit: use auto or accept-edits permissions, and
   make sure the session can push, open pull requests and merge (the `gh` CLI logged in, or the
   GitHub connector in Claude Code on the web).
7. Optional but useful: give the session an Anthropic API key with a monthly spend limit so the evals
   in prompts 14 and 27 can measure real agent costs. Everything else works on fakes until you add
   keys from `HUMAN_TASKS.md`.

## The prompt to paste

```text
You are the orchestrator for building Hermi Phase 1 in this repository.

Read app-buildout/prompts/00-orchestrator.md and follow it exactly, starting with its
"Base code" section (clone https://github.com/avillalv/trip-planner read-only into
.reference/trip-planner and build on it) and its "Context system" section. Then read
app-buildout/prompts/PROGRESS.md, find the first prompt that is not done, and work through
app-buildout/prompts/01-*.md to 28-*.md in order until all of Phase 1 is built.

Models: you run on Opus 5.5 and do the planning, judgement calls and review of every diff.
Use Sonnet 5.5 subagents for all investigation, research and coding, one ticket at a time,
tests first.

For each prompt: create its branch, build every ticket in it against the acceptance criteria in
app-buildout/phase-1-launch/09-build-roadmap.md, run lint and tests, update PROGRESS.md,
HUMAN_TASKS.md and DECISIONS.md, push, open a pull request, wait for CI, fix anything red, merge
into main, pull main, keep your working context small by relying on PROGRESS.md, and start the
next prompt without waiting for me.

Never block on accounts or API keys: use fakes, fixtures and feature flags, and add the setup
step to HUMAN_TASKS.md. Stop only for the stop conditions in 00-orchestrator.md, and when you
stop, write the reason in PROGRESS.md and tell me exactly what you need.

Finish with the Phase 1 completion check in 00-orchestrator.md.
```

## Resuming

If the session ends, runs out of context, or stops for a reason you have now fixed, start a new
Opus 5.5 session on the same repository and paste the same prompt. It resumes from `PROGRESS.md`.

## What to expect

- 28 pull requests, one per prompt, each merged into `main` when CI is green.
- The whole of Phase 1 is large (the roadmap estimates about 560 hours of human work). Expect it to
  take many sessions; each session picks up where the last one stopped.
- Some steps can only be done by you, such as creating accounts, adding keys, building and signing the
  iOS app on a Mac, TestFlight, and App Store submission. They collect in `HUMAN_TASKS.md` in the
  order you should do them.
