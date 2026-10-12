# ruff: noqa: E501  (the matrix rows)
"""The admin permission table (08 section 3). `label` is the matrix row text and `levels` its five role cells; a test
(tests/test_admin_permissions.py) reads 08 and fails when this table and the matrix disagree. Change both together.

Levels: `R` read, `r` read with fields removed or aggregated, `W` write with a reason, `X` write with a reason, step-up
2FA and typed confirmation, `-` no access. A route asks for `read` (r, R, W or X holds) or `write` (W or X holds). The
limits in the matrix notes column (amounts, days, per-day caps) are enforced by the route that owns the action.

shortcut: one name per matrix row. The row "Imports: retry a fetch, turn off feed polling" grants support the polling
half only; the `imports.retry` route must refuse support itself. Split the row when WF-065 lands.
"""

from dataclasses import dataclass

ROLES = ("owner", "engineer", "support", "finance", "content")
LEVEL_RANK = {"-": 0, "r": 1, "R": 2, "W": 3, "X": 4}
NEEDS = {"read": 1, "write": 3}
# Routes any enabled admin may call: they carry no data beyond the caller's own identity (08 section 8, "any").
ANY_ADMIN = frozenset({"auth.session", "auth.stepup", "auth.signin", "auth.signout", "auth.enrol"})


@dataclass(frozen=True)
class Permission:
    name: str
    label: str
    levels: dict[str, str]


def _p(name: str, label: str, *cells: str) -> Permission:
    return Permission(name, label, dict(zip(ROLES, cells, strict=True)))


PERMISSIONS: tuple[Permission, ...] = (
    _p("overview.read", "Overview dashboard", "R", "R", "r", "r", "-"),
    _p("users.read", "User list and detail (masked)", "R", "R", "R", "r", "-"),
    _p("users.reveal", "Reveal email or name on one user", "W", "W", "W", "-", "-"),
    _p("credits.grant", "Grant credits", "X", "X", "W", "-", "-"),
    _p("passes.extend", "Extend a trip pass", "W", "W", "W", "-", "-"),
    _p("comp.grant", "Comp a subscription", "X", "X", "-", "-", "-"),
    _p("users.signout", "Force sign-out", "W", "W", "W", "-", "-"),
    _p("users.export", "Start data export", "W", "W", "W", "-", "-"),
    _p("deletion.queue", "Queue a deletion request", "W", "W", "W", "-", "-"),
    _p("deletion.process", "Process deletion now (skip grace)", "X", "-", "-", "-", "-"),
    _p("impersonation.start", "Impersonate read-only", "W", "W", "W", "-", "-"),
    _p("subscriptions.read", "Subscriptions and store transactions", "R", "R", "r", "R", "-"),
    _p("webhooks.replay", "Replay failed webhook", "W", "W", "-", "-", "-"),
    _p("aispend.read", "Credits and AI spend", "R", "R", "r", "R", "-"),
    _p("runs.cancel", "Cancel an AI run", "W", "W", "W", "-", "-"),
    _p("killswitch.read", "Kill switches: read", "R", "R", "R", "R", "R"),
    _p("killswitch.set", "Kill switches: set", "X", "X", "-", "-", "-"),
    _p("flags.write", "Feature flags and experiments", "W", "W", "-", "-", "-"),
    _p("affiliate.read", "Affiliate revenue reports", "R", "R", "-", "R", "r"),
    _p("affiliate.write", "Affiliate programs, templates, link checker", "W", "W", "-", "-", "-"),
    _p("imports.read", "Imports monitoring", "R", "R", "r", "-", "-"),
    _p("imports.retry", "Imports: retry a fetch, turn off feed polling", "W", "W", "W", "-", "-"),
    _p("referrals.read", "Referral abuse view", "R", "R", "r", "r", "-"),
    _p("referrals.reject", "Referrals: reject a reward, disable a code", "X", "X", "-", "-", "-"),
    _p("passes.revoke", "Import-reward passes: revoke", "X", "X", "-", "-", "-"),
    _p("tickets.manage", "Support inbox", "W", "W", "W", "-", "-"),
    _p("moderation.act", "Content moderation (shared and public trip pages)", "W", "W", "W", "-", "W"),
    _p("system.health", "Provider and system health", "R", "R", "-", "r", "-"),
    _p("finance.reports", "Finance reports and CSV export", "R", "r", "-", "X", "-"),
    _p("settings.ceilings.write", "Settings (prices display, credit prices, ceilings)", "X", "W", "-", "R", "-"),
    _p("audit.read", "Audit log", "R", "R", "r", "r", "r"),
    _p("admin_users.manage", "Admin users and roles", "X", "-", "-", "-", "-"),
)
BY_NAME: dict[str, Permission] = {p.name: p for p in PERMISSIONS}
KNOWN = frozenset(BY_NAME) | ANY_ADMIN


def level(role: str, name: str) -> str:
    p = BY_NAME.get(name)
    return p.levels.get(role, "-") if p else "-"


def permits(role: str, name: str, need: str = "read") -> bool:
    """True when `role` holds `name` at the level `need` ("read" or "write") asks for. Unknown role or name: False."""
    if name in ANY_ADMIN:
        return role in ROLES
    return LEVEL_RANK[level(role, name)] >= NEEDS[need]


def for_role(role: str) -> dict[str, str]:
    """name -> level for every permission the role holds at all (the session response)."""
    return {p.name: p.levels[role] for p in PERMISSIONS if role in p.levels and p.levels[role] != "-"}
