# ruff: noqa: E501  (long SQL strings)
"""WF-015: row-level security as the second lock, tested as hermi_api_login with the app layer out of the way."""


import psycopg
import pytest
from sqlalchemy import create_engine, text

from hermi import db


def _app(db_urls):
    return psycopg.connect(db.psycopg_url(db_urls["app"]))


def _seed(system_conn, make_user):
    a, _ = make_user()
    b, _ = make_user()
    ta = system_conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'A', 'USD') RETURNING id", (a,)).fetchone()[0]
    tb = system_conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'B', 'USD') RETURNING id", (b,)).fetchone()[0]
    return a, b, ta, tb


def test_unset_session_variable_returns_zero_rows(db_urls, system_conn, make_user):
    _seed(system_conn, make_user)
    with _app(db_urls) as c:  # app.user_id was never set on this connection
        for t in ("trips", "trip_members", "users"):
            assert c.execute(f"SELECT count(*) FROM {t}").fetchone() == (0,)


def test_forced_bug_unfiltered_query_still_sees_only_own_tenant(db_urls, system_conn, make_user):
    a, b, ta, tb = _seed(system_conn, make_user)
    engine = create_engine(db.sqlalchemy_url(db_urls["app"]))
    try:
        with db.request_transaction(engine, a) as s:  # no tenant filter at all, as if the app check were removed
            assert {r[0] for r in s.execute(text("SELECT id FROM trips"))} == {ta}
            assert s.execute(text("UPDATE trips SET name = 'x' WHERE id = :t"), {"t": tb}).rowcount == 0
            assert s.execute(text("SELECT count(*) FROM users WHERE id = :b"), {"b": b}).scalar() == 0
    finally:
        engine.dispose()


def test_user_id_does_not_leak_to_the_next_transaction_on_a_pooled_connection(db_urls, system_conn, make_user):
    a, _, ta, _ = _seed(system_conn, make_user)
    engine = create_engine(db.sqlalchemy_url(db_urls["app"]), pool_size=1, max_overflow=0)
    try:
        with db.request_transaction(engine, a) as s:
            assert s.execute(text("SELECT count(*) FROM trips")).scalar() >= 1
        with engine.connect() as c:  # same pooled connection, no request_transaction
            assert c.execute(text("SELECT count(*) FROM trips")).scalar() == 0
            assert c.execute(text("SELECT app_user_id()")).scalar() is None
    finally:
        engine.dispose()


def test_startup_refuses_when_a_table_loses_force(db_urls):
    migrate = psycopg.connect(db.psycopg_url(db_urls["migrate"]), autocommit=True)
    app = create_engine(db.sqlalchemy_url(db_urls["app"]))
    try:
        with app.connect() as c:
            db.assert_rls_forced(c)  # passes at head
        migrate.execute("ALTER TABLE trip_members NO FORCE ROW LEVEL SECURITY")
        with app.connect() as c, pytest.raises(db.MigrationError, match="trip_members"):
            db.assert_rls_forced(c)
    finally:
        migrate.execute("ALTER TABLE trip_members FORCE ROW LEVEL SECURITY")
        migrate.close()
        app.dispose()


def test_startup_refuses_when_a_table_without_trip_or_user_id_loses_force(db_urls):
    migrate = psycopg.connect(db.psycopg_url(db_urls["migrate"]), autocommit=True)
    app = create_engine(db.sqlalchemy_url(db_urls["app"]))
    try:
        migrate.execute("ALTER TABLE trips NO FORCE ROW LEVEL SECURITY")
        with app.connect() as c, pytest.raises(db.MigrationError, match="trips"):
            db.assert_rls_forced(c)
    finally:
        migrate.execute("ALTER TABLE trips FORCE ROW LEVEL SECURITY")
        migrate.close()
        app.dispose()


def test_open_app_engine_refuses_the_migrate_login(db_urls):
    class S:
        database_pool_size = 1
        database_max_overflow = 0
        database_statement_timeout_ms = 5000

        def __init__(self, url):
            self.url = url

        def require(self, _k):
            return self.url

    with pytest.raises(db.MigrationError):
        db.open_app_engine(S(db_urls["migrate"]))
