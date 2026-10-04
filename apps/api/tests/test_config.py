import re
from pathlib import Path

import pytest

from hermi.config import (
    ConfigError,
    NotConfigured,
    Settings,
    claude_cli_allowed,
    load_settings,
    refuse_tests_in_production,
)

ROOT = Path(__file__).resolve().parents[3]

# Everything a hosted environment needs besides the mode switches.
SECRETS = {
    "DATABASE_URL": "postgresql+psycopg://a:s3cretA@db/hermi",
    "DATABASE_URL_SYSTEM": "postgresql+psycopg://b:s3cretB@db/hermi",
    "DATABASE_URL_ADMIN": "postgresql+psycopg://c:s3cretC@db/hermi",
    "FIELD_ENCRYPTION_KEY": "s3cretD",
    "ADMIN_SESSION_SECRET": "s3cretE",
    "UNSUBSCRIBE_SECRET": "s3cretF",
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_JWKS_URL": "https://abc.supabase.co/jwks",
    "SUPABASE_JWT_ISSUER": "https://abc.supabase.co/auth/v1",
    "SUPABASE_JWT_AUDIENCE": "authenticated",
    "RESEND_API_KEY": "re_s3cretG",
    "CF_ACCESS_TEAM_DOMAIN": "hermi.cloudflareaccess.com",
    "CF_ACCESS_AUD": "aud",
    "R2_ACCOUNT_ID": "acct",
    "R2_ACCESS_KEY_ID": "r2id",
    "R2_SECRET_ACCESS_KEY": "s3cretR2",
    "R2_ENDPOINT_URL": "https://acct.r2.cloudflarestorage.com",
    "R2_BUCKET_UPLOADS": "up",
    "R2_BUCKET_EXPORTS": "ex",
    "R2_BUCKET_BACKUPS": "bk",
}
HOSTED_MODES = {
    "AUTH_MODE": "supabase",
    "ADMIN_AUTH_MODE": "cf_access",
    "STORAGE_BACKEND": "r2",
    "EMAIL_BACKEND": "resend",
    "PROVIDERS_MODE": "live",
    "AI_PROVIDER": "anthropic_api",
    "ANTHROPIC_API_KEY": "sk-ant-s3cretH",
}
HOSTED = ["preview", "staging", "production"]


def hosted(environment="staging", **over):
    return {"ENVIRONMENT": environment, **SECRETS, **HOSTED_MODES, **over}


@pytest.fixture
def load(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)

    def _load(env=None, bind_host="127.0.0.1", **kw):
        monkeypatch.setenv("ENVIRONMENT", "local")
        for k, v in (env or {}).items():
            monkeypatch.setenv(k, v)
        return load_settings(env_file=None, bind_host=bind_host, **kw)

    return _load


def refused(load, env, *names, **kw):
    with pytest.raises(ConfigError) as e:
        load(env, **kw)
    for n in names:
        assert n in str(e.value)
    return str(e.value)


# settings matrix


def test_local_defaults_need_no_keys(load):
    s = load()
    assert s.environment == "local"
    assert (s.auth_mode, s.admin_auth_mode) == ("dev", "dev")
    assert (s.storage_backend, s.email_backend) == ("local", "file")
    assert (s.providers_mode, s.import_sandbox) == ("fake", "timeout_only")
    assert s.port == 8100 and s.scheduler_enabled is False
    assert s.worker_concurrency_ai == 2 and s.ai_global_daily_cap_usd == 150


def test_typed_values_and_empty_means_default(load):
    s = load({"PORT": "9000", "SCHEDULER_ENABLED": "true", "ANTHROPIC_API_KEY": ""})
    assert s.port == 9000 and s.scheduler_enabled is True
    assert s.anthropic_api_key is None


def test_bad_type_error_names_the_variable_not_the_value(load):
    msg = refused(load, {"PORT": "not-a-port-9x9"}, "PORT")
    assert "not-a-port-9x9" not in msg


