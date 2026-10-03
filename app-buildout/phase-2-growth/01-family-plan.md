# Pack 01: Family plan and households

Part of [Phase 2: growth](README.md). Written 2026-09-30. Source definitions are in the full specs
([03 section 5.2](../reference-full-spec/03-database-schema.md), [04 section 5.3](../reference-full-spec/04-api-spec.md),
[07 sections 4 and 7.8](../reference-full-spec/07-monetization-spec.md)); this file is self-contained for the build.

| Item | Value |
|---|---|
| Build order | 1 (month 7) |
| Flag | None. The `family` plan is sellable when `plans.is_active` is true (the same rule as the full roadmap, WF-077). |
| Needs from Phase 1 | Entitlements resolver, RevenueCat webhook and purchases, credit ledger with `reserve_credits`, paywall engine, invites, admin users screen |
| Tickets | P2-001 to P2-010 |
| Tier and products | `family`, `hermi_family_monthly` ($8.99), `hermi_family_annual` ($59.99) |

## 1. Goal and why now

**Goal.** Let one payer cover up to six people in a household: each member gets Plus capabilities on
their own trips, 5 live routes, and all of them draw from one pool of 150 credits a month. Persona P3
("Priya, two kids, her parents joining for one week") from [the product spec](../reference-full-spec/01-product-spec.md)
is the buyer: four adults in the household share 150 credits and 5 live routes, and use read-only share
links for grandparents.

**Why now.**

- Phase 1 sells one subscription (`plus`). The Family plan is the cheapest revenue lift because the
  schema, entitlement algorithm and pool logic were designed together and no AI or provider cost is
  added: the pooled ceiling ($3.40 a month) is lower than two separate Plus ceilings ($4.50).
- Price story. Two Plus annual plans cost $79.98. Family annual costs $59.99 (about $5.00 a month).
  Couples who outgrow the free "invite 1 collaborator" rule and families with grandparents have a
  clear reason to upgrade without a pass per trip.
- Competitive reasons. Wanderlog Pro ($39.99 a year) and TripIt Pro ($49 a year) are per person plans
  (reported, verify; see [the business plan](../context/business-plan/01-business-plan.md) competitor table), so a
  household that wants everyone to have offline, live tracking and AI pays once per person. A pooled
  household plan is a simple, honest price point against them.
- Margin watch. The weakest cell in the pricing model is Family annual
  ([09 revenue expansion](../context/business-plan/09-revenue-expansion.md) section 2): alert at $3.00 of pooled spend
  and reprice if more than 25 percent of families sit near the ceiling. This pack builds that alert.

## 2. User stories and acceptance criteria

### F-SUB-3 Family (verbatim from the full product spec)

- Story: As a household, I want to share one plan, so that everyone uses the same pool.
- Acceptance:
  - The `family` payer creates a household (`households`) and invites up to 6 members
    (`household_members`) in the app; Apple Family Sharing stays off.
  - Members get `plus` capabilities on their own trips, 5 live routes and 150 credits pooled,
    drawn by whoever acts.
  - A person can be in one household at a time; leaving takes effect immediately and the person
    returns to their own tier.
  - When the payer cancels, the household reverts to `free` at period end.
- Tier: `family`.

### Stories added by this pack

| ID | Story | Acceptance |
|---|---|---|
| FAM-1 | As a Family payer, I set up my household right after buying, so my people can join. | After a `family` purchase the app opens "Set up your household" (name defaults to "Family"). A household is created once per Family subscription and `subscriptions.household_id` is set. Skipping leaves an "Invite your household" card on Account until done. |
| FAM-2 | As a payer, I invite members by email or by link. | Link `https://hermi.world/h/<token>`, 7 day expiry, single use; email sent through Resend when an address is given. Seats count invited plus active members (6 including the owner); the seventh invite is refused with `403 limit_reached`. |
| FAM-3 | As an invitee, I see what joining changes before I accept. | The accept screen says what they get (Plus capabilities on their own trips, 5 live routes, the shared 150 credits) and what stays theirs (their trips, their purchased credits). A user with their own paid subscription is told it keeps running and stays separate; they keep the higher tier (best of) and their own allowance and also draw from the pool. |
| FAM-4 | As a member, I can leave any time. | Benefits end immediately; the member's own purchased credits and own trips stay with them; trips they owned keep their data and revert to their personal tier capabilities; pooled credits already spent stay spent. |
| FAM-5 | As a payer, I can remove a member and see who spends the pool. | Removal ends benefits immediately and a removed member can be re-invited. Household settings shows per member spend this month ("Spent by Ana: 12"). The pool can be exhausted by one member; there is no per member quota. |
| FAM-6 | As a payer, I am told before a downgrade or lapse removes my household. | 14 days before the boundary an in-app notice lists who will lose benefits. On Family to Plus or cancellation, the household dissolves at `period_end`: members lose household benefits and the pooled credits, keep purchased credits and their own trips, and fall to Free if they have no plan. |
| FAM-7 | As the business, I cannot be gamed by strangers rotating through one plan. | Churn guard (defaults): a person can join or leave a household at most twice in 12 months, and a household may have at most 2 member replacements per quarter, counted from `household_members.joined_at` and `removed_at`. |
| FAM-8 | As a payer upgrading from Plus, I get the new allowance immediately. | On `PRODUCT_CHANGE` the tier switches now and the new grant is the difference up to the new amount (Plus 60 to Family 150: grant 90); existing pools are never reduced. Downgrades apply at renewal. |

