from fastapi.testclient import TestClient

from hermi.main import create_app


def test_health_live():
    r = TestClient(create_app()).get("/health/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
