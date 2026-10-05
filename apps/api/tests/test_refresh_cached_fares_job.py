# ruff: noqa: E501
"""The refresh_cached_fares worker job picks due routes only, through the fixture provider."""

from datetime import UTC, datetime, timedelta

from tests.test_fares_module import (  # noqa: F401
    ROUTE,
    _clean_observations,
    _rows,
    _trip,
    _user,
    client,
)

from hermi.config import Settings
from hermi.providers import travelpayouts
from hermi_worker.jobs import refresh_cached_fares as job


def test_job_refreshes_only_due_active_routes(client, db_urls, system_conn):  # noqa: F811
    h = _user(client)
    rid = client.post(f"/v1/trips/{_trip(client, h)}/routes", json=ROUTE, headers=h).json()["id"]
    system_conn.execute("DELETE FROM flight_routes WHERE id <> %s", (rid,))  # other tests' routes would be due too
    settings = Settings(_env_file=None, providers_mode="fake", database_url_system=db_urls["system"])
    now = datetime.now(UTC)
    assert job.run(settings, client=travelpayouts.fixture_client(), token="t", now=now) >= 1
    assert _rows(system_conn, "SELECT last_checked_at IS NOT NULL FROM flight_routes WHERE id = %s", rid) == [(True,)]
    # Just checked, so not due again; stale again after 6 h; inactive routes are skipped.
    assert job.run(settings, client=travelpayouts.fixture_client(), token="t", now=now + timedelta(hours=1)) == 0
    system_conn.execute("UPDATE flight_routes SET active = false WHERE id = %s", (rid,))
    assert job.run(settings, client=travelpayouts.fixture_client(), token="t", now=now + timedelta(hours=7)) == 0
    system_conn.execute("UPDATE flight_routes SET active = true WHERE id = %s", (rid,))
    assert job.run(settings, client=travelpayouts.fixture_client(), token="t", now=now + timedelta(hours=7)) >= 1


def test_job_does_nothing_without_a_token_in_live_mode(db_urls):
    assert job.run(Settings(_env_file=None, providers_mode="live", database_url_system=db_urls["system"])) == 0