Not supported at launch: transferring household ownership (the owner must resubscribe under the new
owner), Apple Family Sharing, more than one household per person.

## 3. Database additions

Migration `0016_households_family` (Phase 1 ends at `0015_seed`). Phase 1 deliberately has none of
this: [Phase 1 03 section 1.1](../phase-1-launch/03-database-schema.md) lists `households` and
`household_members`, the three `household_id` columns, the `household_monthly` credit kind and the
`family` plan row as dropped, and its section 14 lists what this pack adds. The tables, trigger and
policies are reused from [the full 03 section 5.2](../reference-full-spec/03-database-schema.md).

A household only pools credits and covers the Family subscription (up to 6 members). It grants no
trip access; trips are shared through `trip_members`.

```sql
CREATE TYPE household_role AS ENUM ('owner', 'member');
CREATE TYPE household_member_status AS ENUM ('invited', 'active', 'removed');

CREATE TABLE households (
  id             uuid PRIMARY KEY DEFAULT uuidv7(),
  name           text NOT NULL DEFAULT 'Family' CHECK (char_length(name) BETWEEN 1 AND 60),
  owner_user_id  uuid NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  max_members    smallint NOT NULL DEFAULT 6 CHECK (max_members BETWEEN 1 AND 6),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_households_owner ON households (owner_user_id);
SELECT add_updated_at_trigger('households');

CREATE TABLE household_members (
  id                  uuid PRIMARY KEY DEFAULT uuidv7(),
  household_id        uuid NOT NULL REFERENCES households (id) ON DELETE CASCADE,
  user_id             uuid REFERENCES users (id) ON DELETE CASCADE,   -- null while an emailed invite is pending
  role                household_role NOT NULL DEFAULT 'member',
  status              household_member_status NOT NULL DEFAULT 'invited',
  invited_email       citext,
  invite_token_hash   bytea,                                          -- hash only; 7 day expiry
  invite_expires_at   timestamptz,
  invited_by          uuid REFERENCES users (id) ON DELETE SET NULL,
  joined_at           timestamptz,
  removed_at          timestamptz,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_household_members_user CHECK (status = 'invited' OR user_id IS NOT NULL),
  CONSTRAINT ck_household_members_invite CHECK (status <> 'invited' OR (invite_token_hash IS NOT NULL AND invite_expires_at IS NOT NULL))
);
CREATE UNIQUE INDEX uq_household_members_user ON household_members (household_id, user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX uq_household_members_one_active ON household_members (user_id) WHERE status = 'active';
CREATE UNIQUE INDEX uq_household_members_one_owner ON household_members (household_id) WHERE role = 'owner' AND status = 'active';
CREATE UNIQUE INDEX uq_household_members_invite ON household_members (invite_token_hash) WHERE invite_token_hash IS NOT NULL;
SELECT add_updated_at_trigger('household_members');

-- Size cap (invited and active count). Locks the household row to serialize concurrent joins.
CREATE FUNCTION enforce_household_size() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE v_max smallint; v_count integer;
BEGIN
  IF NEW.status NOT IN ('invited', 'active') THEN RETURN NEW; END IF;
  SELECT max_members INTO v_max FROM households WHERE id = NEW.household_id FOR UPDATE;
  SELECT count(*) INTO v_count FROM household_members
   WHERE household_id = NEW.household_id AND status IN ('invited', 'active') AND id <> NEW.id;
  IF v_count >= v_max THEN RAISE EXCEPTION 'household_full' USING ERRCODE = 'WF409'; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_household_size BEFORE INSERT OR UPDATE OF status ON household_members
  FOR EACH ROW EXECUTE FUNCTION enforce_household_size();

CREATE FUNCTION in_my_household(p_household uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM household_members
                  WHERE household_id = p_household AND user_id = app_user_id() AND status = 'active')
$$;
```

