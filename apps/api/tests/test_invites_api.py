# ruff: noqa: E501  (long comments)
"""WF-025.1: members, invites, accept, roles, leave and transfer (04 section 5.4 and 5.6)."""

import hashlib
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
        public_web_url="https://app.hermi.test",
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


def _trip(client, h):
    r = client.post("/v1/trips", json={"name": "Lisbon"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _invite(client, h, trip, **body):
    r = client.post(f"/v1/trips/{trip['id']}/invites", json={"role": "editor", **body}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _token(inv):
    return inv["url"].rsplit("/", 1)[1]


def _join(client, h_owner, trip, h_user, role="editor"):
    inv = _invite(client, h_owner, trip, role=role)
    r = client.post(f"/v1/invites/{_token(inv)}/accept", json={}, headers=h_user)
    assert r.status_code == 200, r.text
    return r.json()


def _plus(system_conn, user):
    """A Plus owner has 6 collaborator slots (WF-026); Free has 1."""
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus', valid_until = NULL WHERE user_id = %s", (user["id"],))


# --- invites ----------------------------------------------------------------------------------


def test_create_returns_url_once_and_stores_only_the_hash(client, system_conn):
    h, _ = _user(client)
    trip = _trip(client, h)
    inv = _invite(client, h, trip, max_uses=1)
    assert inv["url"].startswith("https://app.hermi.test/invite/") and inv["status"] == "pending"
    assert inv["uses_left"] == 1 and inv["role"] == "editor" and inv["email"] is None
    token = _token(inv)
    assert len(token) >= 22  # 128 bits
    stored = system_conn.execute("SELECT token_hash FROM trip_invites WHERE id = %s", (inv["id"],)).fetchone()[0]
    assert bytes(stored) == hashlib.sha256(token.encode()).digest()
    listed = client.get(f"/v1/trips/{trip['id']}/invites", headers=h).json()
    assert [i["id"] for i in listed] == [inv["id"]] and "url" not in listed[0] and token not in str(listed)


def test_invite_validation_and_roles(client, system_conn):
    owner, ou = _user(client)
    _plus(system_conn, ou)
    editor, _ = _user(client)
    viewer, _ = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, editor, "editor")
    _join(client, owner, trip, viewer, "viewer")
    url = f"/v1/trips/{trip['id']}/invites"
    assert client.post(url, json={"role": "owner"}, headers=owner).status_code == 422
    assert client.post(url, json={"role": "editor", "max_uses": 7}, headers=owner).status_code == 422
    assert client.post(url, json={"role": "editor", "expires_in_days": 15}, headers=owner).status_code == 422
    assert client.post(url, json={"role": "viewer"}, headers=viewer).status_code == 403
    assert client.post(url, json={"role": "viewer"}, headers=editor).status_code == 403  # the owner has not allowed it
    assert client.get(url, headers=editor).status_code == 403  # listing is owner only


def test_editor_may_invite_viewers_only_when_the_owner_allows(client, system_conn):
    owner, ou = _user(client)
    _plus(system_conn, ou)
    editor, _ = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, editor, "editor")
    system_conn.execute("UPDATE trips SET editors_can_invite = true WHERE id = %s", (trip["id"],))
    url = f"/v1/trips/{trip['id']}/invites"
    assert client.post(url, json={"role": "editor"}, headers=editor).status_code == 403
    assert client.post(url, json={"role": "viewer"}, headers=editor).status_code == 201


def test_preview_is_public_and_shows_four_fields(client):
    owner, _ = _user(client)
    trip = _trip(client, owner)
    inv = _invite(client, owner, trip, role="viewer")
    r = client.get(f"/v1/invites/{_token(inv)}")
    assert r.status_code == 200
    assert set(r.json()) == {"trip_name", "cover_url", "inviter_name", "role"}
    assert r.json()["trip_name"] == "Lisbon" and r.json()["role"] == "viewer"


def test_unknown_expired_revoked_and_used_all_return_the_same_410(client, system_conn):
    owner, _ = _user(client)
    joiner, _ = _user(client)
    trip = _trip(client, owner)
    got = [client.get(f"/v1/invites/{uuid.uuid4().hex}")]
    expired = _invite(client, owner, trip)
    system_conn.execute("UPDATE trip_invites SET expires_at = now() - interval '1 minute' WHERE id = %s", (expired["id"],))
    got.append(client.get(f"/v1/invites/{_token(expired)}"))
    revoked = _invite(client, owner, trip)
    assert client.delete(f"/v1/trips/{trip['id']}/invites/{revoked['id']}", headers=owner).status_code == 204
    got.append(client.get(f"/v1/invites/{_token(revoked)}"))
    used = _invite(client, owner, trip)
    assert client.post(f"/v1/invites/{_token(used)}/accept", json={}, headers=joiner).status_code == 200
    got.append(client.get(f"/v1/invites/{_token(used)}"))
    assert {(r.status_code, r.json()["code"], r.json()["detail"]) for r in got} == {(410, "invite_expired", got[0].json()["detail"])}
    other, _ = _user(client)
    for inv in (expired, revoked, used):
        assert client.post(f"/v1/invites/{_token(inv)}/accept", json={}, headers=other).status_code == 410
    assert client.post(f"/v1/invites/{uuid.uuid4().hex}/accept", json={}, headers=other).status_code == 410


def test_accept_joins_with_the_role_and_a_free_invitee_needs_no_slot(client, system_conn):
    owner, _ = _user(client)
    joiner, ju = _user(client)
    trip = _trip(client, owner)
    for _i in range(2):  # the joiner already owns two trips: the joined one must not matter
        _trip(client, joiner)
    inv = _invite(client, owner, trip, role="viewer")
    r = client.post(f"/v1/invites/{_token(inv)}/accept", json={}, headers=joiner)
    assert r.status_code == 200 and r.json()["id"] == trip["id"] and r.json()["my_role"] == "viewer"
    row = system_conn.execute("SELECT role, invited_by FROM trip_members WHERE trip_id = %s AND user_id = %s", (trip["id"], ju["id"])).fetchone()
    assert row[0] == "viewer" and row[1] is not None
    assert client.get(f"/v1/trips/{trip['id']}", headers=joiner).status_code == 200


def test_accept_links_the_chosen_traveler(client, system_conn):
    owner, _ = _user(client)
    joiner, ju = _user(client)
    trip = _trip(client, owner)
    p = client.post("/v1/people", json={"name": "Jo", "color": "#112233", "home_airports": []}, headers=owner).json()
    assert client.put(f"/v1/trips/{trip['id']}/travelers", json={"person_ids": [p["id"]]}, headers=owner).status_code == 200
    inv = _invite(client, owner, trip)
    r = client.post(f"/v1/invites/{_token(inv)}/accept", json={"person_id": p["id"]}, headers=joiner)
    assert r.status_code == 200
    assert str(system_conn.execute("SELECT linked_user_id FROM people WHERE id = %s", (p["id"],)).fetchone()[0]) == ju["id"]


def test_already_member_is_409_with_the_trip_id_and_does_not_consume(client, system_conn):
    owner, ou = _user(client)
    _plus(system_conn, ou)
    joiner, _ = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, joiner)
    inv = _invite(client, owner, trip)
    r = client.post(f"/v1/invites/{_token(inv)}/accept", json={}, headers=joiner)
    assert r.status_code == 409 and r.json()["code"] == "already_member" and r.json()["trip_id"] == trip["id"]
    assert client.post(f"/v1/invites/{_token(inv)}/accept", json={}, headers=owner).status_code == 409
    assert system_conn.execute("SELECT use_count FROM trip_invites WHERE id = %s", (inv["id"],)).fetchone()[0] == 0


