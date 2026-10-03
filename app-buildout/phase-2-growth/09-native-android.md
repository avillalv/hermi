# Pack 09: Native Android app

Part of [Phase 2: growth](README.md). Written 2026-09-30. The full specs mention Android only as later
work ([01 section 7](../reference-full-spec/01-product-spec.md): "Android app (later)"; WF-111 in [09](../reference-full-spec/09-build-roadmap.md):
"Capacitor Android, Play Billing through RevenueCat, FCM push, App Links, Play listing"). Android users
get the web app until this pack ships. Platform rules below come from web search results dated
2026-09-30 and are **reported, verify** against the Google Play Console help pages at the time of
submission.

| Item | Value |
|---|---|
| Build order | 9 (shell, push and links from month 10, billing and tests in month 11, release in month 12); Play Console enrollment and the closed-test clock start in month 9 or 10 |
| Flags | None per feature; the build is gated by `min_app_version` and Play track rollout percentages |
| Needs from Phase 1 | The iOS Capacitor app (bundled web app, native plugins layer in `apps/web/src/lib/native/`), RevenueCat, push abstraction, deep links, offline SQLite, purchases, account deletion |
| Needs from other packs | Products from packs 01, 02 and 06 exist in the stores; flight alerts (pack 05) and comments (pack 03) ride on the push layer |
| Tickets | P2-084 to P2-094, and P2-105 (web billing) |
| Tier and products | Same ladder as iOS: Plus, Family, Pro (when launched), Trip Pass, Group Trip Pass, credit packs, sold through Google Play Billing. The web app also starts selling Plus, Trip Pass and credit packs through RevenueCat Web Billing (Phase 1 says "web billing arrives with Android in Phase 2") |

## 1. Goal and why now

**Goal.** Ship the same Hermi as a native Android app (a Capacitor shell with the web app bundled, not
a remote URL) on Google Play: sign-in, trips, offline reading, push, deep links, purchases through Google
Play Billing via RevenueCat, and the same server rules and entitlements as iOS.

**Why now.**

- Phase 1 tells Android users "use the web app". Invites are the growth loop: an invitee on Android who
  cannot install the app is a dropped invite, and trips mix platforms (a group of friends is not all on
  iPhone).
- Competitive reasons. TripIt and Wanderlog both ship Android apps (reported, verify), so an iOS-only
  planner loses any group that contains an Android user, and Android share is higher outside the US, where
  Hermi's UK and EU storefront rules and eSIM and flight categories matter.
- The bundled web app and server-side rules mean Android is mostly packaging, billing and push: the
  roadmap sizes it as one large ticket (WF-111), and everything it depends on exists after Phase 1. It is
  scheduled last because the risk register says to cut Android, widgets and growth work before cutting
  quality, and because Google Play has long-lead account steps that can run in the background.

## 2. User stories and acceptance criteria

