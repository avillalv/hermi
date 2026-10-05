"""Reference exchange rates from Frankfurter (ECB and other central banks; free, no key)."""

import json
from datetime import date
from decimal import Decimal

import httpx

from hermi.providers import ProviderError

RATES_URL = "https://api.frankfurter.dev/v2/rates"


MAX_BODY_BYTES = 1_000_000  # the real response is about 10 KB


def _fetch(client: httpx.Client) -> list:
    with client.stream("GET", RATES_URL, params={"base": "EUR"}) as response:
        if response.status_code >= 400:
            raise ProviderError(
                f"Couldn't fetch exchange rates: HTTP {response.status_code}",
                status_code=response.status_code,
            )
        body = b""
        for chunk in response.iter_bytes():
            body += chunk
            if len(body) > MAX_BODY_BYTES:
                raise ProviderError("Exchange rate response was too large.")
        return json.loads(body)


def latest_rates_per_eur(client: httpx.Client | None = None) -> dict[str, tuple[Decimal, date]]:
    """Units of each currency per 1 EUR, with the date each rate was published.

    Pass a client in tests; otherwise this owns one with an explicit timeout."""
    try:
        if client is None:
            with httpx.Client(timeout=10.0) as own:
                rows = _fetch(own)
        else:
            rows = _fetch(client)
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError(f"Couldn't fetch exchange rates: {exc}") from exc

    rates: dict[str, tuple[Decimal, date]] = {}
    for row in rows:
        try:
            rates[row["quote"].upper()] = (
                Decimal(str(row["rate"])),
                date.fromisoformat(row["date"]),
            )
        except (KeyError, ValueError, TypeError, ArithmeticError):
            continue
    if not rates:
        raise ProviderError("Exchange rate response had no usable rates.")
    rates["EUR"] = (Decimal(1), max(d for _, d in rates.values()))
    return rates
