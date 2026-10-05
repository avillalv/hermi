# ruff: noqa: E501  (long comments)
"""WF-019.1: GET, PATCH, DELETE, restore, duplicate and destination routes (04 sections 5.4 and 5.5)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14}
PORTO = {"name": "Porto", "country": "Portugal", "country_code": "PT", "lat": 41.15, "lon": -8.61}
FARO = {"name": "Faro", "country": "Portugal", "country_code": "PT", "lat": 37.02, "lon": -7.93}


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
    )
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h)
    assert r.status_code == 201
    return h, r.json()


def _trip(client, h, **kw):
    r = client.post("/v1/trips", json={"name": "Trip", "destinations": [LISBON, PORTO], **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _ifm(h, t):
    return {**h, "If-Match": f'"{t["version"]}"'}


@pytest.fixture
def world(client, system_conn):
    """A trip owned by `o` with an editor `e` and a viewer `v`, and a stranger `s`."""
    o, _ = _user(client)
    e, em = _user(client)
    v, vm = _user(client)
    s, _ = _user(client)
    t = _trip(client, o, start_date="2027-03-12", end_date="2027-03-19")
    for uid, role in ((em["id"], "editor"), (vm["id"], "viewer")):
        system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (t["id"], uid, role))
    return {"o": o, "e": e, "v": v, "s": s, "t": t}


def test_get_returns_the_trip_with_role_and_etag(client, world):
    t = world["t"]
    for who, role in (("o", "owner"), ("e", "editor"), ("v", "viewer")):
        r = client.get(f"/v1/trips/{t['id']}", headers=world[who])
        assert r.status_code == 200 and r.json()["my_role"] == role and r.headers["etag"] == '"1"'
    assert [d["name"] for d in r.json()["destinations"]] == ["Lisbon", "Porto"]


def test_a_stranger_gets_404_on_every_trip_route(client, world):
    s, tid = world["s"], world["t"]["id"]
    for method, path, body in (
        ("GET", f"/v1/trips/{tid}", None),
        ("PATCH", f"/v1/trips/{tid}", {"name": "x"}),
        ("DELETE", f"/v1/trips/{tid}", None),
        ("POST", f"/v1/trips/{tid}/restore", None),
        ("POST", f"/v1/trips/{tid}/duplicate", {}),
        ("GET", f"/v1/trips/{tid}/destinations", None),
        ("POST", f"/v1/trips/{tid}/destinations", FARO),
    ):
        r = client.request(method, path, json=body, headers={**s, "If-Match": '"1"'})
        assert r.status_code == 404, (method, path, r.status_code)
    assert client.get(f"/v1/trips/{tid}", headers=world["o"]).json()["name"] == "Trip"


def test_patch_edits_name_notes_dates_and_bumps_the_version(client, world):
    t = world["t"]
    body = {"name": "  Lisbon again ", "notes": "Pack light", "start_date": "2027-04-01", "end_date": "2027-04-05", "home_currency": "USD"}
    r = client.patch(f"/v1/trips/{t['id']}", json=body, headers=_ifm(world["e"], t))
    assert r.status_code == 200, r.text
    b = r.json()
    assert (b["name"], b["notes"], b["start_date"], b["home_currency"], b["version"]) == ("Lisbon again", "Pack light", "2027-04-01", "USD", 2)
    assert r.headers["etag"] == '"2"'


def test_patch_without_a_version_is_428_and_a_stale_one_is_409_with_current(client, world):
    t = world["t"]
    assert client.patch(f"/v1/trips/{t['id']}", json={"name": "A"}, headers=world["o"]).status_code == 428
    assert client.patch(f"/v1/trips/{t['id']}", json={"name": "A"}, headers=_ifm(world["o"], t)).status_code == 200
    r = client.patch(f"/v1/trips/{t['id']}", json={"name": "B"}, headers=_ifm(world["o"], t))
    assert r.status_code == 409 and r.json()["code"] == "version_conflict"
    assert r.json()["current"]["name"] == "A" and r.json()["current"]["version"] == 2
    ok = client.patch(f"/v1/trips/{t['id']}", json={"name": "C", "version": 2}, headers=world["o"])
    assert ok.status_code == 200 and ok.json()["name"] == "C"


def test_patch_by_a_viewer_is_403_insufficient_role(client, world):
    t = world["t"]
    r = client.patch(f"/v1/trips/{t['id']}", json={"name": "Nope"}, headers=_ifm(world["v"], t))
    assert r.status_code == 403 and r.json()["code"] == "insufficient_role"
    assert client.get(f"/v1/trips/{t['id']}", headers=world["o"]).json()["name"] == "Trip"


@pytest.mark.parametrize("field", [{"status": "booked"}, {"ai_enabled": False}, {"editors_can_invite": True}])
def test_owner_only_fields_are_403_for_an_editor(client, world, field):
    t = world["t"]
    r = client.patch(f"/v1/trips/{t['id']}", json=field, headers=_ifm(world["e"], t))
    assert r.status_code == 403 and r.json()["code"] == "insufficient_role"
    r = client.patch(f"/v1/trips/{t['id']}", json=field, headers=_ifm(world["o"], t))
    assert r.status_code == 200


@pytest.mark.parametrize(
    "body",
    [{"name": ""}, {"name": None}, {"start_date": "2027-03-12", "end_date": "2027-03-01"}, {"start_date": "2027-09-01"}, {"start_date": None}, {"destinations": [LISBON] * 13}, {"status": "weird"}],
)
def test_patch_invalid_bodies_are_422(client, world, body):
    t = world["t"]
    r = client.patch(f"/v1/trips/{t['id']}", json=body, headers=_ifm(world["o"], t))
    assert r.status_code == 422 and r.json()["code"] == "validation_failed", r.text


def test_patch_clears_both_dates_together(client, world):
    t = world["t"]
    r = client.patch(f"/v1/trips/{t['id']}", json={"start_date": None, "end_date": None}, headers=_ifm(world["o"], t))
    assert r.status_code == 200 and r.json()["start_date"] is None and r.json()["end_date"] is None


def test_archive_sets_status_and_archived_at_and_frees_a_slot(client, world, system_conn):
    h, t = world["o"], world["t"]
    r = client.patch(f"/v1/trips/{t['id']}", json={"status": "archived"}, headers=_ifm(h, t))
    assert r.status_code == 200 and r.json()["status"] == "archived"
    assert system_conn.execute("SELECT archived_at IS NOT NULL FROM trips WHERE id = %s", (t["id"],)).fetchone() == (True,)
    assert client.get("/v1/trips", params={"status": "archived"}, headers=h).json()["items"][0]["id"] == t["id"]
    r = client.patch(f"/v1/trips/{t['id']}", json={"status": "planning"}, headers={**h, "If-Match": '"2"'})
    assert r.status_code == 200
    assert system_conn.execute("SELECT archived_at IS NULL FROM trips WHERE id = %s", (t["id"],)).fetchone() == (True,)


def test_patch_replaces_destinations_keeping_ids_and_ordering(client, world):
    h, t = world["o"], world["t"]
    lisbon_id = t["destinations"][0]["id"]
    body = {"destinations": [{**FARO}, {"id": lisbon_id, **LISBON, "name": "Lisboa"}]}
    r = client.patch(f"/v1/trips/{t['id']}", json=body, headers=_ifm(h, t))
    assert r.status_code == 200, r.text
    ds = r.json()["destinations"]
    assert [(d["name"], d["position"]) for d in ds] == [("Faro", 0), ("Lisboa", 1)] and ds[1]["id"] == lisbon_id


def test_patch_destination_id_from_another_trip_is_422(client, world):
    h, t = world["o"], world["t"]
    other = _trip(client, world["s"])
    body = {"destinations": [{"id": other["destinations"][0]["id"], **LISBON}]}
    r = client.patch(f"/v1/trips/{t['id']}", json=body, headers=_ifm(h, t))
    assert r.status_code == 422


def test_patch_traveler_ids_must_be_mine(client, world):
    h, t = world["o"], world["t"]
    _, other = _user(client)
    r = client.patch(f"/v1/trips/{t['id']}", json={"traveler_ids": [other["me_person_id"]]}, headers=_ifm(h, t))
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "traveler_ids"


def test_delete_moves_to_trash_and_restore_brings_it_back(client, world, system_conn):
    h, t = world["o"], world["t"]
    system_conn.execute("UPDATE trips SET calendar_token_hash = '\\x01' WHERE id = %s", (t["id"],))
    assert client.delete(f"/v1/trips/{t['id']}", headers=h).status_code == 204
    assert client.get(f"/v1/trips/{t['id']}", headers=h).status_code == 404
    assert client.get("/v1/trips", headers=h).json()["items"] == []
    row = system_conn.execute("SELECT deleted_at IS NOT NULL, calendar_token_hash IS NULL FROM trips WHERE id = %s", (t["id"],)).fetchone()
    assert row == (True, True)
    r = client.post(f"/v1/trips/{t['id']}/restore", headers=h)
    assert r.status_code == 200 and r.json()["id"] == t["id"] and r.json()["my_role"] == "owner"
    assert client.get(f"/v1/trips/{t['id']}", headers=h).status_code == 200


def test_delete_revokes_invites_and_share_links(client, world, system_conn):
    h, t = world["o"], world["t"]
    system_conn.execute("INSERT INTO trip_invites (trip_id, token_hash) VALUES (%s, '\\x0102')", (t["id"],))
    system_conn.execute("INSERT INTO trip_share_links (trip_id, token_hash) VALUES (%s, '\\x0304')", (t["id"],))
    assert client.delete(f"/v1/trips/{t['id']}", headers=h).status_code == 204
    assert system_conn.execute("SELECT revoked_at IS NOT NULL FROM trip_invites WHERE trip_id = %s", (t["id"],)).fetchone() == (True,)
    assert system_conn.execute("SELECT revoked_at IS NOT NULL FROM trip_share_links WHERE trip_id = %s", (t["id"],)).fetchone() == (True,)


def test_delete_and_restore_are_owner_only(client, world):
    t = world["t"]
    for who in ("e", "v"):
        r = client.delete(f"/v1/trips/{t['id']}", headers=world[who])
        assert r.status_code == 403 and r.json()["code"] == "insufficient_role"
    assert client.delete(f"/v1/trips/{t['id']}", headers=world["o"]).status_code == 204
    # trash is visible to its owner only (trips_select), so others get 404
    for who in ("e", "v"):
        assert client.post(f"/v1/trips/{t['id']}/restore", headers=world[who]).status_code == 404
    assert client.post(f"/v1/trips/{t['id']}/restore", headers=world["s"]).status_code == 404


def test_restore_after_30_days_is_404_and_of_a_live_trip_is_404(client, world, system_conn):
    h, t = world["o"], world["t"]
    assert client.post(f"/v1/trips/{t['id']}/restore", headers=h).status_code == 404
    client.delete(f"/v1/trips/{t['id']}", headers=h)
    system_conn.execute("UPDATE trips SET deleted_at = now() - interval '31 days' WHERE id = %s", (t["id"],))
    assert client.post(f"/v1/trips/{t['id']}/restore", headers=h).status_code == 404


def test_duplicate_copies_destinations_into_a_new_owned_trip_and_shifts_dates(client, world, system_conn):
    h, t = world["o"], world["t"]
    client.patch(f"/v1/trips/{t['id']}", json={"status": "archived"}, headers=_ifm(h, t))
    r = client.post(f"/v1/trips/{t['id']}/duplicate", json={"start_date": "2028-05-01"}, headers=h)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["id"] != t["id"] and d["name"] == "Trip (copy)" and d["status"] == "planning" and d["my_role"] == "owner" and d["version"] == 1
    assert (d["start_date"], d["end_date"]) == ("2028-05-01", "2028-05-08")
    assert [x["name"] for x in d["destinations"]] == ["Lisbon", "Porto"] and d["destinations"][0]["id"] != t["destinations"][0]["id"]
    assert r.headers["location"] == f"/v1/trips/{d['id']}"
    ids = [x["id"] for x in client.get("/v1/trips", headers=h).json()["items"]]
    assert d["id"] in ids and t["id"] in ids
    assert system_conn.execute("SELECT count(*) FROM trip_members WHERE trip_id = %s", (d["id"],)).fetchone() == (1,)


def test_duplicate_without_a_start_date_has_no_dates(client, world):
    h, t = world["o"], world["t"]
    d = client.post(f"/v1/trips/{t['id']}/duplicate", json={"name": "Next one"}, headers=h)
    assert d.status_code == 201 and d.json()["name"] == "Next one" and d.json()["start_date"] is None and d.json()["end_date"] is None


def test_duplicate_is_refused_for_editors_and_viewers(client, world):
    t = world["t"]
    for who in ("e", "v"):
        r = client.post(f"/v1/trips/{t['id']}/duplicate", json={}, headers=world[who])
        assert r.status_code == 403 and r.json()["code"] == "insufficient_role"


def test_duplicate_counts_toward_the_active_trip_limit(client, world):
    h, t = world["o"], world["t"]
    _trip(client, h)  # a second active trip
    r = client.post(f"/v1/trips/{t['id']}/duplicate", json={}, headers=h)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"


def test_destination_routes(client, world):
    h, v, t = world["o"], world["v"], world["t"]
    tid = t["id"]
    ds = client.get(f"/v1/trips/{tid}/destinations", headers=v).json()
    assert [d["name"] for d in ds] == ["Lisbon", "Porto"]
    r = client.post(f"/v1/trips/{tid}/destinations", json=FARO, headers=h)
    assert r.status_code == 201 and r.json()["position"] == 2 and r.json()["info_status"] == "pending"
    faro = r.json()["id"]
    r = client.patch(f"/v1/trips/{tid}/destinations/{faro}", json={"name": "Faro city"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "Faro city"
    order = [faro, ds[0]["id"], ds[1]["id"]]
    r = client.put(f"/v1/trips/{tid}/destinations/order", json={"ids": order}, headers=h)
    assert r.status_code == 200 and [d["id"] for d in r.json()] == order and [d["position"] for d in r.json()] == [0, 1, 2]
    assert client.put(f"/v1/trips/{tid}/destinations/order", json={"ids": order[:2]}, headers=h).status_code == 422
    assert client.delete(f"/v1/trips/{tid}/destinations/{faro}", headers=h).status_code == 204
    left = client.get(f"/v1/trips/{tid}/destinations", headers=h).json()
    assert [d["name"] for d in left] == ["Lisbon", "Porto"] and [d["position"] for d in left] == [0, 1]


def test_destination_writes_refused_for_viewers_and_capped_at_12(client, world):
    h, v, t = world["o"], world["v"], world["t"]
    tid, d0 = t["id"], t["destinations"][0]["id"]
    for method, path, body in (
        ("POST", f"/v1/trips/{tid}/destinations", FARO),
        ("PATCH", f"/v1/trips/{tid}/destinations/{d0}", {"name": "x"}),
        ("DELETE", f"/v1/trips/{tid}/destinations/{d0}", None),
        ("PUT", f"/v1/trips/{tid}/destinations/order", {"ids": []}),
    ):
        r = client.request(method, path, json=body, headers=v)
        assert r.status_code == 403 and r.json()["code"] == "insufficient_role", (method, path)
    for _ in range(10):
        assert client.post(f"/v1/trips/{tid}/destinations", json=FARO, headers=h).status_code == 201
    assert client.post(f"/v1/trips/{tid}/destinations", json=FARO, headers=h).status_code == 422


def test_destination_of_another_trip_is_404(client, world):
    h, t = world["o"], world["t"]
    other = _trip(client, world["s"])
    foreign = other["destinations"][0]["id"]
    assert client.patch(f"/v1/trips/{t['id']}/destinations/{foreign}", json={"name": "x"}, headers=h).status_code == 404
    assert client.delete(f"/v1/trips/{t['id']}/destinations/{foreign}", headers=h).status_code == 404


def test_smoke_flow_26_archive_a_past_trip_then_duplicate_it(client):
    """10 section 1.6 flow 26, backend part."""
    h, _ = _user(client)
    past = _trip(client, h, start_date="2024-06-01", end_date="2024-06-07")
    assert client.patch(f"/v1/trips/{past['id']}", json={"status": "archived"}, headers=_ifm(h, past)).status_code == 200
    r = client.post(f"/v1/trips/{past['id']}/duplicate", json={"start_date": "2027-06-01"}, headers=h)
    assert r.status_code == 201
    items = {t["id"]: t for t in client.get("/v1/trips", headers=h).json()["items"]}
    assert items[r.json()["id"]]["status"] == "planning" and items[past["id"]]["status"] == "archived"


def test_archive_frees_a_slot_at_the_limit(client):
    h, _ = _user(client)
    a, _b = _trip(client, h), _trip(client, h)
    assert client.post("/v1/trips", json={"name": "Three"}, headers=h).status_code == 402
    assert client.patch(f"/v1/trips/{a['id']}", json={"status": "archived"}, headers=_ifm(h, a)).status_code == 200
    assert client.post("/v1/trips", json={"name": "Three"}, headers=h).status_code == 201


def test_unarchive_at_the_limit_is_402(client):
    h, _ = _user(client)
    a = _trip(client, h)
    r = client.patch(f"/v1/trips/{a['id']}", json={"status": "archived"}, headers=_ifm(h, a))
    _trip(client, h)
    _trip(client, h)
    r2 = client.patch(f"/v1/trips/{a['id']}", json={"status": "planning"}, headers={**h, "If-Match": f'"{r.json()["version"]}"'})
    assert r2.status_code == 402 and r2.json()["code"] == "limit_reached"


def test_restore_at_the_limit_is_402(client):
    h, _ = _user(client)
    a = _trip(client, h)
    assert client.delete(f"/v1/trips/{a['id']}", headers=h).status_code == 204
    _trip(client, h)
    _trip(client, h)
    r = client.post(f"/v1/trips/{a['id']}/restore", headers=h)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"


def test_patch_with_a_repeated_destination_id_is_422(client, world):
    h, t = world["o"], world["t"]
    d = t["destinations"][0]["id"]
    r = client.patch(f"/v1/trips/{t['id']}", json={"destinations": [{"id": d, **LISBON}, {"id": d, **LISBON}]}, headers=_ifm(h, t))
    assert r.status_code == 422


def test_patch_destination_keeps_fields_the_client_did_not_send(client, world, system_conn):
    h = world["o"]
    rich = {**PORTO, "kind": "city", "bbox": [-8.7, 41.1, -8.5, 41.2], "geoapify_place_id": "gp-1", "timezone": "Europe/Lisbon"}
    t = _trip(client, h, destinations=[rich])
    did = t["destinations"][0]["id"]
    body = {"destinations": [{"id": did, "name": "Oporto", "lat": 41.15, "lon": -8.61}]}
    r = client.patch(f"/v1/trips/{t['id']}", json=body, headers=_ifm(h, t))
    assert r.status_code == 200, r.text
    row = system_conn.execute("SELECT name, kind, bbox, geoapify_place_id, timezone, country FROM trip_destinations WHERE id = %s", (did,)).fetchone()
    assert row[0] == "Oporto" and row[1] == "city" and list(row[2]) == [-8.7, 41.1, -8.5, 41.2] and row[3:] == ("gp-1", "Europe/Lisbon", "Portugal")
    # An explicit null still clears.
    t = client.get(f"/v1/trips/{t['id']}", headers=h).json()
    client.patch(f"/v1/trips/{t['id']}", json={"destinations": [{"id": did, "name": "Oporto", "lat": 41.15, "lon": -8.61, "timezone": None}]}, headers=_ifm(h, t))
    assert system_conn.execute("SELECT timezone, kind FROM trip_destinations WHERE id = %s", (did,)).fetchone() == (None, "city")


def test_get_lists_the_trip_travelers_with_is_me_per_caller(client, world, system_conn):
    t, me_person = world["t"], None
    r = client.get(f"/v1/trips/{t['id']}", headers=world["o"])
    assert [p["is_me"] for p in r.json()["travelers"]] == [True]
    me_person = r.json()["travelers"][0]
    assert set(me_person) == {"id", "name", "color", "home_airports", "linked_user_id", "is_me"}
    # a person I own who is not on the trip stays out
    extra = client.post("/v1/people", json={"name": "Zed", "color": "#2BBFAD", "home_airports": []}, headers=world["o"]).json()
    assert extra["id"] not in [p["id"] for p in client.get(f"/v1/trips/{t['id']}", headers=world["o"]).json()["travelers"]]
    # a co-member sees the same traveler, and it is not theirs
    assert [p["is_me"] for p in client.get(f"/v1/trips/{t['id']}", headers=world["v"]).json()["travelers"]] == [False]
    # a person only in another trip never shows
    other = _trip(client, world["s"])
    assert me_person["id"] not in [p["id"] for p in client.get(f"/v1/trips/{other['id']}", headers=world["s"]).json()["travelers"]]
