# ruff: noqa: E501  (long SQL strings; one statement per line reads better)
"""WF-012.2: revision 0004_trips_people (03 sections 5.4, 5.5, 10) and the schema-vs-DDL comparison for 0002 to 0004.

Constraints are exercised as the migrate login (the owner), because grants land in 0014_rls.
The definer functions need table access for hermi_definer, which 0014 grants; the tests grant it here.
"""

import re
import uuid
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from tests.test_migrations import APP_URL, MIGRATE_URL, _alembic_cfg, _need_db

from hermi import db
from hermi.modules.auth import models as _auth  # noqa: F401  (register on Base.metadata)
from hermi.modules.catalog import models as _catalog  # noqa: F401
from hermi.modules.collaboration import models as _collab  # noqa: F401
from hermi.modules.trips import models as _trips  # noqa: F401

SPEC = Path(__file__).resolve().parents[3] / "app-buildout/phase-1-launch/03-database-schema.md"


@pytest.fixture
def conn():
    _need_db()
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    with psycopg.connect(db.psycopg_url(MIGRATE_URL), autocommit=True) as c:
        yield c


def _fails(c, exc, sql, *params):
    with pytest.raises(exc):
        c.execute(sql, params)


def _user(c, email=None):
    email = email or f"{uuid.uuid4().hex[:8]}@example.com"
    return c.execute("INSERT INTO users (email) VALUES (%s) RETURNING id", (email,)).fetchone()[0]


def _trip(c, owner, name="Lisbon"):
    return c.execute(
        "INSERT INTO trips (owner_user_id, name, home_currency) VALUES (%s, %s, 'USD') RETURNING id",
        (owner, name),
    ).fetchone()[0]


def _as(c, user):
    c.execute("SELECT set_config('app.user_id', %s, false)", (str(user) if user else "",))


def test_chain_is_linear_and_single_head():
    s = ScriptDirectory.from_config(_alembic_cfg())
    assert s.get_revision("0004_trips_people").down_revision == "0003_reference_catalog"
    assert len(s.get_heads()) == 1


def test_tables_and_functions_exist_and_round_trip(conn):
    names = (
        "trips trip_members trip_invites trip_share_links trip_destinations activity_log "
        "people trip_people"
    ).split()
    for n in names:
        assert conn.execute("SELECT to_regclass(%s)", (n,)).fetchone()[0], n
    row = conn.execute(
        "SELECT to_regtype('trip_status'), to_regtype('trip_role'), "
        "to_regproc('redeem_trip_invite'), to_regproc('transfer_trip_owner'), "
        "to_regproc('trips_add_owner_member')"
    ).fetchone()
    assert all(r is not None for r in row)
    # No household tables (03 section 1.1).
    assert conn.execute(
        "SELECT to_regclass('households'), to_regclass('household_members')"
    ).fetchone() == (None, None)
    cfg = _alembic_cfg(MIGRATE_URL)
    command.downgrade(cfg, "0003_reference_catalog")
    assert (
        conn.execute(
            "SELECT to_regclass('trips'), to_regclass('people'), to_regtype('trip_role'), "
            "to_regproc('redeem_trip_invite'), to_regproc('transfer_trip_owner')"
        ).fetchone()
        == (None,) * 5
    )
    command.upgrade(cfg, "head")
    assert conn.execute("SELECT to_regclass('trips')").fetchone()[0]


