# ruff: noqa: E501
"""WF-043: price constants, cost from response.usage, and metering writes (06 section 6).

Costs are checked against hand calculations, in micro-dollars (USD * 1e6).
"""

import dataclasses
import uuid
from datetime import date
from types import SimpleNamespace as NS

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hermi import db
from hermi.modules.ai import metering, pricing
from hermi.modules.ai.metering import (
    MeterContext,
    Usage,
    cost_usd_micros,
    record_provider_spend,
    record_usage,
)

SONNET, HAIKU = "claude-sonnet-5-5", "claude-haiku-4-5"

# (name, model, usage, batch, hand-calculated micro-dollars)
CASES = [
    # 10,000 in * $2/M = 20,000; 1,000 out * $10/M = 10,000
    ("plain sonnet", SONNET, Usage(input_tokens=10_000, output_tokens=1_000), False, 30_000),
    # 100,000 read * $0.20/M = 20,000; 5,000 in = 10,000; 2,000 out = 20,000
    ("sonnet cache read", SONNET, Usage(input_tokens=5_000, output_tokens=2_000, cache_read_tokens=100_000), False, 50_000),
    # 40,000 5m write * 2.5 = 100,000; 10,000 1h write * 4 = 40,000; 3,000 out * 10 = 30,000; 2 searches = 20,000
    (
        "sonnet writes and searches", SONNET,
        Usage(output_tokens=3_000, cache_write_5m_tokens=40_000, cache_write_1h_tokens=10_000, web_searches=2),
        False, 190_000,
    ),
    # haiku: 20,000 in * 1 = 20,000; 4,000 out * 5 = 20,000; 8,000 5m write * 1.25 = 10,000; 50,000 read * 0.1 = 5,000; 1 search
    (
        "haiku mixed", HAIKU,
        Usage(input_tokens=20_000, output_tokens=4_000, cache_write_5m_tokens=8_000, cache_read_tokens=50_000, web_searches=1),
        False, 65_000,
    ),
    # batch: tokens (20,000 + 10,000) halved = 15,000; 3 searches stay 30,000
    ("batch halves tokens only", SONNET, Usage(input_tokens=10_000, output_tokens=1_000, web_searches=3), True, 45_000),
]


@pytest.mark.parametrize(("name", "model", "usage", "batch", "expected"), CASES, ids=[c[0] for c in CASES])
def test_cost_matches_hand_calculation(name, model, usage, batch, expected):
    assert cost_usd_micros(usage, model, batch) == expected


def test_batch_is_exactly_half_of_the_token_cost():
    u = Usage(input_tokens=123_456, output_tokens=7_890, cache_read_tokens=44_444)
    assert cost_usd_micros(u, SONNET, True) * 2 in {cost_usd_micros(u, SONNET) + d for d in (-1, 0, 1)}


def test_usage_from_response_reads_sdk_shape_and_dicts():
    r = NS(
        input_tokens=1, output_tokens=2, cache_read_input_tokens=3,
        cache_creation=NS(ephemeral_5m_input_tokens=4, ephemeral_1h_input_tokens=5),
        server_tool_use=NS(web_search_requests=6),
    )
    want = Usage(1, 2, 3, 4, 5, 6)
    assert metering.usage_from_response(r) == want
    flat = {"input_tokens": 1, "output_tokens": 2, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 4}
    assert metering.usage_from_response(flat) == Usage(1, 2, 3, 4, 0, 0)


def test_unknown_model_is_an_error_not_free():
    with pytest.raises(LookupError):
        cost_usd_micros(Usage(input_tokens=1), "claude-unknown")


def test_cli_cost_is_total_cost_usd_times_a_million():
    assert metering.cli_cost_micros(0.123456) == 123_456


