# ruff: noqa: E501
"""WF-048: the one-shot features (explain, packing list, draft day, draft trip) over the provider seam.

Rows are arranged with the system login; the actions run as the app login (RLS applies) against a stub provider that
replays the recorded responses in providers/ai/fixtures. No network and no real model."""

import json
import logging
import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from hermi import db
from hermi.config import Settings
from hermi.errors import ApiError
from hermi.main import create_app
from hermi.modules.admin.flags import FlagRuntime, Snapshot, Switch
from hermi.modules.ai import client as ai_client
from hermi.modules.ai.features import drafts, explain, packing_list
from hermi.modules.ai.features.redact import Redactor
from hermi.modules.ai.metering import Usage
from hermi.providers.ai import ProviderResult
from hermi.providers.ai.fake import FIXTURES
from hermi.security.jwt import mint_dev_token

START = 60  # the Plus monthly grant
HARD = {"explain": 10_000, "draft_day": 30_000, "draft_trip": 100_000}
OPEN = FlagRuntime(lambda: Snapshot(), ttl=0)


def engaged(*keys: str) -> FlagRuntime:
    return FlagRuntime(lambda: Snapshot(switches={k: Switch(k, True) for k in keys}), ttl=0)


class Stub:
    """A provider that replays a recorded response, with the cost, model, stop reason or text overridden."""

    def __init__(self, scenario, *, cost=0, model=None, stop=None, text=None, usage=None, name="fake"):
        self.name = name
        self.calls = []
        msg = json.loads((FIXTURES / f"{scenario}.json").read_text(encoding="utf-8"))
        self._r = ProviderResult(
            provider=name, model=model or msg["model"], content=[{"type": "text", "text": text if text is not None else msg["content"][0]["text"]}],
            stop_reason=stop or msg["stop_reason"], usage=usage or Usage(input_tokens=300, output_tokens=120), cost_usd_micros=cost,
        )

    async def single_call(self, req):
        self.calls.append(req)
        return self._r


@pytest.fixture
def engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]), pool_size=10, max_overflow=0)
    yield e
    e.dispose()


@pytest.fixture
def settings(db_urls):
    return Settings(_env_file=None, environment="ci", auth_mode="dev", providers_mode="fake", database_url=db_urls["app"], database_url_system=db_urls["system"], database_pool_size=10)


@pytest.fixture(autouse=True)
def _dispose_system_engines():
    yield
    db.dispose_system_engines()


def _grant(conn, uid):
    """The Plus monthly allowance. Billing writes it in the product; the Free one is lazy, so a Plus user needs it here."""
    conn.execute(
        "INSERT INTO credit_grants (user_id, kind, credits, remaining, period_key) VALUES (%s, 'monthly', %s, %s, to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM'))",
        (uid, START, START),
    )


@pytest.fixture
def world(system_conn, make_user):
    """A Plus owner (Free cannot afford a $0.10 draft against its $0.05 daily ceiling) with AI consent, a trip (2027-05-01 to 2027-05-05, Lisbon) with one named traveler and one saved place."""
    uid, _ = make_user()
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', '1', true)", (uid,))
    system_conn.execute("INSERT INTO entitlements (user_id, tier_code, source) VALUES (%s, 'plus', 'comp')", (uid,))
    _grant(system_conn, uid)
    tid = system_conn.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency, start_date, end_date) VALUES (%s, 'Trip', 'USD', '2027-05-01', '2027-05-05') RETURNING id", (uid,)
    ).fetchone()[0]
    system_conn.execute("INSERT INTO trip_destinations (trip_id, position, name, country, lat, lon) VALUES (%s, 0, 'Lisbon', 'Portugal', 38.7, -9.1)", (tid,))
    pid = system_conn.execute("INSERT INTO people (owner_user_id, name) VALUES (%s, 'Marguerite Dupont') RETURNING id", (uid,)).fetchone()[0]
    system_conn.execute("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (tid, pid))
    place = system_conn.execute(
        "INSERT INTO saved_places (trip_id, place_provider, place_id, name, category) VALUES (%s, 'manual', 'p1', 'Pasteis cafe', 'food') RETURNING id", (tid,)
    ).fetchone()[0]
    return {"uid": uid, "tid": tid, "place": str(place), "conn": system_conn}


def _make_member(conn, world, name):
    uid = conn.execute("INSERT INTO users (email, display_name) VALUES (%s, %s) RETURNING id", (f"{uuid.uuid4().hex[:10]}@example.com", name)).fetchone()[0]
    conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'editor')", (world["tid"], uid))
    return uid, name


