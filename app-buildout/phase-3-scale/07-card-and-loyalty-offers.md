# Pack 07: Card and loyalty offers

Part of [Phase 3: scale](README.md). Tickets P3-082 to P3-091. Written 2026-09-30.

**This is the last pack and the most compliance-heavy one. Build it only when section 1.3 says it is worth it.**

| | |
|---|---|
| Feature flags | `card_offers` and `loyalty_offers` (created by this pack, off) |
| Needs | A lawyer on retainer (consumer finance advertising, per-offer copy review). A specialist publisher network that will accept the app, and issuer approval of every page of copy. A compliance owner: part of the founder's time at first, a part-time person later. No engineering hire, no funding. |
| Builds on | Phase 1: Before you go checklist (the `money` item), affiliate system (`/go`, conversions, disclosure component, link checker), admin console and audit log. Phase 2: [direct affiliate programs](../phase-2-growth/08-direct-affiliate-programs.md) (adds the `direct` and `impact` networks). |
| Source names | Phase 1 files say "credit cards, VPNs and Amazon product data" are out of scope and that cards are revisited at about 100k MAU with counsel ([01 section 7](../phase-1-launch/01-product-spec.md), [09 section 3.8](../context/business-plan/09-revenue-expansion.md), [08-affiliate-revenue.md section 4.3](../context/business-plan/08-affiliate-revenue.md)). No ticket existed; this pack is new detail. |

## 1. Goal and revenue case

### 1.1 Goal

Show a small number of clearly labeled card and loyalty-program offers in one place: a "Money" section inside the Before you go checklist. Never inside the planner flow (flights, stays, itinerary, presentation), never pushed, never in AI answers, never ranked by payout. The feature exists to earn per-approval commissions from users who want a travel card, without turning the product into a card-comparison site (09 section 3.8).

### 1.2 Revenue case

Card referrals pay $50 to $200 per approved application (reported: CardRatings $50 to $200, Bankrate $50 to $175; verify). Point-tracking services pay $10 to $30 per subscription (reported, `point.me`; 08-affiliate-revenue.md section 13.7).

**Nothing here is in the README scenario totals.** 09 states the potential at 100k MAU only:

| Case (09 section 3.8) | Approval rate per MAU a year | Payout per approval | Revenue at 100k MAU |
|---|---|---|---|
| Low end | 0.5% | $100 | $50k |
| High end | 1.0% | $150 | $150k |

The same inputs at other audience sizes (arithmetic, not a forecast):

| MAU | Low end (0.5% x $100) | High end (1.0% x $150) |
|---|---|---|
| 100k (base case year 4) | $50k | $150k |
| 150k (base case year 5) | $75k | $225k |
| 300k (ambitious case year 4) | $150k | $450k |

The high end "only works if it can be shown without pushing users" (09). Expect the low end or less until measured; most of the MAU never see the section because it lives inside one checklist item, and most who see it do not apply. Treat the figure as an upper bound on a section that has to earn its place by not hurting trust.

### 1.3 When it becomes worth it (the gate)

Start the build only when all of these hold. The first is from 09; the rest are this pack's proposals (assumptions to tune).

1. **Audience.** About 100k MAU (09 section 3.8), sustained for 3 months.
2. **Economics.** The low-end figure at the current MAU is at least 3 times the first-year cost of counsel, the build and compliance upkeep (quotes from P3-082; the multiplier is a rule of thumb).
3. **Access.** A specialist publisher network (CardRatings, Bankrate, or a CJ or Impact program) accepts Hermi as a publisher. Issuers screen publishers; Chase is reported reachable only through CardRatings or Bankrate (08-affiliate-revenue.md section 4.3).
4. **Legal.** Counsel has written advice on the regimes in section 9 and accepts the design in section 2.
5. **Trust.** Over the prior 6 months: affiliate "hide booking links" rate under 5% of users, no rise in trust-related support tickets, and App Store rating stable. If trust is slipping, fix that first.
6. **Capacity.** A named person owns offer expiry, copy re-review and complaints (section 8).

If any item fails, re-check every 6 months. The decision record is written in P3-082.

