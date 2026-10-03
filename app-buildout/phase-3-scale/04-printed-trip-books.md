# Pack 04: Printed trip books

Part of [Phase 3: scale](README.md). Tickets P3-045 to P3-057. Written 2026-09-30.

| | |
|---|---|
| Feature flag | `print_orders` (created by this pack, off) |
| Needs | No hire and no lawyer. An accountant for sales tax on physical goods (Stripe Tax does the calculation). Real vendor quotes before any price is final. |
| Builds on | Phase 1: presentation mode data and PDF export, Stripe webhook endpoint, R2 storage, notifications. Phase 2: memories and sharing cards ([Phase 2](../phase-2-growth/README.md), which adds `trip_memories`); the book needs photos, and this pack adds a photo store if Phase 2 did not. |
| Source names | Phase 1 files call this "year 2" and "Phase 4", ticket WF-109. Spec of record: [07 section 11.3 (full spec)](../reference-full-spec/07-monetization-spec.md), [01 section 4.19 (full spec)](../reference-full-spec/01-product-spec.md), [03 section 5.18 (full spec)](../reference-full-spec/03-database-schema.md), [04 section 5.23 (full spec)](../reference-full-spec/04-api-spec.md). |

## 1. Goal and revenue case

**Goal.** A keepsake the traveler orders after a trip: a print-on-demand book (30 pages, hardcover, 8 by 8 inches) built from the itinerary, notes, maps and photos, plus a poster or printed itinerary. Ordered on the web (Stripe Checkout), no inventory, a print vendor ships. It is an optional export from presentation mode, offered once after a trip ends, and it touches no other part of the product (09 section 3.6).

**Unit economics (print costs reported, verify; get quotes from Prodigi, Peecho, Lulu and Printful).**

| Product | Price | Cost | Contribution |
|---|---|---|---|
| Trip book, 30 pages | $44.99 plus shipping at cost | Print $16 + card $1.60 + returns and support $1.00 | $26.39 |
| Poster or printed itinerary | $24.99 | Print $7 + card $1.03 + support $0.50 | $16.47 (09; the subtraction gives $16.46) |

Reference point: Polarsteps reportedly earns most of its revenue from printed books at EUR 36 to 150 each with 20M users (reported, verify). Gross sales are about 1.7 times contribution ($44.99 / $26.39).

**Margin check.** 07 section 11.3 sets a target of 35 to 45% after vendor cost, shipping and Stripe fees. 09's $26.39 is 59% of the book price because shipping is passed through at cost. The two are compatible only if real shipping is truly at cost. The price guard in P3-049 blocks any quote whose contribution falls below 35% of items plus shipping, and the real vendor quotes (P3-045) decide the final price.

**Revenue (base case, contribution, from 09 section 3.6).**

| Base | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|
| MAU | 20k | 60k | 100k | 150k |
| Attach rate (books and posters per MAU) | 0.4% | 0.6% | 0.8% | 0.8% |
| Contribution at $26 a unit | $2.1k | $9.4k | $20.8k | $31.2k |

Worked: year 5 is 150,000 x 0.8% x $26 = $31,200 (about 1,200 units, roughly $53k of gross sales). Conservative attach is 0.1%, 0.1%, 0.2%, 0.2%; ambitious 0.6%, 1.0%, 1.2%, 1.2%. 09 adds creator paid guides (0.008 per MAU at $2.29, $2.7k in year 5); they are an acquisition tool and are not part of this pack.

**What would break the case.** The photo and journal feature must exist, real print quotes differ from the inputs, and the attach rate is unmeasured. Test with a manual pre-order (P3-057) before scaling.

## 2. Design decisions

