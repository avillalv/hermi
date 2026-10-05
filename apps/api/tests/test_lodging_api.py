# ruff: noqa: E501  (long comments)
"""WF-034.2: lodging (04 section 5.9): CRUD with links kept as pasted, per-night price, hearts, stated sort, compare, one Booked stay,
the saved_lodging_per_trip and lodging_compare limits, parse-link from URL text, hostile URLs and the network block."""

import socket
import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14, "timezone": "Europe/Lisbon"}
AIRBNB = "https://www.AirBnb.com/rooms/12345678?check_in=2027-05-01&check_out=2027-05-05&adults=2&source_impression_id=p3_abc#reviews"


@pytest.fixture
def client(db_urls):
    s = Settings(_env_file=None, environment="ci", auth_mode="dev", providers_mode="fake", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10)
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h)
    assert r.status_code == 201
    return h, r.json()


@pytest.fixture
def world(client, system_conn):
    """Trip owned by `o` with editor `e`, viewer `v` and stranger `s`. `ids` holds the user ids."""
    o, ou = _user(client)
    people = {k: _user(client) for k in ("e", "v", "s")}
    t = client.post("/v1/trips", json={"name": "Trip", "destinations": [LISBON], "start_date": "2027-05-01", "end_date": "2027-05-05"}, headers=o).json()
    for k, role in (("e", "editor"), ("v", "viewer")):
        system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (t["id"], people[k][1]["id"], role))
    return {"o": o, "t": t, "tid": t["id"], "ids": {"o": ou["id"], **{k: people[k][1]["id"] for k in people}}, **{k: people[k][0] for k in people}}


def _plus(system_conn, uid):
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus', valid_until = NULL WHERE user_id = %s", (uid,))


def _add(client, w, who="e", **kw):
    r = client.post(f"/v1/trips/{w['tid']}/lodging", json={"title": "Flat", **kw}, headers=w[who])
    assert r.status_code == 201, r.text
    return r.json()


def _vote(client, h, stay, voted=True):
    r = client.put(f"/v1/lodging/{stay['id']}/votes/me", json={"voted": voted}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_network_stays_blocked_for_listing_sites(client, world):
    """Saving, parsing and listing links to booking sites opens no socket (conftest turns any DNS or connect into a failure)."""
    with pytest.raises(AssertionError):
        socket.getaddrinfo("www.airbnb.com", 443)
    for url in (AIRBNB, "https://www.vrbo.com/1234567", "https://secure.booking.com/hotel/pt/x.html", "https://www.expedia.com/Hotel-Search"):
        assert client.post("/v1/lodging/parse-link", json={"url": url}, headers=world["o"]).status_code == 200
        assert client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "X", "url": url}, headers=world["o"]).status_code == 201


def test_link_is_kept_exactly_as_pasted(client, world):
    stay = _add(client, world, url=AIRBNB)
    assert stay["url"] == AIRBNB and stay["site"] == "www.airbnb.com".removeprefix("www.") and stay["added_via"] == "paste"
    assert client.get(f"/v1/lodging/{stay['id']}", headers=world["v"]).json()["url"] == AIRBNB
    changed = client.patch(f"/v1/lodging/{stay['id']}", json={"notes": "nice", "version": stay["version"]}, headers=world["e"]).json()
    assert changed["url"] == AIRBNB and changed["notes"] == "nice"
    page = client.get(f"/v1/trips/{world['tid']}/lodging", headers=world["v"]).json()
    assert page["items"][0]["url"] == AIRBNB
    # a second paste of the same listing with other tracking parameters is a duplicate
    r = client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "Again", "url": AIRBNB.split("?")[0] + "?x=1"}, headers=world["e"])
    assert r.status_code == 409 and r.json()["code"] == "state_conflict"


