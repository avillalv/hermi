# ruff: noqa: E501
"""WF-049.1: the agent loop over a scripted provider and fake tools. Every cap, the blocked hosts, the cancel and
deadline checkpoints, the nudge, pause_turn, max_tokens and the claude_cli mapping. No network, no real model."""

import asyncio
import json

import pytest

from hermi.modules.ai.metering import Usage
from hermi.modules.ai.policy import api_blocked_domains
from hermi.providers.ai.base import ProviderResult
from hermi.providers.ai.claude_cli import CliRun, CliRunFailed
from hermi.providers.ai.claude_stream import EvidenceCollector, StreamState
from hermi_worker.agents.loop import AgentLoop, Hooks, final_status
from hermi_worker.agents.prompts import NUDGE, PROMPT_VERSION, SYSTEM, task_prompt
from hermi_worker.agents.spec import AgentSpec
from hermi_worker.agents.tools import ToolOutput, blocked_url, check_schema, server_tools

MODEL = "claude-test-main"
FINISH = {"status": "ok", "summary": "Done.", "sources_checked": [], "issues": []}
NOTE = {"title": "T", "body": "B", "urls": ["https://example.com/a"], "topic": "events"}


def spec(**kw) -> AgentSpec:
    return AgentSpec(model=MODEL, system=SYSTEM, allowed_models=frozenset({MODEL}), **kw)


def tool(name, args, tid="t1"):
    return {"type": "tool_use", "id": tid, "name": name, "input": args}


def search(n=1, urls=("https://example.com/a",), tid="s"):
    out = []
    for i in range(n):
        out += [
            {"type": "server_tool_use", "id": f"{tid}{i}", "name": "web_search", "input": {"query": "q"}},
            {"type": "web_search_tool_result", "tool_use_id": f"{tid}{i}", "content": [{"type": "web_search_result", "url": u} for u in urls]},
        ]
    return out


def fetch(url, result_url=None, text="Fare 412.00", tid="f"):
    return [
        {"type": "server_tool_use", "id": tid, "name": "web_fetch", "input": {"url": url}},
        {"type": "web_fetch_tool_result", "tool_use_id": tid, "content": {"type": "web_fetch_result", "url": result_url or url, "content": {"type": "document", "source": {"type": "text", "data": text}}}},
    ]


def resp(content, stop="tool_use", cost=0, model=MODEL, searches=0):
    if stop == "tool_use" and not any(b["type"] == "tool_use" for b in content):
        stop = "pause_turn"  # a response with only server tool blocks never stops on tool_use
    return ProviderResult(
        provider="fake", model=model, content=content, stop_reason=stop, usage=Usage(input_tokens=10, output_tokens=5, web_searches=searches), cost_usd_micros=cost,
    )  # fmt: skip


class Scripted:
    """Replays a list of responses (the last repeats), or calls a function with the request number."""

    name = "fake"

    def __init__(self, script, *, delay=0.0):
        self.script, self.delay, self.calls = script, delay, []

    async def single_call(self, req):
        self.calls.append(req)
        if self.delay:
            await asyncio.sleep(self.delay)
        i = len(self.calls) - 1
        return self.script(i) if callable(self.script) else self.script[min(i, len(self.script) - 1)]


class Recorder:
    def __init__(self):
        self.events, self.metered, self.notes = [], [], []

    def hooks(self, **kw) -> Hooks:
        return Hooks(emit=lambda t, s, p=None, n=None: self.events.append((t, s, p, n)), on_response=lambda turn, r: self.metered.append((turn, r.cost_usd_micros)), poll_seconds=0.02, **kw)

    def handlers(self):
        def add_note(args, ctx):
            self.notes.append(args)
            return ToolOutput({"status": "accepted"}, accepted=1)

        def quotes(args, ctx):
            return ToolOutput({"results": ["accepted"] * len(args["quotes"])}, accepted=len(args["quotes"]))

        return {"add_note": add_note, "submit_flight_quotes": quotes}