def test_trip_defaults_checks_and_triggers(conn):
    owner = _user(conn)
    tid = _trip(conn, owner)
    assert tid.version == 7
    assert conn.execute(
        "SELECT status, version, editors_can_invite, ai_enabled, calendar_token_hash FROM trips WHERE id = %s",
        (tid,),
    ).fetchone() == ("planning", 1, False, True, None)
    conn.execute("UPDATE trips SET notes = 'x' WHERE id = %s", (tid,))
    assert conn.execute("SELECT version FROM trips WHERE id = %s", (tid,)).fetchone() == (2,)
    conn.execute("UPDATE trips SET updated_at = '2000-01-01' WHERE id = %s", (tid,))
    assert conn.execute(
        "SELECT updated_at > '2001-01-01' FROM trips WHERE id = %s", (tid,)
    ).fetchone() == (True,)
    ins = "INSERT INTO trips (owner_user_id, name, home_currency, start_date, end_date) VALUES (%s, %s, %s, %s, %s)"
    _fails(conn, psycopg.errors.CheckViolation, ins, owner, "", "USD", None, None)
    _fails(conn, psycopg.errors.CheckViolation, ins, owner, "x" * 121, "USD", None, None)
    _fails(conn, psycopg.errors.CheckViolation, ins, owner, "t", "USD", "2026-05-01", None)
    _fails(conn, psycopg.errors.CheckViolation, ins, owner, "t", "USD", "2026-05-02", "2026-05-01")
    _fails(conn, psycopg.errors.CheckViolation, ins, owner, "t", "usd", None, None)  # domain check
    conn.execute(ins, (owner, "t", "USD", "2026-05-01", "2026-05-01"))
    _fails(conn, psycopg.errors.InvalidTextRepresentation, "UPDATE trips SET status = 'gone'")
    # Owner cannot be deleted while they own a trip.
    _fails(conn, psycopg.errors.RestrictViolation, "DELETE FROM users WHERE id = %s", owner)


def test_calendar_token_hash_is_unique_when_set(conn):
    owner = _user(conn)
    a, b = _trip(conn, owner, "a"), _trip(conn, owner, "b")
    upd = "UPDATE trips SET calendar_token_hash = %s WHERE id = %s"
    conn.execute(upd, (b"h" * 32, a))
    _fails(conn, psycopg.errors.UniqueViolation, upd, b"h" * 32, b)
    conn.execute(upd, (None, a))
    conn.execute(upd, (None, b))


def test_owner_member_trigger_and_member_constraints(conn):
    owner, other = _user(conn), _user(conn)
    tid = _trip(conn, owner)
    assert conn.execute(
        "SELECT user_id, role FROM trip_members WHERE trip_id = %s", (tid,)
    ).fetchall() == [(owner, "owner")]
    ins = "INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, %s)"
    _fails(conn, psycopg.errors.UniqueViolation, ins, tid, owner, "editor")  # one row per member
    _fails(conn, psycopg.errors.UniqueViolation, ins, tid, other, "owner")  # exactly one owner
    _fails(conn, psycopg.errors.InvalidTextRepresentation, ins, tid, other, "admin")  # valid roles
    conn.execute(ins, (tid, other, "viewer"))
    # Cascade: deleting the trip removes members; deleting a member user removes their row.
    conn.execute("DELETE FROM users WHERE id = %s", (other,))
    assert conn.execute(
        "SELECT count(*) FROM trip_members WHERE trip_id = %s", (tid,)
    ).fetchone() == (1,)
    conn.execute("DELETE FROM trips WHERE id = %s", (tid,))
    assert conn.execute("SELECT count(*) FROM trip_members").fetchone() == (0,)