def _kw(settings, world, **over):
    return {"settings": settings, "flags": OPEN, "user_id": world["uid"], "trip_id": world["tid"], "idempotency_key": uuid.uuid4().hex, **over}


def _run(engine, world, fn, **kw):
    with db.request_transaction(engine, world["uid"]) as s:
        return fn(s, **kw)


def _one(conn, sql, *a):
    return conn.execute(sql, a).fetchone()


def _balance(conn, uid):
    return conn.execute("SELECT coalesce(sum(remaining), 0) FROM credit_balances WHERE user_id = %s", (uid,)).fetchone()[0]


def _ledger(conn, uid):
    return conn.execute("SELECT count(*) FROM credit_ledger WHERE user_id = %s", (uid,)).fetchone()[0]


# ---- each action reserves, calls, meters and settles ----


def test_explain_reserves_calls_meters_settles(engine, settings, world):
    stub = Stub("feature_explain", cost=1_500, usage=Usage(input_tokens=300, output_tokens=40, cache_read_tokens=800))
    done = _run(engine, world, explain.execute, **_kw(settings, world, question="Is Alfama good for kids?", provider=stub))
    assert done.output["label"] == "AI suggestion, check details before booking"
    assert done.output["sources"] == [] and done.output["answer"]
    assert done.run_id  # the route returns it as run_id so thumbs can report this answer
    c = world["conn"]
    action, state, charged, cost, model, reserved = _one(
        c, "SELECT action::text, state::text, credits_charged, cost_usd_micros, model, credits_reserved FROM ai_usage WHERE user_id = %s", world["uid"]
    )
    assert (action, state, charged, cost, model, reserved) == ("explain", "settled", 1, 1_500, "claude-haiku-4-5", 1)
    kind, status, run_cost = _one(c, "SELECT kind::text, status::text, cost_usd_micros FROM runs WHERE id = %s", done.run_id)
    assert (kind, status, run_cost) == ("explain", "succeeded", 1_500)
    assert _balance(c, world["uid"]) == START - 1 and done.receipt.charged == 1 and done.receipt.balance_after == START - 1
    assert _one(c, "SELECT count(*) FROM run_events WHERE run_id = %s AND summary = 'usage'", done.run_id)[0] == 1


def test_packing_list_sends_placeholders_never_names(engine, settings, world):
    stub = Stub("feature_packing_list")
    prefs = "Marguerite wants a sun hat. Dupont is allergic to nuts. Call +1 415 555 0134 or marg@example.com."
    done = _run(engine, world, packing_list.execute, **_kw(settings, world, preferences=prefs, provider=stub))
    sent = json.dumps([stub.calls[0].system, stub.calls[0].messages])
    for secret in ("Marguerite", "Dupont", "marg@example.com", "415 555 0134"):
        assert secret not in sent
    assert "Traveler A" in sent and "[EMAIL_1]" in sent
    assert 18 <= len(done.output["items"]) <= 40
    assert {i["group"] for i in done.output["items"]} <= set(packing_list.GROUPS)
    # same price class as explain: one credit, action explain, run kind packing_list
    c = world["conn"]
    assert _one(c, "SELECT action::text, credits_charged FROM ai_usage WHERE user_id = %s", world["uid"]) == ("explain", 1)
    assert _one(c, "SELECT kind::text, action::text FROM runs WHERE id = %s", done.run_id) == ("packing_list", "explain")