def run(provider, rec=None, sp=None, handlers=None, hooks=None, **kw):
    rec = rec or Recorder()
    loop = AgentLoop(provider, sp or spec(), handlers if handlers is not None else rec.handlers(), hooks or rec.hooks(), **kw)
    return asyncio.run(loop.run("task")), rec, loop


# --- the finish path -----------------------------------------------------------------------------------------------


def test_note_then_finish_run_succeeds_and_meters_every_response():
    p = Scripted([resp([tool("add_note", NOTE)], cost=1000), resp([tool("finish_run", FINISH)], cost=2000)])
    out, rec, _ = run(p)
    assert (out.stop, out.status, out.turns, out.accepted, out.cost_usd_micros) == ("finished", "succeeded", 2, 1, 3000)
    assert rec.metered == [(1, 1000), (2, 2000)] and out.report == FINISH
    # the request layout: server tools first, the caching breakpoint on the static system block, effort medium
    req = p.calls[0]
    assert [t["name"] for t in req.tools] == ["web_search", "web_fetch", "submit_flight_quotes", "add_note", "finish_run"]
    assert req.system[0]["cache_control"] == {"type": "ephemeral"} and req.extra["output_config"] == {"effort": "medium"}
    assert req.extra["thinking"] == {"type": "adaptive"}


def test_tool_results_go_back_in_one_user_message_and_assistant_content_is_unedited():
    first = [{"type": "thinking", "thinking": "hmm", "signature": "sig"}, tool("add_note", NOTE, "a"), tool("nope", {}, "b"), tool("add_note", {"title": 1}, "c")]
    p = Scripted([resp(first), resp([tool("finish_run", FINISH)])])
    out, rec, _ = run(p)
    second = p.calls[1].messages
    assert second[1] == {"role": "assistant", "content": first}  # thinking block round-trips exactly
    results = second[2]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b", "c"]
    assert [bool(r.get("is_error")) for r in results] == [False, True, True]
    assert rec.notes == [NOTE]


def test_finished_with_nothing_saved_is_failed_and_refunded():
    out, _, _ = run(Scripted([resp([tool("finish_run", FINISH)])]))
    assert (out.stop, out.status, out.failure_code) == ("finished", "failed", "nothing_saved")


def test_end_turn_without_finish_is_nudged_once_then_partial_with_saved_work():
    p = Scripted([resp([tool("add_note", NOTE)]), resp([{"type": "text", "text": "done?"}], stop="end_turn"), resp([{"type": "text", "text": "..."}], stop="end_turn")])
    out, _, _ = run(p)
    assert len(p.calls) == 3 and out.stop == "no_finish" and (out.status, out.failure_code) == ("partial", "no_finish")
    nudge = p.calls[2].messages[-1]
    assert nudge == {"role": "user", "content": [{"type": "text", "text": NUDGE}]}


def test_end_turn_then_finish_after_the_nudge():
    p = Scripted([resp([tool("add_note", NOTE)]), resp([{"type": "text", "text": "x"}], stop="end_turn"), resp([tool("finish_run", FINISH)])])
    out, _, _ = run(p)
    assert out.stop == "finished" and out.status == "succeeded"


def test_pause_turn_resends_without_a_new_user_message():
    p = Scripted([resp(search(1), stop="pause_turn"), resp([tool("add_note", NOTE)]), resp([tool("finish_run", FINISH)])])
    out, _, _ = run(p)
    assert out.stop == "finished" and out.searches == 1
    assert p.calls[1].messages[-1]["role"] == "assistant"


# --- caps ------------------------------------------------------------------------------------------------------------


def test_turn_cap_stops_at_20_and_keeps_saved_work_partial():
    p = Scripted([resp([tool("add_note", NOTE)])])
    out, rec, _ = run(p)
    assert (out.stop, out.status, out.turns, out.failure_code) == ("turn_limit", "partial", 20, "turn_limit")
    assert len(p.calls) == 20 and len(rec.notes) == 20  # the last turn's tool still ran