Columns, enum values and constraint swaps on Phase 1 tables (expand steps; each is cheap):

```sql
ALTER TABLE subscriptions ADD COLUMN household_id uuid REFERENCES households (id) ON DELETE SET NULL;   -- set for Family: covers all active members
ALTER TABLE entitlements  ADD COLUMN household_id uuid REFERENCES households (id) ON DELETE SET NULL;   -- Family members inherit the tier through here
ALTER TABLE credit_grants ADD COLUMN household_id uuid REFERENCES households (id) ON DELETE SET NULL;   -- Family pooled credits
CREATE INDEX ix_subscriptions_household ON subscriptions (household_id) WHERE household_id IS NOT NULL;
CREATE INDEX ix_entitlements_household ON entitlements (household_id) WHERE household_id IS NOT NULL;

ALTER TYPE credit_grant_kind ADD VALUE 'household_monthly';              -- own migration step; it cannot be used in the same transaction
-- After that step:
ALTER TABLE credit_grants ADD CONSTRAINT ck_credit_grants_one_owner CHECK (NOT (user_id IS NOT NULL AND household_id IS NOT NULL)) NOT VALID;
ALTER TABLE credit_grants ADD CONSTRAINT ck_credit_grants_household CHECK (kind <> 'household_monthly' OR household_id IS NOT NULL) NOT VALID;
ALTER TABLE credit_grants VALIDATE CONSTRAINT ck_credit_grants_one_owner;
ALTER TABLE credit_grants VALIDATE CONSTRAINT ck_credit_grants_household;
CREATE UNIQUE INDEX uq_credit_grants_household_period ON credit_grants (household_id, kind, period_key) WHERE household_id IS NOT NULL AND period_key IS NOT NULL;
CREATE INDEX ix_credit_grants_household_spend ON credit_grants (household_id, expires_at) WHERE remaining > 0;

ALTER TABLE entitlements DROP CONSTRAINT ck_entitlements_source;
ALTER TABLE entitlements ADD CONSTRAINT ck_entitlements_source CHECK (source IN ('none', 'subscription', 'household', 'comp'));   -- Phase 3 adds 'advisor'
```

Household pool in the credit functions. Phase 1's `credit_balances` view and `reserve_credits()` have no
household branch; this migration replaces them with the versions from
[the full 03 section 5.13](../reference-full-spec/03-database-schema.md) (only the marked lines differ from Phase 1).
`settle_credits()`, expiry and refund functions need no change because they work per grant.

```sql
DROP VIEW credit_balances;
CREATE VIEW credit_balances WITH (security_invoker = true) AS
SELECT user_id,
       household_id,                                                                          -- new
       trip_id,
       sum(remaining)::integer AS remaining,
       (sum(remaining) FILTER (WHERE kind IN ('monthly', 'household_monthly')))::integer AS allowance_remaining,   -- changed
       (sum(remaining) FILTER (WHERE kind = 'purchase'))::integer AS purchased_remaining,
       min(expires_at) FILTER (WHERE remaining > 0) AS next_expiry
  FROM credit_grants
 WHERE remaining > 0 AND (expires_at IS NULL OR expires_at > now())
 GROUP BY user_id, household_id, trip_id;                                                       -- changed

CREATE OR REPLACE FUNCTION reserve_credits(
  p_user uuid, p_trip uuid, p_amount integer, p_action ai_action, p_run uuid, p_idem text
) RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE
  v_res uuid; v_household uuid; v_need integer := p_amount; v_take integer; g record;     -- v_household is new
BEGIN
  IF p_amount <= 0 THEN RAISE EXCEPTION 'amount must be positive'; END IF;
  SELECT reservation_id INTO v_res FROM credit_ledger
   WHERE idempotency_key = p_idem AND entry_type = 'reserve' LIMIT 1;
  IF FOUND THEN RETURN v_res; END IF;
  IF EXISTS (SELECT 1 FROM credit_debts WHERE user_id = p_user AND amount > 0) THEN
    RAISE EXCEPTION 'credit_debt' USING ERRCODE = 'WF402';
  END IF;

  SELECT household_id INTO v_household FROM household_members WHERE user_id = p_user AND status = 'active';   -- new
  v_res := uuidv7();

  FOR g IN
    SELECT id, remaining FROM credit_grants
     WHERE remaining > 0
       AND (expires_at IS NULL OR expires_at > now())
       AND (user_id = p_user OR (household_id IS NOT NULL AND household_id = v_household))      -- changed
       AND (trip_id IS NULL OR trip_id = p_trip)
       AND (restricted_action IS NULL OR restricted_action = p_action)
     ORDER BY CASE kind WHEN 'monthly' THEN 10 WHEN 'household_monthly' THEN 10 WHEN 'promo' THEN 20   -- changed
                        WHEN 'trip_pass' THEN 30 WHEN 'adjustment' THEN 35 ELSE 40 END,
              expires_at NULLS LAST, id
       FOR UPDATE
  LOOP
    EXIT WHEN v_need = 0;
    v_take := LEAST(g.remaining, v_need);
    UPDATE credit_grants SET remaining = remaining - v_take WHERE id = g.id;
    INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, reservation_id, action, run_id, trip_id, idempotency_key)
    VALUES (p_user, g.id, 'reserve', -v_take, v_res, p_action, p_run, p_trip, p_idem);
    v_need := v_need - v_take;
  END LOOP;

  IF v_need > 0 THEN
    RAISE EXCEPTION 'insufficient_credits' USING ERRCODE = 'WF402';   -- rolls back the partial reserve
  END IF;
  RETURN v_res;
END $$;
```

