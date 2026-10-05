---
name: month-gate
description: "Use when running a month exit gate in the autopilot ship session of the prompt after 06, 11, 15, 20 or 24 (the gates for months 1 to 5). Checks the exit list, audits the context layout, gets an opus-judge verdict and writes docs/gates/month-N.md."
---

# Month gate

Run it in the ship session, after the local run check and before `prepare-pr`. Do not commit the result yourself. The `ship: <unit>` commit from `prepare-pr` carries the gate file. The rule for `docs/gates/**` is `.claude/rules/build-logs.md`.

## When it is due

| Gate | Ship session of prompt | Exit list in `10-quality-security-launch.md` section 7 |
|---|---|---|
| Month 1 | 07 | 7.1, the items tagged Month 1 |
| Month 2 | 12 | 7.1, the items tagged Month 2 |
| Month 3 | 16 | 7.2 |
| Month 4 | 21 | 7.3 |
| Month 5 | 25 | 7.4 |

Untagged items in 7.1 go to the first gate where they can run. Month 6 (7.5) belongs to the FINAL unit, not to this skill. Take N from the row that matches `UNIT` in the task line (`07` is month 1, `12` is month 2, `16` is month 3, `21` is month 4, `25` is month 5).

## Steps

1. **Read the exit.** The list above, and the month's row in `app-buildout/phase-1-launch/README.md` ("Month plan"). The month's week table and `Exit:` line are in `09-build-roadmap.md` section 1.
2. **Split the items.** Agent-checkable: you can prove it here with a command that has a pass condition (a test run, a SQL query on the local database, a grep, a script, a file check). Owner-only: it needs staging, a device, a real account, a real purchase, a person, a dashboard or money. An item with both parts (for example "a signed-in user creates a trip on staging") splits: the local proof (`npm run test:e2e:smoke` with dev sign-in) is agent-checked, and the real-world proof is owner-only. A demand signal or a signed go decision is owner-only too; the provisional go in `DECISIONS.md` is the agent-checked part. Never tick an owner-only item. Write the pass condition before you run anything.
3. **Owner-only items.** Add one row each to `app-buildout/prompts/HUMAN_TASKS.md`, in the order the owner should do them: the exact action, and where the evidence goes. Insert each row where it belongs and renumber, as `.claude/rules/build-logs.md` says.
4. **Run the agent-checked items** with `AI_PROVIDER=fake`. Record the exact command, the pass condition and the result, one line each. A check that needs more than about 10 minutes becomes owner-only (back to step 3), or gets a smaller local proof. Say so in the table.
5. **Audit the context layout**, through the Skill tool:
   - `context-kit:context-graph` with args `--code`. Build only. Never `serve`, `vault` or `open`. Read `.claude/context-graph/graph.json` (never the HTML) for its stats and `issues`. A rule whose `paths` match no file is an issue: fix the glob if the fix is small, else list it. Delete `.claude/context-graph/` afterwards (`rm -rf .claude/context-graph`). It is build output and must not be committed.
   - `context-kit:context-init` with args `cleanup only audit, do not propose moves yet`.
   - Keep both outputs for the gate file, trimmed to the summary and the findings (about 60 lines each).
6. **Sync in the foreground.** Run `context-kit:context-sync` through the Skill tool. Where it says to start the routing subagent in the background, start it in the foreground instead (general-purpose, `model: "sonnet"`, `run_in_background: false`), wait for it, then do the skill's step 3. Keep its one-line report for the gate file.
7. **Ask `opus-judge`** (`model: "opus"`). Give it the table, both audit outputs, the month's exit line and `09-build-roadmap.md` section 4 (the cut list). Ask two questions: `pass`, `fix now` in this PR, or `stop`; and whether the cut list applies (only when the month exit is more than two weeks behind, per 09 sections 3 and 8; a failed item alone never applies it).
8. **Write `docs/gates/month-N.md`** from the template below, with the judge's verdict. If the file exists, update it. Use `date +%F` for the date.
9. **Act on the verdict.**
   - **pass:** carry on.
   - **fix now:** one extra step through `sonnet-coder` and `opus-reviewer` (review step id `gate-<N>`). Commit it as `ship: <unit>`, never `gate-<N> <title>`. Push, rerun the failed items, update the table and the verdict line. Ask the judge again if it still fails.
   - **stop:** follow the stop procedure in `app-buildout/prompts/AUTOPILOT.md`. In short: write `.autopilot/stop.json` with the keys `unit`, `reason` and `ownerAction`, set the unit's PROGRESS row to `Stopped (<reason>)` (the reason is the owner action, in one sentence, with no parentheses inside it), commit `ship: <unit>`, never `stop: <unit>`, push, add the label `autopilot:stopped` to the PR (`gh pr edit <n> --add-label autopilot:stopped`), leave the PR as a draft, and end with the owner action as your last message.
   - **cut list applied** (only as step 7 says): paste the judge's DECISIONS.md row, and note the cut tickets in the PROGRESS notes.

## Template

```markdown
# Month N gate

Date: <YYYY-MM-DD>. Unit: <unit>. Verdict: <pass | fixed in this PR | stop>.

## Month exit

<Exit line from phase-1-launch/README.md>: met or not met, with one line of evidence.

## Agent-checked

| Item | Command | Pass condition | Result |
|---|---|---|---|
| <item from section 7> | `<command>` | <condition> | <pass or fail, with the number> |

## Owner-only

| Item | Who does it | HUMAN_TASKS row |
|---|---|---|
| <item> | <the owner, or who the row names> | <short task text, then "(row n)"; the text survives a renumbering> |

## Context audit

### context-graph --code

<trimmed output>

### context-init cleanup (audit only)

<trimmed output>

### Context sync

<one line>

## Judge

<Decision, reason, and cut list applied or not, with the DECISIONS.md row>
```
