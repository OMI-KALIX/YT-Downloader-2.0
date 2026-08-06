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

def test_pause_resume_cancel_endpoints():
    from backend.jobs.manager import is_paused, is_cancelled
    from backend.progress.tracker import progress_tracker

    job_id = "test-job-control-123"
    progress_tracker.create_job(job_id, "https://youtube.com/watch?v=abc")

    # Test Pause endpoint
    res_pause = client.post(f"/api/pause/{job_id}")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "paused"
    assert is_paused(job_id) is True

    # Test Resume endpoint
    res_resume = client.post(f"/api/resume/{job_id}")
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "resumed"
    assert is_paused(job_id) is False

    # Test Cancel endpoint
    res_cancel = client.post(f"/api/cancel/{job_id}")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "cancelled"
    assert is_cancelled(job_id) is True

def test_cookie_diagnostics_and_bot_check_mapping():
    from backend.progress.tracker import progress_tracker
    from backend.jobs.manager import start_download_job
    from backend.downloader.engine import is_bot_check_error, get_env_ydl_opts, BotCheckError

    # Test cookie diagnostics boolean flag
    job_id_no_cookies = start_download_job("https://youtube.com/watch?v=dQw4w9WgXcQ", "audio_128k", cookie_content="")
    job_no_cookies = progress_tracker.get_job(job_id_no_cookies)
    assert job_no_cookies["cookies_supplied"] is False

    job_id_with_cookies = start_download_job("https://youtube.com/watch?v=dQw4w9WgXcQ", "audio_128k", cookie_content="dummy_cookie_val")
    job_with_cookies = progress_tracker.get_job(job_id_with_cookies)
    assert job_with_cookies["cookies_supplied"] is True

    # Test is_bot_check_error helper
    err1 = Exception("yt_dlp.utils.ExtractorError: [youtube] Sign in to confirm you're not a bot.")
    assert is_bot_check_error(err1) is True
    err2 = Exception("yt_dlp.utils.ExtractorError: [youtube] Sign in to confirm you’re not a bot.")
    assert is_bot_check_error(err2) is True
    err3 = Exception("Video unavailable")
    assert is_bot_check_error(err3) is False

    # Test get_env_ydl_opts parsing
    os.environ["YTDLP_SLEEP_REQUESTS"] = "1.5"
    os.environ["YTDLP_PROXY"] = "http://127.0.0.1:8080"
    opts = get_env_ydl_opts()
    assert opts.get("sleep_requests") == 1.5
    assert opts.get("proxy") == "http://127.0.0.1:8080"
    os.environ.pop("YTDLP_SLEEP_REQUESTS", None)
    os.environ.pop("YTDLP_PROXY", None)

def test_resolve_format_spec_and_format_error():
    from backend.downloader.engine import resolve_format_spec, is_format_not_available_error, FormatNotAvailableError

    # Test audio resolution mapping
    spec1, is_aud1, br1 = resolve_format_spec("audio_128k")
    assert "bestaudio[abr<=128]" in spec1
    assert is_aud1 is True
    assert br1 == "128"

    spec2, is_aud2, br2 = resolve_format_spec("audio_320k")
    assert "bestaudio[abr<=320]" in spec2
    assert is_aud2 is True
    assert br2 == "320"

    # Test video resolution mapping
    spec3, is_aud3, _ = resolve_format_spec("bestvideo[height<=1080]+bestaudio/best")
    assert "bestvideo[height<=1080]" in spec3
    assert is_aud3 is False

    # Test itag mapping
    spec4, is_aud4, _ = resolve_format_spec("137+140")
    assert "137+140" in spec4
    assert is_aud4 is False

    # Test format error checker
    err = Exception("yt_dlp.utils.ExtractorError: [youtube] Requested format is not available. Use --list-formats for a list")
    assert is_format_not_available_error(err) is True

def test_js_runtimes_deno_config():
    import yt_dlp
    opts = {"quiet": True, "js_runtimes": {"deno": {}, "node": {}}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        assert "deno" in opts["js_runtimes"]
        assert "node" in opts["js_runtimes"]
