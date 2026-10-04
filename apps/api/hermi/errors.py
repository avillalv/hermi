"""RFC 9457 problem+json errors (04 section 1.4) and the X-Request-Id header (04 section 1.9)."""

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("hermi.errors")
PROBLEM_BASE = "https://api.hermi.world/problems/"
# Codes for statuses that Starlette or FastAPI raise by themselves. Our own errors carry their code.
STATUS_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    415: "unsupported_media_type",
    429: "rate_limited",
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, detail: str, headers: dict[str, str] | None = None):
        super().__init__(code)
        self.status, self.code, self.detail, self.headers = status, code, detail, headers or {}


class RequestIdMiddleware:
    """Pure ASGI, added last in main.py so it is outermost: CORS preflights carry the id too."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        try:
            rid = str(uuid.UUID(headers.get(b"x-request-id", b"").decode("latin-1")))
        except ValueError:
            rid = str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = rid

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                h = [(k, v) for k, v in message["headers"] if k.lower() != b"x-request-id"]
                message = {**message, "headers": [*h, (b"x-request-id", rid.encode())]}
            await send(message)

        await self.app(scope, receive, send_with_id)


def problem(request: Request, status: int, code: str, detail: str, **extra) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    body = {
        "type": PROBLEM_BASE + code,
        "title": code.replace("_", " ").capitalize(),
        "status": status,
        "code": code,
        "detail": detail,
        "instance": request.url.path,
        "request_id": request_id,
        **extra,
    }
    # The 500 handler runs outside the middleware stack, so the id is set here.
    return JSONResponse(
        body,
        status_code=status,
        media_type="application/problem+json",
        headers={"X-Request-Id": request_id} if request_id else None,
    )


def register(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(request: Request, exc: ApiError):
        r = problem(request, exc.status, exc.code, exc.detail)
        r.headers.update(exc.headers)
        return r

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = STATUS_CODES.get(
            exc.status_code, "bad_request" if exc.status_code < 500 else "internal_error"
        )
        r = problem(request, exc.status_code, code, str(exc.detail))
        r.headers.update(exc.headers or {})
        return r

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]),
                "code": e["type"],
                "message": e["msg"],
            }
            for e in exc.errors()
        ]
        return problem(
            request, 422, "validation_failed", "Some fields need another look.", errors=errors
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")  # the stack stays in the log, never in the body
        return problem(
            request, 500, "internal_error", "Something went wrong on our side. Try again."
        )