| # | Decision | Default and reason |
|---|---|---|
| D1 | Web only | The order flow lives on the web; iOS links to it in the in-app browser with visible chrome. Physical goods used outside the app fall under Guideline 3.1.3(e) (confirm current text). Nothing digital is unlocked. |
| D2 | One product first | Launch with one book (30 pages, hardcover, 8x8) shipping to the US. Posters and printed itineraries follow (P3-056). More sizes, countries and page counts only after the first 100 orders. |
| D3 | Preview before payment | The buyer sees a full page-by-page preview and the exact price (items, shipping, tax) before Checkout. |
| D4 | No partner links in print by default | Partner and affiliate content is left out unless the user adds it; if a partner link is printed, the commission sentence is printed beside it (07 section 11.3, F-PRT). No sponsored content is ever printed. |
| D5 | Vendor behind an interface | `providers/printer.py` with one adapter per vendor, chosen after quotes; the order row stores `printer` and `printer_order_id` so vendors can change. |
| D6 | Liability | Misprints and damage follow vendor policy, refunded or reprinted at no cost to the buyer; the buyer is responsible for content rights. No returns for personalized goods except defects (verify consumer law per country before adding any). |

## 3. User stories and acceptance criteria

**B-1. Offer after the trip.**
As a traveler whose trip has ended, I want to be offered a printed book once, so that I can keep the trip.
- A single card appears in the after-trip wrap-up (F-AFT-2) and in the presentation overflow menu; dismissing it hides it for that trip. No push notification is sent for it (Apple 4.10); one email is sent only to users who opted in to marketing email.
- Available to the owner and editors; viewers do not see it.

**B-2. Build the book.**
As an editor, I want to choose what goes in, so that the book is mine.
- Defaults come from presentation data: cover, title page, one page per destination, stays, one spread per day (map, items, notes marked shareable), a closing page. Empty sections are skipped. Private notes are excluded.
- I can pick a cover photo and title and subtitle, reorder days, remove pages and add photos to days. Page count stays within the product's limits and the price is shown as I edit.
- Photos under the minimum resolution warn with the affected page; photos below the block threshold cannot be placed.

**B-3. Preview and proof.**
As a buyer, I want to see exactly what will be printed, so that there are no surprises.
- A flip-through preview renders every page at proof quality including bleed and safe-area guides toggles. The preview is what the print PDF is built from.
- Text that overflows, blank pages and low-resolution images are flagged before payment.

**B-4. Price, pay, track.**
As a buyer, I want to see the total and follow the order, so that I know when it arrives.
- Quote: items, shipping, tax (Stripe Tax), total, valid 30 minutes (04 section 5.23); address validated; US only at launch (other countries show "Not yet available" with a waitlist).
- Pay through Stripe Checkout (Apple Pay where available). Status: Paid, Preparing, Printing, Shipped (carrier and tracking link), Delivered. Email on paid, shipped and delivered.
- Cancel and refund before the order is submitted to the vendor.

**B-5. Something is wrong.**
As a buyer, I want a simple way to report a damaged or misprinted book, so that it is fixed.
- "Report a problem" on the order (photos allowed) opens a support ticket; support triggers a vendor reprint or a refund from the admin screen.

**B-6. Privacy.**
As a buyer, I want my address removed after delivery, so that it is not kept.
- The shipping address is nulled 90 days after delivery (03 section 8); the PDF is deleted after 12 months.

**B-7. Poster or printed itinerary (later).**
As a traveler, I want a single printed page, so that I can put the trip on the wall or the fridge.
- Choose the map poster or the itinerary page; the same preview, quote and checkout flow; price $24.99.

## 4. Database additions

### 4.1 Defined in the full 03 (reuse verbatim)

03 section 5.18 defines `print_orders` with its row policies. Phase 1 dropped the table (Phase 1 03 section 1.1) and no Phase 2 pack creates it, so this pack creates it. Apply 4.1 and 4.2 in one Alembic revision (4.2 amends two of these definitions).

