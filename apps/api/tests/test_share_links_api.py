# ruff: noqa: E501  (long comments)
"""WF-025.2: share links and the read-only shared trip (04 section 5.6 and 5.15)."""

import hashlib
import uuid

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app
from hermi.security.jwt import mint_dev_token


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        database_pool_size=10,
        public_web_url="https://app.hermi.test",
    )
    with TestClient(create_app(s), raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _user(client, name=None):
    sub = uuid.uuid4().hex
    h = {"Authorization": "Bearer " + mint_dev_token(client.settings, sub, email=f"{sub[:12]}@example.com")}
    body = {"age_confirmed": True, "home_currency": "EUR"}
    if name:
        body["display_name"] = name
    r = client.post("/v1/me/bootstrap", json=body, headers=h)
    assert r.status_code == 201
    return h, r.json()


def _trip(client, h):
    r = client.post("/v1/trips", json={"name": "Lisbon"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _link(client, h, trip, **body):
    r = client.post(f"/v1/trips/{trip['id']}/share-links", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _token(link):
    return link["url"].rsplit("/", 1)[1]


def _join(client, h_owner, trip, h_user, role):
    inv = client.post(f"/v1/trips/{trip['id']}/invites", json={"role": role}, headers=h_owner).json()
    assert client.post(f"/v1/invites/{inv['url'].rsplit('/', 1)[1]}/accept", json={}, headers=h_user).status_code == 200


# --- management -------------------------------------------------------------------------------


def test_lifecycle_as_free_owner_and_hash_only_storage(client, system_conn):
    h, _ = _user(client)
    trip = _trip(client, h)
    link = _link(client, h, trip)
    assert link["url"].startswith("https://app.hermi.test/s/")
    assert link["redact"] == {"hotel_address": True, "prices": True, "notes": True, "people": True}
    assert link["show_book_slide"] is True and link["indexable"] is False and link["view_count"] == 0 and link["revoked_at"] is None
    token = _token(link)
    assert len(token) >= 22
    stored = system_conn.execute("SELECT token_hash FROM trip_share_links WHERE id = %s", (link["id"],)).fetchone()[0]
    assert bytes(stored) == hashlib.sha256(token.encode()).digest()
    listed = client.get(f"/v1/trips/{trip['id']}/share-links", headers=h).json()
    assert [x["id"] for x in listed] == [link["id"]] and listed[0]["url"] is None and token not in str(listed) and "token_hash" not in str(listed)
    patched = client.patch(f"/v1/trips/{trip['id']}/share-links/{link['id']}", json={"redact": {"prices": False}, "show_book_slide": False, "expires_in_days": 10}, headers=h)
    assert patched.status_code == 200, patched.text
    p = patched.json()
    assert p["redact"] == {"hotel_address": True, "prices": False, "notes": True, "people": True}
    assert p["show_book_slide"] is False and p["url"] is None
    assert client.delete(f"/v1/trips/{trip['id']}/share-links/{link['id']}", headers=h).status_code == 204
    assert client.get(f"/v1/trips/{trip['id']}/share-links", headers=h).json()[0]["revoked_at"] is not None
    assert client.delete(f"/v1/trips/{trip['id']}/share-links/{uuid.uuid4()}", headers=h).status_code == 404


def test_validation_and_cap_of_five_active(client):
    h, _ = _user(client)
    trip = _trip(client, h)
    url = f"/v1/trips/{trip['id']}/share-links"
    assert client.post(url, json={"expires_in_days": 0}, headers=h).status_code == 422
    assert client.post(url, json={"expires_in_days": 366}, headers=h).status_code == 422
    links = [_link(client, h, trip) for _ in range(5)]
    assert client.post(url, json={}, headers=h).status_code == 409
    client.delete(f"{url}/{links[0]['id']}", headers=h)
    assert client.post(url, json={}, headers=h).status_code == 201


def test_indexable_only_while_sensitive_redaction_stays_on(client):
    h, _ = _user(client)
    trip = _trip(client, h)
    url = f"/v1/trips/{trip['id']}/share-links"
    assert client.post(url, json={"indexable": True, "redact": {"people": False}}, headers=h).status_code == 422
    assert client.post(url, json={"indexable": True, "redact": {"prices": False}}, headers=h).status_code == 201  # prices may show
    ok = _link(client, h, trip)
    assert client.patch(f"{url}/{ok['id']}", json={"indexable": True}, headers=h).status_code == 200
    assert client.patch(f"{url}/{ok['id']}", json={"redact": {"notes": False}}, headers=h).status_code == 422


def test_only_the_owner_manages_links(client, system_conn):
    owner, ou = _user(client)
    system_conn.execute("UPDATE entitlements SET tier_code = 'plus', valid_until = NULL WHERE user_id = %s", (ou["id"],))
    editor, _ = _user(client)
    viewer, _ = _user(client)
    trip = _trip(client, owner)
    _join(client, owner, trip, editor, "editor")
    _join(client, owner, trip, viewer, "viewer")
    link = _link(client, owner, trip)
    url = f"/v1/trips/{trip['id']}/share-links"
    for h in (editor, viewer):
        assert client.get(url, headers=h).status_code == 403
        assert client.post(url, json={}, headers=h).status_code == 403
        assert client.patch(f"{url}/{link['id']}", json={"indexable": False}, headers=h).status_code == 403
        assert client.delete(f"{url}/{link['id']}", headers=h).status_code == 403
    assert len(client.get(f"/v1/trips/{trip['id']}/members", headers=owner).json()) == 3  # a link is never a collaborator


# --- the public read --------------------------------------------------------------------------


def test_shared_read_headers_views_and_revoke_is_immediate(client):
    h, _ = _user(client)
    trip = _trip(client, h)
    link = _link(client, h, trip)
    t = _token(link)
    r = client.get(f"/v1/shared/{t}")  # no auth
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "public, max-age=60" and r.headers["x-robots-tag"] == "noindex"
    body = r.json()
    assert body["trip_name"] == "Lisbon" and body["cta"]["label"] == "Get the app to edit"
    assert body["book_slide"] is None and body["presentation"]["trip"]["id"] == trip["id"] and body["presentation"]["book_slide_enabled"] is True
    client.get(f"/v1/shared/{t}")
    assert client.get(f"/v1/trips/{trip['id']}/share-links", headers=h).json()[0]["view_count"] == 2
    assert client.delete(f"/v1/trips/{trip['id']}/share-links/{link['id']}", headers=h).status_code == 204
    gone = client.get(f"/v1/shared/{t}")
    assert gone.status_code == 410 and gone.json()["code"] == "share_link_revoked"


def test_indexable_link_has_no_noindex(client):
    h, _ = _user(client)
    trip = _trip(client, h)
    t = _token(_link(client, h, trip, indexable=True))
    assert "x-robots-tag" not in client.get(f"/v1/shared/{t}").headers


def test_expired_unknown_and_trashed_are_410(client, system_conn):
    h, _ = _user(client)
    trip = _trip(client, h)
    link = _link(client, h, trip)
    system_conn.execute("UPDATE trip_share_links SET expires_at = now() - interval '1 minute' WHERE id = %s", (link["id"],))
    assert client.get(f"/v1/shared/{_token(link)}").status_code == 410
    assert client.get(f"/v1/shared/{uuid.uuid4().hex}").status_code == 410
    live = _link(client, h, trip)
    assert client.delete(f"/v1/trips/{trip['id']}", headers=h).status_code == 204
    assert client.get(f"/v1/shared/{_token(live)}").status_code == 410


def _fill(system_conn, trip):
    uid = system_conn.execute("SELECT owner_user_id FROM trips WHERE id = %s", (trip["id"],)).fetchone()[0]
    system_conn.execute("INSERT INTO itinerary_days (trip_id, day, title, notes) VALUES (%s, '2027-05-01', 'Alfama', 'SECRET-DAYNOTE')", (trip["id"],))
    system_conn.execute(
        "INSERT INTO itinerary_items (trip_id, day, title, address, lat, lon, notes, estimated_cost_minor, cost_currency, created_by, source, check_url, checked_at) "
        "VALUES (%s, '2027-05-01', 'Castle', 'SECRET-ADDR 1', 38.7, -9.1, 'SECRET-ITEMNOTE', 1234, 'EUR', %s, 'ai_draft', 'https://example.com/hours', now())",
        (trip["id"], uid),
    )
    system_conn.execute(
        "INSERT INTO lodging_options (trip_id, title, check_in, check_out, price_total_minor, price_per_night_minor, currency, location_name, lat, lon, notes, status, added_via) "
        "VALUES (%s, 'Casa Azul', '2027-05-01', '2027-05-03', 55555, 27777, 'EUR', 'SECRET-STAYADDR', 38.7, -9.1, 'SECRET-STAYNOTE', 'booked', 'manual')",
        (trip["id"],),
    )


def test_redaction_on_by_default_and_off_when_asked(client, system_conn):
    h, _ = _user(client, "Ownerella Secret")
    trip = _trip(client, h)
    _fill(system_conn, trip)
    t = _token(_link(client, h, trip))
    r = client.get(f"/v1/shared/{t}")
    assert r.status_code == 200, r.text
    for secret in ("SECRET-DAYNOTE", "SECRET-ITEMNOTE", "SECRET-STAYADDR", "SECRET-STAYNOTE", "1234", "55555", "27777", "Ownerella", "@example.com"):
        assert secret not in r.text, secret
    item = r.json()["presentation"]["days"][0]["items"][0]
    # redact_address hides only lodging items and stays; a sight keeps its place for the map (itinerary_items has no lodging category yet)
    assert item["address"] == "SECRET-ADDR 1" and item["lat"] == 38.7
    assert r.json()["presentation"]["stays"][0]["location_name"] is None and r.json()["presentation"]["stays"][0]["lat"] is None
    # evidence is never redacted
    assert item["source"] == "ai_draft" and item["check_url"] == "https://example.com/hours" and item["checked_at"] is not None
    p = r.json()["presentation"]
    assert p["days"][0]["title"] == "Alfama" and p["days"][0]["items"][0]["title"] == "Castle"
    assert p["stays"][0]["title"] == "Casa Azul"
    assert p["trip"]["travelers"] == ["Traveler 1"]
    open_t = _token(_link(client, h, trip, redact={"hotel_address": False, "prices": False, "notes": False, "people": False}))
    full = client.get(f"/v1/shared/{open_t}").text
    for shown in ("SECRET-DAYNOTE", "SECRET-ITEMNOTE", "SECRET-ADDR 1", "SECRET-STAYADDR", "1234", "55555", "Ownerella"):
        assert shown in full, shown
    assert "SECRET-STAYNOTE" not in full  # lodging notes are never in the presentation


def test_extending_an_expired_link_counts_against_the_cap(client, system_conn):
    h, _ = _user(client)
    trip = _trip(client, h)
    url = f"/v1/trips/{trip['id']}/share-links"
    old = _link(client, h, trip)
    system_conn.execute("UPDATE trip_share_links SET expires_at = now() - interval '1 minute' WHERE id = %s", (old["id"],))
    for _ in range(5):
        _link(client, h, trip)
    r = client.patch(f"{url}/{old['id']}", json={"expires_in_days": 30}, headers=h)
    assert r.status_code == 409
    assert client.patch(f"{url}/{old['id']}", json={"show_book_slide": False}, headers=h).status_code == 200  # no extension, no slot needed
