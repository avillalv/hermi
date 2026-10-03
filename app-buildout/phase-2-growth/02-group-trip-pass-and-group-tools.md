# Pack 02: Group Trip Pass and group tools

Part of [Phase 2: growth](README.md). Written 2026-09-30. Source definitions:
[01 section 4.11](../reference-full-spec/01-product-spec.md), [03 sections 5.9 and 5.16](../reference-full-spec/03-database-schema.md),
[04 sections 5.17 and 5.18](../reference-full-spec/04-api-spec.md), [05 section 6.21](../reference-full-spec/05-ui-ux-spec.md),
[07 sections 7.9 and 10](../reference-full-spec/07-monetization-spec.md).

| Item | Value |
|---|---|
| Build order | 2 (months 7 to 8, after Family starts) |
| Flags | `group_tools` (on), `room_block_requests` (on, tier `group_trip_pass`), `group_payments` (created off; Stripe collection is Phase 3) |
| Needs from Phase 1 | Trips, `people` and `trip_people`, roles, Trip Pass binding and expiry, entitlement merge, `fx_rates`, notifications, offline queue, activity log |
| Soft link | Pack 07 (the room-block request is emailed to the concierge desk until the admin queue exists) |
| Tickets | P2-011 to P2-024 |
| Tier and products | `group_trip_pass` ($19.99 once, 90 days, `hermi_group_trip_pass`); polls and manual splitting in every paid plan and both passes |

## 1. Goal and why now

**Goal.** Give a friend group, family trip or wedding party the three things group trips lack in one
place: a vote on dates, stays and activities (polls), a fair "who owes whom" ledger (manual cost
splitting, no money moves), and, on the Group Trip Pass, up to 12 travelers and a room-block request.

**Why now.**

- Persona P2 (friend-group organizer) is the viral persona: every trip brings 3 to 11 invitees who join
  free and see the product. Polls and splitting give invitees a reason to open the app daily.
- Competitive reasons. Wanderlog and Trippy both have group tools (shared planning and, for Wanderlog,
  expense splitting), so a collaborative planner without polls or costs looks incomplete to the
  friend-group buyer. Splitwise Pro (the cost-splitting anchor, $39.99 a year, reported) shows people
  will pay for splitting alone. The business plan calls group coordination "still clumsy in TripIt and
  Google Docs" ([business plan](../context/business-plan/01-business-plan.md)). Hermi's edge is that polls can vote on
  real objects (a shortlisted stay, a date range) and the winner applies back to the plan.
- Revenue. The Group Trip Pass is 8 percent of payers in the pricing model at $19.99 with a 78 to 92
  percent margin ([09 revenue expansion](../context/business-plan/09-revenue-expansion.md) section 2.3). It is the clean
  answer to "one trip, twelve people, no subscription".
- The room-block request is a lead form routed to the host agency (see pack 07); it adds a reason to
  buy the pass for destination weddings and events.

## 2. User stories and acceptance criteria

Gating rule for the whole pack (verbatim from the full product spec): polls and manual cost splitting
(expenses, balances, "mark as paid") are included in `plus`, `family`, `pro`, `trip_pass` and
`group_trip_pass`. A `free` user uses them on any trip whose capabilities include them (for example a
trip they joined, or a trip with a pass); a `free` owner's own trip shows a preview and the paywall
moment. The Group Trip Pass adds up to 12 travelers and the room-block request. Collecting money
through Stripe (F-GRP-4, Phase 3) is for `group_trip_pass` and `pro` only. Real-world money handling
is through Stripe, never Apple In-App Purchase, and never for digital features.

### F-GRP-1 Polls

- Story: As an organizer, I want a quick vote on dates, stays or activities, so that the group
  decides without a chat thread.
- Acceptance:
  - A poll (`polls`) has a question, 2 to 12 options, single or multiple choice, optional
    deadline, and anonymous or named; votes in `poll_votes`.
  - Poll types: free text, date ranges, or pick from the trip's lodging candidates or ideas.
  - Members vote from the app or the link; results update live on refresh; owner closes the poll
    and can apply the winner (for example, marks the winning stay "Shortlisted").
  - Viewers can vote.
  - Reminder notification to members who have not voted, at most once per poll per day.
- Tier: `plus`, `family`, `pro`, `trip_pass`, `group_trip_pass`, and `free` users on trips that
  have them. A `free` owner sees polls as a preview with the `trip_pass` paywall moment. Credits:
  none.

### F-GRP-2 Expenses

- Story: As a traveler, I want to log who paid for what, so that costs stay fair.
- Acceptance:
  - An expense (`expenses`) has amount in minor units plus currency, payer, date, category,
    description, and shares (`expense_shares`) by equal split, by exact amounts, by percentages,
    or by shares; the description can name the item or stay it is for.
  - Foreign currency amounts convert to the trip currency with the ECB rate of the expense date
    and store both.
  - Editors and owners can add; every member can view their own balance.
  - Deleting an expense keeps an audit line.
- Tier: `plus`, `family`, `pro`, `trip_pass`, `group_trip_pass`, and `free` users on trips that
  have them; the traveler cap is the trip's own limit (8, or 12 on a Group Trip Pass or `pro`).
  A `free` owner sees a preview with the `trip_pass` paywall moment. Credits: none.

### F-GRP-3 Cost splitting

- Story: As a member, I want to see who owes whom in the fewest payments, so that settling is
  easy.
- Acceptance:
  - The balance screen shows each traveler's net position and a minimized set of transfers.
  - Rounding: amounts are integer minor units; leftover cents are assigned deterministically
    (by traveler order) so totals always match.
  - Travelers without accounts (`people` with no linked user) are included and shown by name.
- Tier: same as F-GRP-2.

### F-GRP-4 Settlements (manual part only in Phase 2)

- Story: As a debtor, I want to pay or record a payment, so that the trip is squared away.
- Acceptance (Phase 2 subset):
  - A settlement (`settlements`) is "Mark as paid" (manual, both sides confirm). The Stripe option
    ("Pay with card or bank through Stripe") ships in Phase 3 behind flag `group_payments`.
  - Status (`settlements.status`): pending (waiting for the payee to confirm, or for Stripe),
    recorded (confirmed manual payment), succeeded (Stripe paid), failed, refunded, disputed.
    Recorded and succeeded settlements reduce balances; in Phase 2 only pending and recorded occur.
  - Payment is only for real-world trip costs; nothing digital is sold through it.
- Tier: manual marking is in every F-GRP-2 tier.
- Edge cases: a member leaves with a balance: the balance stays and the owner can write it off
  with an audit line; currency mismatch settles in the trip currency.

### F-GRP-5 Room-block request

