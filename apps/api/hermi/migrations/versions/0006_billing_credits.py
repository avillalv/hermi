"""0006_billing_credits: store transactions, subscriptions, entitlements, passes, webhooks and the credit system (03 sections 5.7 and 5.8).

The SQL is the DDL of 03 sections 5.7 and 5.8, verbatim. Grants, RLS and the definer ownership of the credit functions land in 0014_rls.
credit_ledger_immutable() runs as the caller here; 0014 re-owns the retention_sweep() path to hermi_definer (03 section 5.8).

Revision ID: 0006_billing_credits
Revises: 0005_ai
"""

from alembic import op

revision = "0006_billing_credits"
# 03 section 10 lists 0003 and 0004 as parents; the chain is linear, so the parent is 0005 (one head).
down_revision = "0005_ai"
branch_labels = None
depends_on = None

UP = r"""
CREATE TYPE subscription_status AS ENUM ('active', 'in_trial', 'in_grace', 'billing_retry', 'paused', 'expired', 'refunded', 'revoked');
CREATE TYPE pass_status         AS ENUM ('active', 'expired', 'refunded');
CREATE TYPE store_environment   AS ENUM ('sandbox', 'production');

CREATE TABLE store_transactions (                            -- every money event from a store; kept for tax retention
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id                   uuid REFERENCES users (id) ON DELETE SET NULL,
  store                     text NOT NULL,
  store_transaction_id      text NOT NULL,
  original_transaction_id   text,
  product_id                text REFERENCES store_products (product_id) ON DELETE RESTRICT,
  plan_code                 text REFERENCES plans (code) ON DELETE RESTRICT,
  kind                      text NOT NULL,
  status                    text NOT NULL DEFAULT 'purchased',
  trip_id                   uuid,                                                  -- pass purchases; no FK so a deleted trip keeps the record
  amount_minor              bigint,
  currency                  currency_code,
  net_minor                 bigint,                                                -- after store fee, when known
  purchased_at              timestamptz NOT NULL,
  expires_at                timestamptz,
  refunded_at               timestamptz,
  environment               store_environment NOT NULL DEFAULT 'production',
  raw                       jsonb,                                                 -- kept 12 months, then nulled
  created_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_store_transactions_store CHECK (store = 'apple'),
  CONSTRAINT ck_store_transactions_kind CHECK (kind IN ('subscription', 'pass', 'credit_pack')),
  CONSTRAINT ck_store_transactions_status CHECK (status IN ('purchased', 'renewed', 'refunded', 'revoked', 'failed')),
  CONSTRAINT uq_store_transactions_txn UNIQUE (store, store_transaction_id)
);
CREATE INDEX ix_store_transactions_user ON store_transactions (user_id, purchased_at DESC);
CREATE INDEX ix_store_transactions_original ON store_transactions (store, original_transaction_id);

CREATE TABLE subscriptions (
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id                   uuid REFERENCES users (id) ON DELETE SET NULL,
  store                     text NOT NULL,
  original_transaction_id   text NOT NULL,
  product_id                text REFERENCES store_products (product_id) ON DELETE RESTRICT,
  plan_code                 text NOT NULL REFERENCES plans (code) ON DELETE RESTRICT,
  status                    subscription_status NOT NULL,
  period_start              timestamptz,
  period_end                timestamptz,
  auto_renew                boolean NOT NULL DEFAULT true,
  is_trial                  boolean NOT NULL DEFAULT false,
  environment               store_environment NOT NULL DEFAULT 'production',
  revenuecat_app_user_id    text,
  last_event_at             timestamptz,
  raw_last_event            jsonb,
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_subscriptions_store CHECK (store = 'apple'),
  CONSTRAINT uq_subscriptions_original UNIQUE (store, original_transaction_id)
);
CREATE INDEX ix_subscriptions_user ON subscriptions (user_id) WHERE status IN ('active', 'in_trial', 'in_grace', 'billing_retry');
CREATE INDEX ix_subscriptions_period_end ON subscriptions (period_end) WHERE status IN ('active', 'in_trial', 'in_grace', 'billing_retry');
SELECT add_updated_at_trigger('subscriptions');

CREATE TABLE entitlements (                                   -- materialized per user; rebuilt by the billing service on every event
  user_id                  uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
  tier_code                text NOT NULL DEFAULT 'free' REFERENCES plans (code) ON DELETE RESTRICT,
  source                   text NOT NULL DEFAULT 'none',                           -- none (Free), subscription (Plus from the store), comp (granted in the admin console)
  subscription_id          uuid REFERENCES subscriptions (id) ON DELETE SET NULL,
  in_grace                 boolean NOT NULL DEFAULT false,
  valid_until              timestamptz,                                            -- null for free
  limits                   jsonb NOT NULL DEFAULT '{}'::jsonb,                     -- snapshot of plans.limits at compute time
  computed_at              timestamptz NOT NULL DEFAULT now(),
  updated_at               timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_entitlements_source CHECK (source IN ('none', 'subscription', 'comp'))
);
CREATE INDEX ix_entitlements_valid_until ON entitlements (valid_until) WHERE valid_until IS NOT NULL;   -- nightly reconcile
SELECT add_updated_at_trigger('entitlements');

-- The billing service fills the *_max columns and credits_granted from plans.limits of the purchased plan (the defaults below are the Trip Pass values).
-- A pass is also created without a purchase: the first-import reward (source = 'import_reward', grant_import_reward() in 5.9) and admin comps (source = 'admin').
CREATE TABLE trip_passes (                                    -- non-renewing, bound to one trip on the server
  id                        uuid PRIMARY KEY DEFAULT uuidv7(),
  trip_id                   uuid NOT NULL REFERENCES trips (id) ON DELETE CASCADE,
  purchaser_user_id         uuid REFERENCES users (id) ON DELETE SET NULL,
  plan_code                 text NOT NULL REFERENCES plans (code) ON DELETE RESTRICT,   -- trip_pass in Phase 1
  source                    text NOT NULL DEFAULT 'purchase',                            -- purchase (RevenueCat), import_reward (first import, once per user), admin
  store_transaction_id      uuid REFERENCES store_transactions (id) ON DELETE SET NULL,
  original_transaction_id   text,
  starts_at                 timestamptz NOT NULL DEFAULT now(),
  expires_at                timestamptz NOT NULL,                                        -- starts_at plus 90 days
  live_routes_max           smallint NOT NULL DEFAULT 2,
  live_checks_max           smallint NOT NULL DEFAULT 60,
  live_checks_used          smallint NOT NULL DEFAULT 0,
  collaborators_max         smallint NOT NULL DEFAULT 6,
  travelers_max             smallint NOT NULL DEFAULT 8,
  credits_granted           integer NOT NULL DEFAULT 40,
  status                    pass_status NOT NULL DEFAULT 'active',
  move_count                smallint NOT NULL DEFAULT 0,                                 -- a pass can move to another trip at most once
  created_at                timestamptz NOT NULL DEFAULT now(),
  updated_at                timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_trip_passes_window CHECK (expires_at > starts_at),
  CONSTRAINT ck_trip_passes_checks CHECK (live_checks_used BETWEEN 0 AND live_checks_max),
  CONSTRAINT ck_trip_passes_moves CHECK (move_count BETWEEN 0 AND 1),
  CONSTRAINT ck_trip_passes_plan CHECK (plan_code = 'trip_pass'),
  CONSTRAINT ck_trip_passes_source CHECK (source IN ('purchase', 'import_reward', 'admin')),
  CONSTRAINT uq_trip_passes_original UNIQUE (original_transaction_id)
);
CREATE UNIQUE INDEX uq_trip_passes_one_active ON trip_passes (trip_id) WHERE status = 'active';
CREATE INDEX ix_trip_passes_purchaser ON trip_passes (purchaser_user_id);
CREATE INDEX ix_trip_passes_expiry ON trip_passes (expires_at) WHERE status = 'active';
SELECT add_updated_at_trigger('trip_passes');

CREATE TABLE webhook_events (                                 -- idempotency: insert first, skip on conflict
  provider       text NOT NULL,
  event_id       text NOT NULL,
  event_type     text NOT NULL,
  status         text NOT NULL DEFAULT 'received',
  attempts       smallint NOT NULL DEFAULT 0,
  error          text,
  payload        jsonb NOT NULL,
  received_at    timestamptz NOT NULL DEFAULT now(),
  processed_at   timestamptz,
  PRIMARY KEY (provider, event_id),
  CONSTRAINT ck_webhook_events_provider CHECK (provider IN ('revenuecat', 'travelpayouts', 'viator', 'stay22', 'resend', 'supabase')),
  CONSTRAINT ck_webhook_events_status CHECK (status IN ('received', 'processed', 'failed', 'ignored'))
);
CREATE INDEX ix_webhook_events_pending ON webhook_events (received_at) WHERE status IN ('received', 'failed');
CREATE INDEX ix_webhook_events_received ON webhook_events (received_at);

CREATE TYPE credit_grant_kind AS ENUM ('monthly', 'promo', 'trip_pass', 'purchase', 'adjustment');
CREATE TYPE credit_entry_type AS ENUM ('grant', 'reserve', 'settle', 'refund', 'expire', 'clawback', 'adjust');

CREATE TABLE credit_grants (
  id                    uuid PRIMARY KEY DEFAULT uuidv7(),
  user_id               uuid REFERENCES users (id) ON DELETE SET NULL,
  kind                  credit_grant_kind NOT NULL,
  credits               integer NOT NULL CHECK (credits > 0),                  -- amount granted
  remaining             integer NOT NULL CHECK (remaining >= 0),               -- spendable now (reserved credits are already subtracted)
  trip_id               uuid REFERENCES trips (id) ON DELETE CASCADE,          -- trip_pass grants spend only on this trip
  restricted_action     ai_action,                                             -- e.g. the free taster is agent_run only
  period_key            text,                                                  -- '2026-10' for monthly grants; makes the monthly job idempotent
  expires_at            timestamptz,
  store_transaction_id  uuid REFERENCES store_transactions (id) ON DELETE SET NULL,
  created_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_credit_grants_remaining CHECK (remaining <= credits),
  CONSTRAINT ck_credit_grants_trip_pass CHECK (kind <> 'trip_pass' OR trip_id IS NOT NULL)
);
CREATE UNIQUE INDEX uq_credit_grants_user_period ON credit_grants (user_id, kind, period_key) WHERE user_id IS NOT NULL AND period_key IS NOT NULL;
CREATE UNIQUE INDEX uq_credit_grants_txn ON credit_grants (store_transaction_id) WHERE store_transaction_id IS NOT NULL;
CREATE INDEX ix_credit_grants_user_spend ON credit_grants (user_id, expires_at) WHERE remaining > 0;
CREATE INDEX ix_credit_grants_expiry ON credit_grants (expires_at) WHERE remaining > 0 AND expires_at IS NOT NULL;

CREATE TABLE credit_ledger (
  id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id           uuid REFERENCES users (id) ON DELETE SET NULL,            -- the acting account
  grant_id          uuid REFERENCES credit_grants (id) ON DELETE SET NULL,
  entry_type        credit_entry_type NOT NULL,
  delta             integer NOT NULL,                                          -- grant +, reserve -, refund +, expire -, clawback -, settle 0
  charged           integer,                                                   -- settle entries: final credits charged
  reservation_id    uuid,                                                      -- groups one action's reserve, refund and settle entries
  action            ai_action,
  run_id            uuid,
  trip_id           uuid,
  usage_id          bigint REFERENCES ai_usage (id) ON DELETE SET NULL,
  idempotency_key   text,
  note              text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_credit_ledger_sign CHECK (
    (entry_type IN ('grant', 'refund') AND delta > 0) OR
    (entry_type IN ('reserve', 'expire', 'clawback') AND delta < 0) OR
    (entry_type = 'settle' AND delta = 0 AND charged IS NOT NULL) OR
    (entry_type = 'adjust')),
  CONSTRAINT ck_credit_ledger_reservation CHECK (entry_type NOT IN ('reserve', 'settle') OR reservation_id IS NOT NULL)
);
-- One reserve row per grant per idempotency key: a replayed request cannot reserve twice.
CREATE UNIQUE INDEX uq_credit_ledger_idem ON credit_ledger (idempotency_key, entry_type, grant_id) WHERE idempotency_key IS NOT NULL;
-- Rows with no grant (a refund shortfall, see credit_debts) are not covered by the index above, because NULLs never collide.
CREATE UNIQUE INDEX uq_credit_ledger_idem_nogrant ON credit_ledger (idempotency_key, entry_type) WHERE idempotency_key IS NOT NULL AND grant_id IS NULL;
CREATE INDEX ix_credit_ledger_user ON credit_ledger (user_id, created_at DESC);
CREATE INDEX ix_credit_ledger_reservation ON credit_ledger (reservation_id) WHERE reservation_id IS NOT NULL;
CREATE INDEX ix_credit_ledger_open ON credit_ledger (created_at) WHERE entry_type = 'reserve';

-- Append-only. UPDATE and DELETE are rejected, except the anonymizing update that account deletion uses (user_id set to NULL), the same
-- nulling of grant_id and usage_id that the ON DELETE SET NULL foreign keys perform when a trip or usage row is purged, and the delete of a row
-- older than 7 years by retention_sweep() (8), which is the only caller that runs as hermi_definer (the same pattern as audit_log_immutable, 5.16).
-- Nothing else may change.
CREATE FUNCTION credit_ledger_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' AND current_user = 'hermi_definer' AND OLD.created_at < now() - interval '7 years' THEN
    RETURN OLD;
  END IF;
  IF TG_OP = 'UPDATE'
     AND (to_jsonb(NEW) - 'user_id' - 'grant_id' - 'usage_id') = (to_jsonb(OLD) - 'user_id' - 'grant_id' - 'usage_id')
     AND (NEW.user_id  IS NULL OR NEW.user_id  = OLD.user_id)
     AND (NEW.grant_id IS NULL OR NEW.grant_id = OLD.grant_id)
     AND (NEW.usage_id IS NULL OR NEW.usage_id = OLD.usage_id)
  THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'credit_ledger is append-only' USING ERRCODE = '42501';
END $$;
CREATE TRIGGER trg_credit_ledger_immutable BEFORE UPDATE OR DELETE ON credit_ledger
  FOR EACH ROW EXECUTE FUNCTION credit_ledger_immutable();

-- API callers may act only for themselves. session_user is the login role, so it stays the caller inside a SECURITY DEFINER function;
-- the worker and admin logins are not members of hermi_app and pass.
CREATE FUNCTION assert_credit_caller(p_user uuid) RETURNS void LANGUAGE plpgsql STABLE AS $$
BEGIN
  IF pg_has_role(session_user, 'hermi_app', 'member') AND p_user IS DISTINCT FROM app_user_id() THEN
    RAISE EXCEPTION 'insufficient_privilege' USING ERRCODE = '42501';
  END IF;
END $$;

-- Credits already spent when a pack refund arrived (07 5.6). credit_grants.remaining never goes below 0, so the shortfall lives here:
-- reserve_credits refuses while amount > 0, and settle_credit_debt() pays it down from the next grants. Written by the billing service and the functions below only.
CREATE TABLE credit_debts (
  user_id     uuid PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
  amount      integer NOT NULL CHECK (amount >= 0),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Spendable balance per user and, for pass credits, per trip. RLS applies to the caller.
CREATE VIEW credit_balances WITH (security_invoker = true) AS
SELECT user_id,
       trip_id,
       sum(remaining)::integer AS remaining,
       (sum(remaining) FILTER (WHERE kind = 'monthly'))::integer AS allowance_remaining,
       (sum(remaining) FILTER (WHERE kind = 'purchase'))::integer AS purchased_remaining,
       min(expires_at) FILTER (WHERE remaining > 0) AS next_expiry
  FROM credit_grants
 WHERE remaining > 0 AND (expires_at IS NULL OR expires_at > now())
 GROUP BY user_id, trip_id;

-- Reserve the full price of an action atomically. Raises WF402 (insufficient credits) and changes nothing.
-- Safe to replay with the same p_idem: returns the original reservation id.
CREATE FUNCTION reserve_credits(
  p_user uuid, p_trip uuid, p_amount integer, p_action ai_action, p_run uuid, p_idem text
) RETURNS uuid LANGUAGE plpgsql AS $$
DECLARE
  v_res uuid; v_need integer := p_amount; v_take integer; g record; v_pool boolean; v_taster uuid;
BEGIN
  PERFORM assert_credit_caller(p_user);
  IF p_amount <= 0 THEN RAISE EXCEPTION 'amount must be positive'; END IF;
  SELECT reservation_id INTO v_res FROM credit_ledger
   WHERE idempotency_key = p_idem AND entry_type = 'reserve' LIMIT 1;
  IF FOUND THEN RETURN v_res; END IF;
  IF EXISTS (SELECT 1 FROM credit_debts WHERE user_id = p_user AND amount > 0) THEN
    RAISE EXCEPTION 'credit_debt' USING ERRCODE = 'WF402';           -- same SQLSTATE as a short balance; the message tells the API to show the refund notice (CreditBalance.blocked)
  END IF;

  v_res := uuidv7();

  -- Trip Pass credits are a trip pool: usable by any member who may start AI on the trip (owner or editor).
  v_pool := EXISTS (SELECT 1 FROM trip_members WHERE trip_id = p_trip AND user_id = p_user AND role IN ('owner', 'editor'));

  -- The taster pays for one agent run on its own and is tried first: it never mixes with, or debits, another grant.
  IF p_action = 'agent_run' THEN
    SELECT id INTO v_taster FROM credit_grants
     WHERE user_id = p_user AND period_key = 'taster' AND remaining >= p_amount FOR UPDATE;
    IF FOUND THEN
      UPDATE credit_grants SET remaining = remaining - p_amount WHERE id = v_taster;
      INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, reservation_id, action, run_id, trip_id, idempotency_key)
      VALUES (p_user, v_taster, 'reserve', -p_amount, v_res, p_action, p_run, p_trip, p_idem);
      RETURN v_res;
    END IF;
  END IF;

  FOR g IN
    SELECT id, remaining FROM credit_grants
     WHERE remaining > 0
       AND (expires_at IS NULL OR expires_at > now())
       AND period_key IS DISTINCT FROM 'taster'
       AND ((user_id = p_user AND trip_id IS NULL) OR (kind = 'trip_pass' AND trip_id = p_trip AND v_pool))
       AND (restricted_action IS NULL OR restricted_action = p_action)
     ORDER BY CASE kind WHEN 'monthly' THEN 10 WHEN 'promo' THEN 20
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

-- Settle a reservation: charge p_charged credits and return the rest to the grants it came from
-- (purchased credits first, so allowance credits are not refunded ahead of them). p_charged = 0 releases it.
CREATE FUNCTION settle_credits(p_reservation uuid, p_charged integer, p_usage_id bigint DEFAULT NULL)
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE
  v_user uuid; v_action ai_action; v_run uuid; v_trip uuid;
  v_reserved integer; v_charge integer; v_refund integer; v_back integer; r record;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtextextended(p_reservation::text, 0));
  SELECT user_id INTO v_user FROM credit_ledger WHERE reservation_id = p_reservation AND entry_type = 'reserve' LIMIT 1;
  PERFORM assert_credit_caller(v_user);                              -- an API caller can settle only their own reservation
  IF EXISTS (SELECT 1 FROM credit_ledger WHERE reservation_id = p_reservation AND entry_type = 'settle') THEN
    RETURN 0;                                                        -- already settled
  END IF;
  SELECT (array_agg(user_id))[1], (array_agg(action))[1], (array_agg(run_id))[1], (array_agg(trip_id))[1], sum(-delta)::integer
    INTO v_user, v_action, v_run, v_trip, v_reserved
    FROM credit_ledger WHERE reservation_id = p_reservation AND entry_type = 'reserve';
  IF v_reserved IS NULL THEN RAISE EXCEPTION 'unknown_reservation'; END IF;

  v_charge := LEAST(GREATEST(p_charged, 0), v_reserved);
  v_refund := v_reserved - v_charge;
  FOR r IN SELECT grant_id, -delta AS taken FROM credit_ledger
            WHERE reservation_id = p_reservation AND entry_type = 'reserve' ORDER BY id DESC
  LOOP
    EXIT WHEN v_refund = 0;
    v_back := LEAST(r.taken, v_refund);
    IF r.grant_id IS NOT NULL THEN
      UPDATE credit_grants SET remaining = remaining + v_back WHERE id = r.grant_id;
    END IF;
    INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, reservation_id, action, run_id, trip_id, usage_id)
    VALUES (v_user, r.grant_id, 'refund', v_back, p_reservation, v_action, v_run, v_trip, p_usage_id);
    v_refund := v_refund - v_back;
  END LOOP;

  INSERT INTO credit_ledger (user_id, entry_type, delta, charged, reservation_id, action, run_id, trip_id, usage_id)
  VALUES (v_user, 'settle', 0, v_charge, p_reservation, v_action, v_run, v_trip, p_usage_id);

  IF p_usage_id IS NOT NULL THEN
    UPDATE ai_usage
       SET state = CASE WHEN v_charge = 0 THEN 'released'::usage_state ELSE 'settled'::usage_state END,
           credits_charged = v_charge, settled_at = now()
     WHERE id = p_usage_id;
  END IF;
  RETURN v_reserved - v_charge;
END $$;

-- Sweeper (run every minute): release reservations older than the run deadline plus a grace period (agent runs stop at 20 turns and $0.80,
-- so the deadline is 30 minutes). Idempotent: a settled reservation is skipped, settle_credits() returns 0 for one settled in the meantime, and a
-- second call finds nothing to do. Returns the number released.
CREATE FUNCTION release_stale_reservations(p_deadline interval DEFAULT interval '30 minutes', p_grace interval DEFAULT interval '5 minutes')
RETURNS integer LANGUAGE plpgsql AS $$
DECLARE r record; n integer := 0;
BEGIN
  FOR r IN SELECT DISTINCT l.reservation_id FROM credit_ledger l
            WHERE l.entry_type = 'reserve' AND l.created_at < now() - (p_deadline + p_grace)
              AND NOT EXISTS (SELECT 1 FROM credit_ledger s WHERE s.reservation_id = l.reservation_id AND s.entry_type = 'settle')
  LOOP
    PERFORM settle_credits(r.reservation_id, 0);
    n := n + 1;
  END LOOP;
  RETURN n;
END $$;

-- Expire grants past expires_at (run hourly). Reserved credits are already out of remaining, so they are untouched.
CREATE FUNCTION expire_credit_grants() RETURNS integer LANGUAGE sql AS $$
  WITH due AS (
    SELECT id, user_id, remaining FROM credit_grants
     WHERE remaining > 0 AND expires_at IS NOT NULL AND expires_at <= now() FOR UPDATE),
  z AS (UPDATE credit_grants g SET remaining = 0 FROM due WHERE g.id = due.id RETURNING g.id),
  l AS (INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, note)
        SELECT due.user_id, due.id, 'expire', -due.remaining, 'expired' FROM due JOIN z ON z.id = due.id RETURNING 1)
  SELECT count(*)::integer FROM l
$$;

-- A pack refund found fewer unspent credits than the pack held: claw back what remains (done by the billing service on the grant),
-- then record the rest as debt. p_idem is 'refund:{store_transaction_id}', so a replayed webhook records it once.
CREATE FUNCTION record_credit_debt(p_user uuid, p_credits integer, p_idem text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_id bigint;
BEGIN
  IF p_credits <= 0 THEN RETURN; END IF;
  INSERT INTO credit_ledger (user_id, entry_type, delta, idempotency_key, note)
  VALUES (p_user, 'clawback', -p_credits, p_idem, 'refund shortfall')
  ON CONFLICT (idempotency_key, entry_type) WHERE idempotency_key IS NOT NULL AND grant_id IS NULL DO NOTHING
  RETURNING id INTO v_id;
  IF v_id IS NULL THEN RETURN; END IF;                                  -- replay
  INSERT INTO credit_debts (user_id, amount) VALUES (p_user, p_credits)
  ON CONFLICT (user_id) DO UPDATE SET amount = credit_debts.amount + EXCLUDED.amount, updated_at = now();
END $$;

-- Pay the debt down from the user's own spendable grants, oldest expiry first. The billing service calls it after every grant or pack purchase.
-- Returns the credits repaid.
CREATE FUNCTION settle_credit_debt(p_user uuid) RETURNS integer LANGUAGE plpgsql AS $$
DECLARE v_debt integer; v_take integer; v_paid integer := 0; g record;
BEGIN
  SELECT amount INTO v_debt FROM credit_debts WHERE user_id = p_user FOR UPDATE;
  IF NOT FOUND OR v_debt = 0 THEN RETURN 0; END IF;
  FOR g IN SELECT id, remaining FROM credit_grants
            WHERE user_id = p_user AND remaining > 0 AND (expires_at IS NULL OR expires_at > now())
            ORDER BY expires_at NULLS LAST, id FOR UPDATE
  LOOP
    EXIT WHEN v_debt = 0;
    v_take := LEAST(g.remaining, v_debt);
    UPDATE credit_grants SET remaining = remaining - v_take WHERE id = g.id;
    INSERT INTO credit_ledger (user_id, grant_id, entry_type, delta, note)
    VALUES (p_user, g.id, 'clawback', -v_take, 'debt repayment');
    v_debt := v_debt - v_take;
    v_paid := v_paid + v_take;
  END LOOP;
  UPDATE credit_debts SET amount = v_debt, updated_at = now() WHERE user_id = p_user;
  RETURN v_paid;
END $$;

-- Free allowance, written lazily on the first credit use in a calendar month so idle accounts cost no writes (06 6.3, 07 5.1).
-- The API calls it before every admission; accounts on a paid entitlement get theirs from the billing service instead.
CREATE FUNCTION ensure_free_monthly_grant(p_user uuid) RETURNS void LANGUAGE sql AS $$
  SELECT assert_credit_caller(p_user);
  INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key, expires_at)
  SELECT p_user, 'monthly', p.monthly_credits, p.monthly_credits,
         to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'),
         (date_trunc('month', now() AT TIME ZONE 'UTC') + interval '1 month') AT TIME ZONE 'UTC'
    FROM plans p
   WHERE p.code = 'free' AND p.monthly_credits > 0
     AND NOT EXISTS (SELECT 1 FROM entitlements e
                      WHERE e.user_id = p_user AND e.tier_code <> 'free' AND (e.valid_until IS NULL OR e.valid_until > now()))
  ON CONFLICT (user_id, kind, period_key) WHERE user_id IS NOT NULL AND period_key IS NOT NULL DO NOTHING
$$;

-- Abuse memory: what a person has already earned, kept after the account is gone. Each hash is sha256 of 'apple:<sub>' or 'google:<sub>'
-- (the upstream subject in auth_identities.provider_subject, which does not change when the account is re-created) or of 'email:<lower(email)>' for
-- a verified address (a relay address counts: it is stable per app). For kind 'import_uids' the hash is the import's uid_set_hash.
-- Kept 12 months, then purged by retention_sweep() (8). No grant to hermi_app (6.1); written by the definer functions below and the worker.
CREATE TABLE identity_hashes (
  hash        bytea NOT NULL,
  kind        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (kind, hash),
  CONSTRAINT ck_identity_hashes_kind CHECK (kind IN ('taster', 'import_reward', 'import_uids'))
);
CREATE INDEX ix_identity_hashes_created ON identity_hashes (created_at);                    -- the 12 month purge

-- Every identity hash of one user: one per upstream Apple or Google subject, plus one for the verified email.
CREATE FUNCTION identity_hashes_for(p_user uuid) RETURNS SETOF bytea LANGUAGE sql STABLE AS $$
  SELECT sha256(convert_to(provider || ':' || provider_subject, 'UTF8')) FROM auth_identities
   WHERE user_id = p_user AND provider_subject IS NOT NULL
  UNION
  SELECT sha256(convert_to('email:' || lower(email::text), 'UTF8')) FROM users
   WHERE id = p_user AND email_verified_at IS NOT NULL
$$;

-- The free taster (06 5.9): one promo grant per account for life, restricted to agent runs, no expiry, worth one agent run.
-- Written at the first offer (or at sign-up); the unique index on (user_id, kind, period_key) makes a second call do nothing,
-- and a spent grant stays in the table so it is never granted again.
-- A deleted and re-created account does not earn it again: the user's identity hashes (upstream subjects and verified email) are looked up in
-- identity_hashes (kind 'taster') before the grant and written after it.
CREATE FUNCTION ensure_taster_grant(p_user uuid) RETURNS void LANGUAGE plpgsql AS $$
DECLARE v_id uuid;
BEGIN
  PERFORM assert_credit_caller(p_user);
  IF EXISTS (SELECT 1 FROM identity_hashes WHERE kind = 'taster' AND hash IN (SELECT identity_hashes_for(p_user))) THEN
    RETURN;
  END IF;
  INSERT INTO credit_grants (user_id, kind, credits, remaining, restricted_action, period_key)
  SELECT p_user, 'promo', cap.credits, cap.credits, 'agent_run', 'taster'
    FROM credit_action_prices cap, plans p
   WHERE cap.action = 'agent_run' AND p.code = 'free' AND COALESCE((p.limits ->> 'taster_agent_runs')::integer, 0) > 0
  ON CONFLICT (user_id, kind, period_key) WHERE user_id IS NOT NULL AND period_key IS NOT NULL DO NOTHING
  RETURNING id INTO v_id;
  IF v_id IS NOT NULL THEN
    INSERT INTO identity_hashes (hash, kind) SELECT identity_hashes_for(p_user), 'taster'
    ON CONFLICT DO NOTHING;
  END IF;
END $$;
"""

DOWN = r"""
DROP FUNCTION ensure_taster_grant(uuid);
DROP FUNCTION ensure_free_monthly_grant(uuid);
DROP FUNCTION settle_credit_debt(uuid);
DROP FUNCTION record_credit_debt(uuid, integer, text);
DROP FUNCTION expire_credit_grants();
DROP FUNCTION release_stale_reservations(interval, interval);
DROP FUNCTION settle_credits(uuid, integer, bigint);
DROP FUNCTION reserve_credits(uuid, uuid, integer, ai_action, uuid, text);
DROP VIEW credit_balances;
DROP FUNCTION identity_hashes_for(uuid);
DROP TABLE identity_hashes;
DROP TABLE credit_debts;
DROP FUNCTION assert_credit_caller(uuid);
DROP TABLE credit_ledger;
DROP FUNCTION credit_ledger_immutable();
DROP TABLE credit_grants;
DROP TABLE webhook_events;
DROP TABLE trip_passes;
DROP TABLE entitlements;
DROP TABLE subscriptions;
DROP TABLE store_transactions;
DROP TYPE credit_entry_type;
DROP TYPE credit_grant_kind;
DROP TYPE store_environment;
DROP TYPE pass_status;
DROP TYPE subscription_status;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
