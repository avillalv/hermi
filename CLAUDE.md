# Hermi

Specification, design kit, brand files and build prompts for Hermi, a collaborative trip planner for iOS and the web. All of it lives under `app-buildout/`. There is no application code yet, so no manifest, no build, lint or test command and no CI. Prompt 01 (`app-buildout/prompts/01-repo-foundation.md`) scaffolds the monorepo at the repo root; add a Commands section only after those commands have been run. Only Phase 1 is being built.

## Conventions

- **No em dashes or en dashes (U+2014, U+2013) in anything you write**: UI copy, docs, comments. Use a comma, a period or "to" for ranges. The spec says CI will fail on them (`05-ui-ux-spec.md` section 7) and `app-buildout/` has none today. `findings/` entries are the one exception, because `findings.sh` writes an em dash into every entry heading. Check: `grep -rIl -e $'\xe2\x80\x94' -e $'\xe2\x80\x93' app-buildout` must print nothing.
- **Precedence when documents disagree:** `app-buildout/README.md`, then `phase-1-launch/README.md` (its "Settled values"), then the topic spec (`01` to `08`, `10`), then `09-build-roadmap.md`. For how UI looks: `05-ui-ux-spec.md` section 2 token values, then `design/`, then the ASCII wireframes in 05 section 6. For what UI does and says: `05`.
- **Non-negotiable rules** are in `app-buildout/README.md` ("Non-negotiable rules"). Read them before writing code or UI copy. The ones code breaks silently: never fetch Airbnb, Vrbo or Booking.com pages, no scrapers, never rank by commission, no secrets in the repo.

## Pitfalls

