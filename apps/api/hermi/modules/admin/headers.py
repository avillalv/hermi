# ruff: noqa: E501  (long comments)
"""Every /v1/admin response, errors included, is `noindex` and uncacheable (08 sections 2.1 and 9)."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

PREFIX = "/v1/admin"
ADMIN_HEADERS = ((b"x-robots-tag", b"noindex"), (b"cache-control", b"no-store"))


class AdminHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or not (path == PREFIX or path.startswith(PREFIX + "/")):
            return await self.app(scope, receive, send)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                names = {n for n, _ in ADMIN_HEADERS}
                kept = [(k, v) for k, v in message["headers"] if k.lower() not in names]
                message = {**message, "headers": [*kept, *ADMIN_HEADERS]}
            await send(message)

        await self.app(scope, receive, send_with_headers)