```sql
CREATE TABLE print_orders (
  id                          uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                     uuid REFERENCES trips (id) ON DELETE SET NULL,
  user_id                     uuid REFERENCES users (id) ON DELETE SET NULL,
  status                      text NOT NULL DEFAULT 'draft',
  product                     text NOT NULL DEFAULT 'trip_book',
  format                      text NOT NULL DEFAULT 'softcover',
  page_count                  smallint CHECK (page_count IS NULL OR page_count BETWEEN 8 AND 400),
  copies                      smallint NOT NULL DEFAULT 1 CHECK (copies BETWEEN 1 AND 20),
  pdf_key                     text,                                          -- object key in R2
  shipping_address            jsonb,                                         -- scrubbed after retention
  amount_minor                bigint CHECK (amount_minor IS NULL OR amount_minor >= 0),      -- items, before shipping and tax
  shipping_minor              bigint CHECK (shipping_minor IS NULL OR shipping_minor >= 0),
  tax_minor                   bigint CHECK (tax_minor IS NULL OR tax_minor >= 0),            -- Stripe Tax result; null until calculated
  currency                    currency_code,
  quote_expires_at            timestamptz,                                                   -- a draft row is the quote (04 5.23): its id is PrintQuote.id, valid 30 minutes
  stripe_payment_intent_id    text,
  printer                     text,
  printer_order_id            text,
  carrier                     text,
  tracking_number             text,
  shipped_at                  timestamptz,
  delivered_at                timestamptz,
  created_at                  timestamptz NOT NULL DEFAULT now(),
  updated_at                  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_print_orders_status CHECK (status IN ('draft', 'awaiting_payment', 'paid', 'submitted', 'printing', 'shipped', 'delivered', 'cancelled', 'refunded')),
  CONSTRAINT ck_print_orders_format CHECK (format IN ('softcover', 'hardcover')),
  CONSTRAINT ck_print_orders_quote CHECK (status <> 'draft' OR quote_expires_at IS NOT NULL)
);
CREATE UNIQUE INDEX uq_print_orders_pi ON print_orders (stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL;
CREATE INDEX ix_print_orders_user ON print_orders (user_id, created_at DESC);
CREATE INDEX ix_print_orders_status ON print_orders (status, created_at) WHERE status IN ('paid', 'submitted', 'printing', 'shipped');
SELECT add_updated_at_trigger('print_orders');

ALTER TABLE print_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY print_orders_select ON print_orders FOR SELECT USING (user_id = (SELECT app_user_id()));
CREATE POLICY print_orders_insert ON print_orders FOR INSERT WITH CHECK (user_id = (SELECT app_user_id()) AND (trip_id IS NULL OR can_edit_trip(trip_id)));
CREATE POLICY print_orders_update ON print_orders FOR UPDATE USING (user_id = (SELECT app_user_id()) AND status = 'draft');
```

Flag and constraint changes (Phase 1 seeds no later-phase flags):

```sql
INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('print_orders', 'Printed trip books', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
ALTER TABLE store_transactions DROP CONSTRAINT ck_store_transactions_kind;
ALTER TABLE store_transactions ADD CONSTRAINT ck_store_transactions_kind
  CHECK (kind IN ('subscription', 'pass', 'credit_pack', 'print_order', 'advisor_seat', 'group_payment'));   -- keep values added by other packs
```

The print order status machine (`draft`, `awaiting_payment`, `paid`, `submitted`, `printing`, `shipped`, `delivered`, `cancelled`, `refunded`) and retention rules (7 years for financial fields, address nulled 90 days after delivery, unordered drafts deleted after `quote_expires_at`) are as in 03.

### 4.2 New in this pack

