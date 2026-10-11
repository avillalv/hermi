# ruff: noqa: E501, F811
"""WF-056.2 usage reconciliation (Anthropic cost report vs ai_usage) and the 08 section 10 alert rules.

The rules aggregate whole tables, so the fixture empties content_reports, referral_rewards, trip_imports, ai_usage and the job
queue and moves today's sign-ups back 3 days. That is impractical to narrow to this module's rows; run this module serially
(the suite does) and not beside tests that read those tables."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from tests.test_scheduler import sys_session  # noqa: F401

from hermi.config import Settings
from hermi.modules.ai import reconcile


class Alerts(list):
    def __call__(self, severity, key, message):
        self.append((severity, key))


class Fetch:
    def __init__(self, micros=None, error=None):
        self.micros, self.error, self.days = micros, error, []

    def __call__(self, day):
        self.days.append(day)
        if self.error:
            raise self.error
        return self.micros


@pytest.fixture
def env(system_conn, db_urls, sys_session):
    for t in ("ai_usage", "procrastinate_events", "procrastinate_jobs", "content_reports", "referral_rewards", "trip_imports"):
        system_conn.execute(f"DELETE FROM {t}")
    system_conn.execute("UPDATE kill_switches SET engaged = false, engaged_by = NULL, engaged_at = NULL, expires_at = NULL, reason = NULL")

    def settings(provider="anthropic_api", key="sk-admin-test"):
        return Settings(_env_file=None, database_url_system=db_urls["system"], ai_provider=provider, anthropic_admin_api_key=key)

    # audit_log is append-only and a reconcile alert is once per day for ever, so each test reconciles its own old day.
    day = (datetime.now(UTC) - timedelta(days=2 + uuid.uuid4().int % 20000)).date()
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=UTC) + timedelta(days=1)

    def run(fetch, **kw):
        alert = Alerts()
        out = reconcile.reconcile(sys_session, kw.pop("settings", None) or settings(), fetch=fetch, alert=alert, now=noon)
        sys_session.commit()
        return out, alert

    scope = uuid.uuid4().hex  # audit_log is append-only: a fresh dedupe scope per test

    def rules(only=""):
        """(out, alerts of the rules whose key starts with `only`)"""
        alert = Alerts()
        out = reconcile.evaluate_rules(sys_session, settings(), alert=alert, scope=scope)
        sys_session.commit()
        return out, [a for a in alert if a[1].startswith(only)]

    return system_conn, run, rules, settings, day


def _usage(conn, micros, *, day, provider="anthropic_api", user_id=None, hours=12):
    at = datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(hours=hours)
    conn.execute(
        "INSERT INTO ai_usage (action, provider, cost_usd_micros, user_id, idempotency_key, created_at) "
        "VALUES ('explain', %s, %s, %s, gen_random_uuid()::text, %s)",
        (provider, micros, user_id, at),
    )


def _audit_count(conn, entity_id):
    return conn.execute(
        "SELECT count(*) FROM audit_log WHERE entity_type = 'alert' AND actor_type = 'system' AND entity_id LIKE %s", (entity_id + "%",)
    ).fetchone()[0]


# --- reconciliation ---------------------------------------------------------------------------------------------------


def test_gap_under_three_percent_is_silent(env):
    conn, run, _, _, day = env
    _usage(conn, 100_000_000, day=day)
    out, alerts = run(Fetch(102_000_000))
    assert alerts == [] and out["alerted"] is False
    assert (out["anthropic_micros"], out["ai_usage_micros"]) == (102_000_000, 100_000_000)
    assert 0.019 < out["gap"] < 0.021
    assert _audit_count(conn, f"usage_reconcile:{day}") == 0


def test_five_percent_gap_alerts_once_and_audits_as_system(env):
    conn, run, _, _, day = env
    _usage(conn, 100_000_000, day=day)
    fetch = Fetch(105_000_000)
    out, alerts = run(fetch)
    assert alerts == [("notify", f"usage_reconcile:{day}")] and out["alerted"] is True
    assert fetch.days == [day]
    assert _audit_count(conn, f"usage_reconcile:{day}") == 1
    out2, alerts2 = run(fetch)  # rerun: nothing new
    assert alerts2 == [] and _audit_count(conn, f"usage_reconcile:{day}") == 1
    assert out2["gap"] == out["gap"]


def test_cli_and_fake_rows_are_not_metered_spend(env):
    conn, run, _, _, day = env
    _usage(conn, 100_000_000, day=day)
    _usage(conn, 900_000_000, day=day, provider="claude_cli")
    out, alerts = run(Fetch(100_000_000))
    assert alerts == [] and out["ai_usage_micros"] == 100_000_000


@pytest.mark.parametrize("provider", ["claude_cli", "fake"])
def test_skipped_for_non_metered_providers(env, provider):
    _, run, _, settings, _ = env
    fetch = Fetch(1)
    out, alerts = run(fetch, settings=settings(provider=provider))
    assert out == {"skipped": "provider"} and alerts == [] and fetch.days == []


@pytest.mark.parametrize("key", [None, ""])
def test_skipped_without_the_key(env, key):
    _, run, _, settings, _ = env
    fetch = Fetch(1)
    out, alerts = run(fetch, settings=settings(key=key))
    assert out == {"skipped": "no_key"} and alerts == [] and fetch.days == []


def test_fetch_failure_neither_raises_nor_alerts(env):
    conn, run, _, _, day = env
    _usage(conn, 100_000_000, day=day)
    out, alerts = run(Fetch(error=RuntimeError("boom")))
    assert out == {"skipped": "fetch_failed"} and alerts == [] and _audit_count(conn, f"usage_reconcile:{day}") == 0
    assert _audit_count(conn, f"usage_reconcile_fetch:{day}") == 0


def test_a_refused_admin_key_alerts_once_per_day(env):
    conn, run, _, _, day = env
    req = httpx.Request("GET", reconcile.COST_URL)
    err = httpx.HTTPStatusError("401", request=req, response=httpx.Response(401, request=req))
    out, alerts = run(Fetch(error=err))
    assert out["skipped"] == "fetch_failed" and alerts == [("notify", f"usage_reconcile_fetch:{day}")]
    out2, alerts2 = run(Fetch(error=err))
    assert alerts2 == [] and _audit_count(conn, f"usage_reconcile_fetch:{day}") == 1
    err5 = httpx.HTTPStatusError("503", request=req, response=httpx.Response(503, request=req))
    assert run(Fetch(error=err5))[1] == []  # a server error only logs


def test_make_fetcher_pages_and_sums():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if "page" not in request.url.params:
            return httpx.Response(200, json={"data": [{"results": [{"amount": "100"}]}], "has_more": True, "next_page": "p2"})
        return httpx.Response(200, json={"data": [{"results": [{"amount": "50.5"}]}], "has_more": False, "next_page": None})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    total = reconcile.make_fetcher("sk-admin-x", client=client)(datetime(2026, 10, 10, tzinfo=UTC).date())
    assert total == 150.5 * 10_000
    assert len(seen) == 2 and seen[1].url.params["page"] == "p2"
    first = seen[0]
    assert first.url.path == "/v1/organizations/cost_report"
    assert first.url.params["starting_at"] == "2026-10-10T00:00:00Z"
    assert first.url.params["ending_at"] == "2026-10-11T00:00:00Z"
    assert first.url.params["bucket_width"] == "1d"
    assert first.headers["x-api-key"] == "sk-admin-x" and first.headers["anthropic-version"] == "2023-06-01"


def test_both_zero_is_no_gap(env):
    _, run, _, _, _ = env
    out, alerts = run(Fetch(0))
    assert out["gap"] == 0 and alerts == []


def test_cost_report_amounts_are_cents_as_strings():
    body = {"data": [{"results": [{"amount": "12.5"}, {"amount": "0.5"}]}, {"results": [{"amount": "100"}]}]}
    assert reconcile.cost_micros(body) == 113 * 10_000


# --- alert rules ------------------------------------------------------------------------------------------------------


def _trip(conn, user_id):
    return conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (user_id,)).fetchone()[0]


def _run(conn, user_id, *, status="succeeded", started="0 minutes", turns=1, cost=0):
    trip = _trip(conn, user_id)
    return conn.execute(
        "INSERT INTO runs (trip_id, user_id, kind, action, status, started_at, finished_at, turns_used, cost_usd_micros) "
        "VALUES (%s, %s, 'explain', 'explain', %s, now() - %s::interval, CASE WHEN %s IN ('queued', 'running') THEN NULL ELSE now() END, %s, %s) RETURNING id",
        (trip, user_id, status, started, status, turns, cost),
    ).fetchone()[0]


def _import(conn, user_id, *, status="applied", error_code=None, reward=False, ago="0 minutes"):
    conn.execute(
        "INSERT INTO trip_imports (user_id, source, status, error_code, created_at, completed_at, reward_granted_at) "
        "VALUES (%s, 'ics_file', %s, %s, now() - %s::interval, CASE WHEN %s = 'applied' THEN now() END, CASE WHEN %s THEN now() END)",
        (user_id, status, error_code, ago, status, reward),
    )


def test_account_over_daily_ceiling_by_more_than_ten_percent_pages(env, make_user):
    conn, _, rules, _, _ = env
    ceiling = int(conn.execute("SELECT (limits ->> 'daily_ceiling_micros')::bigint FROM plans WHERE code = 'free'").fetchone()[0])
    over, edge = make_user()[0], make_user()[0]
    today = datetime.now(UTC).date()
    _usage(conn, ceiling * 111 // 100, day=today, user_id=over, hours=0)
    _usage(conn, ceiling * 110 // 100, day=today, user_id=edge, hours=0)
    out, alerts = rules("account_over_ceiling")
    assert alerts == [("page", f"account_over_ceiling:{over}")]
    assert out["fired"].count(f"account_over_ceiling:{over}") == 1
    assert _audit_count(conn, f"account_over_ceiling:{over}") == 1
    out2, alerts2 = rules("account_over_ceiling")  # still over a minute later: one page, not one per minute
    assert alerts2 == [] and _audit_count(conn, f"account_over_ceiling:{over}") == 1


def test_queue_oldest_job_over_ten_minutes_pages(env):
    conn, _, rules, _, _ = env
    q = "q_" + uuid.uuid4().hex[:8]  # a lane name no earlier test has fired for within the hour
    ins = "INSERT INTO procrastinate_jobs (queue_name, task_name, status, scheduled_at) VALUES (%s, 'x', 'todo', now() - %s::interval)"
    conn.execute(ins, (q, "9 minutes"))
    assert rules("queue_oldest_job")[1] == []
    conn.execute(ins, (q, "11 minutes"))
    assert rules("queue_oldest_job")[1] == [("page", f"queue_oldest_job:{q}")]
    assert rules("queue_oldest_job")[1] == []


def test_future_scheduled_job_is_not_waiting(env):
    conn, _, rules, _, _ = env
    conn.execute("INSERT INTO procrastinate_jobs (queue_name, task_name, status, scheduled_at) VALUES ('api', 'x', 'todo', now() + interval '1 hour')")
    assert rules("queue_oldest_job")[1] == []


def test_kill_switch_expiring_within_15_minutes_is_info(env):
    conn, _, rules, _, _ = env
    key = "test_exp_" + uuid.uuid4().hex[:8]
    conn.execute(
        "INSERT INTO kill_switches (key, engaged, reason, engaged_at, expires_at) VALUES (%s, true, 'x', now() - interval '1 hour', now() + interval '20 minutes')",
        (key,),
    )
    assert rules("kill_switch_expiring")[1] == []
    conn.execute("UPDATE kill_switches SET expires_at = now() + interval '10 minutes' WHERE key = %s", (key,))
    assert rules("kill_switch_expiring")[1] == [("info", f"kill_switch_expiring:{key}")]
    assert rules("kill_switch_expiring")[1] == []


def test_run_limit_turns_cost_and_time(env, make_user):
    conn, _, rules, _, _ = env
    uid = make_user()[0]
    stop = int(conn.execute("SELECT hard_stop_micros FROM credit_action_prices WHERE action = 'explain'").fetchone()[0])
    ok = _run(conn, uid, turns=20, cost=stop)  # at the edge: silent
    fine = _run(conn, uid, status="running", started="7 minutes")
    turns = _run(conn, uid, turns=21)
    spend = _run(conn, uid, cost=stop + 1)
    slow = _run(conn, uid, status="running", started="9 minutes")
    out, alerts = rules("run_limit")
    keys = {k for _, k in alerts}
    assert {f"run_limit:{x}" for x in (turns, spend, slow)} <= keys
    assert not keys & {f"run_limit:{x}" for x in (ok, fine)}
    assert all(sev == "page" for sev, _ in alerts)
    assert rules("run_limit")[1] == []  # one page per run per cooldown


def test_moderation_report_older_than_12_hours_notifies(env, make_user):
    conn, _, rules, _, _ = env
    run = _run(conn, make_user()[0])
    rep = "INSERT INTO content_reports (target_type, run_id, reason, created_at) VALUES ('ai_answer', %s, 'spam', now() - %s::interval)"
    conn.execute(rep, (run, "11 hours"))
    assert rules("moderation_report_age")[1] == []
    conn.execute(rep, (run, "13 hours"))
    assert rules("moderation_report_age")[1] == [("notify", "moderation_report_age:open")]
    assert rules("moderation_report_age")[1] == []


def test_import_failure_share_above_20_percent_with_a_minimum_sample(env, make_user):
    conn, _, rules, _, _ = env
    uid = make_user()[0]
    for _ in range(3):  # 3 of 3 failed: under the sample size, silent
        _import(conn, uid, status="failed", error_code="provider_error")
    assert rules("import_failure_rate")[1] == []
    for _ in range(8):
        _import(conn, uid, status="review")
    for _ in range(2):
        _import(conn, uid, status="failed", error_code="provider_error", ago="2 hours")  # outside the hour
    assert rules("import_failure_rate")[1] == [("notify", "import_failure_rate:hour")]  # 3 of 11 is over 20 percent
    assert rules("import_failure_rate")[1] == []


def test_import_failure_share_at_20_percent_is_silent(env, make_user):
    conn, _, rules, _, _ = env
    uid = make_user()[0]
    for _ in range(2):
        _import(conn, uid, status="failed", error_code="nothing_found")
    for _ in range(8):
        _import(conn, uid, status="review")
    assert rules("import_failure_rate")[1] == []  # exactly 2 of 10


def test_more_than_20_blocked_fetches_an_hour_from_one_account(env, make_user):
    conn, _, rules, _, _ = env
    heavy, edge = make_user()[0], make_user()[0]
    for _ in range(21):
        _import(conn, heavy, status="failed", error_code="blocked_source")
    for _ in range(20):
        _import(conn, edge, status="failed", error_code="blocked_source")
    for _ in range(5):
        _import(conn, edge, status="failed", error_code="blocked_source", ago="3 hours")
    assert rules("blocked_fetches")[1] == [("notify", f"blocked_fetches:{heavy}")]
    assert rules("blocked_fetches")[1] == []


def test_more_than_5_redemptions_of_one_code_in_24_hours(env, make_user):
    conn, _, rules, _, _ = env
    referrer = make_user()[0]
    ins = "INSERT INTO referral_rewards (code, referrer_user_id, referee_user_id, created_at) VALUES (%s, %s, %s, now() - %s::interval)"
    for _ in range(5):
        conn.execute(ins, ("ABCDEFGH", referrer, make_user()[0], "1 hour"))
    conn.execute(ins, ("ABCDEFGH", referrer, make_user()[0], "30 hours"))  # outside the window
    assert rules("referral_code_redemptions")[1] == []
    conn.execute(ins, ("ABCDEFGH", referrer, make_user()[0], "2 hours"))
    assert rules("referral_code_redemptions")[1] == [("notify", "referral_code_redemptions:ABCDEFGH")]
    assert rules("referral_code_redemptions")[1] == []


def test_import_reward_passes_above_5_percent_of_todays_signups(env, make_user):
    conn, _, rules, _, _ = env
    conn.execute("UPDATE users SET created_at = created_at - interval '3 days' WHERE created_at >= date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'")
    assert rules("import_reward_farming")[1] == []  # no sign-ups today: nothing to divide by
    _import(conn, make_user()[0], reward=True)  # 1 of 1
    for _ in range(19):
        make_user()
    assert rules("import_reward_farming")[1] == []  # 1 of 20 is exactly 5 percent
    _import(conn, make_user()[0], reward=True)  # 2 of 21
    assert rules("import_reward_farming")[1] == [("notify", "import_reward_farming:day")]
    assert rules("import_reward_farming")[1] == []


def test_alerts_go_out_after_the_rule_closes_its_savepoint(env, sys_session, monkeypatch):
    seen = []

    def find(session, settings, now):
        return [("s", "m")]

    monkeypatch.setattr(reconcile, "RULES", (reconcile.Rule("one", "info", find),))
    reconcile.evaluate_rules(sys_session, env[3](), alert=lambda *a: seen.append(sys_session.in_nested_transaction()), scope=uuid.uuid4().hex)
    sys_session.commit()
    assert seen == [False]


def test_referral_credits_granted_in_a_day_above_1000(env, make_user):
    conn, _, rules, _, _ = env
    referrer = make_user()[0]
    ins = (
        "INSERT INTO referral_rewards (code, referrer_user_id, referee_user_id, status, referrer_credits, referee_credits, referrer_capped, granted_at) "
        "VALUES ('ZZZZZZZZ', %s, %s, 'granted', %s, %s, %s, now())"
    )
    conn.execute(ins, (referrer, make_user()[0], 600, 300, False))  # 900
    conn.execute(ins, (referrer, make_user()[0], 500, 100, True))  # referee only: 1000 in all
    assert rules("referral_credits_daily")[1] == []
    conn.execute(ins, (referrer, make_user()[0], 1, 0, False))  # 1001
    assert rules("referral_credits_daily")[1] == [("notify", "referral_credits_daily:day")]
    assert rules("referral_credits_daily")[1] == []


def test_a_fired_alert_fires_again_after_the_hour(env, sys_session):
    conn, _, _, settings, _ = env
    q = "q_" + uuid.uuid4().hex[:8]
    conn.execute("INSERT INTO procrastinate_jobs (queue_name, task_name, status, scheduled_at) VALUES (%s, 'x', 'todo', now() - interval '20 minutes')", (q,))
    scope, got = uuid.uuid4().hex, []
    now = datetime.now(UTC)

    def go(at):
        reconcile.evaluate_rules(sys_session, settings(), now=at, alert=lambda s, k, m: got.append(k), scope=scope, group="health")
        sys_session.commit()

    go(now)
    go(now + timedelta(minutes=30))
    assert got.count(f"queue_oldest_job:{q}") == 1
    go(now + timedelta(minutes=61))
    assert got.count(f"queue_oldest_job:{q}") == 2


def _research_rows(conn, run, hits, misses, ago="1 hour"):
    ins = (
        "INSERT INTO ai_usage (action, run_id, cache_hit, state, settled_at, idempotency_key, created_at) "
        "VALUES ('research', %s, %s, 'settled', now(), gen_random_uuid()::text, now() - %s::interval)"
    )
    for hit, n in ((True, hits), (False, misses)):
        for _ in range(n):
            conn.execute(ins, (run, hit, ago))


def _cache_run(conn, user_id):
    run = _run(conn, user_id)
    conn.execute("UPDATE runs SET cache_key = repeat('a', 64) WHERE id = %s", (run,))
    return run


def test_cache_hit_rate_down_more_than_20_points_notifies(env, make_user):
    conn, _, rules, _, _ = env
    run = _cache_run(conn, make_user()[0])
    _research_rows(conn, run, 40, 10, ago="3 days")  # 80 percent before
    _research_rows(conn, run, 12, 8, ago="1 hour")  # 60 percent in the last day: a 20 point drop is not more than 20
    assert rules("cache_hit_drop")[1] == []
    _research_rows(conn, run, 0, 1, ago="2 hours")  # 12 of 21 is 57 percent
    assert rules("cache_hit_drop")[1] == [("notify", "cache_hit_drop:day")]
    assert rules("cache_hit_drop")[1] == []


def test_cache_hit_rate_silent_below_the_minimum_sample(env, make_user):
    conn, _, rules, _, _ = env
    run = _cache_run(conn, make_user()[0])
    _research_rows(conn, run, 40, 10, ago="3 days")
    _research_rows(conn, run, 0, 19, ago="1 hour")  # 0 percent, but 19 runs is under the sample size
    assert rules("cache_hit_drop")[1] == []


def _tokens(conn, read, write, inp, ago="10 minutes", provider="anthropic_api"):
    conn.execute(
        "INSERT INTO ai_usage (action, provider, cache_read_tokens, cache_write_tokens, input_tokens, idempotency_key, created_at) "
        "VALUES ('explain', %s, %s, %s, %s, gen_random_uuid()::text, now() - %s::interval)",
        (provider, read, write, inp, ago),
    )


def test_prompt_cache_read_ratio_under_70_percent_notifies(env):
    conn, _, rules, _, _ = env
    _tokens(conn, 7_000, 1_000, 2_000)  # exactly 70 percent: silent
    assert rules("prompt_cache_ratio")[1] == []
    _tokens(conn, 0, 100, 100)  # 7000 of 10200
    assert rules("prompt_cache_ratio")[1] == [("notify", "prompt_cache_ratio:hour")]
    assert rules("prompt_cache_ratio")[1] == []


def test_prompt_cache_ratio_silent_below_the_minimum_and_ignores_other_rows(env):
    conn, _, rules, _, _ = env
    assert rules("prompt_cache_ratio")[1] == []  # no rows: zero denominator
    _tokens(conn, 0, 5_000, 4_000)  # 9,000 tokens is under the sample size
    _tokens(conn, 0, 50_000, 50_000, provider="claude_cli")  # notional, not counted
    _tokens(conn, 0, 50_000, 50_000, ago="2 hours")  # outside the hour
    assert rules("prompt_cache_ratio")[1] == []


def test_rule_groups_split_health_from_business(env):
    groups = {r.id: r.group for r in reconcile.RULES}
    assert {k for k, g in groups.items() if g == "health"} == {"account_over_ceiling", "queue_oldest_job", "kill_switch_expiring", "run_limit"}
    assert {k for k, g in groups.items() if g == "business"} == {
        "moderation_report_age", "import_failure_rate", "blocked_fetches", "referral_code_redemptions", "referral_credits_daily", "import_reward_farming",
        "cache_hit_drop", "prompt_cache_ratio",
    }


def test_a_rule_that_errors_is_skipped_not_fatal(env, monkeypatch):
    _, _, rules, _, _ = env

    def boom(session, settings, now):
        raise RuntimeError("table missing")

    monkeypatch.setattr(reconcile, "RULES", (reconcile.Rule("broken", "page", boom), *reconcile.RULES))
    out, alerts = rules()
    assert out["errors"] == ["broken"]