def test_invites_share_links_destinations_activity(conn):
    owner = _user(conn)
    tid = _trip(conn, owner)
    inv = "INSERT INTO trip_invites (trip_id, token_hash, role, max_uses, use_count) VALUES (%s, %s, %s, %s, %s)"
    conn.execute(inv, (tid, b"a", "editor", 1, 0))
    _fails(conn, psycopg.errors.UniqueViolation, inv, tid, b"a", "editor", 1, 0)
    _fails(conn, psycopg.errors.CheckViolation, inv, tid, b"b", "owner", 1, 0)
    _fails(conn, psycopg.errors.CheckViolation, inv, tid, b"c", "viewer", 0, 0)
    _fails(conn, psycopg.errors.CheckViolation, inv, tid, b"d", "viewer", 51, 0)
    _fails(conn, psycopg.errors.CheckViolation, inv, tid, b"e", "viewer", 2, 3)
    sl = "INSERT INTO trip_share_links (trip_id, token_hash) VALUES (%s, %s)"
    conn.execute(sl, (tid, b"s"))
    _fails(conn, psycopg.errors.UniqueViolation, sl, tid, b"s")
    assert conn.execute(
        "SELECT redact_address, redact_prices, redact_notes, redact_people, indexable, "
        "expires_at > now() + interval '89 days' FROM trip_share_links"
    ).fetchone() == (True, True, True, True, False, True)
    dest = "INSERT INTO trip_destinations (trip_id, position, name, lat, lon, info_status) VALUES (%s, %s, 'Porto', %s, %s, %s)"
    conn.execute(dest, (tid, 0, 41.1, -8.6, "pending"))
    _fails(conn, psycopg.errors.UniqueViolation, dest, tid, 0, 41.1, -8.6, "pending")
    _fails(conn, psycopg.errors.CheckViolation, dest, tid, 1, 91, 0, "pending")
    _fails(conn, psycopg.errors.CheckViolation, dest, tid, 1, 0, 181, "pending")
    _fails(conn, psycopg.errors.CheckViolation, dest, tid, 1, 0, 0, "bogus")
    # The position uniqueness is deferred, so a swap inside one transaction is allowed.
    with conn.transaction():
        conn.execute(dest, (tid, 1, 0, 0, "ready"))
        conn.execute(
            "UPDATE trip_destinations SET position = CASE position WHEN 0 THEN 1 ELSE 0 END WHERE trip_id = %s",
            (tid,),
        )
    act = "INSERT INTO activity_log (trip_id, actor_user_id, verb, entity_type) VALUES (%s, %s, 'added', 'note') RETURNING id"
    first, second = (
        conn.execute(act, (tid, owner)).fetchone()[0],
        conn.execute(act, (tid, owner)).fetchone()[0],
    )
    assert second > first
    _fails(
        conn,
        psycopg.errors.GeneratedAlways,
        "INSERT INTO activity_log (id, trip_id, verb, entity_type) VALUES (1, %s, 'a', 'b')",
        tid,
    )
    conn.execute("DELETE FROM trips WHERE id = %s", (tid,))
    for t in ("trip_invites", "trip_share_links", "trip_destinations", "activity_log"):
        assert conn.execute(f"SELECT count(*) FROM {t}").fetchone() == (0,), t


def test_people_and_trip_people(conn):
    me, friend = _user(conn), _user(conn)
    tid = _trip(conn, me)
    p = "INSERT INTO people (owner_user_id, linked_user_id, name, is_self) VALUES (%s, %s, %s, %s) RETURNING id"
    self_id = conn.execute(p, (me, None, "Me", True)).fetchone()[0]
    assert conn.execute(
        "SELECT color, home_airports::text[] FROM people WHERE id = %s", (self_id,)
    ).fetchone() == (
        "#FF5E7E",
        [],
    )
    _fails(
        conn, psycopg.errors.UniqueViolation, p, me, None, "Me again", True
    )  # one self per owner
    linked = conn.execute(p, (me, friend, "Friend", False)).fetchone()[0]
    _fails(
        conn, psycopg.errors.UniqueViolation, p, me, friend, "Friend 2", False
    )  # one person per linked user
    _fails(conn, psycopg.errors.CheckViolation, p, me, None, "", False)
    _fails(conn, psycopg.errors.CheckViolation, p, me, None, "x" * 61, False)
    _fails(
        conn,
        psycopg.errors.CheckViolation,
        "INSERT INTO people (owner_user_id, name, color) VALUES (%s, 'c', 'red')",
        me,
    )
    conn.execute(
        "INSERT INTO people (owner_user_id, name) VALUES (%s, 'Kid')", (me,)
    )  # unlinked people may repeat
    tp = "INSERT INTO trip_people (trip_id, person_id, added_by) VALUES (%s, %s, %s)"
    conn.execute(tp, (tid, self_id, me))
    _fails(conn, psycopg.errors.UniqueViolation, tp, tid, self_id, me)
    conn.execute("UPDATE people SET updated_at = '2000-01-01' WHERE id = %s", (linked,))
    assert conn.execute(
        "SELECT updated_at > '2001-01-01' FROM people WHERE id = %s", (linked,)
    ).fetchone() == (True,)
    # Deleting the linked account unlinks the person; deleting the owner removes their people.
    conn.execute("DELETE FROM users WHERE id = %s", (friend,))
    assert conn.execute(
        "SELECT linked_user_id FROM people WHERE id = %s", (linked,)
    ).fetchone() == (None,)
    conn.execute("DELETE FROM trips WHERE id = %s", (tid,))
    conn.execute("DELETE FROM users WHERE id = %s", (me,))
    assert conn.execute("SELECT count(*) FROM people").fetchone() == (0,)