```sql
-- Same Alembic revision as 4.1 (p3_print). New tables carry their own grants and policies.

-- Posters and printed itineraries need a flat format and a product check.
ALTER TABLE print_orders DROP CONSTRAINT ck_print_orders_format;
ALTER TABLE print_orders ADD CONSTRAINT ck_print_orders_format CHECK (format IN ('softcover', 'hardcover', 'poster', 'flat'));
ALTER TABLE print_orders ADD CONSTRAINT ck_print_orders_product CHECK (product IN ('trip_book', 'poster', 'itinerary'));
ALTER TABLE print_orders
  ADD COLUMN sku                         text,
  ADD COLUMN stripe_checkout_session_id  text,
  ADD COLUMN stripe_tax_calculation_id   text,
  ADD COLUMN vendor_status               text,                   -- raw vendor state, kept for support
  ADD COLUMN vendor_cost_minor           bigint CHECK (vendor_cost_minor IS NULL OR vendor_cost_minor >= 0),   -- from the vendor invoice, for margin
  ADD COLUMN refund_minor                bigint NOT NULL DEFAULT 0 CHECK (refund_minor >= 0),
  ADD COLUMN refund_reason               text,
  ADD COLUMN layout                      jsonb NOT NULL DEFAULT '{}'::jsonb,   -- cover photo, title, subtitle, page list and photo placements
  ADD COLUMN reprint_of_id               uuid REFERENCES print_orders (id) ON DELETE SET NULL;
CREATE UNIQUE INDEX uq_print_orders_checkout ON print_orders (stripe_checkout_session_id) WHERE stripe_checkout_session_id IS NOT NULL;
CREATE UNIQUE INDEX uq_print_orders_vendor ON print_orders (printer, printer_order_id) WHERE printer_order_id IS NOT NULL;

-- Money and fulfilment state is written by the billing and print workers, not the app role.
REVOKE INSERT, UPDATE, DELETE ON print_orders FROM hermi_app;
GRANT INSERT ON print_orders TO hermi_app;                                          -- quotes (status 'draft') only; enforced by the policy
GRANT UPDATE (layout, copies, shipping_address, format, page_count) ON print_orders TO hermi_app;     -- while draft (policy print_orders_update)

CREATE TABLE print_products (
  sku                text PRIMARY KEY,
  product            text NOT NULL,
  format             text NOT NULL,
  name               text NOT NULL,
  size_label         text NOT NULL,                                -- '8x8 in', 'A3 poster'
  vendor             text NOT NULL,
  vendor_sku         text NOT NULL,
  min_pages          smallint,
  max_pages          smallint,
  default_pages      smallint,
  price_minor        bigint NOT NULL CHECK (price_minor >= 0),     -- items price, before shipping and tax
  extra_page_minor   bigint CHECK (extra_page_minor IS NULL OR extra_page_minor >= 0),   -- set from real vendor quotes
  currency           currency_code NOT NULL DEFAULT 'USD',
  ship_countries     text[] NOT NULL DEFAULT '{US}',
  min_margin_bps     integer NOT NULL DEFAULT 3500 CHECK (min_margin_bps BETWEEN 0 AND 10000),
  is_active          boolean NOT NULL DEFAULT false,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_print_products_pages CHECK (min_pages IS NULL OR max_pages IS NULL OR max_pages >= min_pages)
);
SELECT add_updated_at_trigger('print_products');
GRANT SELECT ON print_products TO hermi_app;
INSERT INTO print_products (sku, product, format, name, size_label, vendor, vendor_sku, min_pages, max_pages, default_pages, price_minor, is_active) VALUES
('trip_book_8x8_hard', 'trip_book', 'hardcover', 'Trip book, hardcover', '8x8 in', 'TBD', 'TBD', 24, 60, 30, 4499, false),
('poster_map',         'poster',    'poster',    'Trip map poster',      'TBD',     'TBD', 'TBD', NULL, NULL, NULL, 2499, false)
ON CONFLICT (sku) DO NOTHING;   -- vendor and sizes are set from the real quotes (P3-045); products stay inactive until then

-- Status history for support and the admin timeline.
CREATE TABLE print_order_events (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  print_order_id  uuid NOT NULL REFERENCES print_orders (id) ON DELETE CASCADE,
  from_status     text,
  to_status       text NOT NULL,
  source          text NOT NULL,                                   -- 'api', 'stripe', 'vendor', 'admin', 'job'
  detail          jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_print_order_events_order ON print_order_events (print_order_id, created_at);
REVOKE ALL ON print_order_events FROM hermi_app;

-- Photos. If Phase 2 memories already stores trip photos, map to that table and skip this one.
CREATE TABLE trip_photos (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id           uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  uploaded_by       uuid REFERENCES users (id) ON DELETE SET NULL,
  itinerary_day_id  uuid REFERENCES itinerary_days (id) ON DELETE SET NULL,
  object_key        text NOT NULL,                                 -- R2 key; originals never served publicly
  content_type      text NOT NULL,
  width_px          integer NOT NULL CHECK (width_px > 0),
  height_px         integer NOT NULL CHECK (height_px > 0),
  bytes             integer NOT NULL CHECK (bytes > 0),
  taken_on          date,
  caption           text NOT NULL DEFAULT '' CHECK (char_length(caption) <= 300),
  alt_text          text NOT NULL DEFAULT '' CHECK (char_length(alt_text) <= 300),
  sort_order        integer NOT NULL DEFAULT 0,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_trip_photos_type CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp', 'image/heic'))
);
CREATE INDEX ix_trip_photos_trip ON trip_photos (trip_id, sort_order);
ALTER TABLE trip_photos ENABLE ROW LEVEL SECURITY;
CREATE POLICY trip_photos_select ON trip_photos FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY trip_photos_insert ON trip_photos FOR INSERT WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY trip_photos_update ON trip_photos FOR UPDATE USING (can_edit_trip(trip_id)) WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY trip_photos_delete ON trip_photos FOR DELETE USING (can_edit_trip(trip_id));

-- The vendor's webhook needs its own provider value.
ALTER TABLE webhook_events DROP CONSTRAINT ck_webhook_events_provider;
ALTER TABLE webhook_events ADD CONSTRAINT ck_webhook_events_provider   -- Phase 1 values, 'impact' from Phase 2, plus 'print'; keep values other packs add
  CHECK (provider IN ('revenuecat', 'apple', 'stripe', 'travelpayouts', 'viator', 'stay22', 'impact', 'print'));

UPDATE feature_flags SET rules = '{"countries":["US"],"min_photo_px_warn":1600,"min_photo_px_block":800,"max_photos_per_trip":200}'::jsonb WHERE key = 'print_orders';
```

