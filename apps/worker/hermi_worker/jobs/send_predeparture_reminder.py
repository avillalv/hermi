# ruff: noqa: E501
"""send_predeparture_reminder: lane notify, hourly (02 section 5.1). The 7-day reminder, from 09:00 local per person.

Deduplicated per user and trip by the notification key reminder:<trip_id>:7d, so a rerun in the same or a later hour makes nothing new.
"""

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.notifications import service

NAME = "send_predeparture_reminder"
LANE = "notify"
SCHEDULE = "0 * * * *"
RETRIES = 3
ARGS = ()


def run(session: Session, settings: Settings) -> int:
    """Returns the number of reminders created."""
    return service.queue_predeparture_reminders(session)
