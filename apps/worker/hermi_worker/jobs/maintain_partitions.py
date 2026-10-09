# ruff: noqa: E501
"""maintain_partitions: lane batch, daily 02:30 UTC (02 section 5.1, 03 section 9).

Creates the next months' partitions through the definer function from migration 0014 and raises an alert (an error log line,
which Sentry reports) when rows sit in a default partition, because that means a month's partition was missing.
"""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

NAME = "maintain_partitions"
LANE = "batch"
SCHEDULE = "30 2 * * *"
RETRIES = 3


def run(session: Session) -> int:
    """Returns the number of partitions created."""
    created = session.execute(text("SELECT maintain_partitions()")).scalar_one()
    for parent, rows in session.execute(text("SELECT parent, row_count FROM partition_default_rows WHERE row_count > 0")):
        log.error("rows landed in a default partition", extra={"parent": parent, "rows": rows})
    return created
