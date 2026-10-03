# 07: Local app to App Store

Part of the [business plan](README.md). The decisions of record in the README override anything here.

Written 2026-09-30, updated for the product name Hermi and the new tiers and revenue lanes. The app is called Hermi from here on; the repository and the personal install keep the working name Trip Planner. Apple policy and US court rulings move fast, so every rule marked "verify" must be re-read on the day of submission.

This file is the master transition checklist: every change needed to go from the local Windows app to a public App Store launch, phase by phase, with a pointer to the file that holds the detail. It also covers the mobile approach, frontend changes, in-app purchases, the App Review checklist and the launch plan. Business case: [01-business-plan.md](01-business-plan.md). Tiers and credits: [02-pricing-tiers.md](02-pricing-tiers.md). AI: [03-ai-features-and-costs.md](03-ai-features-and-costs.md). Accounts: [04-users-and-accounts.md](04-users-and-accounts.md). Hosting: [05-infrastructure.md](05-infrastructure.md). Data and providers: [06-database-and-data-integrations.md](06-database-and-data-integrations.md). Affiliate revenue: [08-affiliate-revenue.md](08-affiliate-revenue.md).

## 1. Where the app is today

| Area | Current state | Consequence for mobile |
|---|---|---|
| API client | `frontend/src/lib/api/client.ts`: `openapi-fetch` with `baseUrl: window.location.origin`, sends `X-Trip-Planner: 1`, listens for 401 | In a native shell the origin is `capacitor://localhost`, so the base URL must be configurable. |
| Auth | One shared passcode and a session cookie (`auth-gate.tsx`, `login-screen.tsx`, `lib/api/auth.ts`); this PC passes straight through | Cookies are fragile in WKWebView across origins. Needs real sign-in and bearer tokens ([04-users-and-accounts.md](04-users-and-accounts.md)). |
| Hosting | `backend/tripplanner/spa.py` serves `frontend/dist` from FastAPI | Fine for personal mode. Hosted web moves to Cloudflare Pages; the native bundle ships inside the app; the API lives on its own host (CORS needed). |
| Router | React Router 7, `createBrowserRouter`, lazy chunks, present mode outside `AppShell` | Works in Capacitor with a small config change (4.1). |
| Viewport | `index.html` already has `viewport-fit=cover` | Good start for safe areas. |
| Layout | `AppShell` with `sidebar-nav.tsx` and `trip-switcher.tsx` | Desktop sidebar. Needs a bottom tab bar under a width breakpoint. |
| Bundle | About 470 kB first load; MapLibre about 1 MB, lazy | Fine when bundled locally. |
| Data layer | TanStack Query 5, generated types via `npm run gen:api` | Query persistence gives an offline cache almost free. |
| Web-only pieces | `@fullcalendar/react`, `recharts`, MapLibre, full-screen present mode | FullCalendar is the riskiest for touch. Present mode needs rethinking on phones. |
| Tests | vitest, pytest, Playwright smoke in Edge | Add a mobile-viewport Playwright project and native smoke tests (Maestro). |
| Agents | The worker runs Claude Code routines on the owner's personal subscription | Cannot serve customers. Moves to the Claude API in Phase 0 ([03-ai-features-and-costs.md](03-ai-features-and-costs.md)). |
| Database and dev machine | Local Postgres on Windows 11, one household | Hosted Postgres on Render ([05-infrastructure.md](05-infrastructure.md)); iOS builds need macOS. |

## 2. Master transition checklist

Effort assumes one developer with Claude Code, about 25 to 35 focused hours a week (part time; halve the calendar time if full time). Ranges lean optimistic for code and pessimistic for approvals and store waits. This table matches the README roadmap.

| Phase | Effort | Calendar | Gate to move on |
|---|---|---|---|
| M0: validate | 2 to 4 weeks | Before week 1 | Landing page, waitlist, 10 user interviews, a clear signal people want it |
| 0: foundations | 3 to 4 weeks | Weeks 1 to 4 | Agents run on the Claude API with metering; Docker image; CI |
| 1: hosted web beta | 6 to 8 weeks | Weeks 5 to 12 | Accounts, sharing, entitlements, ledger; 4-week retention measured |
| 2: iOS TestFlight | 5 to 7 weeks | Weeks 13 to 19 | Capacitor app, purchases, push, account deletion |
| 3: public launch | 3 to 4 weeks (includes review cycles) | Weeks 20 to 23 | App Review passed, support and monitoring in place |
| 4: growth | Ongoing | Week 24 on | Android, shareable trip pages for SEO, Pro, group payments, concierge (if not live earlier), Hermi for Advisors |

Total to public launch: about 5 to 6 months part time, about 3 to 4 months full time. The biggest schedule risk is Phase 1 (multi-tenancy and entitlements), not the mobile work. Do not start a phase until the previous gate is met.

### M0: validate (2 to 4 weeks)

Goal: find out whether anyone wants this before rewriting anything. No app code changes.

| Change | Detail in |
|---|---|
| Confirm the name Hermi (trademark search including the Hermio and Hermès risks in brand/BRAND.md, App Store name "Hermi: Group Trip Planner" and subtitle availability) and buy hermi.world | [01-business-plan.md](01-business-plan.md) |
| Landing page with waitlist capture and email set up (support, no-reply; SPF, DKIM, DMARC) | [01-business-plan.md](01-business-plan.md), [05-infrastructure.md](05-infrastructure.md) |
| 10 user interviews with couples and small groups; write down the signal that counts as "yes" before starting | [01-business-plan.md](01-business-plan.md) |
| Paywall and price test copy shown to interviewees (Trip Pass $9.99, Group Trip Pass $19.99, Plus $5.99 a month or $39.99 a year, Family $8.99 a month or $59.99 a year) | [02-pricing-tiers.md](02-pricing-tiers.md) |
| Answer the open provider questions that could change the numbers (SerpApi terms, Geoapify terms, Travelpayouts rates) | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |

Gate: a clear signal that people want it. If not, stop here and keep the app personal.

### Phase 0: foundations (3 to 4 weeks)

Goal: make the codebase safe to open up, and move the AI off the owner's subscription. Nothing user-facing changes.

