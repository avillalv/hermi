"""Clients for external data sources. Only this package imports httpx (outbound-requests rule)."""

from hermi.config import NotConfigured


class ProviderError(RuntimeError):
    """An external service failed or returned something unusable."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# shortcut: providers take an httpx client from the caller, who must set an explicit timeout.
# Response size limits and the provider_calls row per outbound call arrive with the metering
# wiring (WF-043 and the cached fares module WF-030). Ceiling: until then calls are unmetered.

__all__ = ["NotConfigured", "ProviderError"]
