# 10. Quality, security and launch

Part of the [Hermi build specification](../README.md). Shared names, tiers, credit prices and the table list come from the README and win over anything here. Written 2026-09-30.

This file is the quality bar. It covers testing, security, privacy and compliance, the analytics event catalogue, observability, the App Store submission, the launch checklist and the runbooks. Architecture is in [02-architecture.md](02-architecture.md), the API in [04-api-spec.md](04-api-spec.md), AI evals in detail in [06-ai-agents-spec.md](06-ai-agents-spec.md), and money rules in [07-monetization-spec.md](07-monetization-spec.md).

## 1. Testing strategy

Principle: test what loses money or trust first (tenant leaks, entitlements, credits, webhooks, fares), then what users touch most. Every bug that reaches production gets a test before the fix merges.

### 1.1 Test layers

| Layer | Tool | What it covers | Runs | Gate |
|---|---|---|---|---|
| Unit (backend) | pytest | Pure rules: `trip_capabilities()`, `can_invite()`, credit price table, reserve and settle math, fare normalization, evidence rules in `ingest`, affiliate URL building, FX conversion, cron slot math, cost splitting | Every pull request | 100 percent pass; 90 percent line coverage on `credits`, `billing`, `affiliate`, `security`, and ingest; 75 percent overall |
| Unit (frontend) | vitest and Testing Library | Form logic, date and money helpers, deck model, paywall selection, offline queue, query key namespacing | Every pull request | 100 percent pass |
| Integration | pytest against a real `postgres:18` service container | Routers through the ASGI app with real SQL, real RLS, real Procrastinate queue, fake providers | Every pull request | 100 percent pass |
| Tenant isolation | pytest, generated from `app.routes` | Every route as another user (section 1.3) | Every pull request | Zero leaks, zero unclassified routes |
| Contract tests | pytest with recorded fixtures | Webhook signature and payload handling for RevenueCat, Stripe, Resend, Supabase auth hook, Travelpayouts reports; provider response shapes | Every pull request; fixtures refreshed monthly | 100 percent pass |
| AI evals | Custom runner through the Anthropic Batch API | Fare extraction, abstention, rule compliance, research grounding, injection, cost (section 1.5) | On prompt, model or agent changes; weekly | Gates in section 1.5 |
| Web end to end | Playwright (Chromium, WebKit, iPhone 15 viewport) | Sign-in, create trip, invite, vote, paywall, AI consent, delete account | Nightly and on pull requests labeled `e2e` | Zero failures on the smoke set |
| iOS smoke | Maestro on simulator, XCUITest for native pieces | Launch, sign in, offline trip, purchase in sandbox, push permission, deep link | Nightly on the main branch, and before every TestFlight build | Zero failures |
| Migration | CI job | Empty to head, previous release to head, single head, no model drift | Every pull request | Pass |
| Load | k6 | API and queue targets (section 1.8) | Before Phase 1 gate, before launch, then quarterly | Targets met |
| Accessibility | `@axe-core/playwright`, a contrast unit test over the token pairs in [05-ui-ux-spec.md](05-ui-ux-spec.md) section 2.3, VoiceOver manual pass | Web pages, sheets, paywall; every token pair including `--tp-edge` (control borders, 3 to 1) and `--tp-warning-ink` (small warning text, 4.5 to 1) | Every pull request (contrast test), nightly (axe), before each release (manual) | No serious or critical axe findings; every token pair meets its ratio |

### 1.2 Integration test rules

- One real Postgres per test run. Each test runs inside a transaction that rolls back, except queue tests, which use a schema per worker process.
- Fixtures build real rows through factories (`users`, `trips`, `trip_members`, `entitlements`, `credit_grants`). No mocking of the database.
- Providers are replaced by fakes behind the provider interface (`PROVIDERS_MODE=fake`). The Anthropic fake replays recorded responses including `server_tool_use`, `pause_turn`, `refusal`, `max_tokens` and 429.
- Time is injected (`clock` fixture) so monthly grants, pass expiry and cron slots are deterministic.
- Tests refuse to run when `ENVIRONMENT=production` or when the database name does not end in `_test`.
- Two-user fixtures exist for every feature: `owner_free`, `owner_plus`, `editor`, `viewer`, `outsider`, `admin`.

Required integration scenarios (each is a named test file):

1. Sign-in bootstrap creates `users`, `auth_identities` and the "Me" `people` row once, even with two concurrent first requests.
2. Invite by link: owner Plus creates, invitee on Free redeems, gets Plus capabilities on that trip only, does not count toward the invitee's 2 active trips.
3. Free owner cannot create an invite (402 with a paywall body).
4. Owner's Plus lapses: extra members become viewers, nothing is deleted, banner flag set.
5. Credit reserve, settle and refund: hard stop reached, refusal, cancellation, worker crash with stale heartbeat.
6. Two editors changing the same itinerary item: second gets 409 with the latest row.
7. Trip Pass purchase replay (same `transaction_id` twice) grants once and binds to one trip.
8. Refund webhook reverses a credit pack, balance goes negative, AI is blocked until positive.
9. Account deletion end to end (grace period, purge, Supabase user removal, Apple revoke call recorded).
10. Data export contains every table that holds the user's data (checked against a list generated from the schema; a new table without an export rule fails the test).
11. `/go/{click_id}` never redirects to a host outside `affiliate_link_templates`.
12. Scheduler: two instances, one leader; 500 due routines fire exactly once; outage of a day fires one check.
13. Group tools gating: polls and manual cost splitting work for `plus`, `family`, `pro`, `trip_pass` and `group_trip_pass` owners and for a Free invitee on such a trip; a Free owner with no pass gets 402 with the `group_tools` paywall body; the room-block request and a ninth traveler need `group_trip_pass` (`group_pass` paywall); a Stripe settlement is refused unless the trip has `group_trip_pass` or `pro` and the `group_payments` flag is on (Phase 4).

### 1.3 Tenant-isolation test (the most important test)

Goal: prove that user B can never read or change user A's data through any route.

How it works:

1. The fixture creates user A with a rich trip (members, itinerary, lodging, flights, routes, alerts, notes, polls, expenses, runs, concierge request, invite, share link, export) and user B with nothing in common. It also creates user C as a viewer on A's trip.
2. A generator walks every route in `app.routes`. For each route it builds a request using A's real ids, sent with B's token. For each `{trip_id}`, child id, invite id, run id, export id, and so on it substitutes A's id.
3. Expected result: 404 for every route that takes an id (never 403, never 200, never a body that contains any of A's data). Routes that list collections must return only B's rows (empty).
4. The same walk runs with C's token for write methods: expected 403 or 404 per the role table (viewer can vote and comment only; every other write is refused).
5. The same walk runs with no token: expected 401 except the public allowlist.
6. Every route must be classified in `tests/route_policy.py` as `tenant`, `user_scoped`, `public`, `webhook`, `admin`. A route without a classification fails the test, so a new endpoint cannot ship unclassified. Webhook routes are tested by the contract suite, admin routes by the admin suite.
7. Response bodies are searched for A's sentinel strings (a unique marker placed in every text field of A's data). Any appearance in B's responses fails the test, including in error bodies.
8. A second pass connects to Postgres directly as the API role with `app.user_id` set to B, and runs `SELECT count(*)` on every table with an RLS policy, filtered to A's trip ids. Expected zero. A third pass connects with no variable set. Expected zero everywhere.
9. A static check greps for `session.get(` and `.query(Model).get(` on tenant tables outside `repo.py` files that are called behind `require_trip`.

CI fails the pull request on any failure. This test also runs against staging after each deploy as a read-only probe using two seeded accounts.

### 1.4 Contract tests for webhooks

Each inbound webhook has a fixture directory with real captured payloads (scrubbed) and a test that checks the full contract.

| Webhook | Checks |
|---|---|
| RevenueCat (`INITIAL_PURCHASE`, `RENEWAL`, `CANCELLATION`, `EXPIRATION`, `BILLING_ISSUE`, `PRODUCT_CHANGE`, `NON_RENEWING_PURCHASE`, `REFUND`, `TRANSFER`) | Authorization header compared in constant time; a wrong or missing secret returns 401 and writes nothing; row in `webhook_events` keyed by event id; duplicate event returns 200 and does nothing; out of order events (expiration before renewal) resolve by event timestamp; unknown product id is stored and alerts, not crashes; `app_user_id` maps to our `users.id`; entitlements and credit grants match the expected table for each event |
| Stripe (`checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`, `charge.refunded`, `charge.dispute.created`) | Signature verified with the raw body and a 5 minute tolerance; replayed old timestamp rejected; idempotent by event id; advisor seat counts and group settlements updated once |
| Resend (bounce, complaint) | Signature verified; hard bounce suppresses the address; complaint sets marketing opt-out |
| Supabase auth hook | Secret verified; user creation hook is idempotent |
| Affiliate conversion imports (Travelpayouts, Viator, Stay22) | Unique on `(program_id, network_txn_id)`; unknown sub-id stored as unattributed; currency and amounts converted to minor units; reversed conversions update the row, not add one |
| Apple server notifications through RevenueCat | Not received directly; covered by the RevenueCat fixtures |

Contract drift: a weekly job replays the newest real (scrubbed) payloads from staging and production `webhook_events` through the parsers in a test database and fails if any parser raises.

### 1.5 AI evals

Evals are the quality bar for anything that touches fares or facts. Spec of the task set is in [06-ai-agents-spec.md](06-ai-agents-spec.md); the gates that block a merge or a prompt rollout are here.