def test_names_are_restored_in_the_result(engine, settings, world):
    out = {"groups": [{"name": "other", "items": [{"label": "Gift for Traveler A", "qty": None, "reason": None}]}]}
    done = _run(engine, world, packing_list.execute, **_kw(settings, world, provider=Stub("feature_packing_list", text=json.dumps(out))))
    assert done.output["items"][0]["label"] == "Gift for Marguerite Dupont"


def test_draft_day_shapes_items_and_binds_place_ids(engine, settings, world):
    out = json.loads((FIXTURES / "feature_draft_day.json").read_text(encoding="utf-8"))["content"][0]["text"]
    day = json.loads(out)
    day["items"][0]["place_id"] = world["place"]
    day["items"][0]["verify"] = False
    done = _run(engine, world, drafts.draft_day, **_kw(settings, world, day=date(2027, 5, 2), provider=Stub("feature_draft_day", text=json.dumps(day))))
    first = done.output["items"][0]
    assert first["saved_place_id"] == world["place"] and first["day"] == "2027-05-02" and first["start_time"] == "09:30" and first["end_time"] == "11:00"
    assert first["category"] == "sights" and first["source"] == "ai_draft" and first["verify"] is False
    assert done.output["items"][1]["verify"] is True  # a place not in the saved list is always "check hours"
    assert done.receipt.reserved == 1 and _one(world["conn"], "SELECT action::text FROM runs WHERE id = %s", done.run_id)[0] == "draft_day"


def test_draft_day_foreign_place_id_fails_closed(engine, settings, world):
    day = json.loads(json.loads((FIXTURES / "feature_draft_day.json").read_text(encoding="utf-8"))["content"][0]["text"])
    day["items"][0]["place_id"] = str(uuid.uuid4())
    with pytest.raises(ApiError) as e:
        _run(engine, world, drafts.draft_day, **_kw(settings, world, day=date(2027, 5, 2), provider=Stub("feature_draft_day", text=json.dumps(day))))
    assert (e.value.status, e.value.code) == (502, "ai_failed")
    assert _balance(world["conn"], world["uid"]) == START  # refunded in full


def test_draft_day_outside_trip_dates_is_422_and_free(engine, settings, world):
    with pytest.raises(ApiError) as e:
        _run(engine, world, drafts.draft_day, **_kw(settings, world, day=date(2027, 6, 1), provider=Stub("feature_draft_day")))
    assert e.value.status == 422 and _ledger(world["conn"], world["uid"]) == 0


def test_draft_trip_bills_four_and_block_is_checked(engine, settings, world):
    done = _run(engine, world, drafts.draft_trip, **_kw(settings, world, provider=Stub("feature_draft_trip")))
    assert done.receipt.reserved == 4 and done.receipt.charged == 4 and _balance(world["conn"], world["uid"]) == START - 4
    assert done.output["days"][0]["day"] == "2027-05-01" and done.output["label"]
    # a day outside the requested block is an invalid output
    bad = json.loads(json.loads((FIXTURES / "feature_draft_trip.json").read_text(encoding="utf-8"))["content"][0]["text"])
    bad["days"][0]["date"] = "2027-09-09"
    with pytest.raises(ApiError):
        _run(engine, world, drafts.draft_trip, **_kw(settings, world, preferences="other", provider=Stub("feature_draft_trip", text=json.dumps(bad))))
    assert _balance(world["conn"], world["uid"]) == START - 4


# ---- a repeat of the same request within 6 hours is free (01 F-AI-1, F-AI-2) ----


def test_an_identical_request_within_six_hours_is_free_and_skips_the_provider(engine, settings, world):
    stub = Stub("feature_explain")
    first = _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub))
    again = _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub))
    assert again.output == first.output and again.run_id == first.run_id
    assert (again.receipt.charged, again.receipt.reserved, again.receipt.from_cache) == (0, 0, True)
    assert again.receipt.public()["reservation_id"] is None
    assert len(stub.calls) == 1 and _balance(world["conn"], world["uid"]) == START - 1
    other = _run(engine, world, explain.execute, **_kw(settings, world, question="Why not?", provider=stub))
    assert other.receipt.charged == 1 and len(stub.calls) == 2


