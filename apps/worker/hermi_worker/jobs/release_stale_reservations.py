# ruff: noqa: E501
"""release_stale_reservations: lane api, every 5 minutes (02 section 5.1). Settles abandoned credit reservations at 0.

The SQL function (WF-044) is idempotent: a reservation already settled is not touched, so a retry or a second run is harmless.
"""

from sqlalchemy.orm import Session

from hermi.modules.credits import service

NAME = "release_stale_reservations"
LANE = "api"
SCHEDULE = "*/5 * * * *"
RETRIES = 3


def run(session: Session) -> int:
    """Returns the number of reservations released."""
    return service.release_stale_reservations(session)
