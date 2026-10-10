# ruff: noqa: E501  (SQL strings)
"""`hermi seed --demo` (WF-133.1): the demo trip for the Plus persona and the published sample trips.

Rows go in by SQL on the worker login (BYPASSRLS), so later tickets only add models. The personas are not created here:
`auth.service.dev_session` is the one persona path (WF-013), and this seed calls it. Safe to re-run: every block looks
for what it would add first, so a second run changes nothing.
"""

import hashlib
import uuid
from datetime import date, timedelta

from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from hermi import db
from hermi.config import LOCAL_ENVIRONMENTS, Settings
from hermi.modules.auth import service as auth_service
from hermi.modules.credits import service as credits

CONTENT_EMAIL = "content@hermi.test"
DEMO_TRIP = "Lisbon in March"
LISBON = dict(
    name="Lisbon",
    region="Lisbon",
    country="Portugal",
    country_code="PT",
    kind="city",
    lat=38.7223,
    lon=-9.1393,
    timezone="Europe/Lisbon",
)

# Each sample: destination, saved places (name, category, lat, lon), and days of (title, [(item, category, start time, place index or None)]).
SAMPLES = [
    dict(
        slug="lisbon-food-weekend",
        title="Lisbon food weekend",
        summary="Three slow days of pastries, tascas and viewpoints.",
        tags=["city", "food"],
        suits="Couples and friends who plan around meals",
        dest=LISBON,
        places=[
            ("Pasteis de Belem", "food", 38.6975, -9.2032),
            ("Time Out Market", "food", 38.7067, -9.1458),
            ("Miradouro da Senhora do Monte", "sights", 38.7189, -9.1326),
        ],
        days=[
            (
                "Belem and pastries",
                [
                    ("Custard tarts at Belem", "food", "09:30", 0),
                    ("Jeronimos Monastery", "sights", "11:00", None),
                ],
            ),
            (
                "Markets and fado",
                [
                    ("Lunch at the market", "food", "13:00", 1),
                    ("Fado in Alfama", "nightlife", "21:00", None),
                ],
            ),
            (
                "Viewpoints",
                [
                    ("Sunset at the miradouro", "sights", "18:30", 2),
                    ("Seafood dinner", "food", "20:30", None),
                ],
            ),
        ],
    ),
    dict(
        slug="algarve-beach-week",
        title="Algarve beach week",
        summary="Cliffs, coves and long lunches on Portugal's south coast.",
        tags=["beach"],
        suits="Families and anyone who wants sun with little driving",
        dest=dict(
            name="Lagos",
            region="Algarve",
            country="Portugal",
            country_code="PT",
            kind="city",
            lat=37.1028,
            lon=-8.6730,
            timezone="Europe/Lisbon",
        ),
        places=[
            ("Praia Dona Ana", "nature", 37.0916, -8.6736),
            ("Ponta da Piedade", "nature", 37.0836, -8.6703),
            ("Old town Lagos", "sights", 37.1019, -8.6742),
        ],
        days=[
            (
                "Arrive and swim",
                [
                    ("Beach at Praia Dona Ana", "nature", "11:00", 0),
                    ("Dinner in the old town", "food", "20:00", 2),
                ],
            ),
            (
                "Cliffs by boat",
                [
                    ("Boat trip to Ponta da Piedade", "nature", "10:00", 1),
                    ("Free afternoon", "other", "15:00", None),
                ],
            ),
            (
                "Slow last day",
                [("Market and coffee", "food", "10:00", None), ("Last swim", "nature", "12:30", 0)],
            ),
        ],
    ),
    dict(
        slug="dolomites-hiking-long-weekend",
        title="Dolomites hiking long weekend",
        summary="Three hut-to-viewpoint walks around Cortina d'Ampezzo.",
        tags=["mountains"],
        suits="Active travelers with a car and good boots",
        dest=dict(
            name="Cortina d'Ampezzo",
            region="Veneto",
            country="Italy",
            country_code="IT",
            kind="city",
            lat=46.5405,
            lon=12.1357,
            timezone="Europe/Rome",
        ),
        places=[
            ("Tre Cime di Lavaredo", "nature", 46.6186, 12.3025),
            ("Lago di Braies", "nature", 46.6942, 12.0850),
            ("Rifugio Lagazuoi", "food", 46.5189, 12.0075),
        ],
        days=[
            (
                "Tre Cime loop",
                [("Tre Cime circuit", "nature", "08:30", 0), ("Hut lunch", "food", "13:00", None)],
            ),
            (
                "Lake day",
                [
                    ("Lago di Braies at sunrise", "nature", "07:00", 1),
                    ("Drive to Cortina", "travel", "11:00", None),
                ],
            ),
            (
                "Cable car and ridge",
                [
                    ("Lagazuoi cable car", "nature", "09:30", 2),
                    ("Walk down the tunnels", "sights", "11:30", None),
                ],
            ),
        ],
    ),
]

