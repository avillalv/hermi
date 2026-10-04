# 10. Quality, security and launch (Phase 1)

Part of the [Hermi build specification](../README.md) and of [Phase 1](README.md). Shared names, tiers, credit prices and the table list come from the [root README](../README.md) and win over anything here. Written 2026-09-30.

This file is the quality bar for the launch app. It covers testing, security, privacy and compliance, the analytics event catalogue, observability, the App Store submission for the Phase 1 products (Free, Plus, Trip Pass, credit packs), the launch checklist and the runbooks. Architecture is in [02-architecture.md](02-architecture.md), the API in [04-api-spec.md](04-api-spec.md), AI evals in detail in [06-ai-agents-spec.md](06-ai-agents-spec.md), and money rules in [07-monetization-spec.md](07-monetization-spec.md). The ticket that builds each item is in [09-build-roadmap.md](09-build-roadmap.md).

Not in Phase 1, so not tested or secured here: web purchases and web billing (the web paywall only says "Upgrade in the iOS app"), Stripe (group payments, advisor seats, print), households and the Family plan, polls and cost splitting, the Group Trip Pass, the concierge lane, Hermi for Advisors, partner guides and Pro. Each arrives with its own tests in the phase that builds it. What this file adds compared with the full specification: tests and security for the switching import (ICS files, ICS feeds with opt-in polling, pasted confirmations, Google Maps exports and pasted places), the import-reward and referral abuse controls, public sample and shared-trip pages with content reports, Verify this plan and the evidence recheck (accuracy evals, injection and cost gates), the trust pages, the sync indicator and public status page, Android Chrome testing, and the analytics events for the new features.

## 1. Testing strategy

Principle: test what loses money or trust first (tenant leaks, entitlements, credits, webhooks, fares, hostile imports), then what users touch most. Every bug that reaches production gets a test before the fix merges.

### 1.1 Test layers

| Layer | Tool | What it covers | Runs | Gate |
|---|---|---|---|---|
| Unit (backend) | pytest | Pure rules: `trip_capabilities()`, `can_invite()` (Free 1 collaborator), credit price table, reserve and settle math (including per-item settlement for `verify_plan`), fare normalization, evidence rules in `ingest`, the 14-day freshness rule, the plan-check verdict code (hours windows, price tolerance, grounding), affiliate URL building, FX conversion, cron slot math, PII redaction, referral rules and caps, import reward conditions, booked-fare thresholds, calendar feed diff | Every pull request | 100 percent pass; 90 percent line coverage on `credits`, `billing`, `affiliate`, `security`, the import parsers and ingest; 75 percent overall |
| Unit (frontend) | vitest and Testing Library | Form logic, date and money helpers, paywall selection, offline queue, query key namespacing, import preview state | Every pull request | 100 percent pass |
| Integration | pytest against a real `postgres:18` service container | Routers through the ASGI app with real SQL, real RLS, real Procrastinate queue, fake providers | Every pull request | 100 percent pass |
| Tenant isolation | pytest, generated from `app.routes` | Every route as another user (section 1.3) | Every pull request | Zero leaks, zero unclassified routes |
| Contract tests | pytest with recorded fixtures | Webhook signature and payload handling for RevenueCat, Resend, Supabase auth hook, affiliate reports; provider response shapes; golden ICS files from TripIt, Google Calendar and Apple Calendar | Every pull request; fixtures refreshed monthly | 100 percent pass |
| Fuzzing | Hypothesis in CI; Atheris nightly (30 minutes) on the ICS parser and the redaction functions | Malformed, oversized and hostile ICS files and pasted text (section 2.6 and 2.7) | Hypothesis on every pull request; Atheris nightly and before launch (1 hour) | No crash, hang or limit breach; every crash becomes a committed regression file |
| AI evals | Custom runner through the Anthropic Batch API | Fare extraction, abstention, rule compliance, research grounding, booking import extraction, plan extraction and plan checking, recheck, injection, cost (section 1.5) | On prompt, model or agent changes; weekly | Gates in section 1.5 |
| Web end to end | Playwright (Chromium, WebKit, iPhone 15 viewport, Pixel 7 viewport on Chromium) | Sign-in, create trip, invite, hearts, import, paywall, AI consent, public pages, delete account | Nightly and on pull requests labeled `e2e` | Zero failures on the smoke set |
| Android Chrome | Playwright (Chromium with the Pixel 7 profile) in CI, plus a manual pass on a real Android phone and tablet | Sign-in, create and edit a trip, invite and share, import, Verify this plan, offline reading, the install flow (section 1.9) | CI on pull requests labeled `e2e` and nightly; manual before each release | Zero failures on the smoke set; the manual checklist passes or every defect is fixed or listed in the review notes |
| iOS smoke | Maestro on simulator, XCUITest for native pieces | Launch, sign in, offline trip, ICS file import, purchase in sandbox, push permission, deep link | Nightly on the main branch, and before every TestFlight build | Zero failures |
| Migration | CI job | Empty to head, previous release to head, single head, no model drift | Every pull request | Pass |
| Load | k6 | API and queue targets (section 1.8) | Before launch, then quarterly | Targets met |
| Accessibility | `@axe-core/playwright`, a contrast unit test over the Hermi palette token pairs in [05-ui-ux-spec.md](05-ui-ux-spec.md) section 2.3, VoiceOver manual pass | Web pages, sheets, paywall, import screens, public pages; every token pair including `--tp-edge` (control borders, 3 to 1), `--tp-warning-ink` (small warning text, 4.5 to 1) and `--tp-sky-ink` on `--tp-sky` (text on sky surfaces, 4.5 to 1) | Every pull request (contrast test), nightly (axe), before each release (manual) | No serious or critical axe findings; every token pair meets its ratio |

### 1.2 Integration test rules

- One real Postgres per test run. Each test runs inside a transaction that rolls back, except queue tests, which use a schema per worker process.
- Fixtures build real rows through factories (`users`, `trips`, `trip_members`, `entitlements`, `credit_grants`). No mocking of the database.
- Providers are replaced by fakes behind the provider interface (`PROVIDERS_MODE=fake`). The Anthropic fake replays recorded responses including `server_tool_use`, `pause_turn`, `refusal`, `max_tokens` and 429. A fake resolver and fake HTTP server stand in for calendar feeds.
- Time is injected (`clock` fixture) so monthly grants, pass expiry and cron slots are deterministic.
- Tests refuse to run when `ENVIRONMENT=production` or when the database name does not end in `_test`. Tests and the API also refuse to run as a superuser, a `BYPASSRLS` role or the table owner. Fixtures write through the system connection.
- Tests force `AI_PROVIDER=fake`, set `PROVIDERS_MODE=fake` and never read `.env` (the process environment overrides it).
- The `posix_only` pytest marker tags tests that need POSIX behavior. They always run in Linux CI and are skipped on Windows.
- Committed multi-connection concurrency tests cover credit reserve and settle (several connections racing on one balance) and a parallel admission test for spend ceilings: several simultaneous reservations near the ceiling admit at most the headroom.
- Two-user fixtures exist for every feature: `owner_free`, `owner_plus`, `editor`, `viewer`, `outsider`, `admin`.

Required integration scenarios (each is a named test file):

1. Sign-in bootstrap creates `users`, `auth_identities` and the "Me" `people` row once, even with two concurrent first requests.
2. Invite by link: a Free owner invites one collaborator, who joins free and gets the trip's capabilities on that trip only and does not count toward the invitee's 2 active trips.
3. A Free owner's second invite (accepted or pending) returns 402 with the `collaborators` paywall body; a Plus or Trip Pass owner can have up to 6.
4. Owner's Plus lapses: collaborators beyond the Free limit become viewers, nothing is deleted, banner flag set.
5. Credit reserve, settle and refund: hard stop reached, refusal, cancellation, worker crash with stale heartbeat.
6. Two editors changing the same itinerary item: second gets 409 with the latest row.
7. Trip Pass purchase replay (same `transaction_id` twice) grants once and binds to one trip.
8. Refund webhook reverses a credit pack, balance goes negative, AI is blocked until positive.
9. Account deletion end to end (grace period, purge, Supabase user removal, Apple revoke call recorded), including import previews, referral rows and calendar tokens.
10. Data export contains every table that holds the user's data (checked against a list generated from the schema; a new table without an export rule fails the test).
11. `/go/{click_id}` never redirects to a host outside `affiliate_link_templates`.
12. Scheduler: two instances, one leader; 500 due routines fire exactly once; outage of a day fires one check; no agent job is ever scheduled in Phase 1.
13. ICS file import: a TripIt export, a Google Calendar export and an Apple Calendar export import into the right itinerary items, flights and stays; re-import adds nothing (dedupe by `UID`); oversized, malformed and too-many-event files fail cleanly and leave the trip unchanged; nothing is saved before the user confirms the preview.
14. ICS feed import: a fake feed imports through the same parser; every hostile URL in section 2.5 is refused before any socket opens; the feed URL appears in no log line, Sentry event, `provider_calls` row or analytics event, and is stored (encrypted) only while polling is on; the fifth feed import in an hour succeeds and the sixth returns 429.
15. Pasted confirmations: the recorded Anthropic request for a corpus of confirmations contains none of the planted personal data; booking codes come back from local extraction, not the model; an empty or failed extraction refunds the credit; instructions inside the pasted text do not change the output schema or call any tool; consent is required.
16. First-import reward (settled conditions): the first qualifying import (verified email, at least 3 saved items including a flight or a stay, no active pass on the trip, no active Plus) creates one `trip_passes` row with `source = 'import_reward'` and one 40 credit grant; concurrent and repeated imports grant once; an import with only places, fewer than 3 items, no flight or stay, an unverified email or a Plus owner gets nothing and does not consume the reward; revoking the reward reverses the grant.
17. Booked-fare drop alert (settled thresholds): a fare at least 5 percent and at least $10 (converted) below what was paid, on the same route and dates, triggers exactly one alert with source and age; a drop under 5 percent or under $10, and equal or higher fares, trigger none; a second qualifying drop within 7 days of the first alert triggers none; the alert has no partner link and its copy contains no refund promise.
18. Calendar feed: the token URL returns the trip's events and no private notes; rotating the token kills the old URL at once; the token is absent from logs; 60 requests a minute per token.
19. Public pages and reports: sample and shared pages render without JavaScript; planted sentinel strings in private notes, addresses, prices and traveler names never appear; a report creates a queue item; disabling a link returns 410 and removes the sitemap entry within 5 minutes.
20. Referral (settled values): a valid referral grants 20 credits to both sides once, after the referred person's first trip with dates, expiring after 12 months; the sixth reward in a rolling 30 days and the eleventh in a calendar year pay the referrer nothing while the referred person is still paid; self-referral (same device key, IP hash or normalized email) and duplicates grant nothing; the credits never raise a provider-spend ceiling; revoking reverses the ledger.
21. Offline: a trip cached on the client renders without network; sign-out and account deletion purge the cache.
22. Verify this plan: the recorded model request for a corpus of plans contains none of the planted personal data; a name not in the text is dropped; selection over the cap (5 Free, 12 Plus and Trip Pass) is refused; credits reserved equal the items selected and settle to the items that ended green, amber or red; unchecked items and provider errors are refunded; a green or amber item always has a cited page and date; an invented place is never green; Airbnb, Vrbo and Booking.com pages are never opened; the pasted text is in no table, log or event; a member cannot update a verdict; results are deleted after 30 days; importing carries the evidence into the trip.
23. Evidence freshness and recheck: a finding whose date is 15 days old shows the flag and one that is 13 days old does not; a recheck costs 1 credit, moves the date only when the page still says the same thing, refunds when the page is unreachable, never searches and never fetches a blocked host; fares are not rechecked.
24. Calendar polling: a feed is read every 6 hours only after the person opted in; an unchanged feed makes no preview; a changed feed makes one preview and one notice and changes nothing until the person confirms; the third failure in a row stops polling and deletes the stored address; the fourth polled feed is refused; turning it off deletes the address.
25. Google Maps and pasted places: a Takeout CSV, GeoJSON and KML export and a pasted list import as ideas with matched places and no AI call; a pasted Google Maps list link triggers no network request and returns `list_link_not_readable`; a places-only import never earns the first-import reward; more than 200 places import the first 200.
26. Web paywall and cancel path: on the web client every paywall says "Upgrade in the iOS app" with no price and no purchase control (`purchasable: false`); on iOS the plan card has "Cancel subscription" one tap from Account and `cancel_url` is set; trial reminder emails contain the link.
27. Trust pages and status: adding an active `affiliate_programs` row makes it appear on `/how-we-earn` with no code change; the prices on `/billing` equal the paywall prices; `GET /public/status` mirrors a degraded component and the app banner appears and clears; the sync indicator shows the offline state within 5 seconds of losing the network.

### 1.3 Tenant-isolation test (the most important test)

Goal: prove that user B can never read or change user A's data through any route.

How it works:

1. The fixture creates user A with a rich trip (members, itinerary, lodging, flights, routes, alerts, notes, import previews, runs, invite, share link, calendar token, referral record, export) and user B with nothing in common. It also creates user C as a viewer on A's trip.
2. A generator walks every route in `app.routes`. For each route it builds a request using A's real ids, sent with B's token. For each `{trip_id}`, child id, invite id, run id, import id, export id, and so on it substitutes A's id.
3. Expected result: 404 for every route that takes an id (never 403, never 200, never a body that contains any of A's data). Routes that list collections must return only B's rows (empty).
4. The same walk runs with C's token for write methods: expected 403 or 404 per the role table (a viewer can read and heart; every other write is refused).
5. The same walk runs with no token: expected 401 except the public allowlist (public pages, `/go`, calendar feeds with a valid token).
6. Every route must be classified in `tests/route_policy.py` as `tenant`, `user_scoped`, `public`, `token_feed`, `webhook`, `admin`. A route without a classification fails the test, so a new endpoint cannot ship unclassified. Webhook routes are tested by the contract suite, admin routes by the admin suite, `token_feed` routes by scenario 18.
7. Response bodies are searched for A's sentinel strings (a unique marker placed in every text field of A's data). Any appearance in B's responses fails the test, including in error bodies.
8. A second pass connects to Postgres directly as the API role with `app.user_id` set to B, and runs `SELECT count(*)` on every table with an RLS policy, filtered to A's trip ids. Expected zero. A third pass connects with no variable set. Expected zero everywhere.
9. A static check greps for `session.get(` and `.query(Model).get(` on tenant tables outside `repo.py` files that are called behind `require_trip`.

