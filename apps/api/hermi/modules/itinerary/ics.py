# ruff: noqa: E501  (long lines)
"""RFC 5545 calendar text for a trip (04 section 5.29 content rules), written by hand: CRLF, lines folded at 75 octets, text escaped.

Pure functions, no database. Timed events are written in UTC (`...Z`), converted from the destination's zone with zoneinfo, so the file needs
no VTIMEZONE block and every calendar app shows the right instant. All-day events use `VALUE=DATE`.
shortcut: UTC instead of the spec's `TZID=` form. Ceiling: an app that shows "floating" local time of the destination reads the instant in
the viewer's own zone. Upgrade trigger: the calendar feed ticket (it may emit VTIMEZONE blocks from zoneinfo if Apple Calendar needs them).
Chosen flights are not events yet (they need `depart_at_local` from the flights module); the feed ticket adds them.
"""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

MAX_EVENTS = 2000
SITE = "https://hermi.world"
_STATUS = {"booked": "CONFIRMED", "idea": "TENTATIVE"}


def escape_text(value: str) -> str:
    """TEXT value escaping (RFC 5545 3.3.11): backslash, semicolon, comma and line breaks."""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line: str) -> str:
    """Fold at 75 octets (RFC 5545 3.1). A continuation starts with one space, so it carries 74 octets. Never splits a character."""
    out, cur, size, limit = [], "", 0, 75
    for ch in line:
        n = len(ch.encode())
        if size + n > limit:
            out.append(cur)
            cur, size, limit = "", 1, 75  # the leading space of the continuation is added on join and counts as one octet
        cur += ch
        size += n
    out.append(cur)
    return "\r\n ".join(out)


def _utc(day: date, at: time, zone: str | None) -> datetime:
    try:
        tz = ZoneInfo(zone) if zone else UTC
    except (ZoneInfoNotFoundError, ValueError):
        tz = UTC
    return datetime.combine(day, at, tzinfo=tz).astimezone(UTC)


def _stamp(d: datetime) -> str:
    return d.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _date(d: date) -> str:
    return d.strftime("%Y%m%d")


def _place(*parts: str | None) -> str | None:
    text = ", ".join(p for p in parts if p)
    return text or None


def _event(uid: str, stamp: datetime, version: int, updated_at: datetime, trip_id: str, props: list[str], summary: str,
           *, location: str | None, geo: tuple[float, float] | None, notes: str, url: str | None, status: str | None) -> list[str]:
    lines = ["BEGIN:VEVENT", f"UID:{uid}@hermi.world", f"DTSTAMP:{_stamp(stamp)}", *props, f"SUMMARY:{escape_text(summary)}"]
    if location:
        lines.append(f"LOCATION:{escape_text(location)}")
    if geo:
        lines.append(f"GEO:{geo[0]:.6f};{geo[1]:.6f}")
    # Notes are shared with every member already; prices, confirmation numbers and people never enter the feed.
    description = (notes.strip() + "\n" if notes.strip() else "") + f"{SITE}/trips/{trip_id}"
    lines.append(f"DESCRIPTION:{escape_text(description)}")
    if url:
        lines.append(f"URL:{url.replace(chr(10), '').replace(chr(13), '')}")
    if status:
        lines.append(f"STATUS:{status}")
    lines += [f"SEQUENCE:{version}", f"LAST-MODIFIED:{_stamp(updated_at)}", "END:VEVENT"]
    return lines


def build_calendar(*, name: str, trip_id: str, timezone: str | None, items: list[dict], stays: list[dict], stamp: datetime) -> str:
    """The calendar text. `items` are itinerary rows with a `timezone` key (the day's destination zone); pool items (no day) are left out."""
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Hermi//Trip//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(name)}",
    ]
    if timezone:
        lines.append(f"X-WR-TIMEZONE:{timezone}")
    lines += ["REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H"]
    dated = sorted((i for i in items if i["day"] is not None), key=lambda i: (i["day"], i["start_time"] is None, i["start_time"] or time.min, str(i["id"])))
    for it in dated[:MAX_EVENTS]:
        if it["start_time"] is None:
            props = [f"DTSTART;VALUE=DATE:{_date(it['day'])}", f"DTEND;VALUE=DATE:{_date(it['day'] + timedelta(days=1))}"]
        else:
            start = _utc(it["day"], it["start_time"], it.get("timezone") or timezone)
            end = _utc(it["day"], it["end_time"], it.get("timezone") or timezone) if it["end_time"] is not None else start + timedelta(hours=1)
            if end <= start:  # an end at or before the start runs past midnight
                end = _utc(it["day"] + timedelta(days=1), it["end_time"], it.get("timezone") or timezone) if it["end_time"] is not None else start + timedelta(hours=1)
            props = [f"DTSTART:{_stamp(start)}", f"DTEND:{_stamp(end)}"]
        geo = (it["lat"], it["lon"]) if it.get("lat") is not None and it.get("lon") is not None else None
        lines += _event(
            f"item-{it['id']}", stamp, it["version"], it["updated_at"], trip_id, props, it["title"],
            location=_place(it.get("location_name"), it.get("address")), geo=geo, notes=it.get("notes") or "", url=it.get("url"), status=_STATUS.get(it["status"]),
        )
    room = MAX_EVENTS - len(dated[:MAX_EVENTS])
    for st in [s for s in stays if s.get("check_in")][: max(room, 0)]:
        end = st["check_out"] if st.get("check_out") and st["check_out"] > st["check_in"] else st["check_in"] + timedelta(days=1)
        lines += _event(
            f"stay-{st['id']}", stamp, st["version"], st["updated_at"], trip_id,
            [f"DTSTART;VALUE=DATE:{_date(st['check_in'])}", f"DTEND;VALUE=DATE:{_date(end)}"], st["title"],
            location=st.get("location_name"), geo=None, notes="", url=None, status="CONFIRMED",
        )
    lines.append("END:VCALENDAR")
    return "".join(fold(line) + "\r\n" for line in lines)
