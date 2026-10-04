"""0016_bootstrap_subject: bootstrap_user writes auth_identities.provider_subject, and resolve_identity (03 sections 5.1 and 6.4). Expand only.

0014 made bootstrap_user with five parameters, but 03 says it sets provider_subject, the upstream Apple or Google
subject that identity_hashes needs. The new sixth parameter defaults to null, so a five argument call still works
during a rolling deploy. The old signature is dropped (a second overload would make the call ambiguous) and the
owner, REVOKE and GRANT are redone for the new one. 0014 is merged and stays as it is.

resolve_identity(provider, subject) is the sign-in lookup: row-level security hides auth_identities from the API
role until app.user_id is set, and the id comes from this lookup. Same contract as bootstrap_user: definer owner,
pinned search_path, no PUBLIC, execute for hermi_app only.

Revision ID: 0016_bootstrap_subject
Revises: 0015_seed
"""

from alembic import op

revision = "0016_bootstrap_subject"
down_revision = "0015_seed"
branch_labels = None
depends_on = None

# The body of 0014's function, plus provider_subject. Everything else is unchanged.
_BODY = r"""
RETURNS TABLE (user_id uuid, created boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_user uuid;
BEGIN
  SELECT ai.user_id INTO v_user FROM auth_identities ai
   WHERE ai.provider = p_provider AND ai.subject = p_subject;
  IF v_user IS NOT NULL THEN
    UPDATE auth_identities SET last_login_at = now(){set_existing}
     WHERE provider = p_provider AND subject = p_subject;
    RETURN QUERY SELECT v_user, false;
    RETURN;
  END IF;
  INSERT INTO users (email, email_is_relay, email_verified_at, display_name)
  VALUES (p_email, coalesce(p_email_is_relay, false), CASE WHEN p_email IS NOT NULL THEN now() END,
          left(coalesce(p_display_name, ''), 80))
  RETURNING id INTO v_user;
  INSERT INTO auth_identities (user_id, provider, subject, {col}email, email_is_relay, last_login_at)
  VALUES (v_user, p_provider, p_subject, {val}p_email, coalesce(p_email_is_relay, false), now());
  INSERT INTO people (owner_user_id, linked_user_id, name, is_self)
  VALUES (v_user, v_user, coalesce(nullif(left(p_display_name, 60), ''), 'Me'), true);
  INSERT INTO entitlements (user_id) VALUES (v_user);
  RETURN QUERY SELECT v_user, true;
EXCEPTION WHEN unique_violation THEN
  SELECT ai.user_id INTO v_user FROM auth_identities ai
   WHERE ai.provider = p_provider AND ai.subject = p_subject;
  IF v_user IS NULL THEN
    RAISE;
  END IF;
  RETURN QUERY SELECT v_user, false;
END;
$$;
"""

OLD = "bootstrap_user(text, text, citext, boolean, text)"
NEW = "bootstrap_user(text, text, citext, boolean, text, text)"

UP = (
    f"DROP FUNCTION {OLD};\n"
    "CREATE FUNCTION bootstrap_user(p_provider text, p_subject text, p_email citext, p_email_is_relay boolean,\n"
    "                               p_display_name text, p_provider_subject text DEFAULT NULL)"
    + _BODY.format(
        set_existing=",\n        provider_subject = coalesce(provider_subject, p_provider_subject)",
        col="provider_subject, ",
        val="p_provider_subject, ",
    )
    + f"ALTER FUNCTION {NEW} OWNER TO hermi_definer;\n"
    f"REVOKE ALL ON FUNCTION {NEW} FROM PUBLIC;\n"
    f"GRANT EXECUTE ON FUNCTION {NEW} TO hermi_app;\n"
)

DOWN = (
    f"DROP FUNCTION {NEW};\n"
    "CREATE FUNCTION bootstrap_user(p_provider text, p_subject text, p_email citext, p_email_is_relay boolean,\n"
    "                               p_display_name text)"
    + _BODY.format(set_existing="", col="", val="")
    + f"ALTER FUNCTION {OLD} OWNER TO hermi_definer;\n"
    f"REVOKE ALL ON FUNCTION {OLD} FROM PUBLIC;\n"
    f"GRANT EXECUTE ON FUNCTION {OLD} TO hermi_app;\n"
)

RESOLVE = "resolve_identity(text, text)"
UP += (
    "CREATE FUNCTION resolve_identity(p_provider text, p_subject text)\n"
    "RETURNS TABLE (user_id uuid, status text)\n"
    "LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$\n"
    "  SELECT u.id, u.status::text FROM auth_identities ai JOIN users u ON u.id = ai.user_id\n"
    "   WHERE ai.provider = p_provider AND ai.subject = p_subject\n"
    "$$;\n"
    f"ALTER FUNCTION {RESOLVE} OWNER TO hermi_definer;\n"
    f"REVOKE ALL ON FUNCTION {RESOLVE} FROM PUBLIC;\n"
    f"GRANT EXECUTE ON FUNCTION {RESOLVE} TO hermi_app;\n"
)
DOWN = f"DROP FUNCTION IF EXISTS {RESOLVE};\n" + DOWN


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UP)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DOWN)