- Story: As an organizer of a wedding or event, I want to ask for a hotel room block, so that
  guests get a group rate.
- Acceptance:
  - A form (`room_block_requests`) takes hotel (from the shortlist or typed), dates, rooms, guest
    count, budget and notes.
  - Submission is routed to the concierge team (host agency), who reply by email within 2
    business days; status is visible (submitted, in review, quoted, accepted, declined, expired, cancelled).
  - The form shows a plain disclosure: "Hermi may earn a commission from the hotel or our host
    agency. It does not change what you pay."
  - Request creates no charge and no obligation.
- Tier: `group_trip_pass` only (a trip with a Group Trip Pass, including for its invited members).
  Credits: none.

### F-SUB-2 Group Trip Pass (the parts that differ from Trip Pass)

- Group Trip Pass: the same as Trip Pass plus up to 12 travelers, 80 credits and the room-block
  request. Trip Pass: 2 live routes, at most 60 live checks, 40 credits, up to 6 collaborators, polls
  and manual cost splitting. The passed trip does not count toward the owner's active-trip limit.
- Upgrade: buying a Group Trip Pass for a trip that has an active Trip Pass replaces it (the Trip Pass
  becomes `upgraded`, the new pass gets a full 90 days, the live-check counter carries over and
  unspent Trip Pass credits stay spendable until their own expiry).
- Guests in the group need no subscription; they join free and see polls and splits. Those who want to
  start AI actions draw from their own allowance, then the trip's pass pool.
- Expiry: if the owner's tier does not also grant them, polls and splits become read-only; past polls
  and recorded expenses remain readable and exportable. The owner sees a notice 7 days before expiry.
  A lapsed owner's trip becomes limited: extra members become viewers, live tracking pauses, polls
  close, extras are kept and come back if the owner renews.
- A pass bought while on `plus` still applies its extra group features.

### Stories added by this pack

| ID | Story | Acceptance |
|---|---|---|
| GRP-1 | As an organizer I apply the winning option. | `POST /polls/{id}/apply-winner` on a closed poll with one winner: a lodging option becomes `shortlisted`, a date poll sets the trip dates (only when no flight is chosen), an activity poll creates an idea. Ties are reported and nothing is applied. |
| GRP-2 | As a member I am reminded once. | Job `send_poll_reminders` (notify lane) sends at most one reminder per poll per user per day to members who have not voted, only while the poll is open and before `closes_at`; respects quiet hours and per poll mute. |
| GRP-3 | As a Free invitee I can use what the trip has. | On a trip whose merged limits include `polls` and `cost_splitting`, Free invitees create polls and expenses if their role allows (editor), vote (any role), and see their own balance. |
| GRP-4 | As a traveler without an account I am still in the ledger. | Expenses and shares reference `people`; a child or friend can owe money; the balance screen shows them by first name and color. |
| GRP-5 | As an organizer I hit a clear limit. | A ninth traveler, or the room-block request, without a Group Trip Pass shows the `group_pass` paywall; a 13th traveler is refused even with the pass (`403 limit_reached`, reason `traveler_limit`). |
| GRP-6 | As anyone I can export the ledger. | Per trip export (JSON, ICS, PDF) includes polls, expenses, shares and settlements; CSV of expenses added. Works on archived trips and after pass expiry. |

## 3. Database additions

Migrations `0017_group_tools` (polls, expenses, settlements) and `0018_room_block_requests`. Phase 1 has
none of these tables: [Phase 1 03 section 1.1](../phase-1-launch/03-database-schema.md) lists `polls`,
`poll_votes`, `expenses`, `expense_shares`, `settlements`, `payment_collections` and `room_block_requests`
as dropped, plus the plan limit keys for polls, cost splitting and room blocks, `trip_passes.upgraded_from_id`
and the `upgraded` pass status; its section 14 lists what this pack adds. Definitions are reused from
[the full 03 sections 5.9 and 5.16](../reference-full-spec/03-database-schema.md) with two deliberate differences: `payment_collections`
is not created (Stripe collection is Phase 3, which creates it and attaches the foreign key to
`settlements.collection_id`, a plain nullable column here; see
[Phase 3 pack 01](../phase-3-scale/01-stripe-group-payments.md) section 4.1, which relies on exactly this state), and
`room_block_requests.concierge_request_id` has no foreign key until pack 07 creates `concierge_requests`. The
room-block table also gets two hotel columns the form needs.

Polls keep their options inside the row (`options` is an array of
`{"key": "...", "label": "...", "ref_type": null, "ref_id": null}`), because options are always read
with the poll and never joined. Expenses are kept per traveler (person), not per account, so a child or
a friend without the app can owe money.

