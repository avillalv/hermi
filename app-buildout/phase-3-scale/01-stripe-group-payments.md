# Pack 01: Stripe group payments and the events workspace

Part of [Phase 3: scale](README.md). Tickets P3-001 to P3-014. Written 2026-09-30.

| | |
|---|---|
| Feature flags | `group_payments` (created off by Phase 2), `event_workspaces` (new, off) |
| Needs | A lawyer before any build (money transmission, refunds, disputes, tax, sanctions). A support contractor once collections are live. No funding. |
| Builds on | Phase 1: Stripe webhook endpoint, `webhook_events`, [entitlements](../phase-1-launch/07-monetization-spec.md), [admin console](../phase-1-launch/08-admin-control-center.md). Phase 2: Group Trip Pass, polls, manual cost splitting and the `settlements` table, room-block request ([Phase 2](../phase-2-growth/README.md)). |
| Source names | The Phase 1 files call this "Phase 4" and ticket WF-102 and WF-103. This folder calls it Phase 3. The spec text of record is [07 section 10 (full spec)](../reference-full-spec/07-monetization-spec.md), [04 section 5.17 (full spec)](../reference-full-spec/04-api-spec.md), [08 section 6.9 (full spec)](../reference-full-spec/08-admin-control-center.md). |

## 1. Goal and revenue case

**Goal.** Let the organizer of a group trip collect each traveler's share of a real-world cost (a villa deposit, a tour, a dinner) by card, without Hermi ever being the place the money sits, and sell an events workspace (up to 40 travelers) for offsites, destination weddings and similar. Both extend the group features that already drive Group Trip Pass sales. Payments are a growth driver first and a small margin second.

The two layers come from [09 section 3.2](../context/business-plan/09-revenue-expansion.md) (layers 3 and 4):

| Layer | What | Price to the user | Channel |
|---|---|---|---|
| Events workspace | One trip, up to 40 travelers, group tools, payments, room-block request | $79 once per event, about $76.60 net of 3% card fees | Web only (Stripe Checkout) |
| Payment collection | Stripe Connect Express, organizer is the connected account | 1.5% of the amount collected on top of Stripe's card cost, shown before paying | Stripe |

**Revenue (base case, from 09 sections 3.2 and 6.2).**

| | Y3 | Y4 | Y5 |
|---|---|---|---|
| Events sold (base) | 50 | 200 | 500 |
| Events revenue at $76.60 net | $3.8k | $15.3k | $38.3k |
| Payments, $ per MAU (base) | 0 | $0.08 | $0.12 |
| Payments revenue (MAU 100k, 150k) | 0 | $8.0k | $18.0k |
| Line total | $3.8k | $23.3k | $56.3k |

Worked: year 5 is 500 x $76.60 + 150,000 x $0.12 = $38.3k + $18.0k = $56.3k. Ambitious case: 20, 200, 800 and 2,000 events in years 2 to 5 and $0.15 to $0.25 per MAU of payments (line totals $1.5k, $37.8k, $136.3k, $278.3k). Conservative: zero.

**Check the source arithmetic before relying on it.** 09 gives $0.09 per MAU at the stated inputs: 0.6 trips per MAU x 25% group trips x 2% collecting in the app x $4,000 x 1.5%. Multiplying those gives 0.6 x 0.25 x 0.02 x 4,000 x 0.015 = $0.18, twice the stated figure. The model uses $0.08 (year 4) and $0.12 (year 5), which sit below both, so the line total stands, but P3-013 must replace the assumption with measured collected volume before any growth spending is planned around it.

**Margins and costs.**

- Events workspace: Group Trip Pass class costs, about $1.30 of AI and infrastructure typical, $3.75 worst case (09 section 2.3). Margin about 92% typical on $76.60 net.
- Payments: Hermi's fee is 0% at launch (07 section 10.2, default `fee_bps` 0 in the `group_payments` flag) and 1.5% once the lane is measured. The real cost is support for disputes and refunds, not infrastructure. Stripe Connect charges platforms per connected account and per payout (reported, verify on Stripe's pricing page); model them as cost per collecting organizer, not per payment.
- The fee is never taken on a digital purchase and never hidden: the payer sees every line before paying.

**What would break the case.** Collection is distribution-bound (09 section 6.5: "event volume is distribution-bound") and depends on the legal review in P3-001. If counsel says Hermi needs a money transmitter licence or a state registration, the lane stays as "Mark as paid" and only the events workspace ships.

## 2. Design decisions

