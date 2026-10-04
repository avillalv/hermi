"""0014_rls: grants, FORCE row-level security, policies, helper and definer functions (03 sections 6, 8, 9 and 10).

The SQL is taken from 03 sections 6.1 to 6.4, 8 and 9. Pieces 03 leaves open:
- request_account_deletion, cancel_account_deletion, advance_trip_import, link_my_traveler, file_content_report, clear_run_content and
  clear_my_ai_history are granted to the API in 6.1 but have no DDL in 03, so their bodies follow the contract in 6.1.1.
- trips_guard_owner and its trigger (6.2) and bootstrap_user (6.4) are created here: no earlier revision has them.
- The ALL TABLES grants also reach the existing partitions, so one statement takes those back from hermi_app (6.1: no grant on a partition).
- The admin_* console functions (08 section 6) are not here: 03 gives no list and the console is a later ticket.
Everything runs as hermi_owner (the migrate login). Tests read and write as hermi_api_login and the worker login, never the owner, which FORCE binds.

Revision ID: 0014_rls
Revises: 0013_notifications_samples
"""

from alembic import op

revision = "0014_rls"
down_revision = "0013_notifications_samples"
branch_labels = None
depends_on = None

UP = r"""
-- Functions first: the grants below name them. 03 section 6.2 helpers and owner-change guard, 6.4 bootstrap_user, section 8 and section 9 functions.
CREATE FUNCTION visible_trip_ids() RETURNS SETOF uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT trip_id FROM trip_members WHERE user_id = app_user_id()
$$;

CREATE FUNCTION can_edit_trip(p_trip uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM trip_members
                  WHERE trip_id = p_trip AND user_id = app_user_id() AND role IN ('owner', 'editor'))
$$;

CREATE FUNCTION is_trip_owner(p_trip uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM trip_members WHERE trip_id = p_trip AND user_id = app_user_id() AND role = 'owner')
$$;

CREATE FUNCTION trips_guard_owner() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.owner_user_id <> OLD.owner_user_id AND pg_has_role(current_user, 'hermi_app', 'member') THEN
    RAISE EXCEPTION 'owner_change_forbidden' USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_trips_guard_owner BEFORE UPDATE OF owner_user_id ON trips
  FOR EACH ROW EXECUTE FUNCTION trips_guard_owner();

-- First sign-in (POST /me/bootstrap in 04) runs before any users row exists, so app.user_id is unset
-- and no RLS policy can admit the insert. The app role has no INSERT on users or auth_identities;
-- instead it calls this definer-owned function, which creates exactly one account for one verified
-- (provider, subject) pair and is idempotent. The API passes values only from the verified JWT.
CREATE FUNCTION bootstrap_user(p_provider text, p_subject text, p_email citext, p_email_is_relay boolean,
                               p_display_name text)
RETURNS TABLE (user_id uuid, created boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  v_user uuid;
BEGIN
  SELECT ai.user_id INTO v_user FROM auth_identities ai
   WHERE ai.provider = p_provider AND ai.subject = p_subject;
  IF v_user IS NOT NULL THEN
    UPDATE auth_identities SET last_login_at = now()
     WHERE provider = p_provider AND subject = p_subject;
    RETURN QUERY SELECT v_user, false;
    RETURN;
  END IF;
  INSERT INTO users (email, email_is_relay, email_verified_at, display_name)
  VALUES (p_email, coalesce(p_email_is_relay, false), CASE WHEN p_email IS NOT NULL THEN now() END,   -- the API calls this only with an address the provider verified
          left(coalesce(p_display_name, ''), 80))
  RETURNING id INTO v_user;
  INSERT INTO auth_identities (user_id, provider, subject, email, email_is_relay, last_login_at)
  VALUES (v_user, p_provider, p_subject, p_email, coalesce(p_email_is_relay, false), now());
  INSERT INTO people (owner_user_id, linked_user_id, name, is_self)
  VALUES (v_user, v_user, coalesce(nullif(left(p_display_name, 60), ''), 'Me'), true);
  INSERT INTO entitlements (user_id) VALUES (v_user);
  RETURN QUERY SELECT v_user, true;
EXCEPTION WHEN unique_violation THEN
  -- A concurrent bootstrap for the same identity won; return its row.
  SELECT ai.user_id INTO v_user FROM auth_identities ai
   WHERE ai.provider = p_provider AND ai.subject = p_subject;
  IF v_user IS NULL THEN
    -- Not a race: the email already belongs to another account (uq_users_email). The API answers
    -- 409 email_in_use and offers to sign in with the original method, then link identities.
    RAISE;
  END IF;
  RETURN QUERY SELECT v_user, false;
END;
$$;
ALTER FUNCTION bootstrap_user(text, text, citext, boolean, text) OWNER TO hermi_definer;   -- BYPASSRLS, so FORCE on users does not block the insert
REVOKE ALL ON FUNCTION bootstrap_user(text, text, citext, boolean, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION bootstrap_user(text, text, citext, boolean, text) TO hermi_app;

-- 03 section 8: retention.
-- Hard-deletes trips that have been in the trash for more than 30 days (job purge_trash, daily 04:30). Children cascade. Only trips are soft-deleted
-- (trips.deleted_at); itinerary items, lodging and notes have no trash of their own and go with their trip. Returns the number of trips removed.
CREATE FUNCTION purge_trash(p_window interval DEFAULT interval '30 days') RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE n integer;
BEGIN
  DELETE FROM trips WHERE deleted_at IS NOT NULL AND deleted_at < now() - p_window;
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;

-- Applies every retention class in the table above except the ones that drop partitions (section 9), the cascades and the account deletion job (8.1)
-- (job retention_sweep, daily 05:30). Returns the number of rows deleted or scrubbed.
CREATE FUNCTION retention_sweep() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_sql text; k integer; n integer := 0;
BEGIN
  FOREACH v_sql IN ARRAY ARRAY[
    -- Deletes and scrubs by class. Each statement is safe to repeat.
    $q$DELETE FROM trip_invites WHERE expires_at < now() - interval '30 days'$q$,
    $q$DELETE FROM trip_share_links WHERE expires_at < now() - interval '30 days' OR revoked_at < now() - interval '30 days'$q$,
    $q$DELETE FROM activity_log WHERE created_at < now() - interval '90 days'$q$,
    $q$UPDATE trip_imports SET preview = NULL WHERE preview IS NOT NULL AND created_at < now() - interval '7 days'$q$,
    $q$UPDATE trip_imports SET feed_url_enc = NULL WHERE feed_url_enc IS NOT NULL AND NOT poll_enabled
         AND (status = 'discarded' OR created_at < now() - interval '7 days')$q$,
    $q$UPDATE trip_imports SET pending_changes = NULL, pending_changes_at = NULL
         WHERE pending_changes IS NOT NULL AND pending_changes_at < now() - interval '30 days'$q$,
    $q$DELETE FROM plan_verifications WHERE expires_at < now()$q$,
    $q$UPDATE fare_observations SET raw = NULL WHERE raw IS NOT NULL AND observed_at < now() - interval '14 days'$q$,
    $q$DELETE FROM route_price_insights WHERE expires_at < now() - interval '7 days'$q$,
    $q$UPDATE lodging_options SET raw = NULL WHERE raw IS NOT NULL AND created_at < now() - interval '30 days'$q$,
    $q$UPDATE runs SET prompt = NULL WHERE prompt IS NOT NULL AND created_at < now() - interval '30 days'$q$,
    $q$UPDATE runs SET report = NULL WHERE report IS NOT NULL AND created_at < now() - interval '12 months'$q$,
    $q$DELETE FROM runs WHERE created_at < now() - interval '25 months'$q$,
    $q$UPDATE run_events SET payload = NULL WHERE payload IS NOT NULL AND ts < now() - interval '14 days'$q$,
    $q$DELETE FROM run_events WHERE ts < now() - interval '30 days'$q$,
    $q$DELETE FROM ai_usage WHERE created_at < now() - interval '25 months'$q$,
    $q$DELETE FROM shared_research_cache WHERE stale_until < now() AND flagged_at IS NULL$q$,
    $q$DELETE FROM places_cache WHERE expires_at < now() - interval '1 day'$q$,
    $q$DELETE FROM credit_debts WHERE amount = 0 AND updated_at < now() - interval '12 months'$q$,
    $q$UPDATE store_transactions SET raw = NULL WHERE raw IS NOT NULL AND created_at < now() - interval '12 months'$q$,
    $q$DELETE FROM notifications WHERE created_at < now() - interval '90 days'$q$,
    $q$DELETE FROM webhook_events WHERE received_at < now() - interval '12 months'$q$,
    $q$DELETE FROM support_tickets WHERE resolved_at < now() - interval '24 months'$q$,
    $q$DELETE FROM content_reports WHERE handled_at < now() - interval '24 months'$q$,
    $q$DELETE FROM data_exports WHERE requested_at < now() - interval '30 days'$q$,
    $q$DELETE FROM deletion_requests WHERE completed_at < now() - interval '12 months'$q$,
    $q$DELETE FROM rate_limit_counters WHERE window_start < now() - interval '1 day'$q$,
    $q$DELETE FROM idempotency_keys WHERE expires_at < now()$q$,
    $q$DELETE FROM identity_hashes WHERE created_at < now() - interval '12 months'$q$,
    -- Financial records: 7 years, then deleted (they were anonymized when the account was deleted). The ledger first, its grants after.
    $q$DELETE FROM credit_ledger WHERE created_at < now() - interval '7 years'$q$,
    $q$DELETE FROM credit_grants WHERE created_at < now() - interval '7 years'$q$,
    $q$DELETE FROM trip_passes WHERE created_at < now() - interval '7 years'$q$,
    $q$DELETE FROM subscriptions WHERE created_at < now() - interval '7 years'$q$,
    $q$DELETE FROM store_transactions WHERE created_at < now() - interval '7 years'$q$,
    $q$DELETE FROM affiliate_conversions WHERE created_at < now() - interval '7 years'$q$,
    $q$DELETE FROM affiliate_payouts WHERE created_at < now() - interval '7 years'$q$,
    $q$DELETE FROM devices WHERE revoked_at < now() - interval '90 days'$q$
  ] LOOP
    EXECUTE v_sql;
    GET DIAGNOSTICS k = ROW_COUNT;
    n := n + k;
  END LOOP;

  -- fare_observations is large: delete past 24 months in batches of 5,000 rows.
  LOOP
    DELETE FROM fare_observations WHERE id IN (SELECT id FROM fare_observations WHERE observed_at < now() - interval '24 months' LIMIT 5000);
    GET DIAGNOSTICS k = ROW_COUNT;
    n := n + k;
    EXIT WHEN k < 5000;
  END LOOP;

  -- audit_log: the one place a delete is allowed. audit_log_immutable() (5.16) lets this function delete a row only when the transaction-local
  -- setting is on, the caller is hermi_definer and the row is past its class (13 months standard, 7 years extended).
  PERFORM set_config('hermi.audit_purge', 'on', true);
  DELETE FROM audit_log
   WHERE created_at < now() - CASE retention_class WHEN 'extended' THEN interval '7 years' ELSE interval '13 months' END;
  GET DIAGNOSTICS k = ROW_COUNT;
  n := n + k;
  PERFORM set_config('hermi.audit_purge', 'off', true);
  RETURN n;
END $$;

ALTER FUNCTION purge_trash(interval) OWNER TO hermi_definer;
ALTER FUNCTION retention_sweep() OWNER TO hermi_definer;
GRANT UPDATE, DELETE ON trips, trip_invites, trip_share_links, activity_log, plan_verifications, fare_observations, route_price_insights,
  lodging_options, run_events, places_cache, notifications, webhook_events, support_tickets, content_reports, data_exports,
  rate_limit_counters, idempotency_keys, identity_hashes, credit_grants, credit_ledger, trip_passes, subscriptions, store_transactions,
  affiliate_conversions, affiliate_payouts, devices TO hermi_definer;
REVOKE EXECUTE ON FUNCTION purge_trash(interval), retention_sweep() FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION purge_trash(interval), retention_sweep() TO hermi_worker;

-- 03 section 9: partition maintenance.
-- The scheduler job maintain_partitions (daily 02:30) calls this. The worker role cannot create objects, and CREATE TABLE ... PARTITION OF needs
-- ownership of the parent, so the three parents and every partition are owned by hermi_definer (a role hermi_owner is a member of, so later
-- migrations can still alter them) and the creation runs as hermi_definer (SECURITY DEFINER, 6.1). 0014 re-owns the parents and the first
-- partitions made by 0005 once, at the end (the DO block below). No grant is given on any partition: the API reads and writes through the parent only.
CREATE FUNCTION maintain_partitions() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN ensure_month_partitions('provider_calls', 3) + ensure_month_partitions('run_events', 3) + ensure_month_partitions('link_clicks', 3);
END $$;
ALTER FUNCTION maintain_partitions() OWNER TO hermi_definer;
ALTER FUNCTION ensure_month_partitions(regclass, integer) SECURITY DEFINER SET search_path = public, pg_temp;
ALTER FUNCTION drop_old_partitions(regclass, integer) SECURITY DEFINER SET search_path = public, pg_temp;
ALTER FUNCTION ensure_month_partitions(regclass, integer) OWNER TO hermi_definer;
ALTER FUNCTION drop_old_partitions(regclass, integer) OWNER TO hermi_definer;
-- The worker never gets the generic helpers (they take any table): it calls maintain_partitions() and a wrapper that fixes the parent list.
CREATE FUNCTION drop_old_log_partitions(p_parent text, p_keep_months integer) RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  IF p_parent NOT IN ('provider_calls', 'run_events', 'link_clicks') THEN
    RAISE EXCEPTION 'not a partitioned log table' USING ERRCODE = '22023';
  END IF;
  RETURN drop_old_partitions(p_parent::regclass, p_keep_months);
END $$;
ALTER FUNCTION drop_old_log_partitions(text, integer) OWNER TO hermi_definer;
REVOKE EXECUTE ON FUNCTION maintain_partitions(), drop_old_log_partitions(text, integer), ensure_month_partitions(regclass, integer), drop_old_partitions(regclass, integer) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION maintain_partitions(), drop_old_log_partitions(text, integer) TO hermi_worker;


-- The seven functions 6.1 grants to the API and says are "written in 0014". 03 gives their contract in 6.1.1 and no DDL, so the bodies below follow
-- that table: each checks app_user_id() itself, has a fixed search_path and is owned by hermi_definer (the last statement of this migration).

-- POST /me/deletion: records the request, flags the account, revokes devices and cancels the invites the person sent. Idempotent while a request is open.
-- Trip transfers are separate calls to transfer_trip_owner(); the purge itself is the worker's deletion job (8.1).
CREATE FUNCTION request_account_deletion(p_reason text DEFAULT NULL) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id(); v_id uuid;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  IF NOT EXISTS (SELECT 1 FROM users WHERE id = v_me AND status <> 'deleted') THEN
    RAISE EXCEPTION 'account_not_found' USING ERRCODE = 'P0002';
  END IF;
  SELECT id INTO v_id FROM deletion_requests WHERE user_id = v_me AND status IN ('pending', 'grace') ORDER BY requested_at DESC LIMIT 1;
  IF v_id IS NOT NULL THEN RETURN v_id; END IF;
  INSERT INTO deletion_requests (user_id, reason) VALUES (v_me, left(p_reason, 500)) RETURNING id INTO v_id;
  UPDATE users SET status = 'pending_deletion' WHERE id = v_me;
  UPDATE devices SET revoked_at = now(), refresh_token_hash = NULL, push_token = NULL WHERE user_id = v_me AND revoked_at IS NULL;
  UPDATE trip_invites SET revoked_at = now() WHERE invited_by = v_me AND revoked_at IS NULL AND expires_at > now();
  RETURN v_id;
END $$;

-- POST /me/deletion/cancel: inside the grace window only. Returns false when there is nothing to cancel.
CREATE FUNCTION cancel_account_deletion() RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id(); n integer;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  UPDATE deletion_requests SET status = 'cancelled', cancelled_at = now()
   WHERE user_id = v_me AND status IN ('pending', 'grace') AND scheduled_purge_at > now();
  GET DIAGNOSTICS n = ROW_COUNT;
  IF n = 0 THEN RETURN false; END IF;
  UPDATE users SET status = CASE WHEN suspended_at IS NOT NULL THEN 'suspended'::user_status ELSE 'active'::user_status END
   WHERE id = v_me AND status = 'pending_deletion';
  RETURN true;
END $$;

-- The one way the API changes an existing import (6.1.1). Verbs: confirm (review to applied), discard, refresh (poll the feed now), confirm_changes and
-- dismiss_changes (clear the pending diff; the caller writes the confirmed items as itself). Returns the import's status afterwards.
-- An applied import that earned the reward keeps its status on discard (ck_trip_imports_reward) and only loses its payload columns.
CREATE FUNCTION advance_trip_import(p_import uuid, p_action text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id(); v_imp trip_imports%ROWTYPE;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  IF p_action IS NULL OR p_action NOT IN ('confirm', 'discard', 'refresh', 'confirm_changes', 'dismiss_changes') THEN
    RAISE EXCEPTION 'unknown_import_action' USING ERRCODE = '22023';
  END IF;
  SELECT * INTO v_imp FROM trip_imports WHERE id = p_import AND user_id = v_me FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'import_not_found' USING ERRCODE = 'P0002'; END IF;
  IF p_action = 'confirm' THEN
    IF v_imp.status <> 'review' THEN RAISE EXCEPTION 'invalid_import_state' USING ERRCODE = '55000'; END IF;
    UPDATE trip_imports SET status = 'applied', completed_at = now(), preview = NULL WHERE id = p_import;
  ELSIF p_action = 'discard' THEN
    IF v_imp.status = 'discarded' THEN RETURN 'discarded'; END IF;
    UPDATE trip_imports
       SET status = CASE WHEN status = 'applied' THEN status ELSE 'discarded' END,
           preview = NULL, feed_url_enc = NULL, pending_changes = NULL, pending_changes_at = NULL, poll_enabled = false, next_poll_at = NULL
     WHERE id = p_import;
  ELSIF p_action = 'refresh' THEN
    IF v_imp.source <> 'ics_feed' OR v_imp.status <> 'applied' OR NOT v_imp.poll_enabled THEN
      RAISE EXCEPTION 'invalid_import_state' USING ERRCODE = '55000';
    END IF;
    UPDATE trip_imports SET next_poll_at = now() WHERE id = p_import;
  ELSE
    IF v_imp.pending_changes IS NULL THEN RAISE EXCEPTION 'invalid_import_state' USING ERRCODE = '55000'; END IF;
    UPDATE trip_imports SET pending_changes = NULL, pending_changes_at = NULL WHERE id = p_import;
  END IF;
  RETURN (SELECT status FROM trip_imports WHERE id = p_import);
END $$;

-- PUT /trips/{id}/members/me/traveler: the caller (a member) says which traveler on the trip is them. The person may belong to the trip owner.
-- Returns false when the traveler is not on the trip, is a "Me" row, is the caller's own, or is already linked to someone else.
CREATE FUNCTION link_my_traveler(p_trip uuid, p_person uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id(); v_person people%ROWTYPE;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  IF NOT EXISTS (SELECT 1 FROM trip_members WHERE trip_id = p_trip AND user_id = v_me) THEN
    RAISE EXCEPTION 'insufficient_role' USING ERRCODE = '42501';
  END IF;
  SELECT p.* INTO v_person FROM people p JOIN trip_people tp ON tp.person_id = p.id AND tp.trip_id = p_trip WHERE p.id = p_person FOR UPDATE OF p;
  IF NOT FOUND OR v_person.is_self OR v_person.owner_user_id = v_me OR (v_person.linked_user_id IS NOT NULL AND v_person.linked_user_id <> v_me) THEN
    RETURN false;
  END IF;
  -- uq_people_owner_linked: one person per owner is linked to a given user.
  UPDATE people SET linked_user_id = NULL WHERE owner_user_id = v_person.owner_user_id AND linked_user_id = v_me AND id <> p_person;
  UPDATE people SET linked_user_id = v_me WHERE id = p_person;
  RETURN true;
END $$;

-- POST /reports. p_target_type is shared_trip, agent_note, ai_answer or research_cache; p_ref is the share link, note or run id, or the cache key.
-- The caller must be able to see what they report (a note or run on one of their trips). A cached answer is expired at once and flagged at three distinct reporters.
CREATE FUNCTION file_content_report(p_target_type text, p_ref text, p_reason text, p_detail text DEFAULT '') RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id(); v_id uuid; v_key char(64); v_share uuid; v_note uuid; v_run uuid; v_n integer;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  IF p_target_type = 'shared_trip' THEN
    v_share := p_ref::uuid;
    IF NOT EXISTS (SELECT 1 FROM trip_share_links WHERE id = v_share) THEN RAISE EXCEPTION 'target_not_found' USING ERRCODE = 'P0002'; END IF;
  ELSIF p_target_type = 'agent_note' THEN
    v_note := p_ref::uuid;
    IF NOT EXISTS (SELECT 1 FROM notes WHERE id = v_note AND trip_id IN (SELECT visible_trip_ids()) AND (NOT is_private OR author_user_id = v_me)) THEN
      RAISE EXCEPTION 'target_not_found' USING ERRCODE = 'P0002';
    END IF;
  ELSIF p_target_type = 'ai_answer' THEN
    v_run := p_ref::uuid;
    SELECT r.cache_key INTO v_key FROM runs r WHERE r.id = v_run AND r.trip_id IN (SELECT visible_trip_ids());
    IF NOT FOUND THEN RAISE EXCEPTION 'target_not_found' USING ERRCODE = 'P0002'; END IF;
  ELSIF p_target_type = 'research_cache' THEN
    v_key := p_ref;
    IF NOT EXISTS (SELECT 1 FROM shared_research_cache WHERE key = v_key) THEN RAISE EXCEPTION 'target_not_found' USING ERRCODE = 'P0002'; END IF;
  ELSE
    RAISE EXCEPTION 'unknown_report_target' USING ERRCODE = '22023';
  END IF;
  INSERT INTO content_reports (reporter_user_id, target_type, share_link_id, note_id, run_id, cache_key, reason, detail)
  VALUES (v_me, p_target_type, v_share, v_note, v_run, v_key, p_reason, coalesce(p_detail, '')) RETURNING id INTO v_id;
  IF v_key IS NOT NULL THEN
    SELECT count(DISTINCT reporter_user_id) INTO v_n FROM content_reports WHERE cache_key = v_key AND reporter_user_id IS NOT NULL;
    UPDATE shared_research_cache
       SET expires_at = least(expires_at, now()), stale_until = least(stale_until, now()),
           report_count = least(v_n, 32767),
           flagged_at = CASE WHEN v_n >= 3 THEN coalesce(flagged_at, now()) ELSE flagged_at END
     WHERE key = v_key;
  END IF;
  RETURN v_id;
END $$;

-- DELETE /agent-runs/{id}: the starter or the trip owner nulls the prompt and report of one run. Returns false when the caller may not.
CREATE FUNCTION clear_run_content(p_run uuid) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id(); n integer;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  UPDATE runs SET prompt = NULL, report = NULL WHERE id = p_run AND (user_id = v_me OR is_trip_owner(trip_id));
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n > 0;
END $$;

-- DELETE /me/ai-history: the same for every run the caller started. Returns the number of runs touched.
CREATE FUNCTION clear_my_ai_history() RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_me uuid := app_user_id(); n integer;
BEGIN
  IF v_me IS NULL THEN RAISE EXCEPTION 'not_authenticated' USING ERRCODE = '42501'; END IF;
  UPDATE runs SET prompt = NULL, report = NULL WHERE user_id = v_me AND (prompt IS NOT NULL OR report IS NOT NULL);
  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $$;


-- 03 section 6.1: schema usage, role grants, revokes and the EXECUTE grants.
GRANT USAGE ON SCHEMA public TO hermi_app, hermi_worker, hermi_admin, hermi_definer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hermi_worker;
ALTER DEFAULT PRIVILEGES FOR ROLE hermi_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hermi_worker;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hermi_app, hermi_worker, hermi_admin, hermi_definer;

-- The admin console reads everything and writes only operational tables directly (each edit also inserts an audit_log row in the same transaction).
-- Tenant content and money change only through the audited admin_* functions below, so BYPASSRLS on hermi_admin_login
-- cannot be used to edit a trip, a balance or an account (a BYPASSRLS role skips policies, so its limits are grants).
GRANT SELECT ON ALL TABLES IN SCHEMA public TO hermi_admin;
ALTER DEFAULT PRIVILEGES FOR ROLE hermi_owner IN SCHEMA public GRANT SELECT ON TABLES TO hermi_definer, hermi_admin;
GRANT INSERT, UPDATE, DELETE ON rate_limit_counters, admin_users, feature_flags, kill_switches, plans, store_products, credit_action_prices,
  affiliate_programs, affiliate_link_templates, sample_trips, shared_research_cache, support_tickets, content_reports TO hermi_admin;
GRANT UPDATE ON affiliate_conversions, affiliate_payouts, webhook_events TO hermi_admin;
GRANT INSERT ON audit_log TO hermi_admin;

-- The API gets read and write on tenant tables, then loses what it must never touch.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hermi_app;
-- Abuse and attestation state is never touched by the API: only definer functions and the worker write it (5.1, 5.8).
REVOKE ALL ON identity_hashes, device_attestations, guest_allowances FROM hermi_app;

-- Global reference and catalog data: read only for the API (workers and the admin console write them).
REVOKE INSERT, UPDATE, DELETE ON airports, fx_rates, places_cache, plans, store_products, credit_action_prices,
  shared_research_cache, fare_observations, route_price_insights, affiliate_programs, affiliate_link_templates,
  feature_flags, kill_switches, sample_trips FROM hermi_app;
-- Money and entitlement state is written only by the billing service (worker role) and the credit functions.
REVOKE INSERT, UPDATE, DELETE ON subscriptions, entitlements, trip_passes, store_transactions,
  credit_grants, credit_ledger, credit_debts FROM hermi_app;
-- Referral state is written only through the referral functions in 5.9 and by the worker.
REVOKE INSERT, UPDATE, DELETE ON referral_codes, referral_rewards FROM hermi_app;
-- Never visible to the API. deletion_requests is reached only through request_account_deletion() and cancel_account_deletion() (table in 6.1.1).
REVOKE ALL ON admin_users, webhook_events, affiliate_conversions, affiliate_payouts, deletion_requests,
  rate_limit_counters, provider_calls, provider_call_rollups,
  revenue_by_month, revenue_by_surface, revenue_by_partner, booked_fare_drops FROM hermi_app;
GRANT INSERT ON provider_calls TO hermi_app;                       -- the API logs its own provider calls
GRANT SELECT, INSERT, UPDATE, DELETE ON rate_limit_counters TO hermi_app;   -- Postgres-backed rate limits
GRANT INSERT ON audit_log TO hermi_app;  REVOKE UPDATE, DELETE, SELECT, TRUNCATE ON audit_log FROM hermi_app;
REVOKE UPDATE, DELETE ON link_clicks FROM hermi_app;               -- clicks are minted by the API, never edited by users
GRANT UPDATE (clicked_at, redirect_status, opened_in) ON link_clicks TO hermi_app;   -- the /go redirect stamps these three columns and nothing else
-- link_clicks is partitioned: the API reads and writes through the parent only, and no grant is given on a partition (a new partition has none, which is the safe default).

-- A user may edit only their own profile columns. Status, suspension and the refund-abuse block are written by the worker and admin roles.
REVOKE UPDATE ON users FROM hermi_app;
GRANT UPDATE (display_name, locale, timezone, home_currency, home_airports, country_code, hide_booking_links, prefs, last_seen_at) ON users TO hermi_app;

-- Imports: the API creates an import. Every later change (confirm, discard, dismiss changes, refresh) goes through advance_trip_import(), and polling through
-- set_import_polling(); the worker writes the preview. Nobody but the worker deletes the row, because the reward flag on it is what makes the free Trip Pass a once-per-user grant.
REVOKE UPDATE, DELETE ON trip_imports FROM hermi_app;

-- Plan verification: the API starts a verification, sets its status to checking or discarded, deletes it, and lets the person tick which items to check and import.
-- Items, verdicts, evidence and counts are written by the worker (or the verify_extract SystemSession, 6.6) only, so a member cannot edit what the evidence says.
REVOKE UPDATE ON plan_verifications FROM hermi_app;
GRANT UPDATE (status) ON plan_verifications TO hermi_app;
REVOKE INSERT, UPDATE, DELETE ON plan_verification_items FROM hermi_app;
GRANT UPDATE (selected, include_in_import) ON plan_verification_items TO hermi_app;

-- Runs: the API inserts a queued run and may ask for a cancel; everything else on a run is written by the worker.
REVOKE UPDATE, DELETE ON runs FROM hermi_app;
GRANT UPDATE (cancel_requested) ON runs TO hermi_app;

-- Notifications: the API reads them and marks them read; jobs create them.
REVOKE INSERT, UPDATE, DELETE ON notifications FROM hermi_app;
GRANT UPDATE (read_at) ON notifications TO hermi_app;

-- Append-only user records: consents are a history, and an export row is changed by the export job.
REVOKE UPDATE, DELETE ON consents, data_exports FROM hermi_app;

-- Support: a user opens a ticket and adds messages to it; status, priority, assignment and internal notes belong to the console.
REVOKE INSERT, UPDATE, DELETE ON support_tickets FROM hermi_app;
GRANT INSERT (user_id, trip_id, email, subject, category, source, messages, app_version, platform) ON support_tickets TO hermi_app;
GRANT UPDATE (messages) ON support_tickets TO hermi_app;

-- Reports: users file them through file_content_report() (it also expires the cached answer) and read their own; moderators work them as hermi_admin.
REVOKE INSERT, UPDATE, DELETE ON content_reports FROM hermi_app;

-- Nobody but the retention sweep changes or removes an audit row (the trigger in 5.16 is the second lock). The console and the worker may insert and read.
REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM hermi_worker, hermi_admin;
-- Nobody truncates a money table. The console has no DELETE on them either (it was never granted); the worker deletes only in the retention jobs.
REVOKE TRUNCATE ON credit_ledger, credit_grants, credit_debts, store_transactions, subscriptions, trip_passes,
  affiliate_conversions, affiliate_payouts, webhook_events, trip_imports, referral_rewards FROM hermi_worker;

-- Credit functions run with the definer's rights so the API cannot write credit_grants directly.
ALTER FUNCTION reserve_credits(uuid, uuid, integer, ai_action, uuid, text) SECURITY DEFINER SET search_path = public, pg_temp;
ALTER FUNCTION settle_credits(uuid, integer, bigint) SECURITY DEFINER SET search_path = public, pg_temp;
REVOKE EXECUTE ON FUNCTION reserve_credits(uuid, uuid, integer, ai_action, uuid, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION settle_credits(uuid, integer, bigint) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION reserve_credits(uuid, uuid, integer, ai_action, uuid, text) TO hermi_app, hermi_worker;
GRANT  EXECUTE ON FUNCTION settle_credits(uuid, integer, bigint) TO hermi_app, hermi_worker;
-- The API asks for the lazy Free allowance and the taster grant through these two; debt functions are for the billing service (worker role) only.
ALTER FUNCTION ensure_free_monthly_grant(uuid) SECURITY DEFINER SET search_path = public, pg_temp;
ALTER FUNCTION ensure_taster_grant(uuid) SECURITY DEFINER SET search_path = public, pg_temp;
REVOKE EXECUTE ON FUNCTION ensure_free_monthly_grant(uuid), ensure_taster_grant(uuid), record_credit_debt(uuid, integer, text), settle_credit_debt(uuid) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION ensure_free_monthly_grant(uuid), ensure_taster_grant(uuid) TO hermi_app, hermi_worker;
GRANT  EXECUTE ON FUNCTION record_credit_debt(uuid, integer, text), settle_credit_debt(uuid) TO hermi_worker;
-- Phase 1 reward functions (5.9). The API may ask for its own referral code and redeem a code; granting is worker only.
REVOKE EXECUTE ON FUNCTION grant_import_reward(uuid), ensure_referral_code(uuid), grant_referral_reward(uuid),
  my_referral_code(), redeem_referral(text), set_import_polling(uuid, boolean) FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION grant_import_reward(uuid), ensure_referral_code(uuid), grant_referral_reward(uuid) TO hermi_worker;
GRANT  EXECUTE ON FUNCTION my_referral_code(), redeem_referral(text), set_import_polling(uuid, boolean) TO hermi_app, hermi_worker;

-- Functions the API calls for writes the app role has no grant for (the table in 6.1.1 says which route calls which). redeem_trip_invite and
-- transfer_trip_owner are defined in 5.4; the others are written in 0014 beside these grants. Each checks app_user_id() itself, has a fixed
-- search_path and is owned by hermi_definer. A name without an argument list matches the function's one overload.
REVOKE EXECUTE ON FUNCTION redeem_trip_invite, transfer_trip_owner, request_account_deletion, cancel_account_deletion,
  advance_trip_import, link_my_traveler, file_content_report, clear_run_content, clear_my_ai_history, my_provider_spend_micros FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION redeem_trip_invite, transfer_trip_owner, request_account_deletion, cancel_account_deletion,
  advance_trip_import, link_my_traveler, file_content_report, clear_run_content, clear_my_ai_history, my_provider_spend_micros TO hermi_app;
-- Procrastinate: the API defers jobs through the library's own function; workers hold full rights on the procrastinate_* tables.
GRANT EXECUTE ON FUNCTION procrastinate_defer_jobs_v1 TO hermi_app;
-- The retention sweep is the only deleter of expired audit rows (5.16); only the scheduler's worker role runs it.
REVOKE EXECUTE ON FUNCTION retention_sweep FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION retention_sweep TO hermi_worker;
-- Audited console actions: one admin_* function per action in 08 section 6 that changes tenant content, an account or money (credit adjustments, status changes,
-- comps, hiding content, disabling a share link, rejecting a referral). Each writes its audit_log row in the same transaction and reads the admin from app.admin_user_id.
-- EXECUTE is granted to hermi_admin only, with the function.

-- 03 section 6.1 'Helpers and FORCE': what hermi_definer may read and write.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO hermi_definer;
-- Write rights follow the functions: extend this list in the migration that adds a function writing another table.
GRANT INSERT, UPDATE, DELETE ON users, auth_identities, people, entitlements, devices, trips, trip_members, trip_invites, trip_imports, trip_passes,
  credit_grants, credit_ledger, credit_debts, ai_usage, referral_codes, referral_rewards, notifications, deletion_requests,
  content_reports, shared_research_cache, runs, audit_log, identity_hashes, device_attestations, guest_allowances TO hermi_definer;

-- Views and partition ownership come after the ALL TABLES grants, so the app role gets no access to partition_default_rows.
-- Co-members see each other's display name only, never email. The view is owned by hermi_definer, so it reads co-members across the users policy.
CREATE VIEW trip_member_profiles AS
SELECT tm.trip_id, tm.user_id, tm.role, u.display_name
  FROM trip_members tm JOIN users u ON u.id = tm.user_id
 WHERE tm.trip_id IN (SELECT visible_trip_ids());
ALTER VIEW trip_member_profiles OWNER TO hermi_definer;
GRANT SELECT ON trip_member_profiles TO hermi_app;

ALTER TABLE provider_calls OWNER TO hermi_definer;
ALTER TABLE run_events     OWNER TO hermi_definer;
ALTER TABLE link_clicks    OWNER TO hermi_definer;
DO $$ DECLARE c regclass; BEGIN
  FOR c IN SELECT i.inhrelid::regclass FROM pg_inherits i
            WHERE i.inhparent IN ('provider_calls'::regclass, 'run_events'::regclass, 'link_clicks'::regclass) LOOP
    EXECUTE format('ALTER TABLE %s OWNER TO hermi_definer', c);
  END LOOP;
END $$;

-- Rows per default partition. The worker alerts (10 section 5.3) when any row count is above 0: rows only land there when a month's
-- partition was missing. Owned by hermi_definer so it can read the partitions under FORCE.
CREATE VIEW partition_default_rows AS
SELECT 'provider_calls' AS parent, count(*) AS row_count FROM provider_calls_default
UNION ALL SELECT 'run_events', count(*) FROM run_events_default
UNION ALL SELECT 'link_clicks', count(*) FROM link_clicks_default;
ALTER VIEW partition_default_rows OWNER TO hermi_definer;
REVOKE ALL ON partition_default_rows FROM PUBLIC;
GRANT SELECT ON partition_default_rows TO hermi_worker, hermi_admin;

-- 03 section 6.3.
-- trips: members read; owner deletes; anyone may create a trip they own; editors update (owner change is blocked by trg_trips_guard_owner).
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trips FORCE ROW LEVEL SECURITY;
CREATE POLICY trips_select ON trips FOR SELECT
  USING ((id IN (SELECT visible_trip_ids()) AND deleted_at IS NULL) OR owner_user_id = (SELECT app_user_id()));   -- trash stays visible to its owner
CREATE POLICY trips_insert ON trips FOR INSERT WITH CHECK (owner_user_id = (SELECT app_user_id()));
CREATE POLICY trips_update ON trips FOR UPDATE USING (can_edit_trip(id)) WITH CHECK (can_edit_trip(id));
CREATE POLICY trips_delete ON trips FOR DELETE USING (is_trip_owner(id));

-- trip_members: co-members read the roster; only the owner adds or changes roles; anyone can remove themselves (leave).
-- Invite redemption inserts the row through the SECURITY DEFINER function redeem_trip_invite() (DDL in section 5.4), not through this policy.
ALTER TABLE trip_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_members FORCE ROW LEVEL SECURITY;
CREATE POLICY trip_members_select ON trip_members FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY trip_members_insert ON trip_members FOR INSERT WITH CHECK (is_trip_owner(trip_id));
CREATE POLICY trip_members_update ON trip_members FOR UPDATE USING (is_trip_owner(trip_id)) WITH CHECK (is_trip_owner(trip_id));
CREATE POLICY trip_members_delete ON trip_members FOR DELETE
  USING (is_trip_owner(trip_id) OR (user_id = (SELECT app_user_id()) AND role <> 'owner'));

-- A trip child table (itinerary_items): every member reads, owner and editors write. Viewers cannot edit.
ALTER TABLE itinerary_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE itinerary_items FORCE ROW LEVEL SECURITY;
CREATE POLICY itinerary_items_select ON itinerary_items FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY itinerary_items_insert ON itinerary_items FOR INSERT WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY itinerary_items_update ON itinerary_items FOR UPDATE USING (can_edit_trip(trip_id)) WITH CHECK (can_edit_trip(trip_id));
CREATE POLICY itinerary_items_delete ON itinerary_items FOR DELETE USING (can_edit_trip(trip_id));

-- 03 section 6.4.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'trip_invites', 'trip_share_links', 'trip_destinations', 'trip_people', 'flight_routes', 'trip_fare_links',
    'chosen_flights', 'itinerary_days', 'saved_places', 'lodging_options', 'checklist_items',
    'plan_verifications', 'plan_verification_items'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()))', t || '_select', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR INSERT WITH CHECK (can_edit_trip(trip_id))', t || '_insert', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR UPDATE USING (can_edit_trip(trip_id)) WITH CHECK (can_edit_trip(trip_id))', t || '_update', t);
    EXECUTE format('CREATE POLICY %I ON %I FOR DELETE USING (can_edit_trip(trip_id))', t || '_delete', t);
  END LOOP;
END $$;

-- Hearts: viewers may heart stays and places. A vote row must be the caller's own.
ALTER TABLE lodging_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE lodging_votes FORCE ROW LEVEL SECURITY;
CREATE POLICY lodging_votes_select ON lodging_votes FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY lodging_votes_insert ON lodging_votes FOR INSERT
  WITH CHECK (user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY lodging_votes_delete ON lodging_votes FOR DELETE
  USING (user_id = (SELECT app_user_id()) OR can_edit_trip(trip_id));        -- editors can clear a traveler's heart

ALTER TABLE saved_place_votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_place_votes FORCE ROW LEVEL SECURITY;
CREATE POLICY saved_place_votes_select ON saved_place_votes FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY saved_place_votes_insert ON saved_place_votes FOR INSERT
  WITH CHECK (user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY saved_place_votes_delete ON saved_place_votes FOR DELETE
  USING (user_id = (SELECT app_user_id()) OR can_edit_trip(trip_id));

-- Notes: private notes are visible only to their author and are never sent to AI.
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes FORCE ROW LEVEL SECURITY;
CREATE POLICY notes_select ON notes FOR SELECT
  USING (trip_id IN (SELECT visible_trip_ids()) AND (NOT is_private OR author_user_id = (SELECT app_user_id())));
CREATE POLICY notes_insert ON notes FOR INSERT WITH CHECK (can_edit_trip(trip_id) AND author_user_id = (SELECT app_user_id()));
CREATE POLICY notes_update ON notes FOR UPDATE USING (can_edit_trip(trip_id) AND (NOT is_private OR author_user_id = (SELECT app_user_id())));
CREATE POLICY notes_delete ON notes FOR DELETE USING (can_edit_trip(trip_id) AND (NOT is_private OR author_user_id = (SELECT app_user_id())));

-- Runs: members read; an editor starts a run as themselves (queued); a cancel is the one column the API may update (6.1); everything else is the worker's.
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE runs FORCE ROW LEVEL SECURITY;
CREATE POLICY runs_select ON runs FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY runs_insert ON runs FOR INSERT
  WITH CHECK (can_edit_trip(trip_id) AND user_id = (SELECT app_user_id()) AND status = 'queued');
CREATE POLICY runs_update ON runs FOR UPDATE USING (can_edit_trip(trip_id)) WITH CHECK (can_edit_trip(trip_id));

-- The feed and run logs: members read; the API appends feed rows as the acting member; run events are written by workers only.
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log FORCE ROW LEVEL SECURITY;
CREATE POLICY activity_log_select ON activity_log FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));
CREATE POLICY activity_log_insert ON activity_log FOR INSERT
  WITH CHECK (trip_id IN (SELECT visible_trip_ids()) AND actor_user_id = (SELECT app_user_id()));
ALTER TABLE run_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE run_events FORCE ROW LEVEL SECURITY;
CREATE POLICY run_events_select ON run_events FOR SELECT USING (trip_id IN (SELECT visible_trip_ids()));

-- Alerts are personal: the row belongs to the person who is notified, and they must still be on the trip.
ALTER TABLE price_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_alerts FORCE ROW LEVEL SECURITY;
CREATE POLICY price_alerts_all ON price_alerts FOR ALL
  USING (user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()))
  WITH CHECK (user_id = (SELECT app_user_id()) AND trip_id IN (SELECT visible_trip_ids()));

-- Passes belong to a trip, so every member sees that the trip is upgraded; only the purchaser sees the purchase row.
ALTER TABLE trip_passes ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_passes FORCE ROW LEVEL SECURITY;
CREATE POLICY trip_passes_select ON trip_passes FOR SELECT
  USING (trip_id IN (SELECT visible_trip_ids()) OR purchaser_user_id = (SELECT app_user_id()));

-- Imports are personal to the importer. They may outlive the trip (trip_id is SET NULL), so the rule is user_id, not trip membership.
ALTER TABLE trip_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_imports FORCE ROW LEVEL SECURITY;
CREATE POLICY trip_imports_select ON trip_imports FOR SELECT USING (user_id = (SELECT app_user_id()));
CREATE POLICY trip_imports_insert ON trip_imports FOR INSERT
  WITH CHECK (user_id = (SELECT app_user_id()) AND status = 'received' AND reward_granted_at IS NULL AND reward_pass_id IS NULL
              AND (trip_id IS NULL OR can_edit_trip(trip_id)));
-- No UPDATE or DELETE policy: the API changes an import only through advance_trip_import() and set_import_polling() (6.1.1), which check app_user_id() themselves.

-- Referrals: a person sees the rewards they gave or received. Rows are created and changed by the functions in 5.9.
ALTER TABLE referral_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_codes FORCE ROW LEVEL SECURITY;
CREATE POLICY referral_codes_select ON referral_codes FOR SELECT USING (user_id = (SELECT app_user_id()));
ALTER TABLE referral_rewards ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_rewards FORCE ROW LEVEL SECURITY;
CREATE POLICY referral_rewards_select ON referral_rewards FOR SELECT
  USING (referrer_user_id = (SELECT app_user_id()) OR referee_user_id = (SELECT app_user_id()));

-- Public sample trips: the app sees published rows only.
ALTER TABLE sample_trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE sample_trips FORCE ROW LEVEL SECURITY;
CREATE POLICY sample_trips_published ON sample_trips FOR SELECT USING (status = 'published');

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
CREATE POLICY users_self ON users FOR SELECT USING (id = (SELECT app_user_id()));
CREATE POLICY users_update ON users FOR UPDATE USING (id = (SELECT app_user_id())) WITH CHECK (id = (SELECT app_user_id()));

ALTER TABLE people ENABLE ROW LEVEL SECURITY;
ALTER TABLE people FORCE ROW LEVEL SECURITY;
CREATE POLICY people_select ON people FOR SELECT
  USING (owner_user_id = (SELECT app_user_id()) OR linked_user_id = (SELECT app_user_id())
         OR id IN (SELECT person_id FROM trip_people WHERE trip_id IN (SELECT visible_trip_ids())));
CREATE POLICY people_insert ON people FOR INSERT WITH CHECK (owner_user_id = (SELECT app_user_id()));
CREATE POLICY people_update ON people FOR UPDATE USING (owner_user_id = (SELECT app_user_id())) WITH CHECK (owner_user_id = (SELECT app_user_id()));
CREATE POLICY people_delete ON people FOR DELETE USING (owner_user_id = (SELECT app_user_id()));

-- Tables where user_id = caller is the whole rule. The second array lists which commands the API may run.
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT * FROM (VALUES
    ('auth_identities',  'select'),
    ('devices',          'select,insert,update,delete'),
    ('entitlements',     'select'),
    ('ai_usage',         'select'),
    ('credit_ledger',    'select'),
    ('store_transactions','select'),
    ('consents',         'select,insert'),
    ('notifications',    'select,update'),
    ('data_exports',     'select,insert'),
    ('support_tickets',  'select,insert,update'),
    ('idempotency_keys', 'select,insert,update,delete'),
    ('credit_debts',     'select')
  ) AS v(tbl, cmds)
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', r.tbl);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', r.tbl);
    IF r.cmds LIKE '%select%' THEN
      EXECUTE format('CREATE POLICY %I ON %I FOR SELECT USING (user_id = (SELECT app_user_id()))', r.tbl || '_select', r.tbl); END IF;
    IF r.cmds LIKE '%insert%' THEN
      EXECUTE format('CREATE POLICY %I ON %I FOR INSERT WITH CHECK (user_id = (SELECT app_user_id()))', r.tbl || '_insert', r.tbl); END IF;
    IF r.cmds LIKE '%update%' THEN
      EXECUTE format('CREATE POLICY %I ON %I FOR UPDATE USING (user_id = (SELECT app_user_id())) WITH CHECK (user_id = (SELECT app_user_id()))', r.tbl || '_update', r.tbl); END IF;
    IF r.cmds LIKE '%delete%' THEN
      EXECUTE format('CREATE POLICY %I ON %I FOR DELETE USING (user_id = (SELECT app_user_id()))', r.tbl || '_delete', r.tbl); END IF;
  END LOOP;
END $$;

-- Balances: readable by their owner only.
ALTER TABLE credit_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_grants FORCE ROW LEVEL SECURITY;
CREATE POLICY credit_grants_select ON credit_grants FOR SELECT USING (user_id = (SELECT app_user_id()));
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY;
CREATE POLICY subscriptions_select ON subscriptions FOR SELECT USING (user_id = (SELECT app_user_id()));

-- Abuse and attestation tables: RLS on and no policy, so hermi_app is denied even if a grant ever appears. Definer functions and the worker write them.
ALTER TABLE identity_hashes ENABLE ROW LEVEL SECURITY;      ALTER TABLE identity_hashes FORCE ROW LEVEL SECURITY;
ALTER TABLE device_attestations ENABLE ROW LEVEL SECURITY;  ALTER TABLE device_attestations FORCE ROW LEVEL SECURITY;
ALTER TABLE guest_allowances ENABLE ROW LEVEL SECURITY;     ALTER TABLE guest_allowances FORCE ROW LEVEL SECURITY;

-- Reports: anyone signed in may file one and read their own. Moderators use hermi_admin, which bypasses the policies.
ALTER TABLE content_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_reports FORCE ROW LEVEL SECURITY;
-- No INSERT policy: a report is filed through file_content_report() (6.1.1), which inserts as hermi_definer.
CREATE POLICY content_reports_select ON content_reports FOR SELECT USING (reporter_user_id = (SELECT app_user_id()));

ALTER TABLE link_clicks ENABLE ROW LEVEL SECURITY;
ALTER TABLE link_clicks FORCE ROW LEVEL SECURITY;
CREATE POLICY link_clicks_select ON link_clicks FOR SELECT USING (user_id = (SELECT app_user_id()));
CREATE POLICY link_clicks_insert ON link_clicks FOR INSERT WITH CHECK (user_id = (SELECT app_user_id()));
CREATE POLICY link_clicks_update ON link_clicks FOR UPDATE
  USING (user_id = (SELECT app_user_id())) WITH CHECK (user_id = (SELECT app_user_id()));   -- limited to clicked_at, redirect_status and opened_in by the column grant

-- Review fixes. The migration table and the heartbeat view are not tenant data: the ALL TABLES grants must not let the API or the worker rewrite
-- alembic_version, nor let the API write job_heartbeats. The three credit helpers that run as the caller are for the billing service (worker) only;
-- identity_hashes_for is also read by ensure_taster_grant, which runs as hermi_definer.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON alembic_version FROM hermi_app, hermi_worker;
REVOKE INSERT, UPDATE, DELETE ON job_heartbeats FROM hermi_app;
REVOKE EXECUTE ON FUNCTION release_stale_reservations, expire_credit_grants, identity_hashes_for FROM PUBLIC;
GRANT  EXECUTE ON FUNCTION release_stale_reservations, expire_credit_grants, identity_hashes_for TO hermi_worker;
GRANT  EXECUTE ON FUNCTION identity_hashes_for TO hermi_definer;

-- The partitions got table grants from the ALL TABLES grants above. Only the parent is reached by the API (03 section 6.1): clear them again.
DO $$ DECLARE c regclass; BEGIN
  FOR c IN SELECT oid::regclass FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relispartition AND relkind IN ('r', 'p') LOOP
    EXECUTE format('REVOKE ALL ON %s FROM hermi_app', c);
  END LOOP;
END $$;

-- The last statement of 0014 (03 section 6.1).
DO $$ DECLARE f regprocedure; BEGIN
  FOR f IN SELECT p.oid::regprocedure FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace AND p.prosecdef LOOP
    EXECUTE format('ALTER FUNCTION %s OWNER TO hermi_definer', f);
  END LOOP;
END $$;
"""

