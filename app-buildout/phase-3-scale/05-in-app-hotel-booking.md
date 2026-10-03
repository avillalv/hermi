# Pack 05: In-app hotel booking (LiteAPI)

Part of [Phase 3: scale](README.md). Tickets P3-058 to P3-070. Written 2026-09-30.

| | |
|---|---|
| Feature flag | `inapp_hotel_booking` (created by this pack, off) |
| Needs | A lawyer before building (seller-of-travel position, consumer law, terms of sale). A support process and probably a support hire, because Hermi then owns every hotel problem. A contractor engineer is sensible; this is the highest-effort pack. No funding if Nuitee stays merchant of record. |
| Builds on | Phase 1: lodging shortlist, stay comparison, affiliate system and disclosure component, itinerary, email, admin console. Phase 2: [concierge lane](../phase-2-growth/07-concierge-lane.md) and [direct affiliate programs](../phase-2-growth/08-direct-affiliate-programs.md) (the affiliate options this sits beside). |
| Source names | Phase 1 files call this "year 2 and later" and "Phase 4", ticket WF-110. Spec of record: [07 section 11.1 (full spec)](../reference-full-spec/07-monetization-spec.md), [08-affiliate-revenue.md section 13.4](../context/business-plan/08-affiliate-revenue.md). |

## 1. Goal and revenue case

**Goal.** Hotel search and booking inside Hermi through LiteAPI (Nuitee), a self-serve REST API with 2M+ hotels (reported, verify). Hermi sets a margin per search, Nuitee acts as merchant of record through its payment SDK so card data never touches Hermi, and payouts are weekly for confirmed bookings. The "Book in Hermi" option sits beside the affiliate options and never replaces or outranks them (09 section 3.3).

**Pricing to the user.** The displayed rate is the supplier net rate plus Hermi's margin, 5 to 15% (reported, verify). Bedbank rates are often priced to match public rates, so the usable margin is probably the low end (inference).

**Revenue per booking (09 section 3.3).** A $600 stay at 8% is $48 gross. After card fees, cancellations, chargebacks and support the net is about $15 to $60; the model uses $30. Hermi also loses the affiliate commission it would have earned on the same stay (about $10 assumed), so incremental revenue is $20 per booking.

**Revenue (base case).** Bookings = trips x attach (3% to 5% of trips, assumption) x $20 incremental.

| | Y3 | Y4 | Y5 |
|---|---|---|---|
| Base trips | 36,000 (half year) | 60,000 | 90,000 |
| Attach | 3% | 3% | 4% |
| Bookings | 540 | 1,800 | 3,600 |
| Revenue at $20 | $10.8k | $36.0k | $72.0k |

Ambitious upside (09 section 6.4): $12.0k, $96.0k, $192.0k, $400.0k in years 2 to 5. Conservative: zero. **This lane is not in the README scenario totals** (base year 5 is $572.5k without it, about $698.5k with concierge and this lane), because nothing here is tested.

**Gross versus incremental.** At year 5 base, 3,600 bookings of about $600 is $2.16M of gross bookings value passing through a partner; gross margin at 8% would be $173k, but the plan counts only the $20 incremental after costs and the lost affiliate income. Do not report the gross figure as revenue.

**Go or no-go gate (assumptions to tune, from 08-affiliate-revenue.md section 13.4).** Build only when all four hold:

1. Click data over at least 12 months shows strong booking intent. Proposed thresholds: at least 20% of dated trips reach the stay comparison, at least 10% of dated trips produce a lodging outbound click, and at least 1,500 lodging outbound clicks a month.
2. A support process exists for "I arrived and there is no booking" with a named person, a runbook and a 24-hour emergency path (P3-068).
3. Counsel has confirmed the registration and consumer-law position in writing (P3-069).
4. LiteAPI sandbox testing confirms margin caps, parity rules, payout currencies and minimums (08-affiliate-revenue.md section 13.9 item 4).

**What would break the case.** Rate parity leaves no usable margin, support cost per booking exceeds the margin, or users do not trust an unknown seller. Run the gate check before any engineering.

## 2. Design decisions