```sql
CREATE TYPE poll_status  AS ENUM ('open', 'closed');
CREATE TYPE split_method AS ENUM ('equal', 'exact', 'percent', 'shares');

CREATE TABLE polls (
  id                   uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id              uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  created_by           uuid REFERENCES users (id) ON DELETE SET NULL,
  question             text NOT NULL CHECK (char_length(question) BETWEEN 1 AND 200),
  subject              text NOT NULL DEFAULT 'custom',
  selection            text NOT NULL DEFAULT 'single',
  options              jsonb NOT NULL,
  is_anonymous         boolean NOT NULL DEFAULT false,
  status               poll_status NOT NULL DEFAULT 'open',
  closes_at            timestamptz,
  closed_at            timestamptz,
  winning_option_key   text,
  version              integer NOT NULL DEFAULT 1,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_polls_subject CHECK (subject IN ('custom', 'dates', 'lodging', 'activity', 'destination')),
  CONSTRAINT ck_polls_selection CHECK (selection IN ('single', 'multiple')),
  CONSTRAINT ck_polls_options CHECK (jsonb_typeof(options) = 'array' AND jsonb_array_length(options) BETWEEN 2 AND 12),
  CONSTRAINT uq_polls_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_polls_trip ON polls (trip_id, status, created_at DESC);
SELECT add_version_trigger('polls');
SELECT add_updated_at_trigger('polls');

CREATE TABLE poll_votes (
  poll_id     uuid NOT NULL,
  trip_id     uuid NOT NULL,
  user_id     uuid NOT NULL REFERENCES users (id) ON DELETE CASCADE,
  option_key  text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (poll_id, user_id, option_key),
  FOREIGN KEY (poll_id, trip_id) REFERENCES polls (id, trip_id) ON DELETE CASCADE
);
CREATE INDEX ix_poll_votes_trip ON poll_votes (trip_id);

-- A vote must name a real option, and single-choice polls allow one option per voter.
CREATE FUNCTION poll_votes_validate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_poll polls%ROWTYPE;
BEGIN
  SELECT * INTO v_poll FROM polls WHERE id = NEW.poll_id;
  IF v_poll.status <> 'open' THEN RAISE EXCEPTION 'poll_closed' USING ERRCODE = 'WF409'; END IF;
  IF NOT EXISTS (SELECT 1 FROM jsonb_array_elements(v_poll.options) o WHERE o ->> 'key' = NEW.option_key) THEN
    RAISE EXCEPTION 'unknown_option' USING ERRCODE = 'WF422';
  END IF;
  IF v_poll.selection = 'single' AND EXISTS (
       SELECT 1 FROM poll_votes WHERE poll_id = NEW.poll_id AND user_id = NEW.user_id AND option_key <> NEW.option_key) THEN
    RAISE EXCEPTION 'single_choice' USING ERRCODE = 'WF409';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_poll_votes_validate BEFORE INSERT ON poll_votes
  FOR EACH ROW EXECUTE FUNCTION poll_votes_validate();

CREATE TABLE expenses (
  id                    uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id               uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  paid_by_person_id     uuid NOT NULL,
  description           text NOT NULL CHECK (char_length(description) BETWEEN 1 AND 200),
  category              text NOT NULL DEFAULT 'other',
  amount_minor          bigint NOT NULL CHECK (amount_minor > 0),          -- as paid
  currency              currency_code NOT NULL,
  fx_rate               numeric(20,10) NOT NULL DEFAULT 1 CHECK (fx_rate > 0),   -- paid currency to trip currency, fixed at entry
  amount_trip_minor     bigint NOT NULL CHECK (amount_trip_minor > 0),     -- the record the split and settlements use
  trip_currency         currency_code NOT NULL,
  incurred_on           date NOT NULL DEFAULT CURRENT_DATE,
  split_method          split_method NOT NULL DEFAULT 'equal',
  note                  text NOT NULL DEFAULT '',
  receipt_key           text,                                              -- object key in R2
  created_by            uuid REFERENCES users (id) ON DELETE SET NULL,
  version               integer NOT NULL DEFAULT 1,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (trip_id, paid_by_person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE RESTRICT,
  CONSTRAINT ck_expenses_category CHECK (category IN ('lodging', 'food', 'transport', 'activities', 'groceries', 'other')),
  CONSTRAINT uq_expenses_id_trip UNIQUE (id, trip_id)
);
CREATE INDEX ix_expenses_trip ON expenses (trip_id, incurred_on DESC);
SELECT add_version_trigger('expenses');
SELECT add_updated_at_trigger('expenses');

CREATE TABLE expense_shares (
  expense_id    uuid NOT NULL,
  trip_id       uuid NOT NULL,
  person_id     uuid NOT NULL,
  share_minor   bigint NOT NULL CHECK (share_minor >= 0),                  -- in the trip currency
  weight        numeric(10,4),                                             -- percent or share count when the method needs it
  PRIMARY KEY (expense_id, person_id),
  FOREIGN KEY (expense_id, trip_id) REFERENCES expenses (id, trip_id) ON DELETE CASCADE,
  FOREIGN KEY (trip_id, person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE RESTRICT
);
CREATE INDEX ix_expense_shares_person ON expense_shares (trip_id, person_id);

-- Shares must add up to the expense, checked at commit.
CREATE FUNCTION check_expense_shares_sum() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_id uuid := COALESCE(NEW.expense_id, OLD.expense_id); v_total bigint; v_sum bigint;
BEGIN
  SELECT amount_trip_minor INTO v_total FROM expenses WHERE id = v_id;
  IF NOT FOUND THEN RETURN NULL; END IF;                                   -- expense deleted in the same transaction
  SELECT COALESCE(sum(share_minor), 0) INTO v_sum FROM expense_shares WHERE expense_id = v_id;
  IF v_sum <> v_total THEN RAISE EXCEPTION 'expense_shares_sum_mismatch' USING ERRCODE = 'WF422'; END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER trg_expense_shares_sum AFTER INSERT OR UPDATE OR DELETE ON expense_shares
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_expense_shares_sum();

CREATE TABLE settlements (                                   -- a payment from one traveler to another, in the trip currency
  id                          uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                     uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  from_person_id              uuid NOT NULL,
  to_person_id                uuid NOT NULL,
  amount_minor                bigint NOT NULL CHECK (amount_minor > 0),
  currency                    currency_code NOT NULL,
  method                      text NOT NULL DEFAULT 'manual',
  status                      text NOT NULL DEFAULT 'recorded',   -- manual methods are inserted as 'pending' until the payee confirms (04 5.17)
  collection_id               uuid,                               -- Phase 3: the foreign key to payment_collections is added by the Stripe pack
  stripe_payment_intent_id    text,
  note                        text NOT NULL DEFAULT '',
  settled_at                  timestamptz NOT NULL DEFAULT now(),
  created_by                  uuid REFERENCES users (id) ON DELETE SET NULL,
  created_at                  timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (trip_id, from_person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE RESTRICT,
  FOREIGN KEY (trip_id, to_person_id) REFERENCES trip_people (trip_id, person_id) ON DELETE RESTRICT,
  CONSTRAINT ck_settlements_distinct CHECK (from_person_id <> to_person_id),
  CONSTRAINT ck_settlements_method CHECK (method IN ('manual', 'cash', 'bank_transfer', 'stripe')),
  CONSTRAINT ck_settlements_status CHECK (status IN ('recorded', 'pending', 'succeeded', 'failed', 'refunded', 'disputed')),   -- disputed: charge.dispute.created, until Stripe resolves it
  CONSTRAINT ck_settlements_collection_stripe CHECK (collection_id IS NULL OR method = 'stripe')
);
CREATE INDEX ix_settlements_trip ON settlements (trip_id, settled_at DESC);
CREATE INDEX ix_settlements_collection ON settlements (collection_id) WHERE collection_id IS NOT NULL;
CREATE UNIQUE INDEX uq_settlements_stripe_pi ON settlements (stripe_payment_intent_id) WHERE stripe_payment_intent_id IS NOT NULL;
```

Room-block requests (from 03 section 5.16, plus the two hotel columns the form needs):

