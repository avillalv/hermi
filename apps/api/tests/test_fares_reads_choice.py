# ruff: noqa: E501, F401, F811  (long SQL strings; fixtures imported from the sibling module)
"""WF-030.2: fares reads (best, summary, price history, date grid), fare PATCH, choice and Mark as booked with the price paid."""

import uuid
from datetime import UTC, datetime

import pytest
from tests.test_fares_module import (
    Counting,
    _clean_observations,
    _rows,
    _setup,
    _user,
    client,
    session,
)

from hermi.modules.flights import fares


def _seed(client, session, h):
    trip, rid = _setup(client, h)
    fares.refresh_route(session, uuid.UUID(rid), client=Counting().client, token="t", now=datetime.now(UTC))
    session.commit()
    page = client.get(f"/v1/trips/{trip}/routes/{rid}/fares", headers=h).json()["items"]
    return trip, rid, page


def _viewer(client, system_conn, trip):
    v = _user(client)
    me = client.get("/v1/me", headers=v).json()["id"]
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (trip, me))
    return v


def test_best_sorts_and_hides(client, session):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    url = f"/v1/trips/{trip}/flights/best"
    best = client.get(url, headers=h).json()
    assert [f["price"]["amount_minor"] for f in best] == [152000, 162400] and best[0]["age_label"].startswith("cached ")
    assert len(client.get(url + f"?route_id={rid}&limit=1", headers=h).json()) == 1
    assert client.get(url + "?sort=duration", headers=h).status_code == 200
    assert client.get(url + "?sort=commission", headers=h).status_code == 422
    assert client.get(url + f"?route_id={uuid.uuid4()}", headers=h).json() == []
    client.patch(f"/v1/trips/{trip}/fares/{items[0]['id']}", json={"hidden": True}, headers=h)
    assert len(client.get(url, headers=h).json()) == 1
    assert len(client.get(url + "?include_hidden=true", headers=h).json()) == 2


def test_best_sorts_by_duration_then_stops(client, session):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    url = f"/v1/trips/{trip}/flights/best"
    by_duration = client.get(url + "?sort=duration", headers=h).json()
    assert [f["destination"] for f in by_duration] == ["HND", "NRT"]  # 675 min against 1020
    by_stops = client.get(url + "?sort=stops", headers=h).json()
    assert [f["stops_out"] for f in by_stops] == [0, 1]


def test_summary_has_cheapest_count_and_etag(client, session):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    r = client.get(f"/v1/trips/{trip}/flights/summary", headers=h)
    s = r.json()[0]
    assert s["route_id"] == rid and s["fare_count"] == 2 and s["cheapest"]["id"] == items[0]["id"] and s["chosen"] is None
    assert s["last_checked_at"] is not None and r.headers["etag"]
    assert client.get(f"/v1/trips/{trip}/flights/summary", headers={**h, "If-None-Match": r.headers["etag"]}).status_code == 304
    client.patch(f"/v1/trips/{trip}/fares/{items[0]['id']}", json={"hidden": True}, headers=h)
    s2 = client.get(f"/v1/trips/{trip}/flights/summary", headers=h).json()[0]
    assert s2["fare_count"] == 1 and s2["cheapest"]["id"] == items[1]["id"]


def test_date_grid_cheapest_per_pair(client, session):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    grid = client.get(f"/v1/trips/{trip}/routes/{rid}/date-grid", headers=h).json()
    assert [(c["depart_date"], c["return_date"], c["price"]["amount_minor"]) for c in grid] == [
        ("2026-11-10", "2026-11-17", 152000),
        ("2026-11-12", "2026-11-20", 162400),
    ]
    assert {c["fare_id"] for c in grid} == {i["id"] for i in items} and grid[0]["source"] == "travelpayouts"
    client.patch(f"/v1/trips/{trip}/fares/{items[0]['id']}", json={"suspect": True}, headers=h)
    assert len(client.get(f"/v1/trips/{trip}/routes/{rid}/date-grid", headers=h).json()) == 1


def test_date_grid_stops_at_330_days(client, session, system_conn):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    system_conn.execute(
        "UPDATE fare_observations SET depart_date = CURRENT_DATE + 331 WHERE id IN (SELECT observation_id FROM trip_fare_links WHERE id = %s)",
        (items[0]["id"],),
    )
    assert len(client.get(f"/v1/trips/{trip}/routes/{rid}/date-grid", headers=h).json()) == 1


def test_price_history_daily_minimum_by_source(client, session, system_conn):
    h = _user(client)
    trip, rid, _ = _seed(client, session, h)
    ph = client.get(f"/v1/trips/{trip}/routes/{rid}/price-history", headers=h).json()
    assert ph["currency"] == "USD" and ph["google"] == [] and ph["price_level"] is None
    # observed_at is when the provider saw each fare (the fixture's search_date), so each lands on its own day
    assert [(p["day"], p["source"], p["price"]["amount_minor"]) for p in ph["points"]] == [("2026-10-02", "travelpayouts", 152000), ("2026-10-03", "travelpayouts", 162400)]
    system_conn.execute("DELETE FROM trip_fare_links WHERE route_id = %s", (rid,))
    empty = client.get(f"/v1/trips/{trip}/routes/{rid}/price-history", headers=h).json()
    assert empty["points"] == [] and empty["typical_low"] is None


