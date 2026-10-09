# ruff: noqa: E501
"""purge_trash: lane batch, daily 04:30 UTC (02 section 5.1, 03 section 8). Hard deletes trips in the trash for more than 30 days.

The definer function from migration 0014 does the delete and the cascade. Deleting the same rows twice does nothing, so a retry is safe.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

NAME = "purge_trash"
LANE = "batch"
SCHEDULE = "30 4 * * *"
RETRIES = 3


def run(session: Session) -> int:
    """Returns the number of trips removed."""
    return session.execute(text("SELECT purge_trash(interval '30 days')")).scalar_one()