- **`reference-full-spec/` has the same filenames as `phase-1-launch/`** (`01-product-spec.md` to `10-quality-security-launch.md`) and is the superseded all-phases spec. Never read it for current behavior and never edit it. `phase-2-growth/` and `phase-3-scale/` are not built yet either.
- **Phase numbers differ by folder.** `context/business-plan/` uses an older four-phase scheme where Phase 4 is growth, Stripe and print. The phase folders and the root README use three, with Stripe and print in Phase 3 (one stray "Phase 4" remains in the root README's note on group tools; it means Phase 3). Do not carry a phase number from one to the other.
- **Shared values are repeated in many files.** The Plus annual price and the brand sky hex are each in more than twenty files, counting `context/`; credit costs and ceilings are spread as widely. Change the root README first, then grep `app-buildout/` for the old value before calling it done.

## Where knowledge lives

- Before building or changing a Phase 1 feature, read its spec `app-buildout/phase-1-launch/NN-*.md` and its ticket in `09-build-roadmap.md`. The ticket's acceptance criteria are the definition of done.
- Before any UI, color, font or logo work, read `app-buildout/phase-1-launch/design/README.md` and `app-buildout/brand/BRAND.md`. `.claude/rules/design-token-sync.md` loads itself when you edit those files.
- Before running or resuming the build, read `app-buildout/prompts/KICKOFF.md`, then `00-orchestrator.md`. `PROGRESS.md` is the build's memory between sessions; update it, `HUMAN_TASKS.md` and `DECISIONS.md` in every pull request.
- When a spec says "why", read `app-buildout/context/business-plan/README.md` (business reasoning) or `app-buildout/context/competitive-analysis/README.md` (rivals).
- Topic index for everything else: `knowledge/INDEX.md`.

<!-- context-kit:begin context-layout -->
## Context layout

This project uses a three-tier layout. Do not add knowledge to this file on
your own initiative. If something seems worth keeping, say so in one line and
let me decide.

- Conditional knowledge lives in `.claude/rules/` with `paths` frontmatter.
- Reference and procedures live in `knowledge/` and `.claude/skills/`.
- A procedure that repeats gets captured into `.claude/skills/`. Tell me in one
  line after you create it; do not add it here.
- This file is capped at 200 lines.

To reorganize any of it, run `/context-init cleanup`.
<!-- context-kit:end context-layout -->

<!-- context-kit:begin lean-execution -->
## Lean execution

Active every response. No drift back to over-building; still active if unsure.
Off via `/lean off`.

## Before writing code, stop at the first rung that holds

1. Does this need to exist at all? Speculative need: skip it, say so in one line.
2. Already in this codebase? Reuse the helper, util, type or pattern that is here.
3. Standard library does it? Use it.
4. Native platform feature covers it? Use it.
5. Already-installed dependency solves it? Use it. Never add one for what a few lines do.
6. Can it be one line? One line.
7. Only then: the minimum that works.

The ladder runs *after* you understand the problem, never instead of it. Read
the task and the code it touches, trace the real flow, then climb. Two rungs
work: take the higher one and move on. The smallest change in the wrong place
is not lazy, it is a second bug.

## Before reading

Grep or Glob to locate, then read only the ranges you need. Never read a file
whole to find one symbol. A search spanning many files goes to a subagent so its
raw output never lands in this window; the bar is isolatable AND verbose, not
merely specialized.

## Output

Answer first. Then at most three short lines: what you skipped, when to add it.
No essays, no feature tours, no design notes. If the explanation is longer than
the code, delete the explanation. Explanation the user actually asked for (a
report, a walkthrough, per-phase notes) is exempt: give it in full.

## Never simplify away

Input validation at trust boundaries, error handling that prevents data loss,
security, accessibility, or anything explicitly requested. If the user wants the
full version, build it, no re-arguing.

## Capture

Finished a procedure worth repeating, or spotted knowledge that would be cheaper
as a skill? Use the `skill-capture` skill, create it, and report it in one line.
Do not add it to CLAUDE.md.

Mark a deliberate shortcut that cuts a real corner with a known ceiling using a
`shortcut:` comment naming the ceiling and the upgrade trigger.

Level full: the ladder enforced. Stdlib and native before custom. Shortest working diff, shortest explanation.

When spawning a subagent (Task/Agent tool), include this section's content in its prompt.
<!-- context-kit:end lean-execution -->

<!-- context-kit:begin model-routing -->
## Model routing

This session decides; subagents do the legwork. Pass `model` on every Agent call.

- `model: "sonnet"` (latest Sonnet): exploring, searching, researching,
  investigating, coding to an agreed plan, writing markdown, running tests.
- `model: "opus"`: planning, architecture and trade-offs, review verdicts,
  root-cause judgment, deciding what a result means. If this session is not
  Opus, send these to an Opus subagent instead of deciding here.
- Never use a model your organization restricts; take the nearest allowed one.

Turn this off with `/model-routing off`.
<!-- context-kit:end model-routing -->

<!-- context-kit:begin context-sync -->
## Context sync

Project markdown (PROGRESS.md, docs/, notes) is the source. `knowledge/`, `findings/`,
`.claude/rules/` and `.claude/skills/` are where it gets routed.

- Before the first request of every session, use the `context-sync` skill. Its first
  step is one command; if it prints nothing, carry on.
- If something changed, a background subagent routes it while the request goes ahead.
  Report the result in one line.
- Mid-session, a settled conclusion or dead end goes to `finding-ledger` and a repeatable
  procedure to `skill-capture`, never into this file. Turn this off with `/context-sync off`.
<!-- context-kit:end context-sync -->

<!-- context-kit:begin pr-train -->
## PR train

When an agreed plan holds two or more asks that would each be their own PR
(different areas, independently revertable: a UI change plus a roles change),
run it as a PR train with the `pr-train` skill. Decide for every new ask; one
ask, or tightly coupled changes, stay one PR.

- One branch and PR per task; `.claude/handoff/<train>.md` tracks the plan.
- Tasks with disjoint files run in parallel worktrees; shared files (docs,
  version, changelog) are applied afterwards, in order, so nothing conflicts.
- After each PR or parallel batch, update the handoff and ask me to `/compact`.
- If `.claude/handoff/` holds a train with `status: active`, read it before
  anything else and continue from its next unchecked task.
- Turn this off with `/pr-train off`.
<!-- context-kit:end pr-train -->

<!-- context-kit:begin blast-radius -->
## Blast radius

Before a structural edit, use the `blast-radius` skill on the symbol or file and
read every depth-1 importer it lists. Structural means: changing an exported
function, type, class or signature; renaming, moving or deleting a file or
export; changing a shared module, schema, config key or route. Before
committing, run it on the diff and run the tests it names. A body-only change
inside one function does not need it.

Turn this off with `/context-init off blast-radius`.
<!-- context-kit:end blast-radius -->