| Change | Detail in |
|---|---|
| Move agents from the Claude Code CLI to the Claude Messages API with tool use, run in our own worker. `submit_flight_quotes`, `add_note` and `finish_run` become in-process client tools; evidence rules and blocked domains (Airbnb, Vrbo, Booking) stay | [03-ai-features-and-costs.md](03-ai-features-and-costs.md) |
| Metering: per-run caps (20 turns, 10 searches, 10 fetches, `medium` effort, $0.80 hard stop, one run at a time per account), cost logging, prompt caching | [03-ai-features-and-costs.md](03-ai-features-and-costs.md) |
| Turn scheduled agent routines off for hosted mode (they return with Pro); scheduled work becomes API price checks plus batch scans | [03-ai-features-and-costs.md](03-ai-features-and-costs.md), [05-infrastructure.md](05-infrastructure.md) |
| Split "personal mode" from "hosted mode" by config; remove Windows-only assumptions from hosted paths | [05-infrastructure.md](05-infrastructure.md) |
| Docker image for API and worker; CI on Linux (pytest, vitest, lint, Playwright) | [05-infrastructure.md](05-infrastructure.md) |
| Staging and production on Render behind Cloudflare; Postgres-backed queue (Procrastinate); secrets in the host, `.env.example` updated | [05-infrastructure.md](05-infrastructure.md) |
| Postgres with Alembic migrations as a pre-deploy step; follow `.claude/rules/database-migrations.md` | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| Provider terms audit; keep the rule against scraping Airbnb, Vrbo and Booking (links only) | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| Decisions recorded: legal entity, developer account type, tier structure, Trip Pass semantics | [01-business-plan.md](01-business-plan.md), [02-pricing-tiers.md](02-pricing-tiers.md) |
| Start Apple Developer enrollment (days to weeks); arrange Mac access (Mac mini or Xcode Cloud) | Section 6.1 and 6.11 |

Gate: agents run on the Claude API with metering; Docker image; CI. Also confirm a staging deploy works from a merge to main and one agent run finishes within its cost cap.

### Phase 1: hosted web beta (6 to 8 weeks)

Goal: a real product on the web that strangers can sign up for, with payments off, proving the core loop and the unit economics.

| Change | Detail in |
|---|---|
| Accounts on Supabase Auth (Sign in with Apple, Google, email code); our own `users` table; token handling in `client.ts` | [04-users-and-accounts.md](04-users-and-accounts.md), 4.1 |
| Schema: `trip_members`, UUID public ids, `owner_user_id` and `linked_user_id` on `people`, row-level security behind app checks; migrate the existing local data | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| Trip sharing and invites by link; roles; only the owner pays, invitees join free | [04-users-and-accounts.md](04-users-and-accounts.md) |
| Entitlements table, server-side limit checks and the credit ledger (Free limits, 12 credits a month and the lifetime taster run) | [02-pricing-tiers.md](02-pricing-tiers.md), [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| Upgrade screens are a waitlist or "coming with the app" page; no web payments | [02-pricing-tiers.md](02-pricing-tiers.md) |
| Flight data: Travelpayouts cached fares as the free baseline; live fares behind the provider interface (SerpApi under a feature flag) | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| Join Travelpayouts (also the launch affiliate network); build the `/go/<click_id>` redirect with stored link templates only (no open redirects), a random per-click sub-id, the `affiliate_programs` and `link_clicks` tables, and the nightly conversion pull; disable link previews for Airbnb, Vrbo and Booking.com domains on the hosted server | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) section 6, [08-affiliate-revenue.md](08-affiliate-revenue.md) |
| Frontend: `VITE_API_BASE_URL`, new sign-in and onboarding screens replacing the passcode login, empty and error states, responsive layout with bottom tab bar (4.3) | 4.1, 4.3, section 7 |
| AI consent screen, account deletion backend, data export, privacy policy and terms | [04-users-and-accounts.md](04-users-and-accounts.md), 6.3 to 6.6 |
| Observability (Sentry, PostHog, uptime monitor, structured logs), point-in-time recovery with a tested restore | [05-infrastructure.md](05-infrastructure.md) |
| Abuse controls: rate limits per user and IP, email verification, provider-spend ceilings (Free $0.25, Plus $2.25 a month) | [02-pricing-tiers.md](02-pricing-tiers.md), [05-infrastructure.md](05-infrastructure.md) |
| Beta: 50 to 200 invited users from the M0 waitlist; weekly feedback loop | [01-business-plan.md](01-business-plan.md) |

Gate: accounts, sharing, entitlements and ledger working; 4-week retention measured and recorded. Also require zero cross-tenant leaks in automated tests, AI cost per active user within the modeled ceilings, a restore-from-backup drill done once, and mobile web usable on iPhone Safari.

### Phase 2: iOS TestFlight (5 to 7 weeks)

Goal: a native app that passes the "not a website" test, with purchases working in sandbox.