| # | Decision | Default and reason |
|---|---|---|
| D1 | Charge type | Destination charges, as the spec says: Hermi creates the charge on the platform account with `transfer_data.destination` set to the organizer's Express account and `on_behalf_of` set to the same account. **Verify with Stripe and counsel before building.** Under Stripe's documented model the platform, not the connected account, is responsible for refunds and chargebacks on destination charges, and funds pass through the platform balance before transfer. 07 section 10.2 says "Hermi never holds traveler money" and "disputes are handled by the organizer as the merchant". Those two sentences are not both true for destination charges. Direct charges (created on the connected account, which is then the merchant) match the 07 wording. P3-001 decides; the code path is isolated in `providers/stripe.py` so switching is one function. |
| D2 | Who may collect | A trip with `group_trip_pass` or `event_workspace`, or whose owner is `pro` (limit key `group_payments`). Everyone else sees the `collect_payments` paywall. Never Apple In-App Purchase, never for digital features. |
| D3 | Fee modes | `payer_pays` (default: processing fee and any Hermi fee shown as lines above the share) or `organizer_covers`. Stored in `payment_collections.fee_mode`. |
| D4 | Currency | The trip currency. Launch with currencies the organizer's connected account can settle in (start with USD, EUR, GBP). Others fall back to "Mark as paid" (`422 unsupported_currency`). |
| D5 | Regions | Collection is offered only where Stripe Connect Express is available to the organizer. Otherwise "Mark as paid" only. |
| D6 | Caps | Per payment and per collection caps live in `feature_flags.rules` (`max_payment_minor`, `max_collection_minor`), default $2,500 and $25,000, to keep early fraud and dispute exposure small. |
| D7 | Events workspace is a pass | It reuses `trip_passes` and the entitlement resolver (one more plan code), so no new capability engine is needed. |

## 3. User stories and acceptance criteria

**P1-1. Organizer connects a payout account.**
As an organizer, I want to set up where the money goes once, so that travelers can pay by card.
- Only the trip owner (or a named organizer who is an editor) can start onboarding; `POST /me/stripe-connect/onboarding` returns a Stripe-hosted onboarding link. Hermi stores only `users.stripe_connect_account_id` and `stripe_connect_ready` (from `account.updated`), never bank details.
- If onboarding is incomplete the collection screen says what Stripe still needs and offers "Mark as paid" instead.
- Available only where allowed (D5); otherwise the screen says so plainly.

**P1-2. Organizer creates a collection.**
As an organizer, I want to ask everyone for their share of the villa deposit, so that I do not chase people.
- Fields: title (max 200), total, split method (`equal`, `exact`, `percent`, `shares`), due date, fee mode. The split uses the same minor-unit rounding as expenses (leftover cents assigned by traveler order, so shares sum to the total).
- Creating the collection inserts one `payment_collections` row and one `settlements` row per payer (status `pending`, `method = 'stripe'`, `collection_id` set). The organizer's own share is not a settlement.
- Shown before sending: the fee line per traveler and the sentence "Payments are handled by Stripe. Hermi does not hold your money." (confirm against the D1 outcome).
- Blocked when the trip lacks the capability (`403 entitlement_required`, reason `group_payments`, with the paywall body) or the flag or kill switch is off (`503 feature_disabled`).

**P1-3. Traveler pays.**
As a traveler, I want to pay my share in one step, so that I am done.
- Each payer gets a link (in app and by email) that opens a Stripe Checkout session on the web with Apple Pay and Google Pay where available. The page shows share, each fee line and total before the pay button.
- A traveler without an account pays through the emailed link, which carries an unguessable token tied to the settlement and expires after 30 days.
- Success moves the settlement to `succeeded` from `checkout.session.completed` or `payment_intent.succeeded`, never from the browser redirect.
- Only `recorded` and `succeeded` settlements reduce balances.

**P1-4. Organizer tracks and nudges.**
As an organizer, I want to see who has paid and remind the rest, so that the deposit is on time.
- Progress bar and a per-person list (Paid, Waiting, Failed, Refunded, In dispute) from `settlements.status`.
- "Remind" sends a push and email, at most once per person per 48 hours (`settlements.last_reminded_at`).
- The collection closes itself when every share is `succeeded`; the organizer can close it earlier (open balances stay tracked as manual debts).

**P1-5. Refund.**
As an organizer, I want to refund a traveler who cannot come, so that I am fair.
- Full or partial refund through the app. The refund reopens that balance. Hermi's fee is refunded with it. Processing fees are not returned by Stripe (verify), and the refund screen says so.
- Refund is refused if the collection is in dispute for that payment.

**P1-6. Dispute.**
As an organizer, I want to know when a cardholder disputes a payment, so that I can respond in time.
- `charge.dispute.created` marks the settlement `disputed`, inserts `payment_disputes` with the evidence due date, notifies the organizer, and raises the admin alert 3 days before the due date (08 section 10).
- A won dispute returns the settlement to `succeeded`; a lost one becomes `refunded` (07 section 10.2).