def _grant_definer(c):
    # 0014_rls grants hermi_definer its table access; give it here so the function bodies can run.
    c.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hermi_definer"
    )


def test_redeem_trip_invite(conn):
    _grant_definer(conn)
    owner, guest = _user(conn), _user(conn)
    tid = _trip(conn, owner)
    ins = "INSERT INTO trip_invites (trip_id, invited_by, token_hash, role, max_uses) VALUES (%s, %s, %s, %s, %s)"
    conn.execute(ins, (tid, owner, b"ok", "viewer", 1))
    red = "SELECT redeem_trip_invite(%s)"
    _as(conn, None)
    _fails(conn, psycopg.errors.InsufficientPrivilege, red, b"ok")  # not_authenticated
    _as(conn, guest)
    _fails(conn, psycopg.errors.RaiseException, red, b"unknown")  # P0001 invite_expired
    assert conn.execute(red, (b"ok",)).fetchone() == (tid,)
    assert conn.execute(
        "SELECT role, invited_by FROM trip_members WHERE trip_id = %s AND user_id = %s",
        (tid, guest),
    ).fetchone() == ("viewer", owner)
    assert conn.execute(
        "SELECT use_count, accepted_by, accepted_at IS NOT NULL FROM trip_invites WHERE token_hash = %s",
        (b"ok",),
    ).fetchone() == (1, guest, True)
    # Used up now, and already a member: the used-up check comes first.
    with pytest.raises(psycopg.errors.RaiseException, match="invite_expired"):
        conn.execute(red, (b"ok",))
    # A multi-use invite for a caller who is already a member raises already_member (23505).
    conn.execute(ins, (tid, owner, b"multi", "editor", 5))
    with pytest.raises(psycopg.errors.UniqueViolation, match="already_member"):
        conn.execute(red, (b"multi",))
    # Revoked, expired and trashed-trip invites all look the same as an unknown one.
    other = _user(conn)
    _as(conn, other)
    conn.execute("UPDATE trip_invites SET revoked_at = now() WHERE token_hash = %s", (b"multi",))
    with pytest.raises(psycopg.errors.RaiseException, match="invite_expired"):
        conn.execute(red, (b"multi",))
    conn.execute(
        "UPDATE trip_invites SET revoked_at = NULL, expires_at = now() - interval '1 second' WHERE token_hash = %s",
        (b"multi",),
    )
    with pytest.raises(psycopg.errors.RaiseException, match="invite_expired"):
        conn.execute(red, (b"multi",))
    conn.execute(
        "UPDATE trip_invites SET expires_at = now() + interval '1 day' WHERE token_hash = %s",
        (b"multi",),
    )
    conn.execute("UPDATE trips SET deleted_at = now() WHERE id = %s", (tid,))
    with pytest.raises(psycopg.errors.RaiseException, match="invite_expired"):
        conn.execute(red, (b"multi",))
    conn.execute("UPDATE trips SET deleted_at = NULL WHERE id = %s", (tid,))
    assert conn.execute(red, (b"multi",)).fetchone() == (tid,)


