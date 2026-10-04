# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-022.3: revisions 0007_imports_referrals and 0008_affiliate (03 sections 5.9, 5.10, 10).

Constraints are exercised as the migrate login (the owner), because grants land in 0014_rls.
feature_flags comes from 0012_admin_privacy; the function tests write the two settings they read into it (migrate login).
The schema-vs-DDL comparison for 5.9 and 5.10 lives in test_migrations_trips_people.py (it spans 0002 to 0008).
"""

import uuid
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import APP_URL, MIGRATE_URL, _alembic_cfg, _need_db

from hermi import db

TABLES = (
    "trip_imports referral_codes referral_rewards affiliate_programs affiliate_link_templates link_clicks "
    "affiliate_conversions affiliate_payouts revenue_by_month revenue_by_surface revenue_by_partner"
).split()
FUNCS = (
    "grant_import_reward set_import_polling ensure_referral_code my_referral_code redeem_referral grant_referral_reward"
).split()


@pytest.fixture
def conn():
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as c:
        yield c


@contextmanager
def _check(name):
    """The insert must fail on exactly this CHECK constraint, not another one."""
    with pytest.raises(psycopg.errors.CheckViolation) as e:
        yield
    assert e.value.diag.constraint_name == name


def _user(c, verified=True, created="now()"):
    return c.execute(
        f"INSERT INTO users (email, email_verified_at, created_at) VALUES (%s, CASE WHEN %s THEN now() END, {created}) RETURNING id",
        (f"{uuid.uuid4().hex[:8]}@example.com", verified),
    ).fetchone()[0]


def _trip(c, owner):
    return c.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)
    ).fetchone()[0]


def _import(c, user, trip=None, **kw):
    cols = {"user_id": user, "trip_id": trip, "source": "ics_file", **kw}
    return c.execute(
        f"INSERT INTO trip_imports ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id",
        tuple(cols.values()),
    ).fetchone()[0]


def _applied(c, user, trip, **kw):
    return _import(
        c, user, trip, status="applied", completed_at="2026-01-01", flights_found=2, stays_found=1, other_found=2,
        items_applied=4, flights_applied=2, stays_applied=1, **kw,
    )


def _flags(c):
    c.execute("DELETE FROM public.feature_flags")
    c.execute(
        "INSERT INTO public.feature_flags (key, kind, enabled, rules) VALUES "
        "('setting_import_reward', 'setting', true, '{\"min_items_applied\": 3}'), "
        "('setting_referral_credits', 'setting', true, '{\"referrer\": 20, \"referee\": 20}')"
    )


def _program(c, code="tp_flights", hosts="{}", network="travelpayouts", category="flights"):
    return c.execute(
        "INSERT INTO affiliate_programs (code, network, name, category, hosts) VALUES (%s, %s, 'P', %s, %s) RETURNING id",
        (code, network, category, hosts),
    ).fetchone()[0]


def _as(c, who):
    c.execute("SELECT set_config('app.user_id', %s, false)", (str(who) if who else "",))


def test_chain_is_linear_and_single_head():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0007_imports_referrals").down_revision == "0006_billing_credits"
    assert s.get_revision("0008_affiliate").down_revision == "0007_imports_referrals"
    assert len(s.get_heads()) == 1


def test_objects_exist_and_round_trip(conn):
    for n in TABLES:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n
    for f in FUNCS:
        assert conn.execute("SELECT count(*) FROM pg_proc WHERE proname = %s", (f,)).fetchone()[0] == 1, f
    # First partitions exist (previous month, current month, three ahead and the default).
    assert conn.execute("SELECT count(*) FROM pg_inherits WHERE inhparent = 'link_clicks'::regclass").fetchone()[0] >= 5
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0006_billing_credits")
    assert conn.execute(
        "SELECT to_regclass('trip_imports'), to_regclass('affiliate_programs'), to_regclass('link_clicks'), to_regclass('revenue_by_month')"
    ).fetchone() == (None,) * 4
    assert conn.execute("SELECT count(*) FROM pg_proc WHERE proname = ANY(%s)", (FUNCS,)).fetchone() == (0,)
    command.upgrade(cfg, "head")
    assert conn.execute("SELECT to_regclass('link_clicks')").fetchone()[0]


def test_no_out_of_scope_tables(conn):
    for n in ("stripe_customers", "concierge_requests", "partner_guides", "print_orders", "advisor_clients"):
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0] is None, n


def test_import_checks(conn):
    u = _user(conn)
    t = _trip(conn, u)
    for kw, name in (
        ({"source": "pdf"}, "ck_trip_imports_source"),
        ({"origin": "tripadvisor"}, "ck_trip_imports_origin"),
        ({"status": "done"}, "ck_trip_imports_status"),
        ({"status": "applied"}, "ck_trip_imports_applied"),  # needs completed_at
        ({"reward_granted_at": "2026-01-01"}, "ck_trip_imports_reward"),  # needs applied
        ({"feed_url_enc": b"x"}, "ck_trip_imports_feed_url"),  # only ics_feed
        ({"items_applied": 1}, "ck_trip_imports_counts"),  # exceeds items_found
        ({"poll_enabled": True}, "ck_trip_imports_poll"),
        ({"source_name": "x" * 201}, "trip_imports_source_name_check"),
    ):
        with _check(name):
            _import(conn, u, t, **kw)
    i = _import(conn, u, t, flights_found=1, stays_found=1, other_found=1)
    assert conn.execute("SELECT items_found, status, origin FROM trip_imports WHERE id = %s", (i,)).fetchone() == (
        3,
        "received",
        "other",
    )
    # trip_id is SET NULL: the import survives its trip.
    conn.execute("DELETE FROM trips WHERE id = %s", (t,))
    assert conn.execute("SELECT trip_id FROM trip_imports WHERE id = %s", (i,)).fetchone() == (None,)


def test_one_reward_per_user_index(conn):
    u = _user(conn)
    _applied(conn, u, None, reward_granted_at="2026-01-01")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _applied(conn, u, None, reward_granted_at="2026-02-01")
    _applied(conn, u, None)  # an unrewarded import is fine


def test_grant_import_reward(conn):
    conn.execute(
        "INSERT INTO plans (code, kind, name, duration_days, credits_granted, credits_valid_days) "
        "VALUES ('trip_pass', 'pass', 'Trip Pass', 90, 40, 90) ON CONFLICT DO NOTHING"
    )
    _flags(conn)
    u = _user(conn)
    t = _trip(conn, u)
    grant = lambda i: conn.execute("SELECT grant_import_reward(%s)", (i,)).fetchone()[0]  # noqa: E731
    # Not applied, too few items and place-only imports do not qualify and consume nothing.
    assert grant(_import(conn, u, t)) is None
    few = _import(conn, u, t, status="applied", completed_at="2026-01-01", flights_found=1, items_applied=1, flights_applied=1)
    assert grant(few) is None
    places = _import(conn, u, t, source="maps_file", status="applied", completed_at="2026-01-01", places_found=5, items_applied=5)
    assert grant(places) is None
    ok = _applied(conn, u, t)
    pass_id = grant(ok)
    assert pass_id
    assert conn.execute("SELECT source, credits_granted FROM trip_passes WHERE id = %s", (pass_id,)).fetchone() == ("import_reward", 40)
    assert conn.execute("SELECT kind, credits, period_key FROM credit_grants WHERE user_id = %s", (u,)).fetchone() == (
        "trip_pass",
        40,
        f"import_reward:{ok}",
    )
    assert conn.execute("SELECT reward_pass_id FROM trip_imports WHERE id = %s", (ok,)).fetchone() == (pass_id,)
    # A replay and a second import (even on another trip) get nothing: once per user.
    assert grant(ok) is None
    assert grant(_applied(conn, u, _trip(conn, u))) is None
    # An unverified email never qualifies.
    u2 = _user(conn, verified=False)
    assert grant(_applied(conn, u2, _trip(conn, u2))) is None


def test_set_import_polling(conn):
    u, other = _user(conn), _user(conn)
    t = _trip(conn, u)
    feed = _applied(conn, u, t, source="ics_feed", feed_url_enc=b"enc")
    call = lambda i, on: conn.execute("SELECT set_import_polling(%s, %s)", (i, on)).fetchone()[0]  # noqa: E731
    _as(conn, None)
    assert call(feed, True) is False  # anonymous
    _as(conn, other)
    assert call(feed, True) is False  # someone else's import
    _as(conn, u)
    assert call(feed, True) is True
    assert call(feed, True) is False  # already on
    assert conn.execute("SELECT poll_enabled, next_poll_at IS NOT NULL FROM trip_imports WHERE id = %s", (feed,)).fetchone() == (True, True)
    assert call(feed, False) is True
    assert conn.execute("SELECT poll_enabled, feed_url_enc FROM trip_imports WHERE id = %s", (feed,)).fetchone() == (False, None)
    assert call(feed, True) is False  # the URL was deleted
    for _ in range(3):  # at most 3 polled feeds
        assert call(_applied(conn, u, t, source="ics_feed", feed_url_enc=b"e"), True) is True
    assert call(_applied(conn, u, t, source="ics_feed", feed_url_enc=b"e"), True) is False
    assert call(_applied(conn, u, t), True) is False  # not a feed


def test_referral_code_uniqueness_and_format(conn):
    u, v = _user(conn), _user(conn)
    code = conn.execute("SELECT ensure_referral_code(%s)", (u,)).fetchone()[0]
    assert len(code) == 8 and code == code.upper()
    assert conn.execute("SELECT ensure_referral_code(%s)", (u,)).fetchone() == (code,)
    _as(conn, u)
    assert conn.execute("SELECT my_referral_code()").fetchone() == (code,)
    _as(conn, None)
    assert conn.execute("SELECT my_referral_code()").fetchone() == (None,)
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("INSERT INTO referral_codes (user_id, code) VALUES (%s, %s)", (v, code))
    with _check("ck_referral_codes_code"):
        conn.execute("INSERT INTO referral_codes (user_id, code) VALUES (%s, 'abc')", (v,))


def test_referral_rewards_constraints_and_redeem_flow(conn):
    _flags(conn)
    ref, new = _user(conn), _user(conn)
    code = conn.execute("SELECT ensure_referral_code(%s)", (ref,)).fetchone()[0]
    ins = "INSERT INTO referral_rewards (code, referrer_user_id, referee_user_id{}) VALUES (%s, %s, %s{})"
    with _check("ck_referral_rewards_distinct"):
        conn.execute(ins.format("", ""), (code, ref, ref))
    with _check("ck_referral_rewards_granted"):
        conn.execute(ins.format(", status", ", 'granted'"), (code, ref, new))  # granted needs granted_at
    _as(conn, ref)
    assert conn.execute("SELECT redeem_referral(%s)", (code,)).fetchone() == (None,)  # own code
    _as(conn, new)
    assert conn.execute("SELECT redeem_referral('NOPE1234')").fetchone() == (None,)
    rid = conn.execute("SELECT redeem_referral(%s)", (f" {code.lower()} ",)).fetchone()[0]
    assert rid
    assert conn.execute("SELECT redeem_referral(%s)", (code,)).fetchone() == (None,)  # referred once
    assert conn.execute(
        "SELECT referrer_credits, referee_credits, status FROM referral_rewards WHERE id = %s", (rid,)
    ).fetchone() == (20, 20, "pending")
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins.format("", ""), (code, _user(conn), new))
    old = _user(conn, created="now() - interval '15 days'")  # past the 14 day window
    _as(conn, old)
    assert conn.execute("SELECT redeem_referral(%s)", (code,)).fetchone() == (None,)


def test_grant_referral_reward_is_idempotent_and_caps_referrer(conn):
    _flags(conn)
    ref = _user(conn)
    code = conn.execute("SELECT ensure_referral_code(%s)", (ref,)).fetchone()[0]
    ids = [
        conn.execute(
            "INSERT INTO referral_rewards (code, referrer_user_id, referee_user_id, referrer_credits, referee_credits, status, qualified_at) "
            "VALUES (%s, %s, %s, 20, 20, 'qualified', now()) RETURNING id",
            (code, ref, _user(conn)),
        ).fetchone()[0]
        for _ in range(6)
    ]
    for i in ids:
        assert conn.execute("SELECT grant_referral_reward(%s)", (i,)).fetchone() == (True,)
        assert conn.execute("SELECT grant_referral_reward(%s)", (i,)).fetchone() == (False,)  # replay does nothing
    assert conn.execute("SELECT count(*) FROM credit_grants WHERE user_id = %s AND kind = 'promo'", (ref,)).fetchone() == (5,)
    assert conn.execute("SELECT referrer_capped FROM referral_rewards WHERE id = %s", (ids[5],)).fetchone() == (True,)
    # The referee of the capped row still got their credits.
    assert conn.execute("SELECT count(*) FROM credit_grants WHERE period_key = %s", (f"referral:{ids[5]}",)).fetchone() == (1,)
    assert conn.execute("SELECT count(*) FROM credit_ledger WHERE note = 'referral reward'").fetchone() == (11,)


def test_affiliate_program_and_template_constraints(conn):
    p = _program(conn, hosts="{aviasales.com}")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _program(conn)
    with _check("ck_affiliate_programs_network"):
        _program(conn, "x1", network="impact")
    with _check("ck_affiliate_programs_category"):
        _program(conn, "x2", category="gambling")
    with _check("ck_affiliate_programs_no_airbnb"):
        _program(conn, "x3", hosts="{www.airbnb.com}")  # Airbnb can never be added
    ins = "INSERT INTO affiliate_link_templates (program_id, kind, surface, template) VALUES (%s, %s, %s, %s)"
    conn.execute(ins, (p, "search", None, "https://www.aviasales.com/search?marker={marker}"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, (p, "search", None, "https://www.aviasales.com/other"))  # one cell per program, kind, surface, variant
    conn.execute(ins, (p, "search", "chosen_flight", "https://www.aviasales.com/a"))
    with _check("ck_affiliate_link_templates_https"):
        conn.execute(ins, (p, "map", None, "http://www.aviasales.com/a"))
    with _check("ck_affiliate_link_templates_no_url_param"):
        conn.execute(ins, (p, "deeplink", None, "https://www.aviasales.com/r?url={dest_enc}"))  # no open redirect
    with _check("ck_affiliate_link_templates_kind"):
        conn.execute(ins, (p, "iframe", None, "https://www.aviasales.com/a"))
    conn.execute("DELETE FROM affiliate_programs WHERE id = %s", (p,))  # cascades to templates
    assert conn.execute("SELECT count(*) FROM affiliate_link_templates").fetchone() == (0,)


def test_link_clicks_partitioned_uniqueness_and_default_partition(conn):
    p = _program(conn)
    assert conn.execute("SELECT relkind FROM pg_class WHERE relname = 'link_clicks'").fetchone() == ("p",)
    ins = "INSERT INTO link_clicks (click_id, short_id, program_id, surface, destination_url, created_at) VALUES (%s, %s, %s, 'checklist', 'https://x.test/', %s)"
    conn.execute(ins, ("c1", "s1", p, "2026-10-01"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, ("c1", "s2", p, "2026-10-01"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, ("c2", "s1", p, "2026-10-01"))
    conn.execute(ins, ("c3", None, p, "2026-10-01"))
    conn.execute(ins, ("c4", None, p, "2026-10-01"))  # short_id is unique only when set
    conn.execute(ins, ("far", None, p, "2031-01-01"))  # lands in the default partition
    with _check("ck_link_clicks_opened_in"):
        conn.execute(
            "INSERT INTO link_clicks (click_id, program_id, surface, destination_url, opened_in) VALUES ('c9', %s, 's', 'u', 'ie')", (p,)
        )
    # No foreign keys to users or trips; the program is RESTRICT.
    conn.execute(
        "INSERT INTO link_clicks (click_id, program_id, surface, destination_url, user_id, trip_id) VALUES ('c8', %s, 's', 'u', %s, %s)",
        (p, uuid.uuid4(), uuid.uuid4()),
    )
    with pytest.raises(psycopg.errors.RestrictViolation):
        conn.execute("DELETE FROM affiliate_programs WHERE id = %s", (p,))


def test_conversion_uniqueness_and_payouts(conn):
    p, p2 = _program(conn), _program(conn, "other")
    ins = (
        "INSERT INTO affiliate_conversions (program_id, network, network_txn_id, booked_at, status, commission_minor, commission_currency) "
        "VALUES (%s, 'travelpayouts', %s, now(), %s, 500, 'USD')"
    )
    conn.execute(ins, (p, "tx1", "approved"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, (p, "tx1", "pending"))  # the nightly pull upserts on (program, txn)
    conn.execute(ins, (p2, "tx1", "paid"))  # the same txn id under another program is fine
    conn.execute(
        "INSERT INTO affiliate_conversions (program_id, network, network_txn_id) VALUES (%s, 'travelpayouts', 'tx1') "
        "ON CONFLICT (program_id, network_txn_id) DO NOTHING",
        (p,),
    )
    with _check("ck_affiliate_conversions_status"):
        conn.execute(ins, (p, "tx2", "bogus"))
    with _check("ck_affiliate_conversions_match"):
        conn.execute(
            "INSERT INTO affiliate_conversions (program_id, network, network_txn_id, match_status) VALUES (%s, 'x', 'tx3', 'maybe')", (p,)
        )
    u = _user(conn)
    conn.execute("UPDATE affiliate_conversions SET user_id = %s WHERE network_txn_id = 'tx1' AND program_id = %s", (u, p))
    conn.execute("DELETE FROM users WHERE id = %s", (u,))  # the financial record stays, anonymous
    assert conn.execute(
        "SELECT user_id FROM affiliate_conversions WHERE program_id = %s AND network_txn_id = 'tx1'", (p,)
    ).fetchone() == (None,)
    pay = "INSERT INTO affiliate_payouts (program_id, period_start, period_end, amount_minor, currency) VALUES (%s, %s, %s, %s, 'USD')"
    conn.execute(pay, (p, "2026-09-01", "2026-09-30", 1000))
    with _check("ck_affiliate_payouts_period"):
        conn.execute(pay, (p, "2026-09-30", "2026-09-01", 1000))
    with _check("affiliate_payouts_amount_minor_check"):
        conn.execute(pay, (p, "2026-09-01", "2026-09-30", -1))


def test_materialized_views_refresh(conn):
    p = _program(conn, "tp")
    conn.execute(
        "INSERT INTO affiliate_conversions (program_id, network, network_txn_id, booked_at, status, commission_minor, commission_currency, surface) "
        "VALUES (%s, 'travelpayouts', 't', '2026-09-15', 'paid', 700, 'USD', 'checklist')",
        (p,),
    )
    for v in ("revenue_by_month", "revenue_by_surface", "revenue_by_partner"):
        conn.execute(f"REFRESH MATERIALIZED VIEW {v}")
        conn.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {v}")  # needs the unique index
    assert conn.execute("SELECT bookings, commission_minor FROM revenue_by_partner WHERE program = 'tp'").fetchone() == (1, 700)


def _pass_plan(c):
    c.execute(
        "INSERT INTO plans (code, kind, name, duration_days, credits_granted, credits_valid_days) "
        "VALUES ('trip_pass', 'pass', 'Trip Pass', 90, 40, 90) ON CONFLICT DO NOTHING"
    )


def _consumed(c, u):
    """What a granted reward would leave behind: passes, grants, stamped imports and identity hashes."""
    return c.execute(
        "SELECT (SELECT count(*) FROM trip_passes WHERE purchaser_user_id = %s), (SELECT count(*) FROM credit_grants WHERE user_id = %s), "
        "(SELECT count(*) FROM trip_imports WHERE user_id = %s AND reward_granted_at IS NOT NULL), (SELECT count(*) FROM identity_hashes WHERE kind = 'import_reward')",
        (u, u, u),
    ).fetchone()


def test_grant_import_reward_refusals_consume_nothing(conn):
    _pass_plan(conn)
    _flags(conn)
    grant = lambda i: conn.execute("SELECT grant_import_reward(%s)", (i,)).fetchone()[0]  # noqa: E731

    # Active Plus.
    u = _user(conn)
    conn.execute("INSERT INTO plans (code, kind, name) VALUES ('plus', 'tier', 'Plus') ON CONFLICT DO NOTHING")
    conn.execute("INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, 'plus', 'comp')", (u,))
    imp = _applied(conn, u, _trip(conn, u))
    before = _consumed(conn, u)
    assert grant(imp) is None and _consumed(conn, u) == before == (0, 0, 0, 0)

    # An active pass already on the trip.
    u = _user(conn)
    t = _trip(conn, u)
    conn.execute(
        "INSERT INTO trip_passes (trip_id, purchaser_user_id, plan_code, source, expires_at) VALUES (%s, %s, 'trip_pass', 'admin', now() + interval '30 days')",
        (t, u),
    )
    imp = _applied(conn, u, t)
    assert grant(imp) is None
    assert _consumed(conn, u) == (1, 0, 0, 0)  # only the pre-existing pass

    # A deleted trip.
    u = _user(conn)
    t = _trip(conn, u)
    conn.execute("UPDATE trips SET deleted_at = now() WHERE id = %s", (t,))
    assert grant(_applied(conn, u, t)) is None and _consumed(conn, u) == (0, 0, 0, 0)

    # A trip owned by someone else.
    u, other = _user(conn), _user(conn)
    assert grant(_applied(conn, u, _trip(conn, other))) is None
    assert _consumed(conn, u) == (0, 0, 0, 0) and _consumed(conn, other) == (0, 0, 0, 0)

    # An identity_hashes hit (a deleted and re-created account).
    u = _user(conn)
    conn.execute("INSERT INTO identity_hashes (hash, kind) SELECT identity_hashes_for(%s), 'import_reward'", (u,))
    hashes = conn.execute("SELECT count(*) FROM identity_hashes WHERE kind = 'import_reward'").fetchone()[0]
    assert hashes >= 1
    assert grant(_applied(conn, u, _trip(conn, u))) is None
    assert _consumed(conn, u)[:3] == (0, 0, 0)
    assert conn.execute("SELECT count(*) FROM identity_hashes WHERE kind = 'import_reward'").fetchone()[0] == hashes


def test_definer_functions_ignore_temp_tables_made_by_the_app_login(conn):
    """A temp feature_flags made by the API login must not shadow the real one inside a SECURITY DEFINER function (search_path ends in pg_temp)."""
    _flags(conn)  # the real setting: 20 credits each
    ref, new = _user(conn), _user(conn)
    code = conn.execute("SELECT ensure_referral_code(%s)", (ref,)).fetchone()[0]
    # The test database may or may not have the TEMPORARY revoke applied (bootstrap.sql); grant it so the attack is possible either way.
    dbname = conn.execute("SELECT quote_ident(current_database())").fetchone()[0]
    conn.execute(f"GRANT TEMPORARY ON DATABASE {dbname} TO hermi_api_login")
    try:
        with psycopg.connect(db.psycopg_url(APP_URL), autocommit=True) as app:
            assert app.execute("SELECT current_user").fetchone() == ("hermi_api_login",)
            app.execute("CREATE TEMP TABLE feature_flags (key text, enabled boolean, rules jsonb)")
            app.execute(
                "INSERT INTO feature_flags VALUES ('setting_referral_credits', true, '{\"referrer\": 1000000, \"referee\": 1000000}')"
            )
            app.execute("SELECT set_config('app.user_id', %s, false)", (str(new),))
            rid = app.execute("SELECT redeem_referral(%s)", (code,)).fetchone()[0]
    finally:
        conn.execute(f"REVOKE TEMPORARY ON DATABASE {dbname} FROM hermi_api_login")
    assert rid
    assert conn.execute("SELECT referrer_credits, referee_credits FROM referral_rewards WHERE id = %s", (rid,)).fetchone() == (20, 20)