```sql
CREATE TABLE room_block_requests (                          -- Group Trip Pass feature
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                   uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  requested_by              uuid REFERENCES users (id) ON DELETE SET NULL,
  destination               text NOT NULL,
  hotel_name                text,                              -- typed, or copied from the chosen shortlist stay
  lodging_option_id         uuid REFERENCES lodging_options (id) ON DELETE SET NULL,
  check_in                  date NOT NULL,
  check_out                 date NOT NULL,
  rooms_needed              smallint NOT NULL CHECK (rooms_needed BETWEEN 2 AND 50),
  guests_total              smallint CHECK (guests_total IS NULL OR guests_total BETWEEN 2 AND 200),
  budget_per_room_minor     bigint,
  currency                  currency_code,
  preferences               text NOT NULL DEFAULT '',
  status                    text NOT NULL DEFAULT 'submitted',
  quote                     jsonb,
  concierge_request_id      uuid,                              -- foreign key to concierge_requests is added by pack 07
  share_consent_at          timestamptz NOT NULL,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_room_block_requests_dates CHECK (check_out > check_in),
  CONSTRAINT ck_room_block_requests_status CHECK (status IN ('submitted', 'in_review', 'quoted', 'accepted', 'declined', 'expired', 'cancelled'))
);
CREATE INDEX ix_room_block_requests_trip ON room_block_requests (trip_id);
CREATE INDEX ix_room_block_requests_status ON room_block_requests (status, created_at);
SELECT add_updated_at_trigger('room_block_requests');
```

Row-level security. The four trip-child policies (select for members, insert, update and delete for
owner and editors) apply to `polls`, `expenses`, `expense_shares`, `settlements` and
`room_block_requests` by adding them to the generated loop in 03 section 6.4. Votes have their own
shape: viewers may vote, and a vote row must be the caller's own.

```sql
ALTER TABLE poll_votes ENABLE ROW LEVEL SECURITY;
CREATE POLICY poll_votes_select ON poll_votes FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY poll_votes_insert ON poll_votes FOR INSERT
  WITH CHECK (user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY poll_votes_delete ON poll_votes FOR DELETE USING (user_id = (SELECT app_user_id()));
```

Pass, plan and flag changes on Phase 1 objects (from [03 section 5.14 and 11.1, 11.2](../reference-full-spec/03-database-schema.md)):

```sql
ALTER TYPE pass_status ADD VALUE 'upgraded';        -- in its own migration step; used when a Group Trip Pass replaces a Trip Pass on the same trip (07 7.9)
ALTER TABLE trip_passes ADD COLUMN upgraded_from_id uuid REFERENCES trip_passes (id) ON DELETE SET NULL;   -- the Trip Pass this Group Trip Pass replaced
ALTER TABLE trip_passes DROP CONSTRAINT ck_trip_passes_plan;
ALTER TABLE trip_passes ADD CONSTRAINT ck_trip_passes_plan CHECK (plan_code IN ('trip_pass', 'group_trip_pass'));
ALTER TABLE trip_passes ADD CONSTRAINT ck_trip_passes_upgrade CHECK (upgraded_from_id IS NULL OR plan_code = 'group_trip_pass');
CREATE INDEX ix_trip_passes_upgraded_from ON trip_passes (upgraded_from_id) WHERE upgraded_from_id IS NOT NULL;
-- uq_trip_passes_one_active (one active pass per trip) is a Phase 1 index; 'upgraded' rows fall outside it, which is what lets the new pass be inserted.

-- Phase 1 plan rows have no group keys. A missing key means "not granted", so add them explicitly (true is always the better value).
UPDATE plans SET limits = limits || '{"polls":false,"cost_splitting":false,"room_block_request":false}'::jsonb WHERE code = 'free';
UPDATE plans SET limits = limits || '{"polls":true,"cost_splitting":true,"room_block_request":false}'::jsonb  WHERE code IN ('plus', 'trip_pass');
-- The family and pro rows are inserted by packs 01 and 06 with polls and cost_splitting already true.

INSERT INTO plans (code, kind, name, rank, monthly_credits, credits_granted, credits_valid_days, duration_days, feature_flag_key, is_active, sort_order, limits) VALUES
('group_trip_pass', 'pass', 'Group Trip Pass', 26, 0, 80, 90, 90, NULL, true, 50,
 '{"active_trips_bonus":1,"routes_per_trip":3,"live_routes":2,"live_window_days":120,"live_checks_max":60,"price_alerts":2,"live_alerts":true,
   "collaborators":11,"travelers_per_trip":12,"can_invite":true,"saved_lodging_per_trip":30,"lodging_compare":4,
   "places_searches_per_day":100,"polls":true,"cost_splitting":true,"room_block_request":true,"group_payments":true,
   "hide_presentation_footer":true,
   "monthly_ceiling_micros":3600000,"daily_ceiling_micros":400000}')
ON CONFLICT (code) DO NOTHING;
-- "group_payments": true only takes effect when the group_payments flag (created off below) is turned on in Phase 3.

INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('hermi_group_trip_pass', 'apple', 'group_trip_pass', 'once', 1999, 'USD', 0, true)
ON CONFLICT (product_id) DO NOTHING;

-- Room-block requests share the concierge consent (added here because this pack ships first; pack 07 reuses it).
ALTER TABLE consents DROP CONSTRAINT ck_consents_kind;
ALTER TABLE consents ADD CONSTRAINT ck_consents_kind
  CHECK (kind IN ('terms', 'privacy', 'ai_processing', 'marketing_email', 'push_notifications', 'analytics', 'concierge_sharing'));   -- append to whatever list is current

INSERT INTO feature_flags (key, description, enabled, rollout_pct, rules, variants) VALUES
('group_tools',         'Polls, expenses and settlements',                              true,  100, '{}', '{}'),
('room_block_requests', 'Room-block request on Group Trip Pass trips',                  true,  100, '{"tiers":["group_trip_pass"]}', '{}'),
('group_payments',      'Collect settlements through Stripe (Group Trip Pass and Pro; Phase 3). rules.fee_bps is the application fee', false, 100, '{"fee_bps":0}', '{}')
ON CONFLICT (key) DO NOTHING;
UPDATE feature_flags SET rules = jsonb_set(rules, '{tiers}', rules -> 'tiers' || '["group_trip_pass"]'::jsonb) WHERE key = 'serpapi_live_fares';
```

Notification kinds (Phase 1 has a `notifications` outbox and inbox with a named check on `kind`; each pack that
adds kinds swaps `ck_notifications_kind` for the current list plus its own values): `poll_opened`,
`poll_closed`, `poll_reminder`, `expense_added`, `settlement_requested`, `settlement_confirmed`,
`room_block_update`. Dedupe keys follow the Phase 1 pattern, for example `poll_reminder:<poll_id>:<date>`.

Balance and settle-up algorithm (application code, `apps/api/hermi/modules/groups/balances.py`):

