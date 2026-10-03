# Claude CLI provider (local only)

Hermi's product AI can run through the owner's own `claude -p` instead of the Anthropic API. This page is
everything needed to build, test and operate that provider. The short rules are in `.claude/rules/ai-provider.md`;
what each AI feature does is in `app-buildout/phase-1-launch/06-ai-agents-spec.md`.

**Why it exists.** Owner decision, 2026-10-03: use the subscription CLI until production, so the build and local
use cost no API credit. It is for the owner's machine only. Staging, TestFlight and production use
`anthropic_api`.

## The seam

`apps/api/hermi/providers/ai/` holds an `AiProvider` protocol and three implementations. WF-131 (prompt 12) builds
it, and WF-046 gives the CLI its own queue lane (`AI_CLI_MAX_CONCURRENCY`, 1 or 2).

| Piece | What it does |
|---|---|
| `single_call` | One model call with optional structured output. Explain, packing list, booking import, verify extract, drafts. |
| `agent_run` | A multi-turn run with web tools. Agent runs, research, verify plan. |
| `anthropic_api` | The production provider: Messages API, server tools, prompt caching. |
| `claude_cli` | This page. |
| `fake` | Replays recorded fixtures. The default for tests, CI and the build's smoke runs. |
| `ai/client.py` | A facade. Callers never pick a provider; `AI_PROVIDER` does. |

`ai_usage.provider` and `runs.provider` record which one answered. Metering is provider-neutral.

## The command

```
claude.exe -p --model <full id> --output-format stream-json --verbose --safe-mode --restricted
  --strict-mcp-config --no-session-persistence --permission-mode dontAsk --permission-prompts none
  --disable-slash-commands --system-prompt-file <tmp> --tools ""
  [--tools "WebSearch,WebFetch" --allowedTools WebSearch WebFetch]     web calls, instead of --tools ""
  --disallowedTools "WebFetch(domain:...)" ...                          web calls, one rule per pattern
  [--json-schema <schema>] [--max-budget-usd <stop>] [--max-turns N]
```

The prompt goes on stdin. The working directory is an empty scratch folder (`AI_CLI_SCRATCH_DIR`). The
environment is stripped (below).

| Flag | Why |
|---|---|
| `-p` | Print mode: one prompt in, events out, then exit. |
| `--model <full id>` | Pins the model from `AI_MODEL_FAST` or `AI_MODEL_MAIN`. An alias can lag a release (on 2.1.283 `sonnet` still meant Sonnet 5). No fallback model. |
| `--output-format stream-json --verbose` | The event stream the parser reads. stream-json needs `--verbose` in print mode. |
| `--safe-mode` | Turns every customization off: CLAUDE.md, skills, plugins, hooks, MCP servers, custom agents and commands. Nothing from the owner's setup reaches a product call. |
| `--restricted` | Removes the code-running tools (Bash, PowerShell and the rest) and WebFetch unless `--tools` names it, ignores user, project and local settings files, and confines file tools to the working directory. |
| `--strict-mcp-config` | With no `--mcp-config` given, there are no MCP servers at all. |
| `--no-session-persistence` | Nothing is written to the owner's session history, and the run cannot be resumed. |
| `--permission-mode dontAsk`, `--permission-prompts none` | Anything not explicitly allowed is denied and nobody is asked. This is why web calls need `--allowedTools`. |
| `--disable-slash-commands` | Skills and slash commands off. |
| `--system-prompt-file <tmp>` | Hermi's own system prompt replaces Claude Code's. A file, because the Windows command line is limited. (The base appended to the default prompt instead.) |
| `--tools ""` | No tools: the model can only answer. |
| `--tools "WebSearch,WebFetch"`, `--allowedTools WebSearch WebFetch` | The only two tools that exist, both pre-approved. Without the allow list `dontAsk` denies them. |
| `--disallowedTools "WebFetch(domain:...)"` | Never fetch Airbnb, Vrbo or Booking.com, `localhost`, `127.0.0.1` or `169.254.169.254`. See "Blocked hosts". |
| `--json-schema <schema>` | Structured output. The object arrives in the `result` event as `structured_output`. Validate it again in code: the CLI's check is not a trust boundary. |
| `--max-budget-usd <stop>` | The feature's hard dollar stop. Notional under a subscription, but still a runaway brake. |
| `--max-turns N` | Turn cap. It is not listed in `--help` on 2.1.288, but it is in the binary and the base used it. A `--json-schema` call needs at least 2 turns (observed), so never set 1. |

