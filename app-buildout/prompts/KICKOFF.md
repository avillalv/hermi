# Kickoff: start (or resume) the Phase 1 build

The autopilot builds Phase 1 for you. A Node program, the driver (`scripts/autopilot/run.mjs`), runs a fresh Claude Code session for every step: first S1 to S3 fix the spec, then the 28 build prompts run in order, then a final check. Each session plans, builds one ticket, gets it reviewed and records what it did in git, `PROGRESS.md`, `HUMAN_TASKS.md` and `DECISIONS.md`, so a restart, a crash or a usage limit loses nothing. Sonnet 5.5 writes the code and Opus 5.5 plans and reviews, and every ticket needs an Opus approval. The session rules are in [AUTOPILOT.md](AUTOPILOT.md) and the build rules in [00-orchestrator.md](00-orchestrator.md).

The driver merges, not the AI. It waits until the check named `ci` has passed on each pull request, confirms the Opus verdicts it needs (every ticket, the final gate, and any ci-fix or late ship change that no ticket review covered), looks once more that nothing has stopped the pull request, then squash-merges and deletes the branch. This is deliberate: Claude's auto mode refuses to merge a pull request that no human approved. You asked for automatic merges, so a plain program does it, and only after those checks pass. Because the driver merges with your own login, branch protection on `main` (the `ci` check required, administrators included) is what makes a merge wait for a green `ci`, so the driver refuses to start without it. Sessions are blocked from merging, force-pushing and pushing to `main`.

## Before you start (about 20 minutes, once)

Do these in order, in a terminal on this PC. [HUMAN_TASKS.md](HUMAN_TASKS.md) has the same list with the later tasks.

1. Install the GitHub CLI.

```bash
winget install --id GitHub.cli -e
```

2. Close and reopen the terminal and restart the Claude app, so `gh` is on the path, then check it.

```bash
gh --version
```

3. Log in (choose GitHub.com, HTTPS, and log in with the browser).

```bash
gh auth login
```

4. Let git use that login.

```bash
gh auth setup-git
```

5. Add the `workflow` scope the driver needs.

```bash
gh auth refresh -s workflow
```

6. Protect `main` once the setup pull request that adds the `ci` check has merged. Require a pull request with 0 approvals, require the `ci` check, apply the rules to administrators (you are one), allow squash merges only and delete branches after merge. The driver checks all of this before every session and stops with exit 2 and the exact fix if any part is missing. In the browser: GitHub, `avillalv/hermi`, Settings, Branches, add a classic branch protection rule for `main`: tick "Require a pull request before merging" and leave "Require approvals" off, tick "Require status checks to pass before merging" (add `ci`), and tick "Do not allow bypassing the above settings" (include administrators). Or from the terminal, one command each:

```bash
gh api -X PUT repos/avillalv/hermi/branches/main/protection -F "required_status_checks[strict]=false" -f "required_status_checks[contexts][]=ci" -F enforce_admins=true -F "required_pull_request_reviews[required_approving_review_count]=0" -F restrictions=null
```

```bash
gh api -X PATCH repos/avillalv/hermi -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false -F delete_branch_on_merge=true
```

7. Confirm secret scanning and push protection are on. Both should say `enabled`; if not, turn them on in Settings, Code security.

```bash
gh api repos/avillalv/hermi --jq .security_and_analysis
```

8. Let the setup script reach your local PostgreSQL 18 service as `postgres` without a password in the repo. Create the folder, then open the file in Notepad, type the single line `localhost:5432:*:postgres:YOUR_POSTGRES_PASSWORD` (your own password) and save.

```bash
mkdir -p "$APPDATA/postgresql"
```

```bash
notepad "$APPDATA/postgresql/pgpass.conf"
```

9. Turn off extra usage, so the build can never spend money: claude.ai, Settings, Usage, switch "Extra usage" off. The driver also stops if it ever sees extra usage.

10. Keep the PC awake while it works. Sleep never while plugged in:

```bash
MSYS_NO_PATHCONV=1 powercfg /change standby-timeout-ac 0
```

```bash
MSYS_NO_PATHCONV=1 powercfg /change hibernate-timeout-ac 0
```

Then pause Windows updates for 5 weeks: Settings, Windows Update, Pause updates.

Claude Code is already installed and logged in on this PC (version 2.1.288, claude.ai Max). Nothing else is needed to build: no API key and no accounts. The build runs on fakes and a fake AI provider; the only real AI calls are the final `hermi ai-smoke`, through your own Claude CLI. Real evals and API costs need a key later (see [HUMAN_TASKS.md](HUMAN_TASKS.md)).

## Start

Run these four commands in order from a standalone PowerShell or Windows Terminal window opened at the repo root, not the Claude app's terminal tab, which closes with the app and would stop the driver. Do not work in the same checkout or run `npm run dev` while it runs: before every session the driver stops stray Hermi dev servers on ports 8100 and 5173, stashes uncommitted changes and switches to `main`. Use a separate clone for your own edits. `node scripts/autopilot/run.mjs --help` lists every flag.

1. Dry run. It runs every preflight check (including the branch protection on `main`), changes nothing, and prints the next unit and the exact command. It prints every check even when some fail; each failure comes with its fix.

```bash
node scripts/autopilot/run.mjs --dry-run
```

2. Canary. Four short sessions that prove the model pins, auto mode, the denial counting and both guard hooks (a `cat .env.canary` must be blocked by the bash guard, and a `general-purpose` agent on Opus by the agent guard). It uses a little of your quota.

