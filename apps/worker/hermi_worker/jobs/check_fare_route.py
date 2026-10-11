# ruff: noqa: E501
"""check_fare_route: lane api, one due live route, enqueued by scan_due_routes (02 section 5.2).

shortcut: the body refreshes the route's cached fares through the same provider and ledger as refresh_cached_fares; the live
provider call, eligibility and credit spend arrive with WF-051.2 and WF-052. Upgrade trigger: WF-051.2.
"""

import uuid

import httpx
from sqlalchemy.orm import Session

from hermi.config import NotConfigured, Settings
from hermi.modules.flights import fares

NAME = "check_fare_route"
LANE = "api"
SCHEDULE = None
RETRIES = 3
ARGS = ("route_id",)


def run(session: Session, settings: Settings, route_id: str, client: httpx.Client | None = None, token: str = "") -> bool:
    """Returns True when the route was refreshed; False when Travelpayouts is not configured."""
    own = client is None
    if own:
        try:
            token, client = fares.provider_for(settings)
        except NotConfigured:
            return False
    try:
        fares.refresh_route(session, uuid.UUID(route_id), client=client, token=token)
        return True
    finally:
        if own:
            client.close()