| Change | Detail in |
|---|---|
| Capacitor project (`ios/`), bundled not remote, icon, splash, bundle ID, signing, Xcode Cloud or Fastlane CI | 3, 6.10, 6.11 |
| Native plugins: push, share, haptics, status bar, keyboard, secure storage, in-app review, calendar, app URL open, Sign in with Apple | 4.4 |
| Offline cache and mutation queue; per-trip download; offline banner | 4.2 |
| Universal links and the AASA file; invite flow from Messages to app | 4.4 |
| RevenueCat over StoreKit 2; launch products in App Store Connect; paywall, restore, webhook, credit grants, Trip Pass binding | 5, [02-pricing-tiers.md](02-pricing-tiers.md) |
| APNs push and the price-drop job; notification preference center | 4.4, [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| In-app account deletion (with Sign in with Apple token revoke), report and block, AI consent | 6.3, 6.6, [04-users-and-accounts.md](04-users-and-accounts.md) |
| Privacy manifest, nutrition labels, accessibility pass with VoiceOver | 6.4, 4.6 |
| Affiliate click redirect (`/go/<click_id>`, built in Phase 1) used from the app, so no tracking SDKs and no ATT prompt | 6.5, [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| In-app browser choice for affiliate links: `SFSafariViewController` through the Capacitor Browser plugin (not an embedded WKWebView, not an injected-JS webview); measure attribution loss against opening in Safari | 3, 6.5, [08-affiliate-revenue.md](08-affiliate-revenue.md) |
| Affiliate disclosure text ("We earn a commission if you book here.") beside every partner button, an "Ad" label on UK and EU storefronts, and lists that say how they are sorted | 6.5, [08-affiliate-revenue.md](08-affiliate-revenue.md) |
| App Review notes that explain affiliate links under Guideline 3.1.3(e): they lead to physical travel services consumed outside the app, while Plus, Family, Trip Pass, Group Trip Pass and credit packs use in-app purchase; no ATT prompt because there is no cross-app tracking | 6.5, 6.9 |
| App Privacy labels updated to mention click logging (which partner button was tapped, linked to the user, for app functionality and analytics, not used for tracking) | 6.4 |
| Family plan: household invites inside the app, pooled credits, payer rules, leave and cooldown limits; Apple Family Sharing stays off | 5.2, 5.8, [04-users-and-accounts.md](04-users-and-accounts.md) section 3.6 |
| Group features behind the Group Trip Pass: polls, cost splitting (expense and settle-up records only, no money moves in the app yet), room-block request form behind a flag | [04-users-and-accounts.md](04-users-and-accounts.md) section 3.7, [06-database-and-data-integrations.md](06-database-and-data-integrations.md) section 2.9 |
| Stripe account in test mode, webhook route and event table (no live payments) | 5.8, [05-infrastructure.md](05-infrastructure.md) section 5.6 |
| TestFlight: internal from week 1, external (30 to 100 testers) from week 4 | 6.10 |

Gate: Capacitor app, purchases, push, account deletion. Also require crash-free sessions of at least 99.5 percent over 100 or more sessions, every sandbox purchase scenario passing (purchase, cancel, upgrade from Plus to Family, downgrade, refund, restore on a second device, billing retry, Trip Pass and Group Trip Pass bound to a trip, a Family member joining and leaving a household), a trip fully browsable in airplane mode on a real device, and a self-check against Guidelines 4.2, 4.8, 5.1.1(v), 3.1.2 and 1.2.

### Phase 3: public launch (3 to 4 weeks)

Goal: approved, live, with the launch machinery ready.

| Change | Detail in |
|---|---|
| Final listing: name, subtitle, keywords, screenshots, localized for top storefronts, age rating | 6.7, 6.8 |
| Review notes and a demo account verified against production | 6.9 |
| Submit and handle feedback (budget two cycles of 1 to 4 days each) | 6.9 |
| Load test at 10 times expected launch traffic; alerts; status page | [05-infrastructure.md](05-infrastructure.md) |
| Support live (inbox, macros, FAQ); refund and cancellation guidance | 7, 8.2 |
| Provider recheck: SerpApi flag decision and Skyscanner Partners application status | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| Prepare the direct affiliate applications (Expedia Group for Vrbo, Booking.com after confirming its current network, Skyscanner, Airalo, GetYourGuide): live App Store link, screenshots of disclosure and placement, traffic numbers from the beta | [08-affiliate-revenue.md](08-affiliate-revenue.md) |
| Concierge ("Have a human book this") and the group room-block request go live if the host travel agency agreement is signed (consent screen, request queue, admin page); otherwise they move to Phase 4 and the launch build hides them | [04-users-and-accounts.md](04-users-and-accounts.md) section 3.9, [05-infrastructure.md](05-infrastructure.md) section 4.7 |
| Review notes cover Stripe-paid real-world services and the absence of advisor purchases in the app | 5.8, 6.9 |
| Launch content and phased release | 8.1 |

Gate: App Review passed; support and monitoring in place. Also require crash-free at least 99.5 percent, API error rate under 1 percent, and no P0 in the first 72 hours.

### Phase 4: growth (ongoing)

| Change | Detail in |
|---|---|
| Pro ($11.99 a month or $99 a year) launches when measured agent cost is $0.60 or less per run over 200 runs, or when more than 15% of Plus payers buy agent-run credits. Add its products to the existing subscription group | 5.2, [02-pricing-tiers.md](02-pricing-tiers.md), [03-ai-features-and-costs.md](03-ai-features-and-costs.md) |
| Shareable public trip pages and SEO guides (server-rendered, separate from the SPA) | [01-business-plan.md](01-business-plan.md) |
| Group payments through Stripe: pay your share of real-world trip costs, reminders, settle-up records. Needs counsel's opinion on money transmission first (Stripe Connect or supplier payment links) | 5.8, [05-infrastructure.md](05-infrastructure.md) section 5.6 |
| Concierge and room blocks, if not live at launch; first commission statements reconciled | [04-users-and-accounts.md](04-users-and-accounts.md) section 3.9, [08-affiliate-revenue.md](08-affiliate-revenue.md) |
| Hermi for Advisors (year 2, web only): org and seat tables, client trip workspaces, Stripe Billing at $29 a seat a month or $24 annual, no advisor purchase or sign-up inside the iOS app | 5.8, [04-users-and-accounts.md](04-users-and-accounts.md) section 3.8 |
| Printed trip books and posters (year 2, ordered on the web, physical goods through Stripe) and labeled partner guides | 5.8, [06-database-and-data-integrations.md](06-database-and-data-integrations.md) section 2.10 |
| LiteAPI in-app hotel booking (year 2 or later, only after click data shows strong booking intent): needs its own review of Apple rules for booking physical services and of merchant-of-record terms | [06-database-and-data-integrations.md](06-database-and-data-integrations.md) section 4.5 |
| Android: Capacitor Android, Play Billing through RevenueCat, FCM, App Links; 4 to 6 weeks | 3, 5.1 |
| Retention loop: paywall experiments, win-back offers, lifecycle messages, referral | [01-business-plan.md](01-business-plan.md) |
| From month 3 after launch: submit the direct network applications (Expedia Group, Booking.com, Skyscanner, Airalo, GetYourGuide) and replace the model's affiliate inputs with measured clicks, conversions and attribution loss | [08-affiliate-revenue.md](08-affiliate-revenue.md), [01-business-plan.md](01-business-plan.md) |
| "Before you go" checklist (`checklist_items`; at least half unmonetized, visas link to official sites first, insurance uses insurer-approved copy only) and the after-trip "Was your flight delayed?" prompt, free on every tier | [08-affiliate-revenue.md](08-affiliate-revenue.md), [06-database-and-data-integrations.md](06-database-and-data-integrations.md) |
| Native extras: Live Activities, widget, Face ID lock, offline map tiles | 4.4 |
| Move hosting to AWS or Google Cloud around 50k MAU or $1,500 a month; Redis around 10k MAU | [05-infrastructure.md](05-infrastructure.md) |

Guideline targets, not gates: D30 retention at least 15 percent, free to paid conversion 3 to 5 percent, monthly subscriber churn under 8 percent, LTV to CAC above 3. The kill rule in 8.2 applies.

## 3. Mobile approach

### 3.1 Options compared

| Criterion | Capacitor around the React app | React Native / Expo rewrite | PWA only |
|---|---|---|---|
| Reuse of React 19 code | About 90 to 95 percent | About 20 to 30 percent (types, client, logic; every screen rewritten) | 100 percent |
| Native feel | Good with plugins; still a WebView | Best | Weakest on iOS |
| App Store presence and IAP | Yes, RevenueCat Capacitor plugin | Yes | No listing, no StoreKit |
| Push | `@capacitor/push-notifications` | `expo-notifications` | iOS Web Push only when installed; unreliable |
| Offline | Local bundle plus persisted query cache, SQLite if needed | Best tooling | iOS evicts storage |
| Maps and calendar | MapLibre and FullCalendar work as is (calendar needs touch tuning) | Both rewritten | Work as is |
| Guideline 4.2 risk | Medium; mitigated by native features | Lowest | n/a |
| Solo cost to first TestFlight | 3 to 5 weeks | 3 to 5 months | 0, but no store |
| Android later | Nearly free | Nearly free | n/a |

### 3.2 Guideline 4.2 (minimum functionality)

Apple rejects apps that feel like a website in a frame, not apps that use a WebView. This app is well placed: accounts, per-user data, offline trips, push, purchases, calendar export and share sheet. Make sure the submission build has:

1. Assets and JS bundled inside the app. Never use `server.url` in production.
2. Push that does something (price drops, day-of reminders).
3. Offline trip viewing.
4. Native share sheet, haptics, Apple Maps handoff, universal links.
5. App-like navigation (bottom tabs), no desktop layouts or browser chrome.
6. Sign in with Apple, a working StoreKit purchase flow, and Restore.

### 3.3 Decision

**Capacitor around the existing React app, bundled, with a small set of native plugins.** The hosted web beta ships first from the same code (it is the web app, not the mobile strategy).

- A solo developer cannot maintain a React Native rewrite plus a web app plus SEO pages. Reusing the tested 90 percent is the economic argument.
- The token plumbing (`frontend/src/index.css`) and `.claude/rules/frontend.md` carry over; the values are replaced by the Hermi palette (app-buildout 05 section 2).
- Revisit React Native only if App Review pushes back twice on 4.2, or analytics show WebView scroll or map jank driving retention loss. Keep `lib/` free of DOM assumptions so a later native client can reuse it.
- PWA-only is rejected: no App Store IAP, no store search, weak iOS push and storage.

## 4. Frontend changes

### 4.1 API base URL and auth

- Replace `window.location.origin` in `client.ts` with `import.meta.env.VITE_API_BASE_URL ?? window.location.origin`. The native build sets `https://api.<domain>`.
- Add CORS for `capacitor://localhost`, `https://localhost` (Android) and the web origin. Keep the `X-Trip-Planner` header (it doubles as a CSRF guard) and allow it in CORS.
- Auth is Supabase Auth for sign-in only. The client holds Supabase's short-lived access token and rotating refresh token; the API verifies the JWT and maps it to our `users` row. On iOS store the session in the Keychain through a secure-storage plugin, not `localStorage`. Detail: [04-users-and-accounts.md](04-users-and-accounts.md).
- Request middleware in `client.ts` attaches `Authorization`; a 401 handler tries one refresh before calling `onUnauthorized` (the existing hook in `auth-gate.tsx`).
- Replace the `login-screen.tsx` passcode with Sign in with Apple, Google and an email code. Remove "this PC passes straight through" for hosted builds; personal mode keeps it.
- Router: keep `createBrowserRouter` on web; in the native build keep it or switch to `createHashRouter` if deep-link cold starts misbehave. Test a cold start from a deep link early.
- Per-environment config: `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_REVENUECAT_KEY_IOS`, `VITE_SENTRY_DSN`, `VITE_POSTHOG_KEY`. Document all in `.env.example` (secrets only in `.env`; these public keys are safe in the bundle but still documented).

### 4.2 Offline cache for trips

Travelers are often on airplane mode or roaming. Offline access is the most valuable mobile feature and the best defense against 4.2.

- `@tanstack/query-persist-client` with an async persister. Start with IndexedDB (`idb-keyval`); WKWebView can evict it under storage pressure, so move critical data to SQLite (`@capacitor-community/sqlite`) in Phase 2.
- Persist only trip-scoped queries (trip, days, activities, flights, lodging, people, saved places) with `gcTime` of 30 days and `networkMode: 'offlineFirst'`.
- "Download for offline" per trip, automatic within 7 days of departure, with a "Saved offline, updated 2 h ago" badge.
- Offline edits limited to notes, checkmarks and expenses (mutation cache persistence, `onlineManager`). Last write wins per field; show a toast when a queued edit is rejected. Whole-itinerary edits offline are out of scope for v1 (read-only banner).
- Map tiles do not cache for free: v1 either caches the current trip's bounding box at low zoom or omits offline maps and says so. Full offline maps are Phase 4.
- Confirmations (PDF, images) are stored via `@capacitor/filesystem`, protected by iOS data protection.
- Files touched: `app/providers.tsx`, `lib/hooks.ts`, a new `lib/offline/` module.

### 4.3 Mobile layouts

- Bottom tab bar (Trips, Itinerary, Flights, Lodging, More) under 768 px, driven from `layout/nav-config.ts`; hide `sidebar-nav.tsx` at that width; trip switcher becomes a top sheet.
- Safe areas via `env(safe-area-inset-*)`; `@capacitor/status-bar`; `@capacitor/keyboard` in `body` resize mode.
- Touch targets at least 44 by 44 pt; 16 px inputs to stop iOS zoom; pull-to-refresh; swipe actions on itinerary items. Replace hover-only affordances with tap or long-press.
- FullCalendar on phones: `listWeek` or `timeGridDay`, drag-resize off, a "Move to..." sheet instead of drag and drop.
- Radix `Dialog` becomes a bottom sheet on phones (`vaul`).
- Present mode (`routes/present-page.tsx`): swipeable story view in portrait; full-screen landscape for iPad and AirPlay; wake lock while presenting.
- Recharts: sparkline plus tap-for-detail on phones.
- iPad: ship iPhone-only in v1 to cut screenshot and QA work; the sidebar layout at 768 px and above covers iPad later.
- Add a mobile-viewport Playwright project (iPhone 15 profile) beside the Edge smoke test.

### 4.4 Native features

| Feature | Implementation | Phase |
|---|---|---|
| Push (APNs) | Capacitor push plugin, token registered to `POST /api/devices`, APNs .p8 key. Topics: price drop, itinerary reminder, invite accepted, trip starts tomorrow. Price-drop pushes come from cached-fare alerts and shared route checks | 2 |
| Local notifications | `@capacitor/local-notifications` for "leave for the airport" that works offline | 2 |
| Share sheet | `@capacitor/share` for summaries and invite links | 2 |
| Universal links | `/.well-known/apple-app-site-association` on the web domain (`application/json`, no redirect). Routes: `/invite/:token`, `/trips/:id`, `/s/:shareId`. `appUrlOpen` routes into React Router | 2 |
| Calendar export | ICS on web; native write-only calendar access on iOS; subscribable ICS feed per trip | 2 |
| Maps handoff | "Open in Apple Maps" (`maps://?daddr=lat,lng&q=Name`), Google Maps as second option; MapLibre stays for the overview | 2 |
| Haptics | `@capacitor/haptics` on confirm and purchase success | 2 |
| Sign in with Apple | `@capacitor-community/apple-sign-in`, identity token exchanged through Supabase | 2 (web in 1) |
| Face ID lock for documents | Optional | 4 |
| Live Activities, widgets | Flight status, "Next up"; needs a small Swift plugin | 4 |

### 4.5 Performance

- Keep lazy route chunks; lazy-load MapLibre and Recharts. Budget: interactive under 2 s on an iPhone 12 in airplane mode with a cached trip; main JS chunk under 500 kB gzip.
- Virtualize long lists (`@tanstack/react-virtual`); request sized thumbnails and serve WebP or AVIF from Cloudflare ([05-infrastructure.md](05-infrastructure.md)).
- Turn heavy route pattern effects off under `prefers-reduced-motion` and on older devices. Subset the three bundled `@fontsource` families to Latin.
- Measure with Lighthouse (web) and Xcode Instruments plus Sentry performance (native).

### 4.6 Accessibility

- Audit with VoiceOver on device: labels on icon-only `lucide-react` buttons, focus order in sheets, live regions for `sonner` toasts.
- Dynamic Type: `rem` sizes, tested at the largest sizes, or an in-app text size setting. Wire `theme.tsx` to `prefers-color-scheme`; check AA contrast in light and dark.
- Respect reduce motion and bold text; never rely on color alone (price up or down needs an icon and text).
- Publish an accessibility statement and declare Accessibility Nutrition Labels in App Store Connect (verify whether required at submission).
- Add `@axe-core/playwright` to the e2e suite.

### 4.7 Localization and currency

- Build on `lib/currencies.ts`, `money.ts`, `format.ts`, `timezones.ts`, `dates.ts`. Add `react-i18next` or `lingui` and extract UI copy (update `.claude/rules/frontend.md` for keys). English first, then Spanish, French, German, Portuguese and Japanese by demand.
- Money as integer minor units plus ISO currency; convert with daily FX rates ([06-database-and-data-integrations.md](06-database-and-data-integrations.md)) and show original and converted prices.
- Units, 12 or 24 hour time, first day of week, and logical CSS properties for RTL readiness.
- Localize App Store metadata for en-US, es-MX or es-ES and de-DE at launch.

## 5. Payments and subscriptions

### 5.1 RevenueCat over direct StoreKit 2

| | RevenueCat (chosen) | Direct StoreKit 2 plus own server |
|---|---|---|
| Time to working purchase, restore, sync | Days | 3 to 5 weeks with edge cases |
| Receipt validation and notifications | Handled, webhooks to our backend | We build JWS verification, Server API, notification V2, grace period, refunds |
| Android and web later | Same entitlement model | Three integrations |
| Cost | Free under $2.5k monthly tracked revenue, then about 1 percent (verify) | Our time |
| Risk | Vendor dependency; mirrored entitlements soften it | Full control |

Client: `@revenuecat/purchases-capacitor`. Backend: an `entitlements` table filled by RevenueCat webhooks plus a periodic reconcile job against RevenueCat's REST API, so a later move to direct StoreKit stays possible. Paywalls are our own React screens in the Hermi theme.

The server is the source of truth: the client only displays entitlement, and every API route checks the entitlement row. Link the RevenueCat `app_user_id` to our account UUID (not email); call `logIn` on sign-in and `logOut` on sign-out. Apple's commission is 15 percent under the Small Business Program (under $1M a year in proceeds).

### 5.2 Products in App Store Connect

Launch products:

| Product | Type | Price | Notes |
|---|---|---|---|
| `plus_monthly` | Auto-renewable subscription, group `hermi_membership` | $5.99 | |
| `plus_annual` | Auto-renewable subscription, same group | $39.99 | 7-day free trial (annual only) |
| `family_monthly` | Auto-renewable subscription, same group | $8.99 | Up to 6 people in one household, 150 pooled credits (5.3a) |
| `family_annual` | Auto-renewable subscription, same group | $59.99 | No trial at launch |
| `trip_pass` | Non-renewing subscription | $9.99 | 90 days, bound to one trip on the server (5.3) |
| `group_trip_pass` | Non-renewing subscription | $19.99 | 90 days, bound to one trip, up to 12 travelers, polls, cost splitting, room-block request (5.3) |
| `credits_50` | Consumable | $2.99 | 50 credits |
| `credits_150` | Consumable | $6.99 | 150 credits |
| `credits_400` | Consumable | $14.99 | 400 credits |

Later (Phase 4, behind a flag until then): `pro_monthly` ($11.99) and `pro_annual` ($99), formerly named premium, added to the same `hermi_membership` group. Set the levels in the group as Pro, then Family, then Plus, with each tier's monthly and annual on one level. Moving up a level applies immediately with a prorated refund; moving down applies at the next renewal; moving between monthly and annual of the same tier is a crossgrade.

- One subscription group, so nobody holds Plus, Family or Pro at once. Apple allows one introductory offer per group per user; trial Plus annual only, never Family or Pro at launch. Win-back and promotional offers wait for Phase 4.
- Every product needs localized names and descriptions and a paywall review screenshot. Use Apple's automatic regional pricing first, then tune India, Brazil, Mexico and Turkey by hand. Leave Apple Family Sharing off for every product; it cannot be turned off again once enabled, and Family plan members are invited inside Hermi instead (5.3a).
- Paywall shows at most three visible choices: Trip Pass (lead offer), Plus annual (highlighted, with the trial), and Plus monthly and Family under "More options". Group Trip Pass appears on a trip when its owner adds a poll, splits a cost or has more than 6 people. Credit packs appear when a user runs out of credits. Pro is not shown until it launches.

### 5.3 Trip Pass

Trip Pass is a **non-renewing subscription** with a 90-day duration, decided in [02-pricing-tiers.md](02-pricing-tiers.md). The alternative, a consumable, was rejected because consumables cannot be restored by Apple and a lost purchase becomes a support ticket.

- Buy, then pick the trip. The server records the transaction (idempotent on `transaction_id`), binds the pass to that trip and starts the 90 days at activation. An unapplied pass waits in Settings, Purchases.
- The pass gives that trip 2 live routes, at most 60 live checks, 40 credits and up to 6 collaborators. Only the owner buys it; invitees get the owner's tier on that trip. Credits are charged to whoever starts the action.
- Expiry and binding are our job (Apple only records the purchase). Show pass status and expiry in the trip's settings, and keep the ledger server-side.

**Group Trip Pass** uses the same mechanics: a non-renewing subscription bought by the trip owner, bound to one trip, 90 days, for up to 12 travelers, 80 credits, polls, cost splitting and the room-block request. The polls and cost-splitting tools are digital features, so the pass is sold through In-App Purchase. The money that travelers owe each other for real-world costs is a different thing and follows 5.8.

### 5.3a Family plan

- The payer buys `family_monthly` or `family_annual` with their own Apple ID. RevenueCat knows only the payer; our server derives every other member's Family entitlement from the household record ([04-users-and-accounts.md](04-users-and-accounts.md) section 3.6). Members do not buy anything and need no Apple Family group.
- The product description says "up to 6 people", names the payer's role, and says members are invited in the app. The paywall says the same before purchase.
- Review risk (verify on the day of submission): Apple's Family Sharing is the sanctioned way to share a subscription, and in-app multi-seat plans are common but not guaranteed to pass. Mitigate with clear copy, one payer, a hard 6-person cap, and a review note explaining that the plan is one paying account with invited members and no extra purchase path.
- The payer cancelling ends the household at the end of the paid period. Members fall back to their own tier and keep their data.

### 5.4 Credit packs

- Grant credits only after the server verifies the transaction (RevenueCat webhook or the App Store Server API). Key the grant by `transaction_id`; never grant twice.
- Purchased credits last 12 months and are spent after monthly allowance credits. Say so on the pack screen. Monthly allowances reset on the renewal event for subscribers and on the calendar month for Free.
- Refunds (`REFUND`): reverse the grant, allow the balance to go negative, and block AI use until it is positive. A refunded Family subscription ends the household pool the same way.
- One credit is a budget of up to $0.02 of provider spend, so the worst-case cost is $1.00, $3.00 and $8.00 against $2.54, $5.94 and $12.74 net of Apple's 15 percent. Show balance and history in the app. Ledger schema: [06-database-and-data-integrations.md](06-database-and-data-integrations.md).

### 5.5 Server side

- Endpoints: `POST /api/webhooks/revenuecat` (secret header, idempotent), `GET /api/me/entitlements`, `POST /api/purchases/sync` (the client calls it after a purchase for instant unlock before the webhook lands).
- If ever going direct, register App Store Server Notifications V2 (production and sandbox) and handle `SUBSCRIBED`, `DID_RENEW`, `DID_FAIL_TO_RENEW`, `EXPIRED`, `REFUND`, `REVOKE`.
- Test with Sandbox Apple IDs and StoreKit configuration files. Subscriptions renew on a compressed schedule in sandbox.
- A visible "Restore purchases" button on the paywall and in Settings (App Review checks it).

### 5.6 External purchase links in the US (verify)

Uncertain and moving; date-stamped 2026-09-30.

- After the April 2025 ruling in Epic v. Apple, US apps may link to external purchase without Apple's commission, and Apple appealed. Later rulings left open whether Apple may charge some reduced commission. Outside the US the rules differ (EU, Japan, South Korea).
- **Decision: for digital plans, IAP only at launch, no web checkout.** (Stripe is used only for the non-digital lanes in 5.8.) IAP converts better on iOS; the 15 percent rate lowers the value of avoiding it; the legal picture may reverse. Design the paywall so a web option could be added later, and test it in the US only in Phase 4 if the picture is clear. Recheck on the day of submission (README open question 5).
- Whichever route: keep cancellation easy and disclose renewals per Guideline 3.1.2.

### 5.7 Subscription review requirements (3.1.2)

- The paywall shows price and billing period (largest and clearest), trial length and the price after it, auto-renewal terms, links to Terms of Use and Privacy Policy, and Restore. No misleading "free" wording.
- In App Store Connect: localized subscription info, privacy policy URL, and a review screenshot per product. Apple's standard EULA is fine.

### 5.8 Payments outside In-App Purchase: Stripe for real-world services

Rule of thumb: if the buyer gets a digital feature inside Hermi, it is In-App Purchase. If the money pays for something in the real world, or for software bought and used on the web, it goes through Stripe.

| Money | Route | Why, and the Apple rule |
|---|---|---|
| Plus, Family, Pro, Trip Pass, Group Trip Pass, credit packs | In-App Purchase | Digital features and content consumed in the app (Guideline 3.1.1) |
| Group trip payments: a traveler paying their share of a hotel deposit or dinner | Stripe Checkout, opened in `SFSafariViewController` | A real-world cost that is consumed outside the app, so Guideline 3.1.3(e) (goods and services outside of the app) applies. The payment must never unlock app features or buy credits |
| Concierge bookings | Paid to the supplier or the host agency, never through Hermi or the app | A physical travel service consumed outside the app (3.1.3(e)). The app only collects the request |
| Printed trip books and posters | Stripe Checkout | Physical goods shipped to the buyer (3.1.3(e)) |
| Hermi for Advisors seats | Stripe Billing on the web only | Web software sold to a business. The iOS app does not sell it, link to it, or unlock advisor features; advisors sign up on the web. This avoids Guideline 3.1.3(b), which would otherwise require the same items to be offered through In-App Purchase |
| Partner guide sponsorship | Invoiced on the web | Business to business, never in the app |
| LiteAPI hotel booking (later) | Its own checkout | A physical service consumed outside the app; decide the flow with Apple's rules in hand when the time comes |

- Do not cite Guideline 3.1.5 for any of this; it covers cryptocurrencies and does not apply.
- Keep the wording honest: group payment screens say "Pay your share of the trip costs", never "Unlock" or "Upgrade". Any in-app mention of a web purchase of a digital product (for example an advisor plan) is off limits in the iOS build.
- Stripe rules on the web: hosted Checkout, webhook-granted fulfillment, refunds through the admin console. Detail in [05-infrastructure.md](05-infrastructure.md) section 5.6.
- The US external-link question in 5.6 concerns digital purchases only and does not change this table.
- Apple's commission does not apply to Stripe revenue; Stripe's own fees do ([05-infrastructure.md](05-infrastructure.md) section 8).
- Re-read 3.1.1, 3.1.3(b) and 3.1.3(e) on the day of submission (verify), and have the review notes (6.9) ready to explain each row.

## 6. App Store requirements checklist

### 6.1 Accounts and setup

- [ ] Apple Developer Program, $99 a year. An individual account takes days; an organization needs a D-U-N-S number and a legal entity and takes 1 to 3 weeks. If forming an LLC, do it first so the seller name is the company ([01-business-plan.md](01-business-plan.md)).
- [ ] Paid Applications Agreement, bank and tax forms (required before any IAP; allow days).
- [ ] Bundle ID with Push Notifications, Associated Domains, Sign in with Apple and In-App Purchase.
- [ ] Small Business Program enrollment.
- [ ] Support, marketing and privacy policy URLs on our own domain.

### 6.2 Sign in with Apple (4.8)

Required because Google sign-in is offered. Handle the "Hide My Email" relay (register the sending domain) and Apple's server-to-server notifications for email changes and account deletion. Detail: [04-users-and-accounts.md](04-users-and-accounts.md).

### 6.3 Account deletion (5.1.1(v))

Deletion must be in the app, easy to find in Settings, confirm intent, delete the account and personal data (or explain legal retention), and revoke the Sign in with Apple token through Apple's REST endpoint. Tell users that deleting the account does not cancel an Apple subscription and link to Manage Subscriptions. Backend: soft delete with a 14 to 30 day grace window, then hard delete of trip data and files; backups purge on their normal cycle, documented in the privacy policy. Shared trips transfer to another member or are deleted ([04-users-and-accounts.md](04-users-and-accounts.md)).

### 6.4 Privacy policy and nutrition labels

- Host the policy publicly and link it in Settings and App Store Connect. Cover data collected (email, name, trips, locations, dates, companions' names), AI processing by Anthropic and other providers, analytics, crash reports, affiliates (including the server-side log of which partner button was tapped), retention, deletion, children, transfers and contact.
- Likely App Privacy declarations, all "not used for tracking":

| Data type | Linked to user | Purpose |
|---|---|---|
| Contact info (email, name) | Yes | App functionality, account |
| User content (trips, notes, photos) | Yes | App functionality |
| Identifiers (user ID, device ID for push) | Yes | App functionality, analytics |
| Purchases | Yes | App functionality |
| Usage data (first-party analytics, and affiliate click logging: which partner link was tapped, when, on which screen) | Yes | Analytics, app functionality |
| Contact info and user content sent in a concierge or room-block request, shared with a host travel agency only when the user sends it | Yes | App functionality (not used for tracking). Declare the third-party recipient |
| Financial info (group expense records; payments are taken by Stripe, so no card data) | Yes | App functionality |
| Diagnostics | Optional | App functionality |
| Location | Only if device location is used | App functionality |

- Add `PrivacyInfo.xcprivacy` with required-reason API declarations; check every third-party SDK for a manifest. Add `Info.plist` purpose strings for each permission and ask in context, not at launch.

### 6.5 App Tracking Transparency

ATT is needed only for tracking across other companies' apps and sites. Affiliate clicks go through our own redirect (`/go/<click_id>`), which logs the click server-side (click logging is declared in the App Privacy labels, section 6.4) and appends a random per-click sub-id. No user id, device id or advertising id is sent to partners. Links open in `SFSafariViewController`. **No ad SDKs, no ATT prompt.** This also fits the rule against automated fetching of Airbnb, Vrbo and Booking pages (links only). Disclose affiliate links in the app ("We earn a commission if you book here."). Details: [08-affiliate-revenue.md](08-affiliate-revenue.md).

### 6.6 AI-generated content

- Guideline 1.2 applies if users share AI or user content: add Report, block, a moderation queue and contact info on shared pages and AI answers.
- Apple requires disclosure and explicit permission when personal data goes to third-party AI (5.1.2(i), verify wording). First-use consent: "Your trip details and questions are sent to Anthropic to generate suggestions", with a policy link and an AI off toggle. Store consent with a timestamp.
- Label AI output ("AI suggestion, check details before booking"), add thumbs up or down (which doubles as the report channel), and show source links. No medical, legal or visa advice as authoritative.

### 6.7 Age rating

Answer the 2025 age rating questionnaire honestly. Expect 4+ or 9+ without open web access or chat; sharing and free-form AI text may raise it to 12+. Check state age-assurance laws (Texas, Utah) for new duties.

### 6.8 Store listing assets

- App name "Hermi: Group Trip Planner" (25 characters; 30 max), subtitle "Plan together. Know the fare." (29 characters; check that the name and subtitle are available), promotional text (170), promotional text (170), description, keywords (100, no spaces after commas), category Travel (secondary Lifestyle or Productivity), copyright.
- Screenshots: 6.9 inch iPhone (1320 by 2868), up to 10: trip overview, itinerary on map, price-drop alert, AI plan, offline mode, shared trip. Icon 1024 by 1024, no alpha. App preview video and custom product pages in Phase 4.

### 6.9 Review notes and demo account

- Provide a demo account (email and password or a "Demo mode" button; do not require Sign in with Apple for reviewers) with a loaded trip and an entitlement path that works in sandbox, since reviewers buy in sandbox.
- Notes explain AI features, where deletion lives, how push and affiliate links behave, and that servers are live. Add a second note: "Group payment and print order screens take money for real-world costs and physical goods through Stripe (Guideline 3.1.3(e)); they never unlock features or credits. A concierge request collects no payment. Family plan members are invited by the one paying account. Advisor plans are sold on the web only and are not available in this app." Affiliate note, roughly: "Partner buttons open hotel, tour, flight, car and eSIM booking pages in an in-app browser. These are physical travel services consumed outside the app, so they are outside In-App Purchase under Guideline 3.1.3(e); all digital plans and credits use In-App Purchase. Each button is labeled as a commission link. The app does not track users across other companies' apps or sites and shows no ATT prompt." Include a phone number and email. Keep the backend up and rate limits generous during review.
- Expect 24 to 48 hours per submission and often one rejection. Common causes: broken login, a paywall missing Restore or terms links, missing deletion, privacy label mismatch, 4.2.

### 6.10 TestFlight

- Internal testing (up to 100 users, no review) from day one of Phase 2. External (up to 10,000) needs Beta App Review for the first build of each version; recruit 30 to 100 testers from the waitlist. Builds expire after 90 days.
- Build and upload with Xcode Cloud or GitHub Actions plus Fastlane.

### 6.11 Toolchain

iOS builds need macOS and Xcode. Buy a Mac mini (about $600) for development plus Xcode Cloud for CI (25 free compute hours a month with the developer program), or rent a cloud Mac. Backend and web work continue on Windows.

## 7. Polish list

| Area | Item | Notes |
|---|---|---|
| Onboarding | 3-screen intro, sign in, "Create your first trip" wizard (destination, dates, who is going) | Sample trip to explore first. Ask for notifications after the first price alert, not at launch. |
| Empty states | Trips, day, flights, lodging, places, agents | A dotted route and plane (never people), one action, an example. Reuse the `setup-checklist.tsx` pattern per trip. |
| Error states | Offline, API failure, 401, out of credits, 429, maintenance, forced update | Extend `routes/errors.tsx`; plain copy per `.claude/rules/frontend.md`. |
| Loading | Skeletons, optimistic updates | Consistent across routes. |
| Analytics | PostHog: signup, trip_created, first_itinerary_item, ai_used, paywall_viewed, purchase_started, purchase_completed, restore_tapped, push_opt_in, invite_sent, invite_accepted | Session replay off or masked; respect opt-out; no cross-app tracking. |
| Crash reporting | Sentry, JS and native, source maps and dSYM upload in CI | Alerts to email or Slack. |
| Feature flags | PostHog or a config endpoint | Kill switches for AI features, SerpApi live fares, each affiliate partner, Pro, group payments, concierge requests, print orders; minimum app version. |
| Support | `support@<domain>`, in-app "Contact support" attaching version, device, user ID and error id, static FAQ | Reply within 2 business days. |
| Ratings prompt | `@capacitor-community/in-app-review` | After a positive moment, at most 3 a year, never after an error or paywall; "Send feedback" first for unhappy users. |
| Notifications | Preferences by type, quiet hours, per-trip mute | Batch price alerts; no marketing pushes without opt-in. |
| Legal | Terms, privacy policy, affiliate disclosure, AI disclaimer, licenses screen | Data attributions (OpenStreetMap, Wikimedia) per [06-database-and-data-integrations.md](06-database-and-data-integrations.md). |
| Sharing | Invite link preview card (OG tags), read-only public trip page | Feeds growth and Phase 4 SEO. |
| Data export | "Export my data" (JSON plus ICS) | GDPR and CCPA rights. |

## 8. Launch plan and post-launch

### 8.1 Launch plan

| When | Action |
|---|---|
| T minus 8 weeks | Keep the M0 waitlist warm; build-in-public posts; recruit TestFlight testers from travel subreddits, Discord and friends |
| T minus 4 weeks | External TestFlight; collect testimonials; screenshots; ASO keyword research (Wanderlog, TripIt, Tripadvisor) |
| T minus 2 weeks | Submit with manual release; line up 20 to 30 honest beta reviews (no incentives) |
| Launch day | Release; email the waitlist; Product Hunt; Reddit (follow each community's rules); possibly Show HN; demo video |
| T plus 1 to 4 weeks | Daily review and crash triage; reply to every review; hotfixes twice weekly if needed; public roadmap |
| T plus 4 to 8 weeks | Seasonal push (January to March for summer trips); small Apple Search Ads test (about $10 a day); nominate the app for featuring |

Positioning: "the trip planner that follows your trip offline", price alerts, AI that plans within your constraints, the Hermi design (two routes, one trip). Two-person planning is the wedge (couples and small groups), inherited from the original use case. Use Apple's 7-day phased release for automatic updates and release manually for new installs at launch.

### 8.2 Post-launch operations

- Weekly rhythm: Monday metrics review (installs, activation, trial starts, conversion, churn, MRR, AI cost per user), Tuesday to Thursday build, Friday release and support sweep.
- On call: phone alerts for API down, error spike, queue backlog, payment webhook failures and AI spend anomaly; runbooks for the top 5 incidents; status page ([05-infrastructure.md](05-infrastructure.md)).
- Releases: staging, TestFlight, phased release. Keep the backend compatible with the last 3 app versions and enforce a minimum version for breaking changes. OTA web-layer updates (Capgo, Appflow) are for hotfixes only and must stay within Guideline 3.3.2 (verify).
- Support: reply within 2 business days; refunds go through Apple (reportaproblem.apple.com), and we can reverse credits.
- Cost controls: weekly AI and provider bill review, per-account ceilings, kill switches, anomaly alerts ([03-ai-features-and-costs.md](03-ai-features-and-costs.md)).
- Compliance: yearly Apple renewal; Apple is merchant of record for IAP VAT; GDPR requests within 30 days; recheck the privacy label on every SDK change; recheck provider and affiliate terms twice a year, including SerpApi status.
- Security: monthly dependency audit, secrets rotation, a penetration test before scaling, quarterly restore drill.
- Dashboards (PostHog, RevenueCat, App Store Connect): activation (trip created within 24 hours), week-1 and week-4 retention, paywall view to trial, trial to paid, churn, ARPPU, AI cost as percent of revenue, push opt-in, crash-free rate, ratings.

**Kill rule.** At month 9 after launch, if under 1% of monthly users pay and affiliate income is under $0.20 per monthly user per year (annualized), stop investing and keep it as a personal tool. Track both numbers monthly from launch so month 9 holds no surprise. See [01-business-plan.md](01-business-plan.md).

## 9. Risks specific to this transition

| Risk | Likelihood | Mitigation |
|---|---|---|
| Guideline 4.2 rejection of the wrapper | Medium | Native features (3.2), offline, push, real accounts; clear review notes; more native UI on key screens |
| No Mac on hand | Certain | Mac mini or cloud Mac plus Xcode Cloud; about $600 or $50 to $100 a month |
| No demand | Medium | M0 gate before any rewrite; kill rule after launch |
| WKWebView jank on maps and calendar | Medium | Simplify the phone calendar, cap and cluster markers, profile early in Phase 2 |
| Multi-tenant leak | Low but severe | Row-level security, automated cross-user tests, security review before Phase 1 gate |
| AI cost overrun | Medium | Credits, run caps, spend ceilings, Haiku for short tasks ([03-ai-features-and-costs.md](03-ai-features-and-costs.md)) |
| Provider terms block a data source (SerpApi legal risk) | Medium | Terms audit in Phase 0; SerpApi behind a flag; Skyscanner Partners applied for; cached Travelpayouts fares as baseline; booking sites stay link-only |
| Policy churn (external links, AI disclosure, age assurance) | High | Re-read guidelines before each submission; IAP only; follow Apple Developer news |
| Solo bus factor and burnout | High | Strict gates; cut Android and widgets before cutting quality |
| Credit refund or fraud abuse | Low | Server ledger, refund reversal, velocity checks |
| Apple objects to Stripe group payments or the Family plan's in-app invites | Medium | Copy that ties payments to real-world costs, no unlock language, review notes (6.9), hold group payments until after launch (Phase 4), keep Apple Family Sharing off and cap households at 6 |
| Money transmission or seller-of-travel rules apply to group payments or concierge | Medium | Counsel before building collection; Stripe Connect or supplier payment links; the host agency carries travel registrations; concierge takes no payment |
| Advisor product pulled into the app by Apple's multi-platform rule | Low | Advisor features exist only on the web; the iOS app sells and exposes nothing for advisors |
| Existing two-person local install breaks | Low | Keep the personal-mode config path and its tests until hosted mode is stable |

## 10. Where this plan changed the initial idea

1. **Agents on the owner's Claude Code subscription cannot survive into the product.** Moving to the Claude API is a Phase 0 gate, not a Phase 1 detail, because it drives unit economics and the AI disclosure Apple requires. Scheduled agents stay off for everyone until Pro.
2. **Validate before building.** The first idea went straight to an App Store rewrite. M0 (landing page, waitlist, 10 interviews) comes first, and the kill rule stops spending if paying users and affiliate income stay low after launch.
3. **IAP only for digital plans, no external web checkout at launch.** Stripe is used only for real-world money and web software (5.8). The US external link option for digital purchases exists, but the commission question is unsettled and the 15 percent rate reduces the gain. Revisit in Phase 4.
4. **Trip Pass is a non-renewing subscription, 90 days, bound to one trip.** The earlier debate (consumable, or 30 or 60 days) is closed: Apple can restore it, it carries an expiry, and the server ties it to a trip.
5. **Pro waits (it was called Premium).** It is built behind a flag and launches only when measured agent cost is $0.60 or less per run over 200 runs, or more than 15% of Plus payers buy agent-run credits. It costs $11.99 a month or $99 a year, and joins the existing subscription group. The launch paywall shows Trip Pass, Plus annual, and Plus monthly and Family under "More options", plus credit packs when credits run out. Group Trip Pass appears on group trips.
6. **Price alerts are launch pushes, but cheap.** Alerts run on cached Travelpayouts fares, with one alert on Free. Live checks are batched by route and shared across users, because per-user paid searches scale badly ([06-database-and-data-integrations.md](06-database-and-data-integrations.md)).
7. **Hosted web before iOS.** No public App Store submission until the web beta has shown 4-week retention. It de-risks the backend before paying Apple's review and support cost, and the same web app powers invites, universal links, the privacy policy and SEO.
8. **A Mac is required.** The repo is built for Windows 11, but iOS builds need macOS: budget a Mac mini or Xcode Cloud and a changed workflow.
