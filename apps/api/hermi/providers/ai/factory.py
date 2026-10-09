"""AI_PROVIDER picks the backend. claude_cli is re-checked here on every call (06 section 2.7)."""

from typing import Any

from hermi.config import NotConfigured, Settings, claude_cli_allowed
from hermi.providers.ai.anthropic_api import AnthropicApiProvider, default_client
from hermi.providers.ai.base import AiProvider, ClaudeCliNotBuilt, ProviderRefused
from hermi.providers.ai.fake import FakeProvider


def get_provider(
    settings: Settings,
    user_email: str | None = None,
    *,
    bind_host: str,
    client: Any = None,
) -> AiProvider:
    match settings.ai_provider:
        case "fake":
            return FakeProvider()
        case "anthropic_api":
            if client is None:
                if not settings.anthropic_api_key:
                    raise NotConfigured("ANTHROPIC_API_KEY")
                client = default_client(settings.anthropic_api_key.get_secret_value())
            return AnthropicApiProvider(client)
        case "claude_cli":
            if not claude_cli_allowed(settings, bind_host, user_email):
                raise ProviderRefused(
                    "claude_cli is not allowed for this environment, host or user"
                )
            raise ClaudeCliNotBuilt("claude_cli backend lands in WF-131.2")
    raise ProviderRefused(f"unknown AI_PROVIDER {settings.ai_provider!r}")