## 2. Design decisions

| # | Decision | Default and reason |
|---|---|---|
| D1 | One place only | Offers appear only in the Money section of Before you go (inside the `money` checklist item). They never appear in flights, stays, itinerary, Discover, search, presentation, shared pages, PDFs or print. |
| D2 | No AI involvement | Offer copy is issuer-approved text stored verbatim and shown unchanged. No model writes, summarizes or recommends a card. AI answers never mention specific cards or issuers. Agents never cite offers. |
| D3 | No ranking, no targeting | The section lists offers alphabetically by issuer and says so. Payout never affects order, inclusion or visibility. No personalization from trip data, spending or any financial signal. A user sees the same offers as anyone else in their region. |
| D4 | No financial data collected | Hermi never asks for or stores income, credit score, card numbers or identity numbers. The only data is the outbound click (random sub-id) and the network's approval status. |
| D5 | Opt-in and quiet | Nothing commercial loads or renders until the user taps "Show partner offers" in the Money item, which records the `offers` consent (Phase 1 03 section 14 names this consent value). Withdrawable at any time in Settings or in the section. No push, no email, no paywall mention, no badge, no nudge. The checklist item is unchanged for users who never opt in. |
| D6 | Region first | United States only at launch. Other regions stay off until counsel clears their financial-promotion rules. |
| D7 | Two-person approval | An offer goes live only after legal approval and, where required, an issuer approval reference, recorded in the console by two different admins. Offers carry an expiry and a re-review date. |
| D8 | Loyalty offers use the same frame | Loyalty and points-service offers (for example program signups or a points-tracking service) follow the same rules, placement, labeling and approval flow. No loyalty numbers are stored. |

## 3. User stories and acceptance criteria

**C-1. Traveler chooses to see labeled offers.**
As a traveler preparing for an international trip, I want to see money-related options in the Money checklist item, so that I can decide what to do about foreign card fees.
- The Money item still shows the non-commercial guidance first (tell your bank, carry some cash, use a card without foreign transaction fees) with no links.
- Below it is one plain line, "Partner offers for travel cards and loyalty programs", and a [Show partner offers] button. Until the user taps it no offer is requested from the server or rendered. Tapping records the `offers` consent (`PUT /me/consents/offers`) and expands a labeled section "Offers from partners" (text, not color only; "Ad" on UK and EU storefronts when those regions are later enabled) lists live offers for the user's region, alphabetical by issuer, each with the issuer's approved headline, key terms shown verbatim, required disclosures inline, and a link to the issuer's terms.
- A line above the list: "Hermi earns a commission if you are approved. It does not change which offers we show or their order. Offers are listed alphabetically."
- At most 4 offers are shown; none is pre-selected or highlighted.

**C-2. Traveler applies.**
As a traveler, I want to go to the issuer's page, so that I can read everything and apply.
- "View offer and terms" opens the issuer page through `/go/{click_id}` in the in-app browser with visible chrome; the disclosure sentence is next to the button; no application is taken inside Hermi.
- No data beyond the random sub-id is passed.

**C-3. Traveler turns offers off.**
As a traveler, I want to switch them off again, so that I never see them.
- Settings toggle "Partner offers" (the `offers` consent, granted false when withdrawn); takes effect at once on every surface and the section collapses back to the one-line prompt.

**C-4. Editor and legal approve an offer.**
As the compliance owner, I want an approval trail, so that nothing goes live without review.
- An offer moves draft, legal review, approved, live, paused, expired. Going live needs a legal approval record (who, when, reference) and, if the issuer requires it, the issuer's approval reference and date; copy fields are locked after approval (a change creates a new version that restarts review).
- The console refuses to publish an offer with missing required disclosures, no terms URL, no expiry, or copy that contains banned phrases (for example "pre-approved", "guaranteed", "best card").

**C-5. Founder pauses everything.**
As the owner, I want one switch, so that a complaint or issuer request is handled in minutes.
- Kill switch `card_offers` (and per-program `affiliate.<code>`) removes every offer from every surface immediately; expired offers disappear without a release.

