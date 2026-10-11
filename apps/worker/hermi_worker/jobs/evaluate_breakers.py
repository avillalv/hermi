# ruff: noqa: E501
"""evaluate_breakers: lane api, every minute (06 section 6.6, 08 section 6.5). Leader-only periodic task.

It runs on the api lane so a long agent run on the ai lane never delays a breaker. One pass is idempotent: a rerun
writes nothing new (see hermi.modules.ai.breakers).
"""

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.ai import breakers

NAME = "evaluate_breakers"
LANE = "api"
SCHEDULE = "* * * * *"
RETRIES = 1  # the next minute is the retry
ARGS = ()


def run(session: Session, settings: Settings) -> dict:
    return breakers.evaluate(session, settings)
