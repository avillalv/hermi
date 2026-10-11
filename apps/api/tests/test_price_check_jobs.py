# ruff: noqa: E501, F401, F811  (long SQL strings; fixtures imported from the sibling module)
"""WF-051.2: check_fare_route eligibility, evaluate_price_alerts once per drop, the schedule, and no agent job on it."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from tests.test_scheduler import clean_queue, make_route, sys_session  # noqa: F401

from hermi.config import Settings
from hermi.providers import travelpayouts
from hermi_worker import app as worker_app
from hermi_worker.jobs import (
    check_fare_route,
    evaluate_price_alerts,
    refresh_cached_fares,
    run_agent,
    scan_due_routes,
)

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)  # make_route departs 2027-01-10, 92 days on


@pytest.fixture(autouse=True)
def _usd_rate(system_conn):
    system_conn.execute("INSERT INTO fx_rates (currency, per_eur, rate_date) VALUES ('USD', 1.25, CURRENT_DATE) ON CONFLICT (currency) DO UPDATE SET per_eur = 1.25")


def _settings(db_urls):
    return Settings(_env_file=None, environment="ci", providers_mode="fake", database_url_system=db_urls["system"], scheduler_enabled=True)


def _owner(conn, rid):
    return conn.execute("SELECT t.owner_user_id, t.id FROM flight_routes r JOIN trips t ON t.id = r.trip_id WHERE r.id = %s", (rid,)).fetchone()


def _tier(conn, rid, tier):
    uid, _ = _owner(conn, rid)
    conn.execute(
        "INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, %s, 'comp') ON CONFLICT (user_id) DO UPDATE SET tier_code = EXCLUDED.tier_code, valid_until = NULL",
        (uid, tier),
    )


def _check(sys_session, db_urls, rid, now=NOW):
    out = check_fare_route.run(sys_session, _settings(db_urls), str(rid), client=travelpayouts.fixture_client(), token="t", now=now)
    sys_session.commit()
    return out


def _queued(conn, task):
    return conn.execute("SELECT queue_name, args FROM procrastinate_jobs WHERE task_name = %s", (task,)).fetchall()


def _alert(conn, rid, threshold=100000, push=True, email=True):
    uid, trip = _owner(conn, rid)
    return conn.execute(
        "INSERT INTO price_alerts (trip_id, route_id, user_id, threshold_minor, currency, channel_push, channel_email) VALUES (%s, %s, %s, %s, 'USD', %s, %s) RETURNING id",
        (trip, rid, uid, threshold, push, email),
    ).fetchone()[0]


def _to_fixture_route(conn, rid):
    """Point the route at the recorded provider response (LAX to TYO in November 2026), so a refresh links fares."""
    conn.execute(
        "UPDATE flight_routes SET origin_codes = '{LAX}', destination_codes = '{TYO}', adults = 2, depart_from = '2026-11-01', depart_to = '2026-11-30', return_from = '2026-11-10', return_to = '2026-11-25' WHERE id = %s",
        (rid,),
    )


def _fare(conn, rid, price, currency="USD"):
    _, trip = _owner(conn, rid)
    oid = conn.execute(
        "INSERT INTO fare_observations (search_key, origin, destination, depart_date, source, confidence, currency, price_total_minor, observed_at, expires_at) "
        "VALUES (%s, 'LIS', 'NRT', CURRENT_DATE + 30, 'travelpayouts', 'cached', %s, %s, now(), now() + interval '6 hours') RETURNING id",
        (uuid.uuid4().hex * 2, currency, price),
    ).fetchone()[0]
    conn.execute("INSERT INTO trip_fare_links (trip_id, route_id, observation_id) VALUES (%s, %s, %s)", (trip, rid, oid))


# --- eligibility --------------------------------------------------------------------------------------------------------


def test_a_free_owner_with_no_pass_is_skipped_with_a_named_reason(sys_session, system_conn, make_route, db_urls):
    rid = make_route()
    system_conn.execute("UPDATE flight_routes SET is_live = true WHERE id = %s", (rid,))
    _tier(system_conn, rid, "free")
    assert _check(sys_session, db_urls, rid) == "no_live_window"
    assert system_conn.execute("SELECT last_checked_at FROM flight_routes WHERE id = %s", (rid,)).fetchone()[0] is None


def test_a_plus_live_route_inside_120_days_is_checked(sys_session, system_conn, make_route, db_urls):
    rid = make_route()
    _tier(system_conn, rid, "plus")
    assert _check(sys_session, db_urls, rid) == "checked"
    assert system_conn.execute("SELECT last_checked_at FROM flight_routes WHERE id = %s", (rid,)).fetchone()[0] is not None


def test_departure_beyond_the_window_is_skipped(sys_session, system_conn, make_route, db_urls):
    rid = make_route()
    _tier(system_conn, rid, "plus")
    assert _check(sys_session, db_urls, rid, now=NOW - timedelta(days=60)) == "outside_window"  # 152 days out


def test_cached_inactive_and_past_routes_are_skipped(sys_session, system_conn, make_route, db_urls):
    rid = make_route()
    _tier(system_conn, rid, "plus")
    system_conn.execute("UPDATE flight_routes SET is_live = false WHERE id = %s", (rid,))
    assert _check(sys_session, db_urls, rid) == "not_live"
    system_conn.execute("UPDATE flight_routes SET is_live = true, active = false WHERE id = %s", (rid,))
    assert _check(sys_session, db_urls, rid) == "inactive"
    system_conn.execute("UPDATE flight_routes SET active = true WHERE id = %s", (rid,))
    assert _check(sys_session, db_urls, rid, now=NOW + timedelta(days=200)) == "departed"
    assert _check(sys_session, db_urls, uuid.uuid4()) == "gone"


def test_a_pass_grants_the_window_until_its_checks_run_out(sys_session, system_conn, make_route, db_urls):
    rid = make_route()
    _, trip = _owner(system_conn, rid)
    _tier(system_conn, rid, "free")
    system_conn.execute("DELETE FROM trip_passes WHERE trip_id = %s", (trip,))
    system_conn.execute(
        "INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status, live_checks_max, live_checks_used) VALUES (%s, 'trip_pass', now() - interval '1 day', now() + interval '30 days', 'active', 60, 59)",
        (trip,),
    )
    assert _check(sys_session, db_urls, rid) == "checked"
    system_conn.execute("UPDATE trip_passes SET live_checks_used = 60 WHERE trip_id = %s", (trip,))
    assert _check(sys_session, db_urls, rid) == "pass_checks_used"


# --- outage and enqueue -------------------------------------------------------------------------------------------------


def test_an_outage_backlog_fires_one_check_per_route(sys_session, system_conn, make_route, clean_queue):
    rid = make_route(NOW - timedelta(days=12))
    for minute in (0, 1, 2):
        scan_due_routes.run(sys_session, now=NOW + timedelta(minutes=minute))
        sys_session.commit()
    assert [a["route_id"] for _, a in _queued(system_conn, "check_fare_route")] == [str(rid)]


# --- evaluate_price_alerts ----------------------------------------------------------------------------------------------


def test_an_alert_triggers_once_per_drop_and_hands_a_request_to_the_notify_lane(sys_session, system_conn, make_route, db_urls, clean_queue):
    rid = make_route()
    aid = _alert(system_conn, rid, threshold=100000)
    _fare(system_conn, rid, 90000)
    s = _settings(db_urls)
    assert evaluate_price_alerts.run(sys_session, s, str(rid)) == 1
    sys_session.commit()
    assert evaluate_price_alerts.run(sys_session, s, str(rid)) == 0  # same data: nothing more
    sys_session.commit()
    rows = system_conn.execute("SELECT kind::text, dedupe_key FROM notifications WHERE trip_id = %s AND kind = 'price_drop'", (_owner(system_conn, rid)[1],)).fetchall()
    assert rows == [("price_drop", f"price_drop:{aid}:90000")]
    assert [q for q, _ in _queued(system_conn, "send_email")] == ["notify"]  # the request to the notify lane
    _fare(system_conn, rid, 80000)  # a further drop triggers again
    assert evaluate_price_alerts.run(sys_session, s, str(rid)) == 1
    sys_session.commit()
    assert len(_queued(system_conn, "send_email")) == 2


def test_inactive_alerts_and_alerts_over_target_do_nothing(sys_session, system_conn, make_route, db_urls):
    rid = make_route()
    aid = _alert(system_conn, rid, threshold=50000)
    _fare(system_conn, rid, 90000)
    assert evaluate_price_alerts.run(sys_session, _settings(db_urls), str(rid)) == 0
    sys_session.commit()  # release the alert row lock before the other connection updates it
    system_conn.execute("UPDATE price_alerts SET threshold_minor = 100000, active = false WHERE id = %s", (aid,))
    assert evaluate_price_alerts.run(sys_session, _settings(db_urls), str(rid)) == 0


def test_a_refresh_enqueues_one_evaluation_for_a_route_with_alerts(sys_session, system_conn, make_route, db_urls, clean_queue):
    with_alert, without = make_route(), make_route()
    for r in (with_alert, without):
        _tier(system_conn, r, "plus")
        _to_fixture_route(system_conn, r)
    _alert(system_conn, with_alert)
    _check(sys_session, db_urls, with_alert)
    _check(sys_session, db_urls, with_alert)  # a second refresh while one waits stays one
    _check(sys_session, db_urls, without)
    assert _queued(system_conn, "evaluate_price_alerts") == [("notify", {"route_id": str(with_alert)})]


def test_refresh_cached_fares_runs_as_a_job_and_enqueues_evaluation(sys_session, system_conn, make_route, db_urls, clean_queue):
    rid = make_route()
    _to_fixture_route(system_conn, rid)
    _alert(system_conn, rid)
    done = refresh_cached_fares.run(sys_session, _settings(db_urls), client=travelpayouts.fixture_client(), token="t", now=NOW)
    sys_session.commit()
    assert done >= 1
    assert ("notify", {"route_id": str(rid)}) in _queued(system_conn, "evaluate_price_alerts")


# --- the schedule -------------------------------------------------------------------------------------------------------


def test_the_leader_schedule_has_the_price_and_reminder_jobs_and_no_agent_job(db_urls):
    app = worker_app.build_app(_settings(db_urls))
    try:
        crons = {k[0]: p.cron for k, p in app.scheduled_registry.periodic_tasks.items()}
        assert crons["refresh_cached_fares"] == "17 */6 * * *"
        assert {"send_predeparture_reminder", "build_digest", "send_trial_ending_reminder"} <= set(crons)
        assert "run_agent" not in crons and run_agent.SCHEDULE is None
        assert app.tasks["evaluate_price_alerts"].queue == "notify"
        assert scan_due_routes.CHECK_JOB == "check_fare_route"  # the scan enqueues price checks only
    finally:
        app.sqlalchemy_engine.dispose()
        app.fairness_engine.dispose()
