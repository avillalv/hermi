# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-020.1: revisions 0012_admin_privacy and 0013_notifications_samples (03 sections 5.16 to 5.20, 10).

Constraints are exercised as the migrate login (the owner) at revision 0013 (PRE_RLS), before 0014_rls binds the owner with FORCE.
The schema-vs-DDL comparison lives in test_migrations_trips_people.py (it spans 0002 to 0013).
"""

import re
import uuid
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import MIGRATE_URL, PRE_RLS, _alembic_cfg, _need_db
from tests.test_migrations_trips_people import SPEC

from hermi import db

ADMIN = "admin_users feature_flags kill_switches audit_log support_tickets content_reports consents data_exports deletion_requests rate_limit_counters idempotency_keys".split()
LATER = "notifications sample_trips plan_verifications plan_verification_items".split()


@pytest.fixture
def conn():
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, PRE_RLS)
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as c:
        yield c


@contextmanager
def _check(name):
    with pytest.raises(psycopg.errors.CheckViolation) as e:
        yield
    assert e.value.diag.constraint_name == name


def _user(c):
    return c.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (f"{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]


def _trip(c, owner):
    return c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)).fetchone()[0]


def _insert(c, table, cols):
    return c.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING 1", tuple(cols.values())
    ).fetchone()[0]


def test_chain_is_linear_and_single_head():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0012_admin_privacy").down_revision == "0011_checklist_notes"
    assert s.get_revision("0013_notifications_samples").down_revision == "0012_admin_privacy"
    assert len(s.get_heads()) == 1


def test_objects_exist_and_round_trip(conn):
    for n in ADMIN + LATER:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n
    assert conn.execute("SELECT relpersistence FROM pg_class WHERE relname = 'rate_limit_counters'").fetchone() == ("u",)
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0012_admin_privacy")
    assert all(conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0] is None for n in LATER)
    assert conn.execute("SELECT to_regclass('audit_log')").fetchone()[0]
    command.downgrade(cfg, "0011_checklist_notes")
    for n in ADMIN:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0] is None, n
    assert conn.execute("SELECT to_regtype('admin_role')").fetchone() == (None,)
    assert conn.execute("SELECT count(*) FROM pg_proc WHERE proname IN ('audit_log_immutable', 'audit_log_no_truncate')").fetchone() == (0,)
    assert conn.execute("SELECT to_regclass('notes')").fetchone()[0]
    command.upgrade(cfg, PRE_RLS)
    assert conn.execute("SELECT to_regclass('plan_verification_items')").fetchone()[0]


def test_no_table_in_03_is_missing(conn):
    text = SPEC.read_text(encoding="utf-8")
    ddl = text[text.index("### 5.16 Admin") : text.index("## 6. Row-level security")]
    names = set(re.findall(r"CREATE (?:UNLOGGED )?TABLE (\w+)", ddl))
    assert names == set(ADMIN + LATER)
    for n in names:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n


def test_audit_log_is_append_only(conn):
    conn.execute("INSERT INTO audit_log (actor_type, action) VALUES ('system', 'x')")
    for sql in ("UPDATE audit_log SET action = 'y'", "DELETE FROM audit_log", "TRUNCATE audit_log"):
        with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
            conn.execute(sql)
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone() == (1,)
    with _check("ck_audit_log_actor_type"):
        conn.execute("INSERT INTO audit_log (actor_type, action) VALUES ('bot', 'x')")
    with _check("ck_audit_log_result"):
        conn.execute("INSERT INTO audit_log (actor_type, action, result) VALUES ('user', 'x', 'maybe')")
    with _check("ck_audit_log_retention"):
        conn.execute("INSERT INTO audit_log (actor_type, action, retention_class) VALUES ('user', 'x', 'forever')")


def test_feature_flag_and_kill_switch_checks(conn):
    with _check("ck_feature_flags_key"):
        _insert(conn, "feature_flags", {"key": "Bad-Key"})
    with _check("ck_feature_flags_kind_prefix"):
        _insert(conn, "feature_flags", {"key": "exp_abc"})  # kind defaults to flag
    _insert(conn, "feature_flags", {"key": "exp_abc", "kind": "experiment"})
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, "feature_flags", {"key": "good_one", "rollout_pct": 101})
    with _check("ck_kill_switches_key"):
        _insert(conn, "kill_switches", {"key": "Bad Key"})
    with _check("ck_kill_switches_engaged"):
        _insert(conn, "kill_switches", {"key": "ai.all", "engaged": True})
    admin = _user(conn)
    with _check("ck_kill_switches_expiry"):
        conn.execute("INSERT INTO kill_switches (key, engaged, engaged_at, engaged_by) VALUES ('signups', true, now(), %s)", (admin,))
    conn.execute("INSERT INTO kill_switches (key, engaged, engaged_at, engaged_by) VALUES ('provider.serpapi', true, now(), %s)", (admin,))
    _insert(conn, "kill_switches", {"key": f"user:{uuid.uuid4()}"})
    assert conn.execute("SELECT count(*) FROM feature_flags").fetchone() == (1,)  # nothing is seeded here


def test_support_tickets_and_reports(conn):
    for kw, name in (
        ({"category": "x"}, "ck_support_tickets_category"),
        ({"status": "x"}, "ck_support_tickets_status"),
        ({"priority": "x"}, "ck_support_tickets_priority"),
        ({"source": "x"}, "ck_support_tickets_source"),
    ):
        with _check(name):
            _insert(conn, "support_tickets", {"subject": "s", "email": "a@example.com", **kw})
    with _check("ck_support_tickets_contact"):
        _insert(conn, "support_tickets", {"subject": "s"})
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, "support_tickets", {"subject": "", "email": "a@example.com"})
    _insert(conn, "support_tickets", {"subject": "s", "email": "a@example.com"})
    assert conn.execute("SELECT to_regclass('ix_support_tickets_tags')").fetchone()[0]
    with _check("ck_content_reports_target_ref"):
        _insert(conn, "content_reports", {"target_type": "shared_trip", "reason": "spam"})
    with _check("ck_content_reports_reason"):
        _insert(conn, "content_reports", {"target_type": "research_cache", "cache_key": "a" * 64, "reason": "rude"})
    with _check("ck_content_reports_handled"):
        _insert(conn, "content_reports", {"target_type": "research_cache", "cache_key": "a" * 64, "reason": "spam", "status": "dismissed"})
    _insert(conn, "content_reports", {"target_type": "research_cache", "cache_key": "a" * 64, "reason": "spam"})


def test_privacy_tables(conn):
    u = _user(conn)
    with _check("ck_consents_kind"):
        _insert(conn, "consents", {"user_id": u, "kind": "x", "version": "1", "granted": True})
    with _check("ck_consents_source"):
        _insert(conn, "consents", {"user_id": u, "kind": "terms", "version": "1", "granted": True, "source": "x"})
    with _check("ck_data_exports_status"):
        _insert(conn, "data_exports", {"user_id": u, "status": "x"})
    with _check("ck_deletion_requests_status"):
        _insert(conn, "deletion_requests", {"user_id": u, "status": "x"})
    _insert(conn, "deletion_requests", {"user_id": u})
    with pytest.raises(psycopg.errors.UniqueViolation):  # one open request per user
        _insert(conn, "deletion_requests", {"user_id": u})
    conn.execute("DELETE FROM users WHERE id = %s", (u,))  # no FK: the request survives the purge
    assert conn.execute("SELECT count(*) FROM deletion_requests").fetchone() == (1,)


def test_idempotency_keys_and_rate_limits(conn):
    u = _user(conn)
    base = {"user_id": u, "method": "POST", "path": "/x", "request_hash": "a" * 64}
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, "idempotency_keys", {**base, "key": "short"})
    with _check("ck_idempotency_keys_state"):
        _insert(conn, "idempotency_keys", {**base, "key": "k" * 8, "state": "x", "status_code": 200})
    with _check("ck_idempotency_keys_done"):
        _insert(conn, "idempotency_keys", {**base, "key": "k" * 8, "state": "completed"})
    _insert(conn, "idempotency_keys", {**base, "key": "k" * 8})
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insert(conn, "idempotency_keys", {**base, "key": "k" * 8})
    conn.execute("INSERT INTO rate_limit_counters (bucket, window_start) VALUES ('b', now())")
    assert conn.execute("SELECT count FROM rate_limit_counters").fetchone() == (1,)


def test_notifications(conn):
    u = _user(conn)
    base = {"user_id": u, "kind": "price_drop", "dedupe_key": "d1", "title": "t"}
    with _check("ck_notifications_kind"):
        _insert(conn, "notifications", {**base, "kind": "spam"})
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, "notifications", {**base, "title": ""})
    _insert(conn, "notifications", base)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insert(conn, "notifications", base)
    conn.execute("DELETE FROM users WHERE id = %s", (u,))
    assert conn.execute("SELECT count(*) FROM notifications").fetchone() == (0,)


def test_sample_trips(conn):
    t = _trip(conn, _user(conn))
    with pytest.raises(psycopg.errors.CheckViolation):
        _insert(conn, "sample_trips", {"slug": "Bad Slug", "trip_id": t, "title": "x"})
    with _check("ck_sample_trips_published"):
        _insert(conn, "sample_trips", {"slug": "ok", "trip_id": t, "title": "x", "status": "published"})
    with _check("ck_sample_trips_status"):
        _insert(conn, "sample_trips", {"slug": "ok", "trip_id": t, "title": "x", "status": "live"})
    _insert(conn, "sample_trips", {"slug": "ok", "trip_id": t, "title": "x"})
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insert(conn, "sample_trips", {"slug": "ok2", "trip_id": t, "title": "x"})
    conn.execute("DELETE FROM trips WHERE id = %s", (t,))
    assert conn.execute("SELECT count(*) FROM sample_trips").fetchone() == (0,)


def test_plan_verifications_and_items(conn):
    u = _user(conn)
    t, t2 = _trip(conn, u), _trip(conn, u)
    pv = {"trip_id": t, "user_id": u}
    with _check("ck_plan_verifications_label"):
        _insert(conn, "plan_verifications", {**pv, "source_label": "x"})
    with _check("ck_plan_verifications_status"):
        _insert(conn, "plan_verifications", {**pv, "status": "x"})
    with _check("ck_plan_verifications_counts"):
        _insert(conn, "plan_verifications", {**pv, "green_count": 1})
    v = conn.execute("INSERT INTO plan_verifications (trip_id, user_id, items_found, items_selected) VALUES (%s, %s, 3, 2) RETURNING id", (t, u)).fetchone()[0]
    it = {"verification_id": v, "trip_id": t, "position": 0, "name": "Museum"}
    for kw, name in (
        ({"verdict": "green", "selected": True}, "ck_plan_verification_items_evidence"),
        ({"verdict": "red"}, "ck_plan_verification_items_checked"),
        ({"claimed_price_minor": 5}, "ck_plan_verification_items_claim_price"),
        ({"found_currency": "EUR"}, "ck_plan_verification_items_found_price"),
        ({"lat": 1.0}, "ck_plan_verification_items_lat_lon"),
        ({"verdict": "purple", "selected": True}, "ck_plan_verification_items_verdict"),
    ):
        with _check(name):
            _insert(conn, "plan_verification_items", {**it, **kw})
    _insert(conn, "plan_verification_items", it)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insert(conn, "plan_verification_items", it)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):  # trip must match the verification's trip
        _insert(conn, "plan_verification_items", {**it, "trip_id": t2, "position": 1})
    conn.execute("DELETE FROM plan_verifications WHERE id = %s", (v,))
    assert conn.execute("SELECT count(*) FROM plan_verification_items").fetchone() == (0,)
