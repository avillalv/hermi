# ruff: noqa: E501  (long comments)
"""WF-024.1: people, trip travelers and the "Which traveler are you?" link (04 sections 5.6 and 5.7)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token


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
    h = {
        "Authorization": "Bearer "
        + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")
    }
    r = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h
    )
    assert r.status_code == 201
    return h, r.json()


def _trip(client, h, **kw):
    r = client.post("/v1/trips", json={"name": "Trip", **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _person(client, h, name="Mo", **kw):
    r = client.post(
        "/v1/people", json={"name": name, "color": "#112233", "home_airports": [], **kw}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()


def _join(system_conn, trip, user, role="editor"):
    system_conn.execute(
        "INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)",
        (trip["id"], user["id"], role),
    )


def _linked(system_conn, person):
    return system_conn.execute(
        "SELECT linked_user_id FROM people WHERE id = %s", (person["id"],)
    ).fetchone()[0]


def test_create_returns_person_and_lists_it(client):
    h, _ = _user(client)
    p = _person(client, h, "Ana", home_airports=["LIS", "OPO"])
    assert set(p) == {"id", "name", "color", "home_airports", "linked_user_id", "is_me"}
    assert (
        p["linked_user_id"] is None and p["is_me"] is False and p["home_airports"] == ["LIS", "OPO"]
    )
    people = client.get("/v1/people", headers=h).json()
    assert (
        people[-1]["name"] == "Ana" and [x["is_me"] for x in people].count(True) == 1
    )  # the auto "Me"


@pytest.mark.parametrize(
    "body",
    [
        {"name": "", "color": "#112233", "home_airports": []},
        {"name": "x" * 61, "color": "#112233", "home_airports": []},
        {"name": "A", "color": "red", "home_airports": []},
        {"name": "A", "color": "#112233", "home_airports": ["lis"]},
        {"name": "A", "color": "#112233", "home_airports": ["LIS"] * 7},
    ],
)
def test_person_validation(client, body):
    h, _ = _user(client)
    assert client.post("/v1/people", json=body, headers=h).status_code == 422


def test_person_has_no_birthdate_or_email_field_even_if_sent(client):
    h, _ = _user(client)
    p = _person(client, h, birthdate="2010-01-01", email="a@b.co")
    assert "birthdate" not in p and "email" not in p


def test_thirty_people_cap(client, system_conn):
    h, me = _user(client)
    system_conn.execute(
        "INSERT INTO people (owner_user_id, name) SELECT %s, 'P' || g FROM generate_series(1, 29) g",
        (me["id"],),
    )  # plus "Me" makes 30
    r = client.post(
        "/v1/people", json={"name": "One more", "color": "#112233", "home_airports": []}, headers=h
    )
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"


def test_get_people_hides_strangers_and_shows_co_members_people(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    s, _ = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    _join(system_conn, t, em)
    assert p["id"] in [x["id"] for x in client.get("/v1/people", headers=e).json()]
    assert p["id"] not in [x["id"] for x in client.get("/v1/people", headers=s).json()]


def test_update_person_owner_only(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    s, _ = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    _join(system_conn, t, em)
    body = {"name": "Kiddo", "color": "#abcdef", "home_airports": ["LIS"]}
    r = client.put(f"/v1/people/{p['id']}", json=body, headers=o)
    assert r.status_code == 200 and r.json()["name"] == "Kiddo" and r.json()["color"] == "#abcdef"
    assert client.put(f"/v1/people/{p['id']}", json=body, headers=e).status_code == 403
    assert client.put(f"/v1/people/{p['id']}", json=body, headers=s).status_code == 404


def test_owner_cannot_edit_a_person_linked_to_another_user(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    _join(system_conn, t, em)
    assert (
        client.put(
            f"/v1/trips/{t['id']}/members/me/traveler", json={"person_id": p["id"]}, headers=e
        ).status_code
        == 200
    )
    r = client.put(
        f"/v1/people/{p['id']}",
        json={"name": "X", "color": "#abcdef", "home_airports": []},
        headers=o,
    )
    assert r.status_code == 403


def test_link_and_unlink(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    _join(system_conn, t, em)
    url = f"/v1/trips/{t['id']}/members/me/traveler"
    r = client.put(url, json={"person_id": p["id"]}, headers=e)
    assert r.status_code == 200
    m = r.json()
    assert m["user_id"] == em["id"] and m["person_id"] == p["id"] and m["role"] == "editor"
    assert str(_linked(system_conn, p)) == em["id"]
    mine = next(x for x in client.get("/v1/people", headers=e).json() if x["id"] == p["id"])
    assert mine["is_me"] is True and mine["linked_user_id"] == em["id"]
    assert client.delete(url, headers=e).status_code == 204
    assert _linked(system_conn, p) is None
    assert client.delete(url, headers=e).status_code == 204  # idempotent


def test_a_person_links_to_one_user_per_trip(client, system_conn):
    o, _ = _user(client)
    e1, e1m = _user(client)
    e2, e2m = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    for em in (e1m, e2m):
        _join(system_conn, t, em)
    url = f"/v1/trips/{t['id']}/members/me/traveler"
    assert client.put(url, json={"person_id": p["id"]}, headers=e1).status_code == 200
    assert client.put(url, json={"person_id": p["id"]}, headers=e2).status_code == 422


def test_link_rejects_a_person_not_on_the_trip_and_non_members(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    s, _ = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o)
    _join(system_conn, t, em)
    url = f"/v1/trips/{t['id']}/members/me/traveler"
    assert (
        client.put(url, json={"person_id": p["id"]}, headers=e).status_code == 422
    )  # not on the trip
    assert client.put(url, json={"person_id": p["id"]}, headers=s).status_code == 404
    assert client.delete(url, headers=s).status_code == 404


def test_viewer_can_link(client, system_conn):
    o, _ = _user(client)
    v, vm = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    _join(system_conn, t, vm, "viewer")
    r = client.put(
        f"/v1/trips/{t['id']}/members/me/traveler", json={"person_id": p["id"]}, headers=v
    )
    assert r.status_code == 200 and r.json()["role"] == "viewer"


def test_delete_person_removes_from_trips_and_keeps_the_trip(client, system_conn):
    o, _ = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    assert client.delete(f"/v1/people/{p['id']}", headers=o).status_code == 204
    assert system_conn.execute(
        "SELECT count(*) FROM trip_people WHERE person_id = %s", (p["id"],)
    ).fetchone() == (0,)
    assert client.get(f"/v1/trips/{t['id']}", headers=o).status_code == 200
    assert client.delete(f"/v1/people/{p['id']}", headers=o).status_code == 404


def test_delete_the_only_traveler_on_a_trip_the_caller_does_not_own_is_409(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    mine = _person(client, e, "Mine")
    t = _trip(client, o)
    _join(system_conn, t, em)
    r = client.put(f"/v1/trips/{t['id']}/travelers", json={"person_ids": [mine["id"]]}, headers=e)
    assert r.status_code == 200
    r = client.delete(f"/v1/people/{mine['id']}", headers=e)
    assert r.status_code == 409 and r.json()["code"] == "state_conflict"
    assert system_conn.execute(
        "SELECT count(*) FROM trip_people WHERE person_id = %s", (mine["id"],)
    ).fetchone() == (1,)


def test_cannot_delete_the_me_person(client):
    h, me = _user(client)
    r = client.delete(f"/v1/people/{me['me_person_id']}", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "state_conflict"


def test_set_travelers_replaces_the_list(client, system_conn):
    o, _ = _user(client)
    a, b = _person(client, o, "A"), _person(client, o, "B")
    t = _trip(client, o)
    url = f"/v1/trips/{t['id']}/travelers"
    r = client.put(url, json={"person_ids": [a["id"], b["id"]]}, headers=o)
    assert r.status_code == 200 and sorted(x["name"] for x in r.json()) == ["A", "B"]
    r = client.put(url, json={"person_ids": [b["id"]]}, headers=o)
    assert [x["id"] for x in r.json()] == [b["id"]]
    assert system_conn.execute(
        "SELECT count(*) FROM trip_people WHERE trip_id = %s", (t["id"],)
    ).fetchone() == (1,)


def test_traveler_cap_free_two_plus_eight(client, system_conn):
    o, om = _user(client)
    ps = [_person(client, o, f"P{i}") for i in range(9)]
    t = _trip(client, o)
    url = f"/v1/trips/{t['id']}/travelers"
    r = client.put(url, json={"person_ids": [p["id"] for p in ps[:3]]}, headers=o)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"
    pay = r.json()["paywall"]
    assert pay["reason"] == "traveler_limit" and "trigger" not in pay and pay["free_path"]
    assert (
        client.put(url, json={"person_ids": [p["id"] for p in ps[:2]]}, headers=o).status_code
        == 200
    )
    system_conn.execute(
        "UPDATE entitlements SET tier_code = 'plus' WHERE user_id = %s", (om["id"],)
    )
    assert (
        client.put(url, json={"person_ids": [p["id"] for p in ps[:8]]}, headers=o).status_code
        == 200
    )
    assert client.put(url, json={"person_ids": [p["id"] for p in ps]}, headers=o).status_code == 402


def test_set_travelers_roles_and_ownership(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    v, vm = _user(client)
    s, _ = _user(client)
    t = _trip(client, o)
    _join(system_conn, t, em)
    _join(system_conn, t, vm, "viewer")
    other = _person(client, s, "Not yours")
    url = f"/v1/trips/{t['id']}/travelers"
    assert client.put(url, json={"person_ids": []}, headers=o).status_code == 422
    assert (
        client.put(url, json={"person_ids": [other["id"]]}, headers=e).status_code == 422
    )  # someone else's person
    assert (
        client.put(url, json={"person_ids": [_person(client, e, "E")["id"]]}, headers=v).status_code
        == 403
    )
    assert client.put(url, json={"person_ids": [other["id"]]}, headers=s).status_code == 404


def test_create_and_patch_trip_enforce_the_traveler_cap(client, system_conn):
    o, om = _user(client)
    ps = [_person(client, o, f"P{i}") for i in range(3)]
    ids = [p["id"] for p in ps]
    r = client.post("/v1/trips", json={"name": "T", "traveler_ids": ids}, headers=o)
    assert r.status_code == 402 and r.json()["paywall"]["reason"] == "traveler_limit"
    t = _trip(client, o)
    r = client.patch(
        f"/v1/trips/{t['id']}",
        json={"traveler_ids": ids},
        headers={**o, "If-Match": f'"{t["version"]}"'},
    )
    assert r.status_code == 402 and r.json()["paywall"]["reason"] == "traveler_limit"
    system_conn.execute(
        "UPDATE entitlements SET tier_code = 'plus' WHERE user_id = %s", (om["id"],)
    )
    assert (
        client.post("/v1/trips", json={"name": "T", "traveler_ids": ids}, headers=o).status_code
        == 201
    )


def test_patch_counts_travelers_other_members_added(client, system_conn):
    o, _ = _user(client)
    e, em = _user(client)
    kid = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[kid["id"]])
    _join(system_conn, t, em)
    mine = [_person(client, e, "E1"), _person(client, e, "E2")]
    r = client.patch(
        f"/v1/trips/{t['id']}",
        json={"traveler_ids": [p["id"] for p in mine]},
        headers={**e, "If-Match": f'"{t["version"]}"'},
    )
    assert r.status_code == 402  # the owner's Kid stays: 1 + 2 is over the Free cap of 2


def test_member_invited_by_has_the_inviter_name(client, system_conn):
    o, om = _user(client)
    e, em = _user(client)
    p = _person(client, o, "Kid")
    t = _trip(client, o, traveler_ids=[p["id"]])
    system_conn.execute(
        "INSERT INTO trip_members (trip_id, user_id, role, invited_by) VALUES (%s, %s, 'editor', %s)",
        (t["id"], em["id"], om["id"]),
    )
    system_conn.execute("UPDATE users SET display_name = 'Olga' WHERE id = %s", (om["id"],))
    r = client.put(
        f"/v1/trips/{t['id']}/members/me/traveler", json={"person_id": p["id"]}, headers=e
    )
    assert r.json()["invited_by"] == {"id": om["id"], "display_name": "Olga"}


def test_deleting_me_has_its_own_message(client):
    h, me = _user(client)
    r = client.delete(f"/v1/people/{me['me_person_id']}", headers=h)
    assert r.status_code == 409 and r.json()["detail"] == "Your own traveler cannot be removed."