| # | Decision | Default and reason |
|---|---|---|
| D1 | Merchant of record | Nuitee (LiteAPI), through its payment SDK in a hosted web view. Hermi never sees card numbers (PCI scope stays at the lightest level). Terms and cancellation policy show Nuitee as seller of record before payment. Hermi as merchant of record on net rates is rejected for now. |
| D2 | Uniform margin, commission-blind order | One `margin_bps` per search, the same for every hotel, taken from configuration. Results are sorted only by the user's choice (price, guest rating, distance) and the order is explained. Margin cannot differ by hotel, so nothing can be ranked by it, and a test proves the order is independent of margin. |
| D3 | Sits beside affiliate options | "Book in Hermi" is one option in the same list as the partner links, sorted by the same user-chosen criteria, and the affiliate links and their disclosure stay. Never hidden, never placed first by default. |
| D4 | No price claims we cannot prove | The server never fetches Airbnb, Vrbo or Booking.com pages, so Hermi cannot claim to beat their prices. Show the total price and policy; no "best price" or "lowest price" wording. |
| D5 | Total price honesty | Display the full total for the stay including mandatory taxes and fees known to the supplier; list resort fees or pay-at-property charges separately and clearly. |
| D6 | No packages | Hotel only. No dynamic packaging with flights (package-travel rules, skipped in 09 section 3.9). |
| D7 | Allow-list launch | The flag first opens to an allow-list of users and destinations, then to everyone. |
| D8 | Kill switch | `provider.liteapi` disables search and booking at once; existing bookings stay visible and cancellable. |

## 3. User stories and acceptance criteria

**H-1. Search in the trip.**
As a traveler planning stays, I want to search hotels for my dates and party inside the trip, so that I do not start over elsewhere.
- Search by destination (from the trip), dates and party (adults, children with ages, rooms); defaults come from the trip.
- Results show photo, name, guest rating, distance to the trip center, total price for the stay in the trip currency, cancellation label (Free cancellation until {date} or Non-refundable), and a line "Sorted by {price}. Hermi's fee does not affect the order."
- Sort options: price, rating, distance. No default that depends on margin.

**H-2. Compare beside other options.**
As a traveler, I want to see "Book in Hermi" next to the partner links, so that I can choose.
- On the stay comparison and shortlist the option appears alongside affiliate offers with the same disclosure pattern; affiliate options remain. Choosing either is tracked separately.

**H-3. See the full terms before paying.**
As a buyer, I want to know the total, what is included, who sells it and what happens if I cancel.
- The hotel page and checkout show total price with taxes and fees, pay-at-property charges, cancellation policy with dates and amounts, bed type, board basis, the statement "Sold by Nuitee (LiteAPI), the merchant of record. Hermi arranges the booking and earns a fee.", and the terms link.
- The price is prebooked (locked) and shown with a countdown only as a factual expiry time, not as pressure ("Price held until 14:32").

**H-4. Pay and get a confirmation.**
As a buyer, I want to pay securely and receive proof, so that I can travel with it.
- Payment runs in the LiteAPI payment SDK hosted page; on success the server books through the API with the prebook id and the transaction id.
- The confirmation shows hotel, dates, guests, total, confirmation number (supplier reference), voucher download and the property's contact details; an email is sent; an item is added to the itinerary and the stay is marked `booked` in `lodging_options`.
- If booking fails after payment the buyer sees what happened and is refunded by the merchant of record; the order is never left in an ambiguous state (reconcile job P3-066).

**H-5. Cancel or change.**
As a buyer, I want to cancel within the policy, so that I am not stuck.
- "Cancel booking" shows the exact refund before confirming, based on the policy stored at booking time; cancellation calls the API and updates status; changes of dates or guests are "cancel and rebook" unless the API offers amendments (verify).
- Non-refundable bookings show no cancel button and explain why.

**H-6. Get help.**
As a buyer, I want a person when something is wrong, so that I am not stranded.
- Every booking page and confirmation email has a "Problem with this booking" link to a priority support form and, for stays starting within 24 hours, an emergency contact path (P3-068).
- "I arrived and there is no booking" is a defined runbook (section 8).

**H-7. Privacy and data.**
As a buyer, I want guest details used only to make the booking.
- Guest names, email and phone go only to the supplier and merchant of record as needed; Hermi keeps them for support and scrubs them 90 days after check-out (section 4).

## 4. Database additions

### 4.1 What exists and what this pack adds

