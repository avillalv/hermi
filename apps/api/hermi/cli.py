import argparse
import sys
from pathlib import Path

HOST = "127.0.0.1"


def uvicorn_kwargs(port: int = 8100) -> dict:
    # uvicorn ignores the asyncio event loop policy; ask for the selector loop on Windows.
    return {
        "host": HOST,
        "port": port,
        # The access log would print raw invite tokens; 02 section 9 logs route templates only.
        "access_log": False,
        "loop": "asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
    }


def api(host: str = HOST) -> None:
    """Run the API at PORT, on loopback unless --host says otherwise (the image passes 0.0.0.0).
    Bad config exits before the server binds."""
    import uvicorn

    from hermi.config import ConfigError, load_settings
    from hermi.main import create_app

    try:
        settings = load_settings(bind_host=host)
    except ConfigError as e:
        sys.exit(str(e))
    uvicorn.run(create_app(settings), **{**uvicorn_kwargs(settings.port), "host": host})


def migrate() -> None:
    """Upgrade to head as hermi_migrate_login (MIGRATION_DATABASE_URL), one migrator at a time."""
    from alembic import command
    from alembic.config import Config

    from hermi.config import ConfigError
    from hermi.db import MigrationError

    try:
        command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")
    except (ConfigError, MigrationError) as e:
        sys.exit(str(e))


def seed() -> None:
    """Run the 03 section 11 seed as hermi_migrate_login. Idempotent: ON CONFLICT DO NOTHING."""
    from sqlalchemy import create_engine, pool

    from hermi.config import ConfigError, migration_database_url
    from hermi.db import sqlalchemy_url
    from hermi.seed import SEED_SQL

    try:
        url = migration_database_url()
    except ConfigError as e:
        sys.exit(str(e))
    engine = create_engine(sqlalchemy_url(url), poolclass=pool.NullPool)
    with engine.begin() as conn:
        conn.exec_driver_sql(SEED_SQL)


PLACEHOLDERS = {"worker": "WF-046", "scheduler": "WF-051"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hermi")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("api", help="run the API").add_argument("--host", default=HOST)
    sub.add_parser("migrate", help="upgrade the database to the latest revision")
    seed_parser = sub.add_parser("seed", help="load the Phase 1 seed data (safe to re-run)")
    # shortcut: --demo is accepted and loads the same seed; demo trips arrive from prompt 11 on.
    seed_parser.add_argument("--demo", action="store_true", help="also load demo data (none yet)")
    for name in PLACEHOLDERS:
        sub.add_parser(name, help=f"arrives with {PLACEHOLDERS[name]}")
    args = parser.parse_args(argv)
    if args.command in PLACEHOLDERS:
        # shortcut: fail loudly until the real command lands, so a deploy never idles silently.
        sys.exit(f"hermi {args.command} arrives with {PLACEHOLDERS[args.command]}")
    if args.command == "migrate":
        migrate()
        return
    if args.command == "seed":
        seed()
        return
    api(args.host)
