# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-020.2 review: tenant isolation for every forced table, the 6.1.1 functions under the real roles, and the 6.5 item 2 migration check.

Rows are made with the worker login (TEST_DATABASE_URL_SYSTEM); every claim about what a tenant can or cannot do is made as hermi_api_login.
"""

import hashlib
import re
import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from sqlalchemy import create_engine
from tests.test_migrations import APP_URL, MIGRATE_URL, _alembic_cfg, _need_db
from tests.test_migrations_rls import (
    NO_POLICY,
    SYSTEM_URL,
    _connect,
    _member,
    _trip,
    _user,
    as_user,
)

from hermi import db

VERSIONS = Path(__file__).resolve().parents[1] / "hermi/migrations/versions"
TOKEN = lambda: hashlib.sha256(uuid.uuid4().bytes).digest()  # noqa: E731


@pytest.fixture(scope="module")
def sysm():
    _need_db()
    if not SYSTEM_URL:
        pytest.skip("TEST_DATABASE_URL_SYSTEM is not set")
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with _connect(SYSTEM_URL) as c:
        # 0015_seed adds the real plan rows; these tests insert the few they need.
        c.execute("INSERT INTO plans (code, kind, name, duration_days, credits_granted, credits_valid_days) VALUES ('trip_pass', 'pass', 'Trip Pass', 90, 40, 90) ON CONFLICT DO NOTHING")
        c.execute("INSERT INTO plans (code, kind, name, monthly_credits, limits) VALUES ('free', 'tier', 'Free', 12, '{\"taster_agent_runs\": 1}') ON CONFLICT DO NOTHING")
        yield c


def _flags(c):
    c.execute("DELETE FROM feature_flags")
    c.execute(
        "INSERT INTO feature_flags (key, kind, enabled, rules) VALUES "
        "('setting_import_reward', 'setting', true, '{\"min_items_applied\": 3}'), "
        "('setting_referral_credits', 'setting', true, '{\"referrer\": 20, \"referee\": 20}')"
    )


def _one(c, sql, params=()):
    return c.execute(sql, params).fetchone()[0]


# --- grants that are not tenant data ----------------------------------------------------------------


def test_migration_table_and_heartbeat_view_are_not_writable_by_the_app(sysm):
    can = lambda role, t, p: _one(sysm, "SELECT has_table_privilege(%s, %s, %s)", (role, t, p))  # noqa: E731
    for role in ("hermi_api_login", "hermi_worker_login"):
        assert can(role, "alembic_version", "SELECT") is True
        for p in ("INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            assert can(role, "alembic_version", p) is False, (role, p)
    for p in ("INSERT", "UPDATE", "DELETE"):
        assert can("hermi_api_login", "job_heartbeats", p) is False, p
    assert can("hermi_api_login", "job_heartbeats", "SELECT") is True
    assert can("hermi_worker_login", "job_heartbeats", "INSERT") is True  # the worker keeps write


def test_credit_helpers_are_worker_only(sysm):
    for sig in ("release_stale_reservations(interval,interval)", "expire_credit_grants()", "identity_hashes_for(uuid)"):
        oid = _one(sysm, "SELECT to_regprocedure(%s)::oid", (sig,))
        ex = lambda role, o=oid: _one(sysm, "SELECT has_function_privilege(%s, %s::oid, 'EXECUTE')", (role, o))  # noqa: E731
        assert ex("hermi_worker_login") and not ex("hermi_api_login") and not ex("public"), sig
    assert _one(sysm, "SELECT has_function_privilege('hermi_definer', 'identity_hashes_for(uuid)'::regprocedure, 'EXECUTE')")


# --- the startup check (6.5) ------------------------------------------------------------------------


def test_startup_check_refuses_a_member_of_the_definer(sysm):
    with create_engine(db.sqlalchemy_url(APP_URL)).connect() as c:
        db.assert_app_login_is_safe(c)
    with create_engine(db.sqlalchemy_url(MIGRATE_URL)).connect() as c:
        c.exec_driver_sql("SET ROLE hermi_definer")  # owner of the partitioned parents; the migrate login is a member through hermi_owner
        assert c.exec_driver_sql("SELECT current_user").scalar() == "hermi_definer"
        with pytest.raises(db.MigrationError, match="app connection"):
            db.assert_app_login_is_safe(c)
    with create_engine(db.sqlalchemy_url(SYSTEM_URL)).connect() as c:  # BYPASSRLS
        with pytest.raises(db.MigrationError):
            db.assert_app_login_is_safe(c)


# --- tenant isolation over every forced table ----------------------------------------------------------


def _seeders(x, k):
    """table -> (sql, params). k holds tenant A's ids; x is a fresh token so repeated calls never collide."""
    a, ta = k["a"], k["ta"]
    return {
        "activity_log": ("INSERT INTO activity_log (trip_id, actor_user_id, verb, entity_type) VALUES (%s, %s, 'created', 'trip')", (ta, a)),
        "ai_usage": ("INSERT INTO ai_usage (user_id, trip_id, action, idempotency_key) VALUES (%s, %s, 'research', %s)", (a, ta, x)),
        "auth_identities": ("INSERT INTO auth_identities (user_id, provider, subject) VALUES (%s, 'email', %s)", (a, x)),
        "checklist_items": ("INSERT INTO checklist_items (trip_id, kind, source, title) VALUES (%s, 'custom', 'user', 'Pack')", (ta,)),
        "chosen_flights": ("INSERT INTO chosen_flights (trip_id, route_id, origin, destination, depart_date, price_total_minor, currency, source, observed_at) VALUES (%s, %s, 'LIS', 'JFK', '2027-05-03', 100, 'EUR', 'manual', now())", (ta, k["route"])),
        "consents": ("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'terms', %s, true)", (a, x)),
        "content_reports": ("INSERT INTO content_reports (reporter_user_id, target_type, cache_key, reason) VALUES (%s, 'research_cache', %s, 'spam')", (a, (x * 7)[:64])),
        "credit_debts": ("INSERT INTO credit_debts (user_id, amount) VALUES (%s, 1)", (a,)),
        "credit_grants": ("INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'promo', 1, 1)", (a,)),
        "credit_ledger": ("INSERT INTO credit_ledger (user_id, entry_type, delta) VALUES (%s, 'grant', 1)", (a,)),
        "data_exports": ("INSERT INTO data_exports (user_id) VALUES (%s)", (a,)),
        "device_attestations": ("INSERT INTO device_attestations (key_id, public_key, environment) VALUES (%s, '\\x00', 'development')", (x,)),
        "devices": ("INSERT INTO devices (user_id, platform) VALUES (%s, 'web')", (a,)),
        "entitlements": ("INSERT INTO entitlements (user_id) VALUES (%s)", (a,)),
        "flight_routes": ("INSERT INTO flight_routes (trip_id, origin_codes, destination_codes, depart_from, depart_to, return_from, return_to) VALUES (%s, '{LIS}', '{JFK}', '2027-05-01', '2027-05-10', '2027-05-20', '2027-05-25')", (ta,)),
        "guest_allowances": ("INSERT INTO guest_allowances (key_id, period_key) VALUES (%s, '2027-01')", (k["attest"],)),
        "idempotency_keys": ("INSERT INTO idempotency_keys (user_id, key, method, path, request_hash) VALUES (%s, %s, 'POST', '/x', %s)", (a, x, "0" * 64)),
        "identity_hashes": ("INSERT INTO identity_hashes (hash, kind) VALUES (%s, 'taster')", (TOKEN(),)),
        "itinerary_days": ("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, %s)", (ta, f"2027-0{int(x[:1], 16) % 9 + 1}-1{int(x[1:2], 16) % 9}")),
        "itinerary_items": ("INSERT INTO itinerary_items (trip_id, title) VALUES (%s, 'Visit')", (ta,)),
        "legacy_claims": ("INSERT INTO legacy_claims (user_id, token_hash) VALUES (%s, %s)", (a, TOKEN())),
        "link_clicks": ("INSERT INTO link_clicks (click_id, program_id, surface, destination_url, user_id, trip_id) VALUES (%s, %s, 'checklist', 'https://x.test/', %s, %s)", (x, k["program"], a, ta)),
        "lodging_options": ("INSERT INTO lodging_options (trip_id, title, added_via) VALUES (%s, 'Flat', 'manual')", (ta,)),
        "lodging_votes": ("INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)", (k["lodging"], ta, k["person"], a)),
        "notes": ("INSERT INTO notes (trip_id, author_user_id) VALUES (%s, %s)", (ta, a)),
        "notifications": ("INSERT INTO notifications (user_id, kind, dedupe_key, title) VALUES (%s, 'trip_invite', %s, 'x')", (a, x)),
        "notification_preferences": ("INSERT INTO notification_preferences (user_id) VALUES (%s)", (a,)),
        "trip_notification_mutes": ("INSERT INTO trip_notification_mutes (trip_id, user_id) VALUES (%s, %s)", (ta, a)),
        "people": ("INSERT INTO people (owner_user_id, name) VALUES (%s, 'P')", (a,)),
        "plan_verification_items": ("INSERT INTO plan_verification_items (verification_id, trip_id, position, name) VALUES (%s, %s, %s, 'n')", (k["ver"], ta, int(x[:4], 16) % 30000)),
        "plan_verifications": ("INSERT INTO plan_verifications (trip_id, user_id) VALUES (%s, %s)", (ta, a)),
        "price_alerts": ("INSERT INTO price_alerts (trip_id, route_id, user_id, threshold_minor, currency) VALUES (%s, %s, %s, 5, 'EUR')", (ta, k["route"], a)),
        "referral_codes": ("INSERT INTO referral_codes (user_id, code) VALUES (%s, %s)", (a, x[:8].upper().replace("0", "A").replace("1", "B"))),
        "referral_rewards": ("INSERT INTO referral_rewards (code, referrer_user_id, referee_user_id) VALUES (%s, %s, %s)", (k["code"], k["c"], a)),
        "run_events": ("INSERT INTO run_events (run_id, trip_id, seq, type, summary) VALUES (%s, %s, %s, 'info', 'hi')", (k["run"], ta, int(x[:5], 16))),
        "runs": ("INSERT INTO runs (trip_id, user_id, kind) VALUES (%s, %s, 'explain')", (ta, a)),
        "sample_trips": ("INSERT INTO sample_trips (slug, trip_id, title) VALUES (%s, %s, 'S')", ("s" + x, ta)),
        "saved_place_votes": ("INSERT INTO saved_place_votes (saved_place_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)", (k["place"], ta, k["person"], a)),
        "saved_places": ("INSERT INTO saved_places (trip_id, place_provider, place_id, name) VALUES (%s, 'manual', %s, 'P')", (ta, x)),
        "store_transactions": ("INSERT INTO store_transactions (store, store_transaction_id, kind, purchased_at, user_id) VALUES ('apple', %s, 'pass', now(), %s)", (x, a)),
        "subscriptions": ("INSERT INTO subscriptions (user_id, store, original_transaction_id, plan_code, status) VALUES (%s, 'apple', %s, 'free', 'active')", (a, x)),
        "support_tickets": ("INSERT INTO support_tickets (user_id, subject) VALUES (%s, 's')", (a,)),
        "trip_destinations": ("INSERT INTO trip_destinations (trip_id, position, name, lat, lon) VALUES (%s, %s, 'Porto', 41, -8)", (ta, int(x[:4], 16) % 30000)),
        "trip_fare_links": ("INSERT INTO trip_fare_links (trip_id, route_id, observation_id) VALUES (%s, %s, %s)", (ta, k["route"], k["obs"])),
        "trip_imports": ("INSERT INTO trip_imports (user_id, source) VALUES (%s, 'ics_file')", (a,)),
        "trip_invites": ("INSERT INTO trip_invites (trip_id, token_hash) VALUES (%s, %s)", (ta, TOKEN())),
        "trip_members": ("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (ta, k["c"])),
        "trip_passes": ("INSERT INTO trip_passes (trip_id, purchaser_user_id, plan_code, source, expires_at) VALUES (%s, %s, 'trip_pass', 'admin', now() + interval '30 days')", (ta, a)),
        "trip_people": ("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (ta, k["person2"])),
        "trip_share_links": ("INSERT INTO trip_share_links (trip_id, token_hash) VALUES (%s, %s)", (ta, TOKEN())),
        "trips": ("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD')", (a,)),
        "users": ("INSERT INTO users (email) VALUES (%s)", (f"{x}@example.com",)),
    }


# Tables whose rows the API legitimately cannot see at all, with the reason.
A_BLIND = {
    "identity_hashes": "closed to the app by grants and RLS with no policy (03 6.1)",
    "device_attestations": "closed to the app by grants and RLS with no policy (03 6.1)",
    "guest_allowances": "closed to the app by grants and RLS with no policy (03 6.1)",
    "legacy_claims": "closed to the app by grants and RLS with no policy (0023); definer functions only",
    "sample_trips": "a draft sample: the app sees published rows only, and B would see those too",
}
B_SEES = {"users": 1}  # B always sees its own users row


@pytest.fixture(scope="module")
def tenants(sysm):
    c = sysm
    a, b, other = _user(c, "Ann"), _user(c, "Bea"), _user(c, "Cy")
    ta = _trip(c, a)
    k = {"a": a, "b": b, "c": other, "ta": ta}
    k["person"] = _one(c, "INSERT INTO people (owner_user_id, name) VALUES (%s, 'Pat') RETURNING id", (a,))
    k["person2"] = _one(c, "INSERT INTO people (owner_user_id, name) VALUES (%s, 'Quin') RETURNING id", (a,))
    k["route"] = _one(c, "INSERT INTO flight_routes (trip_id, origin_codes, destination_codes, depart_from, depart_to, return_from, return_to) VALUES (%s, '{LIS}', '{JFK}', '2027-05-01', '2027-05-10', '2027-05-20', '2027-05-25') RETURNING id", (ta,))
    k["obs"] = _one(c, "INSERT INTO fare_observations (search_key, origin, destination, depart_date, source, confidence, currency, price_total_minor, observed_at, expires_at) VALUES (%s, 'LIS', 'JFK', '2027-05-03', 'travelpayouts', 'cached', 'EUR', 100, '2099-01-01', '2099-01-02') RETURNING id", (uuid.uuid4().hex * 2,))
    k["program"] = _one(c, "INSERT INTO affiliate_programs (code, network, name, category, hosts) VALUES ('tp_flights', 'travelpayouts', 'P', 'flights', '{}') RETURNING id")
    k["place"] = _one(c, "INSERT INTO saved_places (trip_id, place_provider, place_id, name) VALUES (%s, 'manual', 'seed', 'P') RETURNING id", (ta,))
    k["lodging"] = _one(c, "INSERT INTO lodging_options (trip_id, title, added_via) VALUES (%s, 'Flat', 'manual') RETURNING id", (ta,))
    k["run"] = _one(c, "INSERT INTO runs (trip_id, user_id, kind) VALUES (%s, %s, 'explain') RETURNING id", (ta, a))
    k["ver"] = _one(c, "INSERT INTO plan_verifications (trip_id, user_id) VALUES (%s, %s) RETURNING id", (ta, a))
    k["attest"] = "att" + uuid.uuid4().hex[:8]
    c.execute("INSERT INTO device_attestations (key_id, public_key, environment) VALUES (%s, '\\x00', 'development')", (k["attest"],))
    k["code"] = _one(c, "INSERT INTO referral_codes (user_id, code) VALUES (%s, 'ZZZZ2222') RETURNING code", (other,))
    c.execute("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (ta, k["person"]))
    return k


def _try(c, user, sql, params=()):
    """Run one statement; a permission or RLS refusal rolls the transaction back and returns None."""
    try:
        return c.execute(sql, params).rowcount
    except psycopg.errors.InsufficientPrivilege:
        c.rollback()
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(user),))
        return None


def _forced(c):
    return {r[0] for r in c.execute("SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind IN ('r', 'p') AND relforcerowsecurity AND NOT relispartition")}


def test_every_forced_table_has_an_isolation_case(sysm, tenants):
    assert set(_seeders("abcdef0123", tenants)) == _forced(sysm), "add the new table to _seeders (and A_BLIND or B_SEES if it needs it)"


@pytest.mark.parametrize("table", sorted(_seeders("abcdef0123", {k: None for k in "a b c ta route obs program place lodging run ver attest code person person2".split()})))
def test_tenant_b_sees_and_changes_nothing_of_tenant_a(sysm, tenants, table):
    k = tenants
    sql, params = _seeders(uuid.uuid4().hex[:10], k)[table]
    sysm.execute(sql, params)  # A's row, made by the worker login
    assert _one(sysm, f"SELECT count(*) FROM {table}") >= 1
    # A reads its own row (except where the app is blind by design).
    with as_user(k["a"]) as c:
        seen = _try(c, k["a"], f"SELECT 1 FROM {table}")
        if table in A_BLIND:
            assert seen is None or seen == 0
        else:
            assert seen and seen >= 1, table
    col = _one(sysm, "SELECT attname FROM pg_attribute WHERE attrelid = %s::regclass AND attnum > 0 AND NOT attisdropped AND attidentity = '' AND attgenerated = '' ORDER BY attnum LIMIT 1", (table,))
    with as_user(k["b"]) as c:
        b = k["b"]
        sel = _try(c, b, f"SELECT 1 FROM {table}")
        assert sel in (None, B_SEES.get(table, 0)), (table, "select")
        upd = _try(c, b, f"UPDATE {table} SET {col} = {col}")
        assert upd in (None, B_SEES.get(table, 0)), (table, "update")
        assert _try(c, b, f"DELETE FROM {table}") in (None, 0), (table, "delete")  # even B's own users row has no delete policy
        ins_sql, ins_params = _seeders(uuid.uuid4().hex[:10], k)[table]
        assert _try(c, b, ins_sql, ins_params) is None, (table, "insert with A's ids must be refused")


def test_private_notes_are_visible_to_their_author_only(sysm):
    owner, editor = _user(sysm), _user(sysm)
    t = _trip(sysm, owner)
    _member(sysm, t, editor, "editor")
    ins = "INSERT INTO notes (trip_id, author_user_id, is_private) VALUES (%s, %s, %s) RETURNING id"
    private, shared = _one(sysm, ins, (t, owner, True)), _one(sysm, ins, (t, owner, False))
    with as_user(owner) as c:
        assert {r[0] for r in c.execute("SELECT id FROM notes")} == {private, shared}
    with as_user(editor) as c:
        assert {r[0] for r in c.execute("SELECT id FROM notes")} == {shared}
        assert c.execute("UPDATE notes SET is_private = false WHERE id = %s", (private,)).rowcount == 0
        assert c.execute("DELETE FROM notes WHERE id = %s", (private,)).rowcount == 0
        assert _try(c, editor, ins, (t, owner, False)) is None  # cannot write as someone else


# --- ownership guard, transfer and invite redemption as hermi_api_login ---------------------------------


def test_owner_change_guard_transfer_and_invite_redemption(sysm):
    owner, other, joiner = _user(sysm), _user(sysm), _user(sysm)
    t = _trip(sysm, owner)
    _member(sysm, t, other, "editor")
    with as_user(owner) as c:
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as e:
            c.execute("UPDATE trips SET owner_user_id = %s WHERE id = %s", (other, t))
        assert e.value.sqlstate == "42501" and "owner_change_forbidden" in str(e.value)
        c.rollback()
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(owner),))
        assert c.execute("SELECT transfer_trip_owner(%s, %s)", (t, other)).fetchone() == (other,)
        c.commit()
    assert sysm.execute("SELECT owner_user_id FROM trips WHERE id = %s", (t,)).fetchone() == (other,)
    assert dict(sysm.execute("SELECT user_id, role FROM trip_members WHERE trip_id = %s", (t,)).fetchall()) == {other: "owner", owner: "editor"}
    with as_user(owner) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):  # no longer the owner
        c.execute("SELECT transfer_trip_owner(%s, %s)", (t, owner))
    token = TOKEN()
    sysm.execute("INSERT INTO trip_invites (trip_id, token_hash, invited_by, max_uses) VALUES (%s, %s, %s, 5)", (t, token, other))
    with as_user(joiner) as c:
        assert c.execute("SELECT redeem_trip_invite(%s)", (token,)).fetchone() == (t,)
        assert c.execute("SELECT role FROM trip_members WHERE trip_id = %s AND user_id = %s", (t, joiner)).fetchone() == ("editor",)
        c.commit()
    assert sysm.execute("SELECT count(*) FROM trip_members WHERE trip_id = %s AND user_id = %s", (t, joiner)).fetchone() == (1,)
    with as_user(joiner) as c, pytest.raises(psycopg.errors.UniqueViolation):  # second redemption: already a member
        c.execute("SELECT redeem_trip_invite(%s)", (token,))


