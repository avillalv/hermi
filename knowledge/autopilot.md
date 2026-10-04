# Autopilot: running the unattended Phase 1 build

How the build runs without you, and how to start, watch, stop and resume it. The driver is
`scripts/autopilot/run.mjs` (Node standard library only). The prompt its sessions follow is
`app-buildout/prompts/AUTOPILOT.md`, and the rulebook is `app-buildout/prompts/00-orchestrator.md`. If this page and
`node scripts/autopilot/run.mjs --help` disagree, the script wins: fix this page.

## What it does

It builds one unit at a time, in the order of the `PROGRESS.md` tables: S1 to S3 (the setup prompts that fix the
spec), 01 to 28 (the build prompts), then FINAL (the completion check). One unit is one branch and one pull
request. A unit runs as a series of short headless `claude -p` sessions, not one long conversation.

| Step | Mode | Model | What happens |
|---|---|---|---|
| 1 | `plan` | Opus | Reads the prompt and its tickets, writes the plan under "Current prompt" in `PROGRESS.md` and in `.autopilot/plans/<unit>.json`, creates the branch and a draft PR. Resumes safely when a branch or PR already exists. |
| 2 | `ticket`, one session per ticket or sub-step | Sonnet | `sonnet-coder` writes tests first, then code. `opus-reviewer` ends with `VERDICT: APPROVE <id>` or `REQUEST_CHANGES <id>`. After 3 rounds `opus-judge` decides. Commit `<step id> <title>` (for example `WF-005.1` or `S1.1`) and push. |
| 3 | `ship` | Sonnet | The local run check, the month gate when due, the records (`PROGRESS.md`, `HUMAN_TASKS.md`, `DECISIONS.md`, knowledge, findings), then `gh pr ready` and the `e2e` label. |
| 4 | the driver | none | Waits until the check named `ci` has passed (it polls `gh pr checks --json`; a green lint job, a skipped `ci` or an empty list never counts), looks once more at the PR, squash-merges, deletes the branch, pulls `main`. |
| 5 | `ci-fix`, only on red | Sonnet | Reproduces and fixes. After one failed fix `opus-judge` finds the root cause; before it ends, `opus-judge` reviews the ci-fix diff. After 3 on one PR the driver stops. |

FINAL has no plan session and no ship session. One `final` session (Opus) opens `phase1/final` and its draft PR
itself, runs the completion check, writes `docs/gates/phase-1-complete.md`, gets the completeness verdict from
`opus-judge` and marks the PR ready; steps 4 and 5 then apply as usual.

The driver checks the facts itself: the ticket commit was pushed, an Opus APPROVE exists for it (read from the
forwarded subagent stream), and the outcome of a merge is read from `gh pr view --json state,mergedAt`, never from
what a model says. A plan, ticket, ship or final session that leaves a fact missing is run again with a
`RETRY_NOTE` that names it, up to 3 attempts, and then the unit stops (exit 2).

### Verdicts the merge needs

A verdict counts only as the exact last line `VERDICT: APPROVE <id>` of an `opus-reviewer` or `opus-judge`
subagent running on Opus. An Agent result that shows a mid-run switch to another model (`modelsUsed`), a hand-back
that was not delivered cleanly (`handback` other than `send`), an unnamed agent or another agent type is ignored. A
session can earn only the id of its own task, and each approval is stored with its branch and PR.

| Id | From | Needed for |
|---|---|---|
| `<step id>` (`WF-023`, `S1.2`, `WF-005.1`) | `opus-reviewer` (or `opus-judge` after an accept) | every step of the plan |
| `ship-<unit>` (`ship-07`) | `opus-reviewer` | a unit whose ship diff (everything pushed since the first ship session) touches more than `docs/`, the three status logs, `knowledge/`, `findings/`, `.claude/skills/`, `apps/web/src/lib/api/` and the seed |
| `ci-fix-<pr>-<n>` (`ci-fix-12-2`, n is `ATTEMPT=`) | `opus-judge` | a PR whose head moved during a ci-fix session (the newest attempt covers all ci-fix commits), and always the fix PR of a red `main` |
| `FINAL` | `opus-judge` | the final PR, with decision `complete` |

Writing a new plan clears every approval, and a ci-fix, ship or final attempt must produce its own verdict after its
changes (the driver forgets the old one first). Right before `gh pr merge` the driver looks again, because hours may
have passed: no `.autopilot/stop.json`, no `autopilot:stopped` label, the PR is not a draft, the `Done (#n)` row (or
the gate file for FINAL) is still on the branch, nothing changed under `scripts/autopilot/`, and every verdict above is
in. Any failure stops the unit (exit 2).

