# ruff: noqa: E501  (long SQL strings)
"""WF-016.2: the OpenAPI-driven cross-tenant suite (10 section 1.3) and its mutation checks."""

import psycopg
from fastapi import APIRouter
from sqlalchemy import text
from tests.route_policy import CLASSES, POLICY, VIEWER_WRITE_OK
from tests.tenancy.leakwalk import (
    HERMI,
    all_routes,
    get_calls_outside_repos,
    rls_leaks,
    routes,
    run_walk,
    tables_without_a_rows,
)

from hermi import db, deps
from hermi.deps import CurrentUser, TripAccess, require_trip
from hermi.modules.trips.models import Trip


def test_every_route_is_classified_and_every_class_is_known(make_app):
    with make_app() as client:
        keys = {k for k, _, _ in routes(client.app)}
    assert sorted(keys - POLICY.keys()) == [], "classify new routes in tests/route_policy.py"
    assert sorted(POLICY.keys() - keys) == [], "stale classification in tests/route_policy.py"
    assert set(POLICY.values()) <= set(CLASSES)


def test_walk_wrong_tenant_viewer_and_no_token(make_app, world):
    with make_app() as client:
        assert run_walk(client, world, POLICY, VIEWER_WRITE_OK) == []


def test_every_rls_table_has_a_row_of_a(system_conn, world):
    assert tables_without_a_rows(system_conn, world) == [], "seed these tables in tests/tenancy/conftest.py (or map them in OWNER_COLUMNS)"


def test_rls_as_b_and_with_no_user_sees_none_of_a(db_urls, system_conn, world):
    assert rls_leaks(db_urls, system_conn, world, world.b) == []
    assert rls_leaks(db_urls, system_conn, world, None) == []


def test_all_routes_sees_the_included_routers_and_the_hidden_ones(make_app):
    with make_app() as client:
        paths = {p for p, _ in all_routes(client.app)}
        assert set(client.app.openapi()["paths"]) <= paths and "/v1/me" in paths and "/docs" in paths


def test_no_get_by_primary_key_outside_repo_files():
    offenders = []
    for path in HERMI.rglob("*.py"):
        if path.name == "repo.py" or "migrations" in path.parts:
            continue
        offenders += [f"{path.relative_to(HERMI)}: {h}" for h in get_calls_outside_repos(path.read_text(encoding="utf-8"))]
    assert offenders == []


def test_static_check_catches_both_forms():
    assert get_calls_outside_repos("session.get(Trip, i)")
    assert get_calls_outside_repos("s.get(Trip, i)")
    assert get_calls_outside_repos("s.query(Trip).get(i)")
    assert not get_calls_outside_repos("d = {}\nd.get('x')\nsession.get(1)")


# --- mutation checks: break one guard and the walk must say so ----------------------------------------------------------

MUT_POLICY = {**POLICY, "GET /v1/_mut/trips/{trip_id}": "tenant", "DELETE /v1/_mut/trips/{trip_id}": "tenant", "GET /v1/_mut/mine": "user_scoped"}


def _router(settings, *, guarded: bool):
    r = APIRouter(prefix="/v1/_mut")
    if guarded:

        @r.get("/trips/{trip_id}")
        def read(access: TripAccess = require_trip("viewer")):  # noqa: B008
            return {"name": access.trip.name}

        @r.delete("/trips/{trip_id}")
        def remove(access: TripAccess = require_trip("owner")):  # noqa: B008
            return {"deleted": str(access.trip.id)}
    else:

        @r.get("/trips/{trip_id}")  # no guard at all: not even a token
        def open_read(trip_id: str):
            with db.system_session("dev_session", settings=settings, route="mut") as s:
                return {"name": s.execute(text("SELECT name FROM trips WHERE id = :i"), {"i": trip_id}).scalar()}

        @r.delete("/trips/{trip_id}")
        def open_delete(trip_id: str):
            return {}

    @r.get("/mine")
    def mine(user: CurrentUser):
        return {"id": str(user.id)}

    return r


def test_walk_passes_on_a_guarded_tenant_route(make_app, settings, world):
    with make_app(_router(settings, guarded=True)) as client:
        assert run_walk(client, world, MUT_POLICY) == []


def test_mutation_unclassified_route_fails(make_app, settings, world):
    with make_app(_router(settings, guarded=True)) as client:
        bad = run_walk(client, world, POLICY)
    assert any("not classified" in b for b in bad)


def test_mutation_route_without_its_guard_fails(make_app, settings, world):
    with make_app(_router(settings, guarded=False)) as client:
        bad = run_walk(client, world, MUT_POLICY)
    assert any("with no token" in b for b in bad) and any("sentinel" in b for b in bad)


def test_mutation_require_trip_lookup_that_ignores_membership_fails(make_app, settings, world, monkeypatch):
    def no_membership(session, trip_id, user_id, **_):  # the guard's lookup with the membership check removed
        with db.system_session("dev_session", settings=settings, route="mut") as s:
            t = s.get(Trip, trip_id)
            if t is not None:
                s.expunge(t)
        return None if t is None else (t, type("M", (), {"role": "owner"})())

    monkeypatch.setattr(deps.trips_repo, "get_trip_with_member", no_membership)
    with make_app(_router(settings, guarded=True)) as client:
        bad = run_walk(client, world, MUT_POLICY)
    assert any("as B" in b for b in bad) and any("sentinel" in b for b in bad)


def test_mutation_viewer_can_write_fails(make_app, settings, world):
    r = APIRouter(prefix="/v1/_mut")

    @r.delete("/trips/{trip_id}")
    def remove(access: TripAccess = require_trip("viewer")):  # noqa: B008  (the guard is too weak for a write)
        return {"deleted": str(access.trip.id)}

    pol = {**POLICY, "DELETE /v1/_mut/trips/{trip_id}": "tenant"}
    with make_app(r) as client:
        bad = run_walk(client, world, pol)
    assert any("as viewer C" in b for b in bad)


def test_mutation_permissive_rls_policy_is_caught(db_urls, system_conn, world):
    migrate = psycopg.connect(db.psycopg_url(db_urls["migrate"]), autocommit=True)
    try:
        migrate.execute("CREATE POLICY mut_leak ON people FOR SELECT USING (true)")
        assert any(b.startswith("people:") for b in rls_leaks(db_urls, system_conn, world, world.b))
    finally:
        migrate.execute("DROP POLICY IF EXISTS mut_leak ON people")
        migrate.close()