# --- Phase 1 functions under the real roles --------------------------------------------------------------


def test_grant_import_reward_once_per_user_even_after_the_trip_is_deleted(sysm):
    _flags(sysm)
    u = _user(sysm)
    sysm.execute("UPDATE users SET email_verified_at = now() WHERE id = %s", (u,))
    t = _trip(sysm, u)
    imp = lambda trip: _one(sysm, "INSERT INTO trip_imports (user_id, trip_id, source, status, completed_at, flights_found, stays_found, other_found, items_applied, flights_applied, stays_applied) VALUES (%s, %s, 'ics_file', 'applied', now(), 2, 1, 2, 4, 2, 1) RETURNING id", (u, trip))  # noqa: E731
    first = imp(t)
    with as_user(u) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):  # the API may not grant its own reward
        c.execute("SELECT grant_import_reward(%s)", (first,))
    assert _one(sysm, "SELECT grant_import_reward(%s)", (first,))
    assert _one(sysm, "SELECT grant_import_reward(%s)", (first,)) is None
    sysm.execute("DELETE FROM trips WHERE id = %s", (t,))
    assert _one(sysm, "SELECT grant_import_reward(%s)", (imp(_trip(sysm, u)),)) is None


def test_referrals_under_the_real_roles(sysm):
    _flags(sysm)
    ref, new = _user(sysm), _user(sysm)
    code = _one(sysm, "SELECT ensure_referral_code(%s)", (ref,))
    with as_user(ref) as c:
        assert c.execute("SELECT my_referral_code()").fetchone() == (code,)
        assert c.execute("SELECT redeem_referral(%s)", (code,)).fetchone() == (None,)  # your own code
    with as_user(new) as c:
        rid = c.execute("SELECT redeem_referral(%s)", (code,)).fetchone()[0]
        assert rid
        c.commit()
    with as_user(new) as c:
        assert c.execute("SELECT redeem_referral(%s)", (code,)).fetchone() == (None,)  # second redemption
        assert c.execute("SELECT count(*) FROM referral_rewards").fetchone() == (1,)  # the referee sees the reward
    with as_user(ref) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute("SELECT grant_referral_reward(%s)", (rid,))
    sysm.execute("UPDATE referral_rewards SET status = 'qualified', qualified_at = now() WHERE id = %s", (rid,))
    assert _one(sysm, "SELECT grant_referral_reward(%s)", (rid,)) is True
    assert _one(sysm, "SELECT grant_referral_reward(%s)", (rid,)) is False