def test_manual_stay_defaults_and_shape(client, world):
    s = _add(client, world, who="o")
    assert s["added_via"] == "manual" and s["status"] == "candidate" and s["votes"] == [] and s["vote_summary"] == {"hearts": 0} and s["version"] == 1
    assert s["url"] is None and s["site"] is None and s["price_per_night"] is None and s["added_by"]["id"] == world["ids"]["o"]
    assert client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "X", "added_via": "import"}, headers=world["o"]).status_code == 422
    assert client.get(f"/v1/trips/{world['tid']}/lodging", headers=world["s"]).status_code == 404


def test_every_stay_shows_a_per_night_price(client, world, system_conn):
    system_conn.execute("INSERT INTO fx_rates (currency, per_eur, rate_date) VALUES ('USD', 1.25, '2027-01-01') ON CONFLICT (currency) DO UPDATE SET per_eur = 1.25")
    total_only = _add(client, world, title="A", check_in="2027-05-01", check_out="2027-05-05", price_total={"amount_minor": 40000, "currency": "EUR"})
    assert total_only["nights"] == 4 and total_only["price_per_night"] == {"amount_minor": 10000, "currency": "EUR"} and total_only["price_total"]["amount_minor"] == 40000
    night_only = _add(client, world, title="B", check_in="2027-05-01", check_out="2027-05-03", price_per_night={"amount_minor": 9000, "currency": "EUR"})
    assert night_only["price_total"] == {"amount_minor": 18000, "currency": "EUR"}
    usd = _add(client, world, title="C", check_in="2027-05-01", check_out="2027-05-03", price_total={"amount_minor": 20000, "currency": "USD"})
    assert usd["price_per_night"] == {"amount_minor": 10000, "currency": "USD"} and usd["price_home_total"] == {"amount_minor": 16000, "currency": "EUR"}
    no_dates = _add(client, world, title="D", price_total={"amount_minor": 5000, "currency": "EUR"})
    assert no_dates["price_per_night"] is None  # nothing to divide by yet
    mixed = client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "E", "price_total": {"amount_minor": 1, "currency": "EUR"}, "price_per_night": {"amount_minor": 1, "currency": "USD"}}, headers=world["e"])
    assert mixed.status_code == 422
    bad_dates = client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "F", "check_in": "2027-05-05", "check_out": "2027-05-01"}, headers=world["e"])
    assert bad_dates.status_code == 422


def test_patch_is_versioned_and_changes_prices(client, world):
    s = _add(client, world, check_in="2027-05-01", check_out="2027-05-03", price_total={"amount_minor": 20000, "currency": "EUR"})
    assert client.patch(f"/v1/lodging/{s['id']}", json={"title": "New"}, headers=world["e"]).status_code == 428
    r = client.patch(f"/v1/lodging/{s['id']}", json={"price_per_night": {"amount_minor": 12000, "currency": "EUR"}, "title": "New"}, headers={**world["e"], "If-Match": f'"{s["version"]}"'})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["price_per_night"]["amount_minor"] == 12000 and r.json()["price_total"]["amount_minor"] == 20000
    stale = client.patch(f"/v1/lodging/{s['id']}", json={"title": "Old"}, headers={**world["e"], "If-Match": '"1"'})
    assert stale.status_code == 409 and stale.json()["current"]["title"] == "New"
    assert client.patch(f"/v1/lodging/{s['id']}", json={"title": None, "version": 2}, headers=world["e"]).status_code == 422
    assert client.patch(f"/v1/lodging/{s['id']}", json={"title": "V", "version": 2}, headers=world["v"]).status_code == 403
    assert client.patch(f"/v1/lodging/{s['id']}", json={"title": "S", "version": 2}, headers=world["s"]).status_code == 404


def test_delete_removes_the_stay_and_its_hearts(client, world, system_conn):
    s = _add(client, world)
    _vote(client, world["v"], s)
    assert system_conn.execute("SELECT count(*) FROM lodging_votes WHERE lodging_id = %s", (s["id"],)).fetchone() == (1,)
    assert client.delete(f"/v1/lodging/{s['id']}", headers=world["v"]).status_code == 403
    assert client.delete(f"/v1/lodging/{s['id']}", headers=world["e"]).status_code == 204
    assert client.get(f"/v1/lodging/{s['id']}", headers=world["e"]).status_code == 404
    assert system_conn.execute("SELECT count(*) FROM lodging_votes WHERE lodging_id = %s", (s["id"],)).fetchone() == (0,)