DEMO_PLAN = dict(
    dest=LISBON,
    places=[("Time Out Market", "food", 38.7067, -9.1458), ("Alfama", "sights", 38.7110, -9.1300)],
    days=[
        (
            "Arrive and Baixa",
            [
                ("Check in and walk Baixa", "sights", "15:00", None),
                ("Dinner at a tasca", "food", "20:00", None),
            ],
        ),
        (
            "Belem",
            [
                ("Jeronimos Monastery", "museum", "10:00", None),
                ("Custard tarts", "food", "12:30", None),
            ],
        ),
        (
            "Alfama and fado",
            [
                ("Alfama viewpoints", "sights", "11:00", 1),
                ("Fado night", "nightlife", "21:00", None),
            ],
        ),
        (
            "Sintra day trip",
            [
                ("Pena Palace", "sights", "10:00", None),
                ("Train back to Lisbon", "travel", "17:00", None),
            ],
        ),
    ],
)


def _base_start(today: date) -> date:
    """The first Monday of the next March (this year's if it has not started)."""
    year = today.year if today < date(today.year, 3, 1) else today.year + 1
    d = date(year, 3, 1)
    return d + timedelta(days=(7 - d.weekday()) % 7)


def _one(conn: Connection, sql: str, **params):
    return conn.execute(text(sql), params).scalar()


def _user_id(conn: Connection, email: str):
    return _one(conn, "SELECT id FROM users WHERE email = :e AND deleted_at IS NULL", e=email)


def _content_user(conn: Connection) -> uuid.UUID:
    """The staff account that owns sample trips. It has no sign-in identity, so nobody can open it."""
    uid = _user_id(conn, CONTENT_EMAIL)
    if uid:
        return uid
    uid = _one(
        conn,
        "INSERT INTO users (email, display_name, email_verified_at) VALUES (:e, 'Hermi content', now()) RETURNING id",
        e=CONTENT_EMAIL,
    )
    conn.execute(
        text(
            "INSERT INTO people (owner_user_id, linked_user_id, name, is_self) VALUES (:u, :u, 'Hermi content', true)"
        ),
        {"u": uid},
    )
    conn.execute(text("INSERT INTO entitlements (user_id) VALUES (:u)"), {"u": uid})
    return uid


def _trip_with_plan(
    conn: Connection, owner, *, name: str, start: date, end: date, spec: dict, notes: str = ""
) -> uuid.UUID:
    """An ordinary trip with one destination, itinerary days and items, and saved places."""
    trip = _one(
        conn,
        "INSERT INTO trips (owner_user_id, name, start_date, end_date, home_currency, notes) VALUES (:o, :n, :s, :e, 'USD', :notes) RETURNING id",
        o=owner,
        n=name,
        s=start,
        e=end,
        notes=notes,
    )
    dest_id = _one(
        conn,
        "INSERT INTO trip_destinations (trip_id, position, name, region, country, country_code, kind, lat, lon, timezone, info_status) "
        "VALUES (:t, 0, :name, :region, :country, :country_code, :kind, :lat, :lon, :timezone, 'skipped') RETURNING id",
        t=trip,
        **spec["dest"],
    )
    places = [
        _one(
            conn,
            "INSERT INTO saved_places (trip_id, place_provider, place_id, name, category, lat, lon, saved_by) "
            "VALUES (:t, 'manual', :pid, :n, CAST(:c AS item_category), :lat, :lon, :u) RETURNING id",
            t=trip,
            pid=f"seed-{i}",
            n=pname,
            c=cat,
            lat=lat,
            lon=lon,
            u=owner,
        )
        for i, (pname, cat, lat, lon) in enumerate(spec["places"])
    ]
    for d, (title, items) in enumerate(spec["days"]):
        day = start + timedelta(days=d)
        conn.execute(
            text(
                "INSERT INTO itinerary_days (trip_id, day, title, destination_id, updated_by) VALUES (:t, :d, :title, :dest, :u)"
            ),
            {"t": trip, "d": day, "title": title, "dest": dest_id, "u": owner},
        )
        for j, (ititle, cat, hhmm, place) in enumerate(items):
            conn.execute(
                text(
                    "INSERT INTO itinerary_items (trip_id, day, start_time, sort_order, title, category, status, saved_place_id, source, created_by, updated_by) "
                    "VALUES (:t, :d, CAST(:h AS time), :so, :title, CAST(:c AS item_category), 'planned', :sp, 'manual', :u, :u)"
                ),
                {
                    "t": trip,
                    "d": day,
                    "h": hhmm,
                    "so": j,
                    "title": ititle,
                    "c": cat,
                    "sp": places[place] if place is not None else None,
                    "u": owner,
                },
            )
    return trip


