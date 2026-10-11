# ruff: noqa: E501, F811
"""WF-056.1 global breakers: thresholds, surge, SerpApi quota, half-open probe, audit as system, idempotency, fail closed."""

from datetime import UTC, datetime, timedelta

import pytest
from tests.test_scheduler import sys_session  # noqa: F401

from hermi.config import Settings
from hermi.modules.admin.flags import engage_switch
from hermi.modules.ai import breakers

KEYS = ("ai.free_tier", "ai.all_but_paid", "ai.batch", "provider.serpapi", "provider.anthropic")
BUDGET = 100_000_000  # $100 in micro-dollars


class Alerts(list):
    def __call__(self, severity, key, message):
        self.append((severity, key))


@pytest.fixture
def env(system_conn, db_urls, sys_session):
    system_conn.execute("DELETE FROM ai_usage")
    system_conn.execute("DELETE FROM provider_calls")
    system_conn.execute(
        "UPDATE kill_switches SET engaged = false, engaged_by = NULL, engaged_at = NULL, expires_at = NULL, reason = NULL WHERE key = ANY(%s)",
        (list(KEYS),),
    )
    system_conn.execute("UPDATE feature_flags SET rules = '{\"usd\":150}' WHERE key = 'setting_ai_global_daily_usd'")
    system_conn.execute("UPDATE feature_flags SET rules = '{\"searches\":5000}' WHERE key = 'setting_serpapi_monthly_quota'")
    settings = Settings(_env_file=None, database_url_system=db_urls["system"], ai_global_daily_cap_usd=100, serpapi_monthly_cap=100)

    def run(now=None, alert=None):
        alert = Alerts() if alert is None else alert
        out = breakers.evaluate(sys_session, settings, now=now, alert=alert)
        sys_session.commit()
        return out, alert

    return system_conn, run, settings


def _spend(conn, micros, ago=timedelta(0)):
    conn.execute(
        "INSERT INTO ai_usage (action, cost_usd_micros, idempotency_key, created_at) VALUES ('explain', %s, gen_random_uuid()::text, now() - %s)",
        (micros, ago),
    )


def _engaged(conn, key):
    return conn.execute("SELECT engaged FROM kill_switches WHERE key = %s", (key,)).fetchone()[0]


def _audit(conn, key):
    return conn.execute(
        "SELECT actor_type, action FROM audit_log WHERE entity_type = 'kill_switch' AND entity_id = %s ORDER BY id", (key,)
    ).fetchall()


