# 07: Monetization specification

Part of the [Hermi build specification](../README.md). Tier codes, prices, credit grants, credit action codes, ceilings and table names come from the README and are final; table, column, enum and limit-key names come from [03-database-schema.md](03-database-schema.md). Where this file needs a value the README does not give (for example a cap or a timer), it is marked "default" and lives in `feature_flags` so it can change without a release. Rates, cookie windows and program rules for affiliate partners are "reported, verify": read each on the network's own terms page after sign-up.

Written 2026-09-30.

## 1. Revenue lanes and principles

| Lane | Who pays | Channel | Section |
|---|---|---|---|
| Subscriptions (Plus, Family, Pro) | The user | App Store in-app purchase through RevenueCat | 2 to 7 |
| Trip passes (Trip Pass, Group Trip Pass) | The trip owner | App Store in-app purchase, non-renewing subscription | 2 to 7 |
| Credit packs | The user | App Store consumable | 5 |
| Affiliate commissions | The partner | Our redirect `/go/{click_id}` | 8 |
| Concierge commissions | The host travel agency | Advisor fulfillment | 9 |
| Group payments (Stripe collection, Phase 4) | No fee at launch | Stripe | 10 |
| Later lanes | Partners, advisors, buyers | Stripe on the web | 11 |

Principles that every rule below follows:

1. The server decides. The app displays entitlement and balance; every API route checks the server's rows, never a client claim.
2. One payer per capability. A trip's capabilities are the best of its owner's tier and any pass on that trip; invitees join free. Credits are charged to the person who starts the action (a Family member draws from the household pool).
3. No dark patterns. The free path is always visible; no fake urgency; price, renewal date and cancel path are stated on every paywall.
4. Never hold data hostage. Downgrade or lapse never hides, locks or deletes a trip; read and export always work.
5. Digital features are sold only through In-App Purchase on iOS. Real-world costs (trip payments, print books, concierge bookings, affiliate bookings) never use In-App Purchase and never unlock app features.
6. Never rank by commission, never sell user data, no banner ads, no lifetime plans.

## 2. Product catalogue

### 2.1 App Store products

Subscription group `hermi_membership` holds every auto-renewing product. Levels within the group, highest first: Pro (level 1), Family (level 2), Plus (level 3). One group means nobody holds two memberships at once. Apple Family Sharing is off on every product. Prices are US tier prices; use Apple's automatic regional pricing first, then tune India, Brazil, Mexico and Turkey by hand after launch.

| Product ID | Type | Price (US) | Duration | Group and level | Trial or intro offer | Entitlement granted | Launch |
|---|---|---|---|---|---|---|---|
| `hermi_plus_monthly` | Auto-renewing subscription | $5.99 | 1 month | `hermi_membership`, level 3 | none | `plus` | Launch |
| `hermi_plus_annual` | Auto-renewing subscription | $39.99 | 1 year | `hermi_membership`, level 3 | 7-day free trial (the only intro offer at launch) | `plus` | Launch (pre-selected) |
| `hermi_family_monthly` | Auto-renewing subscription | $8.99 | 1 month | `hermi_membership`, level 2 | none | `family` | Launch |
| `hermi_family_annual` | Auto-renewing subscription | $59.99 | 1 year | `hermi_membership`, level 2 | none | `family` | Launch |
| `hermi_pro_monthly` | Auto-renewing subscription | $11.99 | 1 month | `hermi_membership`, level 1 | none | `pro` | Built, hidden behind `tier_pro` |
| `hermi_pro_annual` | Auto-renewing subscription | $99.00 | 1 year | `hermi_membership`, level 1 | none | `pro` | Built, hidden behind `tier_pro` |
| `hermi_trip_pass` | Non-renewing subscription | $9.99 | 90 days | none | none | `trip_pass` (one trip) | Launch (lead offer) |
| `hermi_group_trip_pass` | Non-renewing subscription | $19.99 | 90 days | none | none | `group_trip_pass` (one trip) | Launch |
| `hermi_credits_50` | Consumable | $2.99 | n/a | none | none | 50 purchased credits | Launch |
| `hermi_credits_150` | Consumable | $6.99 | n/a | none | none | 150 purchased credits | Launch |
| `hermi_credits_400` | Consumable | $14.99 | n/a | none | none | 400 purchased credits | Launch |

Product IDs are the `store_products.product_id` values seeded in 03 section 11.2 (plan codes such as `plus` and `credits_50` are `plans.code`). Not App Store products: `advisor_seat` ($29 a seat a month, $24 a seat a month on annual billing; Stripe product IDs `advisor_seat_monthly` and `advisor_seat_annual`) is sold on the web through Stripe (section 11). Group payments are Stripe, never an App Store product.

Rules:

- Apple allows one introductory offer per group per user. Only `hermi_plus_annual` carries one at launch. Win-back and promotional offers wait until after launch (section 7.10).
- Every product needs localized display names and descriptions, a paywall review screenshot and the subscription terms text. Use Apple's standard EULA plus our Terms and Privacy links.
- Family, Family Sharing and household are different things: a Family subscription is one Apple ID paying; members are invited inside Hermi (section 7.8).
- Adding products later (for example a Pro promotional offer) never changes a product ID. New price points for experiments get new product IDs (section 6.7).

### 2.2 Tier limits (the capability table)

The entitlement service resolves to this table, which mirrors the `plans.limits` seed in 03 section 11.1. Values the README states are final; others are defaults. Group tools follow the README rule: polls and manual cost splitting are in every paid plan and both passes, the Group Trip Pass adds the room-block request and 12 travelers, and Stripe collection (Phase 4) is for `group_trip_pass` and `pro` only. Launch scope follows the README: `pro` stays behind the `tier_pro` flag until its launch gate; Stripe group payments, advisors, print and LiteAPI are Phase 4.

