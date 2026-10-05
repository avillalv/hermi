"""Outbound address checks and the SSRF guard (02 section 5.4, 10 section 2.5).

The blocked-brand list is `BLOCKED_HOSTS` in `modules/ai/policy.py`. `SsrfGuard` is the only way
to fetch a user-supplied URL. It owns the rules; the socket work sits behind two seams (a
resolver and a `Transport`) so tests run with fakes and never touch the network. The real
transport, the only part that imports httpx, is `providers/pinned_http.py`.
"""

import ipaddress
import socket
import time
import zlib
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urljoin, urlsplit

from hermi.config import own_hosts as configured_own_hosts
from hermi.modules.ai.policy import BLOCKED_HOSTS, blocked_domain

__all__ = [
    "BLOCKED_HOSTS",
    "FEED_POLICY",
    "LINK_PREVIEW_POLICY",
    "FetchResult",
    "PinnedRequest",
    "PinnedResponse",
    "SsrfGuard",
    "SsrfPolicy",
    "SsrfRefused",
    "Transport",
    "is_blocked_host",
    "url_blocked",
]

MAX_URL_LENGTH = 2048
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
_SIX_TO_FOUR = ipaddress.ip_network("2002::/16")


def is_blocked_host(host: str) -> bool:
    return blocked_domain(host) is not None


def url_blocked(url: str) -> str | None:
    """The blocked brand of a URL's host, or None (also None for text that is not a URL)."""
    try:
        host = urlsplit(url.strip()).hostname
    except ValueError:
        return None
    return blocked_domain(host) if host else None


@dataclass(frozen=True)
class SsrfPolicy:
    """What one caller may fetch. Every caller states its own limits."""

    schemes: frozenset[str]
    ports: frozenset[int]
    connect_timeout: float
    total_timeout: float
    max_body_bytes: int
    max_redirects: int = 3
    # Extra brands refused besides BLOCKED_HOSTS (link preview denylist, 03 seed): registrable
    # labels such as "expedia" and exact-or-parent domains such as "hotels.com".
    denied_brands: tuple[str, ...] = ()
    denied_domains: tuple[str, ...] = ()


LINK_PREVIEW_POLICY = SsrfPolicy(
    schemes=frozenset({"https", "http"}),
    ports=frozenset({80, 443}),
    connect_timeout=3,
    total_timeout=5,
    max_body_bytes=1_000_000,
    denied_brands=("expedia",),
    denied_domains=("hotels.com",),
)
# For providers/feed_fetcher.py (WF-072).
FEED_POLICY = SsrfPolicy(
    schemes=frozenset({"https"}),
    ports=frozenset({443}),
    connect_timeout=5,
    total_timeout=15,
    max_body_bytes=2_000_000,
)