| ID | Story | Acceptance |
|---|---|---|
| AND-1 | As an Android user, I install Hermi from Google Play and sign in. | Sign in with Google (native, through the credential manager) and email code work natively; an account created with Sign in with Apple on iOS can sign in on Android through the Apple web OAuth flow in a Custom Tab; guest mode works and is claimed on sign-up as on iOS. |
| AND-2 | As an Android user, I open invite, trip and share links in the app. | App Links (`https://hermi.world/invite/:token`, `/trips/:id`, `/s/:shareId`, `/h/:token` for households) open the app when installed and verified, the web app otherwise, and the Play Store page with an "enter code" fallback when not installed. Cold start from a link is tested. |
| AND-3 | As an Android user, I buy what iOS users can buy. | Plus (monthly and annual with a 7-day trial on annual), Family, Trip Pass and Group Trip Pass (one-time products bound to a trip by our server), and credit packs; Pro appears only after it launches. Restore purchases is present. Entitlements are server-side from RevenueCat, exactly as on iOS. |
| AND-4 | As an Android user, I get push notifications that respect my settings. | Firebase Cloud Messaging with notification channels (price alerts, flight alerts, trip changes, reminders, group and comments, concierge); the Android 13 and later notification permission is requested in context after the first invite or alert, with the same reason screen as iOS; no promotional push. |
| AND-5 | As an Android user, I can read my trips offline and my edits sync. | Same offline behavior as iOS: itinerary, stays, checklist, notes and map tiles cached; edits queue; conflict sheet on 409. |
| AND-6 | As an Android user, it feels native where it matters. | System back button and predictive back work on every screen; edge-to-edge layout with insets; Android share sheet for invites and exports; dark mode; font scaling; TalkBack passes the same checks as VoiceOver; Chrome Custom Tabs for partner links (`opened_in = android_tab`). |
| AND-7 | As an Android user, I can delete my account and my data. | In-app path Settings, Account, Delete account with the same flow and effects as iOS, and a public web page where a person can request deletion without the app (required by Google Play; reported). Deleting does not cancel a Play subscription; the screen says so and deep links to the Play subscriptions page. |
| AND-8 | As the founder, I can ship and watch Android safely. | Internal, closed and production tracks; staged rollout percentages; crash-free sessions at least 99.5 percent and Play vitals within Google's bad-behavior thresholds (user-perceived ANR and crash rates; reported defaults 0.47 percent and 1.09 percent, verify); a device test matrix; Sentry for Android. |
| AND-9 | As a user on both stores, I am not charged twice by mistake. | If one account has active subscriptions on Apple and Google, entitlements take the best tier, credits are granted once per period (idempotent), the app shows a notice "You have plans on two stores", and support has a macro. |
| AND-10 | As a web user, I can buy on the web. | The browser web app shows the normal paywall with a purchase button for Plus (monthly, annual with the 7-day trial), Trip Pass and credit packs through RevenueCat Web Billing; the purchase unlocks through the same entitlement and ledger code; the iOS and Android apps never show or link to it. |

Out of scope for this pack: Wear OS, Android widgets, tablets beyond responsive web layouts, Android
Auto, an Android-specific redesign, Samsung or Huawei stores (Play only), web purchases of consumer
features.

## 3. Database additions

Migration `0025_android`. Phase 1 already allows `devices.platform = 'android'`
([Phase 1 03](../phase-1-launch/03-database-schema.md) `ck_devices_platform`) and `link_clicks.opened_in =
'android_tab'`, and `entitlements.store` already allows `stripe` (RevenueCat Web Billing). It does not allow
`google` in `store_products.store`, `store_transactions.store` or `subscriptions.store` (its section 14 lists
"`store_transactions.store`, `subscriptions.store` value `google`; `devices.push_provider`" as this pack's
changes), so the additions are constraint swaps plus the push provider:

```sql
-- Play is a store: swap the named checks (keep every value earlier revisions allow).
ALTER TABLE store_products     DROP CONSTRAINT ck_store_products_store;
ALTER TABLE store_products     ADD CONSTRAINT ck_store_products_store     CHECK (store IN ('apple', 'stripe', 'google'));
ALTER TABLE store_transactions DROP CONSTRAINT ck_store_transactions_store;
ALTER TABLE store_transactions ADD CONSTRAINT ck_store_transactions_store CHECK (store IN ('apple', 'stripe', 'google'));
ALTER TABLE subscriptions      DROP CONSTRAINT ck_subscriptions_store;
ALTER TABLE subscriptions      ADD CONSTRAINT ck_subscriptions_store      CHECK (store IN ('apple', 'stripe', 'google'));

-- Push provider: APNs for iOS, FCM for Android. The existing push_token column holds either token.
ALTER TABLE devices ADD COLUMN push_provider text;
UPDATE devices SET push_provider = 'apns' WHERE platform = 'ios' AND push_provider IS NULL;
ALTER TABLE devices ADD CONSTRAINT ck_devices_push_provider CHECK (push_provider IS NULL OR push_provider IN ('apns', 'fcm'));
ALTER TABLE devices ADD COLUMN attestation_kind text;             -- app_attest, play_integrity
ALTER TABLE devices ADD CONSTRAINT ck_devices_attestation_kind CHECK (attestation_kind IS NULL OR attestation_kind IN ('app_attest', 'play_integrity'));
-- push_environment stays null for FCM (there is no sandbox token type); ck_devices_push_env already allows null.
-- uq_devices_push_token on (platform, push_token) already keeps tokens unique per platform.
```

Play product rows. `store_products.product_id` is the primary key, so Play ids must not collide with the
Apple ids. Convention: create the Play products with a `_gp` suffix; RevenueCat reports Play
subscriptions as `subscription_id:base_plan_id`. Prices are US prices; Play regional pricing is set in
Play Console (use automatic conversion first, then tune India, Brazil, Mexico and Turkey by hand after
launch, as on iOS).