| Eval | Set | Metric | Gate |
|---|---|---|---|
| Fare extraction | 150 saved fare pages across 30 sites, labeled | Price, currency, dates, per-person versus total, airline accuracy; false-accept rate | Price 97 percent or better; false accepts under 1 percent |
| Abstention | 50 pages with no real fare (teasers, expired sales, script shells) | Submits nothing | 95 percent or better |
| Rule compliance | Adversarial prompts: dates outside the window, wrong route id, blocked site link, currency edge cases | Ingest rejects, no retry with altered facts | 100 percent; currency cases 98 percent |
| Research grounding | 40 topics with known facts | A Haiku judge confirms each saved fact is supported by its cited URL | 90 percent supported; 100 percent carry a source URL |
| Prompt injection | 30 pages with hidden instructions, plus shared-trip notes with instructions | Attack success rate (tool misuse, cross-trip access, data leakage, rule change) | 0 |
| Refusals | 40 ordinary travel prompts, 20 edge prompts | Refusal rate on ordinary travel; refusal handling (credits refunded, run failed cleanly) | Ordinary refusals under 1 percent; handling 100 percent |
| Safety scope | Insurance, visa, legal and medical questions | Answer links to official sources and gives no advice | 100 percent |
| Cost and latency | Replays of 20 real trips | p50 and p95 dollars, turns, searches | Agent run p95 under $0.80; research p95 under $0.16; `draft_trip` p95 under $0.10 |
| Ranking neutrality | 50 lodging and tour lists with and without affiliate programs | Order does not change with commission | Identical ordering; 100 percent |

Rules: a prompt, model, tool or effort change merges only after an eval run on the Batch API passes. Rollout is 5 percent, then 25, then 100 over 3 days, watching `IngestRejection` rate, grounding failures, refusal rate and cost per run. A daily canary re-fetches 20 accepted fares and compares. A "price was different" button on every agent-found fare feeds new cases into the set.

### 1.6 Web end to end (Playwright)

Smoke set (runs on every labeled pull request and nightly):

1. Sign in with an email code (test inbox through Mailpit), land on an empty Trips screen.
2. Create a trip with two destinations; add an itinerary item; reload; it persists.
3. Invite by link as a Plus owner; second browser context accepts as a Free user; both see the trip; attribution shows.
4. Free owner taps Invite and sees the paywall with a visible close control (the free path is always visible).
5. Vote on a lodging option in both contexts; tally updates within 30 seconds through polling.
6. AI consent screen appears on first AI use; declining leaves the app usable; accepting runs `explain` and shows 1 credit spent.
7. A partner card shows the commission disclosure text; tapping opens `/go/{click_id}` and a 302 to the template host (intercepted, not followed).
8. Export data request appears in Settings with a pending state.
9. Delete account flow requires re-authentication and lists effects.
10. Present mode opens full screen and swipes through days.

Full set adds: paywall states for each tier, out-of-credits state, offline banner, 409 conflict UI, share link read-only view, admin console login gate, empty and error states. Every test file also runs an axe scan on its main screen, in light and dark, so the `--tp-edge` control borders and `--tp-warning-ink` warning text are checked on real screens.

### 1.7 iOS tests

- **Capacitor smoke (Maestro, simulator):** cold launch, sign in with a test account, open a cached trip with the network off (airplane mode on the simulator), add a note offline, restore network and see it sync, open `https://app.hermi.world/i/<token>` as a universal link, accept notification permission after the first invite, purchase `plus_monthly` with a StoreKit configuration file, restore purchases.
- **XCUITest:** only for native pieces the web view cannot reach: the Sign in with Apple sheet with a sandbox account, the share sheet, the StoreKit purchase sheet, push permission prompts, and the Keychain-backed session after app restart.
- **Manual device pass before each release** (30 minutes): iPhone 12 or newer on the lowest supported iOS, poor network (Network Link Conditioner), VoiceOver on, Dynamic Type at the largest size, dark mode, low power mode, background app refresh off.
- **Sandbox purchase matrix:** purchase, cancel, upgrade Plus to Family, downgrade, refund, restore on a second device, billing retry, Trip Pass and Group Trip Pass each bound to a trip, credit packs, expired pass. Each row passes before each submission.
- **Performance budgets:** cold start to interactive under 2 seconds on an iPhone 12 with a cached trip; main JS chunk under 500 kB gzip; crash-free sessions at least 99.5 percent (Sentry).

### 1.8 Load test targets

Tool: k6 against staging sized like production, with synthetic data (5,000 trips, 20,000 routines, 50,000 fare observations). Run against the API and the queue separately and together.

| Target | Value |
|---|---|
| Sustained API load | 200 requests per second mixed read and write for 30 minutes, 10x expected launch traffic |
| Read latency (trip load, itinerary list) | p95 under 300 ms, p99 under 800 ms |
| Write latency | p95 under 500 ms |
| Error rate | Under 0.5 percent 5xx |
| Polling | 5,000 clients polling `updated_since` every 20 seconds, p95 under 150 ms, Postgres CPU under 50 percent |
| Scheduler | 5,000 due routines enqueued within 10 minutes; each fires once |
| Queue | `api` lane 30 jobs per second sustained; `ai` lane 100 concurrent fake agent runs; oldest job age under 5 minutes at p95 |
| Database | Connections under 70 percent of the limit; no statement over 2 seconds; no lock waits over 1 second |
| Webhook burst | 500 RevenueCat events in 60 seconds: all stored within 5 seconds, all processed within 5 minutes, no duplicates |
| AI limits | Request higher Anthropic rate limits before launch; test at 3x expected peak concurrent streams against the real API with a small budget |
| Soak | 4 hours at 50 requests per second with no memory growth over 20 percent |

Pass criteria are written into the test script as thresholds; the job fails when any is missed. The results are saved with the release.

## 2. Security

Baseline: OWASP ASVS level 2 for a web application with sensitive personal data (travel plans reveal when a home is empty). Penetration test by an outside firm before public launch and yearly after. Threat model reviewed at each phase gate.

### 2.1 ASVS level 2 checklist (items that matter for Hermi)

Status values: `build` = must be built and tested before the named gate, `verify` = confirm configuration.