## The environment

The child gets the process environment minus: `ANTHROPIC_API_KEY`, every other `ANTHROPIC_*` name (the base list
also covers `ANTHROPIC_DEFAULT_*_MODEL` and `ANTHROPIC_SMALL_FAST_MODEL`), `CLAUDE_CODE_*`, `CLAUDECODE`, the
Bedrock, Vertex and Foundry switches, and every secret Hermi's own config holds. An API key left in the
environment moves the run off the subscription.

## Verified on this machine (claude 2.1.288, 2026-10-03)

One-shot calls on `claude-haiku-4-5` from an empty folder, the exact recipe above. Flags move between releases, so
re-check with `hermi ai-smoke` after every upgrade.

- **`init` event.** With `--tools ""` and `--json-schema`: `tools` is `["StructuredOutput"]`, `mcp_servers` is
  `[]`, `permissionMode` is `dontAsk`, `apiKeySource` is `none`, and `model` is the id as passed
  (`claude-haiku-4-5`). Assistant messages report a dated id (`claude-haiku-4-5-20251001`), so compare by prefix.
  Without `--json-schema` the tool list is `[]`. With the web tools it is
  `["StructuredOutput","WebFetch","WebSearch"]`.
- **A key in the environment.** With a dummy `ANTHROPIC_API_KEY` set, `apiKeySource` read `ANTHROPIC_API_KEY` and
  the call still succeeded, so a leak is silent. Assert `apiKeySource == "none"`.
- **Structured output.** `result.structured_output` is the parsed object and `result.result` its text. The
  model answers through a `StructuredOutput` tool call, so the call took 2 turns. `total_cost_usd` was 0.00172
  for a tiny call.
- **WebSearch.** The tool result is `Web search results for query: "<q>"`, a blank line, then
  `Links: [{"title":"...","url":"https://..."}, ...]` as a JSON array on one line, then a text summary. This
  differs from the markdown links in the base's `fake_claude.py`, so update the fake.
- **WebFetch.** The input is `{"url": ..., "prompt": ...}` and the result is a short model-written answer about
  the page, not the page. A redirect to another host is reported as `REDIRECT DETECTED` instead of being followed.
- **Counters.** `usage.server_tool_use` stays 0 under the CLI. Count `tool_use` blocks in the stream instead.
- **A denied tool.** The stream has a `system` event with subtype `permission_denied` (tool, id, reason
  `rule`), the tool result has `is_error: true` ("WebFetch denied access to domain:example.org."), and
  `result.permission_denials` lists it.
- **Deny matching.** `WebFetch(domain:example.org)` denied `example.org` but let `www.example.org` through.
  `domain:*.example.org` denied `www.example.org`. `domain:example.*` and `domain:*.example.*` denied
  `example.com` and `www.example.com` but not `example.co.uk` or `m.example.com.au`: `*` stands for one label.
- **Usage limits.** A `rate_limit_event` carries `rateLimitType` (`five_hour` or `seven_day`), `utilization`,
  `resetsAt` and `overageStatus`. On this account `overageStatus` was `rejected` with reason `out_of_credits`.
- **Models used.** `modelUsage` can list the pinned model and a dated Haiku that summarized a fetched page.

## Blocked hosts

`BLOCKED_HOSTS` (`ai/policy.py`, 06 section 2.4) is the one list. Generate the CLI rules from the same brands and
country second levels that `blocked_domain` uses. Per brand (`airbnb`, `vrbo`, `booking`) that is `brand.*` and
`*.brand.*`, plus `brand.<sl>.*` and `*.brand.<sl>.*` for each second level it accepts (`co`, `com`, `net`, `org`,
`ne`, `or`), plus the plain hosts the API tool lists use. Because the CLI matches whole labels, also check every
`WebFetch` URL the stream shows with `blocked_domain` (suffix match) and kill the run on a hit. The kill is quick
but cannot undo a fetch already sent, so keep the rules broad.

## Per feature