class SsrfRefused(Exception):
    """The guard refused a URL, a redirect hop or a response. `reason` is a short machine code."""

    def __init__(self, reason: str, *, blocked_brand: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.blocked_brand = blocked_brand


@dataclass(frozen=True)
class PinnedRequest:
    """One hop. The transport must connect to `ip`, send `host` as Host and SNI, and verify the
    certificate against `host`."""

    scheme: str
    host: str
    port: int
    ip: str
    target: str  # path and query
    headers: dict[str, str]
    connect_timeout: float
    read_timeout: float


class PinnedResponse(Protocol):
    status: int
    headers: dict[str, str]  # lower-case names

    def iter_raw(self) -> Iterator[bytes]:
        """Body bytes as sent (still compressed)."""

    def close(self) -> None: ...


class Transport(Protocol):
    def open(self, request: PinnedRequest) -> PinnedResponse: ...


Resolver = Callable[[str, int], list[str]]


def system_resolver(host: str, port: int) -> list[str]:
    return [str(info[4][0]) for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]


@dataclass(frozen=True)
class FetchResult:
    url: str
    status: int
    content_type: str
    body: bytes


def _is_ip_literal(host: str) -> bool:
    """True for any IP spelling: dotted, decimal, octal, hex, short forms and IPv6."""
    if ":" in host:
        return True
    try:
        socket.inet_aton(host)  # accepts 2130706433, 0x7f000001, 0177.0.0.1, 127.1
    except OSError:
        return host.rsplit(".", 1)[-1].isdigit() or host.lower().startswith("0x")
    return True


def is_public_ip(raw: str) -> bool:
    try:
        ip = ipaddress.ip_address(raw.split("%")[0])
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        embedded = ip.ipv4_mapped
        if embedded is None and ip in _NAT64:
            embedded = ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
        if embedded is None and ip in _SIX_TO_FOUR:
            embedded = ipaddress.IPv4Address((int(ip) >> 80) & 0xFFFFFFFF)
        if embedded is not None:
            return is_public_ip(str(embedded))
    return ip.is_global and not (ip.is_multicast or ip.is_unspecified or ip.is_reserved)


def _denied(host: str, policy: SsrfPolicy) -> str | None:
    brand = blocked_domain(host)
    if brand:
        return brand
    labels = host.lower().rstrip(".").split(".")
    for extra in policy.denied_brands:
        if extra in labels[:-1]:
            return extra
    for domain in policy.denied_domains:
        if ".".join(labels[-len(domain.split(".")) :]) == domain:
            return domain
    return None


def _decoder(encoding: str):
    if encoding in ("", "identity"):
        return None
    if encoding in ("gzip", "x-gzip"):
        return zlib.decompressobj(zlib.MAX_WBITS | 16)
    if encoding == "deflate":
        return zlib.decompressobj()
    raise SsrfRefused("unsupported_encoding")


@dataclass
class SsrfGuard:
    policy: SsrfPolicy
    transport: Transport
    resolver: Resolver = system_resolver
    clock: Callable[[], float] = time.monotonic
    # Hosts of our own API and web URLs (config.py), refused so a preview cannot reach ourselves.
    own_hosts: frozenset[str] = field(default_factory=configured_own_hosts)
    user_agent: str = "HermiLinkPreview/1.0"

    def validate(self, url: str) -> tuple[str, str, int, str, list[str]]:
        """Rules 1 to 3. Returns (scheme, host, port, target, public addresses)."""
        if len(url) > MAX_URL_LENGTH:
            raise SsrfRefused("url_too_long")
        try:
            parts = urlsplit(url.strip())
            port_in_url = parts.port
        except ValueError:
            raise SsrfRefused("bad_url") from None
        scheme = parts.scheme.lower()
        if scheme not in self.policy.schemes:
            raise SsrfRefused("bad_scheme")
        if parts.username is not None or parts.password is not None or "@" in parts.netloc:
            raise SsrfRefused("credentials_in_url")
        host = (parts.hostname or "").lower().rstrip(".")
        if not host:
            raise SsrfRefused("no_host")
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            raise SsrfRefused("bad_host") from None
        port = port_in_url or (443 if scheme == "https" else 80)
        if port not in self.policy.ports:
            raise SsrfRefused("bad_port")
        brand = _denied(host, self.policy)
        if brand:
            raise SsrfRefused("blocked_domain", blocked_brand=brand)
        if host in self.own_hosts:
            raise SsrfRefused("own_host")
        if _is_ip_literal(host):
            raise SsrfRefused("ip_literal")
        try:
            addresses = self.resolver(host, port)
        except OSError:
            raise SsrfRefused("dns_failed") from None
        if not addresses or not all(is_public_ip(a) for a in addresses):
            raise SsrfRefused("non_public_address")
        target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        return scheme, host, port, target, addresses

    def fetch(self, url: str) -> FetchResult:
        deadline = self.clock() + self.policy.total_timeout
        seen: set[str] = set()
        previous_scheme: str | None = None
        for _hop in range(self.policy.max_redirects + 1):
            if url in seen:
                raise SsrfRefused("redirect_loop")
            seen.add(url)
            scheme, host, port, target, addresses = self.validate(url)
            if previous_scheme == "https" and scheme != "https":
                raise SsrfRefused("https_downgrade")
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise SsrfRefused("timeout")
            request = PinnedRequest(
                scheme=scheme,
                host=host,
                port=port,
                ip=addresses[0],
                target=target,
                headers={"Host": host, "User-Agent": self.user_agent, "Accept-Encoding": "gzip"},
                connect_timeout=min(self.policy.connect_timeout, remaining),
                read_timeout=remaining,
            )
            response = self.transport.open(request)
            try:
                if response.status in _REDIRECT_STATUSES:
                    location = response.headers.get("location")
                    if not location:
                        raise SsrfRefused("bad_redirect")
                    url = urljoin(url, location)
                    previous_scheme = scheme
                    continue
                return FetchResult(
                    url=url,
                    status=response.status,
                    content_type=response.headers.get("content-type", ""),
                    body=self._read(response, deadline),
                )
            finally:
                response.close()
        raise SsrfRefused("too_many_redirects")

    def _read(self, response: PinnedResponse, deadline: float) -> bytes:
        """Stream the body, cut at the cap after decompression and at the total deadline."""
        cap = self.policy.max_body_bytes
        decoder = _decoder(response.headers.get("content-encoding", "").strip().lower())
        out = bytearray()
        for chunk in response.iter_raw():
            if self.clock() > deadline:
                raise SsrfRefused("timeout")
            if decoder is None:
                out += chunk
            else:
                try:
                    # max_length bounds memory: a bomb is never fully inflated.
                    out += decoder.decompress(chunk, cap + 1 - len(out))
                    while decoder.unconsumed_tail and len(out) <= cap:
                        out += decoder.decompress(decoder.unconsumed_tail, cap + 1 - len(out))
                except zlib.error:
                    raise SsrfRefused("bad_body") from None
            if len(out) > cap:
                raise SsrfRefused("body_too_large")
        if self.clock() > deadline:
            raise SsrfRefused("timeout")
        return bytes(out)
