# ruff: noqa: E501  (long lines)
"""WF-054: AI consent (GET and PUT /me/consents, 04 section 5.2), the gate that follows it, and reports (POST /reports, 04 section 5.14).

Real schema and roles, fake provider, no network. Reports land in `content_reports` for the moderation queue (WF-106)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token

LISBON = {"name": "Lisbon", "country": "Portugal", "country_code": "PT", "lat": 38.72, "lon": -9.14, "timezone": "Europe/Lisbon"}
RUN_SQL = "INSERT INTO runs (trip_id, user_id, kind, status, finished_at, provider) VALUES (%s, %s, 'explain', 'succeeded', now(), 'fake') RETURNING id"


@pytest.fixture
def client(db_urls):
    s = Settings(_env_file=None, environment="ci", auth_mode="dev", ai_provider="fake", providers_mode="fake", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10)
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
    o, ou = _user(client)
    v, vu = _user(client)
    s, _ = _user(client)
    t = client.post("/v1/trips", json={"name": "Trip", "destinations": [LISBON], "start_date": "2027-05-01", "end_date": "2027-05-05"}, headers=o).json()
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (t["id"], vu["id"]))
    run = system_conn.execute(RUN_SQL, (t["id"], ou["id"])).fetchone()[0]
    return {"o": o, "v": v, "s": s, "tid": t["id"], "run": str(run), "oid": ou["id"], "conn": system_conn}


def _explain(client, w):
    return client.post(f"/v1/trips/{w['tid']}/ai/explain", json={"question": "Is Alfama quiet at night?"}, headers={**w["o"], "Idempotency-Key": uuid.uuid4().hex})


def _consent(client, h, granted=True, kind="ai_processing", version="1"):
    return client.put(f"/v1/me/consents/{kind}", json={"version": version, "granted": granted}, headers=h)


# --- consent --------------------------------------------------------------------------------------------------------


def test_no_ai_call_without_consent_and_withdrawal_blocks_again(client, world):
    r = _explain(client, world)
    assert (r.status_code, r.json()["code"]) == (403, "ai_consent_required")
    assert client.get("/v1/me/consents", headers=world["o"]).json() == []

    r = _consent(client, world["o"])
    assert r.status_code == 200
    body = r.json()
    assert (body["kind"], body["version"], body["granted"]) == ("ai_processing", "1", True) and body["accepted_at"]
    after = _explain(client, world)
    assert after.status_code == 200, after.text
    assert uuid.UUID(after.json()["run_id"])  # the target for thumbs and POST /reports

    assert _consent(client, world["o"], granted=False).json()["granted"] is False
    r = _explain(client, world)
    assert (r.status_code, r.json()["code"]) == (403, "ai_consent_required")
    # Account and trips still work: revoking AI disables AI only.
    assert client.get(f"/v1/trips/{world['tid']}", headers=world["o"]).status_code == 200
    assert client.get("/v1/me", headers=world["o"]).json()["consents"] == []


def test_consents_are_stored_with_version_and_timestamp_and_history_is_kept(client, world):
    _consent(client, world["o"], version="2026-10")
    _consent(client, world["o"], granted=False, version="2026-10")
    _consent(client, world["o"], version="2027-01")
    rows = world["conn"].execute("SELECT version, granted, created_at IS NOT NULL FROM consents WHERE user_id = %s AND kind = 'ai_processing' ORDER BY created_at, id", (world["oid"],)).fetchall()
    assert rows == [("2026-10", True, True), ("2026-10", False, True), ("2027-01", True, True)]
    cur = client.get("/v1/me/consents", headers=world["o"]).json()
    assert [(c["kind"], c["version"], c["granted"]) for c in cur] == [("ai_processing", "2027-01", True)]
    me = client.get("/v1/me", headers=world["o"]).json()["consents"]
    assert [(c["kind"], c["version"]) for c in me] == [("ai_processing", "2027-01")]


def test_consent_is_per_account_and_validated(client, world):
    _consent(client, world["o"])
    assert client.get("/v1/me/consents", headers=world["v"]).json() == []
    assert _consent(client, world["o"], kind="made_up").status_code == 422
    assert _consent(client, world["o"], version="").status_code == 422
    assert client.put("/v1/me/consents/ai_processing", json={"version": "1"}, headers=world["o"]).status_code == 422
    assert client.get("/v1/me/consents").status_code == 401


def test_trip_toggle_off_blocks_ai_even_with_consent(client, world):
    _consent(client, world["o"])
    r = client.patch(f"/v1/trips/{world['tid']}", json={"ai_enabled": False, "version": 1}, headers=world["o"])
    assert r.status_code == 200, r.text
    r = _explain(client, world)
    assert (r.status_code, r.json()["code"]) == (403, "ai_disabled_for_trip")


def test_withdrawing_consent_cancels_the_users_queued_agent_runs(client, world):
    _consent(client, world["o"])
    rid = world["conn"].execute(
        "INSERT INTO runs (trip_id, user_id, kind, status, provider) VALUES (%s, %s, 'deep_research', 'queued', 'fake') RETURNING id", (world["tid"], world["oid"])
    ).fetchone()[0]
    assert _consent(client, world["o"], granted=False).status_code == 200
    status, flag = world["conn"].execute("SELECT status::text, cancel_requested FROM runs WHERE id = %s", (rid,)).fetchone()
    assert (status, flag) == ("cancelled", True)


def test_withdrawal_leaves_inline_runs_alone(client, world):
    _consent(client, world["o"])
    rid = world["conn"].execute(
        "INSERT INTO runs (trip_id, user_id, kind, status, provider) VALUES (%s, %s, 'explain', 'queued', 'fake') RETURNING id", (world["tid"], world["oid"])
    ).fetchone()[0]
    assert _consent(client, world["o"], granted=False).status_code == 200
    status, flag = world["conn"].execute("SELECT status::text, cancel_requested FROM runs WHERE id = %s", (rid,)).fetchone()
    assert (status, flag) == ("queued", False)
    assert world["conn"].execute("SELECT count(*) FROM credit_ledger WHERE run_id = %s", (rid,)).fetchone()[0] == 0


# --- reports --------------------------------------------------------------------------------------------------------


def _report(client, h, **body):
    return client.post("/v1/reports", json={"reason": "wrong_info", **body}, headers=h)


def test_thumbs_down_report_creates_a_moderation_item(client, world):
    r = _report(client, world["v"], run_id=world["run"], detail="The museum is closed on Mondays.")
    assert r.status_code == 201, r.text
    row = world["conn"].execute("SELECT target_type, run_id, reason, status, detail FROM content_reports WHERE id = %s", (r.json()["id"],)).fetchone()
    assert row == ("ai_answer", uuid.UUID(world["run"]), "wrong_info", "open", "The museum is closed on Mondays.")


def test_report_is_idempotent_per_user_and_target(client, world):
    first = _report(client, world["o"], run_id=world["run"])
    again = _report(client, world["o"], run_id=world["run"], reason="harmful")
    assert first.status_code == 201 and again.status_code == 200 and again.json()["id"] == first.json()["id"]
    other = _report(client, world["v"], run_id=world["run"])
    assert other.status_code == 201 and other.json()["id"] != first.json()["id"]
    n = world["conn"].execute("SELECT count(*) FROM content_reports WHERE run_id = %s", (world["run"],)).fetchone()[0]
    assert n == 2


def test_price_was_different_after_a_thumbs_down_keeps_both_signals(client, world):
    down = _report(client, world["o"], run_id=world["run"])
    price = _report(client, world["o"], run_id=world["run"], detail="Price was different: fare f1, https://x.example/a, 68400 USD")
    assert down.status_code == 201 and price.status_code == 201 and price.json()["id"] != down.json()["id"]
    again = _report(client, world["o"], run_id=world["run"], detail="Price was different: fare f1, https://x.example/a, 68400 USD")
    assert again.status_code == 200 and again.json()["id"] == price.json()["id"]
    details = world["conn"].execute("SELECT detail FROM content_reports WHERE run_id = %s ORDER BY created_at", (world["run"],)).fetchall()
    assert [d[0] for d in details] == ["", "Price was different: fare f1, https://x.example/a, 68400 USD"]


def test_report_target_rules(client, world):
    assert _report(client, world["s"], run_id=world["run"]).status_code == 404  # a stranger cannot see the run
    assert _report(client, world["o"], run_id=str(uuid.uuid4())).status_code == 404
    assert _report(client, world["o"]).status_code == 422  # neither
    assert _report(client, world["o"], run_id=world["run"], note_id=str(uuid.uuid4())).status_code == 422  # both
    assert _report(client, world["o"], run_id=world["run"], reason="nope").status_code == 422
    assert _report(client, world["o"], run_id=world["run"], detail="x" * 1001).status_code == 422
    assert client.post("/v1/reports", json={"run_id": world["run"], "reason": "spam"}).status_code == 401


def test_report_rate_limit_is_20_a_day(client, world):
    conn = world["conn"]
    for _ in range(20):
        rid = conn.execute(RUN_SQL, (world["tid"], world["oid"])).fetchone()[0]
        assert _report(client, world["o"], run_id=str(rid)).status_code == 201
    rid = conn.execute(RUN_SQL, (world["tid"], world["oid"])).fetchone()[0]
    r = _report(client, world["o"], run_id=str(rid))
    assert (r.status_code, r.json()["code"]) == (429, "rate_limited")
