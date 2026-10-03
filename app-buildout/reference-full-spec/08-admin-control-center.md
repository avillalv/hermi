# 08: Admin control center

Part of the [Hermi build specification](../README.md). The README's shared decisions and table names override anything here; table, column, enum, flag and kill switch names come from [03-database-schema.md](03-database-schema.md).

The admin control center is an internal web console at `admin.hermi.world`. It is how the founder (and later a few helpers) watch money, spend and health, answer support, and pull the brakes when something runs away. It is not a product feature and is never shown to customers. It ships in pieces across the roadmap (see section 11 and [09-build-roadmap.md](09-build-roadmap.md)); the first pieces (audit, users, kill switches, AI spend) must exist before the hosted web beta opens, because spend control is a launch safety requirement.

## 1. Principles

1. **Control, not convenience.** Every screen exists to answer a question the founder asks weekly or to stop a loss. Nothing is added "because we can".
2. **Every write is audited.** Each action writes one `audit_log` row with before and after values and a reason. No exceptions, including system actions such as auto-expiring a kill switch.
3. **Least privilege.** Five roles (the five `admin_role` values in 03), each with the smallest useful permission set. Destructive and money actions have limits and confirmations.
4. **No raw personal data in lists.** Emails and names are masked until an admin reveals them on a single record, and every reveal is audited.
5. **Fail closed.** If the admin API cannot read a kill switch, ledger or role, it refuses the action and says why.
6. **No second source of truth.** The console reads and writes the same tables as the product (`users`, `entitlements`, `credit_ledger`, `kill_switches`, and so on). It adds no parallel billing or spend data. The only new table names are the ones already in the README and 03; config values that have no table of their own use `feature_flags` rows whose key starts with `setting_` and whose `rules` holds the value (section 6.16).
7. **Same non-negotiables as the product.** The console never ranks anything by commission, never fetches Airbnb, Vrbo or Booking.com pages, and never sends user data to a third party.

## 2. Access and sign-in

### 2.1 Where it lives

- Hostname `admin.hermi.world`, served by the same web build as a separate React Router route group (`/admin/*` inside the SPA, mapped from the admin hostname). The group is code-split into its own chunk and is excluded from the Capacitor iOS bundle by a Vite build flag (`VITE_BUILD_TARGET=ios` removes it), so customers never download admin code.
- The admin API is under `/v1/admin` on the main API host. It is a separate FastAPI router with its own dependency chain (section 2.3), its own rate limits, and its own OpenAPI tag so `npm run gen:api` produces a separate client.
- `robots.txt` disallows everything and every admin response carries `X-Robots-Tag: noindex`.

### 2.2 Sign-in: SSO plus 2FA

Two independent layers, both required:

1. **Edge layer: Cloudflare Access** in front of `admin.hermi.world` and `/v1/admin/*`. It authenticates with the company identity provider (Google Workspace SSO) and enforces an IP allowlist or a managed device check (section 9). Cloudflare Access adds a signed `Cf-Access-Jwt-Assertion` header.
2. **App layer:** the API verifies that Cloudflare Access JWT (signature, audience, expiry), maps the verified email to a `users` row that has an `admin_users` row with `disabled_at` null, then requires a second factor (`admin_users.mfa_enrolled` must be true). WebAuthn passkeys (hardware key or platform authenticator) are preferred; TOTP is the fallback. SMS is never used.

Rules:

- An identity that passes Cloudflare Access but has no enabled `admin_users` row gets a 403 and an alert.
- Admin sessions are separate from customer sessions: a customer JWT is rejected on `/v1/admin`, and an admin session is rejected everywhere else. An admin has a `users` row plus an `admin_users` row (`user_id`; the first one is created with `hermi admin-grant`, 03 section 11.6) but signs in only through Cloudflare Access and 2FA, never through Supabase Auth or a customer session.
- Session: 8 hours absolute, 30 minutes idle. Cookie is `HttpOnly`, `Secure`, `SameSite=Strict`, scoped to the admin host.
- **Step-up 2FA** (a fresh WebAuthn or TOTP check inside the last 5 minutes) is required for: revealing PII, money actions, kill switch changes, settings changes, impersonation, deletion processing, role changes and CSV exports.
- Enrollment: the owner invites an email; the invitee signs in through SSO, registers two factors (one passkey and one recovery code set; `mfa_enrolled` becomes true), and is activated by the owner. Recovery codes are single use and stored hashed.
- Break-glass: one owner recovery path (printed recovery codes kept offline) for a lost passkey. Using it pages the owner and is logged.
- Offboarding: setting `admin_users.disabled_at` ends all sessions within 60 seconds (session check reads the row every request, cached 30 seconds). Remove from the Google Workspace group in the same step.

### 2.3 Request pipeline

```
Cloudflare Access (SSO, IP or device policy)
  -> API: verify Cf-Access JWT -> load admin_users row -> check status and role
  -> check session 2FA freshness for the action class
  -> check permission (role x action, section 3) and limits (amount, scope)
  -> require reason for writes (10 to 500 characters)
  -> run action in one transaction that also inserts the audit_log row
  -> return result with audit_id
```

The audit insert and the action commit together or not at all.

## 3. Roles and permission matrix

| Role | Who | Purpose |
|---|---|---|
| `owner` | Founder | Everything, including roles, settings and irreversible actions |
| `engineer` | Engineer or trusted helper | Runs the system: kill switches, flags, jobs, providers, replays (`admin_role` value `engineer`) |
| `support` | Support helper | Helps users: tickets, small credit grants, read-only impersonation |
| `finance` | Bookkeeper or accountant | Revenue, fees, cost and margin reports, commission records, refunds on web payments |
| `content` | Editor | Partner guides and moderation of AI and shared content |

Legend: `R` read, `r` read with fields removed or aggregated (noted), `W` write with a reason, `X` write with a reason, step-up 2FA and typed confirmation, `-` no access. Limits in the notes column are enforced by the API, not the UI.

| Capability | owner | engineer | support | finance | content | Notes and limits |
|---|---|---|---|---|---|---|
| Overview dashboard | R | R | r | r | - | Support sees no revenue or spend tiles; finance sees revenue and cost tiles only |
| User list and detail (masked) | R | R | R | r | - | Finance sees entitlement and payment tabs only |
| Reveal email or name on one user | W | W | W | - | - | Reason required; max 30 reveals an hour per admin |
| Grant credits | X | X | W | - | - | Support up to 50 credits a grant; engineer up to 200; owner up to 1,000; 400 credits a day per admin; comp credits expire in 90 days |
| Extend a trip pass | W | W | W | - | - | Support up to 14 days, engineer and owner up to 30 days; total extension per pass capped at 60 days |
| Comp a subscription | X | X | - | - | - | Engineer up to 90 days, owner up to 12 months; `plus` and `family` only |
| Force sign-out | W | W | W | - | - | Revokes all sessions and push tokens for the user |
| Start data export | W | W | W | - | - | Link goes to the user's email, never to the admin |
| Queue a deletion request | W | W | W | - | - | Starts the normal grace window |
| Process deletion now (skip grace) | X | - | - | - | - | Owner only, for legal or safety reasons |
| Impersonate read-only | W | W | W | - | - | Needs user consent (section 6.2); 15 minutes; one at a time per admin |
| Subscriptions and store transactions | R | R | r | R | - | Support sees status and dates, not amounts |
| Replay failed webhook | W | W | - | - | - | Max 100 events per action |
| Web refund (Stripe) | X | - | - | X | - | Finance up to $100 each, owner above; Apple refunds are never issued here |
| Credits and AI spend | R | R | r | R | - | Support sees one user at a time |
| Cancel an AI run | W | W | W | - | - | Support can cancel only runs of the user being helped |
| Kill switches: read | R | R | R | R | R | |
| Kill switches: set | X | X | - | - | - | Expiry mandatory (section 6.5) |
| Feature flags and experiments | W | W | - | - | - | Support, finance and content can read |
| Affiliate revenue reports | R | R | - | R | r | Content sees clicks and disclosure audit only |
| Affiliate programs, templates, link checker | W | W | - | - | - | Template edits need a second admin's approval (two-person) |
| Concierge queue | W | W | W | W | - | Support updates status; finance records commission; everyone else read |
| Group payments and disputes | R | R | R | W | - | Finance handles refunds and dispute evidence |
| Partner guides: edit and submit | W | - | - | - | W | |
| Partner guides: approve and publish | X | - | - | - | - | Author cannot approve their own guide |
| Support inbox | W | W | W | - | - | Reply needs the ticket's email, which is revealed inside the ticket and audited |
| Content moderation | W | W | W | - | W | Content role: AI content reports only |
| Provider and system health | R | R | - | r | - | Finance sees provider cost only; engineer can retry jobs |
| Finance reports and CSV export | R | r | - | X | - | Engineer sees no fee lines; CSV export is audited |
| Settings (prices display, credit prices, ceilings) | X | W | - | R | - | Engineer within plus or minus 20 percent of the current value; beyond that, owner |
| Audit log | R | R | r | r | r | Non-owners see their own actions; engineers also see all non-security actions |
| Admin users and roles | X | - | - | - | - | Owner only |

