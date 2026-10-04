"""Travelpayouts and Frankfurter parsing against mocked transports. No network."""

from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest

from hermi.providers import ProviderError, frankfurter, travelpayouts


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


TP_ROW = {
    "origin": "LAX",
    "destination": "TYO",
    "origin_airport": "LAX",
    "destination_airport": "NRT",
    "departure_at": "2026-11-10T11:30:00-08:00",
    "return_at": "2026-11-17T10:55:00+09:00",
    "price": 760,
    "airline": "MU",
    "flight_number": "586",
    "transfers": 1,
    "return_transfers": 1,
    "duration_to": 1020,
    "duration_back": 945,
    "link": "/search/LAX1011TYO17111?t=abc&search_date=21092026&expected_price=760",
}


def test_cached_fare_uses_real_airports_local_dates_and_found_date() -> None:
    fare = travelpayouts.to_fare(TP_ROW, "usd")

    assert fare is not None
    assert (fare.origin, fare.destination) == ("LAX", "NRT")
    assert (fare.depart_date, fare.return_date) == (date(2026, 11, 10), date(2026, 11, 17))
    assert fare.depart_at_local == "2026-11-10 11:30"
    assert fare.price_per_adult == Decimal(760)
    assert fare.flight_number == "MU 586"
    assert fare.found_at == datetime(2026, 9, 21, 12, tzinfo=UTC)
    assert fare.link is not None and fare.link.startswith(
        "https://www.aviasales.com/search/LAX1011TYO17111"
    )


def test_rows_without_a_price_or_date_are_skipped() -> None:
    assert travelpayouts.to_fare({**TP_ROW, "price": 0}, "USD") is None
    assert travelpayouts.to_fare({**TP_ROW, "departure_at": None}, "USD") is None


def test_prices_for_dates_requests_a_month_and_reports_failures() -> None:
    bodies = iter(
        [
            {"success": True, "currency": "usd", "data": [TP_ROW]},
            {"success": False, "error": "Unauthorized"},
        ]
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=next(bodies))

    with client_for(handler) as client:
        fares = travelpayouts.prices_for_dates(
            client,
            "token",
            origin="LAX",
            destination="NRT",
            departure_month="2026-11",
            return_month="2026-11",
            currency="USD",
        )
        with pytest.raises(ProviderError, match="Unauthorized"):
            travelpayouts.prices_for_dates(
                client,
                "token",
                origin="LAX",
                destination="NRT",
                departure_month="2026-11",
                return_month=None,
                currency="USD",
            )

    assert len(fares) == 1
    assert str(seen[0].url).startswith(f"{travelpayouts.BASE_URL}/prices_for_dates")
    assert seen[0].headers["x-access-token"] == "token"
    assert seen[0].url.params["one_way"] == "false"
    assert seen[1].url.params["one_way"] == "true"


def test_http_failure_is_a_provider_error() -> None:
    with client_for(lambda r: httpx.Response(500)) as client, pytest.raises(ProviderError):
        travelpayouts.prices_for_dates(
            client,
            "t",
            origin="LAX",
            destination="NRT",
            departure_month="2026-11",
            return_month=None,
            currency="USD",
        )


def test_exchange_rates_include_eur() -> None:
    rows = [
        {"date": "2026-09-26", "base": "EUR", "quote": "USD", "rate": 1.08},
        {"date": "2026-09-25", "base": "EUR", "quote": "JPY", "rate": 171.2},
    ]

    with client_for(lambda r: httpx.Response(200, json=rows)) as client:
        rates = frankfurter.latest_rates_per_eur(client)

    assert rates["USD"] == (Decimal("1.08"), date(2026, 9, 26))
    assert rates["EUR"] == (Decimal(1), date(2026, 9, 26))


def test_empty_exchange_rates_are_an_error() -> None:
    with client_for(lambda r: httpx.Response(200, json=[])) as client, pytest.raises(ProviderError):
        frankfurter.latest_rates_per_eur(client)
