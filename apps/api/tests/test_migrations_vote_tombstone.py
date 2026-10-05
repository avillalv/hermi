# ruff: noqa: E501  (long SQL strings)
"""WF-034.2: revision 0022_vote_tombstone. Removing a traveler keeps their hearts (cleared person, same user); one Booked stay per trip."""

import uuid

import psycopg
import pytest
from alembic import command

from hermi import db


def _arrange(c):
    owner = c.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (f"{uuid.uuid4().hex[:8]}@example.com",)).fetchone()[0]
    t = c.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (owner,)).fetchone()[0]
    p = c.execute("INSERT INTO people (owner_user_id, name) VALUES (%s, 'Kid') RETURNING id", (owner,)).fetchone()[0]
    c.execute("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (t, p))
    s = c.execute("INSERT INTO lodging_options (trip_id, title, added_via) VALUES (%s, 'Flat', 'manual') RETURNING id", (t,)).fetchone()[0]
    pl = c.execute("INSERT INTO saved_places (trip_id, place_provider, place_id, name) VALUES (%s, 'manual', 'x', 'P') RETURNING id", (t,)).fetchone()[0]
    return owner, t, p, s, pl


def test_removing_a_traveler_keeps_the_hearts(db_urls, system_conn):
    owner, t, p, s, pl = _arrange(system_conn)
    system_conn.execute("INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)", (s, t, p, owner))
    system_conn.execute("INSERT INTO saved_place_votes (saved_place_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)", (pl, t, p, owner))
    system_conn.execute("DELETE FROM people WHERE id = %s", (p,))
    assert system_conn.execute("SELECT person_id, user_id FROM lodging_votes WHERE lodging_id = %s", (s,)).fetchone() == (None, owner)
    assert system_conn.execute("SELECT person_id, user_id FROM saved_place_votes WHERE saved_place_id = %s", (pl,)).fetchone() == (None, owner)
    # the stay going away still removes its votes
    system_conn.execute("DELETE FROM lodging_options WHERE id = %s", (s,))
    assert system_conn.execute("SELECT count(*) FROM lodging_votes WHERE lodging_id = %s", (s,)).fetchone() == (0,)


def test_a_member_and_a_traveler_heart_once_but_a_member_without_a_traveler_can_heart(db_urls, system_conn):
    owner, t, p, s, _ = _arrange(system_conn)
    ins = "INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)"
    system_conn.execute(ins, (s, t, None, owner))
    with pytest.raises(psycopg.errors.UniqueViolation):
        system_conn.execute(ins, (s, t, None, owner))  # same member twice
    system_conn.execute(ins, (s, t, p, None))
    with pytest.raises(psycopg.errors.UniqueViolation):
        system_conn.execute(ins, (s, t, p, None))  # same traveler twice


def test_one_booked_stay_per_trip(db_urls, system_conn):
    _, t, _, s, _ = _arrange(system_conn)
    other = system_conn.execute("INSERT INTO lodging_options (trip_id, title, added_via) VALUES (%s, 'B', 'manual') RETURNING id", (t,)).fetchone()[0]
    system_conn.execute("UPDATE lodging_options SET status = 'booked' WHERE id = %s", (s,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        system_conn.execute("UPDATE lodging_options SET status = 'booked' WHERE id = %s", (other,))


def test_round_trip_from_the_last_revision(db_urls):
    from tests.test_migrations import _alembic_cfg

    cfg = _alembic_cfg(db_urls["migrate"])
    command.downgrade(cfg, "0021_fx_convert_exact_rounding")
    with psycopg.connect(db.psycopg_url(db_urls["system"]), autocommit=True) as c:
        assert c.execute("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'lodging_votes' AND column_name = 'person_id'").fetchone() == ("NO",)
    command.upgrade(cfg, "head")
    with psycopg.connect(db.psycopg_url(db_urls["system"]), autocommit=True) as c:
        assert c.execute("SELECT is_nullable FROM information_schema.columns WHERE table_name = 'lodging_votes' AND column_name = 'person_id'").fetchone() == ("YES",)
