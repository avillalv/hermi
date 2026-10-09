# ruff: noqa: E501
"""WF-047: the notification service. Real PostgreSQL, the file mail backend, no network (conftest blocks it)."""

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import NotConfigured, Settings
from hermi.main import create_app
from hermi.modules.notifications import email, service, templates

EM, EN = chr(0x2014), chr(0x2013)  # the dashes the copy must never contain
SECRET = "unit-test-unsubscribe-secret"
NOW = datetime(2027, 3, 1, 15, 0, tzinfo=UTC)  # 10:00 in New York, 15:00 in London, 16:00 in Paris


@pytest.fixture
def settings(db_urls):
    return Settings(
        _env_file=None,
        environment="ci",
        database_url_system=db_urls["system"],
        email_backend="file",
        unsubscribe_secret=SECRET,
        public_web_url="https://app.test",
        public_api_url="https://api.test",
    )


@pytest.fixture
def outbox(monkeypatch, tmp_path):
    monkeypatch.setattr(email, "OUTBOX_DIR", tmp_path / "outbox")
    return tmp_path / "outbox"


@pytest.fixture
def postal(monkeypatch):
    monkeypatch.setattr(templates, "POSTAL_ADDRESS", "Hermi, 1 Example Street, Lisbon")


def mails(outbox):
    return [json.loads(p.read_text()) for p in sorted(outbox.glob("*.json"))] if outbox.exists() else []


@pytest.fixture
def session(db_urls):
    engine = db.make_engine(db_urls["system"])
    with Session(engine) as s:
        yield s
    engine.dispose()


@pytest.fixture
def user(make_user, system_conn):
    def make(tz="UTC", status="active"):
        uid, _ = make_user(status=status)
        system_conn.execute("UPDATE users SET timezone = %s WHERE id = %s", (tz, uid))
        return uid

    return make


def note(session, uid, kind="price_drop", key=None, trip_id=None, **kw):
    nid = service.create(session, user_id=uid, kind=kind, dedupe_key=key or uuid.uuid4().hex, title=kw.pop("title", "Lisbon fare fell"), body=kw.pop("body", "Now 368 euros on Example Air, seen today."), payload={"url": "/trips/x"}, trip_id=trip_id, **kw)
    session.commit()
    return nid


def row(system_conn, nid):
    return system_conn.execute("SELECT want_email, email_sent_at FROM notifications WHERE id = %s", (nid,)).fetchone()


def jobs_for(system_conn, nid):
    return system_conn.execute("SELECT scheduled_at FROM procrastinate_jobs WHERE task_name = 'send_email' AND args->>'notification_id' = %s ORDER BY id", (str(nid),)).fetchall()


def deliver(session, settings, nid, now=NOW):
    out = service.deliver_email(session, settings, nid, now=now)
    session.commit()
    return out


def trip(system_conn, owner, start=None, name="Lisbon"):
    return system_conn.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency, start_date, end_date) VALUES (%s, %s, 'USD', %s, %s) RETURNING id",
        (owner, name, start, start + timedelta(days=5) if start else None),
    ).fetchone()[0]


# --- dedupe: a retried job never sends twice ------------------------------------------------------------------------------


def test_same_dedupe_key_makes_one_row_and_one_job(session, system_conn, user):
    u = user()
    a = note(session, u, key="booked_drop:1:36800")
    b = note(session, u, key="booked_drop:1:36800")
    assert a is not None
    assert b is None
    assert system_conn.execute("SELECT count(*) FROM notifications WHERE user_id = %s", (u,)).fetchone() == (1,)
    assert len(jobs_for(system_conn, a)) == 1
    other = user()
    assert note(session, other, key="booked_drop:1:36800") is not None  # the key is unique per user


def test_a_retried_send_never_mails_twice(session, settings, outbox, system_conn, user):
    nid = note(session, user())
    assert [deliver(session, settings, nid) for _ in range(3)] == ["sent", "already_sent", "already_sent"]
    assert len(mails(outbox)) == 1
    assert row(system_conn, nid)[1] is not None


def test_a_failed_send_rolls_back_so_the_retry_sends(session, settings, outbox, system_conn, user, monkeypatch):
    nid = note(session, user())

    def boom(*a, **k):
        raise TimeoutError("resend down")

    monkeypatch.setattr(email, "send", boom)
    with pytest.raises(TimeoutError):
        service.deliver_email(session, settings, nid, now=NOW)
    session.rollback()
    assert row(system_conn, nid)[1] is None
    monkeypatch.undo()
    monkeypatch.setattr(email, "OUTBOX_DIR", outbox)
    assert deliver(session, settings, nid) == "sent"
    assert len(mails(outbox)) == 1


