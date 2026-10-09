# ruff: noqa: E501
"""WF-131.1: the AiProvider seam, the guard matrix, the fake replay and the anthropic_api backend (stub client)."""

import asyncio
import itertools
import json
from pathlib import Path

import pytest

from hermi.config import Settings, claude_cli_allowed
from hermi.modules.ai import client as ai_client
from hermi.modules.ai.metering import cost_usd_micros
from hermi.providers.ai import (
    AnthropicApiProvider,
    ClaudeCliProvider,
    FakeProvider,
    ProviderRefused,
    ProviderRequest,
    get_provider,
)

REQ = ProviderRequest(
    model="claude-haiku-4-5",
    system="s",
    messages=[{"role": "user", "content": "hi"}],
    max_tokens=100,
)


def run(coro):
    return asyncio.run(coro)


def settings(**over) -> Settings:
    base = {
        "environment": "local",
        "ai_provider": "claude_cli",
        "auth_mode": "dev",
        "ai_cli_allowed_emails": "me@example.com",
    }
    return Settings(**{**base, **over})


def test_guard_matrix_factory_follows_claude_cli_allowed():
    n = 0
    for env, prov, auth, host, allow, email in itertools.product(
        ["local", "ci", "staging", "production"],
        ["anthropic_api", "claude_cli", "fake"],
        ["dev", "supabase"],
        ["127.0.0.1", "::1", "[::1]", "localhost", "0.0.0.0"],
        ["me@example.com", ""],  # AI_CLI_ALLOWED_EMAILS
        ["me@example.com", "other@example.com", None],
    ):
        s = settings().model_copy(
            update={
                "environment": env,
                "ai_provider": prov,
                "auth_mode": auth,
                "ai_cli_allowed_emails": allow,
            }
        )
        allowed = claude_cli_allowed(s, host, email)
        if prov != "claude_cli":
            assert not allowed
            assert isinstance(
                get_provider(s, email, bind_host=host, client=object()),
                (FakeProvider, AnthropicApiProvider),
            )
        elif allowed:
            assert (
                env == "local"
                and host != "0.0.0.0"
                and (auth == "dev" or (allow and email == "me@example.com"))
            )
            assert isinstance(get_provider(s, email, bind_host=host), ClaudeCliProvider)
        else:
            with pytest.raises(ProviderRefused):
                get_provider(s, email, bind_host=host)
        n += 1
    assert n == 4 * 3 * 2 * 5 * 2 * 3


def test_factory_rechecks_at_call_time():
    s = settings(auth_mode="supabase", supabase_url="https://abc.supabase.co")
    with pytest.raises(ProviderRefused):
        get_provider(s, "stranger@example.com", bind_host="127.0.0.1")
    assert isinstance(get_provider(s, "ME@example.com", bind_host="127.0.0.1"), ClaudeCliProvider)
    s.environment = "staging"  # settings changed after startup: refused, never the CLI
    with pytest.raises(ProviderRefused):
        get_provider(s, "me@example.com", bind_host="127.0.0.1")


def test_factory_fake_and_anthropic():
    assert isinstance(
        get_provider(settings(ai_provider="fake"), bind_host="127.0.0.1"), FakeProvider
    )
    assert isinstance(
        get_provider(settings(ai_provider="anthropic_api"), bind_host="127.0.0.1", client=object()),
        AnthropicApiProvider,
    )


def test_anthropic_without_key_is_a_clear_error():
    with pytest.raises(Exception, match="ANTHROPIC_API_KEY"):
        get_provider(settings(ai_provider="anthropic_api"), bind_host="127.0.0.1")


def test_fake_replays_end_turn():
    r = run(FakeProvider().single_call(REQ))
    assert (
        r.provider == "fake" and r.stop_reason == "end_turn" and r.text and r.cost_usd_micros == 0
    )
    assert r.usage.input_tokens > 0


def test_fake_replays_server_tool_use():
    r = run(FakeProvider("server_tool_use").single_call(REQ))
    assert r.server_tool_use == {"web_search_requests": 1}
    assert r.usage.web_searches == 1
    assert any(b["type"] == "server_tool_use" for b in r.content)


def test_fake_replays_refusal():
    assert run(FakeProvider("refusal").single_call(REQ)).stop_reason == "refusal"
    out = run(FakeProvider("refusal").agent_run(REQ))
    assert out.stop == "refusal" and out.turns == 1


def test_fake_pause_turn_is_resent_then_ends():
    out = run(FakeProvider(["pause_turn", "end_turn"]).agent_run(REQ))
    assert out.stop == "end_turn" and out.turns == 2
    assert (
        out.messages[-2]["role"] == "assistant"
        and out.messages[-2]["content"][0]["type"] == "server_tool_use"
    )
    assert out.usage.input_tokens > 0