def test_link_invite_counts_uses_up_to_max_uses(client, system_conn):
    owner, ou = _user(client)
    _plus(system_conn, ou)
    trip = _trip(client, owner)
    inv = _invite(client, owner, trip, max_uses=2)
    assert inv["uses_left"] == 2
    users = [_user(client)[0] for _ in range(3)]
    codes = [client.post(f"/v1/invites/{_token(inv)}/accept", json={}, headers=u).status_code for u in users]
    assert codes == [200, 200, 410]
    listed = client.get(f"/v1/trips/{trip['id']}/invites", headers=owner).json()
    assert listed[0]["uses_left"] == 0 and listed[0]["status"] == "used"


def test_revoke_and_unknown_invite_ids(client):
    owner, _ = _user(client)
    stranger, _ = _user(client)
    trip = _trip(client, owner)
    inv = _invite(client, owner, trip)
    assert client.delete(f"/v1/trips/{trip['id']}/invites/{inv['id']}", headers=stranger).status_code == 404
    assert client.delete(f"/v1/trips/{trip['id']}/invites/{uuid.uuid4()}", headers=owner).status_code == 404
    assert client.delete(f"/v1/trips/{trip['id']}/invites/{inv['id']}", headers=owner).status_code == 204
    assert client.get(f"/v1/trips/{trip['id']}/invites", headers=owner).json()[0]["status"] == "revoked"