The full 03 defines no table for this lane; 07 section 11.1 (full spec) names the new table (`hotel_bookings`, "migration added then"), and Phase 1 03 section 14 lists the additions: `hotel_bookings`, `lodging_options.added_via` value `liteapi`, the flag `inapp_hotel_booking` and the env var `LITEAPI_KEY` (02 section 7.1, empty until used). Reused as they are: `lodging_options` (Phase 1 03 section 5.8; the confirmed stay is stored there with status `booked`), `lodging_status`, the affiliate and disclosure components, `provider_calls`, `webhook_events`, and the itinerary. Nothing is seeded before this pack.

### 4.2 New in this pack

```sql
-- Migration p3_hotel_booking. New tables carry their own grants and policies (Phase 1 03 section 10).

CREATE TABLE hotel_bookings (
  id                      uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id                 uuid REFERENCES users (id) ON DELETE SET NULL,
  trip_id                 uuid REFERENCES trips (id) ON DELETE SET NULL,
  lodging_id              uuid,                                              -- the lodging_options row created on confirmation
  supplier                text NOT NULL DEFAULT 'liteapi',
  supplier_hotel_id       text NOT NULL,
  supplier_prebook_id     text,
  supplier_booking_id     text,                                              -- the supplier's booking id
  confirmation_ref        text,                                              -- reference shown to the guest and the property
  hotel_name              text NOT NULL,
  hotel_address           text,
  hotel_phone             text,
  lat                     double precision,
  lon                     double precision,
  check_in                date NOT NULL,
  check_out               date NOT NULL,
  rooms                   smallint NOT NULL DEFAULT 1 CHECK (rooms BETWEEN 1 AND 8),
  guests                  jsonb NOT NULL,                                    -- lead guest and occupancy; personal data, scrubbed 90 days after check-out
  currency                currency_code NOT NULL,
  net_minor               bigint NOT NULL CHECK (net_minor >= 0),            -- supplier net rate
  margin_bps              integer NOT NULL CHECK (margin_bps BETWEEN 0 AND 3000),
  margin_minor            bigint NOT NULL CHECK (margin_minor >= 0),         -- Hermi's gross margin at booking time
  total_minor             bigint NOT NULL CHECK (total_minor >= net_minor),  -- what the guest paid, as shown
  pay_at_property_minor   bigint NOT NULL DEFAULT 0 CHECK (pay_at_property_minor >= 0),   -- fees due at the hotel, shown separately
  cancellation_policy     jsonb NOT NULL,                                    -- snapshot shown at booking: tiers with dates and amounts
  refundable_until        timestamptz,
  offer_snapshot          jsonb NOT NULL,                                    -- room, board, rate name, price lines the guest saw
  terms_version           text NOT NULL,
  terms_accepted_at       timestamptz NOT NULL,
  status                  text NOT NULL DEFAULT 'prebooked',
  commission_status       text NOT NULL DEFAULT 'pending',
  payout_ref              text,
  payout_paid_on          date,
  payout_minor            bigint CHECK (payout_minor IS NULL OR payout_minor >= 0),
  confirmed_at            timestamptz,
  cancelled_at            timestamptz,
  completed_at            timestamptz,                                       -- check-out date passed; revenue recognized here (07 section 11.1)
  voucher_url             text,
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_hotel_bookings_lodging FOREIGN KEY (lodging_id, trip_id) REFERENCES lodging_options (id, trip_id) ON DELETE SET NULL (lodging_id),
  CONSTRAINT ck_hotel_bookings_dates CHECK (check_out > check_in),
  CONSTRAINT ck_hotel_bookings_total CHECK (total_minor = net_minor + margin_minor),
  CONSTRAINT ck_hotel_bookings_status CHECK (status IN ('prebooked', 'payment_pending', 'confirmed', 'failed', 'cancelled', 'completed', 'no_show', 'disputed')),
  CONSTRAINT ck_hotel_bookings_commission CHECK (commission_status IN ('pending', 'confirmed', 'paid', 'cancelled', 'clawed_back')),
  CONSTRAINT uq_hotel_bookings_supplier UNIQUE (supplier, supplier_booking_id)
);
CREATE INDEX ix_hotel_bookings_user ON hotel_bookings (user_id, created_at DESC);
CREATE INDEX ix_hotel_bookings_trip ON hotel_bookings (trip_id) WHERE trip_id IS NOT NULL;
CREATE INDEX ix_hotel_bookings_status ON hotel_bookings (status, check_in) WHERE status IN ('prebooked', 'payment_pending', 'confirmed');
CREATE INDEX ix_hotel_bookings_payout ON hotel_bookings (commission_status, completed_at) WHERE commission_status IN ('pending', 'confirmed');
SELECT add_updated_at_trigger('hotel_bookings');

CREATE TABLE hotel_booking_events (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  hotel_booking_id  uuid NOT NULL REFERENCES hotel_bookings (id) ON DELETE CASCADE,
  from_status       text,
  to_status         text NOT NULL,
  source            text NOT NULL,                                  -- 'api', 'supplier', 'job', 'admin'
  detail            jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_hotel_booking_events_booking ON hotel_booking_events (hotel_booking_id, created_at);

-- Row-level security: the buyer sees their own bookings; trip members see the confirmed stay through lodging_options, not the row.
ALTER TABLE hotel_bookings ENABLE ROW LEVEL SECURITY;
CREATE POLICY hotel_bookings_select ON hotel_bookings FOR SELECT USING (user_id = (SELECT app_user_id()));
REVOKE INSERT, UPDATE, DELETE ON hotel_bookings FROM hermi_app;       -- written only by the booking service (worker role)
REVOKE ALL ON hotel_booking_events FROM hermi_app;

ALTER TABLE lodging_options DROP CONSTRAINT ck_lodging_options_added_via;
ALTER TABLE lodging_options ADD CONSTRAINT ck_lodging_options_added_via
  CHECK (added_via IN ('bookmarklet', 'paste', 'partner_search', 'agent', 'manual', 'import', 'liteapi'));   -- 'liteapi' is the value Phase 1 03 section 14 names
ALTER TABLE webhook_events DROP CONSTRAINT ck_webhook_events_provider;
ALTER TABLE webhook_events ADD CONSTRAINT ck_webhook_events_provider   -- keep values other packs add
  CHECK (provider IN ('revenuecat', 'apple', 'stripe', 'travelpayouts', 'viator', 'stay22', 'impact', 'print', 'liteapi'));
ALTER TABLE lodging_options ADD COLUMN hotel_booking_id uuid REFERENCES hotel_bookings (id) ON DELETE SET NULL;

-- Kill switch and flag rules.
INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('inapp_hotel_booking', 'In-app hotel booking through LiteAPI', false, 100,
 '{"margin_bps":800,"max_margin_bps":1500,"allow_list":[],"countries":["US"],"max_total_minor":500000}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO kill_switches (key, description) VALUES ('provider.liteapi', 'Disables hotel search and booking through LiteAPI')
ON CONFLICT (key) DO NOTHING;
```