def test_unknown_row_is_missing(session, settings):
    assert deliver(session, settings, uuid.uuid4()) == "missing"


# --- EMAIL_BACKEND --------------------------------------------------------------------------------------------------------


def test_file_backend_writes_the_outbox(session, settings, outbox, user, system_conn):
    u = user()
    nid = note(session, u)
    assert deliver(session, settings, nid) == "sent"
    (m,) = mails(outbox)
    assert m["to"] == system_conn.execute("SELECT email FROM users WHERE id = %s", (u,)).fetchone()[0]
    assert m["subject"] == "Lisbon fare fell"
    assert "https://app.test/trips/x" in m["text"]
    assert "<h1" in m["html"]
    assert m["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert m["headers"]["List-Unsubscribe"].startswith("<https://api.test/v1/unsubscribe?t=")


def test_console_backend_logs_and_writes_no_file(session, settings, outbox, user, caplog):
    nid = note(session, user())
    with caplog.at_level(logging.INFO, logger="hermi.email"):
        assert deliver(session, settings.model_copy(update={"email_backend": "console"}), nid) == "sent"
    assert any("Lisbon fare fell" in r.getMessage() for r in caplog.records)
    assert mails(outbox) == []


def test_resend_backend_posts_with_an_idempotency_key(session, settings, outbox, user, monkeypatch):
    from pydantic import SecretStr

    sent = []
    monkeypatch.setattr(email, "_resend_post", lambda key, path, body, idempotency_key=None: sent.append((key, path, body, idempotency_key)))
    nid = note(session, user())
    s = settings.model_copy(update={"email_backend": "resend", "resend_api_key": SecretStr("re_test")})
    assert deliver(session, s, nid) == "sent"
    ((key, path, body, idem),) = sent
    assert (key, path) == ("re_test", "/emails")
    assert idem == f"notification-{nid}"
    assert body["to"][0].endswith("@example.com") and body["subject"] == "Lisbon fare fell" and body["html"]
    assert mails(outbox) == []


def test_resend_without_a_key_fails_instead_of_losing_the_mail(session, settings, user, system_conn):
    nid = note(session, user())
    s = settings.model_copy(update={"email_backend": "resend", "resend_api_key": None})
    with pytest.raises(NotConfigured):
        service.deliver_email(session, s, nid, now=NOW)
    session.rollback()
    assert row(system_conn, nid)[1] is None


# --- quiet hours ----------------------------------------------------------------------------------------------------------


def test_quiet_hours_defer_to_the_end_of_the_window(session, settings, outbox, user, system_conn):
    u = user("America/New_York")
    nid = note(session, u)
    at = datetime(2027, 3, 1, 3, 0, tzinfo=UTC)  # 22:00 on 28 Feb in New York
    assert deliver(session, settings, nid, now=at) == "deferred"
    assert mails(outbox) == [] and row(system_conn, nid)[1] is None
    jobs = jobs_for(system_conn, nid)
    assert len(jobs) == 2 and jobs[1][0] == datetime(2027, 3, 1, 13, 0, tzinfo=UTC)  # 08:00 EST
    assert deliver(session, settings, nid, now=datetime(2027, 3, 1, 13, 0, tzinfo=UTC)) == "sent"


def test_quiet_hours_after_midnight_end_the_same_morning(session, settings, user):
    prefs = service.Prefs()
    assert service.quiet_release(datetime(2027, 3, 1, 6, 30, tzinfo=UTC), "UTC", prefs) == datetime(2027, 3, 1, 8, 0, tzinfo=UTC)
    assert service.quiet_release(datetime(2027, 3, 1, 23, 0, tzinfo=UTC), "UTC", prefs) == datetime(2027, 3, 2, 8, 0, tzinfo=UTC)
    assert service.quiet_release(datetime(2027, 3, 1, 12, 0, tzinfo=UTC), "UTC", prefs) is None
    assert service.quiet_release(datetime(2027, 3, 1, 8, 0, tzinfo=UTC), "UTC", prefs) is None  # the window is half open
    assert service.quiet_release(datetime(2027, 3, 1, 23, 0, tzinfo=UTC), "Not/AZone", prefs) == datetime(2027, 3, 2, 8, 0, tzinfo=UTC)  # a bad zone reads as UTC


def test_outside_quiet_hours_sends_and_own_hours_apply(session, settings, outbox, user, system_conn):
    u = user("Europe/Paris")  # 16:00 local at NOW
    nid = note(session, u)
    system_conn.execute("INSERT INTO notification_preferences (user_id, quiet_start, quiet_end) VALUES (%s, '15:00', '17:00')", (u,))
    assert deliver(session, settings, nid) == "deferred"
    system_conn.execute("UPDATE notification_preferences SET quiet_enabled = false WHERE user_id = %s", (u,))
    assert deliver(session, settings, nid) == "sent"


def test_the_deletion_confirmation_ignores_quiet_hours_and_unsubscribe_all(session, settings, outbox, user, system_conn):
    u = user("UTC", status="pending_deletion")
    system_conn.execute("INSERT INTO notification_preferences (user_id, email_enabled) VALUES (%s, false)", (u,))
    nid = note(session, u, kind="account_deleted", title="Your Hermi account is scheduled for deletion", body="We will delete it on 31 Mar 2027.")
    assert deliver(session, settings, nid, now=datetime(2027, 3, 1, 2, 0, tzinfo=UTC)) == "sent"
    (m,) = mails(outbox)
    assert "Unsubscribe" not in m["text"] and "unsubscribe" not in m["html"].lower()
    assert "headers" not in m


# --- preferences, mute, marketing ------------------------------------------------------------------------------------------


def test_a_switched_off_type_is_skipped_and_leaves_the_outbox(session, settings, outbox, user, system_conn):
    u = user()
    system_conn.execute("INSERT INTO notification_preferences (user_id, email_off) VALUES (%s, '{price_drop}')", (u,))
    off, on = note(session, u, "price_drop"), note(session, u, "run_finished", title="Your run finished")
    assert deliver(session, settings, off) == "skipped:preference"
    assert deliver(session, settings, on) == "sent"
    assert row(system_conn, off) == (False, None)
    assert len(mails(outbox)) == 1


def test_email_switched_off_skips_everything_but_account_mail(session, settings, outbox, user, system_conn):
    u = user()
    system_conn.execute("INSERT INTO notification_preferences (user_id, email_enabled) VALUES (%s, false)", (u,))
    assert deliver(session, settings, note(session, u)) == "skipped:preference"
    assert mails(outbox) == []


def test_marketing_needs_an_opt_in(session, settings, outbox, user, system_conn, postal):
    u = user()
    assert templates.category("lifecycle") == "marketing" and templates.category("price_drop") == "transactional"
    assert deliver(session, settings, note(session, u, "lifecycle", title="New in Hermi")) == "skipped:no_marketing_consent"
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'marketing_email', 'v1', true)", (u,))
    assert deliver(session, settings, note(session, u, "lifecycle", title="New in Hermi")) == "sent"
    (m,) = mails(outbox)
    assert "Unsubscribe" in m["text"] and "chose to hear from Hermi" in m["text"]
    assert "1 Example Street, Lisbon" in m["text"] and "1 Example Street, Lisbon" in m["html"]
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'marketing_email', 'v1', false)", (u,))  # withdrawn later
    assert deliver(session, settings, note(session, u, "lifecycle", title="Again")) == "skipped:no_marketing_consent"


