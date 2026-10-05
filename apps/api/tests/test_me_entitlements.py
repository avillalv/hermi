# ruff: noqa: E501  (long SQL strings)
"""WF-023.2: GET /v1/me/entitlements, the paywall trigger table and the per-tier limit table (04 sections 2.2 and 5.19, 07 sections 6.2 and 6.5)."""

import json
import re
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.modules.billing import paywall
from hermi.security.jwt import mint_dev_token

SHARED = Path(__file__).resolve().parents[3] / "packages" / "shared" / "src" / "entitlements.ts"
TIERS = ("free", "plus", "trip_pass")


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
    )
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client):
    sub = uuid.uuid4().hex
    h = {
        "Authorization": "Bearer "
        + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")
    }
    r = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h
    )
    assert r.status_code == 201
    return h, uuid.UUID(r.json()["id"])


def _trip(client, h):
    r = client.post("/v1/trips", json={"name": "T"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _plan_limits(system_conn, code):
    return system_conn.execute("SELECT limits FROM plans WHERE code = %s", (code,)).fetchone()[0]


def test_requires_a_token(client):
    assert client.get("/v1/me/entitlements").status_code == 401


def test_free_user_shape(client):
    h, _ = _user(client)
    r = client.get("/v1/me/entitlements", headers=h)
    assert r.status_code == 200, r.text
    e = r.json()
    assert (e["tier"], e["source"], e["status"], e["product_id"], e["valid_until"]) == (
        "free",
        "none",
        "none",
        None,
        None,
    )
    assert e["usage"] == {"active_trips": 0}
    assert e["trip_passes"] == []
    assert e["credits"]["total"] >= 0 and e["credits"]["blocked"] is False
    assert r.headers["ETag"]
    assert (
        client.get(
            "/v1/me/entitlements", headers={**h, "If-None-Match": r.headers["ETag"]}
        ).status_code
        == 304
    )


@pytest.mark.parametrize("tier", ["free", "plus"])
def test_every_limit_key_per_tier_matches_the_plans_seed(client, system_conn, tier):
    h, uid = _user(client)
    system_conn.execute("UPDATE entitlements SET tier_code = %s WHERE user_id = %s", (tier, uid))
    e = client.get("/v1/me/entitlements", headers=h).json()
    assert e["tier"] == tier
    assert e["limits"] == _plan_limits(system_conn, tier)  # every key, no constants in code


def test_usage_counts_active_trips_and_a_lapsed_plus_is_free(client, system_conn):
    h, uid = _user(client)
    _trip(client, h)
    system_conn.execute(
        "UPDATE entitlements SET tier_code = 'plus', source = 'subscription', valid_until = now() - interval '1 day' WHERE user_id = %s",
        (uid,),
    )
    e = client.get("/v1/me/entitlements", headers=h).json()
    assert (e["tier"], e["usage"]["active_trips"]) == ("free", 1)


def test_active_pass_is_listed_and_does_not_change_the_account_tier(client, system_conn):
    h, uid = _user(client)
    t = _trip(client, h)
    system_conn.execute(
        "INSERT INTO trip_passes (trip_id, purchaser_user_id, plan_code, starts_at, expires_at) VALUES (%s, %s, 'trip_pass', now() - interval '1 day', now() + interval '89 days')",
        (t["id"], uid),
    )
    e = client.get("/v1/me/entitlements", headers=h).json()
    assert e["tier"] == "free"
    (p,) = e["trip_passes"]
    assert (
        p["trip_id"],
        p["status"],
        p["source"],
        p["live_checks_left"],
        p["collaborators_max"],
    ) == (t["id"], "active", "purchase", 60, 6)


def test_invitee_sees_only_their_own_tier(client, system_conn):
    ho, owner = _user(client)
    hi, invitee = _user(client)
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus' WHERE user_id = %s", (owner,))
    t = _trip(client, ho)
    system_conn.execute(
        "INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'editor')",
        (t["id"], invitee),
    )
    e = client.get("/v1/me/entitlements", headers=hi).json()
    assert (e["tier"], e["usage"]["active_trips"], e["trip_passes"]) == (
        "free",
        0,
        [],
    )  # the owner's tier applies on that trip only


def test_agent_flag_follows_the_tier(client, system_conn):
    h, uid = _user(client)
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus' WHERE user_id = %s", (uid,))
    f = client.get("/v1/me/entitlements", headers=h).json()["flags"]
    assert f["agent_runs"] is True and f["taster_available"] is False


# 07 section 6.2: the API reason of each trigger
REASONS = {
    "third_trip": "trip_limit",
    "second_route": "live_routes",
    "track_live": "live_routes",
    "alert_limit": "live_routes",
    "invite": "sharing",
    "out_of_credits_draft": "credits",
    "out_of_credits_research": "credits",
    "out_of_credits_agent": "credits",
    "out_of_credits_verify": "credits",
    "export_footer": "export_footer",
    "ninth_stay": "ninth_stay",
    "lifecycle_14d": "lifecycle_14d",
}


def test_trigger_table_covers_every_trigger_with_its_reason_and_free_path():
    assert set(paywall.TRIGGERS) == set(REASONS)
    for code, trig in paywall.TRIGGERS.items():
        assert trig.reason == REASONS[code]
        assert trig.free_path and not re.search("[\\u2013\\u2014]", trig.free_path)


def test_mute_caps_follow_07_6_5():
    t = paywall.TRIGGERS
    assert (paywall.VIEWS_PER_WEEK, paywall.MUTE_AFTER_DISMISSALS) == (3, 3)
    for code in ("third_trip", "second_route", "alert_limit", "ninth_stay", "invite", "track_live"):
        assert (t[code].counts_toward_cap, t[code].mute_days, t[code].long_mute_days) == (
            True,
            7,
            30,
        )
    assert (
        t["export_footer"].counts_toward_cap,
        t["export_footer"].mute_days,
        t["export_footer"].long_mute_days,
    ) == (False, 30, 30)
    assert (
        t["lifecycle_14d"].counts_toward_cap,
        t["lifecycle_14d"].cooldown_days,
        t["lifecycle_14d"].mute_days,
    ) == (False, 14, 30)
    assert t["ninth_stay"].per_trip_days == 7
    assert t["lifecycle_14d"].modal is False and t["export_footer"].modal is False


def test_tier_table_and_triggers_mirror_the_shared_package(system_conn):
    src = SHARED.read_text(encoding="utf-8")
    block = re.search(r"BEGIN TIER_LIMITS\n(.*?)\n// END TIER_LIMITS", src, re.S).group(1)
    table = json.loads(block.removeprefix("export const TIER_LIMITS = ").removesuffix(";"))
    for tier in TIERS:
        assert table[tier] == _plan_limits(system_conn, tier), tier
    assert set(re.findall(r"^  ([a-z_0-9]+): rule\(", src, re.M)) == set(paywall.TRIGGERS)
