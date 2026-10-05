"""SSRF guard and link preview (10 section 2.5). A fake resolver and a fake transport stand in for
DNS and sockets; the autouse fixture makes any real network call fail the test."""

import gzip
import socket
import threading

import httpx
import pytest

from hermi.providers import ProviderError
from hermi.providers.link_preview import BLOCKED_MESSAGE, fetch_link_preview
from hermi.providers.pinned_http import PinnedHttpTransport
from hermi.security.ssrf import (
    FEED_POLICY,
    LINK_PREVIEW_POLICY,
    PinnedRequest,
    SsrfGuard,
    SsrfPolicy,
    SsrfRefused,
)


def test_network_is_blocked_in_tests():
    with pytest.raises(AssertionError):
        socket.create_connection(("example.com", 80))
    with pytest.raises(AssertionError):
        socket.getaddrinfo("example.com", 80)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeResponse:
    def __init__(self, status=200, headers=None, chunks=(b"",), clock=None, tick=0.0):
        self.status = status
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self._chunks, self._clock, self._tick = chunks, clock, tick
        self.closed = False

    def iter_raw(self):
        for chunk in self._chunks:
            if self._clock:
                self._clock.now += self._tick
            yield chunk

    def close(self):
        self.closed = True


class FakeTransport:
    """Records every pinned request. `routes` maps host to a response (or a list, one per call)."""

    def __init__(self, routes):
        self.routes, self.requests = routes, []

    def open(self, request: PinnedRequest):
        self.requests.append(request)
        route = self.routes[request.host]
        if isinstance(route, list):
            return route.pop(0)
        return route


DNS = {
    "public.test": ["93.184.216.34"],
    "localtest.me": ["127.0.0.1"],
    "internal.test": ["10.0.0.5"],
    "flip.test": ["93.184.216.34", "10.0.0.5"],
    "mapped.test": ["::ffff:127.0.0.1"],
    "cgnat.test": ["100.64.0.1"],
    "v6.test": ["fd00::1"],
    "ok.test": ["93.184.216.34"],
}


def resolver(host, port):
    if host not in DNS:
        raise OSError("nxdomain")
    return DNS[host]


def guard(policy, routes, clock=None):
    transport = FakeTransport(routes)
    g = SsrfGuard(policy, transport, resolver=resolver, clock=clock or Clock())
    return g, transport


def redirect(location):
    return FakeResponse(302, {"Location": location})


def html(body=b"<html></html>", **kw):
    return FakeResponse(200, {"Content-Type": "text/html"}, [body], **kw)


POLICIES = [LINK_PREVIEW_POLICY, FEED_POLICY]
IDS = ["link_preview", "feed"]

# (url, routes factory taking the clock). Each must be refused for both policies.
HOSTILE = {
    "loopback v4": ("http://127.0.0.1/", lambda c: {}),
    "loopback v6": ("http://[::1]/", lambda c: {}),
    "metadata": ("http://169.254.169.254/latest/meta-data", lambda c: {}),
    "hex ip": ("http://0x7f000001/", lambda c: {}),
    "decimal ip": ("http://2130706433/", lambda c: {}),
    "octal ip": ("http://0177.0.0.1/", lambda c: {}),
    "localtest.me": ("http://localtest.me/", lambda c: {}),
    "gopher": ("gopher://public.test/", lambda c: {}),
    "file": ("file:///etc/passwd", lambda c: {}),
    "credentials": ("https://user:pass@public.test/", lambda c: {}),
    "port": ("https://public.test:8443/", lambda c: {}),
    "private dns": ("https://internal.test/", lambda c: {}),
    "public then private": ("https://flip.test/", lambda c: {}),
    "mapped v6": ("https://mapped.test/", lambda c: {}),
    "cgnat": ("https://cgnat.test/", lambda c: {}),
    "unique local v6": ("https://v6.test/", lambda c: {}),
    "too long": ("https://public.test/" + "a" * 2100, lambda c: {}),
    "redirect to private": (
        "https://public.test/",
        lambda c: {"public.test": redirect("https://internal.test/")},
    ),
    "redirect to metadata ip": (
        "https://public.test/",
        lambda c: {"public.test": redirect("http://169.254.169.254/")},
    ),
    "https to http": (
        "https://public.test/",
        lambda c: {"public.test": redirect("http://ok.test/"), "ok.test": html()},
    ),
    "redirect loop": (
        "https://public.test/a",
        lambda c: {"public.test": [redirect("/b"), redirect("/a"), redirect("/b")]},
    ),
    "too many redirects": (
        "https://public.test/0",
        lambda c: {"public.test": [redirect(f"/{i}") for i in range(1, 6)]},
    ),
    "oversized body": (
        "https://public.test/",
        lambda c: {"public.test": html(b"x" * 2_100_000)},
    ),
    "gzip bomb": (
        "https://public.test/",
        lambda c: {
            "public.test": FakeResponse(
                200,
                {"Content-Type": "text/html", "Content-Encoding": "gzip"},
                [gzip.compress(b"\0" * 5_000_000)],
            )
        },
    ),
    "never finishes": (
        "https://public.test/",
        lambda c: {
            "public.test": FakeResponse(
                200, {"Content-Type": "text/html"}, [b"x"] * 100, clock=c, tick=10
            )
        },
    ),
}


