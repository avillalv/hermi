"""0017_trip_effective_limits: trip_effective_limits(trip), the 03 section 7.1 merge as a definer function (WF-023.1). Expand only.

A trip member must see the owner's tier on that trip, but row-level security hides the owner's `entitlements` row from
everyone else. This function runs the 7.1 query as the definer and answers only for a trip the caller is a member of
(visible_trip_ids). It returns no rows for any other trip. Same contract as the other helpers: definer owner, pinned
search_path, no PUBLIC, execute for hermi_app only.

Revision ID: 0017_trip_effective_limits
Revises: 0016_bootstrap_subject
"""

from alembic import op

revision = "0017_trip_effective_limits"
down_revision = "0016_bootstrap_subject"
branch_labels = None
depends_on = None

FN = "trip_effective_limits(uuid)"

UP = f"""
CREATE FUNCTION trip_effective_limits(p_trip uuid) RETURNS TABLE (sources text[], limits jsonb)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
WITH owner_tier AS (
  SELECT t.id AS trip_id, pl.code, pl.limits
    FROM trips t
    LEFT JOIN entitlements e ON e.user_id = t.owner_user_id AND (e.valid_until IS NULL OR e.valid_until > now())
    JOIN plans pl ON pl.code = COALESCE(e.tier_code, 'free')
   WHERE t.id = p_trip AND t.deleted_at IS NULL AND p_trip IN (SELECT visible_trip_ids())
), pass AS (
  SELECT tp.trip_id, pl.code,
         pl.limits || jsonb_build_object(
           'live_routes', tp.live_routes_max,
           'live_checks_max', tp.live_checks_max,
           'collaborators', tp.collaborators_max,
           'travelers_per_trip', tp.travelers_max) AS limits
    FROM trip_passes tp JOIN plans pl ON pl.code = tp.plan_code
   WHERE tp.trip_id = p_trip AND tp.status = 'active' AND now() >= tp.starts_at AND now() < tp.expires_at
     AND p_trip IN (SELECT visible_trip_ids())
), candidates AS (
  SELECT 'tier' AS source, code, limits FROM owner_tier
  UNION ALL
  SELECT 'pass', code, limits FROM pass
)
SELECT (SELECT array_agg(source || ':' || code ORDER BY source) FROM candidates), jsonb_object_agg(m.key, m.merged)
FROM (
  SELECT l.key,
         CASE WHEN bool_and(jsonb_typeof(l.value) = 'number')
              THEN to_jsonb(max(CASE WHEN jsonb_typeof(l.value) = 'number' THEN (l.value #>> '{{}}')::numeric END))
              ELSE to_jsonb(bool_or(CASE WHEN jsonb_typeof(l.value) = 'boolean' THEN (l.value #>> '{{}}')::boolean END)) END AS merged
    FROM candidates c, jsonb_each(c.limits) AS l
   GROUP BY l.key
) m
HAVING count(*) > 0
$$;
ALTER FUNCTION {FN} OWNER TO hermi_definer;
REVOKE ALL ON FUNCTION {FN} FROM PUBLIC;
GRANT EXECUTE ON FUNCTION {FN} TO hermi_app;
"""

DOWN = f"DROP FUNCTION IF EXISTS {FN};\n"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UP)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DOWN)
