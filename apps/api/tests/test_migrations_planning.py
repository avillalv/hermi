# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-021.2: revisions 0010_itinerary_lodging and 0011_checklist_notes (03 sections 5.13, 5.14, 5.15, 10).

Constraints are exercised as the migrate login (the owner) at revision 0013 (PRE_RLS), before 0014_rls binds the owner with FORCE.
The schema-vs-DDL comparison lives in test_migrations_trips_people.py (it spans 0002 to 0011).
"""

import uuid
from contextlib import contextmanager

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import MIGRATE_URL, PRE_RLS, _alembic_cfg, _need_db

from hermi import db

TABLES = "itinerary_days saved_places itinerary_items lodging_options lodging_votes saved_place_votes checklist_items notes".split()
VERSIONED = "itinerary_days itinerary_items lodging_options checklist_items notes".split()


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
    return c.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)
    ).fetchone()[0]


def _insert(c, table, cols):
    return c.execute(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id", tuple(cols.values())
    ).fetchone()[0]


def _place(c, trip, **kw):
    return _insert(c, "saved_places", {"trip_id": trip, "place_provider": "manual", "place_id": uuid.uuid4().hex, "name": "P", **kw})


def _item(c, trip, **kw):
    return _insert(c, "itinerary_items", {"trip_id": trip, "title": "Visit", **kw})


def _stay(c, trip, **kw):
    return _insert(c, "lodging_options", {"trip_id": trip, "title": "Flat", "added_via": "manual", **kw})


def _todo(c, trip, **kw):
    return _insert(c, "checklist_items", {"trip_id": trip, "kind": "esim", **kw})


def _note(c, trip, **kw):
    return _insert(c, "notes", {"trip_id": trip, **kw})


def _person(c, owner, trip):
    p = c.execute("INSERT INTO people (owner_user_id, name) VALUES (%s, 'Kid') RETURNING id", (owner,)).fetchone()[0]
    c.execute("INSERT INTO trip_people (trip_id, person_id, added_by) VALUES (%s, %s, %s)", (trip, p, owner))
    return p


def _import(c, user, trip):
    return _insert(c, "trip_imports", {"user_id": user, "trip_id": trip, "source": "ics_file"})


def test_chain_is_linear_and_single_head():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0010_itinerary_lodging").down_revision == "0009_flights"
    assert s.get_revision("0011_checklist_notes").down_revision == "0010_itinerary_lodging"
    assert len(s.get_heads()) == 1


def test_objects_exist_and_round_trip(conn):
    for n in TABLES:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0010_itinerary_lodging")
    assert conn.execute("SELECT to_regclass('checklist_items'), to_regclass('notes'), to_regtype('note_kind')").fetchone() == (None,) * 3
    assert conn.execute("SELECT to_regclass('itinerary_items')").fetchone()[0]
    command.downgrade(cfg, "0009_flights")
    assert conn.execute(
        "SELECT to_regclass('itinerary_days'), to_regclass('saved_places'), to_regclass('lodging_options'), "
        "to_regtype('item_status'), to_regtype('item_category'), to_regtype('lodging_status')"
    ).fetchone() == (None,) * 6
    command.upgrade(cfg, PRE_RLS)
    assert conn.execute("SELECT to_regclass('notes')").fetchone()[0]


def test_trip_id_everywhere_and_lookup_indexes(conn):
    for t in TABLES:
        assert conn.execute(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = %s AND column_name = 'trip_id'", (t,)
        ).fetchone() == ("NO",), t
    for t in VERSIONED:
        assert conn.execute(
            "SELECT is_nullable FROM information_schema.columns WHERE table_name = %s AND column_name = 'version'", (t,)
        ).fetchone() == ("NO",), t
    for ix in (
        "ix_saved_places_trip", "ix_itinerary_items_trip_day", "ix_itinerary_items_updated", "uq_itinerary_items_import_uid",
        "ix_itinerary_items_import", "uq_lodging_options_trip_url", "ix_lodging_options_trip", "ix_lodging_options_import",
        "ix_lodging_votes_trip", "ix_saved_place_votes_trip", "uq_checklist_items_trip_kind", "ix_checklist_items_trip",
        "ix_notes_trip", "ix_notes_run", "ix_notes_item", "ix_notes_day",
    ):
        assert conn.execute("SELECT to_regclass(%s)", (ix,)).fetchone()[0], ix


def test_version_and_updated_at_triggers(conn):
    t = _trip(conn, _user(conn))
    for table, mk in (("itinerary_items", _item), ("lodging_options", _stay), ("checklist_items", _todo), ("notes", _note)):
        i = mk(conn, t)
        assert conn.execute(f"SELECT version FROM {table} WHERE id = %s", (i,)).fetchone() == (1,), table
        conn.execute(f"UPDATE {table} SET created_at = created_at WHERE id = %s", (i,))
        assert conn.execute(f"SELECT version FROM {table} WHERE id = %s", (i,)).fetchone() == (2,), table
    conn.execute("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, '2027-05-01')", (t,))
    conn.execute("UPDATE itinerary_days SET title = 'x' WHERE trip_id = %s", (t,))
    assert conn.execute("SELECT version FROM itinerary_days").fetchone() == (2,)


def test_itinerary_checks(conn):
    t = _trip(conn, _user(conn))
    for kw, name in (
        ({"start_time": "10:00"}, "ck_itinerary_items_times_need_day"),
        ({"day": "2027-05-01", "end_time": "11:00"}, "ck_itinerary_items_end_needs_start"),
        ({"lat": 1.0}, "ck_itinerary_items_lat_lon"),
        ({"estimated_cost_minor": 100}, "ck_itinerary_items_cost"),
        ({"check_url": "https://e.com"}, "ck_itinerary_items_check"),
        ({"import_uid": "u1"}, "ck_itinerary_items_import"),
        ({"source": "scraper"}, "ck_itinerary_items_source"),
    ):
        with _check(name):
            _item(conn, t, **kw)
    with pytest.raises(psycopg.errors.CheckViolation):
        _item(conn, t, title="")
    with pytest.raises(psycopg.errors.CheckViolation):
        _item(conn, t, estimated_cost_minor=-1, cost_currency="EUR")
    with _check("ck_saved_places_lat_lon"):
        _place(conn, t, lat=1.0)
    _item(conn, t, day="2027-05-01", start_time="23:00", end_time="01:00")  # runs past midnight is allowed


def test_import_uid_dedupes_per_trip_and_import_fk(conn):
    u = _user(conn)
    t1, t2 = _trip(conn, u), _trip(conn, u)
    imp = _import(conn, u, t1)
    a = _item(conn, t1, source="import", import_uid="evt-1", import_id=imp)
    with pytest.raises(psycopg.errors.UniqueViolation):
        _item(conn, t1, source="import", import_uid="evt-1")
    _item(conn, t2, source="import", import_uid="evt-1")
    _item(conn, t1)
    _item(conn, t1)
    stay = _stay(conn, t1, import_id=imp, added_via="import")
    conn.execute("DELETE FROM trip_imports WHERE id = %s", (imp,))
    assert conn.execute("SELECT import_id FROM itinerary_items WHERE id = %s", (a,)).fetchone() == (None,)
    assert conn.execute("SELECT import_id FROM lodging_options WHERE id = %s", (stay,)).fetchone() == (None,)


def test_saved_place_unique_and_same_trip_item_link(conn):
    u = _user(conn)
    t1, t2 = _trip(conn, u), _trip(conn, u)
    p = _place(conn, t1, place_provider="geoapify", place_id="g1")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _place(conn, t1, place_provider="geoapify", place_id="g1")
    _place(conn, t2, place_provider="geoapify", place_id="g1")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        _item(conn, t2, saved_place_id=p)
    i = _item(conn, t1, saved_place_id=p)
    conn.execute("DELETE FROM saved_places WHERE id = %s", (p,))  # the item keeps its copy of the fields
    assert conn.execute("SELECT saved_place_id, title FROM itinerary_items WHERE id = %s", (i,)).fetchone() == (None, "Visit")


def test_day_destination_and_user_set_null(conn):
    owner, other = _user(conn), _user(conn)
    t = _trip(conn, owner)
    d = conn.execute("INSERT INTO trip_destinations (trip_id, position, name, lat, lon) VALUES (%s, 0, 'Lisbon', 38.7, -9.1) RETURNING id", (t,)).fetchone()[0]
    conn.execute("INSERT INTO itinerary_days (trip_id, day, destination_id, updated_by) VALUES (%s, '2027-05-01', %s, %s)", (t, d, other))
    i = _item(conn, t, created_by=other, updated_by=other)
    conn.execute("DELETE FROM trip_destinations WHERE id = %s", (d,))
    conn.execute("DELETE FROM users WHERE id = %s", (other,))
    assert conn.execute("SELECT destination_id, updated_by FROM itinerary_days").fetchone() == (None, None)
    assert conn.execute("SELECT created_by, updated_by FROM itinerary_items WHERE id = %s", (i,)).fetchone() == (None, None)
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, '2027-05-01')", (t,))
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO itinerary_days (trip_id, day, title) VALUES (%s, '2027-05-02', %s)", (t, "x" * 121))


def test_lodging_checks_and_url_unique(conn):
    u = _user(conn)
    t1, t2 = _trip(conn, u), _trip(conn, u)
    for kw, name in (
        ({"added_via": "scraper"}, "ck_lodging_options_added_via"),
        ({"check_in": "2027-05-05", "check_out": "2027-05-05"}, "ck_lodging_options_dates"),
        ({"lat": 1.0}, "ck_lodging_options_lat_lon"),
        ({"price_total_minor": 100}, "ck_lodging_options_price_currency"),
    ):
        with _check(name):
            _stay(conn, t1, **kw)
    with pytest.raises(psycopg.errors.CheckViolation):
        _stay(conn, t1, price_total_minor=-1, currency="EUR")
    _stay(conn, t1, url_normalized="https://x.com/a")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _stay(conn, t1, url_normalized="https://x.com/a")
    _stay(conn, t2, url_normalized="https://x.com/a")
    _stay(conn, t1)
    _stay(conn, t1)
    with pytest.raises(psycopg.errors.InvalidTextRepresentation):
        _stay(conn, t1, status="gone")


def test_votes_one_per_person_same_trip_and_cascade(conn):
    u = _user(conn)
    t1, t2 = _trip(conn, u), _trip(conn, u)
    p = _person(conn, u, t1)
    elsewhere = _person(conn, u, t2)
    s, pl = _stay(conn, t1), _place(conn, t1)
    lv = "INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)"
    pv = "INSERT INTO saved_place_votes (saved_place_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)"
    conn.execute(lv, (s, t1, p, u))
    conn.execute(pv, (pl, t1, p, u))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(lv, (s, t1, p, u))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(pv, (pl, t1, p, u))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):  # the person is not on that trip
        conn.execute(lv, (s, t1, elsewhere, u))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):  # the stay is not on that trip
        conn.execute(lv, (s, t2, elsewhere, u))
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(pv, (pl, t2, elsewhere, u))
    conn.execute("DELETE FROM lodging_options WHERE id = %s", (s,))
    conn.execute("DELETE FROM saved_places WHERE id = %s", (pl,))
    assert conn.execute("SELECT (SELECT count(*) FROM lodging_votes) + (SELECT count(*) FROM saved_place_votes)").fetchone() == (0,)


def test_votes_survive_their_user(conn):
    owner, voter = _user(conn), _user(conn)
    t = _trip(conn, owner)
    p = _person(conn, owner, t)
    s, pl = _stay(conn, t), _place(conn, t)
    conn.execute("INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)", (s, t, p, voter))
    conn.execute("INSERT INTO saved_place_votes (saved_place_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)", (pl, t, p, voter))
    conn.execute("DELETE FROM users WHERE id = %s", (voter,))
    assert conn.execute("SELECT user_id FROM lodging_votes").fetchone() == (None,)
    assert conn.execute("SELECT user_id FROM saved_place_votes").fetchone() == (None,)


def test_lodging_option_program_and_run_set_null(conn):
    u = _user(conn)
    t = _trip(conn, u)
    prog = _insert(conn, "affiliate_programs", {"code": "bk", "network": "travelpayouts", "name": "P", "category": "lodging"})
    run = _insert(conn, "runs", {"trip_id": t, "user_id": u, "kind": "deep_research"})
    s = _stay(conn, t, program_id=prog, run_id=run)
    c = _todo(conn, t, kind="tickets", program_id=prog)
    conn.execute("DELETE FROM affiliate_programs WHERE id = %s", (prog,))
    conn.execute("DELETE FROM runs WHERE id = %s", (run,))
    assert conn.execute("SELECT program_id, run_id FROM lodging_options WHERE id = %s", (s,)).fetchone() == (None, None)
    assert conn.execute("SELECT program_id FROM checklist_items WHERE id = %s", (c,)).fetchone() == (None,)


def test_checklist_checks_and_rules_unique(conn):
    u = _user(conn)
    t1, t2 = _trip(conn, u), _trip(conn, u)
    for kw, name in (
        ({"kind": "visa"}, "ck_checklist_items_kind"),
        ({"status": "maybe"}, "ck_checklist_items_status"),
        ({"source": "bot"}, "ck_checklist_items_source"),
        ({"source": "user"}, "ck_checklist_items_source_kind"),
        ({"kind": "custom"}, "ck_checklist_items_source_kind"),
        ({"source": "ai", "kind": "esim", "title": "x"}, "ck_checklist_items_source_kind"),
        ({"source": "user", "kind": "custom"}, "ck_checklist_items_title"),
    ):
        with _check(name):
            _todo(conn, t1, **kw)
    _todo(conn, t1)  # a rules row, no title
    with pytest.raises(psycopg.errors.UniqueViolation):
        _todo(conn, t1)
    _todo(conn, t2)
    for n in range(2):  # custom items and AI packing lines are many per trip
        _todo(conn, t1, kind="custom", source="user", title=f"c{n}")
        _todo(conn, t1, kind="packing", source="ai", title=f"p{n}", meta='{"group": "clothing", "qty": 2}')


def test_notes_checks_and_item_link(conn):
    u = _user(conn)
    t1, t2 = _trip(conn, u), _trip(conn, u)
    with _check("ck_notes_agent_sources"):
        _note(conn, t1, kind="agent")
    with _check("ck_notes_agent_not_private"):
        _note(conn, t1, kind="agent", urls=["https://e.com"], is_private=True)
    with pytest.raises(psycopg.errors.CheckViolation):
        _note(conn, t1, title="x" * 161)
    with pytest.raises(psycopg.errors.CheckViolation):
        _note(conn, t1, topic="x" * 81)
    _note(conn, t1, kind="agent", urls=["https://e.com"])
    i = _item(conn, t1)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):  # another trip's item
        _note(conn, t2, itinerary_item_id=i)
    n = _note(conn, t1, itinerary_item_id=i, day="2027-05-01")
    conn.execute("DELETE FROM itinerary_items WHERE id = %s", (i,))
    assert conn.execute("SELECT itinerary_item_id FROM notes WHERE id = %s", (n,)).fetchone() == (None,)


def test_trip_delete_cascades_everywhere(conn):
    u = _user(conn)
    t = _trip(conn, u)
    p = _person(conn, u, t)
    conn.execute("INSERT INTO itinerary_days (trip_id, day) VALUES (%s, '2027-05-01')", (t,))
    pl, s = _place(conn, t), _stay(conn, t)
    i = _item(conn, t, saved_place_id=pl)
    conn.execute("INSERT INTO lodging_votes (lodging_id, trip_id, person_id) VALUES (%s, %s, %s)", (s, t, p))
    conn.execute("INSERT INTO saved_place_votes (saved_place_id, trip_id, person_id) VALUES (%s, %s, %s)", (pl, t, p))
    _todo(conn, t)
    _note(conn, t, itinerary_item_id=i)
    conn.execute("DELETE FROM trips WHERE id = %s", (t,))
    for tbl in TABLES:
        assert conn.execute(f"SELECT count(*) FROM {tbl}").fetchone() == (0,), tbl