```sql
INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('hermi_plus_gp:monthly',      'google', 'plus',            'month',  599, 'USD', 0, true),
('hermi_plus_gp:annual',       'google', 'plus',            'year',  3999, 'USD', 7, true),     -- 7-day free trial offer on the annual base plan only
('hermi_family_gp:monthly',    'google', 'family',          'month',  899, 'USD', 0, true),
('hermi_family_gp:annual',     'google', 'family',          'year',  5999, 'USD', 0, true),
('hermi_pro_gp:monthly',       'google', 'pro',             'month', 1199, 'USD', 0, false),    -- active with tier_pro, like iOS
('hermi_pro_gp:annual',        'google', 'pro',             'year',  9900, 'USD', 0, false),
('hermi_trip_pass_gp',         'google', 'trip_pass',       'once',   999, 'USD', 0, true),     -- one-time product; 90 days counted from binding by our server
('hermi_group_trip_pass_gp',   'google', 'group_trip_pass', 'once',  1999, 'USD', 0, true),
('hermi_credits_50_gp',        'google', 'credits_50',      'once',   299, 'USD', 0, true),     -- consumable
('hermi_credits_150_gp',       'google', 'credits_150',     'once',   699, 'USD', 0, true),
('hermi_credits_400_gp',       'google', 'credits_400',     'once',  1499, 'USD', 0, true)
ON CONFLICT (product_id) DO NOTHING;
```

Web billing rows (P2-105). The web app sells Plus, Trip Pass and credit packs through RevenueCat Web Billing
(Stripe-backed; Phase 1 04 section 6 already describes its events arriving on the RevenueCat webhook, with
`store = 'stripe'`). `store_products.product_id` is the Stripe price lookup key for these rows and must not
collide with Apple ids, so they carry a `web_` prefix:

```sql
INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('web_plus_monthly',   'stripe', 'plus',      'month',  599, 'USD', 0, true),
('web_plus_annual',    'stripe', 'plus',      'year',  3999, 'USD', 7, true),
('web_trip_pass',      'stripe', 'trip_pass', 'once',   999, 'USD', 0, true),
('web_credits_50',     'stripe', 'credits_50',  'once',  299, 'USD', 0, true),
('web_credits_150',    'stripe', 'credits_150', 'once',  699, 'USD', 0, true),
('web_credits_400',    'stripe', 'credits_400', 'once', 1499, 'USD', 0, true)
ON CONFLICT (product_id) DO NOTHING;
-- Family, Group Trip Pass and Pro web rows follow the same pattern when those plans are sold on the web.
```

Rules for web billing: it is available only in the browser web app, never inside the iOS or Android app and
never linked from them (Apple 3.1.1 and Google Play payments rules; the apps keep "Upgrade in the app" copy
pointing at their own store), prices equal the app prices unless an experiment says otherwise, the paywall
sheet and every free path are the same as in the app, Restore is an account sign-in rather than a store action,
and the same best-of entitlement and idempotent credit grants apply across Apple, Google and web. Web tax
collection is handled by the Web Billing setup (verify Stripe Tax settings); refunds are issued in the Web
Billing or Stripe dashboard and arrive as cancellation events.

Store differences the billing code must handle (RevenueCat carries most of it):

| Topic | Apple | Google Play |
|---|---|---|
| Subscription model | Group `hermi_membership`, one membership at a time, levels Pro 1, Family 2, Plus 3 | Subscriptions with base plans; no group, so the server enforces one active membership per store account and best-of across stores |
| Trip Pass and Group Trip Pass | Non-renewing subscription, restorable | One-time product configured as consumable (so it can be bought again for another trip); not restorable from the store once consumed, so Hermi's server list (`GET /me/passes`) is the source of truth for unapplied and active passes |
| Trial | Introductory offer on annual Plus only | Free trial offer on the annual Plus base plan only (new customers) |
| Grace and retry | Billing grace period 16 days, retry up to 60 days | Grace period and account hold (set the grace period to match 16 days where allowed; account hold maps to `billing_retry`; verify current limits); subscription pause is not offered |
| Refunds | Apple, reportaproblem.apple.com | Google Play refunds and voided purchases, delivered through RevenueCat as cancellations with a reason; same clawback rules |
| Family | Family Sharing off | Play family library off for subscriptions; households are invited inside Hermi |
| Manage subscription | Apple subscriptions page | Play subscriptions deep link for the package and subscription id |

