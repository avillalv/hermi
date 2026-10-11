# ruff: noqa: E501
"""reconcile_anthropic_usage: lane batch, daily at 03:15 UTC (08 section 10, WF-056.2). Leader-only periodic task.

Compares the previous UTC day's Anthropic cost report with ai_usage. Skipped for claude_cli and fake, and without
ANTHROPIC_ADMIN_API_KEY (see hermi.modules.ai.reconcile).
"""

from sqlalchemy.orm import Session

from hermi.config import Settings
from hermi.modules.ai import reconcile

NAME = "reconcile_anthropic_usage"
LANE = "batch"
SCHEDULE = "15 3 * * *"
RETRIES = 2  # a failed fetch is a skip, not a failure; the retry is for a database error
ARGS = ()


def run(session: Session, settings: Settings) -> dict:
    return reconcile.reconcile(session, settings)
