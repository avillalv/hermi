# ruff: noqa: E501  (long SQL strings)
"""Evidence rules for AI output, ported from Trip Planner `services/agent_ingest.py`.

Two layers. The pure checks (`source_problem`, `price_in_bounds`, `observed_during_run`) are rules on one value. The DB-backed
`submit_quotes` and `add_note` (06 section 2.5) run every item through all of them and write account scoped rows: the user,
trip and run come from the `RunBinding` (the runs row), never from tool input, and the only id the model supplies is a route
reference that is looked up in the run's own map. Fares and notes must have been seen on a page during the run (non-negotiable
rule 4): the cited URL has to be in the run's evidence, and a fetched page has to contain the price.
"""

import hashlib
import ipaddress
import json
import re
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Protocol
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.modules.ai.policy import blocked_domain
from hermi.modules.flights.fares import CACHE_TTL, search_key

# Hard bounds on the per-person price, in USD.
MIN_PER_PERSON_USD = Decimal(30)
MAX_PER_PERSON_USD = Decimal(15_000)
# Prices must have been seen during the run (with some slack for clock differences).
OBSERVED_SLACK = timedelta(minutes=10)

PRIVATE_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home.arpa")

__all__ = [
    "IngestResult",
    "RunBinding",
    "add_note",
    "blocked_domain",
    "observed_during_run",
    "price_grounded",
    "price_in_bounds",
    "source_problem",
    "submit_quotes",
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


# --- evidence and grounding ---------------------------------------------------------------------------------------


class EvidenceLike(Protocol):
    """What the run has really shown (the worker's `Evidence`): URLs search returned, and fetched pages with their text."""

    found: set[str]
    fetched: dict[str, str]
    unchecked: set[
        str
    ]  # fetched in a claude_cli run: seen, but no document text to ground a price on


@dataclass(frozen=True)
class RunBinding:
    """Who and what a run writes for. Built from the `runs` row by the job, never from tool input."""

    run_id: uuid.UUID
    user_id: uuid.UUID | None
    trip_id: uuid.UUID


@dataclass
class IngestResult:
    items: list[dict[str, Any]] = field(
        default_factory=list
    )  # one per input item: index, status, errors, flags
    accepted: int = 0
    rejected: int = 0  # duplicates count in neither

    def payload(self) -> dict[str, Any]:
        return {"results": self.items, "accepted": self.accepted, "rejected": self.rejected}


Emit = Callable[
    ..., None
]  # emit(type, summary, payload=None, tool_name=None): the job's run_events writer


def normalize_url(url: str) -> str:
    """Scheme and host lowercased, fragment dropped, one trailing slash dropped: the form evidence is matched on."""
    try:
        p = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    if not p.scheme:
        return url.strip()
    path = p.path[:-1] if p.path.endswith("/") and len(p.path) > 1 else p.path
    return f"{p.scheme.lower()}://{p.netloc.lower()}{path}" + (f"?{p.query}" if p.query else "")


def _host(url: str) -> str:
    try:
        h = (urlsplit(url if "//" in url else f"//{url}").hostname or "").lower()
    except ValueError:
        return ""
    return h.removeprefix("www.")


_NUMBER = re.compile(r"\d[\d.,  ']*\d|\d")
_THOUSANDS_SPACE = re.compile(r"(?<=\d) (?=\d{3}(?!\d))")


def _candidates(token: str) -> set[Decimal]:
    """The values a printed number can mean. A lone separator followed by three digits is read both ways."""
    t = re.sub(r"[  ']", "", token)
    marks = [c for c in t if c in ".,"]
    try:
        if not marks:
            return {Decimal(t)}
        if "." in marks and "," in marks:  # the last mark is the decimal point
            cut = max(t.rfind("."), t.rfind(","))
            return {Decimal(re.sub(r"[.,]", "", t[:cut]) + "." + t[cut + 1 :])}
        if len(marks) > 1:  # 1.412.000: digit groups
            return {Decimal(re.sub(r"[.,]", "", t))}
        cut = t.rfind(marks[0])
        head, tail = t[:cut], t[cut + 1 :]
        if len(tail) == 3:
            return {Decimal(head + tail), Decimal(f"{head}.{tail}")}
        return {Decimal(f"{head}.{tail}")}
    except InvalidOperation:
        return set()


def price_grounded(page_text: str, price: Decimal) -> bool:
    """Whether `price` is printed on the page in a common separator style (412, $412, 412.00, 1.412,00, 1,412.00, 1 412)."""
    for body in (page_text, _THOUSANDS_SPACE.sub("", page_text)):
        for m in _NUMBER.finditer(body):
            if price in _candidates(m.group()):
                return True
    return False


# --- shared helpers -----------------------------------------------------------------------------------------------

_RUN = text(
    "SELECT status::text AS status, params FROM runs WHERE id = :r AND trip_id = :t AND user_id IS NOT DISTINCT FROM :u"
)
_PER_EUR = text("SELECT per_eur FROM fx_rates WHERE currency = :c")
_ROUTE = text(
    """SELECT id, trip_type::text AS trip_type, origin_codes::text[] AS origins, destination_codes::text[] AS dests, depart_from, depart_to,
              return_from, return_to, min_nights, max_nights, adults, children, cabin::text AS cabin, max_stops
         FROM flight_routes WHERE id = :id AND trip_id = :t AND active"""
)
_HOME = text("SELECT home_currency::text FROM trips WHERE id = :t")
_NOT_ACTIVE = "This run is not active, so nothing can be saved."


def _active_run(session: Session, bind: RunBinding) -> dict[str, str] | None:
    """The run's route map when the runs row matches the binding and is still running, else None."""
    row = session.execute(
        _RUN, {"r": bind.run_id, "t": bind.trip_id, "u": bind.user_id}
    ).one_or_none()
    if row is None or row.status != "running":
        return None
    params = row.params if isinstance(row.params, dict) else json.loads(row.params or "{}")
    m = params.get("route_map")
    return {str(k): str(v) for k, v in m.items()} if isinstance(m, dict) else {}


def _reject(
    i: int,
    result: IngestResult,
    errors: list[str],
    item: dict[str, Any],
    tool: str,
    emit: Emit | None,
    keys: Iterable[str],
) -> None:
    result.items.append({"index": i, "status": "rejected", "errors": errors, "flags": []})
    result.rejected += 1
    if emit:
        shown = {
            k: str(item.get(k))[:200] for k in keys if k in item
        }  # a few named fields, never the whole item
        payload = {
            "kind": "ingest_rejection",
            "tool": tool,
            "index": i,
            "errors": errors,
            "item": shown,
        }
        emit("rejection", f"{tool} item {i + 1} rejected: {errors[0]}"[:300], payload, tool)


def _per_eur(session: Session, currency: str) -> Decimal | None:
    if currency == "EUR":
        return Decimal(1)
    return session.execute(_PER_EUR, {"c": currency}).scalar_one_or_none()


def _date(v: Any) -> date | None:
    try:
        return date.fromisoformat(str(v))
    except ValueError:
        return None


_PRICE = re.compile(r"^\d{1,9}(\.\d{1,3})?$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


# --- fares --------------------------------------------------------------------------------------------------------

_QUOTE_FIELDS = (
    "route_ref",
    "origin",
    "destination",
    "depart_date",
    "price_total",
    "currency",
    "source_url",
)


def submit_quotes(
    session: Session,
    bind: RunBinding,
    quotes: list[dict[str, Any]],
    evidence: EvidenceLike,
    *,
    emit: Emit | None = None,
    now: datetime | None = None,
) -> IngestResult:
    """Validate each quote on its own (06 section 2.5 validators 1 to 7) and save the good ones as `fare_observations`
    linked to the run's trip. Every saved row has source 'agent', confidence 'indicative', the source URL and the run id.
    The caller commits."""
    now = now or datetime.now(UTC)
    out = IngestResult()
    route_map = _active_run(session, bind)
    if route_map is None:
        for i, q in enumerate(quotes):
            _reject(i, out, [_NOT_ACTIVE], q, "submit_flight_quotes", emit, ())
        return out
    found = {normalize_url(u) for u in evidence.found}
    fetched = {normalize_url(u): t for u, t in evidence.fetched.items()}
    unchecked = {normalize_url(u) for u in evidence.unchecked} - fetched.keys()
    home = session.execute(_HOME, {"t": bind.trip_id}).scalar_one()
    for i, q in enumerate(quotes):
        try:
            with session.begin_nested():
                item = _one_quote(
                    session, bind, q, i, route_map, found, fetched, unchecked, home, now
                )
        except (
            Exception
        ):  # one bad item must not lose the batch; no text kept, the item may carry page text
            item = {"index": i, "status": "rejected", "errors": ["could not be saved"], "flags": []}
        if item["status"] == "rejected":
            _reject(i, out, item["errors"], q, "submit_flight_quotes", emit, _QUOTE_FIELDS)
            continue
        out.items.append(item)
        out.accepted += item["status"] == "accepted"
    return out


def _one_quote(
    session: Session,
    bind: RunBinding,
    q: dict[str, Any],
    i: int,
    route_map: dict[str, str],
    found: set[str],
    fetched: dict[str, str],
    unchecked: set[str],
    home: str,
    now: datetime,
) -> dict[str, Any]:
    errors: list[str] = []
    flags: list[str] = []

    def rejected(first: str | None = None) -> dict[str, Any]:
        return {
            "index": i,
            "status": "rejected",
            "errors": [first] if first else errors,
            "flags": flags,
        }

    # 1. route match: the reference is looked up in this run's map, then the row must belong to the run's trip
    rid = route_map.get(str(q.get("route_ref", "")).strip())
    route = (
        session.execute(_ROUTE, {"id": rid, "t": bind.trip_id}).mappings().one_or_none()
        if rid
        else None
    )
    if route is None:
        return rejected("route_ref isn't one of this trip's routes; use an id from get_task")
    origin, dest = (
        str(q.get("origin", "")).strip().upper(),
        str(q.get("destination", "")).strip().upper(),
    )
    if origin not in route["origins"]:
        errors.append(
            f"origin {origin} is not one of the route's origins ({', '.join(route['origins'])})"
        )
    if dest not in route["dests"]:
        errors.append(
            f"destination {dest} is not one of the route's destinations ({', '.join(route['dests'])})"
        )

    # 2. date window
    dep = _date(q.get("depart_date"))
    ret = _date(q["return_date"]) if q.get("return_date") else None
    if dep is None:
        errors.append("depart_date must be a date such as 2027-04-09")
    elif dep < now.date():
        errors.append("departure is in the past")
    elif not route["depart_from"] <= dep <= route["depart_to"]:
        errors.append(
            f"departure {dep} is outside the route's window {route['depart_from']} to {route['depart_to']}"
        )
    elif route["trip_type"] == "one_way":
        if ret is not None:
            errors.append("a one way route takes no return date")
    elif ret is None:
        errors.append("a round trip needs a return date")
    elif ret < dep:
        errors.append("return is before departure")
    elif route["min_nights"] is not None:
        if not route["min_nights"] <= (ret - dep).days <= route["max_nights"]:
            errors.append(f"nights must be {route['min_nights']} to {route['max_nights']}")
    elif not route["return_from"] <= ret <= route["return_to"]:
        errors.append(
            f"return is outside the route's return window {route['return_from']} to {route['return_to']}"
        )

    # 3. passengers
    party = route["adults"] + route["children"]
    passengers = q.get("passengers")
    if passengers not in (party, 1):
        errors.append(f"passengers must be {party} (the party) or 1 (a per person price)")

    # 4. price and currency
    price_text = str(q.get("price_total", "")).strip()
    currency = str(q.get("currency", "")).strip().upper()
    price = Decimal(price_text) if _PRICE.match(price_text) else None
    if price is None or price <= 0:
        errors.append("price_total must be digits and a decimal point only, for example 412.00")
        price = None
    rate: Decimal | None = None
    if not _CURRENCY.match(currency):
        errors.append("currency must be a three letter ISO 4217 code")
    else:
        eur_cur, eur_usd, eur_home = (
            _per_eur(session, currency),
            _per_eur(session, "USD"),
            _per_eur(session, home),
        )
        if eur_cur is None or eur_usd is None or eur_home is None:
            errors.append(f"currency {currency} can't be converted yet")
        else:
            rate = eur_cur / eur_usd  # units of the price currency per USD
    total = price
    if price is not None and passengers == 1 and party > 1:
        total = price * party
        flags.append("per_person_price_scaled")
    if total is not None and rate is not None and not price_in_bounds(total, party, rate):
        errors.append("price is not believable for a flight (outside $30 to $15,000 per person)")

    # 5. source, 6. provenance, 7. grounding
    url = str(q.get("source_url", "")).strip()
    key = normalize_url(url)
    if problem := source_problem(url):
        errors.append(f"source_url {problem}")
    elif key not in found and key not in fetched and key not in unchecked:
        errors.append("source_url cited a page you did not open in this run")
    elif key in unchecked:
        flags.append(
            "page_text_unavailable"
        )  # the claude_cli stream carries no document text (Evidence.unchecked)
    else:
        page = fetched.get(key)
        if page is None:
            flags.append(
                "search_snippet_only"
            )  # snippets are encrypted and can't be checked: indicative
        elif price is not None and not price_grounded(page, price):
            errors.append("the price is not on the page you fetched")
    if errors:
        return rejected()

    assert dep is not None and total is not None and price is not None
    exponent = session.execute(text("SELECT currency_exponent(:c)"), {"c": currency}).scalar_one()
    minor = int((total * (Decimal(10) ** exponent)).to_integral_value(ROUND_HALF_UP))
    if minor <= 0:
        return rejected("price rounds to nothing in this currency")
    k = search_key(origin, dest, dep, ret, dict(route))
    if session.execute(
        text(
            "SELECT 1 FROM fare_observations WHERE run_id = :r AND search_key = :k AND price_total_minor = :m AND currency = :c AND source_url = :u LIMIT 1"
        ),
        {"r": bind.run_id, "k": k, "m": minor, "c": currency, "u": url},
    ).first():
        return {"index": i, "status": "duplicate", "errors": [], "flags": flags}
    raw: dict[str, Any] = {"agent": True, "flags": flags}
    if page_text := fetched.get(key):  # kept for disputes
        raw |= {
            "document_url": url,
            "document_sha256": hashlib.sha256(page_text.encode()).hexdigest(),
        }
    if q.get("notes"):
        raw["notes"] = str(q["notes"])[:300]
    obs = session.execute(
        text(
            """INSERT INTO fare_observations (search_key, origin, destination, depart_date, return_date, cabin, adults, children, stops_max, source, confidence,
                 currency, price_total_minor, airlines, stops_out, stops_back, duration_out_min, source_url, source_domain, run_id, observed_at, expires_at, raw)
               VALUES (:k, :o, :d, :dep, :ret, CAST(:cabin AS cabin_class), :adults, :children, :stops, 'agent', 'indicative', :cur, :minor, :airlines,
                 :so, :sb, :dur, :url, :domain, :run, :seen, :exp, CAST(:raw AS jsonb))
               ON CONFLICT (search_key, source, observed_at) DO NOTHING RETURNING id"""
        ),
        {
            "k": k, "o": origin, "d": dest, "dep": dep, "ret": ret, "cabin": route["cabin"], "adults": route["adults"], "children": route["children"],
            "stops": route["max_stops"], "cur": currency, "minor": minor, "airlines": [str(a)[:60] for a in (q.get("airlines") or [])][:6],
            "so": q.get("stops_outbound"), "sb": q.get("stops_return"), "dur": q.get("duration_outbound_min"), "url": url,
            "domain": str(q.get("seen_on") or "").strip()[:80] or _host(url), "run": bind.run_id,
            "seen": now + timedelta(microseconds=i), "exp": now + CACHE_TTL, "raw": json.dumps(raw),
        },
    ).scalar_one_or_none()  # fmt: skip
    if obs is None:
        return {"index": i, "status": "duplicate", "errors": [], "flags": flags}
    session.execute(
        text(
            "INSERT INTO trip_fare_links (trip_id, route_id, observation_id) VALUES (:t, :r, :o) ON CONFLICT DO NOTHING"
        ),
        {"t": bind.trip_id, "r": route["id"], "o": obs},
    )
    return {"index": i, "status": "accepted", "errors": [], "flags": flags}


# --- notes --------------------------------------------------------------------------------------------------------

# Anything that looks like a link or a bare domain: scheme URLs, then host names with a letters-only ending.
_URL_LIKE = re.compile(
    r"""(?i)https?://[^\s<>"')\]]+|(?<![@\w.-])(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d+)?(?:/[^\s<>"')\]]*)?"""
)
_AFFILIATE_HOSTS = text("SELECT DISTINCT lower(h) FROM affiliate_programs, unnest(hosts) AS h")


def add_note(
    session: Session,
    bind: RunBinding,
    note: dict[str, Any],
    evidence: EvidenceLike,
    *,
    emit: Emit | None = None,
) -> IngestResult:
    """Validate one note (06 section 2.5 executor checks, 4.3 item 8) and save it as an agent note on the run's trip with
    its source links. The caller commits."""
    out = IngestResult()
    keys = ("title", "topic", "urls")
    if _active_run(session, bind) is None:
        _reject(0, out, [_NOT_ACTIVE], note, "add_note", emit, keys)
        return out
    errors: list[str] = []
    urls = [u.strip() for u in note.get("urls") or [] if isinstance(u, str) and u.strip()]
    title = _CONTROL.sub("", str(note.get("title", ""))).strip()
    body = _CONTROL.sub("", str(note.get("body", ""))).strip()
    if not urls:
        errors.append("a note needs at least one source link")
    seen = {normalize_url(u) for u in (*evidence.found, *evidence.fetched, *evidence.unchecked)}
    partners = {h.removeprefix("www.") for (h,) in session.execute(_AFFILIATE_HOSTS) if h}
    for u in urls:
        host = _host(u)
        if problem := source_problem(u):
            errors.append(f"link {problem}")
        elif "/go/" in urlsplit(u).path or any(
            host == h or host.endswith("." + h) for h in partners
        ):
            errors.append("a partner or tracking link can't be a source")
        elif normalize_url(u) not in seen:
            errors.append("a source link cites a page you did not open in this run")
    allowed_hosts, allowed_urls = {_host(u) for u in urls}, {normalize_url(u) for u in urls}
    for part in (title, body):
        if "/go/" in part:
            errors.append("text contains a partner link")
        for m in _URL_LIKE.finditer(part):
            s = m.group().rstrip(".,;:!?")
            bare = (
                "://" not in s and "/" not in s
            )  # a source's host may be named, as a bare domain with no path
            if normalize_url(s) not in allowed_urls and not (bare and _host(s) in allowed_hosts):
                errors.append("text contains a link that is not in urls; put sources in urls only")
                break
    if not title or not body:
        errors.append("a note needs a title and a body")
    if errors := list(dict.fromkeys(errors)):
        _reject(0, out, errors, note, "add_note", emit, keys)
        return out
    dup = session.execute(
        text(
            "SELECT 1 FROM notes WHERE run_id = :r AND trip_id = :t AND title = :ti AND body = :b LIMIT 1"
        ),
        {"r": bind.run_id, "t": bind.trip_id, "ti": title[:160], "b": body},
    ).first()
    if dup:
        out.items.append({"index": 0, "status": "duplicate", "errors": [], "flags": []})
        return out
    session.execute(
        text(
            """INSERT INTO notes (trip_id, kind, author_user_id, title, topic, body, urls, run_id, is_private)
               VALUES (:t, 'agent', NULL, :ti, :tp, :b, :u, :r, false)"""
        ),
        {
            "t": bind.trip_id,
            "ti": title[:160],
            "tp": str(note.get("topic", "other"))[:80],
            "b": body,
            "u": urls,
            "r": bind.run_id,
        },
    )
    out.items.append({"index": 0, "status": "accepted", "errors": [], "flags": []})
    out.accepted = 1
    return out
