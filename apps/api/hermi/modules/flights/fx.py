# ruff: noqa: E501
"""Reference-rate refresh and the local currency by country.

Conversion is not here: money is integer minor units, converted at read time in SQL by `fx_convert_minor()`
with `currency_exponent()` (03 section 3). `refresh_fx_rates` is called by the daily worker job.
"""

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from hermi.modules.ai.provider_calls import metered
from hermi.providers import ProviderError, frankfurter

_UPSERT = text(
    """INSERT INTO fx_rates (currency, per_eur, rate_date, fetched_at) VALUES (:c, :r, :d, now())
       ON CONFLICT (currency) DO UPDATE SET per_eur = EXCLUDED.per_eur, rate_date = EXCLUDED.rate_date,
         fetched_at = EXCLUDED.fetched_at"""
)
_CODE = re.compile(r"^[A-Z]{3}$")


def refresh_fx_rates(session: Session, client=None) -> int:
    """Fetch rates (recorded in provider_calls), upsert them, return the count. Old rates stay on failure.

    EUR is the base and has no row (03 section 3), so it is not stored."""
    rates = metered(
        session,
        "frankfurter",
        "/v2/rates",
        lambda: frankfurter.latest_rates_per_eur(client),
        params={"base": "EUR"},
    )
    rows = [
        {"c": c, "r": r, "d": d} for c, (r, d) in rates.items() if c != "EUR" and _CODE.match(c)
    ]
    if not rows:
        raise ProviderError("Exchange rate response had no usable rates.")
    session.execute(_UPSERT, rows)
    return len(rows)


# The currency people pay in, by ISO country code (ISO 4217, as of 2026: Bulgaria uses the euro,
# Curaçao and Sint Maarten the Caribbean guilder).
_LOCAL_CURRENCY_TABLE = """
AD EUR AE AED AF AFN AG XCD AI XCD AL ALL AM AMD AO AOA AR ARS AS USD AT EUR AU AUD AW AWG AX EUR
AZ AZN BA BAM BB BBD BD BDT BE EUR BF XOF BG EUR BH BHD BI BIF BJ XOF BL EUR BM BMD BN BND BO BOB
BQ USD BR BRL BS BSD BT BTN BV NOK BW BWP BY BYN BZ BZD CA CAD CC AUD CD CDF CF XAF CG XAF CH CHF
CI XOF CK NZD CL CLP CM XAF CN CNY CO COP CR CRC CU CUP CV CVE CW XCG CX AUD CY EUR CZ CZK DE EUR
DJ DJF DK DKK DM XCD DO DOP DZ DZD EC USD EE EUR EG EGP EH MAD ER ERN ES EUR ET ETB FI EUR FJ FJD
FK FKP FM USD FO DKK FR EUR GA XAF GB GBP GD XCD GE GEL GF EUR GG GBP GH GHS GI GIP GL DKK GM GMD
GN GNF GP EUR GQ XAF GR EUR GS GBP GT GTQ GU USD GW XOF GY GYD HK HKD HM AUD HN HNL HR EUR HT HTG
HU HUF ID IDR IE EUR IL ILS IM GBP IN INR IO USD IQ IQD IR IRR IS ISK IT EUR JE GBP JM JMD JO JOD
JP JPY KE KES KG KGS KH KHR KI AUD KM KMF KN XCD KP KPW KR KRW KW KWD KY KYD KZ KZT LA LAK LB LBP
LC XCD LI CHF LK LKR LR LRD LS LSL LT EUR LU EUR LV EUR LY LYD MA MAD MC EUR MD MDL ME EUR MF EUR
MG MGA MH USD MK MKD ML XOF MM MMK MN MNT MO MOP MP USD MQ EUR MR MRU MS XCD MT EUR MU MUR MV MVR
MW MWK MX MXN MY MYR MZ MZN NA NAD NC XPF NE XOF NF AUD NG NGN NI NIO NL EUR NO NOK NP NPR NR AUD
NU NZD NZ NZD OM OMR PA USD PE PEN PF XPF PG PGK PH PHP PK PKR PL PLN PM EUR PN NZD PR USD PS ILS
PT EUR PW USD PY PYG QA QAR RE EUR RO RON RS RSD RU RUB RW RWF SA SAR SB SBD SC SCR SD SDG SE SEK
SG SGD SH SHP SI EUR SJ NOK SK EUR SL SLE SM EUR SN XOF SO SOS SR SRD SS SSP ST STN SV USD SX XCG
SY SYP SZ SZL TC USD TD XAF TF EUR TG XOF TH THB TJ TJS TK NZD TL USD TM TMT TN TND TO TOP TR TRY
TT TTD TV AUD TW TWD TZ TZS UA UAH UG UGX UM USD US USD UY UYU UZ UZS VA EUR VC XCD VE VES VG USD
VI USD VN VND VU VUV WF XPF WS WST XK EUR YE YER YT EUR ZA ZAR ZM ZMW ZW ZWG
"""
_codes = _LOCAL_CURRENCY_TABLE.split()
LOCAL_CURRENCY = dict(zip(_codes[::2], _codes[1::2], strict=True))


def local_currency(country_code: str | None) -> str | None:
    return LOCAL_CURRENCY.get(country_code.upper()) if country_code else None