@pytest.mark.parametrize("policy", POLICIES, ids=IDS)
@pytest.mark.parametrize("name", list(HOSTILE))
def test_hostile_url_refused(name, policy):
    url, routes = HOSTILE[name]
    clock = Clock()
    g, transport = guard(policy, routes(clock), clock)
    with pytest.raises(SsrfRefused):
        g.fetch(url)
    # Nothing hostile was ever connected to.
    assert all(r.ip not in ("127.0.0.1", "10.0.0.5", "169.254.169.254") for r in transport.requests)


@pytest.mark.parametrize("name", list(HOSTILE))
def test_hostile_url_refused_through_link_preview(name):
    url, routes = HOSTILE[name]
    clock = Clock()
    g, _ = guard(LINK_PREVIEW_POLICY, routes(clock), clock)
    with pytest.raises(ProviderError):
        fetch_link_preview(url, guard=g)


@pytest.mark.parametrize(
    "url",
    [
        "https://airbnb.co.kr/rooms/1",
        "https://www.airbnb.co.uk/rooms/1",
        "https://vrbo.com/1",
        "https://secure.booking.com/x",
        "https://www.expedia.com/x",
        "https://www.hotels.com/x",
    ],
)
def test_brand_hosts_refused_without_a_request(url):
    g, transport = guard(LINK_PREVIEW_POLICY, {})
    result = fetch_link_preview(url, guard=g)
    assert result.blocked and result.message == BLOCKED_MESSAGE
    assert transport.requests == []


def test_redirect_to_brand_host_returns_blocked_result():
    g, transport = guard(
        LINK_PREVIEW_POLICY, {"public.test": redirect("https://www.airbnb.com/rooms/1")}
    )
    assert fetch_link_preview("https://public.test/", guard=g).blocked
    assert len(transport.requests) == 1


def test_lookalike_brand_is_not_refused():
    DNS["notairbnb.com"] = ["93.184.216.34"]
    try:
        g, _ = guard(LINK_PREVIEW_POLICY, {"notairbnb.com": html()})
        assert g.fetch("https://notairbnb.com/").status == 200
    finally:
        del DNS["notairbnb.com"]


def test_own_host_refused():
    g, _ = guard(LINK_PREVIEW_POLICY, {})
    g.own_hosts = frozenset({"public.test"})
    with pytest.raises(SsrfRefused):
        g.fetch("https://public.test/")


def test_connection_is_pinned_to_the_validated_ip():
    g, transport = guard(LINK_PREVIEW_POLICY, {"public.test": html()})
    g.fetch("https://public.test/page?q=1")
    (req,) = transport.requests
    assert req.ip == "93.184.216.34"
    assert req.host == "public.test" and req.headers["Host"] == "public.test"
    assert req.target == "/page?q=1" and req.port == 443
    assert (req.connect_timeout, req.read_timeout) == (3, 5)


