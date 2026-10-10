# ruff: noqa: E501  (long SQL strings and payloads)
"""WF-062.1: App Attest challenge and attestation, and POST /v1/guest/ai/draft-day on guest_allowances (04 section 5.1).

The fake verifier (PROVIDERS_MODE=fake) accepts what `hermi.security.attest.fake_*` produce; the live verifier is covered
for malformed input only (a real attestation needs a device: owner verification)."""

import json
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from tests.test_auth_provisioning import _auth, _settings

from hermi.main import create_app
from hermi.modules.admin.flags import Flag, FlagRuntime, Snapshot
from hermi.security import attest

BODY = {"destination": "Lisbon", "day": "2027-05-01", "preferences": "slow mornings"}
TABLES = (
    "users",
    "trips",
    "runs",
    "ai_usage",
    "credit_grants",
    "credit_ledger",
    "idempotency_keys",
    "consents",
    "people",
)


GUEST_ON = Flag("guest_mode", "boolean", True, 100, {}, {})


@pytest.fixture
def client(db_urls):
    s = _settings(db_urls)
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _attest(client, key_id=None):
    key_id = key_id or "key-" + uuid.uuid4().hex
    ch = client.post("/v1/devices/attest/challenge")
    assert ch.status_code == 200, ch.text
    nonce = ch.json()["nonce"]
    r = client.post(
        "/v1/devices/attest",
        json={
            "key_id": key_id,
            "attestation": attest.fake_attestation(key_id, nonce),
            "nonce": nonce,
        },
    )
    assert r.status_code == 204, r.text
    return key_id


def _call(client, key_id, counter, body=None, idem=None, **over):
    body = BODY if body is None else body
    raw = json.dumps(body).encode()
    idem = idem or str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": idem,
        "X-Attest-Key-Id": key_id,
        "X-Attest-Assertion": attest.fake_assertion(key_id, counter, attest.client_data(idem, raw)),
        **over,
    }
    return client.post("/v1/guest/ai/draft-day", content=raw, headers=headers)


def _rows(system_conn):
    return {t: system_conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABLES}


def _used(system_conn, key_id):
    r = system_conn.execute(
        "SELECT coalesce(sum(credits_used), 0) FROM guest_allowances WHERE key_id = %s", (key_id,)
    ).fetchone()
    return int(r[0])


def test_challenge_is_a_nonce_with_a_five_minute_expiry(client):
    r = client.post("/v1/devices/attest/challenge")
    assert r.status_code == 200
    assert len(r.json()["nonce"]) >= 32 and r.json()["expires_at"].endswith(("Z", "+00:00"))
    assert client.post("/v1/devices/attest/challenge").json()["nonce"] != r.json()["nonce"]


def test_challenges_are_rate_limited_per_ip(client):
    from hermi.security import rate_limit

    rate_limit.TEST_LIMITS["write_ip"] = 1
    rate_limit.reset_cache()
    codes = [client.post("/v1/devices/attest/challenge").status_code for _ in range(3)]
    assert (
        429 in codes
    )  # the window may already hold a hit from another test, so the first call can be 429 too


def test_attest_stores_the_key_with_counter_zero(client, system_conn):
    key_id = _attest(client)
    row = system_conn.execute(
        "SELECT counter, environment FROM device_attestations WHERE key_id = %s", (key_id,)
    ).fetchone()
    assert row == (0, "development")


def test_a_challenge_works_once(client):
    nonce = client.post("/v1/devices/attest/challenge").json()["nonce"]
    for key_id, want in (("key-" + uuid.uuid4().hex, 204), ("key-" + uuid.uuid4().hex, 422)):
        r = client.post(
            "/v1/devices/attest",
            json={
                "key_id": key_id,
                "attestation": attest.fake_attestation(key_id, nonce),
                "nonce": nonce,
            },
        )
        assert r.status_code == want
    assert r.json()["code"] == "attestation_invalid"


