# ruff: noqa: E501  (long SQL)
"""hermi import-legacy (WF-040, 03 section 12): a direct copy of the owner's Trip Planner database into Hermi.

Step 1 copies the old tables into the `legacy` schema of the hosted database (no export file). Step 2 maps them into
the product tables with SQL, recording every new id in legacy.legacy_id_map so a re-run skips what is already there.
Step 3 verifies. All of it is one transaction on the worker login: a dry run, or any failed check, rolls it back.
Claim emails go out only after a commit, once per owner who has not claimed yet. Nothing here prints a connection
string, a password or a claim token."""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

import psycopg
from psycopg import sql
from sqlalchemy import create_engine, pool
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import NotConfigured, Settings
from hermi.modules.auth import legacy_claim
from hermi.modules.notifications import email as mailer

# Tables the mapping reads, then tables copied for the soak period only (routines, runs and the rest wait for Phase 2).
MAPPED_TABLES = (
    "people",
    "trips",
    "trip_travelers",
    "trip_destinations",
    "flight_routes",
    "flight_quotes",
    "itinerary_days",
    "activities",
    "lodging_options",
    "lodging_votes",
    "agent_notes",
    "runs",
    "run_events",
    "ingest_rejections",
    "api_calls",
    "app_settings",
    "activity_suggestions",
)
# Copied for the 30 day soak and not mapped: routines arrive with Pro in Phase 2 (03 12.1).
KEPT_TABLES = ("routines",)
RUN_KINDS = "('flight_agent', 'research_agent')"  # agent and research runs; scheduled checks and assist runs are dropped
EVENT_WINDOW = "interval '30 days'"
CALL_WINDOW = "interval '13 months'"

EVENT_OK = f"e.ts >= now() - {EVENT_WINDOW} AND EXISTS (SELECT 1 FROM legacy.runs r WHERE r.id = e.run_id AND r.kind IN {RUN_KINDS})"
REJECT_OK = f"j.created_at >= now() - {EVENT_WINDOW} AND EXISTS (SELECT 1 FROM legacy.runs r WHERE r.id = j.run_id AND r.kind IN {RUN_KINDS})"
HASH = "encode(sha256(convert_to('legacy-api-call:' || c.id, 'UTF8')), 'hex')"
ELIGIBLE = "(q.source <> 'agent' OR q.source_url IS NOT NULL)"
# Documented skips per entity: source rows that are left out on purpose and listed in the report.
EXPECTED_SKIPS = {
    "flight_quotes": "SELECT count(*) FROM legacy.flight_quotes q WHERE NOT " + ELIGIBLE,
    "chosen_flights": f"SELECT count(*) FROM legacy.flight_routes r JOIN legacy.flight_quotes q ON q.id = r.chosen_quote_id WHERE NOT {ELIGIBLE}",
    "runs": f"SELECT count(*) FROM legacy.runs r WHERE r.kind NOT IN {RUN_KINDS}",
    "run_events": f"SELECT count(*) FROM legacy.run_events e WHERE NOT ({EVENT_OK})",
    "ingest_rejections": f"SELECT count(*) FROM legacy.ingest_rejections j WHERE NOT ({REJECT_OK})",
    "api_calls": f"SELECT count(*) FROM legacy.api_calls c WHERE c.created_at < now() - {CALL_WINDOW}",
    "app_settings": "SELECT count(*) FROM legacy.app_settings s WHERE s.key <> 'home_currency'",
    "activity_suggestions": "SELECT count(*) FROM legacy.activity_suggestions",
}

SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ImportFailed(Exception):
    """A step failed. The message is safe to print: it never holds a URL, a password or a token."""


@dataclass
class Report:
    dry_run: bool
    entities: dict[str, dict[str, int]] = field(default_factory=dict)
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    skipped_quotes: list[int] = field(default_factory=list)
    kept_in_legacy: dict[str, int] = field(default_factory=dict)
    claims_sent: int = 0
    committed: bool = False

    @property
    def unmapped(self) -> int:
        return sum(max(e["expected"] - e["imported"], 0) for e in self.entities.values())

    @property
    def ok(self) -> bool:
        return self.unmapped == 0 and all(ok for _, ok, _ in self.checks)


def _scrub(e: BaseException, *urls: str | None) -> str:
    """The error's class and first line with URLs, user info and passwords removed."""
    msg = (str(e).splitlines() or [""])[0]
    for u in urls:
        if not u:
            continue
        msg = msg.replace(u, "<url>")
        pw = re.search(r"://[^:/@]*:([^@]+)@", u)
        if pw:
            msg = msg.replace(pw.group(1), "***")
    msg = re.sub(r"://[^\s@/]*@", "://***@", msg)
    return f"{type(e).__name__}: {msg}"


def _m(alias: str, entity: str, col: str) -> str:
    return f"JOIN legacy.legacy_id_map {alias} ON {alias}.entity = '{entity}' AND {alias}.legacy_id = {col}"


def _hit(entity: str, table: str, legacy_alias: str, col: str) -> str:
    """EXISTS clause: the target row for a legacy row exists."""
    return f"EXISTS (SELECT 1 FROM legacy.legacy_id_map m JOIN {table} x ON x.id = m.new_id WHERE m.entity = '{entity}' AND m.legacy_id = {legacy_alias}.{col})"