def test_spend_guest_allowance_refuses_past_the_limit(sysm):
    key = "ga" + uuid.uuid4().hex[:8]
    sysm.execute("INSERT INTO device_attestations (key_id, public_key, environment) VALUES (%s, '\\x00', 'development')", (key,))
    spend = lambda n: _one(sysm, "SELECT spend_guest_allowance(%s, %s, 5)", (key, n))  # noqa: E731
    assert (spend(3), spend(3), spend(2)) == (True, False, True)
    with _connect(APP_URL) as app, pytest.raises(psycopg.errors.InsufficientPrivilege):
        app.execute("SELECT spend_guest_allowance(%s, 1, 5)", (key,))


def test_reserve_then_settle_credits_round_trip_through_credit_balances(sysm):
    u, other = _user(sysm), _user(sysm)
    t = _trip(sysm, u)
    sysm.execute("INSERT INTO credit_grants (user_id, kind, credits, remaining) VALUES (%s, 'purchase', 10, 10)", (u,))
    bal = lambda c: c.execute("SELECT remaining FROM credit_balances").fetchone()  # noqa: E731
    with as_user(other) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):  # not on someone else's balance
        c.execute("SELECT reserve_credits(%s, %s, 1, 'research', NULL, 'x')", (u, t))
    with as_user(u) as c:
        assert bal(c) == (10,)
        res = c.execute("SELECT reserve_credits(%s, %s, 8, 'research', NULL, 'rt1')", (u, t)).fetchone()[0]
        assert bal(c) == (2,)
        assert c.execute("SELECT settle_credits(%s, 3)", (res,)).fetchone() == (5,)
        assert bal(c) == (7,)
        assert c.execute("SELECT count(*) FROM credit_ledger WHERE user_id = %s", (u,)).fetchone()[0] >= 2
        c.commit()
    with as_user(other) as c:
        assert c.execute("SELECT count(*) FROM credit_balances").fetchone() == (0,)