def test_attest_rejects_a_bad_attestation_an_unknown_and_an_expired_nonce(client, system_conn):
    nonce = client.post("/v1/devices/attest/challenge").json()["nonce"]
    bad = client.post(
        "/v1/devices/attest", json={"key_id": "k1", "attestation": "garbage", "nonce": nonce}
    )
    assert bad.status_code == 422 and bad.json()["code"] == "attestation_invalid"
    # an unknown nonce is refused
    unknown = client.post(
        "/v1/devices/attest",
        json={
            "key_id": "k2",
            "attestation": attest.fake_attestation("k2", "nope"),
            "nonce": "nope",
        },
    )
    assert unknown.status_code == 422
    nonce2 = client.post("/v1/devices/attest/challenge").json()["nonce"]
    system_conn.execute(
        "UPDATE rate_limit_counters SET window_start = now() - interval '1 minute' WHERE bucket LIKE 'attest_nonce:%'"
    )
    expired = client.post(
        "/v1/devices/attest",
        json={
            "key_id": "k3",
            "attestation": attest.fake_attestation("k3", nonce2),
            "nonce": nonce2,
        },
    )
    assert expired.status_code == 422
    assert (
        system_conn.execute(
            "SELECT count(*) FROM device_attestations WHERE key_id IN ('k1', 'k2', 'k3')"
        ).fetchone()[0]
        == 0
    )


def test_an_attested_key_cannot_be_registered_again(client):
    key_id = _attest(client)
    nonce = client.post("/v1/devices/attest/challenge").json()["nonce"]
    r = client.post(
        "/v1/devices/attest",
        json={
            "key_id": key_id,
            "attestation": attest.fake_attestation(key_id, nonce),
            "nonce": nonce,
        },
    )
    assert r.status_code == 422 and r.json()["code"] == "attestation_invalid"


def test_draft_day_with_a_valid_assertion_returns_a_draft_and_spends_one_credit(
    client, system_conn
):
    key_id = _attest(client)
    before = _rows(system_conn)
    r = _call(client, key_id, 1)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["day"] == "2027-05-01" and out["items"] and out["rationale"]
    assert out["credits"]["charged"] == 1 and out["credits"]["from_cache"] is False
    assert _used(system_conn, key_id) == 1
    assert (
        system_conn.execute(
            "SELECT counter FROM device_attestations WHERE key_id = %s", (key_id,)
        ).fetchone()[0]
        == 1
    )
    assert (
        _rows(system_conn) == before
    )  # nothing is stored for the guest beyond the allowance row and the counter


def test_a_replayed_counter_is_unauthenticated_and_spends_nothing(client, system_conn):
    key_id = _attest(client)
    assert _call(client, key_id, 5).status_code == 200
    for counter in (5, 4):
        r = _call(client, key_id, counter)
        assert r.status_code == 401 and r.json()["code"] == "unauthenticated"
    assert _used(system_conn, key_id) == 1
    assert _call(client, key_id, 6).status_code == 200


def test_missing_wrong_and_foreign_assertions_are_unauthenticated(client, system_conn):
    key_id = _attest(client)
    other = _attest(client)
    raw = json.dumps(BODY).encode()
    h = {"Content-Type": "application/json", "Idempotency-Key": "idem-12345678"}
    assert client.post("/v1/guest/ai/draft-day", content=raw, headers=h).status_code == 401
    assert (
        client.post(
            "/v1/guest/ai/draft-day", content=raw, headers={**h, "X-Attest-Key-Id": key_id}
        ).status_code
        == 401
    )
    unknown = client.post(
        "/v1/guest/ai/draft-day",
        content=raw,
        headers={
            **h,
            "X-Attest-Key-Id": "nope",
            "X-Attest-Assertion": attest.fake_assertion("nope", 1, b""),
        },
    )
    assert unknown.status_code == 401
    # another device's assertion, and an assertion made for a different body
    r = _call(
        client,
        key_id,
        1,
        **{
            "X-Attest-Assertion": attest.fake_assertion(
                other, 1, attest.client_data("idem-12345678", raw)
            )
        },
        idem="idem-12345678",
    )
    assert r.status_code == 401
    forged = {
        "X-Attest-Assertion": attest.fake_assertion(
            key_id, 1, attest.client_data("idem-12345678", b'{"destination":"Rome"}')
        )
    }
    assert _call(client, key_id, 1, idem="idem-12345678", **forged).status_code == 401
    assert _used(system_conn, key_id) == 0


