"""Pure fare helpers: a new observation, its dedupe key, and the suspect-price check.

The base app stored these in SQLAlchemy models. Hermi has no flight tables yet, so only the
DB-free parts carry over; queries (best options, date grid, live checks) return with the schema.
"""

import hashlib
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

DUPLICATE_WINDOW = timedelta(hours=12)
SUSPECT_LOW, SUSPECT_HIGH = Decimal("0.35"), Decimal(4)
MIN_SAMPLES_FOR_SUSPECT = 5


@dataclass
class NewQuote:
    source: str
    confidence: str
    origin: str
    destination: str
    depart_date: date
    return_date: date | None
    price_total: Decimal
    currency: str
    passengers: int
    observed_at: datetime
    airlines: list[str]
    stops_out: int | None = None
    stops_back: int | None = None
    duration_out_min: int | None = None
    duration_back_min: int | None = None
    depart_at_local: str | None = None
    flight_numbers: list[str] | None = None
    booking_url: str | None = None
    source_url: str | None = None
    raw: dict[str, Any] | None = None


def dedupe_key(route_id: object, q: NewQuote) -> str:
    """Same fare, same flights: different departure times at the same price stay separate."""
    parts = [
        route_id,
        q.source,
        q.origin,
        q.destination,
        q.depart_date,
        q.return_date,
        q.depart_at_local,
        ",".join(sorted(q.airlines)),
        ",".join(q.flight_numbers or []),
        q.price_total.normalize(),
        q.currency,
    ]
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:40]


def is_duplicate(seen_at: Iterable[datetime], observed_at: datetime) -> bool:
    """True if the same fare (same dedupe key) was recorded within the duplicate window."""
    return any(observed_at - DUPLICATE_WINDOW <= t for t in seen_at)


def median_per_person(prices_per_person: list[Decimal]) -> Decimal | None:
    """The median of recent unflagged prices, or None when there are too few samples to judge."""
    if len(prices_per_person) < MIN_SAMPLES_FOR_SUSPECT:
        return None
    return Decimal(statistics.median(prices_per_person))


def is_suspect(per_person: Decimal, median: Decimal | None) -> bool:
    """A price far from the route's recent median is flagged, not hidden."""
    return median is not None and not (median * SUSPECT_LOW <= per_person <= median * SUSPECT_HIGH)
