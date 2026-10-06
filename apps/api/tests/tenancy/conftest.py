# ruff: noqa: E501  (long SQL strings)
"""Shared tenancy fixtures: users A, B and viewer C, A's rich trip with a sentinel string in every text field."""

import uuid
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from tests.tenancy.leakwalk import OWNER_COLUMNS, World
from tests.test_migrations_rls_isolation import _seeders

from hermi.config import Settings
from hermi.main import create_app

SENTINEL = "SENTINEL-A-7f3c9e"


@pytest.fixture
def settings(db_urls):
    return Settings(_env_file=None, environment="ci", auth_mode="dev", database_url=db_urls["app"], database_url_system=db_urls["system"], cors_allowed_origins="https://hermi.example")


@pytest.fixture
def make_app(settings):
    """make_app(extra_router=None) -> context manager yielding a TestClient (with .settings) on the real app."""

    @contextmanager
    def make(extra=None):
        app = create_app(settings)
        if extra is not None:
            app.include_router(extra)
        with TestClient(app, raise_server_exceptions=False) as c:
            c.settings = settings
            yield c

    return make


# Path parameter name (04 section 1) -> the table whose A row fills it.
PARAM_TABLES = {
    "route_id": "flight_routes", "item_id": "itinerary_items", "import_id": "trip_imports", "run_id": "runs",
    "option_id": "lodging_options", "lodging_id": "lodging_options", "person_id": "people", "pass_id": "trip_passes",
    "place_id": "saved_places", "saved_id": "saved_places", "link_id": "trip_share_links", "device_id": "devices",
    "destination_id": "trip_destinations", "alert_id": "price_alerts", "invite_id": "trip_invites",
    "export_id": "data_exports", "chosen_flight_id": "chosen_flights", "ticket_id": "support_tickets",
    "notification_id": "notifications", "checklist_item_id": "checklist_items", "verification_id": "plan_verifications",
}  # fmt: skip
# Tables not seeded by _seeders: closed to the API login, or made by hand below.
NOT_SEEDED = {"identity_hashes", "device_attestations", "guest_allowances", "legacy_claims", "trips", "users", "trip_members", "people", "notes", "auth_identities"}
# Free-text columns that get the sentinel (10 section 1.3 item 1: a unique marker in every text field of A's data).
TEXT_FIELDS = {
    "activity_log": ["summary"], "checklist_items": ["title"], "content_reports": ["detail"], "devices": ["device_name"],
    "flight_routes": ["label"], "itinerary_days": ["title", "notes"], "itinerary_items": ["title", "notes", "location_name", "address"],
    "lodging_options": ["title", "notes", "pros", "cons", "location_name"], "notifications": ["title", "body"],
    "plan_verification_items": ["name", "reason"], "run_events": ["summary"],
    "runs": ["prompt", "summary", "error"], "saved_places": ["name", "note", "address"], "support_tickets": ["subject"],
    "trip_destinations": ["name", "summary"], "trip_imports": ["source_name"],
}  # fmt: skip