def test_turn_cap_is_the_specs():
    out, _, _ = run(Scripted([resp([tool("add_note", NOTE)])]), sp=spec(max_turns=3))
    assert out.stop == "turn_limit" and out.turns == 3


def test_search_cap_exactly_at_the_limit_continues_and_one_more_stops():
    ok, _, _ = run(Scripted([resp(search(5)), resp(search(5)), resp([tool("finish_run", FINISH)])]), handlers={})
    assert ok.searches == 10 and ok.stop == "finished"
    p = Scripted([resp([tool("add_note", NOTE)] + search(4)), resp(search(4)), resp(search(4) + [tool("add_note", NOTE, "n2")]), resp([tool("finish_run", FINISH)])])
    out, rec, _ = run(p)
    assert (out.stop, out.status, out.searches) == ("search_cap", "partial", 12)
    assert len(p.calls) == 3 and len(rec.notes) == 2  # the tool in the capping response still saved


def test_fetch_cap_stops_and_keeps_saved_work():
    p = Scripted([resp([tool("add_note", NOTE)]), resp(fetch("https://example.com/1", tid="f1") * 6), resp(fetch("https://example.com/2", tid="f2") * 6)])
    out, _, _ = run(p)
    assert (out.stop, out.status, out.fetches, out.accepted) == ("fetch_cap", "partial", 12, 1)


def test_server_tool_limits_sent_to_the_api_follow_the_spec():
    tools = {t["name"]: t for t in server_tools(spec(max_searches=7, max_fetches=3))}
    assert tools["web_search"]["max_uses"] == 7 and tools["web_fetch"]["max_uses"] == 3
    assert tools["web_fetch"]["blocked_domains"] == tools["web_search"]["blocked_domains"] == api_blocked_domains()
    assert "allowed_domains" not in tools["web_fetch"] and tools["web_fetch"]["max_content_tokens"] == 5000


def test_remaining_budget_is_sent_each_request_and_counts_never_pass_the_cap():
    # 9 searches in turn 1 leave 1; the next request offers max_uses 1, then web_search is dropped at 0
    p = Scripted([resp(search(9)), resp(search(1)), resp([tool("finish_run", FINISH)])])
    out, _, _ = run(p)
    first, second, third = ({t["name"]: t for t in c.tools if "max_uses" in t} for c in p.calls)
    assert first["web_search"]["max_uses"] == 10 and second["web_search"]["max_uses"] == 1
    assert "web_search" not in third and third["web_fetch"]["max_uses"] == 10
    assert out.stop == "finished" and out.searches == 10


def test_fetch_budget_shrinks_and_drops_the_same_way():
    p = Scripted([resp(fetch("https://example.com/1", tid="a") * 4), resp(fetch("https://example.com/2", tid="b") * 6), resp([tool("finish_run", FINISH)])])
    out, _, _ = run(p)
    names = [[t["name"] for t in c.tools] for c in p.calls]
    assert p.calls[1].tools[1]["max_uses"] == 6 and "web_fetch" not in names[2] and "web_search" in names[2]
    assert out.fetches == 10


def test_dollar_cap_checked_after_each_response_keeps_saved_work():
    p = Scripted([resp([tool("add_note", NOTE)], cost=500_000)])
    out, rec, _ = run(p)
    assert (out.stop, out.status, out.failure_code, out.turns, out.cost_usd_micros) == ("spend_limit", "partial", "budget_stop", 2, 1_000_000)
    assert len(rec.notes) == 2  # turn 2 overshot: its tool still ran, no third call


def test_dollar_cap_counts_cost_already_spent_before_this_loop():
    p = Scripted([resp([tool("finish_run", FINISH)])])
    out, _, _ = run(p, initial_cost=800_000)
    assert out.stop == "spend_limit" and len(p.calls) == 0 and out.status == "failed"


