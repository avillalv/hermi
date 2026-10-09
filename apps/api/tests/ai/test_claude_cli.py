# ruff: noqa: E501
"""WF-131.2: the claude_cli backend against a python fake `claude` (never the real CLI)."""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from hermi import cli
from hermi.config import Settings
from hermi.modules.ai.policy import cli_disallowed_tools
from hermi.providers.ai import (
    ClaudeCliProvider,
    ProviderRefused,
    ProviderRequest,
    get_provider,
)
from hermi.providers.ai import claude_cli as cc
from hermi.providers.ai.claude_cli import CliRunFailed, build_command, find_claude, strip_env
from hermi.providers.ai.smoke import run_smoke

FAKE = [getattr(sys, "_base_executable", sys.executable), str(Path(__file__).with_name("fake_claude.py"))]
MODEL = "claude-haiku-4-5"
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def env(monkeypatch, tmp_path):
    rec = tmp_path / "rec.json"
    monkeypatch.setenv("FAKE_CLAUDE_RECORD", str(rec))
    monkeypatch.setattr(cc, "WATCH_SECONDS", 0.05)
    return rec


def settings(tmp_path, **over) -> Settings:
    base = {"environment": "local", "ai_provider": "claude_cli", "auth_mode": "dev",
            "ai_cli_scratch_dir": str(tmp_path / "scratch")}  # fmt: skip
    return Settings(**{**base, **over})


def provider(tmp_path, **over) -> ClaudeCliProvider:
    return ClaudeCliProvider(settings(tmp_path, **over), bind_host="127.0.0.1", claude=FAKE)


def req(**extra) -> ProviderRequest:
    return ProviderRequest(model=MODEL, system="sys", messages=[{"role": "user", "content": "hi"}],
                           max_tokens=100, output_schema=SCHEMA, extra=extra)  # fmt: skip


def alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def wait_dead(pid: int) -> bool:
    for _ in range(50):
        if not alive(pid):
            return True
        time.sleep(0.1)
    return False


# --- command and environment ---------------------------------------------------------------


def test_command_has_the_recipe_flags_no_tools(tmp_path):
    argv = build_command(["claude.exe"], model=MODEL, system_file=tmp_path / "s.md", web=False,
                         schema=SCHEMA, max_budget_usd=0.5, max_turns=3)  # fmt: skip
    assert argv[:2] == ["claude.exe", "-p"]
    for flag in ("--verbose", "--safe-mode", "--restricted", "--strict-mcp-config", "--no-session-persistence",
                 "--disable-slash-commands", "--permission-mode", "--permission-prompts", "--system-prompt-file",
                 "--json-schema", "--max-budget-usd", "--max-turns"):  # fmt: skip
        assert flag in argv
    assert argv[argv.index("--model") + 1] == MODEL
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert argv[argv.index("--permission-mode") + 1] == "dontAsk"
    assert argv[argv.index("--permission-prompts") + 1] == "none"
    assert argv[argv.index("--tools") + 1] == ""
    assert "--allowedTools" not in argv and "--disallowedTools" not in argv
    assert json.loads(argv[argv.index("--json-schema") + 1]) == SCHEMA
    assert argv[argv.index("--max-budget-usd") + 1] == "0.500000"


def test_command_web_adds_tools_allow_list_and_blocked_hosts(tmp_path):
    argv = build_command(["claude.exe"], model=MODEL, system_file=tmp_path / "s.md", web=True,
                         schema=None, max_budget_usd=0.8, max_turns=20)  # fmt: skip
    assert argv[argv.index("--tools") + 1] == "WebSearch,WebFetch"
    i = argv.index("--allowedTools")
    assert argv[i + 1 : i + 3] == ["WebSearch", "WebFetch"]
    j = argv.index("--disallowedTools")
    rules = argv[j + 1 : j + 1 + len(cli_disallowed_tools())]
    assert rules == cli_disallowed_tools()
    for r in ("WebFetch(domain:airbnb.*)", "WebFetch(domain:*.vrbo.*.*)", "WebFetch(domain:booking.*.*)"):
        assert r in rules
    assert "--json-schema" not in argv


def test_strip_env_drops_keys_flags_and_app_secrets_but_keeps_git_bash():
    base = {
        "ANTHROPIC_API_KEY": "k", "ANTHROPIC_BASE_URL": "u", "anthropic_model": "m", "CLAUDE_CODE_ENTRYPOINT": "x",
        "CLAUDE_CODE_USE_BEDROCK": "1", "CLAUDECODE": "1", "DATABASE_URL_SYSTEM": "pg", "SUPABASE_JWT_SECRET": "s",
        "STRIPE_SECRET_KEY": "s", "CLAUDE_CODE_GIT_BASH_PATH": "C:/bash.exe", "PATH": "/bin", "HOME": "/h",
    }  # fmt: skip
    out = strip_env(base)
    assert set(out) == {"CLAUDE_CODE_GIT_BASH_PATH", "PATH", "HOME"}


