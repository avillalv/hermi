# Pack 02: Hermi for Advisors

Part of [Phase 3: scale](README.md). Tickets P3-015 to P3-034. Written 2026-09-30.

| | |
|---|---|
| Feature flag | `advisor_workspaces` (created by this pack, off) |
| Needs | 15 advisor interviews before any code. Terms and a data-processing addendum reviewed by a lawyer (light review). A part-time support and advisor-success contractor at about 100 seats. No funding. |
| Builds on | Phase 1: presentation mode, PDF export, share links, roles, Stripe webhook endpoint, entitlement resolver, admin console. Phase 2: the [concierge lane](../phase-2-growth/07-concierge-lane.md) (creates `concierge_requests`, which this pack links to organizations). |
| Source names | Phase 1 files call this "year 2" and "Phase 4", tickets WF-107 and WF-108. Spec of record: [07 section 11.4 (full spec)](../reference-full-spec/07-monetization-spec.md), [01 section 4.18 (full spec)](../reference-full-spec/01-product-spec.md), [03 section 5.19 (full spec)](../reference-full-spec/03-database-schema.md), [04 section 5.24 (full spec)](../reference-full-spec/04-api-spec.md). Those are summary level; this pack is the detailed contract. |

## 1. Goal and revenue case

**Goal.** A web product for independent travel advisors: a workspace per client trip, presentations under the advisor's own brand, priced proposals a client can accept, a commission tracker, and Hermi's fare and research tools with source links. Sold by the seat through Stripe on the web, not the App Store. Hermi holds no host-agency credentials, books nothing for the advisor, and takes no share of the advisor's commissions.

**Why it is the largest Phase 3 line.** Consumer subscriptions top out near $149k in base year 5; advisors earn more per person and are a business customer who pays on the web, so Apple's 15% does not apply (09 section 3.4).

**Price.** $29 a seat a month, or $24 a seat a month billed annually ($288 a seat a year). Incumbents (reported, verify): Tern $49 monthly or $35 annual, Travefy from $39 a month, TravelJoy from $19 a month, Safari Portal $199 to $299 a month per team.

**Net per seat.** Blended $27 a month x 12 x 0.97 = $314.28 a year (3% card fees, Stripe Tax on top where collected).

| Average paid seats | Y1 | Y2 | Y3 | Y4 | Y5 |
|---|---|---|---|---|---|
| Conservative | 0 | 0 | 10 | 30 | 60 |
| Base | 0 | 0 | 60 | 200 | 450 |
| Ambitious | 0 | 100 | 400 | 1,000 | 2,000 |

Revenue = seats x $314.28. Base: Y3 $18.9k, Y4 $62.9k, Y5 $141.4k (450 seats is 0.75% of the 60k core advisors the plan uses; trade reports say 310,000 US advisors and Fora says 15,000, so definitions differ). Conservative Y5 $18.9k. Ambitious Y2 to Y5: $31.4k, $125.7k, $314.3k, $628.6k (2,000 seats is 3.3%). The pilot has under 10 average seats and is modeled as zero in the base case.

**Costs and margin.**

- Variable: the seat plan row in 03 section 11.1 grants 150 credits a month and a $3.40 monthly ceiling. With infrastructure ($0.14) the worst case is $3.54 a month against $26.19 net, a margin of 86%. 09 assumes a Plus-level allowance (60 credits, $2.25 ceiling, $2.39 worst case, 91% margin, 96% at $1.00 typical use). The 03 seed is the default here because the pilot should not starve advisors of research; P3-033 measures real use and either keeps 150 or drops to 60 (both are `UPDATE plans` edits, not code).
- Fixed: support about 10 hours a week per 100 seats (assumption), on top of the consumer load. Add a contractor at roughly 100 seats.
- Support economics: 100 seats net about 100 x $26.19 x 12 = $31.4k a year; 10 hours a week is 520 hours a year, about $20.8k at an assumed $40 an hour, so a contractor is affordable from seat revenue at roughly 100 seats and not before. Budget it from seat revenue, not from consumer revenue.

**What would break the case.** Host agencies bundle free tools and cap what advisors pay; part-time advisors churn; 15 interviews say the price is wrong. All three are tested before the build (P3-015).

**Differentiator to test.** Fares and research with source links an advisor can show a client, which no incumbent gives. Go to market: host-agency partnerships, advisor communities, content. No paid ads are assumed.

## 2. Design decisions

| # | Decision | Default and reason |
|---|---|---|
| D1 | Web only | Advisors buy, sign in and work on the web. The iOS app does not sell seats, does not link to the purchase page (Apple 3.1.1) and never shows advisor pricing. Advisors can open client trips in the app as ordinary members. |
| D2 | Organization, not solo | Every advisor belongs to an `advisor_orgs` row (a solo advisor is an org of one). Seats, branding, billing and data belong to the org. |
| D3 | Client trips are real trips | A client trip is an ordinary `trips` row owned by the advisor user; the client joins as `editor` or `viewer` through `trip_members` (03 section 5.19). No separate data store, so all Phase 1 features work. |
| D4 | Seat gives pro-level limits on client trips only | As in 03 section 7.1 (`advisor` CTE): an active or past-due seat raises limits on the org's client trips. The advisor's own personal trips stay on whatever tier they hold. Clients need no paid plan. |
| D5 | Private advisor notes are not trip data | They live in `advisor_notes`, visible to org seats only, so a client who is a trip member can never read them. |
| D6 | Hermi takes no commission | The tracker records what the advisor says they earn. Hermi never pays, collects or advises on commission. |
| D7 | Read-only, never deleted | After failed payment and 14 days of Stripe retries, seats become `read_only`: view and export work, new clients and edits stop. Data is never deleted and is exportable at all times. |
| D8 | Card required | No card-free trial (07 section 11.4). A design-partner pilot uses comped seats instead (`entitlements.source = 'comp'` is not used; the seat is created with a 100% coupon on the Stripe subscription so the billing path is tested). |

## 3. User stories and acceptance criteria