## Why every step is a fresh session

Claude Code cannot compact on demand: it auto-compacts only when the window fills, and the model cannot run
`/compact`. The context reset is therefore a new headless session for every step. Nothing important lives only in a
conversation: state is in git, GitHub, `PROGRESS.md` and `.autopilot/state.json`, and the appended prompt
(`AUTOPILOT.md`) re-teaches every session the rules.

## Models

Plan and FINAL sessions run `claude-opus-5-5`. Ticket, ship and ci-fix sessions run `claude-sonnet-5-5`. Inside
Sonnet sessions every verdict comes from the `opus-reviewer` and `opus-judge` subagents, and the reading and coding
from `sonnet-researcher` and `sonnet-coder`. A PreToolUse hook allows only those four agents (plus `general-purpose`
and `Explore`, on Sonnet only), rejects a model that does not match the agent and rejects any Agent call that sets
`isolation` or `cwd`, and the aliases are pinned with
`ANTHROPIC_DEFAULT_OPUS_MODEL` and `ANTHROPIC_DEFAULT_SONNET_MODEL`. When the weekly Opus limit is hit the run
pauses, so judgement never falls back to Sonnet. Product AI is separate: tests, CI and the build's local smoke runs
force `AI_PROVIDER=fake`, so the build never spends your quota on product answers.

## The files

| Path | What it is |
|---|---|
| `.autopilot/state.json` | The driver's memory: the current unit and phase (`plan`, `ticket`, `ship`, `ci`, `merged` or `stopped`), branch and PR, the Opus approvals by verdict id (each with its agent, branch and PR), the verdict ids still required (`ship-<unit>`, `ci-fix-<pr>-<n>`), the ship diff's base commit, attempt counts, one record per session run (mode, step, id, model, result, log path) and any pause or stop. The fields are defined by `driver/ctx.mjs`; read the file, not this page. Gitignored. |
| `.autopilot/plans/<unit>.json` | The plan: tickets, sub-steps, `Kit:` mockups, migrations, owner-pending criteria. A re-plan keeps and repairs the old file, and a ticket session may split a step by editing it (the driver reloads it after every ticket session). For FINAL the driver writes it once the final session has opened the PR |
| `.autopilot/logs/` | One JSONL stream per `claude` run, named `<unit>-<mode>[-<step>]-<yyyymmddThhmmss>.jsonl`, with the driver's own records mixed in. The driver never prunes it, so it grows with every session; delete it between runs if you like |
| `.autopilot/stop.json` | Written when the run stops with an owner action. Deleting it is part of resuming. A file that exists but is not valid JSON still counts as a stop. |
| `.autopilot/lock` | A PID lock. A stale lock is taken over, so a crash does not block the next start. The takeover kills the recorded `claude` child only if its command line carries `--name hermi-`. |
| `scripts/autopilot/settings.json` | Auto-mode rules, denies, hooks and env, passed to every session with `--settings`. It sets `disableClaudeAiConnectors`, and every session also runs with `--strict-mcp-config`, so your claude.ai connectors (Gmail, Drive) are not loaded |
| `scripts/autopilot/settings-dontask.json` | The opt-in profile (`dontAsk` mode, no classifier, a fixed allow list), used only with `--permission-profile dontask`. It allows `git`, `gh pr` (create, view, list, checks, ready, edit), `gh run`, `gh label` (no `gh api`), `npm run`, `npm ci`, `npx` for playwright, cap, tsc, vitest, eslint, prettier and stylelint, `uv run`, `node scripts/*`, `timeout`, the shell basics (`ls`, `cat`, `grep`, `find`, `mkdir`, `cp`, `mv`, `rm`, `echo`, `head`, `tail`, `wc`, `sort`, `diff`, `sed`, `touch`, `cd`, `pwd`, `which`), `curl` to localhost, the PostgreSQL 18 client tools (`psql`, `createdb`, `dropdb`, `createuser`, `dropuser`, `pg_dump`, `pg_restore`), the Edit and Write tools, `Read(./**)`, Glob, Grep, WebSearch, Agent and Skill. It has no global `WebFetch`, no `npm install` and no `uv add`. Its deny list is the same as `settings.json` |
| `scripts/autopilot/hooks/agent-guard.mjs`, `bash-guard.mjs`, `file-guard.mjs` | The hooks. Agents: only the four named ones (and `general-purpose` or `Explore` on Sonnet) with matching models, no `isolation` or `cwd`. Shell: blocks force pushes, pushes to `main` (also by a wildcard or `heads/main` refspec) or deleting a remote branch, merges, and `gh api` calls that change a ref, branch protection or a ruleset or pass a GraphQL query by file (also through `eval`, `iex`, `-EncodedCommand`, a backslash or backtick in the word, a `$` variable in a command word or refspec, `git -c remote.*`, `gh alias`), `git clean -x`, `git stash clear`, `.env` as a file operand, `DROP` and `TRUNCATE` outside `hermi*` databases, `rm` outside the repo, `--admin`, and writes under `scripts/autopilot/`, `.claude/agents/`, `.claude/settings*.json` and `.mcp.json`. Files: blocks Read, Grep and Glob on `.env` and `.env.*` (not `.env.example`) |

