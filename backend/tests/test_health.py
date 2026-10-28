from unittest.mock import MagicMock
from backend.app.db.database import get_db
from backend.app.main import app
from fastapi.testclient import TestClient


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "database" in data
    assert "timestamp" in data
    assert "app" in data
    assert "version" in data


def test_liveness_and_readiness_probes(client):
    live_res = client.get("/api/v1/health/liveness")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    ready_res = client.get("/api/v1/health/readiness")
    assert ready_res.status_code == 200
    assert ready_res.json()["ready"] is True


def test_health_check_database_failure():
    """Verify that a degraded/failing database returns HTTP 503."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("SQLite disk I/O failure")

    def broken_db():
        yield mock_db

    app.dependency_overrides[get_db] = broken_db
    with TestClient(app) as broken_client:
        res = broken_client.get("/api/v1/health")
        assert res.status_code == 503
        data = res.json()
        assert data["status"] == "degraded"
        assert "SQLite disk I/O failure" in data["database"]

        ready_res = broken_client.get("/api/v1/health/readiness")
        assert ready_res.status_code == 503
        assert ready_res.json()["ready"] is False

    app.dependency_overrides.clear()
