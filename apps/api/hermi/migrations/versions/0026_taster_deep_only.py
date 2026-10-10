# ruff: noqa: E501  (long SQL strings)
"""0026_taster_deep_only: the taster is drawn only by a deep_research run of a Free account (06 section 5.9, WF-053.1).

`reserve_credits` took the taster first for any `agent_run`, so a fare hunt, or a Plus member who still held the grant from
their Free days, could spend it. The function now draws it only when `p_run` is a `deep_research` run and the caller has no
paid entitlement. The attributes (SECURITY DEFINER, fixed search_path) are restated because CREATE OR REPLACE resets them;
the owner and the grants stay. Nothing else changes.

Revision ID: 0026_taster_deep_only
Revises: 0025_notification_prefs
"""

from alembic import op

revision = "0026_taster_deep_only"
down_revision = "0025_notification_prefs"
branch_labels = None
depends_on = None

UP = r"""
CREATE OR REPLACE FUNCTION reserve_credits(
  p_user uuid, p_trip uuid, p_amount integer, p_action ai_action, p_run uuid, p_idem text
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_res uuid; v_need integer := p_amount; v_take integer; g record; v_pool boolean; v_taster uuid;
BEGIN
  PERFORM assert_credit_caller(p_user);
  IF p_amount <= 0 THEN RAISE EXCEPTION 'amount must be positive'; END IF;
  SELECT reservation_id INTO v_res FROM credit_ledger
   WHERE idempotency_key = p_idem AND entry_type = 'reserve' LIMIT 1;
  IF FOUND THEN RETURN v_res; END IF;
  IF EXISTS (SELECT 1 FROM credit_debts WHERE user_id = p_user AND amount > 0) THEN
    RAISE EXCEPTION 'credit_debt' USING ERRCODE = 'WF402';
  END IF;

  v_res := uuidv7();
  v_pool := EXISTS (SELECT 1 FROM trip_members WHERE trip_id = p_trip AND user_id = p_user AND role IN ('owner', 'editor'));

  -- The taster pays for one agent run on its own and is tried first: it never mixes with, or debits, another grant.
  -- It is the lifetime deep run of a Free account (06 section 5.9): only a deep_research run, only while the tier is free.
  IF p_action = 'agent_run'
     AND EXISTS (SELECT 1 FROM runs WHERE id = p_run AND kind = 'deep_research')
     AND NOT EXISTS (SELECT 1 FROM entitlements e WHERE e.user_id = p_user AND e.tier_code <> 'free' AND (e.valid_until IS NULL OR e.valid_until > now())) THEN
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
    RAISE EXCEPTION 'insufficient_credits' USING ERRCODE = 'WF402';
  END IF;
  RETURN v_res;
END $$;
"""

DOWN = r"""
CREATE OR REPLACE FUNCTION reserve_credits(
  p_user uuid, p_trip uuid, p_amount integer, p_action ai_action, p_run uuid, p_idem text
) RETURNS uuid LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_res uuid; v_need integer := p_amount; v_take integer; g record; v_pool boolean; v_taster uuid;
BEGIN
  PERFORM assert_credit_caller(p_user);
  IF p_amount <= 0 THEN RAISE EXCEPTION 'amount must be positive'; END IF;
  SELECT reservation_id INTO v_res FROM credit_ledger
   WHERE idempotency_key = p_idem AND entry_type = 'reserve' LIMIT 1;
  IF FOUND THEN RETURN v_res; END IF;
  IF EXISTS (SELECT 1 FROM credit_debts WHERE user_id = p_user AND amount > 0) THEN
    RAISE EXCEPTION 'credit_debt' USING ERRCODE = 'WF402';
  END IF;

  v_res := uuidv7();
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
    RAISE EXCEPTION 'insufficient_credits' USING ERRCODE = 'WF402';
  END IF;
  RETURN v_res;
END $$;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