| Feature | How the CLI runs it |
|---|---|
| `explain`, packing list, `booking_import`, `verify_extract`, trip and day drafts | No tools: `--tools ""` plus `--json-schema`. The result is validated in code with the same Pydantic model as the API path. |
| `recheck` | Not through the CLI's tools. Hermi's own SSRF-safe fetcher gets the page, then a no-tool call reads it. |
| `research`, `verify_plan`, agent runs | Web tools, with stream counters for the search and fetch caps, an 8 minute watchdog, and a cancel that kills the tree. The final JSON goes through the ported `agent_ingest` checks and the evidence collector. |
| Batch and `cache_warm` | Run synchronously, one call at a time. There is no Batch API behind the CLI. |

The stream-json events are stored in `run_events`, the same table the API path writes.

## Evidence from the stream

An `EvidenceCollector` reads the stream and keeps two sets for the run: **fetched** (the `url` input of every
`WebFetch` tool use) and **found** (the `url` of every link in a `WebSearch` result, parsed from the JSON array
after `Links:`). Each saved fact needs a `source_url` that is in one of the sets, passes `source_problem` (a public
http(s) page that is not a blocked host) and was observed during the run. A URL the stream never showed is
rejected and recorded like an `IngestRejection`. The default for fares is that the URL must be in **fetched**,
because non-negotiable 4 says a fare must be seen on a page; other facts may cite a **found** link. WF-049
confirms that default. The collector proves where a fact came from, not that the page says so: the CLI's WebFetch
returns a summary, which is why the evals are certified on the API (below).

## Caps, watchdog and cancel

The caps are the `max_uses` numbers the API path sends (06 section 2.4): agent run 10 searches and 10 fetches,
research question 5 and 8 (counted across the question), taster 6 and 6, plan check 1 and 1 per item. The CLI has
no equivalent, so counters on the stream enforce them. A breach, the 8 minute watchdog, a cancel and an app
shutdown all kill the whole process tree. The prompt states the caps so a normal run stays under them; the
counters are the safety net.

## Metering

