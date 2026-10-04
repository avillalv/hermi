"""Alembic environment: one linear chain, one migrator at a time, short lock waits (03 section 10)."""

from alembic import context
from sqlalchemy import create_engine, pool

from hermi.config import migration_database_url
from hermi.db import (
    LOCK_TIMEOUT,
    MIGRATION_LOCK_KEY,
    STATEMENT_TIMEOUT,
    assert_single_head,
    sqlalchemy_url,
)

config = context.config


def run_migrations_online() -> None:
    assert_single_head(context.script)
    url = sqlalchemy_url(config.attributes.get("database_url") or migration_database_url())
    options = f"-c lock_timeout={LOCK_TIMEOUT} -c statement_timeout={STATEMENT_TIMEOUT}"
    engine = create_engine(url, poolclass=pool.NullPool, connect_args={"options": options})
    # The advisory lock lives on its own autocommit session so it does not disturb Alembic's transaction.
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as lock_conn:
        lock_conn.exec_driver_sql("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK_KEY,))
        try:
            with engine.connect() as conn:
                context.configure(connection=conn, target_metadata=None)
                with context.begin_transaction():
                    context.run_migrations()
        finally:
            lock_conn.exec_driver_sql("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_KEY,))


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported. Run against a database.")
run_migrations_online()
