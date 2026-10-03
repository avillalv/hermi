---
description: Use when adding or changing an environment variable, config.py, .env.example or Vite env handling. Every variable has to be documented, and a missing optional key must degrade, not crash.
paths:
  - "apps/api/hermi/config.py"
  - ".env.example"
  - "apps/web/vite.config.*"
---

# Config and environment rules

Authority: `02-architecture.md` sections 7.1 and 7.2 (S1 settles the final names and adds the Local column). The
inventory, with the account and the place to get each key, is `knowledge/env-and-accounts.md`. If you need to
break one of these, change the document in the same commit and say why.

## One place, documented twice

- `config.py` is the only place environment variables are read (pydantic-settings). Nothing else touches
  `os.environ`. The one exception is `providers/ai/claude_cli.py`, which copies the process environment, minus the
  stripped names, for the child process.
- Every variable is in `.env.example` and in `knowledge/env-and-accounts.md` in the same pull request (purpose,
  local need, fallback, where to get it). `.env.example` is local-ready: a working local value, or empty for an
  optional key. Never a real secret.
- A new external key also adds a `HUMAN_TASKS.md` row that says where to put it ("put it in `.env` as `NAME`")
  and where to get it.
- The process environment overrides `.env`. That is how tests and CI force fake providers without editing the
  owner's file.

## Degrade, do not crash

- A missing required value fails startup with a list of names, never values.
- A missing optional key degrades to a fake or a no-op with one warning: a provider raises `NotConfigured`, and a
  job logs and skips. The app, the demo trip and `npm run dev` work with only the required local values.

## Dev modes in production

- `config.py` refuses to start with `AUTH_MODE=dev`, `ADMIN_AUTH_MODE=dev`, `STORAGE_BACKEND=local`,
  `PROVIDERS_MODE=fake` or any `EMAIL_BACKEND` but `resend`, anywhere except `local` and `ci` (02 section 7.2).
- It allows `AI_PROVIDER=claude_cli` only when `ENVIRONMENT=local`, the server is bound to loopback, and
  `AUTH_MODE=dev` or the signed-in user's email is in `AI_CLI_ALLOWED_EMAILS`; the provider factory checks the
  same conditions again at call time (`ai-provider.md`). Staging, TestFlight and production use `anthropic_api`
  and require `ANTHROPIC_API_KEY`. A test covers the matrix.

## Secrets and the client

- Never log a secret. The log filter masks any key matching `key|secret|token|password|authorization|cookie|dsn`
  and any JWT-shaped string (02 section 7.2). `settings.public_dict()` never includes a secret, and a unit test
  asserts it.
- Only `VITE_` variables reach the bundle, so a secret never gets a `VITE_` name.
- Vite reads env from the repo root: `envDir: '../..'` in `apps/web/vite.config.*`.
- Agents never read `.env`. `npm run doctor` reports which variables are set, without their values.

## What must not change without a decision

- **The process environment beating `.env`.** Flipping the order lets a stale local file turn a test run into a
  live one.
- **Optional keys degrading.** Making one required breaks `npm run setup` on a machine with no accounts.

## Checkable by grep

```bash
# environment reads outside config.py (prints nothing when clean)
grep -rnE "os\.environ|os\.getenv" apps --include=*.py | grep -v -e "apps/api/hermi/config.py" -e "providers/ai/claude_cli.py" -e "/tests/"
# a variable in .env.example that the knowledge table does not mention (prints nothing when clean)
for v in $(grep -oE '^[A-Z][A-Z0-9_]*=' .env.example | tr -d '='); do grep -q "\`$v\`" knowledge/env-and-accounts.md || echo "$v"; done
# a secret given a VITE_ name (prints nothing when clean)
grep -nE '^VITE_.*(SECRET|SERVICE_ROLE|PRIVATE)' .env.example
```