def test_activity_feed_gets_an_entry(client, world):
    _add(client, world)
    feed = client.get(f"/v1/trips/{world['tid']}/activity", headers=world["o"]).json()
    assert any(i["entity_type"] == "lodging" and i["verb"] == "added" for i in feed["items"])


# --- hearts ---------------------------------------------------------------------------------------------------------------


def test_a_heart_counts_once_per_member_and_viewers_may_heart(client, world):
    s = _add(client, world)
    first = _vote(client, world["v"], s)
    again = _vote(client, world["v"], s)  # repeating changes nothing
    assert first["vote_summary"] == again["vote_summary"] == {"hearts": 1} and again["votes"] == [{"user_id": world["ids"]["v"], "person_id": None}]
    assert _vote(client, world["e"], s)["vote_summary"]["hearts"] == 2
    assert _vote(client, world["v"], s, voted=False)["vote_summary"]["hearts"] == 1
    assert _vote(client, world["v"], s, voted=False)["vote_summary"]["hearts"] == 1  # removing twice is fine
    assert client.put(f"/v1/lodging/{s['id']}/votes/me", json={"voted": True}, headers=world["s"]).status_code == 404
    assert client.put(f"/v1/lodging/{s['id']}/votes/me", json={}, headers=world["e"]).status_code == 422


def test_hearts_survive_a_removed_traveler(client, world, system_conn):
    s = _add(client, world)
    uid = world["ids"]["e"]
    pid = system_conn.execute("SELECT id FROM people WHERE linked_user_id = %s", (uid,)).fetchone()[0]  # the "Me" traveler made at sign-up
    system_conn.execute("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (world["tid"], pid))
    assert _vote(client, world["e"], s)["votes"] == [{"user_id": uid, "person_id": str(pid)}]
    system_conn.execute("DELETE FROM people WHERE id = %s", (pid,))
    after = client.get(f"/v1/lodging/{s['id']}", headers=world["e"]).json()
    assert after["votes"] == [{"user_id": uid, "person_id": None}] and after["vote_summary"]["hearts"] == 1


# --- sort -----------------------------------------------------------------------------------------------------------------


def test_list_states_its_sort_and_never_ranks_by_commission(client, world):
    a = _add(client, world, title="A", rating=4.1, check_in="2027-05-01", check_out="2027-05-03", price_per_night={"amount_minor": 30000, "currency": "EUR"})
    b = _add(client, world, title="B", rating=4.8, check_in="2027-05-01", check_out="2027-05-03", price_per_night={"amount_minor": 10000, "currency": "EUR"})
    c = _add(client, world, title="C", check_in="2027-05-01", check_out="2027-05-03")
    _vote(client, world["v"], a)
    _vote(client, world["e"], a)
    _vote(client, world["v"], c)

    def titles(sort=None, **kw):
        r = client.get(f"/v1/trips/{world['tid']}/lodging", params={**({"sort": sort} if sort else {}), **kw}, headers=world["v"])
        assert r.status_code == 200, r.text
        return [i["title"] for i in r.json()["items"]], r.json()["sorted_by"]

    assert titles() == (["C", "B", "A"], "created")  # newest first
    assert titles("price") == (["B", "A", "C"], "price")  # cheapest per night first, unpriced last
    assert titles("rating") == (["B", "A", "C"], "rating")
    assert titles("votes") == (["A", "C", "B"], "votes")
    assert client.get(f"/v1/trips/{world['tid']}/lodging", params={"sort": "commission"}, headers=world["v"]).status_code == 422
    page = client.get(f"/v1/trips/{world['tid']}/lodging", params={"limit": 2}, headers=world["v"]).json()
    assert len(page["items"]) == 2 and page["has_more"] and client.get(f"/v1/trips/{world['tid']}/lodging", params={"limit": 2, "cursor": page["next_cursor"]}, headers=world["v"]).json()["items"][0]["title"] == "A"
    assert client.get(f"/v1/trips/{world['tid']}/lodging", params={"status": "booked"}, headers=world["v"]).json()["items"] == []
    assert b["title"] == "B"


# --- one Booked stay ------------------------------------------------------------------------------------------------------


def test_exactly_one_stay_can_be_booked(client, world):
    a, b = _add(client, world, title="A"), _add(client, world, title="B")
    ok = client.patch(f"/v1/lodging/{a['id']}", json={"status": "booked", "version": 1}, headers=world["e"])
    assert ok.status_code == 200 and ok.json()["status"] == "booked"
    r = client.patch(f"/v1/lodging/{b['id']}", json={"status": "booked", "version": 1}, headers=world["e"])
    assert r.status_code == 409 and r.json()["code"] == "state_conflict" and r.json()["booked_id"] == a["id"]
    assert client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "C", "status": "booked"}, headers=world["e"]).status_code == 409
    # free the first, then the second can be booked
    assert client.patch(f"/v1/lodging/{a['id']}", json={"status": "shortlisted", "version": 2}, headers=world["e"]).status_code == 200
    assert client.patch(f"/v1/lodging/{b['id']}", json={"status": "booked", "version": 1}, headers=world["e"]).status_code == 200
    # saving the booked stay again with the same status is not a conflict with itself
    assert client.patch(f"/v1/lodging/{b['id']}", json={"status": "booked", "notes": "x", "version": 2}, headers=world["e"]).status_code == 200