**A-1. Create an organization and pay.**
As an advisor, I want to start my agency workspace in minutes, so that I can work today.
- From `hermi.world/advisors` (web only) sign in, name the organization, optionally enter the host agency name and its IATAN or CLIA number, choose monthly or annual, enter business details (VAT id where relevant) and pay through Stripe Checkout.
- On success `advisor_orgs`, an `admin` seat for the owner, and the subscription exist; the workspace opens. Failure to pay leaves nothing active.
- Stripe Tax computes tax; the invoice shows the org name and VAT id.

**A-2. Add and remove seats.**
As an org admin, I want to invite colleagues, so that the team shares clients.
- Invite by email; the seat is `invited` until accepted (unpaid until accepted). Adding an accepted seat changes the Stripe quantity with proration; removing one prorates a credit at the next invoice.
- Removing a seat revokes that person's access to org clients and trips at once; their own personal trips are untouched. The removed advisor's client trips stay in the org (ownership transfers to an org admin by the API before the seat ends).

**A-3. Client workspace.**
As an advisor, I want a home for each client, so that nothing gets lost.
- `POST /advisor-orgs/{org}/clients` creates an `advisor_clients` row (prospect, active, archived) with contact details and notes.
- "Create trip for client" makes a trip owned by the advisor with the client's name as the traveler; the client is invited as `editor` or `viewer` by email or link and needs no paid plan.
- Private notes and the commission fields are visible only to org seats (never to the client).
- The client can export their trip and leave at any time; leaving never deletes the advisor's record of the engagement.

**A-4. Branded presentation.**
As an advisor, I want my logo and colors on what the client sees, so that I look professional.
- Org brand: logo, two colors checked for contrast, contact line, optional tagline. Applied to presentation mode, the share page, the PDF and proposals.
- The "Made with Hermi" footer is hidden (seat limit `hide_presentation_footer`); a small "Planned with Hermi" line is allowed only if the org leaves it on.
- Partner-link disclosure wording never changes and still prints wherever links appear.

**A-5. Proposals.**
As an advisor, I want to send a priced set of options, so that the client can choose and approve.
- A proposal belongs to a client and trip, has a title, an intro, up to 4 options (each a named package with a price, inclusions, terms and optional linked itinerary days or stays), a validity date and the advisor's commission disclosure text when the org chooses to show it.
- A share link with the org's branding lets the client view, pick an option and press Accept or Decline with an optional note. No payment is taken; it records the client's decision and emails the advisor. The advisor, not Hermi, contracts with the client.
- Statuses: draft, sent, accepted, declined, expired. Editing a sent proposal creates a new version; the client sees the latest and the history is kept.

**A-6. Commission tracking.**
As an advisor, I want to know what I am owed and what arrived, so that I can run the business.
- A booking line per client trip: supplier, confirmation number, booked value, expected commission, status (quoted, booked, travelled, commissionable, paid, cancelled), paid date, received amount.
- Totals per client, per month and per supplier; CSV export; expected versus received with days outstanding (commissions often arrive 30 to 90 days after travel).
- Hermi records only what is entered. No passport numbers or card numbers are stored; note fields warn when text looks like one (P3-032).

**A-6b. Templates.**
As an advisor, I want to reuse a trip skeleton, so that I am not retyping.
- Save a client trip as an org template (days, items, notes marked shareable, checklist); creating from a template copies it without client data.

**A-7. Dunning and cancellation.**
As an org admin, I want clear billing states, so that I am not surprised.
- Failed payment: banner and email at once, Stripe smart retries for 14 days, seats stay active during retries, then `read_only`.
- Cancel in the Stripe customer portal; access runs to the period end, then read-only and export only.
- Renewal reminder email before each annual renewal and one-click cancel (state auto-renew rules, [10 section 3.10 (full spec)](../reference-full-spec/10-quality-security-launch.md)).

**A-8. Leave and export.**
As an advisor or a client, I want to take my data, so that I am not locked in.
- Org export (clients, trips, proposals, commission lines) as JSON and CSV at any time, including in read-only state. Client export and leave per F-COL (Phase 1 product spec).

## 4. Database additions

### 4.1 Defined in the full 03 (reuse verbatim)

03 section 5.19 defines the three organization tables. Phase 1 dropped them (Phase 1 03 section 1.1) and Phase 2 does not create them, so this pack creates them. Apply 4.1 and 4.2 in one Alembic revision (4.2 amends two of these definitions).

