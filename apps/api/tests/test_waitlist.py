import json

import pytest
from fastapi.testclient import TestClient

from hermi.main import create_app
from hermi.modules.notifications import email as mail


@pytest.fixture
def outbox(monkeypatch, tmp_path):
    monkeypatch.setattr(mail, "OUTBOX_DIR", tmp_path / "outbox")
    monkeypatch.setenv("EMAIL_BACKEND", "file")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    return tmp_path / "outbox"


def post(client, email="sam@example.com", **extra):
    return client.post("/v1/waitlist", json={"email": email, **extra})


def test_accepts_valid_and_writes_confirmation(outbox):
    r = post(TestClient(create_app()), who="Friends", current_app="Spreadsheets")
    assert r.status_code == 202
    files = list(outbox.glob("*.json"))
    assert len(files) == 1
    msg = json.loads(files[0].read_text())
    assert msg["to"] == "sam@example.com"
    assert "waitlist" in msg["subject"].lower()


def test_logs_one_structured_entry(outbox, caplog):
    caplog.set_level("INFO")
    post(TestClient(create_app()), who="Family")
    entries = [r for r in caplog.records if r.getMessage() == "waitlist_signup"]
    assert len(entries) == 1
    assert entries[0].who == "Family"


@pytest.mark.parametrize("bad", ["", "nope", "a@b", "a b@example.com", "x" * 300 + "@example.com"])
def test_rejects_invalid_email(outbox, bad):
    assert post(TestClient(create_app()), bad).status_code == 422
    assert not list(outbox.glob("*.json")) if outbox.exists() else True


def test_dedupes_case_insensitive(outbox):
    c = TestClient(create_app())
    assert post(c, "Sam@Example.com").status_code == 202
    assert post(c, "sam@example.com").status_code == 202
    assert len(list(outbox.glob("*.json"))) == 1


def test_rate_limits_per_ip(outbox):
    c = TestClient(create_app())
    codes = [post(c, f"u{i}@example.com").status_code for i in range(7)]
    assert codes[:5] == [202] * 5
    assert codes[5:] == [429, 429]


def test_resend_contact_only_when_key_set(outbox, monkeypatch):
    calls = []
    monkeypatch.setattr(
        mail, "_resend_post", lambda key, path, body, **kw: calls.append((key, path, body))
    )
    post(TestClient(create_app()), "a@example.com")
    assert calls == []

    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_BACKEND", "resend")
    r = post(TestClient(create_app()), "b@example.com")
    assert r.status_code == 202
    assert ("re_test", "/contacts", {"email": "b@example.com", "unsubscribed": False}) in calls
    assert any(path == "/emails" for _, path, _ in calls)


def test_resend_failure_does_not_fail_signup(outbox, monkeypatch):
    def boom(*a):
        raise OSError("down")

    monkeypatch.setattr(mail, "_resend_post", boom)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    assert post(TestClient(create_app()), "c@example.com").status_code == 202


def test_signup_record_is_json_on_stderr_with_real_logging_setup(outbox, capsys):
    post(TestClient(create_app()), "log@example.com", who="Family")
    lines = [ln for ln in capsys.readouterr().err.splitlines() if "waitlist_signup" in ln]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["email"] == "log@example.com"
    assert rec["who"] == "Family"


def test_rejects_control_characters(outbox):
    c = TestClient(create_app())
    assert post(c, who="a" + chr(10) + "b").status_code == 422
    assert post(c, current_app="x" + chr(0)).status_code == 422


def test_forwarded_for_only_from_trusted_proxy(outbox, monkeypatch):
    # TestClient peer is "testclient", not an IP, so it is never trusted: XFF is ignored.
    c = TestClient(create_app())
    codes = [
        c.post(
            "/v1/waitlist",
            json={"email": f"u{i}@example.com"},
            headers={"x-forwarded-for": f"9.9.9.{i}"},
        )
        for i in range(6)
    ]
    assert codes[-1].status_code == 429

    from hermi.modules.notifications.waitlist import client_ip

    class Fake:
        client = type("C", (), {"host": "10.0.0.5"})()
        headers = {"x-forwarded-for": "203.0.113.7, 10.0.0.5"}
        app = type("A", (), {"state": type("S", (), {"settings": None})()})()

    default = "203.0.113.7, 10.0.0.5"
    for cidrs, want, hdr in (
        ("10.0.0.0/8", "203.0.113.7", default),
        ("10.0.0.0/8", "203.0.113.7", "1.1.1.1, 203.0.113.7, 10.0.0.5"),
        ("10.0.0.0/8", "10.0.0.5", "garbage, 10.0.0.5"),
        ("", "10.0.0.5", default),
        ("192.168.0.0/16", "10.0.0.5", default),
    ):
        Fake.app.state.settings = type("St", (), {"trusted_proxy_cidrs": cidrs})()
        Fake.headers = {"x-forwarded-for": hdr}
        assert client_ip(Fake) == want  # type: ignore[arg-type]