Webhook mapping: the RevenueCat handler already upserts `subscriptions` and `store_transactions` with
`store = 'google'`; the `subscription_status` enum covers every Play state through the mapping above;
reconcile jobs call RevenueCat's REST API for both stores. Credits and ceilings are unchanged.

## 4. API additions

No new product routes. Changes to existing contracts:

- `PUT /me/devices/{device_id}` accepts `platform: "android"`, `push_provider: "fcm"` and the FCM token
  (`DeviceIn` gains `push_provider`); the push sender routes by provider, treats FCM `UNREGISTERED` like an
  APNs 410 (delete the token), and uses collapse keys and Android channel ids per notification type.
- `POST /purchases/sync` and `POST /purchases/restore` work for Google purchases through RevenueCat's
  REST API (the subscriber is looked up by our user id as `app_user_id`).
- `GET /me/entitlements` returns `store: "google"` and a `manage_subscription_url` pointing at the Play
  subscriptions page.
- `GET /me/passes` lists unapplied Google passes exactly as it lists Apple ones (they are
  `store_transactions` rows with `kind = 'pass'` and no `trip_passes` row).
- `POST /outbound` accepts `opened_in: "android_tab"` (already in the contract).
- Universal link files: serve `/.well-known/assetlinks.json` (Digital Asset Links, JSON, no redirect) with
  the app's package name and the Play App Signing and upload certificate SHA-256 fingerprints, next to the
  existing `apple-app-site-association`.
- Public deletion page: `GET https://hermi.world/delete-account` (a web page, no app required) explains the
  steps and lets a signed-in user request deletion through the same `POST /me/delete` flow with
  re-authentication; its URL is entered in Play Console. The in-app path remains.
- Device trust: the Android equivalent of App Attest is the Play Integrity API; the server verifies the
  integrity token for sensitive routes where iOS uses App Attest (the same policy table,
  [10 section 2.4](../reference-full-spec/10-quality-security-launch.md)), and never blocks a normal user on a failed check
  (degrade with extra rate limits and monitoring).
- Analytics: the `platform` common property gains `android`; nothing else changes.

Jobs: `send_push` gains the FCM sender (HTTP v1, service account in an environment variable
`FCM_SERVICE_ACCOUNT_JSON_B64`, never in the repo); `reconcile_entitlements` covers Google subscribers.
New environment variables (documented in `.env.example`): `FCM_SERVICE_ACCOUNT_JSON_B64`,
`PLAY_INTEGRITY_DECRYPTION_KEY` and `PLAY_INTEGRITY_VERIFICATION_KEY` if the server decodes tokens locally,
`ANDROID_APP_LINKS_SHA256`, and the RevenueCat Google public API key for the client build.

## 5. UI screens and paywall triggers

No new screens. Platform specifics:

- **Shell**: `apps/android/` (sibling of `apps/ios/`), Capacitor Android with the built web app bundled in
  the APK and AAB (no `server.url`), the same `apps/web/src/lib/native/` bridge (`purchases`, `push`,
  `share`, `browser`, `filesystem`, `haptics`, `status-bar`), splash, status and navigation bar colors from
  the Hermi tokens, and dark mode. The adaptive icon is built from the Hermi mark: the H routes and plane
  as the foreground on a sky (`#2AA5FF`) background, plus a monochrome H silhouette for the monochrome
  icon.
- **Navigation**: the bottom tab bar follows the same information architecture; the system back button
  closes sheets first, then pops routes; predictive back animations enabled where supported.
- **Permissions**: notification permission is requested in context (after the first invite or price
  alert) with the existing reason screen; location is never requested; storage is scoped (photo picker for
  receipts and memories).
- **Paywalls**: the same sheet and triggers as iOS; price and period come from the Play Billing product
  details (never hard coded), the trial line states the price after the trial and the renewal date, links
  to Terms and Privacy and Restore are present. "Manage subscription" opens the Play subscriptions page.
- **Partner links**: open in Chrome Custom Tabs (`opened_in = android_tab`); "Ad" tag on UK and EU
  storefronts by Play country or account country; no attribution SDK.
