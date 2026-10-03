# Environment variables and accounts

Every variable Hermi reads, what it is for, whether you need it on your own machine, what happens without it, and
where to get it. Keep it in step with `.env.example`: a variable is added to both in the same pull request
(`.claude/rules/config-and-env.md`).

**Names are settled; S1 writes them into 02 section 7.1 and this file mirrors it.**
`GUEST_TOKEN_SECRET` and `ADMIN_OIDC_*` are dropped by S1 (08 is the authority for admin sign-in).
`ADMIN_ALLOWED_DOMAIN` and `ADMIN_IP_ALLOWLIST` are in 02 today and are left for S1 to keep or drop.

**Where a value goes.** Local keys go in `.env` (gitignored, never read by an agent). Production secrets go in
Render env groups (`hermi-prod-shared`, `hermi-prod-api`, `hermi-prod-worker`, 02 section 7.2). GitHub holds only
deploy credentials through OIDC, `SENTRY_AUTH_TOKEN` and the iOS signing secrets. The process environment beats
`.env`, so tests force fakes without touching your file.

**Local need.** *Required* means the app will not start without it, and `.env.example` already has a local value
(`npm run setup` copies it and generates the secrets). *Optional* means it degrades to a fake or a no-op with one
warning. *Production only* means you never need it on your machine. "Startup fails" always names the variable and
never prints its value. `npm run doctor` lists what is set and what is missing.

## Runtime

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `ENVIRONMENT` | `local`, `ci`, `preview`, `staging` or `production`. Gates every dev mode | Required | Startup fails | `local` |
| `LOG_LEVEL` | Log verbosity | Required | Startup fails | `INFO` |
| `PORT` | API listen port | Required | Startup fails | `8100` |
| `PUBLIC_API_URL` | API base URL used in links and webhooks | Required | Startup fails | `http://localhost:8100` |
| `PUBLIC_WEB_URL` | Web app URL used in emails and invites | Required | Startup fails | `http://localhost:5173` |
| `CORS_ALLOWED_ORIGINS` | Allowed browser origins | Required | Startup fails | `http://localhost:5173`; add `capacitor://localhost` for the iOS build |
| `API_DOCS_ENABLED` | Serves `/docs` | Required | Startup fails | `true` locally, `false` in production |
| `RELEASE_SHA` | Git SHA tagged onto logs, Sentry and metrics | Optional | Left off the tags | Set by CI and Render at deploy |
| `TRUSTED_PROXY_CIDRS` | Networks whose `X-Forwarded-For` is trusted | Optional | Empty: no proxy header is trusted | Cloudflare's published ranges, in production |
| `IMPORT_SANDBOX` | `strict` or `timeout_only`. On Windows `timeout_only` is a time limit plus a psutil memory kill | Required | Startup fails | `timeout_only` locally on Windows, `strict` in CI and production |
| `VITE_API_BASE_URL` | API origin for the web and iOS bundles | Required | Startup fails | `http://localhost:8100` |
| `VITE_APP_ENV` | Shown in the settings footer and Sentry | Required | Startup fails | `local` |

## Processes

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `SCHEDULER_ENABLED` | Whether this process runs the scheduler loop | Required | Startup fails | `true` on the one worker process |
| `WORKER_LANES` | Lanes this worker serves | Required | Startup fails | `api,ai,notify,batch` |
| `WORKER_CONCURRENCY_API`, `WORKER_CONCURRENCY_AI`, `WORKER_CONCURRENCY_NOTIFY`, `WORKER_CONCURRENCY_BATCH` | Concurrent jobs per lane | Required | Startup fails | `4`, `2`, `4`, `1` locally |

## Database