Sessions never edit anything under `scripts/autopilot/`, `.claude/agents/`, `.claude/settings*.json` or `.mcp.json` (the driver stops a unit whose branch changes one, and refuses to start while a `.claude/settings.local.json` exists, because it can disable the hooks). If a rule there needs changing, you change it.

## Commands

Run them from a standalone PowerShell or Windows Terminal window opened at the repo root, not the Claude app's
terminal tab: the tab closes with the app and would take the driver with it. The first four are the start sequence,
in this order.

```
node scripts/autopilot/run.mjs --dry-run   # every preflight check, nothing changes; prints the next unit and the exact command
node scripts/autopilot/run.mjs --canary    # four short real sessions that prove the model pins, auto mode, both guard hooks and denials
node scripts/autopilot/run.mjs --once      # build one unit, merge it, then exit 0
node scripts/autopilot/run.mjs             # the full run: S1 to S3, 01 to 28, FINAL
node scripts/autopilot/run.mjs --unit 07   # only this unit (S1..S3, 01..28 or FINAL), even if PROGRESS.md says Done (a Stopped row still stops it)
node scripts/autopilot/run.mjs --permission-profile dontask   # opt in to the dontAsk profile; any other command takes it too
node scripts/autopilot/status.mjs          # where it is now
node --test "scripts/autopilot/**/*.test.mjs"   # the driver's own tests
```

The tests take about 8 minutes on Windows, because `driver.test.mjs` simulates whole units end to end against a fake `claude`
and a fake `gh`. Set `AUTOPILOT_SKIP_SIM=1` (in PowerShell, `$env:AUTOPILOT_SKIP_SIM = "1"`) to skip that simulation
(about 4 seconds). Use the quoted glob: the directory form fails on Node 22.14. CI runs the same command.

The dry run runs every preflight check and changes nothing. It checks Node 22 or newer, `claude.exe` and `gh`, the
`gh` login (with the `workflow` scope), the `claude` login (a subscription, not an API key), squash merging and push
rights on the repository, protection on `main`, that the files a session needs are on `main`, that `.autopilot/` is
gitignored, that no `.claude/settings.local.json` exists, and that nothing is running or stopped (the lock, `.autopilot/stop.json`, a PR labelled
`autopilot:stopped`, an active PR-train handoff). Protection is a hard requirement (a real run exits 2 with the exact
fix, and the dry run prints a FAIL and goes on to print everything else): `main` must be protected, require a pull
request with 0 approvals (else a commit whose `ci` passed can be pushed to `main` directly), require the status check
`ci` and apply to administrators (`enforce_admins`, "Do not allow bypassing the above settings"). It must not require
approving reviews, because the driver cannot approve. The driver merges with your own token, and protection is the only
thing that makes a merge wait for a green `ci`. The exact command is in `KICKOFF.md` step 6. Then the dry run prints the next unit and the exact `claude` command and environment its first
session would get. A red latest `ci` run on `main` is not a failure: the driver repairs it first with ci-fix sessions
(3 rounds, then it stops).

The canary runs four short Sonnet sessions with the real flags and settings: (a) `opus-judge` runs on Opus,
`sonnet-researcher` on Sonnet and the session is in auto mode (the `init` event); (b) `git status --short`,
`node --version`, `npm --version`, `uv --version` and `node scripts/spec-lint.mjs` run with zero permission denials;
(c) `cat .env.canary` (a decoy name, so a failing guard can never expose the real file) is blocked by the bash-guard
PreToolUse hook (a permission denial alone does not pass); (d) a `general-purpose` agent on Opus is blocked by the
agent-guard hook. It exits 1 if any check fails.

Before every session the driver stops stray Hermi dev servers on ports 8100 and 5173 (another program holding either
port stops the run with exit 1), so do not run `npm run dev` while it runs. The first real attempt is `--once` on S1:
inspect the plan, the ticket sessions, the Opus approvals, the PR, the driver's merge and `state.json`, then start
the continuous run. Expect days to weeks.

## Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | Done: Phase 1 is complete, the `--once` or `--unit` unit merged, or the dry run or canary passed | After the full run, read `docs/gates/phase-1-complete.md` |
| 1 | Any other error: a preflight check failed (`claude` or `gh` missing, a session file not on `main`, another driver running, a port held by another program), auto mode is not available for the session (the driver never falls back by itself; see below), a `git` or `gh` command failed, a canary failed, a bad flag | Read the message, which names the fix, then rerun |
| 2 | Stopped with an owner action | Read the printed message and `.autopilot/stop.json`, do what it says, then resume (below) |
| 3 | Permission denials: 5 in one session | The driver prints them. A command or rule is missing from `settings.json` (or `settings-dontask.json`). Fix it yourself (sessions cannot), commit it to `main`, then rerun. For a package install, see the allow list below |
| 4 | Extra usage (overage) was in use during a session | Turn extra usage off in claude.ai settings, then rerun |
| 5 | Authentication: `claude` or `gh` is logged out, the `gh` token lacks the `workflow` scope, or a session started on an API key | Run `claude auth login` (or `gh auth login`, then `gh auth refresh -s workflow`) and remove `ANTHROPIC_API_KEY` if it is set, then rerun. Auth errors are never retried |
| 130 | Ctrl+C | The driver kills the running session and releases the lock. Rerun to resume |

The package allow list is closed. Auto mode lets a session run `npm install` or `uv add` only for the names in the
"Hermi Stack Packages" entry of `autoMode.allow` in `scripts/autopilot/settings.json` (a name ending in `/*` covers
that npm scope, and `@types/<listed package>` is covered). Any other package is denied, and the denials end in exit
3, or in a session stop with reason `denials` (exit 2) when the same command is denied twice. Sessions cannot edit
the file, so once you decide the package belongs in the build, add its name to that entry. Commit the change to
`main` from a separate clone, because the driver stashes an uncommitted edit in its own checkout before every
session. If the unit already has a branch on origin, merge `origin/main` into it (`git merge origin/main`, then
push), because a session runs with the copy of `settings.json` on the branch it works on; a commit made on the
branch itself would be flagged as a session edit and stop the run. Keep the entry under 3000 characters, run the
tests with `AUTOPILOT_SKIP_SIM=1`, and rerun. The opt-in `dontAsk` profile has no `npm install` or `uv add` at all (only
`npm run *`, `npm ci` and `uv run *`), so dependency work needs rules added to it by hand.

A session stops (exit 2) only for a closed list of reasons, each with a code in `stop.json`:

| `reason` | When |
|---|---|
| `merge-impossible` | Branch protection needs a human review, or a session cannot push or open a PR |
| `ci-fix-failed` | Three ci-fix attempts on one PR failed |
| `spec-conflict` | Two documents disagree on money, security or a data model later prompts rely on, and the precedence order does not settle it |
| `real-money` | An action would spend real money beyond ordinary development API use, or touch production data |
| `denials` | The same command is denied twice, or the driver reports repeated denials |
| `gate-failed` | The `month-gate` verdict is `stop` |

A stopping session writes `.autopilot/stop.json` as `{"unit", "reason", "ownerAction"}` (the owner action is one or
two sentences), sets the unit's `PROGRESS.md` row to `Stopped (<reason>)` on its branch, pushes, and labels the PR
`autopilot:stopped`. Missing keys, accounts or a device, a flaky test, a disputed verdict and a usage limit are
never stops. The driver also stops a unit on its own (exit 2) when a plan, step or ship session still lacks its facts
after 3 attempts, CI stays red after 3 ci-fix sessions, a merge fails, a verdict the merge needs is missing, something
changed between CI and the merge (see "Verdicts the merge needs"), a session changed `scripts/autopilot/`,
`.claude/agents/`, `.claude/settings.json` or `.mcp.json`, a plan session committed anything but the `PROGRESS.md` row, or
the branch holds a step commit (`WF-nnn`, `Sn.k`) that no Opus verdict covers. It
writes the same `stop.json` (with a free-text reason) and the label, but leaves `PROGRESS.md` alone. After you clear a
stop the unit gets a fresh set of attempts (steps, plan, ship and ci-fix), not the 3 it had used.

## Usage limits

