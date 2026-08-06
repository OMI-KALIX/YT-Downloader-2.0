import os
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.cookies.manager import temporary_cookie_file
from backend.progress.tracker import ProgressTracker
from backend.extractors.registry import extractor_registry
from backend.api.router import enforce_rate_limit, RATE_LIMIT_REQUESTS
from fastapi import HTTPException

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_metrics_endpoint():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "active_jobs" in data
    assert "completed_jobs" in data

def test_cookie_file_lifecycle_cleanup():
    cookie_content = "youtube.com\tTRUE\t/\tFALSE\t0\tTEST_NAME\tTEST_VAL"
    created_path = None

    with temporary_cookie_file(cookie_content) as path:
        created_path = path
        assert path is not None
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "TEST_NAME" in content

    # Assert that file was strictly deleted after context exit
    assert not os.path.exists(created_path)

def test_cookie_file_cleanup_on_exception():
    cookie_content = "youtube.com\tTRUE\t/\tFALSE\t0\tTEST_NAME\tTEST_VAL"
    created_path = None

    try:
        with temporary_cookie_file(cookie_content) as path:
            created_path = path
            assert os.path.exists(path)
            raise RuntimeError("Simulated download failure")
    except RuntimeError:
        pass

    # File must still be deleted on failure
    assert not os.path.exists(created_path)

def test_progress_tracker_pubsub():
    tracker = ProgressTracker(ttl_seconds=300)
    job_id = "test-job-123"
    tracker.create_job(job_id, "https://youtube.com/watch?v=dQw4w9WgXcQ")

    updates_received = []
    def on_update(job_snapshot):
        updates_received.append(job_snapshot)

    tracker.subscribe(job_id, on_update)
    tracker.update_job(job_id, {"status": "downloading", "percent": 50.0})

    assert len(updates_received) == 1
    assert updates_received[0]["percent"] == 50.0

    tracker.unsubscribe(job_id, on_update)
    tracker.update_job(job_id, {"status": "completed", "percent": 100.0})

    # Unsubscribed, so updates_received should remain 1
    assert len(updates_received) == 1

def test_extractor_registry():
    yt_match = extractor_registry.match("https://www.youtube.com/watch?v=abc")
    assert yt_match is not None
    assert yt_match.name == "YouTube"

    vimeo_match = extractor_registry.match("https://vimeo.com/123456")
    assert vimeo_match is not None
    assert vimeo_match.name == "Vimeo"

def test_rate_limiter():
    test_ip = "192.168.1.99"
    for _ in range(RATE_LIMIT_REQUESTS):
        enforce_rate_limit(test_ip)

    # The (RATE_LIMIT_REQUESTS + 1)th request must trigger HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        enforce_rate_limit(test_ip)
    assert exc_info.value.status_code == 429
