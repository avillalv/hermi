# Knowledge index

One entry per topic, named for what someone would search for. The filename and the folder are the retrieval index; if you cannot find a topic by its name, the name is wrong.

This repo is the specification itself, so its reference material lives in `app-buildout/` and is **not** copied here. This index points at it so there is one place to look. `knowledge/` holds only what the spec does not say.

## In this folder

| File | Read it when |
|---|---|
| `autopilot.md` | You start, watch, stop or resume the unattended build, meet an exit code or a usage-limit pause, or need to know why sessions never merge. |
| `local-dev-windows.md` | You set up, run or debug Hermi on this Windows machine: the PostgreSQL superuser password, the commands, ports, dev sign-in and the Windows hazards. |
| `env-and-accounts.md` | You add or change an environment variable, or need to know what an account or key is for, whether you need it locally, and where to get it. |
| `ai-provider-claude-cli.md` | You touch the `AiProvider` seam, run product AI through the owner's own `claude -p`, or move to the Anthropic API for production. |
| `trip-planner-base.md` | You port code from the old Trip Planner, or build `npm run setup`, `db:init` or the local AI provider from it. |
| `ios-builds-on-ci.md` | You build, sign or test the iOS app without a Mac: the GitHub macOS jobs, the Apple account steps and TestFlight. |
| `plan-and-stays.md` | You touch the itinerary, places and map, lodging, notes or the shared SSRF guard. |
| `row-level-security.md` | You touch RLS policies, `app.user_id`, or the API startup refusal for an unsafe database login. |

## Repo docs and skills

| File | Read it when |
|---|---|
| `README.md` | You need the setup and run steps for a fresh machine. |
| `docs/adr/0001-name.md` | You touch the product name, fallback names (Twoyage, Zigroam), the trademark checklist or owner-only domain and mail items. |
| `docs/porting-map.md` | You port code from the old Trip Planner: what moved where, what is not ported yet, what was left behind and why. |
| `docs/validation/README.md` | You run the demand validation kit (WF-003): interview script, price test cards, terms checklist. |
| `.claude/skills/autopilot-status` | Someone asks how the autopilot build is going, what is running, or what the owner must do. Read-only. |
| `.claude/skills/month-gate` | You run a month exit gate in the ship session after prompt 06, 11, 15, 20 or 24. |
| `.claude/skills/prepare-pr` | You finish a build unit's pull request in the ship session. Never merges. |
| `.claude/skills/run-hermi-locally` | You confirm a change in the real app: doctor, scratch database, dev servers, smoke test, cleanup. |
| `.claude/skills/verify-ui-against-kit` | A UI step is built and needs checking against the design kit before opus-reviewer. |

## The record: `app-buildout/`

| File | Read it when |
|---|---|
| `app-buildout/README.md` | You need a shared decision: tiers and prices, AI credit costs and ceilings, stack, core table names, the non-negotiable rules, or how Hermi reuses the old Trip Planner code. It wins over every other document. |
| `app-buildout/phase-1-launch/README.md` | You need Phase 1 scope, the month plan, or the "Settled values" (referrals, booked-fare alert, first-import Trip Pass, calendar polling). |
| `app-buildout/phase-1-launch/01-product-spec.md` to `10-quality-security-launch.md` | You are building or changing a Phase 1 feature: product, architecture, schema, API, UI, AI, monetization, admin, roadmap, quality and launch, in that order. |
| `app-buildout/phase-1-launch/09-build-roadmap.md` | You need a ticket (every ticket is in it): dependencies, acceptance criteria, files, tests, and the month exit checklists and cut list. |
| `app-buildout/phase-1-launch/design/README.md` | You are doing any UI work: tokens, component classes, screen mockups and PNGs. |
| `app-buildout/brand/BRAND.md` | You touch the logo, colors, type or voice, or need to regenerate the logo files. |
| `app-buildout/prompts/KICKOFF.md` and `00-orchestrator.md` | You start, resume or run the Phase 1 build: setup, the loop, models, stop conditions. |
| `app-buildout/prompts/AUTOPILOT.md` | You run or debug the autopilot: the session prompt every unattended session follows (its modes, stop reasons and owner verification pending). Operating it is in `knowledge/autopilot.md`. |
| `app-buildout/prompts/S1-spec-runtime.md`, `S2-spec-product-ui.md`, `S3-spec-roadmap-prompts.md` | You need the spec fixes the readiness audit found, applied before prompt 01: runtime and data (S1), product and UI (S2), roadmap and prompts (S3). Each spec file is edited by exactly one of them. |
| `app-buildout/prompts/PROGRESS.md` | You need to know which of the build prompts are done. Status log, so it stays where it is. |
| `app-buildout/prompts/HUMAN_TASKS.md` and `DECISIONS.md` | You hit an owner-only step (accounts, keys, Mac builds, App Store) or made a judgement call. Both are status logs. |
| `app-buildout/context/business-plan/README.md` | A spec says "why" about pricing, AI costs, infrastructure, affiliate revenue or the App Store path. |
| `app-buildout/context/competitive-analysis/README.md` | You need rival context (TripIt, Trippy, Wanderlog, Tripsy, AI planners) or the win plan. |
| `app-buildout/phase-2-growth/README.md`, `phase-3-scale/README.md` | Phase 1 is shipped and you are starting a feature pack. Not before. |
| `app-buildout/reference-full-spec/` | Never for current behavior. It is the superseded all-phases spec the phase folders were cut from. |

## Conventions for this folder

- **One topic per file.** Named for the words someone would search for.
- **Split past ~300 lines.** A lookup pulls the whole file, so a long file drags unrelated subtopics along with the one that was wanted.
- **Every file gets a row above.** A knowledge file missing from this index is a file nobody will find.
- **Do not quote a total from a register; count it.** Any number written into a summary line goes stale the next time the underlying file changes.