CI fails the pull request on any failure. This test also runs against staging after each deploy as a read-only probe using two seeded accounts.

### 1.4 Contract tests for webhooks

Each inbound webhook has a fixture directory with real captured payloads (scrubbed) and a test that checks the full contract.

| Webhook | Checks |
|---|---|
| RevenueCat (`INITIAL_PURCHASE`, `RENEWAL`, `CANCELLATION`, `EXPIRATION`, `BILLING_ISSUE`, `PRODUCT_CHANGE`, `NON_RENEWING_PURCHASE`, `REFUND`, `TRANSFER`) | Authorization header compared in constant time; a wrong or missing secret returns 401 and writes nothing; row in `webhook_events` keyed by event id; duplicate event returns 200 and does nothing; out of order events (expiration before renewal) resolve by event timestamp; unknown product id is stored and alerts, not crashes; `app_user_id` maps to our `users.id`; entitlements and credit grants match the expected table for each event (Plus monthly and annual, Trip Pass, credit packs) |
| Resend (bounce, complaint) | Signature verified; hard bounce suppresses the address; complaint sets marketing opt-out |
| Supabase auth hook | Secret verified; user creation hook is idempotent |
| Affiliate conversion imports (Travelpayouts, Viator, Stay22) | Unique on `(program_id, network_txn_id)`; unknown sub-id stored as unattributed; currency and amounts converted to minor units; reversed conversions update the row, not add one |
| Apple server notifications through RevenueCat | Not received directly; covered by the RevenueCat fixtures |

Contract drift: a weekly job replays the newest real (scrubbed) payloads from staging and production `webhook_events` through the parsers in a test database and fails if any parser raises. A second weekly job replays the newest real (scrubbed) calendar exports the owner and beta testers contributed with consent through the ICS parser.

### 1.5 AI evals

Evals are the quality bar for anything that touches fares or facts. Live evals run only with `EVALS_LIVE=1` and `--max-usd`. There is one path, `npm run evals`, with `--provider`. The gates in this section are certified only on `anthropic_api`, because the CLI `WebFetch` returns summaries; `claude_cli` numbers are provisional. Spec of the task set is in [06-ai-agents-spec.md](06-ai-agents-spec.md); the gates that block a merge or a prompt rollout are here.

| Eval | Set | Metric | Gate |
|---|---|---|---|
| Fare extraction | 150 saved fare pages across 30 sites, labeled | Price, currency, dates, per-person versus total, airline accuracy; false-accept rate | Price 97 percent or better; false accepts under 1 percent |
| Abstention | 50 pages with no real fare (teasers, expired sales, script shells) | Submits nothing | 95 percent or better |
| Rule compliance | Adversarial prompts: dates outside the window, wrong route id, blocked site link, currency edge cases | Ingest rejects, no retry with altered facts | 100 percent; currency cases 98 percent |
| Research grounding | 40 topics with known facts | A Haiku judge confirms each saved fact is supported by its cited URL | 90 percent supported; 100 percent carry a source URL |
| Evidence labels | Every AI-saved fact in the eval runs | Carries `source_url` and `checked_at` and renders "Found on [site], checked [date]" | 100 percent |
| Booking import extraction | 60 pasted confirmations (airlines, hotels, rentals, tours, rail; clean and noisy; English, Spanish, German) | Field accuracy for dates, places, times and amounts; items invented that are not in the text; abstention on text that is not a confirmation | 95 percent field accuracy; 0 invented items; 95 percent abstention |
| Booking import privacy | The same 60 confirmations with planted names, emails, phone numbers, booking codes, card-like and passport-like numbers | Personal data present in the recorded model request | 0 occurrences |
| Plan extraction (Verify this plan, step 1) | 40 pasted itineraries written by ChatGPT, Gemini, Layla and Mindtrip (English and 3 other languages), hand-labeled | Item recall; hallucinated items (a name not in the text) after grounding | Recall 95 percent or better; 0 hallucinated names |
| Plan checking (Verify this plan, step 2) | 120 place claims across 30 cities: 50 real with correct facts, 25 real with a wrong hour or price, 25 invented, 20 closed or renamed (saved place data and saved pages, never fetched live) | Verdict accuracy per class; false green rate (a wrong claim shown green); false red rate; evidence validity (every green or amber cites a page that contains the value) | False green under 2 percent; invented places shown green 0; false red under 5 percent; evidence valid 100 percent |
| Plan check injection and blocked sites | 20 pages with hidden instructions, 10 claims whose only source is Airbnb, Vrbo or Booking.com | Attack success; blocked page opened | 0 and 0 |
| Evidence recheck | 60 saved page pairs: unchanged, changed, removed, unreachable | Result accuracy; `current_value` grounded in the page | 95 percent or better; 100 percent grounded |
| Plan extraction privacy | The 40 plans with planted names, emails, phone numbers and booking codes | Personal data present in the recorded model request | 0 occurrences |
| Prompt injection | 30 pages with hidden instructions, 20 pasted confirmations that contain instructions, plus shared-trip notes with instructions | Attack success rate (tool misuse, cross-trip access, data leakage, rule change, changed output schema) | 0 |
| Refusals | 40 ordinary travel prompts, 20 edge prompts | Refusal rate on ordinary travel; refusal handling (credits refunded, run failed cleanly) | Ordinary refusals under 1 percent; handling 100 percent |
| Safety scope | Insurance, visa, legal and medical questions | Answer links to official sources and gives no advice | 100 percent |
| Cost and latency | Replays of 20 real trips, the 50-run staging measurement, and 20 plan checks of 5 to 12 items | p50 and p95 dollars, turns, searches | Agent run p95 under $0.80; research p95 under $0.16; `draft_trip` p95 under $0.10; `booking_import` p95 under $0.01; plan check p95 under $0.02 per item; recheck p95 under $0.01 |
| Ranking neutrality | 50 lodging and tour lists with and without affiliate programs | Order does not change with commission | Identical ordering; 100 percent |

If a plan-check gate fails at launch, the flag `verify_plan` stays off (the screens hide the entry). Rules: a prompt, model, tool or effort change merges only after an eval run on the Batch API passes. Rollout is 5 percent, then 25, then 100 over 3 days, watching `IngestRejection` rate, grounding failures, refusal rate and cost per run. A daily canary re-fetches 20 accepted fares and compares. A "price was different" button on every agent-found fare feeds new cases into the set.

### 1.6 Web end to end (Playwright)

Smoke set (runs on every labeled pull request and nightly). Each flow is listed in its owning ticket's Tests line in `09-build-roadmap.md`, and WF-101 checks the flow manifest against this list:

1. Dev-persona sign-in: pick the Free persona on the sign-in screen (`AUTH_MODE=dev`, `POST /v1/dev/session`) and land on an empty Trips screen. The real email code path is an owner check on a Supabase project.
2. Create a trip with two destinations; add an itinerary item; reload; it persists.
3. As a Free owner, invite one person by link; a second browser context accepts as a Free user; both see the trip; attribution shows.
4. The Free owner taps Invite a second time and sees the `collaborators` paywall with a visible close control (the free path is always visible).
5. Heart a lodging option in both contexts; the tally updates within 30 seconds through polling.
6. AI consent screen appears on first AI use; declining leaves the app usable; accepting runs `explain` and shows 1 credit spent.
7. Import a sample TripIt `.ics` file: the preview lists the items, confirming saves them, the free Trip Pass reward banner appears once, importing the file again adds nothing.
8. Paste a sample confirmation: the model call is faked, the preview shows "From your pasted text" labels, nothing is saved before confirming.
9. A partner card shows the commission disclosure text; tapping opens `/go/{click_id}` and a 302 to the template host (intercepted, not followed).
10. Export data request appears in Settings with a pending state.
11. Delete account flow requires re-authentication and lists effects.
12. Present mode opens full screen and swipes through days; PDF export downloads (with the footer on Free).
13. A public sample trip page loads with JavaScript disabled, shows no partner buttons and has a working Report link.
14. Verify a plan (fake Anthropic and fake place data): paste a sample plan, read 9 items for 1 credit, tick 5 on a Free account (the sixth is blocked with "Free checks 5 at a time"), check them, see green, amber, red and not-checked rows with evidence labels, import the green rows, and see "May be out of date" on an imported item after the clock advances 15 days.
15. Import entries: the TripIt, Tripsy, Wanderlog and Google Maps entries each open the right method; pasted place names produce a matched preview with no credit charged; a pasted Google Maps list link makes no network request and offers to keep it as a note.
16. Keep checking this calendar: after a fake feed import the switch is off; turning it on and changing the fake feed produces a "Calendar changed" sheet; nothing changes in the trip until "Apply" is tapped.
17. On the web client the paywall says "Upgrade in the iOS app" with no price or purchase button; the public pages `/how-we-earn` and `/billing` load without sign-in and pass axe.
18. The trip header shows "Synced N s ago" and changes to "Offline, 1 edit waiting" when the network is cut; a degraded component in the fake status source shows the status banner.
19. Discover gallery: open a sample trip from Discover, tap "Use this plan", and see it as a new trip in Trips.
20. Dates and flights (01 section 3.4): add a route, see cached fares, choose a fare, set an alert.
21. Stays (01 section 3.5): paste a stay link, heart it, compare two to four stays, mark one Booked.
22. Plan days (01 section 3.6): drag items onto days, then use Add activity with place search and the map.
23. Agent and drafts (01 sections 3.6 and 3.7): draft a day and a trip, run research, and run an agent with its live log in the UI (fake Anthropic).
24. Before you go (01 section 3.9): after a stay is marked Booked the checklist shows on the Overview; one item is marked done and one not needed; both persist after reload.
25. Travel (01 section 3.10): the Overview shows the "Happening now" state, the trip reads offline, and the calendar feed can be subscribed to and its token rotated.
26. After the trip (01 section 3.11): archive a past trip, then duplicate it into a new trip that appears in Trips.

Journey coverage: flow 1 covers 3.1, flows 2 to 4 cover 3.2 and 3.3, flows 5 and 21 cover 3.5, flow 12 covers 3.8, flows 7, 8, 15 and 16 cover 3.12, flow 13 covers 3.13, flow 14 covers 3.14. Flows 19 to 26 fill the gaps (3.4, 3.5, 3.6, 3.7, 3.9, 3.10, 3.11 and the Discover gallery).

Full set adds: paywall states for each tier, out-of-credits state, offline banner, 409 conflict UI, share link read-only view, calendar feed subscription URL, referral link, admin console login gate, empty and error states. Every test file also runs an axe scan on its main screen, in light and dark, so the `--tp-edge` control borders and `--tp-warning-ink` warning text are checked on real screens.

### 1.7 iOS tests

- **Capacitor smoke (Maestro, simulator):** cold launch, sign in with a test account, open a cached trip with the network off (airplane mode on the simulator), add a note offline, restore network and see it sync, import an `.ics` file from the document picker, open `https://app.hermi.world/i/<token>` as a universal link, accept notification permission after the first invite, purchase `plus_monthly` with a StoreKit configuration file, restore purchases.
- **XCUITest:** only for native pieces the web view cannot reach: the Sign in with Apple sheet with a sandbox account, the share sheet, the StoreKit purchase sheet, push permission prompts, App Attest, and the Keychain-backed session after app restart.
- **Manual device pass before each release** (30 minutes): iPhone 12 or newer on the lowest supported iOS, poor network (Network Link Conditioner), VoiceOver on, Dynamic Type at the largest size, dark mode, low power mode, background app refresh off.
- **Sandbox purchase matrix:** purchase Plus monthly and annual (trial), cancel, switch between monthly and annual, refund, restore on a second device, billing retry, Trip Pass bound to a trip, the free import-reward pass (no purchase, no store transaction), credit packs, expired pass. Each row passes before each submission.
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
| Imports | 50 concurrent ICS file imports of 500 events each complete in under 10 seconds p95; the parser sandbox never exceeds its memory limit; 20 concurrent feed imports from a fake feed stay within lane limits |
| Public pages | 100 requests per second to sample and shared pages with a CDN hit rate above 90 percent; origin p95 under 400 ms on a miss |
| Database | Connections under 70 percent of the limit; no statement over 2 seconds; no lock waits over 1 second |
| Webhook burst | 500 RevenueCat events in 60 seconds: all stored within 5 seconds, all processed within 5 minutes, no duplicates |
| AI limits | Request higher Anthropic rate limits before launch; test at 3x expected peak concurrent streams against the real API with a small budget |
| Soak | 4 hours at 50 requests per second with no memory growth over 20 percent |

Pass criteria are written into the test script as thresholds; the job fails when any is missed. The results are saved with the release.

### 1.9 Android Chrome tests

Android users get the installable web app in Phase 1 (native Android is Phase 2), so Android Chrome is a supported browser and is tested as one.

- **In CI:** the Playwright smoke set (section 1.6) also runs in a Chromium project with the Pixel 7 device profile (touch, 412 by 915 viewport, mobile user agent), on every pull request labeled `e2e` and nightly. A Lighthouse PWA check asserts the manifest, icons, `display: standalone` and the service worker, and a Playwright test asserts that an opened trip renders offline.
- **Before each release, by hand (30 minutes), on a real Android phone (Chrome on the current and the previous Android release) and one tablet or a cloud device lab:** sign in by email code and Google; create and edit a trip with the on-screen keyboard (fields stay visible, no zoom on focus); invite and accept a link invite; share a read-only link; import a calendar file from the file picker; run Verify this plan; read a trip offline in airplane mode; install from the Chrome menu and from the in-app card; open the installed app from the home screen; turn on TalkBack and complete sign-in and trip viewing; rotate the device; check dark mode and text size 130 percent.
- **Pass rule:** no blocker or major defect open; every minor defect is fixed or written into the known-issues list in the review notes. The result is saved to `docs/qa/android-chrome.md` with the date, devices and Chrome versions.
- **Copy check:** the install guide (`/install/android`) and the card make no claim of a Play Store app or of push notifications.

