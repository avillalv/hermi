# ruff: noqa: E501  (long comments and SQL)
"""Lodging helpers (04 section 5.9). Everything here works on URL text and rows. Nothing opens a connection to a listing site.

A pasted link is stored exactly as typed. `site` and `url_normalized` are derived copies for display and duplicate detection.
"""

import re
import uuid
from datetime import date
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.errors import ApiError
from hermi.modules.ai.policy import blocked_domain
from hermi.modules.billing import service as billing
from hermi.security.ssrf import LINK_PREVIEW_POLICY, SsrfGuard, SsrfRefused

# Expedia Group brands: link only, like the three in BLOCKED_HOSTS (04 section 5.9). Labels of the registrable domain, or exact parent domains.
_EXPEDIA_LABELS = ("expedia", "orbitz", "travelocity", "hotwire", "cheaptickets", "ebookers", "wotif")
_EXPEDIA_DOMAINS = ("hotels.com",)

NOTE = "We never change your links."
_REFUSED = {
    "bad_scheme": "Use a link that starts with http or https.",
    "credentials_in_url": "Remove the name and password from that link.",
    "bad_port": "That link uses a port we do not accept.",
    "ip_literal": "Use the website name, not an IP address.",
    "own_host": "That link points at Hermi itself.",
    "url_too_long": "That link is too long.",
}


class _NoTransport:
    def open(self, request):  # the guard is only asked to validate, never to fetch
        raise AssertionError("lodging never fetches a URL")


def _guard() -> SsrfGuard:
    # shortcut: validate() resolves the host through the resolver, so a fixed public answer stands in and no DNS lookup happens.
    # A name that points at a private address is stored and never fetched. Upgrade: resolve for real if the server ever fetches a stay link.
    return SsrfGuard(LINK_PREVIEW_POLICY, _NoTransport(), resolver=lambda host, port: ["93.184.216.34"], own_hosts=frozenset())


def url_problem(url: str) -> str | None:
    """Why a pasted link is refused (the hostile table of 10 section 2.5), or None. Airbnb, Vrbo and Booking.com links are fine: they are stored, not fetched."""
    try:
        _guard().validate(url)
    except SsrfRefused as e:
        if e.reason == "blocked_domain":
            return None
        return _REFUSED.get(e.reason, "That does not look like a web link.")
    return None


def host_of(url: str) -> str | None:
    try:
        host = (urlsplit(url.strip()).hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    return host or None


def site_of(url: str | None) -> str | None:
    host = host_of(url) if url else None
    return host.removeprefix("www.") if host else None


def normalized(url: str | None) -> str | None:
    """Query string and fragment stripped, host lowercased, for duplicate detection only."""
    if not url:
        return None
    p = urlsplit(url.strip())
    host = (p.hostname or "").lower()
    return f"{p.scheme.lower()}://{host}{p.path.rstrip('/')}" if host else None


def link_only_brand(host: str | None) -> str | None:
    """The brand of a host we never fetch: the three BLOCKED_HOSTS and the Expedia Group brands."""
    if not host:
        return None
    if brand := blocked_domain(host):
        return brand
    labels = host.lower().rstrip(".").split(".")
    for b in _EXPEDIA_LABELS:
        if b in labels[:-1]:
            return b
    return "hotels.com" if ".".join(labels[-2:]) in _EXPEDIA_DOMAINS else None


_IN = ("check_in", "checkin", "chkin", "startdate", "start_date", "arrival", "checkindate")
_OUT = ("check_out", "checkout", "chkout", "enddate", "end_date", "departure", "checkoutdate")
_GUESTS = ("guests", "adults", "numberofadults", "group_adults", "numadults", "travelers", "numberofguests")
_ID_AFTER = {"rooms", "h", "listing", "listings", "rental", "rentals", "homes"}


def _first(q: dict[str, list[str]], keys: tuple[str, ...]) -> str | None:
    return next((q[k][0] for k in keys if q.get(k)), None)


def _date(raw: str | None) -> date | None:
    try:
        return date.fromisoformat(raw[:10]) if raw else None
    except ValueError:
        return None


def _listing_id(path: str) -> str | None:
    segs = [s for s in path.split("/") if s]
    for i, s in enumerate(segs):
        if s.lower() in _ID_AFTER and i + 1 < len(segs):
            return segs[i + 1]
        if s.lower() == "hotel" and i + 2 < len(segs):  # booking.com/hotel/pt/some-name.en-gb.html
            return re.sub(r"(\.[a-z]{2}(-[a-z]{2})?)?\.html?$", "", segs[i + 2], flags=re.I)
        if s.isdigit() and len(s) >= 5:
            return s
    return None


def parse_link(url: str) -> dict:
    """Host, stay dates, guests and listing id from the URL text alone. shortcut: ISO dates and a few well known parameter names;
    a site that splits a date over year, month and day parameters gives no date. Upgrade: add keys as real links show up."""
    p = urlsplit(url.strip())
    q = {k.lower(): v for k, v in parse_qs(p.query).items()}
    guests = _first(q, _GUESTS)
    listing = _listing_id(p.path)
    return {
        "url": url,
        "site": site_of(url),
        "check_in": _date(_first(q, _IN)),
        "check_out": _date(_first(q, _OUT)),
        "guests": int(guests) if guests and guests.isdigit() and 1 <= int(guests) <= 100 else None,
        "listing_id": listing[:200] if listing else None,
    }


def require_slot(session: Session, trip_id: uuid.UUID) -> None:
    """402 `limit_reached` (trigger `ninth_stay`) when the trip already holds `saved_lodging_per_trip` stays."""
    limit = billing.limit_of(billing.trip_limits(session, trip_id)[1], "saved_lodging_per_trip")
    if session.execute(text("SELECT count(*) FROM lodging_options WHERE trip_id = :t"), {"t": trip_id}).scalar_one() < limit:
        return
    best = session.execute(text("SELECT max((limits->>'saved_lodging_per_trip')::int) FROM plans WHERE limits ? 'saved_lodging_per_trip'")).scalar() or 0
    top = limit >= best  # the highest tier's limit (fair use): nothing to sell. A Free owner or a Trip Pass (30) still gets the upsell.
    msg = f"A trip can hold {limit} saved stays on your plan. Remove one to make room" + ("." if top else ", or upgrade.")
    err = billing.paywall_error("saved_lodging_per_trip", limit, msg, upsell=not top)
    if not top:
        err.extra["paywall"]["free_path"] = "Remove a stay to make room"  # the Later list is a client feature (WF-034.3); the API only offers this
    raise err


def require_compare(session: Session, trip_id: uuid.UUID, count: int) -> None:
    """402 `limit_reached` when `count` stays exceed `lodging_compare` on the trip's merged limits (no paywall reason exists for it, so no hint)."""
    limit = billing.limit_of(billing.trip_limits(session, trip_id)[1], "lodging_compare")
    if count > limit:
        raise ApiError(402, "limit_reached", f"You can compare {limit} stays at once on your plan.")