def test_marketing_is_dropped_while_there_is_no_postal_address(session, settings, outbox, user, system_conn):
    assert templates.POSTAL_ADDRESS == ""  # owner-pending
    u = user()
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'marketing_email', 'v1', true)", (u,))
    nid = note(session, u, "lifecycle", title="New in Hermi")
    assert deliver(session, settings, nid) == "skipped:no_postal_address"
    assert mails(outbox) == [] and row(system_conn, nid) == (False, None)


def test_a_muted_trip_sends_nothing(session, settings, outbox, user, system_conn):
    u = user()
    t, other = trip(system_conn, u), trip(system_conn, u)
    system_conn.execute("INSERT INTO trip_notification_mutes (trip_id, user_id) VALUES (%s, %s)", (t, u))
    assert deliver(session, settings, note(session, u, trip_id=t)) == "skipped:trip_muted"
    assert deliver(session, settings, note(session, u, trip_id=other)) == "sent"


def test_inactive_users_get_no_mail_and_the_kill_switch_holds_it(session, settings, outbox, user, system_conn):
    assert deliver(session, settings, note(session, user(status="suspended"))) == "skipped:inactive_user"
    nid = note(session, user())
    system_conn.execute("UPDATE kill_switches SET engaged = true, engaged_at = now() WHERE key = 'email.all'")
    try:
        assert deliver(session, settings, nid) == "blocked"
        assert row(system_conn, nid) == (True, None)
        assert jobs_for(system_conn, nid)[-1][0] == NOW + timedelta(minutes=15)  # looked at again, not stuck
    finally:
        system_conn.execute("UPDATE kill_switches SET engaged = false, engaged_at = NULL WHERE key = 'email.all'")
    assert deliver(session, settings, nid) == "sent"