Row-level security (a new table includes its own `GRANT`, `ENABLE ROW LEVEL SECURITY` and policies in
the same migration; the tenant-isolation test fails otherwise). Phase 1's `credit_grants_select` and
`subscriptions_select` policies allow only the owning user; Family widens them to the household:

```sql
ALTER TABLE households ENABLE ROW LEVEL SECURITY;
CREATE POLICY households_select ON households FOR SELECT USING (owner_user_id = (SELECT app_user_id()) OR in_my_household(id));
CREATE POLICY households_update ON households FOR UPDATE USING (owner_user_id = (SELECT app_user_id()));
ALTER TABLE household_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY household_members_select ON household_members FOR SELECT USING (user_id = (SELECT app_user_id()) OR in_my_household(household_id));
CREATE POLICY household_members_write ON household_members FOR ALL
  USING (household_id IN (SELECT id FROM households WHERE owner_user_id = (SELECT app_user_id())))
  WITH CHECK (household_id IN (SELECT id FROM households WHERE owner_user_id = (SELECT app_user_id())));

-- Pooled balances: readable by the owner user or by any active member of the household.
DROP POLICY credit_grants_select ON credit_grants;
CREATE POLICY credit_grants_select ON credit_grants FOR SELECT
  USING (user_id = (SELECT app_user_id()) OR (household_id IS NOT NULL AND in_my_household(household_id)));
DROP POLICY subscriptions_select ON subscriptions;
CREATE POLICY subscriptions_select ON subscriptions FOR SELECT
  USING (user_id = (SELECT app_user_id()) OR (household_id IS NOT NULL AND in_my_household(household_id)));
-- credit_ledger stays per acting user (each member sees their own spend); per member spend for the owner is served by the API from the query below.
```

The API role cannot read other members' ledger rows, so the owner's "Spent by Ana: 12" view is served by
a `SECURITY DEFINER` function `household_usage(p_household uuid)` that checks the caller is the household
owner and runs the query below.

Seed (idempotent; from [03 section 11.1 and 11.2](../reference-full-spec/03-database-schema.md)). Phase 1 does not seed the
`family` row at all, not even inactive, so this migration inserts it with the limits the entitlement merge
reads, including `household_members_max`, and adds the keys Phase 1 dropped. The two Family products are
inserted active:

```sql
INSERT INTO plans (code, kind, name, rank, monthly_credits, credits_granted, credits_valid_days, duration_days, feature_flag_key, is_active, sort_order, limits) VALUES
('family', 'tier', 'Family', 30, 150, 0, NULL, NULL, NULL, true, 20,
 '{"active_trips":25,"active_trips_bonus":0,"routes_per_trip":5,"live_routes":5,"live_window_days":120,"price_alerts":3,"live_alerts":true,
   "collaborators":6,"travelers_per_trip":8,"can_invite":true,"saved_lodging_per_trip":100,"lodging_compare":4,
   "places_searches_per_day":100,"polls":true,"cost_splitting":true,"room_block_request":false,"group_payments":false,
   "hide_presentation_footer":true,"scheduled_routines":false,"priority_queue":false,"credit_rollover_cap":0,"taster_agent_runs":0,
   "household_members_max":6,"monthly_ceiling_micros":3400000,"daily_ceiling_micros":400000}')
ON CONFLICT (code) DO NOTHING;

INSERT INTO store_products (product_id, store, plan_code, period, price_minor, currency, trial_days, is_active) VALUES
('hermi_family_monthly',   'apple', 'family', 'month',  899, 'USD', 0, true),
('hermi_family_annual',    'apple', 'family', 'year',  5999, 'USD', 0, true)      -- no trial: only hermi_plus_annual has one
ON CONFLICT (product_id) DO NOTHING;

-- Phase 1 seeds serpapi_live_fares for plus and trip_pass only; Family gets live tracking too.
UPDATE feature_flags SET rules = jsonb_set(rules, '{tiers}', '["plus","trip_pass","family"]'::jsonb) WHERE key = 'serpapi_live_fares';
```