def test_a_draft_repeat_is_free_and_a_run_older_than_six_hours_is_charged(engine, settings, world):
    stub = Stub("feature_draft_day")
    first = _run(engine, world, drafts.draft_day, **_kw(settings, world, day=date(2027, 5, 2), provider=stub))
    again = _run(engine, world, drafts.draft_day, **_kw(settings, world, day=date(2027, 5, 2), provider=stub))
    assert again.output == first.output and again.receipt.charged == 0 and len(stub.calls) == 1
    world["conn"].execute("UPDATE runs SET finished_at = now() - interval '7 hours' WHERE id = %s", (first.run_id,))
    late = _run(engine, world, drafts.draft_day, **_kw(settings, world, day=date(2027, 5, 2), provider=stub))
    assert late.receipt.charged == 1 and len(stub.calls) == 2
    assert _balance(world["conn"], world["uid"]) == START - 2


def test_a_repeat_is_free_at_zero_credits(engine, settings, world):
    stub = Stub("feature_packing_list")
    _run(engine, world, packing_list.execute, **_kw(settings, world, provider=stub))
    world["conn"].execute("UPDATE credit_grants SET remaining = 0 WHERE user_id = %s", (world["uid"],))
    again = _run(engine, world, packing_list.execute, **_kw(settings, world, provider=stub))
    assert again.receipt.charged == 0 and again.receipt.balance_after == 0 and len(stub.calls) == 1


# ---- outputs fail validation closed, with a full refund ----


@pytest.mark.parametrize(
    "text",
    [
        "not json at all",
        json.dumps({"answer": "x", "confidence": "high"}),  # a required field missing
        json.dumps({"answer": "x", "confidence": "high", "needs_source_check": False, "extra": 1}),  # an unknown field
        json.dumps({"answer": "x" * 601, "confidence": "high", "needs_source_check": False}),  # over the length
        json.dumps({"answer": "Book at https://www.airbnb.com/rooms/1", "confidence": "high", "needs_source_check": False}),
        json.dumps({"answer": "Go https://example.com/go/abc123", "confidence": "high", "needs_source_check": False}),
    ],
)
def test_invalid_explain_output_fails_closed_and_refunds(engine, settings, world, text):
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain", text=text, cost=900)))
    assert (e.value.status, e.value.code) == (502, "ai_failed") and "Nothing was charged" in e.value.detail
    c = world["conn"]
    assert _balance(c, world["uid"]) == START
    state, charged, cost = _one(c, "SELECT state::text, credits_charged, cost_usd_micros FROM ai_usage WHERE user_id = %s", world["uid"])
    assert (state, charged, cost) == ("released", 0, 900)  # the real cost is still metered
    assert _one(c, "SELECT status::text, failure_code FROM runs WHERE user_id = %s", world["uid"]) == ("failed", "invalid_output")


def test_refusal_wrong_model_and_max_tokens_refund(engine, settings, world):
    for stub, code in (
        (Stub("feature_explain", stop="refusal"), "ai_refused"),
        (Stub("feature_explain", model="claude-opus-5-5"), "ai_failed"),
        (Stub("feature_explain", stop="max_tokens"), "ai_failed"),
    ):
        with pytest.raises(ApiError) as e:
            _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub))
        assert e.value.code == code
        assert _balance(world["conn"], world["uid"]) == START


def test_provider_error_refunds_and_logs_no_text(engine, settings, world, caplog):
    class Boom:
        name = "fake"

        async def single_call(self, req):
            raise RuntimeError("secret prompt text Marguerite")

    with caplog.at_level(logging.INFO), pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Boom()))
    assert e.value.code == "ai_failed" and _balance(world["conn"], world["uid"]) == START
    assert "Marguerite" not in caplog.text
    assert _one(world["conn"], "SELECT count(*) FROM ai_usage WHERE user_id = %s", world["uid"])[0] == 0


# ---- hard stops: $0.01, $0.03, $0.10 ----


