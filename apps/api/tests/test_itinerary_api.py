# ruff: noqa: E501  (long comments)
"""WF-032.1: itinerary days and items (04 section 5.10): CRUD, roles, version 409s, reorder, move, bulk and the ICS file."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14, "timezone": "Europe/Lisbon"}
PORTO = {"name": "Porto", "country": "Portugal", "country_code": "PT", "lat": 41.15, "lon": -8.61, "timezone": "Europe/Lisbon"}


@pytest.fixture
def client(db_urls):
    s = Settings(_env_file=None, environment="ci", auth_mode="dev", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10)
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
    """Trip 2027-05-01 to 2027-05-03 owned by `o`, with editors `e` and `e2`, a viewer `v` and a stranger `s`."""
    o, _ = _user(client)
    people = {k: _user(client) for k in ("e", "e2", "v", "s")}
    r = client.post("/v1/trips", json={"name": "Trip", "destinations": [LISBON, PORTO], "start_date": "2027-05-01", "end_date": "2027-05-03"}, headers=o)
    assert r.status_code == 201, r.text
    t = r.json()
    for k, role in (("e", "editor"), ("e2", "editor"), ("v", "viewer")):
        system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (t["id"], people[k][1]["id"], role))
    return {"o": o, "t": t, **{k: people[k][0] for k in people}}


def _add(client, w, who="e", **kw):
    r = client.post(f"/v1/trips/{w['t']['id']}/items", json={"title": "Walk", "category": "sights", **kw}, headers=w[who])
    assert r.status_code == 201, r.text
    return r.json()


def _ifm(h, item):
    return {**h, "If-Match": f'"{item["version"]}"'}


def test_create_appends_and_returns_the_item_shape(client, world):
    a = _add(client, world, day="2027-05-01", title="A")
    b = _add(client, world, day="2027-05-01", title="B", start_time="10:00", end_time="11:30", cost={"amount_minor": 1500, "currency": "EUR"}, status="planned")
    assert b["sort_order"] > a["sort_order"] and a["version"] == 1 and a["source"] == "manual" and a["status"] == "idea"
    assert b["start_time"] == "10:00:00" and b["cost"] == {"amount_minor": 1500, "currency": "EUR"} and a["cost"] is None
    assert a["trip_id"] == world["t"]["id"] and a["bookable"] is False and a["added_by"]["id"] and a["notes"] == ""
    pool = _add(client, world, title="Idea")
    assert pool["day"] is None


def test_create_with_a_place_saves_it_once(client, world, system_conn):
    place = {"provider": "geoapify", "id": "abc123", "data": {"phone": "+351 1"}}
    a = _add(client, world, place=place, title="Tram", lat=38.7, lon=-9.1)
    b = _add(client, world, place=place, title="Tram again", lat=38.7, lon=-9.1)
    assert a["source"] == "place_search" and a["place_provider"] == "geoapify" and a["place_id"] == "abc123" and a["place_data"] == {"phone": "+351 1"}
    assert system_conn.execute("SELECT count(*) FROM saved_places WHERE trip_id = %s AND place_id = 'abc123'", (world["t"]["id"],)).fetchone()[0] == 1
    assert b["id"] != a["id"]


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": "x" * 201},
        {"day": "2027-05-01", "start_time": "10:00", "end_time": "09:00"},  # 04: end precedes start is a 422
        {"start_time": "10:00"},  # a time needs a day
        {"day": "2027-05-01", "end_time": "10:00"},  # an end needs a start
        {"lat": 1.0},  # lat and lon go together
        {"cost": {"amount_minor": -1, "currency": "EUR"}},
        {"notes": "n" * 4001},
        {"category": "weird"},
    ],
)
def test_create_validation_is_422(client, world, body):
    r = client.post(f"/v1/trips/{world['t']['id']}/items", json={"title": "T", "category": "sights", **body}, headers=world["e"])
    assert r.status_code == 422 and r.json()["code"] == "validation_failed", r.text


def test_viewer_reads_but_every_write_is_403_and_a_stranger_gets_404(client, world):
    tid = world["t"]["id"]
    item = _add(client, world, day="2027-05-01")
    v, s = world["v"], world["s"]
    assert client.get(f"/v1/trips/{tid}/items", headers=v).status_code == 200
    assert client.get(f"/v1/trips/{tid}/days", headers=v).status_code == 200
    assert client.get(f"/v1/items/{item['id']}", headers=v).status_code == 200
    ifm = {"If-Match": '"1"'}
    writes = [
        ("POST", f"/v1/trips/{tid}/items", {"title": "x", "category": "other"}),
        ("POST", f"/v1/trips/{tid}/items/bulk", {"items": [{"title": "x", "category": "other"}]}),
        ("PATCH", f"/v1/items/{item['id']}", {"title": "x"}),
        ("DELETE", f"/v1/items/{item['id']}", None),
        ("POST", f"/v1/items/{item['id']}/move", {"day": None}),
        ("POST", f"/v1/trips/{tid}/days/2027-05-01/reorder", {"ids": [item["id"]]}),
        ("PUT", f"/v1/trips/{tid}/days/2027-05-01", {"title": "x"}),
    ]
    for method, path, body in writes:
        r = client.request(method, path, json=body, headers={**v, **ifm})
        assert r.status_code == 403 and r.json()["code"] == "insufficient_role", (method, path, r.status_code)
        r = client.request(method, path, json=body, headers={**s, **ifm})
        assert r.status_code == 404, (method, path, r.status_code)
    assert client.get(f"/v1/items/{item['id']}", headers=s).status_code == 404
    assert client.get(f"/v1/items/{item['id']}", headers=v).json()["title"] == "Walk"


def test_patch_bumps_version_and_sets_etag(client, world):
    item = _add(client, world, day="2027-05-01")
    r = client.patch(f"/v1/items/{item['id']}", json={"title": "Renamed", "status": "booked", "day": "2027-05-02"}, headers=_ifm(world["e"], item))
    assert r.status_code == 200, r.text
    b = r.json()
    assert (b["title"], b["status"], b["day"], b["version"]) == ("Renamed", "booked", "2027-05-02", 2) and r.headers["etag"] == '"2"'
    assert client.get(f"/v1/items/{item['id']}", headers=world["v"]).headers["etag"] == '"2"'
    r = client.patch(f"/v1/items/{item['id']}", json={"title": "Body version", "version": 2}, headers=world["e"])
    assert r.status_code == 200 and r.json()["version"] == 3
    r = client.patch(f"/v1/items/{item['id']}", json={"notes": "n"}, headers=world["e"])
    assert r.status_code == 428


def test_patch_validates_the_merged_row(client, world):
    item = _add(client, world, day="2027-05-01", start_time="10:00", end_time="11:00")
    r = client.patch(f"/v1/items/{item['id']}", json={"end_time": "09:00"}, headers=_ifm(world["e"], item))
    assert r.status_code == 422
    r = client.patch(f"/v1/items/{item['id']}", json={"day": None}, headers=_ifm(world["e"], item))
    assert r.status_code == 422  # clearing the day while a time stays is not allowed; use /move, which clears the times


def test_two_editors_on_one_item_the_second_gets_409_with_the_latest_row(client, world):
    item = _add(client, world, day="2027-05-01", title="Original")
    first = client.patch(f"/v1/items/{item['id']}", json={"title": "Editor one"}, headers=_ifm(world["e"], item))
    assert first.status_code == 200
    second = client.patch(f"/v1/items/{item['id']}", json={"title": "Editor two"}, headers=_ifm(world["e2"], item))
    assert second.status_code == 409 and second.json()["code"] == "version_conflict"
    cur = second.json()["current"]
    assert cur["title"] == "Editor one" and cur["version"] == 2 and cur["id"] == item["id"]
    assert client.get(f"/v1/items/{item['id']}", headers=world["o"]).json()["title"] == "Editor one"
    retry = client.patch(f"/v1/items/{item['id']}", json={"title": "Editor two"}, headers=_ifm(world["e2"], cur))
    assert retry.status_code == 200 and retry.json()["version"] == 3


def test_delete_is_versioned(client, world):
    item = _add(client, world)
    client.patch(f"/v1/items/{item['id']}", json={"notes": "x"}, headers=_ifm(world["e"], item))
    r = client.delete(f"/v1/items/{item['id']}", headers=_ifm(world["e2"], item))
    assert r.status_code == 409 and r.json()["current"]["notes"] == "x"
    assert client.delete(f"/v1/items/{item['id']}", headers=world["e2"]).status_code == 428
    assert client.delete(f"/v1/items/{item['id']}", headers={**world["e2"], "If-Match": '"2"'}).status_code == 204
    assert client.get(f"/v1/items/{item['id']}", headers=world["o"]).status_code == 404
    assert client.delete(f"/v1/items/{item['id']}", headers={**world["e2"], "If-Match": '"2"'}).status_code == 404


def test_list_filters_and_pages(client, world):
    tid = world["t"]["id"]
    a = _add(client, world, day="2027-05-02", title="A", category="food")
    b = _add(client, world, day="2027-05-01", title="B", start_time="09:00")
    c = _add(client, world, day="2027-05-01", title="C", start_time="08:00")
    d = _add(client, world, title="Pool")
    h = world["v"]
    ids = lambda r: [x["id"] for x in r.json()["items"]]  # noqa: E731
    assert ids(client.get(f"/v1/trips/{tid}/items", headers=h)) == [c["id"], b["id"], a["id"], d["id"]]  # day, then time, then sort_order; the pool last
    assert ids(client.get(f"/v1/trips/{tid}/items?day=2027-05-01", headers=h)) == [c["id"], b["id"]]
    assert ids(client.get(f"/v1/trips/{tid}/items?unscheduled=true", headers=h)) == [d["id"]]
    assert ids(client.get(f"/v1/trips/{tid}/items?category=food", headers=h)) == [a["id"]]
    p1 = client.get(f"/v1/trips/{tid}/items?limit=3", headers=h).json()
    assert len(p1["items"]) == 3 and p1["has_more"] is True
    p2 = client.get(f"/v1/trips/{tid}/items?limit=3&cursor={p1['next_cursor']}", headers=h).json()
    assert [x["id"] for x in p2["items"]] == [d["id"]] and p2["has_more"] is False and p2["next_cursor"] is None
    assert client.get(f"/v1/trips/{tid}/items?cursor=!!!", headers=h).status_code == 422
    assert client.get(f"/v1/trips/{tid}/items?updated_since=2999-01-01T00:00:00Z", headers=h).json()["items"] == []


def test_days_cover_the_trip_range_and_include_stray_days(client, world):
    tid = world["t"]["id"]
    _add(client, world, day="2027-05-02", title="Late", start_time="18:00")
    _add(client, world, day="2027-05-02", title="Early", start_time="08:00")
    _add(client, world, day="2027-06-09", title="Outside")
    r = client.get(f"/v1/trips/{tid}/days", headers=world["v"])
    assert r.status_code == 200 and r.headers["etag"]
    days = {d["day"]: d for d in r.json()}
    assert list(days) == ["2027-05-01", "2027-05-02", "2027-05-03", "2027-06-09"]
    assert days["2027-05-01"]["item_count"] == 0 and days["2027-05-01"]["first"] is None and days["2027-05-01"]["version"] == 0
    d2 = days["2027-05-02"]
    assert d2["item_count"] == 2 and d2["first"] == {"title": "Early", "start_time": "08:00:00"} and d2["last"]["title"] == "Late"
    assert d2["timezone"] == "Europe/Lisbon" and d2["in_trip"] is True and days["2027-06-09"]["in_trip"] is False
    assert client.get(f"/v1/trips/{tid}/days?updated_since=2999-01-01T00:00:00Z", headers=world["v"]).json() == []


def test_put_day_creates_then_needs_the_version(client, world):
    tid = world["t"]["id"]
    dest = client.get(f"/v1/trips/{tid}/destinations", headers=world["e"]).json()[1]["id"]
    r = client.put(f"/v1/trips/{tid}/days/2027-05-02", json={"title": "Porto day", "notes": "Wine", "destination_id": dest}, headers=world["e"])
    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["title"], d["notes"], d["destination_id"], d["destination_name"], d["version"]) == ("Porto day", "Wine", dest, "Porto", 1) and r.headers["etag"] == '"1"'
    assert client.put(f"/v1/trips/{tid}/days/2027-05-02", json={"title": "B"}, headers=world["e"]).status_code == 428
    ok = client.put(f"/v1/trips/{tid}/days/2027-05-02", json={"title": "B", "version": 1}, headers=world["e"])
    assert ok.status_code == 200 and ok.json()["version"] == 2 and ok.json()["notes"] == "Wine"  # a field left out keeps its value
    stale = client.put(f"/v1/trips/{tid}/days/2027-05-02", json={"title": "C"}, headers={**world["e2"], "If-Match": '"1"'})
    assert stale.status_code == 409 and stale.json()["current"]["title"] == "B"
    bad = client.put(f"/v1/trips/{tid}/days/2027-05-02", json={"destination_id": str(uuid.uuid4()), "version": 2}, headers=world["e"])
    assert bad.status_code == 422
    assert client.put(f"/v1/trips/{tid}/days/2027-05-02", json={"title": "x" * 121, "version": 2}, headers=world["e"]).status_code == 422
    assert client.put(f"/v1/trips/{tid}/days/not-a-date", json={}, headers=world["e"]).status_code == 422


def test_reorder_sets_the_order_and_conflicts_when_ids_differ(client, world):
    tid = world["t"]["id"]
    a, b, c = (_add(client, world, day="2027-05-01", title=t) for t in "ABC")
    r = client.post(f"/v1/trips/{tid}/days/2027-05-01/reorder", json={"ids": [c["id"], a["id"], b["id"]]}, headers=world["e"])
    assert r.status_code == 200, r.text
    assert [x["title"] for x in r.json()] == ["C", "A", "B"]
    got = client.get(f"/v1/trips/{tid}/items?day=2027-05-01", headers=world["e"]).json()["items"]
    assert [x["title"] for x in got] == ["C", "A", "B"]
    miss = client.post(f"/v1/trips/{tid}/days/2027-05-01/reorder", json={"ids": [a["id"], b["id"]]}, headers=world["e2"])
    assert miss.status_code == 409 and miss.json()["code"] == "version_conflict" and [x["title"] for x in miss.json()["current"]] == ["C", "A", "B"]
    stale = client.post(f"/v1/trips/{tid}/days/2027-05-01/reorder", json={"ids": [a["id"], b["id"], c["id"]], "version_map": {a["id"]: 1}}, headers=world["e2"])
    assert stale.status_code == 409  # a's version moved on when the first reorder rewrote it
    ok = client.post(f"/v1/trips/{tid}/days/2027-05-01/reorder", json={"ids": [a["id"], b["id"], c["id"]]}, headers=world["e2"])
    assert ok.status_code == 200 and [x["title"] for x in ok.json()] == ["A", "B", "C"]


def test_move_between_days_and_the_pool(client, world):
    tid = world["t"]["id"]
    a, b = _add(client, world, day="2027-05-01", title="A"), _add(client, world, day="2027-05-01", title="B")
    _add(client, world, day="2027-05-02", title="X")
    y = _add(client, world, day="2027-05-02", title="Y")
    r = client.post(f"/v1/items/{a['id']}/move", json={"day": "2027-05-02", "before_id": y["id"], "start_time": None}, headers=_ifm(world["e"], a))
    assert r.status_code == 200, r.text
    assert {i["title"] for i in r.json()} >= {"A", "Y"}
    order = [i["title"] for i in client.get(f"/v1/trips/{tid}/items?day=2027-05-02", headers=world["e"]).json()["items"]]
    assert order == ["X", "A", "Y"]
    # to the end of a day, with a time
    cur = client.get(f"/v1/items/{b['id']}", headers=world["e"]).json()
    r = client.post(f"/v1/items/{b['id']}/move", json={"day": "2027-05-02", "start_time": "09:00"}, headers=_ifm(world["e"], cur))
    moved = next(i for i in r.json() if i["id"] == b["id"])
    assert moved["day"] == "2027-05-02" and moved["start_time"] == "09:00:00" and moved["version"] == 2
    # to the pool clears the times
    r = client.post(f"/v1/items/{b['id']}/move", json={"day": None}, headers=_ifm(world["e"], moved))
    pooled = next(i for i in r.json() if i["id"] == b["id"])
    assert pooled["day"] is None and pooled["start_time"] is None and pooled["end_time"] is None
    # a stale version is a 409 with the current row; an unknown before_id, or one on another day, is a 422
    r = client.post(f"/v1/items/{b['id']}/move", json={"day": "2027-05-01"}, headers=_ifm(world["e2"], b))
    assert r.status_code == 409 and r.json()["current"]["day"] is None
    cur = client.get(f"/v1/items/{b['id']}", headers=world["e"]).json()
    r = client.post(f"/v1/items/{b['id']}/move", json={"day": "2027-05-01", "before_id": str(uuid.uuid4())}, headers=_ifm(world["e"], cur))
    assert r.status_code == 422
    r = client.post(f"/v1/items/{b['id']}/move", json={"day": "2027-05-01", "before_id": a["id"]}, headers=_ifm(world["e"], cur))
    assert r.status_code == 422  # a is on another day now


def test_bulk_creates_in_one_transaction_with_the_source(client, world, system_conn):
    tid = world["t"]["id"]
    items = [{"title": f"Draft {i}", "category": "food", "day": "2027-05-01"} for i in range(3)]
    r = client.post(f"/v1/trips/{tid}/items/bulk", json={"items": items, "source": "ai_draft"}, headers=world["e"])
    assert r.status_code == 201, r.text
    got = r.json()
    assert [i["title"] for i in got] == ["Draft 0", "Draft 1", "Draft 2"] and {i["source"] for i in got} == {"ai_draft"}
    assert got[0]["sort_order"] < got[1]["sort_order"] < got[2]["sort_order"]
    # one bad item rolls everything back
    n = system_conn.execute("SELECT count(*) FROM itinerary_items WHERE trip_id = %s", (tid,)).fetchone()[0]
    bad = client.post(f"/v1/trips/{tid}/items/bulk", json={"items": [items[0], {"title": "x", "category": "food", "day": "2027-05-01", "start_time": "10:00", "end_time": "09:00"}]}, headers=world["e"])
    assert bad.status_code == 422
    assert system_conn.execute("SELECT count(*) FROM itinerary_items WHERE trip_id = %s", (tid,)).fetchone()[0] == n
    assert client.post(f"/v1/trips/{tid}/items/bulk", json={"items": [items[0]] * 51}, headers=world["e"]).status_code == 422
    assert client.post(f"/v1/trips/{tid}/items/bulk", json={"items": []}, headers=world["e"]).status_code == 422
    assert client.post(f"/v1/trips/{tid}/items/bulk", json={"items": items[:1], "source": "agent"}, headers=world["e"]).status_code == 422


def test_item_routes_resolve_the_trip_of_the_item(client, world):
    item = _add(client, world, day="2027-05-01")
    assert client.get(f"/v1/items/{uuid.uuid4()}", headers=world["e"]).status_code == 404
    assert client.get(f"/v1/items/{item['id']}", headers=world["s"]).status_code == 404


def test_ics_file_export(client, world):
    tid = world["t"]["id"]
    t = _add(client, world, day="2027-05-01", title="Tram; 28", start_time="09:30", end_time="11:00", notes="Line, early")
    _add(client, world, day="2027-05-02", title="Beach day", cost={"amount_minor": 999, "currency": "EUR"})
    _add(client, world, title="Pool idea")
    r = client.get(f"/v1/trips/{tid}/itinerary.ics", headers=world["v"])
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/calendar") and "attachment" in r.headers["content-disposition"]
    body = r.text
    assert body.startswith("BEGIN:VCALENDAR\r\n") and body.endswith("END:VCALENDAR\r\n")
    unfolded = body.replace("\r\n ", "")
    assert f"UID:item-{t['id']}@hermi.world" in unfolded and "SUMMARY:Tram\\; 28" in unfolded and "DTSTART:20270501T083000Z" in unfolded  # Lisbon is UTC+1 in May
    assert "DTSTART;VALUE=DATE:20270502" in unfolded and "Pool idea" not in body and "999" not in body
    assert "X-WR-TIMEZONE:Europe/Lisbon" in unfolded
    assert client.get(f"/v1/trips/{tid}/itinerary.ics", headers=world["s"]).status_code == 404
