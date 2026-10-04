from fastapi.testclient import TestClient

from hermi.main import create_app


def test_health_live():
    r = TestClient(create_app()).get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_app_refuses_hosted_env_with_missing_secrets(monkeypatch):
    import pytest

    from hermi.config import ConfigError

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_MODE", "supabase")
    with pytest.raises(ConfigError, match="missing required"):
        create_app()