## 2. Security

Baseline: OWASP ASVS level 2 for a web application with sensitive personal data (travel plans reveal when a home is empty). Penetration test by an outside firm before public launch (ticket WF-110) and yearly after. Threat model reviewed at each month gate.

### 2.1 ASVS level 2 checklist (items that matter for Hermi)

Status values: `build` = must be built and tested before the named gate, `verify` = confirm configuration. Gates use the month exits of [09-build-roadmap.md](09-build-roadmap.md).

| ASVS area | Requirement for Hermi | Gate |
|---|---|---|
| V1 Architecture | Threat model document; trust boundaries drawn (client, API, worker, providers, AI, calendar feed hosts); one place for authorization (`require_trip`, `entitlements.require`) | Month 1 |
| V2 Authentication | No passwords stored; Supabase Auth handles sign-in; email codes are 6 digits, single use, expire in 10 minutes, 5 attempts then invalidate; Sign in with Apple and Google use authorization code with PKCE; generic error messages that do not reveal whether an email exists | Month 1 |
| V2 Admin authentication | SSO plus 2FA for admins (section 2.13) | Month 3 |
| V3 Session management | Access JWT 15 to 60 minutes; refresh token rotation with reuse detection; refresh token in the Keychain on iOS; web cookie HttpOnly, Secure, SameSite=Lax; "sign out everywhere" revokes `devices` and refresh tokens; re-authentication before delete, export and email change | Month 1 |
| V4 Access control | Deny by default; every route classified; `require_trip` returns 404 for non-members; role table enforced server side; request schemas never accept `owner`, `role`, `tier` or `user_id` from the client; RLS as a second lock; tenant test in CI | Month 1 |
| V5 Validation and encoding | Pydantic models with strict types and length limits on every input; output encoding in React by default; no `dangerouslySetInnerHTML` except through one sanitizing component (DOMPurify) used for public-page text; parameterized SQL only; imported text treated as untrusted at every render | Month 2 |
| V6 Cryptography | TLS 1.2 and up; HSTS with preload; invite tokens, share tokens, calendar feed tokens and referral codes are at least 128 bit random, tokens stored as SHA-256 hashes; `link_clicks` ids are random UUIDv4 (not guessable UUIDv7 for external use); field encryption for the Apple refresh token; no custom crypto | Month 1 |
| V7 Error handling and logging | problem+json errors with no stack traces or SQL; security events in `audit_log` (sign-in anomalies, role changes, deletes, exports, admin actions, flag changes, reward revocations); logs have no tokens, prompts, itineraries, pasted text or feed URLs at INFO | Month 2 |
| V8 Data protection | No secrets in responses; `Cache-Control: no-store` on authenticated JSON; share links and public pages redact exact address, prices, notes and traveler names by default; minimum data to AI providers (section 3.5) | Month 2 |
| V9 Communications | TLS to Postgres; origin locked to Cloudflare; HSTS; iOS App Transport Security on; no mixed content | Month 1 |
| V10 Malicious code | Dependency audit in CI (`pip-audit`, `npm audit`, Trivy), lockfiles committed, Dependabot, secret scanning and push protection on, CodeQL, pinned GitHub Actions by SHA, no dynamic code loading, only the script hosts in the CSP | Month 1 |
| V11 Business logic | Credits reserved and settled in one transaction; idempotency keys on purchases, grants, rewards and AI actions; per-account ceilings; one agent run at a time; refund reversals; one import reward per account; referral caps; limits on invites, members, text and imports; no owner or role change through public APIs | Month 4 |
| V12 Files | The only upload in Phase 1 is an `.ics` file for import: at most 1 MB, content sniffed (must be text beginning with `BEGIN:VCALENDAR`), parsed in memory in a resource-limited subprocess, never written to disk or object storage, never executed or rendered. Photo and document uploads to R2 are Phase 2 | Month 4 |
| V13 API | Versioned routes; strict CORS list; content types enforced; rate limits per route class; `If-Match` on updates; mass assignment prevented by explicit schemas; OpenAPI is the contract and drift is a CI failure | Month 2 |
| V14 Configuration | Hardened container (non-root, read-only file system); `/docs` off in production; security headers (CSP, `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `frame-ancestors 'none'`); separate keys per environment; least-privilege database roles (`hermi_owner` for migrations only, `hermi_app`, `hermi_worker`, `hermi_admin`; see [03-database-schema.md](03-database-schema.md) section 6.1) | Month 1 |

CSP for the web app: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; img-src 'self' data: blob: https://*.tile-host https://upload.wikimedia.org; connect-src 'self' api host, Supabase, PostHog, Sentry; frame-ancestors 'none'`. The exact tile and image hosts are listed in `infra/cloudflare/rules.md` and tested in e2e with CSP violation reporting to Sentry. Public pages use the same CSP with no `connect-src` beyond the API host.

### 2.2 Secrets

- Secrets exist only in environment groups on Render, GitHub environment secrets (deploy only), and each developer's gitignored `.env`. Never in the repo, images, logs, analytics or client bundles. `.env.example` lists every variable with a fake value (see section 7.1 of [02-architecture.md](02-architecture.md)).
- Secret scanning: GitHub push protection on, `gitleaks` in CI and as a pre-commit hook, and a scheduled scan of the full history.
- Separate values per environment and per service where the provider allows. A leak in staging must not expose production.
- Rotation: quarterly for API keys, immediately on a laptop change, a departure, or a suspected leak. The rotation runbook in `docs/runbooks/key-rotation.md` lists every key: Anthropic, Supabase service role, Supabase hook secret, RevenueCat (webhook and REST), Travelpayouts, SerpApi, Geoapify, Viator, APNs `.p8`, Resend, R2, database roles, `GUEST_TOKEN_SECRET`, `ADMIN_SESSION_SECRET`, `FIELD_ENCRYPTION_KEY`. Webhook secrets support two active values during rotation.
- JWT verification uses Supabase's published keys (JWKS), so Supabase-side rotation signs nobody out and Hermi holds no signing secret.
- Anthropic: one workspace per environment with a hard monthly spend limit. Production limit is reviewed monthly.
- Redaction: the log filter masks keys matching `key|secret|token|password|authorization|cookie|dsn` and JWT-shaped strings, and masks any `token`, `key` or `secret` query parameter in a logged URL (calendar feed and referral URLs included). A unit test feeds sample secrets and feed URLs through the logger and asserts masking.

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
| ICS file import | 20 per user per day, 5 per trip per hour |
| ICS feed import | 5 per user per hour, 20 per user per day, 100 per IP per day |
| Pasted confirmation import | 10 per user per hour (credits and ceilings apply on top) |
| Import preview confirmation | 30 per user per day |
| Calendar feed reads | 60 per minute per token, 120 per minute per IP; 404 for unknown tokens counted per IP and blocked at 30 a minute |
| Share and public page views | 60 per minute per token or slug, 120 per minute per IP (the CDN absorbs most traffic) |
| Content reports | 10 per user per hour, 30 per IP per day; one open report per user per page |
| Referral link opens | 30 per IP per hour; referral reward claims limited by the caps in section 2.8 |
| `/go/{click_id}` | 120 per minute per IP; a click id works once per minute per user |
| Link preview | 20 per user per hour |
| Search and geo proxies | Per-user daily quotas (Free 100, paid 500) |
| Export and delete | 1 per day per user each |
| Webhooks | No per-IP limit; signature failures limited to 30 per minute per IP then blocked at Cloudflare |
| Admin | 300 per minute per admin; 10 failed logins per hour per IP |

### 2.4 App Attest and device trust

- iOS uses Apple App Attest. On first launch the app generates a key, the server issues a challenge (`POST /devices/attest/challenge`), the app sends the attestation (`POST /devices/attest`), and the server verifies the certificate chain, the nonce and the App ID hash, and stores the public key against the `devices` row. Later sensitive calls (first AI action of a session, account creation, credit claims, import reward and referral claims) carry an assertion the server verifies with a counter.
- Purpose: tie the Free allowance (12 credits a month and one taster agent run) to a real device and stop signup farming. One attested device gets one Free allowance per 30 days across accounts, and one import reward and one referral reward claim per account.
- Fallback: if attestation is unavailable (old OS, simulator, Apple outage) the account still works with stricter limits: half the free AI allowance, email verification required, per-IP signup limits, no referral reward until the account is verified. Never block normal planning.
- Web has no attestation. Web Free accounts get the same caps and rely on email verification, Cloudflare Turnstile on signup, per-IP limits and disposable-email blocking.
- Jailbreak signals are not used to block users.

### 2.5 SSRF protection for link previews and calendar feed import and polling

Two features fetch URLs typed by users: link previews (`providers/link_preview.py`) and calendar feed import (`providers/ics_feed.py`). Both use the same guard in `security/ssrf.py`, so there is one place to get this right. This is the main server-side request risk.

1. Only `https` and `http` schemes on ports 80 and 443 (`webcal://` is rewritten to `https://` before validation). No credentials in the URL (`user:pass@`). A feed URL's query string may hold the feed's secret token; it is used for the request and then discarded.
2. Host is resolved by our code. Every resolved address (IPv4 and IPv6) must be public: block loopback, link-local (including `169.254.169.254`), private ranges, carrier-grade NAT, multicast, unique local, and IPv4-mapped IPv6 forms. Decimal, octal and hex IP spellings are normalized first. The connection then goes to the validated IP address (pinned), with the original `Host` header and SNI, so DNS rebinding cannot swap it.
3. Redirects are followed manually, at most 3, and each hop repeats steps 1 and 2. A redirect from https to http is refused.
4. Timeouts: 3 seconds connect, 5 seconds total. Response body capped at 1 MB after decompression (link preview parses only `text/html`; feed import accepts only `text/calendar`, `text/plain` or `application/octet-stream` that begins with `BEGIN:VCALENDAR`). Content is never executed or rendered. A link preview extracts only `og:title`, `og:image` URL, `og:description` and `<title>` as plain text; a feed body goes to the sandboxed parser in section 2.6.
5. Denylist: Airbnb, Vrbo and Booking.com hosts (and their country domains) are refused outright, which also satisfies the site-terms rule. The link preview response says "Paste the details or use the bookmarklet."; the feed import says "That link is not a calendar feed we can read." The denylist lives in one module shared with the AI fetch tool.
6. Fetches run in the `api` job lane on a worker with egress through a fixed proxy that has its own network deny rules for internal ranges, as defense in depth.
7. Returned image URLs are not fetched by the server; the client loads them under the CSP.
8. A feed URL is a secret. It is never logged (log masking, section 2.2), never sent to Sentry, PostHog or `provider_calls` (the row stores the host only), and never echoed back in an error message. It is held only until the preview is confirmed or discarded; if the person turns on "Keep checking this calendar" it is then kept encrypted (`FIELD_ENCRYPTION_KEY`, AES-GCM) until polling is turned off, fails three times in a row, the trip ends plus 7 days, the import is discarded or the account is deleted, at which point it is deleted. Otherwise the user repastes it to refresh. The stored address is shown back only as host plus a masked path.
10. Polling limits: every 6 hours per feed, at most 3 polled feeds per account, at most 60 fetches an hour to one destination host across the platform, conditional requests, the same guard on every poll (a host that starts resolving to a private address is refused and counts as a failure). A change preview is stored, never applied automatically, and deleted after 30 days if not confirmed.
9. Tests: a table of hostile URLs (`http://127.0.0.1`, `http://[::1]`, `http://169.254.169.254`, `http://0x7f000001`, `http://2130706433`, `http://localtest.me`, `gopher://`, `file:///`, `https://user:pass@host`, a non-standard port, a DNS name that resolves to a private address, a name that resolves to a public address first and a private one second, a redirect to a private address, an https to http downgrade, a 30x loop, an oversized body, a gzip bomb that expands past 1 MB, a response that never finishes) must all be refused, for both the link preview and the feed import, using a fake resolver and a fake socket layer so the test never touches the network.

The AI `web_fetch` tool is Anthropic's server tool, so it does not run on our network, but the same blocked domain list applies, and fetched URLs must already appear in the conversation.

### 2.6 ICS parsing safety and fuzzing

Calendar files and feeds come from other people's software and from attackers. The parser is treated as hostile-input code.

1. **Limits.** File or feed body at most 1 MB (measured after decompression); at most 500 `VEVENT`s; line length at most 8 KB; property count per event at most 100; nesting depth at most 4; text fields truncated to 2,000 characters; `RRULE` is not expanded beyond 50 occurrences per event and an event with `COUNT` or `UNTIL` beyond that is imported as a single item with a note; `ATTACH`, `URL` and `ATTENDEE` values are ignored and never fetched; `X-` properties are ignored; no `VALARM` is honored.
2. **Sandbox.** The parser runs in a short-lived subprocess with CPU (5 seconds) and memory (256 MB) limits, no network access (the subprocess is started without sockets and a test asserts any attempt fails) and a read-only file system. A timeout or limit hit returns a clear "We could not read that file" message and is counted as a metric.
3. **Output.** The parser returns plain data (title, start, end, time zone, location text, description text, `UID`). Every string is treated as untrusted text from then on: escaped by React, never rendered as HTML, never used to build a URL, never sent to the model in the file and feed paths.
4. **Mapping.** Mapping to itinerary items, flights and stays is a deterministic rule set (TripIt and Google Calendar conventions), not the model. A nothing-found result says so; it does not guess.
5. **Preview before save.** Nothing is written to the trip until the user confirms. Duplicates are skipped by `UID` and by start, end and title.
6. **Fuzzing.** Hypothesis strategies generate valid calendars and mutate them (truncation, repeated lines, huge values, unusual line folding, UTF-8 and UTF-16 byte order marks, control characters, nested `BEGIN:VEVENT`, unknown time zone names, `RRULE` bombs, year 0 and year 9999 dates, extremely long `UID`s). They run on every pull request with a fixed seed budget. Atheris runs coverage-guided for 30 minutes nightly and 1 hour before launch on the same entry point. The pass condition is no unhandled exception, no hang past the CPU limit and no memory growth past the limit. The corpus and every crasher are committed under `apps/api/tests/fixtures/ics_corpus/`.
7. **Golden files.** Real exports (scrubbed) from TripIt, Google Calendar and Apple Calendar, each with the expected item list, run as contract tests. A new vendor format needs a golden file before support is claimed.
8. **Privacy.** Uploaded files are processed in memory and dropped; only the confirmed items are stored. The file name is never logged or sent to analytics.

### 2.7 Pasted text and PII redaction

Pasted confirmations and pasted plans (Verify this plan) are sent to Anthropic, so personal data is removed first.

1. **What is redacted before any model call:** personal names (traveler names become "Traveler 1", "Traveler 2" using the trip's `people` list and a name detector), email addresses, phone numbers, postal and home addresses, dates of birth, booking references and confirmation codes, ticket and loyalty numbers, payment card numbers (Luhn-checked and pattern-based), passport and identity document numbers, and URLs with tokens or query strings. Hotel and airline names, places, dates and times are kept because extraction needs them.
2. **Booking codes come back locally.** The model never sees a code; the preview re-attaches the code found by local extraction from the original text, so the user still gets their reference on the item.
3. **Fail closed.** If the redactor raises or finds an unparsable chunk, the request is not sent and the credit is not charged. Pasted confirmations over 12,000 characters and pasted plans (Verify this plan) over 8,000 characters are refused, not truncated silently.
4. **Consent and labels.** AI consent (section 3.5) is required; the paste screen says the text is processed by Anthropic with personal data removed. Output is labeled "From your pasted text" and needs confirmation before saving.
5. **Logging.** Pasted text and model output are not logged at INFO; run records keep sizes and hashes. Prompt content is kept for 30 days server side as for every AI call (section 3.5), with the pasted text in redacted form only.
6. **Injection.** Pasted text is placed in a `tool_result` style data block, never in the system prompt; the model has no tools in this action; output must match a strict schema or is discarded. The eval set in section 1.5 includes confirmations that contain instructions.
7. **Tests.** A corpus of 40 real-shaped confirmations with planted personal data asserts that the recorded request contains none of it; property tests feed random card-like and passport-like strings; the Atheris run covers the redactor; any miss found in production becomes a corpus entry before the fix merges.

### 2.8 Import reward and referral abuse

Free Trip Passes and referral credits cost real money in AI and provider spend, so both are designed to be hard to farm.

- **Import reward** (one free Trip Pass for the first qualifying import on a trip): once per account; requires a verified email; requires at least 3 items saved from the import including a flight or a stay (places-only imports and calendar change confirmations never qualify); never for an account that already has Plus; never stacks on an existing pass for that trip; nothing for an empty, duplicate or junk import (the same file hash and the same set of `UID`s cannot earn it twice across accounts); the grant is idempotent on `(user_id, 'import_reward')`; the pass and its 40 credits are revocable from admin with the ledger reversed.
- **Referral credits:** a referral link carries only an opaque code (no user id or email). Both sides are rewarded only after the referred account has a verified email and has created their first trip with dates and, on iOS, has passed attestation or the stricter fallback. Both sides receive 20 credits that expire after 12 months and never raise a spend ceiling. Blocked: self-referral (same device key, same IP hash within 30 days, or the same normalized email), referral chains between two accounts, and more than 5 paid rewards in a rolling 30 days or 10 in a calendar year per referrer (the referred person is still paid). The pair is unique; a refund or an abuse flag on the referred account reverses both grants. Rewards are credits only (never cash or gift cards) and are never tied to a rating, review or social post (App Review Guideline 5.6.1).
- **Detection:** `referral_blocked` and `import_reward_granted` events, a daily query for referrers with a high rate of rewards, shared device keys across accounts, and referred accounts that never return after the reward. A spike alert is in section 5.3.
- **Kill switches:** `referrals.grant` pauses referral credit grants (codes can still be entered); `import.all` stops every import path and the reward; `import.polling` stops only feed polling; `ai.import` stops pasted confirmations.
- **Tests:** scenarios 16 and 20 in section 1.2, plus concurrency tests that import the same file in two sessions at once and refer with two signups at once.

### 2.9 Public pages and content reports

Public sample trips and shared-trip pages put user content on the open web, so they get their own controls.

1. **Private by default.** A shared-trip page is `noindex` and unlisted until the owner turns on "Let search engines find this trip". Sample trips are written by Hermi from a system account.
2. **Redaction.** Pages show destinations, dates by day, place names and public descriptions. They never show exact addresses, prices, private notes, traveler names, email, confirmation codes or the owner's profile. A rendered-page scan against sentinel strings runs in CI (scenario 19).
3. **Reports.** Every public page and every AI answer has a Report link that needs no account for public pages (rate limited, section 2.3). Reports land in the admin content reports queue with a 24 hour response alert. Actions: dismiss, hide the page, disable the link, suspend a user's sharing. Disabling returns 410 and drops the page from the sitemap within 5 minutes (CDN purge on disable).
4. **Abuse and scraping.** Slugs for shared pages are random (128 bit) and not enumerable; the sitemap lists only opted-in and sample pages; Cloudflare rate rules apply; `robots.txt` blocks everything except the sitemap entries.
5. **No partner buttons** on public pages in Phase 1 (clicks need an account, section 2.10), so nothing on them is monetized and no disclosure is at risk.
6. **Content rules.** Terms forbid illegal, harassing and deceptive content; counsel reviews the wording; a takedown contact (`abuse@hermi.world`) is published. The kill switch `public_pages` takes every public page offline at once.
7. **Comparison pages.** `/vs` pages are first-party content: each fact has a public source and a checked date, and a correction email is listed. They make no claim that cannot be sourced and use competitor names only to describe them, never as search keywords in App Store metadata.

### 2.10 Open-redirect protection for `/go`

- `/go/{click_id}` accepts only an opaque id. There is no `url`, `to`, `next` or `redirect` parameter anywhere.
- The id refers to a `link_clicks` row created by an authenticated call (`POST /affiliate/clicks`), which names a program, a placement and a destination reference (a stored place, lodging option or route). The redirect target is built on the server from `affiliate_link_templates` plus the destination reference, with a random per-click sub-id. No user id or device id is sent to partners.
- The built URL is checked against the host allowlist of the program (`affiliate_programs.hosts`) before the 302. A mismatch logs a security event, returns the user to the trip page and never redirects off-site.
- Expired (over 15 minutes) or unknown ids redirect to the web app home. Responses send `Referrer-Policy: no-referrer` and `Cache-Control: no-store`.
- Pasted lodging links are never rewritten and never routed through `/go`; they open directly and carry no disclosure.
- A test generates 1,000 random and hostile ids and asserts every response is a 302 to an allowlisted host or the app home.
- Other redirects in the app (sign-in return paths, universal links, referral links) accept only relative paths or allowlisted app hosts.

### 2.11 Webhook signature checks

| Source | Check |
|---|---|
| RevenueCat | Shared secret in the `Authorization` header compared with `hmac.compare_digest`. Reject if missing or wrong. Payload is also cross-checked by a REST fetch for any event that grants something (purchase, refund), so a forged payload with a leaked secret still cannot grant without RevenueCat confirming |
| Resend | Svix style signature verified with `RESEND_WEBHOOK_SECRET` |
| Supabase auth hook | Standard webhooks signature with `SUPABASE_AUTH_HOOK_SECRET` |
| Affiliate report pulls | Outbound pulls (we call them), so no inbound signature; responses are validated against a schema |

Every webhook: read the raw body first (before any JSON parsing), verify, insert into `webhook_events` with the provider event id as a unique key, return 200, and process in a job. Unverified requests return 401, write nothing and increment a counter that alerts above 30 per hour. Processing is idempotent and order tolerant. Webhook endpoints have no cookies and no CORS.

### 2.12 Other controls

- **Prompt injection.** Tools bind `user_id`, `trip_id` and `run_id` from the run row; the model supplies only ids that are checked against the trip. No tool can email, post or spend. Web text, pasted confirmations and collaborator notes stay in `tool_result` blocks, never in the system prompt. Private notes are excluded from context. Evals gate every change (section 1.5).
- **Clickjacking and XSS.** `frame-ancestors 'none'`, strict CSP, no inline scripts, React escaping, sanitized rich text only in one component. Imported titles and descriptions are plain text everywhere.
- **CSRF.** Bearer tokens are immune. The web cookie path requires the `X-Hermi: 1` header plus `Origin` match. Calendar feed and public page routes are read-only GETs.
- **Supply chain.** Lockfiles, pinned base image digests, pinned GitHub Actions by SHA, SBOM generated in CI, provenance attestation on the image. The ICS parser library is pinned and fuzzed on every upgrade.
- **iOS app.** Keychain for tokens, no secrets in the bundle (public keys only), ATS on, no `server.url` in production, jailbreak not enforced, privacy manifest shipped, universal links validated server side.
- **Denial of service.** Cloudflare rate rules and bot fight mode, body size limits, pagination caps (max 100), query timeouts, parser sandbox limits, and kill switches.
- **Data at rest.** Provider-default encryption for Postgres and R2; encrypted off-provider dumps with a key held outside Render.
- **Penetration test.** Scoped to auth, tenant isolation, purchase and credit flows, `/go`, link previews, ICS file and feed import, pasted import, public pages and reports, referral abuse and admin. Findings rated high or critical block launch.

### 2.13 Admin access

The admin console (see [08-admin-control-center.md](08-admin-control-center.md)) is the most powerful surface, so it has its own controls.

1. **SSO only.** Admins sign in through the company identity provider (OIDC). Only emails on `ADMIN_ALLOWED_DOMAIN` with a matching row in `admin_users` get a session. No passwords, no Supabase Auth users for admins.
2. **2FA required.** The identity provider enforces a phishing-resistant second factor (passkey or hardware key). An `admin_users` row records `mfa_enrolled`; the time of the last factor check comes from the identity provider's token, and sessions older than 12 hours or without a recent factor check are refused. Step-up (fresh factor within 10 minutes) is required for refunds, credit grants over 100, flag changes, kill switch changes, user suspension, reward and referral revocation, data export access and deletion.
3. **Roles.** `support` (read users and trips by id, view tickets and content reports, resend emails), `ops` (kill switches, feature flags, queue tools), `finance` (credits, refunds, affiliate revenue), `owner` (all, manage admins). Two admins must approve granting `owner`.
4. **Scope of view.** Support sees account metadata by default. Trip contents need a ticket id and a reason, logged, and expire after 30 minutes. Import previews and pasted text are never visible to admins.
5. **Audit.** Every admin call writes `audit_log` (admin, action, target, before and after, reason, IP, request id). The log is append-only at the database level (no update or delete grants) and is exported weekly to R2. Alerts fire on off-hours use, bulk actions, and any admin change to `admin_users`.
6. **Network.** Optional IP allowlist (`ADMIN_IP_ALLOWLIST`), separate Cloudflare rules for `/admin`, stricter rate limits, and no admin routes on the iOS origin.
7. **No shared accounts.** Offboarding removes the `admin_users` row and the identity provider account the same day.

### 2.14 Verify this plan and evidence recheck

Both features send text to Anthropic and open web pages on the user's behalf, so they follow the AI rules in [06-ai-agents-spec.md](06-ai-agents-spec.md) sections 4.3, 5.11 and 5.12 and these checks.

1. **Privacy.** The pasted plan goes through the same redactor as pasted confirmations (2.7) and is never stored; only the extracted items and their evidence are kept, for 30 days. A check request carries only one item's name, planned time, claimed hours and price and the matched place's public fields.
2. **No fetching of booking sites.** The blocked-domain list (Airbnb, Vrbo, Booking.com and their country sites) applies to every search and fetch; an item whose only source is such a page ends `unchecked` with `blocked_source`. Links inside the pasted text and in an item are never opened; a recheck fetches only the stored source URL that an earlier run already saw.
3. **Verdicts are code, not model output.** The model reports what a page showed; every reported value must appear in a tool result of the same request, and the cited page must be one the search returned or the fetch opened. A value that cannot be grounded is discarded, and a green or amber row without a cited page and date cannot be written (database constraint `ck_plan_verification_items_evidence`).
4. **Tamper resistance.** Members can change only the check and import ticks; verdicts, reasons, evidence and counts are written by the worker role (grants in 03 section 6.1), and the tenant-isolation tests cover both tables.
5. **Injection.** Item text, place data and fetched pages are data; the model has no write tool; output is a strict schema; the eval set includes pages with hidden instructions (section 1.5).
6. **Abuse and cost.** Per-run caps (5 or 12 items), a per-item $0.02 hard stop, admission on month headroom, the AI endpoint rate limits (10 a minute, 30 an hour), refunds for unchecked items, and an alert when real cost per checked item exceeds $0.02 (section 5.4).
7. **Wording.** No screen, email or notification says a plan is "verified", "safe" or "guaranteed"; a copy lint test in CI fails on those words in the verify screens.

## 3. Privacy and compliance

Plain statement used in the app and policy: Hermi does not sell personal data, does not show ads and does not track people across other companies' apps or sites. Legal texts are written by counsel and versioned; `consents` stores the accepted version. This section is the engineering side.

### 3.1 GDPR and CCPA/CPRA

| Topic | Implementation |
|---|---|
| Lawful basis (GDPR) | Contract for running the service; consent for AI processing, marketing email and optional analytics; legitimate interest for security logs and abuse prevention (device and IP hashes) |
| Data inventory | A maintained `docs/privacy/data-map.md`: each table or store, what it holds, purpose, retention, processor, deletion rule. A test fails if a new table lacks an entry (the `referral_*` tables, `plan_verifications`, stored feed addresses and calendar tokens included) |
| Rights | Access, portability (export), correction (edit in app), deletion (in app), objection and restriction (by support within 30 days; 45 days for CCPA) |
| CCPA | No sale or sharing. No "Do not sell or share" link needed because there are no ad SDKs; the policy says so. Honor Global Privacy Control as an opt-out of optional analytics |
| Processors | DPA signed with Anthropic, Supabase, Render, Cloudflare, RevenueCat, Sentry, PostHog, Resend, Better Stack. List is public in the policy |
| International transfers | Standard contractual clauses where needed; US primary region at launch; EU region only when revenue or partners require |
| Breach notice | 72 hours to regulators where required; users notified without undue delay (runbook 8.4) |
| Imports | Uploaded calendar files and Google Maps exports are processed in memory and dropped; a feed URL is kept (encrypted) only while the person has "Keep checking this calendar" on and is deleted when it is turned off; Google Maps list links are never opened or stored; pasted confirmations and pasted plans are redacted before any AI processing, and only confirmed trip items (and, for plan checks, the extracted items with their evidence for 30 days) are kept |
| Public pages | Shared pages are opt-in for indexing; the owner can turn a page off at any time; reports can take a page down. "How we earn", "How billing works", the Android guide and the status page are static or data-driven pages with no personal data |
| Minors | See 3.7 |
| DPIA | A short data protection impact assessment for AI processing, imports and shared trips, reviewed yearly |

### 3.2 Account deletion

Mandatory in the app under Apple guideline 5.1.1(v): Settings, Account, Delete account. No support email route and no web-only route.

1. Re-authenticate (Apple, Google or email code). Show a plain list: what is deleted, what others keep, what stays by law, that the Apple subscription is not cancelled (with a link to Manage Subscriptions).
2. Immediately: `users.status = 'pending_deletion'`, revoke sessions and refresh tokens, revoke the Sign in with Apple token, unregister `devices`, cancel `trip_invites` the user created, rotate and disable calendar feed tokens, take the user's public and shared pages offline, stop notifications.
3. Owned trips with other members: prompt to transfer ownership or delete. If no choice within 30 days and no member accepts, delete the trip.
4. Owned trips with no other members: deleted at the end of the grace window.
5. Trips owned by others: the user is removed; their contributions remain, attributed to "Deleted user" (stated in the policy).
6. Grace window of 30 days: signing in restores the account. A reminder email goes out at day 23.
7. Day 30: `delete_account` job hard deletes `users`, `auth_identities`, `devices`, `people` owned by the user, `consents` (except the deletion record), referral links, `credit_ledger` (aggregated into anonymous totals), AI history, the Supabase Auth user (service role call), PostHog person, and Sentry user context where possible. A checklist row per step makes partial failure visible, and each step is idempotent.
8. Kept by law, stripped of profile data: `store_transactions` and tax records (typically 7 years), and a hashed abuse marker (email hash and device key hash) for 12 months, which also stops a deleted account from claiming a second Free allowance, import reward or referral reward.
9. Backups age out within 35 days (the policy says so). The restore runbook re-applies deletions after any restore (`deletion_requests` is replayed).
10. Test: end-to-end test in the integration suite (section 1.2) and a quarterly drill that restores a backup and confirms deleted users stay deleted.

### 3.3 Data export

Settings, Account, Export my data (re-authentication required, 1 per day). The `export_user_data` job writes a zip to the R2 exports bucket: one JSON file per table that holds the user's data, a readable PDF or CSV per trip, ICS calendars, and consent and referral history. A signed link is emailed and expires in 7 days; the file is deleted at expiry. Target under 24 hours; legal limits are 30 days (GDPR) and 45 days (CCPA). Export is free on every tier and is never gated by a subscription. A generated list of tables with personal data drives both export and deletion so they cannot drift (tested).

### 3.4 App Privacy labels and privacy manifest

All items are "not used for tracking". Labels must match the code; a checklist item in every pull request that adds an SDK or a data field asks whether the label changes.

| Data type | Collected | Linked to user | Purpose |
|---|---|---|---|
| Contact info: email, name | Yes | Yes | App functionality, account |
| User content: trips, notes, itinerary, imported trip items, pasted confirmation text and pasted plan text (redacted before AI processing; plan text is not stored), plan check results (items and evidence, 30 days) | Yes | Yes | App functionality |
| Identifiers: user id, device id (push token, App Attest key id) | Yes | Yes | App functionality, analytics, fraud prevention |
| Purchases | Yes | Yes | App functionality |
| Usage data: product interactions, affiliate click logging (which partner link was tapped, when, on which screen), referral attribution | Yes | Yes | Analytics, app functionality |
| Diagnostics: crash logs, performance | Yes | No where possible | App functionality |
| Location | Only if the user taps "near me"; coarse, not stored | No | App functionality |
| Financial info, health, contacts, browsing history, search history outside the app | No | | |

`PrivacyInfo.xcprivacy` declares required-reason APIs used by the app and each SDK (UserDefaults, file timestamps, system boot time if used). Each SDK (Sentry, PostHog, RevenueCat, Capacitor plugins) is checked for its own manifest. No IDFA, no ATT prompt, no ad SDK. The app reads no calendar data through the system calendar API: import uses a file the user picks or a URL the user pastes, and the calendar feed is a link the user's calendar app subscribes to.

### 3.5 AI data sharing consent

Apple guideline 5.1.2(i) requires disclosure and permission before personal data goes to third-party AI.

- **Consent screen** the first time an AI feature is used, including a pasted confirmation import, Verify this plan and a recheck (also shown from Settings, Privacy). It names Anthropic, says what is sent (destination names, dates, party size, budget, preferences and text the user typed in the request, and pasted confirmation text with personal data removed), says what is not sent (email, name, account id, Apple identifiers, home address, other travelers' names which become "Traveler 1", booking codes, payment data), says it is not used to train models, and links to the policy. Buttons: "Allow" and "Not now". "Not now" leaves everything else working, including file and feed import, which use no AI.
- Stored in `consents(kind='ai_processing', version, granted_at, revoked_at)`. Revoke in Settings disables AI and does not delete the account. A new consent version re-prompts.
- The API refuses AI routes without a current consent row (403 `consent_required`), and the worker checks again before each run.
- Shared trips: the requester's consent covers their own prompt; the trip setting "Allow AI on this trip" (owner) controls whether content others wrote enters context. Notes marked private are never sent.
- Provider terms: zero retention or no training on API data, DPA in place. Opaque per-request ids are used for abuse reports, not user ids.
- Every AI call is recorded in `runs` and `ai_usage` with user id, trip id, model, tokens, credits. Prompt and response content is kept 30 days server side (pasted text in redacted form only) and otherwise only in the visible history.

### 3.6 FTC affiliate disclosure and related advertising rules

- Disclosure text beside every partner button and card: "We earn a commission if you book here." It is on the card itself, not behind a tap or in the footer, and is readable (same size as body text, not low contrast). The text is the `affiliate.disclosure` copy key used by one component, so it cannot be omitted on a new placement.
- Storefronts in the UK and EU also show an "Ad" label on partner cards, per local rules.
- Lists say how they are sorted (for example "Sorted by price"). Nothing is ranked by commission (ranking neutrality eval, section 1.5). Affiliate and non-affiliate options appear together in the same lists.
- Pasted links are never rewritten. Airbnb has no program and gets plain links.
- Public pages carry no partner buttons in Phase 1.
- Terms of each affiliate program are kept in `docs/partners/` and reviewed twice a year. Tracking uses a random per-click sub-id with no user data.
- Reviews and testimonials in marketing are real and uncompensated, or labeled. Referral and import rewards are never conditioned on a review or rating.
- Comparison pages make only claims that are true, sourced and dated.

### 3.7 Children

- Age gate 13 or older at sign-up, 16 or older for EU and UK locales (age is self-declared, not stored as a birthdate beyond the declaration timestamp). Hermi is not in the Kids category and is not directed at children.
- Children on a trip (travelers) are entered by an adult as a first name and a color: no birthdate, no photo, no email, no account.
- If a report or an account shows the user is under the age, the account is deleted and no data is kept.
- Check state age assurance laws (Texas, Utah and others) for new duties before each submission.
- The age rating questionnaire is answered honestly; expect 4+ or 9+, and up to 12+ because of shared content and AI text.

### 3.8 Insurance referral rules

- Hermi shows links to licensed insurance partners only. It does not sell, solicit, negotiate or advise on insurance, and does not collect payment for it. Affiliate compensation for insurance is a referral with no compensation tied to the sale of a policy where state law requires that; counsel confirms the program terms before any insurance link goes live.
- Copy is supplied or approved by the insurer or network. No coverage claims, no comparisons of coverage, no "you need this" language. Every card says "Partner offer. Check the policy terms" plus the commission disclosure.
- The AI never gives insurance, visa or legal advice; it links to official sources (root README rule 5). The AI eval "safety scope" enforces this.
- The "Before you go" checklist lists insurance as one item among many, unranked, and at least half of the checklist items carry no monetization.
- Insurance cards are hidden where the partner is not licensed (region flag).

### 3.9 Other obligations

| Item | Requirement |
|---|---|
| Email | Transactional mail separate from marketing; marketing is opt-in with one-click unsubscribe (`UNSUBSCRIBE_SECRET` signed link) and a physical address in the footer (CAN-SPAM). Referral invitations are sent by the user's own share sheet, not by Hermi email |
| Push | Permission requested in context after the first invite or alert, with a reason screen; no marketing pushes without opt-in |
| Subscriptions | Price, period, trial length and renewal terms visible on the paywall; Terms and Privacy links; Restore button; one-tap "Cancel subscription" on the Account plan card that opens Apple's subscription sheet, the same link in the trial reminder email, and the plain "How billing works" page (guideline 3.1.2) |
| Auto-renew laws | State rules on cancellation and reminders are handled by Apple for in-app subscriptions |
| Accessibility | Accessibility statement, VoiceOver pass, Dynamic Type, reduced motion, AA contrast (the Hermi palette in 05 section 2.3, including `--tp-edge`, `--tp-warning-ink` and `--tp-sky-ink` on sky); accessibility nutrition labels in App Store Connect if required at submission |
| Sales tax and VAT | Apple is merchant of record for all in-app purchases in Phase 1; there is no web checkout |
| Maps and data attributions | OpenStreetMap, Wikimedia and provider attributions in a licenses screen |
| Terms of providers | Never fetch Airbnb, Vrbo or Booking.com pages; no scrapers; review SerpApi and Geoapify terms before scaling; cache only within each provider's terms; competitor facts on `/vs` pages are read by hand, never collected by a program |
| Trademarks | Competitor names are used only to describe compatibility and comparisons ("Import from TripIt"), with a statement of no affiliation |

## 4. Analytics event catalogue

Tool: PostHog (first party, no ad SDKs). Rules:

- Events have no PII: no email, name, free text, trip titles, place names, addresses, notes, file names, feed URLs or pasted text. Identify with the opaque `users.id` UUID only. Session replay is off (or fully masked).
- Properties use enums and buckets, not raw values: destination is a country code or region, dates are buckets (days until departure), money is a bucket or tier, counts are buckets.
- Event names are `snake_case`, past tense, defined once in `packages/shared/src/events.ts`. The server rejects unknown names and unknown properties in `analytics.capture`. Client events go through the same typed helper.
- Opt-out respected (Settings, Privacy) and Global Privacy Control honored. Events are dropped, not queued, when opted out.
- Retention in PostHog 90 days for events, 13 months for aggregated dashboards.

Common properties on every event (not repeated below): `app_version`, `platform` (`ios`, `web`), `tier` (`free`, `plus`), `is_guest` (bool), `locale`, `env` and a random per-launch `session_id`. Screens in [05-ui-ux-spec.md](05-ui-ux-spec.md) list their events by the names in this table; an event a screen needs that is missing here is added here first.

| Event | Properties | When fired |
|---|---|---|
| `app_opened` | `source` (`icon`, `push`, `universal_link`) | App foreground start, at most once per 30 minutes |
| `signup_started` | `method` (`apple`, `google`, `email_code`) | User taps a sign-in method |
| `signup_completed` | `method`, `from_invite` (bool), `from_referral` (bool), `was_guest` (bool) | First `users` row created |
| `sign_in_completed` | `method` | Existing user signs in |
| `guest_trip_created` | none | Guest creates a local trip |
| `guest_claimed` | `trip_count_bucket` | Guest data claimed into an account |
| `onboarding_step_completed` | `step` (`profile`, `home_airport`, `first_trip`) | Each onboarding step |
| `trip_created` | `source` (`blank`, `template`, `import`), `destination_count`, `has_dates` | Trip saved |
| `first_itinerary_item_added` | `minutes_since_signup_bucket` | First item in the user's first trip (activation) |
| `itinerary_item_added` | `category` (`itinerary_items.category`: `sights`, `museum`, `food`, `nature`, `nightlife`, `shopping`, `travel`, `other`), `source` (`itinerary_items.source`: `manual`, `place_search`, `ai_draft`, `agent`, `import`) | Item created |
| `flight_route_added` | `route_type` (`one_way`, `round_trip`), `days_to_departure_bucket` | Route created |
| `fare_alert_created` | `kind` (`cached`, `live`) | Alert created |
| `price_alert_delivered` | `channel` (`push`, `email`, `in_app`) | Alert notification sent |
| `price_alert_opened` | `channel` | User opens from an alert |
| `lodging_option_added` | `source` (`lodging_options.added_via`: `paste`, `bookmarklet`, `partner_search`, `agent`, `manual`) | Option created |
| `lodging_voted` | `voted` (bool: a heart added or removed) | Heart toggled |
| `present_mode_started` | `slide_count_bucket` | Presentation opened |
| `invite_sent` | `channel` (`link`, `email`, `sms_share`), `role` | Invite created |
| `invite_opened` | `platform_before_install` (`installed`, `not_installed`) | Invite link opened |
| `invite_accepted` | `role`, `minutes_to_accept_bucket` | Invite redeemed |
| `collaborator_limit_hit` | `role_requested` | A Free owner tries to invite a second collaborator (server side) |
| `share_link_created` | `redaction_level`, `indexable` (bool) | Share link created |
| `share_link_viewed` | `surface` (`web`) | Shared page loaded (server side) |
| `ai_consent_shown` | none | Consent screen displayed |
| `ai_consent_granted` | `version` | Consent accepted |
| `ai_consent_declined` | none | "Not now" |
| `ai_action_started` | `action` (`explain`, `live_search`, `draft_day`, `draft_trip`, `research`, `agent_run`, `verify_plan`), `feature` (`explain`, `packing_list`, `booking_import`, `verify_extract`, `verify_plan`, `recheck`, `fare_hunt`, `deep_research`, from 06 section 1), `credits`, `from_cache` (bool), `taster` (bool) | Credits reserved (or the taster grant spent) |
| `ai_action_completed` | `action`, `feature`, `outcome` (`ok`, `partial`, `failed`, `refunded`; a run the user stopped is `partial`), `taster` (bool), `duration_seconds_bucket` | Run settled |
| `ai_feedback_given` | `action`, `rating` (`up`, `down`), `reason` (enum) | Thumbs tapped |
| `fare_marked_wrong` | none | "Price was different" tapped |
| `credits_low_shown` | `balance_bucket` | Low credit banner shown |
| `paywall_viewed` | `placement` (a trigger id from [05-ui-ux-spec.md](05-ui-ux-spec.md) section 6.27, for Phase 1: `collaborators`, `track_live`, `third_trip`, `credits`, `out_of_credits_verify`, `trip_pass`, `settings`, `onboarding`; on the web the sheet has no purchase control), `offer_shown` (list of product codes) | Paywall displayed |
| `paywall_dismissed` | `placement` | Closed without purchase |
| `purchase_started` | `product` (`plus`, `trip_pass`, `credits_50`, `credits_150`, `credits_400`), `period` | StoreKit sheet shown |
| `purchase_completed` | `product`, `period`, `is_trial` (bool) | Server confirms entitlement |
| `purchase_failed` | `product`, `reason` (`cancelled`, `pending`, `error`) | Purchase ends without success |
| `restore_tapped` | `result` (`restored`, `nothing`) | Restore purchases tapped |
| `trip_pass_applied` | `source` (`purchase`, `import_reward`) | Pass bound to a trip |
| `subscription_canceled` | `product`, `days_active_bucket` | From RevenueCat webhook |
| `subscription_expired` | `product`, `reason` (`voluntary`, `billing`, `refund`) | From webhook |
| `partner_card_viewed` | `program` (code), `placement` (`flight`, `stay`, `activity`, `esim`, `car`, `insurance`, `checklist`) | Card enters viewport (once per screen visit) |
| `partner_link_tapped` | `program`, `placement` | `/go` click created |
| `affiliate_conversion_imported` | `program`, `status` (`pending`, `approved`, `reversed`) | Server import (no amounts in analytics) |
| `push_prompt_shown` | `context` (`after_invite`, `after_alert`) | Reason screen shown |
| `push_permission_result` | `result` (`granted`, `denied`) | System prompt result |
| `offline_trip_saved` | `trigger` (`manual`, `auto_departure`) | Trip cached for offline |
| `offline_trip_opened` | `connection` (`offline`, `online`) | A trip workspace opens from the offline cache |
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
| `onboarding_switch_answered` | `answer` (`tripit`, `tripsy`, `wanderlog`, `other_app`, `fresh`, `skipped`) | The "Coming from TripIt, Tripsy or Wanderlog?" question answered |
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
| `section_opened` | `section` (`flights`, `stays`, `plan`, `notes`, `checklist`, `ai_activity`) | A summary card or section tab opened |
| `invite_sheet_opened` | none | Invite sheet opened |
| `traveler_linked` | none | "Which traveler are you?" answered |
| `fare_chip_tapped` | `source` (`live`, `cached`, `agent`, `google`) | Fare chip tapped |
| `fare_detail_viewed` | `age_hours_bucket` | Fare detail opened |
| `fare_marked_booked` | `price_entered` (bool) | "Mark as booked" on a chosen fare |
| `flight_chosen` | none | A fare is chosen for a route (server side) |
| `booked_fare_watch_created` | `kind` (`cached`, `live`) | A watch on a booked fare starts |
| `booked_fare_alert_delivered` | `channel` (`push`, `email`, `in_app`), `drop_bucket` | A booked-fare drop alert is sent (server side) |
| `booked_fare_alert_opened` | `channel` | User opens from the alert |
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
| `evidence_opened` | `surface` (`fare`, `note`, `research`, `import`) | Evidence row or source opened |
| `finding_saved_to_notes` | none | A finding copied to notes |
| `present_mode_printed` | none | Print or PDF from present mode |
| `pdf_exported` | `footer` (bool: the Free footer was added) | PDF export created |
| `checklist_item_shown` | `kind` (`checklist_items.kind`) | Checklist row seen, once per item per session |
| `checklist_item_updated` | `kind`, `status` (`done`, `skipped`, `not_needed`, `todo`) | Row ticked, dismissed or reset |
| `discover_viewed` | none | Discover opened |
| `destination_opened` | `country_code` | A destination page opened |
| `trip_started_from_discover` | none | "Start a trip here" tapped |
| `activity_viewed` | `unread_bucket` | Activity opened |
| `activity_item_opened` | `kind` (`alert`, `change`, `run`, `invite`) | Activity row opened |
| `account_viewed` | none | Account opened |
| `setting_changed` | `key` (the setting name, never its value) | A setting toggled |
| `booking_links_hidden` | `value` (bool) | "Hide booking links" switched |
| `manage_subscription_tapped` | none | "Manage subscription" tapped |
| `notification_opened` | `type` (`price_alert`, `booked_fare`, `trip_change`, `reminder`, `run_done`, `calendar_changes`, `verify_done`) | App opened from a push |
| `subscription_started` | `product`, `period`, `is_trial` (bool) | From the RevenueCat webhook |
| `subscription_renewed` | `product`, `period` | From the webhook |
| `trial_converted` | `product` | First paid renewal after a trial |
| `subscription_changed` | `direction` (`upgrade`, `downgrade`), `from`, `to` (product codes, monthly and annual Plus) | Plan switch applied or scheduled |
| `trip_pass_moved` | none | A pass moved to another trip |
| `trip_pass_expired` | `product`, `source` (`purchase`, `import_reward`) | Pass reaches `expires_at` |
| `credits_expired` | `credits_bucket` | Grant expiry sweep (server side, no user id in the event) |
| `import_started` | `method` (`ics_file`, `ics_feed`, `pasted`, `maps_file`, `places`), `source_app` (`tripit`, `tripsy`, `wanderlog`, `google_calendar`, `google_maps`, `other`, `unknown`) | User starts an import (the app name is the entry the user chose or detected from the file format, never from the URL) |
| `import_previewed` | `method`, `item_count_bucket` | The preview list is shown |
| `import_completed` | `method`, `saved_count_bucket` | The user confirms and items are saved |
| `import_failed` | `method`, `reason` (`too_large`, `invalid_file`, `blocked_url`, `list_link_not_readable`, `fetch_failed`, `no_items`, `rate_limited`, `consent_required`, `redaction_failed`, `error`) | An import ends without saving |
| `import_reward_granted` | `method` | The free Trip Pass is granted (server side, once per account) |
| `calendar_feed_enabled` | none | A calendar subscription link is created |
| `calendar_feed_rotated` | none | The link is rotated |
| `calendar_feed_read` | none | The feed is fetched by a calendar app (server side, counted per trip per day) |
| `public_page_viewed` | `kind` (`sample`, `shared`), `referrer_bucket` (`search`, `social`, `direct`, `other`) | A public page loads (server side) |
| `sample_trip_copied` | none | "Copy this trip" after sign-up |
| `share_indexing_toggled` | `value` (bool) | Owner turns search indexing on or off |
| `content_reported` | `surface` (`shared_trip`, `sample_trip`, `ai_answer`, `research`), `reason` (enum) | A report is submitted |
| `vs_page_viewed` | `competitor` (`tripit`, `wanderlog`, `tripsy`) | A comparison page loads (server side) |
| `referral_link_shared` | `channel` (`share_sheet`, `copy`) | The referral link is shared |
| `referral_signup_attributed` | none | A sign-up carries a referral code |
| `referral_reward_granted` | `side` (`referrer`, `referred`) | Credits granted after activation |
| `referral_blocked` | `reason` (`self`, `duplicate`, `cap`, `abuse`, `unverified`) | A reward is refused (server side) |
| `calendar_polling_enabled` | none | "Keep checking this calendar" switched on |
| `calendar_changes_found` | `change_count_bucket` | A poll found changes and made a preview (server side) |
| `calendar_changes_applied` | `applied_count_bucket` | The person applied some or all changes |
| `verify_started` | `label` (`chatgpt`, `gemini`, `layla`, `mindtrip`, `other`), `text_length_bucket` | A pasted plan is read (step 1) |
| `verify_items_read` | `item_count_bucket` | The list of places is shown |
| `verify_checked` | `selected_count_bucket`, `green_bucket`, `amber_bucket`, `red_bucket`, `unchecked_bucket`, `credits` | A plan check settles (server side) |
| `verify_imported` | `item_count_bucket` | Checked items are added to the trip |
| `verify_discarded` | none | A plan check is discarded |
| `evidence_stale_shown` | `age_bucket` (`15_to_30`, `over_30`) | A "May be out of date" chip is shown, once per item per session |
| `evidence_rechecked` | `result` (`confirmed`, `changed`, `not_shown`, `unreachable`), `credits` | A recheck settles (server side) |
| `cancel_link_tapped` | `surface` (`account`, `paywall`, `email`, `billing_page`) | "Cancel subscription" tapped |
| `how_we_earn_viewed` | `source` (`settings`, `paywall`, `vs`, `link`) | The How we earn page loads |
| `billing_page_viewed` | `source` (`settings`, `paywall`, `link`, `listing`) | The How billing works page loads |
| `sync_indicator_tapped` | `state` (`synced`, `syncing`, `offline`, `failing`) | The sync indicator is tapped |
| `status_banner_shown` | `component` (`web`, `api`, `ai`, `fares`, `push`) | The status banner appears |
| `status_page_opened` | `source` (`banner`, `settings`, `link`) | The status page is opened from the app |
| `android_install_card_shown` | none | The Android install card appears |
| `android_install_prompted` | `result` (`accepted`, `dismissed`) | The browser install prompt result |
| `android_install_guide_viewed` | `source` (`card`, `settings`, `link`) | The Android install guide loads |
| `pwa_installed` | none | The installed web app opens for the first time |

Screen names in 05 map to the catalogue as follows, so a screen never invents a name: the Subscription and credits screen is `screen_viewed {screen: subscription}`; a credit pack tap is `purchase_started` with a `credits_*` product; a live check or an explain is `ai_action_started` with its `action`; "Book on ..." on a fare, a stay or a checklist row is `partner_link_tapped` with the matching `placement`; sharing from present mode is `share_link_created`.

Funnels tracked from these events: activation (`signup_completed` to `first_itinerary_item_added` within 24 hours), invite loop (`invite_sent` to `invite_accepted` to second `trip_created`), collaborator limit (`collaborator_limit_hit` to `paywall_viewed` with `collaborators` to `purchase_completed`), paywall (`paywall_viewed` to `purchase_started` to `purchase_completed`), AI (`ai_consent_granted` to `ai_action_completed` with `outcome=ok`), affiliate (`partner_card_viewed` to `partner_link_tapped`), switching (`onboarding_switch_answered` to `import_started` to `import_completed` to `import_reward_granted` to `itinerary_item_added`), public pages (`public_page_viewed` to `signup_started`), referral (`referral_link_shared` to `referral_signup_attributed` to `referral_reward_granted`).

## 5. Observability

### 5.1 Logs

JSON to stdout, one line per event, shipped to Better Stack and kept 14 days hot (30 for security events). Fields: `ts`, `level`, `service`, `env`, `release`, `request_id`, `job_id`, `run_id`, `user_id` (opaque), `route`, `status`, `latency_ms`. `request_id` flows into jobs. No prompts, itineraries, notes, emails, tokens, feed URLs or pasted text at INFO; sizes and hashes instead. Security events (`auth_failed`, `role_changed`, `webhook_rejected`, `admin_action`, `rate_limited`, `import_blocked_url`, `referral_blocked`, `content_report_created`) use a dedicated `event` field.

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
| Imports | Imports started, previewed and completed per method and per entry (TripIt, Tripsy, Wanderlog, Google Maps); failure rate by reason; parser sandbox timeouts and memory kills; feed URLs refused by the SSRF guard; polled feeds, change previews found and confirmed, polls failing; redaction failures; import rewards granted per day |
| Verify this plan | Checks per day, items per check, verdict mix, credits spent, real cost per checked item, refund rate, share served from the `place_check` cache, false-green reports ("Price was different" style reports on green rows), rechecks and their results |
| Referrals | Referral signups, rewards granted and blocked by reason per day |
| Public pages | Requests, CDN hit rate, 4xx and 5xx, reports created, reports open over 24 hours, pages taken down |
| Business | Signups, activation, invites, paywall conversion, MAU, MRR, credits sold, affiliate clicks and conversions, gross margin per tier, switching funnel conversion |
| Client | Crash-free sessions (Sentry), cold start time, JS errors, API errors seen by the app, sync indicator states shown (offline and failing shares), Android installs |

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
| Import failures | More than 30 percent of imports failing for 30 minutes (excluding user mistakes) | notify |
| Import SSRF attempts | More than 50 refused feed URLs in an hour, or any single account with more than 10 | notify; engage `import.all` if it continues |
| Calendar polling | More than 20 percent of polls failing for an hour, or any polled feed host over 60 fetches an hour | notify; engage `import.polling` if it continues |
| Verify this plan cost | Real cost per checked item over $0.02 on a 7 day p95, or more than 5 false-green reports in a day | notify; consider `ai.verify` |
| Status page | A component degraded for more than 10 minutes with no incident posted | notify |
| Parser sandbox kills | More than 5 timeouts or memory kills in an hour | notify |
| Redaction failures | Any spike over 10 in an hour | notify |
| Import rewards or referral rewards | More than 3 times the 7 day daily average, or any account at its cap twice | notify |
| Content reports | More than 10 new in an hour, or any report unresolved after 24 hours | notify |
| Public page errors | Non-2xx rate over 5 percent for 15 minutes | notify |
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
| Booking import spend | Over 3 times the 7 day average, or any account over 30 imports a day | notify | Consider `ai.import` |
| Plan check spend | Over 3 times the 7 day average, or any account over 10 checks a day | notify | Consider `ai.verify` |
| Cache hit rate | Down 20 points from the 7 day average | notify | None |
| Anthropic 429 or overloaded rate | Over 5 percent for 10 minutes | notify | Back off the `ai` lane |
| Refusal rate | Over 3 percent for a feature in a day | notify | Review prompt version |
| Cost per agent run | 7 day p95 over $0.80 | notify | Review before any Pro launch in Phase 2 |
| Gross margin per tier | Below 70 percent on a rolling 30 days for Plus and Trip Pass | digest | Review |
| Anthropic workspace spend | 50, 80 and 100 percent of the monthly limit | notify, page at 80 | Limit is the final backstop |

Monthly provider-spend ceilings per tier (root README) are enforced by the ledger; these alerts catch drift and bugs.

### 5.5 Uptime and status

Better Stack probes `/health/ready` from two regions and runs a synthetic check every 5 minutes that signs in with a test account and loads a trip. A public status page (`status.hermi.world`, hosted by Better Stack outside our own infrastructure, 02 section 8.1) lists five components: web app, API, AI features, fare data and push, each fed by an outside monitor, with 90 days of uptime and plain-words incidents. The app's status banner mirrors it through `GET /public/status`, and the trip header shows "Synced N seconds ago" so a person can tell a local problem from ours. An incident is posted whenever a component is degraded for more than 10 minutes; the drill in section 8.2 includes posting one. Service targets: API availability 99.9 percent, price alert delivery within 30 minutes of a scheduled check, p95 queue wait under 5 minutes.

## 6. App Store submission (Phase 1 products)

Products submitted: Plus monthly and annual (7-day trial on annual), Trip Pass, and the credit packs `credits_50`, `credits_150` and `credits_400`, all through In-App Purchase. Not submitted in Phase 1: Family, Group Trip Pass, Pro, and anything billed through Stripe. There are no web purchases in Phase 1. The submission is made at the end of week 24 (WF-115).

### 6.1 Checklist

Verify every item on the day of submission; Apple policy moves.

**Account and setup**
- [ ] Apple Developer Program enrolled (organization account with D-U-N-S if the company exists) and Paid Applications Agreement, bank and tax forms complete.
- [ ] Bundle id `world.hermi.ios` with Push Notifications, Associated Domains, Sign in with Apple, In-App Purchase, App Attest.
- [ ] Small Business Program enrolled.
- [ ] Support URL, marketing URL and privacy policy URL live on our domain.
- [ ] In-app purchase products created with reference names, localized display names and descriptions, prices, review screenshots and review notes: `hermi_plus_monthly`, `hermi_plus_annual` (introductory offer: 7-day free trial, annual only), `hermi_trip_pass` (non-renewing subscription, 90 days), `hermi_credits_50`, `hermi_credits_150`, `hermi_credits_400` (consumable). No Family, Group or Pro product is created or visible.

**Build**
- [ ] Bundled web build; no `server.url`; release build, not debug; admin routes excluded.
- [ ] Privacy manifest (`PrivacyInfo.xcprivacy`) present, SDK manifests checked.
- [ ] Purpose strings in `Info.plist` for every permission requested (notifications, location when in use if "near me" ships). No calendar permission is requested: import uses the document picker and calendar feeds use a subscription link.
- [ ] No ATT prompt and no `NSUserTrackingUsageDescription`.
- [ ] Universal links work (`apple-app-site-association` served as JSON with no redirect).
- [ ] Crash-free sessions at least 99.5 percent over 100 or more TestFlight sessions.
- [ ] App works on the lowest supported iOS and on iPhone SE size.

**Features Apple checks**
- [ ] Guideline 4.2: offline trip viewing, push, native share sheet, file picker for calendar import, haptics, Apple Maps handoff, bottom tab navigation.
- [ ] Guideline 4.8: Sign in with Apple offered alongside Google.
- [ ] Guideline 5.1.1(v): in-app account deletion works and revokes the Apple token.
- [ ] Guideline 5.1.2(i): AI consent screen names the provider and what is sent, including pasted confirmations with personal data removed.
- [ ] Guideline 3.1.1 and 3.1.2: all digital plans and credits (Plus, Trip Pass, credit packs) use In-App Purchase; paywall shows price, period, trial terms, Terms and Privacy links and Restore; subscription info localized; review screenshots per product. The free Trip Pass for a first import and referral credits are free grants, not sold, and the UI never links to outside purchase.
- [ ] Guideline 3.1.3(e): partner links lead to physical travel services used outside the app, labeled as commission links. No web checkout for digital goods, and the web paywall only says "Upgrade in the iOS app".
- [ ] Guideline 3.1.2: "Cancel subscription" is one tap from the Account plan card and opens Apple's subscription sheet; "How billing works" and "How we earn" are live and linked from Settings and every paywall.
- [ ] Guideline 1.2: report and block on shared content and AI answers, contact info, moderation queue, 24 hour response; public pages have a Report link.
- [ ] Guideline 2.3.7 and 5.2: no competitor names in keywords or the app name; "Import from TripIt" appears only as descriptive text in the description and screenshots with a no-affiliation statement; no claim of partnership.
- [ ] Guideline 5.6.1: no reward (free pass, credits) is offered for a rating or review.
- [ ] Guideline 5.6 and 5.1.1: no dark patterns; data collection matches the privacy label.
- [ ] Age rating questionnaire answered; 13+ gate in place.

**Store listing**
- [ ] Name "Hermi: Group Trip Planner", subtitle "Plan together. Know the fare.", promotional text, description, keywords, category Travel.
- [ ] Screenshots 6.9 inch (1320 by 2868), up to 10: trip overview, itinerary on map, price alert, import from another app, AI plan with evidence labels, a Verify this plan result (green, amber and red rows with sources), offline, shared trip, present mode. Icon 1024 by 1024 without alpha.
- [ ] Localized metadata for en-US and one or two more storefronts.
- [ ] App Privacy labels match section 3.4.
- [ ] Release set to manual; phased release for updates.

### 6.2 Review notes (paste into App Store Connect)

```
Hermi helps people plan trips together: flights, places to stay, a day-by-day itinerary,
and a full-screen presentation of the plan. It can also import a trip from a calendar file
or pasted booking confirmations.

Demo account (no Sign in with Apple needed):
  Email: review@hermi.world   Code: use the "Reviewer sign in" button on the sign-in screen
  The account is on the Plus tier and has a pre-filled trip ("Lisbon in May"), two members,
  and 40 credits. A second account, review-free@hermi.world, is on the Free tier to see the
  paywall and the one-collaborator limit. Purchases work in the sandbox.

Where things are:
  - Account deletion: Settings > Account > Delete account.
  - Restore purchases: paywall and Settings > Purchases.
  - AI features: tap "Ask" on any trip. A consent screen names Anthropic and what is sent.
    Users can turn AI off in Settings > Privacy. AI answers are labeled and show sources
    ("Found on [site], checked [date]").
  - Import: Trips > New trip > Import, or Settings > Import. A sample calendar file
    (sample-trip.ics) and sample confirmation text (sample-confirmation.txt) are attached
    to these notes. An import that adds 3 or more items including a flight or a stay gives a
    free Trip Pass for that trip; nothing is tied to a rating or review.
  - Verify a plan: Trips > "+" > Verify a plan. Paste the attached sample-plan.txt; the
    results show sources ("Found on [site], checked [date]"). Checks cost credits shown
    before the tap; the reviewer account has credits.
  - Billing: Account > plan card > "Cancel subscription" opens the App Store sheet. The page
    "How billing works" and the page "How we earn" are linked from Settings and every paywall.
    The web app sells nothing: its paywall says "Upgrade in the iOS app".
  - Offline: turn on airplane mode after opening "Lisbon in May"; it stays readable.
  - Report and block: the "..." menu on shared trip content and on AI answers. Public
    sample pages on the web have a Report link.
  - Referral: Settings > Invite friends (credits only, no cash).

Purchases:
  Plus (monthly and annual), Trip Pass and credit packs use In-App Purchase. The free
  Trip Pass and referral credits are grants, not purchases.

Partner links:
  Buttons on hotels, tours, flights, cars and eSIMs open partner booking pages in an in-app
  Safari view. These are physical travel services used outside the app (Guideline 3.1.3(e)).
  Each button is labeled "We earn a commission if you book here." The app does not track
  users across other companies' apps or sites and shows no ATT prompt. Clicks are logged on
  our own server only.

Push notifications are used for price alerts, booked-fare price drops and trip reminders,
requested after the first invite or alert.

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
| External purchase language | Search the UI and listing for "web", "cheaper on our site", "lifetime"; the web paywall says "Upgrade in the iOS app" without a price, a purchase page or a checkout |
| Cancel path hidden | From the Account screen, reach the subscription sheet in one tap on a sandbox subscription; screenshot it for the notes |
| AI disclosure | Consent screen screenshot in the notes |
| Sign in with Apple relay emails failing | Send a test email to a relay address |
| Competitor names in metadata | Search keywords, subtitle and screenshots for competitor names outside the descriptive import text |
| Reward tied to a review | Search the UI and emails for "rate" or "review" next to any reward |
| Import sample files missing | Attach the sample files to the notes and test both on a clean device |
| User content without moderation | Screenshot the Report flow and show the admin queue in the notes if asked |

Budget two review cycles of 1 to 4 days. Keep the backend and demo accounts up during review.

## 7. Launch checklist

Gates match the month exits in the Phase 1 README and [09-build-roadmap.md](09-build-roadmap.md). Each item has an owner (the founder unless noted) and a link or artifact as evidence; each gate review is written to `docs/gates/month-N.md`.

### 7.1 Month 1 and Month 2 gates (validate, set up, core planning)

- [ ] Demand signal recorded against the "yes" written before the first interview; go decision signed (Month 1).
- [ ] Tenant-isolation test green in CI and on staging; RLS policies tested (direct SQL pass and no-variable pass) (Month 1).
- [ ] A signed-in user creates a trip on staging (Month 1).
- [ ] Free owner invites one collaborator and the second invite shows the paywall; two people plan a trip together on the web (Month 2).
- [ ] Restore drill passed once (PITR to a scratch database, smoke test against it) (Month 2).
- [ ] Contrast test green for every token pair in the Hermi palette (05 section 2.3), including `--tp-edge`, `--tp-warning-ink` and `--tp-sky-ink` on sky; axe clean on the core screens in light and dark.
- [ ] Sentry and structured logs live; log scan finds no tokens.

### 7.2 Month 3 gate (AI and credits)

- [ ] Credit reserve and settle tests green; ledger reconciliation query returns zero drift.
- [ ] Agent run cost measured over 50 runs on staging with p95 under $0.80; report saved.
- [ ] Every ceiling enforced in tests; the taster works once per account.
- [ ] AI spend alerts fired in a staging drill; every kill switch exercised, including the new `import.all`, `import.polling`, `ai.verify`, `ai.recheck`, `referrals.grant` and `public_pages` switches; AI off in under 30 seconds.
- [ ] Anthropic workspace limits set per environment.
- [ ] Evidence labels on every AI-saved fact (eval gate 100 percent); injection evals at 0.
- [ ] Evidence freshness: a 15-day-old finding shows "May be out of date" and a recheck moves the date, refunds when unreachable and never searches (scenario 23).
- [ ] AI consent live; consent required before any AI call.

### 7.3 Month 4 gate (money, imports, admin essentials)

- [ ] Webhook contract tests green; replay test run.
- [ ] Sandbox purchases pass end to end on the harness for Plus monthly and annual, Trip Pass and every credit pack.
- [ ] Affiliate: disclosure text present on every partner placement (automated UI check), `/go` tests green, clicks and conversions visible in the admin overview.
- [ ] Imports: golden files pass; fuzz run clean (Hypothesis on every pull request, Atheris 30 minutes); SSRF table refused for both feed import and link preview; PII corpus shows zero leaks; first-import reward granted once and only under the settled conditions (3 items including a flight or a stay, verified email, no active Plus); the TripIt, Tripsy and Wanderlog entries and pasted places work; the rival help-page check is dated.
- [ ] Verify this plan works through the API on staging: extraction and checking evals run, the false-green and evidence gates are measured, credits settle per item (scenario 22).
- [ ] Booked-fare alert drill with a fake fare drop (5 percent and $10 thresholds, once per flight every 7 days, no partner link).

### 7.4 Before TestFlight external testing (Month 5 gate)

- [ ] Sandbox purchase matrix passed (section 1.7) on the real purchase flow.
- [ ] Push works end to end (sandbox then production APNs).
- [ ] Universal links and the invite flow from Messages verified on device.
- [ ] Offline trip verified in airplane mode on a real device; offline edits sync on reconnect.
- [ ] Account deletion revokes the Apple token (verified in Apple's settings).
- [ ] App Attest flow verified on a real device; fallback verified.
- [ ] Calendar feed subscribes in Apple Calendar and Google Calendar; rotating the token breaks the old link.
- [ ] Keep checking this calendar: a real TripIt or Google feed is polled every 6 hours, a change produces a preview, nothing applies without confirmation, turning it off deletes the stored address.
- [ ] The sync indicator and the status banner behave on a real device in airplane mode and with a degraded component in staging.
- [ ] Accessibility pass with VoiceOver and Dynamic Type, and a check that `--tp-edge` borders, `--tp-warning-ink` text and `--tp-sky-ink` text on sky hold their contrast in the native shell in light, dark and Increase Contrast.
- [ ] 30 beta testers, crash-free sessions above 99.5 percent over 100 or more sessions; beta report saved.
- [ ] Export and deletion working; privacy policy, terms and affiliate disclosure published.

### 7.5 Before public launch (Month 6 gate)

- [ ] Penetration test complete; no open high or critical findings (WF-110).
- [ ] Load test at 10x expected launch traffic passed; Anthropic rate limits raised and tested at 3x peak.
- [ ] All runbooks in section 8 written, reviewed and each drilled once in staging (spend spike, provider outage with a status page incident posted, webhook backlog, bad deploy rollback, import abuse, public page takedown, a wrong fact in a plan check; breach tabletop).
- [ ] On-call routing tested (a real page reaches the phone at night).
- [ ] Backups: PITR healthy, weekly off-provider dump verified by restore.
- [ ] Dependency audit clean; secrets rotated after beta; secret scan of history clean.
- [ ] Affiliate: program terms filed, conversion import working for Travelpayouts, Viator and Stay22.
- [ ] Public pages: privacy scan clean, report flow and takedown drilled, sitemap lists only opted-in and sample pages; `/vs` facts all sourced and under 90 days old.
- [ ] Referral and import reward abuse controls tested with the abuse scenarios in section 2.8.
- [ ] Provider terms recheck: SerpApi decision, Geoapify, Travelpayouts; Airbnb, Vrbo and Booking.com remain link only.
- [ ] Support live: inbox, macros (including import problems), FAQ, refund and cancellation guidance, abuse inbox.
- [ ] Data processing agreements on file for every processor.
- [ ] App Review passed; release set to manual.
- [ ] Status page live with its five monitors and a practice incident posted; announcement drafted; launch day owner and rollback plan named.
- [ ] Verify this plan: all gates in section 1.5 pass (false green under 2 percent, invented places never green, evidence valid 100 percent, plan check p95 under $0.02 per item) or the `verify_plan` flag stays off.
- [ ] Trust pages live and reviewed: How we earn lists every active partner, How billing works matches the paywall prices, the cancel link opens the subscription sheet, the trial reminder email carries it.
- [ ] Android Chrome: the manual checklist in section 1.9 passed on a real phone and tablet; the install guide screenshots match the current Chrome menus.

### 7.6 Launch day and first 72 hours

- [ ] Release manually; watch crash-free rate, API 5xx, queue age, AI spend, webhook lag, signups, purchases, import failures, referral rewards.
- [ ] Check a real purchase, a real invite, a real AI action, a real `/go` click, a real ICS import and a real public page view in production with the team's own accounts.
- [ ] Reply to every review and support message within a day; clear the content reports queue daily.
- [ ] No P0 open after 72 hours, crash-free at least 99.5 percent, API errors under 1 percent. Otherwise hold the marketing push.
- [ ] Hotfix path rehearsed: a fix reaches staging in under 30 minutes and production in under 2 hours (backend) or submitted to App Review with expedite (iOS).

### 7.7 After launch

- Weekly: metrics review, AI and provider bill review, dead letter and support sweep, import failure and reward review, content reports review.
- Monthly: dependency audit, cost per user, gross margin per tier, affiliate conversion reconciliation, flag cleanup, `/vs` fact freshness, fuzz corpus update from real failures.
- Quarterly: restore drill (including deletions staying deleted), key rotation, kill switch drill, load test, access review of admins, privacy label recheck.
- Twice a year: affiliate and provider terms review. Yearly: penetration test, DPIA review, Apple renewal.

## 8. Runbooks

Each runbook also lives in `docs/runbooks/` as its own file with the same headings. Format: detect, contain, fix, recover, follow up. Every incident gets a short written review within 5 days (what happened, timeline, cause, what changes). Status page updates go out within 15 minutes of a confirmed user-facing incident.

### 8.1 AI spend spike

**Detect.** `ai_spend_guard` page (global daily over cap, hourly over 25 percent of cap, or a single account over 3x its ceiling), or an Anthropic workspace 80 percent alert.

**Contain (first 10 minutes).**
1. Open the admin AI spend dashboard: spend by hour, feature, tier, account and model.
2. If a single feature or agent runs is the source, turn on `ai.agent_runs` (or the matching switch, such as `ai.import` or `ai.verify`). If unclear, turn on `ai.all`. The app shows "AI is paused, your plans are safe".
3. If one account is the source, suspend its AI from the admin console (reason logged) and check its `runs` for loops.
4. If the source is free accounts (signup farming, reward farming), turn on `ai.free_tier`, tighten signup limits (`signups` switch if needed) and check section 8.7.

**Find the cause.**
- Runs over caps (turn, search, fetch, dollar): a bug in the loop or the tool executor. Check `run_events` for repeating tool calls.
- Cache hit rate collapse: a prompt version bump or cache key bug sending everything to live search.
- Retries: a provider error causing repeated full-price retries (check retry rate).
- Price table wrong: real spend does not match `ai_usage` cost; compare with the Anthropic usage export.
- Abuse: many new accounts from one device, IP range or email domain.

**Fix and recover.** Ship the fix or roll back the prompt or model config, verify on staging with the fake client and a small live budget, turn switches off one at a time (agent runs last), and watch the next hour. Refund credits for runs that failed because of our bug (admin bulk credit grant with a reason). If the workspace limit was hit, raise it only after the cause is known.

**Follow up.** Add the failing case to the evals, add or tighten an alert, and review whether any per-run cap should be lower. Record the dollar impact.

### 8.2 Provider outage

Covers Anthropic, SerpApi, Travelpayouts, Geoapify, Supabase Auth, RevenueCat, APNs, Resend, Cloudflare and Render.

**Detect.** Provider success rate alert, a status page from the provider, or user reports.

**Contain.**
1. Confirm on the provider's status page and with a direct test call from a staging shell.
2. Turn on the matching kill switch (`provider.<name>`, `ai.all`, `push.all`, `email.all`) only if retries are causing harm (queue growth, spend, user-facing errors). Otherwise let retries with backoff work.
3. Post an incident on the public status page (Better Stack, 02 section 8.1) within 10 minutes of a degraded component, in plain words with the time; the in-app banner follows the page state through `GET /public/status`.

**Per provider.**

| Provider | User impact and action |
|---|---|
| Anthropic | AI paused or queued (pasted confirmation import, Verify this plan and rechecks unavailable; file, feed, Google Maps and pasted-places import keep working); credits stay reserved up to 30 minutes then release; cached research still served; consider `ai_force_haiku` if only Sonnet is degraded |
| SerpApi | Flag `serpapi_live_fares` off; fares fall back to cached Travelpayouts with an age label; no credit charge for empty results |
| Travelpayouts | Show last observations; alerts pause; affiliate links still work |
| Geoapify | Serve `places_cache`; manual place entry still works |
| Supabase Auth | New sign-ins blocked, existing sessions work (JWKS cached 1 hour, extend the cache window to 24 hours by config if the outage is long); do not sign anyone out; status banner on the sign-in screen |
| RevenueCat | Purchases may delay unlocking; use `POST /purchases/sync` and the reconcile job; do not revoke access on missing events |
| APNs or Resend | Retry; in-app feed shows alerts; invites can be shared as links; switch to the standby email provider after 30 minutes |
| Cloudflare | DNS or WAF outage takes the site down and public pages with it; the iOS app keeps showing cached trips offline; follow the provider's guidance and update status |
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
- Bad secret: set the new value (webhook endpoints accept current and previous secrets), then replay events that returned 401 from the provider's dashboard (RevenueCat can resend).
- Large backlog: add worker instances on the `api` lane; ordering is by event timestamp so replay is safe.

**Recover and verify.** Run `reconcile_entitlements` for affected users. Buyers who paid and did not get access: grant the entitlement manually from admin (audited) and let the reconcile confirm. Check credit ledger drift and grant duplicates (unique keys make duplicates impossible; confirm zero).

**Follow up.** Add an alert for the specific cause, add the failing payload to the contract fixtures.

### 8.4 Data breach

**Detect.** Sentry or log anomaly, tenant-test failure, unusual admin activity, a provider breach notice, a leaked key alert from secret scanning, a researcher report to `security@hermi.world`, or a user report of seeing another person's data (including a public or shared page that shows private fields).

**Contain (first hour).** The incident lead is the founder.
1. Open an incident log (private doc): time, who, what is known. Everything done is written down with timestamps.
2. Stop the bleed: rotate the exposed keys (use `docs/runbooks/key-rotation.md`), revoke sessions if tokens are exposed (Supabase sign-out for all, refresh token revocation), turn on `maintenance` (read-only) or disable the affected route or feature by kill switch (`public_pages` for a page leak, `import.feed` for an SSRF finding), block attacker IPs at Cloudflare, suspend affected admin accounts.
3. Preserve evidence: snapshot the database, export logs for the window, do not delete anything. Keep `audit_log` intact.

**Assess (within 24 hours).**
- What data, which tables, how many users, what period. Use logs, `audit_log` and RLS tests to bound the scope.
- Was it personal data of EU or UK residents, children, payment data (we hold none, Apple holds it), or special categories?
- Is it still possible? Reproduce and confirm the fix in staging.

**Fix.** Patch the cause, add a failing test first (tenant suite, security test, fuzz regression), deploy through the normal pipeline with expedite, rotate anything that could have been seen.

**Notify.**
- Regulators: within 72 hours of becoming aware where GDPR or other law applies (breach notification template in `docs/runbooks/breach-notice.md`). State law notices in the US on their timelines.
- Users: without undue delay when there is a high risk to them. Plain language: what happened, what data, what we did, what they should do, contact. Send by email and in-app banner.
- Partners and processors: Apple (if a developer account or app is affected), RevenueCat, affiliate networks if their data or tracking is involved. Insurers and counsel engaged early.
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
5. Jobs that ran with bad code: check `runs` and `credit_ledger` for wrong charges during the window; refund through admin in bulk with a reason. Check `trip_passes` and `credit_grants` for wrongly issued import or referral rewards.

**Web rollback.** Cloudflare Pages keeps previous deployments: promote the previous one (under 1 minute). Users with the old bundle still loaded keep working because the API stays backward compatible.

**iOS rollback.** A shipped app cannot be rolled back. Options: turn off the feature by flag, raise `min_app_version` only as a last resort, or submit a fixed build with an expedited review request. The backend stays compatible with the last 3 app versions so a bad build does not force a backend rollback.

**Follow up.** Write the review, add the missing test or smoke check that would have caught it, and review whether the release should have gone out behind a flag or at a percentage.

### 8.6 Import abuse or a hostile file

**Detect.** Import SSRF, parser sandbox or redaction alerts (section 5.3), a spike of `import_failed` with `blocked_url`, a worker memory or CPU alarm, or a Sentry issue from the parser.

**Contain.**
1. If feed fetches or polling are suspect, turn on `import.polling` (kill switch) at once; it stops only the 6-hourly polling. For a broader problem turn on `import.all`, which stops every import path and the free-pass reward; for a redaction problem in pasted text turn on `ai.import` (and `ai.verify` for pasted plans).
2. Check the `provider_calls` host list (hosts only, never URLs) and rate limit rows for the account or IP; suspend the account's imports from admin if one source is the cause.
3. If a worker was affected, restart the worker service; the sandbox limits should already have killed the child process.

**Find the cause.**
- Was a hostile URL allowed? Reproduce with the hostile URL table and fix `security/ssrf.py` with a failing case first.
- Did a file exceed a limit without being stopped? Add the file to the fuzz corpus as a regression.
- Did personal data reach a model request? Treat it as a privacy incident (section 8.4) and add the text to the redaction corpus.

**Recover.** Ship the fix, rerun the fuzz and SSRF suites and the extended Atheris run, turn the switches off again one at a time. Review rewards granted during the window and revoke any that came from the abuse.

**Follow up.** Update the threat model and the parser limits; note the attack in the penetration test scope.

### 8.7 Reward or referral abuse

**Detect.** Reward alerts (section 5.3), a daily report of referrers near their caps, many new accounts sharing a device key or IP hash, or referred accounts that never return.

**Contain.** Turn on `referrals.grant` to pause referral credit grants (codes can still be entered). For import rewards, add a temporary higher item minimum or turn off the reward only (the import paths keep working).

**Fix.** Revoke rewards from the admin console (audited; the ledger reverses the credits and the pass is ended), block the device keys and normalized emails involved, tighten caps or the activation rule, and confirm no purchased credits were affected.

**Follow up.** Add the pattern to the abuse tests, review whether the activation rule or caps need to change, and record the credits and provider spend lost.

### 8.8 Public page takedown

**Detect.** A content report, an abuse email, a legal notice, or a privacy leak found by the page scan.

**Contain.** From the content reports queue disable the link or hide the page (returns 410, sitemap entry removed and CDN purged within 5 minutes). For anything systemic turn on `public_pages`, which takes every public page offline.

**Fix.** Review the content and reporter, suspend the owner's sharing if the content breaks the terms, and notify the owner with the reason. If the page exposed private fields, treat it as a privacy incident (section 8.4) and fix the redaction with a failing test first.

**Follow up.** Reply to the reporter within 24 hours, add the case to the redaction sentinel tests if it was a leak, and review the report volume for patterns.

### 8.9 Wrong fact shown by Verify this plan

**Detect.** Reports on a green or amber row, the false-green alert (section 5.3), thumbs down on a plan check, or an eval regression.

**Contain.** If more than one wrong green is confirmed, turn on `ai.verify` (the list of places and imports keep working, checking pauses) and leave `ai.recheck` on unless rechecks are wrong too. A single case does not need a switch.

**Find the cause.** Open the run (sizes and verdict reasons, no pasted text): was the page grounded and did it really contain the value? Was the place match wrong (name similarity or distance)? Was a stale `place_check` cache entry served? Add the case to the checking eval set with a failing test first.

**Fix and recover.** Ship the fix behind a canary (5 percent for 48 hours, 06 section 10), expire the affected `place_check` cache keys, rerun the suite and turn the switch off again. Refund the credits of the affected checks if the verdict was our error (an `adjustment` grant with a reason).

**Follow up.** Record the false-green rate in the monthly accuracy note and review whether the tolerance (15 percent price, 60 minute hours) or the match threshold (0.8, 30 km) needs to change.