def test_reads_never_spend_credits_or_call_the_provider(client, session, system_conn):
    h = _user(client)
    trip, rid, _ = _seed(client, session, h)
    calls = _rows(system_conn, "SELECT count(*) FROM provider_calls")
    ledger = _rows(system_conn, "SELECT count(*) FROM credit_ledger")
    for p in ("flights/best", "flights/summary", f"routes/{rid}/date-grid", f"routes/{rid}/price-history"):
        assert client.get(f"/v1/trips/{trip}/{p}", headers=h).status_code == 200
    assert _rows(system_conn, "SELECT count(*) FROM provider_calls") == calls
    assert _rows(system_conn, "SELECT count(*) FROM credit_ledger") == ledger


def test_patch_fare_roles_and_tenancy(client, session, system_conn):
    h, stranger = _user(client), _user(client)
    trip, rid, items = _seed(client, session, h)
    v = _viewer(client, system_conn, trip)
    url = f"/v1/trips/{trip}/fares/{items[0]['id']}"
    r = client.patch(url, json={"hidden": True, "suspect": True}, headers=h)
    assert r.status_code == 200 and r.json()["hidden"] is True and r.json()["suspect"] is True and r.json()["id"] == items[0]["id"]
    assert client.patch(url, json={}, headers=h).status_code == 422
    assert client.patch(url, json={"hidden": False}, headers=v).status_code == 403
    assert client.patch(url, json={"hidden": False}, headers=stranger).status_code == 404
    assert client.patch(f"/v1/trips/{trip}/fares/{uuid.uuid4()}", json={"hidden": False}, headers=h).status_code == 404
    assert _rows(system_conn, "SELECT count(*) FROM fare_observations") == [(2,)]  # shared data is never deleted