Keep photos within limits: 10 MB per upload (existing upload cap), 200 per trip. Originals stay private in R2; thumbnails and proof renders are generated server side. Photos are user content and follow account deletion (03 section 8.1).

## 5. API additions

Base `/v1`, behind the `print_orders` flag. The order routes are already specified in [04 section 5.23 (full spec)](../reference-full-spec/04-api-spec.md) (`POST /print-orders/quote`, `POST /print-orders`, `GET /print-orders`, `GET /print-orders/{id}`, `POST /print-orders/{id}/cancel`); this pack adds the rest.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /print-products` | user | flag | `?country=` to `PrintProduct[]` | Active products for the country with prices and page limits. |
| `POST /trips/{trip_id}/photos` | editor | flag, 200 per trip | multipart to 201 `Photo` | Type, size and dimension checks, EXIF orientation applied, location data stripped from derivatives. |
| `GET /trips/{trip_id}/photos` | viewer | none | `?limit&cursor` to `Page<Photo>` | Signed, short-lived thumbnail URLs. |
| `PATCH /photos/{id}`, `DELETE /photos/{id}` | editor | none | `{ caption?, alt_text?, itinerary_day_id?, sort_order? }` | |
| `POST /trips/{trip_id}/book-preview` | owner or editor | 10 an hour | `{ sku, layout? }` to 202 `{ preview_id }` | Enqueues a render; layout defaults come from presentation data. Returns flags (low-resolution photos, overflow, blank pages). |
| `GET /book-previews/{preview_id}` | requester | none | to `{ status, pages: { n, image_url, flags }[], page_count, pdf_url? }` | Proof-quality page images; `pdf_url` is a watermarked low-resolution proof. |
| `POST /print-orders/quote` | owner or editor | none | as 04 5.23 plus `sku`, `preview_id` | Adds margin guard: `422 price_below_floor` (internal alert) if contribution is under `min_margin_bps`. `422 shipping_unavailable` outside the country list. |
| `POST /print-orders` | owner or editor | none | `{ quote_id }` with `Idempotency-Key` | As 04 5.23; locks `layout` and renders the print-ready PDF (`pdf_key`) before Checkout is created. |
| `POST /print-orders/{id}/report-problem` | requester | status `shipped` or `delivered` | `{ description, photo_keys? }` to 201 | Creates a support ticket linked to the order. |
| `POST /webhooks/print/{vendor}` | vendor | signature per vendor | status and tracking events | Stored in `webhook_events` (`provider = 'print'`), idempotent, order independent. |

```ts
type PrintProduct = { sku: string; product: "trip_book" | "poster" | "itinerary"; format: string; name: string; size_label: string
  price: Money; min_pages: number | null; max_pages: number | null; default_pages: number | null; ship_countries: string[] }
