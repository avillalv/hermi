# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-021.1: revision 0009_flights (03 sections 5.11, 5.12, 10).

Constraints are exercised as the migrate login (the owner), because grants land in 0014_rls.
The schema-vs-DDL comparison for 5.11 and 5.12 lives in test_migrations_trips_people.py (it spans 0002 to 0009).
"""

import uuid
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import MIGRATE_URL, _alembic_cfg, _need_db

from hermi import db

TABLES = "flight_routes fare_observations trip_fare_links chosen_flights route_price_insights booked_fare_drops price_alerts".split()
TRIP_SCOPED = "flight_routes trip_fare_links chosen_flights price_alerts".split()
ALERT = "INSERT INTO price_alerts (trip_id, route_id, user_id, threshold_minor, currency) VALUES (%s, %s, %s, %s, 'EUR')"
LINK = "INSERT INTO trip_fare_links (trip_id, route_id, observation_id) VALUES (%s, %s, %s)"


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
    with pytest.raises(psycopg.errors.CheckViolation) as e:
        yield
    assert e.value.diag.constraint_name == name


def _user(c):
    return c.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (f"{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]


def _trip(c, owner):
    return c.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)
    ).fetchone()[0]


def _insert(c, table, cols):
    return c.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id", tuple(cols.values())
    ).fetchone()[0]


def _route(c, trip, **kw):
    return _insert(c, "flight_routes", {
        "trip_id": trip, "origin_codes": ["LIS"], "destination_codes": ["JFK"], "depart_from": "2027-05-01",
        "depart_to": "2027-05-10", "return_from": "2027-05-20", "return_to": "2027-05-25", **kw,
    })


def _obs(c, **kw):
    return _insert(c, "fare_observations", {
        "search_key": uuid.uuid4().hex * 2, "origin": "LIS", "destination": "JFK", "depart_date": "2027-05-03",
        "return_date": "2027-05-22", "source": "travelpayouts", "confidence": "cached", "currency": "EUR",
        "price_total_minor": 40000, "observed_at": "2099-01-01", "expires_at": "2099-01-02", **kw,
    })


def _chosen(c, trip, route, **kw):
    return _insert(c, "chosen_flights", {
        "trip_id": trip, "route_id": route, "origin": "LIS", "destination": "JFK", "depart_date": "2027-05-03",
        "return_date": "2027-05-22", "price_total_minor": 40000, "currency": "EUR", "source": "travelpayouts",
        "observed_at": "2027-01-01", **kw,
    })


def test_chain_is_linear_and_single_head():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0009_flights").down_revision == "0008_affiliate"
    assert len(s.get_heads()) == 1


def test_objects_exist_and_round_trip(conn):
    for n in TABLES:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0008_affiliate")
    assert conn.execute(
        "SELECT to_regclass('flight_routes'), to_regclass('booked_fare_drops'), to_regclass('price_alerts'), "
        "to_regtype('cabin_class'), to_regtype('trip_type'), to_regtype('fare_confidence')"
    ).fetchone() == (None,) * 6
    command.upgrade(cfg, "head")
    assert conn.execute("SELECT to_regclass('flight_routes')").fetchone()[0]


def test_trip_scoped_tables_have_trip_id_and_lookup_indexes(conn):
    for t in TRIP_SCOPED:
        assert conn.execute(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = %s AND column_name = 'trip_id'", (t,)
        ).fetchone() == ("NO",), t
    for ix in (
        "ix_flight_routes_trip", "ix_flight_routes_live_due", "ix_flight_routes_due", "ix_fare_observations_lookup",
        "ix_fare_observations_key_fresh", "ix_fare_observations_observed", "ix_trip_fare_links_route",
        "ix_trip_fare_links_trip", "ix_chosen_flights_trip", "ix_chosen_flights_drop_watch",
        "uq_route_price_insights_key", "ix_price_alerts_active", "ix_price_alerts_user",
    ):
        assert conn.execute("SELECT to_regclass(%s)", (ix,)).fetchone()[0], ix
    for t in ("fare_observations", "route_price_insights"):  # shared by all users, not trip-scoped
        assert conn.execute(
            "SELECT count(*) FROM information_schema.columns WHERE table_name = %s AND column_name = 'trip_id'", (t,)
        ).fetchone() == (0,), t


def test_view_is_security_invoker(conn):
    assert conn.execute("SELECT reloptions FROM pg_class WHERE relname = 'booked_fare_drops'").fetchone()[0] == [
        "security_invoker=true"
    ]


def test_flight_route_checks_version_and_updated_at(conn):
    t = _trip(conn, _user(conn))
    for kw, name in (
        ({"depart_to": "2027-04-01"}, "ck_flight_routes_depart_window"),
        ({"adults": 0}, "ck_flight_routes_passengers"),
        ({"return_to": None}, "ck_flight_routes_return_pair"),
        ({"min_nights": 3}, "ck_flight_routes_nights_pair"),
        ({"trip_type": "one_way"}, "ck_flight_routes_return_rule"),
        ({"alert_price_minor": 100}, "ck_flight_routes_alert_currency"),
        ({"sources": ["booking"]}, "ck_flight_routes_sources"),
    ):
        with _check(name):
            _route(conn, t, **kw)
    with pytest.raises(psycopg.errors.CheckViolation):
        _route(conn, t, origin_codes=[])
    with pytest.raises(psycopg.errors.CheckViolation):
        _route(conn, t, origin_codes=["lis"])
    r = _route(conn, t)
    assert conn.execute("SELECT version FROM flight_routes WHERE id = %s", (r,)).fetchone() == (1,)
    conn.execute("UPDATE flight_routes SET label = 'x' WHERE id = %s", (r,))
    assert conn.execute("SELECT version FROM flight_routes WHERE id = %s", (r,)).fetchone() == (2,)


def test_fare_observation_checks(conn):
    with _check("ck_fare_observations_source"):
        _obs(conn, source="booking")
    with _check("ck_fare_observations_agent_evidence"):
        _obs(conn, source="agent")
    with pytest.raises(psycopg.errors.CheckViolation):
        _obs(conn, price_total_minor=0)
    assert _obs(conn, source="agent", source_url="https://example.com/fare")
    k = uuid.uuid4().hex * 2
    _obs(conn, search_key=k)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _obs(conn, search_key=k)


def test_links_cascade_and_same_trip_foreign_key(conn):
    u = _user(conn)
    t1, t2 = _trip(conn, u), _trip(conn, u)
    r = _route(conn, t1)
    o = _obs(conn)
    # The (route_id, trip_id) key stops a row from pointing at another trip's route.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(LINK, (t2, r, o))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _chosen(conn, t2, r)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(ALERT, (t2, r, u, 100))
    conn.execute(LINK, (t1, r, o))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(LINK, (t1, r, o))
    c = _chosen(conn, t1, r, observation_id=o)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _chosen(conn, t1, r)
    conn.execute(ALERT, (t1, r, u, 100))

    # Deleting an observation drops the link and keeps the chosen flight (its snapshot).
    conn.execute("DELETE FROM fare_observations WHERE id = %s", (o,))
    assert conn.execute("SELECT count(*) FROM trip_fare_links").fetchone() == (0,)
    assert conn.execute("SELECT observation_id FROM chosen_flights WHERE id = %s", (c,)).fetchone() == (None,)

    # Deleting the trip removes everything under it.
    conn.execute("DELETE FROM trips WHERE id = %s", (t1,))
    for t in TRIP_SCOPED:
        assert conn.execute(f"SELECT count(*) FROM {t}").fetchone() == (0,), t


def test_route_delete_cascades_to_children(conn):
    u = _user(conn)
    t = _trip(conn, u)
    r = _route(conn, t)
    conn.execute(LINK, (t, r, _obs(conn)))
    _chosen(conn, t, r)
    conn.execute(ALERT, (t, r, u, 100))
    conn.execute("DELETE FROM flight_routes WHERE id = %s", (r,))
    for tbl in ("trip_fare_links", "chosen_flights", "price_alerts"):
        assert conn.execute(f"SELECT count(*) FROM {tbl}").fetchone() == (0,), tbl
    assert conn.execute("SELECT count(*) FROM fare_observations").fetchone() == (1,)  # shared rows stay


def test_user_deletion_keeps_chosen_flight_and_removes_alert(conn):
    owner, other = _user(conn), _user(conn)
    t = _trip(conn, owner)
    r = _route(conn, t, created_by=other)
    c = _chosen(conn, t, r, chosen_by=other, booked_by=other, booked_at="2027-01-02")
    conn.execute(ALERT, (t, r, other, 100))
    conn.execute("DELETE FROM users WHERE id = %s", (other,))
    assert conn.execute("SELECT chosen_by, booked_by FROM chosen_flights WHERE id = %s", (c,)).fetchone() == (None, None)
    assert conn.execute("SELECT created_by FROM flight_routes WHERE id = %s", (r,)).fetchone() == (None,)
    assert conn.execute("SELECT count(*) FROM price_alerts").fetchone() == (0,)


def test_chosen_flight_paid_checks(conn):
    t = _trip(conn, _user(conn))
    r = _route(conn, t)
    for kw, name in (
        ({"paid_minor": 100}, "ck_chosen_flights_paid"),
        ({"paid_minor": 100, "paid_currency": "EUR"}, "ck_chosen_flights_paid_booked"),
        ({"paid_source": "manual"}, "ck_chosen_flights_paid_source"),
        ({"paid_minor": 100, "paid_currency": "EUR", "booked_at": "2027-01-02", "paid_source": "web"}, "ck_chosen_flights_paid_source"),
    ):
        with _check(name):
            _chosen(conn, t, r, **kw)
    with pytest.raises(psycopg.errors.CheckViolation):
        _chosen(conn, t, r, price_total_minor=0)


def test_price_alert_checks(conn):
    u = _user(conn)
    t = _trip(conn, u)
    r = _route(conn, t)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(ALERT, (t, r, u, 0))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO price_alerts (trip_id, route_id, user_id, threshold_minor, currency, basis) VALUES (%s, %s, %s, 5, 'EUR', 'hot')",
            (t, r, u),
        )
    conn.execute(ALERT, (t, r, u, 5))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(ALERT, (t, r, u, 6))


def test_route_price_insights_unique_key_treats_null_return_as_one(conn):
    sql = (
        "INSERT INTO route_price_insights (origin, destination, depart_date, return_date, currency, observed_at, expires_at) "
        "VALUES ('LIS', 'JFK', '2027-05-03', %s, 'EUR', now(), now())"
    )
    conn.execute(sql, (None,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(sql, (None,))
    conn.execute(sql, ("2027-05-20",))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO route_price_insights (origin, destination, depart_date, currency, price_level, observed_at, expires_at) "
            "VALUES ('LIS', 'JFK', '2027-06-03', 'EUR', 'cheap', now(), now())"
        )


def test_booked_fare_drops_view_matches_like_with_like(conn):
    u = _user(conn)
    t = _trip(conn, u)
    r = _route(conn, t)
    fut = "2099-05-03"
    c = _chosen(
        conn, t, r, depart_date=fut, return_date=None, airlines=["TP"], booked_by=u, booked_at="2027-01-02",
        paid_minor=50000, paid_currency="EUR",
    )
    other = _obs(conn, depart_date=fut, return_date=None, airlines=["LH"], price_total_minor=30000)
    same = _obs(conn, depart_date=fut, return_date=None, airlines=["TP"], price_total_minor=40000)
    conn.execute("UPDATE fare_observations SET observed_at = now() WHERE id IN (%s, %s)", (other, same))
    conn.execute(LINK, (t, r, other))
    assert conn.execute("SELECT count(*) FROM booked_fare_drops").fetchone() == (0,)  # a different airline is not a drop
    conn.execute(LINK, (t, r, same))
    assert conn.execute(
        "SELECT chosen_flight_id, user_id, current_minor, drop_minor, drop_pct FROM booked_fare_drops"
    ).fetchall() == [(c, u, 40000, 10000, 20.0)]
    conn.execute("UPDATE trip_fare_links SET hidden = true WHERE observation_id = %s", (same,))
    assert conn.execute("SELECT count(*) FROM booked_fare_drops").fetchone() == (0,)
