# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-022.1: revision 0005_ai (03 sections 5.6, 7.4, 9, 10) with Procrastinate's schema and job_heartbeats.

Constraints are exercised as the migrate login (the owner), because grants land in 0014_rls.
The schema-vs-DDL comparison for 5.6 lives in test_migrations_trips_people.py (it spans 0002 to 0005).
"""

import uuid

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import APP_URL, MIGRATE_URL, _alembic_cfg, _need_db

from hermi import db


@pytest.fixture
def conn():
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as c:
        yield c


def _user(c):
    return c.execute(
        "INSERT INTO users (email) VALUES (%s) RETURNING id", (f"{uuid.uuid4().hex[:8]}@example.com",)
    ).fetchone()[0]


def _run(c, kind="research_question"):
    owner = _user(c)
    tid = c.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id",
        (owner,),
    ).fetchone()[0]
    rid = c.execute(
        "INSERT INTO runs (trip_id, user_id, kind) VALUES (%s, %s, %s) RETURNING id", (tid, owner, kind)
    ).fetchone()[0]
    return owner, tid, rid


def test_chain_is_linear_and_single_head():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0005_ai").down_revision == "0004_trips_people"
    assert len(s.get_heads()) == 1


def test_objects_exist_and_round_trip(conn):
    for n in "runs run_events ai_usage provider_calls provider_call_rollups shared_research_cache".split():
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n
    row = conn.execute(
        "SELECT to_regproc('my_provider_spend_micros'), to_regproc('ensure_month_partitions'), "
        "to_regproc('drop_old_partitions'), to_regproc('procrastinate_defer_jobs_v1'), "
        "to_regclass('procrastinate_jobs'), to_regclass('procrastinate_workers'), "
        "to_regclass('procrastinate_events'), to_regclass('procrastinate_periodic_defers'), "
        "to_regclass('job_heartbeats'), to_regtype('run_kind'), to_regtype('run_status'), "
        "to_regtype('usage_state'), to_regtype('run_trigger')"
    ).fetchone()
    assert all(r is not None for r in row)
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0004_trips_people")
    assert conn.execute(
        "SELECT to_regclass('runs'), to_regclass('provider_calls'), to_regproc('ensure_month_partitions'), "
        "to_regproc('my_provider_spend_micros'), to_regproc('procrastinate_defer_jobs_v1'), "
        "to_regclass('procrastinate_jobs'), to_regclass('job_heartbeats'), to_regtype('run_kind'), "
        "to_regtype('procrastinate_job_status')"
    ).fetchone() == (None,) * 9
    assert (
        conn.execute(
            "SELECT count(*) FROM pg_proc WHERE proname LIKE 'procrastinate%'"
        ).fetchone()[0]
        == 0
    )
    command.upgrade(cfg, "head")
    assert conn.execute("SELECT to_regclass('runs')").fetchone()[0]


def test_first_partitions_exist_for_both_log_tables(conn):
    for parent in ("run_events", "provider_calls"):
        kids = {
            r[0]
            for r in conn.execute(
                "SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid WHERE i.inhparent = %s::regclass",
                (parent,),
            )
        }
        # previous month, current month, three ahead, plus the default
        assert len(kids) == 6, (parent, kids)
        assert f"{parent}_default" in kids
        month = conn.execute("SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY_MM')").fetchone()[0]
        assert f"{parent}_{month}" in kids


def test_ensure_month_partitions_is_idempotent_and_rows_route(conn):
    assert conn.execute("SELECT ensure_month_partitions('provider_calls', 3)").fetchone() == (0,)
    assert conn.execute("SELECT ensure_month_partitions('provider_calls', 4)").fetchone() == (1,)
    month = conn.execute("SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY_MM')").fetchone()[0]
    conn.execute("INSERT INTO provider_calls (provider, endpoint, ok) VALUES ('serpapi', 'search', true)")
    assert conn.execute(f"SELECT count(*) FROM provider_calls_{month}").fetchone() == (1,)
    # A row with no partition lands in the default one.
    conn.execute(
        "INSERT INTO provider_calls (provider, endpoint, ok, created_at) VALUES ('serpapi', 'search', true, '2001-01-01')"
    )
    assert conn.execute("SELECT count(*) FROM provider_calls_default").fetchone() == (1,)


def test_drop_old_partitions_drops_only_old_months(conn):
    # keep 0 months: only the previous month is older than the current one.
    assert conn.execute("SELECT drop_old_partitions('run_events', 0)").fetchone() == (1,)
    assert conn.execute("SELECT drop_old_partitions('run_events', 0)").fetchone() == (0,)
    assert conn.execute("SELECT to_regclass('run_events_default')").fetchone()[0]
    assert conn.execute("SELECT drop_old_partitions('provider_calls', 12)").fetchone() == (0,)


def test_run_events_partitioned_insert_and_keys(conn):
    _, tid, rid = _run(conn)
    conn.execute(
        "INSERT INTO run_events (run_id, trip_id, seq, type, summary) VALUES (%s, %s, 1, 'info', 'hi')",
        (rid, tid),
    )
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(
            "INSERT INTO run_events (run_id, trip_id, seq, ts, type, summary) "
            "SELECT run_id, trip_id, seq, ts, type, summary FROM run_events"
        )
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO run_events (run_id, trip_id, seq, type, summary) VALUES (%s, %s, 2, 'nope', 'x')",
            (rid, tid),
        )
    # The events go with the run.
    conn.execute("DELETE FROM runs WHERE id = %s", (rid,))
    assert conn.execute("SELECT count(*) FROM run_events").fetchone() == (0,)


def test_runs_rules(conn):
    owner, tid, rid = _run(conn, "deep_research")
    assert conn.execute(
        "SELECT status, provider, trigger, cost_usd_micros, cancel_requested FROM runs WHERE id = %s", (rid,)
    ).fetchone() == ("queued", "anthropic_api", "manual", 0, False)
    # One active agent run per account.
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("INSERT INTO runs (trip_id, user_id, kind) VALUES (%s, %s, 'fare_hunt')", (tid, owner))
    # A finished run needs finished_at.
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE runs SET status = 'failed' WHERE id = %s", (rid,))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE runs SET provider = 'openai' WHERE id = %s", (rid,))


def test_ai_usage_and_cache_checks(conn):
    ins = "INSERT INTO ai_usage (action, idempotency_key, credits_reserved, credits_charged, state, settled_at) VALUES ('research', %s, %s, %s, %s, %s)"
    conn.execute(ins, ("k1", 8, 0, "reserved", None))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ins, ("k1", 8, 0, "reserved", None))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(ins, ("k2", 1, 2, "reserved", None))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(ins, ("k3", 1, 1, "settled", None))
    conn.execute(
        "INSERT INTO shared_research_cache (key, kind, provider, params, response, expires_at, stale_until) "
        "VALUES (%s, 'destination_brief', 'anthropic', '{}', '{}', now(), now())",
        ("a" * 64,),
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO shared_research_cache (key, kind, provider, params, response, expires_at, stale_until) "
            "VALUES (%s, 'destination_brief', 'anthropic', '{}', '{}', now() + interval '1 day', now())",
            ("b" * 64,),
        )


def test_my_provider_spend_micros_is_definer_and_sums_own_non_claude_spend(conn):
    row = conn.execute(
        "SELECT pg_get_userbyid(proowner), prosecdef, proconfig::text, "
        "has_function_privilege('hermi_app', oid, 'EXECUTE'), has_function_privilege('public', oid, 'EXECUTE') "
        "FROM pg_proc WHERE proname = 'my_provider_spend_micros'"
    ).fetchone()
    assert row[0] == "hermi_definer" and row[1] is True and "search_path=public" in row[2]
    assert (row[3], row[4]) == (True, False)
    conn.execute("GRANT SELECT ON provider_calls TO hermi_definer")  # 0014 grants this
    me, other = _user(conn), _user(conn)
    ins = "INSERT INTO provider_calls (provider, endpoint, ok, user_id, cost_usd_micros) VALUES (%s, 'x', true, %s, %s)"
    conn.execute(ins, ("serpapi", me, 5000))
    conn.execute(ins, ("geoapify", me, 2000))
    conn.execute(ins, ("anthropic", me, 99999))  # Claude cost lives in ai_usage
    conn.execute(ins, ("serpapi", other, 7000))
    with psycopg.connect(db.psycopg_url(APP_URL), autocommit=True) as app:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            app.execute("SELECT my_provider_spend_micros('2000-01-01')")
        app.execute("SELECT set_config('app.user_id', %s, false)", (str(me),))
        assert app.execute("SELECT my_provider_spend_micros('2000-01-01')").fetchone() == (7000,)
        assert app.execute("SELECT my_provider_spend_micros(now() + interval '1 day')").fetchone() == (0,)


def test_procrastinate_schema_and_job_heartbeats(conn):
    assert conn.execute(
        "SELECT count(*) FROM pg_proc WHERE proname IN ('procrastinate_defer_jobs_v1', 'procrastinate_fetch_job_v2', "
        "'procrastinate_finish_job_v1', 'procrastinate_register_worker_v1', 'procrastinate_update_heartbeat_v1')"
    ).fetchone()[0] >= 4
    # Defer a job through the library function, then register a worker and read the view.
    job = conn.execute(
        "SELECT (procrastinate_defer_jobs_v1(ARRAY[ROW('ai', 'demo', 0, NULL, NULL, '{}'::jsonb, NULL)::procrastinate_job_to_defer_v1]))"
    ).fetchall()
    assert len(job) == 1
    assert conn.execute("SELECT count(*) FROM procrastinate_jobs WHERE status = 'todo'").fetchone() == (1,)
    wid = conn.execute("SELECT procrastinate_register_worker_v1()").fetchone()[0]
    row = conn.execute(
        "SELECT worker_id, last_heartbeat, seconds_since_heartbeat FROM job_heartbeats WHERE worker_id = %s",
        (wid,),
    ).fetchone()
    assert row[0] == wid and row[2] >= 0
    # The API login can read nothing of it yet (0014 grants), but the view exists for the owner.
    with psycopg.connect(db.psycopg_url(APP_URL), autocommit=True) as app:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            app.execute("SELECT * FROM procrastinate_jobs")