- **Sign-in**: Google native, email code, and Sign in with Apple through the web OAuth flow (needed so an
  iOS-created Apple account can sign in on Android); Apple's requirement to offer Sign in with Apple
  applies to iOS only.
- **Accessibility**: TalkBack pass, 48 dp touch targets, font scale 200 percent, reduced motion respected
  (`prefers-reduced-motion` from the system animation scale).
- **Offline**: same SQLite and persisted query cache as iOS; "Leave for the airport" style local
  notifications use Android alarms with exact-alarm permission only if required (prefer inexact times or
  a foreground reminder; verify the current exact alarm policy).
- **Store listing screens**: screenshots from the same flows (phone, plus optional 7 and 10 inch), feature
  graphic, short and full description in plain words, "How we earn money" referenced.

## 6. Monetization and App Store products

Google Play products (created in Play Console; ids listed in section 3):

| Play product (id) | Type | Price (US) | Duration | Trial | Entitlement |
|---|---|---|---|---|---|
| `hermi_plus_gp`, base plans `monthly`, `annual` | Subscription | $5.99 a month, $39.99 a year | 1 month, 1 year | 7 days on `annual` only | `plus` |
| `hermi_family_gp`, base plans `monthly`, `annual` | Subscription | $8.99 a month, $59.99 a year | 1 month, 1 year | none | `family` |
| `hermi_pro_gp`, base plans `monthly`, `annual` | Subscription (hidden until `tier_pro`) | $11.99 a month, $99.00 a year | 1 month, 1 year | none | `pro` |
| `hermi_trip_pass_gp` | One-time product, consumable | $9.99 | one trip, 90 days from binding | none | `trip_pass` |
| `hermi_group_trip_pass_gp` | One-time product, consumable | $19.99 | one trip, 90 days from binding | none | `group_trip_pass` |
| `hermi_credits_50_gp`, `hermi_credits_150_gp`, `hermi_credits_400_gp` | One-time, consumable | $2.99, $6.99, $14.99 | credits valid 12 months | none | purchased credits |

- Prices are the same as iOS. Google's service fee and Apple's fee differ (reported: 15 percent on the
  first $1M of annual revenue in a small business program and on subscriptions after the first year;
  verify); model net revenue per store in finance reports and enroll in the reduced-fee program where
  eligible.
- RevenueCat: add the Google app, import products, create packages in the same offerings with the same
  entitlements; configure the passes and packs as consumable in RevenueCat and in Play Console; one
  `app_user_id` (our user UUID) across stores.
- Rules that are unchanged: Hermi web payments are never used for consumer digital features; group
  payments (Phase 3) and concierge are real-world services outside Play Billing (verify the Play payments
  policy text on the day of submission and keep the review notes explicit that nothing digital is unlocked
  by them).
- No new credits, prices or limits; the plan catalog is shared.

## 7. Admin additions

- **Users and subscriptions (08 sections 6.2 and 6.3)**: store column (`apple`, `google`), platform filter,
  Play subscription state mapping in the detail view, webhook replay and reconcile buttons for Google
  events, refund visibility for Play voided purchases, the "plans on two stores" flag on an account.
- **Overview**: MRR, trials and conversions split by store; net of each store's fee.
- **Provider health**: FCM send success and invalid token rate; Play Integrity verdict mix.
- **System health**: push lane by provider.
- **Support macros**: "Cancel a Google Play subscription", "Restore purchases on Android", "I paid on two
  stores", "Delete my account without the app".
- **Flags**: `min_app_version` already supports per platform rules (`platforms`, `min_app_version`).
- **Alert rules (08 section 10)**: Android crash-free sessions below 99.5 percent for 24 hours (notify),
  FCM failure rate above 5 percent (notify), RevenueCat Google events failing (page, existing webhook
  alerts).

## 8. AI additions

None. All AI features run on the server and are platform independent; consent screens, the AI disclosure
and the credit rules are identical on Android.

## 9. Analytics events

No new events. The common property `platform` gains the value `android` and `tier` and every existing
event applies unchanged. Two server-side additions for store health:

| Event | Properties | When fired |
|---|---|---|
| `push_token_invalidated` | `platform` (`ios`, `android`) | A provider reports an invalid token and it is removed |
| `purchase_store_conflict_detected` | none | Account found with active plans on two stores |

Funnels and retention are reported by platform; the Android readiness review compares D7 and D30 against
iOS ([README](README.md) section 7).