type Photo = { id: Uuid; trip_id: Uuid; thumb_url: string; width_px: number; height_px: number; caption: string; alt_text: string; itinerary_day_id: Uuid | null; taken_on: string | null }
```

Stripe webhooks ([04 section 6](../phase-1-launch/04-api-spec.md)) already name `checkout.session.completed`, `payment_intent.succeeded`, `charge.refunded` for print orders. Handlers: a paid order moves to `paid`, enqueues `submit_print_order`; a refund moves to `refunded`; all idempotent.

Jobs: `render_book_preview` (render queue), `render_print_pdf` (validates page size with bleed, fonts embedded, image resolution at 300 dpi target), `submit_print_order` (vendor API, retries with backoff, transient and permanent failure classes), `sync_print_status` (poll vendors every 30 minutes as a fallback for missed webhooks), `scrub_print_addresses` and `delete_expired_print_drafts` (nightly, 03 section 8), `purge_print_pdfs` (12 months). Provider calls are logged in `provider_calls`; kill switch `provider.printer`.

## 6. UI screens

Web app under `/trips/{id}/print`; the iOS app shows the entry card and opens the same URL in the in-app browser.

**Entry card.** After-trip wrap-up and presentation overflow menu: "Turn this trip into a book", a cover thumbnail and [Make a book]. Dismiss hides it for the trip. Copy is factual, no urgency: "A 30-page hardcover book from your plan, notes and photos. You see every page before you pay."

**Book builder.** Purpose: choose what goes in. Layout: left page strip (thumbnails, drag to reorder, remove), center page editor (photo slots, caption, title), right panel (cover photo, title, subtitle, page count, price). Photo picker from `trip_photos` with an upload button. Warnings are inline on the page, never modal. States: loading skeleton; no photos "Add a few photos or make the book without them"; render error "We could not build the preview. Try again." with the trip unchanged; offline "Book builder needs a connection".

**Preview.** Flip-through at proof quality, toggle for bleed and safe-area guides, checklist of flags (Low resolution on page 7: Replace or keep), total price visible throughout. [Continue to shipping].

**Shipping and payment.** Address form (US), shipping method at cost, tax line from Stripe Tax, copies (1 to 20), total, and "Pay with Stripe". Fine print: "Printed by {vendor}. Ships in about {estimate}. Personalized items cannot be returned unless damaged or misprinted." Never shown in the iOS app itself.

**Order status.** Timeline (Paid, Preparing, Printing, Shipped, Delivered) with tracking link, total and receipt, [Cancel order] until submitted, [Report a problem] afterwards.

**My orders.** Account page listing orders with status.

Accessibility: every page image has alt text from the page title; the builder is keyboard operable with explicit reorder buttons (drag is an enhancement); money is read with currency; status is text. Events: `print_card_shown`, `print_builder_opened`, `print_preview_viewed`, `print_quote_created {product}`, `print_checkout_started`, `print_order_paid`, `print_order_shipped`, `print_problem_reported`.

## 7. Billing

- **Stripe Checkout** in payment mode, one line per item plus shipping, **Stripe Tax** for sales tax or VAT on physical goods (verify US nexus and registrations; start US only). Apple Pay and Google Pay appear where available. Card fees are modeled at about 3.5% of the order in the contribution figures ($1.60 on $44.99).
- **No In-App Purchase.** Physical goods used outside the app (Guideline 3.1.3(e), confirm current text); the iOS app links to the web page only.
- **Vendor cost.** The print vendor is paid from Hermi's account (invoice or card on file per vendor). `print_orders.vendor_cost_minor` is recorded from the vendor's invoice to give real margin per order.
- **Refunds.** Full refund before submission (cancel). After shipment, misprints and damage are reprinted or refunded per the vendor policy and support discretion; refunds go through Stripe and set `refund_minor`; the vendor credit is claimed back where available.
- **Accounting.** Revenue is recognized at shipment; sales tax collected is a liability tracked by Stripe Tax reports.

## 8. Admin additions

Extends the console ([08](../phase-1-launch/08-admin-control-center.md); source ticket WF-109 had no admin screen, so this is new).

- **Screen: Print orders (Money group).** List with status, product, buyer (masked), total, vendor status, age, tracking, margin; filter by status, vendor, country, stuck (paid but not submitted over 1 hour, printing over vendor SLA plus 2 days); order detail with timeline from `print_order_events`, preview of the print PDF (download for support), vendor reference and raw vendor status, refund history.
- **Actions.** Retry submission (engineer), cancel and refund (finance up to $100, owner above, typed confirmation), reprint (creates a linked order with `reprint_of_id` at no charge, support or finance), edit the address before submission (support, audited reveal), mark delivered manually (engineer).
- **Products.** A Print products settings tab: activate a sku, set vendor sku, `price_minor`, `extra_page_minor`, `min_margin_bps`. Price changes need the owner (08 section 3 "Settings").
- **Alerts.** Order paid and unsubmitted over 1 hour (page), vendor webhook failures, return and problem rate above 3% of orders in a month (notify), render job failure rate, quote blocked by the margin guard (notify).
- **Finance reports.** Print revenue, vendor cost, contribution and margin per order and per month, tax collected, refund rate.

## 9. Legal and compliance

1. **Sales tax and VAT.** Stripe Tax calculates and reports; counsel or an accountant confirms registration once nexus thresholds are reached. US only at launch avoids VAT.
2. **Consumer rights.** Personalized goods are commonly excluded from return rights; confirm per country before selling outside the US and state the policy before payment. Provide a clear refund route for defects.
3. **Content rights.** The buyer warrants they own or may print the photos and text; terms and a checkbox at order. The vendor's content rules apply (for example nudity and hate content); a vendor rejection refunds the buyer.
4. **Maps.** Printed maps must carry the data licence attribution (OpenStreetMap and the map provider). The Geoapify terms for static maps in print are an open item in the Phase 1 plan and must be confirmed before P3-047 ships; fall back to a self-rendered map from OSM data with attribution.
5. **Privacy.** The shipping address goes to the print vendor as a processor and is scrubbed 90 days after delivery; add the vendor to the processor list and sign its data-processing terms. Children's photos and names are the buyer's responsibility; other travelers' names appear only as in presentation mode, with private notes excluded.
6. **Affiliate and sponsored content.** Not printed by default; if a partner link is printed, the commission sentence is printed with it (FTC, UK and EU rules in [08-affiliate-revenue.md section 7.4](../context/business-plan/08-affiliate-revenue.md)). Partner guide content is never printed.
7. **Apple.** Web-only checkout; the app only opens the page. No claim in the app that a purchase unlocks anything.
8. **Product description.** Accurate size, page count, paper and shipping estimate; no quality claim the vendor cannot support.

## 10. Analytics

Events are in section 6. First-party and admin metrics: offers shown, builder opens, previews viewed, quotes, orders, conversion from offer to order (base case assumes 0.8% of MAU order in year 5), average copies, average price, shipping cost, contribution per order (target at or above $26), problem rate, refund rate, time from paid to shipped, median delivery days, share of orders with photos. PostHog carries the funnel; no ad SDKs. Decision rule after the first 100 orders: if the attach rate is under 0.2% of MAU the lane stays manual and poster work (P3-056) is cancelled.

## 11. Tests

- **Golden PDF.** For a fixture trip the rendered PDF has the exact page count, trim and bleed size, embedded fonts, no pages with overflow, images at or above 300 dpi where the source allows; page thumbnails compare against stored goldens with a small tolerance; private notes and partner links are absent.
- **State machine.** Every legal transition passes and every illegal one raises `409 state_conflict`; events are recorded; cancel refunds before submission and is refused after.
- **Quote.** Expiry after 30 minutes (`quote_expired`), price guard (`price_below_floor`), shipping outside the country list, tax calculation with a Stripe Tax fake.
- **Webhooks.** Stripe and vendor events idempotent and order independent; a missed vendor webhook is recovered by the polling job.
- **Vendor adapter.** Contract tests with recorded vendor fixtures; sandbox order end to end once; retry classes (transient versus permanent rejection).
- **Retention.** Address scrub 90 days after delivery, draft deletion, PDF purge.
- **Privacy and tenancy.** A member of another trip cannot read photos, previews or orders (cross-tenant test includes `trip_photos` and `print_orders`); EXIF location stripped from derivatives; signed URLs expire.
- **Web only.** The iOS client has no purchase UI; the link opens the web page.

## 12. Tickets

| ID | Title | Size | Needs | Who |
|---|---|---|---|---|
| P3-045 | Vendor selection: quotes from Prodigi, Peecho, Lulu and Printful, a sample order of each, final price, shipping and SLA; fill `print_products` | M | none | Founder |
| P3-046 | Photos: upload, storage, derivatives, limits (skip the table if Phase 2 memories has it) | M | none | Engineer |
| P3-047 | Book layout and render engine: page templates, server-side PDF with bleed, static maps with attribution, fonts, image checks, golden tests | L | P3-045, P3-046 | Engineer |
| P3-048 | Builder and preview UI: page strip, editor, flags, flip-through proof | L | P3-047 | Engineer |
| P3-049 | Quote API: products endpoint, shipping and Stripe Tax, margin guard, schema migration (4.2) | M | P3-045 | Engineer |
| P3-050 | Checkout and orders: print-ready PDF at order time, Stripe Checkout, webhook handling, order status page and emails | L | P3-047, P3-049 | Engineer |
| P3-051 | Vendor submission and status sync: adapter, `submit_print_order`, vendor webhook, polling fallback, tracking | L | P3-050 | Engineer |
| P3-052 | Cancel, refund and reprint rules; report-a-problem flow and support ticket link | M | P3-051 | Engineer |
| P3-053 | Retention and privacy jobs: address scrub, draft deletion, PDF purge; processor list and terms | S | P3-050 | Engineer |
| P3-054 | Admin print orders screen, products tab, alerts, finance lines | M | P3-051 | Engineer |
| P3-055 | Entry points: after-trip card, presentation menu, opt-in email, web-only guard for iOS, reviewer note | S | P3-048 | Engineer |
| P3-056 | Second products: poster and printed itinerary (same flow, new templates) | M | P3-050 | Engineer |
| P3-057 | Manual pre-order test (10 to 20 real orders from existing users) then launch behind the flag; decision rule on attach rate | M | P3-054, P3-055 | Founder |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Real print and shipping costs erode the $26 contribution | Medium | Medium | Margin guard, vendor quotes first, price changes through the products tab |
| No photo and journal feature, weak books | Medium | Medium | P3-046, allow photo-free books from maps and notes, test with real users |
| Attach rate below 0.2% of MAU | Medium | Low | Manual pre-order before building more; cancel posters if low |
| Misprints, damage and returns | Medium | Medium | Vendor policy, reprint flow, problem rate alert, vendor choice on quality |
| Map or photo licensing in print | Low | Medium | Attribution, licence check for static maps, user warranty for photos |
| Sales tax complexity | Low | Low | US only, Stripe Tax, accountant confirms registrations |
| Privacy of addresses and photos | Low | Medium | Processor terms, 90-day scrub, private originals, tenancy tests |
| Apple reads the flow as steering | Low | Low | Physical goods, web only, plain reviewer notes |
