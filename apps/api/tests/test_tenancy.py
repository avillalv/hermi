# ruff: noqa: E501  (long SQL strings and comments)
"""WF-014: require_trip permission matrix, the router import rule, the id-route walk and the SystemSession allowlist."""

import ast
import uuid
from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import text
from tests.tenancy.leakwalk import all_routes

from hermi import db
from hermi.config import Settings
from hermi.deps import CurrentUser, DbSession, TripAccess, require_trip
from hermi.main import create_app
from hermi.modules.trips import repo as trips_repo
from hermi.security.jwt import mint_dev_token

HERMI = Path(__file__).resolve().parents[1] / "hermi"
# Routes with an id parameter that do not take a trip: public tokens and the user's own resources.
PUBLIC_ID_ROUTES: set[str] = {
    "/v1/people/{person_id}",  # the caller's own people (WF-024.1)
    "/v1/places/{place_id}",  # a provider place id (geoapify:<id>), not a trip child
}


@pytest.fixture
def client(db_urls):
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        database_url=db_urls["app"],
        database_url_system=db_urls["system"],
        cors_allowed_origins="https://hermi.example",
    )
    app = create_app(s)
    r = APIRouter(prefix="/v1/_test")
    for role in ("viewer", "editor", "owner"):

        @r.get("/" + role + "/{trip_id}", name=role)
        def read(access: TripAccess = require_trip(role)):  # noqa: B008
            return {"role": access.role, "caps": sorted(access.capabilities)}

    @r.get("/list")
    def mine(session: DbSession, user: CurrentUser):
        return [str(t.id) for t in trips_repo.list_my_trips(session, user.id)]

    app.include_router(r)
    with TestClient(app, raise_server_exceptions=False) as c:
        c.settings = s
        yield c


def _h(client, sub):
    return {"Authorization": "Bearer " + mint_dev_token(client.settings, sub)}


@pytest.fixture
def world(client, make_user, system_conn):
    """A trip owned by A with an editor and a viewer, a stranger, and a trashed trip."""
    users = {k: make_user() for k in ("owner", "editor", "viewer", "stranger")}

    def trip(deleted=False):
        tid = system_conn.execute(
            "INSERT INTO trips (owner_user_id, name, home_currency, deleted_at) VALUES (%s, 't', 'USD', %s) RETURNING id",
            (users["owner"][0], "2026-01-01" if deleted else None),
        ).fetchone()[0]
        return tid

    t, trash = trip(), trip(deleted=True)
    for who in ("editor", "viewer"):
        system_conn.execute(
            "INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)", (t, users[who][0], who)
        )
    return users, t, trash


ALLOWED = {
    "viewer": {"viewer", "editor", "owner"},
    "editor": {"editor", "owner"},
    "owner": {"owner"},
}


@pytest.mark.parametrize("endpoint", ["viewer", "editor", "owner"])
@pytest.mark.parametrize("who", ["owner", "editor", "viewer"])
def test_permission_matrix(client, world, endpoint, who):
    users, t, _ = world
    r = client.get(f"/v1/_test/{endpoint}/{t}", headers=_h(client, users[who][1]))
    if who in ALLOWED[endpoint]:
        assert r.status_code == 200 and r.json()["role"] == who
    else:
        assert r.status_code == 403 and r.json()["code"] == "insufficient_role"


@pytest.mark.parametrize("endpoint", ["viewer", "editor", "owner"])
def test_stranger_unknown_and_trashed_trips_are_404(client, world, endpoint):
    users, t, trash = world
    h = _h(client, users["stranger"][1])
    for tid in (t, uuid.uuid4()):
        assert client.get(f"/v1/_test/{endpoint}/{tid}", headers=h).status_code == 404
    owner = _h(client, users["owner"][1])
    assert client.get(f"/v1/_test/{endpoint}/{trash}", headers=owner).status_code == 404
    assert client.get(f"/v1/_test/{endpoint}/{t}").status_code == 401


def test_capabilities_follow_the_role(client, world):
    users, t, _ = world
    caps = {
        w: client.get(f"/v1/_test/viewer/{t}", headers=_h(client, users[w][1])).json()["caps"]
        for w in ("owner", "editor", "viewer")
    }
    assert caps == {"owner": ["can_edit", "can_manage"], "editor": ["can_edit"], "viewer": []}