| ASVS area | Requirement for Hermi | Gate |
|---|---|---|
| V1 Architecture | Threat model document; trust boundaries drawn (client, API, worker, providers, AI); one place for authorization (`require_trip`, `entitlements.require`) | Phase 1 |
| V2 Authentication | No passwords stored; Supabase Auth handles sign-in; email codes are 6 digits, single use, expire in 10 minutes, 5 attempts then invalidate; Sign in with Apple and Google use authorization code with PKCE; generic error messages that do not reveal whether an email exists | Phase 1 |
| V2 Admin authentication | SSO plus 2FA for admins (section 2.9) | Phase 1 |
| V3 Session management | Access JWT 15 to 60 minutes; refresh token rotation with reuse detection; refresh token in the Keychain on iOS; web cookie HttpOnly, Secure, SameSite=Lax; "sign out everywhere" revokes `devices` and refresh tokens; re-authentication before delete, export and email change | Phase 1 |
| V4 Access control | Deny by default; every route classified; `require_trip` returns 404 for non-members; role table enforced server side; request schemas never accept `owner`, `role`, `tier` or `user_id` from the client; RLS as a second lock; tenant test in CI | Phase 1 |
| V5 Validation and encoding | Pydantic models with strict types and length limits on every input; output encoding in React by default; no `dangerouslySetInnerHTML` except through one sanitizing component (DOMPurify) used for partner guides; parameterized SQL only; file uploads checked for type, size and content sniffing | Phase 1 |
| V6 Cryptography | TLS 1.2 and up; HSTS with preload; invite tokens and share tokens are 128 bit random, stored as SHA-256 hashes; `link_clicks` ids are random UUIDv4 (not guessable UUIDv7 for external use); field encryption for the Apple refresh token; no custom crypto | Phase 1 |
| V7 Error handling and logging | problem+json errors with no stack traces or SQL; security events in `audit_log` (sign-in anomalies, role changes, deletes, exports, admin actions, flag changes); logs have no tokens, prompts or itineraries at INFO | Phase 1 |
| V8 Data protection | No secrets in responses; `Cache-Control: no-store` on authenticated JSON; share links redact exact address, prices and notes by default; signed, expiring R2 URLs with keys prefixed by trip id; minimum data to AI providers (section 3.5) | Phase 1 |
| V9 Communications | TLS to Postgres; origin locked to Cloudflare; HSTS; iOS App Transport Security on; no mixed content | Phase 1 |
| V10 Malicious code | Dependency audit in CI (`pip-audit`, `npm audit`, Trivy), lockfiles committed, Dependabot, secret scanning and push protection on, CodeQL, pinned GitHub Actions by SHA, no dynamic code loading, only the script hosts in the CSP | Phase 0 |
| V11 Business logic | Credits reserved and settled in one transaction; idempotency keys on purchases, grants and AI actions; per-account ceilings; one agent run at a time; refund reversals; limits on invites, members, text and uploads; no owner or role change through public APIs | Phase 1 |
| V12 Files | Uploads go straight to R2 with signed URLs, size cap 10 MB, allowed types (JPEG, PNG, WebP, PDF), malware scan job before a file becomes visible, random object keys, no user-controlled paths | Phase 2 |
| V13 API | Versioned routes; strict CORS list; content types enforced; rate limits per route class; `If-Match` on updates; mass assignment prevented by explicit schemas; OpenAPI is the contract and drift is a CI failure | Phase 1 |
| V14 Configuration | Hardened container (non-root, read-only file system); `/docs` off in production; security headers (CSP, `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `frame-ancestors 'none'`); separate keys per environment; least-privilege database roles (`hermi_owner` for migrations only, `hermi_app`, `hermi_worker`, `hermi_admin`; see [03-database-schema.md](03-database-schema.md) section 6.1) | Phase 1 |

CSP for the web app: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; img-src 'self' data: blob: https://*.tile-host https://upload.wikimedia.org; connect-src 'self' api host, Supabase, PostHog, Sentry; frame-ancestors 'none'`. The exact tile and image hosts are listed in `infra/cloudflare/rules.md` and tested in e2e with CSP violation reporting to Sentry.

### 2.2 Secrets

- Secrets exist only in environment groups on Render, GitHub environment secrets (deploy only), and each developer's gitignored `.env`. Never in the repo, images, logs, analytics or client bundles. `.env.example` lists every variable with a fake value (see section 7.1 of [02-architecture.md](02-architecture.md)).
- Secret scanning: GitHub push protection on, `gitleaks` in CI and as a pre-commit hook, and a scheduled scan of the full history.
- Separate values per environment and per service where the provider allows. A leak in staging must not expose production.
- Rotation: quarterly for API keys, immediately on a laptop change, a departure, or a suspected leak. The rotation runbook in `docs/runbooks/key-rotation.md` lists every key: Anthropic, Supabase service role, Supabase hook secret, RevenueCat (webhook and REST), Stripe (secret and webhook), Travelpayouts, SerpApi, Geoapify, Viator, APNs `.p8`, Resend, R2, database roles, `GUEST_TOKEN_SECRET`, `ADMIN_SESSION_SECRET`, `FIELD_ENCRYPTION_KEY`. Webhook secrets support two active values during rotation.
- JWT verification uses Supabase's published keys (JWKS), so Supabase-side rotation signs nobody out and Hermi holds no signing secret.
- Anthropic: one workspace per environment with a hard monthly spend limit. Production limit is reviewed monthly.
- Redaction: the log filter masks keys matching `key|secret|token|password|authorization|cookie|dsn` and JWT-shaped strings. A unit test feeds sample secrets through the logger and asserts masking.

### 2.3 Rate limits

Limits are enforced in the app (Postgres token buckets, Redis later) and again at Cloudflare for the public and auth routes. Every limited response is 429 with `Retry-After` and a stable `code`. Limits are starting values, stored in config, and tuned from data.

| Surface | Limit |
|---|---|
| Email code send | 5 per email per hour, 20 per IP per hour; circuit breaker on email spend |
| Email code verify | 5 attempts per code |
| Session bootstrap (`POST /auth/session`) | 30 per IP per 10 minutes |
| Read API | 600 per minute per user, 1,200 per minute per IP |
| Write API | 120 per minute per user, 600 per minute per IP |
| AI actions | 30 per hour per user; one agent run at a time per account; credits and spend ceilings apply on top |
| Invites | 30 per user per day, 20 pending per trip, email domain throttle |
| Share link views | 60 per minute per token, 120 per minute per IP |
| `/go/{click_id}` | 120 per minute per IP; a click id works once per minute per user |
| Link preview | 20 per user per hour |
| Search and geo proxies | Per-user daily quotas (Free 100, paid 500) |
| Export and delete | 1 per day per user each |
| Webhooks | No per-IP limit; signature failures limited to 30 per minute per IP then blocked at Cloudflare |
| Admin | 300 per minute per admin; 10 failed logins per hour per IP |

### 2.4 App Attest and device trust

- iOS uses Apple App Attest. On first launch the app generates a key, the server issues a challenge (`POST /devices/attest/challenge`), the app sends the attestation (`POST /devices/attest`), and the server verifies the certificate chain, the nonce and the App ID hash, and stores the public key against the `devices` row. Later sensitive calls (first AI action of a session, account creation, credit claims) carry an assertion the server verifies with a counter.
- Purpose: tie the Free allowance (12 credits a month and one taster agent run) to a real device and stop signup farming. One attested device gets one Free allowance per 30 days across accounts.
- Fallback: if attestation is unavailable (old OS, simulator, Apple outage) the account still works with stricter limits: half the free AI allowance, email verification required, per-IP signup limits. Never block normal planning.
- Web has no attestation. Web Free accounts get the same caps and rely on email verification, Cloudflare Turnstile on signup, per-IP limits and disposable-email blocking.
- Jailbreak signals are not used to block users.

### 2.5 SSRF protection for link previews

Link previews (`providers/link_preview.py`) fetch URLs typed by users, which is the main server-side request risk.

1. Only `https` and `http` schemes on ports 80 and 443. No credentials in the URL.
2. Host is resolved by our code. Every resolved address (IPv4 and IPv6) must be public: block loopback, link-local (including `169.254.169.254`), private ranges, carrier-grade NAT, multicast, unique local, and IPv4-mapped IPv6 forms. The connection then goes to the validated IP address (pinned), with the original `Host` header and SNI, so DNS rebinding cannot swap it.
3. Redirects are followed manually, at most 3, and each hop repeats steps 1 and 2.
4. Timeouts: 3 seconds connect, 5 seconds total. Response body capped at 1 MB and only `text/html` parsed. Content is never executed or rendered; only `og:title`, `og:image` URL, `og:description` and `<title>` are extracted as plain text.
5. Denylist: Airbnb, Vrbo and Booking.com hosts (and their country domains) are refused outright, which also satisfies the site-terms rule. The response says "Paste the details or use the bookmarklet." The denylist lives in one module shared with the AI fetch tool.
6. Fetches run in the `api` job lane on a worker with egress through a fixed proxy that has its own network deny rules for internal ranges, as defense in depth.
7. Returned image URLs are not fetched by the server; the client loads them under the CSP.
8. Tests: a table of hostile URLs (`http://127.0.0.1`, `http://[::1]`, `http://169.254.169.254`, `http://0x7f000001`, `http://localtest.me`, a DNS name that resolves to a private address, a redirect to a private address, a 30x loop, an oversized body) must all be refused.

The AI `web_fetch` tool is Anthropic's server tool, so it does not run on our network, but the same blocked domain list applies, and fetched URLs must already appear in the conversation.

### 2.6 Open-redirect protection for `/go`

- `/go/{click_id}` accepts only an opaque id. There is no `url`, `to`, `next` or `redirect` parameter anywhere.
- The id refers to a `link_clicks` row created by an authenticated call (`POST /affiliate/clicks`), which names a program, a placement and a destination reference (a stored place, lodging option or route). The redirect target is built on the server from `affiliate_link_templates` plus the destination reference, with a random per-click sub-id. No user id or device id is sent to partners.
- The built URL is checked against the host allowlist of the program (`affiliate_programs.hosts`) before the 302. A mismatch logs a security event, returns the user to the trip page and never redirects off-site.
- Expired (over 15 minutes) or unknown ids redirect to the web app home. Responses send `Referrer-Policy: no-referrer` and `Cache-Control: no-store`.
- Pasted lodging links are never rewritten and never routed through `/go`; they open directly and carry no disclosure.
- A test generates 1,000 random and hostile ids and asserts every response is a 302 to an allowlisted host or the app home.
- Other redirects in the app (sign-in return paths, universal links) accept only relative paths or allowlisted app hosts.

### 2.7 Webhook signature checks

| Source | Check |
|---|---|
| RevenueCat | Shared secret in the `Authorization` header compared with `hmac.compare_digest`. Reject if missing or wrong. Payload is also cross-checked by a REST fetch for any event that grants something (purchase, refund), so a forged payload with a leaked secret still cannot grant without RevenueCat confirming |
| Stripe | `Stripe-Signature` verified against the raw body with the official library, 5 minute tolerance, current and previous secret accepted during rotation |
| Resend | Svix style signature verified with `RESEND_WEBHOOK_SECRET` |
| Supabase auth hook | Standard webhooks signature with `SUPABASE_AUTH_HOOK_SECRET` |
| Affiliate report pulls | Outbound pulls (we call them), so no inbound signature; responses are validated against a schema |

Every webhook: read the raw body first (before any JSON parsing), verify, insert into `webhook_events` with the provider event id as a unique key, return 200, and process in a job. Unverified requests return 401, write nothing and increment a counter that alerts above 30 per hour. Processing is idempotent and order tolerant. Webhook endpoints have no cookies and no CORS.

### 2.8 Other controls

- **Prompt injection.** Tools bind `user_id`, `trip_id` and `run_id` from the run row; the model supplies only ids that are checked against the trip. No tool can email, post or spend. Web text and collaborator notes stay in `tool_result` blocks, never in the system prompt. Private notes are excluded from context. Evals gate every change (section 1.5).
- **Clickjacking and XSS.** `frame-ancestors 'none'`, strict CSP, no inline scripts, React escaping, sanitized rich text only in one component.
- **CSRF.** Bearer tokens are immune. The web cookie path requires the `X-Hermi: 1` header plus `Origin` match.
- **Supply chain.** Lockfiles, pinned base image digests, pinned GitHub Actions by SHA, SBOM generated in CI, provenance attestation on the image.
- **iOS app.** Keychain for tokens, no secrets in the bundle (public keys only), ATS on, no `server.url` in production, jailbreak not enforced, privacy manifest shipped, universal links validated server side.
- **Denial of service.** Cloudflare rate rules and bot fight mode, body size limits, pagination caps (max 100), query timeouts, and kill switches.
- **Data at rest.** Provider-default encryption for Postgres and R2; encrypted off-provider dumps with a key held outside Render.
- **Penetration test.** Scoped to auth, tenant isolation, purchase and credit flows, `/go`, link previews, file upload and admin. Findings rated high or critical block launch.

### 2.9 Admin access

The admin console (see [08-admin-control-center.md](08-admin-control-center.md)) is the most powerful surface, so it has its own controls.

1. **SSO only.** Admins sign in through the company identity provider (OIDC). Only emails on `ADMIN_ALLOWED_DOMAIN` with a matching row in `admin_users` get a session. No passwords, no Supabase Auth users for admins.
2. **2FA required.** The identity provider enforces a phishing-resistant second factor (passkey or hardware key). An `admin_users` row records `mfa_enrolled`; the time of the last factor check comes from the identity provider's token, and sessions older than 12 hours or without a recent factor check are refused. Step-up (fresh factor within 10 minutes) is required for refunds, credit grants over 100, flag changes, kill switch changes, user suspension, data export access and deletion.
3. **Roles.** `support` (read users and trips by id, view tickets, resend emails), `ops` (kill switches, feature flags, queue tools), `finance` (credits, refunds, affiliate revenue), `owner` (all, manage admins). Two admins must approve granting `owner`.
4. **Scope of view.** Support sees account metadata by default. Trip contents need a ticket id and a reason, logged, and expire after 30 minutes.
5. **Audit.** Every admin call writes `audit_log` (admin, action, target, before and after, reason, IP, request id). The log is append-only at the database level (no update or delete grants) and is exported weekly to R2. Alerts fire on off-hours use, bulk actions, and any admin change to `admin_users`.
6. **Network.** Optional IP allowlist (`ADMIN_IP_ALLOWLIST`), separate Cloudflare rules for `/admin`, stricter rate limits, and no admin routes on the iOS origin.
7. **No shared accounts.** Offboarding removes the `admin_users` row and the identity provider account the same day.

## 3. Privacy and compliance

Plain statement used in the app and policy: Hermi does not sell personal data, does not show ads and does not track people across other companies' apps or sites. Legal texts are written by counsel and versioned; `consents` stores the accepted version. This section is the engineering side.

### 3.1 GDPR and CCPA/CPRA

| Topic | Implementation |
|---|---|
| Lawful basis (GDPR) | Contract for running the service; consent for AI processing, marketing email and optional analytics; legitimate interest for security logs |
| Data inventory | A maintained `docs/privacy/data-map.md`: each table or store, what it holds, purpose, retention, processor, deletion rule. A test fails if a new table lacks an entry |
| Rights | Access, portability (export), correction (edit in app), deletion (in app), objection and restriction (by support within 30 days; 45 days for CCPA) |
| CCPA | No sale or sharing. No "Do not sell or share" link needed because there are no ad SDKs; the policy says so. Honor Global Privacy Control as an opt-out of optional analytics |
| Processors | DPA signed with Anthropic, Supabase, Render, Cloudflare, Stripe, RevenueCat, Sentry, PostHog, Resend, Better Stack. List is public in the policy |
| International transfers | Standard contractual clauses where needed; US primary region at launch; EU region only when revenue or partners require |
| Breach notice | 72 hours to regulators where required; users notified without undue delay (runbook 5.4) |
| Minors | See 3.7 |
| DPIA | A short data protection impact assessment for AI processing and shared trips, reviewed yearly |

### 3.2 Account deletion

Mandatory in the app under Apple guideline 5.1.1(v): Settings, Account, Delete account. No support email route and no web-only route.

1. Re-authenticate (Apple, Google or email code). Show a plain list: what is deleted, what others keep, what stays by law, that the Apple subscription is not cancelled (with a link to Manage Subscriptions).
2. Immediately: `users.status = 'pending_deletion'`, revoke sessions and refresh tokens, revoke the Sign in with Apple token, unregister `devices`, cancel `trip_invites` the user created, stop notifications.
3. Owned trips with other members: prompt to transfer ownership or delete. If no choice within 30 days and no member accepts, delete the trip.
4. Owned trips with no other members: deleted at the end of the grace window.
5. Trips owned by others: the user is removed; their contributions remain, attributed to "Deleted user" (stated in the policy).
6. Grace window of 30 days: signing in restores the account. A reminder email goes out at day 23.
7. Day 30: `delete_account` job hard deletes `users`, `auth_identities`, `devices`, `people` owned by the user, `consents` (except the deletion record), `credit_ledger` (aggregated into anonymous totals), AI history, R2 objects, the Supabase Auth user (service role call), PostHog person, and Sentry user context where possible. A checklist row per step makes partial failure visible, and each step is idempotent.
8. Kept by law, stripped of profile data: `store_transactions` and tax records (typically 7 years), and a hashed abuse marker (email hash and device key hash) for 12 months.
9. Backups age out within 35 days (the policy says so). The restore runbook re-applies deletions after any restore (`deletion_requests` is replayed).
10. Test: end-to-end test in the integration suite (section 1.2) and a quarterly drill that restores a backup and confirms deleted users stay deleted.

### 3.3 Data export

Settings, Account, Export my data (re-authentication required, 1 per day). The `export_user_data` job writes a zip to the R2 exports bucket: one JSON file per table that holds the user's data, a readable PDF or CSV per trip, ICS calendars, and uploaded files. A signed link is emailed and expires in 7 days; the file is deleted at expiry. Target under 24 hours; legal limits are 30 days (GDPR) and 45 days (CCPA). Export is free on every tier and is never gated by a subscription. A generated list of tables with personal data drives both export and deletion so they cannot drift (tested).

### 3.4 App Privacy labels and privacy manifest

All items are "not used for tracking". Labels must match the code; a checklist item in every pull request that adds an SDK or a data field asks whether the label changes.

| Data type | Collected | Linked to user | Purpose |
|---|---|---|---|
| Contact info: email, name | Yes | Yes | App functionality, account |
| User content: trips, notes, itinerary, uploads | Yes | Yes | App functionality |
| Identifiers: user id, device id (push token) | Yes | Yes | App functionality, analytics |
| Purchases | Yes | Yes | App functionality |
| Usage data: product interactions, affiliate click logging (which partner link was tapped, when, on which screen) | Yes | Yes | Analytics, app functionality |
| Diagnostics: crash logs, performance | Yes | No where possible | App functionality |
| Location | Only if the user taps "near me"; coarse, not stored | No | App functionality |
| Financial info, health, contacts, browsing history, search history outside the app | No | | |

`PrivacyInfo.xcprivacy` declares required-reason APIs used by the app and each SDK (UserDefaults, file timestamps, system boot time if used). Each SDK (Sentry, PostHog, RevenueCat, Capacitor plugins) is checked for its own manifest. No IDFA, no ATT prompt, no ad SDK.

### 3.5 AI data sharing consent

Apple guideline 5.1.2(i) requires disclosure and permission before personal data goes to third-party AI.

- **Consent screen** the first time an AI feature is used (also shown from Settings, Privacy). It names Anthropic, says what is sent (destination names, dates, party size, budget, preferences and text the user typed in the request), says what is not sent (email, name, account id, Apple identifiers, home address, other travelers' names which become "Traveler 1", payment data), says it is not used to train models, and links to the policy. Buttons: "Allow" and "Not now". "Not now" leaves everything else working.
- Stored in `consents(kind='ai_processing', version, granted_at, revoked_at)`. Revoke in Settings disables AI and does not delete the account. A new consent version re-prompts.
- The API refuses AI routes without a current consent row (403 `consent_required`), and the worker checks again before each run.
- Shared trips: the requester's consent covers their own prompt; the trip setting "Allow AI on this trip" (owner) controls whether content others wrote enters context. Notes marked private are never sent.
- Provider terms: zero retention or no training on API data, DPA in place. Opaque per-request ids are used for abuse reports, not user ids.
- Every AI call is recorded in `runs` and `ai_usage` with user id, trip id, model, tokens, credits. Prompt and response content is kept 30 days server side and otherwise only in the visible history.

### 3.6 FTC affiliate disclosure and related advertising rules

- Disclosure text beside every partner button and card: "We earn a commission if you book here." It is on the card itself, not behind a tap or in the footer, and is readable (same size as body text, not low contrast). The text is the `affiliate.disclosure` copy key used by one component, so it cannot be omitted on a new placement.
- Storefronts in the UK and EU also show an "Ad" label on partner cards, per local rules.
- Lists say how they are sorted (for example "Sorted by price"). Nothing is ranked by commission (ranking neutrality eval, section 1.5). Affiliate and non-affiliate options appear together in the same lists.
- Pasted links are never rewritten. Airbnb has no program and gets plain links.
- Partner guides and sponsored placements (later) are labeled "Partner guide" and "Sponsored".
- Terms of each affiliate program are kept in `docs/partners/` and reviewed twice a year. Tracking uses a random per-click sub-id with no user data.
- Reviews and testimonials in marketing are real and uncompensated, or labeled.

### 3.7 Children

- Age gate 13 or older at sign-up, 16 or older for EU and UK locales (age is self-declared, not stored as a birthdate beyond the declaration timestamp). Hermi is not in the Kids category and is not directed at children.
- Children on a trip (travelers) are entered by an adult as a first name and a color: no birthdate, no photo, no email, no account.
- If a report or an account shows the user is under the age, the account is deleted and no data is kept.
- Check state age assurance laws (Texas, Utah and others) for new duties before each submission.
- The age rating questionnaire is answered honestly; expect 4+ or 9+, and up to 12+ because of shared content and AI text.

### 3.8 Seller of travel and concierge

The concierge lane ("Have a human book this") is fulfilled by an advisor under a host travel agency. Several US states (California, Florida, Hawaii, Washington, Iowa) regulate sellers of travel.

- The concierge feature is behind the flag `concierge_requests`, enabled per region only after counsel confirms the host agency's registration covers that region. The state list is in `concierge_regions` config.
- Every request shows who fulfills it: "Booked by [host agency name], seller of travel registration [number]" with the state registrations that apply, in the request screen, the confirmation email and the terms.
- Hermi does not hold customer funds for bookings. Payment to suppliers goes through the host agency or the supplier directly. Hermi's own fee (if any) and commission arrangement are disclosed in plain words before the user submits.
- Consent is explicit and separate from app terms: the user agrees to share trip details and traveler names needed for booking with the advisor. Passport numbers are never collected in the app.
- Advisors sign an agreement covering data handling, conduct and commission; they see only the requests assigned to them. Access is audited.
- Insurance, visas and legal advice are outside the concierge scope.
- Cancellations and disputes follow the host agency's terms, linked from the request.

### 3.9 Insurance referral rules

- Hermi shows links to licensed insurance partners only. It does not sell, solicit, negotiate or advise on insurance, and does not collect payment for it. Affiliate compensation for insurance is a referral with no compensation tied to the sale of a policy where state law requires that; counsel confirms the program terms before any insurance link goes live.
- Copy is supplied or approved by the insurer or network. No coverage claims, no comparisons of coverage, no "you need this" language. Every card says "Partner offer. Check the policy terms" plus the commission disclosure.
- The AI never gives insurance, visa or legal advice; it links to official sources (README rule 5). The AI eval "safety scope" enforces this.
- The "Before you go" checklist lists insurance as one item among many, unranked, and at least half of the checklist items carry no monetization.
- Insurance cards are hidden where the partner is not licensed (region flag).

### 3.10 Other obligations

| Item | Requirement |
|---|---|
| Email | Transactional mail separate from marketing; marketing is opt-in with one-click unsubscribe (`UNSUBSCRIBE_SECRET` signed link) and a physical address in the footer (CAN-SPAM) |
| Push | Permission requested in context after the first invite or alert, with a reason screen; no marketing pushes without opt-in |
| Subscriptions | Price, period, trial length and renewal terms visible on the paywall; Terms and Privacy links; Restore button; easy path to cancel through Apple (guideline 3.1.2) |
| Auto-renew laws | State rules on cancellation and reminders are handled by Apple for in-app subscriptions; Stripe-billed advisor seats get a renewal reminder email and one-click cancel |
| Accessibility | Accessibility statement, VoiceOver pass, Dynamic Type, reduced motion, AA contrast (including `--tp-edge` and `--tp-warning-ink`); accessibility nutrition labels in App Store Connect if required at submission |
| Sales tax and VAT | Apple is merchant of record for in-app purchases. Stripe Tax for advisor seats and print orders |
| Maps and data attributions | OpenStreetMap, Wikimedia and provider attributions in a licenses screen |
| Terms of providers | Never fetch Airbnb, Vrbo or Booking.com pages; no scrapers; review SerpApi and Geoapify terms before scaling; cache only within each provider's terms |

## 4. Analytics event catalogue

Tool: PostHog (first party, no ad SDKs). Rules:

- Events have no PII: no email, name, free text, trip titles, place names, addresses or notes. Identify with the opaque `users.id` UUID only. Session replay is off (or fully masked).
- Properties use enums and buckets, not raw values: destination is a country code or region, dates are buckets (days until departure), money is a bucket or tier.
- Event names are `snake_case`, past tense, defined once in `packages/shared/src/events.ts`. The server rejects unknown names and unknown properties in `analytics.capture`. Client events go through the same typed helper.
- Opt-out respected (Settings, Privacy) and Global Privacy Control honored. Events are dropped, not queued, when opted out.
- Retention in PostHog 90 days for events, 13 months for aggregated dashboards.

Common properties on every event (not repeated below): `app_version`, `platform` (`ios`, `web`), `tier` (`free`, `plus`, `family`, `pro`), `is_guest` (bool), `locale`, `env` and a random per-launch `session_id`. Screens in [05-ui-ux-spec.md](05-ui-ux-spec.md) list their events by the names in this table; an event a screen needs that is missing here is added here first.

| Event | Properties | When fired |
|---|---|---|
| `app_opened` | `source` (`icon`, `push`, `universal_link`) | App foreground start, at most once per 30 minutes |
| `signup_started` | `method` (`apple`, `google`, `email_code`) | User taps a sign-in method |
| `signup_completed` | `method`, `from_invite` (bool), `was_guest` (bool) | First `users` row created |
| `sign_in_completed` | `method` | Existing user signs in |
| `guest_trip_created` | none | Guest creates a local trip |
| `guest_claimed` | `trip_count_bucket` | Guest data claimed into an account |
| `onboarding_step_completed` | `step` (`profile`, `home_airport`, `first_trip`) | Each onboarding step |
| `trip_created` | `source` (`blank`, `template`, `concierge`), `destination_count`, `has_dates` | Trip saved |
| `first_itinerary_item_added` | `minutes_since_signup_bucket` | First item in the user's first trip (activation) |
| `itinerary_item_added` | `category` (`itinerary_items.category`: `sights`, `museum`, `food`, `nature`, `nightlife`, `shopping`, `travel`, `other`), `source` (`itinerary_items.source`: `manual`, `place_search`, `ai_draft`, `agent`, `import`, `guide`) | Item created |
| `flight_route_added` | `route_type` (`one_way`, `round_trip`), `days_to_departure_bucket` | Route created |
| `fare_alert_created` | `kind` (`cached`, `live`) | Alert created |
| `price_alert_delivered` | `channel` (`push`, `email`, `in_app`) | Alert notification sent |
| `price_alert_opened` | `channel` | User opens from an alert |
| `lodging_option_added` | `source` (`lodging_options.added_via`: `paste`, `bookmarklet`, `partner_search`, `agent`, `manual`) | Option created |
| `lodging_voted` | `voted` (bool: a heart added or removed) | Heart toggled |
| `poll_created` | `option_count`, `subject` (`custom`, `dates`, `lodging`, `activity`, `destination`) | Poll created |
| `present_mode_started` | `slide_count_bucket` | Presentation opened |
| `invite_sent` | `channel` (`link`, `email`, `sms_share`), `role` | Invite created |
| `invite_opened` | `platform_before_install` (`installed`, `not_installed`) | Invite link opened |
| `invite_accepted` | `role`, `minutes_to_accept_bucket` | Invite redeemed |
| `share_link_created` | `redaction_level` | Share link created |
| `share_link_viewed` | `surface` (`web`) | Public share page loaded (server side) |
| `ai_consent_shown` | none | Consent screen displayed |
| `ai_consent_granted` | `version` | Consent accepted |
| `ai_consent_declined` | none | "Not now" |
| `ai_action_started` | `action` (`explain`, `live_search`, `draft_day`, `draft_trip`, `research`, `agent_run`), `feature` (`explain`, `packing_list`, `booking_import`, `fare_hunt`, `deep_research`, and so on, from 06 section 1), `credits`, `from_cache` (bool), `taster` (bool) | Credits reserved (or the taster grant spent) |
| `ai_action_completed` | `action`, `feature`, `outcome` (`ok`, `partial`, `failed`, `refunded`; a run the user stopped is `partial`), `taster` (bool), `duration_seconds_bucket` | Run settled |
| `ai_feedback_given` | `action`, `rating` (`up`, `down`), `reason` (enum) | Thumbs tapped |
| `fare_marked_wrong` | none | "Price was different" tapped |
| `credits_low_shown` | `balance_bucket` | Low credit banner shown |
| `paywall_viewed` | `placement` (a trigger id from [05-ui-ux-spec.md](05-ui-ux-spec.md) section 6.27, such as `invite`, `track_live`, `group_tools`, `group_pass`, `third_trip`, or `settings`, `onboarding`), `offer_shown` (list of product codes) | Paywall displayed |
| `paywall_dismissed` | `placement` | Closed without purchase |
| `purchase_started` | `product` (`plus`, `family`, `pro`, `trip_pass`, `group_trip_pass`, `credits_50`, `credits_150`, `credits_400`), `period` | StoreKit sheet shown |
| `purchase_completed` | `product`, `period`, `is_trial` (bool) | Server confirms entitlement |
| `purchase_failed` | `product`, `reason` (`cancelled`, `pending`, `error`) | Purchase ends without success |
| `restore_tapped` | `result` (`restored`, `nothing`) | Restore purchases tapped |
| `trip_pass_applied` | `product` (`trip_pass`, `group_trip_pass`), `is_upgrade` (bool) | Pass bound to a trip |
| `subscription_canceled` | `product`, `days_active_bucket` | From RevenueCat webhook |
| `subscription_expired` | `product`, `reason` (`voluntary`, `billing`, `refund`) | From webhook |
| `partner_card_viewed` | `program` (code), `placement` (`flight`, `stay`, `activity`, `esim`, `car`, `insurance`, `checklist`), `sponsored` (bool) | Card enters viewport (once per screen visit) |
| `partner_link_tapped` | `program`, `placement` | `/go` click created |
| `affiliate_conversion_imported` | `program`, `status` (`pending`, `approved`, `reversed`) | Server import (no amounts in analytics) |
| `concierge_requested` | `kind` (`stay`, `cruise`, `complex_trip`, `other`), `region` | Request submitted |
| `concierge_status_changed` | `kind`, `status` (`concierge_status`) | Server status change, including a cancel by the requester |
| `expense_added` | `split_type` (`expenses.split_method`: `equal`, `exact`, `percent`, `shares`), `member_count_bucket` | Expense created |
| `settlement_started` | `method` (`settlements.method`: `manual`, `cash`, `bank_transfer`, `stripe`) | Settle-up begun or a payment request created |
| `push_prompt_shown` | `context` (`after_invite`, `after_alert`) | Reason screen shown |
| `push_permission_result` | `result` (`granted`, `denied`) | System prompt result |
| `offline_trip_saved` | `trigger` (`manual`, `auto_departure`) | Trip cached for offline |
| `export_requested` | none | Export started |
| `export_ready` | none | Export file ready (server side) |
| `account_deletion_requested` | `had_subscription` (bool) | Deletion confirmed |
| `account_deletion_cancelled` | none | Restored in grace window |
| `review_prompt_shown` | none | Native review prompt displayed |
| `error_shown` | `code` (stable error code), `screen` | User sees an error state |
| `kill_switch_banner_shown` | `switch` | User sees a paused feature message |
| `screen_viewed` | `screen` (the route name from 05 section 5.4) | Any screen appears; not repeated in the per-screen lists in 05 |
| `onboarding_started` | none | Splash shown to a signed-out visitor |
| `onboarding_choice_made` | `choice` (`plan`, `sign_in`, `invite`) | A splash button tapped |
| `onboarding_step_skipped` | `step` (`profile`, `home_airport`, `first_trip`) | "Skip for now" on a step |
| `sign_in_failed` | `method`, `reason` (`wrong_code`, `expired_code`, `rate_limited`, `cancelled`, `error`) | Sign-in ends without success |
| `save_prompt_shown` | `trigger` (`invite`, `sync`, `ai`, `export`, `alert`, `purchase`, `banner`) | Guest "Save your trip" sheet shown |
| `save_prompt_dismissed` | `trigger` | Guest taps "Not now" |
| `trips_home_viewed` | `trip_count_bucket`, `active_count` | Trips home opened |
| `trip_opened` | `source` (`home`, `link`, `push`, `switcher`) | A trip workspace opened |
| `trip_archived` | none | Trip archived |
| `trip_create_started` | none | Create-trip flow opened |
| `trip_overview_viewed` | none | Overview tab opened |
| `next_step_tapped` | `step` (`dates`, `flight`, `stay`, `first_day`) | A Next steps row tapped |
| `section_opened` | `section` (`flights`, `stays`, `plan`, `group`, `notes`, `checklist`, `ai_activity`) | A summary card or section tab opened |
| `invite_sheet_opened` | none | Invite sheet opened |
| `traveler_linked` | none | "Which traveler are you?" answered |
| `fare_chip_tapped` | `source` (`live`, `cached`, `agent`, `google`) | Fare chip tapped |
| `fare_detail_viewed` | `age_hours_bucket` | Fare detail opened |
| `fare_marked_booked` | none | "Mark as booked" on a chosen fare |
| `flight_chosen` | none | A fare is chosen for a route (server side) |
| `lodging_compare_opened` | `count` | Compare opened with 2 to 4 stays |
| `lodging_booked` | none | A stay marked Booked |
| `plan_viewed` | `mode` (`days`, `calendar`, `map`) | Plan section opened |
| `itinerary_item_moved` | `method` (`drag`, `move_to_sheet`, `actions`) | Item moved to another day or position |
| `itinerary_item_deleted` | none | Item deleted |
| `edit_conflict_shown` | `resolution` (`keep_mine`, `use_theirs`, `dismissed`) | 409 `version_conflict` sheet resolved |
| `place_searched` | `result_count_bucket` | Place search run |
| `map_opened` | none | Plan map opened |
| `map_pin_selected` | none | Pin tapped |
| `maps_handoff` | `app` (`apple`, `google`) | "Open in ..." maps tapped |
| `ai_sheet_opened` | none | Ask sheet opened |
| `agent_finding_saved` | `kind` (`fare`, `note`) | "Save to trip" on a run finding |
| `taster_offered` | none | Taster card shown |
| `taster_upsell_shown` | none | Post-taster card shown |
| `note_added` | `scope` (`trip`, `day`, `item`, `stay`), `private` (bool) | Note created |
| `evidence_opened` | none | Evidence row or source opened |
| `finding_saved_to_notes` | none | A finding copied to notes |
| `present_mode_printed` | none | Print or PDF from present mode |
| `checklist_item_shown` | `kind` (`checklist_items.kind`) | Checklist row seen, once per item per session |
| `checklist_item_updated` | `kind`, `status` (`done`, `skipped`, `not_needed`, `todo`) | Row ticked, dismissed or reset |
| `poll_voted` | `selection` (`single`, `multiple`) | Vote cast |
| `settle_up_viewed` | none | Settle up list opened |
| `concierge_card_shown` | `surface` (`stays`, `overview`) | Entry card in view |
| `discover_viewed` | none | Discover opened |
| `destination_opened` | `country_code` | A destination page opened |
| `trip_started_from_discover` | none | "Start a trip here" tapped |
| `activity_viewed` | `unread_bucket` | Activity opened |
| `activity_item_opened` | `kind` (`alert`, `change`, `poll`, `run`, `invite`, `concierge`, `expense`) | Activity row opened |
| `account_viewed` | none | Account opened |
| `setting_changed` | `key` (the setting name, never its value) | A setting toggled |
| `booking_links_hidden` | `value` (bool) | "Hide booking links" switched |
| `manage_subscription_tapped` | none | "Manage subscription" tapped |
| `notification_opened` | `type` (`price_alert`, `trip_change`, `reminder`, `digest`, `run_done`, `concierge`) | App opened from a push |
| `subscription_started` | `product`, `period`, `is_trial` (bool) | From the RevenueCat webhook |
| `subscription_renewed` | `product`, `period` | From the webhook |
| `trial_converted` | `product` | First paid renewal after a trial |
| `subscription_changed` | `direction` (`upgrade`, `downgrade`), `from`, `to` (product codes) | Upgrade applied or downgrade scheduled |
| `trip_pass_moved` | none | A pass moved to another trip |
| `trip_pass_expired` | `product` | Pass reaches `expires_at` |
| `credits_expired` | `credits_bucket` | Grant expiry sweep (server side, no user id in the event) |
| `payment_collection_created` | `member_count_bucket` | Phase 4: Stripe collection opened |
| `payment_collection_paid` | `share_count_bucket` | Phase 4: every share paid |

Screen names in 05 map to the catalogue as follows, so a screen never invents a name: the Subscription and credits screen is `screen_viewed {screen: subscription}`; a credit pack tap is `purchase_started` with a `credits_*` product; a live check or an explain is `ai_action_started` with its `action`; "Book on ..." on a fare, a stay or a checklist row is `partner_link_tapped` with the matching `placement`; sharing from present mode is `share_link_created`.

Funnels tracked from these events: activation (`signup_completed` to `first_itinerary_item_added` within 24 hours), invite loop (`invite_sent` to `invite_accepted` to second `trip_created`), paywall (`paywall_viewed` to `purchase_started` to `purchase_completed`), AI (`ai_consent_granted` to `ai_action_completed` with `outcome=ok`), affiliate (`partner_card_viewed` to `partner_link_tapped`).

## 5. Observability

### 5.1 Logs

JSON to stdout, one line per event, shipped to Better Stack and kept 14 days hot (30 for security events). Fields: `ts`, `level`, `service`, `env`, `release`, `request_id`, `job_id`, `run_id`, `user_id` (opaque), `route`, `status`, `latency_ms`. `request_id` flows into jobs. No prompts, itineraries, notes, emails or tokens at INFO; sizes and hashes instead. Security events (`auth_failed`, `role_changed`, `webhook_rejected`, `admin_action`, `rate_limited`) use a dedicated `event` field.

### 5.2 Metrics

| Area | Metrics |
|---|---|
| API | Request rate, p50, p95, p99 latency by route template, 5xx rate, 4xx by code, auth failures, rate limit hits |
| Queue | Depth per lane, oldest job age, jobs per minute, retry rate, dead letters, worker heartbeats, reaper requeues |
| Scheduler | Ticks per minute, due routines, enqueued, skipped by reason, lag (now minus oldest `next_run_at`) |
| Database | CPU, connections versus limit, longest transaction, lock waits, replication lag if any, disk growth, slow queries |
| Providers | Success rate, latency, 429 rate and remaining quota per provider, cache hit rate |
| AI | Spend per day, model, action and tier; cost per active user; p95 cost per action; refusal rate; cache hit rate; batch share; retries |
| Billing | Webhook lag (received to processed), unprocessed events, entitlement mismatches found by reconcile |
| Notifications | Push delivered rate, 410 rate, email bounce and complaint rate |
| Business | Signups, activation, invites, paywall conversion, MAU, MRR, credits sold, affiliate clicks and conversions, gross margin per tier |
| Client | Crash-free sessions (Sentry), cold start time, JS errors, API errors seen by the app |

Platform metrics plus Sentry until 10k MAU, then Prometheus style metrics into Grafana Cloud. The AI and business dashboards are built before launch (Metabase on a read replica through a SELECT-only login that is not one of the application roles).

### 5.3 Alerts

Severity: `page` (phone, any hour), `notify` (chat, business hours), `digest` (weekly). The founder is on call, so pages are kept to outage, data loss risk, security and spend runaway.

| Alert | Threshold | Severity |
|---|---|---|
| API availability (ready probe from 2 regions) | Fails 3 checks in a row | page |
| API 5xx rate | Over 2 percent for 5 minutes | page |
| API p95 latency | Over 1 second for 10 minutes | notify |
| Queue oldest job age | Over 10 minutes (any lane) | page; over 5 minutes notify |
| Queue depth | Over 1,000 waiting in `api` or over 200 in `ai` for 10 minutes | notify |
| Dead letters | More than 5 in an hour in one lane | notify |
| Scheduler heartbeat | No ping for 3 minutes | page |
| Scheduler lag | Oldest due routine over 15 minutes late | notify |
| Database CPU | Over 70 percent for 15 minutes | notify; over 90 percent page |
| Database connections | Over 80 percent of limit | notify |
| Database disk | Over 80 percent | notify; over 90 percent page |
| Backup age | Last successful weekly dump older than 8 days, or PITR unhealthy | page |
| Webhook backlog | Oldest unprocessed `webhook_events` over 10 minutes | page |
| Webhook signature failures | Over 30 an hour | notify |
| Entitlement mismatch | Reconcile finds more than 5 users in an hour | notify |
| Provider failure | Success rate under 80 percent for 10 minutes | notify; all fare providers failing page |
| Provider quota | Under 20 percent of monthly quota left | notify |
| Affiliate link errors | `/go` non-302 rate over 2 percent for 15 minutes | notify |
| Push 410 or failure rate | Over 20 percent for 30 minutes | notify |
| Email bounce rate | Over 5 percent in a day | notify |
| Crash-free sessions | Under 99.5 percent on the latest build | notify; under 98 percent page |
| Sentry new issue in production | Any new issue | notify; spike over 50 events in 10 minutes page |
| Security: tenant test on staging | Any failure | page |
| Security: admin off-hours or bulk action | Any | notify |

### 5.4 AI spend alerts

The most likely way to lose money is a runaway agent or a loop. Alerts run from `ai_spend_guard` every 5 minutes.

| Alert | Threshold | Severity | Automatic action |
|---|---|---|---|
| Global daily spend (absolute) | Over `AI_GLOBAL_DAILY_CAP_USD` (launch value $150) | page | Circuit breaker pauses the `ai` and `batch` lanes for non-urgent work and notifies |
| Global daily spend (relative) | Over 1.5 times the trailing 7 day average after noon UTC | page | None; founder decides |
| Hourly spend | Over 25 percent of the daily cap in one hour | page | Pause agent runs (`ai.agent_runs`) |
| Single account | Over 3 times its daily ceiling (the ledger should prevent this, so it means a bug) | page | Suspend AI for that account |
| Single run | Passes its turn, search, fetch or dollar cap | notify | Run stopped by code; alert on any overrun |
| Free tier spend | Over 30 percent of total daily spend | notify | Consider `ai.free_tier` switch |
| Cache hit rate | Down 20 points from the 7 day average | notify | None |
| Anthropic 429 or overloaded rate | Over 5 percent for 10 minutes | notify | Back off the `ai` lane |
| Refusal rate | Over 3 percent for a feature in a day | notify | Review prompt version |
| Cost per agent run | 7 day p95 over $0.80 | notify | Review before any Pro launch (gate is $0.60 or less over 200 runs) |
| Gross margin per tier | Below 70 percent on a rolling 30 days for paid tiers | digest | Review |
| Anthropic workspace spend | 50, 80 and 100 percent of the monthly limit | notify, page at 80 | Limit is the final backstop |

Monthly provider-spend ceilings per tier (README) are enforced by the ledger; these alerts catch drift and bugs.

### 5.5 Uptime and status

Better Stack probes `/health/ready` from two regions and runs a synthetic check every 5 minutes that signs in with a test account and loads a trip. A public status page (`status.hermi.world`) lists API, AI, sign-in, purchases and push. Service targets: API availability 99.9 percent, price alert delivery within 30 minutes of a scheduled check, p95 queue wait under 5 minutes.

## 6. App Store submission

### 6.1 Checklist

Verify every item on the day of submission; Apple policy moves.

**Account and setup**
- [ ] Apple Developer Program enrolled (organization account with D-U-N-S if the company exists) and Paid Applications Agreement, bank and tax forms complete.
- [ ] Bundle id `world.hermi.ios` with Push Notifications, Associated Domains, Sign in with Apple, In-App Purchase, App Attest.
- [ ] Small Business Program enrolled.
- [ ] Support URL, marketing URL and privacy policy URL live on our domain.

**Build**
- [ ] Bundled web build; no `server.url`; release build, not debug.
- [ ] Privacy manifest (`PrivacyInfo.xcprivacy`) present, SDK manifests checked.
- [ ] Purpose strings in `Info.plist` for every permission requested (notifications, calendar write-only, location when in use if "near me" ships).
- [ ] No ATT prompt and no `NSUserTrackingUsageDescription`.
- [ ] Universal links work (`apple-app-site-association` served as JSON with no redirect).
- [ ] Crash-free sessions at least 99.5 percent over 100 or more TestFlight sessions.
- [ ] App works on the lowest supported iOS and on iPhone SE size.

**Features Apple checks**
- [ ] Guideline 4.2: offline trip viewing, push, native share sheet, haptics, Apple Maps handoff, bottom tab navigation.
- [ ] Guideline 4.8: Sign in with Apple offered alongside Google.
- [ ] Guideline 5.1.1(v): in-app account deletion works and revokes the Apple token.
- [ ] Guideline 5.1.2(i): AI consent screen names the provider and what is sent.
- [ ] Guideline 3.1.1 and 3.1.2: all digital plans and credits (Plus, Family, Trip Pass, Group Trip Pass, credit packs; Pro only when its flag launches) use In-App Purchase; paywall shows price, period, trial terms, Terms and Privacy links and Restore; subscription info localized; review screenshots per product.
- [ ] Guideline 3.1.3(e): partner links lead to physical travel services used outside the app, labeled as commission links. No web checkout for digital goods.
- [ ] Guideline 1.2: report and block on shared content and AI answers, contact info, moderation queue.
- [ ] Guideline 5.6 and 5.1.1: no dark patterns; data collection matches the privacy label.
- [ ] Age rating questionnaire answered; 13+ gate in place.

**Store listing**
- [ ] Name "Hermi: Group Trip Planner" (reserved in WF-001; the bare name is taken), subtitle, promotional text, description, keywords, category Travel.
- [ ] Screenshots 6.9 inch (1320 by 2868), up to 10: trip overview, itinerary on map, price alert, AI plan, offline, shared trip, present mode. Icon 1024 by 1024 without alpha.
- [ ] Localized metadata for en-US and one or two more storefronts.
- [ ] App Privacy labels match section 3.4.
- [ ] Release set to manual; phased release for updates.

### 6.2 Review notes (paste into App Store Connect)

```
Hermi helps people plan trips together: flights, places to stay, a day-by-day itinerary,
and a full-screen presentation of the plan.

Demo account (no Sign in with Apple needed):
  Email: review@hermi.world   Code: use the "Reviewer sign in" button on the sign-in screen
  The account is on the Plus tier and has a pre-filled trip ("Lisbon in May"), two members,
  and 40 credits. A second account, review-free@hermi.world, is on the Free tier to see the
  paywall. Purchases work in the sandbox.

Where things are:
  - Account deletion: Settings > Account > Delete account.
  - Restore purchases: paywall and Settings > Purchases.
  - AI features: tap "Ask" on any trip. A consent screen names Anthropic and what is sent.
    Users can turn AI off in Settings > Privacy. AI answers are labeled and show sources.
  - Report and block: the "..." menu on shared trip content and on AI answers.

Purchases:
  Plus, Family, Trip Pass, Group Trip Pass and credit packs use In-App Purchase.

Partner links:
  Buttons on hotels, tours, flights, cars and eSIMs open partner booking pages in an in-app
  Safari view. These are physical travel services used outside the app (Guideline 3.1.3(e)).
  Each button is labeled "We earn a commission if you book here." The app does not track
  users across other companies' apps or sites and shows no ATT prompt. Clicks are logged on
  our own server only.

Push notifications are used for price alerts and trip reminders, requested after the first
invite or alert.

The backend is live and rate limits are relaxed for the reviewer accounts.
Contact: +1 (xxx) xxx-xxxx, review@hermi.world
```

A "Reviewer sign in" path is a server-side allowlisted account that signs in with a fixed code; it exists only for these two emails and is disabled by a flag after approval. Verify the demo accounts against production the day before submission.

### 6.3 Common rejection causes and pre-checks

| Cause | Pre-check |
|---|---|
| Broken login for the reviewer | Test both accounts on a clean device on the production backend |
| Paywall missing Restore or terms links | Screenshot each paywall state |
| Missing deletion | Delete a throwaway account end to end |
| Privacy label mismatch | Compare the label to section 3.4 and the SDK list |
| 4.2 web wrapper feel | Airplane mode demo video, native features listed in the notes |
| External purchase language | Search the UI and listing for "web", "cheaper on our site", "lifetime" |
| AI disclosure | Consent screen screenshot in the notes |
| Sign in with Apple relay emails failing | Send a test email to a relay address |

Budget two review cycles of 1 to 4 days. Keep the backend and demo accounts up during review.

## 7. Launch checklist

Gates match the README roadmap. Each item has an owner (the founder unless noted) and a link or artifact as evidence.

### 7.1 Before the hosted web beta (Phase 1 gate)

- [ ] Tenant-isolation test green in CI and on staging.
- [ ] RLS policies tested (direct SQL pass and no-variable pass).
- [ ] Credit reserve and settle tests green; ledger reconciliation query returns zero drift.
- [ ] Webhook contract tests green; replay test run.
- [ ] Restore drill passed once (PITR to a scratch database, smoke test against it).
- [ ] AI spend alerts fired in a staging drill; every kill switch exercised.
- [ ] Anthropic workspace limits set per environment.
- [ ] Load test at 1,000 users passed (section 1.8 targets, scaled).
- [ ] Contrast test green for every token pair in 05 section 2.3, including `--tp-edge` and `--tp-warning-ink`; axe clean on the web beta screens in light and dark.
- [ ] Privacy policy, terms and cookie notice published; AI consent live; export and deletion working.
- [ ] Sentry, uptime, log shipping and the status page live.
- [ ] 4-week retention measured and recorded.

### 7.2 Before TestFlight external testing (Phase 2 gate)

- [ ] Sandbox purchase matrix passed (section 1.7).
- [ ] Push works end to end (sandbox then production APNs).
- [ ] Universal links and the invite flow from Messages verified on device.
- [ ] Offline trip verified in airplane mode on a real device.
- [ ] Account deletion revokes the Apple token (verified in Apple's settings).
- [ ] App Attest flow verified on a real device; fallback verified.
- [ ] Accessibility pass with VoiceOver and Dynamic Type, and a check that `--tp-edge` borders and `--tp-warning-ink` text hold their contrast in the native shell in light, dark and Increase Contrast.

### 7.3 Before public launch (Phase 3 gate)

- [ ] Penetration test complete; no open high or critical findings.
- [ ] Load test at 10x expected launch traffic passed; Anthropic rate limits raised and tested at 3x peak.
- [ ] All runbooks in section 8 written, reviewed and each drilled once in staging (spend spike, provider outage, webhook backlog, bad deploy rollback; breach tabletop).
- [ ] On-call routing tested (a real page reaches the phone at night).
- [ ] Backups: PITR healthy, weekly off-provider dump verified by restore.
- [ ] Dependency audit clean; secrets rotated after beta; secret scan of history clean.
- [ ] Affiliate: disclosure text present on every partner placement (automated UI check), `/go` tests green, program terms filed, conversion import working for Travelpayouts, Viator and Stay22.
- [ ] Seller-of-travel status confirmed for each region where concierge is enabled (otherwise flag stays off).
- [ ] Provider terms recheck: SerpApi decision, Geoapify, Travelpayouts; Airbnb, Vrbo and Booking.com remain link only.
- [ ] Support live: inbox, macros, FAQ, refund and cancellation guidance, abuse inbox.
- [ ] Data processing agreements on file for every processor.
- [ ] App Review passed; release set to manual.
- [ ] Status page and announcement drafted; launch day owner and rollback plan named.

### 7.4 Launch day and first 72 hours

- [ ] Release manually; watch crash-free rate, API 5xx, queue age, AI spend, webhook lag, signups, purchases.
- [ ] Check a real purchase, a real invite, a real AI action, a real `/go` click in production with the team's own accounts.
- [ ] Reply to every review and support message within a day.
- [ ] No P0 open after 72 hours, crash-free at least 99.5 percent, API errors under 1 percent. Otherwise hold the marketing push.
- [ ] Hotfix path rehearsed: a fix reaches staging in under 30 minutes and production in under 2 hours (backend) or submitted to App Review with expedite (iOS).

### 7.5 After launch

- Weekly: metrics review, AI and provider bill review, dead letter and support sweep.
- Monthly: dependency audit, cost per user, gross margin per tier, affiliate conversion reconciliation, flag cleanup.
- Quarterly: restore drill (including deletions staying deleted), key rotation, kill switch drill, load test, access review of admins, privacy label recheck.
- Twice a year: affiliate and provider terms review. Yearly: penetration test, DPIA review, Apple renewal.

## 8. Runbooks

Each runbook also lives in `docs/runbooks/` as its own file with the same headings. Format: detect, contain, fix, recover, follow up. Every incident gets a short written review within 5 days (what happened, timeline, cause, what changes). Status page updates go out within 15 minutes of a confirmed user-facing incident.

### 8.1 AI spend spike

**Detect.** `ai_spend_guard` page (global daily over cap, hourly over 25 percent of cap, or a single account over 3x its ceiling), or an Anthropic workspace 80 percent alert.

**Contain (first 10 minutes).**
1. Open the admin AI spend dashboard: spend by hour, feature, tier, account and model.
2. If a single feature or agent runs is the source, turn on `ai.agent_runs` (or the matching switch). If unclear, turn on `ai.all`. The app shows "AI is paused, your plans are safe".
3. If one account is the source, suspend its AI from the admin console (reason logged) and check its `runs` for loops.
4. If the source is free accounts (signup farming), turn on `ai.free_tier` and tighten signup limits (`signups` switch if needed).

**Find the cause.**
- Runs over caps (turn, search, fetch, dollar): a bug in the loop or the tool executor. Check `run_events` for repeating tool calls.
- Cache hit rate collapse: a prompt version bump or cache key bug sending everything to live search.
- Retries: a provider error causing repeated full-price retries (check retry rate).
- Price table wrong: real spend does not match `ai_usage` cost; compare with the Anthropic usage export.
- Abuse: many new accounts from one device, IP range or email domain.

**Fix and recover.** Ship the fix or roll back the prompt or model config, verify on staging with the fake client and a small live budget, turn switches off one at a time (agent runs last), and watch the next hour. Refund credits for runs that failed because of our bug (admin bulk credit grant with a reason). If the workspace limit was hit, raise it only after the cause is known.

**Follow up.** Add the failing case to the evals, add or tighten an alert, and review whether any per-run cap should be lower. Record the dollar impact.

### 8.2 Provider outage

Covers Anthropic, SerpApi, Travelpayouts, Geoapify, Supabase Auth, RevenueCat, Stripe, APNs, Resend, Cloudflare and Render.

**Detect.** Provider success rate alert, a status page from the provider, or user reports.

**Contain.**
1. Confirm on the provider's status page and with a direct test call from a staging shell.
2. Turn on the matching kill switch (`provider.<name>`, `ai.all`, `push.all`, `email.all`) only if retries are causing harm (queue growth, spend, user-facing errors). Otherwise let retries with backoff work.
3. Post a status page update.

**Per provider.**

| Provider | User impact and action |
|---|---|
| Anthropic | AI paused or queued; credits stay reserved up to 30 minutes then release; cached research still served; consider `ai_force_haiku` if only Sonnet is degraded |
| SerpApi | Flag `serpapi_live_fares` off; fares fall back to cached Travelpayouts with an age label; no credit charge for empty results |
| Travelpayouts | Show last observations; alerts pause; affiliate links still work |
| Geoapify | Serve `places_cache`; manual place entry still works |
| Supabase Auth | New sign-ins blocked, existing sessions work (JWKS cached 1 hour, extend the cache window to 24 hours by config if the outage is long); do not sign anyone out; status banner on the sign-in screen |
| RevenueCat | Purchases may delay unlocking; use `POST /purchases/sync` and the reconcile job; do not revoke access on missing events |
| Stripe | Group payments and advisor billing show "temporarily unavailable" |
| APNs or Resend | Retry; in-app feed shows alerts; invites can be shared as links; switch to the standby email provider after 30 minutes |
| Cloudflare | DNS or WAF outage takes the site down; the iOS app keeps showing cached trips offline; follow the provider's guidance and update status |
| Render | If a region is down, restore the latest backup into a new Render account from `render.yaml` (target RTO 1 hour); point Cloudflare at it |

**Recover.** When the provider returns, turn switches off, let the queue drain (watch oldest job age), run `reconcile_entitlements` and confirm no duplicate pushes (idempotency keys). Post the all clear.

**Follow up.** Check that the fallback worked as designed, fix any path that showed a raw error, and review the retry and circuit breaker settings.

### 8.3 Webhook backlog

**Detect.** Alert: oldest unprocessed `webhook_events` over 10 minutes, or users reporting a purchase that did not unlock.

**Contain.**
1. Check the `api` lane: is `process_webhook_event` running? Look at queue depth, worker heartbeats and dead letters.
2. Check the database (locks, CPU). A long transaction often blocks entitlement updates.
3. Check that inbound receipt still works (new rows are arriving). If receipt fails, check Cloudflare rules and the signature secret (a recent rotation is a common cause).

**Fix.**
- Workers down: scale or restart the worker service. Jobs resume from the queue.
- One poison event failing repeatedly: read the error, fix the parser, or mark that event `skipped` with a reason in admin so the queue moves. Never delete the row.
- Bad secret: set the new value (webhook endpoints accept current and previous secrets), then replay events that returned 401 from the provider's dashboard (RevenueCat and Stripe can resend).
- Large backlog: add worker instances on the `api` lane; ordering is by event timestamp so replay is safe.

**Recover and verify.** Run `reconcile_entitlements` for affected users. Buyers who paid and did not get access: grant the entitlement manually from admin (audited) and let the reconcile confirm. Check credit ledger drift and grant duplicates (unique keys make duplicates impossible; confirm zero).

**Follow up.** Add an alert for the specific cause, add the failing payload to the contract fixtures.

### 8.4 Data breach

**Detect.** Sentry or log anomaly, tenant-test failure, unusual admin activity, a provider breach notice, a leaked key alert from secret scanning, a researcher report to `security@hermi.world`, or a user report of seeing another person's data.

**Contain (first hour).** The incident lead is the founder.
1. Open an incident log (private doc): time, who, what is known. Everything done is written down with timestamps.
2. Stop the bleed: rotate the exposed keys (use `docs/runbooks/key-rotation.md`), revoke sessions if tokens are exposed (Supabase sign-out for all, refresh token revocation), turn on `maintenance` (read-only) or disable the affected route or feature by kill switch, block attacker IPs at Cloudflare, suspend affected admin accounts.
3. Preserve evidence: snapshot the database, export logs for the window, do not delete anything. Keep `audit_log` intact.

**Assess (within 24 hours).**
- What data, which tables, how many users, what period. Use logs, `audit_log` and RLS tests to bound the scope.
- Was it personal data of EU or UK residents, children, payment data (we hold none, Apple and Stripe do), or special categories?
- Is it still possible? Reproduce and confirm the fix in staging.

**Fix.** Patch the cause, add a failing test first (tenant suite, security test), deploy through the normal pipeline with expedite, rotate anything that could have been seen.

**Notify.**
- Regulators: within 72 hours of becoming aware where GDPR or other law applies (breach notification template in `docs/runbooks/breach-notice.md`). State law notices in the US on their timelines.
- Users: without undue delay when there is a high risk to them. Plain language: what happened, what data, what we did, what they should do, contact. Send by email and in-app banner.
- Partners and processors: Apple (if a developer account or app is affected), RevenueCat, Stripe, affiliate networks if their data or tracking is involved. Insurers and counsel engaged early.
- Status page post.

**Recover and follow up.** Restore normal service after verification, run a full tenant-isolation and RLS test pass, consider a forced re-authentication, run a post-incident review in 5 days, update the threat model, and schedule a fresh penetration test of the affected area.

### 8.5 Bad deploy rollback

**Detect.** Post-deploy smoke test fails, `/health/ready` fails, 5xx over 2 percent, a spike of new Sentry issues, queue age climbing, or crash-free rate falling right after a release.

**Contain.** Stop further deploys. If it is only a new feature, turn off its feature flag first (seconds, no deploy).

**Backend rollback.**
1. The pipeline rolls back automatically if `/health/ready` fails for 2 minutes. If it did not (the app is up but wrong), trigger `deploy-prod.yml` with the previous image digest (shown in the last successful run). Rollback never rebuilds.
2. Check whether the release had a migration. Expand-and-contract means the previous code still works against the new schema, so rolling back code is safe. Do not run a down migration in production.
3. If a migration itself broke data or locked tables: stop the migration (kill the session), roll back the code, and if data was damaged restore to a point in time into a scratch database, verify, then copy back the affected rows (or cut over to the restored database if damage is wide). The pre-release snapshot is the fast path.
4. Drain and verify: queue depth back to normal, oldest job age under 5 minutes, webhook lag under 1 minute, smoke test green, error rate under 1 percent.
5. Jobs that ran with bad code: check `runs` and `credit_ledger` for wrong charges during the window; refund through admin in bulk with a reason.

**Web rollback.** Cloudflare Pages keeps previous deployments: promote the previous one (under 1 minute). Users with the old bundle still loaded keep working because the API stays backward compatible.

**iOS rollback.** A shipped app cannot be rolled back. Options: turn off the feature by flag, raise `min_app_version` only as a last resort, or submit a fixed build with an expedited review request. The backend stays compatible with the last 3 app versions so a bad build does not force a backend rollback.

**Follow up.** Write the review, add the missing test or smoke check that would have caught it, and review whether the release should have gone out behind a flag or at a percentage.
