"""Typed settings. The only place environment variables are read (02 section 7).

The process environment beats `.env`. Errors list variable names, never values.
"""

import os
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
LOCAL_ENVIRONMENTS = frozenset({"local", "ci"})

Environment = Literal["local", "ci", "preview", "staging", "production"]

# Needed (non-empty) outside local and ci. Staging and production add ANTHROPIC_API_KEY.
HOSTED_REQUIRED = (
    "DATABASE_URL",
    "DATABASE_URL_SYSTEM",
    "DATABASE_URL_ADMIN",
    "FIELD_ENCRYPTION_KEY",
    "ADMIN_SESSION_SECRET",
    "UNSUBSCRIBE_SECRET",
    "SUPABASE_URL",
    "SUPABASE_JWKS_URL",
    "SUPABASE_JWT_ISSUER",
    "SUPABASE_JWT_AUDIENCE",
    "RESEND_API_KEY",
    "CF_ACCESS_TEAM_DOMAIN",
    "CF_ACCESS_AUD",
    # Hosted environments force STORAGE_BACKEND=r2.
    "R2_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT_URL",
    "R2_BUCKET_UPLOADS",
    "R2_BUCKET_EXPORTS",
    "R2_BUCKET_BACKUPS",
)


class ConfigError(Exception):
    """Configuration refused. The message holds variable names, never values."""


class NotConfigured(Exception):
    """An optional key is empty, so its provider cannot run."""