def test_hard_stops_and_max_tokens_match_the_price_table_and_06(system_conn):
    rows = {a: h for a, h in system_conn.execute("SELECT action::text, hard_stop_micros FROM credit_action_prices WHERE action IN ('explain','draft_day','draft_trip')").fetchall()}
    assert rows == HARD
    assert (explain.SPEC.hard_stop_micros, packing_list.SPEC.hard_stop_micros, drafts.DAY_SPEC.hard_stop_micros, drafts.TRIP_SPEC.hard_stop_micros) == (10_000, 10_000, 30_000, 100_000)
    assert [s.call.max_tokens for s in (explain.SPEC, packing_list.SPEC, drafts.DAY_SPEC, drafts.TRIP_SPEC)] == [400, 900, 1500, 6000]
    assert [s.call.tier for s in (explain.SPEC, packing_list.SPEC, drafts.DAY_SPEC, drafts.TRIP_SPEC)] == ["fast", "fast", "main", "main"]
    assert (drafts.DAY_SPEC.call.effort, drafts.TRIP_SPEC.call.effort, explain.SPEC.call.effort) == ("low", "medium", None)


@pytest.mark.parametrize(
    ("which", "hard"),
    [("explain", 10_000), ("packing", 10_000), ("draft_day", 30_000), ("draft_trip", 100_000)],
)
def test_a_call_that_reaches_its_hard_stop_is_refunded(engine, settings, world, which, hard):
    def go(cost):  # the cost differs per call, and so does the input: an identical request would be a free repeat
        fn, kw, sc = {
            "explain": (explain.execute, {"question": f"Why {cost}?"}, "feature_explain"),
            "packing": (packing_list.execute, {"preferences": f"p{cost}"}, "feature_packing_list"),
            "draft_day": (drafts.draft_day, {"day": date(2027, 5, 2), "preferences": f"p{cost}"}, "feature_draft_day"),
            "draft_trip": (drafts.draft_trip, {"preferences": f"p{cost}"}, "feature_draft_trip"),
        }[which]
        return _run(engine, world, fn, **_kw(settings, world, provider=Stub(sc, cost=cost), **kw))

    ok = go(hard - 1)  # one micro under the stop is a normal call
    assert ok.receipt.charged > 0
    with pytest.raises(ApiError) as e:
        go(hard)
    assert e.value.code == "ai_failed"
    c = world["conn"]
    assert _one(c, "SELECT failure_code FROM runs WHERE user_id = %s ORDER BY created_at DESC LIMIT 1", world["uid"])[0] == "spend_limit"
    assert _balance(c, world["uid"]) == START - ok.receipt.charged  # only the first call stayed charged


@pytest.mark.parametrize(("action", "hard"), list(HARD.items()))
def test_admission_refuses_when_the_hard_stop_does_not_fit_the_month(engine, settings, world, action, hard):
    # Plus ceiling is $2.25 a month: spend that leaves one micro too little for this action's hard stop is refused.
    world["conn"].execute(
        "INSERT INTO ai_usage (user_id, trip_id, action, cost_usd_micros, state, idempotency_key, settled_at) VALUES (%s, %s, 'explain', %s, 'settled', %s, now())",
        (world["uid"], world["tid"], 2_250_000 - hard + 1, f"spend:{uuid.uuid4()}"),
    )
    fn, kw, sc = {
        "explain": (explain.execute, {"question": "Why?"}, "feature_explain"),
        "draft_day": (drafts.draft_day, {"day": date(2027, 5, 2)}, "feature_draft_day"),
        "draft_trip": (drafts.draft_trip, {}, "feature_draft_trip"),
    }[action]
    stub = Stub(sc)
    with pytest.raises(ApiError) as e:
        _run(engine, world, fn, **_kw(settings, world, provider=stub, **kw))
    assert (e.value.status, e.value.code) == (429, "provider_budget_exhausted")
    assert stub.calls == [] and _ledger(world["conn"], world["uid"]) == 0  # no call, no reservation


# ---- kill switches and the gate ----


@pytest.mark.parametrize("switch", ["ai.all", "ai.explain"])
def test_explain_kill_switches(engine, settings, world, switch):
    stub = Stub("feature_explain")
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub, flags=engaged(switch)))
    assert e.value.status == 503 and stub.calls == [] and _ledger(world["conn"], world["uid"]) == 0


