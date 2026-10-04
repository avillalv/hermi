import argparse
import sys

HOST = "127.0.0.1"


def uvicorn_kwargs(port: int = 8100) -> dict:
    # uvicorn ignores the asyncio event loop policy; ask for the selector loop on Windows.
    return {
        "host": HOST,
        "port": port,
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


PLACEHOLDERS = {"worker": "WF-046", "scheduler": "WF-051", "migrate": "WF-011"}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hermi")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("api", help="run the API").add_argument("--host", default=HOST)
    for name in PLACEHOLDERS:
        sub.add_parser(name, help=f"arrives with {PLACEHOLDERS[name]}")
    args = parser.parse_args(argv)
    if args.command in PLACEHOLDERS:
        # shortcut: fail loudly until the real command lands, so a deploy never idles silently.
        sys.exit(f"hermi {args.command} arrives with {PLACEHOLDERS[args.command]}")
    api(args.host)