**C-6. Loyalty signup offer (optional).**
As a traveler, I want to see a loyalty program signup or points-tracking service that matches my trip, so that I can choose to use one.
- Same section and rules as C-1 with kind `loyalty_program` or `points_service`. Matching is by trip type only (for example an airline or hotel brand present in the trip's own chosen items), never by the user's finances. I can tell the app I already have a membership (yes or no, no number stored) to stop seeing that signup.

**C-7. Complaint handling.**
As a user or issuer, I want a way to report a problem with an offer, so that it is fixed quickly.
- "Report this offer" on every offer creates a moderation report; the owner is paged for a report about accuracy; an offer under complaint can be paused in one action.

## 4. Database additions

### 4.1 What exists and what this pack adds

Reused from Phase 1 and 2: the affiliate tables (`affiliate_programs`, `affiliate_link_templates`, `link_clicks`, `affiliate_conversions`, Phase 1 03 section 5.15), `consents` (append-only log, Phase 1 03 section 5.17), `checklist_items` with the `money` kind (F-CHK-1), the `/go` redirect, kill switches named `affiliate.<code>`, and the direct-network values from Phase 2. Phase 1 03 section 14 names this pack's additions: `card_offers` and `loyalty_accounts`, `affiliate_programs.category` value `cards`, and `consents.kind` value `offers`. The full 03 has no DDL for cards, so the DDL below is new. The Phase 1 category list already contains `money` (the plain "tell your bank" guidance kind); offers get the separate value `cards` so reports and kill switches never mix them with neutral money links.

```sql
-- Current Phase 1 constraints that 4.2 widens (swap the named constraint, keeping every value already allowed):
-- ck_affiliate_programs_category: flights, lodging, tours, cars, transfers, trains, esim, insurance, compensation, luggage, restaurants, visas, money, other
-- ck_consents_kind: terms, privacy, ai_processing, marketing_email, push_notifications, analytics (Phase 2 adds concierge_sharing)
```

### 4.2 New in this pack

```sql
-- Migration p3_card_offers. New tables carry their own grants and policies (Phase 1 03 section 10).

ALTER TABLE affiliate_programs DROP CONSTRAINT ck_affiliate_programs_category;
ALTER TABLE affiliate_programs ADD CONSTRAINT ck_affiliate_programs_category CHECK (category IN (
  'flights', 'lodging', 'tours', 'cars', 'transfers', 'trains', 'esim', 'insurance',
  'compensation', 'luggage', 'restaurants', 'visas', 'money', 'other', 'cards'));
ALTER TABLE consents DROP CONSTRAINT ck_consents_kind;
ALTER TABLE consents ADD CONSTRAINT ck_consents_kind CHECK (kind IN ('terms', 'privacy', 'ai_processing', 'marketing_email', 'push_notifications',
  'analytics', 'concierge_sharing', 'offers'));   -- 'concierge_sharing' from Phase 2

CREATE TABLE card_offers (
  id                     uuid PRIMARY KEY DEFAULT uuidv7(),
  program_id             uuid NOT NULL REFERENCES affiliate_programs (id) ON DELETE RESTRICT,   -- category 'cards'
  kind                   text NOT NULL,
  issuer_name            text NOT NULL CHECK (char_length(issuer_name) BETWEEN 1 AND 120),
  product_name           text NOT NULL CHECK (char_length(product_name) BETWEEN 1 AND 160),
  headline               text NOT NULL CHECK (char_length(headline) BETWEEN 1 AND 200),       -- issuer-approved text, verbatim
  key_terms              jsonb NOT NULL DEFAULT '[]'::jsonb,                                  -- [{"label","text"}] verbatim: fees, APR, rewards as the issuer states them
  required_disclosures   text NOT NULL,                                                       -- issuer- or law-required lines, shown inline
  terms_url              text NOT NULL CHECK (terms_url ~ '^https://'),
  image_url              text,                                                                -- issuer-supplied, hosted by us
  regions                country_code2[] NOT NULL DEFAULT '{US}',
  status                 text NOT NULL DEFAULT 'draft',
  copy_version           integer NOT NULL DEFAULT 1,
  issuer_approval_ref    text,                                                                -- reference or email id of the issuer's copy approval
  issuer_approved_at     timestamptz,
  legal_approved_by      uuid REFERENCES users (id) ON DELETE SET NULL,                       -- never the editor
  legal_approved_at      timestamptz,
  created_by             uuid REFERENCES users (id) ON DELETE SET NULL,
  valid_from             date,
  valid_to               date NOT NULL,                                                       -- every offer expires
  review_due_on          date NOT NULL,                                                       -- re-review cadence (at most 90 days)
  payout_note            text,                                                                -- finance only: reported payout per approval, verify
  live_at                timestamptz,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_card_offers_kind CHECK (kind IN ('credit_card', 'loyalty_program', 'points_service')),
  CONSTRAINT ck_card_offers_status CHECK (status IN ('draft', 'legal_review', 'approved', 'live', 'paused', 'expired')),
  CONSTRAINT ck_card_offers_live CHECK (status <> 'live' OR (legal_approved_at IS NOT NULL AND legal_approved_by IS DISTINCT FROM created_by
                                        AND live_at IS NOT NULL AND valid_from <= valid_to)),
  CONSTRAINT ck_card_offers_terms_array CHECK (jsonb_typeof(key_terms) = 'array'),
  CONSTRAINT ck_card_offers_dates CHECK (valid_from IS NULL OR valid_to >= valid_from),
  CONSTRAINT ck_card_offers_review CHECK (review_due_on <= valid_to)
);
CREATE INDEX ix_card_offers_live ON card_offers (kind, issuer_name) WHERE status = 'live';
CREATE INDEX ix_card_offers_review ON card_offers (review_due_on) WHERE status IN ('approved', 'live');
SELECT add_updated_at_trigger('card_offers');

-- Approval trail: every state change and every approval, kept as long as the offer and then 7 years.
CREATE TABLE card_offer_reviews (
  id              uuid PRIMARY KEY DEFAULT uuidv7(),
  card_offer_id   uuid NOT NULL REFERENCES card_offers (id) ON DELETE CASCADE,
  copy_version    integer NOT NULL,
  action          text NOT NULL,
  actor_id        uuid REFERENCES users (id) ON DELETE SET NULL,
  reference       text,                                                                       -- counsel memo id, issuer email id
  checklist       jsonb NOT NULL DEFAULT '{}'::jsonb,
  note            text NOT NULL DEFAULT '',
  copy_snapshot   jsonb NOT NULL,                                                             -- the exact text approved
  created_at      timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_card_offer_reviews_action CHECK (action IN ('submit', 'legal_approve', 'legal_reject', 'issuer_approve', 'publish', 'pause', 'expire', 'rereview', 'complaint'))
);
CREATE INDEX ix_card_offer_reviews_offer ON card_offer_reviews (card_offer_id, created_at);
REVOKE ALL ON card_offer_reviews FROM hermi_app;                                          -- admin only

-- The app sees live, in-window offers for the caller's region, and never the review or payout columns.
REVOKE ALL ON card_offers FROM hermi_app;
GRANT SELECT (id, program_id, kind, issuer_name, product_name, headline, key_terms, required_disclosures, terms_url,
              image_url, regions, status, copy_version, valid_from, valid_to) ON card_offers TO hermi_app;
ALTER TABLE card_offers ENABLE ROW LEVEL SECURITY;
CREATE POLICY card_offers_live ON card_offers FOR SELECT
  USING (status = 'live' AND (valid_from IS NULL OR valid_from <= CURRENT_DATE) AND valid_to >= CURRENT_DATE);

-- Optional (C-6): "I already have this membership". No numbers, no balances. (Phase 1 03 section 14 working name: loyalty_accounts.)
CREATE TABLE loyalty_accounts (
  user_id        uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  brand          text NOT NULL CHECK (char_length(brand) BETWEEN 1 AND 80),
  has_membership boolean NOT NULL DEFAULT true,
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, brand)
);
ALTER TABLE loyalty_accounts ENABLE ROW LEVEL SECURITY;
CREATE POLICY loyalty_accounts_own ON loyalty_accounts FOR ALL
  USING (user_id = (SELECT app_user_id())) WITH CHECK (user_id = (SELECT app_user_id()));

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('card_offers',    'Labeled card offers in the Money section of Before you go (US only, legal review first)', false, 100, '{"countries":["US"],"max_offers":4}', '{}'),
('loyalty_offers', 'Labeled loyalty and points-service offers in the same section',                          false, 100, '{"countries":["US"],"max_offers":2}', '{}')
ON CONFLICT (key) DO NOTHING;
INSERT INTO kill_switches (key, description) VALUES ('card_offers', 'Remove every card and loyalty offer from every surface')
ON CONFLICT (key) DO NOTHING;

-- Outbound clicks use the existing link_clicks table; allow the new entity type wherever a check lists entity types (04 OutboundIn.entity_type gains 'card_offer').
```

Illustrative program seed (status stays `planned` until the network approves the app; `terms_url` and `hosts` are filled from the network's terms, never guessed):

```sql
INSERT INTO affiliate_programs (code, network, name, category, status, hosts, cookie_days, subid_param, api_credentials_ref, disclosure_text) VALUES
('cards_network_primary', 'direct', 'Card referral network (publisher)', 'cards', 'planned', '{}', 30, 'sub_id', 'CARDS_NETWORK_TOKEN',
 'We earn a commission if you are approved. This does not change which offers we show or their order.')
ON CONFLICT (code) DO NOTHING;
```

Add `CARDS_NETWORK_TOKEN` to `.env.example` and the secrets list ([02 section 7.1](../phase-1-launch/02-architecture.md)); never commit a value. Retention: `card_offers` and `card_offer_reviews` 7 years; `link_clicks` 25 months as usual; `loyalty_accounts` with the account.

## 5. API additions

Base `/v1`, behind `card_offers` and `loyalty_offers` and the kill switch `card_offers`.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/money-offers` | viewer | flags; needs the `offers` consent; empty when the region is not allowed | to `MoneyOffers` | Without consent it returns `{ consent: "not_granted", offers: [] }` and reads no offer rows. Otherwise returns live offers for the user's country (from the session, not the request), alphabetical by `issuer_name`, at most `max_offers`; no personalization input. `sorted_by` is always `"issuer name, alphabetical"`. |
| `POST /outbound` | user (viewer) | existing | `OutboundIn` with `entity_type: "card_offer"` | Existing flow: mints a `link_clicks` row with a random sub-id, checks kill switches (`card_offers`, `affiliate.<code>`) and the region; returns the `/go/{click_id}` URL. |
| `POST /money-offers/{offer_id}/report` | user | 10 an hour | `{ reason, description? }` to 201 | Creates a moderation report; an accuracy report pages the owner. |
| `PUT /me/loyalty-programs/{brand}` | user | `loyalty_offers` | `{ has_membership: boolean }` | Stops signup offers for that brand. |
| `PUT /me/consents/offers` | user | none | `{ version: string, granted: boolean }` to `Consent` | The existing consent endpoint (Phase 1 04 section 5.2) with the new kind; granting expands the section, withdrawing collapses it. |

```ts
type MoneyOffers = { consent: "granted" | "not_granted"; sorted_by: "issuer name, alphabetical"; disclosure: string; offers: MoneyOffer[] }
type MoneyOffer = { offer_id: Uuid; kind: "credit_card" | "loyalty_program" | "points_service"; issuer_name: string; product_name: string
  headline: string; key_terms: { label: string; text: string }[]; required_disclosures: string; terms_url: string; image_url: string | null
  label: "Ad" | "Partner offer" }
```

Admin API (`/v1/admin`, [08 section 8](../phase-1-launch/08-admin-control-center.md)): `GET/POST /card-offers`, `PUT /card-offers/{id}` (draft only), `POST /card-offers/{id}/submit`, `POST /card-offers/{id}/review` (legal approve or reject, records reference and checklist), `POST /card-offers/{id}/issuer-approval`, `POST /card-offers/{id}/publish` (owner, step-up 2FA), `POST /card-offers/{id}/pause`, `GET /card-offers/{id}/reviews`. Every call needs a reason and writes `audit_log` with before and after.

Conversions: the existing nightly pull or postback stores approvals in `affiliate_conversions` (status pending, approved, rejected, paid); a card approval is reported only as an aggregate. Jobs: `expire_card_offers` (daily, sets `expired`, writes a review row, alerts 14 days before `valid_to` and 7 days before `review_due_on`), `card_offer_link_check` (weekly, through the existing link checker, pauses an offer whose destination fails or changes host).

## 6. UI screens

**Money item in Before you go (extends 6.20).** Purpose: help with money before a trip; offers are a small, labeled extra. Layout: the checklist item detail shows the plain guidance (tell your bank, cash, cards without foreign transaction fees) and done or not needed actions first, with no commercial content. Below a rule, one plain line "Partner offers for travel cards and loyalty programs" with [Show partner offers]. After the user opts in (consent `offers`), a section titled "Offers from partners" appears with the explainer line and up to 4 cards.

Offer card: issuer and product name, headline, key terms as a description list (for example annual fee, foreign transaction fee, rewards, as the issuer states them), required disclosures in body text, a text label "Ad" or "Partner offer", the sentence "Hermi earns a commission if you are approved here.", a terms link, and [View offer and terms] opening through `/go`. Overflow menu: Turn off partner offers, Report this offer.

States: no live offers or region not allowed, the section is absent; loading skeleton; offline "Offers need a connection" (plain guidance still visible); consent withdrawn, the section collapses to the one-line prompt; expired offers vanish.

Loyalty signup cards (when enabled) use the same frame plus "I already have this" that hides that brand. No pop-ups, sheets, badges, banners or countdowns; the opt-in prompt is one inline line. Nothing appears on the trip overview, Discover, presentation, share pages or PDFs.

Copy rules: no claims beyond the issuer's approved text; no "best", "top", "pre-approved", "guaranteed", or urgency; sentence case; no em dashes. Accessibility: the label and the commission sentence are read with the card name before the headline; terms are a real description list; the link announces that it opens an external site.

**Settings.** "Partner offers" toggle (the `offers` consent) next to "Hide booking links".

**Admin console.** See section 8.

Events: `money_offers_viewed {count}`, `money_offer_opened {kind}`, `money_offer_reported`, `money_offers_consent_changed {granted}`. No event carries card names in a user-linked profile beyond the offer id, and none records any financial attribute.

## 7. Billing

There is no user billing and nothing in the app is paid. Revenue is a network commission per approved application (or per subscription for a points service), reported through the existing affiliate conversion import.

- **Reporting.** Finance reports add card and loyalty commissions by offer and network, approvals, pending versus approved versus rejected, and payout dates; revenue is recognized when the network approves, net of reversals.
- **Payouts.** Per network terms (verify payment thresholds and lag); `affiliate_payouts` records receipts (03 section 5.15).
- **Tax and 1099.** Commission income from US networks is reported by the network; finance keeps the records.
- **No cashback, no rewards to users.** Hermi does not pay users any share (08-affiliate-revenue.md section 13.6).
- **Apple.** These are offers for financial products used outside the app. No in-app purchase is involved and nothing digital is unlocked. Check the App Review guideline on financial products and credit offers for any extra requirements on disclosure (verify text on the submission day) and describe the section in reviewer notes.

## 8. Admin additions

New "Card and loyalty offers" screen (Control group), extends [08](../phase-1-launch/08-admin-control-center.md).

- **List and detail.** Offers with status, issuer, kind, regions, `valid_to`, `review_due_on`, copy version, clicks and approvals; the detail page shows the locked copy, disclosures, the approval trail (`card_offer_reviews`), linked program and link templates, and a live preview of the card exactly as users see it.
- **Workflow.** Editor drafts and submits; counsel or the compliance owner approves on the legal checklist (issuer text verbatim, required disclosures present, no banned phrases, region allowed, expiry and re-review dates set, terms link works, no ranking or targeting claim, no AI-written text); the owner publishes with step-up 2FA. The editor cannot be the legal approver (`ck_card_offers_live`). A copy change after approval creates a new version and returns the offer to review.
- **Actions.** Pause (engineer or owner, immediate), expire, duplicate as a new version, record an issuer approval reference, open the complaint queue, engage the `card_offers` kill switch (owner or engineer).
- **Permissions.** `cardoffers.edit` (content), `cardoffers.review` (owner or a designated compliance admin, never the author), `cardoffers.publish` (owner only), `cardoffers.payout.read` (finance and owner). The route-permission test covers them.
- **Alerts.** An offer expires in 14 days or needs re-review in 7 days (notify), a live offer's destination host changed (page), a complaint about accuracy (page), consent withdrawals above 10% of opted-in users in a week (notify), a live offer without a legal approval record (page; should be impossible).
- **Finance and audit.** Revenue by offer and network, reversal rate, `audit_log` extended retention class for publish and pause actions (08 section 4.2).

## 9. Legal and compliance

This is the reason the pack is last. Counsel confirms each item before the first offer goes live; the lists are questions to ask, not advice.

1. **Advertising disclosure.** FTC endorsement rules require a clear, adjacent disclosure (the sentence in section 3). UK and EU rules differ; the UK treats affiliate links as advertising ("Ad") and credit-card promotion is a regulated financial promotion, so the UK and EU stay off until counsel clears them (D6).
2. **Consumer finance advertising.** Credit card advertising must not be unfair, deceptive or abusive, and must show required terms. Issuers provide approved language and disclosures (for example fees and rates); Hermi displays them verbatim and does not summarize, rewrite or add claims. Counsel confirms which federal and state rules reach a publisher that only links out.
3. **Licensing.** Whether simple referral linking requires any state registration or licence (usually not for referral only, but verify).
4. **Network and issuer terms.** Issuers screen publishers, review all copy, may restrict placement, targeting, incentives and traffic types, and may require approvals per page. Get written approval before publishing each offer and keep it with the record (`issuer_approval_ref`).
5. **No advice.** No "best card for Japan", no comparisons or rankings, no eligibility predictions, no personalized suggestions; AI never produces or discusses card content (D2). The section's explainer says the offers are advertisements.
6. **Data protection.** No financial data is collected (D4). The random sub-id carries no user id, trip id or device id (08-affiliate-revenue.md section 7.2). Click logs stay within the existing privacy policy wording; add card offers to the affiliate section of the policy and to the App Privacy answers if anything changes (it should not).
7. **Apple.** Guideline review for financial offers (verify the text); no dark patterns; the in-app browser with visible chrome; no claim that an application unlocks anything.
8. **Minors and eligibility.** Offers state issuer eligibility as the issuer states it; Hermi does not collect age, so the terms text and the destination page carry eligibility; the section is not shown to guest accounts.
9. **Incentives.** No user incentive for applying (cashback rule above); no link between offers and app features.
10. **Complaint and takedown.** A reported offer can be paused in one action; issuer takedown requests are honored the same day; a record of each request is kept.

## 10. Analytics

Events in section 6. Metrics: users who opened the Money item, offers viewed per opener, offer opens (click-through), approvals and approval rate from the network, revenue per 1,000 MAU, opt-in rate (users who tapped Show partner offers), withdrawal rate, report rate, and trust indicators measured before and after (affiliate hide rate, support tickets with "ads" or "trust" tags, App Store rating, retention of those who saw the section versus those who did not). Stop rule after 6 months: if revenue per 1,000 MAU is under the low end of the model (500 x $100 per 100k MAU, about $0.50 per MAU a year) and the withdrawal rate is above 10%, pause the section and write down why. No experiment may change copy, hide disclosure, reorder by payout or add targeting (the experiments guardrail in 07 section 6.7 applies).

## 11. Tests

- **Consent gate.** Without the `offers` consent `GET /money-offers` reads no offer rows and the client renders only the one-line prompt; granting shows the section, withdrawing collapses it at once; the consent is recorded append-only with the copy version.
- **Placement.** Crawl every screen, list, search, AI response, presentation, share page, PDF and print output: no offer text appears outside the Money item.
- **Order and inclusion.** For shuffled payout values, the order is always alphabetical by issuer and the set never changes with payout; no personalization input is accepted by `GET /money-offers`.
- **Copy integrity.** Snapshot tests: the rendered card contains the approved headline, terms and required disclosures byte for byte; the banned-phrase check rejects a draft containing "pre-approved", "guaranteed", "best"; no model call path exists for offers (static analysis and a test that agent tools never return offer content).
- **Approval rules.** An offer cannot go live without legal approval by a different admin, a terms URL, an expiry and a review date; editing approved copy resets status; expired offers disappear without a release; re-review reminder job fires.
- **Kill and consent.** `card_offers` switch hides all offers within a minute; without the `offers` consent no offer row is read or rendered and withdrawing it collapses the section at once; region not in `regions` hides the offer; guest accounts see none.
- **Privacy.** The outbound URL carries only the random sub-id; `link_clicks` rows hold no financial attribute; the loyalty table stores no numbers; account deletion removes `loyalty_accounts`.
- **Link checker.** A destination that changes host pauses the offer and raises the alert.
- **Grants.** The app role cannot read review, payout or approval columns or `card_offer_reviews`.
- **Accessibility.** Label and commission sentence read before the headline; keyboard and VoiceOver pass on the card.

## 12. Tickets

| ID | Title | Size | Needs | Who |
|---|---|---|---|---|
| P3-082 | Gate review and decision record: MAU, economics quotes, network acceptance, trust metrics, counsel engagement, owner named | M | about 100k MAU | Founder, lawyer |
| P3-083 | Publisher and network onboarding: apply through a specialist network, collect issuer terms and copy rules, sign agreements, create the program and link templates | M | P3-082 | Founder |
| P3-084 | Schema (4.2): offers, review trail, loyalty table, flags, kill switch, grants and policy, tests | M | P3-082 | Engineer |
| P3-085 | Money section UI in Before you go: opt-in prompt and consent, offer cards, labels, states, settings toggle, accessibility | M | P3-084 | Engineer |
| P3-086 | Offers API and compliance enforcement: region and expiry filter, alphabetical order, no personalization, banned-phrase checks, `card_offer` entity type | M | P3-084 | Engineer |
| P3-087 | Tracking: `/go` integration for offers, conversion import mapping, reporting lines, aggregate-only approvals | S | P3-086 | Engineer |
| P3-088 | Loyalty and points-service offers (optional): membership flags without numbers, brand matching from the trip's own items, second flag | S | P3-086 | Engineer |
| P3-089 | Admin offers screen: workflow, approval trail, preview, permissions, alerts, expiry and re-review jobs, link check | L | P3-084 | Engineer |
| P3-090 | Tests and audit: placement crawl, copy integrity, order invariance, approval rules, privacy, grants; counsel review of live copy before first publish | M | P3-085, P3-086, P3-089 | Engineer, lawyer |
| P3-091 | Launch and monitoring: US-only flag at 10% rollout, complaint process, weekly review for the first 8 weeks, 6-month stop rule | S | P3-090 | Founder |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Trust damage: users read it as ads or advice | Medium | High | One place only, alphabetical, no AI, opt-in consent, quiet by design, trust metrics with a stop rule |
| Issuer or network rejects the publisher or the copy | Medium | Medium | Specialist network, written approvals before publish, no rewriting of issuer text |
| Regulatory breach (advertising, consumer finance, financial promotion abroad) | Low | High | Counsel gate (P3-082, P3-090), US only, verbatim copy, two-person approval, expiry and re-review |
| Copy drift or stale terms | Medium | High | Locked copy, version trail, expiry and re-review dates, link checker, alerts |
| Drift toward advice ("best card") | Medium | High | Design rules D2 and D3, banned phrases, placement and order tests, no AI path |
| Low revenue per MAU (section 1.2 is an upper bound) | Medium | Low | Decision gate requires 3 times cost coverage at the low end; stop rule after 6 months |
| Apple review objection to credit offers | Low | Medium | Reviewer notes, in-app browser, re-read the financial-products guideline on submission day |
| Data misuse concern | Low | High | No financial data collected, random sub-id only, no targeting |