@pytest.fixture
def world(make_user, system_conn) -> World:
    """A owns a trip with a row in every table the API login can read, B and C are described in World."""
    (a, sa), (b, sb), (c, sc) = make_user(), make_user(), make_user()
    one = lambda sql, p=(): system_conn.execute(sql, p).fetchone()[0]  # noqa: E731
    system_conn.execute("UPDATE users SET display_name = %s WHERE id = %s", (SENTINEL + "-user", a))
    ta = one("INSERT INTO trips (owner_user_id, name, home_currency, notes) VALUES (%s, %s, 'USD', %s) RETURNING id", (a, SENTINEL + "-trip", SENTINEL + "-trip-notes"))
    system_conn.execute("INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (ta, c))
    # GET /me needs the "Me" person that POST /me/bootstrap would have made.
    me = one("INSERT INTO people (owner_user_id, name, is_self) VALUES (%s, %s, true) RETURNING id", (a, SENTINEL + "-me"))
    for other in (b, c):
        system_conn.execute("INSERT INTO people (owner_user_id, name, is_self) VALUES (%s, 'Me', true)", (other,))
    system_conn.execute("INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, 'B trip', 'USD')", (b,))  # B is not empty
    x = uuid.uuid4().hex
    k = {"a": a, "b": b, "c": c, "ta": ta, "attest": "att" + x[:8], "person": me}
    k["person2"] = one("INSERT INTO people (owner_user_id, name) VALUES (%s, %s) RETURNING id", (a, SENTINEL + "-person2"))
    k["route"] = one("INSERT INTO flight_routes (trip_id, origin_codes, destination_codes, depart_from, depart_to, return_from, return_to) VALUES (%s, '{LIS}', '{JFK}', '2027-05-01', '2027-05-10', '2027-05-20', '2027-05-25') RETURNING id", (ta,))
    k["obs"] = one("INSERT INTO fare_observations (search_key, origin, destination, depart_date, source, confidence, currency, price_total_minor, observed_at, expires_at) VALUES (%s, 'LIS', 'JFK', '2027-05-03', 'travelpayouts', 'cached', 'EUR', 100, '2099-01-01', '2099-01-02') RETURNING id", (x * 2,))
    k["program"] = one("INSERT INTO affiliate_programs (code, network, name, category, hosts) VALUES (%s, 'travelpayouts', 'P', 'flights', '{}') RETURNING id", ("tp_" + x[:10],))
    k["place"] = one("INSERT INTO saved_places (trip_id, place_provider, place_id, name) VALUES (%s, 'manual', 'seed', 'P') RETURNING id", (ta,))
    k["lodging"] = one("INSERT INTO lodging_options (trip_id, title, added_via) VALUES (%s, 'Flat', 'manual') RETURNING id", (ta,))
    k["run"] = one("INSERT INTO runs (trip_id, user_id, kind) VALUES (%s, %s, 'explain') RETURNING id", (ta, a))
    k["ver"] = one("INSERT INTO plan_verifications (trip_id, user_id) VALUES (%s, %s) RETURNING id", (ta, a))
    k["code"] = one("INSERT INTO referral_codes (user_id, code) VALUES (%s, %s) RETURNING code", (c, x[8:16].upper().replace("0", "A").replace("1", "B")))
    system_conn.execute("INSERT INTO trip_people (trip_id, person_id) VALUES (%s, %s)", (ta, me))
    # One private and one shared note, both A's.
    note = "INSERT INTO notes (trip_id, author_user_id, is_private, title, topic, body) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id"
    note_id = one(note, (ta, a, False, SENTINEL + "-note-t", SENTINEL + "-note-p", SENTINEL + "-note-b"))
    private_note_id = one(note, (ta, a, True, SENTINEL + "-pnote-t", SENTINEL + "-pnote-p", SENTINEL + "-pnote-b"))
    for table, (sql, params) in _seeders(uuid.uuid4().hex[:10], k).items():
        if table not in NOT_SEEDED:
            system_conn.execute(sql, params)
    for table, cols in TEXT_FIELDS.items():
        system_conn.execute(f"UPDATE {table} SET " + ", ".join(f"{col} = '{SENTINEL}-{table}-{col}'" for col in cols))
    ids = {"id": ta, "trip_id": ta, "user_id": a, "note_id": note_id, "private_note_id": private_note_id}
    for param, table in PARAM_TABLES.items():
        col, kind = OWNER_COLUMNS[table]
        row = system_conn.execute(f"SELECT id FROM {table} WHERE {col} = %s LIMIT 1", (ta if kind == "trip" else a,)).fetchone()
        assert row, f"no seeded row in {table} for {{{param}}}"
        ids[param] = row[0]
    ids["person_id"] = me
    return World(a=a, b=b, c=c, subjects={"a": sa, "b": sb, "c": sc}, trip=ta, ids=ids, sentinels=[SENTINEL])