def test_choose_a_fare_sets_trip_dates_and_route(client, session, system_conn):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    url = f"/v1/trips/{trip}/routes/{rid}/choice"
    r = client.put(url, json={"fare_id": items[1]["id"]}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == trip and r.json()["start_date"] == "2026-11-12" and r.json()["end_date"] == "2026-11-20"
    row = _rows(system_conn, "SELECT price_total_minor, currency, origin, destination, airlines, booked_at, paid_minor FROM chosen_flights WHERE route_id = %s", rid)
    assert row == [(162400, "USD", "LAX", "HND", ["JL"], None, None)]
    route = client.get(f"/v1/trips/{trip}/routes", headers=h).json()[0]
    assert route["chosen_fare_id"] == items[1]["id"]
    assert client.get(f"/v1/trips/{trip}/flights/summary", headers=h).json()[0]["chosen"]["id"] == items[1]["id"]
    # choosing again replaces the choice and leaves the trip's dates alone
    r2 = client.put(url, json={"fare_id": items[0]["id"]}, headers=h)
    assert r2.json()["start_date"] == "2026-11-12"
    assert _rows(system_conn, "SELECT count(*), min(destination) FROM chosen_flights WHERE route_id = %s", rid) == [(1, "NRT")]
    assert client.delete(url, headers=h).json()["id"] == trip
    assert _rows(system_conn, "SELECT count(*) FROM chosen_flights WHERE route_id = %s", rid) == [(0,)]


def test_choice_rejects_other_routes_unknown_and_past_fares(client, session, system_conn):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    _, _, other_items = _seed(client, session, _user(client))
    url = f"/v1/trips/{trip}/routes/{rid}/choice"
    assert client.put(url, json={"fare_id": other_items[0]["id"]}, headers=h).status_code == 404  # another trip's fare
    assert client.put(url, json={"fare_id": str(uuid.uuid4())}, headers=h).status_code == 404
    system_conn.execute(
        "UPDATE fare_observations SET depart_date = CURRENT_DATE - 1 WHERE id IN (SELECT observation_id FROM trip_fare_links WHERE id = %s)",
        (items[0]["id"],),
    )
    r = client.put(url, json={"fare_id": items[0]["id"]}, headers=h)
    assert r.status_code == 422 and "already left" in r.json()["detail"]


def test_choice_is_editor_only(client, session, system_conn):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    v = _viewer(client, system_conn, trip)
    url = f"/v1/trips/{trip}/routes/{rid}/choice"
    assert client.put(url, json={"fare_id": items[0]["id"]}, headers=v).status_code == 403
    assert client.delete(url, headers=v).status_code == 403
    assert client.post(url + "/booked", json={"booked": True}, headers=v).status_code == 403


def test_mark_as_booked_with_price_paid(client, session, system_conn):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    url = f"/v1/trips/{trip}/routes/{rid}/choice"
    booked = url + "/booked"
    assert client.post(booked, json={"booked": True}, headers=h).status_code == 409  # nothing chosen yet
    client.put(url, json={"fare_id": items[0]["id"]}, headers=h)
    assert client.post(booked, json={"booked": True, "paid": {"amount_minor": 0, "currency": "USD"}}, headers=h).status_code == 422
    assert client.post(booked, json={"booked": True, "paid": {"amount_minor": 1000, "currency": "ZZZ"}}, headers=h).status_code == 422
    assert client.post(booked, json={"booked": True, "booked_at": "2999-01-01T00:00:00Z"}, headers=h).status_code == 422
    assert client.post(booked, json={"booked": True, "booked_at": "2026-01-01T00:00:00"}, headers=h).status_code == 422  # no zone
    r = client.post(booked, json={"booked": True, "paid": {"amount_minor": 149900, "currency": "USD"}}, headers=h)
    assert r.status_code == 200 and r.json()["id"] == trip
    me = client.get("/v1/me", headers=h).json()["id"]
    sql = "SELECT paid_minor, paid_currency, booked_at IS NOT NULL, booked_by::text, paid_source FROM chosen_flights WHERE route_id = %s"
    assert _rows(system_conn, sql, rid) == [(149900, "USD", True, me, "manual")]
    client.post(booked, json={"booked": True}, headers=h)  # booked with no amount keeps what was paid
    assert _rows(system_conn, "SELECT paid_minor FROM chosen_flights WHERE route_id = %s", rid) == [(149900,)]
    client.post(booked, json={"booked": True, "paid": None}, headers=h)  # paid: null clears only the amount
    assert _rows(system_conn, "SELECT paid_minor, booked_at IS NOT NULL FROM chosen_flights WHERE route_id = %s", rid) == [(None, True)]
    client.post(booked, json={"booked": True, "paid": {"amount_minor": 1500, "currency": "EUR"}}, headers=h)
    assert client.post(booked, json={"booked": False}, headers=h).status_code == 200
    assert _rows(system_conn, "SELECT paid_minor, paid_currency, booked_at, booked_by, paid_source FROM chosen_flights WHERE route_id = %s", rid) == [(None, None, None, None, None)]


def test_choice_with_paid_marks_booked_in_one_call(client, session, system_conn):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    url = f"/v1/trips/{trip}/routes/{rid}/choice"
    r = client.put(url, json={"fare_id": items[0]["id"], "paid": {"amount_minor": 150000, "currency": "USD"}}, headers=h)
    assert r.status_code == 200
    assert _rows(system_conn, "SELECT paid_minor, booked_at IS NOT NULL FROM chosen_flights WHERE route_id = %s", rid) == [(150000, True)]
    client.put(url, json={"fare_id": items[0]["id"]}, headers=h)  # the same fare again is a no-op
    assert _rows(system_conn, "SELECT paid_minor, booked_at IS NOT NULL FROM chosen_flights WHERE route_id = %s", rid) == [(150000, True)]
    client.put(url, json={"fare_id": items[1]["id"]}, headers=h)  # a different flight drops the old booking
    assert _rows(system_conn, "SELECT paid_minor, booked_at FROM chosen_flights WHERE route_id = %s", rid) == [(None, None)]


def test_choice_is_logged_without_the_amount(client, session, system_conn):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    client.put(f"/v1/trips/{trip}/routes/{rid}/choice", json={"fare_id": items[0]["id"], "paid": {"amount_minor": 150000, "currency": "USD"}}, headers=h)
    rows = _rows(system_conn, "SELECT verb, summary FROM activity_log WHERE trip_id = %s AND entity_type = 'flight'", trip)
    assert rows and not any("150000" in s or "1500" in s for _, s in rows)


@pytest.mark.parametrize("path", ["flights/summary", "flights/best"])
def test_stranger_gets_404_on_reads(client, session, path):
    h = _user(client)
    trip, _, _ = _seed(client, session, h)
    assert client.get(f"/v1/trips/{trip}/{path}", headers=_user(client)).status_code == 404


def test_fare_carries_a_plain_airline_search_link(client, session):
    h = _user(client)
    _, _, items = _seed(client, session, h)
    for f in items:
        url = f["airline_search_url"]
        assert url.startswith("https://www.google.com/travel/flights?q=")
        assert f["origin"] in url and f["destination"] in url
        assert not any(w in url.lower() for w in ("marker", "airbnb", "vrbo", "booking.com", "aviasales", "travelpayouts"))


def test_fare_carries_run_id_and_source_domain_for_the_evidence_label(client, session):
    h = _user(client)
    trip, rid, items = _seed(client, session, h)
    assert all("run_id" in f and "source_domain" in f for f in items)
    assert all(f["run_id"] is None for f in items)  # provider fares have no agent run
