# ruff: noqa: E501
"""send_email: lane notify, an event job (02 section 5.1). Mails one notification row.

Unique per (user, template, dedupe_key) through the notifications row: the row is locked and email_sent_at is checked under the lock,
so a retried or duplicated job never sends twice. During quiet hours the job queues itself again for the end of the quiet window.
"""

import uuid

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.notifications import service

NAME = "send_email"
LANE = "notify"
SCHEDULE = None  # event job, no cron
RETRIES = 5
ARGS = ("notification_id",)


def run(session: Session, settings: Settings, notification_id: str) -> str:
    """Returns sent, already_sent, deferred, blocked, missing or skipped:<why>."""
    return service.deliver_email(session, settings, uuid.UUID(notification_id))