class Settings(BaseSettings):
    # Field names are the variable names in lower case. Keep this list and .env.example equal
    # (a test checks it). VITE_* client variables live only in .env.example.
    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    # Core
    environment: Environment  # required, no default: a missing value must not mean local
    release_sha: str = "dev"
    log_level: str = "DEBUG"
    port: int = 8100
    public_api_url: str = "http://127.0.0.1:8100"
    public_web_url: str = "http://localhost:5173"
    cors_allowed_origins: str = "http://localhost:5173"
    trusted_proxy_cidrs: str = ""
    api_docs_enabled: bool = True
    scheduler_enabled: bool = False
    worker_lanes: str = "api,ai,notify,batch"
    worker_concurrency_api: int = 4
    worker_concurrency_ai: int = 2
    worker_concurrency_notify: int = 4
    worker_concurrency_batch: int = 1

    # Database
    database_url: SecretStr | None = None
    database_url_system: SecretStr | None = None
    database_url_admin: SecretStr | None = None
    migration_database_url: SecretStr | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 2
    database_statement_timeout_ms: int = 15000
    test_database_url: SecretStr | None = None
    test_database_url_system: SecretStr | None = None
    test_migration_database_url: SecretStr | None = None
    redis_url: SecretStr | None = None

    # Identity and device trust
    auth_mode: Literal["supabase", "dev"] = "dev"
    supabase_url: str | None = None
    supabase_jwks_url: str | None = None
    supabase_jwt_issuer: str | None = None
    supabase_jwt_audience: str | None = None
    supabase_service_role_key: SecretStr | None = None
    supabase_auth_hook_secret: SecretStr | None = None
    apple_team_id: str | None = None
    apple_bundle_id: str | None = None
    apple_signin_key_id: str | None = None
    apple_signin_private_key: SecretStr | None = None
    apple_app_attest_env: str | None = None
    field_encryption_key: SecretStr | None = None

    # AI
    ai_provider: Literal["anthropic_api", "claude_cli", "fake"] = "fake"
    anthropic_api_key: SecretStr | None = None
    anthropic_admin_api_key: SecretStr | None = None
    ai_cli_allowed_emails: str = ""
    ai_cli_max_concurrency: int = 1
    ai_cli_scratch_dir: str = ".data/ai-scratch"
    claude_cli_path: str | None = None
    ai_model_fast: str = "claude-haiku-4-5"
    ai_model_main: str = "claude-sonnet-5-5"
    ai_global_daily_cap_usd: float = 150
    ai_alert_daily_multiplier: float = 1.5
    prompt_version: str = "dev"
    evals_live: bool = False

    # Payments
    revenuecat_webhook_secret: SecretStr | None = None
    revenuecat_api_key: SecretStr | None = None

    # Modes and backends
    providers_mode: Literal["fake", "live"] = "fake"
    storage_backend: Literal["local", "r2"] = "local"
    email_backend: Literal["console", "file", "resend"] = "file"
    import_sandbox: Literal["strict", "timeout_only"] = "timeout_only"

    # Data, affiliate and travel providers
    travelpayouts_token: SecretStr | None = None
    travelpayouts_marker: str | None = None
    viator_api_key: SecretStr | None = None
    stay22_aid: str = "hermi"
    serpapi_api_key: SecretStr | None = None
    serpapi_monthly_cap: int = 5000
    geoapify_api_key: SecretStr | None = None
    wikimedia_contact: str = "dev@localhost"
    frankfurter_base_url: str = "https://api.frankfurter.dev"

    # Messaging, storage, observability
    resend_api_key: SecretStr | None = None
    resend_webhook_secret: SecretStr | None = None
    email_from: str = "Hermi <dev@localhost>"
    unsubscribe_secret: SecretStr | None = None
    apns_key_id: str | None = None
    apns_team_id: str | None = None
    apns_private_key: SecretStr | None = None
    apns_topic: str | None = None
    apns_use_sandbox: bool = True
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: SecretStr | None = None
    r2_endpoint_url: str | None = None
    r2_bucket_uploads: str | None = None
    r2_bucket_exports: str | None = None
    r2_bucket_backups: str | None = None
    sentry_dsn: str | None = None
    sentry_auth_token: SecretStr | None = None
    posthog_key: str | None = None
    posthog_host: str = "https://eu.i.posthog.com"
    betterstack_source_token: SecretStr | None = None
    betterstack_heartbeat_scheduler: SecretStr | None = None
    betterstack_heartbeat_queue: SecretStr | None = None
    alert_webhook_url: SecretStr | None = None

    # Admin
    admin_auth_mode: Literal["cf_access", "dev"] = "dev"
    cf_access_team_domain: str | None = None
    cf_access_aud: str | None = None
    admin_session_secret: SecretStr | None = None
    status_page_url: str | None = None

    @property
    def scheduled_agents_enabled(self) -> bool:
        # Scheduled agent runs are not part of Phase 1, whatever SCHEDULER_ENABLED says.
        return False

    @property
    def cli_allowed_emails(self) -> frozenset[str]:
        emails = (e.strip().lower() for e in self.ai_cli_allowed_emails.split(","))
        return frozenset(e for e in emails if e)

    def public_dict(self) -> dict:
        """Every field except secrets, safe to log or send to a client."""
        secret = {n for n, f in type(self).model_fields.items() if "SecretStr" in str(f.annotation)}
        return {k: v for k, v in self.model_dump().items() if k not in secret}

    def require(self, name: str) -> str:
        """Value of an optional key, or NotConfigured so its provider degrades."""
        value = getattr(self, name.lower())
        if isinstance(value, SecretStr):
            value = value.get_secret_value()
        if not value:
            raise NotConfigured(name.upper())
        return value


def claude_cli_allowed(s: Settings, bind_host: str, user_email: str | None = None) -> bool:
    """The claude_cli guard. Startup checks the host and the auth/allowlist rule; the provider
    factory calls this again per user. Auth mode dev admits everyone; otherwise the email must
    be on AI_CLI_ALLOWED_EMAILS."""
    if s.ai_provider != "claude_cli" or s.environment != "local":
        return False
    if bind_host.strip("[]").lower() not in LOOPBACK_HOSTS:
        return False
    if s.auth_mode == "dev":
        return True
    return bool(user_email) and user_email.strip().lower() in s.cli_allowed_emails


