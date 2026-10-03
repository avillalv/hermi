# 07: Monetization specification (Phase 1)

Part of the [Hermi build specification](../README.md), [Phase 1: the launch app](README.md). Tier codes, prices, credit grants, credit action codes, ceilings and table names come from the [README](../README.md) and are final; table, column, enum and limit-key names come from [03-database-schema.md](03-database-schema.md). Where this file needs a value the README does not give (for example a cap or a timer), it is marked "default" and lives in `feature_flags` so it can change without a release. Rates, cookie windows and program rules for affiliate partners are "reported, verify": read each on the network's own terms page after sign-up.

Written 2026-09-30.

Phase 1 sells Free, Plus, Trip Pass and three credit packs, only inside the iOS app (there are no web purchases in Phase 1), earns affiliate commission through Travelpayouts, Stay22 and Viator, prices the "Verify this plan" check and the evidence recheck in credits (section 5.8), publishes the trust pages ("How we earn", billing and cancel; sections 7.11 and 8.5), and adds two growth mechanics that cost credits instead of earning money: referral credits (section 9) and a free Trip Pass for a first import (section 10). Everything that belongs to Phase 2 or 3 is listed in section 11 and is not built in Phase 1.

## 1. Revenue lanes and principles

| Lane | Who pays | Channel | Section |
|---|---|---|---|
| Subscriptions (Plus) | The user | App Store in-app purchase through RevenueCat | 2 to 7 |
| Trip Pass | The trip owner | App Store in-app purchase, non-renewing subscription | 2 to 7 |
| Credit packs | The user | App Store consumable | 5 |
| Affiliate commissions | The partner | Our redirect `/go/{click_id}` | 8 |
| Referral credits and the first-import Trip Pass (growth cost, not revenue) | Hermi | No store involved | 9, 10 |

Principles that every rule below follows:


1. The server decides. The app displays entitlement and balance; every API route checks the server's rows, never a client claim.
2. One payer per capability. A trip's capabilities are the best of its owner's tier and any pass on that trip; invitees join free. Credits are charged to the person who starts the action.
3. No dark patterns. The free path is always visible; no fake urgency; price, renewal date and cancel path are stated on every paywall.
4. Never hold data hostage. Downgrade or lapse never hides, locks or deletes a trip; read and export always work.
5. Digital features are sold only through In-App Purchase on iOS. The web app sells nothing in Phase 1: its paywall says "Upgrade in the iOS app" and links to the App Store, with no price list and no purchase button (web billing arrives with Android in Phase 2). Real-world costs (affiliate bookings and any trip cost paid to a third party) never use In-App Purchase and never unlock app features.
6. Never rank by commission, never sell user data, no banner ads, no lifetime plans.

## 2. Product catalogue

### 2.1 App Store products

Subscription group `hermi_membership` holds every auto-renewing product. In Phase 1 it holds Plus monthly and Plus annual, at the lowest level, so the higher levels can be added above it later (Later: Phase 2). One group means nobody holds two memberships at once. Apple Family Sharing is off on every product. Prices are US tier prices; use Apple's automatic regional pricing first, then tune India, Brazil, Mexico and Turkey by hand after launch.

| Product ID | Type | Price (US) | Duration | Group and level | Trial or intro offer | Entitlement granted |
|---|---|---|---|---|---|---|
| `hermi_plus_monthly` | Auto-renewing subscription | $5.99 | 1 month | `hermi_membership`, level 3 | none | `plus` |
| `hermi_plus_annual` | Auto-renewing subscription | $39.99 | 1 year | `hermi_membership`, level 3 | 7-day free trial (the only intro offer at launch) | `plus` |
| `hermi_trip_pass` | Non-renewing subscription | $9.99 | 90 days | none | none | `trip_pass` (one trip) |
| `hermi_credits_50` | Consumable | $2.99 | n/a | none | none | 50 purchased credits |
| `hermi_credits_150` | Consumable | $6.99 | n/a | none | none | 150 purchased credits |
| `hermi_credits_400` | Consumable | $14.99 | n/a | none | none | 400 purchased credits |

Product IDs are the `store_products.product_id` values seeded in 03 section 11.2 (plan codes such as `plus` and `credits_50` are `plans.code`). Plus annual is pre-selected on the paywall and Trip Pass is the lead offer for a trip with dates.

Later: Phase 2 or 3: the Family, Pro and Group Trip Pass products, web billing with Android, and the Stripe-sold `advisor_seat` and group payments. None of them is created in App Store Connect for Phase 1.

**The web paywall.** When a signed-in person hits a limit on the web app, the server returns the same offer with `purchasable: false` (04 section 5.20). The sheet says what the upgrade unlocks, the free path, and "Upgrade in the iOS app" with an App Store badge. It never shows a price, a checkout or a "cheaper on the web" line, and the web app has no purchase code at all.

Rules:

- Apple allows one introductory offer per group per user. Only `hermi_plus_annual` carries one at launch. Win-back and promotional offers wait until after launch (section 7.10).
- Every product needs localized display names and descriptions, a paywall review screenshot and the subscription terms text. Use Apple's standard EULA plus our Terms and Privacy links.
- Adding products later never changes a product ID. New price points for experiments get new product IDs (section 6.7).

### 2.2 Tier limits (the capability table)

The entitlement service resolves to this table, which mirrors the `plans.limits` seed in 03 section 11.1. Values the README states are final; others are defaults. The free first-import Trip Pass (section 10) has exactly the `trip_pass` column.

| Capability key (`plans.limits`) | `free` | `plus` | `trip_pass` (on its trip) |
|---|---|---|---|
| `active_trips` | 2 | unlimited (fair use 25) | `active_trips_bonus` 1: the passed trip does not count toward the owner's limit |
| `routes_per_trip` (cached-fare routes) | 1 | 5 | 3 |
| `live_routes` (checked daily, within 120 days of departure, `live_window_days`) | 0 | 3 | 2, at most 60 checks (`live_checks_max`) |
| Credits: `monthly_credits` for tiers, `credits_granted` for passes | 12 a month | 60 a month | 40 once |
| `collaborators` (people the owner can invite to one trip) | 1 | 6 (default) | 6 |
| `travelers_per_trip` | 2 | 8 | 8 |
| `price_alerts` (`live_alerts` false on Free; the booked-fare drop watch does not count here) | 1 cached-fare | 3 | 2 |
| `imports` (including Google Maps lists and calendar polling) and `calendar_feed` | yes | yes | yes |
| Share links (read-only, `Made with Hermi` footer on Free) | yes | yes | yes |
| `verify_items_per_run` (items one "Verify this plan" check may include) | 5 | 12 | 12 |
| `hide_presentation_footer` (true removes the Made with Hermi footer and PDF watermark) | false (shown) | true | true |

Everyone joins other people's trips free, on every tier, and gets that trip's capabilities on that trip.

Later: Phase 2 or 3: the `family`, `pro` and `group_trip_pass` columns and the capabilities only they carry (polls, manual cost splitting, collecting payments, the room-block request, scheduled routines, the priority queue and credit rollover).

Free taster: one lifetime deep agent run per user (`plans.limits.taster_agent_runs = 1` on `free`), held as a one-time `promo` row in `credit_grants` with `restricted_action = 'agent_run'` and `period_key = 'taster'`, so it is outside the monthly allowance and usable once ([06-ai-agents-spec.md](06-ai-agents-spec.md) section 5.9).

## 3. RevenueCat setup

RevenueCat (RC) sits between StoreKit 2 and our server. It validates receipts, handles restore and cross-device sync, and sends webhooks. Our server remains the source of truth: RC is a transaction feed, and `subscriptions`, `entitlements`, `trip_passes`, `store_transactions` and `credit_grants` are ours. A periodic reconcile job compares them with RC's REST API so a later move to direct StoreKit stays possible.

### 3.1 Project configuration

| Item | Setting |
|---|---|
| Project and app | One RC project "Hermi", one iOS app (bundle ID `world.hermi.ios`, default) with the App Store Connect in-app purchase key. Later: Phase 2: Android joins the same project. |
| App user ID | Our `users.id` (UUIDv7), never email. Call `Purchases.logIn(userId)` on sign-in and `logOut()` on sign-out. Anonymous IDs are not used because purchases are disabled until sign-in. |
| Attributes | Set `$email` off (we do not send it), `tier` not sent. Only `app_user_id`. No ad or attribution integrations. |
| Products | The six products in 2.1, each imported from App Store Connect. |
| Entitlements | `plus` (attached to `hermi_plus_monthly`, `hermi_plus_annual`). Trip passes and packs are not relied on as RC entitlements (see 3.3). The `family` and `pro` entitlements are added in Phase 2. |
| Offerings | See 3.2. |
| Webhook | `POST https://api.hermi.world/v1/webhooks/revenuecat` with an `Authorization` header holding a long random secret, environment-specific (sandbox events go to staging only). |
| Fees | RC is free under about $2,500 in monthly tracked revenue, then about 1% (verify). |

### 3.2 Offerings and packages

An offering is what the paywall shows. The server chooses the offering (section 6); the app fetches it by identifier from RC and renders our own React paywall in the Hermi theme (RC Paywalls UI is not used).

| Offering ID | Packages (RC package to product) | Used when |
|---|---|---|
| `default` | `$rc_annual` = `hermi_plus_annual` (highlighted, trial), `$rc_monthly` = `hermi_plus_monthly` (under "More options"), `trip_pass` = `hermi_trip_pass` | Generic upgrade |
| `trip_first` | `trip_pass` = `hermi_trip_pass` (lead), `$rc_annual` = `hermi_plus_annual`, `$rc_monthly` = `hermi_plus_monthly` | A trip with dates inside 120 days; live tracking and invite triggers |
| `plus_first` | `$rc_annual` = `hermi_plus_annual` (highlighted), `trip_pass`, `$rc_monthly` | Two or more active trips; third-trip limit |
| `credits` | `hermi_credits_50`, `hermi_credits_150`, `hermi_credits_400` | Out of credits |
| `exp_*` | Variants created for experiments (section 6.7) | Experiments |

The paywall shows at most three visible choices; credit packs appear only in the `credits` offering or as a secondary row on a credit-out paywall.

