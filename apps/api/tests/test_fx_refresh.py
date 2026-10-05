"""Daily FX refresh, the provider_calls ledger and exact conversion, against a mocked Frankfurter and the test database."""
# ruff: noqa: E501

import httpx
import pytest

from hermi import db
from hermi.providers import ProviderError

ROWS = [
    {"date": "2026-10-02", "base": "EUR", "quote": "USD", "rate": 1.1},
    {"date": "2026-10-02", "base": "EUR", "quote": "JPY", "rate": 160},
    {"date": "2026-10-02", "base": "EUR", "quote": "gbp", "rate": 0.85},
]

# The same vectors are in apps/web/src/lib/money.test.ts: (minor, from, to, expected). Rates per EUR: GBP 0.5, JPY 1, KWD 1, CHF 3, CAD 1.5.
HALF_VECTORS = [
    (5, "EUR", "GBP", 3),
    (-5, "EUR", "GBP", -3),
    (1, "EUR", "GBP", 1),
    (50, "EUR", "JPY", 1),
    (-50, "EUR", "JPY", -1),
    (5, "KWD", "EUR", 1),
    (-5, "KWD", "EUR", -1),
    (4, "KWD", "EUR", 0),
    (1, "CHF", "CAD", 1),  # 1 / 3 * 1.5 * 100 / 100 = 0.5 exactly; a divide-first form truncates to 0
    (-1, "CHF", "CAD", -1),
]


def _client(status: int = 200, rows=ROWS):
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=rows)))


@pytest.fixture
def session(db_urls, system_conn):
    from sqlalchemy.orm import Session

    system_conn.execute("DELETE FROM fx_rates")
    system_conn.execute("DELETE FROM provider_calls")
    engine = db.make_engine(db_urls["system"])
    with Session(engine) as s:
        yield s
    engine.dispose()


def test_refresh_upserts_rates_and_records_one_ledger_row(session, system_conn):
    from hermi.modules.flights.fx import refresh_fx_rates

    with _client() as c:
        assert refresh_fx_rates(session, c) == 3  # EUR is the base and has no row
    session.commit()
    with _client(rows=[{**ROWS[0], "rate": 1.2, "date": "2026-10-03"}]) as c:
        refresh_fx_rates(session, c)
    session.commit()

    got = dict(system_conn.execute("SELECT currency, per_eur FROM fx_rates").fetchall())
    assert float(got["USD"]) == 1.2 and "EUR" not in got and "JPY" in got
    calls = system_conn.execute(
        "SELECT provider, endpoint, ok, status_code, cached, cost_usd_micros, request_hash FROM provider_calls ORDER BY id"
    ).fetchall()
    assert len(calls) == 2
    assert calls[0][:2] == ("frankfurter", "/v2/rates") and calls[0][2] is True
    assert calls[0][3] == 200 and calls[0][4] is False and calls[0][5] is None
    assert len(calls[0][6]) == 64


