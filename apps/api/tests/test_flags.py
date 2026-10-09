# ruff: noqa: E501  (long SQL strings)
"""WF-042: flag evaluation, the 5 second cache, NOTIFY invalidation, fail closed for paid calls, audited switches."""

import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hermi import db
from hermi.errors import ApiError
from hermi.modules.admin import flags as f


def flag(key="f", enabled=True, pct=100, rules=None):
    return f.Flag(key=key, kind="flag", enabled=enabled, rollout_pct=pct, rules=rules or {}, variants={})


def sw(key, engaged=True, expires_at=None):
    return f.Switch(key=key, engaged=engaged, expires_at=expires_at)


class Clock:
    def __init__(self):
        self.t = 1_000_000.0

    def __call__(self):
        return self.t


def runtime(flags=(), switches=(), fail=None):
    clock = Clock()
    calls = []

    def loader():
        calls.append(1)
        if fail and fail[0]:
            raise RuntimeError("db down")
        return f.Snapshot({x.key: x for x in flags}, {x.key: x for x in switches})

    rt = f.FlagRuntime(loader, clock=clock)
    rt.calls = calls
    return rt, clock


# --- evaluation rules ---------------------------------------------------------------------------------------------


def test_disabled_flag_is_off_and_unknown_flag_is_off():
    assert not f.evaluate_flag(flag(enabled=False), f.Ctx())
    rt, _ = runtime()
    assert rt.evaluate("nope") is False


def test_percent_rollout_is_stable_per_user_and_roughly_proportional():
    users = [uuid.uuid4() for _ in range(2000)]
    on = [u for u in users if f.evaluate_flag(flag(pct=30), f.Ctx(user_id=u))]
    assert 450 < len(on) < 750
    assert all(f.evaluate_flag(flag(pct=30), f.Ctx(user_id=u)) for u in on[:20])
    assert not f.evaluate_flag(flag(pct=0), f.Ctx(user_id=users[0]))
    assert f.evaluate_flag(flag(pct=100), f.Ctx())
    assert not f.evaluate_flag(flag(pct=50), f.Ctx())  # no user, partial rollout


def test_rollout_depends_on_the_key():
    users = [uuid.uuid4() for _ in range(300)]
    a = {u for u in users if f.evaluate_flag(flag("a", pct=50), f.Ctx(user_id=u))}
    b = {u for u in users if f.evaluate_flag(flag("b", pct=50), f.Ctx(user_id=u))}
    assert a != b


@pytest.mark.parametrize(
    ("rules", "ctx", "want"),
    [
        ({"tiers": ["plus"]}, f.Ctx(tier="plus"), True),
        ({"tiers": ["plus"]}, f.Ctx(tier="free"), False),
        ({"tiers": ["plus"]}, f.Ctx(), False),
        ({"platforms": ["ios"]}, f.Ctx(platform="ios"), True),
        ({"platforms": ["ios"]}, f.Ctx(platform="web"), False),
        ({"countries": ["US", "CA"]}, f.Ctx(country="CA"), True),
        ({"countries": ["US", "CA"]}, f.Ctx(country="DE"), False),
        ({"min_app_version": "1.2.0"}, f.Ctx(app_version="1.10.0"), True),
        ({"min_app_version": "1.2.0"}, f.Ctx(app_version="1.1.9"), False),
        ({"max_app_version": "1.9.9"}, f.Ctx(app_version="1.9.9"), True),
        ({"max_app_version": "1.9.9"}, f.Ctx(app_version="2.0.0"), False),
        ({"min_app_version": "1.2.0"}, f.Ctx(), False),
        ({"tiers": ["plus"], "platforms": ["ios"]}, f.Ctx(tier="plus", platform="web"), False),
    ],
)
def test_rules(rules, ctx, want):
    assert f.evaluate_flag(flag(rules=rules), ctx) is want


def test_user_ids_rule():
    me = uuid.uuid4()
    r = {"user_ids": [str(me)]}
    assert f.evaluate_flag(flag(rules=r), f.Ctx(user_id=me))
    assert not f.evaluate_flag(flag(rules=r), f.Ctx(user_id=uuid.uuid4()))
    assert not f.evaluate_flag(flag(rules=r), f.Ctx())


# --- cache ----------------------------------------------------------------------------------------------------------


def test_snapshot_is_cached_for_5_seconds_then_reloaded():
    rt, clock = runtime([flag("x")])
    assert rt.evaluate("x") and rt.evaluate("x")
    assert len(rt.calls) == 1
    clock.t += 4.9
    rt.evaluate("x")
    assert len(rt.calls) == 1
    clock.t += 0.2
    rt.evaluate("x")
    assert len(rt.calls) == 2