@pytest.mark.parametrize("switch", ["ai.all", "ai.packing"])
def test_packing_kill_switches(engine, settings, world, switch):
    stub = Stub("feature_packing_list")
    with pytest.raises(ApiError) as e:
        _run(engine, world, packing_list.execute, **_kw(settings, world, provider=stub, flags=engaged(switch)))
    assert e.value.status == 503 and stub.calls == [] and _ledger(world["conn"], world["uid"]) == 0


@pytest.mark.parametrize("switch", ["ai.all", "ai.draft"])
def test_draft_kill_switches_cover_day_and_trip(engine, settings, world, switch):
    for fn, kw, sc in ((drafts.draft_day, {"day": date(2027, 5, 2)}, "feature_draft_day"), (drafts.draft_trip, {}, "feature_draft_trip")):
        stub = Stub(sc)
        with pytest.raises(ApiError) as e:
            _run(engine, world, fn, **_kw(settings, world, provider=stub, flags=engaged(switch), **kw))
        assert e.value.status == 503 and stub.calls == []
    assert _ledger(world["conn"], world["uid"]) == 0


def test_other_feature_switch_does_not_block(engine, settings, world):
    done = _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain"), flags=engaged("ai.draft", "ai.packing")))
    assert done.receipt.charged == 1


def test_provider_anthropic_switch_blocks_the_api_backend_only(engine, settings, world):
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain", name="anthropic_api"), flags=engaged("provider.anthropic")))
    assert e.value.status == 503


def test_unreadable_flags_fail_closed(engine, settings, world):
    def broken():
        raise RuntimeError("down")

    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain"), flags=FlagRuntime(broken, ttl=0)))
    assert e.value.status == 503


def test_consent_and_trip_toggle_are_checked(engine, settings, world):
    c = world["conn"]
    c.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', '1', false)", (world["uid"],))
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain")))
    assert (e.value.status, e.value.code) == (403, "ai_consent_required")
    c.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', '1', true)", (world["uid"],))
    c.execute("UPDATE trips SET ai_enabled = false WHERE id = %s", (world["tid"],))
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain")))
    assert (e.value.status, e.value.code) == (403, "ai_disabled_for_trip")
    assert _ledger(c, world["uid"]) == 0


def test_a_retry_with_the_same_key_never_charges_twice(engine, settings, world):
    key = uuid.uuid4().hex
    stub = Stub("feature_explain")
    _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub, idempotency_key=key))
    with pytest.raises(ApiError) as e:  # the HTTP layer replays a success; below it a settled key is refused
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub, idempotency_key=key))
    assert (e.value.status, e.value.code) == (409, "idempotency_key_reused")
    assert len(stub.calls) == 1 and _balance(world["conn"], world["uid"]) == START - 1


def test_retry_after_a_failed_call_does_not_call_the_provider_again(engine, settings, world):
    key = uuid.uuid4().hex
    c = world["conn"]
    stub = Stub("feature_explain", text="not json")
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub, idempotency_key=key))
    assert e.value.code == "ai_failed"
    with pytest.raises(ApiError) as e:  # the key was freed by the 5xx; the reservation is already refunded
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=stub, idempotency_key=key))
    assert (e.value.status, e.value.code) == (409, "idempotency_key_reused")
    assert len(stub.calls) == 1 and _balance(c, world["uid"]) == START
    assert _one(c, "SELECT count(*) FROM runs WHERE user_id = %s", world["uid"])[0] == 1
    assert _one(c, "SELECT count(*) FROM runs WHERE user_id = %s AND status = 'queued'", world["uid"])[0] == 0


def test_anthropic_api_without_a_key_is_503_and_reserves_nothing(engine, settings, world):
    s = settings.model_copy(update={"ai_provider": "anthropic_api", "anthropic_api_key": None})
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(s, world, question="Why?"))
    assert (e.value.status, e.value.code) == (503, "feature_disabled")
    assert _ledger(world["conn"], world["uid"]) == 0