# --- the 7 functions 03 leaves without DDL: the branches ----------------------------------------------------


def test_file_content_report_branches(sysm):
    owner, member, outsider = _user(sysm), _user(sysm), _user(sysm)
    t = _trip(sysm, owner)
    _member(sysm, t, member, "viewer")
    link = _one(sysm, "INSERT INTO trip_share_links (trip_id, token_hash) VALUES (%s, %s) RETURNING id", (t, TOKEN()))
    note = _one(sysm, "INSERT INTO notes (trip_id, author_user_id, is_private) VALUES (%s, %s, false) RETURNING id", (t, owner))
    private = _one(sysm, "INSERT INTO notes (trip_id, author_user_id, is_private) VALUES (%s, %s, true) RETURNING id", (t, owner))
    key = uuid.uuid4().hex * 2
    sysm.execute("INSERT INTO shared_research_cache (key, kind, provider, params, response, expires_at, stale_until) VALUES (%s, 'destination_brief', 'fake', '{}', '{}', now() + interval '1 day', now() + interval '2 days')", (key,))
    run = _one(sysm, "INSERT INTO runs (trip_id, user_id, kind, cache_key) VALUES (%s, %s, 'explain', %s) RETURNING id", (t, owner, key))
    rep = "SELECT file_content_report(%s, %s, 'wrong_info', 'detail')"
    # shared_trip: a share link is public, so any signed-in person may report it (no membership needed). Unknown id: not found.
    with as_user(outsider) as c:
        assert c.execute(rep, ("shared_trip", str(link))).fetchone()[0]
        with pytest.raises(psycopg.errors.NoDataFound):
            c.execute(rep, ("shared_trip", str(uuid.uuid4())))
    # agent_note: members only, and a private note only to its author.
    with as_user(member) as c:
        assert c.execute(rep, ("agent_note", str(note))).fetchone()[0]
        with pytest.raises(psycopg.errors.NoDataFound):
            c.execute(rep, ("agent_note", str(private)))
    with as_user(outsider) as c, pytest.raises(psycopg.errors.NoDataFound):
        c.execute(rep, ("agent_note", str(note)))
    with as_user(owner) as c:
        assert c.execute(rep, ("agent_note", str(private))).fetchone()[0]
    # ai_answer: members only; it expires the run's cached answer at once.
    with as_user(outsider) as c, pytest.raises(psycopg.errors.NoDataFound):
        c.execute(rep, ("ai_answer", str(run)))
    assert _one(sysm, "SELECT expires_at > now() + interval '1 hour' FROM shared_research_cache WHERE key = %s", (key,))
    with as_user(member) as c:
        assert c.execute(rep, ("ai_answer", str(run))).fetchone()[0]
        c.commit()
    assert _one(sysm, "SELECT expires_at <= now() FROM shared_research_cache WHERE key = %s", (key,))
    assert _one(sysm, "SELECT report_count FROM shared_research_cache WHERE key = %s", (key,)) == 1


