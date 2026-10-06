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


@pytest.mark.parametrize(("argv", "demo"), [(["seed"], False), (["seed", "--demo"], True)])
def test_seed_subcommand_runs_the_seed(monkeypatch, argv, demo):
    seen = []
    monkeypatch.setattr(cli, "seed", lambda demo=False: seen.append(demo))
    cli.main(argv)
    assert seen == [demo]


def test_seed_exits_when_migration_url_missing(monkeypatch):
    from hermi import config

    monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "ROOT_ENV_FILE", config.ROOT_ENV_FILE.parent / "no-such.env")
    with pytest.raises(SystemExit, match="MIGRATION_DATABASE_URL"):
        cli.seed()


class _FakeEngine:
    def begin(self):
        from contextlib import nullcontext

        return nullcontext(type("C", (), {"exec_driver_sql": lambda self, sql: None})())


def _stub_seed_environment(monkeypatch, demo_fn):
    import sqlalchemy

    from hermi import config
    from hermi.seed import demo

    settings = type("S", (), {"require": lambda self, key: "postgresql://x/y"})()
    monkeypatch.setattr(config, "migration_database_url", lambda: "postgresql://x/y")
    monkeypatch.setattr(config, "load_settings", lambda **kw: settings)
    monkeypatch.setattr(sqlalchemy, "create_engine", lambda *a, **kw: _FakeEngine())
    monkeypatch.setattr(demo, "seed_demo", demo_fn)


def test_seed_demo_exits_with_the_refusal_message(monkeypatch):
    def refuse(*a, **kw):
        raise RuntimeError("hermi seed --demo is for local and ci databases only")

    _stub_seed_environment(monkeypatch, refuse)
    with pytest.raises(SystemExit, match="local and ci databases only"):
        cli.seed(demo=True)


def test_seed_demo_runs_the_demo_seed(monkeypatch, capsys):
    calls = []

    def ok(settings, *, system_url):
        calls.append(system_url)
        return {"demo_trips": 1, "sample_trips": 3}

    _stub_seed_environment(monkeypatch, ok)
    cli.seed(demo=True)
    assert calls == ["postgresql://x/y"]
    assert "3 sample trips" in capsys.readouterr().out


def test_access_log_is_off_so_invite_tokens_stay_out_of_logs():
    assert uvicorn_kwargs()["access_log"] is False
