"""0019_invite_preview: preview_trip_invite(token_hash) for the public invite landing page (WF-025.1). Expand only.

GET /invites/{token} has no signed-in user, and row-level security hides every invite from one. This definer function
returns the four fields 04 section 5.6 allows (trip name, cover, inviter display name, role) for a live invite, and no
row for an unknown, revoked, expired, used-up or trashed-trip invite, so the caller cannot tell those apart.
Same contract as redeem_trip_invite: definer owner, pinned search_path, no PUBLIC, execute for hermi_app only.

Revision ID: 0019_invite_preview
Revises: 0018_unlink_my_traveler
"""

from alembic import op

revision = "0019_invite_preview"
down_revision = "0018_unlink_my_traveler"
branch_labels = None
depends_on = None

FN = "preview_trip_invite(bytea)"

UP = f"""
CREATE FUNCTION preview_trip_invite(p_token_hash bytea)
RETURNS TABLE (trip_name text, cover_url text, inviter_name text, role trip_role)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT t.name, t.cover_image_url, NULLIF(u.display_name, ''), i.role
    FROM trip_invites i
    JOIN trips t ON t.id = i.trip_id AND t.deleted_at IS NULL
    LEFT JOIN users u ON u.id = i.invited_by
   WHERE i.token_hash = p_token_hash AND i.revoked_at IS NULL AND i.expires_at > now() AND i.use_count < i.max_uses
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