def test_ai_all_switch_is_feature_disabled_before_consent(engine, settings, world):
    world["conn"].execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', '1', false)", (world["uid"],))
    with pytest.raises(ApiError) as e:
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain"), flags=engaged("ai.all")))
    assert (e.value.status, e.value.code) == (503, "feature_disabled")


def test_an_unexpected_error_after_the_call_refunds_and_fails_the_run(engine, settings, world, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("meter down")

    monkeypatch.setattr("hermi.modules.ai.features.base.record_usage", boom)
    with pytest.raises(RuntimeError):
        _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain", cost=100)))
    c = world["conn"]
    assert _balance(c, world["uid"]) == START
    assert _one(c, "SELECT status::text FROM runs WHERE user_id = %s", world["uid"])[0] == "failed"


def test_other_members_names_are_redacted_from_item_titles(engine, settings, world):
    c = world["conn"]
    bob, _ = _make_member(c, world, "Bob Hall")
    c.execute("INSERT INTO itinerary_items (trip_id, day, title) VALUES (%s, '2027-05-02', 'Dinner with Bob')", (world["tid"],))
    stub = Stub("feature_draft_day")
    _run(engine, world, drafts.draft_day, **_kw(settings, world, day=date(2027, 5, 2), provider=stub))
    sent = json.dumps([stub.calls[0].system, stub.calls[0].messages])
    assert "Bob" not in sent and "Dinner with" in sent


# ---- prompt cache layout and the logged read ratio ----


def test_request_layout_puts_the_static_prefix_first_and_the_date_last(settings):
    spec = drafts.DAY_SPEC.call
    a = ai_client.build_request(settings, spec, "<day>one</day>", today=date(2027, 1, 1))
    b = ai_client.build_request(settings, spec, "<day>two</day>", today=date(2027, 1, 2))
    assert a.system == b.system and a.tools == [] == b.tools
    assert a.system[0]["cache_control"] == {"type": "ephemeral"}
    blocks = a.messages[0]["content"]
    assert [x["text"] for x in blocks] == ["<day>one</day>", "<today>2027-01-01</today>"]  # task, then the volatile tail
    assert a.model == settings.ai_model_main and a.max_tokens == 1500
    assert a.extra == {"output_config": {"effort": "low"}} and a.output_schema is drafts.DAY_SCHEMA
    haiku = ai_client.build_request(settings, explain.SPEC.call, "q")
    assert haiku.model == settings.ai_model_fast and haiku.extra == {}  # Haiku has no effort control
    assert not any(k in haiku.extra for k in ("temperature", "top_p", "top_k"))


def test_cache_read_ratio_is_logged_and_stored(engine, settings, world, caplog):
    usage = Usage(input_tokens=100, output_tokens=40, cache_read_tokens=800, cache_write_5m_tokens=100)
    with caplog.at_level(logging.INFO, logger="hermi.ai"):
        done = _run(engine, world, explain.execute, **_kw(settings, world, question="Why?", provider=Stub("feature_explain", usage=usage)))
    rec = next(r for r in caplog.records if r.getMessage() == "ai_call")
    assert rec.cache_read_ratio == 0.8 and rec.feature == "explain" and rec.outcome == "ok"
    report = _one(world["conn"], "SELECT report FROM runs WHERE id = %s", done.run_id)[0]
    assert report["cache_read_ratio"] == 0.8


# ---- redactor ----


def test_redactor_round_trip_and_dates_survive():
    r = Redactor(["Marguerite Dupont", "Al"])
    out = r.clean("marguerite and DUPONT land 2027-05-01, ring +1 415 555 0134, mail a@b.co. Al too")
    assert "arguerite" not in out and "upont" not in out and "2027-05-01" in out
    assert "[REF_1]" in out and "[EMAIL_1]" in out
    assert r.restore("Hi Traveler A").startswith("Hi Marguerite Dupont")
    assert r.restore(out).count("+1 415 555 0134") == 1


# ---- over HTTP, on AI_PROVIDER=fake ----


@pytest.fixture
def client(db_urls, settings):
    with TestClient(create_app(settings), raise_server_exceptions=False) as c:
        c.settings = settings
        yield c


def _as_owner(client, world):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    r = client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=h)
    assert r.status_code == 201, r.text
    uid = r.json()["id"]
    world["conn"].execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'ai_processing', '1', true)", (uid,))
    tid = world["conn"].execute(
        "INSERT INTO trips (owner_user_id, name, home_currency, start_date, end_date) VALUES (%s, 'T', 'USD', '2027-05-01', '2027-05-05') RETURNING id", (uid,)
    ).fetchone()[0]
    world["conn"].execute("INSERT INTO trip_destinations (trip_id, position, name, lat, lon) VALUES (%s, 0, 'Lisbon', 38.7, -9.1)", (tid,))
    return h, uid, str(tid)


