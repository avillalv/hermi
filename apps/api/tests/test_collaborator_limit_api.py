# ruff: noqa: E501  (long SQL strings)
"""WF-026: Free owners invite 1 collaborator, Plus and Trip Pass owners up to 6, joining is always free, lapse demotes extras."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token


@pytest.fixture
def client(db_urls):
    s = Settings(_env_file=None, environment="ci", auth_mode="dev", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10, public_web_url="https://app.hermi.test")
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h)
    assert r.status_code == 201
    return h, r.json()["id"]


def _trip(client, h):
    return client.post("/v1/trips", json={"name": "Lisbon"}, headers=h).json()


def _invite(client, h, trip, **body):
    return client.post(f"/v1/trips/{trip['id']}/invites", json={"role": "editor", **body}, headers=h)


def _accept(client, inv, h):
    return client.post(f"/v1/invites/{inv.json()['url'].rsplit('/', 1)[1]}/accept", json={}, headers=h)


def _tier(system_conn, uid, tier):
    system_conn.execute("UPDATE entitlements SET tier_code = %s, valid_until = NULL WHERE user_id = %s", (tier, uid))


def test_free_owner_invites_one_and_the_second_is_a_402_with_the_invite_paywall(client):
    owner, _ = _user(client)
    trip = _trip(client, owner)
    assert _invite(client, owner, trip, email="a@example.com").status_code == 201
    r = _invite(client, owner, trip, role="viewer")
    assert r.status_code == 402
    body = r.json()
    assert body["code"] == "limit_reached"
    assert body["paywall"]["trigger"] == "invite" and body["paywall"]["reason"] == "sharing"
    assert body["paywall"]["offer_url"] == "/v1/paywall/offer?reason=sharing" and body["paywall"]["free_path"]
    assert "Plus" in body["detail"] and "read-only link" in body["detail"]


def test_pending_invites_count_and_revoking_frees_the_slot(client):
    owner, _ = _user(client)
    trip = _trip(client, owner)
    first = _invite(client, owner, trip)
    assert _invite(client, owner, trip).status_code == 402
    assert client.delete(f"/v1/trips/{trip['id']}/invites/{first.json()['id']}", headers=owner).status_code == 204
    assert _invite(client, owner, trip).status_code == 201


def test_an_accepted_collaborator_counts_and_a_link_cannot_admit_more_than_the_slots(client):
    owner, _ = _user(client)
    joiner, _ = _user(client)
    other, _ = _user(client)
    trip = _trip(client, owner)
    link = _invite(client, owner, trip, max_uses=6)
    assert link.status_code == 201 and link.json()["uses_left"] == 1  # clamped to the free slot
    assert _accept(client, link, joiner).status_code == 200
    assert _invite(client, owner, trip).status_code == 402
    assert _accept(client, link, other).status_code == 410


def test_plus_and_trip_pass_owners_invite_up_to_six(client, system_conn):
    plus, plus_id = _user(client)
    _tier(system_conn, plus_id, "plus")
    t1 = _trip(client, plus)
    for _ in range(6):
        assert _invite(client, plus, t1).status_code == 201
    r = _invite(client, plus, t1)
    assert r.status_code == 402 and "paywall" not in r.json()  # the Plus ceiling is 6: nothing to buy, so no paywall hint

    free, _ = _user(client)
    t2 = _trip(client, free)
    system_conn.execute("INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', now() - interval '1 day', now() + interval '30 days', 'active')", (t2["id"],))
    for _ in range(6):
        assert _invite(client, free, t2).status_code == 201


def test_the_invitee_needs_no_plan_even_with_free_trips_of_their_own(client):
    owner, _ = _user(client)
    joiner, _ = _user(client)
    for _ in range(2):
        _trip(client, joiner)  # the invitee is at their own Free trip limit
    trip = _trip(client, owner)
    assert _accept(client, _invite(client, owner, trip), joiner).status_code == 200


def test_lapse_demotes_extras_to_viewers_keeps_everyone_and_flags_the_trip(client, system_conn):
    owner, oid = _user(client)
    _tier(system_conn, oid, "plus")
    trip = _trip(client, owner)
    people = [_user(client) for _ in range(3)]
    for h, _ in people:
        assert _accept(client, _invite(client, owner, trip), h).status_code == 200
    assert client.get(f"/v1/trips/{trip['id']}", headers=owner).json()["limited"] is False
    _tier(system_conn, oid, "free")  # the plan lapses
    t = client.get(f"/v1/trips/{trip['id']}", headers=owner).json()
    assert t["limited"] is True
    members = {m["user_id"]: m["role"] for m in client.get(f"/v1/trips/{trip['id']}/members", headers=owner).json()}
    assert len(members) == 4 and members[oid] == "owner"
    roles = [members[uid] for _, uid in people]  # joined order: the first keeps their role
    assert roles == ["editor", "viewer", "viewer"]
    assert [i["limited"] for i in client.get("/v1/trips", headers=owner).json()["items"]] == [True]
    # a collaborator reads the same flag but nothing is lost for them
    assert client.get(f"/v1/trips/{trip['id']}", headers=people[2][0]).json()["my_role"] == "viewer"


def test_back_under_the_limit_clears_the_flag(client, system_conn):
    owner, oid = _user(client)
    _tier(system_conn, oid, "plus")
    trip = _trip(client, owner)
    people = [_user(client) for _ in range(2)]
    for h, _ in people:
        assert _accept(client, _invite(client, owner, trip), h).status_code == 200
    _tier(system_conn, oid, "free")
    assert client.get(f"/v1/trips/{trip['id']}", headers=owner).json()["limited"] is True
    assert client.delete(f"/v1/trips/{trip['id']}/members/{people[1][1]}", headers=owner).status_code == 204
    assert client.get(f"/v1/trips/{trip['id']}", headers=owner).json()["limited"] is False


def test_an_expired_trip_pass_demotes_extras(client, system_conn):
    owner, _ = _user(client)
    trip = _trip(client, owner)
    system_conn.execute("INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', now() - interval '1 day', now() + interval '30 days', 'active')", (trip["id"],))
    people = [_user(client) for _ in range(2)]
    for h, _ in people:
        assert _accept(client, _invite(client, owner, trip), h).status_code == 200
    system_conn.execute("UPDATE trip_passes SET starts_at = now() - interval '40 days', expires_at = now() - interval '1 day' WHERE trip_id = %s", (trip["id"],))
    assert client.get(f"/v1/trips/{trip['id']}", headers=owner).json()["limited"] is True
    roles = {m["user_id"]: m["role"] for m in client.get(f"/v1/trips/{trip['id']}/members", headers=owner).json()}
    assert [roles[uid] for _, uid in people] == ["editor", "viewer"]


def test_a_multi_use_link_counts_every_remaining_use(client, system_conn):
    owner, oid = _user(client)
    _tier(system_conn, oid, "plus")
    trip = _trip(client, owner)
    assert _invite(client, owner, trip, max_uses=6).json()["uses_left"] == 6
    assert _invite(client, owner, trip).status_code == 402  # six uses are six pending collaborators


def test_a_lapsed_owners_leftover_link_cannot_admit_beyond_the_limit(client, system_conn):
    owner, oid = _user(client)
    _tier(system_conn, oid, "plus")
    trip = _trip(client, owner)
    link = _invite(client, owner, trip, max_uses=3)
    first, second = _user(client)[0], _user(client)[0]
    assert _accept(client, link, first).status_code == 200
    _tier(system_conn, oid, "free")  # one collaborator is the Free limit
    r = _accept(client, link, second)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"
    members = client.get(f"/v1/trips/{trip['id']}/members", headers=owner).json()
    assert len(members) == 2
    assert client.get(f"/v1/trips/{trip['id']}/invites", headers=owner).json()[0]["uses_left"] == 2  # the redeem rolled back


def test_two_concurrent_invites_on_a_free_trip_make_exactly_one(client):
    from concurrent.futures import ThreadPoolExecutor

    owner, _ = _user(client)
    trip = _trip(client, owner)
    with ThreadPoolExecutor(2) as ex:
        codes = sorted(f.result().status_code for f in [ex.submit(_invite, client, owner, trip) for _ in range(2)])
    assert codes == [201, 402]


def test_the_slot_lock_does_not_deadlock_with_concurrent_joins(client, db_urls):
    """A join's trip_members insert holds FOR KEY SHARE on the trip. The slot lock must not conflict with it (FOR UPDATE would)."""
    import threading

    import psycopg

    from hermi import db
    from hermi.modules.collaboration.service import LOCK_TRIP

    owner, _ = _user(client)
    trip = _trip(client, owner)
    u1, u2 = _user(client)[1], _user(client)[1]
    sql = LOCK_TRIP.replace(":t", "%(t)s")
    errors: list[Exception] = []
    a = psycopg.connect(db.psycopg_url(db_urls["system"]))
    b = psycopg.connect(db.psycopg_url(db_urls["system"]))
    try:
        for c, u in ((a, u1), (b, u2)):
            c.execute("SET lock_timeout = '5s'")
            c.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'editor')", (trip["id"], u))

        def lock(c):
            try:
                c.execute(sql, {"t": trip["id"]})  # the second locker waits for the first to commit, which is the point
                c.commit()
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        t = threading.Thread(target=lock, args=(a,))
        t.start()
        lock(b)
        t.join(10)
        assert errors == [], errors
    finally:
        a.rollback()
        b.rollback()
        a.close()
        b.close()


def test_concurrent_viewer_joins_on_a_lapsed_trip_are_all_refused(client, system_conn):
    """Viewers cannot take a row lock on the trip (RLS), so the slot lock must still serialize them."""
    from concurrent.futures import ThreadPoolExecutor

    owner, oid = _user(client)
    _tier(system_conn, oid, "plus")
    trip = _trip(client, owner)
    link = _invite(client, owner, trip, role="viewer", max_uses=3)
    first, a, b = _user(client)[0], _user(client)[0], _user(client)[0]
    assert _accept(client, link, first).status_code == 200
    _tier(system_conn, oid, "free")
    with ThreadPoolExecutor(2) as ex:
        codes = [f.result().status_code for f in [ex.submit(_accept, client, link, h) for h in (a, b)]]
    assert codes == [402, 402]
    assert len(client.get(f"/v1/trips/{trip['id']}/members", headers=owner).json()) == 2
