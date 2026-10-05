# ruff: noqa: E501, F401, F811  (long SQL strings; fixtures imported from the sibling module)
"""WF-031.1: price_alerts API (limit through the resolver, alert_limit paywall), pure drop detection, idempotent trigger."""

import uuid
from datetime import date, timedelta

import pytest
from tests.test_fares_module import ROUTE, _clean_observations, _setup, _user, client, session

from hermi.modules.flights.alerts import detect_drop, evaluate_alert

BODY = {"target_price": {"amount_minor": 100000, "currency": "USD"}, "notify": {"push": True, "email": False}, "active": True}


@pytest.fixture(autouse=True)
def _usd_rate(system_conn):
    system_conn.execute("INSERT INTO fx_rates (currency, per_eur, rate_date) VALUES ('USD', 1.25, CURRENT_DATE) ON CONFLICT (currency) DO UPDATE SET per_eur = 1.25")


def _plus(client, system_conn, h):
    uid = client.get("/v1/me", headers=h).json()["id"]
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus', valid_until = NULL WHERE user_id = %s", (uid,))


def _fare(system_conn, trip, rid, price, currency="USD", expires="now() + interval '6 hours'", depart=None, confidence="cached"):
    depart = depart or date.today() + timedelta(days=30)
    oid = system_conn.execute(
        "INSERT INTO fare_observations (search_key, origin, destination, depart_date, source, confidence, currency, price_total_minor, observed_at, expires_at) "
        f"VALUES (%s, 'LAX', 'NRT', %s, 'travelpayouts', %s, %s, %s, now(), {expires}) RETURNING id",
        (uuid.uuid4().hex * 2, depart, confidence, currency, price),
    ).fetchone()[0]
    system_conn.execute("INSERT INTO trip_fare_links (trip_id, route_id, observation_id) VALUES (%s, %s, %s)", (trip, rid, oid))


def test_detect_drop_thresholds():
    assert detect_drop([120000, 99000, 101000], 100000, None) == 99000  # cheapest, at or under the target
    assert detect_drop([100000], 100000, None) == 100000  # equal triggers
    assert detect_drop([100001], 100000, None) is None
    assert detect_drop([], 100000, None) is None
    assert detect_drop([None, 90000], 100000, None) == 90000  # an unconvertible fare is skipped
    assert detect_drop([90000], 100000, 90000) is None  # same price: already told
    assert detect_drop([90000], 100000, 85000) is None  # higher than the last told price
    assert detect_drop([80000], 100000, 90000) == 80000  # a further drop triggers again


def test_create_list_patch_delete(client, system_conn):
    h = _user(client)
    trip, rid = _setup(client, h)
    r = client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=h)
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["route_id"] == rid and a["target_price"] == BODY["target_price"] and a["notify"] == BODY["notify"] and a["last_notified_price"] is None
    assert client.get(f"/v1/trips/{trip}/price-alerts", headers=h).json() == [a]
    p = client.patch(f"/v1/price-alerts/{a['id']}", json={"active": False, "notify": {"push": False, "email": True}}, headers=h)
    assert p.status_code == 200 and p.json()["active"] is False and p.json()["notify"] == {"push": False, "email": True}
    assert p.json()["target_price"] == BODY["target_price"]
    assert client.delete(f"/v1/price-alerts/{a['id']}", headers=h).status_code == 204
    assert client.get(f"/v1/trips/{trip}/price-alerts", headers=h).json() == []
    assert client.delete(f"/v1/price-alerts/{a['id']}", headers=h).status_code == 404


def test_free_limit_is_one_with_alert_limit_paywall(client, system_conn):
    h = _user(client)
    trip, rid = _setup(client, h)
    assert client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=h).status_code == 201
    assert client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=h).status_code == 409  # one per route and person
    trip2 = client.post("/v1/trips", json={"name": "Rome"}, headers=h).json()["id"]
    rid2 = client.post(f"/v1/trips/{trip2}/routes", json=ROUTE, headers=h).json()["id"]
    r = client.post(f"/v1/routes/{rid2}/price-alerts", json=BODY, headers=h)
    assert r.status_code == 402 and r.json()["code"] == "limit_reached"
    assert r.json()["paywall"]["trigger"] == "alert_limit"
    _plus(client, system_conn, h)
    assert client.post(f"/v1/routes/{rid2}/price-alerts", json=BODY, headers=h).status_code == 201


def test_validation_and_currency(client):
    h = _user(client)
    _, rid = _setup(client, h)
    url = f"/v1/routes/{rid}/price-alerts"
    assert client.post(url, json={**BODY, "target_price": {"amount_minor": 0, "currency": "USD"}}, headers=h).status_code == 422
    assert client.post(url, json={**BODY, "target_price": {"amount_minor": 5, "currency": "ZZZ"}}, headers=h).status_code == 422
    assert client.post(f"/v1/routes/{uuid.uuid4()}/price-alerts", json=BODY, headers=h).status_code == 404


def test_roles_and_tenancy(client, system_conn):
    h = _user(client)
    trip, rid = _setup(client, h)
    a = client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=h).json()
    v, s = _user(client), _user(client)
    vid = client.get("/v1/me", headers=v).json()["id"]
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (trip, vid))
    assert client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=v).status_code == 403
    assert client.get(f"/v1/trips/{trip}/price-alerts", headers=v).json() == []  # alerts are personal
    assert client.patch(f"/v1/price-alerts/{a['id']}", json={"active": False}, headers=v).status_code == 404
    assert client.delete(f"/v1/price-alerts/{a['id']}", headers=v).status_code == 404
    assert client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=s).status_code == 404
    assert client.get(f"/v1/trips/{trip}/price-alerts", headers=s).status_code == 404


