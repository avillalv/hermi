---
description: Use when touching any model call, the AiProvider seam, the claude_cli provider, agent loops, evals or AI tests. Product AI runs behind AI_PROVIDER, and claude_cli is a locked-down provider for local use only.
paths:
  - "apps/api/hermi/modules/ai/**"
  - "apps/api/hermi/providers/ai/**"
  - "apps/worker/hermi_worker/agents/**"
---

# AI provider rules

Authority: `06-ai-agents-spec.md` sections 1 to 3, WF-131 in `09-build-roadmap.md` and the owner decision of
2026-10-03 in `DECISIONS.md`. The full recipe and the reason for every flag are in
`knowledge/ai-provider-claude-cli.md`. To break one of these, change the document in the same commit and say why.

## The seam

- Every model call goes through `AiProvider` (`single_call`, `agent_run`) in `apps/api/hermi/providers/ai/`
  (`anthropic_api`, `claude_cli`, `fake`, chosen by `AI_PROVIDER`). `ai/client.py` is only a facade, and only
  `providers/*` import the Anthropic SDK or spawn `claude` (02 section 3).
- Product model ids come only from config (`AI_MODEL_FAST`, `AI_MODEL_MAIN`), as full ids, never a CLI alias or a
  build model.
- Every saved fact carries a source URL seen during the run (non-negotiable 4) and passes the ported ingest checks.
  With `claude_cli` the URLs come from the stream, not from the model's say-so.

## The claude_cli guard

- `claude_cli` runs only when `ENVIRONMENT=local`, the server is bound to loopback, and `AUTH_MODE=dev` or the
  signed-in user's email is in `AI_CLI_ALLOWED_EMAILS`.
- `config.py` refuses to start otherwise, and the provider factory checks the same conditions again at call time.
  `render.yaml` pins `AI_PROVIDER=anthropic_api`.
- Staging, TestFlight and production use `anthropic_api` and require `ANTHROPIC_API_KEY`. A personal subscription
  may only serve its owner: no tunnel to the dev API and no testers on it.

## Every CLI call

- Lockdown flags: `--safe-mode`, `--restricted`, `--strict-mcp-config`, `--no-session-persistence`,
  `--permission-mode dontAsk`, `--permission-prompts none`, `--disable-slash-commands`, `--system-prompt-file` and
  `--tools` (empty, or `WebSearch,WebFetch` plus `--allowedTools`). Add `--json-schema` (validate again in code),
  `--max-budget-usd` and `--max-turns`.
- Read the `init` event first and kill the call unless the model starts with the pinned id, `apiKeySource` is
  `none`, `mcp_servers` is empty, and the tool list is what the call asked for plus `StructuredOutput` with a schema.
- Deny rules (`WebFetch(domain:...)`) come from `BLOCKED_HOSTS`. The CLI matches whole labels, so also check every
  `WebFetch` URL in the stream with `blocked_domain` (a suffix match) and kill the run on a hit.
- The child environment drops `ANTHROPIC_*`, `CLAUDE_CODE_*`, `CLAUDECODE` and the app's secrets. The working
  directory is an empty scratch folder (`AI_CLI_SCRATCH_DIR`), and the prompt goes on stdin.
- Windows: spawn the native `claude.exe` (never a `.cmd` shim) with `subprocess.Popen` in a thread. Cancel, a cap
  breach and the 8 minute watchdog kill the whole process tree.

## Tests and evals

- Tests, CI and the build's smoke runs force `AI_PROVIDER=fake` through the process environment and never read
  `.env`. The runner and stream parser are tested against `fake_claude.py`, never the real CLI.
- Live evals run only with `EVALS_LIVE=1` and a `--max-usd`. WF-057 and WF-119 are certified on `anthropic_api` only.

## What must not change without a decision

- **The lockdown flags, the guard with its call-time check, and `fake` in tests.** Loosening one lets the owner's
  hooks or quota into a product call, or lets a personal subscription serve other people.

## Checkable by grep

```bash
# the Anthropic SDK or the CLI used outside providers/ai (prints nothing when clean)
grep -rnE "import anthropic|from anthropic|--permission-mode|claude\.exe" apps --include=*.py | grep -v -e "apps/api/hermi/providers/ai/" -e "/tests/"
# a model id written into code instead of config
grep -rnE "claude-(haiku|sonnet|opus)-[0-9]" apps --include=*.py | grep -v -e "/tests/" -e "apps/api/hermi/config.py" -e "modules/ai/pricing.py"  # pricing.py keys its price table by model id
```