def test_transfer_trip_owner(conn):
    _grant_definer(conn)
    owner, member, stranger = _user(conn), _user(conn), _user(conn)
    tid = _trip(conn, owner)
    conn.execute(
        "INSERT INTO trip_members (trip_id, user_id, role) VALUES (%s, %s, 'viewer')", (tid, member)
    )
    tr = "SELECT transfer_trip_owner(%s, %s)"
    _as(conn, member)  # not the owner
    _fails(conn, psycopg.errors.InsufficientPrivilege, tr, tid, member)
    _as(conn, owner)
    _fails(conn, psycopg.errors.InvalidParameterValue, tr, tid, owner)  # to self
    _fails(conn, psycopg.errors.InvalidParameterValue, tr, tid, stranger)  # not a member
    assert conn.execute(tr, (tid, member)).fetchone() == (member,)
    assert conn.execute("SELECT owner_user_id FROM trips WHERE id = %s", (tid,)).fetchone() == (
        member,
    )
    assert dict(
        conn.execute("SELECT user_id, role FROM trip_members WHERE trip_id = %s", (tid,)).fetchall()
    ) == {
        member: "owner",
        owner: "editor",
    }
    _fails(
        conn, psycopg.errors.InsufficientPrivilege, tr, tid, owner
    )  # the old owner no longer may
    # A trashed trip cannot be transferred.
    _as(conn, member)
    conn.execute("UPDATE trips SET deleted_at = now() WHERE id = %s", (tid,))
    _fails(conn, psycopg.errors.InsufficientPrivilege, tr, tid, owner)


def test_definer_functions_are_owned_and_granted_correctly(conn):
    rows = conn.execute(
        "SELECT p.proname, pg_get_userbyid(p.proowner), p.prosecdef, p.proconfig::text, "
        "has_function_privilege('hermi_app', p.oid, 'EXECUTE'), has_function_privilege('public', p.oid, 'EXECUTE') "
        "FROM pg_proc p WHERE p.proname IN ('redeem_trip_invite', 'transfer_trip_owner') ORDER BY 1"
    ).fetchall()
    assert [(r[0], r[1], r[2], r[4], r[5]) for r in rows] == [
        ("redeem_trip_invite", "hermi_definer", True, True, False),
        ("transfer_trip_owner", "hermi_definer", True, True, False),
    ]
    assert all("search_path=public" in r[3] for r in rows)


def test_app_login_can_call_definer_functions_and_not_insert_members(conn):
    _grant_definer(conn)
    owner = _user(conn)
    tid = _trip(conn, owner)
    conn.execute("INSERT INTO trip_invites (trip_id, token_hash) VALUES (%s, %s)", (tid, b"tok"))
    guest = _user(conn)
    with psycopg.connect(db.psycopg_url(APP_URL), autocommit=True) as app:
        with pytest.raises(
            psycopg.errors.InsufficientPrivilege
        ):  # not authenticated: app.user_id unset
            app.execute("SELECT redeem_trip_invite(%s)", (b"tok",))
        app.execute("SELECT set_config('app.user_id', %s, false)", (str(guest),))
        assert app.execute("SELECT redeem_trip_invite(%s)", (b"tok",)).fetchone() == (tid,)


# --- Schema vs DDL: 0002 to 0005 tables against the DDL in 03 sections 5.1 to 5.6 ---------------


def _ddl_text():
    lines = SPEC.read_text(encoding="utf-8").split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.startswith("### 5.1 "))
    end = next(i for i, ln in enumerate(lines) if ln.startswith("### 5.7 "))
    out, inside = [], False
    for ln in lines[start:end]:
        if ln.startswith("```sql"):
            inside = True
        elif ln.startswith("```"):
            inside = False
        elif inside:
            out.append(ln.split("--")[0].rstrip() if "--" in ln else ln.rstrip())
    return "\n".join(out)


