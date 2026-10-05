# ruff: noqa: E501, F811  (long comments; the imported client fixture is used as an argument)
"""WF-027.1: activity_log writes on trip changes and GET /v1/trips/{id}/activity (04 section 5.4, 05 section 6.24)."""

from tests.test_invites_api import _join, _plus, _trip, _user, client  # noqa: F401


def _feed(client, h, trip, **q):
    r = client.get(f"/v1/trips/{trip['id']}/activity", params=q, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _pair(client, system_conn):
    ho, owner = _user(client)
    he, editor = _user(client)
    _plus(system_conn, owner)
    trip = _trip(client, ho)
    _join(client, ho, trip, he)
    return ho, owner, he, editor, trip


def test_editor_changes_show_in_owner_feed_with_actor(client, system_conn):
    ho, owner, he, editor, trip = _pair(client, system_conn)
    dest = {"name": "Porto", "lat": 41.15, "lon": -8.61}
    d = client.post(f"/v1/trips/{trip['id']}/destinations", json=dest, headers=he).json()
    assert client.patch(f"/v1/trips/{trip['id']}", json={"name": "Portugal", "version": trip["version"]}, headers=he).status_code == 200
    client.delete(f"/v1/trips/{trip['id']}/destinations/{d['id']}", headers=he)
    page = _feed(client, ho, trip)
    got = [(i["verb"], i["entity_type"]) for i in page["items"]]
    assert got[:3] == [("removed", "destination"), ("updated", "trip"), ("added", "destination")]
    assert ("joined", "member") in got
    top = page["items"][0]
    assert top["actor"]["id"] == editor["id"] and top["actor"]["display_name"]
    assert "Porto" in top["summary"]
    assert page["has_more"] is False and page["next_cursor"] is None


def test_role_change_and_leave_are_logged(client, system_conn):
    ho, owner, he, editor, trip = _pair(client, system_conn)
    client.patch(f"/v1/trips/{trip['id']}/members/{editor['id']}", json={"role": "viewer"}, headers=ho)
    assert _feed(client, ho, trip)["items"][0]["verb"] == "role_changed"
    client.post(f"/v1/trips/{trip['id']}/leave", headers=he)
    assert _feed(client, ho, trip)["items"][0]["verb"] == "left"


def test_deleted_user_renders_as_deleted_user(client, system_conn):
    ho, owner, he, editor, trip = _pair(client, system_conn)
    client.post(f"/v1/trips/{trip['id']}/destinations", json={"name": "Faro", "lat": 37.0, "lon": -7.9}, headers=he)
    system_conn.execute("DELETE FROM users WHERE id = %s", (editor["id"],))
    item = _feed(client, ho, trip)["items"][0]
    assert item["actor"] == {"id": None, "display_name": "Deleted user"}


def test_note_text_never_in_feed(client, system_conn):
    ho, owner, he, editor, trip = _pair(client, system_conn)
    assert client.patch(f"/v1/trips/{trip['id']}", json={"notes": "SECRET plan", "version": trip["version"]}, headers=he).status_code == 200
    items = _feed(client, ho, trip)["items"]
    assert items[0]["verb"] == "updated" and all("SECRET" not in str(i) for i in items)


def test_record_skips_private_entries(client, system_conn):
    import uuid

    from hermi.db import request_transaction
    from hermi.modules.collaboration import activity

    ho, owner, he, editor, trip = _pair(client, system_conn)
    with request_transaction(client.app.state.engine, uuid.UUID(owner["id"])) as s:
        assert activity.record(s, uuid.UUID(trip["id"]), uuid.UUID(owner["id"]), "added", "note", None, "SECRET", private=True) is None
    assert all("SECRET" not in str(i) for i in _feed(client, ho, trip)["items"])


def test_keyset_pagination_and_non_member_404(client, system_conn):
    ho, owner, he, editor, trip = _pair(client, system_conn)
    for n in range(3):
        client.post(f"/v1/trips/{trip['id']}/destinations", json={"name": f"P{n}", "lat": 1, "lon": 1}, headers=he)
    p1 = _feed(client, ho, trip, limit=2)
    assert len(p1["items"]) == 2 and p1["has_more"] and p1["next_cursor"]
    p2 = _feed(client, ho, trip, limit=2, cursor=p1["next_cursor"])
    s1, s2 = [i["summary"] for i in p1["items"]], [i["summary"] for i in p2["items"]]
    assert s2 and not set(s1) & set(s2) and "id" not in p1["items"][0]
    hs, _ = _user(client)
    assert client.get(f"/v1/trips/{trip['id']}/activity", headers=hs).status_code == 404
    assert client.get(f"/v1/trips/{trip['id']}/activity", params={"cursor": "zz"}, headers=ho).status_code == 400