def test_failed_fetch_is_in_the_ledger_and_keeps_old_rates(session, system_conn):
    from hermi.modules.flights.fx import refresh_fx_rates

    with _client() as c:
        refresh_fx_rates(session, c)
    session.commit()
    with _client(status=503) as c, pytest.raises(ProviderError):
        refresh_fx_rates(session, c)

    assert system_conn.execute("SELECT count(*) FROM fx_rates").fetchone()[0] == 3
    ok, code = system_conn.execute(
        "SELECT ok, status_code FROM provider_calls ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert (ok, code) == (False, 503)


def test_failed_metered_call_does_not_commit_the_callers_pending_work(session, system_conn):
    from sqlalchemy import text

    from hermi.modules.ai.provider_calls import metered

    session.execute(
        text("INSERT INTO fx_rates (currency, per_eur, rate_date) VALUES ('ZZZ', 2, current_date)")
    )

    def boom():
        raise ProviderError("down", status_code=502)

    with pytest.raises(ProviderError):
        metered(session, "frankfurter", "/v2/rates", boom)

    assert (
        system_conn.execute("SELECT count(*) FROM fx_rates WHERE currency = 'ZZZ'").fetchone()[0]
        == 0
    )
    assert system_conn.execute("SELECT status_code FROM provider_calls").fetchone()[0] == 502
    session.rollback()


def test_stored_rates_convert_with_consistent_rounding(session, system_conn):
    from hermi.modules.flights.fx import refresh_fx_rates

    with _client() as c:
        refresh_fx_rates(session, c)
    session.commit()

    def conv(m, a, b):
        return system_conn.execute("SELECT fx_convert_minor(%s, %s, %s)", (m, a, b)).fetchone()[0]

    assert conv(10000, "USD", "JPY") == 14545  # same as money.test.ts
    assert conv(11000, "USD", "EUR") == 10000
    assert conv(100, "USD", "ZZZ") is None


@pytest.mark.parametrize(("minor", "src", "dst", "expected"), HALF_VECTORS)
def test_exact_halves_round_away_from_zero(system_conn, db_urls, minor, src, dst, expected):
    system_conn.execute("DELETE FROM fx_rates")
    system_conn.execute(
        "INSERT INTO fx_rates (currency, per_eur, rate_date) VALUES ('GBP', 0.5, current_date), ('JPY', 1, current_date), ('KWD', 1, current_date), ('CHF', 3, current_date), ('CAD', 1.5, current_date)"
    )
    got = system_conn.execute("SELECT fx_convert_minor(%s, %s, %s)", (minor, src, dst)).fetchone()[
        0
    ]
    assert got == expected


def _settings(db_urls, mode="live"):
    class S:
        providers_mode = mode

        def require(self, _k):
            return db_urls["system"]

    return S()


def test_job_runs_through_the_worker_login(db_urls, system_conn):
    from hermi_worker.jobs import refresh_fx_rates as job

    system_conn.execute("DELETE FROM fx_rates")
    with _client() as c:
        assert job.run(_settings(db_urls), client=c) == 3
    assert system_conn.execute("SELECT count(*) FROM fx_rates").fetchone()[0] == 3


def test_job_skips_in_fake_mode_and_when_the_kill_switch_is_engaged(db_urls, system_conn):
    from hermi_worker.jobs import refresh_fx_rates as job

    system_conn.execute("DELETE FROM fx_rates")
    assert job.run(_settings(db_urls, "fake")) == 0

    system_conn.execute("DELETE FROM kill_switches WHERE key = 'provider.frankfurter'")
    system_conn.execute(
        "INSERT INTO kill_switches (key, engaged, engaged_at, expires_at) VALUES ('provider.frankfurter', true, now(), now() + interval '1 hour')"
    )
    try:
        with _client() as c:
            assert job.run(_settings(db_urls), client=c) == 0
    finally:
        system_conn.execute("DELETE FROM kill_switches WHERE key = 'provider.frankfurter'")
    assert system_conn.execute("SELECT count(*) FROM fx_rates").fetchone()[0] == 0


def test_job_with_a_failing_provider_raises_and_leaves_a_failed_ledger_row(db_urls, system_conn):
    from hermi_worker.jobs import refresh_fx_rates as job

    system_conn.execute("DELETE FROM provider_calls")
    with _client(status=503) as c, pytest.raises(ProviderError):
        job.run(_settings(db_urls), client=c)
    ok, code = system_conn.execute("SELECT ok, status_code FROM provider_calls ORDER BY id DESC LIMIT 1").fetchone()
    assert (ok, code) == (False, 503)


def test_a_response_with_no_usable_rates_is_an_error_and_stores_nothing(session, system_conn):
    from hermi.modules.flights.fx import refresh_fx_rates

    # Only an EUR quote survives parsing, and EUR is the base with no row.
    with _client(rows=[{"date": "2026-10-02", "base": "EUR", "quote": "EUR", "rate": 1}]) as c:
        with pytest.raises(ProviderError, match="no usable rates"):
            refresh_fx_rates(session, c)
    assert system_conn.execute("SELECT count(*) FROM fx_rates").fetchone()[0] == 0