# --- templates ------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(templates.KINDS))
def test_every_template_renders_clean_copy(kind):
    subject, text, html = templates.render(kind, title="A <b>title</b>", body="Body & more", payload={"url": "/trips/1"}, base_url="https://app.test", unsubscribe_url="https://api.test/v1/unsubscribe?t=x")
    for s in (subject, text, html, *[k.cta + k.note for k in templates.KINDS.values()]):
        assert EM not in s and EN not in s
    assert "&lt;b&gt;title" in html and "<b>title" not in html  # escaped
    assert (kind == "account_deleted") == ("unsubscribe" not in html)


def test_trial_ending_has_a_fixed_cancel_link():
    _, text, html = templates.render("trial_ending", title="Your free trial ends soon", body="b", payload={"url": "/account"}, base_url="https://app.test", unsubscribe_url="u")
    assert "Cancel subscription: https://apps.apple.com/account/subscriptions" in text
    assert 'href="https://apps.apple.com/account/subscriptions"' in html and ">Cancel subscription<" in html
    _, other, _ = templates.render("price_drop", title="t", body="", payload={}, base_url="https://app.test", unsubscribe_url="u")
    assert "apps.apple.com" not in other


def test_the_unsubscribe_link_is_labelled_for_what_it_does():
    _, text, html = templates.render("run_finished", title="t", body="", payload={}, base_url="https://app.test", unsubscribe_url="https://api.test/u")
    assert "Stop all email from Hermi: https://api.test/u" in text and ">Stop all email from Hermi<" in html


def test_a_payload_link_off_site_is_not_followed():
    _, text, html = templates.render("trip_invite", title="t", body="", payload={"url": "https://evil.test/x"}, base_url="https://app.test", unsubscribe_url="u")
    assert "evil.test" not in text and "evil.test" not in html
    _, text, _ = templates.render("trip_invite", title="t", body="", payload={"url": "//evil.test/x"}, base_url="https://app.test", unsubscribe_url="u")
    assert "evil.test" not in text


def test_booked_fare_copy_never_promises_a_refund():
    _, text, _ = templates.render("booked_fare_drop", title="You paid $412. It is now $368.", body="", payload={}, base_url="https://app.test", unsubscribe_url="u")
    assert "change and credit rules" in text and "does not mean a refund" in text


# --- unsubscribe -----------------------------------------------------------------------------------------------------------


def test_unsubscribe_token_round_trip_and_tamper(settings):
    u = uuid.uuid4()
    t = service.sign_unsubscribe(settings, u, "all")
    assert service.verify_unsubscribe(settings, t) == (u, "all")
    raw, sig = t.split(".")
    assert service.verify_unsubscribe(settings, raw + "." + sig[:-2] + ("AA" if not sig.endswith("AA") else "BB")) is None
    other = service.sign_unsubscribe(settings, uuid.uuid4(), "all")
    assert service.verify_unsubscribe(settings, raw + "." + other.split(".")[1]) is None
    assert service.verify_unsubscribe(settings, "garbage") is None
    assert service.verify_unsubscribe(Settings(_env_file=None, environment="ci", unsubscribe_secret="another-secret"), t) is None


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), raise_server_exceptions=False) as c:
        yield c


def test_get_only_shows_a_confirm_page_and_changes_nothing(client, settings, system_conn, user):
    u = user()
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'marketing_email', 'v1', true)", (u,))
    t = service.sign_unsubscribe(settings, u, "all")
    r = client.get("/v1/unsubscribe", params={"t": t})
    assert r.status_code == 200 and "Stop all email from Hermi" in r.text
    assert '<form method="post" action="/v1/unsubscribe?t=' in r.text
    assert system_conn.execute("SELECT count(*) FROM consents WHERE user_id = %s", (u,)).fetchone() == (1,)
    assert system_conn.execute("SELECT count(*) FROM notification_preferences WHERE user_id = %s", (u,)).fetchone() == (0,)
    assert "Account" not in r.text  # no pointer to a settings screen that does not exist yet


