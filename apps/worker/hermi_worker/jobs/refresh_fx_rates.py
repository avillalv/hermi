# ruff: noqa: E501
"""refresh_fx_rates: daily 06:00, api lane, Frankfurter (02 section 7). Upsert by currency, so a rerun is harmless.

shortcut: no queue yet, so the transient x5 retry policy is the runtime's job to apply when it wires this in.
Ceiling: until then one failed run waits for the next day. Upgrade trigger: the Procrastinate wiring ticket.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.db import make_engine
from hermi.modules.flights.fx import refresh_fx_rates

NAME = "refresh_fx_rates"
SCHEDULE = "0 6 * * *"
RETRIES = 5
KILL_KEY = "provider.frankfurter"
_KILLED = text(
    "SELECT 1 FROM kill_switches WHERE key = :k AND engaged AND (expires_at IS NULL OR expires_at > now())"
)


def run(settings, client=None) -> int:
    """Returns the number of rates stored; 0 when skipped (PROVIDERS_MODE=fake or the kill switch is engaged)."""
    # shortcut: fake mode just skips. A recorded Frankfurter fixture for dev runs comes with the fakes ticket.
    if client is None and getattr(settings, "providers_mode", "live") == "fake":
        return 0
    # A job is not a request, so it opens the worker login directly (the SystemSession allowlist is for requests).
    engine = make_engine(settings.require("DATABASE_URL_SYSTEM"), pool_size=1, max_overflow=1)  # the ledger's failure row uses a second connection
    try:
        with Session(engine) as session:
            if session.execute(_KILLED, {"k": KILL_KEY}).first():
                return 0
            count = refresh_fx_rates(session, client)
            session.commit()
            return count
    finally:
        engine.dispose()