KEY = "encode(sha256(convert_to(q.dedupe_key, 'UTF8')), 'hex')"
MONEY = "round({v} * power(10::numeric, currency_exponent({c})))::bigint"

ID_MAP = (
    ("person", "people", "p.created_at"),
    ("trip", "trips", "p.created_at"),
    ("destination", "trip_destinations", None),
    ("route", "flight_routes", "p.created_at"),
    ("activity", "activities", "p.created_at"),
    ("lodging", "lodging_options", "p.created_at"),
    ("note", "agent_notes", "p.created_at"),
)

MAPPING = (
    (
        "people",
        f"""INSERT INTO people (id, owner_user_id, linked_user_id, name, color, home_airports, is_self, created_at, updated_at)
SELECT m.new_id, CASE p.id WHEN %(qp)s THEN %(qu)s ELSE %(pu)s END,
       CASE p.id WHEN %(pp)s THEN %(pu)s WHEN %(qp)s THEN %(qu)s END,
       p.name, p.color, p.home_airports::text[]::iata_code[], p.id IN (%(pp)s, %(qp)s), p.created_at, p.updated_at
  FROM legacy.people p {_m("m", "person", "p.id")} ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "trips",
        f"""INSERT INTO trips (id, owner_user_id, name, start_date, end_date, status, home_currency, notes, archived_at, created_at, updated_at)
SELECT m.new_id, %(pu)s, t.name, t.start_date, t.end_date, t.status::trip_status, t.home_currency, t.notes,
       CASE WHEN t.status = 'archived' THEN t.updated_at END, t.created_at, t.updated_at
  FROM legacy.trips t {_m("m", "trip", "t.id")} ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "trip_members",
        """INSERT INTO trip_members (trip_id, user_id, role, invited_by)
SELECT t.id, %(qu)s, 'editor', %(pu)s FROM legacy.legacy_id_map m JOIN trips t ON t.id = m.new_id WHERE m.entity = 'trip'
ON CONFLICT DO NOTHING""",
    ),
    (
        "trip_people",
        f"""INSERT INTO trip_people (trip_id, person_id, added_by)
SELECT tm.new_id, pm.new_id, %(pu)s FROM legacy.trip_travelers tt {_m("tm", "trip", "tt.trip_id")} {_m("pm", "person", "tt.person_id")}
ON CONFLICT DO NOTHING""",
    ),
    (
        "trip_destinations",
        f"""INSERT INTO trip_destinations (id, trip_id, position, name, region, country, country_code, kind, lat, lon, timezone, bbox,
    geoapify_place_id, summary, wiki_url, image_url, info_status, info_updated_at)
SELECT m.new_id, tm.new_id, d.position, d.name, d.region, d.country, d.country_code, d.kind, d.lat, d.lon, d.timezone, d.bbox,
       d.geoapify_place_id, d.summary, d.wiki_url, d.image_url, d.info_status, d.info_updated_at
  FROM legacy.trip_destinations d {_m("m", "destination", "d.id")} {_m("tm", "trip", "d.trip_id")} ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "flight_routes",
        f"""INSERT INTO flight_routes (id, trip_id, label, origin_codes, destination_codes, trip_type, depart_from, depart_to, return_from, return_to,
    min_nights, max_nights, adults, children, cabin, max_stops, sources, alert_price_minor, alert_currency, is_live, active,
    created_by, created_at, updated_at)
SELECT m.new_id, tm.new_id, r.label, r.origin_codes::text[]::iata_code[], r.destination_codes::text[]::iata_code[], r.trip_type::trip_type,
       r.depart_from, r.depart_to, r.return_from, r.return_to, r.min_nights, r.max_nights, r.adults, r.children, r.cabin::cabin_class,
       r.max_stops, r.sources::text[],
       CASE WHEN r.alert_price IS NOT NULL THEN {MONEY.format(v="r.alert_price", c="t.home_currency")} END,
       CASE WHEN r.alert_price IS NOT NULL THEN t.home_currency END,
       'serpapi' = ANY (r.sources), r.active, %(pu)s, r.created_at, r.updated_at
  FROM legacy.flight_routes r JOIN legacy.trips t ON t.id = r.trip_id {_m("m", "route", "r.id")} {_m("tm", "trip", "r.trip_id")}
ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "fare_observations",
        f"""INSERT INTO fare_observations (search_key, origin, destination, depart_date, return_date, cabin, adults, children, stops_max, source,
    confidence, currency, price_total_minor, airlines, stops_out, stops_back, duration_out_min, duration_back_min, depart_at_local,
    flight_numbers, deep_link_template, source_url, source_domain, observed_at, expires_at)
SELECT {KEY}, q.origin, q.destination, q.depart_date, q.return_date, r.cabin::cabin_class, r.adults, r.children, r.max_stops, q.source,
       q.confidence::fare_confidence, q.currency, {MONEY.format(v="q.price_total", c="q.currency")}, q.airlines::text[], q.stops_out, q.stops_back,
       q.duration_out_min, q.duration_back_min, q.depart_at_local, q.flight_numbers, q.booking_url, q.source_url, q.source_domain,
       q.observed_at, q.observed_at
  FROM legacy.flight_quotes q JOIN legacy.flight_routes r ON r.id = q.route_id
 WHERE {ELIGIBLE} ORDER BY q.id
ON CONFLICT (search_key, source, observed_at) DO NOTHING""",
    ),
    (
        "trip_fare_links",
        f"""INSERT INTO trip_fare_links (trip_id, route_id, observation_id, hidden, suspect, linked_at)
SELECT tm.new_id, rm.new_id, o.id, q.hidden, q.suspect, q.observed_at
  FROM legacy.flight_quotes q {_m("tm", "trip", "q.trip_id")} {_m("rm", "route", "q.route_id")}
  JOIN fare_observations o ON o.search_key = {KEY} AND o.source = q.source AND o.observed_at = q.observed_at
 WHERE {ELIGIBLE} ORDER BY q.id
ON CONFLICT (route_id, observation_id) DO NOTHING""",
    ),
    (
        "chosen_flights",
        f"""INSERT INTO chosen_flights (trip_id, route_id, observation_id, origin, destination, depart_date, return_date, price_total_minor, currency,
    airlines, flight_numbers, adults, children, source, observed_at, deep_link_template, chosen_by, chosen_at, cabin)
SELECT tm.new_id, rm.new_id, o.id, q.origin, q.destination, q.depart_date, q.return_date, {MONEY.format(v="q.price_total", c="q.currency")}, q.currency,
       q.airlines::text[], q.flight_numbers, r.adults, r.children, q.source, q.observed_at, q.booking_url, %(pu)s, r.updated_at, r.cabin::cabin_class
  FROM legacy.flight_routes r JOIN legacy.flight_quotes q ON q.id = r.chosen_quote_id {_m("tm", "trip", "r.trip_id")} {_m("rm", "route", "r.id")}
  LEFT JOIN fare_observations o ON o.search_key = {KEY} AND o.source = q.source AND o.observed_at = q.observed_at
 WHERE {ELIGIBLE}
ON CONFLICT (route_id) DO NOTHING""",
    ),
    (
        "itinerary_days",
        f"""INSERT INTO itinerary_days (trip_id, day, title, notes, destination_id, updated_at)
SELECT tm.new_id, d.day, d.title, d.notes, dm.new_id, d.updated_at
  FROM legacy.itinerary_days d {_m("tm", "trip", "d.trip_id")}
  LEFT JOIN legacy.legacy_id_map dm ON dm.entity = 'destination' AND dm.legacy_id = d.destination_id
ON CONFLICT (trip_id, day) DO NOTHING""",
    ),
    (
        "itinerary_items",
        f"""INSERT INTO itinerary_items (id, trip_id, day, start_time, end_time, sort_order, title, category, status, location_name, address, lat, lon, url,
    notes, place_provider, place_id, place_data, source, created_by, version, created_at, updated_at)
SELECT m.new_id, tm.new_id, a.day, a.start_time, a.end_time,
       row_number() OVER (PARTITION BY a.trip_id, a.day ORDER BY a.start_time NULLS LAST, a.id) - 1,
       a.title, a.category::item_category, a.status::item_status, a.location_name, a.address, a.lat, a.lon, a.url, a.notes,
       a.place_provider, a.place_id, a.place_data, CASE WHEN a.place_provider IS NOT NULL THEN 'place_search' ELSE 'manual' END,
       %(pu)s, a.version, a.created_at, a.updated_at
  FROM legacy.activities a {_m("m", "activity", "a.id")} {_m("tm", "trip", "a.trip_id")} ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "lodging_options",
        f"""INSERT INTO lodging_options (id, trip_id, title, url, url_normalized, site, check_in, check_out, guests, price_total_minor, price_per_night_minor,
    currency, photos, location_name, lat, lon, bedrooms, beds, baths, rating, review_count, notes, pros, cons, status, favorite,
    added_via, created_by, created_at, updated_at)
SELECT m.new_id, tm.new_id, l.title, l.url, l.url_normalized, l.site, l.check_in, l.check_out, l.guests,
       {MONEY.format(v="l.price_total", c="coalesce(l.currency, t.home_currency)")}, {MONEY.format(v="l.price_per_night", c="coalesce(l.currency, t.home_currency)")},
       CASE WHEN l.price_total IS NOT NULL OR l.price_per_night IS NOT NULL THEN coalesce(l.currency, t.home_currency) ELSE l.currency END,
       l.photos, l.location_name, l.lat, l.lon, l.bedrooms, l.beds, l.baths, l.rating, l.review_count, l.notes, l.pros, l.cons,
       l.status::lodging_status, l.favorite, CASE l.added_via WHEN 'serpapi' THEN 'partner_search' ELSE l.added_via END, %(pu)s,
       l.created_at, l.updated_at
  FROM legacy.lodging_options l JOIN legacy.trips t ON t.id = l.trip_id {_m("m", "lodging", "l.id")} {_m("tm", "trip", "l.trip_id")}
ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "lodging_votes",
        f"""INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id, created_at)
SELECT lm.new_id, tm.new_id, pm.new_id, np.linked_user_id, v.created_at
  FROM legacy.lodging_votes v JOIN legacy.lodging_options l ON l.id = v.lodging_id {_m("lm", "lodging", "v.lodging_id")} {_m("tm", "trip", "l.trip_id")}
  {_m("pm", "person", "v.person_id")} JOIN people np ON np.id = pm.new_id
ON CONFLICT DO NOTHING""",
    ),
    (
        "notes",
        f"""INSERT INTO notes (id, trip_id, kind, author_user_id, title, body, urls, checked_at, created_at, updated_at)
SELECT m.new_id, tm.new_id, CASE WHEN cardinality(n.urls) > 0 THEN 'agent' ELSE 'user' END::note_kind,
       CASE WHEN cardinality(n.urls) > 0 THEN NULL ELSE %(pu)s END,
       CASE WHEN cardinality(n.urls) > 0 THEN n.title ELSE left('From an agent (no source): ' || n.title, 160) END,
       n.body, n.urls, n.created_at, n.created_at, n.created_at
  FROM legacy.agent_notes n {_m("m", "note", "n.id")} {_m("tm", "trip", "n.trip_id")} ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "runs",
        f"""INSERT INTO runs (id, trip_id, user_id, kind, trigger, status, params, provider, queued_at, started_at, finished_at, summary, report, error,
    accepted_count, rejected_count, input_tokens, output_tokens, cost_usd_micros, cancel_requested)
SELECT r.id, tm.new_id, %(pu)s,
       (CASE r.kind WHEN 'flight_agent' THEN 'fare_hunt' ELSE 'deep_research' END)::run_kind, 'manual',
       (CASE WHEN r.status IN ('queued', 'running') THEN 'interrupted' ELSE r.status END)::run_status,
       r.params, 'claude_cli', r.queued_at, r.started_at, coalesce(r.finished_at, r.started_at, r.queued_at), r.summary, r.report, r.error,
       r.accepted_count, r.rejected_count, r.input_tokens, r.output_tokens, round(coalesce(r.cost_usd_est, 0) * 1000000)::bigint, r.cancel_requested
  FROM legacy.runs r {_m("tm", "trip", "r.trip_id")} WHERE r.kind IN {RUN_KINDS} ON CONFLICT (id) DO NOTHING""",
    ),
    (
        "run_events",
        f"""INSERT INTO run_events (run_id, trip_id, seq, ts, type, tool_name, summary, payload)
SELECT e.run_id, x.trip_id, e.seq, e.ts, e.type, e.tool_name, e.summary, e.payload
  FROM legacy.run_events e JOIN runs x ON x.id = e.run_id WHERE {EVENT_OK} ON CONFLICT DO NOTHING""",
    ),
    (
        "ingest_rejections",
        f"""INSERT INTO run_events (run_id, trip_id, seq, ts, type, summary, payload)
SELECT j.run_id, x.trip_id, 1000000 + j.id, j.created_at, 'rejection', 'Rejected ' || j.entity,
       jsonb_build_object('entity', j.entity, 'item', j.item, 'errors', j.errors)
  FROM legacy.ingest_rejections j JOIN runs x ON x.id = j.run_id WHERE {REJECT_OK} ON CONFLICT DO NOTHING""",
    ),
    (
        "api_calls",
        f"""INSERT INTO provider_calls (provider, endpoint, user_id, units, cached, ok, status_code, request_hash, created_at)
SELECT c.provider, c.endpoint, %(pu)s, c.units, c.cached, c.ok, c.status_code, {HASH}, c.created_at
  FROM legacy.api_calls c WHERE c.created_at >= now() - {CALL_WINDOW}
   AND NOT EXISTS (SELECT 1 FROM provider_calls p WHERE p.request_hash = {HASH} AND p.created_at = c.created_at)
 ORDER BY c.id""",
    ),
    (
        "entitlements",
        """INSERT INTO entitlements (user_id, tier_code, source, valid_until, limits)
SELECT u.id, 'plus', 'comp', NULL, (SELECT limits FROM plans WHERE code = 'plus') FROM users u WHERE u.id IN (%(pu)s, %(qu)s)
ON CONFLICT (user_id) DO UPDATE SET tier_code = 'plus', source = 'comp', limits = EXCLUDED.limits""",
    ),
)

# name, source count, imported count (source rows whose target row exists). Skips come from EXPECTED_SKIPS.
LINK_KEY = f"{KEY}, q.source, q.observed_at"
COUNTS = (
    (
        "people",
        "SELECT count(*) FROM legacy.people p",
        "SELECT count(*) FROM legacy.people p WHERE " + _hit("person", "people", "p", "id"),
    ),
    (
        "trips",
        "SELECT count(*) FROM legacy.trips p",
        "SELECT count(*) FROM legacy.trips p WHERE " + _hit("trip", "trips", "p", "id"),
    ),
    (
        "trip_people",
        "SELECT count(*) FROM legacy.trip_travelers",
        f"SELECT count(*) FROM legacy.trip_travelers tt {_m('tm', 'trip', 'tt.trip_id')} {_m('pm', 'person', 'tt.person_id')} JOIN trip_people x ON x.trip_id = tm.new_id AND x.person_id = pm.new_id",
    ),
    (
        "trip_destinations",
        "SELECT count(*) FROM legacy.trip_destinations p",
        "SELECT count(*) FROM legacy.trip_destinations p WHERE "
        + _hit("destination", "trip_destinations", "p", "id"),
    ),
    (
        "flight_routes",
        "SELECT count(*) FROM legacy.flight_routes p",
        "SELECT count(*) FROM legacy.flight_routes p WHERE "
        + _hit("route", "flight_routes", "p", "id"),
    ),
    (
        "flight_quotes",
        "SELECT count(*) FROM legacy.flight_quotes",
        f"SELECT count(*) FROM legacy.flight_quotes q {_m('tm', 'trip', 'q.trip_id')} {_m('rm', 'route', 'q.route_id')} WHERE {ELIGIBLE} AND EXISTS (SELECT 1 FROM fare_observations o JOIN trip_fare_links l ON l.observation_id = o.id AND l.route_id = rm.new_id WHERE o.search_key = {KEY} AND o.source = q.source AND o.observed_at = q.observed_at)",
    ),
    (
        "fare_observations",
        f"SELECT count(*) FROM (SELECT DISTINCT {LINK_KEY} FROM legacy.flight_quotes q WHERE {ELIGIBLE}) d",
        f"SELECT count(*) FROM (SELECT DISTINCT {LINK_KEY} FROM legacy.flight_quotes q WHERE {ELIGIBLE} AND EXISTS (SELECT 1 FROM fare_observations o WHERE o.search_key = {KEY} AND o.source = q.source AND o.observed_at = q.observed_at)) d",
    ),
    (
        "trip_fare_links",
        f"SELECT count(*) FROM (SELECT DISTINCT q.route_id, {LINK_KEY} FROM legacy.flight_quotes q WHERE {ELIGIBLE}) d",
        f"SELECT count(*) FROM (SELECT DISTINCT q.route_id, {LINK_KEY} FROM legacy.flight_quotes q {_m('rm', 'route', 'q.route_id')} WHERE {ELIGIBLE} AND EXISTS (SELECT 1 FROM fare_observations o JOIN trip_fare_links l ON l.observation_id = o.id AND l.route_id = rm.new_id WHERE o.search_key = {KEY} AND o.source = q.source AND o.observed_at = q.observed_at)) d",
    ),
    (
        "chosen_flights",
        "SELECT count(*) FROM legacy.flight_routes WHERE chosen_quote_id IS NOT NULL",
        f"SELECT count(*) FROM legacy.flight_routes r JOIN legacy.flight_quotes q ON q.id = r.chosen_quote_id {_m('rm', 'route', 'r.id')} JOIN chosen_flights c ON c.route_id = rm.new_id WHERE {ELIGIBLE}",
    ),
    (
        "itinerary_days",
        "SELECT count(*) FROM legacy.itinerary_days",
        f"SELECT count(*) FROM legacy.itinerary_days d {_m('tm', 'trip', 'd.trip_id')} JOIN itinerary_days x ON x.trip_id = tm.new_id AND x.day = d.day",
    ),
    (
        "itinerary_items",
        "SELECT count(*) FROM legacy.activities p",
        "SELECT count(*) FROM legacy.activities p WHERE "
        + _hit("activity", "itinerary_items", "p", "id"),
    ),
    (
        "lodging_options",
        "SELECT count(*) FROM legacy.lodging_options p",
        "SELECT count(*) FROM legacy.lodging_options p WHERE "
        + _hit("lodging", "lodging_options", "p", "id"),
    ),
    (
        "lodging_votes",
        "SELECT count(*) FROM legacy.lodging_votes",
        f"SELECT count(*) FROM legacy.lodging_votes v {_m('lm', 'lodging', 'v.lodging_id')} {_m('pm', 'person', 'v.person_id')} JOIN lodging_votes x ON x.lodging_id = lm.new_id AND x.person_id = pm.new_id",
    ),
    (
        "runs",
        "SELECT count(*) FROM legacy.runs",
        f"SELECT count(*) FROM legacy.runs r WHERE r.kind IN {RUN_KINDS} AND EXISTS (SELECT 1 FROM runs x WHERE x.id = r.id)",
    ),
    (
        "run_events",
        "SELECT count(*) FROM legacy.run_events",
        f"SELECT count(*) FROM legacy.run_events e WHERE {EVENT_OK} AND EXISTS (SELECT 1 FROM run_events x WHERE x.run_id = e.run_id AND x.seq = e.seq AND x.ts = e.ts)",
    ),
    (
        "ingest_rejections",
        "SELECT count(*) FROM legacy.ingest_rejections",
        f"SELECT count(*) FROM legacy.ingest_rejections j WHERE {REJECT_OK} AND EXISTS (SELECT 1 FROM run_events x WHERE x.run_id = j.run_id AND x.seq = 1000000 + j.id AND x.ts = j.created_at)",
    ),
    (
        "api_calls",
        "SELECT count(*) FROM legacy.api_calls",
        f"SELECT count(*) FROM legacy.api_calls c WHERE c.created_at >= now() - {CALL_WINDOW} AND EXISTS (SELECT 1 FROM provider_calls p WHERE p.request_hash = {HASH} AND p.created_at = c.created_at)",
    ),
    (
        "app_settings",
        "SELECT count(*) FROM legacy.app_settings",
        "SELECT count(*) FROM legacy.app_settings s WHERE s.key = 'home_currency' AND s.value #>> '{}' ~ '^[A-Za-z]{3}$' AND EXISTS (SELECT 1 FROM users u WHERE u.id = %(pu)s AND (u.home_currency = upper(s.value #>> '{}') OR EXISTS (SELECT 1 FROM auth_identities a WHERE a.user_id = u.id)))",
    ),
    ("activity_suggestions", "SELECT count(*) FROM legacy.activity_suggestions", "SELECT 0"),
    (
        "notes",
        "SELECT count(*) FROM legacy.agent_notes p",
        "SELECT count(*) FROM legacy.agent_notes p WHERE " + _hit("note", "notes", "p", "id"),
    ),
)

STRUCTURE_CHECKS = (
    (
        "no trip_people row without a person",
        "SELECT count(*) FROM trip_people tp JOIN legacy.legacy_id_map m ON m.entity = 'trip' AND m.new_id = tp.trip_id LEFT JOIN people p ON p.id = tp.person_id WHERE p.id IS NULL",
    ),
    (
        "every trip has exactly one owner member",
        "SELECT count(*) FROM (SELECT t.id FROM legacy.legacy_id_map m JOIN trips t ON t.id = m.new_id LEFT JOIN trip_members tm ON tm.trip_id = t.id AND tm.role = 'owner' WHERE m.entity = 'trip' GROUP BY t.id HAVING count(tm.user_id) <> 1) x",
    ),
    (
        "lodging money totals match per currency",
        f"""SELECT count(*) FROM (SELECT coalesce(l.currency, t.home_currency)::text cur, sum({MONEY.format(v="l.price_total", c="coalesce(l.currency, t.home_currency)")}) total FROM legacy.lodging_options l JOIN legacy.trips t ON t.id = l.trip_id
  WHERE l.price_total IS NOT NULL GROUP BY 1) s
  LEFT JOIN (SELECT o.currency::text cur, sum(o.price_total_minor) minor FROM lodging_options o JOIN legacy.legacy_id_map m ON m.entity = 'lodging' AND m.new_id = o.id GROUP BY 1) n ON n.cur = s.cur
  WHERE s.total IS DISTINCT FROM coalesce(n.minor, 0)""",
    ),
)


def _identifier(name: str) -> str:
    if not SAFE_NAME.match(name):
        raise ImportFailed("The source schema name must be letters, digits and underscores")
    return name


def _copy_tables(src, tgt, schema: str, say: Callable[[str], None]) -> dict[str, int]:
    kept: dict[str, int] = {}
    for table in MAPPED_TABLES + KEPT_TABLES:
        cols = src.execute(
            "SELECT a.attname, format_type(a.atttypid, a.atttypmod) FROM pg_attribute a "
            "WHERE a.attrelid = to_regclass(%s) AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum",
            (f'"{schema}"."{table}"',),
        ).fetchall()
        if not cols:
            if table in MAPPED_TABLES:
                raise ImportFailed(f"The source database has no table {table} in schema {schema}")
            continue
        names = sql.SQL(", ").join(sql.Identifier(c[0]) for c in cols)
        tgt.execute(sql.SQL("DROP TABLE IF EXISTS legacy.{} CASCADE").format(sql.Identifier(table)))
        tgt.execute(
            sql.SQL("CREATE TABLE legacy.{} ({})").format(
                sql.Identifier(table),
                sql.SQL(", ").join(
                    sql.SQL("{} ").format(sql.Identifier(c[0])) + sql.SQL(c[1]) for c in cols
                ),
            )
        )
        out = sql.SQL("COPY (SELECT {} FROM {}.{}) TO STDOUT").format(
            names, sql.Identifier(schema), sql.Identifier(table)
        )
        into = sql.SQL("COPY legacy.{} ({}) FROM STDIN").format(sql.Identifier(table), names)
        with src.cursor().copy(out) as cout, tgt.cursor().copy(into) as cin:
            for block in cout:
                cin.write(block)
        n = tgt.execute(
            sql.SQL("SELECT count(*) FROM legacy.{}").format(sql.Identifier(table))
        ).fetchone()[0]
        say(f"copied {table}: {n} rows")
        if table in KEPT_TABLES:
            kept[table] = n
    return kept


def _ensure_legacy_schema(system_url: str, owner_url: str | None, owner_error: str) -> None:
    """The worker login cannot create schemas, so the owner login makes `legacy` once and grants the worker the rest."""
    with psycopg.connect(db.psycopg_url(system_url), autocommit=True) as c:
        ok = c.execute(
            "SELECT to_regnamespace('legacy') IS NOT NULL AND has_schema_privilege(current_user, to_regnamespace('legacy'), 'CREATE')"
        ).fetchone()[0]
    if ok:
        return
    if not owner_url:
        raise ImportFailed(owner_error)
    with psycopg.connect(db.psycopg_url(owner_url), autocommit=True) as c:
        c.execute("CREATE SCHEMA IF NOT EXISTS legacy")
        c.execute("GRANT ALL ON SCHEMA legacy TO hermi_worker")


def _person_ids(
    tgt, primary_id: int | None, partner_id: int | None
) -> tuple[int, int, str, str, list[str], list[str]]:
    rows = tgt.execute(
        "SELECT id, name, home_airports::text[] FROM legacy.people ORDER BY id"
    ).fetchall()
    by_id = {r[0]: r for r in rows}
    if primary_id is None or partner_id is None:
        if len(rows) < 2:
            raise ImportFailed(
                "The source database needs at least two people (you and your partner)"
            )
        primary_id = primary_id if primary_id is not None else rows[0][0]
        partner_id = (
            partner_id if partner_id is not None else next(r[0] for r in rows if r[0] != primary_id)
        )
    if primary_id == partner_id or primary_id not in by_id or partner_id not in by_id:
        raise ImportFailed(
            "The primary and partner person ids must be two different people in the source database"
        )
    p, q = by_id[primary_id], by_id[partner_id]
    return primary_id, partner_id, p[1], q[1], p[2], q[2]


def _user(tgt, addr: str, name: str, airports: list[str], currency: str) -> uuid.UUID:
    row = tgt.execute("SELECT id FROM users WHERE email = %s", (addr,)).fetchone()
    if row:
        return row[0]
    return tgt.execute(
        "INSERT INTO users (email, display_name, status, home_currency, home_airports) VALUES (%s, %s, 'active', %s, %s::text[]::iata_code[]) RETURNING id",
        (addr, name[:80], currency, airports),
    ).fetchone()[0]


def _exec(tgt, name: str, query: str, params: dict | None = None):
    try:
        return tgt.execute(query, params or {})
    except psycopg.Error as e:
        state = getattr(e.diag, "sqlstate", None) or "?"
        raise ImportFailed(f"{name} failed ({state}): {(str(e).splitlines() or [''])[0]}") from None


def _rls_smoke(settings: Settings, ids: list[uuid.UUID], owner: uuid.UUID) -> tuple[bool, str]:
    try:
        url = settings.require("DATABASE_URL")
    except NotConfigured:
        return False, "DATABASE_URL is not set, so the RLS smoke test could not run"
    from sqlalchemy import text

    engine = create_engine(db.sqlalchemy_url(url), poolclass=pool.NullPool)
    try:
        counts = []
        for user in (owner, uuid.uuid4()):
            with db.request_transaction(engine, user) as s:
                counts.append(
                    s.execute(
                        text("SELECT count(*) FROM trips WHERE id = ANY(:ids)"), {"ids": ids}
                    ).scalar()
                )
    finally:
        engine.dispose()
    return counts == [
        len(ids),
        0,
    ], f"primary sees {counts[0]} of {len(ids)} trips, a third user sees {counts[1]}"


def _send_claims(
    settings: Settings,
    system_url: str,
    owners: list[tuple[uuid.UUID, str, str]],
    report: Report,
    say,
) -> None:
    # A claim token goes only into a real mailbox or the file outbox, never into the console log.
    key = settings.resend_api_key.get_secret_value() if settings.resend_api_key else None
    if not (settings.email_backend == "file" or (settings.email_backend == "resend" and key)):
        report.checks.append(
            (
                "claim emails",
                False,
                "EMAIL_BACKEND must be resend (with RESEND_API_KEY) or file; no claim link was created",
            )
        )
        return
    engine = create_engine(db.sqlalchemy_url(system_url), poolclass=pool.NullPool)
    try:
        for uid, addr, name in owners:
            with Session(engine) as s:
                if (
                    s.connection()
                    .exec_driver_sql(
                        "SELECT EXISTS (SELECT 1 FROM auth_identities WHERE user_id = %s) OR EXISTS (SELECT 1 FROM legacy_claims WHERE user_id = %s AND used_at IS NULL AND expires_at > now())",
                        (uid, uid),
                    )
                    .scalar()
                ):
                    continue
                try:
                    token = legacy_claim.create_claim(s, uid)
                    link = f"{settings.public_web_url.rstrip('/')}/claim/{token}"
                    body = (
                        f"Hi {name},\n\nYour trips from the old Trip Planner are now in Hermi. Open this link and sign in with this email address to make them yours:\n\n"
                        f"{link}\n\nThe link works once and expires in {legacy_claim.CLAIM_DAYS} days. If you did not expect this email, ignore it.\n"
                    )
                    mailer.send(settings, addr, "Claim your Hermi account", body)
                    s.commit()
                    report.claims_sent += 1
                except Exception as e:
                    s.rollback()
                    report.checks.append((f"claim email to owner {name}", False, _scrub(e)))
                    say(f"claim email to {name} failed; run again to retry")
    finally:
        engine.dispose()


def run_import(
    settings: Settings,
    *,
    source_url: str,
    system_url: str,
    primary_email: str,
    partner_email: str,
    dry_run: bool = False,
    source_schema: str = "public",
    owner_url: str | None = None,
    primary_person_id: int | None = None,
    partner_person_id: int | None = None,
    out: Callable[[str], None] = print,
) -> Report:
    """Copy, map and verify. Returns the report; raises ImportFailed for a step that cannot continue."""
    schema = _identifier(source_schema)
    primary_email, partner_email = primary_email.strip(), partner_email.strip()
    if (
        "@" not in primary_email
        or "@" not in partner_email
        or primary_email.lower() == partner_email.lower()
    ):
        raise ImportFailed("Give two different email addresses for the two owners")
    urls = (source_url, system_url, owner_url)
    report = Report(dry_run=dry_run)
    out("hermi import-legacy " + ("(dry run, nothing is kept)" if dry_run else "(real run)"))
    try:
        _ensure_legacy_schema(
            system_url,
            owner_url,
            "The legacy schema is missing. Set MIGRATION_DATABASE_URL so the importer can create it once.",
        )
        with (
            psycopg.connect(db.psycopg_url(source_url), connect_timeout=10) as src,
            psycopg.connect(db.psycopg_url(system_url)) as tgt,
        ):
            src.read_only = True
            src.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
            try:
                report.kept_in_legacy = _copy_tables(src, tgt, schema, out)
                _exec(
                    tgt,
                    "id map",
                    "CREATE TABLE IF NOT EXISTS legacy.legacy_id_map (entity text NOT NULL, legacy_id bigint NOT NULL, new_id uuid NOT NULL, PRIMARY KEY (entity, legacy_id))",
                )
                for entity, table, created in ID_MAP:
                    shift = f"uuidv7({created} - now())" if created else "uuidv7()"
                    _exec(
                        tgt,
                        f"id map for {entity}",
                        f"INSERT INTO legacy.legacy_id_map (entity, legacy_id, new_id) SELECT '{entity}', p.id, {shift} FROM legacy.{table} p ON CONFLICT DO NOTHING",
                    )
                pp, qp, pname, qname, pair, qair = _person_ids(
                    tgt, primary_person_id, partner_person_id
                )
                cur = (
                    tgt.execute(
                        "SELECT upper(value #>> '{}') FROM legacy.app_settings WHERE key = 'home_currency' AND value #>> '{}' ~ '^[A-Za-z]{3}$'"
                    ).fetchone()
                    or ("USD",)
                )[0]
                pu = _user(tgt, primary_email, pname, pair, cur)
                qu = _user(tgt, partner_email, qname, qair, cur)
                params = {"pu": pu, "qu": qu, "pp": pp, "qp": qp}
                for name, query in MAPPING:
                    _exec(tgt, name, query, params)
                for name, src_sql, hit_sql in COUNTS:
                    total = _exec(tgt, f"count {name}", src_sql, params).fetchone()[0]
                    skipped = (
                        _exec(tgt, f"skips {name}", EXPECTED_SKIPS[name], params).fetchone()[0]
                        if name in EXPECTED_SKIPS
                        else 0
                    )
                    imported = _exec(tgt, f"count imported {name}", hit_sql, params).fetchone()[0]
                    report.entities[name] = {
                        "source": total,
                        "skipped": skipped,
                        "expected": total - skipped,
                        "imported": imported,
                    }
                report.skipped_quotes = [
                    r[0]
                    for r in tgt.execute(
                        "SELECT q.id FROM legacy.flight_quotes q WHERE NOT "
                        + ELIGIBLE
                        + " ORDER BY q.id"
                    ).fetchall()
                ]
                for name, query in STRUCTURE_CHECKS:
                    bad = _exec(tgt, name, query).fetchone()[0]
                    report.checks.append(
                        (name, bad == 0, "ok" if bad == 0 else f"{bad} problem rows")
                    )
                trip_ids = [
                    r[0]
                    for r in tgt.execute(
                        "SELECT m.new_id FROM legacy.legacy_id_map m JOIN trips t ON t.id = m.new_id WHERE m.entity = 'trip'"
                    ).fetchall()
                ]
                if report.ok and not dry_run:
                    tgt.commit()
                    report.committed = True
                else:
                    tgt.rollback()
            except BaseException:
                tgt.rollback()
                raise
    except ImportFailed:
        raise
    except Exception as e:
        raise ImportFailed(_scrub(e, *urls)) from None

    if report.ok and not dry_run:
        try:
            ok, detail = _rls_smoke(settings, trip_ids, pu)
        except Exception as e:
            ok, detail = False, _scrub(e, *urls)
        report.checks.append(("RLS smoke test as the API login", ok, detail))
        if report.ok:  # claim links go out only when every check passed
            _send_claims(
                settings,
                system_url,
                [(pu, primary_email, pname), (qu, partner_email, qname)],
                report,
                out,
            )
    elif dry_run:
        report.checks.append(("RLS smoke test as the API login", True, "skipped in a dry run"))
    _print(report, out)
    return report


def _print(report: Report, out: Callable[[str], None]) -> None:
    out(f"{'table':20} {'source':>7} {'skipped':>8} {'imported':>9} {'unmapped':>9}")
    for name, e in report.entities.items():
        out(
            f"{name:20} {e['source']:>7} {e['skipped']:>8} {e['imported']:>9} {max(e['expected'] - e['imported'], 0):>9}"
        )
    if report.skipped_quotes:
        out(
            "skipped agent quotes without a source url (legacy ids): "
            + ", ".join(map(str, report.skipped_quotes))
        )
    if report.kept_in_legacy:
        out(
            "kept in the legacy schema for now: "
            + ", ".join(f"{k} ({v})" for k, v in report.kept_in_legacy.items())
        )
    for name, ok, detail in report.checks:
        out(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    out(f"unmapped rows: {report.unmapped}")
    out(f"claim emails sent: {report.claims_sent}")
    out(
        "RESULT: "
        + ("ok" if report.ok else "FAILED" + ("" if report.committed else ", nothing was written"))
    )
