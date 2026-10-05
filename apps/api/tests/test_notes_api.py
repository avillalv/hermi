# ruff: noqa: E501  (long lines)
"""WF-035.1: notes (04 section 5.14): CRUD with sources, private notes visible only to their author, versioned PATCH, stale flag, roles, URL validation."""

import socket
import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14, "timezone": "Europe/Lisbon"}


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
    """Trip owned by `o` with editors `e` and `e2`, viewer `v` and stranger `s`."""
    o, ou = _user(client)
    people = {k: _user(client) for k in ("e", "e2", "v", "s")}
    t = client.post("/v1/trips", json={"name": "Trip", "destinations": [LISBON], "start_date": "2027-05-01", "end_date": "2027-05-05"}, headers=o).json()
    for k, role in (("e", "editor"), ("e2", "editor"), ("v", "viewer")):
        system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (t["id"], people[k][1]["id"], role))
    return {"o": o, "tid": t["id"], "ids": {"o": ou["id"], **{k: people[k][1]["id"] for k in people}}, **{k: people[k][0] for k in people}}


def _add(client, w, who="e", **kw):
    r = client.post(f"/v1/trips/{w['tid']}/notes", json={"body": "Hello", **kw}, headers=w[who])
    assert r.status_code == 201, r.text
    return r.json()


def _ids(client, w, who):
    r = client.get(f"/v1/trips/{w['tid']}/notes", headers=w[who])
    assert r.status_code == 200, r.text
    return [n["id"] for n in r.json()["items"]]


def test_note_saves_with_source(client, world):
    n = _add(client, world, title="Tip", source_url="https://www.Example.com/tips?a=1#x", pinned=True)
    assert n["kind"] == "user" and n["version"] == 1 and n["pinned"] is True and n["is_private"] is False and n["stale"] is False
    assert n["sources"][0]["url"] == "https://www.Example.com/tips?a=1#x"  # stored as pasted
    assert n["sources"][0]["site"] == "example.com"
    assert n["author"]["id"] == world["ids"]["e"] and n["run_id"] is None and n["day"] is None and n["item_id"] is None
    got = client.get(f"/v1/trips/{world['tid']}/notes", headers=world["v"]).json()
    assert got["items"][0]["id"] == n["id"] and got["has_more"] is False
    plain = _add(client, world, body="No source")
    assert plain["sources"] == []


def test_network_stays_blocked(client, world):
    with pytest.raises(AssertionError):
        socket.getaddrinfo("www.airbnb.com", 443)
    n = _add(client, world, source_url="https://www.airbnb.com/rooms/1")
    assert n["sources"][0]["site"] == "airbnb.com"


@pytest.mark.parametrize("url", ["ftp://example.com/x", "javascript:alert(1)", "not a url", "http://127.0.0.1/", "https://example.com/" + "a" * 2100])
def test_bad_source_url_is_422(client, world, url):
    r = client.post(f"/v1/trips/{world['tid']}/notes", json={"body": "x", "source_url": url}, headers=world["e"])
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"


def test_validation_and_links(client, world):
    url = f"/v1/trips/{world['tid']}/notes"
    assert client.post(url, json={}, headers=world["e"]).status_code == 422
    assert client.post(url, json={"body": "x" * 10001}, headers=world["e"]).status_code == 422
    assert client.post(url, json={"body": "x", "title": "t" * 161}, headers=world["e"]).status_code == 422
    assert _add(client, world, kind="agent")["kind"] == "user"  # kind cannot be forced to agent
    assert _add(client, world, day="2027-05-02")["day"] == "2027-05-02"
    assert client.post(url, json={"body": "x", "item_id": str(uuid.uuid4())}, headers=world["e"]).status_code == 422


