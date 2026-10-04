import argparse
import sys


def uvicorn_kwargs() -> dict:
    # uvicorn ignores the asyncio event loop policy; ask for the selector loop on Windows.
    # shortcut: port is fixed; WF-006 moves it to config.py (PORT).
    return {
        "host": "127.0.0.1",
        "port": 8100,
        "loop": "asyncio:SelectorEventLoop" if sys.platform == "win32" else "auto",
    }


def api() -> None:
    """Run the API on loopback, port 8100."""
    import uvicorn

    uvicorn.run("hermi.main:app", **uvicorn_kwargs())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="hermi")
    parser.add_subparsers(dest="command", required=True).add_parser("api", help="run the API")
    parser.parse_args(argv)
    api()
