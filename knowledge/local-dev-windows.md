# Local development on Windows

How to run Hermi on this machine: Windows 11, Git Bash and PowerShell 5.1, no Docker. The commands are the ones
the spec defines. Prompt 01 onward fills in their exact output, so a "missing script" error means the prompt that
writes it has not run yet. Variables are in `knowledge/env-and-accounts.md`.

## What is on this machine (checked 2026-10-03)

| Tool | State | Notes |
|---|---|---|
| Node, npm | Node 22.14, npm 10.9 | The root scripts are Node scripts |
| uv | 0.12.19 | Python 3.13.2 is installed (`...\Programs\Python\Python313`) and the system Python is 3.14. The project pins 3.13 (`.python-version`, from prompt 01), so uv uses 3.13 |
| PostgreSQL 18 | Windows service `postgresql-x64-18`, running | Binaries in `C:\Program Files\PostgreSQL\18\bin`. `psql` is not on PATH, so `npm run db:init` finds that folder itself |
| Claude Code | 2.1.288, native `~\.local\bin\claude.exe` | Signed in through claude.ai (Max). `claude auth status` prints `loggedIn` and `subscriptionType` |
| Git Bash, PowerShell 5.1 | Present | Either works for npm scripts |
| `gh` | Not installed yet | Owner step 0. Only the autopilot needs it |
| Docker, Redis | Not needed | `infra/docker/compose.yml` stays optional |

## One time: the PostgreSQL superuser password

`npm run db:init` connects as `postgres` once, to create the roles and databases. It reads the password from
`%APPDATA%\postgresql\pgpass.conf`, which libpq uses on its own, so nothing is prompted and nothing is stored in
the repo, in `.env` or in chat. The file has one line, with your own password:

```
localhost:5432:*:postgres:<your password>
```