DOWN = r"""
DO $$ DECLARE r record; BEGIN
  FOR r IN SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public' LOOP
    EXECUTE format('DROP POLICY %I ON %I', r.policyname, r.tablename);
  END LOOP;
  FOR r IN SELECT oid::regclass AS t FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind IN ('r', 'p') AND relrowsecurity LOOP
    EXECUTE format('ALTER TABLE %s NO FORCE ROW LEVEL SECURITY', r.t);
    EXECUTE format('ALTER TABLE %s DISABLE ROW LEVEL SECURITY', r.t);
  END LOOP;
END $$;
DROP VIEW partition_default_rows;
DROP VIEW trip_member_profiles;
DROP FUNCTION clear_my_ai_history();
DROP FUNCTION clear_run_content(uuid);
DROP FUNCTION file_content_report(text, text, text, text);
DROP FUNCTION link_my_traveler(uuid, uuid);
DROP FUNCTION advance_trip_import(uuid, text);
DROP FUNCTION cancel_account_deletion();
DROP FUNCTION request_account_deletion(text);
DROP FUNCTION drop_old_log_partitions(text, integer);
DROP FUNCTION maintain_partitions();
DROP FUNCTION retention_sweep();
DROP FUNCTION purge_trash(interval);
DROP FUNCTION bootstrap_user(text, text, citext, boolean, text);
DROP TRIGGER trg_trips_guard_owner ON trips;
DROP FUNCTION trips_guard_owner();
DROP FUNCTION is_trip_owner(uuid);
DROP FUNCTION can_edit_trip(uuid);
DROP FUNCTION visible_trip_ids();
-- Functions that earlier revisions made as plain functions and this one turned into definer functions.
ALTER FUNCTION reserve_credits(uuid, uuid, integer, ai_action, uuid, text) SECURITY INVOKER RESET search_path;
ALTER FUNCTION settle_credits(uuid, integer, bigint) SECURITY INVOKER RESET search_path;
ALTER FUNCTION ensure_free_monthly_grant(uuid) SECURITY INVOKER RESET search_path;
ALTER FUNCTION ensure_taster_grant(uuid) SECURITY INVOKER RESET search_path;
ALTER FUNCTION ensure_month_partitions(regclass, integer) SECURITY INVOKER RESET search_path;
ALTER FUNCTION drop_old_partitions(regclass, integer) SECURITY INVOKER RESET search_path;
ALTER FUNCTION reserve_credits(uuid, uuid, integer, ai_action, uuid, text) OWNER TO hermi_owner;
ALTER FUNCTION settle_credits(uuid, integer, bigint) OWNER TO hermi_owner;
ALTER FUNCTION ensure_free_monthly_grant(uuid) OWNER TO hermi_owner;
ALTER FUNCTION ensure_taster_grant(uuid) OWNER TO hermi_owner;
ALTER FUNCTION ensure_month_partitions(regclass, integer) OWNER TO hermi_owner;
ALTER FUNCTION drop_old_partitions(regclass, integer) OWNER TO hermi_owner;
DO $$ DECLARE c regclass; BEGIN
  FOR c IN SELECT oid::regclass FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind IN ('r', 'p')
           AND pg_get_userbyid(relowner) = 'hermi_definer' LOOP
    EXECUTE format('ALTER TABLE %s OWNER TO hermi_owner', c);
  END LOOP;
END $$;
-- Grants: back to what 0013 left (nothing on tables and sequences for the four roles, and the EXECUTE grants 0002, 0004 and 0005 gave).
ALTER DEFAULT PRIVILEGES FOR ROLE hermi_owner IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM hermi_worker;
ALTER DEFAULT PRIVILEGES FOR ROLE hermi_owner IN SCHEMA public REVOKE SELECT ON TABLES FROM hermi_definer, hermi_admin;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM hermi_app, hermi_worker, hermi_admin, hermi_definer;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM hermi_app, hermi_worker, hermi_admin, hermi_definer;
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM hermi_app, hermi_worker, hermi_admin;
GRANT EXECUTE ON FUNCTION redeem_trip_invite, transfer_trip_owner, my_provider_spend_micros TO hermi_app;
GRANT EXECUTE ON FUNCTION spend_guest_allowance TO hermi_worker;
GRANT EXECUTE ON FUNCTION release_stale_reservations, expire_credit_grants, identity_hashes_for TO PUBLIC;
REVOKE USAGE ON SCHEMA public FROM hermi_app, hermi_worker, hermi_admin, hermi_definer;
"""


def upgrade() -> None:
    op.execute(UP)


def downgrade() -> None:
    op.execute(DOWN)