Queries this pack adds (not tables):

```sql
-- Per member spend this month, for "Spent by Ana: 12" (settled charges net of refunds); runs inside household_usage().
SELECT l.user_id, -sum(l.delta) AS credits_spent
  FROM credit_ledger l JOIN credit_grants g ON g.id = l.grant_id
 WHERE g.household_id = :household_id
   AND l.entry_type IN ('reserve', 'refund')
   AND l.created_at >= date_trunc('month', now())
 GROUP BY l.user_id;

-- Churn guard: joins and leaves in the last 12 months for one person.
SELECT count(*) FROM household_members
 WHERE user_id = :user_id AND (joined_at > now() - interval '12 months' OR removed_at > now() - interval '12 months');

-- Pooled provider-spend ceiling (03 section 7.4 sums one user; a Family member is checked against the household).
-- Replace ":user_id = user_id" in the spend CTEs of 7.4 with the member list below and compare with the $3.40 Family ceiling.
SELECT user_id FROM household_members
 WHERE household_id = (SELECT household_id FROM household_members WHERE user_id = :user_id AND status = 'active')
   AND status = 'active';
```

The entitlement algorithm already exists from Phase 1 (07 section 4.2); this pack turns on its
`household` branch (a member of a household whose owner has an active Family subscription resolves to
`family` with `source = 'household'`; the `Tier` type gains `family`, additive per
[Phase 1 04 section 1.1](../phase-1-launch/04-api-spec.md)). Provider-spend ceilings for Family are
pooled across active members: the ceiling function sums `ai_usage` and `provider_calls` over the member
list above, which is the simplification this pack adopts (spend by a member who left during the month
stays with the household for that month).

## 4. API additions

From [04 section 5.3](../reference-full-spec/04-api-spec.md), verbatim. A household belongs to a Family subscriber and
shares the tier, the pooled 150 credits and 5 live routes across up to 6 members. Trips stay per-trip
membership; the household only shares entitlements and the credit pool.

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /households/current` | user | none | none to `Household \| null` | Household the caller belongs to, with members and pooled credit balance. |
| `POST /households` | user with tier `family` | Family | `{ name: string }` to 201 `Household` | Creates `households` and an `owner` `household_members` row. One household per Family subscription. |
| `PATCH /households/{id}` | household owner | none | `{ name? }` to `Household` | Rename. |
| `POST /households/{id}/invites` | household owner | seats left under 6 | `{ email?: string }` to 201 `HouseholdInvite` | Universal link `https://hermi.world/h/<token>`, 7 day expiry, single use. Email sent through Resend when `email` is set. |
| `POST /household-invites/{token}/accept` | user | none | none to `Household` | Joins; entitlements recomputed (member gets Family tier, draws from the pool). Fails with `410 invite_expired`, `403 limit_reached` (6 seats), `409 already_member`. A user with their own paid sub is told their sub keeps running and stays separate. |
| `DELETE /households/{id}/members/{user_id}` | household owner, or the member themself | none | 204 | Removes member; their entitlements recomputed at once. The owner cannot be removed while others remain. |
| `DELETE /households/{id}` | household owner | none | 204 | Dissolves; members fall back to their own tier. |

```ts
type Household = {
  id: Uuid; name: string
  members: { user_id: Uuid; display_name: string | null; role: "owner" | "member"; joined_at: string }[]
  seats_total: 6; seats_used: number
  pooled_credits: { balance: number; monthly_grant: 150 }
}
type HouseholdInvite = { id: Uuid; url: string; expires_at: string }
```

Additions in this pack:

| Endpoint | Auth | Gate and cost | Request and response | Errors and side effects |
|---|---|---|---|---|
| `GET /households/{id}/usage` | household owner | none | none to `{ month: string, members: { user_id: Uuid, display_name: string \| null, credits_spent: number }[] }` | The per member query above. Members see only their own line. |
| `GET /household-invites/{token}` | none (token) | throttled per IP | none to `{ household_name: string, inviter_name: string, seats_left: number, expires_at: string }` | Powers the accept screen before sign-in. Reveals no member names. `410 invite_expired` when past expiry, revoked or used. |
| `POST /households/{id}/invites/{invite_id}/revoke` | household owner | none | 204 | Cancels a pending invite. |
| `GET /me/entitlements` | user | none | `Entitlements` | Already exists; `source: "household"` and `limits.live_routes: 5` for members. |