```sql
CREATE TABLE advisor_orgs (
  id                       uuid PRIMARY KEY DEFAULT uuidv7(),
  name                     text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
  slug                     text NOT NULL,
  owner_user_id            uuid REFERENCES users (id) ON DELETE SET NULL,
  host_agency_name         text,
  host_agency_id           text,                                      -- IATAN or CLIA number of the host agency, when supplied
  billing_email            citext,
  stripe_customer_id       text,
  brand                    jsonb NOT NULL DEFAULT '{}'::jsonb,        -- logo key, colors, contact line for branded presentations
  commission_split_bps     integer NOT NULL DEFAULT 0 CHECK (commission_split_bps BETWEEN 0 AND 10000),
  status                   text NOT NULL DEFAULT 'active',
  created_at               timestamptz NOT NULL DEFAULT now(),
  updated_at               timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_advisor_orgs_slug UNIQUE (slug),
  CONSTRAINT ck_advisor_orgs_status CHECK (status IN ('active', 'suspended', 'closed'))
);
CREATE UNIQUE INDEX uq_advisor_orgs_stripe_customer ON advisor_orgs (stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
SELECT add_updated_at_trigger('advisor_orgs');



CREATE TABLE advisor_seats (
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id            uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  user_id                   uuid REFERENCES users (id) ON DELETE CASCADE,         -- null while an invite is pending
  invited_email             citext,
  role                      text NOT NULL DEFAULT 'advisor',
  billing_period            text NOT NULL DEFAULT 'month',
  stripe_subscription_id    text,
  stripe_subscription_item_id text,
  status                    text NOT NULL DEFAULT 'active',
  started_at                timestamptz NOT NULL DEFAULT now(),
  ended_at                  timestamptz,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_advisor_seats_role CHECK (role IN ('admin', 'advisor')),
  CONSTRAINT ck_advisor_seats_period CHECK (billing_period IN ('month', 'year')),
  CONSTRAINT ck_advisor_seats_status CHECK (status IN ('invited', 'active', 'past_due', 'ended')),
  CONSTRAINT ck_advisor_seats_user_or_email CHECK (user_id IS NOT NULL OR invited_email IS NOT NULL)
);
CREATE UNIQUE INDEX uq_advisor_seats_org_user ON advisor_seats (advisor_org_id, user_id) WHERE user_id IS NOT NULL AND status <> 'ended';
CREATE INDEX ix_advisor_seats_user ON advisor_seats (user_id) WHERE user_id IS NOT NULL;
SELECT add_updated_at_trigger('advisor_seats');

CREATE TABLE advisor_clients (
  id                          uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id              uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  advisor_user_id             uuid REFERENCES users (id) ON DELETE SET NULL,      -- the advisor who owns the relationship
  client_user_id              uuid REFERENCES users (id) ON DELETE SET NULL,      -- set when the client has a Hermi account
  client_name                 text NOT NULL CHECK (char_length(client_name) BETWEEN 1 AND 120),
  client_email                citext,
  trip_id                     uuid REFERENCES trips (id) ON DELETE SET NULL,
  status                      text NOT NULL DEFAULT 'prospect',
  proposal_status             text NOT NULL DEFAULT 'none',
  commission_expected_minor   bigint,
  commission_received_minor   bigint,
  commission_currency         currency_code,
  notes                       text NOT NULL DEFAULT '',
  created_at                  timestamptz NOT NULL DEFAULT now(),
  updated_at                  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_advisor_clients_status CHECK (status IN ('prospect', 'active', 'archived')),
  CONSTRAINT ck_advisor_clients_proposal CHECK (proposal_status IN ('none', 'draft', 'sent', 'accepted', 'declined'))
);
CREATE INDEX ix_advisor_clients_org ON advisor_clients (advisor_org_id, status);
CREATE INDEX ix_advisor_clients_advisor ON advisor_clients (advisor_user_id) WHERE advisor_user_id IS NOT NULL;
CREATE INDEX ix_advisor_clients_trip ON advisor_clients (trip_id) WHERE trip_id IS NOT NULL;
SELECT add_updated_at_trigger('advisor_clients');

-- concierge_requests exists from Phase 2; the full 03 adds its advisor link here (Phase 1 03 section 14).
ALTER TABLE concierge_requests ADD COLUMN advisor_org_id uuid REFERENCES advisor_orgs (id) ON DELETE SET NULL;
```

Plan, product and constraint changes from the full 03 (sections 5.12, 5.14 and 11; none of these rows exist before this pack, because Phase 1 seeds only Phase 1 plan codes):

```sql
ALTER TABLE plans DROP CONSTRAINT ck_plans_kind;
ALTER TABLE plans ADD CONSTRAINT ck_plans_kind CHECK (kind IN ('tier', 'pass', 'credit_pack', 'advisor_seat'));
ALTER TABLE entitlements DROP CONSTRAINT ck_entitlements_source;
ALTER TABLE entitlements ADD CONSTRAINT ck_entitlements_source CHECK (source IN ('none', 'subscription', 'household', 'comp', 'advisor'));   -- 'household' from Phase 2
ALTER TABLE store_transactions DROP CONSTRAINT ck_store_transactions_kind;
ALTER TABLE store_transactions ADD CONSTRAINT ck_store_transactions_kind
  CHECK (kind IN ('subscription', 'pass', 'credit_pack', 'advisor_seat', 'group_payment', 'print_order'));   -- keep the values other packs add

-- Seat plan: pro-level limits on the org's client trips only, 150 credits a month, $3.40 monthly and $0.40 daily ceilings (defaults the admin can change).
INSERT INTO plans (code, kind, name, rank, monthly_credits, credits_granted, credits_valid_days, duration_days, feature_flag_key, is_active, sort_order, limits) VALUES
('advisor_seat', 'advisor_seat', 'Hermi for Advisors seat', 35, 150, 0, NULL, NULL, 'advisor_workspaces', false, 70,
 '{"active_trips":50,"active_trips_bonus":0,"routes_per_trip":8,"live_routes":6,"live_window_days":120,"price_alerts":6,"live_alerts":true,
   "collaborators":12,"travelers_per_trip":12,"can_invite":true,"saved_lodging_per_trip":100,"lodging_compare":4,
   "places_searches_per_day":200,"polls":true,"cost_splitting":true,"room_block_request":false,"group_payments":false,
   "hide_presentation_footer":true,"scheduled_routines":false,"priority_queue":false,"credit_rollover_cap":0,"taster_agent_runs":0,
   "monthly_ceiling_micros":3400000,"daily_ceiling_micros":400000}')
ON CONFLICT (code) DO NOTHING;

INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('advisor_seat_monthly', 'stripe', 'advisor_seat', 'month',  2900, 'USD', 0, false),
('advisor_seat_annual',  'stripe', 'advisor_seat', 'year',  28800, 'USD', 0, false)     -- $24 a seat a month, billed yearly
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('advisor_workspaces', 'Hermi for Advisors', false, 100, '{}', '{}')
ON CONFLICT (key) DO NOTHING;
```

Entitlement query. Add the advisor branch to the effective-entitlement query that Phase 1 built (full 03 section 7.1): the seat applies to client trips only, through this extra CTE and union branch, and the owner-tier CTE must not treat an advisor-sourced entitlement as a personal tier.

```sql
-- in owner_tier: the seat never raises the advisor's own trips
--   JOIN plans pl ON pl.code = CASE WHEN e.source = 'advisor' THEN 'free' ELSE COALESCE(e.tier_code, 'free') END
), advisor AS (                                         -- an advisor seat gives pro-level limits on the org's client trips only
  SELECT t.id AS trip_id, pl.code, pl.limits
    FROM trips t
    JOIN advisor_clients c ON c.trip_id = t.id
    JOIN advisor_seats s ON s.advisor_org_id = c.advisor_org_id AND s.user_id = t.owner_user_id AND s.status IN ('active', 'past_due')
    JOIN plans pl ON pl.code = 'advisor_seat'
   WHERE t.id = :trip_id AND t.deleted_at IS NULL
-- and in candidates:
--   UNION ALL
--   SELECT 'advisor', code, limits FROM advisor
```