`npm run db:init` creates the roles and databases on the native PostgreSQL 18 service, and `npm run setup` writes
the URLs with generated passwords. You never type a database password. The superuser password stays in
`%APPDATA%\postgresql\pgpass.conf`, outside the repo (`knowledge/local-dev-windows.md`).

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `DATABASE_URL` | App login (`hermi_api_login`, in `hermi_app`): DML only, row-level security applies | Required | Startup fails | Written by `npm run setup` |
| `DATABASE_URL_SYSTEM` | Worker login (`hermi_worker_login`, `BYPASSRLS`): jobs that cross tenants | Required | Startup fails | Written by `npm run setup` |
| `MIGRATION_DATABASE_URL` | Migrate login (`hermi_migrate_login`, a member of the NOLOGIN `hermi_owner`): used only by `hermi migrate` | Required | Migrations cannot run | Written by `npm run setup` |
| `TEST_DATABASE_URL` | App login on the `hermi_test` database | Required | pytest refuses to run | Written by `npm run setup` |
| `TEST_DATABASE_URL_SYSTEM` | Worker login on `hermi_test`: test fixtures write through it | Required | pytest refuses to run | Written by `npm run setup` |
| `DATABASE_URL_ADMIN` | Admin login (`hermi_admin_login`, `BYPASSRLS`): the admin console only. New | Required | Startup fails | Written by `npm run setup` |
| `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW` | Pool size per process | Required | Startup fails | `10`, `5` |
| `DATABASE_STATEMENT_TIMEOUT_MS` | Per-statement timeout | Required | Startup fails | `15000` |
| `REDIS_URL` | Empty until Redis is added (about 10k monthly users) | Optional | Empty: no Redis | Nothing to do |

## Sign-in

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `AUTH_MODE` | `supabase` or `dev`. `dev` mints local tokens for seeded personas (Free, Plus, admin) | Required | Startup fails | `dev` locally, `supabase` in staging and production. Refused outside `local` and `ci` |
| `SUPABASE_URL` | Supabase project URL | Optional | `AUTH_MODE=dev` signs in the personas | supabase.com, free plan: Project settings, API |
| `SUPABASE_JWKS_URL` | Signing keys for JWT verification (use asymmetric JWT keys) | Optional | Same | `<project url>/auth/v1/.well-known/jwks.json` |
| `SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUDIENCE` | Expected `iss` and `aud` | Optional | Same | `<project url>/auth/v1` and `authenticated` |
| `SUPABASE_SERVICE_ROLE_KEY` | Deletes users on account deletion, admin lookups | Optional | Those calls log and skip | Supabase dashboard, API keys |
| `SUPABASE_AUTH_HOOK_SECRET` | Verifies Supabase Auth hook calls | Optional | The hook route refuses calls | Supabase dashboard, Auth hooks |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | Client sign-in (the anon key is public by design) | Optional | The dev persona picker is shown | Same project, API keys |

Supabase setup: free plan, email code on, Google provider on. The built-in email is rate limited, so add custom
SMTP through Resend before real users. Free projects pause when idle. Google sign-in needs an OAuth client from the
Google Cloud console (free), configured inside Supabase and not in `.env`. Calendar import uses a secret iCal URL
and Maps import uses Takeout files, so no Google API key is involved.

## Secrets generated by setup

`npm run setup` fills these with random values the first time. Production gets its own values, never a copy of a
local one.

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `FIELD_ENCRYPTION_KEY` | Encrypts rare sensitive fields (Apple refresh token, feed addresses while polling is on) | Required | Startup fails | Generated by `npm run setup` (base64, 32 bytes) |
| `UNSUBSCRIBE_SECRET` | Signs one-click unsubscribe links | Required | Startup fails | Generated by `npm run setup` |
| `ADMIN_SESSION_SECRET` | Signs admin session cookies | Required | Startup fails | Generated by `npm run setup` |
| `REVENUECAT_WEBHOOK_SECRET` | Authorizes RevenueCat webhook calls | Required | Startup fails | Generated by `npm run setup`. In production, the value in the Render env group must match the one in the RevenueCat webhook settings |