def test_find_claude_prefers_config_path_and_refuses_shims():
    s = Settings(environment="local", claude_cli_path="C:/x/claude.exe")
    assert find_claude(s, which=lambda n: None) == ["C:/x/claude.exe"]
    assert find_claude(Settings(environment="local", claude_cli_path="C:/x/claude.cmd")) is None
    assert find_claude(Settings(environment="local"), which=lambda n: "C:/n/claude.cmd") is None
    assert find_claude(Settings(environment="local"), which=lambda n: "C:/n/claude.exe") == ["C:/n/claude.exe"]
    assert find_claude(Settings(environment="local"), which=lambda n: None) is None


# --- guard ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("over", "host", "email"),
    [
        ({"environment": "ci"}, "127.0.0.1", None),
        ({"ai_provider": "fake"}, "127.0.0.1", None),
        ({}, "0.0.0.0", None),
        ({"auth_mode": "supabase", "supabase_url": "https://a.supabase.co"}, "127.0.0.1", "x@example.com"),
    ],
)  # fmt: skip
def test_provider_itself_refuses_outside_the_guard(tmp_path, over, host, email):
    with pytest.raises(ProviderRefused):
        ClaudeCliProvider(settings(tmp_path, **over), bind_host=host, user_email=email, claude=FAKE)


def test_factory_returns_the_cli_provider_when_allowed(tmp_path):
    p = get_provider(settings(tmp_path), None, bind_host="localhost")
    assert isinstance(p, ClaudeCliProvider) and p.name == "claude_cli"


# --- runs against the fake -----------------------------------------------------------------