Permission names in code follow `resource.action`, for example `users.reveal`, `credits.grant`, `killswitch.set`, `settings.ceilings.write`. The matrix above is the source for `admin/permissions.py`, and a test asserts that every `/v1/admin` route has a permission and that the table and code agree.

## 4. Audit log

Every admin write, reveal, export and sign-in writes one `audit_log` row. Reads of lists do not, but reads of a single user's detail, an impersonated page, and any CSV export do.

### 4.1 Row shape

| Field (`audit_log` column) | Meaning |
|---|---|
| `id` | Internal bigint identity; the API returns it as the string `audit_id` |
| `created_at` | `timestamptz`, UTC |
| `actor_type` | `admin`, `system` (scheduler, auto-expiry, breakers), `worker` (jobs and webhook handlers) or `user` |
| `actor_user_id` | `admin_users.user_id`, null for system and worker |
| `action` | Dotted name such as `credits.grant`, `killswitch.set`, `user.reveal`, `impersonation.start` |
| `entity_type`, `entity_id` | For example `user` and the user's UUID, or `kill_switch` and its key |
| `before`, `after` | JSON of the changed fields only; secrets and raw PII masked (see 4.2) |
| `reason` | Free text, required for writes |
| `request_id`, `ip_hash` | Correlation and context; IP stored hashed with a monthly salt |
| `actor_role` | The admin's `admin_role` at the time of the action |
| `impersonation_id` | Set on every row written during an impersonation session |
| `result`, `error_code` | `ok`, `denied` or `error`, with an error code for the last two |
| `user_agent` | The admin browser's user agent |
| `retention_class` | `extended` for money, security and control actions (prefixes `credits.`, `refund.`, `comp.`, `admin_user.`, `killswitch.`, `impersonation.`, `deletion.`, `settings.`), otherwise `standard` (4.2) |

### 4.2 Rules

- **Before and after are mandatory** for updates. For creates `before` is null; for deletes `after` is null. A credit grant records the balance before and after as well as the amount.
- **Append only.** The application database role for admin has `INSERT` and `SELECT` on `audit_log` only; a trigger rejects `UPDATE` and `DELETE`. The table is purged only by the retention job: `standard` rows after 13 months, `extended` rows (the money, security and control prefixes in 4.1) after 7 years, and the nightly hash-chain digests below for 7 years (03 section 8).
- **Redaction.** PII fields in `before` and `after` are stored masked (`a***@g***.com`) or as a salted hash. Secrets (API keys, webhook secrets, tokens) are never stored, even encrypted.
- **Denied attempts are logged** with `ctx.result = 'denied'`; 5 denials in 10 minutes by one admin raises an alert.
- **Tamper evidence.** A nightly job computes a hash chain over the day's rows and stores the digest in R2 object storage with object lock.
- **Viewer.** Filter by actor, action, target, date and result; "show raw JSON" is available to the owner. Each row links to the affected screen.
- **Visible to the user** only for impersonation: the user's Settings shows "Support access log" (time, reason category, read-only) fed by `audit_log`.

## 5. Console conventions

