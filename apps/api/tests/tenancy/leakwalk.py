# ruff: noqa: E501  (long SQL strings)
"""The tenant-isolation walk (10 section 1.3). Pure functions: the tests feed them an app, a policy and a world."""

import ast
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from hermi import db
from hermi.security.jwt import mint_dev_token

HERMI = Path(__file__).resolve().parents[2] / "hermi"
WRITE = {"POST", "PUT", "PATCH", "DELETE"}
PARAM = re.compile(r"\{(\w+)(?::\w+)?\}")


@dataclass
class World:
    """User A owns a rich trip, B is a stranger, C is a viewer on A's trip."""

    a: uuid.UUID
    b: uuid.UUID
    c: uuid.UUID
    subjects: dict[str, str]
    trip: uuid.UUID
    ids: dict[str, uuid.UUID]  # path parameter name -> A's id
    sentinels: list[str] = field(default_factory=list)


def all_routes(app):
    """(full path, route) for every route on the app, including those outside the OpenAPI schema.

    FastAPI 0.142 keeps an included router as a lazy `_IncludedRouter` in `app.routes`, so this walks
    `app.router.routes` and recurses into `original_router`, adding each include prefix on the way."""

    def walk(rs, prefix):
        for r in rs:
            if hasattr(r, "original_router"):
                yield from walk(r.original_router.routes, prefix + r.include_context.prefix)
            else:
                yield prefix + r.path, r

    yield from walk(app.router.routes, "")


def routes(app):
    """(key, method, path) for every route, keys as in route_policy.POLICY."""
    seen = {
        (f"{m} {path}", m, path)
        for path, r in all_routes(app)
        for m in (getattr(r, "methods", None) or set()) - {"HEAD", "OPTIONS"}
    }
    return sorted(seen)


def concrete(path: str, ids: dict[str, uuid.UUID]) -> str:
    # An id the fixture has no row for becomes a fresh uuid, which still has to be a 404.
    return PARAM.sub(lambda m: str(ids.get(m.group(1)) or uuid.uuid4()), path)


def _send(client, method, url, token=None):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    if method in WRITE:
        h["Idempotency-Key"] = str(uuid.uuid4())
    return client.request(method, url, headers=h, json={} if method in WRITE else None)