```bash
node scripts/autopilot/run.mjs --canary
```

3. Once. It runs exactly one unit, merges it and exits. The first time it is S1, the first spec fix, so you see every mechanism once: plan, ticket sessions, Opus approvals, ship, `ci`, the merge and `.autopilot/state.json`. To prove resume, press Ctrl+C in the middle of a ticket and run the same command again. Add `--unit <id>` to run a named unit.

```bash
node scripts/autopilot/run.mjs --once
```

4. Full run. S2, S3, prompts 01 to 28 and the final check, until it finishes or stops.

```bash
node scripts/autopilot/run.mjs
```

To check the driver itself at any time, run its tests. They take about 8 minutes because the simulation tests run whole units end to end; set the environment variable `AUTOPILOT_SKIP_SIM` to `1` to skip that simulation (about 4 seconds). Use the quoted glob, because the directory form fails on Node 22.14.

```bash
node --test "scripts/autopilot/**/*.test.mjs"
```

## Watch

- `node scripts/autopilot/status.mjs` shows the current unit, the step, the pull request and the last stop.
- `.autopilot/logs/` has one JSONL log per session; the newest file is the live one.
- GitHub: `gh pr list` shows one pull request per unit (draft while it builds, ready when shipped, merged by the driver).
- Ask any Claude session "autopilot status". The `autopilot-status` skill reads the state, `PROGRESS.md`, the open pull requests and the last lines of the newest log.

## Stop and resume

Press Ctrl+C in the driver window to stop. It ends the running session and its processes. Run the same command again to resume: the state is in `.autopilot/state.json`, git, GitHub and `PROGRESS.md`, and the driver takes over the stale lock and picks up the interrupted unit where it stopped.

When the driver stops by itself it prints why and exits with a code:

| Code | Meaning | What to do |
|---|---|---|
| 0 | Done: every unit is finished, or the `--once` or `--unit` unit is merged | Nothing (after the full run, read `docs/gates/phase-1-complete.md`) |
| 1 | Any other error: a preflight check failed (for example `claude` or `gh` not installed, a session file not on `main`, another driver already running, a port held by another program), auto mode is not available for the session, a canary failed, a bad flag, or something unexpected | Read the message, which names the fix, then run again. If auto mode is the problem, fix its cause, or rerun with `--permission-profile dontask` to opt in to the narrower dontAsk profile (no classifier; it runs only what `scripts/autopilot/settings-dontask.json` allows: read that list first). The driver never switches to it by itself |
| 2 | Stopped with an owner action: a session or the driver found one of the stop reasons. The reason and the action are printed and saved in `.autopilot/stop.json` | Do the action. Then clear the signs of the stop that exist. A stop of a unit always writes `.autopilot/stop.json` (delete it) and, once a pull request exists, labels it (remove the label with `gh pr edit <n> --remove-label autopilot:stopped`). Only a stop by a session also sets the `Stopped (...)` row in `PROGRESS.md` on its branch (set it back to `In progress (<branch>)`); a stop by the driver itself (three failed attempts, red CI, a failed merge, a missing Opus verdict, a change under `scripts/autopilot/`) leaves that row alone. A failed preflight check (for example no protection on `main`) leaves none of the three: do the printed fix. Then run again. The run halts again at once if a sign remains, and the unit starts with a fresh set of attempts |
| 3 | Permission denials: 5 in one session. The denied commands are printed | A command or rule is missing from `scripts/autopilot/settings.json`. Fix it yourself (sessions cannot), then run again |
| 4 | Extra usage is on | Turn extra usage off in claude.ai settings, then run again |
| 5 | Authentication: `claude` or `gh` is logged out, the `gh` token lacks the `workflow` scope, or a session started on an API key | Run `claude auth login` (or `gh auth login`, then `gh auth refresh -s workflow`) and remove `ANTHROPIC_API_KEY` if it is set, then run again. Auth errors are never retried |
| 130 | You pressed Ctrl+C | Run again when you want to resume |

After an exit 3 caused by an `npm install` or `uv add` of a package that is not on the closed "Hermi Stack Packages" list under `autoMode.allow` in `scripts/autopilot/settings.json`, add the package name there on `main` (sessions cannot edit that file; `knowledge/autopilot.md` has the steps) and run again.

At a usage limit the driver does not exit. It sleeps until the limit resets, then resumes the session. The weekly Opus limit pauses the whole run.

## What to expect

- Units in order: S1, S2, S3 (the spec fixes), then prompts 01 to 28, then the final check. That is 28 pull requests for the build, 3 for the spec fixes and 1 for the final check, each merged into `main` when `ci` is green.
- Days to weeks. The roadmap estimates about 560 hours of human work, and your plan's usage limits add pauses; the driver waits and resumes by itself. Using the app through `claude_cli` while the build runs draws on the same subscription.
- Some steps only you can do: accounts, keys, the iOS signing setup, TestFlight and App Store submission. They collect in [HUMAN_TASKS.md](HUMAN_TASKS.md) in the order you should do them, and the build never waits for them.

## Interactive alternative

To run one unit by hand in a Claude Code session: start `claude --model claude-opus-5-5`, paste the contents of [AUTOPILOT.md](AUTOPILOT.md), then a task line such as `MODE=plan UNIT=S1 ATTEMPT=1`. Run the modes in order (plan, then one ticket session per step on `claude-sonnet-5-5`, then ship), each in a fresh session, and merge the pull request yourself when `ci` is green.