Write it as plain ASCII, for example in PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:APPDATA\postgresql" | Out-Null
Set-Content -Path "$env:APPDATA\postgresql\pgpass.conf" -Value 'localhost:5432:*:postgres:<your password>' -Encoding ascii
```

PowerShell 5.1's `>` and `Out-File` write UTF-16, and `Set-Content -Encoding UTF8` adds a byte-order mark. Either
one breaks the file for libpq.

## The commands

From the repo root. Defined by the spec and the tickets (WF-004 and the prompts); the exact output comes with them.

| Command | What it does |
|---|---|
| `npm run doctor` | Reports tools, ports, the database, and which `.env` variables are set or missing. Never prints a value |
| `npm run setup` | The one-time setup, safe to rerun: prerequisites, `.env` from `.env.example`, generated secrets, installs, `db:init`, migrations, `hermi seed --demo` |
| `npm run db:init` | Creates the roles and the `hermi` and `hermi_test` databases (`infra/db/bootstrap.sql`). Idempotent |
| `npm run dev` | The API on 8100, the worker and the web app on 5173, with reload |
| `npm run lint`, `npm test` | Lint (ruff, import-linter, oxlint, tsc) and the pytest and vitest suites |
| `npm run test:api`, `test:web`, `test:e2e`, `test:e2e:smoke`, `test:kit` | The split suites. `test:kit` is the design-kit check |
| `npm run gen:api`, `gen:shared` | Regenerate the API types and the shared constants. Commit the result |
| `npm run evals`, `smoke:live` | Live runs. `npm run evals` spends model calls only with `EVALS_LIVE=1`; `npm run smoke:live` always does |
| `npm run ios:sync` | Sync the web build into the Capacitor project. iOS builds run on CI (`knowledge/ios-builds-on-ci.md`) |

Pytest and the Playwright suites reset `hermi_test`, never `hermi`. Reseed the test database before looking at the
UI on it afterwards.

## Ports, sign-in and data

- **Ports.** The API is on 8100, so it can sit beside the old Trip Planner on 8000. The web app is on 5173.
- **Sign-in.** `AUTH_MODE=dev` mints local tokens for seeded personas (Free, Plus and an admin) and shows a persona
  picker. `ADMIN_AUTH_MODE=dev` does the same for the admin console. Both are refused outside `local` and `ci`.
  Playwright uses them. Supabase and Cloudflare Access are the real paths and need accounts.
- **Data.** `npm run setup` seeds a demo trip ("Lisbon in March") and the sample trips for Discover.
- **No keys needed.** Fares and places are fixtures (`PROVIDERS_MODE=fake`), email goes to `.data/outbox` and files
  go to `.data/storage`. To use a real key, add it to `.env` and set `PROVIDERS_MODE=live`; `npm run doctor` lists
  what is missing.
- **AI.** Your `.env` sets `AI_PROVIDER=claude_cli`, which runs your own signed-in `claude.exe`
  (`knowledge/ai-provider-claude-cli.md`). Tests, CI and the build's smoke runs force `AI_PROVIDER=fake`. The
  CLI answers only to loopback, so a phone on your network cannot use it.

## Windows hazards

- **Event loops.** psycopg async needs the Selector event loop, and asyncio subprocesses need the Proactor loop.
  `cli.py` sets the Selector policy on win32, so run `claude` with `subprocess.Popen` in a thread, never an asyncio
  subprocess.
- **A running app locks its launcher.** `uv sync` cannot replace `hermi.exe` while it runs ("Access is denied").
  The dev scripts use `uv run --no-sync`. Install and sync with the app stopped. The old Trip Planner learned this
  the hard way.
- **Whole process trees.** Stopping only a parent leaves children holding ports and files. Kill the tree
  (`taskkill /T /F /PID <pid>`, or psutil in code).
- **Command-line length.** About 32k characters for a process, about 8k through `cmd.exe`. Keep system prompts in a
  file, put the prompt on stdin and use `--max-turns`.
- **Native `claude.exe`, never a `.cmd` shim.** A shim runs through `cmd.exe`, which re-parses the arguments.
- **Shell syntax in npm scripts.** npm runs scripts through `cmd.exe` on Windows, so `FOO=1 cmd`, `$VAR` and
  chained shell tricks fail. Root scripts are Node scripts (`node scripts/x.mjs`) that spawn what they need.
- **Quoting.** PowerShell 5.1 strips double quotes when it passes an argument to a native program, so a JSON schema
  on a `claude.exe` command line arrives broken. Use Git Bash, or a Python list passed to `Popen`.
- **Line endings.** The repo is LF (`.gitattributes`: `* text=auto eol=lf`). `*.ics` stays as is (`-text`) so
  calendar golden files keep their CRLF bytes, and `.cmd`, `.bat` and `.ps1` stay CRLF. Do not let an editor
  convert them.
- **File encodings.** PowerShell 5.1 `>` writes UTF-16. Use `-Encoding ascii` or write config files from Node.
- **Tests that need POSIX.** Mark them `posix_only`. They skip on Windows and always run in Linux CI, and a nightly
  `windows-latest` job covers the Windows side.
- **The Microsoft Store `python.exe` stub.** uv may warn that it failed to inspect it. The warning is harmless.

## When something fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `db:init` cannot connect | The service is stopped, or `pgpass.conf` is missing or wrong | `Get-Service postgresql-x64-18`, start it, check the file |
| Port 8100 or 5173 in use | An earlier dev server is still running | `Get-NetTCPConnection -LocalPort 8100 -State Listen`, then stop that process |
| `uv sync` says "Access is denied" | The app is running and holds its launcher | Stop the app, or use `uv run --no-sync` |
| AI answers fail with a sign-in message | `claude` is not signed in, or its login expired | Run `claude`, type `/login`, check `claude auth status` |
| AI answers fail with a usage message | The 5 hour or weekly limit of the subscription is used up | Wait for the reset. The autopilot shares this quota |