def test_roles(client, world):
    url = f"/v1/trips/{world['tid']}/notes"
    assert client.post(url, json={"body": "x"}, headers=world["v"]).status_code == 403
    assert client.post(url, json={"body": "x"}, headers=world["s"]).status_code == 404
    assert client.get(url, headers=world["s"]).status_code == 404
    assert client.get(url, headers=world["v"]).status_code == 200
    n = _add(client, world)
    assert client.patch(f"/v1/notes/{n['id']}", json={"body": "y", "version": 1}, headers=world["v"]).status_code == 403
    assert client.patch(f"/v1/notes/{n['id']}", json={"body": "y", "version": 1}, headers=world["s"]).status_code == 404
    assert client.delete(f"/v1/notes/{n['id']}", headers=world["v"]).status_code == 403
    assert client.delete(f"/v1/notes/{n['id']}", headers=world["s"]).status_code == 404
    # another editor is neither the author nor the owner
    assert client.patch(f"/v1/notes/{n['id']}", json={"body": "y", "version": 1}, headers=world["e2"]).status_code == 403
    assert client.delete(f"/v1/notes/{n['id']}", headers=world["e2"]).status_code == 403
    # the owner may
    assert client.patch(f"/v1/notes/{n['id']}", json={"body": "by owner", "version": 1}, headers=world["o"]).status_code == 200
    assert client.delete(f"/v1/notes/{n['id']}", headers=world["o"]).status_code == 204
    assert client.get(f"/v1/notes/{n['id']}/evidence", headers=world["v"]).status_code == 404


def test_patch_is_versioned(client, world):
    n = _add(client, world, title="A")
    assert client.patch(f"/v1/notes/{n['id']}", json={"body": "B"}, headers=world["e"]).status_code == 428
    r = client.patch(f"/v1/notes/{n['id']}", json={"body": "B", "source_url": "https://example.org/a"}, headers={**world["e"], "If-Match": '"1"'})
    assert r.status_code == 200 and r.json()["version"] == 2 and r.json()["body"] == "B" and r.json()["sources"][0]["site"] == "example.org" and r.headers["etag"] == '"2"'
    stale = client.patch(f"/v1/notes/{n['id']}", json={"body": "C"}, headers={**world["e"], "If-Match": '"1"'})
    assert stale.status_code == 409 and stale.json()["current"]["body"] == "B"
    cleared = client.patch(f"/v1/notes/{n['id']}", json={"source_url": None, "version": 2}, headers=world["e"])
    assert cleared.status_code == 200 and cleared.json()["sources"] == [] and cleared.json()["body"] == "B"
    assert client.patch(f"/v1/notes/{n['id']}", json={"body": None, "version": 3}, headers=world["e"]).status_code == 422
    assert client.patch(f"/v1/notes/{n['id']}", json={"source_url": "ftp://x.com/", "version": 3}, headers=world["e"]).status_code == 422


def test_private_notes_are_author_only(client, world):
    p = _add(client, world, who="e", body="secret plan", is_private=True)
    pid = p["id"]
    assert p["is_private"] is True
    assert pid in _ids(client, world, "e")
    for who in ("o", "e2", "v"):
        assert pid not in _ids(client, world, who)
        assert client.patch(f"/v1/notes/{pid}", json={"body": "x", "version": 1}, headers=world[who]).status_code == 404
        assert client.delete(f"/v1/notes/{pid}", headers=world[who]).status_code == 404
        assert client.get(f"/v1/notes/{pid}/evidence", headers=world[who]).status_code == 404
    assert client.get(f"/v1/notes/{pid}/evidence", headers=world["e"]).status_code == 200
    # private notes never reach the activity feed, for anyone
    for who in ("e", "o"):
        feed = client.get(f"/v1/trips/{world['tid']}/activity", headers=world[who])
        assert feed.status_code == 200 and "secret plan" not in feed.text and pid not in feed.text
    # an author can make a shared note private, and others stop seeing it
    shared = _add(client, world, who="e", body="shared")
    assert shared["id"] in _ids(client, world, "o")
    r = client.patch(f"/v1/notes/{shared['id']}", json={"is_private": True, "version": 1}, headers=world["e"])
    assert r.status_code == 200 and r.json()["is_private"] is True
    assert shared["id"] not in _ids(client, world, "o")
    # the author can edit and delete their private note
    assert client.patch(f"/v1/notes/{pid}", json={"body": "new", "version": 1}, headers=world["e"]).json()["body"] == "new"
    assert client.delete(f"/v1/notes/{pid}", headers=world["e"]).status_code == 204


