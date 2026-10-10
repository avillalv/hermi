# ruff: noqa: E501  (long SQL strings)
"""One trip fare as the API shows it: the shared SELECT over `trip_fare_links` and its observation, and the row to `Fare` mapping."""

from datetime import UTC, datetime
from urllib.parse import quote

from hermi.modules.flights.schemas import Fare, Money

FARE_COLUMNS = (
    "l.id, l.route_id, l.hidden, l.suspect, o.source, o.confidence::text AS confidence, o.origin, o.destination, o.depart_date, "
    "o.return_date, o.price_total_minor, o.currency, o.adults, o.children, o.airlines, o.stops_out, o.stops_back, "
    "o.duration_out_min, o.duration_back_min, o.depart_at_local, o.flight_numbers, o.source_url, o.source_domain, o.run_id, o.observed_at, o.cabin::text AS cabin, o.expires_at"
)
FARE_FROM = "trip_fare_links l JOIN fare_observations o ON o.id = l.observation_id"


def age_label(observed_at: datetime, confidence: str, now: datetime | None = None) -> str:
    """'cached 6 h ago': every fare shows how old it is (05 section 6)."""
    seconds = max(0, int(((now or datetime.now(UTC)) - observed_at).total_seconds()))
    age = "just now" if seconds < 60 else f"{seconds // 60} min ago" if seconds < 3600 else f"{seconds // 3600} h ago" if seconds < 172800 else f"{seconds // 86400} d ago"
    return f"{confidence} {age}"


def search_url(origin: str, destination: str, depart, back) -> str:
    """A plain Google Flights search for the same airports and dates: no partner, no marker, never a rental site. The server does not fetch it; the traveler opens it."""
    q = f"Flights from {origin} to {destination} on {depart.isoformat()}" + (f" through {back.isoformat()}" if back else "")
    return f"https://www.google.com/travel/flights?q={quote(q)}"


def fare_of(r) -> Fare:
    return Fare(
        id=r["id"], route_id=r["route_id"], source=r["source"], confidence=r["confidence"], origin=r["origin"], destination=r["destination"],
        depart_date=r["depart_date"], return_date=r["return_date"], price=Money(amount_minor=r["price_total_minor"], currency=r["currency"]),
        passengers=r["adults"] + r["children"], airlines=r["airlines"], stops_out=r["stops_out"], stops_back=r["stops_back"],
        duration_out_min=r["duration_out_min"], duration_back_min=r["duration_back_min"], depart_at_local=r["depart_at_local"],
        flight_numbers=r["flight_numbers"], airline_search_url=search_url(r["origin"], r["destination"], r["depart_date"], r["return_date"]), source_url=r["source_url"], source_domain=r["source_domain"], run_id=r["run_id"], observed_at=r["observed_at"],
        age_label=age_label(r["observed_at"], r["confidence"]), suspect=r["suspect"], hidden=r["hidden"],
    )