def test_a_jwt_does_not_replace_the_assertion_and_the_assertion_does_not_open_other_routes(
    client, system_conn
):
    key_id = _attest(client)
    raw = json.dumps(BODY).encode()
    r = client.post(
        "/v1/guest/ai/draft-day",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": "idem-12345678",
            **_auth(client),
        },
    )
    assert r.status_code == 401
    headers = {
        "X-Attest-Key-Id": key_id,
        "X-Attest-Assertion": attest.fake_assertion(
            key_id, 1, attest.client_data("idem-12345678", b"")
        ),
    }
    assert client.get("/v1/trips", headers=headers).status_code == 401
    assert client.get("/v1/me", headers=headers).status_code == 401
    assert client.post("/v1/me/claim", json={}, headers=headers).status_code == 401
    assert (
        client.post(f"/v1/trips/{uuid.uuid4()}/invites", json={}, headers=headers).status_code
        == 401
    )  # guests cannot invite
    assert (
        client.post(
            f"/v1/trips/{uuid.uuid4()}/ai/draft-day",
            json={"day": "2027-05-01"},
            headers={**headers, "Idempotency-Key": "idem-12345678"},
        ).status_code
        == 401
    )


def test_idempotency_key_is_required_and_a_reused_key_is_not_charged_twice(client, system_conn):
    key_id = _attest(client)
    raw = json.dumps(BODY).encode()
    no_key = client.post(
        "/v1/guest/ai/draft-day",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Attest-Key-Id": key_id,
            "X-Attest-Assertion": attest.fake_assertion(key_id, 1, attest.client_data("", raw)),
        },
    )
    assert no_key.status_code == 400 and no_key.json()["code"] == "idempotency_key_required"
    assert _call(client, key_id, 1, idem="idem-aaaaaaaa").status_code == 200
    again = _call(client, key_id, 2, idem="idem-aaaaaaaa")
    assert again.status_code == 409 and again.json()["code"] == "idempotency_key_reused"
    assert _used(system_conn, key_id) == 1


def test_an_empty_allowance_is_402_with_the_sign_up_prompt(client, system_conn):
    key_id = _attest(client)
    limit = system_conn.execute("SELECT monthly_credits FROM plans WHERE code = 'free'").fetchone()[
        0
    ]
    for n in range(1, limit + 1):
        assert _call(client, key_id, n).status_code == 200
    r = _call(client, key_id, limit + 1)
    assert r.status_code == 402 and r.json()["code"] == "insufficient_credits"
    assert r.json()["paywall"]["reason"] == "credits" and r.json()["paywall"]["free_path"]
    assert _used(system_conn, key_id) == limit


def test_two_parallel_calls_cannot_overspend(client, system_conn):
    key_id = _attest(client)
    limit = system_conn.execute("SELECT monthly_credits FROM plans WHERE code = 'free'").fetchone()[
        0
    ]
    system_conn.execute(
        "INSERT INTO guest_allowances (key_id, period_key, credits_used) VALUES (%s, to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'), %s)",
        (key_id, limit - 1),
    )
    with ThreadPoolExecutor(2) as pool:
        codes = sorted(pool.map(lambda n: _call(client, key_id, n).status_code, (10, 11)))
    assert codes in ([200, 401], [200, 402])
    assert _used(system_conn, key_id) == limit


def test_a_new_month_starts_a_new_allowance_row(client, system_conn):
    key_id = _attest(client)
    system_conn.execute(
        "INSERT INTO guest_allowances (key_id, period_key, credits_used) VALUES (%s, to_char((now() AT TIME ZONE 'UTC') - interval '1 month', 'YYYY-MM'), 12)",
        (key_id,),
    )
    assert _call(client, key_id, 1).status_code == 200
    assert (
        system_conn.execute(
            "SELECT count(*) FROM guest_allowances WHERE key_id = %s", (key_id,)
        ).fetchone()[0]
        == 2
    )


