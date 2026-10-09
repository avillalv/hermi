# ruff: noqa: E501  (long SQL strings)
"""0024_trip_pass_spend: the Trip Pass spend sum for the ceiling check (03 section 7.4, WF-045).

A pass is the payer for work on its trip, summed over every member. Under row-level security an API session sees only its
own ai_usage and credit_ledger rows, so the sum runs in a definer function, like my_provider_spend_micros. It refuses a trip
the caller is not a member of (42501) and counts only the active pass window. Same sum as the `pass_month_micros` query:
settled cost plus the hard stop of every open reservation (a usage row in state reserved, or an open ledger reserve with no
usage row), taster reservations left out.

Revision ID: 0024_trip_pass_spend
Revises: 0023_legacy_claims
"""

from alembic import op

revision = "0024_trip_pass_spend"
down_revision = "0023_legacy_claims"
branch_labels = None
depends_on = None

SIG = "trip_pass_spend_micros(uuid, timestamptz, timestamptz)"

UP = rf"""
CREATE FUNCTION trip_pass_spend_micros(p_trip uuid, p_month timestamptz, p_day timestamptz)
RETURNS TABLE (month_micros bigint, day_micros bigint)
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_start timestamptz; v_end timestamptz;
BEGIN
  IF app_user_id() IS NULL OR p_trip NOT IN (SELECT visible_trip_ids()) THEN
    RAISE EXCEPTION 'not_visible' USING ERRCODE = '42501';
  END IF;
  SELECT p.starts_at, p.expires_at INTO v_start, v_end FROM trip_passes p WHERE p.trip_id = p_trip AND p.status = 'active';
  IF NOT FOUND THEN RETURN QUERY SELECT 0::bigint, 0::bigint; RETURN; END IF;
  RETURN QUERY
  SELECT coalesce(sum(s.micros), 0)::bigint, coalesce(sum(s.micros) FILTER (WHERE s.created_at >= p_day), 0)::bigint FROM (
    SELECT u.created_at,
           CASE WHEN u.state = 'reserved'
                THEN GREATEST(u.cost_usd_micros, cap.hard_stop_micros * CASE WHEN u.action = 'verify_plan' THEN u.credits_reserved ELSE 1 END)
                ELSE u.cost_usd_micros END AS micros
      FROM ai_usage u JOIN credit_action_prices cap ON cap.action = u.action
     WHERE u.trip_id = p_trip AND u.state <> 'released' AND u.created_at >= p_month AND u.created_at >= v_start AND u.created_at < v_end
       AND NOT EXISTS (SELECT 1 FROM credit_ledger l JOIN credit_grants g ON g.id = l.grant_id
                        WHERE l.reservation_id = u.reservation_id AND g.period_key = 'taster')
    UNION ALL
    SELECT o.created_at, cap.hard_stop_micros * CASE WHEN o.action = 'verify_plan' THEN o.credits ELSE 1 END
      FROM (SELECT l.reservation_id, min(l.created_at) AS created_at, (array_agg(l.action))[1] AS action,
                   sum(-l.delta) AS credits, coalesce(bool_or(g.period_key = 'taster'), false) AS taster
              FROM credit_ledger l LEFT JOIN credit_grants g ON g.id = l.grant_id
             WHERE l.trip_id = p_trip AND l.entry_type = 'reserve' AND l.created_at >= p_month AND l.created_at >= v_start AND l.created_at < v_end
               AND NOT EXISTS (SELECT 1 FROM credit_ledger s WHERE s.reservation_id = l.reservation_id AND s.entry_type = 'settle')
               AND NOT EXISTS (SELECT 1 FROM ai_usage a WHERE a.reservation_id = l.reservation_id)
             GROUP BY l.reservation_id) o
      JOIN credit_action_prices cap ON cap.action = o.action
     WHERE NOT o.taster
  ) s;
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
