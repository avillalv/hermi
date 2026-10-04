# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-020.2: revision 0014_rls (03 sections 6, 8, 9 and 10): grants, FORCE row-level security, policies, definer functions.

Everything the app can or cannot do is asserted as hermi_api_login. Rows are made with the worker login (TEST_DATABASE_URL_SYSTEM),
never the owner, because the owner is under FORCE too (03 section 6.5).
"""

import os
import uuid
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import APP_URL, MIGRATE_URL, _alembic_cfg, _need_db

from hermi import db

SYSTEM_URL = os.environ.get("TEST_DATABASE_URL_SYSTEM")

# Tables with a trip_id or user_id column that 03 section 6.5 allows to have no RLS (closed by grants).
RLS_ALLOWLIST = {"admin_users", "deletion_requests", "affiliate_conversions", "provider_calls"}
NO_POLICY = {"identity_hashes", "device_attestations", "guest_allowances"}
DEFINER_FUNCTIONS = [  # (signature, search_path pinned, app can execute, worker can execute)
    ("visible_trip_ids()", True, True, True),
    ("can_edit_trip(uuid)", True, True, True),
    ("is_trip_owner(uuid)", True, True, True),
    ("bootstrap_user(text,text,citext,boolean,text)", True, True, False),
    ("purge_trash(interval)", True, False, True),
    ("retention_sweep()", True, False, True),
    ("maintain_partitions()", True, False, True),
    ("drop_old_log_partitions(text,integer)", True, False, True),
    ("ensure_month_partitions(regclass,integer)", True, False, False),
    ("drop_old_partitions(regclass,integer)", True, False, False),
    ("reserve_credits(uuid,uuid,integer,ai_action,uuid,text)", True, True, True),
    ("settle_credits(uuid,integer,bigint)", True, True, True),
    ("ensure_free_monthly_grant(uuid)", True, True, True),
    ("ensure_taster_grant(uuid)", True, True, True),
    ("request_account_deletion(text)", True, True, False),
    ("cancel_account_deletion()", True, True, False),
    ("advance_trip_import(uuid,text)", True, True, False),
    ("link_my_traveler(uuid,uuid)", True, True, False),
    ("file_content_report(text,text,text,text)", True, True, False),
    ("clear_run_content(uuid)", True, True, False),
    ("clear_my_ai_history()", True, True, False),
    ("my_provider_spend_micros(timestamptz)", True, True, False),
]


@pytest.fixture(scope="module")
def migrated():
    _need_db()
    if not SYSTEM_URL:
        msg = "TEST_DATABASE_URL_SYSTEM is not set (npm run test:api loads it from .env)"
        if os.environ.get("CI"):
            pytest.fail(msg)
        pytest.skip(msg)
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return cfg


def _connect(url):
    return psycopg.connect(db.psycopg_url(url), autocommit=True)


@pytest.fixture
def app(migrated):
    with _connect(APP_URL) as c:
        yield c


@pytest.fixture
def sysc(migrated):
    with _connect(SYSTEM_URL) as c:
        yield c


@contextmanager
def as_user(user):
    """One API transaction with app.user_id set, like the real request dependency."""
    with _connect(APP_URL) as c:
        c.autocommit = False
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(user) if user else "",))
        try:
            yield c
        finally:
            c.rollback()


def _user(c, name="U"):
    return c.execute("INSERT INTO users (email, display_name) VALUES (%s, %s) RETURNING id", (f"{uuid.uuid4().hex[:8]}@example.com", name)).fetchone()[0]


def _trip(c, owner):
    return c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)).fetchone()[0]


def _member(c, trip, user, role):
    c.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (trip, user, role))


# --- chain ---------------------------------------------------------------------------------------


def test_chain_is_linear_and_0014_follows_0013():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0014_rls").down_revision == "0013_notifications_samples"
    assert s.get_heads() == ["0014_rls"]


# --- RLS on every tenant table ---------------------------------------------------------------------


def test_every_trip_or_user_table_has_rls_enabled_and_forced(sysc):
    rows = sysc.execute(
        """
        SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
          FROM pg_class c
         WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p') AND NOT c.relispartition
           AND EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = c.oid AND a.attname IN ('trip_id', 'user_id') AND NOT a.attisdropped)
        """
    ).fetchall()
    assert len(rows) > 40
    bad = [r[0] for r in rows if r[0] not in RLS_ALLOWLIST and not (r[1] and r[2])]
    assert bad == []


def test_named_tables_are_forced_and_have_policies(sysc):
    forced = {r[0] for r in sysc.execute("SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind IN ('r', 'p') AND relrowsecurity AND relforcerowsecurity")}
    for t in ("users", "people", "sample_trips", "link_clicks", "content_reports", "credit_grants", "subscriptions", "referral_codes", "runs", "run_events", "notes",
              "lodging_votes", "saved_place_votes", "price_alerts", "trip_passes", "trip_imports", "activity_log", "itinerary_items", "trips", "trip_members",
              *NO_POLICY):
        assert t in forced, t
    pol = {}
    for table, name in sysc.execute("SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public'"):
        pol.setdefault(table, set()).add(name)
    for t in forced - NO_POLICY:
        assert pol.get(t), f"{t} has RLS but no policy"
    for t in NO_POLICY:
        assert t not in pol
    assert pol["trips"] == {"trips_select", "trips_insert", "trips_update", "trips_delete"}
    assert pol["trip_members"] == {"trip_members_select", "trip_members_insert", "trip_members_update", "trip_members_delete"}
    assert pol["itinerary_days"] == {"itinerary_days_select", "itinerary_days_insert", "itinerary_days_update", "itinerary_days_delete"}
    assert pol["link_clicks"] == {"link_clicks_select", "link_clicks_insert", "link_clicks_update"}
    assert pol["content_reports"] == {"content_reports_select"}
    assert pol["trip_imports"] == {"trip_imports_select", "trip_imports_insert"}
    assert pol["price_alerts"] == {"price_alerts_all"}
    assert pol["devices"] == {"devices_select", "devices_insert", "devices_update", "devices_delete"}


# --- grants (6.1) ----------------------------------------------------------------------------------


def _can(c, role, table, priv):
    return c.execute("SELECT has_table_privilege(%s, %s, %s)", (role, table, priv)).fetchone()[0]


def test_app_grants(app):
    for t in ("trips", "itinerary_days", "people", "plans", "airports", "credit_ledger"):
        assert _can(app, "hermi_api_login", t, "SELECT"), t
    assert _can(app, "hermi_api_login", "trips", "INSERT") and _can(app, "hermi_api_login", "trips", "DELETE")
    for t in ("airports", "fx_rates", "plans", "feature_flags", "sample_trips", "credit_ledger", "credit_grants", "referral_rewards", "notifications"):
        assert not _can(app, "hermi_api_login", t, "INSERT"), t
    for t in ("runs", "trip_imports"):  # the API inserts these but never updates or deletes them whole
        assert _can(app, "hermi_api_login", t, "INSERT") and not _can(app, "hermi_api_login", t, "DELETE"), t
    for t in ("identity_hashes", "device_attestations", "guest_allowances", "admin_users", "webhook_events", "affiliate_conversions", "affiliate_payouts",
              "deletion_requests", "provider_call_rollups", "provider_calls", "revenue_by_month", "booked_fare_drops"):
        assert not _can(app, "hermi_api_login", t, "SELECT"), t
    assert _can(app, "hermi_api_login", "provider_calls", "INSERT")
    assert _can(app, "hermi_api_login", "rate_limit_counters", "DELETE")
    assert _can(app, "hermi_api_login", "audit_log", "INSERT")
    for p in ("SELECT", "UPDATE", "DELETE", "TRUNCATE"):
        assert not _can(app, "hermi_api_login", "audit_log", p), p
    assert not _can(app, "hermi_api_login", "users", "UPDATE")
    col = lambda t, c: app.execute("SELECT has_column_privilege('hermi_api_login', %s, %s, 'UPDATE')", (t, c)).fetchone()[0]  # noqa: E731
    assert col("users", "display_name") and not col("users", "status")
    assert col("link_clicks", "clicked_at") and col("link_clicks", "opened_in") and not col("link_clicks", "user_id")
    assert col("runs", "cancel_requested") and not col("runs", "status")
    assert col("notifications", "read_at") and col("plan_verifications", "status") and col("plan_verification_items", "selected")
    assert not _can(app, "hermi_api_login", "link_clicks", "DELETE")
    assert _can(app, "hermi_api_login", "trip_member_profiles", "SELECT")
    assert not _can(app, "hermi_api_login", "partition_default_rows", "SELECT")


def test_no_app_grant_on_any_partition(app):
    parts = [r[0] for r in app.execute("SELECT c.relname FROM pg_class c WHERE c.relispartition AND c.relnamespace = 'public'::regnamespace")]
    assert any(p.startswith("link_clicks_") for p in parts)
    for p in parts:
        for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            assert not _can(app, "hermi_api_login", p, priv), (p, priv)


def test_worker_and_admin_grants(sysc):
    assert _can(sysc, "hermi_worker_login", "trips", "DELETE")
    assert _can(sysc, "hermi_worker_login", "audit_log", "INSERT") and _can(sysc, "hermi_worker_login", "audit_log", "SELECT")
    for p in ("UPDATE", "DELETE", "TRUNCATE"):
        assert not _can(sysc, "hermi_worker_login", "audit_log", p), p
        assert not _can(sysc, "hermi_admin_login", "audit_log", p), p
    assert not _can(sysc, "hermi_worker_login", "credit_ledger", "TRUNCATE")
    assert _can(sysc, "hermi_admin_login", "trips", "SELECT") and not _can(sysc, "hermi_admin_login", "trips", "INSERT")
    assert _can(sysc, "hermi_admin_login", "feature_flags", "UPDATE") and _can(sysc, "hermi_admin_login", "affiliate_conversions", "UPDATE")
    assert not _can(sysc, "hermi_admin_login", "affiliate_conversions", "DELETE")
    assert _can(sysc, "hermi_admin_login", "partition_default_rows", "SELECT") and _can(sysc, "hermi_worker_login", "partition_default_rows", "SELECT")
    assert _can(sysc, "hermi_definer", "trips", "DELETE") and _can(sysc, "hermi_definer", "provider_calls", "SELECT")


# --- definer functions ---------------------------------------------------------------------------


@pytest.mark.parametrize("sig,pinned,app_exec,worker_exec", DEFINER_FUNCTIONS)
def test_definer_function(sysc, sig, pinned, app_exec, worker_exec):
    name = sig.split("(")[0]
    row = sysc.execute(
        "SELECT p.prosecdef, pg_get_userbyid(p.proowner), p.proconfig, p.oid FROM pg_proc p WHERE p.oid = to_regprocedure(%s)", (sig,)
    ).fetchone()
    assert row, sig
    assert row[0] is True and row[1] == "hermi_definer", sig
    assert pinned and any(x.startswith("search_path=public") and "pg_temp" in x for x in row[2] or []), sig
    can = lambda role: sysc.execute("SELECT has_function_privilege(%s, %s::oid, 'EXECUTE')", (role, row[3])).fetchone()[0]  # noqa: E731
    assert can("hermi_api_login") is app_exec, (name, "app")
    assert can("hermi_worker_login") is worker_exec or name in ("visible_trip_ids", "can_edit_trip", "is_trip_owner"), (name, "worker")
    if name in ("ensure_month_partitions", "drop_old_partitions", "retention_sweep", "purge_trash"):
        assert sysc.execute("SELECT has_function_privilege('public', %s::oid, 'EXECUTE')", (row[3],)).fetchone()[0] is False


def test_every_security_definer_function_is_owned_by_hermi_definer(sysc):
    rows = sysc.execute("SELECT p.proname, pg_get_userbyid(p.proowner) FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace AND p.prosecdef").fetchall()
    assert len(rows) >= 25
    assert [r for r in rows if r[1] != "hermi_definer"] == []


def test_procrastinate_defer_is_callable_by_app(sysc):
    assert sysc.execute("SELECT has_function_privilege('hermi_api_login', 'procrastinate_defer_jobs_v1(procrastinate_job_to_defer_v1[])'::regprocedure, 'EXECUTE')").fetchone()[0]


# --- retention and partition functions -----------------------------------------------------------


def test_app_cannot_run_worker_functions(app):
    for sql in ("SELECT retention_sweep()", "SELECT purge_trash()", "SELECT maintain_partitions()", "SELECT drop_old_log_partitions('run_events', 1)"):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            app.execute(sql)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app.execute("SELECT * FROM partition_default_rows")


def test_partition_functions_as_worker(sysc):
    assert sysc.execute("SELECT maintain_partitions()").fetchone()[0] == 0  # 0005 and 0008 already made them
    assert sysc.execute("SELECT drop_old_log_partitions('run_events', 1)").fetchone()[0] == 0
    assert sysc.execute("SELECT drop_old_log_partitions('link_clicks', 25)").fetchone()[0] == 0
    with pytest.raises(psycopg.errors.InvalidParameterValue):
        sysc.execute("SELECT drop_old_log_partitions('trips', 1)")
    assert sorted(sysc.execute("SELECT parent, row_count FROM partition_default_rows").fetchall()) == [("link_clicks", 0), ("provider_calls", 0), ("run_events", 0)]


def test_maintain_partitions_creates_a_missing_month_and_drop_removes_old(sysc):
    sysc.execute("SELECT drop_old_log_partitions('provider_calls', 0)")  # keep the current month onward: the previous month goes
    n = sysc.execute("SELECT maintain_partitions()").fetchone()[0]
    assert n >= 1  # the previous month came back
    assert sysc.execute("SELECT maintain_partitions()").fetchone()[0] == 0


def test_purge_trash_and_retention_sweep(sysc):
    u = _user(sysc)
    old, fresh, live = _trip(sysc, u), _trip(sysc, u), _trip(sysc, u)
    sysc.execute("UPDATE trips SET deleted_at = now() - interval '31 days' WHERE id = %s", (old,))
    sysc.execute("UPDATE trips SET deleted_at = now() - interval '2 days' WHERE id = %s", (fresh,))
    assert sysc.execute("SELECT purge_trash()").fetchone()[0] == 1
    left = {r[0] for r in sysc.execute("SELECT id FROM trips WHERE owner_user_id = %s", (u,))}
    assert left == {fresh, live}
    # retention_sweep: audit_log row past its class goes, a row inside it stays (03 section 6.5, test 6).
    sysc.execute("INSERT INTO audit_log (actor_type, action, retention_class, created_at) VALUES ('system', 't.old', 'standard', now() - interval '14 months')")
    sysc.execute("INSERT INTO audit_log (actor_type, action, retention_class, created_at) VALUES ('system', 't.ext', 'extended', now() - interval '14 months')")
    sysc.execute("INSERT INTO audit_log (actor_type, action, retention_class, created_at) VALUES ('system', 't.new', 'standard', now() - interval '1 month')")
    sysc.execute("INSERT INTO notifications (user_id, kind, dedupe_key, title, created_at) VALUES (%s, 'price_drop', 'k', 'x', now() - interval '91 days')", (u,))
    assert sysc.execute("SELECT retention_sweep()").fetchone()[0] >= 2
    acts = {r[0] for r in sysc.execute("SELECT action FROM audit_log WHERE action LIKE 't.%'")}
    assert acts == {"t.ext", "t.new"}
    assert sysc.execute("SELECT count(*) FROM notifications WHERE user_id = %s", (u,)).fetchone() == (0,)
    assert sysc.execute("SELECT retention_sweep()").fetchone()[0] == 0  # idempotent
    with pytest.raises(psycopg.errors.InsufficientPrivilege):  # the worker has no DELETE on audit_log; only the sweep deletes
        sysc.execute("DELETE FROM audit_log WHERE action = 't.new'")


# --- behavior as hermi_api_login ------------------------------------------------------------------


def test_startup_check_passes_for_api_login(app):
    assert app.execute(
        """SELECT r.rolsuper OR r.rolbypassrls OR EXISTS (SELECT 1 FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p')
                     AND (c.relowner = r.oid OR pg_has_role(r.oid, c.relowner, 'member'))) FROM pg_roles r WHERE r.rolname = current_user"""
    ).fetchone() == (False,)


def test_tenant_isolation_and_roles(sysc):
    a, b, viewer = _user(sysc, "Ann"), _user(sysc, "Bob"), _user(sysc, "Vic")
    ta, tb = _trip(sysc, a), _trip(sysc, b)
    _member(sysc, ta, viewer, "viewer")
    sysc.execute("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, '2027-05-01')", (ta,))
    sysc.execute("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, '2027-05-01')", (tb,))

    with as_user(a) as c:
        assert {r[0] for r in c.execute("SELECT id FROM trips")} == {ta}
        assert c.execute("SELECT count(*) FROM itinerary_days").fetchone() == (1,)
        assert c.execute("SELECT count(*) FROM trip_members WHERE trip_id = %s", (tb,)).fetchone() == (0,)
        # B's trip cannot be changed, deleted or written into.
        assert c.execute("UPDATE trips SET name = 'x' WHERE id = %s", (tb,)).rowcount == 0
        assert c.execute("DELETE FROM trips WHERE id = %s", (tb,)).rowcount == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, '2027-05-02')", (tb,))
        c.rollback()
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(a),))
        # A new trip must be owned by the caller, and the owner member row appears.
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD')", (b,))
        c.rollback()
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(a),))
        mine = c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'Mine', 'USD') RETURNING id", (a,)).fetchone()[0]
        assert c.execute("SELECT role FROM trip_members WHERE trip_id = %s AND user_id = %s", (mine, a)).fetchone() == ("owner",)

    with as_user(viewer) as c:  # a viewer reads but never writes
        assert {r[0] for r in c.execute("SELECT id FROM trips")} == {ta}
        assert c.execute("SELECT count(*) FROM itinerary_days").fetchone() == (1,)
        assert c.execute("UPDATE trips SET name = 'x' WHERE id = %s", (ta,)).rowcount == 0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, '2027-05-03')", (ta,))

    with as_user(None) as c:  # no user: nothing visible
        assert c.execute("SELECT count(*) FROM trips").fetchone() == (0,)
        assert c.execute("SELECT count(*) FROM users").fetchone() == (0,)

    with as_user(a) as c:  # users: only your own row, and only the profile columns
        assert {r[0] for r in c.execute("SELECT id FROM users")} == {a}
        assert c.execute("UPDATE users SET display_name = 'Anna' WHERE id = %s", (a,)).rowcount == 1
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("UPDATE users SET status = 'suspended' WHERE id = %s", (a,))


def test_trip_member_profiles_show_co_members_display_names_only(sysc):
    a, b, outsider = _user(sysc, "Ann"), _user(sysc, "Bob"), _user(sysc, "Zed")
    ta, tz = _trip(sysc, a), _trip(sysc, outsider)
    _member(sysc, ta, b, "editor")
    with as_user(b) as c:
        rows = c.execute("SELECT trip_id, user_id, role, display_name FROM trip_member_profiles").fetchall()
        assert {(r[0], r[1], r[3]) for r in rows} == {(ta, a, "Ann"), (ta, b, "Bob")}
        assert all(r[0] != tz for r in rows)
        assert [d[0] for d in c.execute("SELECT * FROM trip_member_profiles").description] == ["trip_id", "user_id", "role", "display_name"]
        assert c.execute("SELECT count(*) FROM users WHERE id = %s", (a,)).fetchone() == (0,)  # a co-member's account row is not readable, only the view


def test_abuse_tables_are_closed_to_the_app(sysc):
    with as_user(_user(sysc)) as c:
        for t in ("identity_hashes", "device_attestations", "guest_allowances"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                c.execute(f"SELECT 1 FROM {t}")
            c.rollback()
            c.execute("SELECT set_config('app.user_id', '', true)")


def test_bootstrap_user_is_idempotent_and_app_callable(app, sysc):
    sysc.execute("INSERT INTO plans (code, kind, name) VALUES ('free', 'tier', 'Free') ON CONFLICT DO NOTHING")  # 0015_seed adds the real row
    sub = uuid.uuid4().hex
    email = f"{sub[:8]}@example.com"
    r1 = app.execute("SELECT * FROM bootstrap_user('google', %s, %s, false, 'Zoe')", (sub, email)).fetchone()
    r2 = app.execute("SELECT * FROM bootstrap_user('google', %s, %s, false, 'Zoe')", (sub, email)).fetchone()
    assert r1[1] is True and r2 == (r1[0], False)
    with as_user(r1[0]) as c:
        assert c.execute("SELECT display_name FROM users").fetchone() == ("Zoe",)
        assert c.execute("SELECT is_self FROM people").fetchone() == (True,)


def test_account_deletion_functions(sysc):
    u = _user(sysc)
    sysc.execute("INSERT INTO devices (user_id, platform) VALUES (%s, 'web')", (u,))
    with as_user(u) as c:
        rid = c.execute("SELECT request_account_deletion('changed my mind')").fetchone()[0]
        assert c.execute("SELECT request_account_deletion('again')").fetchone()[0] == rid  # idempotent
        c.commit()
    assert sysc.execute("SELECT status FROM users WHERE id = %s", (u,)).fetchone() == ("pending_deletion",)
    assert sysc.execute("SELECT count(*) FROM devices WHERE user_id = %s AND revoked_at IS NULL", (u,)).fetchone() == (0,)
    with as_user(u) as c:
        assert c.execute("SELECT cancel_account_deletion()").fetchone() == (True,)
        c.commit()
    assert sysc.execute("SELECT status FROM users WHERE id = %s", (u,)).fetchone() == ("active",)
    assert sysc.execute("SELECT status FROM deletion_requests WHERE user_id = %s", (u,)).fetchone() == ("cancelled",)
    with as_user(None) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute("SELECT request_account_deletion(NULL)")


def test_clear_run_content_and_ai_history(sysc):
    a, editor, other = _user(sysc), _user(sysc), _user(sysc)
    t = _trip(sysc, a)
    _member(sysc, t, editor, "editor")
    r = sysc.execute("INSERT INTO runs (trip_id, user_id, kind, prompt, report) VALUES (%s, %s, 'explain', 'p', '{}'::jsonb) RETURNING id", (t, editor)).fetchone()[0]
    with as_user(other) as c:
        assert c.execute("SELECT clear_run_content(%s)", (r,)).fetchone() == (False,)
    with as_user(a) as c:  # the trip owner may clear a member's run
        assert c.execute("SELECT clear_run_content(%s)", (r,)).fetchone() == (True,)
        c.commit()
    assert sysc.execute("SELECT prompt, report FROM runs WHERE id = %s", (r,)).fetchone() == (None, None)
    sysc.execute("UPDATE runs SET prompt = 'again', report = '{}'::jsonb WHERE id = %s", (r,))
    with as_user(editor) as c:
        assert c.execute("SELECT clear_my_ai_history()").fetchone() == (1,)
        c.commit()
    assert sysc.execute("SELECT prompt, report FROM runs WHERE id = %s", (r,)).fetchone() == (None, None)


def test_file_content_report_flags_cache_at_three_reporters(sysc):
    key = uuid.uuid4().hex + uuid.uuid4().hex
    sysc.execute(
        "INSERT INTO shared_research_cache (key, kind, provider, params, response, expires_at, stale_until) VALUES (%s, 'destination_brief', 'fake', '{}', '{}', now() + interval '1 day', now() + interval '2 days')",
        (key,),
    )
    users = [_user(sysc) for _ in range(3)]
    for i, u in enumerate(users):
        with as_user(u) as c:
            c.execute("SELECT file_content_report('research_cache', %s, 'wrong_info', 'bad')", (key,))
            c.commit()
        flagged, count, fresh = sysc.execute("SELECT flagged_at IS NOT NULL, report_count, expires_at <= now() FROM shared_research_cache WHERE key = %s", (key,)).fetchone()
        assert (flagged, count, fresh) == (i == 2, i + 1, True)
    assert sysc.execute("SELECT count(*) FROM content_reports WHERE cache_key = %s", (key,)).fetchone() == (3,)
    with as_user(users[0]) as c:
        assert c.execute("SELECT count(*) FROM content_reports").fetchone() == (1,)  # only their own
        with pytest.raises(psycopg.errors.InvalidParameterValue):
            c.execute("SELECT file_content_report('bogus', 'x', 'spam', '')")


def test_advance_trip_import_verbs(sysc):
    u, other = _user(sysc), _user(sysc)
    imp = sysc.execute("INSERT INTO trip_imports (user_id, source, status, preview) VALUES (%s, 'ics_file', 'review', '{}'::jsonb) RETURNING id", (u,)).fetchone()[0]
    with as_user(other) as c, pytest.raises(psycopg.errors.NoDataFound):
        c.execute("SELECT advance_trip_import(%s, 'confirm')", (imp,))
    with as_user(u) as c:
        with pytest.raises(psycopg.errors.InvalidParameterValue):
            c.execute("SELECT advance_trip_import(%s, 'nonsense')", (imp,))
        c.rollback()
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(u),))
        with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):
            c.execute("SELECT advance_trip_import(%s, 'confirm_changes')", (imp,))
        c.rollback()
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(u),))
        assert c.execute("SELECT advance_trip_import(%s, 'confirm')", (imp,)).fetchone() == ("applied",)
        c.commit()
    assert sysc.execute("SELECT status, preview, completed_at IS NOT NULL FROM trip_imports WHERE id = %s", (imp,)).fetchone() == ("applied", None, True)
    d = sysc.execute("INSERT INTO trip_imports (user_id, source, status, preview) VALUES (%s, 'ics_file', 'review', '{}'::jsonb) RETURNING id", (u,)).fetchone()[0]
    with as_user(u) as c:
        assert c.execute("SELECT advance_trip_import(%s, 'discard')", (d,)).fetchone() == ("discarded",)
        c.commit()
    assert sysc.execute("SELECT status, preview FROM trip_imports WHERE id = %s", (d,)).fetchone() == ("discarded", None)


def test_link_my_traveler(sysc):
    owner, me = _user(sysc), _user(sysc)
    t = _trip(sysc, owner)
    _member(sysc, t, me, "editor")
    p = sysc.execute("INSERT INTO people (owner_user_id, name) VALUES (%s, 'Mo') RETURNING id", (owner,)).fetchone()[0]
    sysc.execute("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (t, p))
    stranger = _user(sysc)
    with as_user(stranger) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute("SELECT link_my_traveler(%s, %s)", (t, p))
    with as_user(me) as c:
        assert c.execute("SELECT link_my_traveler(%s, %s)", (t, p)).fetchone() == (True,)
        c.commit()
    assert sysc.execute("SELECT linked_user_id FROM people WHERE id = %s", (p,)).fetchone() == (me,)


def test_downgrade_removes_0014_and_upgrade_restores_it(migrated, sysc):
    command.downgrade(migrated, "0013_notifications_samples")
    assert sysc.execute("SELECT to_regclass('trip_member_profiles')").fetchone() == (None,)
    assert sysc.execute("SELECT count(*) FROM pg_policies WHERE schemaname = 'public'").fetchone() == (0,)
    assert sysc.execute("SELECT count(*) FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relrowsecurity").fetchone() == (0,)
    assert sysc.execute("SELECT to_regprocedure('retention_sweep()')").fetchone() == (None,)
    command.upgrade(migrated, "head")
    assert sysc.execute("SELECT to_regclass('trip_member_profiles')").fetchone()[0]
