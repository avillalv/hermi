# ruff: noqa: E501  (long SQL strings)
"""WF-040.2: hermi import-legacy against a fixture copy of a real-shaped Trip Planner database."""

import json
import re
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.legacy_fixture import DATA, DDL

from hermi import cli, db
from hermi.config import Settings
from hermi.legacy_import import ImportFailed, run_import
from hermi.modules.auth import legacy_claim
from hermi.modules.notifications import email

SRC = "tp_src"


@pytest.fixture(scope="module")
def source(db_urls):
    """The fixture Trip Planner database, as a schema on the test server (the importer reads it over its own connection)."""
    with psycopg.connect(db.psycopg_url(db_urls["migrate"]), autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {SRC} CASCADE")
        c.execute(DDL.format(s=SRC))
        c.execute(DATA.format(s=SRC))
    yield {"url": db_urls["migrate"], "schema": SRC}
    with psycopg.connect(db.psycopg_url(db_urls["migrate"]), autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {SRC} CASCADE")


@pytest.fixture
def env(db_urls, source, system_conn, tmp_path, monkeypatch):
    """A clean legacy schema, a file outbox and two fresh owner emails."""
    system_conn.execute(
        "DO $$ DECLARE t text; BEGIN FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'legacy' LOOP EXECUTE format('DROP TABLE legacy.%I CASCADE', t); END LOOP; END $$"
    ) if system_conn.execute("SELECT to_regnamespace('legacy')").fetchone()[0] else None
    # Runs keep their legacy uuid, so rows from an earlier test would block the next owner's copy.
    system_conn.execute("DELETE FROM runs WHERE id::text LIKE '00000000-0000-4000-8000-%'")
    system_conn.execute(
        "DELETE FROM provider_calls WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'ana-%@example.com')"
    )
    monkeypatch.setattr(email, "OUTBOX_DIR", tmp_path / "outbox")
    tag = uuid.uuid4().hex[:8]
    settings = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        email_backend="file",
        public_web_url="https://app.hermi.world",
    )
    return {
        "settings": settings,
        "primary": f"ana-{tag}@example.com",
        "partner": f"ben-{tag}@example.com",
        "outbox": tmp_path / "outbox",
        "out": [],
        "kw": dict(
            system_url=db_urls["system"],
            source_url=source["url"],
            source_schema=source["schema"],
            owner_url=db_urls["migrate"],
        ),
    }


def _run(env, **over):
    kw = {
        **env["kw"],
        "primary_email": env["primary"],
        "partner_email": env["partner"],
        "dry_run": False,
        "out": env["out"].append,
    }
    return run_import(env["settings"], **{**kw, **over})


def _mails(env):
    return (
        [json.loads(p.read_text()) for p in sorted(env["outbox"].glob("*.json"))]
        if env["outbox"].exists()
        else []
    )


def _user(system_conn, addr):
    return system_conn.execute("SELECT id FROM users WHERE email = %s", (addr,)).fetchone()


def test_dry_run_reports_zero_unmapped_and_writes_nothing(env, system_conn):
    rep = _run(env, dry_run=True)
    assert rep.ok and rep.unmapped == 0
    assert rep.entities["trips"] == {"source": 3, "skipped": 0, "expected": 3, "imported": 3}
    assert _user(system_conn, env["primary"]) is None and _user(system_conn, env["partner"]) is None
    assert _mails(env) == []
    assert system_conn.execute("SELECT to_regclass('legacy.legacy_id_map')").fetchone()[0] is None
    assert any("dry run" in line.lower() for line in env["out"])


def test_real_run_counts_match_per_table(env):
    rep = _run(env)
    assert rep.ok and rep.unmapped == 0, rep.checks
    ent = {k: (v["source"], v["skipped"], v["imported"]) for k, v in rep.entities.items()}
    assert ent["people"] == (3, 0, 3)
    assert ent["trips"] == (3, 0, 3)
    assert ent["trip_people"] == (6, 0, 6)
    assert ent["trip_destinations"] == (2, 0, 2)
    assert ent["flight_routes"] == (3, 0, 3)
    assert ent["chosen_flights"] == (
        2,
        1,
        1,
    )  # the route whose chosen quote is an agent quote without a source url
    assert ent["runs"] == (5, 2, 3)  # scheduled and assist runs are dropped
    assert ent["run_events"] == (5, 2, 3)  # one older than 30 days, one on a dropped run
    assert ent["ingest_rejections"] == (2, 1, 1)
    assert ent["api_calls"] == (4, 1, 3)  # one older than 13 months
    assert ent["app_settings"] == (2, 1, 1)  # the server wide key is not copied
    assert ent["activity_suggestions"] == (2, 2, 0)  # documented skip
    assert ent["flight_quotes"] == (6, 1, 5)  # the agent quote without a source url is skipped
    assert ent["fare_observations"][2] == 4  # two quotes share one key, source and time
    assert ent["trip_fare_links"][2] == 4
    assert ent["itinerary_days"] == (2, 0, 2)
    assert ent["itinerary_items"] == (3, 0, 3)
    assert ent["lodging_options"] == (4, 0, 4)
    assert ent["lodging_votes"] == (4, 0, 4)
    assert ent["notes"] == (2, 0, 2)
    assert rep.skipped_quotes == [3]
    assert all(ok for _, ok, _ in rep.checks)


def test_owners_trips_members_and_comp_entitlement(env, system_conn):
    _run(env)
    (pid,), (qid,) = _user(system_conn, env["primary"]), _user(system_conn, env["partner"])
    assert system_conn.execute(
        "SELECT status::text, display_name, home_airports::text[] FROM users WHERE id = %s", (pid,)
    ).fetchone() == ("active", "Ana", ["SFO"])
    assert (
        system_conn.execute(
            "SELECT count(*) FROM auth_identities WHERE user_id = ANY(%s)", ([pid, qid],)
        ).fetchone()[0]
        == 0
    )
    for u in (pid, qid):
        assert system_conn.execute(
            "SELECT tier_code, source FROM entitlements WHERE user_id = %s", (u,)
        ).fetchone() == ("plus", "comp")
    me = system_conn.execute(
        "SELECT name, id FROM people WHERE linked_user_id = %s AND is_self", (pid,)
    ).fetchone()
    assert me[0] == "Ana"
    assert system_conn.execute(
        "SELECT owner_user_id = %s, linked_user_id IS NULL FROM people WHERE name = 'Cy' AND owner_user_id IN (%s, %s)",
        (pid, pid, qid),
    ).fetchone() == (True, True)
    rows = system_conn.execute(
        "SELECT t.name, t.status::text, t.archived_at IS NOT NULL, t.owner_user_id = %s, "
        "(SELECT role::text FROM trip_members m WHERE m.trip_id = t.id AND m.user_id = %s) FROM trips t WHERE t.owner_user_id = %s ORDER BY t.name",
        (pid, qid, pid),
    ).fetchall()
    assert [r for r in rows if r[0] in ("Costa Rica", "Japan", "Old trip")] == [
        ("Costa Rica", "booked", False, True, "editor"),
        ("Japan", "planning", False, True, "editor"),
        ("Old trip", "archived", True, True, "editor"),
    ]


def test_ids_keep_the_creation_time_and_money_is_in_minor_units(env, system_conn):
    _run(env)
    pid = _user(system_conn, env["primary"])[0]
    tid, created = system_conn.execute(
        "SELECT id, created_at FROM trips WHERE owner_user_id = %s AND name = 'Costa Rica'", (pid,)
    ).fetchone()
    ms = int.from_bytes(tid.bytes[:6], "big")
    assert abs(datetime.fromtimestamp(ms / 1000, UTC) - created).total_seconds() < 1
    prices = dict(
        system_conn.execute(
            "SELECT title, price_total_minor FROM lodging_options WHERE trip_id IN (SELECT id FROM trips WHERE owner_user_id = %s)",
            (pid,),
        ).fetchall()
    )
    assert (
        prices["Treehouse"] == 123456
        and prices["Ryokan"] == 150000
        and prices["No price yet"] is None
    )
    assert system_conn.execute(
        "SELECT price_total_minor, currency FROM lodging_options WHERE title = 'Currency missing' AND trip_id = %s",
        (tid,),
    ).fetchone() == (10000, "USD")
    assert system_conn.execute(
        "SELECT alert_price_minor, alert_currency, is_live, origin_codes::text[] FROM flight_routes WHERE trip_id = %s",
        (tid,),
    ).fetchone() == (65050, "USD", True, ["SFO", "OAK"])
    assert system_conn.execute(
        "SELECT price_total_minor, currency, paid_minor, booked_by FROM chosen_flights WHERE trip_id = %s",
        (tid,),
    ).fetchone() == (61234, "USD", None, None)
    assert (
        system_conn.execute(
            "SELECT count(*) FROM fare_observations WHERE source_url = 'https://example.com/fare' AND price_total_minor = 52010"
        ).fetchone()[0]
        >= 1
    )


def test_fares_items_votes_and_notes(env, system_conn):
    _run(env)
    pid = _user(system_conn, env["primary"])[0]
    tid = system_conn.execute(
        "SELECT id FROM trips WHERE owner_user_id = %s AND name = 'Costa Rica'", (pid,)
    ).fetchone()[0]
    assert system_conn.execute(
        "SELECT hidden, suspect FROM trip_fare_links WHERE trip_id = %s ORDER BY hidden DESC LIMIT 1",
        (tid,),
    ).fetchone() == (True, True)
    assert (
        system_conn.execute(
            "SELECT count(*) FROM fare_observations WHERE source = 'agent' AND source_url IS NULL"
        ).fetchone()[0]
        == 0
    )
    items = system_conn.execute(
        "SELECT title, status::text, sort_order, version, source FROM itinerary_items WHERE trip_id = %s ORDER BY title",
        (tid,),
    ).fetchall()
    assert ("Hot springs", "booked", 1.0, 3, "manual") in items and (
        "Volcano hike",
        "planned",
        0.0,
        1,
        "place_search",
    ) in items
    assert (
        system_conn.execute(
            "SELECT count(*) FROM lodging_votes WHERE user_id = %s", (pid,)
        ).fetchone()[0]
        == 2
    )
    assert (
        system_conn.execute(
            "SELECT added_via FROM lodging_options WHERE title = 'Treehouse' AND trip_id = %s",
            (tid,),
        ).fetchone()[0]
        == "partner_search"
    )
    notes = dict(
        system_conn.execute(
            "SELECT title, kind::text FROM notes WHERE trip_id = %s", (tid,)
        ).fetchall()
    )
    assert notes == {"ANA sale": "agent", "From an agent (no source): Rumor": "user"}
    assert (
        system_conn.execute(
            "SELECT d.name FROM itinerary_days i JOIN trip_destinations d ON d.id = i.destination_id WHERE i.trip_id = %s",
            (tid,),
        ).fetchone()
        is not None
    )


def test_claim_emails_hold_a_redeemable_one_time_link(env, system_conn, db_urls):
    rep = _run(env)
    mails = _mails(env)
    assert rep.claims_sent == 2 and sorted(m["to"] for m in mails) == sorted(
        [env["primary"], env["partner"]]
    )
    mail = next(m for m in mails if m["to"] == env["primary"])
    token = re.search(r"https://app\.hermi\.world/claim/([\w-]+)", mail["text"]).group(1)
    eng = create_engine(
        db.sqlalchemy_url(db_urls["app"])
    )  # the claim page redeems as the API login
    try:
        with Session(eng) as s:
            uid = legacy_claim.redeem(
                s,
                token,
                provider="email",
                subject=uuid.uuid4().hex,
                email=env["primary"],
                email_is_relay=False,
                provider_subject=None,
            )
            s.commit()
    finally:
        eng.dispose()
    assert uid == _user(system_conn, env["primary"])[0]
    assert token not in "\n".join(env["out"])


def test_rerun_is_idempotent(env, system_conn):
    first = _run(env)
    pid = _user(system_conn, env["primary"])[0]

    def snapshot():
        q = "SELECT (SELECT count(*) FROM trips WHERE owner_user_id = %(p)s), (SELECT count(*) FROM people WHERE owner_user_id = %(p)s), (SELECT count(*) FROM trip_members WHERE invited_by = %(p)s), (SELECT count(*) FROM trip_fare_links WHERE trip_id IN (SELECT id FROM trips WHERE owner_user_id = %(p)s)), (SELECT count(*) FROM itinerary_items WHERE created_by = %(p)s), (SELECT count(*) FROM lodging_options WHERE created_by = %(p)s), (SELECT count(*) FROM notes WHERE trip_id IN (SELECT id FROM trips WHERE owner_user_id = %(p)s)), (SELECT count(*) FROM legacy_claims WHERE user_id = %(p)s), (SELECT array_agg(id ORDER BY id) FROM trips WHERE owner_user_id = %(p)s), (SELECT count(*) FROM users WHERE email = %(e)s)"
        return system_conn.execute(q, {"p": pid, "e": env["primary"]}).fetchone()

    before = snapshot()
    second = _run(env)
    assert second.ok and second.unmapped == 0
    assert second.entities == first.entities
    assert snapshot() == before
    assert second.claims_sent == 0 and len(_mails(env)) == 2


def test_a_failed_check_writes_nothing(env, system_conn, monkeypatch):
    from hermi.legacy_import import EXPECTED_SKIPS

    monkeypatch.setattr(
        "hermi.legacy_import.EXPECTED_SKIPS", {**EXPECTED_SKIPS, "flight_quotes": "SELECT 0"}
    )
    rep = _run(env)
    assert not rep.ok and rep.unmapped == 1
    assert _user(system_conn, env["primary"]) is None and _mails(env) == []


def test_rls_smoke_runs_as_the_api_login(env):
    rep = _run(env)
    rls = [(n, ok, d) for n, ok, d in rep.checks if "rls" in n.lower()]
    assert len(rls) == 1 and rls[0][1], rls
    assert rls[0][2].startswith("primary sees 3 of")


def test_rls_check_fails_a_real_run_when_the_api_url_is_missing(env, system_conn):
    env["settings"] = env["settings"].model_copy(update={"database_url": None})
    rep = _run(env)
    assert not rep.ok and rep.claims_sent == 0 and _mails(env) == []
    assert any("rls" in n.lower() and not ok for n, ok, _ in rep.checks)


def test_console_mail_backend_never_logs_a_claim_token(env, system_conn, caplog):
    env["settings"] = env["settings"].model_copy(update={"email_backend": "console"})
    with caplog.at_level("DEBUG"):
        rep = _run(env)
    assert not rep.ok and rep.claims_sent == 0
    assert any(n == "claim emails" and not ok for n, ok, _ in rep.checks)
    assert "/claim/" not in caplog.text and "/claim/" not in "".join(env["out"])
    pid = _user(system_conn, env["primary"])[0]
    assert (
        system_conn.execute(
            "SELECT count(*) FROM legacy_claims WHERE user_id = %s", (pid,)
        ).fetchone()[0]
        == 0
    )


def test_runs_events_calls_and_settings_are_mapped(env, system_conn):
    _run(env)
    pid = _user(system_conn, env["primary"])[0]
    r1 = "00000000-0000-4000-8000-000000000001"
    assert system_conn.execute(
        "SELECT kind::text, trigger::text, status::text, cost_usd_micros, prompt, report, provider, user_id = %s FROM runs WHERE id = %s",
        (pid, r1),
    ).fetchone() == (
        "fare_hunt",
        "manual",
        "succeeded",
        123400,
        None,
        {"found": 2},
        "claude_cli",
        True,
    )
    r5 = system_conn.execute(
        "SELECT status::text, finished_at IS NOT NULL FROM runs WHERE id = '00000000-0000-4000-8000-000000000005'"
    ).fetchone()
    assert r5 == ("interrupted", True)
    assert (
        system_conn.execute(
            "SELECT count(*) FROM runs WHERE id IN ('00000000-0000-4000-8000-000000000003', '00000000-0000-4000-8000-000000000004')"
        ).fetchone()[0]
        == 0
    )
    assert (
        system_conn.execute("SELECT count(*) FROM run_events WHERE run_id = %s", (r1,)).fetchone()[
            0
        ]
        == 0
    )
    assert system_conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE type = 'rejection') FROM run_events WHERE run_id = '00000000-0000-4000-8000-000000000002'"
    ).fetchone() == (3, 1)
    assert system_conn.execute(
        "SELECT count(*), count(cost_usd_micros) FROM provider_calls WHERE user_id = %s", (pid,)
    ).fetchone() == (3, 0)
    assert (
        system_conn.execute("SELECT home_currency FROM users WHERE id = %s", (pid,)).fetchone()[0]
        == "EUR"
    )