The daily allowance job (03 section 7.5, "monthly allowance grant for entitlements that have no store billing cycle") must include `e.source = 'advisor'`; the rest of the plumbing (`credit_grants.period_key` idempotency, per-user ceilings) is unchanged. `my_advisor_orgs()` and the row policies are in 4.2.

### 4.2 New in this pack

```sql
-- Same Alembic revision as 4.1 (p3_advisors). Every table carries its own grants and row policies (Phase 1 03 section 10: tables added after the RLS revision).

ALTER TABLE advisor_seats DROP CONSTRAINT ck_advisor_seats_status;
ALTER TABLE advisor_seats ADD CONSTRAINT ck_advisor_seats_status
  CHECK (status IN ('invited', 'active', 'past_due', 'read_only', 'ended'));   -- read_only: dunning over (D7); not counted by the entitlement CTE

ALTER TABLE advisor_orgs
  ADD COLUMN vat_id            text,
  ADD COLUMN country_code      country_code2,
  ADD COLUMN billing_state     text NOT NULL DEFAULT 'ok',        -- ok, past_due, read_only, canceled
  ADD COLUMN data_processing_accepted_at timestamptz,
  ADD COLUMN terms_version     text,
  ADD CONSTRAINT ck_advisor_orgs_billing_state CHECK (billing_state IN ('ok', 'past_due', 'read_only', 'canceled'));

-- One Stripe subscription per org per billing period; seats are the quantity.
CREATE TABLE advisor_subscriptions (
  id                     uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id         uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  billing_period         text NOT NULL,
  stripe_subscription_id text NOT NULL,
  stripe_item_id         text NOT NULL,
  quantity               integer NOT NULL CHECK (quantity >= 0),
  status                 text NOT NULL DEFAULT 'active',
  current_period_end     timestamptz,
  cancel_at_period_end   boolean NOT NULL DEFAULT false,
  coupon_code            text,                                      -- design-partner pilot (D8)
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_advisor_subscriptions_period CHECK (billing_period IN ('month', 'year')),
  CONSTRAINT ck_advisor_subscriptions_status CHECK (status IN ('active', 'past_due', 'canceled', 'incomplete')),
  CONSTRAINT uq_advisor_subscriptions_stripe UNIQUE (stripe_subscription_id),
  CONSTRAINT uq_advisor_subscriptions_org_period UNIQUE (advisor_org_id, billing_period)
);
SELECT add_updated_at_trigger('advisor_subscriptions');

-- Private advisor notes: visible to org seats only, never to trip members who are clients.
CREATE TABLE advisor_notes (
  id               uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id   uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  client_id        uuid REFERENCES advisor_clients (id) ON DELETE CASCADE,
  trip_id          uuid REFERENCES trips (id) ON DELETE CASCADE,
  item_id          uuid REFERENCES itinerary_items (id) ON DELETE CASCADE,
  author_user_id   uuid REFERENCES users (id) ON DELETE SET NULL,
  body             text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 8000),
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_advisor_notes_target CHECK (client_id IS NOT NULL OR trip_id IS NOT NULL)
);
CREATE INDEX ix_advisor_notes_org ON advisor_notes (advisor_org_id, created_at DESC);
CREATE INDEX ix_advisor_notes_trip ON advisor_notes (trip_id) WHERE trip_id IS NOT NULL;
SELECT add_updated_at_trigger('advisor_notes');

CREATE TABLE advisor_proposals (
  id                uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id    uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  client_id         uuid NOT NULL REFERENCES advisor_clients (id) ON DELETE CASCADE,
  trip_id           uuid REFERENCES trips (id) ON DELETE SET NULL,
  created_by        uuid REFERENCES users (id) ON DELETE SET NULL,
  title             text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 160),
  intro             text NOT NULL DEFAULT '',
  options           jsonb NOT NULL DEFAULT '[]'::jsonb,              -- [{"key","name","price_minor","inclusions":[],"terms","day_ids":[],"lodging_ids":[]}], read whole, 1 to 4 entries
  currency          currency_code NOT NULL,
  show_commission_note boolean NOT NULL DEFAULT false,
  commission_note   text NOT NULL DEFAULT '',
  status            text NOT NULL DEFAULT 'draft',
  version           integer NOT NULL DEFAULT 1,
  share_token_hash  bytea,                                           -- hash of the link token; the token itself is shown once
  valid_until       date,
  sent_at           timestamptz,
  responded_at      timestamptz,
  chosen_option_key text,
  response_note     text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_advisor_proposals_status CHECK (status IN ('draft', 'sent', 'accepted', 'declined', 'expired')),
  CONSTRAINT ck_advisor_proposals_options CHECK (jsonb_typeof(options) = 'array' AND jsonb_array_length(options) <= 4),
  CONSTRAINT ck_advisor_proposals_response CHECK (status NOT IN ('accepted', 'declined') OR responded_at IS NOT NULL)
);
CREATE UNIQUE INDEX uq_advisor_proposals_token ON advisor_proposals (share_token_hash) WHERE share_token_hash IS NOT NULL;
CREATE INDEX ix_advisor_proposals_client ON advisor_proposals (client_id, status);
SELECT add_version_trigger('advisor_proposals');
SELECT add_updated_at_trigger('advisor_proposals');

CREATE TABLE advisor_bookings (                                     -- commission tracking, entered by the advisor
  id                          uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id              uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  client_id                   uuid NOT NULL REFERENCES advisor_clients (id) ON DELETE CASCADE,
  trip_id                     uuid REFERENCES trips (id) ON DELETE SET NULL,
  advisor_user_id             uuid REFERENCES users (id) ON DELETE SET NULL,
  supplier_name               text NOT NULL CHECK (char_length(supplier_name) BETWEEN 1 AND 120),
  supplier_type               text NOT NULL DEFAULT 'hotel',
  confirmation_ref            text,
  travel_start                date,
  travel_end                  date,
  booked_minor                bigint CHECK (booked_minor IS NULL OR booked_minor >= 0),
  currency                    currency_code NOT NULL,
  commission_expected_minor   bigint CHECK (commission_expected_minor IS NULL OR commission_expected_minor >= 0),
  commission_received_minor   bigint CHECK (commission_received_minor IS NULL OR commission_received_minor >= 0),
  status                      text NOT NULL DEFAULT 'booked',
  commission_paid_on          date,
  notes                       text NOT NULL DEFAULT '',
  created_at                  timestamptz NOT NULL DEFAULT now(),
  updated_at                  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_advisor_bookings_type CHECK (supplier_type IN ('hotel', 'cruise', 'tour', 'air', 'rail', 'car', 'package', 'insurance', 'other')),
  CONSTRAINT ck_advisor_bookings_status CHECK (status IN ('quoted', 'booked', 'travelled', 'commissionable', 'paid', 'cancelled')),
  CONSTRAINT ck_advisor_bookings_dates CHECK (travel_end IS NULL OR travel_start IS NULL OR travel_end >= travel_start)
);
CREATE INDEX ix_advisor_bookings_org ON advisor_bookings (advisor_org_id, status);
CREATE INDEX ix_advisor_bookings_client ON advisor_bookings (client_id);
SELECT add_updated_at_trigger('advisor_bookings');

CREATE TABLE advisor_templates (
  id               uuid PRIMARY KEY DEFAULT uuidv7(),
  advisor_org_id   uuid NOT NULL REFERENCES advisor_orgs (id) ON DELETE CASCADE,
  created_by       uuid REFERENCES users (id) ON DELETE SET NULL,
  name             text NOT NULL CHECK (char_length(name) BETWEEN 1 AND 120),
  destination_name text,
  day_count        smallint,
  skeleton         jsonb NOT NULL,                                   -- days, items, shareable notes, checklist; no client data
  version          integer NOT NULL DEFAULT 1,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_advisor_templates_org ON advisor_templates (advisor_org_id);
SELECT add_version_trigger('advisor_templates');
SELECT add_updated_at_trigger('advisor_templates');

-- Row-level security: every org table is visible to, and editable by, seat holders of that org only.
CREATE FUNCTION my_advisor_orgs() RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT advisor_org_id FROM advisor_seats
   WHERE user_id = app_user_id() AND status IN ('active', 'past_due', 'read_only')
$$;
CREATE FUNCTION my_writable_advisor_orgs() RETURNS SETOF uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT s.advisor_org_id FROM advisor_seats s JOIN advisor_orgs o ON o.id = s.advisor_org_id
   WHERE s.user_id = app_user_id() AND s.status IN ('active', 'past_due') AND o.status = 'active'
$$;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['advisor_orgs', 'advisor_seats', 'advisor_clients', 'advisor_notes', 'advisor_proposals',
                           'advisor_bookings', 'advisor_templates', 'advisor_subscriptions'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;
CREATE POLICY advisor_orgs_select ON advisor_orgs FOR SELECT USING (id IN (SELECT my_advisor_orgs()));
CREATE POLICY advisor_seats_select ON advisor_seats FOR SELECT USING (advisor_org_id IN (SELECT my_advisor_orgs()) OR user_id = (SELECT app_user_id()));
CREATE POLICY advisor_clients_select ON advisor_clients FOR SELECT USING (advisor_org_id IN (SELECT my_advisor_orgs()));
CREATE POLICY advisor_clients_write ON advisor_clients FOR ALL USING (advisor_org_id IN (SELECT my_writable_advisor_orgs()))
  WITH CHECK (advisor_org_id IN (SELECT my_writable_advisor_orgs()));
-- The same select and write pair for advisor_notes, advisor_proposals, advisor_bookings and advisor_templates (generate in a loop like 03 section 6.4).
-- advisor_subscriptions and billing columns are written by the billing service (worker role); the app role only reads its own org's rows.
REVOKE INSERT, UPDATE, DELETE ON advisor_orgs, advisor_seats, advisor_subscriptions FROM hermi_app;
GRANT UPDATE (name, brand, host_agency_name, host_agency_id, billing_email, vat_id) ON advisor_orgs TO hermi_app;   -- org admins only, enforced in the service layer
```