def test_deadline_cancels_a_call_in_flight_and_marks_timed_out():
    p = Scripted([resp([tool("add_note", NOTE)]), resp([tool("finish_run", FINISH)])], delay=5)
    out, _, _ = run(p, sp=spec(deadline_s=0.15))
    assert (out.stop, out.status) == ("deadline", "timed_out") and out.turns == 0


def test_deadline_between_turns_uses_the_injected_clock_and_keeps_work():
    now = [0.0]

    def script(i):
        now[0] += 300.0  # each turn "takes" five minutes
        return resp([tool("add_note", NOTE)])

    rec = Recorder()
    hooks = rec.hooks(clock=lambda: now[0])
    out, _, _ = run(Scripted(script), rec=rec, hooks=hooks)
    assert (out.stop, out.status, out.turns, out.accepted) == ("deadline", "timed_out", 2, 2)


def test_max_tokens_retries_once_with_double_then_stops():
    p = Scripted([resp([tool("add_note", NOTE)], stop="max_tokens"), resp([tool("add_note", NOTE)], stop="max_tokens")])
    out, rec, _ = run(p)
    assert [c.max_tokens for c in p.calls] == [8000, 16000]
    assert out.stop == "max_tokens" and rec.notes == [] and out.status == "failed"


def test_refusal_and_model_mismatch_fail_without_running_tools():
    out, rec, _ = run(Scripted([resp([tool("add_note", NOTE)], stop="refusal")]))
    assert (out.stop, out.status, out.failure_code) == ("refusal", "failed", "refused") and rec.notes == []
    out, rec, _ = run(Scripted([resp([tool("add_note", NOTE)], model="claude-other")]))
    assert (out.stop, out.failure_code) == ("model_mismatch", "model_mismatch") and rec.notes == []


def test_second_invalid_input_for_one_tool_stops_the_run():
    out, _, _ = run(Scripted([resp([tool("add_note", {"title": ""})])]))
    assert out.stop == "invalid_tool_input" and out.turns == 2


# --- blocked domains -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "https://www.airbnb.co.uk/rooms/1", "https://secure.booking.com/x", "https://airbnb.co.kr/", "https://vrbo.com/1",
    "http://m.vrbo.com/a", "booking.com/hotel", "https://WWW.AIRBNB.COM.AU/x",
])  # fmt: skip
def test_a_fetch_of_a_blocked_host_stops_the_run_and_is_never_evidence_or_acted_on(url):
    p = Scripted([resp([tool("add_note", NOTE)] + search(1)), resp(fetch(url) + [tool("add_note", NOTE, "n2")]), resp([tool("finish_run", FINISH)])])
    out, rec, loop = run(p)
    assert (out.stop, out.status, out.failure_code) == ("blocked_domain", "partial", "blocked_domain")
    assert len(p.calls) == 2 and len(rec.notes) == 1  # the blocked response's tools did not run
    assert url not in out.evidence.fetched and all(not blocked_url(u) for u in out.evidence.found)
    assert any(e[0] == "error" for e in rec.events)


def test_a_redirect_that_lands_on_a_blocked_host_stops_the_run():
    out, _, _ = run(Scripted([resp(fetch("https://example.com/r", result_url="https://www.booking.com/h"))]))
    assert out.stop == "blocked_domain" and out.evidence.fetched == {}


def test_blocked_urls_in_search_results_are_dropped_from_evidence_but_do_not_stop():
    p = Scripted([resp(search(1, urls=("https://www.airbnb.com/r", "https://example.com/ok"))), resp([tool("finish_run", FINISH)])])
    out, _, _ = run(p)
    assert out.stop == "finished" and out.evidence.found == {"https://example.com/ok"}


@pytest.mark.parametrize("url", ["https://notairbnb.com/", "https://booking.aa.com/", "https://example.com/airbnb.com"])
def test_lookalikes_are_not_blocked(url):
    assert blocked_url(url) is None