def run_walk(client, world: World, policy: dict[str, str], viewer_write_ok: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Run items 2 to 7 of 1.3 through the HTTP app. Returns one line per failure.

    Writes carry a fresh Idempotency-Key and an empty JSON body. A tenant route must run its guard (require_trip)
    before any If-Match 428 check, or the walk sees a 428 where it expects a 404."""
    s = client.settings
    tok = {k: mint_dev_token(s, world.subjects[k]) for k in ("b", "c")}
    bad: list[str] = []

    def leaked(key, who, r):
        if any(x in r.text for x in world.sentinels):
            bad.append(f"{key} as {who}: A's sentinel in the body ({r.status_code})")

    for key, method, path in routes(client.app):
        kind = policy.get(key)
        if kind is None:
            bad.append(f"{key}: not classified in tests/route_policy.py")
            continue
        if kind not in ("tenant", "user_scoped", "public"):
            continue  # webhook, admin and token_feed have their own suites
        url = concrete(path, world.ids)
        has_id = bool(PARAM.search(path))
        who, token = ("no token", None) if kind == "public" else ("B", tok["b"])
        if kind != "public":
            r = _send(client, method, url)
            if r.status_code != 401:
                bad.append(f"{key} with no token: {r.status_code}, expected 401")
            leaked(key, "no token", r)
        r = _send(client, method, url, token)
        leaked(key, who, r)
        if r.status_code >= 500:
            bad.append(f"{key} as {who}: {r.status_code}")
        if kind == "tenant":
            if has_id and r.status_code != 404:
                bad.append(f"{key} as B: {r.status_code}, expected 404")
            if method in WRITE and has_id and key not in viewer_write_ok:
                rc = _send(client, method, url, tok["c"])
                if rc.status_code not in (403, 404):
                    bad.append(f"{key} as viewer C: {rc.status_code}, expected 403 or 404")
    return bad


# Every table the API login can read and has RLS: the column that ties a row to a tenant, and what it holds.
# "user": the column holds A's user id. "trip": it holds A's trip id. A new table must be added here (rls_leaks fails otherwise).
OWNER_COLUMNS: dict[str, tuple[str, str]] = {
    **{t: ("trip_id", "trip") for t in (
        "activity_log", "checklist_items", "chosen_flights", "flight_routes", "itinerary_days", "itinerary_items",
        "lodging_options", "lodging_votes", "notes", "plan_verification_items", "plan_verifications", "run_events",
        "runs", "sample_trips", "saved_place_votes", "saved_places", "trip_destinations", "trip_fare_links",
        "trip_invites", "trip_members", "trip_passes", "trip_people", "trip_share_links",
    )},  # fmt: skip
    **{t: ("user_id", "user") for t in (
        "ai_usage", "auth_identities", "consents", "credit_debts", "credit_grants", "credit_ledger", "data_exports",
        "devices", "entitlements", "idempotency_keys", "link_clicks", "notifications", "price_alerts",
        "notification_preferences", "referral_codes", "trip_notification_mutes", "store_transactions", "subscriptions", "support_tickets", "trip_imports",
    )},  # fmt: skip
    "content_reports": ("reporter_user_id", "user"),
    "people": ("owner_user_id", "user"),
    "referral_rewards": ("referee_user_id", "user"),
    "trips": ("id", "trip"),
    "users": ("id", "user"),
}


def _a_filter(table: str, world: World) -> str:
    col, kind = OWNER_COLUMNS[table]
    return f"{col} = '{world.trip if kind == 'trip' else world.a}'"


def rls_tables(system_conn) -> list[str]:
    """Every table with RLS on that the API login can select from (the deny-all tables are skipped)."""
    return [
        t
        for (t,) in system_conn.execute(
            "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind IN ('r','p') "
            "AND NOT relispartition AND relrowsecurity AND has_table_privilege('hermi_api_login', oid, 'SELECT') ORDER BY 1"
        )
    ]


def tables_without_a_rows(system_conn, world: World) -> list[str]:
    """RLS tables where A has no row, so a zero count for B would prove nothing. Also unmapped tables."""
    return [t for t in rls_tables(system_conn) if t not in OWNER_COLUMNS or not system_conn.execute(f"SELECT count(*) FROM {t} WHERE {_a_filter(t, world)}").fetchone()[0]]


def rls_leaks(db_urls, system_conn, world: World, as_user: uuid.UUID | None) -> list[str]:
    """Passes 2 and 3: as the API login with app.user_id set to as_user (or unset), count A's rows on every RLS table.

    A readable RLS table with no OWNER_COLUMNS entry is a failure, never a skip."""
    bad = []
    with psycopg.connect(db.psycopg_url(db_urls["app"])) as c:
        if as_user is not None:
            c.execute("SELECT set_config('app.user_id', %s, true)", (str(as_user),))
        for t in rls_tables(system_conn):
            if t not in OWNER_COLUMNS:
                bad.append(f"{t}: RLS table with no owner column in tests/tenancy/leakwalk.py OWNER_COLUMNS")
                continue
            where = _a_filter(t, world) if as_user is not None else "true"  # unset: nothing at all may show
            if n := c.execute(f"SELECT count(*) FROM {t} WHERE {where}").fetchone()[0]:
                bad.append(f"{t}: {n} rows visible as {'user ' + str(as_user) if as_user else 'no user'}")
    return bad


def model_names() -> set[str]:
    """Names of every mapped model class under hermi.modules."""
    import importlib
    import pkgutil

    import hermi.modules as pkg
    from hermi.modules.base import Base

    for m in pkgutil.walk_packages(pkg.__path__, "hermi.modules."):
        if m.name.endswith(".models"):
            importlib.import_module(m.name)
    return {m.class_.__name__ for m in Base.registry.mappers}


def get_calls_outside_repos(code: str, models: set[str] | None = None) -> list[str]:
    """Item 9: `<anything>.get(Model, ...)` for a mapped model, and `.query(Model).get(...)` (callers skip repo.py)."""
    models = model_names() if models is None else models
    hits = []
    for n in ast.walk(ast.parse(code)):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get"):
            continue
        by_pk = bool(n.args) and isinstance(n.args[0], ast.Name) and n.args[0].id in models
        v = n.func.value
        if by_pk or (isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr == "query"):
            hits.append(ast.unparse(n)[:60])
    return hits