def test_an_unusable_output_refunds_the_allowance(client, system_conn, monkeypatch):
    from hermi.modules.ai import client as ai_client

    class Bad:
        name = "fake"

        async def single_call(self, req):
            from hermi.modules.ai.metering import Usage
            from hermi.providers.ai import ProviderResult

            return ProviderResult(
                provider="fake",
                model=req.model,
                content=[{"type": "text", "text": "not json"}],
                stop_reason="end_turn",
                usage=Usage(),
                cost_usd_micros=0,
            )

    monkeypatch.setattr(ai_client, "provider_for", lambda settings, spec, user_email=None: Bad())
    key_id = _attest(client)
    r = _call(client, key_id, 1, idem="idem-bbbbbbbb")
    assert r.status_code == 502 and r.json()["code"] == "ai_failed"
    assert _used(system_conn, key_id) == 0
    monkeypatch.undo()
    assert (
        _call(client, key_id, 2, idem="idem-bbbbbbbb").status_code == 200
    )  # the key was released with the refund


@pytest.mark.parametrize("switch", ["ai.all", "ai.draft", "ai.free_tier"])
def test_a_kill_switch_stops_guest_ai_before_any_spend(client, system_conn, switch):
    from hermi.modules.admin.flags import FlagRuntime, Snapshot, Switch

    key_id = _attest(client)
    client.app.state.flags = FlagRuntime(
        lambda: Snapshot(flags={"guest_mode": GUEST_ON}, switches={switch: Switch(switch, True)}),
        ttl=0,
    )
    r = _call(client, key_id, 1)
    assert r.status_code == 503
    assert _used(system_conn, key_id) == 0
    assert (
        system_conn.execute(
            "SELECT counter FROM device_attestations WHERE key_id = %s", (key_id,)
        ).fetchone()[0]
        == 0
    )


def test_input_is_validated_and_clipped(client, system_conn):
    key_id = _attest(client)
    assert _call(client, key_id, 1, body={"destination": ""}).status_code == 422
    assert _call(client, key_id, 2, body={"destination": "Lisbon", "extra": 1}).status_code == 422
    assert _used(system_conn, key_id) == 0


def test_the_live_verifier_rejects_malformed_input_and_needs_the_apple_root():
    v = attest.AppleVerifier("ABCDE12345", "world.hermi.ios")
    from hermi.config import NotConfigured

    with pytest.raises(NotConfigured):
        v.verify_attestation(key_id="a", attestation="AA==", nonce="n")
    for junk in (
        "",
        "not base64!",
        "AA==",
        "oWFhYQ==",
    ):  # empty, bad base64, truncated, a map without the signature
        with pytest.raises(attest.AttestError):
            v.verify_assertion(
                key_id="a", public_key=b"\x04" + bytes(64), assertion=junk, client_data=b"x"
            )


def test_live_mode_without_the_app_identity_is_not_configured(db_urls):
    from hermi.config import NotConfigured

    s = _settings(db_urls, providers_mode="live", environment="local")
    with pytest.raises(NotConfigured):
        attest.verifier_for(s)


def test_guest_mode_off_turns_all_three_routes_off(client, system_conn):
    key_id = _attest(client)
    off = Flag("guest_mode", "boolean", False, 100, {}, {})
    client.app.state.flags = FlagRuntime(lambda: Snapshot(flags={"guest_mode": off}), ttl=0)
    assert client.post("/v1/devices/attest/challenge").status_code == 503
    r = client.post("/v1/devices/attest", json={"key_id": "k9", "attestation": "x", "nonce": "n"})
    assert r.status_code == 503 and r.json()["code"] == "feature_disabled"
    assert _call(client, key_id, 1).status_code == 503
    assert _used(system_conn, key_id) == 0


def test_production_refuses_a_development_attestation_key():
    from types import SimpleNamespace

    def settings(environment):
        return SimpleNamespace(
            providers_mode="live",
            apple_team_id="ABCDE12345",
            apple_bundle_id="world.hermi.ios",
            environment=environment,
        )

    assert attest.verifier_for(settings("production")).allow_development is False
    assert attest.verifier_for(settings("staging")).allow_development is True
