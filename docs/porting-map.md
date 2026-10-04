# Porting map

Source: the Trip Planner repo, read-only in `.reference/trip-planner/` (`backend/tripplanner/` and
`frontend/src/`). Authority for what to reuse, adapt or drop: `app-buildout/phase-1-launch/02-architecture.md`
section 14. Ticket: WF-005 (commits WF-005.1, WF-005.2, WF-005.3). Tests were ported and adapted next to each
module, in `apps/api/tests/` and as `*.test.ts` beside the web files.

## Backend

| Source (`backend/tripplanner/`) | New home (`apps/api/hermi/`) | Notes |
|---|---|---|
| `providers/travelpayouts.py` | `providers/travelpayouts.py` | Keyless provider raises `NotConfigured` (`config.py`) |
| `providers/frankfurter.py` | `providers/frankfurter.py` | Reference rates only |
| `providers/geoapify.py`, `providers/geoapify_places.py` | `providers/geoapify.py` | Two files merged: destination search and places |
| `providers/wikipedia.py` | `providers/wikipedia.py` | User-Agent uses Hermi's name and a contact |
| `schemas/*` provider shapes | `providers/schemas.py` | Only what providers return |
| `services/search_planner.py` | `modules/flights/planner.py` | Takes a plain `RouteWindow`, not a SQLAlchemy `FlightRoute` |
| `services/quotes.py` | `modules/flights/quotes.py` | Pure helpers only: new observation, dedupe key, suspect check |
| `services/flight_choice.py` | `modules/flights/flight_choice.py` | DB-free |
| `services/fx.py` | `modules/flights/fx.py` | Refresh timing and local currency; conversion moves to read time (money is minor units) |
| `services/agent_ingest.py` (link and evidence rules) | `modules/ai/ingest.py` | `source_problem`, price bounds, observed-during-run. Pure; the DB writes land with the tables and tools |
| `services/agent_ingest.py` `blocked_domain`, `services/agent_context.py` `BLOCKED_DOMAINS` | `modules/ai/policy.py` | One constant `BLOCKED_HOSTS` (brands), plus generators for the API list and CLI rules. `security/ssrf.py` imports it |
| `.env` and `config` reads | `config.py` | WF-004, not a port |

## Web and tokens

| Source (`frontend/src/lib/`) | New home (`apps/web/src/lib/`) |
|---|---|
| `currencies.ts`, `dates.ts`, `errors.ts`, `format.ts`, `geo.ts`, `interests.ts`, `itinerary-time.ts`, `money.ts`, `timezones.ts` | same names, with their tests (`timezones.ts` has none upstream) |
| old passport theme CSS | `packages/tokens/tokens.css` and `theme.css`: Hermi values from 05 sections 2.1 to 2.4, only the plumbing is ported. Checked by `apps/web/src/tokens.test.ts` |

## Not ported yet (lands when a feature ticket needs it)

Itinerary and lodging logic (`services/itinerary.py`, `lodging.py`, `suggestions.py`, `ai_lodging.py`), presentation
mode (`services/presentation.py`), `services/agent_context.py` (adapts to `modules/ai/context.py`), the agent prompts
(`worker/agents/prompts.py`: they name Trip Planner and a household, so they are rewritten in WF-130 on, not copied),
`providers/link_preview.py` (WF for imports), `open_meteo.py`, `serpapi*.py`, `activity-meta.ts`, `trip-display.ts`,
`trip-status.ts`, `price-sources.ts`, `schedules.ts`.

## Left behind on purpose

| Piece | Why |
|---|---|
| Passcode auth (`api/auth.py`, `components/auth/*`) | Replaced by sign-in and the guest flow |
| Claude CLI runner (`services/claude_cli.py`, `worker/agents/runner.py`, `stream.py`, `smoke.py`) | WF-131 adapts it as the dev-only provider in `providers/ai/claude_cli.py`, the only file allowed `subprocess` |
| MCP bridge (`agent_bridge/`) | Hermi's tools run in process |
| APScheduler (`worker/scheduler.py`) | Replaced by the leader and the `next_check_at` scan. `apscheduler` is forbidden (`tests/test_forbidden_imports.py`) |
| Windows scripts (`scripts/*.ps1`), `services/backups.py` | Native node scripts; point-in-time recovery |
| Tailscale sharing (`scripts/share-tailscale.ps1`) | Not used |
