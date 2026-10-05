# ruff: noqa: E501
"""WF-037: structured log context, redaction, request log by route template, Sentry scrub and init."""

import json
import logging
import re

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from sentry_sdk.transport import Transport

from hermi.config import Settings
from hermi.logging_setup import JsonFormatter, bind, clear_context, setup_logging
from hermi.main import create_app
from hermi.sentry_setup import init_sentry, scrub_event

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig_abc-123"
FEED = "https://calendar.example.com/ical/abcSECRETtoken123/basic.ics"
WEBCAL = "webcal://h.example/cal/SECRETwebcal77"
ICLOUD = "https://p12-caldav.icloud.com/published/2/SECRETicloud88"
EMAIL = "ana.perez+trip@example.com"
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _fmt(msg="x", level="INFO", **extra):
    r = logging.makeLogRecord({"msg": msg, "levelname": level, "levelno": getattr(logging, level), "name": "t", **extra})
    return json.loads(JsonFormatter().format(r))


@pytest.fixture(autouse=True)
def _ctx():
    clear_context()
    yield
    clear_context()


def test_context_fields_on_every_line():
    bind(request_id="r1", job_id="j1", run_id="u1", user_id="0190-opaque")
    out = _fmt()
    assert (out["request_id"], out["job_id"], out["run_id"], out["user_id"]) == (
        "r1", "j1", "u1", "0190-opaque",
    )


def test_no_context_means_no_fields():
    assert "request_id" not in _fmt()


def test_headers_redacted():
    out = _fmt(headers={"Authorization": "Bearer abc123tok", "x-api-key": "k", "X-Api-Key": "k2"})
    assert set(out["headers"].values()) == {"[redacted]"}


def test_emails_and_feed_urls_redacted_in_messages():
    out = _fmt(f"user {EMAIL} fetched {FEED} and webcal://h.example/a/b.ics?x=1 and /v1/calendar/tok123.ics")
    s = json.dumps(out)
    for bad in (EMAIL, "abcSECRETtoken123", "tok123", "webcal://h.example"):
        assert bad not in s


@pytest.mark.parametrize("level,hidden", [("INFO", True), ("WARNING", True), ("DEBUG", False)])
def test_prompts_and_feed_urls_only_at_debug(level, hidden):
    out = _fmt(level=level, prompt="Plan 3 days in Lisbon", feed_url="https://h.example/x")
    assert (out["prompt"] == "[redacted]") is hidden
    assert (out["feed_url"] == "[redacted]") is hidden


def test_log_scan_finds_no_emails_tokens_or_feed_urls(capsys):
    setup_logging("debug")
    bind(request_id="r1", user_id="0190-opaque")
    log = logging.getLogger("scan")
    log.info("hello %s", EMAIL, extra={"email_note": EMAIL})
    log.warning("auth Bearer abc123tok %s", JWT, extra={"headers": {"Authorization": "Bearer abc123tok"}})
    log.error("feed %s %s %s", FEED, WEBCAL, ICLOUD, extra={"prompt": "secret prompt text"})
    log.info("GET /v1/invites/INVTOKEN55 and /shared/SHRTOKEN66")
    try:
        raise ValueError(f"bad {EMAIL} {FEED}")
    except ValueError:
        log.exception("boom")
    err = capsys.readouterr().err
    assert err
    assert not EMAIL_RE.search(err)
    for bad in ("abc123tok", JWT, "abcSECRETtoken123", "basic.ics", "secret prompt text", "SECRETwebcal77", "SECRETicloud88", "INVTOKEN55", "SHRTOKEN66"):
        assert bad not in err


def _app(**kw):
    kw.setdefault("environment", "ci")
    app = create_app(Settings(_env_file=None, auth_mode="dev", release_sha="abc123d", **kw))

    @app.get("/probe/{item_id}")
    def probe(item_id: str):
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def test_request_log_uses_route_template_never_raw_path_or_query(capsys):
    c = TestClient(_app())
    r = c.get("/probe/SECRETTOKEN99?token=abc123tok&e=a@b.co")
    assert r.status_code == 200
    lines = [json.loads(x) for x in capsys.readouterr().err.splitlines() if x.startswith("{")]
    req = [x for x in lines if x.get("logger") == "hermi.request"]
    assert len(req) == 1
    assert req[0]["route"] == "/probe/{item_id}"
    assert req[0]["status"] == 200
    assert (req[0]["service"], req[0]["env"], req[0]["release"]) == ("api", "ci", "abc123d")
    assert isinstance(req[0]["latency_ms"], int)
    assert req[0]["bytes"] == len(r.content)
    assert "ms" not in req[0]
    assert req[0]["request_id"] == r.headers["x-request-id"]
    blob = json.dumps(req[0])
    assert "SECRETTOKEN99" not in blob and "abc123tok" not in blob and "a@b.co" not in blob