The `result` event carries `total_cost_usd`, `usage` and `modelUsage`. Store `round(total_cost_usd * 1_000_000)`
in the micro-dollar spend column with `provider = 'claude_cli'`. The number is notional: a subscription is not
billed per call, and this is what the API would have charged. It still feeds the ceilings, the admin spend view
and eval budgets. There is no usage reconcile for `claude_cli` (`ANTHROPIC_ADMIN_API_KEY` has nothing to compare
against). Map a limit error to a plain message ("Your Claude usage limit was reached. Try again after it
resets."), as the base's `explain_failure` does. The owner's manual use of the dev app and the autopilot share one
subscription, so heavy product testing eats build quota.

## The guard

`claude_cli` runs only when `ENVIRONMENT=local`, the server is bound to loopback, and `AUTH_MODE=dev` or the
signed-in user's email is in `AI_CLI_ALLOWED_EMAILS`. `config.py` refuses to start otherwise, and the provider
factory checks again at call time. `render.yaml` pins `AI_PROVIDER=anthropic_api`, `/health/ready` reports the
active provider, and a matrix test covers provider by environment by bind address by auth mode.

## Windows spawning

- Spawn the native `claude.exe`, never a `.cmd` shim. An npm shim runs through `cmd.exe`, which re-parses the
  arguments (the empty `--tools ""` and the JSON schema are at risk), and a kill would hit the shim instead of the
  CLI. The base's `find_claude` uses `shutil.which("claude")`, which can return a shim. Hermi's must look for
  `claude.exe` (`CLAUDE_CLI_PATH`, else PATH) and refuse `.cmd` and `.bat`.
- Use `subprocess.Popen` in a thread. psycopg async needs the Selector event loop on Windows and asyncio
  subprocesses need the Proactor loop, so asyncio subprocesses are not available. Write stdin, read stdout and
  drain stderr from separate threads, so a full pipe never blocks either side.
- Kill the tree with psutil: terminate the children and the parent, wait 5 seconds, then kill what is left.
- Pass `CREATE_NO_WINDOW`, decode as UTF-8 with `errors="replace"`, and keep only the last 30 scratch folders.

## Ported from trip-planner, and what is not

The base is `C:/Users/matic/code/trip-planner` (see `knowledge/trip-planner-base.md`). Paths are under
`backend/tripplanner/` unless they start with `backend/` or `scripts/`, which are from the repo root. All were
confirmed on 2026-10-03.

| Base file | Carries over | Changes in Hermi |
|---|---|---|
| `services/claude_cli.py` | `STRIPPED_ENV`, `agent_env`, `find_claude`, `auth_status` (`claude auth status`, no model call), `NO_WINDOW` | `claude.exe` only, `CLAUDE_CLI_PATH`, a longer strip list |
| `worker/agents/runner.py` | `Watchdog`, `StderrDrain`, the stdin writer thread, `kill_tree`, `kill_orphan`, `guard_problem`, `explain_failure`, `redact`, `prepare_run_dir` | No MCP bridge; the model check allows Haiku summaries and adds `apiKeySource`; `--system-prompt-file`, `--safe-mode`, `--json-schema`, `--max-budget-usd` |
| `worker/agents/stream.py` | `StreamParser`, `StreamState` (the `init` fields, the `result` event) | Feeds `run_events`; drops the `mcp__trip__` prefix |
| `services/agent_ingest.py` | `blocked_domain`, `source_problem`, the observed-during-the-run window, price bounds, per-item rejection records | Becomes `modules/ai/ingest.py` (02 section 14.1: Reuse), plus the evidence collector |
| `backend/tests/fake_claude.py` | A stand-in `claude` that prints scripted stream-json (scenarios `success`, `crash`, `wrong_model`, `mcp_failed`, `hang`, `auth_error`, `max_turns`, `signed_out`) and records argv, prompt, cwd and key leaks | Update the `WebSearch` result to the JSON `Links:` format; add scenarios for a blocked fetch, a cap breach and a Haiku summary |
| `worker/agents/smoke.py` | One real run against a throwaway trip | Becomes `hermi ai-smoke`: one no-tool call and one capped web-tool call |

The runner and the stream parser land in `apps/api/hermi/providers/ai/` only. Only providers spawn `claude`
(02 section 3), so nothing from them goes to `hermi_worker/agents/`.

Not ported: `agent_bridge/` (the MCP stdio bridge, because Hermi's tools run in process), APScheduler
(`worker/scheduler.py`), passcode auth, the Windows-only `scripts/*.ps1` and Tailscale sharing.

## Evals

The CLI's WebFetch returns summaries, so a grounding eval cannot measure what the API path measures. WF-057 and
WF-119 are certified only on `anthropic_api` (`--provider`), and `claude_cli` numbers are provisional. The eval
runner carries a `shortcut:` comment that names this ceiling and the trigger to remove it: the first
`ANTHROPIC_API_KEY`. Live evals need `EVALS_LIVE=1` and `--max-usd`.

## Terms

A Claude subscription is for its owner's own use. Serving other people through it (a shared tunnel, testers, a
staging server) is outside what a personal plan is for. That is why the provider never leaves the owner's machine:
loopback bind only, no tunnel to the dev API, no testers on it. Check Anthropic's current terms before relaxing
the guard.

## Switching to the API for production

1. Create an Anthropic workspace per environment, with prepaid credit and a spend limit. Put `ANTHROPIC_API_KEY`
   in the Render env group (a `HUMAN_TASKS.md` row).
2. Set `AI_PROVIDER=anthropic_api` (`render.yaml` already does). The guard refuses `claude_cli` outside `local`.
3. Add `ANTHROPIC_ADMIN_API_KEY` so the usage reconcile runs.
4. Run WF-057 and WF-119 on the API (`EVALS_LIVE=1`, `--provider anthropic_api`, `--max-usd`). Their gates stay
   provisional until then.
5. Spend numbers are now real dollars: the $150 daily cap and the monthly ceilings protect real money.
6. Leave `AI_CLI_ALLOWED_EMAILS` and `CLAUDE_CLI_PATH` out of every hosted environment.

## Open items

- A `PreToolUse` hook passed through `--settings` could deny a fetch by suffix before it runs. Not tested: it is
  unknown whether `--safe-mode` keeps hooks that come from `--settings`.
- Stripping every `CLAUDE_CODE_*` name might remove one `claude.exe` needs on Windows (for example
  `CLAUDE_CODE_GIT_BASH_PATH`). Unverified. If the CLI starts from a shell but not from the app, look here first.
- What a capped or killed run returns (nothing, or the last complete JSON in the stream) and how credits follow
  are for WF-049 and 06's refund rules to settle.