def test_fetched_evidence_keeps_the_document_text_and_server_errors_warn():
    err = {"type": "web_fetch_tool_result", "tool_use_id": "e", "content": {"type": "web_fetch_tool_error", "error_code": "url_not_accessible"}}
    p = Scripted([resp(fetch("https://example.com/p", text="Total 412.00 USD") + [err]), resp([tool("finish_run", FINISH)])])
    out, rec, _ = run(p)
    assert out.evidence.fetched == {"https://example.com/p": "Total 412.00 USD"} and out.evidence.seen("https://example.com/p")
    assert ("warning", "web_fetch: url_not_accessible", {"error_code": "url_not_accessible"}, "web_fetch") in rec.events


# --- cancel ----------------------------------------------------------------------------------------------------------


def test_cancel_is_checked_before_each_turn_and_keeps_saved_work():
    state = {"n": 0}

    def script(i):
        state["n"] = i + 1
        return resp([tool("add_note", NOTE)])

    rec = Recorder()
    out, _, _ = run(Scripted(script), rec=rec, hooks=rec.hooks(is_cancelled=lambda: state["n"] >= 1))
    assert (out.stop, out.status, out.turns, out.accepted) == ("cancelled", "cancelled", 1, 1)
    assert state["n"] == 1  # the provider was called once, not again after the cancel


def test_cancel_before_the_first_turn_never_calls_the_provider():
    p = Scripted([resp([tool("finish_run", FINISH)])])
    rec = Recorder()
    out, _, _ = run(p, rec=rec, hooks=rec.hooks(is_cancelled=lambda: True))
    assert out.stop == "cancelled" and p.calls == [] and out.turns == 0


def test_cancel_mid_call_kills_the_stream_without_waiting_for_it():
    flag = {"v": False}
    started = []

    class Slow(Scripted):
        async def single_call(self, req):
            started.append(1)
            flag["v"] = True
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                started.append("cancelled")
                raise

    rec = Recorder()
    out, _, _ = run(Slow([]), rec=rec, hooks=rec.hooks(is_cancelled=lambda: flag["v"]))
    assert out.stop == "cancelled" and started == [1, "cancelled"]


# --- status table ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("stop", "saved", "want"), [
    ("finished", 3, ("succeeded", None)), ("finished", 0, ("failed", "nothing_saved")),
    ("turn_limit", 2, ("partial", "turn_limit")), ("turn_limit", 0, ("failed", "nothing_saved")),
    ("spend_limit", 1, ("partial", "budget_stop")), ("search_cap", 1, ("partial", "search_cap")),
    ("fetch_cap", 1, ("partial", "fetch_cap")), ("deadline", 1, ("timed_out", None)), ("deadline", 0, ("timed_out", "nothing_saved")),
    ("cancelled", 4, ("cancelled", "cancelled")), ("refusal", 0, ("failed", "refused")),
])  # fmt: skip
def test_final_status(stop, saved, want):
    assert final_status(stop, saved) == want


def test_schema_check_matches_the_tool_schemas():
    s = {"type": "object", "properties": {"n": {"type": ["integer", "null"], "minimum": 1}}, "required": ["n"], "additionalProperties": False}
    assert check_schema(s, {"n": None}) is None and check_schema(s, {"n": 1}) is None
    assert check_schema(s, {"n": 0}) and check_schema(s, {"n": True}) and check_schema(s, {}) and check_schema(s, {"n": 1, "x": 1})


# --- claude_cli ------------------------------------------------------------------------------------------------------


class CliStub:
    name = "claude_cli"

    def __init__(self, *, result=None, fail=None):
        self.result, self.fail, self.req = result, fail, None
        self.last_run = CliRun("ok", None, None, StreamState(searches=2, fetches=1), EvidenceCollector(found={"https://example.com/a", "https://www.airbnb.com/x"}, fetched={"https://example.com/p"}))

    async def agent_run(self, req, *, max_turns, stop_micro, run_tool=None):
        self.req = req
        if self.fail:
            raise self.fail
        return self.result