def test_agent_run_turn_limit():
    out = run(FakeProvider(["pause_turn"] * 5).agent_run(REQ, max_turns=3))
    assert out.stop == "turn_limit" and out.turns == 3


def test_agent_run_spend_limit():
    # shortcut: the fake costs nothing, so a stub with a priced reply proves the stop.
    c = StubClient(reply(stop_reason="pause_turn"), reply())
    out = run(AnthropicApiProvider(c).agent_run(REQ, stop_micro=1))
    assert out.stop == "spend_limit" and out.turns == 1


def test_agent_run_client_tool_loop():
    seen = []

    async def run_tool(block):
        seen.append(block["name"])
        return {"type": "tool_result", "tool_use_id": block["id"], "content": "ok"}

    out = run(FakeProvider(["tool_use", "end_turn"]).agent_run(REQ, run_tool=run_tool))
    assert seen == ["lookup"] and out.stop == "end_turn"
    assert out.messages[-2]["content"][0]["type"] == "tool_result"


class StubMessages:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    async def create(self, **kw):
        self.calls.append(kw)
        return self.replies.pop(0)


class StubClient:
    def __init__(self, *replies):
        self.messages = StubMessages(replies)


def reply(**over):
    return {
        "model": "claude-haiku-4-5",
        "content": [{"type": "text", "text": "hello"}],
        "stop_reason": "end_turn",
        "usage": {
            "input_tokens": 1000,
            "output_tokens": 500,
            "cache_read_input_tokens": 200,
            "server_tool_use": {"web_search_requests": 2},
        },
        **over,
    }


def test_anthropic_request_shape_and_usage_mapping():
    c = StubClient(reply())
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 3}]
    req = ProviderRequest(
        model="claude-haiku-4-5",
        system=[{"type": "text", "text": "sys"}],
        messages=[{"role": "user", "content": "q"}],
        max_tokens=256,
        tools=tools,
        output_schema={"type": "object"},
    )
    r = run(AnthropicApiProvider(c).single_call(req))
    kw = c.messages.calls[0]
    assert kw["model"] == "claude-haiku-4-5" and kw["max_tokens"] == 256 and kw["tools"] == tools
    assert kw["system"] == [{"type": "text", "text": "sys"}] and kw["messages"] == req.messages
    assert kw["output_config"] == {"format": {"type": "json_schema", "schema": {"type": "object"}}}
    assert r.provider == "anthropic_api" and r.text == "hello"
    assert (
        r.usage.input_tokens,
        r.usage.output_tokens,
        r.usage.cache_read_tokens,
        r.usage.web_searches,
    ) == (1000, 500, 200, 2)
    assert r.server_tool_use == {"web_search_requests": 2}
    assert r.cost_usd_micros == cost_usd_micros(r.usage, "claude-haiku-4-5") > 0


def test_anthropic_omits_unset_fields_and_resends_on_pause():
    c = StubClient(reply(stop_reason="pause_turn"), reply())
    out = run(AnthropicApiProvider(c).agent_run(REQ))
    assert "tools" not in c.messages.calls[0] and "output_config" not in c.messages.calls[0]
    assert out.turns == 2 and out.stop == "end_turn"
    assert out.usage.input_tokens == 2000 and out.cost_usd_micros > 0
    assert len(c.messages.calls[1]["messages"]) == 2


def test_facade_passes_through():
    p = FakeProvider()
    assert run(ai_client.single_call(p, REQ)).provider == "fake"
    assert run(ai_client.agent_run(p, REQ)).stop == "end_turn"


def test_fixtures_are_valid_messages_responses():
    files = list(
        (Path(__file__).resolve().parents[2] / "hermi/providers/ai/fixtures").glob("*.json")
    )
    assert len(files) >= 4
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        assert {"content", "stop_reason", "usage"} <= d.keys(), f.name


def test_factory_refuses_off_loopback_even_with_dev_auth():
    with pytest.raises(ProviderRefused):
        get_provider(settings(), "me@example.com", bind_host="0.0.0.0")


def test_bind_host_is_required():
    with pytest.raises(TypeError):
        get_provider(settings(ai_provider="fake"))  # type: ignore[call-arg]


def test_agent_run_does_not_report_end_turn_for_tool_use_or_unknown():
    out = run(FakeProvider("tool_use").agent_run(REQ))
    assert out.stop == "tool_use"


def test_extra_cannot_override_core_fields():
    from hermi.providers import ProviderError

    req = ProviderRequest(model="claude-haiku-4-5", messages=[], max_tokens=1, extra={"model": "x"})
    with pytest.raises(ProviderError):
        run(AnthropicApiProvider(StubClient(reply())).single_call(req))
    ok = ProviderRequest(
        model="claude-haiku-4-5", messages=[], max_tokens=1, extra={"temperature": 0}
    )
    c = StubClient(reply())
    run(AnthropicApiProvider(c).single_call(ok))
    assert c.messages.calls[0]["temperature"] == 0
