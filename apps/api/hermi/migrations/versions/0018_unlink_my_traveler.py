"""0018_unlink_my_traveler: unlink_my_traveler(trip), the undo of link_my_traveler (WF-024.1). Expand only.

A member who linked themselves to a traveler owned by someone else cannot clear `people.linked_user_id`: row-level security
lets only the person's owner update it. This definer function clears the caller's own link on one trip they belong to.
Same contract as link_my_traveler: definer owner, pinned search_path, no PUBLIC, execute for hermi_app only.

Revision ID: 0018_unlink_my_traveler
Revises: 0017_trip_effective_limits
"""

from alembic import op

revision = "0018_unlink_my_traveler"
down_revision = "0017_trip_effective_limits"
branch_labels = None
depends_on = None

FN = "unlink_my_traveler(uuid)"

UP = f"""
CREATE FUNCTION unlink_my_traveler(p_trip uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id();
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  IF NOT EXISTS (SELECT 1 FROM trip_members WHERE trip_id = p_trip AND user_id = v_me) THEN
    RAISE EXCEPTION 'insufficient_role' USING ERRCODE = '42501';
  END IF;
  UPDATE people SET linked_user_id = NULL
   WHERE linked_user_id = v_me AND NOT is_self AND owner_user_id <> v_me
     AND id IN (SELECT person_id FROM trip_people WHERE trip_id = p_trip);
END $$;
ALTER FUNCTION {FN} OWNER TO hermi_definer;
REVOKE ALL ON FUNCTION {FN} FROM PUBLIC;
GRANT EXECUTE ON FUNCTION {FN} TO hermi_app;
"""

DOWN = f"DROP FUNCTION IF EXISTS {FN};\n"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UP)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DOWN)