def _sample_trips(conn: Connection, start: date) -> int:
    content = _content_user(conn)
    made = 0
    for order, s in enumerate(SAMPLES):
        if _one(conn, "SELECT 1 FROM sample_trips WHERE slug = :s", s=s["slug"]):
            continue
        end = start + timedelta(days=len(s["days"]) - 1)
        trip = _trip_with_plan(
            conn, content, name=s["title"], start=start, end=end, spec=s, notes=s["summary"]
        )
        conn.execute(
            text(
                "INSERT INTO sample_trips (slug, trip_id, title, summary, country_code, tags, suits, status, sort_order, published_at, created_by) "
                "VALUES (:slug, :trip, :title, :summary, :cc, :tags, :suits, 'published', :so, now(), :u)"
            ),
            {
                "slug": s["slug"],
                "trip": trip,
                "title": s["title"],
                "summary": s["summary"],
                "cc": s["dest"]["country_code"],
                "tags": s["tags"],
                "suits": s["suits"],
                "so": order,
                "u": content,
            },
        )
        made += 1
    return made


def _demo_trip(conn: Connection, plus, start: date) -> bool:
    if _one(
        conn,
        "SELECT 1 FROM trips WHERE owner_user_id = :u AND name = :n AND deleted_at IS NULL",
        u=plus,
        n=DEMO_TRIP,
    ):
        return False
    ret = start + timedelta(days=7)
    trip = _trip_with_plan(
        conn,
        plus,
        name=DEMO_TRIP,
        start=start,
        end=ret,
        spec=DEMO_PLAN,
        notes="A week to eat, walk and ride the trams.",
    )
    # The route, three fake fares and the chosen one (its dates are the trip's dates). These are FIXTURE data inserted
    # by SQL: nothing saw them on a page during a run. Never copy this pattern into real code (rule 4: fares must be seen).
    route = _one(
        conn,
        "INSERT INTO flight_routes (trip_id, label, origin_codes, destination_codes, trip_type, depart_from, depart_to, min_nights, max_nights, sources, created_by) "
        "VALUES (:t, 'New York to Lisbon', '{JFK}', '{LIS}', 'round_trip', :d0, :d1, 6, 8, '{manual}', :u) RETURNING id",
        t=trip,
        d0=start - timedelta(days=1),
        d1=start + timedelta(days=1),
        u=plus,
    )
    obs = []
    for i, (price, airline, stops) in enumerate(
        [(41200, "TAP Air Portugal", 0), (36800, "Iberia", 1), (33900, "Aer Lingus", 1)]
    ):
        oid = _one(
            conn,
            "INSERT INTO fare_observations (search_key, origin, destination, depart_date, return_date, source, confidence, currency, price_total_minor, airlines, stops_out, stops_back, "
            "source_url, source_domain, observed_at, expires_at) "
            "VALUES (:k, 'JFK', 'LIS', :d, :r, 'manual', 'indicative', 'USD', :p, :a, :s, :s, 'https://example.com/demo-fares', 'example.com', now() + make_interval(secs => :i), now() + interval '30 days') RETURNING id",
            k=hashlib.sha256(f"demo|{trip}|{i}".encode()).hexdigest(),
            d=start,
            r=ret,
            p=price,
            a=[airline],
            s=stops,
            i=i,
        )
        obs.append((oid, price, airline))
        conn.execute(
            text(
                "INSERT INTO trip_fare_links (trip_id, route_id, observation_id) VALUES (:t, :r, :o)"
            ),
            {"t": trip, "r": route, "o": oid},
        )
    oid, price, airline = obs[0]
    conn.execute(
        text(
            "INSERT INTO chosen_flights (trip_id, route_id, observation_id, origin, destination, depart_date, return_date, price_total_minor, currency, airlines, source, observed_at, chosen_by) "
            "VALUES (:t, :r, :o, 'JFK', 'LIS', :d, :ret, :p, 'USD', :a, 'manual', now(), :u)"
        ),
        {
            "t": trip,
            "r": route,
            "o": oid,
            "d": start,
            "ret": ret,
            "p": price,
            "a": [airline],
            "u": plus,
        },
    )
    # Two travelers so the hearts differ: the Plus owner's own person and a friend.
    me = _one(conn, "SELECT id FROM people WHERE owner_user_id = :u AND is_self", u=plus)
    friend = _one(
        conn,
        "SELECT id FROM people WHERE owner_user_id = :u AND name = 'Sam' AND linked_user_id IS NULL",
        u=plus,
    ) or _one(
        conn, "INSERT INTO people (owner_user_id, name) VALUES (:u, 'Sam') RETURNING id", u=plus
    )
    for p in (me, friend):
        conn.execute(
            text("INSERT INTO trip_people (trip_id, person_id, added_by) VALUES (:t, :p, :u)"),
            {"t": trip, "p": p, "u": plus},
        )
    stays = [
        (
            "Alfama terrace apartment",
            "https://example.com/stays/alfama-terrace",
            78000,
            "shortlisted",
            [me, friend],
        ),
        ("Baixa design loft", "https://example.com/stays/baixa-loft", 91000, "candidate", [me]),
        (
            "Principe Real garden flat",
            "https://example.com/stays/principe-real",
            84500,
            "candidate",
            [friend],
        ),
    ]
    for title, url, total, status, hearts in stays:
        lid = _one(
            conn,
            "INSERT INTO lodging_options (trip_id, title, url, url_normalized, site, check_in, check_out, guests, price_total_minor, price_per_night_minor, currency, status, favorite, added_via, created_by) "
            "VALUES (:t, :ti, :url, :url, 'example.com', :ci, :co, 2, :p, :pn, 'USD', CAST(:st AS lodging_status), :fav, 'manual', :u) RETURNING id",
            t=trip,
            ti=title,
            url=url,
            ci=start,
            co=ret,
            p=total,
            pn=total // 7,
            st=status,
            fav=len(hearts) > 1,
            u=plus,
        )
        for person in hearts:
            conn.execute(
                text(
                    "INSERT INTO lodging_votes (lodging_id, trip_id, person_id, user_id) VALUES (:l, :t, :p, :u)"
                ),
                {
                    "l": lid,
                    "t": trip,
                    "p": person,
                    "u": plus if person == me else None,
                },  # the friend has no account
            )
    for kind, title, status, source in [
        ("flights_booked", None, "done", "rules"),
        ("stay_booked", None, "todo", "rules"),
        ("tickets", None, "todo", "rules"),
        ("documents", None, "todo", "rules"),
        ("custom", "Book a table for the fado night", "todo", "user"),
    ]:
        done = status == "done"
        conn.execute(
            text(
                "INSERT INTO checklist_items (trip_id, kind, title, status, source, done_at, done_by) VALUES (:t, :k, :ti, :s, :src, CASE WHEN :d THEN now() END, CASE WHEN :d THEN CAST(:u AS uuid) END)"
            ),
            {"t": trip, "k": kind, "ti": title, "s": status, "src": source, "d": done, "u": plus},
        )
    # Evidence label: the note carries the source URL and the day it was seen (checked_at).
    conn.execute(
        text(
            "INSERT INTO notes (trip_id, kind, title, topic, body, urls, checked_at) VALUES (:t, 'agent', 'Trams and the transit pass', 'transport', "
            "'Tram 28 is crowded around midday. The 24 hour pass on the operator page covers trams, metro and buses.', "
            "'{https://www.carris.pt/en/}', now())"
        ),
        {"t": trip},
    )
    return True