## 10. Tests

- Device matrix (Maestro flows on real devices and emulators): at least one low-end device (3 GB RAM or
  less), one mid-range and one current Pixel; Android versions from the minimum supported (the Capacitor
  version's minSdk, verify) to the current release; Samsung One UI and a stock Android build; both gesture
  and three-button navigation.
- Core flows: sign in (Google, email code, Apple web), create a trip, invite by link and open it in the
  app (cold start and warm), plan a day, map and calendar performance on the low-end device (simplified
  phone calendar and marker clustering from the risk register), presentation mode, PDF export and share
  sheet, account deletion.
- Purchases in the Play sandbox (license testers): every scenario from the iOS matrix adapted: subscribe,
  trial conversion, cancel, upgrade Plus to Family, downgrade at renewal, refund or void, restore on a
  second device, grace and account hold, Trip Pass and Group Trip Pass each bound to a trip, credit pack
  granted once, expired pass, plans on two stores.
- Push: FCM delivery, channels, permission prompt on Android 13 and later, invalid token cleanup, quiet
  hours, collapse keys, tapping a notification opens the exact screen.
- App Links: `assetlinks.json` verification, cold start from each link type, fallback to web and to the
  Play listing, no open redirect.
- Offline and sync: airplane mode reading, queued edits, conflict sheet, calendar feed unchanged.
- Security: Play Integrity verification path, no secrets in the APK (scan the bundle), network security
  config blocks cleartext, WebView debugging off in release, no `server.url`, ProGuard or R8 rules keep
  the Capacitor plugins working.
- Accessibility: TalkBack smoke test on the main flows, font scale, contrast tokens.
- Play pre-launch report clean of crashes and accessibility blockers; Play vitals within thresholds
  during the closed test.
- Regression: the same automated API and tenant-isolation suites (unchanged) plus a web end-to-end run
  against the Android build's bundled assets.

## 11. Tickets

#### P2-084 Play Console, compliance and closed-test clock [S, starts month 9 or 10]
- Description: create the Google Play developer account (a personal account created after 13 November
  2023 must run a closed test with at least 12 opted-in testers for 14 continuous days before production
  access; organization accounts are exempt; reported, verify), complete identity verification, the
  merchant profile for paid products, the app record, Play App Signing, the data safety form, content
  rating (IARC questionnaire answered honestly), target audience (13 and older, not a children's app),
  the ads declaration and the account deletion URL, and recruit and brief the closed-test testers.
- Accept: app record complete; closed test running with 12 or more opted-in testers (testers actually
  use the app; Google is reported to check); deletion page live.
- Touches: `docs/launch/android/`.

#### P2-085 Capacitor Android project and build pipeline [M, needs Phase 1 iOS shell]
- Description: `apps/android/`, bundled assets, plugin set, target API 36 (the requirement for new apps
  and updates from 31 August 2026, reported, verify), edge-to-edge and insets, adaptive icons from the
  Hermi mark, splash, signing with upload key in CI secrets, AAB build, internal testing upload from CI,
  R8 rules, Sentry.
- Accept: a merge to `main` produces a signed AAB in the internal track; the app boots offline with
  bundled assets.

#### P2-086 Play Billing through RevenueCat [L, needs P2-085, Phase 1 purchases]
- Description: Play products and base plans, RevenueCat Google app and offerings, client purchase flow,
  consumable passes and packs, trial, restore, paywall price display from Play product details.
- Accept: sandbox scenarios in section 10 pass; paywall text meets Play and Apple equivalent rules.
- Touches: `apps/web/src/lib/native/purchases.ts`, `apps/web/src/routes/paywall/`.

#### P2-087 Server support for the Google store [M, needs P2-086]
- Description: `store_products` rows, status mapping for grace and account hold, refund and void
  clawback, reconcile for Google subscribers, best-of across stores with idempotent credit grants,
  two-store notice, store-specific manage links.
- Accept: webhook fixtures for every Google event pass; no double grants.
- Touches: `apps/api/hermi/modules/billing/`.

#### P2-088 Push with FCM [M, needs P2-085]
- Description: push provider abstraction, FCM HTTP v1 sender, device registration, channels, collapse
  keys, invalid token cleanup, Android 13 permission flow and reason screen.
- Accept: push tests pass for every notification type; permission requested only after the first invite
  or alert.

#### P2-089 App Links and invite flows [M, needs P2-085]
- Description: `assetlinks.json`, intent filters with auto verify, `appUrlOpen` routing, Play Store
  fallback with an enter-code path, cold start tests, household links (`/h/`).
- Accept: every link type opens the right screen from cold and warm starts.

#### P2-090 Android UX adaptations [M, needs P2-085]
- Description: back button and predictive back, insets, share sheet, Custom Tabs for partner links,
  Sign in with Apple through web OAuth and native Google sign-in, TalkBack labels, font scale, dark mode.
- Accept: TalkBack pass on main flows; no horizontal scroll at phone width; 48 dp targets.

#### P2-091 Offline and performance parity [M, needs P2-085]
- Description: SQLite and persisted cache on Android, offline edits queue, map and calendar performance
  on the low-end device, startup time budget.
- Accept: offline tests pass; cold start and scroll budgets met on the low-end device.

#### P2-092 Device trust and security hardening [S, needs P2-085]
- Description: Play Integrity verification where iOS uses App Attest, network security config, release
  WebView settings, bundle secret scan, dependency audit for Android libraries.
- Accept: security checklist items for Android complete; failed integrity degrades with limits, never
  blocks a normal user.

#### P2-093 Test matrix and Play sandbox runs [M, needs P2-086, P2-088, P2-089]
- Description: Maestro flows, device matrix, purchase matrix, push and link tests, pre-launch report
  review, vitals baseline during the closed test.
- Accept: matrix recorded in `docs/launch/android/`; crash-free sessions at least 99.5 percent over 100 or
  more sessions.

#### P2-094 Listing, review and staged release [L, needs P2-084, P2-093]
- Description: store listing copy and screenshots, privacy policy update for Android, data safety form
  final check, review notes (server-side entitlements, services consumed outside the app, no unlock by
  partner purchases), production access request after the closed test, staged rollout 5, 20, 50, 100
  percent with the vitals watch, support macros.
- Accept: app live on Google Play; no P0 in the first 72 hours; Android share of new installs tracked.

#### P2-105 Web billing with RevenueCat Web Billing [L, needs Phase 1 purchases and RevenueCat webhook]
- Description: configure RevenueCat Web Billing (Stripe-backed) for Plus monthly and annual (7-day trial on
  annual), Trip Pass and the three credit packs with the `web_` product rows above; web paywall purchase
  flow on the browser web app only; `POST /purchases/sync` and the webhook handler for `store = 'stripe'`;
  sign-in based restore; tax and receipts settings; hide every purchase path inside the iOS and Android
  apps; refund and cancellation handling; admin store filter.
- Accept: web purchases unlock within seconds and appear in `subscriptions`, `store_transactions`,
  `trip_passes` and `credit_grants` exactly like app purchases; no web purchase link exists in any native
  build (test scans the bundles); two-store and web-plus-app notice works; sandbox matrix adapted.
- Touches: `apps/web/src/routes/paywall/`, `apps/api/hermi/modules/billing/`.
- Tests: sandbox purchase matrix on web, bundle scan for purchase URLs, idempotent grants across stores.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Closed-test requirement delays launch (12 testers for 14 days, plus review of about 7 days; reported) | Start in month 9 or 10, recruit early from invitees and beta users, consider an organization account |
| WebView jank and memory pressure on low-end devices (risk register item 9) | Simplified phone calendar, marker clustering, profile early on a low-end device, performance budget |
| Fragmentation (OEM skins, WebView versions) | Device matrix, Play pre-launch report, minimum WebView check at startup with an update prompt |
| Billing differences (consumable passes are not store-restorable, grace versus hold) | Server list of passes is the source of truth, status mapping, fixtures, sandbox matrix |
| Double billing across stores and web | Best-of entitlement, idempotent grants, notice and support macro |
| Web billing link inside a native app breaks store rules | Web purchases exist only in the browser build; bundle scan test; apps keep store purchases only |
| Play policy churn (target API level, account deletion web link, payments policy, data safety) | Re-read policies before each submission, keep review notes explicit, deletion page live |
| Solo developer capacity (risk register item 11) | Android is the first cut if quality or schedule slips; it is scheduled last and independent |
| Fewer affiliate and subscription conversions on Android at first | Report metrics by platform; do not assume iOS conversion rates |
