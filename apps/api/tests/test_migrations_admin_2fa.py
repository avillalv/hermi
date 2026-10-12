# ruff: noqa: E501  (long SQL strings)
"""WF-058.2: revision 0028_admin_2fa. Four admin tables, closed to the app login like admin_users, one head, and a clean
downgrade and upgrade."""

import os

import psycopg
import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from tests.test_migrations import _alembic_cfg

from hermi import db

TABLES = ("admin_credentials", "admin_recovery_codes", "admin_sessions", "admin_auth_challenges")


@pytest.fixture
def app_engine(db_urls):
    e = create_engine(db.sqlalchemy_url(db_urls["app"]))
    yield e
    e.dispose()


@pytest.fixture
def admin_conn(db_urls):
    """Autocommit connection as the admin login (TEST_DATABASE_URL_ADMIN): the role that works these four tables."""
    url = os.environ.get("TEST_DATABASE_URL_ADMIN")
    if not url:
        if os.environ.get("CI") and not os.environ.get("HERMI_TESTS_WITHOUT_DB"):
            pytest.fail("TEST_DATABASE_URL_ADMIN is not set")
        pytest.skip("TEST_DATABASE_URL_ADMIN is not set")
    with psycopg.connect(db.psycopg_url(url), autocommit=True) as c:
        yield c


def _admin(system_conn, make_user):
    uid, _ = make_user()
    system_conn.execute("INSERT INTO admin_users (user_id, role) VALUES (%s, 'owner')", (uid,))
    return uid


def test_one_head_and_0028_follows_0027(db_urls):
    s = ScriptDirectory.from_config(_alembic_cfg(db_urls["migrate"]))
    assert s.get_heads() == ["0028_admin_2fa"]
    assert s.get_revision("0028_admin_2fa").down_revision == "0027_credit_balance_definer"


def test_the_api_login_cannot_touch_the_admin_tables(app_engine):
    for t in TABLES:
        for sql in (f"SELECT * FROM {t}", f"DELETE FROM {t}"):
            with app_engine.connect() as c, pytest.raises(DBAPIError) as e:
                c.execute(text(sql))
            assert "permission denied" in str(e.value), (t, sql)


def test_the_worker_login_has_no_privileges_on_the_admin_tables(system_conn):
    """03 section 6.1 and 0028: closed to the worker as well as the API; only hermi_admin works them."""
    for t in TABLES:
        for p in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            ok = system_conn.execute("SELECT has_table_privilege('hermi_worker_login', %s, %s)", (t, p)).fetchone()[0]
            assert not ok, (t, p)
        for p in ("SELECT", "INSERT", "UPDATE", "DELETE"):  # the admin login still works them
            assert system_conn.execute("SELECT has_table_privilege('hermi_admin_login', %s, %s)", (t, p)).fetchone()[0], (t, p)


def test_credential_shape_and_uniqueness(system_conn, admin_conn, make_user):
    uid = _admin(system_conn, make_user)
    with pytest.raises(psycopg.errors.CheckViolation):  # a webauthn row without a key
        admin_conn.execute("INSERT INTO admin_credentials (user_id, kind, credential_id) VALUES (%s, 'webauthn', %s)", (uid, b"id"))
    with pytest.raises(psycopg.errors.CheckViolation):
        admin_conn.execute("INSERT INTO admin_credentials (user_id, kind, secret_enc) VALUES (%s, 'sms', %s)", (uid, b"x"))
    admin_conn.execute("INSERT INTO admin_credentials (user_id, kind, credential_id, public_key) VALUES (%s, 'webauthn', %s, %s)", (uid, b"id", b"k"))
    with pytest.raises(psycopg.errors.UniqueViolation):
        admin_conn.execute("INSERT INTO admin_credentials (user_id, kind, credential_id, public_key) VALUES (%s, 'webauthn', %s, %s)", (uid, b"id", b"k2"))
    admin_conn.execute("INSERT INTO admin_credentials (user_id, kind, secret_enc) VALUES (%s, 'totp', %s)", (uid, b"s"))
    with pytest.raises(psycopg.errors.UniqueViolation):  # one pending TOTP enrolment at a time
        admin_conn.execute("INSERT INTO admin_credentials (user_id, kind, secret_enc) VALUES (%s, 'totp', %s)", (uid, b"s2"))


def test_rows_go_with_the_admin(system_conn, admin_conn, make_user):
    uid = _admin(system_conn, make_user)
    admin_conn.execute("INSERT INTO admin_recovery_codes (user_id, salt, code_hash) VALUES (%s, %s, %s)", (uid, b"s", b"h"))
    admin_conn.execute(
        "INSERT INTO admin_auth_challenges (user_id, purpose, challenge, expires_at) VALUES (%s, 'signin', %s, now())", (uid, b"c")
    )
    system_conn.execute("DELETE FROM admin_users WHERE user_id = %s", (uid,))
    for t in ("admin_recovery_codes", "admin_auth_challenges"):
        assert admin_conn.execute(f"SELECT count(*) FROM {t} WHERE user_id = %s", (uid,)).fetchone()[0] == 0


def test_downgrade_and_upgrade_are_clean(db_urls, system_conn):
    cfg = _alembic_cfg(db_urls["migrate"])
    command.downgrade(cfg, "0027_credit_balance_definer")
    for t in TABLES:
        assert system_conn.execute("SELECT to_regclass(%s)", (t,)).fetchone()[0] is None
    command.upgrade(cfg, "head")
    for t in TABLES:
        assert system_conn.execute("SELECT to_regclass(%s)", (t,)).fetchone()[0] is not None