# --- limits ---------------------------------------------------------------------------------------------------------------


def test_saved_lodging_limit_is_402_on_free_and_higher_on_plus(client, world, system_conn):
    for n in range(8):
        _add(client, world, title=f"S{n}")
    r = client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "Ninth"}, headers=world["e"])
    assert r.status_code == 402 and r.json()["code"] == "limit_reached" and r.json()["paywall"]["trigger"] == "ninth_stay"
    _plus(system_conn, world["ids"]["o"])  # the owner's tier counts for the whole trip
    assert client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "Ninth"}, headers=world["e"]).status_code == 201


def test_compare_two_to_four_with_the_plan_cap(client, world, system_conn):
    s = [
        _add(client, world, title=t, rating=r, bedrooms=2, beds=3, baths=1.5, pros="p" + t, cons="c" + t, lat=38.7, lon=-9.1, check_in="2027-05-01", check_out="2027-05-03",
             price_per_night={"amount_minor": p, "currency": "EUR"})
        for t, r, p in (("A", 4.5, 10000), ("B", 4.0, 12000), ("C", 3.5, 8000), ("D", 5.0, 9000), ("E", 4.2, 7000))
    ]
    _vote(client, world["v"], s[1])
    ids = lambda *ix: ",".join(s[i]["id"] for i in ix)  # noqa: E731
    url = f"/v1/trips/{world['tid']}/lodging/compare"
    r = client.get(url, params={"ids": ids(1, 0)}, headers=world["v"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["columns"] == [s[1]["id"], s[0]["id"]] and body["home_currency"] == "EUR"  # the order of ids
    rows = {x["key"]: x["values"] for x in body["rows"]}
    assert rows["title"] == ["B", "A"] and rows["price_per_night"] == [12000, 10000] and rows["price_total"] == [24000, 20000] and rows["rating"] == [4.0, 4.5]
    assert rows["bedrooms"] == [2, 2] and rows["baths"] == [1.5, 1.5] and rows["votes"] == [1, 0] and rows["pros"] == ["pB", "pA"] and rows["cons"] == ["cB", "cA"]
    assert rows["distance_to_center_km"][0] is not None and rows["distance_to_center_km"][0] < 10
    assert client.get(url, params={"ids": ids(0)}, headers=world["v"]).status_code == 422  # fewer than 2
    assert client.get(url, params={"ids": ids(0, 0)}, headers=world["v"]).status_code == 422  # not different
    assert client.get(url, params={"ids": "nope,nope"}, headers=world["v"]).status_code == 422
    assert client.get(url, params={"ids": ids(0, 1, 2, 3, 4)}, headers=world["v"]).status_code == 422  # more than 4
    cap = client.get(url, params={"ids": ids(0, 1, 2)}, headers=world["v"])  # Free compares 2
    assert cap.status_code == 402 and cap.json()["code"] == "limit_reached"
    _plus(system_conn, world["ids"]["o"])
    assert client.get(url, params={"ids": ids(0, 1, 2, 3)}, headers=world["v"]).status_code == 200
    assert client.get(url, params={"ids": f"{s[0]['id']},{uuid.uuid4()}"}, headers=world["v"]).status_code == 404
    assert client.get(url, params={"ids": ids(0, 1)}, headers=world["s"]).status_code == 404


# --- parse-link and hostile URLs ------------------------------------------------------------------------------------------


def test_parse_link_reads_only_the_url_text(client, world):
    r = client.post("/v1/lodging/parse-link", json={"url": AIRBNB}, headers=world["o"])
    assert r.status_code == 200, r.text
    assert r.json() == {
        "url": AIRBNB, "site": "airbnb.com", "fetch_allowed": False, "check_in": "2027-05-01", "check_out": "2027-05-05", "guests": 2, "listing_id": "12345678",
        "title": None, "photos": [], "description": None, "note": "We never change your links.",
    }
    other = client.post("/v1/lodging/parse-link", json={"url": "https://stays.example.org/place?checkin=2027-06-01&checkout=2027-06-04&guests=3", "guests": 5}, headers=world["o"]).json()
    assert other["fetch_allowed"] is False and other["guests"] == 5 and other["check_in"] == "2027-06-01" and other["title"] is None
    booking = client.post("/v1/lodging/parse-link", json={"url": "https://www.booking.com/hotel/pt/casa-azul.en-gb.html?checkin=2027-05-01"}, headers=world["o"]).json()
    assert booking["listing_id"] == "casa-azul" and booking["check_in"] == "2027-05-01"
    assert client.post("/v1/lodging/parse-link", json={"url": AIRBNB}).status_code == 401


@pytest.mark.parametrize("url", ["https://airbnb.co.kr/rooms/1", "https://www.vrbo.com/1234567", "https://secure.booking.com/hotel/x.html", "https://www.expedia.com/x", "https://www.hotels.com/ho1"])
def test_fetch_flag_on_a_blocked_host_is_422(client, world, url):
    r = client.post("/v1/lodging/parse-link", json={"url": url, "fetch": True}, headers=world["o"])
    assert r.status_code == 422 and r.json()["code"] == "blocked_domain"
    ok = client.post("/v1/lodging/parse-link", json={"url": url}, headers=world["o"]).json()
    assert ok["fetch_allowed"] is False and ok["title"] is None and ok["photos"] == []


def test_fetch_flag_on_another_host_never_fetches(client, world):
    r = client.post("/v1/lodging/parse-link", json={"url": "https://stays.example.org/p", "fetch": True}, headers=world["o"])
    assert r.status_code == 200 and r.json()["fetch_allowed"] is False and r.json()["title"] is None


HOSTILE = [
    "http://127.0.0.1/", "http://[::1]/", "http://169.254.169.254/latest/meta-data", "http://0x7f000001/", "http://2130706433/", "http://0177.0.0.1/",
    "gopher://public.test/", "file:///etc/passwd", "javascript:alert(1)", "https://user:pass@public.test/", "https://public.test:8443/", "https://public.test/" + "a" * 2100, "not a link",
]


@pytest.mark.parametrize("url", HOSTILE)
def test_hostile_urls_are_refused_everywhere(client, world, url):
    r = client.post("/v1/lodging/parse-link", json={"url": url}, headers=world["o"])
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
    r = client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "X", "url": url}, headers=world["o"])
    assert r.status_code == 422
    s = _add(client, world, title="ok")
    r = client.patch(f"/v1/lodging/{s['id']}", json={"url": url, "version": 1}, headers=world["o"])
    assert r.status_code == 422


