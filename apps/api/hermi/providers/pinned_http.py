"""The real `Transport` for the SSRF guard: connects to the validated IP, keeps Host and SNI."""

import threading
from collections.abc import Callable, Iterator

import httpx

from hermi.providers import ProviderError
from hermi.security.ssrf import PinnedRequest, SsrfRefused


def _new_client() -> httpx.Client:
    # No redirects (the guard follows each hop), no env proxies, no keep-alive so every hop gets a
    # fresh TLS connection checked against its own SNI. One client per hop, so no cookie
    # carries over.
    return httpx.Client(
        follow_redirects=False,
        trust_env=False,
        limits=httpx.Limits(max_keepalive_connections=0),
    )


class _Response:
    def __init__(self, client, ctx, response, timer, fired) -> None:
        self._client, self._ctx, self._response = client, ctx, response
        self._timer, self._fired = timer, fired
        self.status = response.status_code
        self.headers = {k.lower(): v for k, v in response.headers.items()}

    def iter_raw(self) -> Iterator[bytes]:
        try:
            yield from self._response.iter_raw()
        except httpx.HTTPError as exc:
            if self._fired.is_set():
                raise SsrfRefused("timeout") from exc
            raise ProviderError(f"fetch failed: {type(exc).__name__}") from exc

    def close(self) -> None:
        self._timer.cancel()
        try:
            self._ctx.__exit__(None, None, None)
        finally:
            self._client.close()


class PinnedHttpTransport:
    def __init__(self, client_factory: Callable[[], httpx.Client] = _new_client) -> None:
        self._client_factory = client_factory

    def open(self, request: PinnedRequest) -> _Response:
        """Headers and body must finish within `request.read_timeout` in total: a watchdog closes
        the client when it runs out, because httpx timeouts apply to each read, not the whole."""
        client = self._client_factory()
        fired = threading.Event()

        def expire() -> None:
            fired.set()
            client.close()

        timer = threading.Timer(request.read_timeout, expire)
        timer.daemon = True
        timer.start()
        ip = f"[{request.ip}]" if ":" in request.ip else request.ip
        timeout = httpx.Timeout(
            request.read_timeout, connect=request.connect_timeout, read=request.read_timeout
        )
        ctx = client.stream(
            "GET",
            f"{request.scheme}://{ip}:{request.port}{request.target}",
            headers=request.headers,
            timeout=timeout,
            extensions={"sni_hostname": request.host},
        )
        try:
            return _Response(client, ctx, ctx.__enter__(), timer, fired)
        except Exception as exc:
            timer.cancel()
            client.close()
            if fired.is_set():
                raise SsrfRefused("timeout") from exc
            if isinstance(exc, httpx.HTTPError):
                raise ProviderError(f"fetch failed: {type(exc).__name__}") from exc
            raise