### 3.3 How purchases reach our server

1. The app calls `Purchases.purchase(package)`. On success it calls `POST /v1/purchases/sync` with no payload (the server asks RC for the subscriber) so the unlock is instant, before the webhook lands; for a pass the body carries the `trip_id` (04 section 5.19).
2. RC sends a webhook. The handler is in 3.4.
3. For a trip pass, the app asks "Which trip is this for?" before it starts the purchase (pre-selected when the purchase started from a trip) and sends the `trip_id` with `POST /v1/purchases/sync`. A pass bought with no trip stays unapplied until `POST /v1/me/passes/{pass_id}/bind` (7.7).
4. A nightly reconcile job lists RC subscribers who changed in the last 48 hours and compares them with our rows; differences raise an alert and are repaired from RC.

Non-renewing subscriptions are not a reliable RC entitlement (RC treats them like one-off purchases, verify in the dashboard). So `hermi_trip_pass` arrives as a `NON_RENEWING_PURCHASE` transaction; the server writes a `store_transactions` row (`kind = 'pass'`) and, once the trip is known, a `trip_passes` row. The 90 days (`starts_at`, `expires_at`), the trip binding and expiry are ours.

### 3.4 Webhook handling

Endpoint contract: verify the secret header; insert the raw body into `webhook_events` (`provider = 'revenuecat'`, `event_id`; the primary key is `(provider, event_id)`) and return 200 immediately; a worker job processes each row exactly once, idempotent on that key, and sets `status` (`processed`, `failed` or `ignored`), `processed_at` or `error`. Failures retry with backoff for 24 hours, then alert.

| RC event | Server action |
|---|---|
| `INITIAL_PURCHASE` (subscription) | Upsert `subscriptions` (`product_id`, `plan_code`, status `active` or `in_trial`, `period_start`, `period_end`, `auto_renew`, `is_trial`), upsert `store_transactions` (unique on `store` and `store_transaction_id`), recompute `entitlements` for the user, write a `credit_grants` row for the period (section 5.3), fire analytics `purchase_completed` |
| `RENEWAL` | Extend the period, new `store_transactions` row, grant credits for the new period if the plan is monthly (annual plans are granted monthly by the scheduler, 5.3), recompute entitlements |
| `PRODUCT_CHANGE` | Switch between Plus monthly and Plus annual (the only change in Phase 1); apply the rules in 7.3 |
| `CANCELLATION` with `cancel_reason` `UNSUBSCRIBE` | Set `auto_renew = false`, status stays `active` until `period_end`; start the win-back timer (7.10) |
| `CANCELLATION` with `cancel_reason` `CUSTOMER_SUPPORT` or a refund reason | Treat as a refund (7.6): revoke now, claw back credits |
| `UNCANCELLATION` | `auto_renew = true` |
| `BILLING_ISSUE` | Status `in_grace` if Apple's grace period is on (entitlement stays), else `billing_retry`; send the billing email and in-app banner (7.5) |
| `EXPIRATION` | Status `expired`; recompute entitlements; expire allowance credits of the subscription (purchased credits stay) |
| `NON_RENEWING_PURCHASE` | If product is a pass: write `store_transactions` (`kind = 'pass'`, `trip_id` when the purchase carried one); with a trip, insert `trip_passes` (`status = 'active'`, `starts_at`, `expires_at`, the `*_max` columns and `credits_granted` copied from `plans.limits`) and its `trip_pass` grant (7.7); with no trip the pass stays unapplied. If a credit pack: write a `purchase` grant (5.2) |
| `TRANSFER` | Move the subscription to the new `app_user_id` only if both are our users and the target has no active membership; otherwise flag for support |
| Any refund of a consumable or pass | Reverse per 5.6 and 7.6 |

Each handler runs in one database transaction with the ledger writes, so a half-processed event cannot exist.

### 3.5 Server endpoints (contract only; full shapes in [04-api-spec.md](04-api-spec.md))

`POST /v1/webhooks/revenuecat`, `POST /v1/purchases/sync`, `GET /v1/me/entitlements` (tier, status, period end, auto_renew, pass list, credit balance by pool, capability values), `POST /v1/purchases/restore`, `GET /v1/me/passes`, `GET /v1/trips/{trip_id}/pass`, `POST /v1/me/passes/{pass_id}/bind`, `POST /v1/me/passes/{pass_id}/move`, `GET /v1/me/credits`, `GET /v1/me/credits/ledger`, `GET /v1/credits/packs`, `POST /v1/credits/packs/claim`, `GET /v1/paywall/offer`, `POST /v1/paywall/events`, `GET /v1/me/referral`, `GET /v1/me/referral/rewards`, `POST /v1/me/referral/redeem`. `POST /v1/imports/{id}/confirm` returns the reward pass when a first import earned one (section 10). A visible "Restore purchases" button is on every paywall and in Settings (App Review checks it); it calls `Purchases.restorePurchases()` then `POST /v1/purchases/restore`.

## 4. Entitlement resolution

### 4.1 Data

- `subscriptions`: one row per store subscription: `user_id`, `store` (`apple` in Phase 1), `product_id`, `plan_code` (`plus`), `status` (`active`, `in_trial`, `in_grace`, `billing_retry`, `paused`, `expired`, `refunded`, `revoked`), `period_start`, `period_end`, `auto_renew`, `is_trial`, `original_transaction_id`.
- `entitlements`: a materialized, per-user result of the algorithm below: `user_id`, `tier_code` (`free` or `plus`), `source` (`none`, `subscription`, `comp`), `subscription_id`, `in_grace`, `valid_until`, `limits` (snapshot of `plans.limits`), `computed_at`. It is a cache that can always be recomputed; it is rewritten on every relevant event and by a nightly sweep.
- `trip_passes`: `id`, `trip_id`, `purchaser_user_id`, `plan_code` (`trip_pass`), `source` (`purchase`, `import_reward` or `admin`), `store_transaction_id` (null unless purchased), `original_transaction_id`, `starts_at`, `expires_at`, `live_routes_max`, `live_checks_max`, `live_checks_used`, `collaborators_max`, `travelers_max`, `credits_granted`, `status` (`active`, `expired` or `refunded`), `move_count`. A row exists only once the pass has a trip; a paid pass with no trip yet is a `store_transactions` row (`kind = 'pass'`, `trip_id` null) and is shown to the client as "unapplied". At most one pass is active per trip.

Tier rank: `free` 0, `plus` 1. A trip pass is an overlay on one trip, not a tier. Later: Phase 2: `family` 2 and `pro` 3.

### 4.2 Algorithm

```python
RANK = {"free": 0, "plus": 1}

def user_tier(user) -> Tier:
    """The user's own tier, from their subscription (a store subscription or a comp)."""
    sub = active_subscription(user.id)           # status in in_trial, active, in_grace; period_end >= now
    if sub:
        return Tier(sub.plan_code, source="subscription", until=sub.period_end)
    return Tier("free", source="none", until=None)

def trip_capabilities(trip) -> Capabilities:
    """What the trip itself can do: best of its owner's tier and any active pass on it (purchased or import reward)."""
    caps = [TIER_CAPS[user_tier(trip.owner).code]]
    for p in passes_on_trip(trip.id):            # status active, expires_at > now
        caps.append(PASS_CAPS[p.plan_code])
    return merge_best(caps)                      # per capability, see below

def merge_best(caps) -> Capabilities:
    out = {}
    for key in CAPABILITY_KEYS:
        vals = [c[key] for c in caps]
        out[key] = max(vals) if is_numeric(key) else any(vals) if is_boolean(key) else best_enum(key, vals)
    # live check budgets add up only within one source; take max of live_routes, not the sum
    return out

def actor_context(actor, trip) -> ActorContext:
    """What the person acting right now can do."""
    caps = trip_capabilities(trip)
    role = trip_role(actor, trip)                # owner, editor, viewer, from trip_members
    tier = user_tier(actor)
    return ActorContext(
        trip_caps=caps, role=role,
        personal_tier=tier,                      # governs actor's own limits: active trips they own, alerts on their own account
        credit_pools=spendable_pools(actor, trip),   # section 5.4
        ceiling=ceiling_for(actor, trip),        # 06 section 6.5
    )
```

Rules that the algorithm encodes:

1. **Best-of on a trip.** Capabilities on a trip are the per-capability best of the owner's tier and the active pass on the trip, purchased or import reward (03 allows one active pass per trip, `uq_trip_passes_one_active`; `merge_best` stays generic). Live check budgets are the maximum, not the sum, because they are a cost cap. This is the same merge as 03 section 7.1.
2. **Invitees.** Collaborators and viewers get the trip's capabilities on that trip only. They do not gain tier benefits elsewhere. They do not pay and cannot buy passes for a trip they do not own (they can buy their own membership).
3. **Personal limits follow the person.** Active trips (the count a user may own), personal alerts and personal credits depend on `user_tier(actor)`, not on the trip.
4. **Owner lapse.** If the owner's tier drops, the trip keeps its data; capabilities recompute. Existing live routes beyond the new limit are paused (not deleted), oldest first kept; collaborators above the limit stay as viewers; AI on the trip continues to draw from whoever acts.
5. **Free is never a lock-out.** If any limit would block reading or exporting, it does not apply to read and export. Trips above the active-trip limit after a downgrade become read-only "archived" until the owner archives or upgrades; a Free user with three trips after a lapse keeps reading and exporting all three and may edit the two most recently edited ones.
6. **Grace.** Status `in_grace` counts as active for resolution (`entitlements.in_grace` is set). `billing_retry` after grace does not.
7. **Caching.** `entitlements` is recomputed on: webhook events, trip pass binding or expiry, and a nightly sweep. API routes read `user_tier` through a 30-second in-process cache keyed by user id; `POST /v1/purchases/sync` bypasses it.

### 4.3 Enforcement points

Every mutation route calls `require(actor_context, capability, value)`; limit errors return HTTP 403 with `code = 'limit_reached'` (or `entitlement_required` when the capability is missing) and a `paywall` hint whose `reason` the client passes to the paywall engine (section 6; [04-api-spec.md](04-api-spec.md) sections 1.4 and 2.2). Not enough credits is 402 `insufficient_credits`, raised from the `WF402` error of `reserve_credits`. A client never infers a limit from its own data.