Errors: `403 limit_reached` (reason `family_members`) for the seventh seat, `409 already_member`,
`409 state_conflict` when a person hits the churn guard (the body says when they can join again),
`403 entitlement_required` when a non Family user calls `POST /households`.

Webhook effects ([04 section 6](../reference-full-spec/04-api-spec.md)): "Family changes update household entitlements."
The RevenueCat handler recomputes `entitlements` for every household member on `INITIAL_PURCHASE`,
`RENEWAL`, `PRODUCT_CHANGE`, `EXPIRATION` and `REFUND` of a `family` product. The
`grant_monthly_credits` job writes one `household_monthly` grant of 150 (`period_key` of the period
start) for the household, not for the payer.

Universal links: add `/h/*` to `/.well-known/apple-app-site-association` (no redirect) and route
`/h/:token` in React Router.

## 5. UI screens and paywall triggers

Screens (web and iOS; sentence case, plain verbs, no em dashes):

1. **Household** (Account, Plan and credits, Household). Members list with avatar, role chip and
   joined date; "Invite" (link or email) with "4 of 6 seats used"; pooled balance "98 of 150 left,
   renews 1 Nov"; per member spend "Spent by Ana: 12" (owner only); "Leave household" for members;
   "Remove" per member for the owner; rename.
   Copy: "Everyone in your household shares 150 credits a month. Your trips and any credits you bought
   stay yours."
2. **Set up your household** (after purchase, and as a card on Account until done).
3. **Join a household** (from `/h/<token>`): inviter name, what you get, what stays yours, [Join]
   [Not now]. Sign-in first if needed.
4. **Plan and credits** (existing 6.26): shows "Family" with the pooled balance; Compare plans table
   gets a Family column (already in the Phase 1 table: "Unlimited, 6 household members", 5 live
   routes, 150 shared credits).
5. **Dissolve notice** banner 14 days before the boundary: "Your household ends on 14 Mar. Ana, Sam
   and Lee will go back to their own plans. Keep Family to keep them."

States: loading skeletons; empty (no household yet): "Plan as a household" card; error: "We could not
load your household. Your plan has not changed. Try again."; offline: read only ("Connect to invite
people"); no permission: members see the list and their own spend, not invite controls.

Paywall triggers (the engine is Phase 1; this pack turns the `household` trigger on):

| Trigger id | When it fires | Headline | What it gives | Free path (equal weight) | Leading offer |
|---|---|---|---|---|---|
| `household` | Invite a second household member, or household signals (07 section 6.4): invited or asked to invite two or more people to a household; 3 or more travelers who are also trip members on at least two different trips; tapped "Family" in the plan comparison | "Plan as a household" | Plus for up to 6 people, 150 pooled credits | "Invite them to this trip for free" | Family |

The signal never uses names, ages or inferred relationships. Experiment 7 from
[07 section 6.7](../reference-full-spec/07-monetization-spec.md) (Family as a row in `default` versus household trigger
only) runs after launch.

## 6. Monetization and App Store products

| Product ID | Type | Price (US) | Duration | Group and level | Trial | Entitlement |
|---|---|---|---|---|---|---|
| `hermi_family_monthly` | Auto-renewing subscription | $8.99 | 1 month | `hermi_membership`, level 2 | none | `family` |
| `hermi_family_annual` | Auto-renewing subscription | $59.99 | 1 year | `hermi_membership`, level 2 | none | `family` |

- Add both to the existing `hermi_membership` group (levels, highest first: Pro 1, Family 2, Plus 3).
  Apple Family Sharing is off on every product. Family, Family Sharing and household are different
  things: one Apple ID pays; members are invited inside Hermi.
- Every new product needs localized names and descriptions, a paywall review screenshot and the
  subscription terms text, and must be submitted with an app version for its first review.
- RevenueCat: add both products to the `default` offering as a package; entitlement `family`.
- Credits: `household_monthly` grant 150 a month (annual plans grant monthly by the scheduler); pooled
  ceiling $3.40 a month, daily $0.40. Spend order stays: monthly or household allowance, promo, trip
  pass, adjustment, purchased.
- Upgrades (Plus to Family or Pro, Family to Pro): Apple applies immediately and refunds unused time
  pro rata; Hermi switches the tier now, recomputes household capabilities, grants the difference.
  Downgrades (Family to Plus) apply at renewal and dissolve the household at the boundary.
