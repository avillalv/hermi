# ruff: noqa: E501  (long assertions)
"""WF-038.1: the analytics catalogue matches packages/shared, capture rejects what the catalogue does not list, and
signup_completed is server emitted once (10 section 4)."""

import json
import re
import uuid
from pathlib import Path

import pytest

from hermi import analytics
from hermi.analytics import AnalyticsError, MemorySink

ROOT = Path(__file__).resolve().parents[3]
UID = uuid.uuid4()


def _ts_block(name: str):
    src = (ROOT / "packages/shared/src/events.ts").read_text(encoding="utf-8")
    m = re.search(rf"// BEGIN {name}\r?\n[^=]*= (\{{.*?\}}) as const;\r?\n// END {name}", src, re.S)
    assert m, f"block {name} missing in events.ts"
    return json.loads(re.sub(r",(\s*\})", r"\1", m.group(1)))


@pytest.fixture
def sink():
    s = MemorySink()
    analytics.set_sink(s)
    yield s
    analytics.set_sink(MemorySink())


def test_generated_catalogue_matches_events_ts():
    # Fails when events.ts changed and `npm run gen:shared` was not run.
    assert analytics.CATALOGUE == _ts_block("EVENT_CATALOGUE")
    assert analytics.COMMON == _ts_block("COMMON_PROPERTIES")


def test_catalogue_names_are_snake_case_and_carry_no_pii_keys():
    for name, props in analytics.CATALOGUE.items():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name)
        assert not {"email", "name", "title", "note", "text", "url", "address"} & set(props)
    assert {"signup_completed", "app_opened", "setting_changed", "pwa_installed"} <= set(
        analytics.CATALOGUE
    )


def test_capture_sends_a_valid_event_with_common_properties(sink):
    assert analytics.capture("app_opened", UID, {"source": "icon", "platform": "web"}) is True
    (e,) = sink.events
    assert e["event"] == "app_opened" and e["distinct_id"] == str(UID)
    assert e["properties"]["source"] == "icon" and e["properties"]["platform"] == "web"


def test_unknown_event_name_is_rejected(sink):
    with pytest.raises(AnalyticsError):
        analytics.capture("trip_created_v2", UID, {})
    assert not sink.events


def test_unknown_property_is_rejected(sink):
    with pytest.raises(AnalyticsError):
        analytics.capture("app_opened", UID, {"source": "icon", "email": "a@b.co"})
    assert not sink.events


def test_bad_enum_value_and_bad_types_are_rejected(sink):
    with pytest.raises(AnalyticsError):
        analytics.capture("app_opened", UID, {"source": "carrier_pigeon"})
    with pytest.raises(AnalyticsError):
        analytics.capture("signup_completed", UID, {"was_guest": "yes"})
    with pytest.raises(AnalyticsError):
        analytics.capture("error_shown", UID, {"code": "x" * 200})
    with pytest.raises(AnalyticsError):
        analytics.capture("error_shown", UID, {"code": "me@example.com"})
    assert not sink.events


def test_distinct_id_must_be_a_user_uuid(sink):
    with pytest.raises(AnalyticsError):
        analytics.capture("app_opened", "sam@example.com", {})


def test_opted_out_drops_the_event(sink):
    assert analytics.capture("app_opened", UID, {"source": "push"}, opted_out=True) is False
    assert not sink.events
    with pytest.raises(AnalyticsError):  # still validated, so a bad call site shows up in tests
        analytics.capture("nope", UID, {}, opted_out=True)


@pytest.fixture
def app_session(db_urls):
    """A session on the runtime login (RLS applies), acting as one user."""
    from sqlalchemy.orm import Session

    from hermi import db
    from hermi.config import Settings
    from hermi.modules.auth import repo

    engine = db.open_app_engine(Settings(_env_file=None, environment="ci", database_url=db_urls["app"]))

    def open_as(user_id):
        session = Session(engine)
        repo.as_user(session, user_id)
        return session

    yield open_as
    engine.dispose()


def test_is_opted_out_reads_the_latest_analytics_consent(make_user, system_conn, app_session):
    uid, _ = make_user()
    with app_session(uid) as s:
        assert analytics.is_opted_out(s, uid) is False  # no row
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'analytics', '1', false)", (uid,))
    with app_session(uid) as s:
        assert analytics.is_opted_out(s, uid) is True
    system_conn.execute("INSERT INTO consents (user_id, kind, version, granted) VALUES (%s, 'analytics', '1', true)", (uid,))
    with app_session(uid) as s:
        assert analytics.is_opted_out(s, uid) is False  # newer grant wins


def test_ci_environment_never_builds_a_posthog_sink():
    from hermi.config import Settings

    try:
        analytics.configure(Settings(_env_file=None, environment="ci", posthog_key="phc_x"))
        assert isinstance(analytics._sink, MemorySink)
    finally:
        analytics.set_sink(MemorySink())