def test_ci_allows_dev_modes(load):
    s = load({"ENVIRONMENT": "ci", "AI_PROVIDER": "fake"})
    assert s.auth_mode == "dev" and s.providers_mode == "fake"


@pytest.mark.parametrize("environment", HOSTED)
def test_hosted_environments_load_with_secrets(load, environment):
    s = load(hosted(environment))
    assert s.environment == environment
    assert s.require("anthropic_api_key") == "sk-ant-s3cretH"


def test_unknown_environment_refused(load):
    refused(load, {"ENVIRONMENT": "prod"}, "ENVIRONMENT")


def test_missing_environment_is_refused(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    with pytest.raises(ConfigError, match="ENVIRONMENT"):
        load_settings(env_file=None, bind_host="127.0.0.1")


def test_process_env_overrides_dotenv(tmp_path, monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    f = tmp_path / ".env"
    f.write_text("ENVIRONMENT=local\nPORT=1111\nLOG_LEVEL=WARNING\nVITE_APP_ENV=local\nPG_BIN=x\n")
    monkeypatch.setenv("PORT", "2222")
    s = load_settings(env_file=f, bind_host="127.0.0.1")
    assert s.port == 2222 and s.log_level == "WARNING"


# production and tests


def test_tests_refuse_to_run_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ConfigError, match="production"):
        refuse_tests_in_production()


def test_tests_refuse_production_set_in_dotenv(monkeypatch, tmp_path):
    f = tmp_path / ".env"
    f.write_text("ENVIRONMENT=production\n")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setattr("hermi.config.ROOT_ENV_FILE", f)
    with pytest.raises(ConfigError, match="production"):
        refuse_tests_in_production()


def test_tests_run_in_local_and_ci(monkeypatch):
    for e in ("local", "ci"):
        monkeypatch.setenv("ENVIRONMENT", e)
        refuse_tests_in_production()


# required secrets


@pytest.mark.parametrize("environment", HOSTED)
def test_missing_secrets_listed_by_name_only(load, environment):
    env = hosted(environment)
    for n in ("DATABASE_URL", "FIELD_ENCRYPTION_KEY", "RESEND_API_KEY"):
        del env[n]
    msg = refused(load, env, "DATABASE_URL", "FIELD_ENCRYPTION_KEY", "RESEND_API_KEY")
    assert "s3cret" not in msg


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_staging_and_production_need_anthropic_key(load, environment):
    env = hosted(environment)
    del env["ANTHROPIC_API_KEY"]
    refused(load, env, "ANTHROPIC_API_KEY")


def test_keyless_provider_raises_not_configured(load):
    with pytest.raises(NotConfigured, match="ANTHROPIC_API_KEY"):
        load().require("anthropic_api_key")


def test_secrets_are_masked_in_repr(load):
    assert "s3cret" not in repr(load(hosted()))


def test_public_dict_excludes_every_secret(load):
    s = load(hosted())
    d = s.public_dict()
    fields = Settings.model_fields.items()
    secret_fields = {n for n, f in fields if "SecretStr" in str(f.annotation)}
    assert secret_fields and not secret_fields & d.keys()
    assert "s3cret" not in repr(d) and d["environment"] == "staging"


def test_scheduled_agents_stay_off(load):
    assert load({"SCHEDULER_ENABLED": "true"}).scheduled_agents_enabled is False


# refusal matrix: one test per rule


@pytest.mark.parametrize("environment", HOSTED)
def test_refuses_auth_mode_dev(load, environment):
    refused(load, hosted(environment, AUTH_MODE="dev"), "AUTH_MODE")


@pytest.mark.parametrize("environment", HOSTED)
def test_refuses_admin_auth_mode_dev(load, environment):
    refused(load, hosted(environment, ADMIN_AUTH_MODE="dev"), "ADMIN_AUTH_MODE")


@pytest.mark.parametrize("environment", HOSTED)
def test_refuses_local_storage(load, environment):
    refused(load, hosted(environment, STORAGE_BACKEND="local"), "STORAGE_BACKEND")


@pytest.mark.parametrize("backend", ["console", "file"])
def test_refuses_email_backend_other_than_resend(load, backend):
    refused(load, hosted(EMAIL_BACKEND=backend), "EMAIL_BACKEND")


@pytest.mark.parametrize("environment", HOSTED)
def test_refuses_fake_providers(load, environment):
    refused(load, hosted(environment, PROVIDERS_MODE="fake"), "PROVIDERS_MODE")


# claude_cli guard


def cli_env(**over):
    return {"ENVIRONMENT": "local", "AI_PROVIDER": "claude_cli", **over}


def test_claude_cli_allowed_locally_with_dev_auth(load):
    assert claude_cli_allowed(load(cli_env()), bind_host="127.0.0.1")


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_claude_cli_loopback_hosts(load, host):
    assert load(cli_env(), bind_host=host).ai_provider == "claude_cli"


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.5", "::", "example.com"])
def test_claude_cli_refused_off_loopback(load, host):
    refused(load, cli_env(), "AI_PROVIDER", bind_host=host)


@pytest.mark.parametrize("environment", ["ci", "preview", "staging", "production"])
def test_claude_cli_refused_outside_local(load, environment):
    if environment == "ci":
        env = {"ENVIRONMENT": "ci", "AI_PROVIDER": "claude_cli"}
    else:
        env = hosted(environment, AI_PROVIDER="claude_cli")
    refused(load, env, "AI_PROVIDER")


def test_claude_cli_with_supabase_auth_needs_allowlist(load):
    env = cli_env(AUTH_MODE="supabase", SUPABASE_URL="https://abc.supabase.co")
    refused(load, env, "AI_PROVIDER")
    s = load({**env, "AI_CLI_ALLOWED_EMAILS": "Me@Example.com, other@example.com"})
    assert claude_cli_allowed(s, "127.0.0.1", "me@example.com")
    assert not claude_cli_allowed(s, "127.0.0.1", "stranger@example.com")
    assert not claude_cli_allowed(s, "127.0.0.1", None)


def test_claude_cli_recheck_per_call_fails_off_loopback_or_other_provider(load):
    s = load(cli_env())
    assert not claude_cli_allowed(s, "0.0.0.0")
    assert not claude_cli_allowed(load({"AI_PROVIDER": "fake"}), "127.0.0.1")


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_hosted_refuses_provider_other_than_anthropic_api(load, environment):
    refused(load, hosted(environment, AI_PROVIDER="fake"), "AI_PROVIDER")


# .env.example


def example_names():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    return re.findall(r"^([A-Z][A-Z0-9_]*)=", text, re.M)


def test_env_example_matches_config():
    names = example_names()
    assert len(names) == len(set(names)), "duplicate variable in .env.example"
    fields = {f.upper() for f in Settings.model_fields}
    client_only = {n for n in names if n.startswith("VITE_")}
    assert fields - set(names) == set(), "in config.py but not .env.example"
    assert set(names) - fields - client_only == set(), "in .env.example but not config.py"


def test_env_example_loads_as_local_ready(monkeypatch):
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
    s = load_settings(env_file=ROOT / ".env.example", bind_host="127.0.0.1")
    assert s.environment == "local" and s.ai_provider == "claude_cli"


def test_create_app_ignores_root_env_when_process_env_forces_fake(tmp_path, monkeypatch):
    from hermi import config
    from hermi.main import create_app

    env = tmp_path / "root.env"
    env.write_text("AI_PROVIDER=claude_cli\n")
    monkeypatch.setattr(config, "ROOT_ENV_FILE", env)
    monkeypatch.setenv("AI_PROVIDER", "fake")
    assert config.load_settings(bind_host="0.0.0.0").ai_provider == "fake"
    create_app()