Brand shape in `advisor_orgs.brand` (jsonb): `{"logo_key": "r2/key", "primary": "#RRGGBB", "secondary": "#RRGGBB", "contact_line": "...", "tagline": "...", "show_powered_by": true}`; colors must satisfy `hex_color` and a contrast check in the service layer (AA on the paper background).

Client-visible versus org-private fields: a client who is a trip member can read the trip through ordinary `trip_members` policies and can read a proposal only through its share link. `advisor_notes`, `advisor_bookings`, `advisor_clients.notes` and the commission fields have no trip-member policy, so they are invisible to clients by construction (cross-tenant test in section 11).

Retention (03 section 8): `advisor_clients` and its children 24 months after the client is archived, `advisor_*` until an admin removes them or the org closes; `advisor_bookings` 7 years for financial fields, contact fields scrubbed when the client row is purged.

## 5. API additions

Base `/v1`, all behind the `advisor_workspaces` flag (404 when off, [04 section 5.24 (full spec)](../reference-full-spec/04-api-spec.md)). Advisor routes require a seat in the org; write routes require `status` active or past_due and the org not read-only.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /advisor-orgs` | user (web) | flag | `{ name, host_agency_name?, host_agency_id?, billing_period, country_code, vat_id?, accept_terms: true }` to `{ org, checkout_url }` | Creates the org (status `active`, billing pending), a Stripe customer and a Checkout session (quantity 1). `409 already_member` if the user already owns one. |
| `GET /advisor-orgs/{org_id}` | seat | none | to `AdvisorOrg` | |
| `PATCH /advisor-orgs/{org_id}` | org admin | versioned | `{ name?, brand?, host_agency_name?, host_agency_id?, billing_email?, vat_id? }` | Brand changes are validated (contrast, logo type and size up to 2 MB). |
| `POST /advisor-orgs/{org_id}/logo` | org admin | 5 an hour | multipart to `{ logo_key }` | Type and size checks, stored in R2. |
| `GET /advisor-orgs/{org_id}/billing` | org admin | none | to `{ subscriptions, seats_paid, portal_url?, billing_state }` | `portal_url` is a Stripe customer portal session. |
| `POST /advisor-orgs/{org_id}/seats` | org admin | none | `{ invites: { email, role }[] }` to `Seat[]` | Creates `invited` seats and sends email. Quantity changes to Stripe on acceptance. |
| `PATCH /advisor-orgs/{org_id}/seats/{seat_id}` | org admin | none | `{ role?, billing_period? }` | Role change; period change moves the seat between subscriptions. |
| `DELETE /advisor-orgs/{org_id}/seats/{seat_id}` | org admin | none | 204 | Transfers owned client trips to an org admin first, sets `ended`, reduces the Stripe quantity with proration. The last admin cannot be removed. |
| `POST /advisor-seat-invites/{token}/accept` | user | token | to `Seat` | Links the signed-in user; adds quantity in Stripe. |
| `GET /advisor-orgs/{org_id}/clients` | seat | none | `?status=&q=&limit&cursor` to `Page<AdvisorClient>` | |
| `POST /advisor-orgs/{org_id}/clients` | seat (write) | none | `ClientIn` to 201 | |
| `PATCH /advisor-orgs/{org_id}/clients/{client_id}` | seat (write) | versioned | partial `ClientIn` | Archive sets `status = 'archived'`. |
| `POST /advisor-orgs/{org_id}/clients/{client_id}/trips` | seat (write) | plan limit `active_trips` of the seat | `{ name, destination?, start_date?, end_date?, template_id?, client_role: "editor" \| "viewer", invite: boolean }` to 201 `Trip` | Creates a trip owned by the advisor, links `advisor_clients.trip_id`, optionally applies a template and invites the client. |
| `GET/POST /advisor-orgs/{org_id}/notes` and `PATCH/DELETE /advisor-notes/{id}` | seat | none | `{ client_id?, trip_id?, item_id?, body }` | Never returned by any trip route. |
| `GET/POST /advisor-orgs/{org_id}/proposals`, `GET/PATCH /proposals/{id}` | seat | none | `ProposalIn` | Edits to a `sent` proposal bump `version` and notify the client if they opened it. |
| `POST /proposals/{id}/send` | seat (write) | status `draft` | `{ valid_until?, email_client?: boolean }` to `{ share_url }` | Generates the token (shown once, only the hash stored), sets `sent`, emails the client. |
| `GET /proposals/shared/{token}` | none | 60 an hour per IP | to `PublicProposal` | Branded, read only. Hides advisor notes and commission unless `show_commission_note`. Expired or revoked returns `410 share_link_revoked`. |
| `POST /proposals/shared/{token}/respond` | none | once per proposal version | `{ decision: "accept" \| "decline", option_key?, note? }` | Records the response, emails the advisor. No payment. |
| `GET/POST /advisor-orgs/{org_id}/bookings`, `PATCH/DELETE /advisor-bookings/{id}` | seat | none | `BookingIn` | Amounts are minor units plus currency. |
| `GET /advisor-orgs/{org_id}/commissions` | org admin or own rows | none | `?from&to&group=client\|supplier\|month` to `CommissionReport` | `?format=csv` for export. Expected versus received and days outstanding. |
| `GET/POST /advisor-orgs/{org_id}/templates`, `POST /trips/{trip_id}/save-as-template` | seat | none | `{ name }` | Strips client data, private notes and personal traveler names. |
| `GET /advisor-orgs/{org_id}/export` | org admin | once a minute | to 202 `{ export_id }` | JSON and CSV bundle by email link; works in `read_only`. |
| `GET /presentation/{trip_id}/branded` | member | none | to `PresentationData` with `brand` | The existing presentation data plus the org brand when the trip is an org client trip. |

```ts
type ClientIn = { client_name: string; client_email?: string; status?: "prospect" | "active" | "archived"; notes?: string }
type ProposalIn = {
  client_id: Uuid; trip_id?: Uuid; title: string; intro?: string; currency: string; valid_until?: string
  options: { name: string; price: Money; inclusions: string[]; terms?: string; day_ids?: Uuid[]; lodging_ids?: Uuid[] }[]
  show_commission_note?: boolean; commission_note?: string
}
type BookingIn = {
  client_id: Uuid; trip_id?: Uuid; supplier_name: string; supplier_type: string; confirmation_ref?: string
  travel_start?: string; travel_end?: string; booked?: Money; commission_expected?: Money; commission_received?: Money
  status?: "quoted" | "booked" | "travelled" | "commissionable" | "paid" | "cancelled"; commission_paid_on?: string
}
```

Webhooks ([04 section 6](../phase-1-launch/04-api-spec.md), `POST /webhooks/stripe`): `checkout.session.completed` (create subscription rows, activate the org), `customer.subscription.created`, `.updated`, `.deleted`, `invoice.paid`, `invoice.payment_failed`. Handlers update `advisor_subscriptions`, `advisor_seats` and `advisor_orgs.billing_state`, write `store_transactions` (`store = 'stripe'`, `kind = 'advisor_seat'`), and call the entitlement recompute for each seat holder. Idempotent by event id.

Entitlement and credits: nothing new to build beyond wiring. A seat holder's client trips resolve to pro-level limits through the `advisor` CTE; the daily grant job writes the monthly credit allowance for `advisor` entitlements; credits are charged to the advisor who starts the action; the $3.40 monthly and $0.40 daily ceilings apply per seat.

## 6. UI screens

A separate web surface under `/advisors` (React route tree, same design tokens as the consumer app, [05](../phase-1-launch/05-ui-ux-spec.md)). Consumer screens never show advisor branding except when a client opens an advisor's trip.

**Advisor home.** Purpose: what needs attention today. Layout: left navigation (Clients, Proposals, Commissions, Templates, Team, Brand, Billing); main area with "Needs a reply" (proposals viewed, client comments), upcoming departures in 30 days, commissions awaiting payment, and a "New client" action. Empty: "Add your first client. Everything you build for them stays in one place." Events: `advisor_home_viewed`.

**Clients list and client page.** List with status filter and search. Client page: tabs Trip (opens the normal trip UI), Proposals, Bookings, Private notes, Details. Private notes carry a lock icon and the line "Clients cannot see this." The client's invite state (invited, joined, viewing) is shown. Archive and export actions.

**Create trip for client.** Sheet: name, destination, dates, template (optional), client's role (editor or viewer), invite by email or link. Result opens the trip with the org brand active for presentation.

**Branded presentation and share page.** Same slides as Phase 1 presentation mode with the org logo, colors and contact line; no "Made with Hermi" footer by default; "Book the plan" slide off by default for advisor trips (the advisor usually books). PDF export uses the brand. Disclosure sentences stay wherever partner links appear.

**Proposal builder.** Steps: client and trip, options (up to 4 cards with price, inclusions, terms, linked days and stays), preview as the client sees it, send. The preview shows the exact public page. Copy: "You send this. You are the seller, not Hermi." (Advisor-facing; plain statement of roles.) Sent state shows opened, accepted or declined with timestamps.

**Public proposal page.** Branded header, intro, options as cards, validity date, Accept and Decline with an optional note, advisor contact line, commission note only if enabled. No Hermi marketing beyond a small footer the org can keep or remove. Works without sign-in.

**Commissions.** Table of bookings with status chips, filters (client, supplier, month, status), totals (expected, received, outstanding and oldest outstanding days), add and edit sheet, CSV export. Empty: "Track what you book and what you are owed."

**Templates, Team, Brand.** Templates list; Team with seats, roles, invite, remove; Brand with logo upload, two colors with live contrast check, contact line, preview.

**Billing.** Plan, seats paid, next invoice, billing state banner (past due, read only) and "Manage billing" to the Stripe portal, VAT id, invoices. Never shown in the iOS app.

States, accessibility and copy follow Phase 1 rules: loading skeletons, offline read only, errors that say what happened and what to do, tables with real headers, status as text plus icon, money read with currency.

## 7. Billing

- **Stripe Billing**, per-seat quantity subscriptions: monthly price $29, annual price $288 (lookup keys `advisor_seat_monthly`, `advisor_seat_annual`; ids in `STRIPE_ADVISOR_PRICE_ID` and a second variable for annual, add both to `.env.example` and the secrets list).
- **Checkout** for the first purchase, **customer portal** for card, invoices, plan and cancel. Seat adds and removes change quantity with proration (`proration_behavior = create_prorations`).
- **Tax.** Stripe Tax for sales tax and VAT (verify thresholds and registrations); capture business VAT ids; advisors are business customers.
- **Dunning.** Stripe smart retries for 14 days, then the webhook sets seats `read_only` and `billing_state = 'read_only'` (D7). Data is never deleted.
- **Entitlement.** An active or past-due seat gives pro-level limits on the org's client trips only, plus 150 credits a month (03 default; tune in P3-033).
- **Web only.** The iOS app neither sells nor links to seat purchase. Reviewer notes state that advisor sign-up is a separate business product on the web.
- **Design partners.** A Stripe coupon (100% for a stated period) on a real subscription, so the billing and dunning paths are exercised; track `advisor_subscriptions.coupon_code`.
- **Auto-renew rules.** Renewal reminder email before each annual renewal and one-click cancel in the portal ([10 section 3.10 (full spec)](../reference-full-spec/10-quality-security-launch.md)).

## 8. Admin additions

Extends [08](../phase-1-launch/08-admin-control-center.md) (source ticket WF-108).

- **New screen: Advisors (Money group).** Orgs list (name, status, billing state, seats paid, MRR, created, host agency), org detail (seats, clients count, subscriptions, invoices link, last activity, flags), seats list.
- **Actions.** Open in Stripe; suspend or reactivate an org (owner, reason); resend seat invite; extend dunning by up to 14 days (owner); comp a period with a Stripe coupon (owner or finance); transfer ownership of an org's client trips; start an org export for the customer (support); close an org after export (owner, typed confirmation).
- **Permissions.** Read for support, engineer, finance and owner; money actions for finance and owner; suspend and close owner only. Add `advisors.*` permission names to `admin/permissions.py`; the route-permission test must still pass.
- **Support tooling.** Read-only impersonation of an advisor needs the advisor's consent and never exposes client names unless the ticket requires it (audited reveal, like users).
- **Overview and finance.** Add advisor MRR, seats, net revenue per seat, churned seats, seats in dunning, support hours per 100 seats (from the ticket system).
- **Alerts.** Advisor invoice failed, org in dunning more than 10 days, seat count drops more than 10% in a week, cross-org access attempt logged (page).
- **Kill switch.** `advisors.billing` disables new checkouts and seat changes while read and export keep working.

## 9. Legal and compliance

1. **Role.** Hermi is a software vendor, not a seller of travel. Terms say so: advisors are responsible to their clients for bookings, advice, licences, registrations and their own disclosures. Counsel confirms no seller-of-travel registration is triggered by providing a tool.
2. **Client personal data.** The advisor is the controller of client data entered into the workspace and Hermi is the processor. Publish a data-processing addendum (accepted at org creation, `advisor_orgs.data_processing_accepted_at`), list sub-processors, and support deletion and export on request. The client is also a Hermi user when they join a trip; the client can export and leave.
3. **Sensitive data.** Never store passport numbers, card numbers or government ids. Inputs that look like a passport or card number trigger a warning and are masked in logs; the terms forbid storing them. Dates of birth and names appear only as the trip's people fields already do.
4. **Commission disclosure.** Advisors disclose their commissions to clients. The tool lets them add a commission note to a proposal and never hides partner-link disclosure. Hermi records commission but does not advise on it.
5. **Host-agency rules.** Some host agencies restrict outside software or data sharing; the terms put that responsibility on the advisor. Do not name or imply any host agency partnership unless a written agreement exists.
6. **Tax.** Sales tax on SaaS varies by state; use Stripe Tax and verify registration thresholds with an accountant.
7. **Apple.** No sale or purchase link in the iOS app (Guideline 3.1.1); advisors sign in on the web. Re-read the guideline on each submission.
8. **Auto-renew.** Provide reminder and one-click cancel per state rules; state the renewal terms at checkout.
9. **Advertising law.** Branded proposals sent by an advisor are the advisor's advertising; Hermi's own marketing of the product follows the honest-comparison rules (competitor prices are "reported, verify").
10. **Security.** Org isolation is the main risk (tenancy tests in section 11, external review before public launch); proposal share tokens are random, hashed, expiring and rate limited; all uploads are type and size checked.

## 10. Analytics

Events to PostHog: `advisor_org_created {billing_period}`, `advisor_checkout_completed`, `advisor_seat_added`, `advisor_seat_removed`, `advisor_client_created`, `advisor_client_trip_created {template: bool}`, `advisor_presentation_branded_viewed`, `advisor_proposal_sent`, `advisor_proposal_viewed`, `advisor_proposal_responded {decision}`, `advisor_booking_logged {supplier_type}`, `advisor_export_started`, `advisor_billing_failed`.

Metrics (first party, admin finance view): paid seats, MRR, net revenue per seat, seat churn (monthly), activation (a client trip created within 7 days of signup, target 70%), proposals sent per active seat a month, weekly active seats, credits used per seat (drives the 150 versus 60 decision), support hours per 100 seats, share of seats on annual. Base case needs 60 average seats in year 3; the leading indicators are design-partner seats and 30-day activation.

## 11. Tests

- **Tenancy.** The cross-tenant leak test ([10 section 1.3](../phase-1-launch/10-quality-security-launch.md)) is extended: user A in org 1 gets zero rows from every `advisor_*` table belonging to org 2; a client (trip member) gets zero `advisor_notes`, `advisor_bookings` or commission fields; a removed seat loses access on the next request; `my_advisor_orgs()` fails closed with no `app.user_id`.
- **Seat limits and billing.** Fake Stripe: add and remove seats, proration, annual versus monthly subscriptions, failed payment then `read_only` after 14 days, cancel at period end, replayed and reordered webhooks, last admin cannot be removed.
- **Entitlement.** Seat holder gets pro-level limits on client trips, not on personal trips; a past-due seat keeps them; a `read_only` seat loses them; monthly credit grant is idempotent.
- **Proposals.** Token hashed at rest, single-use response per version, expired link returns 410, edit bumps version, hidden fields never serialized, accept and decline emails.
- **Branding.** Contrast validation rejects failing colors; logo size and type limits; the partner-link disclosure renders on branded slides and PDF (snapshot test).
- **Web only.** iOS client header cannot create an org or reach checkout; no purchase link in the app bundle (grep test in CI).
- **Data.** Export completes in `read_only`; template strip removes client data; sensitive-number guard warns.
- **E2E (Playwright, Stripe test mode).** Create org, pay, invite a colleague, create client trip, invite client, send proposal, client accepts, log a booking, export.

## 12. Tickets

| ID | Title | Size | Needs | Who |
|---|---|---|---|---|
| P3-015 | Validation: 15 advisor interviews, price test ($29 and $24 against incumbents), host-agency bundling check, 5 signed design partners | M | none | Founder |
| P3-016 | Schema and RLS (4.2): new tables, `read_only` status, `my_advisor_orgs()` helpers, policies and grants, leak tests | L | P3-015 | Engineer |
| P3-017 | Org creation and Stripe Billing: Checkout, per-seat quantity subscriptions, portal, proration, tax, VAT ids | L | P3-016 | Engineer |
| P3-018 | Stripe webhook handlers for subscriptions and invoices, `advisor_subscriptions`, seat state, dunning to `read_only` | M | P3-017 | Engineer |
| P3-019 | Seat entitlement wiring: advisor branch in the entitlement query, plan and product seeds, credit allowance job, ceilings, activation behind the flag | M | P3-016 | Engineer |
| P3-020 | Client workspaces: clients API, create client trip, invite client, private notes, ownership transfer on seat removal | L | P3-016, P3-019 | Engineer |
| P3-021 | Branded presentation: brand settings, logo upload, themed presentation, share page and PDF, footer rules | M | P3-016 | Engineer |
| P3-022 | Proposals: schema use, builder API, send, public page, respond, versions, emails | L | P3-020, P3-021 | Engineer |
| P3-023 | Commission tracker: bookings API, totals, CSV export, outstanding report | M | P3-020 | Engineer |
| P3-024 | Templates: save as template, create from template, client-data strip | S | P3-020 | Engineer |
| P3-025 | Advisor web shell and screens: home, clients, client page, navigation, states | L | P3-020 | Engineer |
| P3-026 | Seats, brand and billing screens; proposal builder and public page UI; commissions UI | L | P3-022, P3-023, P3-025 | Engineer |
| P3-027 | Web-only guardrails: iOS client blocks, no purchase link, reviewer notes, CI grep test | S | P3-017 | Engineer |
| P3-028 | Export, leave and offboarding: org export job, read-only behavior, client export and leave paths | M | P3-020 | Engineer |
| P3-029 | Admin Advisors screens, actions, permissions, alerts, kill switch | M | P3-018 | Engineer |
| P3-030 | Legal pack: terms, data-processing addendum, sub-processor list, sensitive-data rules, auto-renew reminder; lawyer review | M | P3-015 | Lawyer, founder |
| P3-031 | Analytics events and revenue reporting (MRR, seats, churn, activation) | S | P3-018 | Engineer |
| P3-032 | Security: org-isolation test suite, sensitive-number guard, proposal token tests, external review | M | P3-022 | Engineer, reviewer |
| P3-033 | Pilot with design partners (comped seats through Stripe coupon), measure credits per seat and activation, decide 150 versus 60 credits and final price | M | P3-026, P3-029 | Founder |
| P3-034 | Launch: open sign-ups on the web, host-agency and community outreach, support contractor at about 100 seats, status page and runbook | M | P3-032, P3-033 | Founder, support contractor |

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Host agencies bundle free tools and cap prices | Medium | High | P3-015 asks directly; differentiate on sourced fares and research; consider a host-agency partnership only with a written agreement |
| Part-time advisor churn | Medium | Medium | Annual billing default at $24, activation target, templates and proposals to build habit |
| Market size smaller than the 60k core assumption | Medium | Medium | Base case needs 0.75% of 60k; stop rule if the pilot yields under 15 paying design partners |
| Org data leak across tenants | Low | Severe | Helpers fail closed, leak tests in CI, external review before launch |
| Support load outgrows the founder | High | Medium | About 10 hours a week per 100 seats budgeted; contractor hired from seat revenue |
| Client data regulation (DPA, deletion) | Low | High | Processor terms, export and delete paths tested, no sensitive ids stored |
| Apple treats web-only sale as steering | Low | Medium | No price or link in the app; advisors are business users on the web |
| Commission tracker read as financial or legal advice | Low | Medium | Records only what the advisor enters; terms say so |
