from pathlib import Path

from fastapi.testclient import TestClient

from hermi import health
from hermi.config import load_settings
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


# WF-008: /health/ready. The probes are injected, so no database is needed.

DB_URL = "postgresql+psycopg://user:s3cret@db:5432/hermi"


def ready(monkeypatch, *, url=DB_URL, probe=lambda u: "abc", head=lambda: "abc"):
    if url:
        monkeypatch.setenv("DATABASE_URL", url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(health, "probe_db", probe)
    monkeypatch.setattr(health, "expected_head", head)
    return TestClient(create_app(load_settings(bind_host="127.0.0.1"))).get("/health/ready")


def test_ready_ok_and_reports_ai_provider(monkeypatch):
    r = ready(monkeypatch)
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "database": "ok",
        "migrations": "ok",
        "ai_provider": "fake",
    }


def test_ready_ok_when_no_migrations_exist_yet(monkeypatch):
    r = ready(monkeypatch, probe=lambda u: None, head=lambda: None)
    assert r.status_code == 200 and r.json()["migrations"] == "none"


def test_ready_503_on_stale_migration(monkeypatch):
    r = ready(monkeypatch, probe=lambda u: "old")
    assert r.status_code == 503
    assert r.json()["status"] == "fail" and r.json()["migrations"] == "stale"


def test_ready_503_when_database_unreachable_without_leaking(monkeypatch):
    def boom(u):
        raise RuntimeError(f"could not connect to {u}")

    r = ready(monkeypatch, probe=boom)
    assert r.status_code == 503 and r.json()["database"] == "unreachable"
    assert "s3cret" not in r.text and "postgresql" not in r.text


def test_ready_503_when_database_not_configured(monkeypatch):
    r = ready(monkeypatch, url=None)
    assert r.status_code == 503 and r.json()["database"] == "not_configured"


def test_psycopg_url_strips_driver_suffix():
    assert health.psycopg_url(DB_URL) == "postgresql://user:s3cret@db:5432/hermi"


def test_expected_head_reads_the_revision_graph(tmp_path):
    (tmp_path / "a.py").write_text('revision = "a1"\ndown_revision = None\n')
    (tmp_path / "b.py").write_text('revision: str = "b2"\ndown_revision: str | None = "a1"\n')
    assert health.expected_head(tmp_path) == "b2"
    assert health.expected_head(tmp_path / "missing") is None


def test_dockerfile_is_non_root_with_healthcheck():
    text = (Path(__file__).parents[3] / "infra/docker/Dockerfile").read_text()
    assert "USER 10001" in text and "HEALTHCHECK" in text and "/health/live" in text


def test_expected_head_with_several_heads_is_never_current(tmp_path):
    (tmp_path / "a.py").write_text('revision = "a1"\ndown_revision = None\n')
    (tmp_path / "b.py").write_text('revision = "b2"\ndown_revision = None\n')
    head = health.expected_head(tmp_path)
    assert head not in ("a1", "b2")


def test_versions_dir_is_inside_the_package():
    import hermi

    assert health.VERSIONS_DIR == Path(hermi.__file__).parent / "migrations" / "versions"