def _ddl_tables(sql):
    """{table: {columns, constraints}} from every CREATE TABLE in the DDL."""
    tables = {}
    for m in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\)(?: PARTITION BY RANGE \(\w+\))?;", sql, re.S):
        cols, cons = set(), set()
        for ln in m.group(2).split("\n"):
            s = ln.strip()
            first = s.split(" ")[0].rstrip(",") if s else ""
            if first == "CONSTRAINT":
                cons.add(s.split(" ")[1])
            elif (
                first
                and first not in ("PRIMARY", "UNIQUE", "CHECK", "FOREIGN")
                and re.fullmatch(r"[a-z_]+", first)
            ):
                cols.add(first)
        tables[m.group(1)] = {"columns": cols, "constraints": cons}
    return tables


def _ddl_indexes(sql):
    """{name: (table, unique, columns, partial)} from every CREATE [UNIQUE] INDEX."""
    out = {}
    for m in re.finditer(
        r"CREATE (UNIQUE )?INDEX (\w+) ON (\w+) \(((?:[^()]|\([^()]*\))*)\)(\s+WHERE [^;]*)?;", sql
    ):
        out[m.group(2)] = (m.group(3), bool(m.group(1)), _norm_cols(m.group(4)), bool(m.group(5)))
    return out


def _norm_cols(s):
    return re.sub(r"\s+", "", s)


def _live_indexes(c):
    rows = c.execute(
        "SELECT i.relname, t.relname, x.indisunique, pg_get_indexdef(x.indexrelid) "
        "FROM pg_index x JOIN pg_class i ON i.oid = x.indexrelid JOIN pg_class t ON t.oid = x.indrelid "
        "JOIN pg_namespace n ON n.oid = t.relnamespace "
        "WHERE n.nspname = 'public' AND NOT x.indisprimary AND NOT i.relispartition AND t.relname NOT LIKE 'procrastinate%' "
        "AND NOT EXISTS (SELECT 1 FROM pg_constraint k WHERE k.conindid = x.indexrelid)"
    ).fetchall()
    out = {}
    for name, table, unique, definition in rows:
        m = re.search(r"USING btree \((.*?)\)( WHERE .*)?$", definition)
        out[name] = (table, unique, _norm_cols(m.group(1)), bool(m.group(2)))
    return out


def test_live_schema_matches_ddl_in_03(conn):
    sql = _ddl_text()
    ddl_tables, ddl_idx = _ddl_tables(sql), _ddl_indexes(sql)
    assert {"users", "devices", "plans", "trips", "people"} <= set(ddl_tables)

    live_tables = {
        r[0]
        for r in conn.execute(
            "SELECT c.relname FROM pg_class c WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p') "
            "AND NOT c.relispartition AND c.relname <> 'alembic_version' AND c.relname NOT LIKE 'procrastinate%'"
        )
    }
    assert live_tables == set(ddl_tables)

    for table, spec in ddl_tables.items():
        live_cols = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
                (table,),
            )
        }
        assert live_cols == spec["columns"], table
        live_cons = {
            r[0]
            for r in conn.execute(
                "SELECT conname FROM pg_constraint WHERE conrelid = %s::regclass AND contype IN ('c', 'u') "
                "AND conname ~ '^(ck|uq)_'",
                (table,),
            )
        }
        assert live_cons == {c for c in spec["constraints"] if re.match(r"(ck|uq)_", c)}, table
        # Every foreign key and primary key exists, so the table was not created without them.
        assert conn.execute(
            "SELECT count(*) FROM pg_constraint WHERE conrelid = %s::regclass AND contype = 'p'",
            (table,),
        ).fetchone() == (1,), table

    live_idx = _live_indexes(conn)
    # Procrastinate tables and partition children are excluded; every other public table is in the DDL range.
    assert live_idx == ddl_idx