## 5. Credit system

One credit is a budget of up to $0.02 of provider spend. Credit action codes, prices and hard stops are in the README and in [06-ai-agents-spec.md](06-ai-agents-spec.md); this section owns the balance, grants, pools and ledger.

### 5.1 Pools and grants

`credit_grants` holds pools. `credit_ledger` holds every movement. A balance is the sum of `remaining` on unexpired pools; it is never stored as a single number.

| Pool (`credit_grants.kind`) | Created by | `credits` | Owner | Expires | Spend order |
|---|---|---|---|---|---|
| `monthly` (Free) | Lazily at first use in a month (`period_key` `YYYY-MM`) | 12 | user | End of calendar month (UTC) | 1 |
| `monthly` (Plus) | Subscription period or monthly tick | 60 | user | End of that month's period | 1 |
| `promo` | Free taster, referral rewards (section 9) | Taster: the `agent_run` price (40) with `restricted_action = 'agent_run'`. Referral: 20 for each person (`setting_referral_credits`), no restriction | user | Taster: none. Referral: 12 months after the grant | 2 |
| `trip_pass` | Pass start (purchased or import reward) | 40, from `plans.credits_granted` | trip (`trip_id`; spendable by any member acting on that trip) | Pass expiry (90 days) | 3 |
| `adjustment` | Support goodwill | any | user | Set by admin (default 12 months) | 4 |
| `purchase` | Pack purchase | 50, 150 or 400 | user | 12 months after purchase | 5 (oldest expiry first) |

`credit_grants` columns used: `id`, `user_id`, `trip_id` (required for `trip_pass` grants), `kind`, `credits`, `remaining`, `restricted_action`, `period_key`, `expires_at`, `store_transaction_id`, `created_at`. Idempotency comes from the unique indexes on (`user_id`, `kind`, `period_key`) and `store_transaction_id`. The spend order is the `ORDER BY` inside `reserve_credits` (03 section 5.13). Period keys for the growth grants: `import_reward:{import_id}` for the first-import pass and `referral:{reward_id}` for referral rewards.

### 5.2 Purchase grants

