import os
import uuid
import tempfile
import threading
import logging
from typing import Optional

from backend.cookies.manager import temporary_cookie_file
from backend.downloader.engine import download_media
from backend.progress.tracker import progress_tracker

logger = logging.getLogger("yt_backend")

def process_download_job(job_id: str, url: str, format_id: str, cookie_content: Optional[str] = None):
    """
    Executes a download job in a background worker thread.
    Guarantees cookie file cleanup immediately upon completion.
    """
    download_dir = tempfile.mkdtemp(prefix="yt_dl_")
    
    try:
        progress_tracker.update_job(job_id, {"status": "starting"})
        
        with temporary_cookie_file(cookie_content or "") as cookie_path:
            file_path = download_media(job_id, url, format_id, download_dir, cookie_path)
            
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
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        progress_tracker.update_job(job_id, {
            "status": "failed",
            "error": str(e)
        })

def start_download_job(url: str, format_id: str, cookie_content: Optional[str] = None) -> str:
    """
    Generates job ID, creates job state in tracker, and launches worker thread.
    """
    job_id = str(uuid.uuid4())
    progress_tracker.create_job(job_id, url)
    
    thread = threading.Thread(
        target=process_download_job,
        args=(job_id, url, format_id, cookie_content),
        daemon=True
    )
    thread.start()
    
    return job_id