- Refunds: subscription status `refunded`, revoke now, claw back the unspent allowance of that period
  (the household pool for that period), as in 07 section 7.6.
- Grace: `in_grace` counts as active; members keep access during the 16 day billing grace period;
  the owner sees the banner and gets emails on day 0, 7 and 14.

## 7. Admin additions

- **Users (08 section 6.2).** User detail shows a household card: owner, members with status, seats
  used, pool balance for the month, per member spend, churn guard counters. Actions (audited, with a
  reason): remove a member, revoke an invite, dissolve a household, reset a churn guard block (owner
  role only). Comp a subscription already allows `family` (engineer up to 90 days, owner up to 12
  months); a comped Family creates the household the same way.
- **Overview.** MRR split by `plus`, `family`, `pro` already exists; add the Family share and average
  seats used.
- **Credits and AI spend.** Household pool buckets appear as `household_monthly`; add a column
  "pooled spend as a share of the $3.40 ceiling".
- **Alert rules (08 section 10).** Family pooled spend at or above $3.00 in a month (notify);
  more than 25 percent of active households above $3.00 (page the owner by email: reprice decision).
- **Support macros.** "How households work", "Remove someone from my household", "I bought Family
  but cannot invite".

## 8. AI additions

None. Household members draw from the pool through the normal `reserve_credits` path, and the
existing ceilings apply to the pool as one account (`ceiling_for(actor, trip)`, 06 section 6.5).
Prompts never contain household or member names.

## 9. Analytics events

Defined once in `packages/shared/src/events.ts`; no PII, enums and buckets only. Existing events used:
`paywall_viewed {placement: household}`, `purchase_started`, `purchase_completed`,
`subscription_changed {direction, from, to}`, `subscription_canceled`.

| Event | Properties | When fired |
|---|---|---|
| `household_created` | none | Household created |
| `household_invite_sent` | `channel` (`link`, `email`), `seats_used_bucket` | Invite created |
| `household_invite_opened` | `signed_in` (bool) | Accept screen loaded |
| `household_member_joined` | `seats_used_bucket`, `had_own_plan` (bool) | Invite accepted |
| `household_member_left` | `by` (`self`, `owner`) | Member leaves or is removed |
| `household_dissolved` | `reason` (`owner_request`, `downgrade`, `lapse`, `refund`) | Household ends |
| `household_pool_low_shown` | `balance_bucket` | Pool under 20 percent banner shown |

## 10. Tests

- Pooled spend concurrency: 6 members reserve in parallel against one pool, no overspend, refunds
  return to the same grant (extends the Phase 1 ledger tests).
- Membership limit: the seventh invite or accept is refused (`household_full`, API `limit_reached`);
  concurrent accepts serialize on the household row.
- One active household per user; accepting while already active returns `already_member`.
- Churn guard: third join in 12 months refused; replacements per quarter counted.
- Upgrade grant arithmetic: Plus 60 to Family 150 grants 90, never reduces an existing pool; grant
  `period_key` includes the change date.
- Downgrade and lapse: household dissolves at `period_end`, members recompute to their own tier,
  purchased credits kept, trips kept, pooled credits gone.
- Member with own Plus: best of tier, own allowance plus pool, removal leaves own plan intact.
- RLS and tenant isolation: a non member cannot read a household, its members or its grants (added
  to the automated cross-tenant suite); a member cannot read another member's email.
- Webhook replay: `PRODUCT_CHANGE`, `EXPIRATION`, `REFUND` replays recompute every member once, no
  double grants.
- Sandbox purchase matrix additions: Family monthly and annual purchase, Plus to Family upgrade,
  Family to Plus downgrade at renewal, refund, restore on a second device.
- E2E: buy Family, create household, invite by link, second account joins, both spend from one pool.

## 11. Tickets

Conventions and the definition of done are in [the Phase 2 README](README.md) section 4. "Needs" lists
Phase 1 capabilities or earlier Phase 2 tickets.

#### P2-001 Household schema and RLS [M, needs Phase 1 schema]
- Description: migration `0016_households_family` with the tables, size trigger, extra columns and
  constraint swaps, `in_my_household`, replacement `credit_balances` view and `reserve_credits()`,
  widened `credit_grants` and `subscriptions` policies, `household_usage()` and seed rows above.
- Accept: empty to head and previous revision to head both pass; cross-tenant suite includes
  households; seventh member raises `household_full`.
- Touches: `apps/api/hermi/migrations/versions/`, `apps/api/hermi/modules/billing/models.py`.
- Tests: migration, RLS and trigger tests.