The driver reads the `rate_limit_event` in each stream: `rateLimitType` (`five_hour` or `seven_day`),
`utilization`, `resetsAt` and `overageStatus`. At a limit it sleeps until `resetsAt` plus a minute (30 minutes when
the reset time is unknown), then resumes the session with `--resume <session_id>`. The weekly Opus limit
(`seven_day_opus`) pauses the whole run. A pause is not a failure and needs nothing from you. As of 2026-10-03 this
account reports `overageStatus: rejected` with reason `out_of_credits`, so the build cannot spend extra usage, and
keeping extra usage off in claude.ai settings keeps it that way. Your own use of the dev app through `claude_cli`
shares the same subscription and eats build quota.

Two guards sit beside the limits. A watchdog kills a session's process tree after 45 minutes without a stream event
or 5 hours in total, and the next attempt resumes that session (it counts as one of the 3 attempts). A session that
collects 5 permission denials stops the run (exit 3); a block by the driver's own guard hooks is listed but not
counted.

If auto mode turns out to be unavailable, the driver does NOT loosen anything by itself: it exits 1 with an owner
action. Fix the cause (auto mode needs a plan and a model that support it and no policy that disables it), or opt in
to the narrower `dontAsk` profile with `--permission-profile dontask` (no classifier; only the allow list in
`settings-dontask.json` runs, and the guard hooks stay on in both profiles). Read that list first.

A session the watchdog killed is resumed in its own working tree: the driver pushes its commits but does not stash or
check out anything before the resume, so uncommitted work survives.

## Intervening

- **Pause or stop.** Press Ctrl+C in the window (exit 130). The driver kills the running session and releases the
  lock. Nothing is lost, because state is on disk and in git. Starting again resumes: after a crash it takes over the
  stale lock, then it finishes or restarts the unit, and the `plan` session continues from an existing branch or PR.
- **Resume after a stop.** Do what `ownerAction` in `stop.json` says. Then clear the signs of the stop that exist: a
  stop of a unit always writes `.autopilot/stop.json` and, once a PR exists, puts the `autopilot:stopped` label on it
  (`gh pr edit <n> --remove-label autopilot:stopped`). Only a stop written by a session also sets the
  `Stopped (<reason>)` row in `PROGRESS.md` (its stop commit put it on the unit's branch; set it back to
  `In progress (<branch>)`); a stop by the driver leaves the row alone. A failed preflight check (no protection on
  `main`, an active PR-train handoff) leaves none of the three: do the printed fix. Then rerun
  `node scripts/autopilot/run.mjs`. The run halts again at once if a sign remains, and the unit starts with fresh
  attempts.
- **See what it did.** `node scripts/autopilot/status.mjs`, the PR list on GitHub, the newest file in
  `.autopilot/logs/`, or ask any Claude session to use the `autopilot-status` skill, which reads the state, the
  progress table, the open PRs and the end of the newest log without loading the whole log. Branches are
  `phase1/pNN-<slug>`, `spec/sN-<slug>` for the setup prompts, `phase1/final`, and `fix/main-ci-<yyyymmdd>` when
  `main` itself goes red.
- **Do not work in the same checkout while it runs.** Before every session the driver pushes leftover commits,
  stashes what is uncommitted, switches to `main` and pulls. Use a separate clone for your own edits.

## Why sessions never merge

Auto mode deliberately blocks an AI from merging a pull request no human approved (its "Merge Without Review"
rule), and a headless session aborts after repeated classifier denials. Both were confirmed in the 2.1.288 binary.
So sessions are denied `gh pr merge`, and a plain program merges instead: only after the check named `ci` has passed
and every verdict listed under "Verdicts the merge needs" is in, from an Opus model. Because you asked for automatic merges, this is
the one place a program, not a model, holds the final say.

## Before you start

The ordered list is in `app-buildout/prompts/HUMAN_TASKS.md`. In short: install `gh` and log in with the
`workflow` scope; protect `main` (require a pull request with 0 approvals, require the `ci` check, include administrators,
squash only, auto-delete branches; the driver refuses to start without the first three; the command is in `KICKOFF.md`
step 6)
and confirm secret-scanning push protection; create `%APPDATA%\postgresql\pgpass.conf`; turn extra usage off in
claude.ai settings; set Windows sleep to Never while plugged in and pause updates for 5 weeks.

## What it will not do

It never merges from a session, never force-pushes or pushes to `main`, never reads `.env`, never loads your claude.ai connectors, never edits
`scripts/autopilot/`, never adds a dependency outside the spec's stack without an `opus-judge` decision (and auto
mode still denies a package that is not on the closed allow list), and never runs an interactive command. It never
spends real money: extra usage must be off, and the driver kills any session that draws on it and exits 4.
