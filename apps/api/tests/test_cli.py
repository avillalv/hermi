import sys

import pytest

from hermi import cli
from hermi.cli import uvicorn_kwargs


@pytest.mark.parametrize(
    ("platform", "loop"), [("win32", "asyncio:SelectorEventLoop"), ("linux", "auto")]
)
def test_loop_by_platform(monkeypatch, platform, loop):
    monkeypatch.setattr(sys, "platform", platform)
    assert uvicorn_kwargs()["loop"] == loop


def test_api_uses_port_from_settings(monkeypatch):
    import uvicorn

    monkeypatch.setenv("PORT", "9123")
    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: seen.update(kw))
    cli.api()
    assert seen["port"] == 9123 and seen["host"] == "127.0.0.1"


def test_api_exits_on_bad_config_without_starting(monkeypatch):
    import uvicorn

    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: pytest.fail("started"))
    with pytest.raises(SystemExit, match="Configuration refused"):
        cli.api()


def test_api_host_flag_binds_container_address(monkeypatch):
    import uvicorn

    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: seen.update(kw))
    cli.main(["api", "--host", "0.0.0.0"])
    assert seen["host"] == "0.0.0.0"


@pytest.mark.parametrize("cmd", ["worker", "scheduler"])
def test_placeholder_commands_exit_non_zero_with_a_pointer(cmd):
    with pytest.raises(SystemExit, match="arrives with WF-"):
        cli.main([cmd])