def test_list_my_trips_is_tenant_scoped_and_hides_trash(client, world):
    users, t, trash = world
    assert client.get("/v1/_test/list", headers=_h(client, users["viewer"][1])).json() == [str(t)]
    assert client.get("/v1/_test/list", headers=_h(client, users["owner"][1])).json() == [str(t)]
    assert client.get("/v1/_test/list", headers=_h(client, users["stranger"][1])).json() == []


def test_every_route_with_an_id_parameter_resolves_through_require_trip(client):
    def uses_require_trip(dep):
        return getattr(dep.call, "__require_trip__", None) or any(
            uses_require_trip(d) for d in dep.dependencies
        )

    api = [(p, r) for p, r in all_routes(client.app) if isinstance(r, APIRoute)]
    assert any(p.startswith("/v1/me") for p, _ in api) and any(p.startswith("/v1/_test/") for p, _ in api)
    bad = [
        p
        for p, r in api
        if any(n.endswith("_id") or n == "id" for n in r.param_convertors)
        and p not in PUBLIC_ID_ROUTES
        and not uses_require_trip(r.dependant)
    ]
    assert bad == []


def banned_model_imports(code: str) -> list[str]:
    """Imports of a models module in a source string, in every form."""
    found = []
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod.split(".")[-1] == "models" or mod == "hermi.modules.base":
                found.append(f"from {'.' * node.level}{mod}")
            elif node.level > 0 or mod.startswith("hermi.modules"):
                found += [f"from {mod} import models" for n in node.names if n.name == "models"]
        elif isinstance(node, ast.Import):
            found += [f"import {n.name}" for n in node.names if n.name.split(".")[-1] == "models"]
    return found


def test_banned_model_imports_catches_every_form():
    for src in (
        "from hermi.modules.trips.models import Trip",
        "from .models import Trip",
        "from . import models",
        "from ..trips import models",
        "from hermi.modules.trips import models",
        "import hermi.modules.trips.models",
        "from hermi.modules.base import Base",
    ):
        assert banned_model_imports(src), src
    assert not banned_model_imports("from hermi.modules.trips import repo\nimport uuid")


def test_only_models_repo_and_service_import_models():
    offenders = []
    for path in (HERMI / "modules").rglob("*.py"):
        if path.name in ("models.py", "repo.py", "service.py"):
            continue
        code = path.read_text(encoding="utf-8")
        offenders += [f"{path.relative_to(HERMI)}: {i}" for i in banned_model_imports(code)]
        if path.name == "router.py":
            for node in ast.walk(ast.parse(code)):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr in ("get", "query")
                    and getattr(node.value, "id", "") == "session"
                ):
                    offenders.append(f"{path.relative_to(HERMI)}: session.{node.attr}")
    assert offenders == []


def test_system_session_allowlist_is_the_03_section_6_6_set():
    assert db.SYSTEM_SESSION_ALLOWLIST == {
        "share_view", "share_report", "share_outbound", "go_redirect", "calendar_feed",
        "sample_read", "billing_sync", "import_preview", "verify_extract", "places_cache",
        "fare_refresh",
        "ai_single_call",
        "unsubscribe",
        "dev_session",  # local and ci only
    }  # fmt: skip


def test_system_session_refuses_an_unlisted_purpose():
    with pytest.raises(PermissionError):
        with db.system_session("nope", settings=None, route="GET /x"):
            pass


def test_only_db_py_and_config_touch_the_system_database_url():
    # config.py declares the setting. Migrations and the CLI are not request code and may build their own engines.
    skip = {HERMI / "db.py", HERMI / "config.py"}
    offenders = []
    for path in HERMI.rglob("*.py"):
        if path in skip or "migrations" in path.parts or path == HERMI / "cli.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            name = ast.unparse(node) if isinstance(node, ast.Constant | ast.Attribute | ast.Name) else ""
            if "DATABASE_URL_SYSTEM" in name or "database_url_system" in name or name.endswith("make_engine"):
                offenders.append(f"{path.relative_to(HERMI)}: {name}")
    assert offenders == []


def test_system_session_opens_for_an_allowlisted_purpose(db_urls, caplog):
    s = Settings(_env_file=None, environment="ci", database_url_system=db_urls["system"])
    try:
        with caplog.at_level("INFO", logger="hermi.system_session"):
            with db.system_session("dev_session", settings=s, route="GET /x") as sess:
                assert sess.execute(text("SELECT 1")).scalar() == 1
        rec = caplog.records[-1]
        assert (rec.purpose, rec.route, rec.caller) == ("dev_session", "GET /x", "anonymous")
    finally:
        db.dispose_system_engines()