def _check(s: Settings, bind_host: str) -> None:
    bad: list[str] = []
    if s.environment not in LOCAL_ENVIRONMENTS:
        for name, value, ok in (
            ("AUTH_MODE", s.auth_mode, "supabase"),
            ("ADMIN_AUTH_MODE", s.admin_auth_mode, "cf_access"),
            ("STORAGE_BACKEND", s.storage_backend, "r2"),
            ("EMAIL_BACKEND", s.email_backend, "resend"),
            ("PROVIDERS_MODE", s.providers_mode, "live"),
        ):
            if value != ok:
                bad.append(f"{name} must be {ok} in {s.environment}")
        missing = [n for n in HOSTED_REQUIRED if not getattr(s, n.lower())]
        if s.environment in ("staging", "production"):
            if s.ai_provider != "anthropic_api":
                bad.append(f"AI_PROVIDER must be anthropic_api in {s.environment}")
            if not s.anthropic_api_key:
                missing.append("ANTHROPIC_API_KEY")
        if missing:
            bad.append("missing required: " + ", ".join(missing))
    if s.ai_provider == "claude_cli":
        # Everything but the per-user part; with allowlist auth the user is checked per call.
        if s.environment != "local":
            bad.append("AI_PROVIDER claude_cli needs ENVIRONMENT=local")
        elif bind_host.strip("[]").lower() not in LOOPBACK_HOSTS:
            bad.append("AI_PROVIDER claude_cli needs a loopback bind host")
        elif s.auth_mode != "dev" and not s.cli_allowed_emails:
            bad.append("AI_PROVIDER claude_cli needs AUTH_MODE=dev or AI_CLI_ALLOWED_EMAILS")
    if bad:
        raise ConfigError("Configuration refused: " + "; ".join(bad))


_ROOT = object()


def load_settings(*, bind_host: str, env_file: Path | str | None | object = _ROOT) -> Settings:
    """Load, type-check and refuse. Pass env_file=None to ignore .env. Default is the root .env."""
    if env_file is _ROOT:
        env_file = ROOT_ENV_FILE  # read at call time so tests can point it elsewhere
    try:
        s = Settings(_env_file=env_file)
    except ValidationError as e:
        # pydantic errors echo input values; list only the variable names.
        names = sorted({str(err["loc"][0]).upper() for err in e.errors() if err["loc"]})
        raise ConfigError("Invalid configuration: " + ", ".join(names)) from None
    _check(s, bind_host)
    return s


def refuse_tests_in_production() -> None:
    # The process environment wins over the root .env, as in Settings. Values are never printed.
    env = os.environ.get("ENVIRONMENT") or dotenv_values(ROOT_ENV_FILE).get("ENVIRONMENT") or ""
    if env.strip().lower() == "production":
        raise ConfigError("Tests refuse to run when ENVIRONMENT=production")


def migration_database_url() -> str:
    """The migration login URL (hermi_migrate_login). Process env beats .env. Raises ConfigError."""
    url = os.environ.get("MIGRATION_DATABASE_URL") or dotenv_values(ROOT_ENV_FILE).get(
        "MIGRATION_DATABASE_URL"
    )
    if not url:
        raise ConfigError(
            "MIGRATION_DATABASE_URL is not set. Run npm run setup, then npm run db:init."
        )
    return url


def own_hosts() -> frozenset[str]:
    """Hostnames of our own API and web URLs. The SSRF guard refuses to fetch them."""
    from urllib.parse import urlsplit

    file = dotenv_values(ROOT_ENV_FILE)
    hosts = set()
    for name, default in (
        ("PUBLIC_API_URL", Settings.model_fields["public_api_url"].default),
        ("PUBLIC_WEB_URL", Settings.model_fields["public_web_url"].default),
    ):
        host = urlsplit(os.environ.get(name) or file.get(name) or default).hostname
        if host:
            hosts.add(host.lower())
    return frozenset(hosts)
