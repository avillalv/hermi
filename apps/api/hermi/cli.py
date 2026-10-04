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


def api() -> None:
    """Run the API on loopback at PORT. Bad config exits before the server binds."""
    import uvicorn

    from hermi.config import ConfigError, load_settings
    from hermi.main import create_app

    try:
        settings = load_settings(bind_host=HOST)
    except ConfigError as e:
        sys.exit(str(e))
    uvicorn.run(create_app(settings), **uvicorn_kwargs(settings.port))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hermi")
    parser.add_subparsers(dest="command", required=True).add_parser("api", help="run the API")
    parser.parse_args(argv)
    api()