def test_unmatched_path_logs_placeholder(capsys):
    TestClient(_app()).get("/nope/SECRETTOKEN99")
    err = capsys.readouterr().err
    assert "SECRETTOKEN99" not in err


class Capture(Transport):
    def __init__(self, options=None):
        super().__init__(options)
        self.events = []

    def capture_envelope(self, envelope):
        if envelope.get_event():
            self.events.append(envelope.get_event())


def test_init_is_noop_without_dsn():
    assert init_sentry(None, release="r", environment="e") is False
    assert sentry_sdk.get_client().is_active() is False


def test_thrown_error_reaches_sentry_with_release_and_environment_scrubbed():
    t = Capture()
    assert init_sentry("https://k@o1.ingest.sentry.io/1", release="abc123d", environment="staging", transport=t)
    try:
        try:
            raise RuntimeError(f"fail for {EMAIL} at {FEED} Bearer abc123tok")
        except RuntimeError as e:
            sentry_sdk.capture_exception(e)
        sentry_sdk.flush()
        (ev,) = t.events
        assert ev["release"] == "abc123d"
        assert ev["environment"] == "staging"
        blob = json.dumps(ev)
        for bad in (EMAIL, "abcSECRETtoken123", "abc123tok"):
            assert bad not in blob
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.init()  # back to the no-op client


def test_scrub_event_strips_pii():
    ev = {
        "user": {"id": "0190", "email": EMAIL, "ip_address": "1.2.3.4", "username": "ana"},
        "request": {
            "url": "http://h/v1/invites/INVTOKEN55?token=zzz",
            "query_string": "token=zzz",
            "cookies": {"s": "1"},
            "data": {"prompt": "hi"},
            "headers": {"Authorization": "Bearer abc123tok", "x-api-key": "k", "accept": "*/*"},
        },
        "extra": {"prompt": "Plan Lisbon", "feed_url": FEED},
        "transaction": "/v1/invites/{token}",
        "message": f"{WEBCAL} {ICLOUD}",
        "breadcrumbs": {"values": [{"message": f"GET {FEED}"}]},
    }
    out = scrub_event(ev, {})
    blob = json.dumps(out)
    for bad in (EMAIL, "1.2.3.4", "INVTOKEN55", "SECRETwebcal77", "SECRETicloud88", "zzz", "abc123tok", "Plan Lisbon", "abcSECRETtoken123", '"ana"'):
        assert bad not in blob
    assert out["user"] == {"id": "0190"}
    assert out["request"]["headers"]["accept"] == "*/*"
    assert out["request"]["url"] == "/v1/invites/{token}"
    ev2 = {"request": {"url": "http://h/v1/invites/INVTOKEN55"}}
    assert "url" not in scrub_event(ev2, {})["request"]


def test_app_error_reaches_sentry_once_with_request_id_and_no_pii(monkeypatch, capsys):
    import hermi.main as main

    t = Capture()
    real = main.init_sentry
    monkeypatch.setattr(main, "init_sentry", lambda *a, **k: real(*a, transport=t, **k))
    app = _app(sentry_dsn="https://k@o1.ingest.sentry.io/1", environment="local")
    try:
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get(f"/boom?e={EMAIL}", headers={"Authorization": "Bearer abc123tok", "x-api-key": "k"})
        sentry_sdk.flush()
        assert r.status_code == 500
        assert len(t.events) == 1
        ev = t.events[0]
        assert (ev["release"], ev["environment"]) == ("abc123d", "local")
        assert ev["tags"]["request_id"] == r.headers["x-request-id"]
        blob = json.dumps(ev)
        for bad in (EMAIL, "abc123tok", "1.testclient"):
            assert bad not in blob
        assert "query_string" not in ev["request"]
    finally:
        sentry_sdk.get_client().close()
        sentry_sdk.init()
