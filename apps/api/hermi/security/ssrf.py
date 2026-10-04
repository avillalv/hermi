"""Outbound address checks. The blocked-brand list is `BLOCKED_HOSTS` in `modules/ai/policy.py`."""

from urllib.parse import urlsplit

from hermi.modules.ai.policy import BLOCKED_HOSTS, blocked_domain

__all__ = ["BLOCKED_HOSTS", "is_blocked_host", "url_blocked"]
# shortcut: brand check only. https/443, DNS and redirect rules (02 section 5.4) come with imports.


def is_blocked_host(host: str) -> bool:
    return blocked_domain(host) is not None


def url_blocked(url: str) -> str | None:
    """The blocked brand of a URL's host, or None (also None for text that is not a URL)."""
    try:
        host = urlsplit(url.strip()).hostname
    except ValueError:
        return None
    return blocked_domain(host) if host else None