def test_one_click_unsubscribe_needs_no_login(client, settings, session, system_conn, user):
    u = user()
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'marketing_email', 'v1', true)", (u,))
    t = service.sign_unsubscribe(settings, u, "marketing")
    r = client.post("/v1/unsubscribe", params={"t": t}, data={"List-Unsubscribe": "One-Click"})
    assert r.status_code == 200 and r.json() == {"unsubscribed": True}
    assert not service.has_marketing_consent(session, u)
    assert system_conn.execute("SELECT count(*) FROM consents WHERE user_id = %s", (u,)).fetchone() == (2,)
    client.post("/v1/unsubscribe", params={"t": t})  # idempotent
    assert system_conn.execute("SELECT count(*) FROM consents WHERE user_id = %s", (u,)).fetchone() == (2,)
    assert system_conn.execute("SELECT count(*) FROM notification_preferences WHERE user_id = %s", (u,)).fetchone() == (0,)  # marketing scope leaves the other mail alone


def test_the_confirm_button_post_answers_with_a_page(client, settings, system_conn, user):
    u = user()
    r = client.post("/v1/unsubscribe", params={"t": service.sign_unsubscribe(settings, u, "all")}, headers={"Accept": "text/html"})
    assert r.status_code == 200 and "We have stopped all email from Hermi" in r.text
    assert system_conn.execute("SELECT email_enabled FROM notification_preferences WHERE user_id = %s", (u,)).fetchone() == (False,)


def test_unsubscribe_all_switches_email_off(client, settings, system_conn, user):
    u = user()
    r = client.post("/v1/unsubscribe", params={"t": service.sign_unsubscribe(settings, u, "all")}, data={"List-Unsubscribe": "One-Click"})
    assert r.status_code == 200 and r.json() == {"unsubscribed": True}
    assert system_conn.execute("SELECT email_enabled FROM notification_preferences WHERE user_id = %s", (u,)).fetchone() == (False,)


def test_a_bad_unsubscribe_link_is_a_400(client, settings):
    assert client.get("/v1/unsubscribe", params={"t": "nope"}).status_code == 400
    assert client.post("/v1/unsubscribe", params={"t": "nope"}).status_code == 400
    assert client.post("/v1/unsubscribe", params={"t": service.sign_unsubscribe(settings, uuid.uuid4(), "all")}).status_code == 400  # signed, but no such user


# --- the scheduled producers -----------------------------------------------------------------------------------------------


def kinds(system_conn, uid, kind):
    return system_conn.execute("SELECT dedupe_key, trip_id, title FROM notifications WHERE user_id = %s AND kind = %s", (uid, kind)).fetchall()


def test_predeparture_reminder_once_per_user_and_trip(session, system_conn, user):
    owner, guest = user("UTC"), user("UTC")
    t = trip(system_conn, owner, start=NOW.date() + timedelta(days=7))
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'editor')", (t, guest))
    assert service.queue_predeparture_reminders(session, NOW) == 2
    session.commit()
    assert service.queue_predeparture_reminders(session, NOW) == 0
    assert service.queue_predeparture_reminders(session, NOW + timedelta(hours=3)) == 0  # a later hourly run
    session.commit()
    (r,) = kinds(system_conn, owner, "pre_trip_reminder")
    assert r == (f"reminder:{t}:7d", t, "Lisbon starts in 7 days")
    assert len(kinds(system_conn, guest, "pre_trip_reminder")) == 1


def test_predeparture_waits_for_nine_local_and_the_right_day(session, system_conn, user):
    early = user("Europe/Paris")
    t = trip(system_conn, early, start=NOW.date() + timedelta(days=7))
    assert service.queue_predeparture_reminders(session, datetime(2027, 3, 1, 7, 0, tzinfo=UTC)) == 0  # 08:00 in Paris
    assert service.queue_predeparture_reminders(session, datetime(2027, 3, 1, 8, 0, tzinfo=UTC)) == 1  # 09:00 in Paris
    session.commit()
    wrong = user("UTC")
    trip(system_conn, wrong, start=NOW.date() + timedelta(days=6))
    assert service.queue_predeparture_reminders(session, NOW) == 0
    assert len(kinds(system_conn, early, "pre_trip_reminder")) == 1 and t


def test_predeparture_skips_a_muted_or_trashed_trip(session, system_conn, user):
    u = user()
    muted, trashed = trip(system_conn, u, start=NOW.date() + timedelta(days=7)), trip(system_conn, u, start=NOW.date() + timedelta(days=7))
    system_conn.execute("INSERT INTO trip_notification_mutes (trip_id, user_id) VALUES (%s, %s)", (muted, u))
    system_conn.execute("UPDATE trips SET deleted_at = now() WHERE id = %s", (trashed,))
    assert service.queue_predeparture_reminders(session, NOW) == 0


