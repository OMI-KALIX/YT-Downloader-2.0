from fastapi.testclient import TestClient
from cloud.app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "extension" in data
    assert "agent" in data


def test_config_endpoint():
    response = client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "max_concurrent_downloads" in data


def test_agent_latest_endpoint():
    response = client.get("/agent/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "2.1.0"
    assert "sha256" in data
    assert "download_url" in data