- **Layout:** left navigation grouped as Monitor (Overview, Provider health, System health), People (Users, Support inbox, Moderation), Money (Subscriptions, Credits and AI spend, Affiliate, Finance, Concierge, Group payments), Control (Kill switches, Flags, Settings, Partner guides), Audit. Items hidden when the role has no access. The Hermi design tokens are reused, with a neutral "Hermi admin" header so it cannot be mistaken for the customer app.
- **Environment banner:** production shows a thin bar in `--tp-route-a-ink` (#C4264D) labeled "Production"; staging shows a thin bar in `--tp-sky` labeled "Staging". Destructive buttons are disabled on staging data copied from production.
- **Lists:** server-side pagination (cursor), 50 rows a page, sortable columns, filters stored in the URL so a view can be shared with another admin. Maximum 10,000 rows in any CSV.
- **Masking:** emails as `a***@g***.com`, names as initials, trip titles truncated to 20 characters, no addresses, no phone numbers, no notes text, no passport or document data anywhere. User ids are shown as the last 8 characters of the UUID with copy.
- **Confirmation tiers:** `W` actions show a dialog with the effect and a reason box. `X` actions add a typed confirmation (for example the word `KILL-AI` or the user's short id) and a step-up 2FA check.
- **Money display:** integer minor units rendered with the currency; AI and provider spend shown in dollars to 4 decimals from micro-dollars.
- **Time:** all times in UTC with a local tooltip. "Today" means the UTC day, matching the ledger's daily ceiling period.
- **Empty and error states:** every tile shows "No data yet" or a reason ("Stripe unreachable, last sync 14:02 UTC"); a failed tile never shows zero.
- **Auto refresh:** Overview every 60 seconds, Provider and System health every 30 seconds, others on demand.

## 6. Screens

Each screen lists purpose, data shown, filters, actions and guardrails.

### 6.1 Overview dashboard

- **Purpose:** the Monday metrics review in one page and the place alerts surface. Matches the weekly rhythm and kill rule tracking in the plan.
- **Data shown** (source tables in brackets):
  - MAU (distinct non-test `users` with an authenticated request in the trailing 30 days) and DAU (trailing 24 hours), with 7 and 30 day sparklines [`users`, rollup].
  - New signups today and this week; trials started (`subscriptions` with `is_trial`); trial to paid conversions this week; free to paid conversion of MAU [`subscriptions`, `store_transactions`].
  - MRR: monthly-normalized active subscriptions, gross and net of Apple's 15 percent fee, split by `plus`, `family`, `pro` [`subscriptions`].
  - Revenue today by stream: subscriptions, Trip Pass and Group Trip Pass, credit packs, affiliate (estimated from approved plus pending, labeled "estimate"), concierge commission, group payment fees, advisor seats, print [`store_transactions`, `affiliate_conversions`, `concierge_requests`, `settlements`].
  - AI spend today versus budget: sum of `ai_usage` cost plus `provider_calls` cost against the global daily budget setting, with a bar that turns amber at 80 percent and red at 95 percent (the same thresholds that trigger the automatic breakers).
  - Affiliate clicks today and EPC (earnings per click: approved commission in the last 30 days divided by clicks in the same window) [`link_clicks`, `affiliate_conversions`].
  - Kill rule card: share of MAU that pays and affiliate income per MAU annualized, with months since launch (month 9 is the decision point).
  - Active kill switches and breakers, with expiry countdowns.
  - Alerts list (section 10): open alerts with severity, age and a link to the screen.
- **Filters:** date range (today, 7 days, 30 days, custom), platform (web, iOS), tier. Default is today and 30-day trend.
- **Actions:** acknowledge an alert (W, engineer and owner), snooze an alert for up to 24 hours with a reason, jump to the screen behind a tile. There are no money or user actions on this page.
- **Guardrails:** data comes from rollup tables refreshed every 5 minutes and stamped "as of"; a stale rollup (over 15 minutes) shows a warning. Support and finance see only the tiles their role permits.

### 6.2 Users

- **Purpose:** find one person fast, see everything that affects their experience, and fix it with a small, audited action.
- **Search:** exact email (matched by a salted hash, so the search box itself never returns partial matches on PII), user id, RevenueCat app user id, Stripe customer id, device token suffix, trip id, support ticket id. No free-text name search.
- **List columns (masked):** short id, masked email, tier, country, signup date, last seen, status (`active`, `suspended`, `pending_deletion`, `deleted`).
- **Filters:** tier, platform, country, signup range, status, has open ticket, deletion pending, AI held.
- **Profile (detail) tabs:**
  - Summary: tier, sign-in providers (`auth_identities` provider names only), locale, created, last seen, consents (`consents`: AI consent timestamp, marketing opt-in), flags that apply.
  - Trips: `trips` and `trip_members` roles, owner or guest, title truncated, dates, pass attached.
  - Entitlements: current `entitlements`, `subscriptions`, `trip_passes` with source (store, comp, pass) and expiry.
  - Credits: balance by bucket (`monthly` and `household_monthly`, `trip_pass`, `purchase`, from `credit_balances`), `credit_ledger` history, `credit_grants`, month and day spend against ceiling.
  - Devices: `devices` (platform, app version, last seen, push enabled); no tokens shown.
  - Support history: `support_tickets` linked to this user.
  - Privacy: `data_exports`, `deletion_requests`, consent history.
  - Audit: `audit_log` rows with this user as target.
- **Actions:**
  - *Grant credits with reason* (`credits.grant`): amount, reason category (goodwill, bug, refund reversal, promotion), note. Writes a `credit_grants` row (kind `adjustment`) and a `credit_ledger` entry (`entry_type = 'adjust'`), expiring in 90 days. Limits in section 3.
  - *Extend a pass*: choose a `trip_passes` row and days. Updates its expiry and logs before and after.
  - *Comp a subscription*: grants a promotional entitlement through the RevenueCat promotional API, mirrors it in `entitlements` with `source = comp` and an end date. Cannot stack on an active paid subscription.
  - *Force sign-out*: revokes the Supabase sessions through the Auth admin API, sets `devices.revoked_at`, and queues a silent push that clears the app session.
  - *Start export*: creates a `data_exports` row and job; the download link is emailed to the user only.
  - *Process deletion*: lists the `deletion_requests` row; "process now" is owner only and shows what will be removed, the Apple subscription warning (deleting an account does not cancel an Apple subscription) and any shared trips that will transfer or be deleted.
  - *Impersonate read-only*: see below.
  - *Hold AI for this user*: a `kill_switches` row with the user-scoped key `user:<users.id>` (created on demand, never seeded, with the same mandatory expiry as any manual switch), for abuse or a runaway (engineer and owner).
- **Impersonation, read-only, with consent:**
  1. Support opens the request and picks a reason category; the user gets an in-app prompt and an email: "Hermi support asks to view your account to help with ticket 4821. They cannot change anything." with Approve and Decline.
  2. On approval the API mints a 15 minute impersonation token bound to that admin and user, carrying an `imp` claim. The API rejects every non-GET request with that token and hides secrets, payment details and notes bodies.
  3. The admin UI shows a full-width banner with a countdown and an End button. Each page fetched writes an `audit_log` row with `impersonation_id`. Start, end and expiry are logged.
  4. The user sees the event in Settings, "Support access log". Without consent there is no impersonation; there is no override, including for the owner.
- **Guardrails:** reveal of email or name is per record, reason required, and limited to 30 an hour; no bulk reveal; no user edit of email, name or password from the console; a grant above the role limit is rejected with the limit shown; a user with a deletion pending shows a red banner and most actions are disabled.

### 6.3 Subscriptions and store transactions

- **Purpose:** know that money events from Apple (through RevenueCat) and Stripe reached our tables, and fix the ones that did not.
- **Data shown:**
  - RevenueCat sync status: last webhook received, webhook lag (p95 over 24 hours), last reconcile job run and result, count of entitlement mismatches between `entitlements` and RevenueCat's REST API, backlog of unprocessed `webhook_events`.
  - Subscription list (`subscriptions`): status (`in_trial`, `active`, `in_grace`, `billing_retry`, `paused`, `expired`, `refunded`, `revoked`), product, period end, store, masked user.
  - Store transactions (`store_transactions`): transaction id, product, price, currency, purchase date, `refunded_at`, linked user and trip (for passes).
  - Failed webhooks (`webhook_events` with status failed): source (RevenueCat, Stripe, affiliate networks), event type, error, attempts, age; payload shown redacted.
  - Refunds: `REFUND` events with the credit reversal result and current balance (negative balances are highlighted because AI is blocked until positive).
- **Filters:** source, event type, status, product, date range, user short id, "mismatched only".
- **Actions:**
  - *Replay a failed webhook* (single or selected, max 100): reprocesses the stored payload through the same idempotent handler, keyed by event id, so a replay cannot double-grant. A dry run shows what would change first.
  - *Run reconcile now* for one user or all (engineer, owner).
  - *Web refund (Stripe only)* for group payments, advisor seats and print orders (finance up to $100, owner above). The console never refunds an Apple purchase; it shows the link to Apple's report-a-problem guidance and lets support reverse credits if Apple refunds.
- **Guardrails:** replays never change a processed event's stored payload; an event replayed more than 3 times needs the owner; purchases granted by the server only after verified transactions (the console cannot create a `store_transactions` row).

### 6.4 Credits and AI spend

- **Purpose:** see where provider money goes, catch runaways in minutes, and stop a run.
- **Data shown** (from `ai_usage`, `provider_calls`, `credit_ledger`, `runs`, `run_events`):
  - Spend today, this month and trailing 7-day mean, versus the global budget; gap between our sum and the daily Anthropic cost report (alert above 3 percent).
  - Per feature: cost and call count for `explain`, `live_search`, `draft_day`, `draft_trip`, `research`, `agent_run`; credits charged versus real cost (repricing signal when drift exceeds 20 percent); shared research cache hit rate; prompt cache read ratio on agent runs (alert under 70 percent).
  - Per tier: spend per active user and per active payer (alerts above $2 for Plus and $6 for Pro).
  - Top spenders: top 20 users by month-to-date spend, with tier, ceiling, percent of ceiling.
  - Ceiling hits: users who reached their daily or monthly ceiling, by tier, with the upsell outcome (pack bought or not).
  - Runaway detection list (section 10 rules): runs past 20 turns, past their dollar stop, past 8 minutes, accounts above a ceiling by more than 10 percent, accounts with more than 5 paid actions in a minute.
  - Live runs: in-flight `runs` with account, feature, turns used, spend so far, age.
- **Filters:** date range, feature, model, tier, provider, shared cache status (hit, miss, refresh, bypass), batch or not.
- **Actions:**
  - *Cancel a run*: sets the run's cancel request; the worker stops at the next checkpoint, keeps what was saved, settles credits pro rata by turns used (minimum 8 credits for an agent run) and refunds if nothing was saved. Audited with the run id.
  - *Hold AI for a user* (engineer, owner), *release hold*.
  - *Open the user* or *open the run* (run events, without prompt text; prompts and itineraries are never shown, only sizes and hashes).
- **Guardrails:** this screen is read-only for money; ledger balances are changed only through the audited grant action on the user screen. A cancel cannot raise a balance above what was reserved. Per-user spend is visible to support only inside that user's profile.

### 6.5 Kill switches and circuit breakers

- **Purpose:** stop spend or a failing dependency in seconds, without a deploy.
- **Switches** (rows in `kill_switches`; `engaged = true` means the feature is stopped; keys are the 03 section 11.5 seeds):

| Key | Stops | Keeps working |
|---|---|---|
| `ai.all` | Every Claude call and agent run | Cached and saved data, cached fares, all non-AI features |
| `ai.free_tier` | AI actions for the Free tier | Paid tiers, cached answers |
| `ai.all_but_paid` | AI actions for every tier except paid ones (the 95 percent breaker) | Paid tiers, cached answers |
| `provider.serpapi` | Live flight and rental search (SerpApi, the live provider) | Travelpayouts cached fares, saved fares, alerts on cached fares |
| `provider.travelpayouts`, `provider.geoapify`, `provider.anthropic`, `provider.viator`, `provider.stay22`, `provider.frankfurter`, `provider.stripe` | All calls to that provider; the dependent feature shows a stale-data banner | Everything that does not need it |
| `ai.explain`, `ai.draft`, `ai.research`, `ai.taster`, `ai.import`, `ai.packing`, `ai.web_search`, `ai.web_fetch`, `ai.model.sonnet`, `ai.model.haiku`, `ai.force_haiku`, `ai.batch`, `ai.shared_cache_write` | That AI feature, tool, model route or lane (06 section 6.6) | Everything else |
| `ai.agent_runs` | Starting new agent runs (running ones finish or are cancelled) | Single-call AI, research from cache |
| `user:<users.id>` (a per-account hold; created on demand, never seeded) | AI and live actions for one account | Everything else for that account |
| `affiliate.all`, `affiliate.{program code}` | Partner links (plain links only) | Everything else |
| `signups`, `purchases` | New account creation; paywalls and purchase buttons | Existing accounts and restores |

- **Breakers (automatic):** the system flips switches itself and records them with `actor_type = system`: at 80 percent of the daily global Anthropic budget `ai.free_tier` engages; at 95 percent `ai.all_but_paid` engages (the `auto_rule` values in 03); at 90 percent of the SerpApi monthly quota `provider.serpapi` narrows live checks to top-value routes (a chosen flight or an active alert), then cached only; any provider error rate over 50 percent for 5 minutes trips that provider's switch to "half-open" (one probe a minute) until it recovers. Automatic trips page the owner.
- **Data shown:** each switch with state (on, off manual, off automatic), who set it, reason, set time, expiry countdown, the effect on users (count of requests blocked in the last hour), and history of the last 20 changes.
- **Actions:** set or clear a switch. The dialog requires: reason, typed confirmation of the switch key, step-up 2FA, and an expiry.
- **Auto-expiry:** every manual "off" must have an expiry (`kill_switches.expires_at`; the check constraint `ck_kill_switches_expiry` in 03 rejects an admin-set switch without one, except a provider switch left "until cleared" by the owner): 1 hour, 4 hours (default), 24 hours or 72 hours. Only the owner may choose "until cleared", and only for provider switches during a provider incident. A scheduler job clears expired switches and writes an `audit_log` row as `system`; the owner gets a notification 15 minutes before expiry (`expiry_notified_at` records it) so a live incident is not silently re-enabled.
- **Guardrails:** the API reads switches through a 5 second in-process cache (refreshed at once by `NOTIFY` on a change) and fails closed (paid calls refused) if the table cannot be read; switching `ai.all` off posts to the on-call channel; a runbook link is shown beside each switch; a "test in staging" toggle lets an engineer practice without touching production. Users see plain copy ("Live prices are paused. Saved prices still work.") with no blame on a provider.

### 6.6 Feature flags and experiments

- **Purpose:** roll features out gradually and test paywall and onboarding changes without a release.
- **Data shown:** `feature_flags` rows with key, `kind` (`flag`, `experiment` for `exp_` keys, `setting` for `setting_` keys; a check constraint keeps it in step with the prefix), `enabled`, `rollout_pct`, `rules` (`tiers`, `platforms`, `countries`, `user_ids`, `min_app_version`, `max_app_version`), `variants`, `updated_by`, created and changed times, and a stale-flag warning (unchanged 90 days at 100 percent or 0 percent).
- **Flags at launch** (03 section 11.5): `tier_pro` (off), `serpapi_live_fares` (on behind legal review), `scheduled_agent_routines` (off), `group_tools` (on), `group_payments` (off until Phase 4), `concierge_requests`, `partner_guides`, `print_orders`, `advisor_workspaces`, `poll_comments`, `inapp_hotel_booking`, `insurance_cards`, `visa_assist` and `passkeys` (all off), `room_block_requests` (on, for Group Trip Pass trips), `guest_mode`, `shared_research_cache`, `link_preview`, `affiliate_lodging_test` and `min_app_version` (on). There is deliberately no flag that turns affiliate links or their disclosure off for a tier.
- **Experiments:** name, hypothesis, variants with allocation, primary metric, guardrail metrics, start and end dates, status (draft, running, stopped, concluded). Results table per variant: exposures, conversions, conversion rate, relative lift, probability to beat control (Bayesian), minimum detectable effect, and guardrails (refund rate, AI cost per user, 7-day retention). Exposure and conversion events come from PostHog (03 has no `analytics_events` table); revenue figures come from `store_transactions`.
- **Paywall experiments** in the roadmap: Trip Pass price points, annual-first versus pass-first ordering, trial copy. A price test uses separate store products or RevenueCat offerings (the console cannot change App Store prices); the console only assigns users to offerings.
- **Filters:** kind, state, owner, tier, stale.
- **Actions:** create, edit rollout percent (steps of 1, 5, 10, 25, 50, 100), pause, end an experiment and pick a winner, archive a flag. All changes audited; percentage changes apply within 60 seconds.
- **Guardrails:**
  - No experiment may hide or weaken an affiliate disclosure, rank by commission, or change what Free users can see of cached fares. The form rejects variants that touch those keys.
  - No more than 50 percent of eligible traffic in an experiment; a minimum runtime of 14 days and a minimum sample before a winner can be declared; peeking warnings before then.
  - Assignment is sticky by user id hash, so nobody sees price changes flip back and forth.
  - One experiment per surface at a time. Killing an experiment reverts everyone to control instantly.
  - Turning on `tier_pro` needs the Pro launch gate (measured agent cost of $0.60 or less per run over 200 runs, or over 15 percent of Plus payers buying agent-run credits); the screen shows both numbers and blocks enabling until one is met, unless the owner overrides with a reason.

### 6.7 Affiliate revenue

- **Purpose:** see what the free-tier income is, where it comes from, and whether tracking and disclosure are healthy.
- **Data shown** (`link_clicks`, `affiliate_conversions`, `affiliate_programs`, `affiliate_link_templates`):
  - Revenue by month, by network (Travelpayouts, Viator, Stay22, later Expedia Group, Booking.com, Skyscanner, Airalo, GetYourGuide), by program, by placement (surface), by partner; revenue per MAU.
  - Clicks, conversions, conversion rate, EPC, click-to-booking days, by surface and program; the launch assumption next to the measured value ($0.10, $0.60, $1.50 per monthly user per year).
  - Cash view: pending, approved and paid amounts, and a three month projection from the observed pending-to-approved ratio.
  - Conversion import status: for each network the last nightly import time, rows imported, rows changed, failures, unmatched share (alert above 10 percent, which means a tracking break).
  - Redirect health: `/go/{click_id}` 4xx and 5xx rate (alert above 1 percent), expired or reused click ids, clicks down more than 50 percent day over day.
  - Broken link checker: for every active template, the result of the last check.
  - Disclosure audit: each surface that shows a partner button, with a check that the text "We earn a commission if you book here." is present, the "Ad" label appears on UK and EU storefronts, lists state how they are sorted, and the "Hide booking links" setting works.
- **Filters:** date range, network, program, surface, platform, country, status (pending, approved, rejected, paid).
- **Actions:**
  - *Run the link checker now* for a template or all; *disable a template* (`affiliate_link_templates.active = false`; stops new clicks through it and falls back to a plain link).
  - *Edit a template* (two-person approval): proposes a change; a second admin approves it; the diff of the template is stored in `audit_log`.
  - *Re-run a conversion import* for a date range (idempotent upsert on program and network transaction id).
  - *Mark a payout received* (finance): inserts an `affiliate_payouts` row (`program_id`, `period_start`, `period_end`, `amount_minor`, `currency`, `received_at`, `reference`).
  - *Run disclosure audit now* and attach the result screenshots.
- **Guardrails:**
  - The link checker never fetches Airbnb, Vrbo or Booking.com pages. It checks only our own redirect (that the stored template renders a well-formed `Location` for a test click id) and, for other partners, a HEAD request to the partner's tracking domain. Airbnb links are plain links and are listed as "not checked by design".
  - No ranking by commission: the screen shows payout per program for finance only; the code path that orders lists never reads it, and a test fails the build if it does.
  - Templates are stored values only; there is no free-form URL entry and no `url=` parameter, so the redirect can never become an open redirect.
  - Click logs show `ip_hash` and sub-id only; user ids are visible only after a user-level reveal.

### 6.8 Concierge queue

- **Purpose:** run the optional "Have a human book this" lane with clear status and commission records (hosted under a host travel agency).
- **Data shown** (`concierge_requests`): request id, masked requester, trip, `kind` (`stay`, `cruise`, `complex_trip`, `other`; room block requests come from `room_block_requests`), budget range, dates, `status`, `assigned_to`, SLA timer, `quote_minor`, `agency_reference` (booking reference), `perks`, `commission_expected_minor` and `commission_received_minor`, `booked_at` and `completed_at`.
- **Statuses** (`concierge_status`): `submitted`, `triaged`, `assigned`, `quoted`, `booked`, `completed`, `cancelled`, `declined`. Commission pending and received are read from `commission_expected_minor` and `commission_received_minor`.
- **Filters:** status, assignee, type, age, overdue SLA, commission outstanding.
- **Actions:** assign, change status (support, engineer, owner), add note, send templated message (via support macros), record commission (finance: `commission_expected_minor`, `commission_received_minor`, `commission_currency`; the host split is `advisor_orgs.commission_split_bps`), attach perks, decline with reason, convert into a support ticket.
- **Guardrails:** first reply due within 1 business day (overdue shows red); a request is created only by a user's explicit tap, never automatically; the requester sees the disclosure ("Hermi earns a commission from the travel agency on bookings made this way"); commission fields are finance and owner writable only; the console never stores payment card data; a declined request says why to the user through a macro.

### 6.9 Group payments and settlements

- **Purpose (Phase 4; at launch this screen lists manual `recorded` settlements read-only, since Stripe collection is for `group_trip_pass` and `pro` in Phase 4):** watch real-world cost collection done through Stripe (never Apple In-App Purchase, never for digital features) and handle disputes.
- **Data shown** (`expenses`, `expense_shares`, `settlements` plus Stripe state): per trip settlements with amount, currency, payer, payee (masked), `settlements.status` (`recorded`, `pending`, `succeeded`, `failed`, `refunded`) with the live Stripe state, payout status, fees, and open disputes with reason, due-by date and evidence status.
- **Filters:** Stripe status, trip, currency, amount range, dispute state, date.
- **Actions:** open in Stripe (deep link), refund (finance up to $100, owner above, typed confirmation), attach evidence notes to a dispute (finance), mark a settlement as settled outside the app (with reason), resend a payment request.
- **Guardrails:** a scan blocks any settlement tagged as paying for a digital Hermi feature (policy check); dispute due dates raise an alert 3 days before; amounts above $500 need the owner; the console never shows card or bank details, only Stripe ids and last four where Stripe returns them.

### 6.10 Partner guides

- **Purpose:** manage labeled destination guides from tourism boards and hotel brands without ever mixing them into rankings.
- **Data shown** (`partner_guides`): `title`, `destination_name`, `partner_name` (sponsor), `disclosure_text` (label text), `is_sponsored`, `status` (`draft`, `published`, `archived`), `review_state` (`none`, `in_review`, `changes_requested`, `approved`), `reviewed_by`, `created_by` (author), `published_at`, sponsorship terms (`sponsor_starts_on`, `sponsor_ends_on`, `sponsor_fee_minor`, `sponsor_invoice_ref`; finance only), outbound clicks from `link_clicks`, views from first-party analytics events, disclosure check result.
- **Editor:** structured content blocks (overview, neighborhoods, sample days, practical notes), sources list, images with alt text and credits, sponsor block, a mandatory label field that renders "Sponsored guide from {sponsor}" on every guide page and card. Side-by-side preview in the app's guide layout and a diff view between versions.
- **Filters:** status, destination, sponsor, author, expiring in 14 days.
- **Workflow:** author (`content` or owner) drafts, submits for review; a different admin reviews against the checklist (label present, sources cited, no claim that AI wrote it, no insurance, visa or legal advice beyond official links, affiliate links labeled, no paid placement in search results); the owner approves and publishes. Approval and publish are `X` actions. Publishing schedules an end date.
- **Actions:** save draft, submit, request changes (with comments), approve, publish, pause (immediately hides), archive, duplicate as new version.
- **Guardrails:** an author cannot approve their own guide; a guide cannot publish without the label and a sponsor record; guides appear only in the guides section and destination pages with the label, never in search, autosuggest or ranked lists; sponsor payment records live with finance, not in the editor; every publish writes before and after content to `audit_log`.

### 6.11 Support inbox

- **Purpose:** answer users within 2 business days (the commitment in the plan) with full context.
- **Data shown** (`support_tickets`): ticket id, `source` (`in_app` with `app_version` and `platform` attached, `email` to support@hermi.world, or `admin`), `subject`, `category`, `status` (`open`, `pending`, `resolved`, `closed`), `priority` (`low`, `normal`, `high`, `urgent`), `assigned_admin_id`, SLA timer, linked user (card with tier, entitlements, recent errors), thread (`messages`), `internal_notes` and `tags`.
- **Filters:** status, assignee, priority, tag, source, tier, overdue, linked to concierge, contains refund.
- **Actions:** reply (email via Resend), internal note, assign, tag, merge duplicates, link or unlink user, set priority, close, insert a macro, jump to the user screen actions (grant credits, extend pass) with the ticket id prefilled as the reason.
- **Macros:** versioned templates with variables (`{first_name}`, `{ticket_id}`, `{product}`), kept as markdown files in the repo (`admin/macros/*.md`) and loaded at deploy, so changes are reviewed in pull requests and no new table is needed. Launch set: refund guidance (refunds go through Apple at reportaproblem.apple.com, we can reverse credits), cancellation help (Manage Subscriptions link), deletion does not cancel an Apple subscription, how to restore purchases, credits explained, data export ready, affiliate disclosure explained, report received, concierge follow-up, outage apology.
- **Guardrails:** the ticket's email is revealed inside the ticket (audited once per ticket); macros cannot include admin-only data; no ticket text is sent to AI services; attachments are scanned and stored in R2 with signed URLs; a reply that mentions a refund or credit has to be paired with an audited action or it warns the agent.

### 6.12 Content moderation

- **Purpose:** satisfy App Review Guideline 1.2 and protect users: act on reports of shared trips and AI content quickly.
- **Queues:**
  - Reported shared trips (`content_reports` with `target_type = 'shared_trip'`, joined to `trip_share_links`): link, reason, reporter count, content preview (titles and text with notes bodies hidden until opened), owner (masked).
  - AI content reports (`content_reports` with `target_type` `agent_note`, `ai_answer` or `research_cache`: "report a problem" on AI answers, saved notes from runs and shared research entries; thumbs-down is feedback only): content, sources cited, report reason, run id, model, prompt version.
- **Filters:** queue, reason (spam, harmful, wrong info, copyright, privacy), age, status, repeat offender.
- **Actions:** dismiss with reason; disable a share link (sets `trip_share_links.revoked_at`); hide content; flag a shared research cache entry (sets `stale_until` to now so it is purged, re-run and not served); ask the user to edit; warn; suspend sharing for a user (`users.sharing_suspended_at`); escalate to owner (the owner may then set `users.status = 'suspended'`, which the API answers with `403 account_inactive`). Content role can act on AI content only.
- **Guardrails:** reports are answered within 24 hours (the dashboard alerts at 12); reporter identity is never revealed to the reported user; the console shows the source URL of every AI fact so a wrong fact can be traced to a page; every action is audited; repeat violations (3 in 30 days, counted from `content_reports`) queue a suspension for owner review.

### 6.13 Provider health

- **Purpose:** know whether SerpApi, Travelpayouts, Geoapify, Anthropic and Stripe are working and affordable, before users notice.
- **Data shown** (`provider_calls`, provider status APIs where they exist): per provider: requests, success rate, p50 and p95 latency, 429 and 5xx rates, quota used and remaining (SerpApi account API, Travelpayouts limits, Geoapify credits, Anthropic rate-limit headers and org daily spend, Stripe API errors), spend today and this month, cache hit rate, current kill switch state, and the last incident. Also listed for completeness: RevenueCat, Supabase Auth, APNs and Resend, with status and last error.
- **Filters:** provider, endpoint, range, cached or live.
- **Actions:** run a synthetic probe (one cheap request), open the kill switch dialog, set a quota alert threshold (settings), export an error sample (redacted).
- **Guardrails:** probes use a test account and are rate limited to 1 a minute; quotas that drop under 20 percent alert; the screen explains the fallback users get when each provider is down.

### 6.14 System health

- **Purpose:** queues, jobs, webhooks and deploys in one place.
- **Data shown:** queue depth and oldest job age per lane (`api`, `ai`, `notify`); job failures and dead letters with error class; scheduler heartbeat (last scan, routines overdue); webhook backlog (unprocessed `webhook_events`, oldest age); nightly jobs status (conversion import, usage reconciliation, rollups, exports, deletion sweeps, audit hash chain); database (connections versus limit, longest transaction, disk); recent deploys (version, commit, time, migration head, result) with a link to roll back in the host; last restore drill date; current minimum app version.
- **Filters:** lane, job kind, status, time range.
- **Actions:** retry a failed job, retry all of one kind (max 200), cancel a queued job, move a dead letter back to the queue, pause a lane (engineer, owner; creates a manual kill switch with expiry), force a rollup refresh.
- **Guardrails:** retry is idempotent (jobs are keyed); a job that failed 3 times after a retry needs the owner; nothing on this screen shows job payloads with user content, only kinds, ids and error text scrubbed of PII.

### 6.15 Finance reports

- **Purpose:** the monthly close and the kill rule, without a spreadsheet.
- **Data shown:**
  - Monthly revenue by stream: subscriptions by tier, Trip Pass, Group Trip Pass, credit packs, affiliate by network, concierge commission, group payment fees, advisor seats, print.
  - Fees: Apple at 15 percent (Small Business Program; shown as computed and flagged if the program status changes), Stripe fees from balance transactions, RevenueCat fee.
  - Cost: AI spend (from `ai_usage`), provider spend (SerpApi, Geoapify, Travelpayouts), infrastructure and other costs (entered monthly by finance as `feature_flags` rows with a `setting_` key, for example `setting_finance_cost_2026_11`).
  - Gross margin per month and per tier: revenue after store and payment fees, minus AI and provider cost, minus infrastructure. Targets from the plan are shown as a reference line.
  - Kill rule tracker: percent of MAU that pays and affiliate income per MAU annualized, month counter since launch.
  - Cash versus recognized: affiliate pending, approved, paid.
- **Filters:** month range, stream, tier, currency (reported in USD with stored FX from `fx_rates`).
- **Actions:** export CSV (aggregates by month and stream; a per-transaction export uses opaque user ids, never emails), lock a month (finance: prevents later edits to cost entries), add or correct a cost entry (with reason).
- **Guardrails:** exports need step-up 2FA and are audited with the filter used; no PII in any export; a locked month can be unlocked only by the owner; figures are labeled "estimate" until the network or store has paid.

### 6.16 Settings

- **Purpose:** change business parameters without a deploy and keep a history.
- **Data shown and editable.** Each group is stored where 03 already keeps it, so an edit is an audited `UPDATE` and never a migration (03 section 11):
  - Prices display: `store_products.price_minor` for Plus, Family, Pro, Trip Pass, Group Trip Pass and credit packs, used on the web pricing page and paywall fallback. The real prices live in App Store Connect and Stripe; the screen shows a check that these values match the store prices (from RevenueCat offerings) and flags a mismatch.
  - Credit prices per action in `credit_action_prices` (`explain` 1, `live_search` 1, `draft_day` 1, `draft_trip` 4, `research` 8 with `credits_cached` 1, `agent_run` 40 with `credits_cached` 8, plus `hard_stop_micros`, `max_turns`, `max_searches`, `max_fetches`) and monthly allowances in `plans.monthly_credits` and `plans.credits_granted` (Free 12, Plus 60, Family 150, Pro 240, Trip Pass 40, Group Trip Pass 80).
  - Ceilings: `plans.limits` keys `monthly_ceiling_micros` and `daily_ceiling_micros` per tier and pass. The global daily Anthropic budget (`setting_ai_global_daily_usd`, seeded at $50), per-provider quotas (`setting_serpapi_monthly_quota`, seeded at 5,000) and alert thresholds are `setting_` rows in `feature_flags` (03 section 11.5 seeds these and `setting_ai_warm_daily_usd`; the console creates the others).
  - Admin limits used in section 3 (grant caps, extension caps), also `setting_` rows.
- **Filters:** group, changed in the last 30 days.
- **Actions:** edit a value with reason (engineer within plus or minus 20 percent of the current value, owner beyond), schedule a change for a future time, revert to a previous value from history.
- **Guardrails:** bounds per setting (a ceiling cannot be set above 2 times the plan default, a credit price cannot be 0 or negative, allowances cannot be raised above the level where ceiling covers them) enforced by the API; changes apply within 60 seconds and never alter reservations already made; history shows who, when, before, after and reason; changes to ceilings post to the on-call channel.

## 7. Wireframes

### 7.1 Overview dashboard

```
+----------------------------------------------------------------------------------+
| HERMI ADMIN   [Production]                           anthony (owner)   [Sign out]|
+-------------+--------------------------------------------------------------------+
| MONITOR     | Overview            Range: [Today v]  Platform: [All v]  as of 14:05Z |
|  Overview   +--------------------------------------------------------------------+
|  Providers  | ALERTS (2)  [!] AI spend at 83% of daily budget     12m  [Open]      |
|  System     |             [!] Conversion import late (Stay22)      3h  [Open]      |
| PEOPLE      +------------+------------+------------+------------+----------------+
|  Users      | MAU        | DAU        | New signups| Trials     | Conversions    |
|  Support    | 4,210      | 612        | 38         | 21 started | 6 this week    |
|  Moderation | ~~~~/\~~~  | ~~/\/\~~   | today      | 9 active   | 3.1% of MAU    |
| MONEY       +------------+------------+------------+------------+----------------+
|  Subscript. | MRR gross $6,420   net of Apple $5,457   plus 2,610 family 410 pro 0  |
|  Credits/AI +--------------------------------+-----------------------------------+
|  Affiliate  | Revenue today by stream        | AI spend today vs budget          |
|  Finance    |  Subscriptions      $188.20    |  $41.30 of $50.00  [=========>  ] |
|  Concierge  |  Trip passes         $79.92    |  Claude $36.10  SerpApi $4.20     |
|  Group pay  |  Credit packs        $22.93    |  Geoapify $1.00                   |
| CONTROL     |  Affiliate (est.)    $31.40    |  Top feature: agent_run $22.80    |
|  Kill sw.   |  Concierge            $0.00    |  Amber at 80%, red at 95%         |
|  Flags      |  Group / advisors     $0.00    +-----------------------------------+
|  Settings   |  Total today        $322.45    | Affiliate today                   |
|  Guides     |                                |  Clicks 486   EPC (30d) $0.071    |
| AUDIT       +--------------------------------+  Unmatched conversions 4.2%       |
|             | KILL SWITCHES  all on          +-----------------------------------+
|             | none off. [Manage]             | KILL RULE (month 4 of 9)          |
|             |                                |  Paying share of MAU   2.6%       |
|             |                                |  Affiliate $/MAU/yr    $0.41      |
+-------------+--------------------------------+-----------------------------------+
```

Tiles are clickable and open the owning screen with the same filters. A tile whose source is stale shows a grey "as of" chip and an amber warning instead of a number.

### 7.2 User detail

```
+----------------------------------------------------------------------------------+
| Users / 7f3a91c2    [Production]                                        [Audit tab]|
+----------------------------------------------------------------------------------+
| a***@g***.com  [Reveal]        Plus annual (renews 2027-03-02)     Status: active |
| US, iOS 1.2.0, joined 2026-11-03, last seen 2h ago   Consent: AI yes, marketing no|
+---------------------------------+------------------------------------------------+
| TABS: Summary | Trips | Entitlements | Credits | Devices | Support | Privacy | Audit |
+---------------------------------+------------------------------------------------+
| CREDITS                         | SPEND (provider cost)                          |
|  Balance  38                    |  Today   $0.12 of $0.40 daily                  |
|   monthly 22  pass 0  bought 16 |  Month   $1.41 of $2.25 ceiling   [=====>   ] |
|  Ledger (last 5)                |  Live runs: none    Hold AI: off               |
|   +8  refund  run 91ab  Nov 18  +---------------------------------------------+
|   -40 agent_run       Nov 18  | TRIPS (3)                                       |
|   +60 grant_monthly   Nov 12  |  Lisbon in March     owner   2026-03-14  pass  |
|   ...                [All]    |  Japan, 10 days      owner   2026-04-02  none  |
|                               |  Anna's birthday     guest   2026-01-20  n/a   |
+---------------------------------+------------------------------------------------+
| ACTIONS                                                                          |
| [Grant credits] [Extend pass] [Comp subscription] [Force sign-out]               |
| [Start export]  [Queue deletion] [Hold AI] [Impersonate read-only (asks user)]   |
| Buttons the role may not use are hidden. Limits shown in each dialog.            |
+----------------------------------------------------------------------------------+
| GRANT CREDITS dialog                                                             |
|  Amount [ 20 ]  (your limit 50)   Category [Goodwill v]   Expires in 90 days     |
|  Reason [ Agent run failed twice, ticket 4821                               ]    |
|  Balance after: 58                              [Cancel]  [Grant credits]        |
+----------------------------------------------------------------------------------+
```

## 8. Admin API

Base path `/v1/admin`. All routes require an admin session (section 2). Conventions:

- JSON in and out; money as integer minor units plus `currency`; provider spend in micro-dollars (fields end in `_micros`, for example `cost_usd_micros`); public ids are UUIDv7 (`audit_id` is the bigint `audit_log.id` as a string).
- Lists use cursor pagination (`?limit=50&cursor=...`), filters as query parameters, and return masked data. Detail routes return the same masking unless a reveal is called.
- Every write takes `reason` (10 to 500 characters) in the body and an `Idempotency-Key` header, and returns `{ "result": ..., "audit_id": "..." }`.
- Errors use the shared problem format; 403 includes the missing permission, 409 means a limit or state conflict, 423 means a kill switch or hold blocks the action, 428 means step-up 2FA is required.
- Minimum role is shown; the real check is the permission matrix in section 3.

| Method and path | Purpose | Min role |
|---|---|---|
| `GET /auth/session` | Current admin, role, permissions, 2FA freshness | any |
| `POST /auth/stepup` | Verify a fresh WebAuthn or TOTP challenge | any |
| `GET /admin-users` | List admins | owner |
| `POST /admin-users` | Invite an admin with a role | owner |
| `PATCH /admin-users/{id}` | Change role or status (disable) | owner |
| `GET /overview` | All dashboard tiles, filters as params | support |
| `GET /alerts` | Open and recent alerts | engineer |
| `POST /alerts/{id}/ack` | Acknowledge or snooze | engineer |
| `GET /users` | Search and list (masked) | support |
| `GET /users/{id}` | Profile summary | support |
| `GET /users/{id}/trips` | Trips and roles | support |
| `GET /users/{id}/entitlements` | Entitlements, subscriptions, passes | support |
| `GET /users/{id}/credits` | Balance buckets, ledger, spend vs ceiling | support |
| `GET /users/{id}/devices` | Devices (no tokens) | support |
| `GET /users/{id}/tickets` | Linked support tickets | support |
| `GET /users/{id}/privacy` | Exports, deletions, consents | support |
| `POST /users/{id}/reveal` | Reveal email or name (audited) | support |
| `POST /users/{id}/credits/grant` | Grant credits | support |
| `POST /users/{id}/passes/{pass_id}/extend` | Extend a trip pass | support |
| `POST /users/{id}/comp` | Comp a subscription | engineer |
| `POST /users/{id}/sign-out` | Force sign-out | support |
| `POST /users/{id}/export` | Start a data export | support |
| `POST /users/{id}/deletion` | Queue a deletion request | support |
| `POST /users/{id}/deletion/process` | Process deletion now | owner |
| `POST /users/{id}/ai-hold` | Set or release a per-user AI hold (`kill_switches` key `user:<id>`) | engineer |
| `POST /users/{id}/impersonation/request` | Ask the user for consent | support |
| `GET /impersonation/{id}` | Request status | support |
| `POST /impersonation/{id}/start` | Mint the read-only token after consent | support |
| `POST /impersonation/{id}/end` | End the session | support |
| `GET /subscriptions` | Subscriptions list with filters | finance |
| `GET /store-transactions` | Store transactions list | finance |
| `GET /revenuecat/status` | Sync status, lag, reconcile result | engineer |
| `POST /revenuecat/reconcile` | Run reconcile for a user or all | engineer |
| `GET /webhook-events` | Webhook events, failed filter, backlog | engineer |
| `POST /webhook-events/replay` | Replay selected events (max 100), dry run flag | engineer |
| `POST /refunds/stripe` | Refund a Stripe payment | finance |
| `GET /ai-spend/summary` | Spend by day, feature, model, tier | finance |
| `GET /ai-spend/top-spenders` | Top users by spend | engineer |
| `GET /ai-spend/ceiling-hits` | Ceiling hit list | engineer |
| `GET /ai-spend/runaways` | Runaway detection results | engineer |
| `GET /runs` | Runs list, live filter | engineer |
| `GET /runs/{id}` | Run events (no prompt text) | engineer |
| `POST /runs/{id}/cancel` | Cancel a run | support |
| `GET /kill-switches` | All switches, state, history | support |
| `PUT /kill-switches/{key}` | Set or clear with expiry | engineer |
| `GET /flags` | Flags, experiments, settings list | support |
| `POST /flags` | Create a flag or experiment | engineer |
| `PATCH /flags/{key}` | Change rollout, rules, state | engineer |
| `GET /experiments/{key}/results` | Variant results and guardrails | engineer |
| `POST /experiments/{key}/conclude` | Stop and pick a winner | engineer |
| `GET /affiliate/summary` | Revenue, clicks, EPC by dimension | finance |
| `GET /affiliate/programs` | Programs and templates | engineer |
| `PUT /affiliate/templates/{id}` | Propose a template change | engineer |
| `POST /affiliate/templates/{id}/approve` | Second admin approves | owner |
| `GET /affiliate/imports` | Conversion import status | finance |
| `POST /affiliate/imports/run` | Re-run an import for a date range | engineer |
| `POST /affiliate/link-check` | Run the link checker | engineer |
| `GET /affiliate/disclosure-audit` | Disclosure audit results | content |
| `POST /affiliate/payouts` | Record a payout received (`affiliate_payouts` row) | finance |
| `GET /concierge` | Concierge requests | support |
| `PATCH /concierge/{id}` | Assign, change status, notes | support |
| `POST /concierge/{id}/commission` | Record commission | finance |
| `GET /settlements` | Settlements with Stripe status | finance |
| `GET /disputes` | Open disputes | finance |
| `POST /disputes/{id}/notes` | Add evidence notes | finance |
| `GET /guides` | Partner guides list | content |
| `POST /guides` | Create a draft | content |
| `PUT /guides/{id}` | Edit a draft | content |
| `POST /guides/{id}/submit` | Submit for review | content |
| `POST /guides/{id}/review` | Approve or request changes | owner |
| `POST /guides/{id}/publish` | Publish or pause | owner |
| `GET /tickets` | Support inbox | support |
| `GET /tickets/{id}` | Thread and user card | support |
| `POST /tickets/{id}/reply` | Reply with optional macro | support |
| `PATCH /tickets/{id}` | Status, `assigned_admin_id`, priority, `tags`, link user | support |
| `GET /macros` | Macro list (read only, from the repo) | support |
| `GET /moderation/queue` | Reported shared trips and AI reports | content |
| `POST /moderation/{id}/action` | Dismiss, hide, disable link (`revoked_at`), flag (`stale_until`), warn, escalate | content |
| `GET /providers/health` | Per provider metrics and quota | engineer |
| `POST /providers/{name}/probe` | Synthetic probe | engineer |
| `GET /system/queues` | Lane depth, oldest age, scheduler | engineer |
| `GET /system/jobs` | Job failures and dead letters | engineer |
| `POST /system/jobs/retry` | Retry jobs (max 200) | engineer |
| `GET /system/deploys` | Recent deploys and migration head | engineer |
| `GET /finance/monthly` | Revenue, fees, cost, margin by month | finance |
| `POST /finance/export` | Create a CSV export (audited) | finance |
| `PUT /finance/costs/{month}` | Enter or correct manual costs | finance |
| `POST /finance/months/{month}/lock` | Lock or unlock a month | finance |
| `GET /settings` | All settings with bounds | finance |
| `PUT /settings/{key}` | Change a setting | engineer |
| `GET /settings/{key}/history` | Change history from `audit_log` | finance |
| `GET /audit` | Audit list with filters | support |
| `GET /audit/{id}` | One row, raw JSON for owner | support |

## 9. Security rules

1. **Network gate.** Cloudflare Access with an IP allowlist (founder's fixed addresses or a WARP device posture check) in front of the host and path. The origin accepts admin traffic only from Cloudflare (authenticated origin pulls). A request that reaches the origin without a valid Access JWT is dropped and alerted.
2. **Separate identity.** Admin sessions are not customer sessions; different token audience (`hermi-admin`), different cookie scope, different code path, separate rate limit bucket.
3. **Least privilege in the database.** Admin routes use the database role `hermi_admin` (03 section 6.1, `BYPASSRLS`, used by the admin console only). The grants in 03 give it all DML on every table before that block narrows them; the narrowing this section wants (`INSERT` and `SELECT` only on `audit_log`, no `DELETE` on money tables such as `credit_ledger` and `store_transactions`) is the `REVOKE` block at the end of 03 section 6.1. `hermi_app` cannot read `audit_log` or `admin_users`.
4. **No raw PII in lists.** Masking is done in the API serializer, not the UI, so a raw response never carries it. Emails are searchable only by hash. Reveal is per record, reasoned, rate limited and audited. No passport, document, payment card or note text is ever exposed. Logs and Sentry events from admin routes are scrubbed of masked fields.
5. **Rate limits** (per admin, Postgres token bucket plus a Cloudflare rule): 120 requests a minute on reads, 20 a minute on writes, 5 a minute on `X` actions, 30 reveals an hour, 5 exports an hour, 10 step-up attempts an hour with lockout and alert.
6. **Step-up and confirmation** on every money, destructive, reveal and control action (section 2.2); typed confirmation on `X` actions.
7. **Web hardening.** Strict CSP with no third-party scripts (no analytics, no session replay and no PostHog in the admin bundle), `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, CSRF token on every write, `SameSite=Strict`, Subresource Integrity for any CDN asset, and dependency pinning.
8. **Exports.** CSV files contain no emails or names, carry a watermark row (admin id, time), download from short-lived signed R2 URLs (15 minutes), and expire after 24 hours.
9. **Anomaly alerts** to the owner: admin login from a new country, more than 20 reveals in an hour, 3 or more denied actions, a role change, a kill switch set outside business hours, a CSV export by a non-owner, an impersonation without a ticket id.
10. **Secrets.** The console holds no provider secrets; the API calls providers with its own keys. Admin actions that call RevenueCat, Stripe or Supabase use scoped service keys kept in environment variables only.
11. **Review.** The owner reviews `admin_users` and the last 30 days of high-risk audit actions every quarter; a penetration test covers admin before public launch.
12. **Staging is not production.** Staging has its own Cloudflare Access application, its own `admin_users`, synthetic data, and sandbox keys. There is no path from staging to production data.

## 10. Alert rules

Alerts are evaluated by a scheduled job every minute (spend and health) or every 15 minutes (business). Each alert has a severity (page, notify, info) and appears on the Overview. Page-level alerts phone the owner; the rest go to the on-call channel.

| Rule | Severity |
|---|---|
| Daily global AI spend above 80 percent of budget, then 95 percent | notify, then page (and the breakers act) |
| Daily global AI spend above 1.5 times the trailing 7-day mean | page |
| Any run past 20 turns, 8 minutes or its dollar stop | page |
| Any account above its daily ceiling by more than 10 percent (ledger bug signal) | page |
| Cost per active payer above $2 (Plus) or $6 (Pro) | notify |
| Shared research cache hit rate down more than 20 points; prompt cache read ratio under 70 percent | notify |
| Anthropic 429 or overloaded above 5 percent for 10 minutes | notify |
| SerpApi quota under 10 percent or Geoapify credits under 20 percent | notify |
| Webhook backlog older than 10 minutes, or RevenueCat lag p95 above 5 minutes | page |
| Entitlement mismatches found by reconcile above 0 | notify |
| Conversion import failed or unmatched share above 10 percent | notify |
| Redirect `/go` 4xx or 5xx above 1 percent; clicks down more than 50 percent day over day | notify |
| Queue oldest job above 10 minutes, scheduler idle over 3 minutes | page |
| Moderation report older than 12 hours | notify |
| Support ticket past SLA; concierge request past 1 business day | notify |
| Stripe dispute due within 3 days | notify |
| Kill switch expiring in 15 minutes | info to owner |

## 11. Build order and tests

Staged so spend control is never late. Ticket details are in [09-build-roadmap.md](09-build-roadmap.md).

| Phase | Screens | Tickets |
|---|---|---|
| 1 hosted web beta | Access and sign-in, audit log, overview, users (read and actions), impersonation, kill switches, credits and AI spend | WF-056 to WF-063 |
| 2 iOS TestFlight | Subscriptions and webhook replay | WF-079 |
| 3 public launch | Support inbox, moderation, flags and experiments, provider and system health, affiliate, finance and settings | WF-091 to WF-095 |
| 4 growth | Concierge, group payments (Stripe collection), partner guides editor, advisor admin | WF-103, WF-106, WF-108 |

Tests required for the console as a whole:

- Every `/v1/admin` route is covered by a permission; a role x route matrix test confirms each role gets 200 or 403 as the table says.
- Every write produces exactly one `audit_log` row with correct before and after; a failed action leaves no partial write and a `denied` or `error` row.
- Limits (grant caps, extension caps, refund caps, settings bounds) reject over-limit requests.
- Customer tokens are rejected on `/v1/admin`; admin sessions are rejected elsewhere; disabled admins lose access within 60 seconds.
- Impersonation tokens cannot perform any non-GET request and expire after 15 minutes.
- Kill switches are read with the fail-closed default; expiry clears a switch and logs a `system` row.
- No list endpoint response contains a raw email or name (a serializer test scans for the patterns).
- A test fails the build if any ranking or ordering code for affiliate placements reads payout or commission fields.