The `kill_switches` insert uses the columns of 03 section 5.20 (`key`, `description`; `engaged` defaults to false). `margin_bps` of 800 is the 8% example from 09 and is a configuration default, not a recommendation. Retention: `hotel_bookings` 7 years for financial fields (with `guests` nulled 90 days after check-out and the row anonymized on account deletion, as for `print_orders`); `hotel_booking_events` with the booking; search results are not stored beyond a short cache (section 5).

## 5. API additions

Base `/v1`, behind the `inapp_hotel_booking` flag and kill switch `provider.liteapi`. The LiteAPI key is held server side (`LITEAPI_KEY`); the client never calls the supplier.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/hotel-searches` | editor | flag, allow-list, 30 an hour per user | `HotelSearchIn` to 201 `HotelSearch` | Queries LiteAPI, applies the uniform `margin_bps`, caches results for 10 minutes by normalized key, logs `provider_calls`. No credits. `503 provider_unavailable` when down. |
| `GET /hotel-searches/{search_id}` | requester | none | `?sort=price\|rating\|distance&cursor` to `Page<HotelResult>` | Sorting is done by the server on the chosen key only; the response includes `sorted_by` and the commission-blind statement. |
| `GET /hotel-searches/{search_id}/hotels/{hotel_id}` | requester | none | to `HotelDetail` with `offers: HotelOffer[]` | Photos, amenities, policies, offers with total price lines, pay-at-property items, cancellation policy. |
| `POST /hotel-offers/{offer_id}/prebook` | requester | 10 an hour | `{ guests: GuestIn, rooms }` with `Idempotency-Key` to `{ booking_id, total: Money, price_lines, expires_at, payment: { sdk_config } }` | Calls prebook (price lock), creates `hotel_bookings` (`prebooked`) and the terms snapshot. `409 offer_changed` if the price moved (returns the new total for re-consent). |
| `POST /hotel-bookings/{booking_id}/confirm` | requester | status `prebooked` | `{ transaction_id, terms_accepted: true }` with `Idempotency-Key` to `HotelBooking` | Books with the prebook id and the merchant-of-record transaction id, stores the supplier id, creates the `lodging_options` row, itinerary item, email and voucher job. On supplier failure after payment: status `failed`, alert, refund path (P3-066). |
| `GET /hotel-bookings` | user | none | `?limit&cursor` to `Page<HotelBooking>` | |
| `GET /hotel-bookings/{id}` | requester | none | to `HotelBooking` | Includes policy snapshot, refund preview, help links. |
| `POST /hotel-bookings/{id}/cancel` | requester | status `confirmed`, before `refundable_until` or explicit non-refundable acknowledgment | `{ confirm_refund: Money }` with `Idempotency-Key` to `HotelBooking` | Calls supplier cancel, records the refund amount returned; `409 state_conflict` when not cancellable; `422 refund_changed` if the amount differs from the preview. |
| `GET /hotel-bookings/{id}/voucher` | requester | status `confirmed` | to 302 signed URL | Supplier voucher or our generated PDF. |
| `POST /hotel-bookings/{id}/problem` | requester | none | `{ kind, description }` to 201 | Priority support ticket linked to the booking; stays starting within 24 hours page the on-call. |
| `POST /webhooks/liteapi` | supplier | signature or shared secret (verify what LiteAPI offers) | status events | Stored in `webhook_events` (the migration adds `'liteapi'` to the provider check); a polling fallback reconciles any missed event. |

```ts
type HotelSearchIn = { destination?: string; lat?: number; lon?: number; check_in: string; check_out: string
  adults: number; children_ages?: number[]; rooms: number; currency?: string }
