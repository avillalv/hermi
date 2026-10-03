---
name: prepare-pr
description: "Finish a build unit's pull request in the autopilot ship session. Pushes every step commit, regenerates API types, writes the PR body, sets the PROGRESS row to Done, marks the PR ready and adds the e2e label. Never merges."
---

# Prepare the pull request

Use in ship mode, after the local run check, the month gate (when due) and the records (HUMAN_TASKS.md, DECISIONS.md, knowledge) are done. The driver merges after CI. You never merge, never force-push and never push to `main`. Every step is safe to repeat: skip what is already done.

## Inputs

- `UNIT` from the task line: `S1` to `S3`, a prompt number `01` to `28` (drop a leading `p`), or `FINAL`. `PR` from the task line, else `gh pr view --json number --jq .number`.
- Title: `Phase 1 / P<NN>: <prompt title>`, for a setup unit `Setup / <UNIT>: <title>`, or for FINAL `Phase 1 / FINAL: completion check`. Except for FINAL, the title is the link text in the unit's row in `app-buildout/prompts/PROGRESS.md`. FINAL has no row.

## Steps

1. **Push.** `git status --short` must show only files that belong to the unit. Then `git fetch origin` and `git log origin/<branch>..HEAD --oneline` (`<branch>` is `git branch --show-current`). If anything is ahead, `git push`.
2. **API types.** If `git diff --name-only origin/main...HEAD` shows route or model files in `apps/api/`, run `npm run gen:api`. If the generated types changed, commit `ship: <unit> api types` and push.
3. **Gather facts.** The earlier sessions are gone, so read them from files.
   - Steps and titles: `.autopilot/plans/<unit>.json`. Step commits: `git log --format='%h %s' origin/main..HEAD`.
   - Opus verdicts per step: read them only from `.autopilot/state.json`, key `approvals`: one entry per step id with `agent`, `model` and `at` (the time). If a step has no entry, write "verdict not found". Never write an approval you did not see.
   - Verification. A setup unit (`S1` to `S3`) has no application code yet: run `node scripts/spec-lint.mjs` and the dash grep (`grep -rIl -e $'\xe2\x80\x94' -e $'\xe2\x80\x93' app-buildout`, which must print nothing) once now and quote the results. `npm run lint` and the npm test suites apply only from prompt 01 on: run `npm run lint` and `npm test` once now, quote the summary lines and name the test files each ticket's Tests line lists. Never quote a result you did not see.
   - Owner tasks and decisions added: `git diff -U0 origin/main...HEAD -- app-buildout/prompts/HUMAN_TASKS.md app-buildout/prompts/DECISIONS.md`.
   - Deferred items: the "Current prompt" notes in `PROGRESS.md` and the plan.
4. **Write the body** to `.autopilot/tmp/pr-<unit>.md` (`mkdir -p .autopilot/tmp`; a quoted heredoc keeps backticks safe), from the template below. No em or en dashes.
5. **Update the PR.** `gh pr edit <n> --title "<title>" --body-file .autopilot/tmp/pr-<unit>.md`.
6. **PROGRESS row.** In the unit's row, change the Status cell to `Done (#<n>)`. Change nothing else. For FINAL skip this edit, because FINAL has no row. Run `git status --short`. If it shows nothing unexpected (no `.env`, logs, build output or `.claude/context-graph/`), `git add -A`. Commit `ship: <unit>` (this also carries the gate file when one was written). Push.
7. **Ready and label.** `gh pr ready <n>` (fine if it already is), then `gh pr edit <n> --add-label e2e`. If the label does not exist, run `gh label create e2e` once and add it again.
8. **Check.** `gh pr view <n> --json isDraft,labels --jq '{draft: .isDraft, labels: [.labels[].name]}'` shows `draft: false` and `e2e`. The PROGRESS row says `Done (#<n>)` (not checked for FINAL). `git status -sb` shows nothing ahead of origin. Report the PR URL in one line.

## Body template

```markdown
## Phase 1 / P<NN>: <prompt title>

<One sentence: what this prompt delivers.>

### Tickets

| Ticket | Status | Verified by |
|---|---|---|
| WF-NNN <title> | Done | <test files, and the summary line from this session> |
| WF-NNN <title> | Code done, owner verification pending | <the criterion that needs a device, account, key or person, and the HUMAN_TASKS row> |

### Opus review

| Step | Verdict (agent, time) |
|---|---|
| <step id> | APPROVE (<agent>, <time>) |

### Checks

- Lint and tests: <summary lines; for a setup unit, the `node scripts/spec-lint.mjs` and dash grep results instead>
- Local run check (`AI_PROVIDER=fake`): <pass, or "not due before P06">
- Month gate: <month N, verdict, `docs/gates/month-N.md`; omit when none is due>

### Owner tasks added

- <HUMAN_TASKS row, one line each, or "None">

### Decisions

- <DECISIONS row, one line each, or "None">

### Deferred

- <item and why, or "None">

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

A setup unit uses the same template with the heading `## Setup / <UNIT>: <title>`, and the setup tickets (`S1.1`) in the Tickets table. FINAL uses the heading `## Phase 1 / FINAL: completion check`. The attribution line is the last line of every body.

## Windows notes

Use Git Bash. Put `MSYS_NO_PATHCONV=1` in front of any `gh api /repos/...` call (or drop the leading slash), or Git Bash rewrites the path. Write temp files under `.autopilot/tmp/`, never `/tmp`.
