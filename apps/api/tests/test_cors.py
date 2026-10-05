"""WF-017: CORS for the web app, staging and Capacitor. Bearer only, so no credentials."""

import pytest
from fastapi.testclient import TestClient

from hermi.config import Settings
from hermi.main import create_app


@pytest.fixture
def client():
    s = Settings(
        _env_file=None,
        environment="ci",
        auth_mode="dev",
        cors_allowed_origins="https://staging.hermi.example",
    )
    return TestClient(create_app(s))


def _preflight(client, origin):
    return client.options(
        "/health/live",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


@pytest.mark.parametrize(
    "origin",
    [
        "https://staging.hermi.example",
        "capacitor://localhost",
        "https://localhost",
    ],
)
def test_preflight_allows_web_staging_and_capacitor(client, origin):
    r = _preflight(client, origin)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin
    assert "authorization" in r.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in r.headers


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost"])
def test_preflight_refuses_other_origins(client, origin):
    r = _preflight(client, origin)
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers
