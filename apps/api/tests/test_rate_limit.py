# ruff: noqa: E501  (long lines)
"""WF-028: Postgres buckets with a fake clock, limits from the setting_rate_limits row, route classes, signup velocity and disposable email."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.db import open_app_engine
from hermi.errors import ApiError
from hermi.main import create_app
from hermi.security import rate_limit as rl
from hermi.security.jwt import mint_dev_token


@pytest.fixture(autouse=True)
def _real_limits():
    rl.TEST_LIMITS = {}  # runs after conftest's hook: this module tests the real limits
    yield


def _settings(db_urls, **kw):
    return Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
        **kw,
    )


def _set_row(system_conn, rules):
    system_conn.execute(
        "UPDATE feature_flags SET rules = %s::jsonb WHERE key = 'setting_rate_limits'",
        (json.dumps(rules),),
    )
    rl.reset_cache()


@pytest.fixture
def engine(db_urls):
    e = open_app_engine(_settings(db_urls))
    yield e
    e.dispose()


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_seed_row_mirrors_the_built_in_limits(system_conn):
    rules = system_conn.execute(
        "SELECT rules FROM feature_flags WHERE key = 'setting_rate_limits'"
    ).fetchone()[0]
    assert rules == {k: v[0] for k, v in rl.ROUTE_CLASSES.items()}


def test_bucket_allows_the_limit_then_429_with_retry_after_and_resets_next_window(
    engine, system_conn
):
    _set_row(system_conn, {"ai": 10})
    clock, key = Clock(), uuid.uuid4().hex
    for _ in range(10):
        rl.hit(engine, "ai", key, clock=clock)
    with pytest.raises(ApiError) as e:
        rl.hit(engine, "ai", key, clock=clock)
    assert e.value.status == 429 and e.value.code == "rate_limited"
    assert 1 <= int(e.value.headers["Retry-After"]) <= 3600
    rl.hit(engine, "ai", uuid.uuid4().hex, clock=clock)  # another account is untouched
    clock.t += 3601
    rl.hit(engine, "ai", key, clock=clock)  # next window


def test_retry_after_counts_to_the_window_end(engine):
    clock, key = Clock(1_800_000_000.0 - 1_800_000_000.0 % 86400 + 86390), uuid.uuid4().hex
    rl.hit(engine, "export", key, clock=clock)  # 1 a day
    with pytest.raises(ApiError) as e:
        rl.hit(engine, "export", key, clock=clock)
    assert e.value.headers["Retry-After"] == "10"


def test_changing_the_row_changes_the_limit_with_no_restart(engine, system_conn, monkeypatch):
    monkeypatch.setattr(
        rl, "CACHE_TTL", 0
    )  # the cache would otherwise hold the old value for up to 30 seconds
    clock, key = Clock(), uuid.uuid4().hex
    _set_row(system_conn, {"outbound": 1})
    rl.hit(engine, "outbound", key, clock=clock)
    with pytest.raises(ApiError):
        rl.hit(engine, "outbound", key, clock=clock)
    system_conn.execute(
        "UPDATE feature_flags SET rules = '{\"outbound\": 5}' WHERE key = 'setting_rate_limits'"
    )
    rl.hit(engine, "outbound", key, clock=clock)  # same engine, same process
    system_conn.execute(
        "UPDATE feature_flags SET rules = '[1]' WHERE key = 'setting_rate_limits'"
    )  # malformed: built-in 60
    for _ in range(10):
        rl.hit(engine, "outbound", key, clock=clock)


def test_limits_fall_back_to_built_ins_and_a_new_class_is_one_entry(monkeypatch):
    assert (
        rl.limit_for("ai") == (30, 3600)
        and rl.limit_for("outbound") == (60, 3600)
        and rl.limit_for("places_search") == (30, 60)
    )
    assert (
        rl.limit_for("ai", {"ai": 3}) == (3, 3600)
        and rl.limit_for("ai", {"ai": "x"}) == (30, 3600)
        and rl.limit_for("ai", {"ai": True}) == (30, 3600)
    )
    assert rl.limit_for("export") == (1, 86400) and rl.limit_for("delete") == (1, 86400)
    monkeypatch.setitem(rl.ROUTE_CLASSES, "demo", (7, 30))
    assert rl.limit_for("demo") == (7, 30)
    with pytest.raises(KeyError):
        rl.limit_for("nope")


def test_rate_limited_dependency_over_http(db_urls, system_conn):
    _set_row(system_conn, {})  # earlier tests leave rows behind
    settings = _settings(db_urls)
    app = create_app(settings)
    # a route guarded by the dependency, added to the real app so auth and error handlers are the real ones
    app.add_api_route("/v1/throwaway", lambda: {"ok": True}, dependencies=[rl.rate_limited("ai")])
    with TestClient(app, raise_server_exceptions=False) as c:

        def user():
            sub = uuid.uuid4().hex
            h = {
                "Authorization": "Bearer "
                + mint_dev_token(settings, sub, email=f"{sub[:12]}@example.com")
            }
            assert (
                c.post("/v1/me/bootstrap", json={"age_confirmed": True}, headers=h).status_code
                == 201
            )
            return h

        a, b = user(), user()
        for _ in range(30):
            assert c.get("/v1/throwaway", headers=a).status_code == 200
        r = c.get("/v1/throwaway", headers=a)
        assert (
            r.status_code == 429
            and r.json()["code"] == "rate_limited"
            and r.json()["status"] == 429
        )
        assert (
            r.headers["content-type"].startswith("application/problem+json")
            and int(r.headers["Retry-After"]) > 0
        )
        assert c.get("/v1/throwaway", headers=b).status_code == 200
        assert c.get("/v1/throwaway").status_code == 401


def test_disposable_email_domains_and_subdomains():
    assert rl.is_disposable("a@mailinator.com") and rl.is_disposable("a@x.Mailinator.com")
    assert not rl.is_disposable("a@gmail.com") and not rl.is_disposable(
        "a@privaterelay.appleid.com"
    )


@pytest.fixture
def client(db_urls, system_conn):
    system_conn.execute(
        "DELETE FROM rate_limit_counters"
    )  # earlier tests signed users up from the same test-client IP
    _set_row(system_conn, {"signup_ip": 2})
    with TestClient(create_app(_settings(db_urls)), raise_server_exceptions=False) as c:
        yield c


def _h(client, email=None):
    sub = uuid.uuid4().hex
    return {
        "Authorization": "Bearer "
        + mint_dev_token(client.app.state.settings, sub, email=email or f"{sub[:12]}@example.com")
    }


def test_signup_velocity_blocks_the_third_new_account_from_one_ip_but_not_sign_ins(client):
    body = {"age_confirmed": True}
    first = _h(client)
    assert client.post("/v1/me/bootstrap", json=body, headers=first).status_code == 201
    assert client.post("/v1/me/bootstrap", json=body, headers=_h(client)).status_code == 201
    r = client.post("/v1/me/bootstrap", json=body, headers=_h(client))
    assert (
        r.status_code == 429
        and r.json()["code"] == "rate_limited"
        and int(r.headers["Retry-After"]) > 0
    )
    assert (
        client.post("/v1/me/bootstrap", json=body, headers=first).status_code == 200
    )  # existing account


def test_disposable_email_cannot_sign_up(client):
    r = client.post(
        "/v1/me/bootstrap", json={"age_confirmed": True}, headers=_h(client, "x@mailinator.com")
    )
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"


def _shared_token(client):
    from tests.test_share_links_api import _link, _token, _trip

    sub = uuid.uuid4().hex
    h = {
        "Authorization": "Bearer "
        + mint_dev_token(client.app.state.settings, sub, email=f"{sub[:12]}@example.com")
    }
    assert (
        client.post(
            "/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h
        ).status_code
        == 201
    )
    return _token(_link(client, h, _trip(client, h)))


def test_shared_trip_is_limited_per_token_then_429(client, system_conn):
    _set_row(system_conn, {"signup_ip": 100000, "share_view": 3})
    t = _shared_token(client)
    for _ in range(3):
        assert client.get(f"/v1/shared/{t}").status_code == 200
    r = client.get(f"/v1/shared/{t}")
    assert (
        r.status_code == 429
        and r.json()["code"] == "rate_limited"
        and int(r.headers["Retry-After"]) > 0
    )
    assert (
        client.get(f"/v1/shared/{_shared_token(client)}").status_code == 200
    )  # another token is fine


def test_shared_trip_is_limited_per_ip_when_the_token_is_under_its_limit(client, system_conn):
    _set_row(system_conn, {"signup_ip": 100000, "share_view_ip": 2})
    t = _shared_token(client)
    assert client.get(f"/v1/shared/{t}").status_code == 200
    assert client.get(f"/v1/shared/{t}").status_code == 200
    r = client.get(f"/v1/shared/{t}")
    assert (
        r.status_code == 429 and r.json()["code"] == "rate_limited" and "Retry-After" in r.headers
    )
