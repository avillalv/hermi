# ruff: noqa: E501  (long SQL strings and payloads)
"""WF-062.1: POST /v1/me/claim (04 section 5.1, F-ACC-3): one guest trip moves into the caller's account exactly once."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from tests.test_auth_provisioning import BODY, _auth, _settings

from hermi.main import create_app


@pytest.fixture
def client(db_urls):
    s = _settings(db_urls)
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _trip_json(**kw):
    return {
        "name": "Lisbon long weekend",
        "start_date": "2027-05-01",
        "end_date": "2027-05-03",
        "notes": "From the phone",
        "destinations": [
            {
                "name": "Lisbon",
                "country": "Portugal",
                "country_code": "PT",
                "lat": 38.72,
                "lon": -9.14,
            }
        ],
        "days": [{"day": "2027-05-01", "title": "Arrive"}],
        "places": [
            {
                "ref": "p1",
                "name": "Time Out Market",
                "category": "food",
                "lat": 38.707,
                "lon": -9.146,
            }
        ],
        "items": [
            {
                "title": "Tram 28",
                "day": "2027-05-01",
                "start_time": "10:00",
                "end_time": "11:00",
                "category": "sights",
            },
            {"title": "Lunch", "day": "2027-05-02", "category": "food", "place_ref": "p1"},
            {"title": "Ideas for later", "category": "other"},
        ],
        "people": [{"name": "Sam"}, {"name": "Alex"}],
        **kw,
    }


def _signed_in(client):
    h = _auth(client)
    assert client.post("/v1/me/bootstrap", json=BODY, headers=h).status_code == 201
    return h


def _claim(client, h, trip=None, claim_id=None, **kw):
    return client.post(
        "/v1/me/claim",
        json={"trip": trip or _trip_json(), "claim_id": claim_id or str(uuid.uuid4()), **kw},
        headers=h,
    )


def _count(system_conn, sql, *args):
    return system_conn.execute(sql, args).fetchone()[0]


def test_claim_imports_the_trip_days_items_places_and_people(client, system_conn):
    h = _signed_in(client)
    r = _claim(client, h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (
        body["people_imported"] == 2 and body["items_imported"] == 3 and body["archived"] is False
    )
    assert "Idempotent-Replay" not in r.headers
    tid = body["trip_id"]
    t = system_conn.execute(
        "SELECT name, status::text, home_currency::text FROM trips WHERE id = %s", (tid,)
    ).fetchone()
    assert t[0] == "Lisbon long weekend" and t[1] == "planning"
    assert (
        _count(system_conn, "SELECT count(*) FROM trip_destinations WHERE trip_id = %s", tid) == 1
    )
    assert (
        _count(
            system_conn,
            "SELECT count(*) FROM itinerary_items WHERE trip_id = %s AND source = 'manual'",
            tid,
        )
        == 3
    )
    assert _count(system_conn, "SELECT count(*) FROM saved_places WHERE trip_id = %s", tid) == 1
    assert (
        _count(system_conn, "SELECT count(*) FROM itinerary_days WHERE trip_id = %s", tid) == 2
    )  # the listed day and the lunch day
    lunch = system_conn.execute(
        "SELECT saved_place_id FROM itinerary_items WHERE trip_id = %s AND title = 'Lunch'", (tid,)
    ).fetchone()
    assert lunch[0] is not None
    # the trip belongs to the caller, with the caller as owner member and the extra people unlinked
    owner = system_conn.execute("SELECT owner_user_id FROM trips WHERE id = %s", (tid,)).fetchone()[
        0
    ]
    assert (
        system_conn.execute(
            "SELECT role::text FROM trip_members WHERE trip_id = %s AND user_id = %s", (tid, owner)
        ).fetchone()[0]
        == "owner"
    )
    assert (
        _count(
            system_conn,
            "SELECT count(*) FROM people WHERE owner_user_id = %s AND linked_user_id IS NULL",
            owner,
        )
        == 2
    )


def test_the_same_claim_id_returns_the_first_result_and_imports_nothing_twice(client, system_conn):
    h = _signed_in(client)
    cid = str(uuid.uuid4())
    first = _claim(client, h, claim_id=cid)
    second = _claim(client, h, claim_id=cid)
    assert second.status_code == 200
    assert second.json() == first.json()
    assert second.headers["Idempotent-Replay"] == "true"
    owner = system_conn.execute(
        "SELECT owner_user_id FROM trips WHERE id = %s", (first.json()["trip_id"],)
    ).fetchone()[0]
    assert _count(system_conn, "SELECT count(*) FROM trips WHERE owner_user_id = %s", owner) == 1
    assert (
        _count(
            system_conn,
            "SELECT count(*) FROM people WHERE owner_user_id = %s AND NOT is_self",
            owner,
        )
        == 2
    )


def test_a_double_submit_in_parallel_imports_once(client, system_conn):
    h = _signed_in(client)
    cid = str(uuid.uuid4())
    with ThreadPoolExecutor(4) as pool:
        rs = list(pool.map(lambda _: _claim(client, h, claim_id=cid), range(4)))
    assert {r.status_code for r in rs} == {200}
    assert len({r.json()["trip_id"] for r in rs}) == 1
    owner = system_conn.execute(
        "SELECT owner_user_id FROM trips WHERE id = %s", (rs[0].json()["trip_id"],)
    ).fetchone()[0]
    assert _count(system_conn, "SELECT count(*) FROM trips WHERE owner_user_id = %s", owner) == 1


def test_a_different_claim_id_is_a_new_claim(client, system_conn):
    h = _signed_in(client)
    a = _claim(client, h, merge=True)
    b = _claim(client, h, merge=True)
    assert a.json()["trip_id"] != b.json()["trip_id"]


def test_an_account_that_already_has_trips_needs_a_merge_choice(client, system_conn):
    h = _signed_in(client)
    assert client.post("/v1/trips", json={"name": "Existing"}, headers=h).status_code == 201
    r = _claim(client, h)
    assert r.status_code == 409 and r.json()["code"] == "state_conflict"
    assert r.json()["counts"]["trips"] == 1
    assert "1 trip" in r.json()["detail"]
    # nothing was written, and the refusal is not remembered: the same claim id can be retried with a choice
    cid = str(uuid.uuid4())
    assert _claim(client, h, claim_id=cid).status_code == 409
    again = _claim(client, h, claim_id=cid, merge=True)
    assert again.status_code == 200 and again.json()["trip_id"] is not None


def test_keep_separate_imports_nothing_and_is_remembered(client, system_conn):
    h = _signed_in(client)
    assert client.post("/v1/trips", json={"name": "Existing"}, headers=h).status_code == 201
    cid = str(uuid.uuid4())
    r = _claim(client, h, claim_id=cid, merge=False)
    assert r.status_code == 200
    assert r.json() == {
        "trip_id": None,
        "people_imported": 0,
        "items_imported": 0,
        "archived": False,
    }
    uid = client.get("/v1/me", headers=h).json()["id"]
    assert (
        _count(
            system_conn,
            "SELECT count(*) FROM trips WHERE owner_user_id = %s AND name = 'Lisbon long weekend'",
            uid,
        )
        == 0
    )
    assert (
        _claim(client, h, claim_id=cid, merge=True).json()["trip_id"] is None
    )  # the first result stands


def test_a_claim_over_the_active_trip_limit_is_archived_not_dropped(client, system_conn):
    h = _signed_in(client)
    for n in ("A", "B"):  # Free allows 2 active trips
        assert client.post("/v1/trips", json={"name": n}, headers=h).status_code == 201
    r = _claim(client, h, merge=True)
    assert r.status_code == 200 and r.json()["archived"] is True
    row = system_conn.execute(
        "SELECT status::text, archived_at IS NOT NULL FROM trips WHERE id = %s",
        (r.json()["trip_id"],),
    ).fetchone()
    assert row == ("archived", True)
    assert r.json()["items_imported"] == 3


def test_counts_come_from_the_server_not_the_payload(client, system_conn):
    h = _signed_in(client)
    r = _claim(
        client,
        h,
        trip=_trip_json(items_imported=999, people_imported=999, owner_user_id=str(uuid.uuid4())),
    )
    assert r.status_code == 200 and (r.json()["items_imported"], r.json()["people_imported"]) == (
        3,
        2,
    )
    owner = system_conn.execute(
        "SELECT owner_user_id FROM trips WHERE id = %s", (r.json()["trip_id"],)
    ).fetchone()[0]
    assert _count(system_conn, "SELECT count(*) FROM users WHERE id = %s", owner) == 1
    assert owner != uuid.UUID(int=0)


def test_guest_caps_are_validation_errors(client):
    h = _signed_in(client)
    many = [{"title": f"Item {i}"} for i in range(201)]
    r = _claim(client, h, trip=_trip_json(items=many))
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
    r = _claim(client, h, trip=_trip_json(start_date="2027-05-09", end_date="2027-05-01"))
    assert r.status_code == 422
    r = _claim(client, h, trip=_trip_json(items=[{"title": "x", "place_ref": "missing"}]))
    assert r.status_code == 422


def test_claim_needs_a_signed_in_user_and_a_guest_has_no_token(client, system_conn):
    before = _count(system_conn, "SELECT count(*) FROM trips WHERE name = 'Lisbon long weekend'")
    r = client.post("/v1/me/claim", json={"trip": _trip_json(), "claim_id": str(uuid.uuid4())})
    assert r.status_code == 401
    assert (
        _count(system_conn, "SELECT count(*) FROM trips WHERE name = 'Lisbon long weekend'")
        == before
    )
    # a token that has no users row yet is not a claim either: bootstrap comes first
    r = client.post(
        "/v1/me/claim",
        json={"trip": _trip_json(), "claim_id": str(uuid.uuid4())},
        headers=_auth(client),
    )
    assert r.status_code in (401, 403, 404)


def test_claim_id_is_per_user(client, system_conn):
    cid = str(uuid.uuid4())
    a, b = _signed_in(client), _signed_in(client)
    ra, rb = _claim(client, a, claim_id=cid), _claim(client, b, claim_id=cid)
    assert ra.status_code == rb.status_code == 200
    assert ra.json()["trip_id"] != rb.json()["trip_id"]
    assert "Idempotent-Replay" not in rb.headers


def _grant(system_conn, uid):
    r = system_conn.execute(
        "SELECT remaining FROM credit_grants WHERE user_id = %s AND kind = 'monthly' "
        "AND period_key = to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM')",
        (uid,),
    ).fetchone()
    return None if r is None else r[0]


def _spend_as_guest(client, n):
    from tests.test_guest_ai_api import _attest, _call

    key_id = _attest(client)
    for i in range(1, n + 1):
        assert _call(client, key_id, i).status_code == 200
    return key_id


def test_claim_counts_the_guest_allowance_against_the_free_grant_once(client, system_conn):
    key_id = _spend_as_guest(client, 3)
    h = _signed_in(client)
    uid = client.get("/v1/me", headers=h).json()["id"]
    free = system_conn.execute("SELECT monthly_credits FROM plans WHERE code = 'free'").fetchone()[
        0
    ]
    cid = str(uuid.uuid4())
    assert _claim(client, h, claim_id=cid, attest_key_id=key_id).status_code == 200
    assert _grant(system_conn, uid) == free - 3
    assert (
        _claim(client, h, claim_id=cid, attest_key_id=key_id).headers["Idempotent-Replay"] == "true"
    )
    assert _grant(system_conn, uid) == free - 3
    # a second claim with the same device key counts nothing more: the key's month is counted once
    assert _claim(client, h, merge=True, attest_key_id=key_id).status_code == 200
    assert _grant(system_conn, uid) == free - 3
    assert system_conn.execute(
        "SELECT count(*), coalesce(sum(delta), 0) FROM credit_ledger WHERE user_id = %s AND entry_type = 'adjust'",
        (uid,),
    ).fetchone() == (1, -3)


def test_claim_without_a_key_id_debits_nothing_and_never_goes_below_zero(client, system_conn):
    key_id = _spend_as_guest(client, 3)
    h = _signed_in(client)
    uid = client.get("/v1/me", headers=h).json()["id"]
    assert _claim(client, h).status_code == 200
    assert (
        _grant(system_conn, uid) is None
        or _grant(system_conn, uid)
        == system_conn.execute("SELECT monthly_credits FROM plans WHERE code = 'free'").fetchone()[
            0
        ]
    )
    # the grant holds 2, the key spent 3: it is debited to 0, not below
    system_conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key, expires_at) "
        "VALUES (%s, 'monthly', 12, 2, to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'), now() + interval '20 days') "
        "ON CONFLICT (user_id, kind, period_key) WHERE user_id IS NOT NULL AND period_key IS NOT NULL DO UPDATE SET remaining = 2",
        (uid,),
    )
    assert _claim(client, h, merge=True, attest_key_id=key_id).status_code == 200
    assert _grant(system_conn, uid) == 0


def test_claim_ignores_an_unknown_key_id(client, system_conn):
    h = _signed_in(client)
    uid = client.get("/v1/me", headers=h).json()["id"]
    assert _claim(client, h, attest_key_id="never-attested").status_code == 200
    assert (
        system_conn.execute(
            "SELECT count(*) FROM credit_ledger WHERE user_id = %s AND entry_type = 'adjust'",
            (uid,),
        ).fetchone()[0]
        == 0
    )