def test_single_call_no_tools_cost_provider_and_isolation(tmp_path, env, monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_ENTRYPOINT", "CLAUDECODE", "DATABASE_URL_SYSTEM"):
        monkeypatch.setenv(k, "secret")
    r = run(provider(tmp_path).single_call(req()))
    assert r.provider == "claude_cli" and r.model == MODEL and r.stop_reason == "end_turn"
    assert json.loads(r.text) == {"ok": True, "scenario": "success"}
    assert r.cost_usd_micros == 123_400  # total_cost_usd * 1e6, notional
    assert r.usage.input_tokens == 1000 and r.usage.output_tokens == 1500
    rec = json.loads(env.read_text())
    assert rec["leaked"] == [] and "DATABASE_URL_SYSTEM" not in rec["env_names"]
    assert rec["prompt"] == "hi"
    assert Path(rec["cwd"]).parent.samefile(tmp_path / "scratch")
    assert rec["argv"][rec["argv"].index("--tools") + 1] == ""
    sysfile = Path(rec["argv"][rec["argv"].index("--system-prompt-file") + 1])
    assert not sysfile.exists()  # temp prompt cleaned up


@pytest.mark.parametrize("scenario", ["wrong_model", "key_leak", "tools_mismatch", "no_init", "mcp_present", "midstream_model"])
def test_init_assertions_kill_the_run(tmp_path, env, monkeypatch, scenario):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", scenario)
    pidfile = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_CLAUDE_CHILD_PIDFILE", str(pidfile))
    t0 = time.monotonic()
    with pytest.raises(CliRunFailed) as e:
        run(provider(tmp_path).single_call(req()))
    assert e.value.status == "guard" and time.monotonic() - t0 < 30
    if scenario == "wrong_model":
        assert wait_dead(int(pidfile.read_text()))  # the whole tree, not only the parent


def test_orphan_grandchild_holding_stdout_cannot_hang_the_read_loop(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "orphan")
    pidfile = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_CLAUDE_CHILD_PIDFILE", str(pidfile))
    t0 = time.monotonic()
    with pytest.raises(CliRunFailed):
        run(provider(tmp_path).single_call(req()))
    assert time.monotonic() - t0 < 30
    assert wait_dead(int(pidfile.read_text()))


def test_search_cap_breach_kills_the_run(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "too_many_searches")
    with pytest.raises(CliRunFailed) as e:
        run(provider(tmp_path).agent_run(req(max_searches=2, max_fetches=2)))
    assert e.value.status == "cap_exceeded"
    assert e.value.run.searches == 3


def test_fetch_cap_breach(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "too_many_fetches")
    with pytest.raises(CliRunFailed) as e:
        run(provider(tmp_path).agent_run(req(max_searches=2, max_fetches=1)))
    assert e.value.status == "cap_exceeded" and e.value.run.fetches == 2


def test_blocked_fetch_in_stream_kills_the_run(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "blocked_fetch")
    t0 = time.monotonic()
    with pytest.raises(CliRunFailed) as e:
        run(provider(tmp_path).agent_run(req()))
    assert e.value.status == "blocked_domain" and time.monotonic() - t0 < 30
    assert "https://www.airbnb.co.kr/rooms/1" not in e.value.run.evidence.fetched


def test_watchdog_timeout_kills_the_tree(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "hang")
    pidfile = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_CLAUDE_CHILD_PIDFILE", str(pidfile))
    with pytest.raises(CliRunFailed) as e:
        run(provider(tmp_path).agent_run(req(timeout_s=1.5)))
    assert e.value.status == "timeout"
    assert wait_dead(int(pidfile.read_text()))


def test_default_watchdog_is_eight_minutes():
    assert cc.WATCHDOG_SECONDS == 8 * 60


def test_cancel_kills_the_tree(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "hang")
    pidfile = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_CLAUDE_CHILD_PIDFILE", str(pidfile))
    flag = threading.Event()
    threading.Timer(2.0, flag.set).start()
    with pytest.raises(CliRunFailed) as e:
        run(provider(tmp_path).agent_run(req(is_cancelled=flag.is_set)))
    assert e.value.status == "cancelled"
    assert wait_dead(int(pidfile.read_text()))


def test_agent_run_collects_evidence_counters_and_allows_haiku_summaries(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "haiku_summary")
    p = provider(tmp_path)
    r = ProviderRequest(model="claude-sonnet-5-5", messages=[{"role": "user", "content": "go"}], max_tokens=1, system="s")
    out = run(p.agent_run(r))
    assert out.stop == "end_turn" and out.cost_usd_micros == 123_400
    assert out.result.provider == "claude_cli" and out.usage.web_searches == 1
    ev = p.last_run.evidence
    assert ev.fetched == {"https://zipair.net/en/sale"}
    assert ev.found == {"https://zipair.net/en/sale", "https://b.example/p"}
    a = json.loads(env.read_text())["argv"]
    assert a[a.index("--tools") + 1] == "WebSearch,WebFetch" and a[a.index("--allowedTools") + 1] == "WebSearch"
    assert "--json-schema" not in a
    assert len(p.last_run.events) >= 6  # stream events kept for run_events


def test_turn_and_budget_stops_map_to_outcome_stops(tmp_path, env, monkeypatch):
    for scenario, stop in (("max_turns", "turn_limit"), ("budget", "spend_limit")):
        monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", scenario)
        assert run(provider(tmp_path).agent_run(req())).stop == stop


def test_crash_and_auth_error_are_explained(tmp_path, env, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "crash")
    with pytest.raises(CliRunFailed, match="boom"):
        run(provider(tmp_path).single_call(req()))
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "auth_error")
    with pytest.raises(CliRunFailed, match="isn't signed in"):
        run(provider(tmp_path).single_call(req()))


def test_missing_binary_is_reported(tmp_path):
    p = ClaudeCliProvider(settings(tmp_path), bind_host="127.0.0.1", claude=["no-such-claude-binary"])
    with pytest.raises(CliRunFailed, match="start"):
        run(p.single_call(req()))


def test_scratch_dirs_are_pruned(tmp_path, env):
    root = tmp_path / "scratch"
    root.mkdir()
    for i in range(40):
        (root / f"old{i}").mkdir()
    run(provider(tmp_path).single_call(req()))
    assert len([d for d in root.iterdir() if d.is_dir()]) <= cc.KEEP_RUN_DIRS


# --- ai-smoke ------------------------------------------------------------------------------


def test_smoke_makes_one_no_tool_and_one_capped_web_call(tmp_path, env):
    lines: list[str] = []
    assert run_smoke(provider(tmp_path), MODEL, lines.append) == 0
    text = "\n".join(lines)
    assert "no tools" in text and "web tools" in text
    a = json.loads(env.read_text())["argv"]  # the last call is the web one, with a budget
    assert "--max-budget-usd" in a and a[a.index("--tools") + 1] == "WebSearch,WebFetch"


def test_ai_smoke_command_refuses_unless_claude_cli_is_selected(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "fake")
    called = []
    monkeypatch.setattr(cc, "run_cli", lambda *a, **k: called.append(1))
    with pytest.raises(SystemExit) as e:
        cli.main(["ai-smoke"])
    assert "claude_cli" in str(e.value) and called == []