- A pack purchase arrives as `NON_RENEWING_PURCHASE` or a consumable transaction. The handler writes a `credit_grants` row (kind `purchase`, `credits` from `plans.credits_granted` of the product's `plan_code`, `store_transaction_id`, `expires_at` = purchase time plus `credits_valid_days`, 365) and a `credit_ledger` row (`entry_type = 'grant'`, positive `delta`, `idempotency_key` `store:{transaction_id}`); the unique index on `credit_grants.store_transaction_id` means a replayed webhook never grants twice.
- The pack screen states: "Purchased credits last 12 months and are spent after your monthly credits."
- Purchased credits also raise the account's spend ceiling by their cost value ([06-ai-agents-spec.md](06-ai-agents-spec.md) section 6.5). No other credit does: monthly allowances, the taster, Trip Pass credits, import-reward pass credits and referral credits never raise a ceiling.

### 5.3 Grants on renewal

| Plan | When credits are granted | `period_key` |
|---|---|---|
| Monthly (`hermi_plus_monthly`) | On `INITIAL_PURCHASE` and each `RENEWAL` (a paid period) | `YYYYMMDD` of the period start |
| Annual (`hermi_plus_annual`) | On purchase, and then on each monthly anniversary by the scheduler while the entitlement is active, until the annual period ends | `YYYYMMDD` of the anniversary |
| Trial (`hermi_plus_annual` trial) | Plus allowance (60) is granted at trial start but the ceiling for the trial is the normal Plus ceiling; trial exposure is about $0.45 in live checks and credits for a typical trial | `YYYYMMDD` of the trial start |
| Grace or billing retry | No new grant during `billing_retry`; during `in_grace` the current period's pool remains spendable; if payment recovers, the grant for the new period is written with the recovered period start | |
| Free | Lazily written on first credit use each month; idle accounts cost nothing | `YYYY-MM` |

The scheduler job `grant_monthly_credits` (02 section 5.1) runs hourly. It finds active annual Plus subscriptions whose monthly anniversary has arrived and whose last grant is older than 28 days, and writes the grant. It never grants during `billing_retry`, `expired` or `refunded`.

### 5.4 Spend order

When an action reserves N credits, the ledger draws from pools in this order, oldest expiry first within a priority:

1. Monthly allowance pools the actor can use: their own `monthly` grant.
2. `promo` grants (the taster, only for the `agent_run` action it is restricted to, and referral credits, for any action).
3. `trip_pass` grants of the trip they are acting on.
4. `adjustment` grants.
5. `purchase` grants, oldest expiry first (purchased credits are spent last).

A reservation that spans pools records each draw (`credit_ledger` rows with `grant_id`), so a refund returns credits to the same pools. If a pool expired before the refund, the refund is skipped for that part and the ledger says so; in practice runs last minutes, so this is rare. Credits are charged to the person who starts the action, so a collaborator on a Trip Pass trip first uses their own allowance, then the trip's pass pool. The order lives in `reserve_credits`, which raises SQLSTATE `WF402` when the pools cannot cover the price.

### 5.5 Expiry and rollover

- Allowances do not roll over on Free or Plus. Later: Phase 2: Pro rolls over one month.
- Expiry is processed by `expire_credit_grants()`, called by the `expire_credits` job (02 section 5.1; `reserve_credits` ignores expired pools, so the schedule only affects ledger tidiness): for each grant past `expires_at` with `remaining > 0`, it writes a `credit_ledger` row with `entry_type = 'expire'` and the negative `delta` and sets `remaining = 0`. Reserved credits are already out of `remaining`, so running actions are untouched; a second run finds nothing to expire.
- Downgrade or lapse: allowance pools vanish at period end; `purchase` and `adjustment` credits stay usable on Free.
- Trip pass credits expire with the pass; unspent credits do not convert to anything.

### 5.6 Refunds and clawback

| Event | Action |
|---|---|
| Refund of a pack | Remove the unspent part of that pack's pool (`credit_ledger` `entry_type = 'clawback'`, negative `delta`, `remaining` set to 0). If some credits were already spent, the billing service calls `record_credit_debt` (03 section 5.13): the shortfall is a `clawback` ledger row with no `grant_id` plus a `credit_debts` row (`credit_grants.remaining` never goes below 0). `reserve_credits` refuses while `credit_debts.amount > 0`, `settle_credit_debt` pays it down from the user's next grants (monthly, pack or pass), and `CreditBalance.blocked` tells the client; show "Your balance is below zero after a refund. Buy credits or wait for your next monthly credits." Repeated refund abuse (3 refunds in 90 days, counted from `store_transactions` with `status = 'refunded'`; default) blocks pack purchases for 180 days (`users.pack_purchases_blocked_until`, written by the billing service; the admin console lists accounts with an active block) and flags the account for review. |
| Refund of a subscription period | Revoke the entitlement now; remove the unspent part of that period's allowance pool; leave the credits of earlier periods. Spent allowance credits are not recovered (the cost is ours). |
| Refund of a trip pass | Status `refunded`; the trip drops to the owner's tier capabilities; remaining pass credits are removed; live checks stop. |
| AI action failed, refused, timed out or saved nothing | Automatic refund to the same pools ([06-ai-agents-spec.md](06-ai-agents-spec.md) section 6.3), never a support task. |
| Support goodwill | `adjustment` grant with a reason (ledger `entry_type = 'adjust'`); every adjustment writes `audit_log`. |
| Referral or import-reward abuse | An admin reject claws back the unspent referral credits of that reward; an admin revokes an import-reward pass and removes its unspent credits ([08-admin-control-center.md](08-admin-control-center.md) sections 6.2 and 6.9). Spent credits stay spent. |

### 5.7 Ledger entries and balance

`credit_ledger.entry_type` values: `grant`, `reserve`, `settle`, `refund`, `expire`, `clawback`, `adjust`. Each row: `user_id` (payer), `grant_id`, `entry_type`, `delta`, `charged` (settle rows), `reservation_id`, `action` (credit action code), `run_id`, `trip_id`, `usage_id`, `idempotency_key`, `note`, `created_at`. Rules:

- Append only; corrections are new rows.
- `reserve_credits` writes one negative `reserve` row per grant it draws from, all sharing a `reservation_id`. `settle_credits` writes positive `refund` rows for the uncharged part (back to the same grants) and one zero-delta `settle` row whose `charged` is final; charging 0 releases the whole reservation. A replay with the same `idempotency_key` returns the original reservation.
- Both run in the API or worker transaction: the candidate grants are locked with `SELECT ... FOR UPDATE` inside `reserve_credits`, so two parallel actions can never overspend. `release_stale_reservations()` settles abandoned reservations at 0.
- `GET /v1/me/credits` returns the balance per pool with expiry dates from the `credit_balances` view; the in-app usage meter shows "Monthly credits", "Trip Pass credits", "Bonus credits" (promo) and "Purchased credits" separately.
- A daily reconciliation asserts that, per grant, `credits` plus the sum of its non-`grant` `delta` values equals `remaining`; any mismatch alerts.

### 5.8 Credit prices added from the competitive analysis

Three actions join the price list of the README. Prices are in credits at the README rate (1 credit is a budget of up to $0.02); the real spend is lower for most items, which is the margin. Hard stops and the AI details are in [06-ai-agents-spec.md](06-ai-agents-spec.md) sections 5.11 and 5.12 and the seed rows in 03 section 11.3.

| Action | Credit action code | Price | Cap | Real cost (Haiku 4.5) |
|---|---|---|---|---|
| Read a pasted plan into items ("Verify this plan", step 1) | `explain` | 1 | one plan, up to 8,000 characters and 25 items | about $0.004 to $0.008 |
| Check a plan item (step 2) | `verify_plan` | 1 per checked item | 5 items per run on Free, 12 on Plus and Trip Pass (`plans.limits.verify_items_per_run`) | about $0.002 when place data settles it, about $0.017 with one search and one page; the hard stop is $0.02 per item |
| Recheck evidence older than 14 days | `explain` | 1 | one fact; refunded when the source page cannot be reached | about $0.005 |

How it plays out: a 7 item plan costs 1 + 7 = 8 credits; one full check of 12 items on Plus costs 13. A Free account has 12 monthly credits, which is two short checks of 5 items (6 credits each), so a person who likes it reaches the credit limit naturally and sees the normal credit-out paywall (`out_of_credits_verify`, 6.2): a Trip Pass (40 credits) covers about three full checks, Plus (60 a month) about four to five, and the 50-credit pack about three. The price is per checked item, not per dollar: a hit on a popular place served from the shared `place_check` cache still costs 1 credit, because the cache is margin. Unchecked items, items that hit a provider error or the dollar stop, and a plan in which nothing is found are refunded in full (06 section 6.3), so no one pays for work that did not happen. Every step states its price before it runs, and a check of 6 or more items asks for the usual confirm.

Margin check: worst case on Free is 1 + 5 credits for at most $0.11 of real spend, inside the Free ceiling of $0.25 a month (a check is admitted when the month has headroom for its hard stop, 06 section 6.5); worst case on Plus is 1 + 12 credits for at most $0.25 against a $2.25 monthly ceiling. A check of 12 items bought with purchased credits at the 50-credit price ($0.0598 a credit) earns about $0.78 against at most $0.25 of cost.

## 6. Paywall decision engine

The server chooses whether to show a paywall and what to offer. The client renders the result. This keeps frequency rules, experiments and entitlements in one place and lets us change them without an app release.

### 6.1 API

The engine behind `GET /v1/paywall/offer?reason={code}&trip_id={id}&surface={surface}` ([04-api-spec.md](04-api-spec.md) section 5.20) produces the decision below; the route maps `offering` and `highlight` to the `lead` and `alternatives` of `PaywallOffer`:

```json
{
  "show": true,
  "reason": "limit_reached",
  "trigger": "track_live",
  "offering": "trip_first",
  "highlight": "hermi_plus_annual",
  "copy_key": "paywall.track_live.trip",
  "trip_summary": "Live prices for Lisbon in April, checked daily until you fly",
  "free_path": {"label": "Not now", "action": "dismiss"},
  "credit_option": {"credits": 1, "label": "Check once for 1 credit"},
  "experiment": {"key": "annual_price", "variant": "control"},
  "muted_until": null
}
```

When `show` is false, `reason` says why (`session_cap`, `muted`, `first_session`, `recent_purchase`, `presentation`, `not_needed`), so the client can log and do nothing. `POST /v1/paywall/events` records `paywall_viewed`, `paywall_dismissed`, `purchase_started`, `purchase_completed`, `purchase_failed`, `restore_tapped` (the catalogue in [10-quality-security-launch.md](10-quality-security-launch.md) section 4; the `cta_tapped` event of the API is `purchase_started`) with the trigger as `placement`, offering, variant and trip; these go to PostHog; the few per-user facts the frequency caps need (recent view times, muted triggers) are kept in `users.prefs` under `paywall`, because 03 creates no `analytics_events` table.

### 6.2 Triggers

Trigger ids are the same as in [05-ui-ux-spec.md](05-ui-ux-spec.md) section 6.27 and the `paywall_viewed` event in [10-quality-security-launch.md](10-quality-security-launch.md).

| Trigger code | Moment | Shown when | Default offering | Free path |
|---|---|---|---|---|
| `third_trip` | Create a third active trip | Free limit reached | `plus_first` | Archive a trip |
| `second_route` | Add a second flight route | Free: 1 route per trip | `trip_first` (preview of cached fares first) | Keep one route |
| `track_live` | Tap "Track live" or "Refresh now" | No live access | `trip_first`, with "1 credit" option | Use 1 credit or cached fares |
| `alert_limit` | Price alert beyond the free one | Free alert used | `trip_first` | Keep the cached-fare alert |
| `invite` | Invite a second collaborator on a trip | Free owner (Free allows 1 collaborator per trip) | `trip_first` ("Plan together: they join free") | Keep the one collaborator, or share a read-only link |
| `out_of_credits_draft` | "Draft my itinerary" | Out of credits | `credits` or `plus_first`; blurred preview of day one | Plan manually, or invite a friend for credits (section 9) |
| `out_of_credits_research` | "Research this" or "Ask" | Out of credits | `credits` (small pack first) | Skip, or invite a friend for credits (section 9) |
| `out_of_credits_agent` | Deep agent run or fare hunt | Fewer than 40 credits | `credits` (400 pack highlighted when short by more than 50) or `plus_first` | Use a research question |
| `out_of_credits_verify` | "Check these places" in Verify this plan (or a Recheck) | Fewer credits than the items selected | `credits` or `plus_first` | Check fewer items, or invite a friend for credits (section 9) |
| `export_footer` | Export or share with the Made with footer | Free export | Soft line at export, never a modal | Export with footer |
| `ninth_stay` | Save the 9th lodging option | Free limit | `trip_first`; keep saving to a "later" list | Later list |
| `lifecycle_14d` | 14 days before departure | Free trip with dates | `trip_first` via email or in-app card, not a modal | Dismiss |

No trigger exists for the first session, for presentation playback, for actions after an affiliate booking, or for the first-import reward (the free Trip Pass is a gift, not an upsell). Hard limits (third trip) are a block with the free alternative, not a nag. A trip that already has an active pass, paid or promo, never gets a Trip Pass offer, and triggers that pass already covers do not fire. The API `reason` for each trigger ([04-api-spec.md](04-api-spec.md) section 2.2): `third_trip` is `trip_limit`; `second_route`, `track_live` and `alert_limit` are `live_routes`; `invite` is `sharing`; the four `out_of_credits_*` triggers are `credits` (the taster is `agent_taster_used`). `export_footer`, `ninth_stay` and `lifecycle_14d` are client-initiated and are sent as `reason` by their trigger code.

Later: Phase 2 or 3: the triggers `routine`, `group_tools`, `group_pass`, `collect_payments` and `household`, and the offerings `group`, `family` and `pro`.

### 6.3 Which offer to show

```python
def choose_offering(ctx, trigger):
    if trigger in CREDIT_TRIGGERS:                         # draft, research, agent out of credits
        return "credits" if ctx.tier != "free" or ctx.recent_pack_buyer else "plus_first"
    if ctx.trip and ctx.trip.dates_within(120):            # "I have a trip in March"
        return "trip_first"
    if ctx.active_trips >= 2:
        return "plus_first"
    return "default"
```

Defaults from the plan: best-converting first is Trip Pass, then annual Plus, then monthly Plus; Trip Pass leads when the trip has dates within 120 days, annual Plus leads when the user has two or more active trips. Plus annual is pre-selected in `default` and `plus_first`; the trial line states the price after the trial and the renewal date.

### 6.4 Household signal

Later: Phase 2: the household signal and the `family` offering. Phase 1 has no household.

### 6.5 Frequency caps and mute rules

| Rule | Default |
|---|---|
| No paywall in the first session or before the user has created a trip | always |
| At most one paywall per session | always |
| At most 3 paywall views per rolling 7 days, across all triggers | 3 |
| Dismissing a trigger mutes that trigger for 7 days | 7 days |
| Dismissing the same trigger 3 times mutes it for 30 days | 30 days |
| No paywall within 24 hours after a purchase, or while a purchase is pending | 24 hours |
| Never during presentation playback, offline, or while a run the user started is in progress | always |
| Never on a trip where the user is an invitee and the trigger is about owning the trip (collaborator invite, footer) | always |
| Credit-out paywalls show only when the user tapped the AI action (never as a banner) | always |
| Hard-limit blocks (third trip) always show their block, but the offer section is subject to the mute rules | always |
| Lifecycle prompts go by email or an in-app card, never a modal, and at most one per trip per 14 days | 14 days |

Counters are read server-side from `users.prefs` (`paywall`: the times of recent `paywall_viewed` and `paywall_dismissed` events and the muted triggers), so they hold across devices.

### 6.6 Paywall content rules

- Show price and billing period most prominently, then trial length and the price after the trial, auto-renew terms, a plain line on how to cancel with a link to "How billing works" (7.11), links to Terms of Use and Privacy Policy, and Restore (Guideline 3.1.2). On the web app the paywall shows none of the price lines: it says "Upgrade in the iOS app".
- Say what the user gets on this trip ("Live prices for Lisbon in April"), use real numbers ("3 routes, checked daily until you fly"), and never "unlimited AI" or "unlimited live tracking".
- Always a "Not now" control of the same size and contrast as the main one. No countdown timers, no invented scarcity, no pre-checked upsells. Trial reminder: a local notification and an email two days before the trial converts.
- The free path and the plain-text "How we earn money" link are on every paywall. No affiliate card appears beside an upsell.

### 6.7 Experiments

Server-side assignment: `variant = hash(user_id || experiment_key) mod 100` against the experiment's allocation, stored in `feature_flags` with `key = 'exp_{name}'` (keys are lowercase snake_case), the allocation and `started_at` in `rules`, the cells in `variants` and the owner in `description`. A user keeps their variant. Every variant discloses price and terms; no variant hides the free path. Price tests need separate App Store product IDs and an RC offering per variant (for example `hermi_trip_pass_b` at $7.99 and `hermi_trip_pass_c` at $12.99, `hermi_plus_annual_b` at $34.99).

| # | Experiment | Variants | Primary metric | Guardrail |
|---|---|---|---|---|
| 1 | Trip Pass price | $9.99, $7.99, $12.99 | Revenue per paywall view | Trip Pass to Plus cannibalization, refunds |
| 2 | Plus annual price | $39.99, $34.99 | Net revenue per view at 60 days | Trial start rate |
| 3 | Annual pre-selection | Annual pre-selected vs none | Annual share of purchases | Refund rate in 14 days |
| 4 | Lead offer on `track_live` | Trip Pass lead vs annual lead | Purchases per view | Plus churn at 60 days |
| 5 | Trial length | 7 days vs 3 days (annual only) | Trial to paid | Complaints |
| 6 | Credit pack order | 50 first vs 150 highlighted | Revenue per credit-out view | Pack refunds |

Rules: one experiment per trigger at a time; pre-register the metric and minimum run length (at least 4 weeks and 1,000 views per arm, default); stop an arm that lowers satisfaction (support tickets, ratings prompts). Results are read in the admin console ([08-admin-control-center.md](08-admin-control-center.md)).

## 7. Lifecycle rules

### 7.1 Trials

- Only `hermi_plus_annual` has a 7-day free trial, one per Apple ID per group. The paywall shows "7 days free, then $39.99 a year" with the renewal date, and a reminder two days before it converts. The reminder email and the local notification carry the one-tap cancel link (7.11).
- During the trial: status `in_trial`, full Plus capabilities and the normal Plus allowance, the normal Plus ceiling. Exposure for a typical trial is about $0.45.
- Trial to paid: `RENEWAL` event with a paid period; status `active`. Trial cancelled: access until the trial ends, then `EXPIRATION`.
- No trial for monthly plans, passes or packs. Reinstalls and new devices cannot restart a trial (Apple enforces one per Apple ID per group).

### 7.2 Purchases outside the lifecycle

- Buying a trip pass while on a membership is allowed and useful (the pass lives on one trip and is best-of with the owner's tier).
- Buying a membership while a trip pass is active is allowed; both coexist.

### 7.3 Plan changes

Phase 1 has one membership level, so the only change is between Plus monthly and Plus annual. Apple treats it as a crossgrade (same level, different duration) and applies it at the next renewal date (verify in App Store Connect). On `PRODUCT_CHANGE`:

1. Record the new product at its effective date and recompute entitlements.
2. No extra grant: the allowance is 60 credits a month on both products, and the current period's pool is left alone.
3. Analytics `subscription_changed` with the from and to products.

Later: Phase 2: upgrades to Family or Pro, with an immediate change and a top-up of the allowance.

### 7.4 Downgrades

There is no lower paid level in Phase 1; ending Plus is a cancellation (7.5). Later: Phase 2: Family to Plus, and the household dissolving at the period boundary.

### 7.5 Cancellation, grace, billing retry

- **Cancellation.** The user cancels through Apple (we cannot cancel for them), and we make it one tap to get there: the Account screen shows "Cancel subscription" on the plan card (7.11) and never hides it. Status stays `active` with `auto_renew = false` until the period ends, then `EXPIRATION`. The app shows "Your plan ends on {date}" and a one-tap resubscribe. Account deletion does not cancel an Apple subscription; the deletion screen says so and links to Manage Subscriptions.
- **Billing grace period.** Turn on Apple's billing grace period for all subscription products, 16 days (default). During grace the entitlement stays active and the credits of the current period stay spendable, but no new allowance is granted. The app shows a banner "We could not renew your plan. Update your payment method" with a deep link to the App Store subscription page; email on day 0, 7 and 14.
- **Billing retry.** After grace, Apple keeps retrying for up to 60 days in total. Status `billing_retry`: entitlement is off (the user drops to their remaining sources), the banner stays, purchased credits remain. If payment succeeds, a `RENEWAL` arrives, status returns to `active`, and the allowance for the new period is granted. If it never succeeds, `EXPIRATION`.
- **Pause.** Not used; Apple subscription pause is not offered. The pricing plan's "3-month pause" idea is handled by a win-back (7.10), not by the store.
- **Re-subscribe after expiry.** A new period, a new grant, no trial.

### 7.6 Refunds

Refunds happen through Apple (reportaproblem.apple.com); we cannot issue them. On a refund notice from RC:

| Product | Action |
|---|---|
| Subscription | Status `refunded`, revoke now, claw back the unspent allowance of that period (5.6), count refunds per user from `store_transactions` (`status = 'refunded'`) |
| Trip Pass (paid) | Status `refunded`; the pass stops granting capabilities; its unspent credits are removed; live checks stop. The trip and its data stay. |
| Credit pack | Clawback (5.6); negative balance blocks paid AI until positive |
| Pattern | 3 refunds in 90 days: block pack purchases for that user for 180 days (`users.pack_purchases_blocked_until`) and flag for review (default) |
| Import-reward Trip Pass | Nothing was paid, so there is no refund. An admin may revoke it for abuse (section 10) |

Support can grant goodwill credits (an `adjustment` grant) but never reverse a refund into a free pass.

### 7.7 Trip pass binding and expiry

1. On purchase the store transaction is written (`store_transactions`, `kind = 'pass'`). If the purchase started from a trip, the app sent its `trip_id` and the `trip_passes` row is written at once. Otherwise the app asks "Which trip is this for?" and lists the owner's trips; until then the pass is unapplied (a `store_transactions` row with `trip_id` null and no `trip_passes` row) and waits in Settings, Purchases, for 12 months (default), then lapses.
2. Binding (`trip_id` on `POST /v1/purchases/sync`, or `POST /v1/me/passes/{pass_id}/bind`) inserts `trip_passes` with `starts_at = now()` and `expires_at = starts_at + 90 days`, sets `store_transactions.trip_id`, copies `live_routes_max`, `live_checks_max`, `collaborators_max`, `travelers_max` and `credits_granted` from `plans.limits` of the purchased plan, writes the `trip_pass` credit grant (40, with `trip_id`) and recomputes the trip's capabilities. Only the trip owner may bind, and the purchaser must be the owner. A trip holds one active pass (`uq_trip_passes_one_active`); binding a second pass is refused with `409 state_conflict`.
3. A pass can be moved once (`move_count` 0 to 1, `POST /v1/me/passes/{pass_id}/move`) to another trip that the same owner owns; moving keeps the original `expires_at`, changes `trip_id` on the pass and on its unspent `trip_pass` grant, and pauses live routes on the old trip. A second move is refused.
4. Live check counters (`live_checks_used` against `live_checks_max`) belong to the pass and move with it.
5. Expiry at `expires_at`: `status` becomes `expired`, capabilities drop to the owner's tier, unspent pass credits expire, the trip stays. The app shows the pass status and expiry date in the trip's settings, a notice 7 days before, and offers renewal by buying a new pass (a new pass starts a new 90 days).
6. A pass is tied to the purchaser's Apple ID through the transaction; it is restorable, because it is a non-renewing subscription and not a consumable.
7. If the bound trip is deleted by the owner, the trip sits in trash for 30 days and keeps its pass; restoring the trip restores the pass. When the trip is purged, the `trip_passes` row goes with it (`trip_id` cascades), the pass is not refunded and the `store_transactions` row stays as the record.
8. An import-reward pass (section 10) is written by the server with no store transaction (`source = 'import_reward'`), so it is not restorable through the store; it stays on the account and on its trip, and can move once like any pass.

### 7.8 Family membership changes

Later: Phase 2: households, the Family plan, pooled credits and the churn guard.

### 7.9 Group Trip Pass rules

Later: Phase 2: the Group Trip Pass (12 travelers, polls, manual cost splitting, the room-block request and the upgrade from a Trip Pass).

### 7.10 Win-back and retention (after launch)

When `auto_renew` turns false, the next two checkpoints are a cancellation survey (one question, skippable) and a win-back offer 7 days after expiry: an Apple promotional or win-back offer on the same product (for example 3 months at a discount, verify product configuration). Win-back offers are configured in App Store Connect after the first month of data and delivered through RC; never used as a dark pattern (shown once, clearly priced). A lifecycle email "Planning another trip?" goes out to lapsed users with a trip in the next 120 days.

### 7.11 Plain billing page and one-tap cancel

These are trust features that answer the most repeated complaints about travel apps (hard-to-find cancel, surprise renewals). They cost nothing to run.

- **One-tap cancel link.** The plan card on the Account screen has a first-level row "Cancel subscription" (next to "Change plan"), not inside a menu. One tap opens Apple's own subscription sheet for that subscription (`Purchases.showManageSubscriptions()` in RevenueCat, which opens StoreKit's manage-subscriptions sheet), where Apple asks for the final confirm. We ask no questions and show no retention offer before the link. `Entitlements.cancel_url` (04 section 5.19) carries the same target for the web app, where the row reads "Cancel in the iOS app" and opens Apple's subscription page (`https://apps.apple.com/account/subscriptions`). The trial reminder email, the renewal receipt email and the billing-problem emails carry the same link. The link is shown even when `auto_renew` is already false, where it reads "Your plan ends on {date}".
- **How billing works (`/billing`, also in Settings and on every paywall).** A plain page, written in short sentences and reviewed with every price change: what each plan costs and when it renews; the 7-day trial on the annual plan, what happens on day 8 and that we remind you 2 days before; that Trip Pass is a one-time $9.99 for 90 days and never renews; that credit packs are one-time, last 12 months and are spent after monthly credits; how to cancel (the link above) and what stays when you do (your trips, read and export, purchased credits); that refunds go through Apple (`reportaproblem.apple.com`) and what we can do ourselves (goodwill credits); that we never store card details; that purchases are in the iOS app only for now; and the free path: what stays free on every tier.
- **Rules.** No dark patterns around either: no countdowns, no "are you sure", no hidden or renamed cancel. The page and the link are included in the App Review notes.

## 8. Affiliate system

Affiliate income is the Free tier's revenue. It is earned on every tier in the same places. Every partner link goes through our redirect. Program details and rates are "reported, verify".

### 8.1 Program catalogue

`affiliate_programs` holds one row per program: `code`, `name`, `network`, `category`, `status` (`planned`, `applied`, `active`, `paused`, `closed`), `hosts`, `commission_model`, `commission_note`, `cookie_days`, `subid_param`, `subid_max_len`, `campaign_param`, `terms_url`, `countries_allowed`, `countries_blocked`, `feature_flag_key`. Seed data for launch (Travelpayouts, Viator partner API, Stay22; the first column is the `code` seeded in 03 section 11.4:

| Code | Network | Category | Status at launch | Notes |
|---|---|---|---|---|
| `travelpayouts_aviasales` | Travelpayouts | flights | active | Cached-fare data API is open; "Book" opens an Aviasales search with our marker |
| `travelpayouts_kiwi` | Travelpayouts | flights | active | Label self-transfer fares |
| `travelpayouts_tripcom_flights` | Travelpayouts | flights | active | Trip.com flights; the lodging program is `travelpayouts_trip` |
| `travelpayouts_booking` | Travelpayouts | lodging | active | Show Booking's required disclosure line next to the link |
| `travelpayouts_agoda` | Travelpayouts | lodging | active | |
| `travelpayouts_trip` | Travelpayouts | lodging | active | |
| `travelpayouts_hostelworld` | Travelpayouts | lodging | active | Hostel items only |
| `stay22` | Stay22 | lodging | active (challenger) | Maps widget and Link Swap for pasted listing hosts that have approved programs |
| `travelpayouts_discovercars` | Travelpayouts | cars | active | |
| `travelpayouts_localrent` | Travelpayouts | cars | active | |
| `travelpayouts_omio` | Travelpayouts | trains | active | Train and bus search |
| `travelpayouts_welcome` | Travelpayouts | transfers | active | |
| `travelpayouts_kiwitaxi` | Travelpayouts | transfers | active | |
| `viator` | Viator partner API | tours | active | Basic access is self-service; weekly payout, $50 minimum |
| `travelpayouts_gyg` | Travelpayouts | tours | active | |
| `travelpayouts_tiqets` | Travelpayouts | tours | active | |
| `travelpayouts_gocity` | Travelpayouts | tours | active | Pass cities only |
| `travelpayouts_radical` | Travelpayouts | luggage | active | On checkout days only |
| `travelpayouts_compensair` | Travelpayouts | compensation | active | Paid per confirmed application |
| `travelpayouts_ekta`, `travelpayouts_visitorscov` | Travelpayouts | insurance | planned | Off until legal sign-off; insurer-approved copy only |

Later: Phase 2: the direct programs `expedia_group` (Vrbo, Expedia, Hotels.com), `booking_direct`, `skyscanner`, `airalo`, `getyourguide_direct` and the month-3 programs after them.

Not integrated: Airbnb (no program an app can join: listings get a plain link that is never converted), credit cards, VPNs, Amazon product data, the Expedia Rapid API, and new integrations on Partnerize (merging into CJ).

Rules:

- One partner per surface per test cell; never two networks on one button.
- Each program has a kill switch named `affiliate.{code}` in `kill_switches` (`feature_flag_key` stays null unless a partner needs a staged rollout) and there is a global `affiliate.all`. An off switch hides that partner's buttons on the next fetch and makes `/go` return the non-affiliate fallback (the plain destination or a neutral search link).
- Pasted listing links stay exactly as pasted. A separate labeled "Book via partner" button offers a partner link built from the URL text (host, path, the trip's dates), never by fetching the page, and only for hosts with an approved program. It never appears for Airbnb. The server never fetches Airbnb, Vrbo or Booking.com pages, not even for link previews (previews for partner hosts are disabled by default).
- No list, badge, default sort or AI answer depends on commission. When two partners offer the same item, the choice is by A/B cell or the user's own criteria, never by payout.
- Checklist partner items (eSIM, insurance, transfers, bookings) use only programs in the table above that are `active`. An item with no active program shows its plain guidance and no button.

### 8.2 Link templates

`affiliate_link_templates` holds one row per program, kind and surface cell: `program_id`, `kind` (`search`, `deeplink`, `widget`, `map`), `surface` (null for any), `variant` (the A/B cell), `weight`, `template` (a URL with placeholders), `required_placeholders`, `active`. Geography comes from the program's `countries_allowed` and `countries_blocked`. Templates are stored, never taken from a request. Placeholders: `{sub_id}` (our click id, or `{short_id}` where the network limits length), `{marker}`, `{campaign}` (the surface label), `{dest_enc}` (URL-encoded target), `{dest}`, `{origin}`, `{destination}`, `{depart}`, `{return}`, `{adults}`, `{checkin}`, `{checkout}`, `{guests}`, `{lat}`, `{lon}`. Partner ids such as `pid` or `mcid` are written literally into the template text. Verify each template against the network's terms page after sign-up; these are the intended shapes.

| Program | Template shape (intended) | Sub-id field |
|---|---|---|
| Travelpayouts (partner links) | `https://tp.media/r?marker={marker}.{short_id}&p={program_p}&u={dest_enc}&campaign_id={campaign}` | Appended to `marker` |
| Aviasales data API booking link | `https://www.aviasales.com/search/{route_code}?marker={marker}.{short_id}` | Appended to `marker` |
| Viator | `https://www.viator.com/tours/{path}?pid={pid}&mcid={mcid}&medium=api&campaign={short_id}` | `campaign` |
| Stay22 | `https://www.stay22.com/allez/{brand}?aid={aid}&campaign={short_id}&address={dest}&checkin={checkin}&checkout={checkout}&adults={adults}` | `campaign`; surface in a second field where supported (`campaign_param`) |

### 8.3 Creating a click: `/v1/outbound` and `/go/{click_id}`

1. The app calls `POST /v1/outbound` with `{entity_type, entity_id, surface, trip_id, checklist_item_kind?}` (authenticated; see [04-api-spec.md](04-api-spec.md)). The server checks trip access, checks that the program's kill switch is on, chooses the program (feature flags, geography, A/B cell; never commission), builds the target URL from the stored template and inserts a `link_clicks` row, then returns `https://go.hermi.world/go/{click_id}`. Rate limit: 60 an hour per user (04 section 1.8), with repeat clicks on the same entity within 30 seconds returning the same `click_id`.
2. `click_id` is a random 128-bit value encoded in base62 (about 22 characters), generated only by this authenticated call. Where a network limits sub-id length, `link_clicks.short_id` (8 to 12 characters) is sent instead; the click id itself never leaves our system except in our own URL.
3. The app opens the URL in `SFSafariViewController` (Capacitor Browser plugin). The web app opens a new tab with `rel="noopener noreferrer"`.
4. `GET /go/{click_id}` looks the row up; checks it is under 10 minutes old and has not been used; sets `clicked_at`; returns HTTP 302 to the partner URL built from the stored template, with the sub-id. Headers: `Cache-Control: no-store`, `Referrer-Policy: no-referrer`. The response has no body and renders no page, so there is no third-party script, pixel or cookie from us. A known but expired or used id returns a 302 to the plain destination (the non-affiliate route) so the user is never stranded; an id that never existed returns 404 with an empty body.
5. No open redirects: the target is only ever a stored template filled with validated fields. There is no `url=` parameter on `/go`.

`link_clicks` columns used: `id`, `click_id` (the random sub-id), `short_id`, `user_id`, `trip_id`, `program_id`, `template_id`, `entity_type`, `entity_id`, `checklist_item_kind`, `surface`, `variant` (A/B cell), `destination_url`, `opened_in` (`sfsvc`, `safari` or `web`), `created_at`, `clicked_at`, `redirect_status`, `country`, `platform`, `app_version`, `ip_hash` (salted, rotated monthly). The category comes from the program (`affiliate_programs.category`). No advertising ID, no IDFA or IDFV, no device fingerprint.

### 8.4 Sub-ids, privacy and App Tracking Transparency

- The sub-id is a random per-click token. User id, trip id and email never appear in a URL; the join from a conversion to a click to a user and trip happens only in our database.
- No ad, attribution or third-party analytics SDK; no hashed email or phone to any partner. Conversions are pulled by our server from each network's API and joined to `link_clicks` in our database. This keeps the app outside App Tracking Transparency (no ATT prompt); note it in the review notes and verify with Apple.
- Privacy label: Usage Data (product interaction: outbound clicks), linked to identity, for analytics and app functionality, not used for tracking.
- Click rows are retained 25 months; aggregates 7 years (suggested; counsel to confirm). The privacy policy lists the purpose "affiliate revenue attribution and fraud detection".

### 8.5 Disclosure

- Sentence used everywhere, next to every partner button, in AI output cards, on shared trip pages, in presentation mode and in the PDF: **"We earn a commission if you book here."** Text, never color alone; VoiceOver reads it in the same element as the button.
- "Ad" tag on UK and EU storefronts (by App Store storefront country or account country; the stricter rule applies when unknown).
- Booking.com adds its own required line where its tracking link appears.
- Every list says how it is sorted (price, rating, distance, hearts) and that commission plays no part. Prices from partners show the date checked and provider. "How we earn" page (`/how-we-earn`, public, no sign-in) linked from Settings, every paywall and empty states, and from every `/vs` page: it states the rules (never ranked by commission, every link labeled, no ads, no sale of data, Airbnb, Vrbo and Booking.com pages never fetched), lists every active partner by category with its disclosure line, and shows live counts (partners and categories, from `affiliate_programs`; 04 section 5.28). It is rendered from data, so a new partner cannot be added without appearing on it; a "Hide booking links" switch collapses buttons to a plain "Open on partner site" link.
- No insurance card until the trip has a chosen flight or booking; no eSIM card for domestic trips; AI never gives insurance advice; visas link to official sites first.
- No affiliate push that exists only to drive clicks (Guideline 4.10). User-requested price alerts are fine, and they link into the app route, not to a partner.
- Affiliate purchases never unlock app features, and nothing is worded as if they do (Guideline 3.1.1).

### 8.6 Nightly conversion import

A worker job per network runs nightly (05:00 UTC, jittered per network) and on demand from the admin console. Each writes `affiliate_conversions`: `program_id`, `network`, `network_txn_id`, `sub_id_returned`, `click_id` (nullable when unmatched), `match_status` (`matched`, `unmatched`), `status` (`pending`, `approved`, `rejected`, `paid`), `network_status_raw`, `booking_value_minor` with `booking_currency`, `commission_minor` with `commission_currency`, `booked_at`, `click_lag_hours`, `approved_at`, `paid_at`, `reversal_at`, `status_history`, `raw` (jsonb). USD figures are computed at read time with `fx_rates` at the event date, not stored. Unique on `(program_id, network_txn_id)`; every import is an idempotent upsert that updates status and amounts and appends to `status_history`. A network reversal or cancellation is stored as `rejected` with `reversal_at` set.

| Network | Source | Sub-id where it comes back |
|---|---|---|
| Travelpayouts | Booking statistics API, then payments API | The part of `marker` after the dot (`sub_id`) |
| Viator | Partner API commissions report (weekly payouts) | `campaign` |
| Stay22 | Reporting API or dashboard export (verify) | `campaign` |

Matching and health:

- Match a conversion to a click by sub-id. Unmatched conversions are stored and counted; the unmatched share above 10% for a program is a tracking break and alerts.
- Status changes: `pending` becomes `approved` or `rejected` after the partner's validation window (often after check-out); `approved` becomes `paid` with `paid_at` when the network pays. Cancelled stays and returns become `rejected` (with `reversal_at`).
- Job alerts: failed import, zero rows for 3 days on a live program, reversed amounts above 25% of the month, redirect 4xx or 5xx above 1%, clicks down more than 50% day over day, a program approval rate under 60%.
- Network payouts (what actually lands in the bank) are reconciled monthly by hand against `paid` rows; differences are logged as `adjust` notes in `audit_log`.
- A Travelpayouts written confirmation that a native app using the partner-links API with a server-side redirect is allowed, and the sub-id length and character rules, are a pre-launch item.

### 8.7 Revenue attribution

Revenue is attributed along the chain conversion, click, (user, trip, surface, program, category).

- **Recognition.** Show three numbers: pending (expected), approved, paid. Expected revenue for pending rows uses the program's trailing 90-day approved-to-pending ratio. Reported revenue for accounting is paid; management revenue is approved plus expected pending.
- **Per trip.** Sum of conversions whose click has that `trip_id`, in USD, by category. "Real trips" are trips with dates in the next 12 months and at least a chosen flight, a shortlisted stay or two itinerary items.
- **Per surface.** Conversions grouped by the click's `surface` and `checklist_item_kind`.
- **Per user and tier.** Joined to the clicker's tier at click time (`link_clicks.tier_code`, stamped when the click is minted from the effective tier or pass, so no later join to `subscriptions` or `trip_passes` is needed) so Free versus paid earnings are reportable.
- **Overlap.** When Viator and GetYourGuide both show the same item, only the booked one is counted; never count two commissions for one booking.
- **Dedupe of self-purchase.** Conversions from accounts on the internal list (`admin_users` and test accounts) are excluded.

### 8.8 Dashboards (admin console)

Views in [08-admin-control-center.md](08-admin-control-center.md), built on the materialized views `revenue_by_month`, `revenue_by_surface` and `revenue_by_partner` (03 section 5.15) and on admin queries for category and revenue per MAU (same MAU definition as section 12, divided by the PostHog count), `click_to_booking_by_surface`, `epc_by_program_and_surface`, days from click to booking and from approval to payout, a cash view (pending, approved, paid, and a 3-month projection from the real pending-to-approved ratio), the unmatched share per program, and the A/B experiment results. Annualized affiliate income per monthly user is tracked from launch against the kill rule (under $0.20 at month 9).

### 8.9 Affiliate experiments

Queue in priority order (one per surface at a time, pre-registered metric, server-side assignment, never hide the disclosure or rank by commission): (1) link-out container (`SFSafariViewController` vs external Safari), measured as tracked bookings per 100 clicks; (2) lodging partner (Travelpayouts Booking.com versus Stay22), as net commission per click; (3) disclosure wording (every variant discloses: standard sentence, "Paid link: we earn a commission.", standard plus "Ad"); (4) checklist timing (45, 30 or 14 days before departure); (5) button position on lodging cards; (6) price alert delivery (push, email, in-app); (7) "Book the plan" last slide on or off by default; (8) "Hide booking links" visibility; (9) paid-tier weighting. Sample size note: detecting 3.0% to 3.6% lodging conversion needs about 20,000 clicks per arm, so early on test click-through and treat bookings as a slow aggregate.

## 9. Referral credits

Referral credits reward people who bring a friend who actually plans a trip. They are a growth cost, not revenue, and they are paid only in AI credits: never cash, never a discount on a purchase. They are available to every tier. The routes are in [04-api-spec.md](04-api-spec.md) section 5.27, the tables `referral_codes` and `referral_rewards` in 03 section 5.9. Flag `referrals`; kill switch `referrals.grant`.

### 9.1 Codes, links and redeeming

- Every user has one code (`referral_codes`: 8 characters from an alphabet without 0, O, 1 and I) and a link `https://hermi.world/r/{code}`. The link is a page on the marketing site that opens the app through a universal link; its text comes from `GET /referrals/{code}`. The app shares it through the native share sheet and never reads the contact list.
- A code is redeemed by a signed-in, non-guest account, either in `POST /me/bootstrap` at sign-up or with `POST /me/referral/redeem` within 14 days of sign-up. A guest keeps the code locally and it travels with the claim. One referrer per account, set once (`uq_referral_rewards_referee`).
- `GET /me/referral` returns the code, link, counts and credits earned; `GET /me/referral/rewards` returns the history.

### 9.2 Grant rules

| Status (`referral_rewards.status`) | Meaning |
|---|---|
| `pending` | The code was redeemed |
| `qualified` | The referred person did the qualifying thing |
| `granted` | Credits were given to both people |
| `rejected` | Abuse or not eligible (`reject_reason`) |

- **Qualifying.** The referred person has a verified email (an Apple relay address counts) and, within 30 days of redeeming, creates their first trip with dates. On iOS the device must have passed App Attest, or the stricter fallback in [02-architecture.md](02-architecture.md) section 8.
- **Reward.** The amounts live in the setting `setting_referral_credits` (settled values): 20 credits for each person, expiring after 12 months, with the caps in 9.3 and no ceiling raise. Each is a `promo` grant in `credit_grants` with `period_key = 'referral:{reward_id}'` (a unique key, so a reward can never be granted twice), expiring 12 months after the grant, with a `grant` entry in `credit_ledger`. Both people get a notification. The job `grant_referral_rewards` (02 section 5.1) marks rewards `qualified` and calls `grant_referral_reward()`.
- **Spending.** Referral credits are spent after the monthly allowance and before pass and purchased credits (5.4), on any AI action. They cannot be bought, sold or transferred and have no cash value. They are spent inside the normal provider-spend ceilings and do not raise them ([06-ai-agents-spec.md](06-ai-agents-spec.md) section 6.5), so on Free they are used across several months rather than at once.

### 9.3 Abuse limits

All values are defaults in the setting `setting_referral_credits` and can change without a release.

| Limit | Rule |
|---|---|
| Referrer caps | At most 5 rewards granted to one referrer in a rolling 30 days and 10 in a calendar year (`referrer_monthly_cap` and `referrer_yearly_cap`). Past a cap the referred person still gets their credits and the referrer gets nothing more |
| New people only | The code must be redeemed within 14 days of sign-up. The referred person must not share an identity (Apple or Google subject, or a normalized email with case, dots and plus suffix removed where the provider ignores them) with an existing account, or with an account deleted in the last 90 days (kept only as a salted hash for this check) |
| Self-referral | Not your own code; not the same device key (App Attest key or device id) as the referrer; not the same hashed IP within 30 days; not the same normalized email. No chains between two accounts (A refers B, then B refers A) |
| Real activity | No reward without a verified email and the qualifying action above |
| Disposable email | Addresses on a disposable-domain denylist cannot earn or give rewards. Apple's private relay addresses are allowed |
| Velocity | More than 5 redemptions of one code in 24 hours stay `pending` until an admin reviews them in the abuse view ([08-admin-control-center.md](08-admin-control-center.md) section 6.9) |
| Reversal | A refund or an abuse flag on the referred account before the grant sets `rejected`. After the grant, an admin reject claws back the unspent credits of both people; spent credits stay spent |
| Stopping abuse | An admin can disable one code (`referral_codes.disabled_at`). The kill switch `referrals.grant` pauses every grant: codes can still be redeemed and rewards wait as `qualified` |
| Detection | Daily alerts for a referrer with a high reward rate, shared device keys across accounts, and referred accounts that never return ([08-admin-control-center.md](08-admin-control-center.md) section 10) |

The referrer sees only "We could not count this referral" for a rejected reward, never the reason.

### 9.4 Where it appears

- Settings, "Invite friends": the link, a plain rule line ("You and your friend each get credits when they plan their first trip. Credits are for AI features."), and progress.
- A quiet "Invite a friend for credits" line in the free path of the out-of-credits paywalls (6.2). Never a modal, never a push that exists only to ask for invites, never pre-selected contacts.
- Analytics events: `referral_link_shared`, `referral_signup_attributed`, `referral_reward_granted` (12.4).

### 9.5 Data

`referral_codes` and `referral_rewards` with the functions `ensure_referral_code`, `redeem_referral` and `grant_referral_reward` (03 section 5.9). Only `referrals.service` calls them, and credits are written only through `credits.service` ([02-architecture.md](02-architecture.md) section 3).

## 10. Free Trip Pass for a first import

The free Trip Pass rewards people who switch from another planner by importing a real trip. It is a promo pass: a real Trip Pass (90 days, the same limits, 40 credits) with no store transaction, stored as `trip_passes.source = 'import_reward'`. It is given once per user, so the first trip they bring over shows what a paid trip can do.

### 10.1 Rules

- **Once per user.** The first qualifying import earns it, once for life (gate `import_reward`). The unique index `uq_trip_imports_one_reward` and `grant_import_reward()` enforce it, and the reward flag lives on the import row, so deleting the trip and importing again never grants a second pass.
- **Conditions.** All must hold, otherwise nothing is granted and, where noted, the reward is not consumed:
  - The confirm saved at least 3 items, at least one a flight or a stay (the setting `setting_import_reward` holds the minimum). Place-only imports (Google Maps lists and pasted places) and calendar change confirmations never qualify. An empty, duplicate or junk import earns nothing, and the same file hash (`trip_imports.content_hash`) or the same set of event `UID` values cannot earn it twice across accounts.
  - The trip is owned by the importer, is not in the trash, and has no active pass (otherwise nothing is consumed and the reward stays for the next import).
  - The owner has no active Plus subscription, because Plus already carries these capabilities (nothing is consumed).
  - The account has a verified email (an Apple relay address counts), and no earlier reward went to this user, this normalized email, or this Apple or Google subject.
- **Grant.** `grant_import_reward()` inserts a `trip_passes` row (`plan_code = 'trip_pass'`, `source = 'import_reward'`, no `store_transaction_id`, `starts_at` now, `expires_at` 90 days later, and the limits of the `trip_pass` plan: 2 live routes, 60 live checks, 6 collaborators, 8 travelers), writes the `trip_pass` credit grant (40 credits, `period_key = 'import_reward:{import_id}'`, expiring with the pass), and sets `trip_imports.reward_granted_at` and `reward_pass_id`. A concurrent second call does nothing. Only `billing.service` writes `trip_passes`.
- **A gift.** No card is asked, it is not a trial that converts, it is not refundable, and it is not restorable through the store because there is no transaction. It can move to another trip once, like any pass (7.7). It expires like any pass: a notice 7 days before, capabilities drop to the owner's tier, unspent pass credits expire, the trip stays.
- **What the user sees.** `GET /me/import-reward` drives the onboarding card and the import screen copy, and the confirm response carries the pass. One note on the result: "Your trip has a free Trip Pass for 90 days: 2 live fare routes, up to 6 people to plan with, and 40 credits." It is never a paywall. The 7-day expiry notice may offer a Trip Pass or Plus under the normal mute rules (6.5), and a trip with an active pass never gets a Trip Pass offer.

### 10.2 Cost and abuse control

- Worst case per pass is the Trip Pass ceiling ($1.80 of provider spend over 90 days); typical use is far lower. These passes count at $0 revenue and their exposure is reported as a promotional cost ([08-admin-control-center.md](08-admin-control-center.md) section 6.15).
- An admin can revoke an import-reward pass (`passes.revoke`): the pass ends, its unspent credits are removed, and the ledger is reversed. An alert fires when the day's rewards exceed 5 percent of sign-ups.
- The kill switch `import.all` stops every import path and the reward. Setting `enabled = false` on `setting_import_reward` stops only the reward.
- Analytics: `import_reward_granted`.

## 11. Later lanes

Later: Phase 2: Family plan and households (products, pooled credits, household rules), Group Trip Pass with polls and manual cost splitting and the room-block request, Pro with scheduled routines, the concierge lane, direct affiliate programs beyond Travelpayouts, Stay22 and Viator, Android purchases and web billing.

Later: Phase 3: Stripe and Stripe Connect group payments, Hermi for Advisors (Stripe Billing), partner guides, printed trip books, in-app hotel booking through LiteAPI, and white-label and API.

None of these changes the principles in section 1.

## 12. Revenue reporting and metrics

### 12.1 Sources

| Source | What it gives | Stored in |
|---|---|---|
| RevenueCat webhooks and reconcile | Subscription, pass and pack transactions | `subscriptions`, `store_transactions`, `trip_passes`, `credit_grants` |
| App Store Connect sales and trends (monthly import) | Apple's net proceeds and tax adjustments | finance sheet, reconciled to `store_transactions` |
| Affiliate networks | Commissions | `affiliate_conversions` |
| `ai_usage`, `provider_calls` | Variable cost | [06-ai-agents-spec.md](06-ai-agents-spec.md) |
| PostHog | Funnels, paywall views (frequency-cap state is in `users.prefs`) | |
| `trip_imports`, `referral_rewards`, `trip_passes` (`source = 'import_reward'`) | Growth funnel and promotional cost | Our tables, with PostHog funnels |

All amounts are stored in minor units with an ISO currency and converted to USD with `fx_rates` at the event date for reports. Apple revenue is reported net of Apple's 15% commission (Small Business Program, under $1M in annual proceeds; above that, standard rates apply and the model is rerun).

### 12.2 Definitions

| Metric | Definition |
|---|---|
| Net price per plan | Gross minus 15%: Plus monthly $5.09, Plus annual $33.99, Trip Pass $8.49, credits 50 $2.54, credits 150 $5.94, credits 400 $12.74 |
| MRR | Sum over active subscriptions (status `active`, `in_grace`; `in_trial` excluded until paid) of the monthly equivalent of net price; annual plans divided by 12; passes and packs excluded |
| New, expansion, contraction, churned MRR | The month-over-month movements by subscription; upgrades are expansion, downgrades contraction, expirations churned |
| ARR | MRR times 12 (subscriptions only) |
| Passes and packs revenue | Net sales in the month, reported separately, since they are one-off |
| ARPPU | Total net revenue in the month (subscriptions, passes, packs) divided by paying users in the month (any purchase or active subscription) |
| ARPU | Total net revenue including affiliate divided by monthly active users |
| Paid conversion | Users with at least one purchase or active subscription, divided by monthly active users; also cohort conversion at 30 and 90 days after signup |
| Trial to paid | Plus annual trials that produced a paid renewal, divided by trials started |
| Churn | Monthly subscriber churn (subscriptions that ended in the month divided by active at the start); annual plans measured at renewal |
| Refund rate | Refunded transactions over transactions, by product |
| Paywall conversion | Purchases attributed to a paywall view (within 24 hours, same trigger) divided by views; by trigger, offering, variant, tier |
| Credit burn | Credits reserved and settled per period by action code and by pool; the share of monthly allowance used; expiry rate (credits expired divided by granted) |
| Credit margin | Credit revenue (pack net price per credit times credits spent, plus allowance value by tier) versus real `ai_usage` and `provider_calls` cost per credit; alert when a feature's real cost per credit exceeds $0.02 by more than 20% |
| AI cost share | `ai_usage` plus `provider_calls` cost divided by net revenue excluding affiliate; target 20% or less (plan: 17% to 22%) |
| Affiliate EPC | Approved commission in USD divided by outbound clicks, by program, surface and category (earnings per click); also paid EPC |
| Affiliate revenue per MAU per year | Annualized approved affiliate revenue divided by monthly active users; kill rule at month 9 below $0.20 per monthly user per year |
| Revenue per trip | All revenue attributed to a real trip (passes bought for it, affiliate conversions from its clicks) divided by the number of real trips in the period; also per trip by tier of owner |
| Gross margin | Net revenue minus variable cost (AI, provider calls, infrastructure allocation, payment fees) divided by net revenue |
| Free cost per MAU | (Free-tier AI plus provider cost) divided by Free MAU; guard value about $0.02 a month for AI |
| Import activation | New users who confirm an import within 7 days of sign-up, divided by new users; by method (`ics_file`, `ics_feed`, `pasted_text`, `maps_file`, `places_text`) and by entry (`origin`: TripIt, Tripsy, Wanderlog, Google Maps) |
| Import reward conversion | Import-reward passes granted; share whose owner buys a Trip Pass, Plus or a pack within 30 days after the pass ends; promotional cost per converted user |
| Referral funnel | Links shared, sign-ups attributed, rewards `pending`, `qualified`, `granted` and `rejected`; reject rate; referred users' 30-day retention and paid conversion versus organic |
| Promotional cost | (Referral credits granted plus import-reward pass credits granted) times $0.02, as a share of net revenue |
| Verify this plan | Checks started per 100 new users; items checked per run; verdict mix (green, amber, red); credits spent and real cost per checked item (alert above $0.02); share of Free users who check a plan; conversion to a pack, Trip Pass or Plus within 7 days of a check; imports of verified items per check |
| Evidence rechecks | Rechecks per 100 stale labels shown; share that come back `changed` or `not_shown`; credits spent |
| Trust pages | Views of `/how-we-earn` and `/billing`; taps on "Cancel subscription"; cancellations started within 7 days of the trial reminder |

Kill rule: at month 9 after launch, if under 1% of monthly users pay and affiliate income is under $0.20 per monthly user per year (annualized), stop investing. Both numbers are tracked monthly from launch.

### 12.3 Dashboards and cadence

- **Revenue overview.** MRR waterfall, ARR, passes and packs, affiliate (pending, approved, paid), total net revenue, gross margin. Daily refresh, month close on the 5th.
- **Paywall.** Views, dismissals, purchases and revenue by trigger, offering and experiment variant; funnel from view to `purchase_started` to `purchase_completed`; mute and cap hit rates.
- **Plans.** Active by tier, trials, churn and reasons, upgrade and downgrade flows, pass binding rate and time to bind, unapplied passes.
- **Credits.** Balances by pool, burn by action code, expiry, negative balances, packs sold, credit margin by action.
- **Affiliate.** Section 8.8.
- **Growth.** Imports started and completed, import-reward passes granted and their conversion, the referral funnel, reject rate, and promotional cost.
- **Cohorts.** Revenue per user by signup month, by acquisition source, by first paywall trigger.
- **Alerts** (to email and the on-call channel): MRR drop over 10% month on month, webhook failures, reconcile mismatches, refund rate above 5% for a product, cost per active Plus payer above $2, negative credit balances above 20 accounts, affiliate import failures.

Weekly Monday review uses the same tiles: installs, activation, import activation, trial starts, paywall views and conversion, MRR and churn, credit burn, affiliate EPC, AI cost share, and the referral funnel.

### 12.4 Events (first-party, sent to PostHog)

`paywall_viewed`, `paywall_dismissed`, `purchase_started`, `purchase_completed` (with `is_trial` for a trial start), `purchase_failed`, `restore_tapped`, `subscription_started`, `subscription_renewed`, `trial_converted`, `subscription_canceled`, `subscription_changed` (monthly and annual switches), `trip_pass_applied`, `trip_pass_moved`, `trip_pass_expired`, `ai_action_started` and `ai_action_completed` (credit reserve, settle and refund, with `outcome: refunded`), `credits_expired`, `purchase_completed` with a `credits_*` product (a pack), `partner_link_tapped` (an outbound click). Phase 1 adds `import_started`, `import_previewed`, `import_completed`, `import_failed`, `import_reward_granted`, `referral_link_shared`, `referral_signup_attributed`, `referral_reward_granted`, `calendar_feed_enabled`, `calendar_feed_rotated`, `calendar_feed_read`, `booked_fare_drop_sent`, `calendar_polling_enabled`, `calendar_changes_found`, `verify_started`, `verify_checked`, `verify_imported`, `evidence_rechecked`, `cancel_link_tapped`, `how_we_earn_viewed` and `billing_page_viewed`; the catalogue with their properties is in [10-quality-security-launch.md](10-quality-security-launch.md) section 4. No event carries names, emails, feed addresses, pasted text or other free text; session replay is off or masked.