def test_deleting_a_traveler_through_the_api_clears_the_heart_person_under_rls(client, world, system_conn):
    """DELETE /v1/people/{id} runs as the app role with RLS on; the heart stays, its person is cleared."""
    s = _add(client, world)
    people = client.get("/v1/people", headers=world["o"]).json()
    me = next(p for p in people if p["is_me"])
    kid = client.post("/v1/people", json={"name": "Kid", "color": "#FF5E7E"}, headers=world["o"]).json()
    r = client.put(f"/v1/trips/{world['tid']}/travelers", json={"person_ids": [me["id"], kid["id"]]}, headers=world["o"])
    assert r.status_code == 200, r.text
    system_conn.execute("INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (%s, %s, %s, %s)", (s["id"], world["tid"], kid["id"], world["ids"]["o"]))
    assert client.delete(f"/v1/people/{kid['id']}", headers=world["o"]).status_code == 204
    after = client.get(f"/v1/lodging/{s['id']}", headers=world["o"]).json()
    assert after["votes"] == [{"user_id": world["ids"]["o"], "person_id": None}]


def test_a_race_past_the_checks_is_the_same_409(client, world, monkeypatch):
    """The pre-checks are skipped, so the unique indexes (one Booked, duplicate link) answer, and the answer is a 409 not a 500."""
    from hermi.modules.lodging import router as lodging_router

    monkeypatch.setattr(lodging_router, "_one_booked", lambda *a, **k: None)
    monkeypatch.setattr(lodging_router, "_no_duplicate", lambda *a, **k: None)
    a = _add(client, world, title="A", status="booked", url="https://stays.example.org/a")
    assert client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "B", "status": "booked"}, headers=world["e"]).status_code == 409
    assert client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "C", "url": "https://stays.example.org/a?x=1"}, headers=world["e"]).status_code == 409
    b = _add(client, world, title="B")
    assert client.patch(f"/v1/lodging/{b['id']}", json={"status": "booked", "version": 1}, headers=world["e"]).status_code == 409
    d = _add(client, world, title="D", url="https://stays.example.org/d")
    assert client.patch(f"/v1/lodging/{d['id']}", json={"url": "https://stays.example.org/a", "version": 1}, headers=world["e"]).status_code == 409
    assert client.get(f"/v1/lodging/{a['id']}", headers=world["e"]).status_code == 200  # the transaction still works


