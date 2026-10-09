import argparse
import os
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


def worker(lanes: str | None = None) -> None:
    """Run the job workers. The only place the API package starts the worker (imported late)."""
    from hermi.config import ConfigError, NotConfigured, load_settings

    try:
        settings = load_settings(bind_host=HOST)
        settings.require("DATABASE_URL_SYSTEM")
    except (ConfigError, NotConfigured) as e:
        sys.exit(str(e))
    from hermi_worker import runner

    runner.run(settings, lanes)


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


def seed(demo: bool = False) -> None:
    """Run the 03 section 11 seed as hermi_migrate_login. Idempotent: ON CONFLICT DO NOTHING.
    With demo, also add the demo trip and sample trips (hermi.seed.demo) on the worker login."""
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
    if demo:
        from hermi.config import NotConfigured, load_settings
        from hermi.seed.demo import seed_demo

        try:
            settings = load_settings(bind_host=HOST)
            added = seed_demo(settings, system_url=settings.require("DATABASE_URL_SYSTEM"))
        except (ConfigError, NotConfigured, RuntimeError) as e:
            sys.exit(str(e))
        print(
            f"Demo seed: {added['demo_trips']} demo trip, "
            f"{added['sample_trips']} sample trips added"
        )


def ai_smoke() -> None:
    """Two real claude_cli calls: one with no tools, one capped web call (the owner plan)."""
    from hermi.config import ConfigError, load_settings
    from hermi.providers.ai import ClaudeCliProvider, ProviderRefused
    from hermi.providers.ai.claude_cli import CliRunFailed, auth_status, find_claude
    from hermi.providers.ai.smoke import run_smoke

    try:
        settings = load_settings(bind_host=HOST)
    except ConfigError as e:
        sys.exit(str(e))
    if settings.ai_provider != "claude_cli":
        sys.exit("ai-smoke needs AI_PROVIDER=claude_cli (and ENVIRONMENT=local)")
    claude = find_claude(settings)
    if claude is None:
        sys.exit("Claude Code wasn't found. Install it or set CLAUDE_CLI_PATH to the full path of the native claude binary.")
    if auth_status(claude, os.environ).signed_in is False:
        sys.exit("Claude Code isn't signed in. Run claude and type /login, then try again.")
    try:
        user = next(iter(sorted(settings.cli_allowed_emails)), None)
        provider = ClaudeCliProvider(settings, bind_host=HOST, user_email=user, claude=claude)
    except ProviderRefused as e:
        sys.exit(str(e))
    try:
        code = run_smoke(provider, settings.ai_model_fast)
    except CliRunFailed as e:
        sys.exit(str(e))
    sys.exit(code)


def import_legacy(args: argparse.Namespace) -> None:
    """Copy the old Trip Planner database into Hermi (03 section 12)."""
    from hermi.config import ConfigError, NotConfigured, load_settings, migration_database_url
    from hermi.legacy_import import ImportFailed, run_import

    try:
        settings = load_settings(bind_host=HOST)
    except ConfigError as e:
        sys.exit(str(e))
    try:
        system_url = settings.require("DATABASE_URL_SYSTEM")
    except NotConfigured:
        sys.exit("DATABASE_URL_SYSTEM is not set (the worker login the importer writes with)")
    try:
        owner_url = migration_database_url()
    except ConfigError:
        owner_url = None
    try:
        report = run_import(
            settings,
            source_url=args.source_db,
            system_url=system_url,
            source_schema=args.source_schema,
            primary_email=args.primary_email,
            partner_email=args.partner_email,
            dry_run=args.dry_run,
            owner_url=owner_url,
            primary_person_id=args.primary_person_id,
            partner_person_id=args.partner_person_id,
        )
    except ImportFailed as e:
        sys.exit(f"Import failed: {e}")
    if not report.ok:
        sys.exit(1)


PLACEHOLDERS = {"scheduler": "WF-051"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hermi")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("api", help="run the API").add_argument("--host", default=HOST)
    sub.add_parser("migrate", help="upgrade the database to the latest revision")
    seed_parser = sub.add_parser("seed", help="load the Phase 1 seed data (safe to re-run)")
    seed_parser.add_argument(
        "--demo",
        action="store_true",
        help="also add the demo trip and sample trips (local and ci only)",
    )
    legacy = sub.add_parser(
        "import-legacy", help="copy the old Trip Planner database into Hermi (one-off)"
    )
    legacy.add_argument("--source-db", required=True, help="URL of the old database (read only)")
    legacy.add_argument("--source-schema", default="public")
    legacy.add_argument("--primary-email", required=True)
    legacy.add_argument("--partner-email", required=True)
    legacy.add_argument(
        "--primary-person-id",
        type=int,
        help="legacy people.id of the primary owner (default: lowest id)",
    )
    legacy.add_argument(
        "--partner-person-id",
        type=int,
        help="legacy people.id of the partner (default: next lowest id)",
    )
    legacy.add_argument(
        "--dry-run", action="store_true", help="run everything, report, keep nothing"
    )
    sub.add_parser("ai-smoke", help="one no-tool and one capped web call through claude_cli")
    worker_parser = sub.add_parser("worker", help="run the background job workers")
    worker_parser.add_argument("--lanes", help="comma separated lanes (default: WORKER_LANES)")
    for name in PLACEHOLDERS:
        sub.add_parser(name, help=f"arrives with {PLACEHOLDERS[name]}")
    args = parser.parse_args(argv)
    if args.command in PLACEHOLDERS:
        # shortcut: fail loudly until the real command lands, so a deploy never idles silently.
        sys.exit(f"hermi {args.command} arrives with {PLACEHOLDERS[args.command]}")
    if args.command == "migrate":
        migrate()
        return
    if args.command == "ai-smoke":
        ai_smoke()
        return
    if args.command == "worker":
        worker(args.lanes)
        return
    if args.command == "seed":
        seed(args.demo)
        return
    if args.command == "import-legacy":
        import_legacy(args)
        return
    api(args.host)
