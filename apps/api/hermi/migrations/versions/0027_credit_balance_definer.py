# ruff: noqa: E501  (long SQL strings)
"""0027_credit_balance_definer: the caller's spendable credits for one action and trip, pool included (WF-132.1).

Under row-level security an API session reads only its own credit_grants, so it cannot see the Trip Pass pool a trip
member may spend, and the AI sheet could not show it. This definer function does the same sum reserve_credits draws from
(own grants with no trip, plus the trip's `trip_pass` grants for an owner or editor; expired and `restricted_action`
mismatches left out) and says which pool would pay first. The taster counts only for an `agent_run` it covers whole, only
on a Free tier (as reserve since 0026, which also needs a deep_research run: the agent row is one) and only when it beats
the other grants, so it never lowers the number shown. `app_user_id()` must be set and a given trip must be visible (42501).

Revision ID: 0027_credit_balance_definer
Revises: 0026_taster_deep_only
"""

from alembic import op

revision = "0027_credit_balance_definer"
down_revision = "0026_taster_deep_only"
branch_labels = None
depends_on = None

SIG = "my_credit_balance(uuid, ai_action, integer)"

UP = rf"""
CREATE FUNCTION my_credit_balance(p_trip uuid, p_action ai_action, p_price integer)
RETURNS TABLE (own integer, pool integer, version bigint, blocked boolean, payer text)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_me uuid := app_user_id(); v_price integer; v_can boolean := false;
  v_own integer; v_pool integer; v_taster integer; v_payer text := 'own';
BEGIN
  IF v_me IS NULL OR (p_trip IS NOT NULL AND p_trip NOT IN (SELECT visible_trip_ids())) THEN
    RAISE EXCEPTION 'not_visible' USING ERRCODE = '42501';
  END IF;
  v_price := coalesce(p_price, (SELECT cap.credits FROM credit_action_prices cap WHERE cap.action = p_action));
  IF p_trip IS NOT NULL THEN
    v_can := EXISTS (SELECT 1 FROM trip_members m WHERE m.trip_id = p_trip AND m.user_id = v_me AND m.role IN ('owner', 'editor'));
  END IF;

  SELECT coalesce(sum(g.remaining) FILTER (WHERE g.period_key IS DISTINCT FROM 'taster' AND g.user_id = v_me AND g.trip_id IS NULL), 0)::integer,
         coalesce(sum(g.remaining) FILTER (WHERE v_can AND g.kind = 'trip_pass' AND g.trip_id = p_trip), 0)::integer,
         coalesce(sum(g.remaining) FILTER (WHERE g.period_key = 'taster' AND g.user_id = v_me), 0)::integer
    INTO v_own, v_pool, v_taster
    FROM credit_grants g
   WHERE g.remaining > 0 AND (g.expires_at IS NULL OR g.expires_at > now())
     AND (g.restricted_action IS NULL OR g.restricted_action = p_action)
     AND (g.user_id = v_me OR (g.kind = 'trip_pass' AND g.trip_id = p_trip));

  IF p_action = 'agent_run' AND v_taster >= v_price AND v_price > v_own + v_pool
     AND NOT EXISTS (SELECT 1 FROM entitlements e WHERE e.user_id = v_me AND e.tier_code <> 'free' AND (e.valid_until IS NULL OR e.valid_until > now())) THEN
    v_own := v_price; v_pool := 0;  -- the taster alone pays, and never mixes with another grant
  ELSIF v_pool > 0 THEN
    SELECT CASE WHEN g.kind = 'trip_pass' THEN 'trip_pass' ELSE 'own' END INTO v_payer
      FROM credit_grants g
     WHERE g.remaining > 0 AND (g.expires_at IS NULL OR g.expires_at > now()) AND g.period_key IS DISTINCT FROM 'taster'
       AND (g.restricted_action IS NULL OR g.restricted_action = p_action)
       AND ((g.user_id = v_me AND g.trip_id IS NULL) OR (v_can AND g.kind = 'trip_pass' AND g.trip_id = p_trip))
     ORDER BY CASE g.kind WHEN 'monthly' THEN 10 WHEN 'promo' THEN 20 WHEN 'trip_pass' THEN 30 WHEN 'adjustment' THEN 35 ELSE 40 END,
              g.expires_at NULLS LAST, g.id
     LIMIT 1;
  END IF;

  RETURN QUERY
  SELECT v_own, v_pool,
         (SELECT coalesce(max(l.id), 0) FROM credit_ledger l
           WHERE l.user_id = v_me
              OR (v_can AND l.grant_id IN (SELECT g.id FROM credit_grants g WHERE g.kind = 'trip_pass' AND g.trip_id = p_trip)))::bigint,
         EXISTS (SELECT 1 FROM credit_debts d WHERE d.user_id = v_me AND d.amount > 0),
         v_payer;
END $$;
ALTER FUNCTION {SIG} OWNER TO hermi_definer;
REVOKE EXECUTE ON FUNCTION {SIG} FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION {SIG} TO hermi_app;
"""

DOWN = f"DROP FUNCTION {SIG};"


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