def test_price_versions_are_ordered_unique_and_frozen():
    dates = [v.effective_from for v in pricing.PRICE_VERSIONS]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    assert len({v.version for v in pricing.PRICE_VERSIONS}) == len(dates)
    with pytest.raises(dataclasses.FrozenInstanceError):
        pricing.PRICE_VERSIONS[0].web_search_micros = 1  # type: ignore[misc]
    with pytest.raises(LookupError):
        pricing.price_version(date(2000, 1, 1))
    # Version 1 as published in 06 section 6.1: a new version is added, this one is never edited.
    v1 = pricing.PRICE_VERSIONS[0]
    assert v1.models[SONNET] == pricing.ModelPrice(2_000_000, 2_500_000, 4_000_000, 200_000, 10_000_000)
    assert v1.models[HAIKU] == pricing.ModelPrice(1_000_000, 1_250_000, 2_000_000, 100_000, 5_000_000)
    assert v1.web_search_micros == 10_000


def test_an_older_date_uses_the_older_version(monkeypatch):
    newer = dataclasses.replace(pricing.PRICE_VERSIONS[0], version="next", effective_from=date(2099, 1, 1), web_search_micros=20_000)
    monkeypatch.setattr(pricing, "PRICE_VERSIONS", (*pricing.PRICE_VERSIONS, newer))
    u = Usage(web_searches=1)
    assert cost_usd_micros(u, SONNET, on=date(2030, 1, 1)) == 10_000
    assert cost_usd_micros(u, SONNET, on=date(2099, 1, 1)) == 20_000


# --- database -----------------------------------------------------------------------------------------------------


@pytest.fixture
def worker_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["system"]))
    yield e
    e.dispose()


def _trip_run(system_conn, user, provider="anthropic_api"):
    trip = system_conn.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'T', 'USD') RETURNING id", (user,)
    ).fetchone()[0]
    run = system_conn.execute(
        "INSERT INTO runs (trip_id, user_id, kind, provider) VALUES (%s, %s, 'explain', %s) RETURNING id", (trip, user, provider)
    ).fetchone()[0]
    return trip, run


def _ctx(user, trip, run, **kw):
    base = dict(action="explain", idempotency_key=f"{user}:{uuid.uuid4()}", model=SONNET, user_id=user, trip_id=trip, run_id=run)
    return MeterContext(**(base | kw))


def test_record_usage_sums_responses_into_one_row_and_one_event_each(worker_engine, system_conn, make_user):
    user, _ = make_user()
    trip, run = _trip_run(system_conn, user)
    ctx = _ctx(user, trip, run)
    with Session(worker_engine) as s, s.begin():
        c1 = record_usage(s, ctx, Usage(input_tokens=10_000, output_tokens=1_000), request_id="msg_1", turn=1, stop_reason="tool_use")
        c2 = record_usage(
            s, ctx, Usage(output_tokens=3_000, cache_write_5m_tokens=40_000, cache_write_1h_tokens=10_000, web_searches=2),
            request_id="msg_2", turn=2, stop_reason="end_turn",
        )
    assert (c1, c2) == (30_000, 190_000)
    row = system_conn.execute(
        "SELECT cost_usd_micros, input_tokens, output_tokens, cache_write_tokens, web_searches, provider, via_batch FROM ai_usage WHERE idempotency_key = %s",
        (ctx.idempotency_key,),
    ).fetchone()
    assert row == (220_000, 10_000, 4_000, 50_000, 2, "anthropic_api", False)
    assert system_conn.execute("SELECT cost_usd_micros, provider FROM runs WHERE id = %s", (run,)).fetchone() == (220_000, "anthropic_api")
    events = system_conn.execute(
        "SELECT seq, type, payload->>'kind', payload->>'request_id', (payload->>'cost_usd_micros')::int FROM run_events WHERE run_id = %s ORDER BY seq",
        (run,),
    ).fetchall()
    assert events == [(1, "info", "usage", "msg_1", 30_000), (2, "info", "usage", "msg_2", 190_000)]


def test_batch_row_is_flagged_and_halved(worker_engine, system_conn, make_user):
    user, _ = make_user()
    trip, run = _trip_run(system_conn, user)
    ctx = _ctx(user, trip, run, via_batch=True)
    with Session(worker_engine) as s, s.begin():
        record_usage(s, ctx, Usage(input_tokens=10_000, output_tokens=1_000, web_searches=3))
    assert system_conn.execute(
        "SELECT cost_usd_micros, via_batch FROM ai_usage WHERE idempotency_key = %s", (ctx.idempotency_key,)
    ).fetchone() == (45_000, True)