| Capability key (`plans.limits`) | `free` | `plus` | `family` | `pro` | `trip_pass` (on its trip) | `group_trip_pass` (on its trip) |
|---|---|---|---|---|---|---|
| `active_trips` | 2 | unlimited (fair use 25) | unlimited (fair use 25 each member) | unlimited (fair use 50) | `active_trips_bonus` 1: the passed trip does not count toward the owner's limit | same |
| `routes_per_trip` (cached-fare routes) | 1 | 5 | 5 | 8 | 3 | 3 |
| `live_routes` (checked daily, within 120 days of departure, `live_window_days`) | 0 | 3 | 5 | 6 | 2, at most 60 checks (`live_checks_max`) | 2, at most 60 checks |
| Credits: `monthly_credits` for tiers, `credits_granted` for passes | 12 a month | 60 a month | 150 a month, pooled | 240 a month | 40 once | 80 once |
| `collaborators` | 0 (joins others' trips free) | 6 (default) | 6 (default) | 12 (default) | 6 | 11 (up to 12 travelers) |
| `travelers_per_trip` | 2 | 8 | 8 | 12 | 8 | 12 |
| `price_alerts` (`live_alerts` false on Free) | 1 cached-fare | 3 | 3 | 6 | 2 | 2 |
| `polls`, `cost_splitting` (manual splitting, no money moves) | no on its own trips; joins trips that have them | yes | yes | yes | yes | yes |
| `group_payments` (collect money through Stripe; Phase 4, also needs the flag `group_payments`) | no | no | no | yes | no | yes |
| `room_block_request` | no | no | no | no | no | yes |
| `scheduled_routines` | no | no | no | yes (3 per trip) | no | no |
| `priority_queue` | no | no | no | yes | no | no |
| `credit_rollover_cap` | 0 | 0 | 0 | 240 | n/a | n/a |
| `hide_presentation_footer` (true removes the Made with Hermi footer and PDF watermark) | false (shown) | true | true | true | true | true |

Free taster: one lifetime deep agent run per user (`plans.limits.taster_agent_runs = 1` on `free`), held as a one-time `promo` row in `credit_grants` with `restricted_action = 'agent_run'` and `period_key = 'taster'`, so it is outside the monthly allowance and usable once ([06-ai-agents-spec.md](06-ai-agents-spec.md) section 5.9).

## 3. RevenueCat setup

RevenueCat (RC) sits between StoreKit 2 and our server. It validates receipts, handles restore and cross-device sync, and sends webhooks. Our server remains the source of truth: RC is a transaction feed, and `subscriptions`, `entitlements`, `trip_passes`, `store_transactions` and `credit_grants` are ours. A periodic reconcile job compares them with RC's REST API so a later move to direct StoreKit stays possible.

### 3.1 Project configuration

| Item | Setting |
|---|---|
| Project and app | One RC project "Hermi", one iOS app (bundle ID `world.hermi.ios`, default) with the App Store Connect in-app purchase key. Android is added in Phase 4 to the same project. |
| App user ID | Our `users.id` (UUIDv7), never email. Call `Purchases.logIn(userId)` on sign-in and `logOut()` on sign-out. Anonymous IDs are not used because purchases are disabled until sign-in. |
| Attributes | Set `$email` off (we do not send it), `tier` not sent. Only `app_user_id`. No ad or attribution integrations. |
| Products | The eleven products in 2.1, each imported from App Store Connect. |
| Entitlements | `plus` (attached to `hermi_plus_monthly`, `hermi_plus_annual`), `family` (`hermi_family_monthly`, `hermi_family_annual`), `pro` (`hermi_pro_monthly`, `hermi_pro_annual`). Trip passes and packs are not relied on as RC entitlements (see 3.3). |
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
| `group` | `group_pass` = `hermi_group_trip_pass` (lead), `trip_pass`, `$rc_annual` | `group_pass` and `collect_payments` triggers: room-block request, more than 8 travelers, collecting payments |
| `family` | `$rc_annual` = `hermi_family_annual` (highlighted), `$rc_monthly` = `hermi_family_monthly`, `$rc_annual` of Plus | Household signals (section 6.4) |
| `credits` | `hermi_credits_50`, `hermi_credits_150`, `hermi_credits_400` | Out of credits |
| `pro` | `$rc_annual` = `hermi_pro_annual`, `$rc_monthly` = `hermi_pro_monthly`, `credits` | Only when `tier_pro` is on |
| `exp_*` | Variants created for experiments (section 6.7) | Experiments |

The paywall shows at most three visible choices; credit packs appear only in the `credits` offering or as a secondary row on a credit-out paywall. Pro is not shown until it launches.

### 3.3 How purchases reach our server

1. The app calls `Purchases.purchase(package)`. On success it calls `POST /v1/purchases/sync` with no payload (the server asks RC for the subscriber) so the unlock is instant, before the webhook lands; for a pass the body carries the `trip_id` (04 section 5.19).
2. RC sends a webhook. The handler is in 3.4.
3. For a trip pass, the app asks "Which trip is this for?" before it starts the purchase (pre-selected when the purchase started from a trip) and sends the `trip_id` with `POST /v1/purchases/sync`. A pass bought with no trip stays unapplied until `POST /v1/me/passes/{pass_id}/bind` (7.7).
4. A nightly reconcile job lists RC subscribers who changed in the last 48 hours and compares them with our rows; differences raise an alert and are repaired from RC.

Non-renewing subscriptions are not a reliable RC entitlement (RC treats them like one-off purchases, verify in the dashboard). So `hermi_trip_pass` and `hermi_group_trip_pass` arrive as `NON_RENEWING_PURCHASE` transactions; the server writes a `store_transactions` row (`kind = 'pass'`) and, once the trip is known, a `trip_passes` row. The 90 days (`starts_at`, `expires_at`), the trip binding and expiry are ours.

### 3.4 Webhook handling

Endpoint contract: verify the secret header; insert the raw body into `webhook_events` (`provider = 'revenuecat'`, `event_id`; the primary key is `(provider, event_id)`) and return 200 immediately; a worker job processes each row exactly once, idempotent on that key, and sets `status` (`processed`, `failed` or `ignored`), `processed_at` or `error`. Failures retry with backoff for 24 hours, then alert.

| RC event | Server action |
|---|---|
| `INITIAL_PURCHASE` (subscription) | Upsert `subscriptions` (`product_id`, `plan_code`, status `active` or `in_trial`, `period_start`, `period_end`, `auto_renew`, `is_trial`), upsert `store_transactions` (unique on `store` and `store_transaction_id`), recompute `entitlements` for the user, write a `credit_grants` row for the period (section 5.3), fire analytics `purchase_completed` |
| `RENEWAL` | Extend the period, new `store_transactions` row, grant credits for the new period if the plan is monthly (annual plans are granted monthly by the scheduler, 5.3), recompute entitlements |
| `PRODUCT_CHANGE` | Update product and tier; apply the upgrade or downgrade rules in 7.3 and 7.4 |
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

`POST /v1/webhooks/revenuecat`, `POST /v1/purchases/sync`, `GET /v1/me/entitlements` (tier, status, period end, auto_renew, pass list, credit balance by pool, capability values), `POST /v1/purchases/restore`, `GET /v1/me/passes`, `GET /v1/trips/{trip_id}/pass`, `POST /v1/me/passes/{pass_id}/bind`, `POST /v1/me/passes/{pass_id}/move`, `GET /v1/me/credits`, `GET /v1/me/credits/ledger`, `GET /v1/credits/packs`, `POST /v1/credits/packs/claim`, `GET /v1/paywall/offer`, `POST /v1/paywall/events`. A visible "Restore purchases" button is on every paywall and in Settings (App Review checks it); it calls `Purchases.restorePurchases()` then `POST /v1/purchases/restore`.

## 4. Entitlement resolution

### 4.1 Data

- `subscriptions`: one row per store subscription: `user_id` (or `household_id` for Family), `store` (`apple`, `stripe`, `google`), `product_id`, `plan_code` (`plus`, `family`, `pro`), `status` (`active`, `in_trial`, `in_grace`, `billing_retry`, `paused`, `expired`, `refunded`, `revoked`), `period_start`, `period_end`, `auto_renew`, `is_trial`, `original_transaction_id`.
- `entitlements`: a materialized, per-user result of the algorithm below: `user_id`, `tier_code` (the user's own best, including household), `source` (`none`, `subscription`, `household`, `comp`, `advisor`), `subscription_id`, `household_id`, `in_grace`, `valid_until`, `limits` (snapshot of `plans.limits`), `computed_at`. It is a cache that can always be recomputed; it is rewritten on every relevant event and by a nightly sweep.
- `trip_passes`: `id`, `trip_id`, `purchaser_user_id`, `plan_code` (`trip_pass`, `group_trip_pass`), `store_transaction_id`, `original_transaction_id`, `starts_at`, `expires_at`, `live_routes_max`, `live_checks_max`, `live_checks_used`, `collaborators_max`, `travelers_max`, `credits_granted`, `status` (`active`, `expired`, `refunded`, `upgraded`), `move_count`, `upgraded_from_id`. A row exists only once the pass has a trip; a paid pass with no trip yet is a `store_transactions` row (`kind = 'pass'`, `trip_id` null) and is shown to the client as "unapplied". At most one pass is active per trip.
- `households`, `household_members` ([03-database-schema.md](03-database-schema.md)): the owner is the Family subscriber; up to 6 members including the owner.
- Advisor seats (`advisor_seats`) grant `pro`-level capabilities to an advisor user on client trips only (section 11.4). A user whose only paid source is a seat has `entitlements.source = 'advisor'` and `tier_code = 'advisor_seat'`; on their own non-client trips they resolve as Free. 03 section 7.1 adds the seat as a third candidate (`advisor`) on a trip that has an `advisor_clients` row.

Tier rank: `free` 0, `plus` 1, `family` 2, `pro` 3. A trip pass is an overlay on one trip, not a tier.

### 4.2 Algorithm

```python
RANK = {"free": 0, "plus": 1, "family": 2, "pro": 3}

def user_tier(user) -> Tier:
    """The user's own best tier, from their subscription or their household."""
    best = Tier("free", source="none", until=None)
    sub = active_subscription(user.id)           # status in in_trial, active, in_grace; period_end >= now
    if sub:
        best = Tier(sub.plan_code, source="subscription", until=sub.period_end)
    m = household_membership(user.id)            # at most one household per user
    if m and household_owner_has_active_family(m.household_id):
        fam = Tier("family", source="household", until=owner_sub_period_end(m.household_id))
        best = max_rank(best, fam)
    if flags.get("tier_pro") is False and best.code == "pro":   # feature_flags.tier_pro off: Pro is hidden
        best = Tier("family" if has_family(user) else "plus", ...)   # Pro hidden: never resolves before launch
    return best

def trip_capabilities(trip) -> Capabilities:
    """What the trip itself can do: best of its owner's tier and any active pass on it."""
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

1. **Best-of on a trip.** Capabilities on a trip are the per-capability best of the owner's tier, the active pass on the trip (03 allows one active pass per trip, `uq_trip_passes_one_active`; `merge_best` stays generic) and, on a client trip, the owner's advisor seat. Live check budgets are the maximum, not the sum, because they are a cost cap. This is the same merge as 03 section 7.1.
2. **Invitees.** Collaborators and viewers get the trip's capabilities on that trip only. They do not gain tier benefits elsewhere. They do not pay and cannot buy passes for a trip they do not own (they can buy their own membership).
3. **Personal limits follow the person.** Active trips (the count a user may own), personal alerts and personal credits depend on `user_tier(actor)`, not on the trip.
4. **Owner lapse.** If the owner's tier drops, the trip keeps its data; capabilities recompute. Existing live routes beyond the new limit are paused (not deleted), oldest first kept; collaborators above the limit stay as viewers; AI on the trip continues to draw from whoever acts.
5. **Free is never a lock-out.** If any limit would block reading or exporting, it does not apply to read and export. Trips above the active-trip limit after a downgrade become read-only "archived" until the owner archives or upgrades; a Free user with three trips after a lapse keeps reading and exporting all three and may edit the two most recently edited ones.
6. **Grace.** Status `in_grace` counts as active for resolution (`entitlements.in_grace` is set). `billing_retry` after grace does not.
7. **Caching.** `entitlements` is recomputed on: webhook events, household changes, trip pass binding or expiry, the `tier_pro` flag, and a nightly sweep. API routes read `user_tier` through a 30-second in-process cache keyed by user id; `POST /v1/purchases/sync` bypasses it.

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
| `household_monthly` (Family) | Subscription period or monthly tick | 150 | household (pooled, `household_id`) | End of that month's period | 1 |
| `monthly` (Pro) | Subscription period or monthly tick | 240 (plus carried credits, 5.5) | user | End of that month's period | 1 |
| `promo` | Free taster, promotions | Taster: the `agent_run` price (40), `restricted_action = 'agent_run'` | user | None for the taster | 2 |
| `trip_pass` | Pass start | 40 (Trip Pass) or 80 (Group Trip Pass), from `plans.credits_granted` | trip (`trip_id`; spendable by any member acting on that trip) | Pass expiry (90 days) | 3 |
| `adjustment` | Support, concierge perk, rollover | any | user | Set by admin (default 12 months) | 4 |
| `purchase` | Pack purchase | 50, 150 or 400 | user | 12 months after purchase | 5 (oldest expiry first) |

`credit_grants` columns used: `id`, `user_id` or `household_id` (never both), `trip_id` (required for `trip_pass` grants), `kind`, `credits`, `remaining`, `restricted_action`, `period_key`, `expires_at`, `store_transaction_id`, `created_at`. Idempotency comes from the unique indexes on (`user_id`, `kind`, `period_key`), (`household_id`, `kind`, `period_key`) and `store_transaction_id`. The spend order is the `ORDER BY` inside `reserve_credits` (03 section 5.13).

### 5.2 Purchase grants

- A pack purchase arrives as `NON_RENEWING_PURCHASE` or a consumable transaction. The handler writes a `credit_grants` row (kind `purchase`, `credits` from `plans.credits_granted` of the product's `plan_code`, `store_transaction_id`, `expires_at` = purchase time plus `credits_valid_days`, 365) and a `credit_ledger` row (`entry_type = 'grant'`, positive `delta`, `idempotency_key` `store:{transaction_id}`); the unique index on `credit_grants.store_transaction_id` means a replayed webhook never grants twice.
- The pack screen states: "Purchased credits last 12 months and are spent after your monthly credits."
- Purchased credits also raise the account's spend ceiling by their cost value ([06-ai-agents-spec.md](06-ai-agents-spec.md) section 6.5).

### 5.3 Grants on renewal

| Plan | When credits are granted | `period_key` |
|---|---|---|
| Monthly (`hermi_plus_monthly`, `hermi_family_monthly`, `hermi_pro_monthly`) | On `INITIAL_PURCHASE` and each `RENEWAL` (a paid period) | `YYYYMMDD` of the period start |
| Annual (`hermi_plus_annual`, `hermi_family_annual`, `hermi_pro_annual`) | On purchase, and then on each monthly anniversary by the scheduler while the entitlement is active, until the annual period ends | `YYYYMMDD` of the anniversary |
| Trial (`hermi_plus_annual` trial) | Plus allowance (60) is granted at trial start but the ceiling for the trial is the normal Plus ceiling; trial exposure is about $0.45 in live checks and credits for a typical trial | `YYYYMMDD` of the trial start |
| Grace or billing retry | No new grant during `billing_retry`; during `in_grace` the current period's pool remains spendable; if payment recovers, the grant for the new period is written with the recovered period start | |
| Free | Lazily written on first credit use each month; idle accounts cost nothing | `YYYY-MM` |

The scheduler job `grant_monthly` runs daily at 02:00 UTC, finds active annual subscriptions whose monthly anniversary is today and whose last grant is older than 28 days, and writes the grant. It never grants during `billing_retry`, `expired` or `refunded`.

### 5.4 Spend order

When an action reserves N credits, the ledger draws from pools in this order, oldest expiry first within a priority:

1. Monthly allowance pools the actor can use: their own `monthly` grant, or the `household_monthly` pool for a Family member.
2. `promo` grants (the taster, only for the `agent_run` action it is restricted to).
3. `trip_pass` grants of the trip they are acting on.
4. `adjustment` grants.
5. `purchase` grants, oldest expiry first (purchased credits are spent last).

A reservation that spans pools records each draw (`credit_ledger` rows with `grant_id`), so a refund returns credits to the same pools. If a pool expired before the refund, the refund is skipped for that part and the ledger says so; in practice runs last minutes, so this is rare. Credits are charged to the person who starts the action, so a collaborator on a Trip Pass trip first uses their own allowance, then the trip's pass pool. The order lives in `reserve_credits`, which raises SQLSTATE `WF402` when the pools cannot cover the price.

### 5.5 Expiry and rollover

- Allowances do not roll over on Free, Plus or Family. Pro rolls over one month: before the new grant, unspent `monthly` credits of the Pro allowance convert to an `adjustment` grant (note `rollover`) capped at `plans.limits.credit_rollover_cap` (240; a product decision carried from the pricing plan, not in the README). Rolled credits expire at the end of the new period.
- Expiry is processed by `expire_credit_grants()`, run hourly: for each grant past `expires_at` with `remaining > 0`, it writes a `credit_ledger` row with `entry_type = 'expire'` and the negative `delta` and sets `remaining = 0`. Reserved credits are already out of `remaining`, so running actions are untouched; a second run finds nothing to expire.
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

### 5.7 Ledger entries and balance

`credit_ledger.entry_type` values: `grant`, `reserve`, `settle`, `refund`, `expire`, `clawback`, `adjust`. Each row: `user_id` (payer), `grant_id`, `entry_type`, `delta`, `charged` (settle rows), `reservation_id`, `action` (credit action code), `run_id`, `trip_id`, `usage_id`, `idempotency_key`, `note`, `created_at`. Rules:

- Append only; corrections are new rows.
- `reserve_credits` writes one negative `reserve` row per grant it draws from, all sharing a `reservation_id`. `settle_credits` writes positive `refund` rows for the uncharged part (back to the same grants) and one zero-delta `settle` row whose `charged` is final; charging 0 releases the whole reservation. A replay with the same `idempotency_key` returns the original reservation.
- Both run in the API or worker transaction: the candidate grants are locked with `SELECT ... FOR UPDATE` inside `reserve_credits`, so two parallel actions can never overspend. `release_stale_reservations()` settles abandoned reservations at 0.
- `GET /v1/me/credits` returns the balance per pool with expiry dates from the `credit_balances` view; the in-app usage meter shows "Monthly credits", "Trip Pass credits", "Purchased credits" separately.
- A daily reconciliation asserts that, per grant, `credits` plus the sum of its non-`grant` `delta` values equals `remaining`; any mismatch alerts.

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
| `invite` | Invite a collaborator | Free owner | `trip_first` ("Plan together: they join free") | Share a read-only link |
| `out_of_credits_draft` | "Draft my itinerary" | Out of credits | `credits` or `plus_first`; blurred preview of day one | Plan manually |
| `out_of_credits_research` | "Research this" or "Ask" | Out of credits | `credits` (small pack first) | Skip |
| `out_of_credits_agent` | Deep agent run or fare hunt | Fewer than 40 credits | `credits` (400 pack highlighted when short by more than 50) or `plus_first` | Use a research question |
| `routine` | Start a scheduled routine | Not Pro | Sample result from cache; one manual run for credits; Pro once launched | Run once manually |
| `group_tools` | Open polls or cost splitting on a trip that lacks them (Free owner) | Trip lacks `polls` or `cost_splitting` | `trip_first` (`plus_first` when the person has two or more active trips) | View what others add; join trips that have them |
| `group_pass` | Open the room-block request, or add a ninth traveler | No Group Trip Pass on the trip | `group` | Keep to 8 travelers, skip the room block |
| `collect_payments` | Tap "Collect payments" (Phase 4, flag `group_payments`) | No Group Trip Pass or Pro | `group` | Mark as paid by hand |
| `export_footer` | Export or share with the Made with footer | Free export | Soft line at export, never a modal | Export with footer |
| `ninth_stay` | Save the 9th lodging option | Free limit | `trip_first`; keep saving to a "later" list | Later list |
| `lifecycle_14d` | 14 days before departure | Free trip with dates | `trip_first` via email or in-app card, not a modal | Dismiss |
| `household` | Invite a second household member | Household signals (6.4) | `family` | Invite as collaborator |

No trigger exists for the first session, for presentation playback, or for actions after an affiliate booking. Hard limits (third trip) are a block with the free alternative, not a nag. The API `reason` for each trigger ([04-api-spec.md](04-api-spec.md) section 2.2): `third_trip` is `trip_limit`; `second_route`, `track_live` and `alert_limit` are `live_routes`; `invite` is `sharing`; the three `out_of_credits_*` triggers are `credits` (the taster is `agent_taster_used`); `routine` is `routines`; `group_tools` is `group_tools`; `group_pass` is `traveler_limit` (above 8 travelers) or `room_block`; `collect_payments` is `group_payments`; `household` is `family_members`. `export_footer`, `ninth_stay` and `lifecycle_14d` are client-initiated and are sent as `reason` by their trigger code.

### 6.3 Which offer to show

```python
def choose_offering(ctx, trigger):
    if not ctx.pro_enabled and trigger == "routine":
        return "credits"                                   # manual run via credits, no Pro
    if trigger in CREDIT_TRIGGERS:                         # draft, research, agent out of credits
        return "credits" if ctx.tier != "free" or ctx.recent_pack_buyer else "plus_first"
    if trigger == "group_tools" or ctx.trip.travelers > 8:
        return "group"
    if ctx.household_signal:
        return "family"
    if ctx.trip and ctx.trip.dates_within(120):            # "I have a trip in March"
        return "trip_first"
    if ctx.active_trips >= 2:
        return "plus_first"
    return "default"
```

Defaults from the plan: best-converting first is Trip Pass, then annual Plus, then monthly Plus; Trip Pass leads when the trip has dates within 120 days, annual Plus leads when the user has two or more active trips. Plus annual is pre-selected in `default` and `plus_first`; the trial line states the price after the trial and the renewal date.

### 6.4 Household signal

`household_signal` is true when any of: the user has invited, or been asked to invite, two or more people to a household; the user's trips have 3 or more travelers that are also trip members on at least two different trips; or the user tapped "Family" in the plan comparison. It never uses names, ages or inferred relationships.

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

- Show price and billing period most prominently, then trial length and the price after the trial, auto-renew terms, links to Terms of Use and Privacy Policy, and Restore (Guideline 3.1.2).
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
| 7 | Family visibility | Family as a row in `default` vs household trigger only | Family share | Plus downgrades |

Rules: one experiment per trigger at a time; pre-register the metric and minimum run length (at least 4 weeks and 1,000 views per arm, default); stop an arm that lowers satisfaction (support tickets, ratings prompts). Results are read in the admin console ([08-admin-control-center.md](08-admin-control-center.md)).

## 7. Lifecycle rules

### 7.1 Trials

- Only `hermi_plus_annual` has a 7-day free trial, one per Apple ID per group. The paywall shows "7 days free, then $39.99 a year" with the renewal date, and a reminder two days before it converts.
- During the trial: status `in_trial`, full Plus capabilities and the normal Plus allowance, the normal Plus ceiling. Exposure for a typical trial is about $0.45.
- Trial to paid: `RENEWAL` event with a paid period; status `active`. Trial cancelled: access until the trial ends, then `EXPIRATION`.
- No trial for monthly plans, Family, Pro, passes or packs. Reinstalls and new devices cannot restart a trial (Apple enforces one per Apple ID per group).

### 7.2 Purchases outside the lifecycle

- Buying a trip pass while on a membership is allowed and useful (the pass lives on one trip and is best-of with the owner's tier).
- Buying a membership while a trip pass is active is allowed; both coexist.

### 7.3 Upgrades

Plus to Family or Pro, Family to Pro, monthly to annual of a higher tier: Apple applies the change immediately and refunds the unused time of the old plan pro rata (same group, higher level). Our handling on `PRODUCT_CHANGE`:

1. Switch the tier now; recompute entitlements and household capabilities.
2. Grant the new tier's allowance for the current period now, minus any allowance already granted and unspent in this period: the old allowance pool stays valid for spending (never reduce a pool the user already has), and the new grant is the difference up to the new amount (Plus 60 to Family 150: grant 90). The grant's `period_key` includes the product change date.
3. Family gains the household pool: existing household members gain benefits immediately.
4. Analytics `subscription_changed` with `direction: upgrade` and the from and to products.

### 7.4 Downgrades

Family to Plus or Plus to a cheaper cycle, or any lower level: Apple applies it at the next renewal. Until then the user keeps the current tier. At renewal:

1. The new product and tier apply; the old allowance expires with the old period; the new allowance is granted.
2. Family to Plus: the household dissolves at the boundary. Members lose household benefits and the pooled credits; each member keeps their own purchased credits and their own trips. Members with no plan fall to Free. The owner gets 14 days before the boundary an in-app notice listing who will lose benefits (7.8).
3. Limits above the new tier are handled by the owner-lapse rules in 4.2 (pause, never delete).

### 7.5 Cancellation, grace, billing retry

- **Cancellation.** The user cancels in iOS Settings (we link to Manage Subscriptions from Settings and never hide it). Status stays `active` with `auto_renew = false` until the period ends, then `EXPIRATION`. The app shows "Your plan ends on {date}" and a one-tap resubscribe. Account deletion does not cancel an Apple subscription; the deletion screen says so and links to Manage Subscriptions.
- **Billing grace period.** Turn on Apple's billing grace period for all subscription products, 16 days (default). During grace the entitlement stays active and the credits of the current period stay spendable, but no new allowance is granted. The app shows a banner "We could not renew your plan. Update your payment method" with a deep link to the App Store subscription page; email on day 0, 7 and 14.
- **Billing retry.** After grace, Apple keeps retrying for up to 60 days in total. Status `billing_retry`: entitlement is off (the user drops to their remaining sources), the banner stays, purchased credits remain. If payment succeeds, a `RENEWAL` arrives, status returns to `active`, and the allowance for the new period is granted. If it never succeeds, `EXPIRATION`.
- **Pause.** Not used; Apple subscription pause is not offered. The pricing plan's "3-month pause" idea is handled by a win-back (7.10), not by the store.
- **Re-subscribe after expiry.** A new period, a new grant, no trial.

### 7.6 Refunds

Refunds happen through Apple (reportaproblem.apple.com); we cannot issue them. On a refund notice from RC:

| Product | Action |
|---|---|
| Subscription | Status `refunded`, revoke now, claw back the unspent allowance of that period (5.6), count refunds per user from `store_transactions` (`status = 'refunded'`) |
| Trip pass or Group Trip Pass | Status `refunded`; the pass stops granting capabilities; its unspent credits are removed; live checks stop. The trip and its data stay. |
| Credit pack | Clawback (5.6); negative balance blocks paid AI until positive |
| Pattern | 3 refunds in 90 days: block pack purchases for that user for 180 days (`users.pack_purchases_blocked_until`) and flag for review (default) |

Support can grant goodwill credits (an `adjustment` grant) but never reverse a refund into a free pass.

### 7.7 Trip pass binding and expiry

1. On purchase the store transaction is written (`store_transactions`, `kind = 'pass'`). If the purchase started from a trip, the app sent its `trip_id` and the `trip_passes` row is written at once. Otherwise the app asks "Which trip is this for?" and lists the owner's trips; until then the pass is unapplied (a `store_transactions` row with `trip_id` null and no `trip_passes` row) and waits in Settings, Purchases, for 12 months (default), then lapses.
2. Binding (`trip_id` on `POST /v1/purchases/sync`, or `POST /v1/me/passes/{pass_id}/bind`) inserts `trip_passes` with `starts_at = now()` and `expires_at = starts_at + 90 days`, sets `store_transactions.trip_id`, copies `live_routes_max`, `live_checks_max`, `collaborators_max`, `travelers_max` and `credits_granted` from `plans.limits` of the purchased plan, writes the `trip_pass` credit grant (40 or 80, with `trip_id`) and recomputes the trip's capabilities. Only the trip owner may bind, and the purchaser must be the owner. A trip holds one active pass (`uq_trip_passes_one_active`); binding a second of the same plan is refused with `409 state_conflict`. Binding a Group Trip Pass to a trip that has an active Trip Pass is the upgrade in 7.9.
3. A pass can be moved once (`move_count` 0 to 1, `POST /v1/me/passes/{pass_id}/move`) to another trip that the same owner owns; moving keeps the original `expires_at`, changes `trip_id` on the pass and on its unspent `trip_pass` grant, and pauses live routes on the old trip. A second move is refused.
4. Live check counters (`live_checks_used` against `live_checks_max`) belong to the pass and move with it.
5. Expiry at `expires_at`: `status` becomes `expired`, capabilities drop to the owner's tier, unspent pass credits expire, the trip stays. The app shows the pass status and expiry date in the trip's settings, a notice 7 days before, and offers renewal by buying a new pass (a new pass starts a new 90 days).
6. A pass is tied to the purchaser's Apple ID through the transaction; it is restorable, because it is a non-renewing subscription and not a consumable.
7. If the bound trip is deleted by the owner, the trip sits in trash for 30 days and keeps its pass; restoring the trip restores the pass. When the trip is purged, the `trip_passes` row goes with it (`trip_id` cascades), the pass is not refunded and the `store_transactions` row stays as the record.

### 7.8 Family membership changes

- Household owner: the Family subscriber. Up to 6 members including the owner. Members are invited in the app (link or email), must accept, and must have a Hermi account. Apple Family Sharing is not used.
- One household per user. A user with their own Plus or Pro subscription who joins a household keeps the higher tier from `user_tier` (best of) and their own allowance; they also draw from the household pool as a member.
- Household credits are one pool (a `household_monthly` grant, 150 a month). Spend is charged to the person acting and drawn from the pool first; there is no per-member quota. A member can exhaust the pool (the owner sees per-member usage in Settings).
- Adding a member: immediate; no extra charge.
- Removing a member (by the owner) or a member leaving: benefits end immediately; the member's own purchased credits and own trips stay with them; trips they owned keep their data and revert to their personal tier capabilities; pooled credits already spent stay spent. A removed member may be re-invited.
- Churn guard (default): a person can join or leave a household at most twice in 12 months, and a household may have at most 2 replacements of members per quarter; counted from `household_members` (`joined_at`, `removed_at`).
- Owner cancels or lapses: the household dissolves at `period_end` with the notices in 7.4.
- Ownership transfer: not supported at launch (the owner must resubscribe under the new owner).

### 7.9 Group Trip Pass rules

- Bound to one trip, 90 days from binding, purchased by the trip owner only ($19.99).
- Raises the trip to up to 12 travelers (owner plus up to 11 collaborators), 80 credits (the `trip_pass` grant), and the room-block request form (`room_block_requests`, a lead form that goes to the concierge advisor; no payment). Polls and manual cost splitting are not exclusive to it: every paid plan and both passes include them (section 2.2). With `pro` it is the only way to collect money through Stripe (Phase 4, section 10).
- Capabilities for live routes are 2 routes and at most 60 checks, like Trip Pass.
- One pass per trip at a time (`uq_trip_passes_one_active`); it is best-of with the owner's tier. **Upgrade from Trip Pass.** The owner buys a Group Trip Pass and binds it to the same trip. The Trip Pass row becomes `upgraded` (which frees the unique index), the new row records `upgraded_from_id`, runs a full 90 days from binding, and copies `live_checks_used` so the 60-check cap is not reset. Unspent Trip Pass credits stay spendable until their own expiry, and the Group Trip Pass grants its 80 credits. Nothing is refunded by us; Apple refund rules (7.6) apply to each purchase.
- Guests in the group need no subscription; they join free and see polls and splits. Those who want to start AI actions draw from their own allowance, then the trip's pass pool.
- Expiry: if the owner's tier does not also grant them, polls and splits become read-only; past polls and recorded expenses remain readable and exportable; open Stripe collections (Phase 4) continue to completion on Stripe (they are not an app feature, section 10). The owner sees a notice 7 days before expiry.
- Not refundable by us; Apple refund rules (7.6) apply.

### 7.10 Win-back and retention (after launch)

When `auto_renew` turns false, the next two checkpoints are a cancellation survey (one question, skippable) and a win-back offer 7 days after expiry: an Apple promotional or win-back offer on the same product (for example 3 months at a discount, verify product configuration). Win-back offers are configured in App Store Connect after the first month of data and delivered through RC; never used as a dark pattern (shown once, clearly priced). A lifecycle email "Planning another trip?" goes out to lapsed users with a trip in the next 120 days.

## 8. Affiliate system

Affiliate income is the Free tier's revenue. It is earned on every tier in the same places. Every partner link goes through our redirect. Program details and rates are "reported, verify".

### 8.1 Program catalogue

`affiliate_programs` holds one row per program: `code`, `name`, `network`, `category`, `status` (`planned`, `applied`, `active`, `paused`, `closed`), `hosts`, `commission_model`, `commission_note`, `cookie_days`, `subid_param`, `subid_max_len`, `campaign_param`, `terms_url`, `countries_allowed`, `countries_blocked`, `feature_flag_key`. Seed data for launch (Travelpayouts, Viator partner API, Stay22) and month-3 applications; the first column is the `code` seeded in 03 section 11.4:

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
| `expedia_group` (Vrbo, Expedia, Hotels.com) | Impact | lodging | planned, applied at month 3 | The only route to Vrbo |
| `booking_direct` | confirm current network first | lodging | planned, applied at month 3 | |
| `skyscanner` | Impact | flights | planned, applied at month 3 | The licensed fare data matters more than the cash |
| `airalo` | Impact | esim | planned, applied at month 3 | Link out only; never sold in the app |
| `getyourguide_direct` | own program | tours | planned, applied at month 3 | |
| `airhelp` | direct | compensation | month 3 plus | |
| `trainline`, `worldnomads`, `heymondo`, `klook` | various | various | month 3 plus | Add only when data shows demand |

Not integrated: Airbnb (no program an app can join: listings get a plain link that is never converted), credit cards, VPNs, Amazon product data, the Expedia Rapid API, and new integrations on Partnerize (merging into CJ).

Rules:

- One partner per surface per test cell; never two networks on one button.
- Each program has a kill switch named `affiliate.{code}` in `kill_switches` (`feature_flag_key` stays null unless a partner needs a staged rollout) and there is a global `affiliate.all`. An off switch hides that partner's buttons on the next fetch and makes `/go` return the non-affiliate fallback (the plain destination or a neutral search link).
- Pasted listing links stay exactly as pasted. A separate labeled "Book via partner" button offers a partner link built from the URL text (host, path, the trip's dates), never by fetching the page, and only for hosts with an approved program. It never appears for Airbnb. The server never fetches Airbnb, Vrbo or Booking.com pages, not even for link previews (previews for partner hosts are disabled by default).
- No list, badge, default sort or AI answer depends on commission. When two partners offer the same item, the choice is by A/B cell or the user's own criteria, never by payout.

### 8.2 Link templates

`affiliate_link_templates` holds one row per program, kind and surface cell: `program_id`, `kind` (`search`, `deeplink`, `widget`, `map`), `surface` (null for any), `variant` (the A/B cell), `weight`, `template` (a URL with placeholders), `required_placeholders`, `active`. Geography comes from the program's `countries_allowed` and `countries_blocked`. Templates are stored, never taken from a request. Placeholders: `{sub_id}` (our click id, or `{short_id}` where the network limits length), `{marker}`, `{campaign}` (the surface label), `{dest_enc}` (URL-encoded target), `{dest}`, `{origin}`, `{destination}`, `{depart}`, `{return}`, `{adults}`, `{checkin}`, `{checkout}`, `{guests}`, `{lat}`, `{lon}`. Partner ids such as `pid` or `mcid` are written literally into the template text. Verify each template against the network's terms page after sign-up; these are the intended shapes.

| Program | Template shape (intended) | Sub-id field |
|---|---|---|
| Travelpayouts (partner links) | `https://tp.media/r?marker={marker}.{short_id}&p={program_p}&u={dest_enc}&campaign_id={campaign}` | Appended to `marker` |
| Aviasales data API booking link | `https://www.aviasales.com/search/{route_code}?marker={marker}.{short_id}` | Appended to `marker` |
| Viator | `https://www.viator.com/tours/{path}?pid={pid}&mcid={mcid}&medium=api&campaign={short_id}` | `campaign` |
| Stay22 | `https://www.stay22.com/allez/{brand}?aid={aid}&campaign={short_id}&address={dest}&checkin={checkin}&checkout={checkout}&adults={adults}` | `campaign`; surface in a second field where supported (`campaign_param`) |
| Impact (Expedia Group, Skyscanner, Airalo) | `https://{tracker}.sjv.io/c/{account}/{ad}/{program_id}?subId1={sub_id}&subId2={campaign}&u={dest_enc}` | `subId1`, surface in `subId2` |
| Booking.com (once a direct program exists) | Per Partner Center deep links | `label` |

### 8.3 Creating a click: `/v1/outbound` and `/go/{click_id}`

1. The app calls `POST /v1/outbound` with `{entity_type, entity_id, surface, trip_id, checklist_item_kind?}` (authenticated; see [04-api-spec.md](04-api-spec.md)). The server checks trip access, checks that the program's kill switch is on, chooses the program (feature flags, geography, A/B cell; never commission), builds the target URL from the stored template and inserts a `link_clicks` row, then returns `https://go.hermi.world/go/{click_id}`. Rate limit: 60 an hour per user (04 section 1.8), with repeat clicks on the same entity within 30 seconds returning the same `click_id`.
2. `click_id` is a random 128-bit value encoded in base62 (about 22 characters), generated only by this authenticated call. Where a network limits sub-id length, `link_clicks.short_id` (8 to 12 characters) is sent instead; the click id itself never leaves our system except in our own URL.
3. The app opens the URL in `SFSafariViewController` (Capacitor Browser plugin). The web app opens a new tab with `rel="noopener noreferrer"`.
4. `GET /go/{click_id}` looks the row up; checks it is under 10 minutes old and has not been used; sets `clicked_at`; returns HTTP 302 to the partner URL built from the stored template, with the sub-id. Headers: `Cache-Control: no-store`, `Referrer-Policy: no-referrer`. The response has no body and renders no page, so there is no third-party script, pixel or cookie from us. A known but expired or used id returns a 302 to the plain destination (the non-affiliate route) so the user is never stranded; an id that never existed returns 404 with an empty body.
5. No open redirects: the target is only ever a stored template filled with validated fields. There is no `url=` parameter on `/go`.

`link_clicks` columns used: `id`, `click_id` (the random sub-id), `short_id`, `user_id`, `trip_id`, `program_id`, `template_id`, `entity_type`, `entity_id`, `checklist_item_kind`, `surface`, `variant` (A/B cell), `destination_url`, `opened_in` (`sfsvc`, `safari`, `web` or `android_tab`), `created_at`, `clicked_at`, `redirect_status`, `country`, `platform`, `app_version`, `ip_hash` (salted, rotated monthly). The category comes from the program (`affiliate_programs.category`). No advertising ID, no IDFA or IDFV, no device fingerprint.

### 8.4 Sub-ids, privacy and App Tracking Transparency

- The sub-id is a random per-click token. User id, trip id and email never appear in a URL; the join from a conversion to a click to a user and trip happens only in our database.
- No ad, attribution or third-party analytics SDK; no hashed email or phone to any partner. Conversions are pulled by our server from each network's API and joined to `link_clicks` in our database. This keeps the app outside App Tracking Transparency (no ATT prompt); note it in the review notes and verify with Apple.
- Privacy label: Usage Data (product interaction: outbound clicks), linked to identity, for analytics and app functionality, not used for tracking.
- Click rows are retained 25 months; aggregates 7 years (suggested; counsel to confirm). The privacy policy lists the purpose "affiliate revenue attribution and fraud detection".

### 8.5 Disclosure

- Sentence used everywhere, next to every partner button, in AI output cards, on shared trip pages, in presentation mode and in the PDF: **"We earn a commission if you book here."** Text, never color alone; VoiceOver reads it in the same element as the button.
- "Ad" tag on UK and EU storefronts (by App Store storefront country or account country; the stricter rule applies when unknown).
- Booking.com adds its own required line where its tracking link appears.
- Every list says how it is sorted (price, rating, distance, hearts) and that commission plays no part. Prices from partners show the date checked and provider. "How we earn money" page linked from Settings, every paywall and empty states; a "Hide booking links" switch collapses buttons to a plain "Open on partner site" link.
- No insurance card until the trip has a chosen flight or booking; no eSIM card for domestic trips; AI never gives insurance advice; visas link to official sites first.
- No affiliate push that exists only to drive clicks (Guideline 4.10). User-requested price alerts are fine, and they link into the app route, not to a partner.
- Affiliate purchases never unlock app features, and nothing is worded as if they do (Guideline 3.1.1).

### 8.6 Nightly conversion import

A worker job per network runs nightly (02:30 UTC, jittered per network) and on demand from the admin console. Each writes `affiliate_conversions`: `program_id`, `network`, `network_txn_id`, `sub_id_returned`, `click_id` (nullable when unmatched), `match_status` (`matched`, `unmatched`), `status` (`pending`, `approved`, `rejected`, `paid`), `network_status_raw`, `booking_value_minor` with `booking_currency`, `commission_minor` with `commission_currency`, `booked_at`, `click_lag_hours`, `approved_at`, `paid_at`, `reversal_at`, `status_history`, `raw` (jsonb). USD figures are computed at read time with `fx_rates` at the event date, not stored. Unique on `(program_id, network_txn_id)`; every import is an idempotent upsert that updates status and amounts and appends to `status_history`. A network reversal or cancellation is stored as `rejected` with `reversal_at` set.

| Network | Source | Sub-id where it comes back |
|---|---|---|
| Travelpayouts | Booking statistics API, then payments API | The part of `marker` after the dot (`sub_id`) |
| Viator | Partner API commissions report (weekly payouts) | `campaign` |
| Stay22 | Reporting API or dashboard export (verify) | `campaign` |
| Impact (Expedia Group, Skyscanner, Airalo) | Impact Actions API | `subId1` |
| Awin or CJ (only if a program requires it) | Their reporting APIs | Network's sub-id field |

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

Queue in priority order (one per surface at a time, pre-registered metric, server-side assignment, never hide the disclosure or rank by commission): (1) link-out container (`SFSafariViewController` vs external Safari), measured as tracked bookings per 100 clicks; (2) lodging partner (Travelpayouts Booking.com vs Stay22 vs direct once approved), as net commission per click; (3) disclosure wording (every variant discloses: standard sentence, "Paid link: we earn a commission.", standard plus "Ad"); (4) checklist timing (45, 30 or 14 days before departure); (5) button position on lodging cards; (6) price alert delivery (push, email, in-app); (7) "Book the plan" last slide on or off by default; (8) "Hide booking links" visibility; (9) paid-tier weighting. Sample size note: detecting 3.0% to 3.6% lodging conversion needs about 20,000 clicks per arm, so early on test click-through and treat bookings as a slow aggregate.

## 9. Concierge lane

An optional "Have a human book this" request on stays, cruises and complex trips. A human advisor, working under a host travel agency, fulfills it. The user gets perks; Hermi earns the agency commission. It is always optional, always disclosed, and never pushed.

### 9.1 Request flow

1. **Entry points.** A quiet card on a shortlisted stay ("Want a person to book this and handle changes?"), on a cruise idea, and on complex trips (more than 2 destinations, more than 8 travelers, a honeymoon or milestone flag). Never inside AI output, never on a paywall, never as a push.
2. **Request form.** Kind (`stay`, `cruise`, `complex_trip`, `other`), dates (`start_date`, `end_date`) and flexibility, `party_size`, budget range (`budget_min_minor`, `budget_max_minor`, `currency`), a brief (`brief`, free text; it also carries preferences, the saved items it refers to, phone if given and preferred contact method), and `contact_email`. The trip's public summary is attached.
3. **Consent screen** (section 9.2) must be accepted before submit.
4. **Confirmation.** The user sees "Request sent. An advisor replies within 1 business day" (default SLA), the status tracker and the disclosure.
5. **Advisor work.** Quote and proposal are prepared and sent by the advisor outside the app (email) at launch; proposals are attached to the request as files (R2). Booking happens on the agency's and supplier's systems; the client pays the supplier or agency directly. Hermi never takes payment for the booking and never stores card data.
6. **After booking.** The advisor records the booking reference and commission estimate; the confirmation is added to the trip (flight, stay or itinerary item) with the client's consent.

### 9.2 Consent

A `consents` row (`kind = 'concierge_sharing'`, `version`, `granted`, `source`, timestamp) is required, and the request records `share_consent_at`. The screen lists exactly what goes to the advisor and the agency: name, email, phone (if given), the request details, the trip's dates and destination, and traveler names and dates of birth only at the time of booking and only when the advisor asks for them inside the request thread. It says: "Hermi is paid a commission by the travel agency that books this. The price to you is the same as booking direct." Users can withdraw consent, which closes the request and deletes the advisor-side copy within 30 days (except records the agency must keep by law).

### 9.3 Handoff to the advisor

- **Launch mode.** The founder is the advisor. A new request creates an item in the admin console queue ([08-admin-control-center.md](08-admin-control-center.md)) and an email to the advisor inbox with a secure link (no personal data in the email body). The advisor works the request under the host agency's credentials.
- **Later mode.** Additional advisors are users with an `advisor_seats` row, see only `concierge_requests` whose `assigned_to` is them (or whose `advisor_org_id` is their org), and may use Hermi for Advisors (section 11.4). Assignment is round robin by kind and workload; users never choose by commission.
- `concierge_requests` columns used: `id`, `requested_by`, `trip_id`, `kind`, `status`, `brief`, `destination`, `start_date`, `end_date`, `party_size`, `budget_min_minor`, `budget_max_minor`, `currency`, `contact_email`, `share_consent_at`, `advisor_org_id`, `assigned_to`, `agency_reference` (the booking reference), `perks` (jsonb), `quote_minor`, `quote_currency`, `commission_expected_minor`, `commission_received_minor`, `commission_currency`, `booked_at`, `completed_at`.

### 9.4 Status tracking

Statuses (`concierge_status`): `submitted`, `triaged`, `assigned`, `quoted`, `booked`, `completed`, `cancelled`, `declined`. The user sees a tracker with plain labels and dates, and gets an in-app message and optional push on changes they requested (no marketing). SLA alerts in the admin console: a `submitted` request older than 1 business day, a `quoted` request older than 7 days with no reply (advisor follow-up).

### 9.5 Commission recording

- The host agency pays commission after the traveler checks out (hotels roughly 8 to 15%, cruises 10 to 16%, host split 70 to 90%, all reported, verify the agency contract). The advisor records the expected commission at booking (`commission_expected_minor`).
- Monthly, the agency's commission statement is imported (CSV upload in the admin console) and matched by `agency_reference`; matched rows get `commission_received_minor` when the payout lands. A cancelled booking (`status = 'cancelled'`) with an expected commission and nothing received counts as lost.
- Revenue is recognized when received (`commission_received_minor` set); management reports also show expected.
- Perks (breakfast, upgrades, agency credits) are noted in `perks`. A Hermi reward of 40 credits on a completed booking is granted as an `adjustment` grant (default, configurable).

### 9.6 Disclosures and legal notes

- The card, the form, the confirmation and the advisor's proposal all say Hermi earns a commission. Recommendations must include options the client asked for, are never ranked by commission, and the advisor records conflicts.
- **Seller of travel.** Several US states (California, Florida, Hawaii, Iowa, Washington and others) regulate sellers of travel. The advisor operates as an independent contractor under a host agency that holds the required registrations, consumer protection (trust or bond) and errors and omissions insurance; Hermi itself does not sell travel, take payment for travel or hold itself out as a travel seller. The legal structure, the contract with the host agency, the disclosures wording and state-by-state rules are confirmed by counsel before launch (pre-launch item). Cruise lines and suppliers require the advisor's credentials (for example IATA/CLIA/ARC numbers through the host agency).
- Apple: the service is a physical travel service consumed outside the app, so it is outside In-App Purchase under Guideline 3.1.3(e); it never unlocks app features; it is described in the review notes.
- No insurance sales or advice through the concierge path unless the host agency and counsel approve in writing.

## 10. Group payments (Stripe)

Two layers. Tracking (polls, expenses and manual splits inside the app) ships at launch and is included in every paid plan and both passes. Collection (paying each other through Stripe for real-world costs) is Phase 4 and is for `group_trip_pass` and `pro` only (flag `group_payments`, off at launch). Group payments are Stripe only: never In-App Purchase, and never for digital features. The passes and plans (IAP) unlock the features; the money that travelers owe each other is real-world cost.

### 10.1 Tracking (plus, family, pro, trip_pass and group_trip_pass)

Polls and manual cost splitting are in every paid plan and both passes (section 2.2); Free users use them on trips that have them. `expenses` (`paid_by_person_id`, `amount_minor`, `currency`, `description`, `incurred_on`, `category`, `split_method`, `trip_id`, plus `fx_rate`, `amount_trip_minor` and `trip_currency` for the record of what was agreed), `expense_shares` (`expense_id`, `person_id`, `share_minor`, `weight`) and `settlements` (`from_person_id`, `to_person_id`, `amount_minor`, `currency`, `method`, `status`, `stripe_payment_intent_id`) hold it. Split methods (`split_method`): `equal`, `exact`, `percent`, `shares` (person-nights are entered as `shares` weights). Multi-currency expenses keep their original currency; balances are shown in the trip's currency from `amount_trip_minor` (fixed at entry with `fx_rate` from `fx_rates`), with the original shown beside. The settle-up screen proposes the minimal set of payments to zero every balance.

### 10.2 Collection

1. **Organizer setup (Phase 4).** The trip owner or a named organizer connects a Stripe Connect Express account (Stripe-hosted onboarding; Hermi stores the account id only, in `users.stripe_connect_account_id`, with `stripe_connect_ready` set from the `account.updated` webhook; never bank details). Without it, the app offers "Mark as paid" (cash, bank transfer or app of your choice) but no card collection.
2. **Collect.** The organizer creates a collection for a real-world cost ("Villa deposit, $2,400"; a `payment_collections` row with the total, currency, `split_method`, `fee_mode`, due date and a snapshot of the connected account id) and picks a split. The app generates one payment link per traveler (Stripe Checkout, reachable in the app browser or on the web; Apple Pay and Google Pay appear where available). Each traveler pays their own share, recorded as a `settlements` row with `collection_id` and `method = 'stripe'`.
3. **Destination charges.** Each payment is a Stripe destination charge to the organizer's connected account, so funds settle to the organizer and Hermi never holds traveler money (the structure is reviewed with counsel for money transmission, pre-launch item).
4. **Fees.** Stripe's processing fee (about 2.9% plus $0.30 for US cards, verify) is shown to the payer as a separate line before paying, or absorbed by the organizer when they choose "I cover fees". Connect and payout fees (verify) are charged to the organizer's connected account. Hermi's application fee is 0 at launch (default `fee_bps` in the `rules` of the `group_payments` feature flag, copied to `payment_collections.application_fee_bps` when the collection is created); the lane is a driver of Group Trip Pass sales, not a margin. A later fee, if any, is disclosed before payment and is never a percentage of a digital purchase.
5. **Settle.** Webhooks (`payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`, `charge.dispute.created`, `account.updated`, `payout.paid`) update `settlements` and the collection's progress: `status` `pending`, `succeeded`, `failed`, `refunded` and `disputed` (from `charge.dispute.created` until Stripe resolves it; a won dispute returns to `succeeded`, a lost one becomes `refunded`). A collection closes (`payment_collections.status = 'closed'`) when every share is `succeeded` or the organizer closes it; open balances remain tracked. Idempotency keys on every Stripe call are `settlement:{id}:{attempt}`.
6. **Refunds.** The organizer refunds through the app (a Stripe refund on the connected account); Hermi's fee (none at launch) would be refunded with it. A refunded share reopens the balance. Disputes are handled by the organizer as the merchant on the connected account; the app shows status and instructions and Hermi support assists. Hermi cannot refund money it never held.
7. **Receipts and privacy.** Stripe emails receipts. We store Stripe ids and amounts, not card data. Payer names shown to the organizer are the trip's people names.

### 10.3 Apple rules for this lane

- Payments between travelers for real-world trip costs are for goods and services consumed outside the app, so they fall under Guideline 3.1.3(e) and do not use In-App Purchase. Verify the current text on the day of submission, and keep the review notes explicit that nothing digital is unlocked by these payments.
- The Group Trip Pass stays an In-App Purchase. The app never links to a web page to buy the Group Trip Pass.
- Collections are not offered to users in regions where Stripe Connect Express is unavailable; they fall back to "Mark as paid".
- Payment links open in the in-app browser with visible chrome (Guideline 5.1.1) and carry no tracking.

## 11. Later lanes (spec level)

Each lane is behind a `feature_flags` key (default off; 03 section 11.5 seeds `group_payments`, `concierge_requests`, `room_block_requests`, `partner_guides`, `print_orders` and `advisor_workspaces`) and is specified to the depth needed to keep the schema and ledger ready. None changes the non-negotiable rules.

### 11.1 In-app hotel booking through LiteAPI (year 2 and later)

- Start only after click data shows strong booking intent (lodging click-to-booking and a meaningful share of users reaching the stay comparison). LiteAPI (Nuitee) is merchant of record; Hermi earns a margin (5 to 15%, reported, verify) on the net rate.
- Flow: search by place and dates and party (server-side, server-held API key), show rates sorted by price or rating with the commission-blind statement, prebook (price lock), collect payment with LiteAPI's payment flow in a web view hosted by LiteAPI (card data never touches our servers), book, store the confirmation as a `lodging_options` booking with status `booked`, send the confirmation email.
- Apple: a physical service consumed outside the app; Stripe-style web payment is allowed under 3.1.3(e); never unlocks features. Terms, cancellation policy and the merchant of record are shown before payment.
- New table at that time (migration added then): `hotel_bookings` (user, trip, supplier, supplier_ref, price, margin, currency, status, commission_status). Revenue recognized at check-out. Support and cancellations go through LiteAPI; refunds follow their rules.
- Never displaces the affiliate options or their neutrality: the "Book in Hermi" option appears beside them and is sorted by the same user-chosen criteria.

### 11.2 Partner guides (year 2 and later)

- Tourism boards and hotel brands sponsor labeled destination guides stored in `partner_guides` (`partner_name`, `partner_url`, `destination_name`, `title`, `summary`, `body_md`, `cover_image_url`, `is_sponsored`, `disclosure_text`, `status`, `published_at`, `program_id`, plus `entries` (the places a reader can copy into an itinerary), the review fields `review_state`, `reviewed_by` and `reviewed_at`, and the sponsorship terms `sponsor_starts_on`, `sponsor_ends_on`, `sponsor_fee_minor`, `sponsor_fee_currency` and `sponsor_invoice_ref`, which are finance data the app role can never read). Sold as flat-fee sponsorships invoiced outside the app (Stripe invoices or bank transfer).
- Rules: every guide carries a visible "Sponsored by {partner}" label, lives in its own section, is never mixed into search, lists, rankings or AI answers, never gets a push, and is never cited by an agent. A sponsored guide cannot change a place's rating or position anywhere. FTC and UK ASA labeling: "Ad" or "Sponsored" in text.
- Reporting: impressions and taps (first-party events, no third-party SDK) go into a monthly sponsor report.

### 11.3 Printed trip books (year 2)

- Print-on-demand trip books and posters generated from presentation mode, ordered on the web (not in the iOS app; a link from the app opens the web order page in the in-app browser). Stripe Checkout takes payment; the print vendor's API (for example Prodigi or Printful, vendor chosen at that phase) receives the print job and ships.
- `print_orders`: `user_id`, `trip_id`, `product`, `format` (`softcover`, `hardcover`), `page_count`, `copies`, `pdf_key` (R2 key to the PDF), `amount_minor`, `shipping_minor`, `currency`, `stripe_payment_intent_id`, `printer`, `printer_order_id`, `status` (`draft`, `awaiting_payment`, `paid`, `submitted`, `printing`, `shipped`, `delivered`, `cancelled`, `refunded`), `carrier`, `tracking_number`, `shipping_address` (jsonb), `tax_minor` (the Stripe Tax result), `quote_expires_at` (a `draft` row is the quote, 04 5.23), `created_at`.
- Margin target 35 to 45% after vendor cost, shipping and Stripe fees. Sales tax or VAT through Stripe Tax (verify). Physical goods consumed outside the app are outside In-App Purchase. Affiliate and sponsor content is excluded from printed books unless the user adds it; the commission sentence is printed wherever a partner link is shown.
- Refunds for misprints and damage per vendor policy; data retention for addresses is 90 days after delivery.

### 11.4 Hermi for Advisors (year 2 and later)

- Web SaaS for independent travel advisors: client trip workspaces, branded presentation mode, proposals, and commission tracking. Sold on the web through Stripe Billing, not through the App Store. The iOS app does not sell it and does not link to its purchase page (Guideline 3.1.1); advisors sign in on the web.
- Pricing: $29 a seat a month, or $24 a seat a month on annual billing ($288 a seat a year). Stripe Checkout and Customer Portal; per-seat quantity subscription; 14-day trial without a card is not offered (default: card required, cancel anytime).
- Tables: `advisor_orgs` (`name`, `slug`, `host_agency_name`, `billing_email`, `stripe_customer_id`, `commission_split_bps`, `status`), `advisor_seats` (`advisor_org_id`, `user_id`, `role`, `billing_period`, `stripe_subscription_item_id`, `status`), `advisor_clients` (`advisor_org_id`, `advisor_user_id`, `client_name`, `client_user_id` nullable, `trip_id`, `commission_expected_minor`, `status`). Seeds: plan `advisor_seat`, products `advisor_seat_monthly` and `advisor_seat_annual`, flag `advisor_workspaces`.
- Entitlement: an active seat gives the advisor `pro`-level capabilities on trips in their org's client workspaces only (resolved in 4.2 and 03 section 7.1; the `advisor_seat` plan row carries the pro-level limits, `entitlements.source` is `advisor`), no personal AI allowance beyond a seat allowance that is a default of 150 credits a month as a `monthly` grant (`plans.monthly_credits` of `advisor_seat`, written by the daily grant job for `advisor` entitlements) so advisor AI spend is covered by seat revenue against the $0.40 daily budget and a seat ceiling of $3.40 (`plans.limits` of `advisor_seat`, defaults). Client guests join free.
- Dunning: Stripe smart retries for 14 days; seats go read-only after that, never deleted; client data is exportable at all times.
- Commission tracking: advisors record bookings and expected commission per client trip (`advisor_clients` and a per-booking JSON), with monthly totals and CSV export. Hermi takes no commission on an advisor's bookings.
- Webhooks: `customer.subscription.created`, `.updated`, `.deleted`, `invoice.paid`, `invoice.payment_failed`, `checkout.session.completed`; handler writes `webhook_events` (`provider = 'stripe'`) and follows the same idempotent pattern as 3.4.
- Taxes: Stripe Tax for VAT and sales tax (verify registration thresholds). Advisors are business customers; capture VAT ids.

### 11.5 White-label and API (year 3 and later)

Licensed planner for agencies and tour operators; specified only as a direction: a separate tenancy (`advisor_orgs` with a `white_label` flag and custom domain), API keys, and annual contracts invoiced by Stripe. No work is scheduled before the advisor lane has paying customers.

## 12. Revenue reporting and metrics

### 12.1 Sources

| Source | What it gives | Stored in |
|---|---|---|
| RevenueCat webhooks and reconcile | Subscription, pass and pack transactions | `subscriptions`, `store_transactions`, `trip_passes`, `credit_grants` |
| App Store Connect sales and trends (monthly import) | Apple's net proceeds and tax adjustments | finance sheet, reconciled to `store_transactions` |
| Stripe | Advisor seats, print orders, group payment fees if any | `webhook_events`, `print_orders`, `advisor_*` |
| Affiliate networks | Commissions | `affiliate_conversions` |
| Concierge statements | Agency commissions | `concierge_requests` |
| `ai_usage`, `provider_calls` | Variable cost | [06-ai-agents-spec.md](06-ai-agents-spec.md) |
| PostHog | Funnels, paywall views (frequency-cap state is in `users.prefs`) | |

All amounts are stored in minor units with an ISO currency and converted to USD with `fx_rates` at the event date for reports. Apple revenue is reported net of Apple's 15% commission (Small Business Program, under $1M in annual proceeds; above that, standard rates apply and the model is rerun).

### 12.2 Definitions

| Metric | Definition |
|---|---|
| Net price per plan | Gross minus 15%: Plus monthly $5.09, Plus annual $33.99, Family monthly $7.64, Family annual $51.00, Pro monthly $10.19, Pro annual $84.15, Trip Pass $8.49, Group Trip Pass $16.99 |
| MRR | Sum over active subscriptions (status `active`, `in_grace`; `in_trial` excluded until paid) of the monthly equivalent of net price; annual plans divided by 12; passes and packs excluded |
| New, expansion, contraction, churned MRR | The month-over-month movements by subscription; upgrades are expansion, downgrades contraction, expirations churned |
| ARR | MRR times 12 (subscriptions only) |
| Passes and packs revenue | Net sales in the month, reported separately, since they are one-off |
| ARPPU | Total net revenue in the month (subscriptions, passes, packs, advisor seats) divided by paying users in the month (any purchase or active subscription) |
| ARPU | Total net revenue including affiliate and concierge divided by monthly active users |
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
| Revenue per trip | All revenue attributed to a real trip (passes bought for it, affiliate conversions from its clicks, concierge commission, print orders) divided by the number of real trips in the period; also per trip by tier of owner |
| Concierge | Requests, request to booked rate, average booking value, average commission, days to paid |
| Group payments | Collections opened, share of shares paid, refund and dispute rate, Group Trip Pass attach to collections |
| Gross margin | Net revenue minus variable cost (AI, provider calls, infrastructure allocation, payment fees) divided by net revenue |
| Free cost per MAU | (Free-tier AI plus provider cost) divided by Free MAU; guard value about $0.02 a month for AI |

Kill rule: at month 9 after launch, if under 1% of monthly users pay and affiliate income is under $0.20 per monthly user per year (annualized), stop investing. Both numbers are tracked monthly from launch.

### 12.3 Dashboards and cadence

- **Revenue overview.** MRR waterfall, ARR, passes and packs, affiliate (pending, approved, paid), concierge (expected, confirmed, paid), total net revenue, gross margin. Daily refresh, month close on the 5th.
- **Paywall.** Views, dismissals, purchases and revenue by trigger, offering and experiment variant; funnel from view to `purchase_started` to `purchase_completed`; mute and cap hit rates.
- **Plans.** Active by tier, trials, churn and reasons, upgrade and downgrade flows, household sizes, pass binding rate and time to bind, unapplied passes.
- **Credits.** Balances by pool, burn by action code, expiry, negative balances, packs sold, credit margin by action.
- **Affiliate.** Section 8.8.
- **Concierge.** Section 9.4 metrics and commission aging.
- **Cohorts.** Revenue per user by signup month, by acquisition source, by first paywall trigger.
- **Alerts** (to email and the on-call channel): MRR drop over 10% month on month, webhook failures, reconcile mismatches, refund rate above 5% for a product, cost per active payer above $2 (Plus, Family) or $6 (Pro), negative credit balances above 20 accounts, affiliate import failures.

Weekly Monday review uses the same tiles: installs, activation, trial starts, paywall views and conversion, MRR and churn, credit burn, affiliate EPC, AI cost share, concierge pipeline. The Pro launch gate (200 measured agent runs averaging $0.60 or less per run, or more than 15% of Plus payers buying agent-run credits) is computed on the Credits dashboard and flips nothing automatically; a person turns `tier_pro` on.

### 12.4 Events (first-party, sent to PostHog)

`paywall_viewed`, `paywall_dismissed`, `purchase_started`, `purchase_completed` (with `is_trial` for a trial start), `purchase_failed`, `restore_tapped`, `subscription_started`, `subscription_renewed`, `trial_converted`, `subscription_canceled`, `subscription_changed` (upgrade and downgrade), `trip_pass_applied`, `trip_pass_moved`, `trip_pass_expired`, `ai_action_started` and `ai_action_completed` (credit reserve, settle and refund, with `outcome: refunded`), `credits_expired`, `purchase_completed` with a `credits_*` product (a pack), `partner_link_tapped` (an outbound click), `concierge_requested`, `concierge_status_changed`, `payment_collection_created`, `payment_collection_paid`. These are the names in 10 section 4. No event carries names, emails or free text; session replay is off or masked.