type HotelResult = { hotel_id: string; name: string; photo_url: string | null; rating: number | null; review_count: number | null
  distance_km: number | null; lat: number; lon: number; from_total: Money; refundable: boolean; free_cancellation_until: string | null }
type HotelOffer = { offer_id: string; room: string; board: string; total: Money; price_lines: { label: string; amount: Money }[]
  pay_at_property: { label: string; amount: Money }[]; cancellation: { label: string; tiers: { until: string; refund: Money }[] }
  merchant_of_record: "Nuitee (LiteAPI)"; margin_disclosed: true }
type HotelBooking = { id: Uuid; trip_id: Uuid | null; hotel_name: string; check_in: string; check_out: string
  status: "prebooked" | "payment_pending" | "confirmed" | "failed" | "cancelled" | "completed" | "no_show" | "disputed"
  total: Money; confirmation_ref: string | null; refundable_until: string | null; voucher_available: boolean; help_url: string }
```

Jobs: `poll_hotel_bookings` (reconcile status with the supplier every 15 minutes for bookings within 7 days of check-in, hourly otherwise, and for any `payment_pending` older than 10 minutes), `complete_hotel_bookings` (set `completed` after check-out and recognize revenue), `import_liteapi_commissions` (weekly, match payouts to bookings, set `commission_status` and `payout_ref`), `scrub_hotel_guests` (nightly, 90 days after check-out), `send_booking_reminders` (check-in minus 3 days, transactional, with the property's contact details).

## 6. UI screens

Follows [05](../phase-1-launch/05-ui-ux-spec.md). The hosted payment page opens in the in-app browser with visible chrome.

**Stay comparison (extends 6.11).** Purpose: one place to choose. A quiet option "Search and book in Hermi" sits beside the partner options with the standard disclosure pattern, and the existing list explains its sort. States: flag off or country unavailable, the option is absent; LiteAPI down "Hotel booking in Hermi is unavailable right now. Partner links still work."

**Hotel search sheet and results.** Dates and party prefilled from the trip; results list with map toggle, sort menu (Price, Rating, Distance) and the line "Sorted by price. Hermi's fee does not affect the order." Filters: free cancellation, rating, price range, distance. Skeleton loading; empty "No hotels found for these dates. Try other dates or another area."; error with retry; offline disabled.

**Hotel page.** Photo carousel, name, rating, address and map, amenities, room and rate options with the full total, taxes and fees lines, pay-at-property charges under "Pay at the hotel", cancellation policy with dates, who sells it, and [Continue]. Factual expiry only after prebook ("Price held until 14:32").

**Checkout.** Guest details (lead guest name, email, phone), special requests (not guaranteed), terms and cancellation acknowledgement checkbox, total, the hosted payment page, and a clear [Book] only after payment succeeds. Copy: "Nuitee (LiteAPI) sells this room and processes your payment. Hermi arranges the booking and earns a fee from the price shown. The fee does not change the order of results." Failure states explain whether any money moved.

**Confirmation and My bookings.** Confirmation number, hotel contacts, voucher, add to calendar, cancel (with refund preview), "Problem with this booking". My bookings lists upcoming, past and cancelled. Booking appears in the trip's Stays with a "Booked in Hermi" chip and in the itinerary.

**Cancel sheet.** Shows the exact refund and date, asks for confirmation, then the result with the refund timeline from the supplier.

Accessibility: prices read with currency and units ("total for 4 nights"); policy tiers are a list with dates; status is text; focus returns to the booking after the payment view closes. Events: `hotel_search_started`, `hotel_results_viewed {sort}`, `hotel_offer_viewed`, `hotel_prebook_started`, `hotel_booking_confirmed {nights_bucket, refundable}`, `hotel_booking_failed {stage}`, `hotel_booking_cancelled`, `hotel_problem_reported`, `book_in_hermi_chosen` (compare with `partner_link_clicked` in the same context).

## 7. Billing

- **Payments.** Collected and processed by Nuitee as merchant of record through the LiteAPI payment SDK; Hermi does not use Stripe for this lane and holds no card data. Confirm in the sandbox how the payment transaction id is returned and how refunds flow (open item).
- **Revenue.** Margin per search, paid weekly by Nuitee for confirmed bookings (reported, verify). Hermi records `margin_minor` at booking and `commission_status` through payout; revenue is recognized at check-out (07 section 11.1); cancelled bookings earn nothing; clawbacks set `clawed_back`.
- **Refunds.** Follow the rate's cancellation policy and the merchant of record's process; Hermi support can ask Nuitee for exceptions and may issue goodwill credit only as an admin action outside this flow (never automatic).
- **Currency.** Show the trip currency with the conversion shown; bookings are charged as the supplier quotes (verify which currencies Nuitee charges).
- **No cashback and no credits.** This lane does not pay or credit users (08-affiliate-revenue.md section 13.6).
- **Tax.** Hotel taxes are handled in the supplier rate and by the merchant of record; Hermi's fee treatment for sales tax or VAT is confirmed with the accountant (verify). No Stripe Tax needed unless a separate service fee is ever charged, which this design avoids.

## 8. Admin additions

New screen and support tooling; extends [08](../phase-1-launch/08-admin-control-center.md) (Money group).

- **Hotel bookings.** List by status, check-in date, supplier, destination, margin, commission status; detail with timeline (`hotel_booking_events`), guest details (masked, audited reveal), supplier reference, policy snapshot, refund amounts, payout reference.
- **Actions.** Re-check status with the supplier (support), cancel on the guest's behalf within policy (support), request a supplier exception (support), mark a payout received (finance), open in the supplier dashboard (deep link), create a goodwill credit note record (owner only, reason).
- **Runbook: "I arrived and there is no booking".** (1) Open the booking, check supplier status live. (2) Phone or message the property with the confirmation reference from the supplier; ask LiteAPI support in parallel. (3) If not resolved within 30 minutes, rebook an equivalent or better room through the supplier or a partner at the guest's option and recover cost from the supplier or as a goodwill cost. (4) Refund through the merchant of record. (5) Record the incident and the supplier in the provider health notes; three incidents in a month with one supplier pages the owner. Target: stays within 24 hours get a human reply within 1 hour (assumption; needs a support process, P3-068).
- **Finance.** Margin by month, payout lag, cancellations, clawbacks, revenue recognized at check-out, support cost per booking.
- **Alerts.** Booking `failed` after payment (page), `payment_pending` older than 10 minutes, supplier API error rate above 5% for 10 minutes, price changed at prebook above 3% of searches (rate quality), refund rate above 15%, payout overdue more than 14 days (notify), problem reports above 2% of bookings (page).
- **Kill switch and flag.** `provider.liteapi` and `inapp_hotel_booking`, plus the `allow_list` rule for staged rollout; an engineer can set the margin within `max_margin_bps`, the owner changes the cap.

## 9. Legal and compliance

1. **Seller of travel.** As a seller rather than a referrer, Hermi probably needs seller-of-travel registration in some states and must follow consumer-protection and refund rules (inference; counsel to confirm). California, Florida, Hawaii, Washington and Iowa regulate sellers of travel ([10 section 3.8 (full spec)](../reference-full-spec/10-quality-security-launch.md)). Do not launch in a state until counsel confirms the position; the flag's `countries` rule and a per-state block list enforce it.
2. **Merchant of record.** Nuitee is the seller and processes the payment; Hermi's terms of sale say it arranges the booking and earns a fee. Get Nuitee's API and reseller terms reviewed, including liability for supplier failure, rate parity obligations, and permitted marketing.
3. **Price display and fees.** Show the total price including mandatory fees; list pay-at-property charges clearly. The FTC rule on unfair or deceptive fees covers short-term lodging (verify scope and effective date with counsel). EU and UK price-transparency and "drip pricing" rules apply to European users.
4. **No ranking by margin.** Uniform margin, user-chosen sort, statement of the sort basis (EU Omnibus and the plan's non-negotiable rule 2). The ordering test in section 11 guards it.
5. **Disclosure.** The fee is disclosed at search, at checkout and in confirmation; the affiliate commission sentence is unchanged on partner links.
6. **Privacy.** Guest data goes to Nuitee and the property as needed to fulfil the booking; list Nuitee as a processor (or controller for its own use, per its terms), update the privacy policy and the App Privacy label answers if purchases are now collected in the app; scrub guest data 90 days after check-out.
7. **Consumer rights.** Show cancellation terms before payment; store a snapshot of what was shown; state that hotel stays have no statutory withdrawal period in many jurisdictions but do follow the rate's policy (verify per country).
8. **Apple.** A physical service consumed outside the app (Guideline 3.1.3(e)); payment happens in the supplier's hosted page; no digital feature is unlocked; describe the flow in reviewer notes (re-read the guideline on submission).
9. **Accessibility and security.** Payment page in the in-app browser with visible chrome; no card data handled by Hermi; SSRF and input controls on any supplier-provided URL (photos) through the existing checks.
10. **Insurance.** No insurance sales; the existing insurance referral rules are unchanged.

## 10. Analytics

Events in section 6. Metrics: search-to-offer, offer-to-prebook, prebook-to-confirmed conversion, booking failure rate after payment (target under 0.5%), cancellation rate, average nights and value, average margin per booking, net contribution after support cost (target at or above $20 incremental), attach rate (share of trips with a Hermi hotel booking, base 3% to 4%), affiliate click share before and after launch (cannibalization), support contacts per 100 bookings, "no booking at arrival" incidents (target zero), payout lag days. The decision to continue after the first 200 bookings: incremental contribution per booking at or above $10 and incidents under 1 per 200; otherwise stop and keep affiliate links.

## 11. Tests

- **Sandbox end to end.** Search, prebook, pay in the SDK sandbox, confirm, voucher, cancel, refund, using the LiteAPI sandbox; run nightly in staging.
- **Ordering.** For a fixed result set, changing `margin_bps` or per-hotel net rates never changes the order under each sort; sorting ties break by a deterministic key that is not price-minus-net; the statement text is present.
- **Uniform margin.** A property test asserts every result in a search has the same `margin_bps`.
- **Price integrity.** Total equals net plus margin; prebook price change returns `409 offer_changed` and requires re-consent; displayed total equals the amount the merchant of record charges (fake SDK).
- **Failure handling.** Booking failure after payment sets `failed`, raises the page alert and is recoverable by the reconcile job; duplicate confirm calls are idempotent; supplier timeouts do not double book.
- **Cancellation.** Refund preview equals the policy snapshot at booking time; cancellation after the deadline is refused unless acknowledged; status sync matches the supplier.
- **Privacy and tenancy.** A user cannot read another's bookings (cross-tenant test includes `hotel_bookings`); guests are scrubbed on schedule; account deletion anonymizes the row.
- **Affiliate neutrality.** With the lane on, affiliate offers still render with disclosure in the same context; click tracking for both is recorded separately.
- **Kill switch.** `provider.liteapi` on returns `503 feature_disabled` for search and prebook, while bookings and cancellations remain available.
- **Chaos.** Supplier 429, 5xx and timeouts behave per the retry classes; breaker opens on repeated failure (WF-023 pattern).

## 12. Tickets

| ID | Title | Size | Needs | Who |
|---|---|---|---|---|
| P3-058 | Gate review: click-data analysis against the four thresholds, LiteAPI sandbox account, margin cap and parity answers, go or no-go memo | M | Phase 1 and 2 click data | Founder |
| P3-059 | LiteAPI provider adapter: search, rates, prebook, book, cancel, retrieve; retry classes, `provider_calls`, breaker and kill switch | L | P3-058 | Engineer |
| P3-060 | Schema and row policies (4.2), flag rules, `lodging_options` link, `webhook_events` provider value | M | P3-058 | Engineer |
| P3-061 | Search API and commission-blind ordering: uniform margin, sort on user criteria, caching, statement, ordering test | L | P3-059, P3-060 | Engineer |
| P3-062 | Offer and price rendering: total price lines, taxes and fees, pay-at-property, cancellation policy and snapshot, currency | M | P3-061 | Engineer |
| P3-063 | Prebook and payment: prebook API, hosted payment SDK integration in the in-app browser, confirm endpoint, idempotency | L | P3-062 | Engineer |
| P3-064 | Confirmation: itinerary and lodging links, email, voucher, calendar item, reminders | M | P3-063 | Engineer |
| P3-065 | Cancel and status sync: cancel API with refund preview, polling job, supplier webhook, completion job | L | P3-063 | Engineer |
| P3-066 | Reconciliation and revenue: failed-after-payment recovery, commission import, payout matching, revenue recognition at check-out | M | P3-065 | Engineer, bookkeeper |
| P3-067 | UI: stay comparison option, search, results, hotel page, checkout, confirmation, my bookings, cancel sheet, states and copy | L | P3-062, P3-064 | Engineer |
| P3-068 | Support process and admin: hotel bookings screen, actions, runbook "I arrived and there is no booking", emergency path, support macros, alerts; hire or contract a support person | L | P3-065 | Founder, support hire |
| P3-069 | Legal: counsel memo on seller-of-travel and consumer law, terms of sale, Nuitee terms review, privacy and label updates, per-state block list | M | P3-058 | Lawyer, founder |
| P3-070 | Tests and staged launch: test list in section 11, allow-list beta with 30 users, go or no-go at 200 bookings using the stop rule | M | P3-067, P3-068, P3-069 | Founder |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Rate parity leaves little or no margin | High | High | Sandbox check in P3-058, gate before building, stop rule at 200 bookings |
| Support load from hotel problems overwhelms a solo founder | High | High | Support process first (P3-068), hire before opening to everyone, allow-list rollout |
| "I arrived and there is no booking" incident | Medium | High | Runbook, reconcile jobs, contact paths, supplier incident count, goodwill budget |
| Legal exposure as a seller (registration, consumer law) | Medium | High | P3-069 before launch, per-state block list, Nuitee as merchant of record |
| Trust loss from being an unknown seller | Medium | Medium | Disclosure, plain terms, cancellation clarity, partner options stay beside it |
| Cannibalizes affiliate income more than the assumed $10 | Medium | Medium | Track affiliate click share before and after; incremental accounting in metrics |
| Supplier outage or API change | Medium | Medium | Kill switch, breaker, polling fallback, bookings stay visible and cancellable |
| Ranking by margin creeps in | Low | High | Uniform margin by construction, ordering and property tests in CI |
| Apple reads the flow as in-app commerce for digital goods | Low | Low | Physical service, hosted payment, reviewer notes |
