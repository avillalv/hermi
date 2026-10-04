"""POST /v1/waitlist (WF-002). No table in Phase 1: a structured log line, in-memory dedupe."""

import ipaddress
import logging
import re
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from hermi.modules.notifications import email

log = logging.getLogger("hermi.waitlist")
router = APIRouter()
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
RATE_LIMIT, RATE_WINDOW_S = 5, 60
MAX_SEEN = 100_000  # shortcut: past this, new addresses are still served but no longer deduped
CONFIRM = "\n".join(
    [
        "You are on the Hermi waitlist. We will email you once when Hermi opens.",
        "Plan together. Know the fare.",
        "",
        "To be removed, reply to this email and we will delete your entry.",
        "Questions: support@hermi.world",
    ]
)
CONTROL_RE = re.compile("[" + chr(0) + "-" + chr(31) + chr(127) + "]")


class State:
    # shortcut: per-process memory, resets on restart and is not shared across instances.
    # Upgrade to Redis (or a table) when the API runs more than one instance.
    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        with self.lock:
            q = self.hits[ip]
            while q and now - q[0] > RATE_WINDOW_S:
                q.popleft()
            if len(q) >= RATE_LIMIT:
                return False
            q.append(now)
            for k in [k for k, d in self.hits.items() if not d or now - d[-1] > RATE_WINDOW_S]:
                del self.hits[k]
            return True

    def is_new(self, addr: str) -> bool:
        with self.lock:
            if addr in self.seen:
                return False
            if len(self.seen) < MAX_SEEN:
                self.seen.add(addr)
            return True


class WaitlistIn(BaseModel):
    email: str = Field(max_length=254)
    who: str = Field(default="", max_length=100)
    current_app: str = Field(default="", max_length=100)

    @field_validator("who", "current_app")
    @classmethod
    def _plain(cls, v: str) -> str:
        if CONTROL_RE.search(v):
            raise ValueError("control characters")
        return v.strip()

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email")
        return v


def client_ip(request: Request) -> str:
    """Socket peer, or when the peer is a trusted proxy the first untrusted X-Forwarded-For hop
    from the right (the left side is client-forgeable). Any invalid entry falls back to the peer."""
    peer = request.client.host if request.client else "unknown"
    try:
        nets = [
            ipaddress.ip_network(c.strip(), strict=False)
            for c in request.app.state.settings.trusted_proxy_cidrs.split(",")
            if c.strip()
        ]
        trusted = lambda ip: any(ip in n for n in nets)  # noqa: E731
        if not trusted(ipaddress.ip_address(peer)):
            return peer
        hops = request.headers.get("x-forwarded-for", "").split(",")
        for hop in reversed(hops):
            ip = ipaddress.ip_address(hop.strip())
            if not trusted(ip):
                return str(ip)
    except ValueError:
        pass
    return peer


@router.post("/v1/waitlist", status_code=202)
def join(body: WaitlistIn, request: Request) -> dict[str, str]:
    state: State = request.app.state.waitlist
    if not state.allow(client_ip(request)):
        raise HTTPException(429, "Too many requests. Try again in a minute.")
    if state.is_new(body.email):
        settings = request.app.state.settings
        log.info(
            "waitlist_signup",
            extra={"email": body.email, "who": body.who, "current_app": body.current_app},
        )
        # A provider outage must not lose or fail the signup; the log line is the record.
        for step, args in (
            (email.add_contact, ()),
            (email.send, ("You are on the Hermi waitlist", CONFIRM)),
        ):
            try:
                step(settings, body.email, *args)
            except Exception:
                log.exception("waitlist_%s_failed", step.__name__)
    return {"status": "ok"}


def register(app: FastAPI) -> None:
    app.state.waitlist = State()
    app.include_router(router)
