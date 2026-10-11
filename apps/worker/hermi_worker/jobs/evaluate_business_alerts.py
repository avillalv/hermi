# ruff: noqa: E501
"""evaluate_business_alerts: lane api, every 15 minutes (08 section 10 "business" cadence, WF-056.2). Leader-only periodic task.

Runs the "business" group of the table-driven alert rules in hermi.modules.ai.reconcile (moderation age, import health,
referral and reward abuse). They scan tables with no index for the window, so they do not run every minute.
"""

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.ai import reconcile

NAME = "evaluate_business_alerts"
LANE = "api"
SCHEDULE = "*/15 * * * *"
RETRIES = 1  # the next run is the retry
ARGS = ()


def run(session: Session, settings: Settings) -> dict:
    return reconcile.evaluate_rules(session, settings, group="business")
