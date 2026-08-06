import os
import uuid
import time
import tempfile
import threading
import logging
from typing import Optional, List, Dict, Any

from backend.cookies.manager import temporary_cookie_file
from backend.downloader.engine import download_media, extract_playlist_items, cleanup_expired_partials
from backend.progress.tracker import progress_tracker

logger = logging.getLogger("yt_backend")

# Active cancellation and pause sets
_cancelled_jobs = set()
_cancelled_lock = threading.Lock()

_paused_jobs = set()
_paused_lock = threading.Lock()

def cancel_job(job_id: str) -> bool:
    with _cancelled_lock:
        _cancelled_jobs.add(job_id)
    with _paused_lock:
        _paused_jobs.discard(job_id)
    job = progress_tracker.get_job(job_id)
    if job:
        progress_tracker.update_job(job_id, {"status": "cancelled", "speed": "Cancelled", "error": "User cancelled download"})
        return True
    return False

def is_cancelled(job_id: str) -> bool:
    with _cancelled_lock:
        return job_id in _cancelled_jobs

def pause_job(job_id: str) -> bool:
    with _paused_lock:
        _paused_jobs.add(job_id)
    job = progress_tracker.get_job(job_id)
    if job:
        progress_tracker.update_job(job_id, {"status": "paused", "speed": "Paused", "eta": "--:--"})
        return True
    return False

def resume_job(job_id: str) -> bool:
    with _paused_lock:
        _paused_jobs.discard(job_id)
    job = progress_tracker.get_job(job_id)
    if job:
        progress_tracker.update_job(job_id, {"status": "downloading", "speed": "Resuming..."})
        return True
    return False

def is_paused(job_id: str) -> bool:
    with _paused_lock:
        return job_id in _paused_jobs

def process_download_job(job_id: str, url: str, format_id: str, cookie_content: Optional[str] = None, delay_seconds: int = 0):
    """
    Executes a download job in a background worker thread.
    Guarantees cookie file cleanup immediately upon completion.
    Supports scheduled delayed execution and user cancellation.
    """
    if delay_seconds > 0:
        progress_tracker.update_job(job_id, {"status": "scheduled", "eta": f"Starts in {delay_seconds}s"})
        elapsed = 0
        while elapsed < delay_seconds:
            if is_cancelled(job_id):
                return
            time.sleep(1)
            elapsed += 1

    if is_cancelled(job_id):
        return

    download_dir = tempfile.mkdtemp(prefix="yt_dl_")
    
    try:
        progress_tracker.update_job(job_id, {"status": "starting"})
        
        with temporary_cookie_file(cookie_content or "") as cookie_path:
            file_path = download_media(job_id, url, format_id, download_dir, cookie_path)
            
            if is_cancelled(job_id):
                return

            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                progress_tracker.update_job(job_id, {
                    "status": "completed",
                    "percent": 100.0,
                    "filename": filename,
                    "file_path": file_path,
                    "error": None
                })
                logger.info(f"Job {job_id} successfully completed: {file_path}")
            else:
                raise FileNotFoundError(f"Downloaded file not found at {file_path}")

    except Exception as e:
        if not is_cancelled(job_id):
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            progress_tracker.update_job(job_id, {
                "status": "failed",
                "error": str(e)
            })

def start_download_job(url: str, format_id: str, cookie_content: Optional[str] = None, delay_seconds: int = 0) -> str:
    """
    Generates job ID, creates job state in tracker, and launches worker thread.
    """
    job_id = str(uuid.uuid4())
    progress_tracker.create_job(job_id, url)
    
    thread = threading.Thread(
        target=process_download_job,
        args=(job_id, url, format_id, cookie_content, delay_seconds),
        daemon=True
    )
    thread.start()
    
    return job_id

def process_batch_job(parent_job_id: str, url: str, format_id: str, cookie_content: Optional[str] = None, max_items: int = 25, delay_seconds: int = 0):
    """
    Processes playlist / batch downloads by resolving individual video items and tracking sub-jobs.
    """
    if delay_seconds > 0:
        progress_tracker.update_job(parent_job_id, {"status": "scheduled", "eta": f"Starts in {delay_seconds}s"})
        elapsed = 0
        while elapsed < delay_seconds:
            if is_cancelled(parent_job_id):
                return
            time.sleep(1)
            elapsed += 1

    progress_tracker.update_job(parent_job_id, {"status": "starting", "percent": 0.0})
    
    with temporary_cookie_file(cookie_content or "") as cookie_path:
        items = extract_playlist_items(url, cookie_path, max_items=max_items)
        
    sub_job_ids = []
    for item in items:
        sub_id = str(uuid.uuid4())
        progress_tracker.create_job(sub_id, item["url"], parent_job_id=parent_job_id)
        progress_tracker.update_job(sub_id, {"filename": item["title"]})
        sub_job_ids.append(sub_id)

    progress_tracker.update_job(parent_job_id, {
        "status": "downloading",
        "is_batch": True,
        "total_items": len(sub_job_ids),
        "completed_items": 0,
        "sub_jobs": sub_job_ids
    })

    completed_count = 0
    for idx, sub_id in enumerate(sub_job_ids):
        if is_cancelled(parent_job_id) or is_cancelled(sub_id):
            progress_tracker.update_job(sub_id, {"status": "cancelled"})
            continue

        item_info = items[idx]
        process_download_job(sub_id, item_info["url"], format_id, cookie_content, delay_seconds=0)
        
        sub_status = progress_tracker.get_job(sub_id)
        if sub_status and sub_status.get("status") == "completed":
            completed_count += 1

        overall_percent = round((idx + 1) / len(sub_job_ids) * 100, 1)
        progress_tracker.update_job(parent_job_id, {
            "percent": overall_percent,
            "completed_items": completed_count
        })

    progress_tracker.update_job(parent_job_id, {
        "status": "completed",
        "percent": 100.0,
        "completed_items": completed_count
    })

def start_batch_job(url: str, format_id: str, cookie_content: Optional[str] = None, max_items: int = 25, delay_seconds: int = 0) -> str:
    parent_job_id = str(uuid.uuid4())
    progress_tracker.create_job(parent_job_id, url)
    progress_tracker.update_job(parent_job_id, {"is_batch": True})
    
    thread = threading.Thread(
        target=process_batch_job,
        args=(parent_job_id, url, format_id, cookie_content, max_items, delay_seconds),
        daemon=True
    )
    thread.start()
    
    return parent_job_id

# Background retention cleanup thread sweep
def _start_retention_cleanup_sweep():
    def _sweep_loop():
        while True:
            time.sleep(1800)  # Run every 30 minutes
            cleanup_expired_partials(retention_seconds=3600)
    
    t = threading.Thread(target=_sweep_loop, daemon=True)
    t.start()

_start_retention_cleanup_sweep()