**P1-7. Manual fallback always works.**
As any member, I want "Mark as paid" to keep working when card collection is off, so that nothing breaks.
- With the flag off, the region unsupported or Stripe down, the Settle up screen shows manual marking only and no error.

**P1-8. Buy an events workspace.**
As an organizer of an offsite or destination wedding, I want room for up to 40 travelers, so that everyone is in one plan.
- Sold on the web only: "Get the events workspace" on the trip opens the web checkout in the in-app browser; the iOS app does not sell it (07 section 11.4 rule, Apple 3.1.1; re-read the current text at submission).
- After payment a `trip_passes` row is bound to the trip: 90 days, 40 travelers, 39 collaborators, 80 credits, polls, cost splitting, room-block request and payments. If the trip has a Group Trip Pass it is set to `upgraded` and the unspent credits stay spendable (same rule as 07 section 7.9).
- Refund on the web within 14 days if no collection has been opened (finance approves, 08 section 3).

**P1-9. Finance reconciles.**
As the founder or bookkeeper, I want the ledger to match Stripe, so that books close.
- A daily reconcile job compares `settlements`, `payment_collections` and Stripe balance transactions, and alerts on any mismatch above zero.

## 4. Database additions

### 4.1 State after Phase 2, and the definitions reused from the full 03

Phase 2 ([Group Trip Pass and group tools](../phase-2-growth/02-group-trip-pass-and-group-tools.md)) already creates `polls`, `poll_votes`, `expenses`, `expense_shares` and `settlements`, with `settlements.method` allowing `stripe`, `settlements.status` allowing `disputed`, `settlements.collection_id` as a plain nullable column with no foreign key, `settlements.stripe_payment_intent_id` with its unique index, the `group_tools` and `group_payments` flags (the latter off, `rules.fee_bps` 0), the `group_trip_pass` plan with limit key `group_payments` true, and `trip_passes.upgraded_from_id` with `ck_trip_passes_upgrade`. Phase 1 has none of the Stripe Connect objects (Phase 1 03 section 1.1 lists `payment_collections` and `users.stripe_connect_*` as dropped), so this pack creates them. Definitions come from the full 03 (section 5.9 and 5.1):

```sql
CREATE TABLE payment_collections (
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                   uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  organizer_user_id         uuid REFERENCES users (id) ON DELETE SET NULL,          -- the organizer; funds go to users.stripe_connect_account_id
  organizer_person_id       uuid NOT NULL,                                           -- the payee on the settlements rows
  title                     text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),   -- "Villa deposit"
  total_minor               bigint NOT NULL CHECK (total_minor > 0),
  currency                  currency_code NOT NULL,                                  -- the trip currency
  split_method              split_method NOT NULL DEFAULT 'equal',
  fee_mode                  text NOT NULL DEFAULT 'payer_pays',                      -- who bears the Stripe processing fee
  application_fee_bps       integer NOT NULL DEFAULT 0 CHECK (application_fee_bps BETWEEN 0 AND 10000),   -- copied from feature_flags.rules.fee_bps of group_payments when created (0 at launch)
  stripe_account_id         text NOT NULL,                                           -- snapshot of the organizer's connected account
  status                    text NOT NULL DEFAULT 'open',
  due_on                    date,
  closed_at                 timestamptz,
  created_by                uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (trip_id, organizer_person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE RESTRICT,
  CONSTRAINT ck_payment_collections_fee_mode CHECK (fee_mode IN ('payer_pays', 'organizer_covers')),
  CONSTRAINT ck_payment_collections_status CHECK (status IN ('open', 'closed', 'cancelled')),
  CONSTRAINT ck_payment_collections_closed CHECK (status = 'open' OR closed_at IS NOT NULL),
  CONSTRAINT uq_payment_collections_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_payment_collections_trip ON payment_collections (trip_id, status);
SELECT add_updated_at_trigger('payment_collections');

-- Phase 2 left settlements.collection_id as a plain column; attach the foreign key now (full 03 section 5.9).
ALTER TABLE settlements ADD CONSTRAINT fk_settlements_collection_id_payment_collections
  FOREIGN KEY (collection_id, trip_id) REFERENCES payment_collections (id, trip_id) ON DELETE SET NULL (collection_id);
CREATE INDEX ix_settlements_collection ON settlements (collection_id) WHERE collection_id IS NOT NULL;

-- Stripe Connect Express account of the organizer (never bank details); written by the billing service, not by the app role.
ALTER TABLE users
  ADD COLUMN stripe_connect_account_id text,
  ADD COLUMN stripe_connect_ready boolean NOT NULL DEFAULT false;      -- charges_enabled, from the account.updated webhook
CREATE UNIQUE INDEX uq_users_stripe_connect ON users (stripe_connect_account_id) WHERE stripe_connect_account_id IS NOT NULL;

-- Trip-child policies (the generated loop in full 03 section 6.4 lists payment_collections; Phase 2 extended the loop for its own tables).
ALTER TABLE payment_collections ENABLE ROW LEVEL SECURITY;
CREATE POLICY payment_collections_select ON payment_collections FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY payment_collections_insert ON payment_collections FOR INSERT WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY payment_collections_update ON payment_collections FOR UPDATE USING (can_edit_trip(trip_id)) WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY payment_collections_delete ON payment_collections FOR DELETE USING (can_edit_trip(trip_id));
```