def test_invalidate_forces_a_reload():
    rt, _ = runtime([flag("x")])
    rt.evaluate("x")
    rt.invalidate()
    rt.evaluate("x")
    assert len(rt.calls) == 2


# --- switches and fail closed ---------------------------------------------------------------------------------------


def test_expired_engaged_switch_counts_as_cleared():
    rt, clock = runtime(switches=[sw("ai.all", expires_at=datetime.fromtimestamp(1_000_100, UTC))])
    assert rt.switch_engaged("ai.all")
    clock.t = 1_000_101
    assert not rt.switch_engaged("ai.all")
    rt.ensure_paid_allowed()


def test_each_switch_blocks_only_its_feature_and_ai_all_blocks_everything():
    rt, _ = runtime(switches=[sw("ai.all", False), sw("ai.draft"), sw("ai.research", False)])
    with pytest.raises(ApiError) as e:
        rt.ensure_paid_allowed("ai.draft")
    assert (e.value.status, e.value.code) == (503, "ai_unavailable")
    rt.ensure_paid_allowed("ai.research")
    rt.ensure_paid_allowed("ai.explain")
    rt.ensure_paid_allowed()
    rt2, _ = runtime(switches=[sw("ai.all")])
    for keys in (("ai.draft",), ("ai.research",), ()):
        with pytest.raises(ApiError):
            rt2.ensure_paid_allowed(*keys)


def test_user_hold_and_tier_switches():
    me, other = uuid.uuid4(), uuid.uuid4()
    rt, _ = runtime(switches=[sw(f"user:{me}"), sw("ai.free_tier")])
    with pytest.raises(ApiError):
        rt.ensure_paid_allowed(user_id=me)
    rt.ensure_paid_allowed(user_id=other, tier="plus")
    with pytest.raises(ApiError):
        rt.ensure_paid_allowed(user_id=other, tier="free")
    rt3, _ = runtime(switches=[sw("ai.all_but_paid")])
    rt3.ensure_paid_allowed(tier="plus")
    with pytest.raises(ApiError):
        rt3.ensure_paid_allowed(tier="free")


def test_unreadable_tables_fail_closed_for_paid_calls_but_flags_use_last_good():
    fail = [False]
    rt, clock = runtime([flag("x")], fail=fail)
    rt.ensure_paid_allowed()
    fail[0] = True
    clock.t += 6
    with pytest.raises(ApiError) as e:
        rt.ensure_paid_allowed("ai.draft")
    assert e.value.status == 503
    assert rt.evaluate("x") is True  # a non-paid read keeps the last good snapshot
    fail[0] = False
    clock.t += 6
    rt.ensure_paid_allowed()


def test_never_loaded_and_unreadable_fails_closed():
    rt, _ = runtime(fail=[True])
    with pytest.raises(ApiError):
        rt.ensure_paid_allowed()
    assert rt.evaluate("x") is False


def test_unreachable_database_blocks_paid_calls_via_the_real_loader():
    bad = create_engine("postgresql+psycopg://nobody:x@127.0.0.1:1/none", connect_args={"connect_timeout": 1})
    try:
        with pytest.raises(ApiError):
            f.FlagRuntime(f.engine_loader(bad)).ensure_paid_allowed()
    finally:
        bad.dispose()


# --- database: audited writes, NOTIFY -------------------------------------------------------------------------------


@pytest.fixture
def sys_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["system"]), pool_size=4)
    yield e
    e.dispose()


@pytest.fixture
def app_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]))
    yield e
    e.dispose()


def _audit(system_conn, key):
    return system_conn.execute(
        "SELECT action, actor_type, actor_user_id, retention_class, entity_type, reason, before, after FROM audit_log WHERE entity_id = %s ORDER BY id",
        (key,),
    ).fetchall()


def _reset_switch(system_conn, key):
    system_conn.execute("INSERT INTO kill_switches (key) VALUES (%s) ON CONFLICT DO NOTHING", (key,))
    system_conn.execute("UPDATE kill_switches SET engaged = false, engaged_at = NULL, expires_at = NULL, engaged_by = NULL WHERE key = %s", (key,))


def _in_an_hour():
    return datetime.now(UTC) + timedelta(hours=1)


