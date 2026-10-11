# ruff: noqa: E501
"""evaluate_alert_rules: lane api, every minute (08 section 10, WF-056.2). Leader-only periodic task.

Runs the "health" group of the table-driven alert rules in hermi.modules.ai.reconcile (the business group runs in
evaluate_business_alerts). A fired subject is silent for an hour.
"""

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.ai import reconcile

NAME = "evaluate_alert_rules"
LANE = "api"
SCHEDULE = "* * * * *"
RETRIES = 1  # the next minute is the retry
ARGS = ()


def run(session: Session, settings: Settings) -> dict:
    return reconcile.evaluate_rules(session, settings, group="health")