@pytest.mark.parametrize(
    ("pct", "free", "paid"),
    [(79, False, False), (80, True, False), (94, True, False), (95, True, True)],
)
def test_thresholds(env, pct, free, paid):
    conn, run, _ = env
    _spend(conn, BUDGET * pct // 100)
    run()
    assert (_engaged(conn, "ai.free_tier"), _engaged(conn, "ai.all_but_paid")) == (free, paid)


def test_boundary_just_under_80_percent(env):
    conn, run, _ = env
    _spend(conn, BUDGET * 80 // 100 - 1)
    run()
    assert not _engaged(conn, "ai.free_tier")


def test_surge_trips_the_right_breaker_and_pages(env):
    conn, run, _ = env
    _spend(conn, 80_000_000)
    out, alerts = run()
    assert out["engaged"] == ["ai.free_tier"] and alerts == [("notify", "ai.free_tier")]
    _spend(conn, 15_000_000)
    out, alerts = run()
    assert out["engaged"] == ["ai.all_but_paid"] and alerts == [("page", "ai.all_but_paid")]


def test_breaker_rows_are_audited_as_system_and_engage_is_idempotent(env):
    conn, run, _ = env
    base = _audit(conn, "ai.free_tier")
    _spend(conn, 85_000_000)
    run()
    first = _audit(conn, "ai.free_tier")
    assert first[len(base):] == [("system", "killswitch.engage")]
    out, alerts = run()
    assert out["engaged"] == [] and alerts == [] and _audit(conn, "ai.free_tier") == first


def test_release_on_new_utc_day_clears_only_auto_switches(env, sys_session):
    conn, run, _ = env
    _spend(conn, 96_000_000)
    run()
    # an admin engages ai.batch by hand; the breaker must never clear it
    engage_switch(sys_session, "ai.batch", actor_type="admin", reason="manual", expires_at=datetime.now(UTC) + timedelta(hours=2))
    sys_session.commit()
    tomorrow = datetime.now(UTC) + timedelta(days=1)
    out, _ = run(now=tomorrow)
    assert sorted(out["released"]) == ["ai.all_but_paid", "ai.free_tier"]
    assert not _engaged(conn, "ai.free_tier") and not _engaged(conn, "ai.all_but_paid") and _engaged(conn, "ai.batch")
    assert ("system", "killswitch.clear") in _audit(conn, "ai.free_tier")


def test_admin_engaged_breaker_key_is_not_taken_over_or_released(env, sys_session):
    conn, run, _ = env
    engage_switch(sys_session, "ai.free_tier", actor_type="admin", reason="manual", expires_at=datetime.now(UTC) + timedelta(hours=2))
    sys_session.commit()
    _spend(conn, 85_000_000)
    out, alerts = run()
    assert out["engaged"] == [] and alerts == []
    run(now=datetime.now(UTC) + timedelta(days=1))
    assert _engaged(conn, "ai.free_tier")


def test_fail_closed_when_spend_cannot_be_read(env, monkeypatch):
    conn, run, _ = env

    def boom(*a, **k):
        raise RuntimeError("view down")

    monkeypatch.setattr(breakers, "_spend", boom)
    out, alerts = run()
    assert set(out["engaged"]) == {"ai.free_tier", "ai.all_but_paid"} and ("page", "ai.all_but_paid") in alerts


def test_serpapi_quota_90_percent_turns_live_search_off_and_pages(env):
    conn, run, _ = env  # cap is 100 in this fixture
    for _ in range(89):
        conn.execute("INSERT INTO provider_calls (provider, endpoint, ok) VALUES ('serpapi', 'search', true)")
    run()
    assert not _engaged(conn, "provider.serpapi")
    conn.execute("INSERT INTO provider_calls (provider, endpoint, ok) VALUES ('serpapi', 'search', true)")
    out, alerts = run()
    assert out["engaged"] == ["provider.serpapi"] and alerts == [("page", "provider.serpapi")]
    assert ("system", "killswitch.engage") in _audit(conn, "provider.serpapi")


def test_spend_above_1_5x_the_7_day_mean_pauses_batch(env):
    conn, run, _ = env
    for d in range(1, 8):
        _spend(conn, 10_000_000, ago=timedelta(days=d))
    _spend(conn, 14_000_000)
    run(now=datetime.now(UTC))
    assert not _engaged(conn, "ai.batch")
    _spend(conn, 3_000_000)  # 17M > 1.5 x the prior mean
    _, alerts = run(now=datetime.now(UTC))
    assert _engaged(conn, "ai.batch") and ("page", "ai.batch") in alerts


def test_pure_helpers():
    assert breakers.reached(79, 100, 80) is False and breakers.reached(80, 100, 80) is True
    assert breakers.reached(0, 0, 80) is True  # no budget: fail closed
    assert breakers.surged(16, [10] * 7) and not breakers.surged(15, [10] * 7) and not breakers.surged(5, [])


def _calls(conn, ok_n, bad_n, at, status=429):
    for _ in range(ok_n):
        conn.execute("INSERT INTO provider_calls (provider, endpoint, ok, status_code, created_at) VALUES ('anthropic', 'm', true, 200, %s)", (at,))
    for _ in range(bad_n):
        conn.execute("INSERT INTO provider_calls (provider, endpoint, ok, status_code, created_at) VALUES ('anthropic', 'm', false, %s, %s)", (status, at))


def _backdate(conn, key="provider.anthropic", seconds=120):
    conn.execute("UPDATE kill_switches SET engaged_at = now() - make_interval(secs => %s) WHERE key = %s", (seconds, key))


def _claim(conn):
    return conn.execute(
        "UPDATE kill_switches SET engaged_at = now(), reason = %s WHERE key = 'provider.anthropic' AND engaged AND engaged_by IS NULL "
        "AND reason LIKE 'auto:%%' AND engaged_at <= now() - interval '60 seconds' RETURNING key",
        (breakers.PROBING,),
    ).fetchone()


def test_zero_budget_engages_both_ai_switches(env, db_urls, sys_session):
    conn, _, _ = env
    zero = Settings(_env_file=None, database_url_system=db_urls["system"], ai_global_daily_cap_usd=0)
    breakers.evaluate(sys_session, zero, alert=Alerts())
    sys_session.commit()
    assert _engaged(conn, "ai.free_tier") and _engaged(conn, "ai.all_but_paid")


def test_half_open_probe_cycle(env, sys_session):
    conn, run, _ = env
    t0 = datetime.now(UTC)
    _calls(conn, 4, 8, t0)
    out, alerts = run(now=t0)
    assert out["engaged"] == ["provider.anthropic"] and alerts == [("page", "provider.anthropic")]
    # open: cooldown not over, so no probe and nothing to judge
    assert breakers.probe_allowed(sys_session) is False
    assert breakers.claim_probe(sys_session) is False
    sys_session.commit()
    run(now=t0)
    assert _engaged(conn, "provider.anthropic")
    # after the cooldown exactly one probe claim wins
    _backdate(conn)
    assert breakers.probe_allowed(sys_session) is True
    assert breakers.claim_probe(sys_session) is True and breakers.claim_probe(sys_session) is False
    sys_session.commit()
    run()
    assert _engaged(conn, "provider.anthropic")  # claimed, not recorded yet
    # a failed probe (a 500) re-opens it
    _calls(conn, 0, 1, datetime.now(UTC), status=500)
    _, alerts = run()
    assert _engaged(conn, "provider.anthropic") and ("notify", "provider.anthropic") in alerts
    assert _claim(conn) is None  # cooldown restarted
    # a later successful probe closes it, and the old failures do not trip it again
    _backdate(conn)
    assert _claim(conn) is not None
    _calls(conn, 1, 0, datetime.now(UTC))
    out, _ = run()
    assert out["released"] == ["provider.anthropic"] and not _engaged(conn, "provider.anthropic")
    out, alerts = run()
    assert out["engaged"] == [] and not _engaged(conn, "provider.anthropic")


def test_a_user_400_never_reopens_the_probe_and_500s_and_null_status_trip(env, system_conn):
    conn, run, _ = env
    t0 = datetime.now(UTC)
    _calls(conn, 8, 0, t0)
    _calls(conn, 0, 6, t0, status=400)  # our own bad requests: not a provider failure
    out, _ = run(now=t0)
    assert out["engaged"] == []
    _calls(conn, 0, 3, t0, status=500)
    for _ in range(4):
        conn.execute("INSERT INTO provider_calls (provider, endpoint, ok, status_code, created_at) VALUES ('anthropic', 'm', false, NULL, %s)", (t0,))
    out, _ = run(now=t0)
    assert out["engaged"] == []  # 7 of 21 is under half: still closed
    _calls(conn, 0, 8, t0, status=500)
    out, _ = run(now=t0)
    assert out["engaged"] == ["provider.anthropic"]  # 15 of 29, over half
    _backdate(conn)
    assert _claim(conn) is not None
    _calls(conn, 0, 1, datetime.now(UTC), status=400)
    run()
    assert _engaged(conn, "provider.anthropic")
    assert conn.execute("SELECT reason FROM kill_switches WHERE key = 'provider.anthropic'").fetchone()[0] == breakers.PROBING  # not re-opened


def test_gate_blocks_while_open_and_admits_one_probe_then_a_success_closes(env, db_urls, sys_session):
    import threading

    from sqlalchemy import create_engine

    from hermi import db
    from hermi.errors import ApiError
    from hermi.modules.admin.flags import FlagRuntime, engine_loader

    conn, run, settings = env
    t0 = datetime.now(UTC)
    _calls(conn, 2, 10, t0)
    run(now=t0)
    assert _engaged(conn, "provider.anthropic")
    engine = create_engine(db.psycopg_url(db_urls["system"]))
    try:
        flags = FlagRuntime(engine_loader(engine), ttl=0)
        flags.settings = settings

        def gate():
            try:
                breakers.ensure_anthropic_allowed(flags, "ai.explain", tier="free")
                return True
            except ApiError as e:
                assert e.status == 503
                return False

        assert gate() is False  # open: cooldown not over
        _backdate(conn)
        results = []
        ts = [threading.Thread(target=lambda: results.append(gate())) for _ in range(2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        assert sorted(results) == [False, True]  # exactly one probe
        assert gate() is False  # and no second one inside the cooldown
        _calls(conn, 1, 0, datetime.now(UTC))
        run()
        assert not _engaged(conn, "provider.anthropic")
        assert gate() is True
    finally:
        engine.dispose()


def test_low_error_rate_only_notifies(env):
    conn, run, _ = env
    t0 = datetime.now(UTC)
    _calls(conn, 90, 8, t0)  # about 8 percent: above 5, under 50
    out, alerts = run(now=t0)
    assert out["engaged"] == [] and alerts == [("notify", "provider.anthropic")]
    assert not _engaged(conn, "provider.anthropic")


def test_real_gate_admits_the_probe_and_writes_a_probe_audit_row(env, db_urls, sys_session, make_user):
    from sqlalchemy import create_engine

    from hermi import db
    from hermi.errors import ApiError
    from hermi.modules.admin.flags import FlagRuntime, engine_loader
    from hermi.modules.ai.features import base, drafts

    conn, run, settings = env
    uid, _ = make_user()
    trip = conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (uid,)).fetchone()[0]
    conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', 'v1', true)", (uid,))
    t0 = datetime.now(UTC)
    _calls(conn, 2, 10, t0)
    run(now=t0)
    assert _engaged(conn, "provider.anthropic")
    before = [r for r in _audit(conn, "provider.anthropic") if r[1] == "killswitch.probe"]
    engine = create_engine(db.psycopg_url(db_urls["system"]))
    try:
        flags = FlagRuntime(engine_loader(engine), ttl=0)
        flags.settings = settings

        def gate():
            base.gate(sys_session, flags, drafts.DAY_SPEC, user_id=uid, trip_id=trip, provider="anthropic_api")

        with pytest.raises(ApiError):
            gate()  # open
        _backdate(conn)
        gate()  # half-open: the probe is admitted through the real gate
        with pytest.raises(ApiError):
            gate()  # one probe per cooldown
    finally:
        engine.dispose()
    after = [r for r in _audit(conn, "provider.anthropic") if r[1] == "killswitch.probe"]
    assert [r[0] for r in after[len(before):]] == ["system"]


def test_unauthenticated_guest_post_does_not_claim_the_probe(db_urls, system_conn):
    from fastapi.testclient import TestClient
    from tests.test_auth_provisioning import _settings

    from hermi.main import create_app

    system_conn.execute(
        "UPDATE kill_switches SET engaged = true, engaged_by = NULL, reason = 'auto: error rate', engaged_at = now() - interval '5 minutes' "
        "WHERE key = 'provider.anthropic'"
    )
    s = _settings(db_urls, ai_provider="anthropic_api")
    try:
        with TestClient(create_app(s), raise_server_exceptions=False) as c:
            before = system_conn.execute("SELECT reason, engaged_at FROM kill_switches WHERE key = 'provider.anthropic'").fetchone()
            for _ in range(2):
                r = c.post("/v1/guest/ai/draft-day", content=b"{}", headers={"Idempotency-Key": "idem-12345678"})
                assert r.status_code == 401, r.text
            after = system_conn.execute("SELECT reason, engaged_at FROM kill_switches WHERE key = 'provider.anthropic'").fetchone()
            assert after == before
    finally:
        system_conn.execute(
            "UPDATE kill_switches SET engaged = false, engaged_at = NULL, reason = NULL WHERE key = 'provider.anthropic'"
        )
