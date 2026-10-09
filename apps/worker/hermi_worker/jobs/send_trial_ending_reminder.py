# ruff: noqa: E501
"""send_trial_ending_reminder: lane notify, hourly (02 section 5.1). Reminds a person 2 days before their annual trial converts.

Deduplicated per user and trial period by the key trial_ending:<period end date>. WF-051 owns the billing trigger and calls the same service function.
"""

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.notifications import service

NAME = "send_trial_ending_reminder"
LANE = "notify"
SCHEDULE = "10 * * * *"
RETRIES = 3
ARGS = ()


def run(session: Session, settings: Settings) -> int:
    """Returns the number of reminders created."""
    return service.queue_trial_ending_reminders(session)