DEMO_CREDITS = 40
DEMO_CREDITS_REASON = "demo seed"


def _demo_credits(conn: Connection, plus) -> int:
    """A funded demo account: one adjustment grant for the Plus persona, so the AI sheet shows a balance. Once only."""
    if _one(
        conn,
        "SELECT 1 FROM credit_ledger WHERE user_id = :u AND entry_type = 'adjust' AND note = :r",
        u=plus,
        r=DEMO_CREDITS_REASON,
    ):
        return 0
    with Session(bind=conn) as s:
        credits.adjust(s, plus, DEMO_CREDITS, reason=DEMO_CREDITS_REASON)
    return DEMO_CREDITS


def seed_demo(settings: Settings, *, system_url: str, today: date | None = None) -> dict[str, int]:
    """Create the personas through the dev session path, then the demo trip and the sample trips. Returns what was added."""
    if settings.environment not in LOCAL_ENVIRONMENTS or settings.auth_mode != "dev":
        raise RuntimeError("hermi seed --demo is for local and ci databases only")
    start = _base_start(today or date.today())
    engine = db.open_app_engine(settings)
    try:
        auth_service.dev_session(settings, engine, "plus")
    finally:
        engine.dispose()
    system = create_engine(db.sqlalchemy_url(system_url), poolclass=pool.NullPool)
    try:
        with system.begin() as conn:
            plus = _user_id(conn, auth_service.PERSONAS["plus"].email)
            return {
                "demo_trips": int(_demo_trip(conn, plus, start)),
                "sample_trips": _sample_trips(conn, start),
                "credits_granted": _demo_credits(conn, plus),
            }
    finally:
        system.dispose()