def test_evaluate_triggers_once_per_drop(client, system_conn, session):
    h = _user(client)
    trip, rid = _setup(client, h)
    aid = uuid.UUID(client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=h).json()["id"])
    assert evaluate_alert(session, aid) is None  # no fares yet
    _fare(system_conn, trip, rid, 120000)
    assert evaluate_alert(session, aid) is None  # above the target
    _fare(system_conn, trip, rid, 95000)
    t = evaluate_alert(session, aid)
    assert t is not None and (t.price_minor, t.currency, t.alert_id) == (95000, "USD", aid)
    assert evaluate_alert(session, aid) is None and evaluate_alert(session, aid) is None  # idempotent
    session.commit()
    got = client.get(f"/v1/trips/{trip}/price-alerts", headers=h).json()[0]
    assert got["last_notified_price"] == {"amount_minor": 95000, "currency": "USD"} and got["last_notified_at"] is not None
    _fare(system_conn, trip, rid, 90000)
    t2 = evaluate_alert(session, aid)
    assert t2 is not None and t2.price_minor == 90000  # a new, lower price is a new drop
    assert evaluate_alert(session, aid) is None


def test_evaluate_converts_currency_and_skips_inactive(client, system_conn, session):
    h = _user(client)
    trip, rid = _setup(client, h)
    aid = uuid.UUID(client.post(f"/v1/routes/{rid}/price-alerts", json={**BODY, "target_price": {"amount_minor": 100000, "currency": "USD"}}, headers=h).json()["id"])
    _fare(system_conn, trip, rid, 72000, currency="EUR")  # 900.00 USD at 1.25
    t = evaluate_alert(session, aid)
    assert t is not None and t.price_minor == 90000 and t.currency == "USD"
    session.commit()
    client.patch(f"/v1/price-alerts/{aid}", json={"active": False}, headers=h)
    _fare(system_conn, trip, rid, 40000, currency="EUR")
    assert evaluate_alert(session, aid) is None


def test_stale_fares_do_not_trigger(client, system_conn, session):
    h = _user(client)
    trip, rid = _setup(client, h)
    aid = uuid.UUID(client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=h).json()["id"])
    _fare(system_conn, trip, rid, 50000, expires="now() - interval '1 hour'")  # cache window over
    _fare(system_conn, trip, rid, 50000, depart="2020-01-01")  # already departed
    _fare(system_conn, trip, rid, 50000, confidence="indicative")  # not a cached fare
    assert evaluate_alert(session, aid) is None


def test_reset_alert_does_not_notify_twice(client, system_conn, session):
    h = _user(client)
    trip, rid = _setup(client, h)
    aid = uuid.UUID(client.post(f"/v1/routes/{rid}/price-alerts", json=BODY, headers=h).json()["id"])
    _fare(system_conn, trip, rid, 95000)
    assert evaluate_alert(session, aid) is not None
    session.commit()
    system_conn.execute("UPDATE price_alerts SET last_notified_price_minor = NULL WHERE id = %s", (aid,))
    assert evaluate_alert(session, aid) is None
    session.commit()
    rows = system_conn.execute("SELECT kind, dedupe_key, want_push FROM notifications WHERE dedupe_key = %s", (f"price_drop:{aid}:95000",)).fetchall()
    assert rows == [("price_drop", f"price_drop:{aid}:95000", True)]


def test_pass_raises_the_cap_on_its_own_trip_only(client, system_conn):
    h = _user(client)
    trip, rid = _setup(client, h)
    trip2, rid2 = _setup(client, h)
    system_conn.execute("INSERT INTO trip_passes (trip_id, plan_code, starts_at, expires_at, status) VALUES (%s, 'trip_pass', now() - interval '1 day', now() + interval '30 days', 'active')", (trip,))
    post = lambda r: client.post(f"/v1/routes/{r}/price-alerts", json=BODY, headers=h).status_code  # noqa: E731
    assert post(rid2) == 201  # the Free alert, on a trip with no pass
    assert post(rid) == 201 and post(client.post(f"/v1/trips/{trip}/routes", json=ROUTE, headers=h).json()["id"]) == 201  # the pass trip has room for 2
    assert post(client.post(f"/v1/trips/{trip}/routes", json=ROUTE, headers=h).json()["id"]) == 402  # and no more


def test_notification_body_follows_the_currency_exponent(client, system_conn, session):
    system_conn.execute("INSERT INTO fx_rates (currency, per_eur, rate_date) VALUES ('JPY', 160, CURRENT_DATE) ON CONFLICT (currency) DO UPDATE SET per_eur = 160")
    h = _user(client)
    trip, rid = _setup(client, h)
    body = {**BODY, "target_price": {"amount_minor": 20000, "currency": "JPY"}}
    aid = uuid.UUID(client.post(f"/v1/routes/{rid}/price-alerts", json=body, headers=h).json()["id"])
    _fare(system_conn, trip, rid, 15000, currency="JPY")
    assert evaluate_alert(session, aid) is not None
    session.commit()
    assert system_conn.execute("SELECT body FROM notifications WHERE dedupe_key = %s", (f"price_drop:{aid}:15000",)).fetchone()[0] == "A fare is down to 15000 JPY."
