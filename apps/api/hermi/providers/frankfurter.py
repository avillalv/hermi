"""Reference exchange rates from Frankfurter (ECB and other central banks; free, no key)."""

from datetime import date
from decimal import Decimal

import httpx

from hermi.providers import ProviderError

RATES_URL = "https://api.frankfurter.dev/v2/rates"


def latest_rates_per_eur(client: httpx.Client) -> dict[str, tuple[Decimal, date]]:
    """Units of each currency per 1 EUR, with the date each rate was published."""
    try:
        response = client.get(RATES_URL, params={"base": "EUR"})
        response.raise_for_status()
        rows = response.json()
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