def test_pending_cap_is_20(client, system_conn):
    owner, ou = _user(client)
    _plus(system_conn, ou)
    trip = _trip(client, owner)
    for _i in range(20):  # straight into the table: a plan's slots stop the API at 6, this is the cap behind them
        system_conn.execute("INSERT INTO trip_invites (trip_id, invited_by, token_hash) VALUES (%s, %s, %s)", (trip["id"], ou["id"], uuid.uuid4().bytes))
    r = client.post(f"/v1/trips/{trip['id']}/invites", json={"role": "editor"}, headers=owner)
    assert r.status_code == 429 and r.json()["code"] == "rate_limited"


# --- members ----------------------------------------------------------------------------------


def test_list_members_and_role_change(client):
    owner, ou = _user(client)
    joiner, ju = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, joiner, "viewer")
    ms = client.get(f"/v1/trips/{trip['id']}/members", headers=joiner).json()
    assert {m["user_id"]: m["role"] for m in ms} == {ou["id"]: "owner", ju["id"]: "viewer"}
    assert set(ms[0]) == {"user_id", "display_name", "role", "person_id", "joined_at", "invited_by"}
    url = f"/v1/trips/{trip['id']}/members/{ju['id']}"
    r = client.patch(url, json={"role": "editor"}, headers=owner)
    assert r.status_code == 200 and r.json()["role"] == "editor" and r.json()["user_id"] == ju["id"]
    assert client.patch(url, json={"role": "owner"}, headers=owner).status_code == 422
    assert client.patch(url, json={"role": "viewer"}, headers=joiner).status_code == 403
    assert client.patch(f"/v1/trips/{trip['id']}/members/{ou['id']}", json={"role": "editor"}, headers=owner).status_code == 409
    assert client.patch(f"/v1/trips/{trip['id']}/members/{uuid.uuid4()}", json={"role": "editor"}, headers=owner).status_code == 404


def test_limited_trip_cannot_raise_a_role(client, system_conn):
    owner, ou = _user(client)
    a, au = _user(client)
    b, _bu = _user(client)
    trip = _trip(client, owner)
    _plus(system_conn, ou)
    _join(client, owner, trip, a, "viewer")
    _join(client, owner, trip, b, "viewer")
    system_conn.execute("UPDATE entitlements SET tier_code = 'free' WHERE user_id = %s", (ou["id"],))  # the plan lapses: two collaborators on a Free trip (limit 1)
    r = client.patch(f"/v1/trips/{trip['id']}/members/{au['id']}", json={"role": "editor"}, headers=owner)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached" and r.json()["paywall"]["reason"] == "sharing"
    system_conn.execute("UPDATE trip_members SET role = 'editor' WHERE trip_id = %s AND user_id = %s", (trip["id"], au["id"]))
    assert client.patch(f"/v1/trips/{trip['id']}/members/{au['id']}", json={"role": "viewer"}, headers=owner).status_code == 200


def test_owner_removes_a_member_and_detaches_the_traveler(client, system_conn):
    owner, _ = _user(client)
    joiner, ju = _user(client)
    trip = _trip(client, owner)
    p = client.post("/v1/people", json={"name": "Jo", "color": "#112233", "home_airports": []}, headers=owner).json()
    client.put(f"/v1/trips/{trip['id']}/travelers", json={"person_ids": [p["id"]]}, headers=owner)
    inv = _invite(client, owner, trip)
    client.post(f"/v1/invites/{_token(inv)}/accept", json={"person_id": p["id"]}, headers=joiner)
    assert client.delete(f"/v1/trips/{trip['id']}/members/{ju['id']}", headers=joiner).status_code == 403
    assert client.delete(f"/v1/trips/{trip['id']}/members/{ju['id']}", headers=owner).status_code == 204
    assert client.get(f"/v1/trips/{trip['id']}", headers=joiner).status_code == 404
    assert system_conn.execute("SELECT linked_user_id FROM people WHERE id = %s", (p["id"],)).fetchone()[0] is None
    assert system_conn.execute("SELECT count(*) FROM people WHERE id = %s", (p["id"],)).fetchone()[0] == 1
    assert client.delete(f"/v1/trips/{trip['id']}/members/{ju['id']}", headers=owner).status_code == 404