def test_redirect_hops_are_revalidated_and_followed():
    g, transport = guard(
        LINK_PREVIEW_POLICY, {"public.test": redirect("https://ok.test/x"), "ok.test": html()}
    )
    result = g.fetch("https://public.test/")
    assert result.url == "https://ok.test/x"
    assert [r.host for r in transport.requests] == ["public.test", "ok.test"]


def test_gzip_body_under_cap_is_decoded():
    body = gzip.compress(b"<html>hi</html>")
    g, _ = guard(
        LINK_PREVIEW_POLICY,
        {"public.test": FakeResponse(200, {"Content-Encoding": "gzip"}, [body])},
    )
    assert g.fetch("https://public.test/").body == b"<html>hi</html>"


def test_happy_path_preview_parse():
    page = (
        b"<html><head><title> Fallback  title </title>"
        b'<meta property="og:title" content="Casa Verde">'
        b'<meta property="og:description" content="Two rooms\n by the sea">'
        b'<meta property="og:image" content="https://img.test/a.jpg">'
        b'<meta property="og:video" content="https://img.test/v.mp4">'
        b"</head><body><script>alert(1)</script></body></html>"
    )
    g, transport = guard(
        LINK_PREVIEW_POLICY,
        {"public.test": FakeResponse(200, {"Content-Type": "text/html; charset=utf-8"}, [page])},
    )
    result = fetch_link_preview("https://public.test/casa", guard=g)
    assert (result.title, result.description) == ("Casa Verde", "Two rooms by the sea")
    assert result.image_url == "https://img.test/a.jpg" and not result.blocked
    # The image URL is never fetched by the server.
    assert [r.host for r in transport.requests] == ["public.test"]


def test_title_fallback_and_non_html_refused():
    g, _ = guard(LINK_PREVIEW_POLICY, {"public.test": html(b"<title>Just a title</title>")})
    assert fetch_link_preview("https://public.test/", guard=g).title == "Just a title"
    g, _ = guard(
        LINK_PREVIEW_POLICY,
        {"public.test": FakeResponse(200, {"Content-Type": "application/pdf"}, [b"%PDF"])},
    )
    with pytest.raises(ProviderError):
        fetch_link_preview("https://public.test/", guard=g)


def test_real_transport_pins_ip_and_sends_sni_and_host():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["host"] = request.headers["host"]
        seen["sni"] = request.extensions.get("sni_hostname")
        return httpx.Response(200, content=iter([b"ok"]))

    transport = PinnedHttpTransport(
        lambda: httpx.Client(transport=httpx.MockTransport(handler))
    )
    req = PinnedRequest(
        "https", "public.test", 443, "93.184.216.34", "/p", {"Host": "public.test"}, 3, 5
    )
    response = transport.open(req)
    assert b"".join(response.iter_raw()) == b"ok"
    response.close()
    assert seen == {
        "url": "https://93.184.216.34/p",
        "host": "public.test",
        "sni": "public.test",
    }


class StalledTransport(httpx.BaseTransport):
    """A server that trickles nothing: the request blocks until the client is closed."""

    def __init__(self):
        self.closed = threading.Event()

    def handle_request(self, request):
        self.closed.wait(10)
        raise httpx.ReadError("closed")

    def close(self):
        self.closed.set()


def test_real_transport_enforces_the_total_deadline_on_stalled_headers():
    stalled = StalledTransport()
    transport = PinnedHttpTransport(lambda: httpx.Client(transport=stalled))
    g = SsrfGuard(LINK_PREVIEW_POLICY, transport, resolver=resolver)
    g.policy = SsrfPolicy(
        schemes=LINK_PREVIEW_POLICY.schemes,
        ports=LINK_PREVIEW_POLICY.ports,
        connect_timeout=1,
        total_timeout=0.3,
        max_body_bytes=1000,
    )
    with pytest.raises(SsrfRefused) as caught:
        g.fetch("https://public.test/")
    assert caught.value.reason == "timeout"


def test_link_preview_refuses_our_own_api_host_by_default(monkeypatch):
    monkeypatch.setenv("PUBLIC_API_URL", "https://api.hermi.test")
    transport = FakeTransport({})
    with pytest.raises(ProviderError, match="own_host"):
        fetch_link_preview("https://api.hermi.test/health", transport=transport)
    assert transport.requests == []
