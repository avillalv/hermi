# ruff: noqa: E501  (long SQL strings and assertions)
"""WF-133.1: hermi seed --demo adds the Lisbon demo trip and the published sample trips."""

import pytest

from hermi.config import Settings
from hermi.seed.demo import CONTENT_EMAIL, DEMO_TRIP, seed_demo

PERSONA_EMAILS = ("free@hermi.test", "plus@hermi.test", "admin@hermi.test")


@pytest.fixture
def settings(db_urls):
    return Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
    )


def _count(conn, sql, *args):
    return conn.execute(sql, args).fetchone()[0]


def _tables(conn):
    return {
        "users": _count(conn, "SELECT count(*) FROM users"),
        "trips": _count(conn, "SELECT count(*) FROM trips"),
        "items": _count(conn, "SELECT count(*) FROM itinerary_items"),
        "stays": _count(conn, "SELECT count(*) FROM lodging_options"),
        "votes": _count(conn, "SELECT count(*) FROM lodging_votes"),
        "samples": _count(conn, "SELECT count(*) FROM sample_trips"),
        "people": _count(conn, "SELECT count(*) FROM people"),
    }


@pytest.fixture
def seeded(settings, db_urls, system_conn):
    seed_demo(settings, system_url=db_urls["system"])
    return system_conn


def test_plus_persona_finds_the_demo_trip(seeded):
    c = seeded
    trip = c.execute(
        "SELECT t.id, t.start_date, t.end_date FROM trips t JOIN users u ON u.id = t.owner_user_id "
        "WHERE u.email = 'plus@hermi.test' AND t.name = %s AND t.deleted_at IS NULL",
        (DEMO_TRIP,),
    ).fetchall()
    assert len(trip) == 1
    t, start, end = trip[0]
    assert _count(c, "SELECT count(*) FROM itinerary_days WHERE trip_id = %s", t) == 4
    assert _count(c, "SELECT count(*) FROM lodging_options WHERE trip_id = %s", t) == 3
    assert (
        _count(
            c,
            "SELECT count(DISTINCT lodging_id) FROM lodging_votes WHERE trip_id = %s",
            t,
        )
        == 3
    )
    assert _count(c, "SELECT count(*) FROM flight_routes WHERE trip_id = %s", t) == 1
    assert _count(c, "SELECT count(*) FROM trip_fare_links WHERE trip_id = %s", t) == 3
    chosen = c.execute(
        "SELECT depart_date, return_date FROM chosen_flights WHERE trip_id = %s", (t,)
    ).fetchall()
    assert chosen == [(start, end)]
    assert _count(c, "SELECT count(*) FROM checklist_items WHERE trip_id = %s", t) >= 3
    note = c.execute(
        "SELECT urls, checked_at FROM notes WHERE trip_id = %s AND kind = 'agent'", (t,)
    ).fetchall()
    assert len(note) == 1 and len(note[0][0]) >= 1 and note[0][1] is not None


def test_sample_trips_are_published_and_owned_by_the_content_account(seeded):
    rows = seeded.execute(
        "SELECT s.slug, s.tags, s.suits, s.published_at, u.email, "
        "       (SELECT count(*) FROM itinerary_days d WHERE d.trip_id = t.id), "
        "       (SELECT count(*) FROM itinerary_items i WHERE i.trip_id = t.id), "
        "       (SELECT count(*) FROM saved_places p WHERE p.trip_id = t.id) "
        "  FROM sample_trips s JOIN trips t ON t.id = s.trip_id "
        "  JOIN users u ON u.id = t.owner_user_id "
        " WHERE s.status = 'published'"
    ).fetchall()
    assert len(rows) >= 3
    for slug, tags, suits, published_at, owner, days, items, places in rows:
        assert slug and tags and suits and published_at
        assert owner == CONTENT_EMAIL
        assert days >= 1 and items >= 1 and places >= 1


def test_plus_persona_is_funded_once(settings, db_urls, seeded):
    sql = (
        "SELECT coalesce(sum(g.remaining), 0) FROM credit_grants g JOIN users u ON u.id = g.user_id "
        "WHERE u.email = 'plus@hermi.test' AND g.kind = 'adjustment'"
    )
    assert _count(seeded, sql) == 40
    assert seed_demo(settings, system_url=db_urls["system"])["credits_granted"] == 0
    assert _count(seeded, sql) == 40  # a second run does not double it


def test_seed_is_idempotent_and_makes_no_second_persona(settings, db_urls, seeded):
    before = _tables(seeded)
    again = seed_demo(settings, system_url=db_urls["system"])
    assert again == {"demo_trips": 0, "sample_trips": 0, "credits_granted": 0}
    assert _tables(seeded) == before
    assert (
        _count(seeded, "SELECT count(*) FROM users WHERE email = ANY(%s)", list(PERSONA_EMAILS))
        == 3
    )
    assert _count(seeded, "SELECT count(*) FROM users WHERE email = 'plus@hermi.test'") == 1


@pytest.mark.parametrize(
    ("environment", "auth_mode"),
    [("preview", "dev"), ("staging", "dev"), ("production", "dev"), ("ci", "supabase")],
)
def test_demo_seed_refuses_non_local(settings, db_urls, system_conn, environment, auth_mode):
    bad = settings.model_copy(update={"environment": environment, "auth_mode": auth_mode})
    sql = "SELECT count(*) FROM users WHERE email LIKE %s"
    before = _count(system_conn, sql, "%@hermi.test")
    with pytest.raises(RuntimeError, match="local and ci"):
        seed_demo(bad, system_url=db_urls["system"])
    assert _count(system_conn, sql, "%@hermi.test") == before


def test_content_account_cannot_be_signed_into(settings, seeded):
    from hermi import db
    from hermi.errors import ApiError
    from hermi.modules.auth import service
    from hermi.modules.auth.schemas import BootstrapIn
    from hermi.security.jwt import VerifiedToken

    engine = db.open_app_engine(settings)
    try:
        token = VerifiedToken("someone-else", "email", CONTENT_EMAIL, {})
        with pytest.raises(ApiError) as e:
            service.bootstrap(engine, token, BootstrapIn(display_name="X", age_confirmed=True))
    finally:
        engine.dispose()
    assert e.value.status == 409 and e.value.code == "email_in_use"