def test_fake_and_cli_providers_record_provider_and_cost(worker_engine, system_conn, make_user):
    user, _ = make_user()
    trip, run = _trip_run(system_conn, user, "fake")
    fake = _ctx(user, trip, run, provider="fake", model="fake")
    trip2, run2 = _trip_run(system_conn, user, "claude_cli")
    cli = _ctx(user, trip2, run2, provider="claude_cli", model="claude-sonnet-5-5")
    with Session(worker_engine) as s, s.begin():
        assert record_usage(s, fake, Usage(input_tokens=500, output_tokens=50)) == 0
        assert record_usage(s, cli, Usage(), cost_micros=metering.cli_cost_micros(0.25)) == 250_000
    got = system_conn.execute(
        "SELECT provider, cost_usd_micros FROM ai_usage WHERE idempotency_key = ANY(%s) ORDER BY cost_usd_micros",
        ([fake.idempotency_key, cli.idempotency_key],),
    ).fetchall()
    assert got == [("fake", 0), ("claude_cli", 250_000)]
    assert system_conn.execute("SELECT cost_usd_micros FROM runs WHERE id = %s", (run2,)).fetchone()[0] == 250_000


def test_usage_row_is_rolled_back_when_the_event_insert_fails(worker_engine, system_conn, make_user, monkeypatch):
    user, _ = make_user()
    trip, run = _trip_run(system_conn, user)
    ctx = _ctx(user, trip, run)
    bad = metering.text("INSERT INTO run_events (run_id, trip_id, seq, type, summary) VALUES (:run_id, :trip_id, :seq, 'bogus', 'x')")
    monkeypatch.setattr(metering, "_INSERT_EVENT", bad)
    with pytest.raises(Exception):  # noqa: B017  the check constraint on run_events.type
        with Session(worker_engine) as s, s.begin():
            record_usage(s, ctx, Usage(input_tokens=1_000, output_tokens=100))
    assert system_conn.execute("SELECT count(*) FROM ai_usage WHERE idempotency_key = %s", (ctx.idempotency_key,)).fetchone()[0] == 0
    assert system_conn.execute("SELECT cost_usd_micros FROM runs WHERE id = %s", (run,)).fetchone()[0] == 0
    assert system_conn.execute("SELECT count(*) FROM run_events WHERE run_id = %s", (run,)).fetchone()[0] == 0


def test_provider_calls_record_serpapi_and_geoapify_spend_with_account_and_trip(worker_engine, system_conn, make_user):
    user, _ = make_user()
    trip, _run = _trip_run(system_conn, user)
    with Session(worker_engine) as s, s.begin():
        serp = record_provider_spend(s, "serpapi", "google_flights", user_id=user, trip_id=trip)
        geo = record_provider_spend(s, "geoapify", "geocode/search", units=3, user_id=user, trip_id=trip)
        failed = record_provider_spend(s, "serpapi", "google_flights", ok=False, user_id=user, trip_id=trip)
        cached = record_provider_spend(s, "geoapify", "geocode/search", cached=True, cache_layer="db", user_id=user, trip_id=trip)
    assert (serp, geo, failed, cached) == (15_000, 1_500, None, None)
    rows = system_conn.execute(
        "SELECT provider, cost_usd_micros, user_id, trip_id, ok FROM provider_calls WHERE user_id = %s ORDER BY id", (user,)
    ).fetchall()
    assert rows == [("serpapi", 15_000, user, trip, True), ("geoapify", 1_500, user, trip, True), ("serpapi", None, user, trip, False), ("geoapify", None, user, trip, True)]


def test_claude_cli_without_an_explicit_cost_is_refused(worker_engine, system_conn, make_user):
    user, _ = make_user()
    trip, run = _trip_run(system_conn, user, "claude_cli")
    ctx = _ctx(user, trip, run, provider="claude_cli")
    with pytest.raises(ValueError, match="cost_micros"):
        with Session(worker_engine) as s, s.begin():
            record_usage(s, ctx, Usage(input_tokens=1))
    assert system_conn.execute("SELECT count(*) FROM ai_usage WHERE idempotency_key = %s", (ctx.idempotency_key,)).fetchone()[0] == 0
