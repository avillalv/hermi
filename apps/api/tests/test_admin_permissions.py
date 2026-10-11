# ruff: noqa: E501  (long lines)
"""WF-058.1: the permission table is the 08 section 3 matrix, and every /v1/admin route names a permission."""

import re
from pathlib import Path

import pytest
from tests.tenancy.leakwalk import all_routes

from hermi.config import Settings
from hermi.main import create_app
from hermi.modules.admin import permissions as perm

SPEC = Path(__file__).resolve().parents[3] / "app-buildout" / "phase-1-launch" / "08-admin-control-center.md"
ROLES = ("owner", "engineer", "support", "finance", "content")


def _matrix() -> dict[str, tuple[str, ...]]:
    rows, on = {}, False
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Capability | owner |"):
            on = True
            continue
        if on:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set(cells[0]) <= {"-"}:
                continue
            rows[cells[0]] = tuple(cells[1:6])
    return rows


def test_the_code_table_equals_the_spec_matrix():
    spec = _matrix()
    assert len(spec) >= 30
    code = {p.label: tuple(p.levels[r] for r in ROLES) for p in perm.PERMISSIONS}
    assert code == spec


def test_names_are_resource_dot_action_and_unique():
    names = [p.name for p in perm.PERMISSIONS]
    assert len(names) == len(set(names))
    assert all(re.fullmatch(r"[a-z_]+(\.[a-z_]+){1,2}", n) for n in names)
    for example in ("users.reveal", "credits.grant", "killswitch.set", "settings.ceilings.write", "imports.retry", "referrals.reject", "passes.revoke"):
        assert example in names


@pytest.mark.parametrize(
    ("role", "name", "need", "ok"),
    [
        ("owner", "admin_users.manage", "read", True),
        ("engineer", "admin_users.manage", "read", False),
        ("support", "credits.grant", "write", True),
        ("finance", "credits.grant", "write", False),
        ("support", "users.read", "read", True),
        ("support", "overview.read", "read", True),  # r: read with fields removed
        ("content", "overview.read", "read", False),
        ("finance", "finance.reports", "write", True),
        ("engineer", "finance.reports", "write", False),
        ("engineer", "finance.reports", "read", True),
        ("content", "killswitch.read", "read", True),
        ("content", "killswitch.set", "write", False),
        ("owner", "no.such_thing", "read", False),
    ],
)
def test_permits(role, name, need, ok):
    assert perm.permits(role, name, need) is ok


def test_an_unknown_role_has_nothing():
    assert perm.permits("intern", "users.read", "read") is False


def _dependants(dependant):
    for d in dependant.dependencies:
        yield d
        yield from _dependants(d)


def test_every_admin_route_has_a_known_permission_and_a_rate_class():
    from hermi.security.rate_limit import ROUTE_CLASSES

    app = create_app(Settings(_env_file=None, environment="ci", auth_mode="dev", admin_auth_mode="dev"))
    routes = [(p, r) for p, r in all_routes(app) if p.startswith("/v1/admin")]
    assert routes, "no /v1/admin routes mounted"
    names = set(perm.KNOWN)
    for path, route in routes:
        found = [getattr(d.call, "__admin_permission__", None) for d in _dependants(route.dependant)]
        found = [f for f in found if f]
        assert len(found) == 1, f"{path}: needs exactly one require(...) dependency"
        assert found[0][0] in names, f"{path}: {found[0][0]} is not in the matrix"
        assert found[0][2] in ROUTE_CLASSES, f"{path}: unknown rate class"
