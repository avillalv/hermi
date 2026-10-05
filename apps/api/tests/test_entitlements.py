# ruff: noqa: E501  (long SQL strings)
"""WF-023.1: entitlement resolver, trip_capabilities() and the third-trip 402 (03 section 7.1, 04 sections 2.2 and 2.3)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi import db
from hermi.config import Settings
from hermi.errors import NotFound
from hermi.main import create_app
from hermi.modules.billing import service as billing
from hermi.modules.trips import repo
from hermi.modules.trips.service import trip_capabilities
from hermi.security.jwt import mint_dev_token


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
    return h, uuid.UUID(r.json()["id"])


def _trip(client, h, name="T"):
    r = client.post("/v1/trips", json={"name": name}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _tier(system_conn, uid, tier, valid_until="NULL"):
    system_conn.execute(f"UPDATE entitlements SET tier_code = %s, valid_until = {valid_until} WHERE user_id = %s", (tier, uid))


def _pass(system_conn, trip_id, expires="now() + interval '90 days'", starts="now() - interval '1 day'", status="active"):
    system_conn.execute(
        f"INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', {starts}, {expires}, %s)", (trip_id, status)
    )


def _caps(client, uid, trip_id):
    with db.request_transaction(client.app.state.engine, uid) as s:
        found = repo.get_trip_with_member(s, uuid.UUID(str(trip_id)), uid)
        assert found, "caller must be a member"
        return trip_capabilities(s, found[0])


def _member(system_conn, trip_id, uid, role="editor"):
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (trip_id, uid, role))


# (owner tier, pass?) -> effective tier, source, collaborators, live routes
TIER_TABLE = [
    ("free", False, "free", "owner_tier", 1, 0),
    ("plus", False, "plus", "owner_tier", 6, 3),
    ("free", True, "trip_pass", "trip_pass", 6, 2),
    ("plus", True, "trip_pass", "trip_pass", 6, 3),  # the best of both, per limit
]


@pytest.mark.parametrize(("tier", "has_pass", "eff", "source", "collab", "live"), TIER_TABLE)
def test_capabilities_are_the_best_of_owner_tier_and_pass(client, system_conn, tier, has_pass, eff, source, collab, live):
    h, uid = _user(client)
    t = _trip(client, h)
    _tier(system_conn, uid, tier)
    if has_pass:
        _pass(system_conn, t["id"])
    c = _caps(client, uid, t["id"])
    assert (c.effective_tier, c.source, c.max_collaborators, c.live_routes_max) == (eff, source, collab, live)
    assert c.can_invite is True and c.collaborators_used == 0 and c.limited is False
    assert (c.pass_expires_at is not None) is has_pass
    assert c.live_checks_left == (60 if has_pass else None)


def test_expired_pass_and_lapsed_plus_fall_back_to_free(client, system_conn):
    h, uid = _user(client)
    t1, t2 = _trip(client, h), _trip(client, h)
    _pass(system_conn, t1["id"], starts="now() - interval '100 days'", expires="now() - interval '10 days'", status="expired")
    assert _caps(client, uid, t1["id"]).effective_tier == "free"
    _tier(system_conn, uid, "plus", valid_until="now() - interval '1 day'")
    assert _caps(client, uid, t2["id"]).max_collaborators == 1
    _tier(system_conn, uid, "plus", valid_until="now() + interval '1 day'")
    assert _caps(client, uid, t2["id"]).max_collaborators == 6


def test_invitee_gets_the_owner_tier_on_that_trip_only(client, system_conn):
    ho, owner = _user(client)
    hi, invitee = _user(client)
    hf, _free_owner = _user(client)
    _tier(system_conn, owner, "plus")
    plus_trip, free_trip = _trip(client, ho), _trip(client, hf)
    _member(system_conn, plus_trip["id"], invitee)
    assert _caps(client, invitee, plus_trip["id"]).max_collaborators == 6  # the owner's Plus, on this trip
    own = _trip(client, hi)
    assert _caps(client, invitee, own["id"]).max_collaborators == 1  # their own trips keep their own tier
    _tier(system_conn, invitee, "plus")
    _member(system_conn, free_trip["id"], invitee)
    assert _caps(client, invitee, free_trip["id"]).effective_tier == "free"  # their Plus does not follow them onto it


def test_a_stranger_cannot_resolve_another_trips_limits(client):
    ho, _ = _user(client)
    _, stranger = _user(client)
    t = _trip(client, ho)
    with db.request_transaction(client.app.state.engine, stranger) as s:
        assert billing.trip_limits(s, uuid.UUID(t["id"])) == ([], {})
        with pytest.raises(NotFound):
            trip_capabilities(s, type("T", (), {"id": uuid.UUID(t["id"]), "ai_enabled": True})())


def test_collaborators_count_members_and_pending_invites(client, system_conn):
    ho, owner = _user(client)
    _, ed = _user(client)
    t = _trip(client, ho)
    _member(system_conn, t["id"], ed)
    assert _caps(client, owner, t["id"]).can_invite is False  # Free allows 1 collaborator
    _tier(system_conn, owner, "plus")
    c = _caps(client, owner, t["id"])
    assert (c.collaborators_used, c.can_invite) == (1, True)
    system_conn.execute("INSERT INTO trip_invites (trip_id, invited_by, token_hash) VALUES (%s, %s, %s)", (t["id"], owner, uuid.uuid4().bytes))
    assert _caps(client, owner, t["id"]).collaborators_used == 2


def test_limits_come_from_the_plans_seed_not_from_code(client, system_conn):
    h, uid = _user(client)
    t = _trip(client, h)
    system_conn.execute("UPDATE plans SET limits = jsonb_set(limits, '{collaborators}', '3') WHERE code = 'free'")
    try:
        assert _caps(client, uid, t["id"]).max_collaborators == 3
    finally:
        system_conn.execute("UPDATE plans SET limits = jsonb_set(limits, '{collaborators}', '1') WHERE code = 'free'")


def test_third_active_trip_on_free_is_402_with_the_third_trip_hint(client):
    h, _ = _user(client)
    _trip(client, h)
    _trip(client, h)
    r = client.post("/v1/trips", json={"name": "Third"}, headers=h)
    assert r.status_code == 402
    body = r.json()
    assert body["code"] == "limit_reached"
    assert body["paywall"]["trigger"] == "third_trip" and body["paywall"]["reason"] == "trip_limit"
    assert body["paywall"]["offer_url"] and body["paywall"]["free_path"]


def test_archived_trips_do_not_count(client):
    h, _ = _user(client)
    a = _trip(client, h)
    _trip(client, h)
    r = client.patch(f"/v1/trips/{a['id']}", json={"status": "archived"}, headers={**h, "If-Match": f'"{a["version"]}"'})
    assert r.status_code == 200, r.text
    assert client.post("/v1/trips", json={"name": "Third"}, headers=h).status_code == 201


def test_plus_has_the_higher_limit_and_a_pass_frees_one_slot(client, system_conn):
    h, uid = _user(client)
    t1 = _trip(client, h)
    _trip(client, h)
    assert client.post("/v1/trips", json={"name": "x"}, headers=h).status_code == 402
    _pass(system_conn, t1["id"])  # the passed trip stops counting
    assert client.post("/v1/trips", json={"name": "x"}, headers=h).status_code == 201
    assert client.post("/v1/trips", json={"name": "y"}, headers=h).status_code == 402
    _tier(system_conn, uid, "plus")
    assert client.post("/v1/trips", json={"name": "y"}, headers=h).status_code == 201


def test_joined_trips_never_count_toward_the_limit(client, system_conn):
    ho, _ = _user(client)
    hj, joiner = _user(client)
    for name in ("a", "b"):
        _member(system_conn, _trip(client, ho, name)["id"], joiner)
    assert client.post("/v1/trips", json={"name": "mine"}, headers=hj).status_code == 201


def test_live_routes_used_counts_live_routes(client, system_conn):
    h, uid = _user(client)
    t = _trip(client, h)
    for live in (True, False):
        system_conn.execute(
            "INSERT INTO flight_routes (trip_id, origin_codes, destination_codes, depart_from, depart_to, return_from, return_to, is_live) "
            "VALUES (%s, '{LIS}', '{OPO}', '2027-03-01', '2027-03-10', '2027-03-15', '2027-03-20', %s)",
            (t["id"], live),
        )
    assert _caps(client, uid, t["id"]).live_routes_used == 1


def test_limited_when_members_exceed_the_collaborator_limit(client, system_conn):
    ho, owner = _user(client)
    t = _trip(client, ho)
    for _ in range(2):
        _member(system_conn, t["id"], _user(client)[1])  # Free allows 1
    c = _caps(client, owner, t["id"])
    assert c.limited is True and c.can_invite is False


def test_paid_tier_at_its_ceiling_gets_a_plain_402_without_an_upsell(client, system_conn):
    h, uid = _user(client)
    _tier(system_conn, uid, "plus")
    system_conn.execute("UPDATE plans SET limits = jsonb_set(limits, '{active_trips}', '3') WHERE code = 'plus'")
    try:
        for _ in range(3):
            _trip(client, h)
        r = client.post("/v1/trips", json={"name": "x"}, headers=h)
    finally:
        system_conn.execute("UPDATE plans SET limits = jsonb_set(limits, '{active_trips}', '25') WHERE code = 'plus'")
    assert r.status_code == 402 and r.json()["code"] == "limit_reached" and "paywall" not in r.json()