## AI

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `AI_PROVIDER` | `claude_cli`, `anthropic_api` or `fake` | Required | Startup fails | `claude_cli` in your `.env`, `fake` forced in tests and CI, `anthropic_api` in production |
| `CLAUDE_CLI_PATH` | Full path to the native `claude.exe` | Optional | Looks for `claude.exe` on PATH | `%USERPROFILE%\.local\bin\claude.exe` on this machine |
| `AI_CLI_MAX_CONCURRENCY` | Parallel `claude` processes | Optional | A small default (1 or 2, WF-046) | Your choice |
| `AI_CLI_SCRATCH_DIR` | Empty working folder for each call | Optional | A folder under `.data/` | Your choice |
| `AI_CLI_ALLOWED_EMAILS` | Comma list of users who may use `claude_cli` when `AUTH_MODE` is not `dev` | Optional | Empty: nobody | Your own email |
| `ANTHROPIC_API_KEY` | API key, one workspace per environment with a spend limit | Production only | Not needed for `claude_cli` or `fake`; stripped from the CLI's environment on purpose | console.anthropic.com: prepaid credit and a workspace spend limit |
| `ANTHROPIC_ADMIN_API_KEY` | Usage reconcile (an organization admin key) | Production only | The reconcile job logs and skips | console.anthropic.com, organization settings, Admin keys |
| `AI_MODEL_FAST` | Haiku id for short answers, page summaries and pasted-text import | Required | Startup fails | `claude-haiku-4-5` |
| `AI_MODEL_MAIN` | Sonnet id | Required | Startup fails | `claude-sonnet-5-5` |
| `AI_GLOBAL_DAILY_CAP_USD` | Circuit breaker for total daily spend | Required | Startup fails | `150` |
| `AI_ALERT_DAILY_MULTIPLIER` | Alert when daily spend passes this times the 7 day average | Required | Startup fails | `1.5` |
| `PROMPT_VERSION` | Current prompt set, part of shared cache keys | Required | Startup fails | The `.env.example` value |
| `EVALS_LIVE` | `1` lets `npm run evals` call a real model | Optional | Unset: evals use fixtures | Set it only when you mean to spend |

## Fares, places and data

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `PROVIDERS_MODE` | `fake`: every external data provider returns recorded fixtures. `live`: real calls, and a provider with no key raises `NotConfigured` | Required | Startup fails | `fake` locally and in CI. `live` is required in staging and production, and is what you set to use the keys below |
| `TRAVELPAYOUTS_TOKEN`, `TRAVELPAYOUTS_MARKER` | Cached fares API, and the affiliate marker in partner URLs | Optional | Fake fares | travelpayouts.com, free account |
| `SERPAPI_API_KEY` | Live fares and rentals, behind flag `serpapi_live_fares` (off by default) | Optional | Flag stays off, no live searches | serpapi.com, free plan: 250 searches a month |
| `SERPAPI_MONTHLY_CAP` | Global search cap | Optional | The `.env.example` value | `250` on the free plan |
| `GEOAPIFY_API_KEY` | Place search and geocoding | Optional | Fake place search | geoapify.com, free: 3,000 credits a day |
| `WIKIMEDIA_CONTACT` | Contact in the Wikipedia API user agent | Optional | Nothing: `PROVIDERS_MODE=fake` never calls Wikimedia | Any email you read; set it before using `PROVIDERS_MODE=live` |
| `FRANKFURTER_BASE_URL` | FX rates, no key | Required | Startup fails | `https://api.frankfurter.dev` |

Map tiles come from OpenFreeMap and need no key.

## Affiliate and purchases

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `VIATOR_API_KEY` | Viator partner API | Optional | Activity cards hidden by the kill switch | Viator partner program, self-serve signup |
| `STAY22_AID` | Stay22 affiliate id | Optional | Stay cards hidden by the kill switch | stay22.com, self-serve signup |
| `REVENUECAT_API_KEY` | REST key for the purchase reconcile | Optional | The reconcile job logs and skips | app.revenuecat.com; products come from App Store Connect |

`REVENUECAT_WEBHOOK_SECRET` is generated by setup, so it is listed under "Secrets generated by setup".

## Email and storage

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `EMAIL_BACKEND` | `console`, `file` or `resend` only. `EMAIL_PROVIDER` is deleted; SES is a manual standby, 02 section 8 | Required | Startup fails | `file` locally (messages go to `.data/outbox`), `resend` in staging and production |
| `RESEND_API_KEY` | Sends email | Optional | The `file` backend | resend.com, free tier; verify a sending domain |
| `RESEND_WEBHOOK_SECRET` | Authorizes bounce webhooks | Optional | The webhook route refuses calls | Resend dashboard, webhooks |
| `EMAIL_FROM` | From address | Optional | A local placeholder | `Hermi <hello@your-domain>` once the domain exists (WF-001) |
| `STORAGE_BACKEND` | `local` or `r2` | Required | Startup fails | `local` (files in `.data/storage`, signed URLs from the API), `r2` in production |
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | R2 S3 credentials | Production only | Local storage | Cloudflare dashboard, R2, API tokens. R2 needs a card on file |
| `R2_BUCKET_UPLOADS`, `R2_BUCKET_EXPORTS`, `R2_BUCKET_BACKUPS` | Bucket names | Production only | Local storage | Create them in R2 (`hermi-uploads` and so on) |
| `R2_ENDPOINT_URL` | S3 endpoint of the R2 account. New | Production only | Local storage | `https://<account id>.r2.cloudflarestorage.com` |