def test_secrets_never_reach_the_output(env):
    secret = "hunter2-very-secret"
    with pytest.raises(ImportFailed) as exc:
        _run(env, source_url=f"postgresql://someone:{secret}@127.0.0.1:notaport/none")
    assert secret not in str(exc.value) and secret not in "\n".join(env["out"])


def test_cli_wires_the_flags(monkeypatch):
    seen = {}
    monkeypatch.setattr(
        "hermi.legacy_import.run_import",
        lambda settings, **kw: seen.update(kw) or type("R", (), {"ok": True})(),
    )
    monkeypatch.setenv("DATABASE_URL_SYSTEM", "postgresql://u:p@localhost/x")
    cli.main(
        [
            "import-legacy",
            "--source-db",
            "postgresql://u:p@localhost/old",
            "--primary-email",
            "a@example.com",
            "--partner-email",
            "b@example.com",
            "--dry-run",
        ]
    )
    assert (
        seen["dry_run"] is True
        and seen["primary_email"] == "a@example.com"
        and seen["source_url"].endswith("/old")
    )


def test_cli_exits_non_zero_when_the_report_fails(monkeypatch):
    monkeypatch.setattr(
        "hermi.legacy_import.run_import", lambda settings, **kw: type("R", (), {"ok": False})()
    )
    monkeypatch.setenv("DATABASE_URL_SYSTEM", "postgresql://u:p@localhost/x")
    with pytest.raises(SystemExit) as e:
        cli.main(
            [
                "import-legacy",
                "--source-db",
                "postgresql://u:p@localhost/old",
                "--primary-email",
                "a@example.com",
                "--partner-email",
                "b@example.com",
            ]
        )
    assert e.value.code != 0