1. Net per person = sum of shares owed subtracted from amounts paid, in `amount_trip_minor`, plus
   recorded and succeeded settlements (a payer's settlement moves their net toward zero).
2. Split arithmetic: `equal` divides `amount_trip_minor` by the number of included people; the leftover
   minor units (at most n minus 1) go one each to the first people in traveler order
   (`trip_people.created_at`, then `person_id`). `exact` shares must sum to the amount. `percent`
   weights must sum to 100 (four decimals); `shares` uses integer weights (person-nights are entered
   as weights). The largest remainder method assigns leftovers deterministically so the sum always
   matches.
3. Minimal transfers (at most 12 travelers): find the partition of people with non zero net into the
   largest number of zero-sum groups (bitmask dynamic programming over at most 4,096 subsets); each
   group of k people needs k minus 1 transfers; inside a group match the largest debtor with the
   largest creditor, ties broken by traveler order. The output is stable across calls.
4. FX: a foreign-currency expense uses the `fx_rates` (ECB via Frankfurter) rate of the expense date
   (the last published date on or before `incurred_on`), stores `fx_rate` and `amount_trip_minor`, and
   shows the original beside the converted amount. The rate is fixed at entry.

Decision for an inconsistency in the full specs: [04 section 5.17](../reference-full-spec/04-api-spec.md) says leftover
cents go to the payer, [01 F-GRP-3](../reference-full-spec/01-product-spec.md) says deterministic by traveler order. This
pack follows the product spec (traveler order).

Edit rule for expenses: the spec says an expense is blocked once a settlement that includes it is
recorded. Because settlements are between people, not expenses, this pack defines it as: amount,
payer, currency and shares of an expense created on or before the newest `recorded` settlement on the
trip are locked (`409 state_conflict`); description, category, note and receipt stay editable.

## 4. API additions

All routes below are in [04 sections 5.17 and 5.18](../reference-full-spec/04-api-spec.md). Gate for the group tool routes:
`group_tools` (the trip's merged limits have `polls` and `cost_splitting`). Hermi records who owes
whom; any real money moves outside the app.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /trips/{trip_id}/polls` | viewer | none (read allowed on any tier once created) | `?status=` to `Poll[]` | |
| `POST /trips/{trip_id}/polls` | editor | `group_tools` | `PollIn` to 201 `Poll` | Options may reference `lodging_options`, `itinerary_items` or free text; they are stored in `polls.options` (jsonb, each with a `key`). |
| `PATCH /polls/{poll_id}` | author or owner | versioned | `{ question?, closes_at?, status?: "open" \| "closed" }` to `Poll` | Closing sets `closed_at` and `winning_option_key` (ties are reported in `winners` and the key stays null). |
| `DELETE /polls/{poll_id}` | author or owner | none | 204 | |
| `PUT /polls/{poll_id}/votes/me` | viewer | poll open | `{ option_keys: string[] }` to `Poll` | Writes `poll_votes` (`option_key`). `single` polls accept one key, `multiple` polls any number of the options. Replaces the caller's previous vote. |
| `GET /trips/{trip_id}/expenses` | viewer | none | `?limit&cursor` to `Page<Expense>` | |
| `POST /trips/{trip_id}/expenses` | editor | `group_tools` | `ExpenseIn` with `Idempotency-Key` to 201 `Expense` | Writes `expenses` and `expense_shares`. Shares must sum to the amount (minor units, leftover by traveler order). |
| `PATCH /expenses/{expense_id}` | author or owner | versioned | `Partial<ExpenseIn>` to `Expense` | Locked fields per the edit rule above (`409 state_conflict`). |
| `DELETE /expenses/{expense_id}` | author or owner | none | 204 | Writes an `activity_log` audit line (verb `removed`, summary with description and amount). |
| `GET /trips/{trip_id}/balances` | viewer | none | none to `Balances` | Net per person and the minimal suggested transfers, in the trip home currency (FX from `fx_rates`, date shown). |
| `POST /trips/{trip_id}/settlements` | editor | `group_tools` | `{ from_person_id, to_person_id, amount: Money, method: "manual" \| "cash" \| "bank_transfer" }` with `Idempotency-Key` to 201 `Settlement` | Records a payment. The methods start `pending` and the recipient confirms them (status `recorded`). `method: "stripe"` returns `503 feature_disabled` while flag `group_payments` is off; Stripe collection ships in Phase 3. |
| `POST /settlements/{settlement_id}/confirm` | recipient | status `pending` | none to `Settlement` | Recipient confirms receipt; status becomes `recorded`. |
| `GET /trips/{trip_id}/settlements` | viewer | none | none to `Settlement[]` | |

```ts
type PollIn = {
  question: string; subject?: "custom" | "dates" | "lodging" | "activity" | "destination"
  selection: "single" | "multiple"; is_anonymous?: boolean; closes_at?: string | null
  options: { label: string; lodging_id?: Uuid; item_id?: Uuid }[]          // 2 to 12; stored in polls.options with a generated key
}
type Poll = {
  id: Uuid; trip_id: Uuid; version: number; question: string; selection: "single" | "multiple"
  status: "open" | "closed"; closes_at: string | null; created_by: Attribution
  options: { key: string; label: string; lodging_id: Uuid | null; item_id: Uuid | null; votes: number }[]
  my_vote: string[]; winners: string[] | null
}
type ExpenseIn = {
  description: string; amount: Money; paid_by_person_id: Uuid; incurred_on: string
  category?: "lodging" | "food" | "transport" | "activities" | "groceries" | "other"
  split_method: "equal" | "exact" | "percent" | "shares"
  shares: { person_id: Uuid; amount?: Money; percent?: number; weight?: number }[]; version?: number
}
type Expense = Omit<ExpenseIn, "version" | "shares"> & { id: Uuid; version: number; shares: { person_id: Uuid; amount: Money }[]; created_by: Attribution }
type Balances = { currency: string; fx_date: string; net: { person_id: Uuid; amount: Money }[]; transfers: { from: Uuid; to: Uuid; amount: Money }[] }
type Settlement = {
  id: Uuid; from_person_id: Uuid; to_person_id: Uuid; amount: Money
  method: "manual" | "cash" | "bank_transfer" | "stripe"; status: "recorded" | "pending" | "succeeded" | "failed" | "refunded" | "disputed"   // settlements.status
  collection_id: Uuid | null                                        // Phase 3 Stripe collection (payment_collections)
  payment_url: string | null; settled_at: string | null
}
```

Room-block routes (from 04 section 5.18):

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /trips/{trip_id}/room-block-requests` | owner | `room_block_request` capability (Group Trip Pass), at least 8 travelers | `RoomBlockIn` with `Idempotency-Key` to 201 `RoomBlockRequest` | Group Trip Pass feature. Writes `room_block_requests`, notifies the desk. |
| `GET /trips/{trip_id}/room-block-requests` | viewer | none | none to `RoomBlockRequest[]` | |

```ts
type RoomBlockIn = { destination: string; check_in: string; check_out: string; rooms: number; guests: number; budget_per_room?: Money; notes?: string; hotel_name?: string; lodging_id?: Uuid }   // rooms_needed, guests_total, preferences in room_block_requests
type RoomBlockRequest = RoomBlockIn & { id: Uuid; trip_id: Uuid; status: "submitted" | "in_review" | "quoted" | "accepted" | "declined" | "expired" | "cancelled"; quote: Record<string, unknown> | null; created_at: string }
```

Additions in this pack:

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `POST /polls/{poll_id}/apply-winner` | owner | poll closed with exactly one winner | none to `{ applied: "lodging_shortlisted" \| "dates_set" \| "idea_created" }` | Applies per GRP-1; writes an `activity_log` line; `409 state_conflict` on a tie or an open poll. |
| `POST /trips/{trip_id}/write-off` | owner | none | `{ person_id: Uuid, reason: string }` to `Balances` | Writes off a leaving member's balance with an audit line (F-GRP-4 edge case). |
| `GET /trips/{trip_id}/expenses.csv` | viewer | none | CSV | Export of the ledger. |
| `PATCH /room-block-requests/{id}` | requester | status `submitted`, `in_review` or `quoted` | `{ message?: string, cancel?: boolean }` | Requester cancels or adds a message. |

Capability errors: `403 entitlement_required` with reason `group_tools` (Free owner's own trip),
`403 entitlement_required` with reason `room_block` (no Group Trip Pass), `403 limit_reached` with
reason `traveler_limit` (above 8 travelers without the pass, above 12 with it). `PaywallHint.reason`
values `group_tools`, `traveler_limit` and `room_block` already exist in the full spec. The room-block
route is also hidden and returns `503 feature_disabled` in regions where concierge is not confirmed
(seller-of-travel gate, [10 section 3.8](../reference-full-spec/10-quality-security-launch.md)).

Jobs (worker): `send_poll_reminders` (notify lane, daily at 15:00 local, key
`(poll_id, user_id, date)`), `close_due_polls` (api lane, every 5 minutes, closes polls past
`closes_at` and applies nothing), `expire_trip_passes` (existing, extended: on Group Trip Pass expiry
close open polls when the trip loses `polls`), `send_group_settle_reminders` (existing in the job
catalogue, daily at 15:00 local, only for settlements the user opted into).

Notification event types added to the F-NOT-1 matrix: poll opened, poll closed, expense added,
settlement requested, settlement confirmed, room-block update (email). Change-digest push stays at most
one per hour per trip.

## 5. UI screens and paywall triggers

Screen 6.21 "Group tools: polls, expenses, settle up" from [05](../reference-full-spec/05-ui-ux-spec.md), verbatim:

**Purpose.** Decide together and split real costs fairly. Polls and manual cost splitting are in Plus,
Family, Pro, Trip Pass and Group Trip Pass, and Free users have them on any trip that has them; the
Group Trip Pass adds up to 12 travelers and the room-block request; Stripe collection is for Group Trip
Pass and Pro and arrives in Phase 3; viewing is always allowed.
**Layout.** The Group section has a segmented control: **People, Polls, Expenses, Settle up**.
**People.** Traveler list with avatars, roles, home airports (visible to members only), "Invite" (6.8),
"Which traveler are you?" link if unclaimed. Travelers without accounts are first names with a color.
**Polls.** A poll card: question, options (stays, dates, restaurants, free text), votes as avatar chips,
a deadline, and a result line ("Alfama loft leads, 3 of 5 voted"). Create from a stay or from "New
poll". Vote is a single or multiple choice; change allowed until it closes; owner closes. A poll never
implies a purchase.
**Expenses.** List of expenses with payer, amount in mono (currency and converted trip currency), who
shares it, and category; "Add expense": title, amount, paid by, split (equally, by share, by amount, or
exclude people), date, receipt photo. Totals: "Trip total $3,480, $870 each." Offline add is queued.
**Settle up.** A plain list of "who pays whom" reduced to the fewest transfers ("Ana pays Sam $120"),
each row with "Mark as paid" (manual, available wherever cost splitting is). A payment carries the
`settlements.status` as a text chip: Waiting for confirmation (`pending`, until the person paid
confirms) and Paid (`recorded`, or `succeeded` for a Stripe payment); Failed, Refunded and In dispute
appear only with Phase 3; only Paid rows reduce the balances. The "Collect payments" button (Stripe)
is not built in Phase 2 and is not shown.
**States.** Loading: skeleton rows. Empty polls: "No polls yet", "Ask the group to choose between two
stays or a date.", [New poll]. Empty expenses: "No expenses yet", "Add what you pay for and we will work
out who owes whom.", [Add expense]. Error: "We could not save this expense. Check the amount and try
again." Offline: queued edits with "Waiting to sync". No permission: viewers can vote in polls and see
expenses, not add. Limit: on a trip whose owner is on Free with no pass, Polls and Expenses show a
locked preview and the `group_tools` paywall (Trip Pass or Plus; free path: view what others add, and a
free read-only balance); the room-block request and more than 8 travelers show the `group_pass` paywall
(Group Trip Pass); expense viewing stays free.
**Copy.** "Split equally among 4 people, $27.50 each." "Mark as paid" confirmation "Marked as paid. Sam
will see it." and, for the payee, "Ana says she paid you $120. Confirm?" (confirming moves the status
from `pending` to `recorded`).
**Accessibility.** Money is read with currency ("one hundred twenty US dollars"); split controls are a
labeled radio group; "who owes whom" is a list, not only a chart.

New screens and sheets in this pack:

1. **New poll** sheet: question, type (free text, dates, stays from the shortlist, ideas), options (2 to
   12), single or multiple, named or anonymous, deadline.
2. **Poll result** state with "Apply winner" (owner) and the tie message "It is a tie between Alfama
   loft and Bairro Alto flat. Pick one to apply."
3. **Room-block request** sheet (Group Trip Pass only). Fields: hotel (pick from the shortlist or type),
   dates, rooms (2 to 50), guests, budget per room, notes. Disclosure block above Submit, in body text:
   "Hermi may earn a commission from the hotel or our host agency. It does not change what you pay."
   and "Sending this creates no charge and no obligation. A person replies by email within 2 business
   days." Status tracker: submitted, in review, quoted, accepted, declined, expired, cancelled.
4. **Trip settings, Pass** block: pass status and expiry, notice 7 days before expiry, renewal offer,
   and for a Trip Pass "Upgrade to Group Trip Pass".
5. **Limit states**: the 9th traveler sheet ("Plan for a bigger group") and the 13th traveler message
   ("A Group Trip Pass holds up to 12 travelers").

Paywall triggers (sheet from 4.14, rules in section 8 of the UI spec; free path has equal weight):

| Trigger id | When it fires | Headline | What it gives on this trip | Free path | Leading offer |
|---|---|---|---|---|---|
| `group_tools` | Free owner opens polls or expenses on a trip with no pass | "Decide together, split costs" | Polls and manual cost splitting on this trip | "View what others add" | Trip Pass (or Plus when the person has two or more active trips) |
| `group_pass` | Open the room-block request, or add a ninth traveler, without a Group Trip Pass | "Plan for a bigger group" | Up to 12 travelers, the room-block request, 80 credits | "Keep to 8 travelers" or "Skip the room block" | Group Trip Pass |
| `invite` (existing) | Free owner taps Invite | "Plan together. They join free." | Invite up to 6 people | "Share a read-only link" | Trip Pass (Group Trip Pass when the trip has 5 or more travelers) |

The decision rule `choose_offering` already returns `group` when a trigger is `group_tools` or the
trip has more than 8 travelers. No paywall appears for invitees about owning the trip, after an
affiliate booking, or during presentation playback.

## 6. Monetization and App Store products

| Product ID | Type | Price (US) | Duration | Group and level | Trial | Entitlement |
|---|---|---|---|---|---|---|
| `hermi_group_trip_pass` | Non-renewing subscription | $19.99 | 90 days | none | none | `group_trip_pass` (one trip) |

- Purchase comes first, binding second. Before purchase the app asks "Which trip is this for?"
  (pre-selected when the purchase started from a trip) and sends the trip with
  `POST /v1/purchases/sync`. A pass bought with no trip waits as "unapplied" in Settings, Purchases
  (kept 12 months) until the owner binds it with `POST /v1/me/passes/{pass_id}/bind`. Only the trip's
  owner can bind, and the purchaser must be that owner. A trip holds one active pass.
- One move: an active pass can move to another trip the same owner owns, once.
- Upgrade from Trip Pass: bind a Group Trip Pass to a trip with an active Trip Pass (see section 2).
  Nothing is refunded by Hermi; Apple refund rules apply to each purchase. A Trip Pass cannot be
  bound to a trip that has a Group Trip Pass (`409 state_conflict`).
- Group Trip Pass limits from its `plans` row: 12 travelers (owner plus up to 11 collaborators), 80
  credits (the `trip_pass` grant with the trip id), 2 live routes and at most 60 live checks, room-block
  request. Credits follow the acting user: a guest first spends their own allowance, then the trip pool.
  Monthly provider-spend ceiling $3.60, daily $0.40.
- Refund: the pass stops granting capabilities, unspent credits are removed, the trip and data stay.
- The app never links to a web page to buy the Group Trip Pass. Every purchase is an In-App Purchase;
  nothing here uses Stripe in Phase 2.
- RevenueCat: add `hermi_group_trip_pass` as a non-renewing product and to the `default` offering.
  Review screenshot and metadata needed; submit with an app version.

## 7. Admin additions

- **Users (08 section 6.2).** Trip passes list with status, binding, move count and upgrade chain; action
  "extend pass" (audited, existing).
- **Group payments and settlements (08 section 6.9).** In Phase 2 this screen lists manual `recorded`
  settlements read-only (as the full spec defines for launch); Stripe state, refunds and disputes arrive
  with Phase 3 ([../phase-3-scale/01-stripe-group-payments.md](../phase-3-scale/01-stripe-group-payments.md)).
- **Concierge queue (08 section 6.8).** Room-block requests appear with kind "room block" (they come
  from `room_block_requests`); until pack 07 builds the queue, each submission emails the concierge
  desk inbox and is listed in a simple read-only Room blocks table (status, dates, rooms, age) with
  status updates by an owner-role action.
- **Overview.** Revenue by stream shows Trip Pass and Group Trip Pass separately.
- **Alert rules.** A room-block request older than 2 business days without a reply (notify).
- **Feature flags.** `group_tools` and `room_block_requests` visible; `group_payments` locked off with a
  note "Phase 3".
- **Support macros.** "How the Group Trip Pass works", "Move my pass to another trip", "Who can see the
  ledger".

## 8. AI additions

None. Polls, expenses and settlements do not use AI, and expense data, poll text and traveler names are
never sent to Anthropic (06 section 12.1: `draft_day` and `draft_trip` never send "names, notes,
expenses, other members"). A later optional idea (suggest poll options from the shortlist) would be a
`explain`-class action and is not in this pack.

## 9. Analytics events

Existing events from the full catalogue: `poll_created {option_count, subject}`, `poll_voted
{selection}`, `expense_added {split_type, member_count_bucket}`, `settle_up_viewed`,
`settlement_started {method}`, `trip_pass_applied {product, is_upgrade}`, `trip_pass_moved`,
`trip_pass_expired`, `paywall_viewed {placement}`.

| Event | Properties | When fired |
|---|---|---|
| `poll_closed` | `selection`, `vote_count_bucket`, `outcome` (`winner`, `tie`, `no_votes`), `by` (`owner`, `deadline`) | Poll closes |
| `poll_winner_applied` | `subject` | Apply winner succeeds |
| `poll_reminder_sent` | none (server side) | Reminder delivered |
| `expense_edited` | `locked_attempt` (bool) | Expense saved or blocked |
| `settlement_confirmed` | `method` | Payee confirms |
| `balance_written_off` | none | Owner writes off |
| `room_block_requested` | `rooms_bucket`, `guests_bucket`, `region` | Request submitted |
| `room_block_status_changed` | `status` (`room_block_requests.status`) | Server status change |
| `traveler_limit_reached` | `limit` (`8`, `12`) | Add traveler blocked |

## 10. Tests

- Split arithmetic property tests: for every method, random amounts and participant sets, shares always
  sum to `amount_trip_minor`; leftovers go to traveler order; balances sum to zero across a trip;
  multi-currency expenses keep both amounts.
- Minimal transfers: for random nets of up to 12 people the result zeroes all balances and never uses
  more than n minus 1 transfers; the exact partition beats or equals greedy on crafted cases; output is
  stable.
- Settlement lifecycle: `pending` until the payee confirms; only `recorded` and `succeeded` reduce
  balances; the payer cannot confirm their own payment; the `stripe` method is refused while `group_payments` is off.
- Polls: single versus multiple enforcement (DB trigger and API), option key validation, closing with
  ties, apply winner per subject, deadline job, viewers can vote but not create, closed polls reject
  votes.
- Entitlements matrix: every tier and pass against `polls`, `cost_splitting` and `room_block_request`;
  Free invitee on a Plus-owned trip can use them; Free owner's own trip gets the preview and paywall;
  Plus with a Group Trip Pass takes the higher traveler limit.
- Traveler cap: 12 travelers allowed on the pass, a 13th refused, a 9th on Trip Pass shows `group_pass`.
- Upgrade: Trip Pass to Group Trip Pass keeps `live_checks_used`, old credits stay spendable, old row
  becomes `upgraded`, a second active pass on one trip refused.
- Expiry: polls close, tools become read-only, data stays exportable, notice sent 7 days before.
- Room block: entitlement, 8 traveler minimum, disclosure present in the DOM and in the email, no
  charge path exists, hidden in unconfirmed regions.
- Tenant isolation: non members cannot read or write polls, votes, expenses, shares, settlements or
  room-block requests (added to the automated cross-tenant suite).
- Offline: an expense added offline syncs once, no duplicate (idempotency key).
- E2E: create a trip with 4 people, poll two stays, apply the winner, add 3 expenses in 2 currencies,
  settle up, mark as paid and confirm.
- Sandbox purchase matrix additions: Group Trip Pass bound to a trip, upgrade from Trip Pass, bind and
  move-once, expiry, refund.

## 11. Tickets

#### P2-011 Group tables, RLS and seeds [L, needs Phase 1 schema]
- Description: migrations `0017_group_tools` and `0018_room_block_requests`, policies, pass and plan changes
  (enum value, constraint swaps, limit keys on the Free, Plus and Trip Pass rows), `plans`, `store_products`,
  consent kind and flag seeds above.
- Accept: empty to head and previous to head pass; shares-sum trigger rejects mismatches; cross-tenant
  suite covers the new tables.
- Touches: `apps/api/hermi/migrations/versions/`, `modules/groups/models.py`.
- Tests: migration, trigger and RLS tests.

#### P2-012 Capability flags and gates [M, needs P2-011, Phase 1 entitlement resolver]
- Description: `polls`, `cost_splitting`, `room_block_request`, `travelers_per_trip` in the merge;
  `group_tools` gate; `traveler_limit` and `room_block` paywall hints.
- Accept: matrix in section 10 passes; Free invitees get tools on trips that have them.
- Touches: `modules/billing/entitlements.py`, `modules/groups/deps.py`.

#### P2-013 Polls API [M, needs P2-012]
- Description: create, vote, close, delete, apply winner, deadline job.
- Accept: ties reported, winners applied per subject, viewers vote.
- Tests: poll tests.

#### P2-014 Poll UI and reminders [M, needs P2-013]
- Description: poll card, New poll sheet, result states, `send_poll_reminders` (at most one per poll per
  user per day), notification types and settings rows.
- Accept: states and copy as in section 5; reminder idempotent.
- Touches: `apps/web/src/routes/group/polls/`, worker `jobs/poll_reminders.py`.

#### P2-015 Expenses and FX [M, needs P2-012]
- Description: expense CRUD with the four split methods, `fx_rates` conversion at entry, receipt upload
  to R2, edit lock rule, audit line on delete.
- Accept: shares always sum; original and converted amounts stored.
- Tests: split property tests, FX tests.

#### P2-016 Balances and minimal transfers [M, needs P2-015]
- Description: net balances, deterministic leftover assignment, exact minimal-transfer partition for up
  to 12 people.
- Accept: properties in section 10; responds under 100 ms for 12 people and 500 expenses.
- Tests: property and stability tests.

#### P2-017 Settlements, confirm and write-off [M, needs P2-016]
- Description: manual settlements, pending to recorded confirmation, write-off, settle-up reminders,
  Stripe method refused behind the flag.
- Accept: lifecycle tests pass; balances update only on recorded.

#### P2-018 Group screens: People, Expenses, Settle up [L, needs P2-015, P2-017]
- Description: segmented Group section, Add expense, Settle up list, Free preview state, states and copy
  from 6.21, CSV export.
- Accept: axe clean; money read with currency by VoiceOver; list not only a chart.
- Touches: `apps/web/src/routes/group/`.

#### P2-019 Offline expenses [M, needs P2-018, Phase 1 offline queue]
- Description: queue expense adds and confirmations offline with idempotency keys and "Waiting to sync".
- Accept: no duplicates after reconnect; conflicts use the existing 409 sheet.

#### P2-020 Group Trip Pass product, bind and upgrade [M, needs P2-012, Phase 1 Trip Pass binding]
- Description: sell `hermi_group_trip_pass`, bind like Trip Pass, upgrade path from Trip Pass,
  12 traveler and 11 collaborator caps, credits grant of 80, expiry handling that closes polls.
- Accept: a pass supports 12 travelers and not a 13th; upgrade keeps the live-check counter; expiry
  behavior as in section 2.
- Touches: `modules/billing/passes.py`, `apps/web/src/routes/trip-settings/`.

#### P2-021 Room-block request [M, needs P2-020]
- Description: form, API, disclosure, email to the concierge desk inbox through Resend until pack 07,
  status visible to the requester, region gate shared with concierge, requester cancel.
- Accept: needs a Group Trip Pass (otherwise the `group_pass` paywall); creates no charge or
  obligation; disclosure always visible; hidden where concierge is not confirmed.

#### P2-022 Group paywalls [S, needs P2-012, Phase 1 paywall engine]
- Description: `group_tools` and `group_pass` triggers, Free owner preview, offering `group`, plan
  comparison rows for Group Trip Pass.
- Accept: decision table tests; free path present; no paywall for invitees about owning the trip.

#### P2-023 Admin room blocks, pass tools and alerts [S, needs P2-021]
- Description: Room blocks table, settlements read-only list, pass chain view, alert rule.
- Accept: every action audited; roles enforced.

#### P2-024 Purchase matrix and review assets [S, needs P2-020]
- Description: product metadata, review screenshot, rerun the sandbox matrix for bind, upgrade, move,
  expiry and refund; submit with the next app version.
- Accept: matrix recorded.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Rounding bugs make balances not sum to zero | Integer minor units, deterministic leftovers, property tests, DB sum trigger |
| Users expect Hermi to move money | Copy says Hermi records who owes whom; Stripe collection is Phase 3 and never Apple IAP |
| Pass confusion (Trip Pass, Group Trip Pass, Plus) | Best-of rule stated in the paywall; upgrade path; pass status in trip settings |
| 12 travelers and AI cost on one trip | Credits follow the acting user; pass pool 80; ceilings per account |
| Room-block leads overload the founder or need licensing | Same region gate as concierge; 2 business day reply promise; capacity setting from pack 07 |
| Children or friends without accounts entered as travelers | First name and color only, no email or birthdate |
| Free invitees can write expenses on a trip that later lapses | Read only on lapse, data kept, export always works |
