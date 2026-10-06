# ruff: noqa: E501  (long comments)
"""WF-133.2: public sample trip list and read, and the copy into the caller's trips (04 section 5.28)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi import analytics
from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token
from hermi.seed.demo import seed_demo


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
        public_web_url="https://app.hermi.test",
    )
    seed_demo(s, system_url=db_urls["system"])
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    assert client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h).status_code == 201
    return h


def _key(h):
    return {**h, "Idempotency-Key": uuid.uuid4().hex}


def _slugs(client, **q):
    r = client.get("/v1/public/sample-trips", params=q)
    assert r.status_code == 200, r.text
    return r


def test_list_is_public_cached_and_published_only(client, system_conn):
    system_conn.execute("UPDATE sample_trips SET status = 'draft', published_at = NULL WHERE slug = 'lisbon-food-weekend'")
    try:
        r = _slugs(client)
        assert r.headers["cache-control"] == "public, max-age=3600"
        slugs = [i["slug"] for i in r.json()["items"]]
        assert "lisbon-food-weekend" not in slugs and slugs
        assert client.get("/v1/public/sample-trips/lisbon-food-weekend").status_code == 404
    finally:
        system_conn.execute("UPDATE sample_trips SET status = 'published', published_at = now() WHERE slug = 'lisbon-food-weekend'")


def test_list_filters_by_tag_and_paginates(client):
    r = _slugs(client, tag="food")
    items = r.json()["items"]
    assert items and all("food" in i["tags"] for i in items)
    first = items[0]
    assert {"slug", "title", "destination_name", "days", "summary", "cover", "tags", "suits"} <= set(first)
    assert first["days"] >= 1
    assert _slugs(client, tag="no-such-tag").json()["items"] == []
    p1 = _slugs(client, limit=1).json()
    assert len(p1["items"]) == 1 and p1["has_more"] and p1["next_cursor"]
    p2 = _slugs(client, limit=1, cursor=p1["next_cursor"]).json()
    assert p2["items"][0]["slug"] != p1["items"][0]["slug"]


def test_detail_is_redacted_read_only_and_carries_no_partner_links(client):
    r = client.get("/v1/public/sample-trips/lisbon-food-weekend")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=3600"
    b = r.json()
    assert b["label"] == "Sample trip" and b["book_slide"] is None
    assert b["cta"] == {"label": "Plan your own", "url": "https://app.hermi.test"}
    pres = b["presentation"]
    assert pres["trip"]["travelers"] == [] and pres["flights"] == []
    assert pres["days"] and all(d["notes"] == "" and all(i["notes"] == "" for i in d["items"]) for d in pres["days"])
    assert b["updated_at"]


def test_detail_404_for_unknown_slug(client):
    assert client.get("/v1/public/sample-trips/nope-nothing").status_code == 404


def test_copy_needs_a_signed_in_user(client):
    assert client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers={"Idempotency-Key": uuid.uuid4().hex}).status_code == 401


def test_copy_makes_an_editable_trip_with_days_items_and_saved_places(client, system_conn):
    h = _user(client)
    src = client.get("/v1/public/sample-trips/lisbon-food-weekend").json()["presentation"]
    r = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={"start_date": "2030-05-10"}, headers=_key(h))
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["my_role"] == "owner" and t["start_date"] == "2030-05-10" and t["end_date"] == "2030-05-12"
    assert [d["name"] for d in t["destinations"]] == ["Lisbon"]
    assert client.get(f"/v1/trips/{t['id']}", headers=h).status_code == 200
    rows = system_conn.execute("SELECT day::text, source FROM itinerary_items WHERE trip_id = %s ORDER BY day, sort_order", (t["id"],)).fetchall()
    assert len(rows) == sum(len(d["items"]) for d in src["days"])
    assert {r[1] for r in rows} == {"manual"} and rows[0][0] == "2030-05-10" and rows[-1][0] == "2030-05-12"
    assert system_conn.execute("SELECT count(*) FROM itinerary_days WHERE trip_id = %s", (t["id"],)).fetchone()[0] == len(src["days"])
    assert system_conn.execute("SELECT count(*) FROM saved_places WHERE trip_id = %s", (t["id"],)).fetchone()[0] == 3
    # items still point at the copied saved places, never the sample's
    q = "SELECT count(*) FROM itinerary_items i JOIN saved_places p ON p.id = i.saved_place_id AND p.trip_id = i.trip_id WHERE i.trip_id = %s"
    assert system_conn.execute(q, (t["id"],)).fetchone()[0] == 3
    for tbl in ("flight_routes", "trip_fare_links"):
        assert system_conn.execute(f"SELECT count(*) FROM {tbl} WHERE trip_id = %s", (t["id"],)).fetchone()[0] == 0


def test_copy_without_start_date_keeps_the_sample_dates_shape(client):
    h = _user(client)
    r = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers=_key(h))
    assert r.status_code == 201 and r.json()["start_date"] is not None


def test_copy_replays_with_the_same_key(client):
    h = _key(_user(client))
    a = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers=h)
    b = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers=h)
    assert a.status_code == b.status_code == 201 and a.json()["id"] == b.json()["id"]
    assert b.headers.get("idempotent-replay") == "true"


def test_copy_requires_an_idempotency_key(client):
    h = _user(client)
    r = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"


def test_copy_at_the_free_active_trip_limit_is_402(client):
    h = _user(client)
    for n in ("One", "Two"):
        assert client.post("/v1/trips", json={"name": n}, headers=h).status_code == 201
    r = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers=_key(h))
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"
    assert r.json()["paywall"]["trigger"] == "third_trip"


def test_copy_404_for_unpublished_slug(client):
    assert client.post("/v1/public/sample-trips/nope-nothing/copy", json={}, headers=_key(_user(client))).status_code == 404


def test_copy_emits_sample_trip_copied(client, monkeypatch):
    seen = []
    monkeypatch.setattr(analytics, "capture", lambda name, did, props=None, **k: seen.append((name, props)) or True)
    h = _user(client)
    seen.clear()
    r = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers=_key(h))
    assert r.status_code == 201
    assert seen == [("sample_trip_copied", {"slug": "lisbon-food-weekend", "was_guest": False})]


@pytest.fixture
def planted(system_conn):
    """Rows on the Lisbon sample that must never reach a reader or a copy: notes, a price, a traveler, a booked status, a check."""
    tid, owner = system_conn.execute("SELECT t.id, t.owner_user_id FROM sample_trips s JOIN trips t ON t.id = s.trip_id WHERE s.slug = 'lisbon-food-weekend'").fetchone()
    person = system_conn.execute("SELECT id FROM people WHERE owner_user_id = %s AND is_self", (owner,)).fetchone()[0]
    system_conn.execute("INSERT INTO trip_people (trip_id, person_id, added_by) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (tid, person, owner))
    system_conn.execute("UPDATE itinerary_days SET notes = 'SECRET day note' WHERE trip_id = %s", (tid,))
    system_conn.execute("UPDATE saved_places SET note = 'SECRET place note' WHERE trip_id = %s", (tid,))
    system_conn.execute(
        "UPDATE itinerary_items SET notes = 'SECRET item note', estimated_cost_minor = 1234, cost_currency = 'EUR', status = 'booked', "
        "check_url = 'https://example.com/p', checked_at = now() WHERE trip_id = %s", (tid,))
    yield tid
    system_conn.execute("DELETE FROM trip_people WHERE trip_id = %s AND person_id = %s", (tid, person))
    system_conn.execute("UPDATE itinerary_days SET notes = '' WHERE trip_id = %s", (tid,))
    system_conn.execute("UPDATE saved_places SET note = '' WHERE trip_id = %s", (tid,))
    system_conn.execute(
        "UPDATE itinerary_items SET notes = '', estimated_cost_minor = NULL, cost_currency = NULL, status = 'planned', check_url = NULL, checked_at = NULL WHERE trip_id = %s", (tid,))


def test_detail_hides_planted_notes_and_people(client, planted):
    b = client.get("/v1/public/sample-trips/lisbon-food-weekend").json()
    assert "SECRET" not in str(b)
    assert b["presentation"]["trip"]["travelers"] == []
    assert any(i["estimated_cost_minor"] == 1234 for d in b["presentation"]["days"] for i in d["items"])  # example prices stay


def test_copy_never_carries_prices_notes_checks_or_booked_status(client, system_conn, planted):
    r = client.post("/v1/public/sample-trips/lisbon-food-weekend/copy", json={}, headers=_key(_user(client)))
    assert r.status_code == 201
    tid = r.json()["id"]
    q = lambda sql: system_conn.execute(sql, (tid,)).fetchall()  # noqa: E731
    assert q("SELECT 1 FROM itinerary_items WHERE trip_id = %s AND (estimated_cost_minor IS NOT NULL OR cost_currency IS NOT NULL OR notes <> '' OR check_url IS NOT NULL OR checked_at IS NOT NULL OR status = 'booked')") == []
    assert q("SELECT 1 FROM itinerary_days WHERE trip_id = %s AND notes <> ''") == []
    assert q("SELECT 1 FROM saved_places WHERE trip_id = %s AND note <> ''") == []
    assert q("SELECT 1 FROM trip_people WHERE trip_id = %s") != [] and len(q("SELECT 1 FROM trip_people WHERE trip_id = %s")) == 1  # only the caller


def test_public_reads_are_rate_limited_per_ip(client, system_conn, monkeypatch):
    from hermi.security import rate_limit

    system_conn.execute("DELETE FROM rate_limit_counters")
    monkeypatch.setitem(rate_limit.TEST_LIMITS, "read_ip", 1)
    assert client.get("/v1/public/sample-trips").status_code == 200
    r = client.get("/v1/public/sample-trips/lisbon-food-weekend")
    assert r.status_code == 429 and r.json()["code"] == "rate_limited"
    system_conn.execute("DELETE FROM rate_limit_counters")


def test_destination_filter_treats_wildcards_literally(client):
    assert _slugs(client, destination="Lis").json()["items"]
    assert _slugs(client, destination="%").json()["items"] == []
