# ruff: noqa: E501
"""build_digest: lane notify, hourly (02 section 5.1). The activity digest, from 08:00 local per person.

Deduplicated per user and trip by the key digest:<trip_id>:<local date>, so at most one a day per person and trip.
"""

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.notifications import service

NAME = "build_digest"
LANE = "notify"
SCHEDULE = "5 * * * *"
RETRIES = 3
ARGS = ()


def run(session: Session, settings: Settings) -> int:
    """Returns the number of digests created."""
    return service.build_digests(session)
