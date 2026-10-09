# ruff: noqa: E501
"""Entry point for `hermi worker [--lanes api,ai,notify,batch]`."""

import asyncio
import sys

from hermi.config import Settings
from hermi.jobs import LANES
from hermi_worker import observability
from hermi_worker.app import build_app, run_workers


def run(settings: Settings, lanes: str | None = None) -> None:
    observability.start(settings)
    chosen = list(dict.fromkeys(x.strip() for x in (lanes or settings.worker_lanes).split(",") if x.strip()))
    bad = [x for x in chosen if x not in LANES]
    if bad or not chosen:
        sys.exit(f"unknown lane {', '.join(bad) or '(none given)'}; use any of {', '.join(LANES)}")
    app = build_app(settings)
    try:
        # psycopg's async mode needs the selector loop on Windows.
        asyncio.run(
            run_workers(app, settings, chosen),
            loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None,
        )
    finally:
        app.sqlalchemy_engine.dispose()
        app.fairness_engine.dispose()