Also from the full 03: `store_transactions.kind` gains `group_payment` (each succeeded Stripe settlement writes one row for the finance ledger, `store = 'stripe'`, amount charged, net after Stripe's fee; see 4.2), and the kill switch `provider.stripe` exists (create it if Phase 1 did not seed it).

### 4.2 New in this pack

```sql
-- Migration p3_group_payments (same revision as 4.1). A table added after the RLS revision carries its own grants and policies.

ALTER TABLE settlements
  ADD COLUMN stripe_checkout_session_id text,
  ADD COLUMN stripe_charge_id           text,
  ADD COLUMN charged_minor              bigint CHECK (charged_minor IS NULL OR charged_minor >= amount_minor),  -- what the payer was charged: share plus fee lines
  ADD COLUMN hermi_fee_minor            bigint NOT NULL DEFAULT 0 CHECK (hermi_fee_minor >= 0),
  ADD COLUMN stripe_fee_minor           bigint CHECK (stripe_fee_minor IS NULL OR stripe_fee_minor >= 0),       -- actual, from the balance transaction
  ADD COLUMN refunded_minor             bigint NOT NULL DEFAULT 0 CHECK (refunded_minor >= 0),
  ADD COLUMN due_on                     date,
  ADD COLUMN payer_token_hash           bytea,                                                                   -- hash of the emailed pay-link token (people without accounts)
  ADD COLUMN payer_token_expires_at     timestamptz,
  ADD COLUMN last_reminded_at           timestamptz;
CREATE UNIQUE INDEX uq_settlements_checkout ON settlements (stripe_checkout_session_id) WHERE stripe_checkout_session_id IS NOT NULL;
CREATE UNIQUE INDEX uq_settlements_payer_token ON settlements (payer_token_hash) WHERE payer_token_hash IS NOT NULL;

CREATE TABLE payment_disputes (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  settlement_id       uuid NOT NULL REFERENCES settlements (id) ON DELETE CASCADE,
  trip_id             uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  stripe_dispute_id   text NOT NULL,
  reason              text,
  amount_minor        bigint NOT NULL CHECK (amount_minor > 0),
  currency            currency_code NOT NULL,
  status              text NOT NULL DEFAULT 'needs_response',
  evidence_due_by     timestamptz,
  evidence_note       text NOT NULL DEFAULT '',                       -- finance notes; the evidence itself is submitted in the Stripe dashboard
  evidence_submitted_at timestamptz,
  outcome             text,
  resolved_at         timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_payment_disputes_stripe UNIQUE (stripe_dispute_id),
  CONSTRAINT ck_payment_disputes_status CHECK (status IN ('needs_response', 'under_review', 'won', 'lost', 'warning_closed')),
  CONSTRAINT ck_payment_disputes_outcome CHECK (outcome IS NULL OR outcome IN ('won', 'lost', 'withdrawn'))
);
CREATE INDEX ix_payment_disputes_open ON payment_disputes (evidence_due_by) WHERE status IN ('needs_response', 'under_review');
CREATE INDEX ix_payment_disputes_trip ON payment_disputes (trip_id);
SELECT add_updated_at_trigger('payment_disputes');
-- Admin only: the API exposes dispute state through settlements.status.
REVOKE ALL ON payment_disputes FROM hermi_app;

-- Payments are a money table: the API may not write them (03 section 6.1 pattern).
REVOKE INSERT, UPDATE, DELETE ON payment_collections, settlements FROM hermi_app;
GRANT INSERT ON payment_collections TO hermi_app;
GRANT UPDATE (status, closed_at, due_on, title) ON payment_collections TO hermi_app;             -- organizer edits; the service layer narrows further
GRANT INSERT ON settlements TO hermi_app;                                                        -- manual and cash records; Stripe rows are written by the worker role
GRANT UPDATE (status, note, settled_at, last_reminded_at) ON settlements TO hermi_app;           -- confirm a manual payment; RLS limits rows to the trip
```

Events workspace seed (a pass, so the existing resolver in 03 section 7.1 needs no change beyond the upgrade check):

```sql
ALTER TABLE trip_passes DROP CONSTRAINT ck_trip_passes_plan;
ALTER TABLE trip_passes ADD CONSTRAINT ck_trip_passes_plan CHECK (plan_code IN ('trip_pass', 'group_trip_pass', 'event_workspace'));
ALTER TABLE trip_passes DROP CONSTRAINT ck_trip_passes_upgrade;
ALTER TABLE trip_passes ADD CONSTRAINT ck_trip_passes_upgrade
  CHECK (upgraded_from_id IS NULL OR plan_code IN ('group_trip_pass', 'event_workspace'));
ALTER TABLE store_transactions DROP CONSTRAINT ck_store_transactions_kind;
ALTER TABLE store_transactions ADD CONSTRAINT ck_store_transactions_kind
  CHECK (kind IN ('subscription', 'pass', 'credit_pack', 'group_payment', 'advisor_seat', 'print_order'));   -- keep values added by other packs

INSERT INTO plans (code, kind, name, rank, monthly_credits, credits_granted, credits_valid_days, duration_days, feature_flag_key, is_active, sort_order, limits) VALUES
('event_workspace', 'pass', 'Events workspace', 27, 0, 80, 90, 90, 'event_workspaces', false, 55,
 '{"active_trips_bonus":1,"routes_per_trip":3,"live_routes":2,"live_window_days":120,"live_checks_max":60,"price_alerts":2,"live_alerts":true,
   "collaborators":39,"travelers_per_trip":40,"can_invite":true,"saved_lodging_per_trip":30,"lodging_compare":4,
   "places_searches_per_day":100,"polls":true,"cost_splitting":true,"room_block_request":true,"group_payments":true,
   "hide_presentation_footer":true,
   "monthly_ceiling_micros":3600000,"daily_ceiling_micros":400000}')
ON CONFLICT (code) DO NOTHING;

INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('event_workspace_once', 'stripe', 'event_workspace', 'once', 7900, 'USD', 0, false)
ON CONFLICT (product_id) DO NOTHING;

UPDATE feature_flags SET rules = rules || '{"max_payment_minor":250000,"max_collection_minor":2500000}'::jsonb WHERE key = 'group_payments';   -- fee_bps stays 0 until P3-013 has data
INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('event_workspaces', 'Events workspace pass (up to 40 travelers), web checkout only', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
```

The `group_payments` limit key is already true for `pro` and `group_trip_pass` (Phase 2) and is true for `event_workspace`. A Stripe-paid events workspace is written to `store_transactions` as `store = 'stripe'`, `kind = 'pass'`; a succeeded collection payment is written as `kind = 'group_payment'`. Retention: `settlements` and `payment_collections` live with the trip (cascade); `store_transactions` 7 years; `payment_disputes` 7 years; `payer_token_hash` is nulled when the settlement is final.

## 5. API additions

Base `/v1`. Conventions, errors and idempotency are in [04 section 1](../phase-1-launch/04-api-spec.md). All routes below are behind the `group_payments` flag and its kill switch `provider.stripe`.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /me/stripe-connect/onboarding` | user | flag | `{ return_url, refresh_url }` to `{ url, expires_at }` | Creates the Express account on first call (`users.stripe_connect_account_id`) and returns a Stripe account link. `422 unsupported_region` where unavailable. |
| `GET /me/stripe-connect` | user | flag | to `{ ready, requirements_due: string[], country }` | Reads the cached account state; `ready` mirrors `stripe_connect_ready`. |
| `GET /trips/{trip_id}/collections` | viewer | none | to `Collection[]` | Progress per collection. |
| `POST /trips/{trip_id}/collections` | owner or named organizer | `group_payments` | `CollectionIn` with `Idempotency-Key` to 201 `Collection` | Checks Connect ready, currency, caps (D6); inserts the collection and one `pending` settlement per payer; returns the fee preview. `403 entitlement_required` (reason `group_payments`) with the `collect_payments` paywall. |
| `POST /collections/{collection_id}/quote` | organizer | none | `{ person_id }` to `FeeQuote` | The exact lines a payer will see (share, Hermi fee, processing fee, total). Pure function, no Stripe call. |
| `POST /collections/{collection_id}/close` | organizer | status `open` | to `Collection` | Sets `closed`; open balances remain tracked. |
| `POST /collections/{collection_id}/remind` | organizer | 1 per person per 48 hours | `{ person_ids? }` to 202 | Push and email through the notification service. |
| `POST /settlements/{settlement_id}/checkout` | payer (member) | status `pending` or `failed`, method `stripe` | `Idempotency-Key` to `{ checkout_url, expires_at }` | Creates the Stripe Checkout session (idempotency key `settlement:{id}:{attempt}`), stores `stripe_checkout_session_id` and `charged_minor`. |
| `GET /pay/{token}` | none (emailed token) | token valid, 60 an hour per IP | to `PayPage` | For travelers without accounts: share, fee lines, `checkout_url`. Reveals nothing beyond the trip name, organizer first name and amounts. |
| `POST /settlements/{settlement_id}/refund` | organizer | status `succeeded`, no open dispute | `{ amount?: Money, reason }` with `Idempotency-Key` to `Settlement` | Stripe refund (reverses the transfer when D1 is destination charges); updates `refunded_minor`; status `refunded` when full. |
| `GET /trips/{trip_id}/collections/{collection_id}/ledger` | organizer | none | to `{ rows, totals }` | Amounts, fees, payouts; CSV via `?format=csv`. |
| `POST /trips/{trip_id}/event-workspace/checkout` | owner | flag `event_workspaces`; web clients only (`X-Client: web`) | to `{ checkout_url }` | `403 not_available_on_ios` from the iOS client. Stripe Checkout in payment mode for `event_workspace_once`. |

```ts
type CollectionIn = {
  title: string; total: Money; split_method: "equal" | "exact" | "percent" | "shares"
  shares: { person_id: Uuid; amount?: Money; percent?: number; weight?: number }[]
  due_on?: string; fee_mode: "payer_pays" | "organizer_covers"
}
type Collection = {
  id: Uuid; trip_id: Uuid; title: string; total: Money; status: "open" | "closed" | "cancelled"; due_on: string | null
  fee_mode: "payer_pays" | "organizer_covers"
  progress: { paid: Money; waiting: Money; failed: Money; refunded: Money }
  payers: { person_id: Uuid; settlement_id: Uuid; share: Money; status: Settlement["status"]; last_reminded_at: string | null }[]
}
type FeeQuote = { share: Money; hermi_fee: Money; processing_fee: Money; total: Money; fee_mode: string; note: string }   // lines add up to total
```

Webhooks (extend `POST /webhooks/stripe`, [04 section 6](../phase-1-launch/04-api-spec.md)): `checkout.session.completed`, `payment_intent.succeeded`, `payment_intent.payment_failed`, `charge.refunded`, `charge.dispute.created`, `charge.dispute.closed`, `account.updated`, `payout.paid`, `payout.failed`. Handlers are order independent, write `webhook_events` first, and take amounts from our own `settlements` row, never from the payload alone. The fee for one payment is computed by one function, `quote_collection_fee()`, and the payer total solves `total - (pct x total + fixed) = share + hermi_fee`, rounded up to the minor unit. Example at 2.9% plus $0.30 (verify the live rate) and a 1.5% Hermi fee on a $250.00 share: Hermi fee $3.75, total $261.64, processing fee $7.89, organizer receives $250.00.

## 6. UI screens

Follows [05](../phase-1-launch/05-ui-ux-spec.md): sentence case, money in mono, no em dashes, text plus icon for status.

**Collect payments (extends 6.21 Settle up).**
- Purpose: start and follow a real-world collection. Shown only on trips with the capability and the flag on.
- Layout: "Collect payments" button in Settle up; a sheet with title, total, split, due date and fee mode; a preview row per person showing the share and fee lines; a confirmation with the Stripe sentence.
- Payer view: a card per open request with "Pay $261.64" and the fee breakdown; status chips (Waiting, Paid, Failed, Refunded, In dispute).
- States: loading skeletons; empty "No payment requests yet"; Connect not ready "Finish setup with Stripe to collect by card" with the list of what is missing and "Mark as paid instead"; region unsupported "Card payments are not available where you are yet. You can still mark payments as paid."; error "We could not start this payment. You were not charged."; offline: read only with "Waiting to sync".
- Copy rules: always "Payments are handled by Stripe. Hermi does not hold your money." (adjust to the D1 outcome). Never urgency ("pay now or lose your spot") and never a fee shown only after the pay tap.
- Accessibility: amounts read with currency; fee lines are a description list; status is text.

**Payout setup.** Stripe-hosted onboarding opens in the in-app browser with visible chrome; returning shows "Payout account ready" or the open requirements.

**Organizer collection detail.** Progress bar with text ("4 of 6 paid, $1,200 of $2,400"), per-person rows, Remind, Refund (typed amount, reason, "Stripe keeps its processing fee"), Close, Export CSV.

**Pay page (web, no account).** Trip name, organizer first name, what the payment is for, fee lines, Stripe Checkout button, and a link to the plain-language terms. No login needed, no trip details beyond the name.

**Events workspace purchase (web).** One screen: what is included (40 travelers, group tools, payments, room-block request, 80 credits, 90 days), $79, Stripe Checkout, and "Bought on the web. Works in the app." The iOS app shows the capability once active and never the price or a link to buy.

**Admin screens:** see section 8.

Events: `payout_setup_started`, `payout_setup_completed`, `payment_collection_created {member_count_bucket}`, `payment_started`, `payment_succeeded {method}`, `payment_failed {reason}`, `payment_refunded`, `dispute_opened`, `event_workspace_viewed`, `event_workspace_purchased`.

## 7. Billing

- **Stripe Connect Express.** Hermi is the platform; each organizer is an Express account created on first use. Stripe-hosted onboarding collects identity and bank details. Keys: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` (already in 02 section 7.1); add `STRIPE_CONNECT_CLIENT_ID` if OAuth is used, and a separate webhook endpoint secret for Connect events.
- **Fees.** Hermi fee starts at 0 (07). The 1.5% in the revenue case turns on by editing `feature_flags.rules.fee_bps` to 150; the value is copied to each new `payment_collections.application_fee_bps` so an old collection never changes price. The fee is shown before payment and is never a percentage of a digital purchase.
- **Events workspace.** Stripe Checkout, one-time price `event_workspace_once`, Stripe Tax for sales tax and VAT (verify thresholds), receipt by Stripe email. The webhook writes `store_transactions` (`store = 'stripe'`, `kind = 'pass'`) and binds the `trip_passes` row, using the same idempotent pattern as RevenueCat passes.
- **Platform costs and liability.** Budget for Stripe Connect account and payout fees (verify), dispute fees, and loss on disputes under D1. Keep a platform reserve in the plan (amount decided with counsel).
- **Refunds.** Payments: organizer initiated, see P1-5. Events workspace: finance refund on the web within 14 days if unused (owner above $100, 08 section 3).

## 8. Admin additions

Extends [08 section 6.9 (full spec)](../reference-full-spec/08-admin-control-center.md) (Group payments and settlements), which is read only until this pack ships.

- **Screen: Group payments.** Per trip: collections, settlements with live Stripe state, payout status, fees, open disputes (reason, evidence due date, evidence status).
- **Actions:** open in Stripe (deep link), refund (finance up to $100, owner above, typed confirmation), attach evidence notes (finance), mark a settlement settled outside the app (reason), resend a payment request, freeze a collection (engineer or owner, reason).
- **Guardrails:** a scan blocks any settlement tagged as paying for a digital Hermi feature; dispute due dates alert 3 days ahead; amounts above $500 need the owner; the console never shows card or bank details, only Stripe ids and last four where Stripe returns them.
- **Events screen:** workspaces sold, by trip and owner, with refund action (finance).
- **Kill switches:** `provider.stripe` (existing) and a new `group_payments.collect` switch that disables new collections while leaving reads and manual marking.
- **Alerts:** dispute due within 3 days (existing), collection failure rate above 10% in an hour, reconcile mismatch above zero (page), Stripe webhook backlog older than 10 minutes (page).
- **Finance reports:** add collected volume, Hermi fee revenue net of Stripe cost, refunds, disputes won and lost, events sold.

## 9. Legal and compliance

This pack is the most legally exposed lane in Phase 3. Nothing is built until P3-001 returns a written memo.

1. **Money transmission.** Counsel confirms whether Connect with destination charges (or direct charges) keeps Hermi outside money transmitter licensing in every state where users live, relying on Stripe as the licensed party and the agent-of-the-payee exemption where it applies. The answer may depend on D1.
2. **Terms.** Organizer terms (the organizer is the payee and responsible to travelers for what the money is for), payer terms, refund rules, a statement that Hermi does not guarantee any trip, and Stripe's Connected Account Agreement acceptance.
3. **Refunds, chargebacks, disputes.** Who pays dispute fees and lost disputes, how Hermi recovers from an organizer with a negative balance, and how long refunds are allowed.
4. **Tax.** Stripe issues tax forms for Express accounts where required (verify); counsel and an accountant confirm Hermi's own reporting and whether the events workspace needs sales tax collection in more states.
5. **Sanctions and fraud.** Stripe screens connected accounts; add Hermi velocity caps (D6), a block on collections from suspended users, and a review queue for first collections above a threshold.
6. **Stripe platform review.** Stripe must approve the use case; describe it accurately (group trip cost sharing) and do not describe Hermi as a marketplace that sells trips.
7. **Apple.** Real-world trip costs are outside In-App Purchase (3.1.3(e) as quoted in 07 section 10.3; re-read on the submission day). The events workspace is a digital feature: web only, no price or purchase link in the iOS app, reviewer notes explain it. If Apple's link-out rules change ([09 risk 7](../context/business-plan/09-revenue-expansion.md)), revisit.
8. **Privacy.** We store Stripe ids, amounts and names from the trip's people, never card data. Payer emails for people without accounts are kept only until the settlement is final, then nulled. Add Stripe to the processor list already in the privacy policy.
9. **Consumer law.** Show price, fees and refund terms before payment; keep the sentence "Payments are handled by Stripe" on every payment page; no dark patterns.

## 10. Analytics

Events in section 6 go to PostHog (no ad SDKs). First-party revenue reporting adds: collections opened, collected volume by currency, fee revenue, average payment, time to first payment, share of trips with a collection (target 2% of trips, the 09 assumption), refund and dispute rates (alert above 1% of volume), events sold, and events per Group Trip Pass upgrade. These replace the 09 assumptions in the admin revenue view (P3-013).

## 11. Tests

- Unit: `quote_collection_fee()` property tests (lines always sum to the total, rounding up, zero fee mode, all fee modes); share splits sum to the total for all four methods with leftover cents.
- Integration with Stripe fakes: create collection, checkout, `payment_intent.succeeded`, refund, dispute opened and closed both ways, `account.updated`, payout failed. Every webhook handler is idempotent (replay each event twice) and order independent (shuffle).
- Entitlement: a trip without `group_payments` is refused with the paywall body; flag off; kill switch on; region unsupported; currency unsupported; caps enforced.
- Tenancy: a member of another trip cannot read or pay a collection (cross-tenant leak test includes both tables); pay-link tokens work once per settlement and expire.
- Policy: a settlement whose description names a digital Hermi feature is blocked; the iOS client cannot reach `/event-workspace/checkout`.
- Reconcile job: seeded mismatch raises the alert.
- E2E (Playwright, Stripe test mode): organizer onboarding stub, collection, two payers pay, one refund.

## 12. Tickets

| ID | Title | Size | Needs | Who |
|---|---|---|---|---|
| P3-001 | Legal gate: written counsel memo on money transmission, D1 charge type, terms, tax, sanctions, Stripe platform approval | M | none | Lawyer, founder |
| P3-002 | Stripe platform setup: Connect enabled, webhook endpoints (platform and Connect), `providers/stripe.py` with the charge-type switch, test mode in staging | M | P3-001 | Engineer |
| P3-003 | Organizer onboarding: onboarding link, `account.updated`, `users.stripe_connect_*`, region and currency checks | M | P3-002 | Engineer |
| P3-004 | Collections API and schema migration (4.2): create, read, close, per-payer settlements, split rounding, caps | L | P3-002 | Engineer |
| P3-005 | Payments: Checkout session per settlement, `quote_collection_fee()`, pay page for travelers without accounts, emailed tokens | L | P3-004 | Engineer |
| P3-006 | Stripe webhook handlers for payments, refunds, payouts, idempotency and order independence | L | P3-005 | Engineer |
| P3-007 | Refunds and disputes: organizer refund, `payment_disputes`, status transitions, organizer notifications | M | P3-006 | Engineer |
| P3-008 | Settle up UI: Collect payments sheet, collection detail, payer cards, payout setup, states and copy | L | P3-005 | Engineer |
| P3-009 | Gate and paywall: `group_payments` limit check, `collect_payments` paywall, flag and kill switches, reminders job | M | P3-004 | Engineer |
| P3-010 | Admin group payments and disputes screens, guardrails, alerts (08 section 6.9) | M | P3-006 | Engineer |
| P3-011 | Events workspace: plan seed, upgrade check, web checkout, webhook binding of the pass, Stripe Tax | M | P3-002 | Engineer |
| P3-012 | Events workspace UI (web purchase screen, in-app active state, 40-traveler limits and copy) | M | P3-011 | Engineer |
| P3-013 | Reconcile job, finance report lines, measured collected volume replacing the 09 assumption | M | P3-006 | Engineer, bookkeeper |
| P3-014 | Tests and launch: full test list, closed beta with 10 organizers, counsel sign-off on copy, support macros for refunds and disputes | M | P3-007, P3-010, P3-012 | Founder, support contractor |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Counsel says a licence or registration is needed | Medium | High | Gate in P3-001; fall back to "Mark as paid" and ship only the events workspace |
| D1 mismatch: destination charges leave disputes and refunds with Hermi | Medium | High | Decide in P3-001; caps (D6); reserve; direct charges as the alternative |
| Disputes and refunds overwhelm a solo founder | Medium | Medium | Caps, organizer-first dispute handling, support contractor, macros |
| Fraud: a fake organizer collects and vanishes | Low | High | Stripe onboarding checks, first-collection review, velocity caps, freeze action |
| Stripe rejects the use case | Low | High | Describe accurately, apply early in P3-002, keep manual fallback |
| Low volume (only distribution-bound events) | Medium | Medium | The lane drives Group Trip Pass sales; revenue case is small ($56.3k base year 5) |
| Fee read as a hidden charge | Low | Medium | Lines shown before any tap, plain copy, test in usability sessions |
| Apple objects to the events workspace link | Low | Medium | Web only, no in-app price or link, reviewer notes |
