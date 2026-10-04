# ruff: noqa: E501  (long comments and SQL)
"""Idempotency-Key middleware (04 section 1.6, 03 `idempotency_keys`).

Pure ASGI, innermost user middleware. Only POSTs from a signed-in active user are looked at: anything else
passes through and fails downstream (401 and so on). The claim row is committed before the handler runs, so a
second request with the same key sees `in_progress`. The response is stored for 24 hours.

Rules this file settles:
- A 5xx, a 429 or a raised exception releases the key (deletes the claim) so the client can retry with it.
- A non-JSON body (a stream) is not stored: the key is released.
- The body is buffered (at most MAX_BODY) so it can be hashed, then replayed to the handler.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hermi.db import request_transaction
from hermi.deps import _identity_user, verified_token
from hermi.errors import ApiError, problem

# 04 section 1.6 required list, as route templates relative to /v1. `*` matches the rest of the path.
# Routes that do not exist yet need no code: they match here once they are added.
REQUIRED_TEMPLATES = (
    "/trips/{id}/ai/*",
    "/trips/{id}/agent-runs",
    "/agent-runs/{id}/cancel",
    # shortcut: guests have no users row, so the middleware skips this route and does not enforce the key (ceiling).
    # Upgrade in the guest draft-day ticket, which keys on the App Attest key id.
    "/guest/ai/draft-day",
    "/trips/{id}/flights/live-search",
    "/trips/{id}/lodging/rental-search",
    "/trips/{id}/verify-plan",
    "/plan-verifications/{id}/check",
    "/notes/{id}/recheck",
    "/items/{id}/recheck",
    "/imports/paste",
    "/imports/ics-feed",
    "/imports/{id}/confirm",
    "/imports/{id}/changes/confirm",
    "/me/referral/redeem",
    "/credits/packs/claim",
    "/purchases/sync",
    "/purchases/restore",
    "/me/passes/{id}/bind",
)
log = logging.getLogger("hermi.idempotency")
API_PREFIX = "/v1"
MAX_BODY = 1024 * 1024  # 04 error table: JSON bodies over 1 MB are 413
RETRYABLE = {429}  # besides every 5xx
LEASE = (
    "5 minutes"  # an in_progress claim older than this is a crashed request and may be taken over
)
KEEP_HEADERS = (b"etag", b"location")  # stored beside the body and sent again on replay


def _compile(template: str) -> re.Pattern:
    parts = re.split(r"(\{[^}]+\}|\*)", template)
    rx = "".join(
        ".+" if p == "*" else "[^/]+" if p.startswith("{") else re.escape(p) for p in parts
    )
    return re.compile(rx)


_REQUIRED = tuple(_compile(t) for t in REQUIRED_TEMPLATES)


def is_required(path: str) -> bool:
    rel = path.removeprefix(API_PREFIX).rstrip("/") or "/"
    return any(p.fullmatch(rel) for p in _REQUIRED)


def request_hash(body: bytes) -> str:
    """sha256 of the canonical body: parsed JSON with sorted keys, else the raw bytes."""
    try:
        canon = json.dumps(
            json.loads(body), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    except ValueError:
        canon = body
    return hashlib.sha256(canon).hexdigest()


@dataclass
class _Claim:
    outcome: str  # "claimed" | "replay" | "in_progress" | "reused"
    status: int | None = None
    body: bytes = b""
    headers: dict | None = None


_CLAIM_SQL = text(
    "INSERT INTO idempotency_keys (user_id, key, method, path, request_hash) "
    "VALUES (:u, :k, :m, :p, :h) ON CONFLICT (user_id, key) DO NOTHING RETURNING 1"
)


def _claim(engine, user_id, key, method, path, digest) -> _Claim:
    args = {"u": user_id, "k": key, "m": method, "p": path, "h": digest}
    with request_transaction(engine, user_id) as s:
        s.execute(
            text(
                "DELETE FROM idempotency_keys WHERE user_id = :u AND key = :k AND (expires_at <= now() "
                f"OR (state = 'in_progress' AND created_at < now() - interval '{LEASE}'))"
            ),
            args,
        )
        if s.execute(_CLAIM_SQL, args).first():
            return _Claim("claimed")
        row = s.execute(
            text(
                "SELECT method, path, request_hash, state, status_code, response::text "
                "FROM idempotency_keys WHERE user_id = :u AND key = :k"
            ),
            args,
        ).first()
    if (
        row is None
    ):  # deleted between the insert and the read: treat as still running, the client retries
        return _Claim("in_progress")
    if (row[0], row[1], row[2].strip()) != (method, path, digest):
        return _Claim("reused")
    if row[3] != "completed":
        return _Claim("in_progress")
    stored = json.loads(row[5]) if row[5] else {}
    body = stored.get("body")
    return _Claim(
        "replay",
        row[4],
        b"" if body is None else json.dumps(body).encode(),
        stored.get("headers", {}),
    )


def _finish(
    engine, user_id, key, status: int | None, body: bytes, headers: dict | None = None
) -> None:
    """Store the response (status given) or release the key (status None).

    `response` holds {"body": <json or null>, "headers": {"etag": ..., "location": ...}}: the jsonb column has
    no room for headers and a migration is out of scope. Failures are logged: the row then expires or its lease runs out."""
    try:
        _write_finish(engine, user_id, key, status, body, headers or {})
    except Exception:
        log.exception("idempotency finish failed")


def _write_finish(engine, user_id, key, status, body, headers) -> None:
    with request_transaction(engine, user_id) as s:
        if status is None:
            s.execute(
                text("DELETE FROM idempotency_keys WHERE user_id = :u AND key = :k"),
                {"u": user_id, "k": key},
            )
        else:
            s.execute(
                text(
                    "UPDATE idempotency_keys SET state = 'completed', status_code = :c, response = CAST(:r AS jsonb) "
                    "WHERE user_id = :u AND key = :k"
                ),
                {
                    "u": user_id,
                    "k": key,
                    "c": status,
                    "r": json.dumps(
                        {"body": json.loads(body) if body else None, "headers": headers}
                    ),
                },
            )


class IdempotencyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        engine = getattr(scope["app"].state, "engine", None)
        raw_key = next((v for k, v in scope["headers"] if k == b"idempotency-key"), None)
        path = scope["path"]
        required = is_required(path)
        if engine is None or (raw_key is None and not required):
            return await self.app(scope, receive, send)

        request = Request(scope)
        try:
            user = await run_in_threadpool(lambda: _identity_user(request, verified_token(request)))
        except ApiError:
            user = None  # the route's own auth answers 401
        except Exception:  # noqa: BLE001
            # shortcut: any lookup failure (database down) skips idempotency for this request, so a retry is not protected.
            # Ceiling: one request unprotected. Upgrade when the route's own auth no longer repeats the same lookup.
            user = None
        if user is None or user.status != "active":
            return await self.app(scope, receive, send)

        def fail(status, code, detail, headers=None, **extra):
            r = problem(request, status, code, detail, **extra)
            r.headers.update(headers or {})
            return r

        key = raw_key.decode("latin-1").strip() if raw_key is not None else None
        if key is None:
            return await fail(400, "idempotency_key_required", "Send an Idempotency-Key header.")(
                scope, receive, send
            )
        if not 8 <= len(key) <= 128:
            r = fail(
                422,
                "validation_failed",
                "Some fields need another look.",
                errors=[
                    {
                        "field": "Idempotency-Key",
                        "code": "string_length",
                        "message": "Use 8 to 128 characters.",
                    }
                ],
            )
            return await r(scope, receive, send)

        body = b""
        while True:
            msg = await receive()
            if msg["type"] == "http.disconnect":
                return
            body += msg.get("body", b"")
            if len(body) > MAX_BODY:
                return await fail(413, "payload_too_large", "That request is too large.")(
                    scope, receive, send
                )
            if not msg.get("more_body"):
                break

        claim = await run_in_threadpool(
            _claim, engine, user.id, key, "POST", path, request_hash(body)
        )
        if claim.outcome == "reused":
            r = fail(
                422,
                "idempotency_key_reused",
                "That key was used for a different request. Use a new key.",
            )
            return await r(scope, receive, send)
        if claim.outcome == "in_progress":
            r = fail(
                409,
                "idempotency_in_progress",
                "That request is still running.",
                {"Retry-After": "1"},
            )
            return await r(scope, receive, send)
        if claim.outcome == "replay":
            ctype = "application/problem+json" if claim.status >= 400 else "application/json"
            r = Response(
                claim.body,
                claim.status,
                {**(claim.headers or {}), "Idempotent-Replay": "true"},
                ctype if claim.body else None,
            )
            return await r(scope, receive, send)

        sent = False

        async def replay_receive() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        start: Message | None = None
        chunks: list[bytes] = []

        async def capture(message: Message) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, replay_receive, capture)
        except BaseException:
            await run_in_threadpool(_finish, engine, user.id, key, None, None)
            raise
        status = start["status"] if start else 500
        payload = b"".join(chunks)
        storable = status < 500 and status not in RETRYABLE
        if storable and payload:
            try:
                json.loads(payload)
            except ValueError:
                storable = False
        kept = (
            {
                k.decode(): v.decode("latin-1")
                for k, v in start["headers"]
                if k.lower() in KEEP_HEADERS
            }
            if start
            else {}
        )
        await run_in_threadpool(
            _finish, engine, user.id, key, status if storable else None, payload, kept
        )