def test_shared_notes_reach_the_feed_without_the_text(client, world):
    n = _add(client, world, body="visible note body")
    feed = client.get(f"/v1/trips/{world['tid']}/activity", headers=world["o"])
    assert n["id"] in feed.text and "visible note body" not in feed.text


def _agent(system_conn, w, checked_days_ago):
    r = system_conn.execute(
        "INSERT INTO notes (trip_id, kind, title, body, urls, checked_at) VALUES (%s, 'agent', 'Found', 'Open daily', %s, now() - make_interval(days => %s)) RETURNING id",
        (w["tid"], ["https://example.com/hours"], checked_days_ago),
    ).fetchone()
    return str(r[0])


def test_stale_flag_and_evidence(client, world, system_conn):
    old, fresh = _agent(system_conn, world, 15), _agent(system_conn, world, 3)
    items = {n["id"]: n for n in client.get(f"/v1/trips/{world['tid']}/notes?kind=agent", headers=world["v"]).json()["items"]}
    assert items[old]["stale"] is True and items[fresh]["stale"] is False and items[old]["kind"] == "agent" and items[old]["author"] is None
    ev = client.get(f"/v1/notes/{old}/evidence", headers=world["v"]).json()
    assert ev["note_id"] == old and ev["stale"] is True and ev["stale_after_days"] == 14 and ev["sources"][0]["url"] == "https://example.com/hours" and ev["run_id"] is None and "checked_at" in ev
    assert client.get(f"/v1/notes/{fresh}/evidence", headers=world["v"]).json()["stale"] is False
    user = _add(client, world)
    assert user["stale"] is False
    assert client.get(f"/v1/trips/{world['tid']}/notes?kind=user", headers=world["v"]).json()["items"][0]["id"] == user["id"]


def test_agent_notes_can_only_be_pinned(client, world, system_conn):
    a = _agent(system_conn, world, 1)
    assert client.patch(f"/v1/notes/{a}", json={"body": "edit", "version": 1}, headers=world["o"]).status_code == 422
    assert client.patch(f"/v1/notes/{a}", json={"is_private": True, "version": 1}, headers=world["o"]).status_code == 422
    r = client.patch(f"/v1/notes/{a}", json={"pinned": True, "version": 1}, headers=world["o"])
    assert r.status_code == 200 and r.json()["pinned"] is True and r.json()["body"] == "Open daily"
    assert client.delete(f"/v1/notes/{a}", headers=world["o"]).status_code == 204


def test_list_filters_and_paging(client, world):
    for i in range(3):
        _add(client, world, body=f"n{i}", pinned=(i == 0))
    page = client.get(f"/v1/trips/{world['tid']}/notes?limit=2", headers=world["v"]).json()
    assert len(page["items"]) == 2 and page["has_more"] and page["items"][0]["pinned"] is True
    rest = client.get(f"/v1/trips/{world['tid']}/notes?limit=2&cursor={page['next_cursor']}", headers=world["v"]).json()
    assert len(rest["items"]) == 1 and not rest["has_more"]
    assert len(client.get(f"/v1/trips/{world['tid']}/notes?pinned=true", headers=world["v"]).json()["items"]) == 1
    assert client.get(f"/v1/trips/{world['tid']}/notes?updated_since=2999-01-01T00:00:00Z", headers=world["v"]).json()["items"] == []