def test_engage_and_clear_write_audit_rows(sys_engine, system_conn, make_user):
    admin, _ = make_user()
    key = "ai.research"
    _reset_switch(system_conn, key)
    exp = _in_an_hour()
    with Session(sys_engine) as s, s.begin():
        f.engage_switch(s, key, actor_type="admin", actor_user_id=admin, reason="drill", expires_at=exp)
    row = system_conn.execute("SELECT engaged, engaged_by, reason, expires_at FROM kill_switches WHERE key = %s", (key,)).fetchone()
    assert row == (True, admin, "drill", exp)
    with Session(sys_engine) as s, s.begin():
        f.clear_switch(s, key, actor_type="admin", actor_user_id=admin, reason="done")
    assert system_conn.execute("SELECT engaged, expires_at FROM kill_switches WHERE key = %s", (key,)).fetchone() == (False, None)
    a = _audit(system_conn, key)
    assert [r[:5] for r in a] == [
        ("killswitch.engage", "admin", admin, "extended", "kill_switch"),
        ("killswitch.clear", "admin", admin, "extended", "kill_switch"),
    ]
    assert a[0][5] == "drill" and a[0][7]["engaged"] is True and a[1][6]["engaged"] is True


def test_admin_switch_needs_an_expiry_except_provider_keys(sys_engine, system_conn, make_user):
    admin, _ = make_user()
    _reset_switch(system_conn, "ai.explain")
    with Session(sys_engine) as s, pytest.raises(ApiError) as e:
        f.engage_switch(s, "ai.explain", actor_type="admin", actor_user_id=admin, reason="x")
    assert e.value.status == 422
    assert _audit(system_conn, "ai.explain") == []
    _reset_switch(system_conn, "provider.geoapify")
    with Session(sys_engine) as s, s.begin():
        f.engage_switch(s, "provider.geoapify", actor_type="admin", actor_user_id=admin, reason="incident")
        f.clear_switch(s, "provider.geoapify", actor_type="admin", actor_user_id=admin)


def test_system_engage_and_user_hold_created_on_demand(sys_engine, system_conn):
    hold = f"user:{uuid.uuid4()}"
    with Session(sys_engine) as s, s.begin():
        f.engage_switch(s, hold, actor_type="system", reason="breaker", expires_at=_in_an_hour())
    assert system_conn.execute("SELECT engaged, engaged_by FROM kill_switches WHERE key = %s", (hold,)).fetchone() == (True, None)
    assert _audit(system_conn, hold)[0][:2] == ("killswitch.engage", "system")


def test_rolled_back_engage_leaves_no_audit_row(sys_engine, system_conn):
    _reset_switch(system_conn, "ai.packing")
    with Session(sys_engine) as s:
        f.engage_switch(s, "ai.packing", actor_type="system", reason="r", expires_at=_in_an_hour())
        s.rollback()
    assert _audit(system_conn, "ai.packing") == []
    assert system_conn.execute("SELECT engaged FROM kill_switches WHERE key = 'ai.packing'").fetchone() == (False,)


def test_app_role_runtime_sees_an_engaged_switch_within_the_ttl(app_engine, sys_engine, system_conn, make_user):
    admin, _ = make_user()
    _reset_switch(system_conn, "ai.all")
    rt = f.FlagRuntime(f.engine_loader(app_engine))  # the API login, real 5 second TTL
    rt.ensure_paid_allowed()
    with Session(sys_engine) as s, s.begin():
        f.engage_switch(s, "ai.all", actor_type="admin", actor_user_id=admin, reason="drill", expires_at=_in_an_hour())
    try:
        deadline = time.monotonic() + 5.5
        blocked = False
        while time.monotonic() < deadline and not blocked:
            try:
                rt.ensure_paid_allowed()
                time.sleep(0.25)
            except ApiError:
                blocked = True
        assert blocked
    finally:
        with Session(sys_engine) as s, s.begin():
            f.clear_switch(s, "ai.all", actor_type="admin", actor_user_id=admin)


def test_notify_makes_a_change_visible_before_the_ttl(app_engine, sys_engine, system_conn, db_urls, make_user):
    admin, _ = make_user()
    _reset_switch(system_conn, "ai.taster")
    rt = f.FlagRuntime(f.engine_loader(app_engine), ttl=60)
    rt.ensure_paid_allowed("ai.taster")  # cached for a minute
    listener = f.start_listener(db.psycopg_url(db_urls["app"]), rt)
    try:
        time.sleep(0.5)
        with Session(sys_engine) as s, s.begin():
            f.engage_switch(s, "ai.taster", actor_type="admin", actor_user_id=admin, reason="drill", expires_at=_in_an_hour())
        deadline = time.monotonic() + 3
        blocked = False
        while time.monotonic() < deadline and not blocked:
            try:
                rt.ensure_paid_allowed("ai.taster")
                time.sleep(0.05)
            except ApiError:
                blocked = True
        assert blocked
    finally:
        listener.stop()
        with Session(sys_engine) as s, s.begin():
            f.clear_switch(s, "ai.taster", actor_type="admin", actor_user_id=admin)
