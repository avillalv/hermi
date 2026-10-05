# ruff: noqa: E501  (long comments)
"""WF-032.1: the RFC 5545 generator (04 section 5.29 content rules), checked against a golden file. Pure, no database."""

from datetime import UTC, date, datetime, time
from pathlib import Path

from hermi.modules.itinerary import ics

GOLDEN = Path(__file__).parent / "fixtures" / "itinerary_golden.ics"
TRIP = "0192f1b2-0000-7000-8000-000000000001"
STAMP = datetime(2027, 4, 2, 12, 0, tzinfo=UTC)


def _item(n, **kw):
    base = dict(
        id=f"0192f1b2-0000-7000-8000-0000000001{n:02d}", day=date(2027, 5, 1), start_time=None, end_time=None, title="Item",
        location_name=None, address=None, lat=None, lon=None, url=None, notes="", status="planned", version=1,
        updated_at=datetime(2027, 4, 1, 10, 0, tzinfo=UTC), timezone="Europe/Lisbon",
    )
    return {**base, **kw}


def _calendar():
    items = [
        _item(1, start_time=time(9, 30), end_time=time(11, 0), title="Tram 28; Alfama, early", location_name="Alfama", address="Rua da Graca 1, Lisbon",
              lat=38.7139, lon=-9.1301, url="https://example.com/tram", notes="Bring cash\\ small notes,\nearly start", status="booked", version=3),
        _item(2, day=date(2027, 5, 2), title="Day trip to Sintra with a very long title that has to be folded because it runs past seventy five octets, with an accent: café éééééééééé", status="idea"),
        _item(3, day=date(2027, 5, 3), start_time=time(22, 0), end_time=time(1, 0), title="Fado night"),
        _item(4, day=date(2027, 5, 3), start_time=time(8, 0), title="Flight to Tokyo", timezone="Asia/Tokyo"),
        _item(5, day=None, title="Pool idea, never in the feed"),
    ]
    stays = [dict(id="0192f1b2-0000-7000-8000-000000000201", title="Hotel Alfama", check_in=date(2027, 5, 1), check_out=date(2027, 5, 4), location_name="Alfama",
                  lat=None, lon=None, version=2, updated_at=datetime(2027, 4, 1, 11, 0, tzinfo=UTC))]
    return ics.build_calendar(name="Lisbon, spring", trip_id=TRIP, timezone="Europe/Lisbon", items=items, stays=stays, stamp=STAMP)


def test_matches_the_golden_file():
    assert _calendar().encode() == GOLDEN.read_bytes()


def test_wire_format_rules():
    out = _calendar()
    assert out.endswith("\r\n") and "\n" not in out.replace("\r\n", "")
    for line in out.split("\r\n")[:-1]:
        assert len(line.encode()) <= 75, line
    unfolded = out.replace("\r\n ", "")
    assert unfolded.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Hermi//Trip//EN\r\n")
    assert unfolded.count("BEGIN:VEVENT") == unfolded.count("END:VEVENT") == 5  # four items and one stay; the pool item is left out
    assert "Pool idea" not in out
    assert "SUMMARY:Tram 28\\; Alfama\\, early" in unfolded
    assert "UID:item-0192f1b2-0000-7000-8000-000000000101@hermi.world" in unfolded and "SEQUENCE:3" in unfolded
    assert "DTSTART:20270503T210000Z" in unfolded and "DTEND:20270504T000000Z" in unfolded  # 22:00 to 01:00 runs past midnight
    assert "DTSTART:20270502T230000Z" in unfolded  # Tokyo 08:00 on the 3rd is 23:00Z on the 2nd


def test_escape_and_fold_keep_multibyte_characters_whole():
    assert ics.escape_text("a\\b;c,d\ne\r\nf") == "a\\\\b\\;c\\,d\\ne\\nf"
    folded = ics.fold("DESCRIPTION:" + "é" * 100)
    for part in folded.split("\r\n"):
        assert len(part.encode()) <= 75
        part.encode().decode()  # no split character
    assert folded.replace("\r\n ", "") == "DESCRIPTION:" + "é" * 100