def test_digest_goes_to_others_once_a_day(session, system_conn, user):
    a, b = user("UTC"), user("UTC")
    t = trip(system_conn, a)
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'editor')", (t, b))
    now = datetime.now(UTC).replace(hour=10, minute=0)
    system_conn.execute("INSERT INTO activity_log (trip_id, actor_user_id, verb, entity_type, summary) VALUES (%s, %s, 'added', 'item', 'Sam added Alfama walk')", (t, b))
    assert service.build_digests(session, now) == 1  # a hears about b; b made the change
    session.commit()
    assert service.build_digests(session, now + timedelta(hours=1)) == 0
    assert kinds(system_conn, b, "activity_digest") == []
    ((key, trip_id, title),) = kinds(system_conn, a, "activity_digest")
    assert key == f"digest:{t}:{now.date().isoformat()}" and trip_id == t and title == "Changes on Lisbon"
    body = system_conn.execute("SELECT body FROM notifications WHERE user_id = %s AND kind = 'activity_digest'", (a,)).fetchone()[0]
    assert body == "1 change: Sam added Alfama walk."


def test_digest_waits_for_eight_local_and_respects_mute(session, system_conn, user):
    a, b = user("UTC"), user("UTC")
    t = trip(system_conn, a)
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'editor')", (t, b))
    system_conn.execute("INSERT INTO activity_log (trip_id, actor_user_id, verb, entity_type, summary) VALUES (%s, %s, 'added', 'item', 'x')", (t, b))
    day = datetime.now(UTC).replace(minute=0)
    assert service.build_digests(session, day.replace(hour=7)) == 0
    system_conn.execute("INSERT INTO trip_notification_mutes (trip_id, user_id) VALUES (%s, %s)", (t, a))
    assert service.build_digests(session, day.replace(hour=9)) == 0


def test_trial_ending_reminder_once_per_period(session, system_conn, user):
    u = user()
    end = NOW + timedelta(hours=40)
    system_conn.execute("INSERT INTO subscriptions (user_id, store, original_transaction_id, plan_code, status, is_trial, period_end) VALUES (%s, 'apple', %s, 'plus', 'in_trial', true, %s)", (u, uuid.uuid4().hex, end))
    far = user()
    system_conn.execute("INSERT INTO subscriptions (user_id, store, original_transaction_id, plan_code, status, is_trial, period_end) VALUES (%s, 'apple', %s, 'plus', 'in_trial', true, %s)", (far, uuid.uuid4().hex, NOW + timedelta(days=5)))
    assert service.queue_trial_ending_reminders(session, NOW) == 1
    session.commit()
    assert service.queue_trial_ending_reminders(session, NOW + timedelta(hours=1)) == 0
    ((key, trip_id, title),) = kinds(system_conn, u, "trial_ending")
    assert key == "trial_ending:2027-03-03" and trip_id is None and title == "Your free trial ends soon"
    assert kinds(system_conn, far, "trial_ending") == []


# --- the worker path -------------------------------------------------------------------------------------------------------


def test_the_worker_runs_send_email_from_the_queue_and_a_second_run_sends_nothing(db_urls, settings, outbox, user, session, system_conn):
    import asyncio
    import sys

    from hermi import jobs
    from hermi_worker import app as worker_app

    for t in ("procrastinate_events", "procrastinate_periodic_defers", "procrastinate_jobs", "procrastinate_workers"):
        system_conn.execute(f"DELETE FROM {t}")
    nid = note(session, user())  # queues one send_email job
    jobs.enqueue(session, "send_email", notification_id=str(nid))  # the same notification queued twice, as a duplicate event would
    session.commit()
    app = worker_app.build_app(settings)

    async def drain():
        async with app.open_async():
            await app._worker(queues=["notify"], name="n", concurrency=2, wait=False, install_signal_handlers=False, listen_notify=False).run()

    try:
        asyncio.run(drain(), loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)
    finally:
        app.sqlalchemy_engine.dispose()
        app.fairness_engine.dispose()
    assert len(mails(outbox)) == 1
    assert system_conn.execute("SELECT status::text FROM procrastinate_jobs WHERE task_name = 'send_email' ORDER BY id").fetchall() == [("succeeded",), ("succeeded",)]
