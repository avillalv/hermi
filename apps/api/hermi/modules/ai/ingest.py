"""Evidence rules for AI output, ported from Trip Planner `services/agent_ingest.py`.

Pure checks only. The database writes (quotes, suggestions, lodging picks, rejections) arrive with
the tables and tools that need them (WF-130 on); they call these rules. Fares must have been seen
on a page during the run (non-negotiable rule 4).
"""

import ipaddress
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from urllib.parse import urlsplit

from hermi.modules.ai.policy import blocked_domain

# Hard bounds on the per-person price, in USD.
MIN_PER_PERSON_USD = Decimal(30)
MAX_PER_PERSON_USD = Decimal(15_000)
# Prices must have been seen during the run (with some slack for clock differences).
OBSERVED_SLACK = timedelta(minutes=10)

PRIVATE_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home.arpa")

__all__ = [
    "blocked_domain",
    "observed_during_run",
    "price_in_bounds",
    "source_problem",
]


def source_problem(url: str) -> str | None:
    """Why a link can't be cited as a source, or None. Sources must be public http(s) pages."""
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
    except ValueError:
        return "isn't a valid link"
    if parts.scheme not in ("http", "https") or not host:
        return "must be an http(s) link to the page that showed it"
    if host == "localhost" or host.endswith(PRIVATE_SUFFIXES):
        return "must be a public website"
    try:
        if not ipaddress.ip_address(host).is_global:
            return "must be a public website"
    except ValueError:
        if "." not in host:
            return "must be a public website"
    if brand := blocked_domain(host):
        return f"is on a {brand} site, which agents must not use"
    return None


def price_in_bounds(price_total: Decimal, passengers: int, rate: Decimal = Decimal(1)) -> bool:
    """Whether the per-person price is believable. `rate` is units of the price currency per USD."""
    if passengers < 1:
        return False
    per_person = price_total / passengers
    return MIN_PER_PERSON_USD * rate <= per_person <= MAX_PER_PERSON_USD * rate


def observed_during_run(observed: datetime, started: datetime, now: datetime) -> bool:
    """Whether a price was seen between the run's start and now, within the clock slack."""
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    return started - OBSERVED_SLACK <= observed <= now + OBSERVED_SLACK
