# The Trip Planner base code

Hermi is built on top of the owner's existing single-household app, Trip Planner. This page says where it is, what
carries over, and which pieces now matter for the local AI provider and the native Windows setup. Where each file
actually landed after prompt 02 is in `docs/porting-map.md`.

## Where it is

- Local: `C:/Users/matic/code/trip-planner`.
- GitHub: `github.com/avillalv/trip-planner`. It is public (checked 2026-10-03), so a clone needs no access setup.
- In a build: cloned read-only to `.reference/trip-planner/`, which is gitignored
  (`git clone --depth 50 https://github.com/avillalv/trip-planner .reference/trip-planner`, then
  `git -C .reference/trip-planner pull --ff-only` to update). Never commit to it, push to it or edit it. Copy what
  you port into the Hermi layout and adapt it there; `git log` and `git blame` in the clone give context.
- Layout: the backend is Python 3.13 with uv in `backend/tripplanner/`, the frontend is Vite and React 19 in
  `frontend/src/`. It ran on Windows 11 with no Docker, passcode auth, a Claude Code CLI agent runner with an MCP
  bridge, and APScheduler.

## What to reuse, adapt and drop

`app-buildout/phase-1-launch/02-architecture.md` section 14 maps every module and says reuse, adapt or drop with
the reason. Do not copy that table here: it is the authority, and a second copy goes stale. The short version,
from `app-buildout/README.md` ("Reusing the existing Trip Planner code"):

- **Carries over:** flight route and fare logic, itinerary and lodging features, presentation mode, the design
  token plumbing (not the old passport colors), the Travelpayouts, Geoapify, Wikipedia and Frankfurter providers,
  the evidence rules in `services/agent_ingest.py`, and the agent prompts.
- **Does not:** passcode auth, APScheduler, Windows-only scripts, Tailscale sharing, and the MCP bridge.

After S1, section 14.1 also marks the Claude CLI runner pieces (`claude_cli.py`, the agent runner, the stream
parser, `smoke.py` and `fake_claude.py`) as Adapt for the local AI provider, built in WF-131 (prompt 12). Prompt 02
itself does not port them.

## What now carries over for the local provider and the native setup

Paths are under `backend/tripplanner/` unless they start with `backend/`, `frontend/` or `scripts/`, which are from
the repo root. All were confirmed on 2026-10-03. The provider side is in detail in
`knowledge/ai-provider-claude-cli.md`.

| Base file | Why it matters | Where it goes |
|---|---|---|
| `scripts/setup.mjs` (86 lines) | The model for `npm run setup`: a prerequisite check that says how to fix a miss (for example `winget install --id astral-sh.uv -e`), `.env` copied from `.env.example`, random values for blank secrets (`randomBytes(...).toString('base64url')`), then installs, then the database step. Uses `spawnSync` with `shell: true` on win32 because npm is a `.cmd` shim | `scripts/setup.mjs`. Changes: generate Hermi's secrets, run `db:init`, migrate and `hermi seed --demo`, and never prompt for a password |
| `setup_db.py` (79 lines) | The model for `db:init`: connect as the superuser, create or alter a role (`ALTER` when it exists), create the databases, a clear error when the superuser connection fails, then migrate | `infra/db/bootstrap.sql` run by `npm run db:init`, idempotent. Changes: the password comes from `pgpass.conf`, not `getpass` or `POSTGRES_SUPERUSER_PASSWORD`; several roles, with `hermi_owner` NOLOGIN |
| `services/claude_cli.py` | Finding `claude`, the stripped environment, `claude auth status`, `NO_WINDOW` | `apps/api/hermi/providers/ai/claude_cli.py` |
| `worker/agents/runner.py` | The `claude -p` runner: watchdog, stderr drain, stdin writer, process-tree kill, model guard, failure messages | `apps/api/hermi/providers/ai/` only: only providers spawn `claude`, so nothing goes to `hermi_worker/agents/` |
| `worker/agents/stream.py` | Turns stream-json into run events and keeps the `init` and `result` facts | `apps/api/hermi/providers/ai/` only, as the stream parser behind the `run_events` writer and the init assertions |
| `services/agent_ingest.py` | The trust boundary for AI output: `blocked_domain`, `source_problem`, observed-during-the-run, price bounds, rejection records | `modules/ai/ingest.py` (pure rules ported: `source_problem`, `price_in_bounds`, `observed_during_run`); `modules/ai/policy.py` holds `BLOCKED_HOSTS`, `blocked_domain`, `api_blocked_domains()` and `cli_disallowed_tools()` |
| `backend/tests/fake_claude.py` | A scripted stand-in for the CLI, so tests never call the real one | The provider and parser tests |
| `worker/agents/smoke.py` | One real run on a throwaway trip | `hermi ai-smoke` |

## What stays out

Same path rule as above.

- `agent_bridge/` (the MCP stdio bridge): Hermi's tools run in process.
- APScheduler (`worker/scheduler.py`): replaced by the leader and the `flight_routes.next_check_at` scan
  (`scan_due_routes`).
- Passcode auth (`api/auth.py`, `frontend/src/components/auth/*`): replaced by sign-in and the guest flow.
- Windows-only scripts (`scripts/autostart-install.ps1`, `autostart-remove.ps1`, `run-hidden.ps1`) and
  `scripts/share-tailscale.ps1`.
- `services/backups.py` (Windows `pg_dump.exe` into a local folder): replaced by point-in-time recovery and an
  off-provider dump job.

## Two habits worth keeping

- **Run with `uv run --no-sync`** while the app is up, because a running `trip-planner.exe` blocks `uv sync`. Hermi's
  dev scripts do the same (`knowledge/local-dev-windows.md`).
- **Tests wipe the test database**, so the real data and the test data live in different databases, and a check of
  the UI on seeded data is done after a reseed.