def test_owner_cannot_be_removed_without_transfer(client):
    owner, ou = _user(client)
    trip = _trip(client, owner)
    r = client.delete(f"/v1/trips/{trip['id']}/members/{ou['id']}", headers=owner)
    assert r.status_code == 409 and r.json()["code"] == "state_conflict"


def test_leave_keeps_history_and_the_owner_must_transfer_first(client):
    owner, ou = _user(client)
    joiner, _ = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, joiner)
    r = client.post(f"/v1/trips/{trip['id']}/leave", headers=owner)
    assert r.status_code == 409 and r.json()["code"] == "state_conflict"
    assert client.post(f"/v1/trips/{trip['id']}/leave", headers=joiner).status_code == 204
    assert client.get(f"/v1/trips/{trip['id']}", headers=joiner).status_code == 404
    assert client.post(f"/v1/trips/{trip['id']}/leave", headers=joiner).status_code == 404
    ms = client.get(f"/v1/trips/{trip['id']}/members", headers=owner).json()
    assert [m["user_id"] for m in ms] == [ou["id"]]


def test_transfer_swaps_owner_and_editor(client, system_conn):
    owner, ou = _user(client)
    joiner, ju = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, joiner, "viewer")
    url = f"/v1/trips/{trip['id']}/transfer"
    assert client.post(url, json={"new_owner_id": ju["id"]}, headers=joiner).status_code == 403
    assert client.post(url, json={"new_owner_id": str(uuid.uuid4())}, headers=owner).status_code == 422
    assert client.post(url, json={"new_owner_id": ou["id"]}, headers=owner).status_code == 422
    r = client.post(url, json={"new_owner_id": ju["id"]}, headers=owner)
    assert r.status_code == 200 and r.json()["my_role"] == "editor"
    roles = {str(u): role for u, role in system_conn.execute("SELECT user_id, role FROM trip_members WHERE trip_id = %s", (trip["id"],)).fetchall()}
    assert roles == {ou["id"]: "editor", ju["id"]: "owner"}
    assert client.post(f"/v1/trips/{trip['id']}/leave", headers=owner).status_code == 204  # the old owner may leave now


def test_accept_with_a_person_not_on_the_trip_joins_and_links_nothing(client, system_conn):
    owner, _ = _user(client)
    joiner, _ = _user(client)
    trip = _trip(client, owner)
    p = client.post("/v1/people", json={"name": "Jo", "color": "#112233", "home_airports": []}, headers=owner).json()  # not on the trip
    inv = _invite(client, owner, trip)
    r = client.post(f"/v1/invites/{_token(inv)}/accept", json={"person_id": p["id"]}, headers=joiner)
    assert r.status_code == 200 and r.json()["id"] == trip["id"]
    assert system_conn.execute("SELECT linked_user_id FROM people WHERE id = %s", (p["id"],)).fetchone()[0] is None


def test_capabilities_after_transfer_to_a_free_member(client):
    owner, _ = _user(client)
    joiner, ju = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, joiner, "editor")
    r = client.post(f"/v1/trips/{trip['id']}/transfer", json={"new_owner_id": ju["id"]}, headers=owner)
    assert r.status_code == 200
    # shortcut: Trip has no capabilities field yet (it arrives with the screens), so the new owner's powers are checked through the routes.
    assert r.json()["my_role"] == "editor"
    assert client.get(f"/v1/trips/{trip['id']}/invites", headers=joiner).status_code == 200  # a Free new owner holds owner powers
    assert client.get(f"/v1/trips/{trip['id']}/invites", headers=owner).status_code == 403  # the old owner is an editor now