## Apple and iOS

Nothing on your Windows machine needs these. They come with the Apple Developer Program ($99 a year) and are used
by the iOS build (`knowledge/ios-builds-on-ci.md`). Locally, push, App Attest and token revocation log and skip.
The `.p8` private keys are secrets: never commit one (`*.p8` is in `.gitignore`).

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `APPLE_TEAM_ID`, `APPLE_BUNDLE_ID` | App identity for App Attest and Apple APIs | Production only | App Attest checks are skipped | developer.apple.com, Membership, and the bundle id you register |
| `APPLE_APP_ATTEST_ENV` | `development` or `production` attestation | Production only | Skipped | Your choice per build |
| `APPLE_SIGNIN_KEY_ID`, `APPLE_SIGNIN_PRIVATE_KEY` | Sign in with Apple key, used to revoke tokens on deletion | Production only | Revocation logs and skips | developer.apple.com, Keys |
| `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_PRIVATE_KEY` | Token-based push | Production only | Push logs and skips | developer.apple.com, Keys (APNs) |
| `APNS_TOPIC`, `APNS_USE_SANDBOX` | Bundle id topic, and the sandbox switch | Production only | Push logs and skips | The bundle id; `true` for development builds |
| `VITE_REVENUECAT_KEY_IOS` | Public SDK key for iOS purchases | Production only | The purchase screen shows its unavailable state | app.revenuecat.com, the iOS app |

## Observability

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `SENTRY_DSN`, `VITE_SENTRY_DSN` | Error reporting | Optional | Off | sentry.io, free plan |
| `SENTRY_AUTH_TOKEN` | CI only: upload source maps and dSYMs | Optional | The upload is skipped | sentry.io auth tokens, stored as a GitHub Actions secret |
| `POSTHOG_KEY`, `VITE_POSTHOG_KEY`, `POSTHOG_HOST` | Product analytics | Optional | Events are dropped | posthog.com, free plan |
| `BETTERSTACK_SOURCE_TOKEN` | Log shipping | Production only | Logs stay local | betterstack.com, free tier |
| `BETTERSTACK_HEARTBEAT_SCHEDULER`, `BETTERSTACK_HEARTBEAT_QUEUE` | Heartbeat URLs (each URL is a bearer secret) | Production only | Heartbeats are skipped | Better Stack, heartbeats |
| `STATUS_PAGE_URL`, `VITE_STATUS_PAGE_URL` | The hosted public status page | Production only | The Settings link is hidden | The Better Stack status page you create |
| `ALERT_WEBHOOK_URL` | Chat channel for alerts | Production only | Alerts are logged only | A Slack or Discord incoming webhook |

## Admin

| Variable | Purpose | Local need | Fallback when missing | Where to get it |
|---|---|---|---|---|
| `ADMIN_AUTH_MODE` | `cf_access` or `dev`. `dev` uses a fake Access signer for seeded admins | Required | Startup fails | `dev` locally, `cf_access` in production. The first admin is `hermi admin-grant` |
| `CF_ACCESS_TEAM_DOMAIN` | Cloudflare Access team domain | Production only | Admin sign-in is unavailable | Cloudflare Zero Trust (free to 50 users) |
| `CF_ACCESS_AUD` | Audience tag of the Access application | Production only | Admin sign-in is unavailable | The Access application's settings |

## Accounts that are not variables

| Account | What it is for | Local need | Cost and notes |
|---|---|---|---|
| Claude subscription (Max) | `claude.exe` for the local AI provider and for the autopilot | Required for real AI answers | Already signed in on this machine. Check with `claude auth status` |
| GitHub | The public repo, branch protection, Actions, the autopilot's `gh` | Required for the autopilot only | Free for a public repo, which also makes macOS CI free |
| Supabase, Google Cloud | Real sign-in and Google sign-in | Optional | Free plans |
| Apple Developer Program, App Store Connect, RevenueCat | iOS builds, TestFlight, purchases | Production only | $99 a year |
| Render | API, worker and Postgres in staging and production | Production only | Paid, about $80 to $100 a month planned |
| Cloudflare | DNS, Pages, WAF, Access, R2 | Production only | Free plans (R2 needs a card). A deploy API token and the account id become GitHub secrets |
| The domain and a support email | Links, email, store listing | Production only | WF-001 |
