# ruff: noqa: E501  (long SQL strings)
"""WF-058.1: `hermi admin-grant <email>` writes the first admin_users row (08 section 2.2, 03 section 11.6)."""

import pytest

from hermi import cli


@pytest.fixture
def env(monkeypatch, db_urls):
    monkeypatch.setenv("ENVIRONMENT", "ci")
    monkeypatch.setenv("DATABASE_URL_SYSTEM", db_urls["system"])


def _row(system_conn, email):
    return system_conn.execute(
        "SELECT a.role, a.disabled_at, a.mfa_enrolled FROM admin_users a JOIN users u ON u.id = a.user_id WHERE u.email = %s",
        (email,),
    ).fetchone()


def _grants(system_conn, email):
    return system_conn.execute(
        "SELECT count(*) FROM audit_log l JOIN users u ON u.id::text = l.entity_id WHERE l.action = 'admin_user.grant' AND u.email = %s",
        (email,),
    ).fetchone()[0]


def test_grant_makes_an_owner_and_is_idempotent(env, make_user, system_conn):
    _, subject = make_user()
    email = f"{subject[:10]}@example.com"
    cli.main(["admin-grant", email])
    assert _row(system_conn, email) == ("owner", None, False)
    cli.main(["admin-grant", email.upper()])
    assert _row(system_conn, email) == ("owner", None, False)
    n = system_conn.execute("SELECT count(*) FROM admin_users a JOIN users u ON u.id = a.user_id WHERE u.email = %s", (email,)).fetchone()[0]
    assert n == 1 and _grants(system_conn, email) == 1  # the second run changed nothing, so wrote nothing


def test_email_flag_and_role(env, make_user, system_conn):
    _, subject = make_user()
    email = f"{subject[:10]}@example.com"
    cli.main(["admin-grant", "--email", email, "--role", "support"])
    assert _row(system_conn, email)[0] == "support"


def test_regrant_re_enables_and_sets_the_role(env, make_user, system_conn):
    uid, subject = make_user()
    email = f"{subject[:10]}@example.com"
    system_conn.execute("INSERT INTO admin_users (user_id, role, disabled_at) VALUES (%s, 'support', now())", (uid,))
    cli.main(["admin-grant", email])
    assert _row(system_conn, email) == ("owner", None, False)


def test_unknown_email_needs_create_user(env, system_conn, capsys):
    email = "first-founder@example.com"
    with pytest.raises(SystemExit, match="--create-user"):
        cli.main(["admin-grant", email])
    assert _row(system_conn, email) is None
    cli.main(["admin-grant", email, "--create-user"])
    assert _row(system_conn, email) == ("owner", None, False)


def test_bad_role_and_missing_email_exit(env):
    with pytest.raises(SystemExit):
        cli.main(["admin-grant", "a@example.com", "--role", "root"])
    with pytest.raises(SystemExit):
        cli.main(["admin-grant"])


def test_needs_the_worker_login(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "ci")
    monkeypatch.delenv("DATABASE_URL_SYSTEM", raising=False)
    with pytest.raises(SystemExit, match="DATABASE_URL_SYSTEM"):
        cli.main(["admin-grant", "a@example.com"])