def test_advance_trip_import_refresh_and_changes(sysm):
    u = _user(sysm)
    feed = _one(sysm, "INSERT INTO trip_imports (user_id, source, status, completed_at, poll_enabled, feed_url_enc, next_poll_at, pending_changes, pending_changes_at) VALUES (%s, 'ics_feed', 'applied', now(), true, '\\x01', now() + interval '6 hours', '{\"added\": []}', now()) RETURNING id", (u,))
    plain = _one(sysm, "INSERT INTO trip_imports (user_id, source, status, completed_at) VALUES (%s, 'ics_file', 'applied', now()) RETURNING id", (u,))
    with as_user(u) as c:
        assert c.execute("SELECT advance_trip_import(%s, 'refresh')", (feed,)).fetchone() == ("applied",)
        assert c.execute("SELECT next_poll_at <= now() FROM trip_imports WHERE id = %s", (feed,)).fetchone() == (True,)
        with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):  # not a polled feed
            c.execute("SELECT advance_trip_import(%s, 'refresh')", (plain,))
        c.rollback()
        c.execute("SELECT set_config('app.user_id', %s, true)", (str(u),))
        assert c.execute("SELECT advance_trip_import(%s, 'dismiss_changes')", (feed,)).fetchone() == ("applied",)
        assert c.execute("SELECT pending_changes, pending_changes_at FROM trip_imports WHERE id = %s", (feed,)).fetchone() == (None, None)
        with pytest.raises(psycopg.errors.ObjectNotInPrerequisiteState):  # nothing pending now
            c.execute("SELECT advance_trip_import(%s, 'confirm_changes')", (feed,))


