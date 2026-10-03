---
description: Use when editing the build's status logs (PROGRESS.md, HUMAN_TASKS.md, DECISIONS.md) or a gate file under docs/gates. The autopilot driver parses PROGRESS.md, and the owner works through HUMAN_TASKS.md in order.
paths:
  - "app-buildout/prompts/PROGRESS.md"
  - "app-buildout/prompts/HUMAN_TASKS.md"
  - "app-buildout/prompts/DECISIONS.md"
  - "docs/gates/**"
---

# Build logs and gate files

Authority: `app-buildout/prompts/00-orchestrator.md` (the rulebook) and `app-buildout/prompts/AUTOPILOT.md`
(what `ship` mode records). If you need to break one of these, change the document in the same commit and say
why.

These are status logs, so they stay where they are and are not copied into `knowledge/`. Update them in every
build pull request (CLAUDE.md), and add a row only when there is something to record.

## PROGRESS.md

- Two tables, `## Setup prompts` (S1 to S3) and `## Prompts` (01 to 28), each with the columns
  `| # | Prompt | Tickets | Status |`. Keep the headings and the column names: the driver reads them to pick the
  next unit.
- Status is exactly one of `Not started`, `In progress (<branch>)`, `In review (#<pr>)`, `Done (#<pr>)` or
  `Stopped (<reason>)`. Nothing else, and no prose in the cell. Detail goes in "Notes for later prompts".
- A `Stopped (<reason>)` row halts the run. The reason is the owner action, as one sentence a person can follow,
  with no parentheses inside it. The commit that sets it uses the mode's subject (`plan: <unit>`, `ship: <unit>`
  or `ci-fix: <summary>`), never `stop:` or a step id such as `gate-N`.
- A unit's row changes in the pull request that does the work. Owner-pending criteria are not a status: the row
  still reads `Done (#<pr>)` and the pending item becomes a `HUMAN_TASKS.md` row.

## HUMAN_TASKS.md

- One table, and its header row is the format: fill every column of it. Status is `Open` or `Done`.
- Keep the rows in the order the owner should do them. Insert a row where it belongs and renumber; do not append
  out of order.
- Each row says exactly where a key or setting goes and where to get it. For example "put it in `.env` as
  `TRAVELPAYOUTS_TOKEN`, from travelpayouts.com", "add as GitHub Actions secret `NAME`" or "add to Render env
  group `hermi-staging`". A row that says only "get an API key" is incomplete.
- Never a secret value, a token fragment or a screenshot of one, here or in a commit message.
- The build never blocks on a row. Use a fake, a fixture or a flag until the owner has done it.

## DECISIONS.md

- Columns `| Date | Prompt | Decision | Reason | How to reverse |`. All five are filled.
- Date is absolute (`2026-10-03`). Prompt is the unit: `S1` to `S3`, `01` to `28`, `FINAL`, or `setup` for decisions made while preparing the autopilot.
- Append only. To change a decision, add a row that says which row it replaces.
- A row is required for: a dependency outside the 02 stack, a review accepted after three rounds, a conflict
  between documents settled by precedence or by the safer choice, a cut-list change after a failed gate, a small
  decision the spec leaves open (a name, a default, a library inside the stack), and the provisional "go" on the
  business gates WF-001 and WF-003 (their tickets are recorded `Done (docs)`; the real-world steps are
  `HUMAN_TASKS.md` rows). `Done (docs)` goes in the PR body tickets table, never in the PROGRESS Status cell.

## Gate files (`docs/gates/**`)

- One file per gate: `docs/gates/month-<n>.md` (the `month-gate` skill) and `docs/gates/phase-1-complete.md`
  (FINAL). The exit criteria come from 10 section 7; do not invent new ones.
- Two lists. **Agent-checked**: each item has the command that was run, the pass condition and the result.
  **Owner-only**: each item names who does it and links its `HUMAN_TASKS.md` row.
- The agent never ticks an owner-only item. A gate passes when the agent-checked list passes, the `opus-judge`
  verdict is recorded and every owner-only item is a `HUMAN_TASKS.md` row.

## What must not change without a decision

- **The five status strings and the table headers.** The driver and the `autopilot-status` skill parse them. A new
  spelling reads as "not started" or breaks the unit order.
- **The headings** `## Current prompt`, `## Setup prompts` and `## Prompts`.
- **Earlier DECISIONS rows.** Editing history hides why the build went the way it did.

## Checkable by grep

```bash
# a prompt row whose status is not one of the five (prints nothing when clean)
grep -nE '^\| (S[1-3]|[0-9]{2}) ' app-buildout/prompts/PROGRESS.md | grep -vE '\| (Not started|In progress \([^)]+\)|In review \(#[0-9]+\)|Done \(#[0-9]+\)|Stopped \([^)]+\)) \|$'
```