def test_upsell_depends_on_the_highest_tier_not_free(client, world, system_conn):
    """Trip Pass (30 stays) still gets the upsell and a free path the API can do; Plus at its ceiling (100) gets none."""
    system_conn.execute("INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', now() - interval '1 day', now() + interval '30 days', 'active')", (world["tid"],))
    for n in range(30):
        system_conn.execute("INSERT INTO lodging_options (trip_id, title, added_via) VALUES (%s, %s, 'manual')", (world["tid"], f"S{n}"))
    r = client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "x"}, headers=world["e"])
    p = r.json()
    assert r.status_code == 402 and p["paywall"]["trigger"] == "ninth_stay" and p["paywall"]["free_path"] == "Remove a stay to make room" and "upgrade" in p["detail"]
    assert "later list" not in p["detail"].lower()
    system_conn.execute("UPDATE trip_passes SET status = 'expired' WHERE trip_id = %s", (world["tid"],))
    _plus(system_conn, world["ids"]["o"])
    for n in range(70):
        system_conn.execute("INSERT INTO lodging_options (trip_id, title, added_via) VALUES (%s, %s, 'manual')", (world["tid"], f"P{n}"))
    r = client.post(f"/v1/trips/{world['tid']}/lodging", json={"title": "x"}, headers=world["e"])
    assert r.status_code == 402 and "paywall" not in r.json() and "upgrade" not in r.json()["detail"]