def cli_outcome(final: dict, stop="end_turn", cost=100_000):
    from hermi.providers.ai.base import AgentOutcome

    r = ProviderResult("claude_cli", MODEL, [{"type": "text", "text": json.dumps(final)}], "end_turn", Usage(web_searches=2), cost)
    return AgentOutcome(stop, r, 5, r.usage, cost, [])  # type: ignore[arg-type]


def test_cli_run_passes_caps_and_cancel_down_and_saves_the_final_json_through_the_handlers():
    final = {**FINISH, "quotes": [], "notes": [NOTE]}
    p = CliStub(result=cli_outcome(final))
    out, rec, _ = run(p)
    assert p.req.extra["max_searches"] == 10 and p.req.extra["max_fetches"] == 10 and callable(p.req.extra["is_cancelled"])
    assert (out.stop, out.status, out.accepted, out.turns, out.cost_usd_micros) == ("finished", "succeeded", 1, 5, 100_000)
    assert rec.notes == [NOTE] and out.evidence.found == {"https://example.com/a"}  # the blocked search link is dropped


@pytest.mark.parametrize(("status", "stop"), [("blocked_domain", "blocked_domain"), ("timeout", "deadline"), ("cancelled", "cancelled")])
def test_cli_failures_map_to_our_stops(status, stop):
    out, _, _ = run(CliStub(fail=CliRunFailed(status, "x")))
    assert out.stop == stop


def test_cli_cap_exceeded_maps_to_search_or_fetch_cap():
    run_ = CliRun("cap_exceeded", "x", None, StreamState(searches=11, fetches=2), EvidenceCollector())
    out, _, _ = run(CliStub(fail=CliRunFailed("cap_exceeded", "x", run_)))
    assert out.stop == "search_cap"
    run_ = CliRun("cap_exceeded", "x", None, StreamState(searches=3, fetches=11), EvidenceCollector())
    out, _, _ = run(CliStub(fail=CliRunFailed("cap_exceeded", "x", run_)))
    assert out.stop == "fetch_cap"


def test_cli_other_failures_propagate_to_the_job():
    with pytest.raises(CliRunFailed):
        run(CliStub(fail=CliRunFailed("error", "boom")))


def test_cli_spend_stop_and_bad_final_json():
    out, _, _ = run(CliStub(result=cli_outcome({}, stop="spend_limit")))
    assert out.stop == "spend_limit"
    out, _, _ = run(CliStub(result=cli_outcome({"summary": "x"})))
    assert out.stop == "no_finish"


# --- prompts ---------------------------------------------------------------------------------------------------------


def test_task_prompt_wraps_instructions_and_states_the_caps():
    t = task_prompt("fare_hunt", trip_name="Lisbon", task_json="{}", today="2027-01-01", run_short_id="ab12", max_searches=10, max_fetches=10, instructions="<b>cheap</b>\x00 only")
    assert "<instructions>bcheap/b only</instructions>" in t and "at most 10 searches and 10 page fetches" in t
    assert "Today is 2027-01-01. Run ab12." in t and "Today" not in SYSTEM  # the volatile part stays out of the cached prefix
    assert "at most 4 searches and 3 page fetches" in task_prompt("fare_hunt", trip_name="x", task_json="{}", today="d", run_short_id="r", max_searches=4, max_fetches=3)
    long = task_prompt("fare_hunt", trip_name="<b>" + "N" * 400, task_json="{}", today="d", run_short_id="r")
    assert "for b" + "N" * 159 + "\n" in long and "N" * 160 not in long  # brackets removed, cut at 160
    assert PROMPT_VERSION
    with pytest.raises(ValueError):
        task_prompt("nope", trip_name="x", task_json="{}", today="d", run_short_id="r")


def test_blocked_domain_hit_still_counts_the_responses_searches_and_fetches():
    blocked = fetch("https://www.booking.com/hotel/x", tid="bf")
    p = Scripted([resp(search(2) + blocked, searches=2)])
    out, _, _ = run(p)
    assert out.stop == "blocked_domain" and out.searches == 2 and out.fetches == 1