def test_http_routes_on_the_fake_provider(client, world):
    h, uid, tid = _as_owner(client, world)
    world["conn"].execute("UPDATE entitlements SET tier_code = 'plus' WHERE user_id = %s", (uid,))
    _grant(world["conn"], uid)
    post = lambda path, body, key=None: client.post(f"/v1/trips/{tid}/ai/{path}", json=body, headers={**h, "Idempotency-Key": key or uuid.uuid4().hex})  # noqa: E731
    r = post("packing-list", {"preferences": "light"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["label"] and len(body["items"]) >= 18 and body["credits"]["charged"] == 1 and body["credits"]["action"] == "explain"
    r = post("explain", {"question": "Is it far?"})
    assert r.status_code == 200, r.text
    assert r.json()["sources"] == [] and r.json()["answer"]
    r = post("draft-day", {"day": "2027-05-02"})
    assert r.status_code == 200 and r.json()["items"][0]["source"] == "ai_draft"
    r = post("draft-trip", {})
    assert r.status_code == 202 and r.json()["status"] == "done" and r.json()["credits"]["charged"] == 4
    assert _balance(world["conn"], uid) == START - 7


def test_http_needs_an_idempotency_key_and_an_editor(client, world):
    h, uid, tid = _as_owner(client, world)
    assert client.post(f"/v1/trips/{tid}/ai/explain", json={"question": "x"}, headers=h).status_code == 400
    other = uuid.uuid4().hex
    oh = {"Authorization": "Bearer " + mint_dev_token(client.settings, other, email=f"{other[:12]}@example.com")}
    client.post("/v1/me/bootstrap", json={"age_confirmed": True, "home_currency": "EUR"}, headers=oh)
    r = client.post(f"/v1/trips/{tid}/ai/explain", json={"question": "x"}, headers={**oh, "Idempotency-Key": uuid.uuid4().hex})
    assert r.status_code == 404  # not a member


def test_http_kill_switch_returns_503_feature_disabled(client, world):
    h, uid, tid = _as_owner(client, world)
    client.app.state.flags = engaged("ai.packing")
    r = client.post(f"/v1/trips/{tid}/ai/packing-list", json={}, headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    assert r.status_code == 503 and r.json()["code"] == "feature_disabled"
    r = client.post(f"/v1/trips/{tid}/ai/explain", json={"question": "x"}, headers={**h, "Idempotency-Key": uuid.uuid4().hex})
    assert r.status_code == 200  # only that feature is off


def test_a_packing_repeat_is_free_for_seven_days_and_charged_after(engine, settings, world):
    stub = Stub("feature_packing_list")
    first = _run(engine, world, packing_list.execute, **_kw(settings, world, provider=stub))
    c = world["conn"]
    c.execute("UPDATE runs SET finished_at = now() - interval '7 hours' WHERE id = %s", (first.run_id,))
    again = _run(engine, world, packing_list.execute, **_kw(settings, world, provider=stub))
    assert again.receipt.charged == 0 and again.receipt.from_cache and len(stub.calls) == 1
    c.execute("UPDATE runs SET finished_at = now() - interval '8 days' WHERE id = %s", (first.run_id,))
    late = _run(engine, world, packing_list.execute, **_kw(settings, world, provider=stub))
    assert late.receipt.charged == 1 and len(stub.calls) == 2
