"""Evidence rules, adapted from the Trip Planner test_agent_api.py link rules and ingest bounds."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from hermi.modules.ai import ingest
from hermi.modules.ai.ingest import observed_during_run, price_in_bounds, source_problem


@pytest.mark.parametrize(
    "url",
    [
        "http://10.0.0.5/x",
        "http://[::1]/x",
        "http://printer.local/x",
        "http://intranet/x",
        "javascript:alert(1)",
        "",
        "http://localhost/x",
        "ftp://example.com/x",
    ],
)
def test_private_or_odd_links_are_not_sources(url: str) -> None:
    assert source_problem(url) is not None


def test_public_links_are_sources() -> None:
    assert source_problem("https://www.united.com/en/us/fsr/choose-flights?f=LAX&t=NRT") is None


@pytest.mark.parametrize(
    "url",
    [
        "https://www.airbnb.co.uk/rooms/1",
        "https://vrbo.com/x",
        "https://secure.booking.com/h",
        "https://airbnb.co.kr/",
    ],
)
def test_blocked_hosts_are_not_sources(url: str) -> None:
    assert "must not use" in (source_problem(url) or "")


def test_ingest_imports_the_one_constant() -> None:
    from hermi.modules.ai import policy

    assert ingest.blocked_domain is policy.blocked_domain


def test_price_bounds() -> None:
    assert price_in_bounds(Decimal(500), 1)
    assert price_in_bounds(Decimal(1000), 2)
    assert not price_in_bounds(Decimal(10), 1)
    assert not price_in_bounds(Decimal(40_000), 2)
    assert price_in_bounds(Decimal(60), 1, rate=Decimal("2"))  # 30 USD at 2 per USD
    assert not price_in_bounds(Decimal(59), 1, rate=Decimal("2"))


def test_observed_during_the_run() -> None:
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    start = now - timedelta(minutes=30)
    assert observed_during_run(now - timedelta(minutes=5), start, now)
    assert observed_during_run(start - timedelta(minutes=9), start, now)
    assert not observed_during_run(start - timedelta(hours=2), start, now)
    assert not observed_during_run(now + timedelta(hours=1), start, now)
    assert observed_during_run(datetime(2026, 1, 1, 11, 50), start, now)  # naive means UTC