#### P2-002 Household API [M, needs P2-001]
- Description: the seven endpoints in section 4 plus usage, invite preview and revoke; Resend invite
  email (plain text too) with the inviter's display name.
- Accept: one household per Family subscription; owner cannot be removed while others remain; tokens
  are 128 bit, stored hashed, expire in 7 days.
- Touches: `apps/api/hermi/modules/billing/family.py`.
- Tests: endpoint tests per role; token expiry and single use.

#### P2-003 Entitlement resolver household branch [M, needs P2-001]
- Description: `user_tier` returns `family` for active members of a household whose owner has an
  active Family subscription; best-of with own subscription; nightly sweep and event recompute.
- Accept: member limits show `live_routes` 5 and `collaborators` 6; owner lapse dissolves access at
  period end; `GET /me/entitlements` reports `source: "household"`.
- Touches: `apps/api/hermi/modules/billing/entitlements.py`.
- Tests: resolver table tests across owner and member states.

#### P2-004 Pooled credits and monthly grant [M, needs P2-001, Phase 1 ledger]
- Description: `household_monthly` grant (150) by `grant_monthly_credits` for monthly and annual
  Family; the replacement `reserve_credits` draws from the household pool first; the pooled $3.40
  ceiling sums spend over the active member list (the ceiling check in 03 section 7.4 gets the member
  query); `credit_balances` and `GET /me/credits` report the pool.
- Accept: pool spend is charged to the acting member in `credit_ledger`; grants are idempotent on
  (`household_id`, `kind`, `period_key`).
- Touches: `apps/api/hermi/modules/billing/credits.py`, worker `grant_monthly_credits`.
- Tests: concurrency test, idempotent grant, refund to same pool.

#### P2-005 Family purchase lifecycle [L, needs P2-003, P2-004, Phase 1 RevenueCat webhook]
- Description: handle `family` products in the webhook: subscription with `household_id`, upgrade
  difference grant, downgrade at renewal and dissolve, refund clawback, grace and retry behavior,
  owner notices (14 days before dissolve, grace emails).
- Accept: every scenario in section 10 passes against recorded RevenueCat fixtures.
- Touches: `apps/api/hermi/modules/billing/webhooks.py`, `family.py`.
- Tests: fixture replay, idempotency.

#### P2-006 Churn guard and abuse controls [S, needs P2-002]
- Description: join and leave counters from `household_members`, replacement cap per quarter, admin
  reset, `409 state_conflict` body with the next allowed date.
- Accept: defaults configurable through `feature_flags` settings; limits audited.
- Tests: counters across boundaries.

#### P2-007 Household UI [L, needs P2-002]
- Description: Household screen, Set up card, Join screen, dissolve banner, pool meter, per member
  spend, states and copy in section 5; universal link `/h/:token`.
- Accept: axe clean; VoiceOver reads seats and balances as text with units; no em dashes in copy.
- Touches: `apps/web/src/routes/household/`, AASA file.
- Tests: Playwright flows for owner and invitee.

#### P2-008 Family paywall and plan comparison [S, needs P2-003, Phase 1 paywall engine]
- Description: turn on the `household` trigger and the `family` offering; add household signal
  computation (07 section 6.4); Family column in Compare plans; Family in `default` per experiment 7
  settings.
- Accept: no paywall in the first session; mute rules apply; free path present.
- Tests: decision table tests.

#### P2-009 Admin household tools and alerts [S, needs P2-002]
- Description: household card, actions, pooled spend column and the two alert rules in section 7.
- Accept: every action writes `audit_log` with a reason; permissions by role.
- Tests: permission and audit tests.

#### P2-010 App Store products, purchase matrix and review assets [M, needs P2-005]
- Description: create both products in App Store Connect and RevenueCat, localized metadata, review
  screenshot, rerun the sandbox purchase matrix for Family, submit with the next app version.
- Accept: matrix recorded; products approved with the app update.
- Touches: `docs/launch/`.

## 12. Risks

| Risk | Mitigation |
|---|---|
| One member drains the pool | Per member usage visible to the owner; pooled ceiling; alert at $3.00; reprice rule |
| Plan sharing by strangers | One household per person, churn guard, invites need accounts, owner sees members |
| Upgrade proration and grant mistakes | Grant the difference only, never reduce a pool, fixture tests for `PRODUCT_CHANGE` |
| Household RLS mistake leaks member emails | Policies above, member list exposes display names only, cross-tenant tests |
| Family annual margin is thin (weakest cell in the model) | Ceiling, alert, experiment plan; the price is an `UPDATE`, not a deploy |
| Apple review of a new product | Submit with an app version, complete metadata, restore present |