def test_link_my_traveler_false_cases(sysm):
    owner, me, third = _user(sysm), _user(sysm), _user(sysm)
    t = _trip(sysm, owner)
    _member(sysm, t, me, "editor")
    person = lambda uid, **kw: _one(sysm, "INSERT INTO people (owner_user_id, name, is_self, linked_user_id) VALUES (%s, 'X', %s, %s) RETURNING id", (uid, kw.get("is_self", False), kw.get("linked")))  # noqa: E731
    on_trip = lambda p: sysm.execute("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (t, p))  # noqa: E731
    selfrow, mine, taken, off_trip, good = person(owner, is_self=True), person(me), person(owner, linked=third), person(owner), person(owner)
    for p in (selfrow, mine, taken, good):
        on_trip(p)
    call = lambda c, p: c.execute("SELECT link_my_traveler(%s, %s)", (t, p)).fetchone()[0]  # noqa: E731
    with as_user(me) as c:
        assert [call(c, p) for p in (selfrow, mine, taken, off_trip, uuid.uuid4())] == [False] * 5
        assert call(c, good) is True
        c.commit()
    assert _one(sysm, "SELECT linked_user_id FROM people WHERE id = %s", (good,)) == me


# --- 6.5 item 2: a table's GRANT, ENABLE, FORCE and policies travel together ---------------------------------


def rls_gaps(sql: str) -> list[str]:
    """Tables in one migration that have some but not all of GRANT, ENABLE, FORCE and a policy (a created table needs all four)."""
    found: dict[str, set[str]] = {}
    mark = lambda t, what: found.setdefault(t, set()).add(what)  # noqa: E731
    for t in re.findall(r"CREATE TABLE\s+(\w+)", sql, re.I):
        found.setdefault(t, set())
    for t in re.findall(r"ALTER TABLE\s+(\w+)\s+ENABLE ROW LEVEL SECURITY", sql, re.I):
        mark(t, "enable")
    for t in re.findall(r"ALTER TABLE\s+(\w+)\s+FORCE ROW LEVEL SECURITY", sql, re.I):
        mark(t, "force")
    for t in re.findall(r"CREATE POLICY\s+\w+\s+ON\s+(\w+)", sql, re.I):
        mark(t, "policy")
    for stmt in re.findall(r"\bGRANT\b[^;]*;", sql, re.I):
        m = re.search(r"\bON\s+(?!FUNCTION|SCHEMA|ALL|SEQUENCE|TYPE)(?:TABLE\s+)?(.+?)\s+TO\b", stmt, re.I | re.S)
        for t in re.split(r"\s*,\s*", re.sub(r"\([^)]*\)", "", m.group(1))) if m else []:
            mark(t.strip(), "grant")
    exempt = set(re.findall(r"--\s*rls-exempt:\s*(\w+)", sql))  # a global table the API only reads: needs a reason in the migration
    gaps = []
    for t, have in found.items():
        need = {"grant", "enable", "force", "policy"} - ({"policy"} if t in NO_POLICY or t in exempt else set())
        if t not in exempt and need - have:
            gaps.append(f"{t}: missing {sorted(need - have)}")
    return gaps


def test_rls_gap_check_catches_missing_pieces():
    good = "CREATE TABLE t1 (id int);\nGRANT SELECT, INSERT ON t1 TO hermi_app;\nALTER TABLE t1 ENABLE ROW LEVEL SECURITY;\nALTER TABLE t1 FORCE ROW LEVEL SECURITY;\nCREATE POLICY t1_select ON t1 FOR SELECT USING (true);"
    assert rls_gaps(good) == []
    assert rls_gaps(good.replace("ALTER TABLE t1 FORCE ROW LEVEL SECURITY;", "")) == ["t1: missing ['force']"]
    assert rls_gaps(good.replace("GRANT SELECT, INSERT ON t1 TO hermi_app;", "")) == ["t1: missing ['grant']"]
    assert rls_gaps(good.replace("CREATE POLICY t1_select ON t1 FOR SELECT USING (true);", "")) == ["t1: missing ['policy']"]
    assert rls_gaps("CREATE TABLE t2 (id int);") == ["t2: missing ['enable', 'force', 'grant', 'policy']"]
    assert rls_gaps("CREATE TABLE t3 (id int); -- rls-exempt: t3 (reference data)") == []


def test_every_revision_after_0014_keeps_grant_enable_force_and_policies_together():
    later = [p for p in sorted(VERSIONS.glob("[0-9][0-9][0-9][0-9]_*.py")) if int(p.name[:4]) > 14]
    for p in later:
        assert rls_gaps(p.read_text(encoding="utf-8")) == [], p.name
    # 0014 itself: every table it touches with a policy is also forced and granted.
    text = (VERSIONS / "0014_rls.py").read_text(encoding="utf-8")
    assert "CREATE POLICY" in text
