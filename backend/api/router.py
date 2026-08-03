import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

from backend.downloader.engine import get_video_formats
from backend.cookies.manager import temporary_cookie_file
from backend.jobs.manager import start_download_job
from backend.progress.tracker import progress_tracker

logger = logging.getLogger("yt_backend")
router = APIRouter(prefix="/api")

class FormatsRequest(BaseModel):
    url: str
    cookies: Optional[str] = None

class DownloadRequest(BaseModel):
    url: str
    format_id: str = "bestvideo+bestaudio/best"
    cookies: Optional[str] = None

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "youtube-downloader-backend"}

@router.post("/formats")
def fetch_formats(req: FormatsRequest):
    try:
        with temporary_cookie_file(req.cookies or "") as cookie_path:
            info = get_video_formats(req.url, cookie_path)
            return {"status": "success", "data": info}
    except Exception as e:
        logger.error(f"Error fetching formats: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/download")
def request_download(req: DownloadRequest):
    try:
        job_id = start_download_job(req.url, req.format_id, req.cookies)
        return {"status": "started", "job_id": job_id}
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/progress/{job_id}")
def check_progress(job_id: str):
    job = progress_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

def cleanup_file_delayed(file_path: str, job_id: str, delay_seconds: int = 300):
    import time
    def _delayed_task():
        time.sleep(delay_seconds)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                parent_dir = os.path.dirname(file_path)
                if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
                logger.info(f"Cleaned up completed download file for job {job_id}")
            progress_tracker.remove_job(job_id)
        except Exception as e:
            logger.error(f"Failed cleaning file {file_path}: {e}")

    import threading
    t = threading.Thread(target=_delayed_task, daemon=True)
    t.start()

@router.get("/file/{job_id}")
def retrieve_file(job_id: str, background_tasks: BackgroundTasks):
    job = progress_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Job is not completed yet. Current status: {job.get('status')}")
    
    file_path = job.get("file_path")
    filename = job.get("filename", "downloaded_media")
    
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested file no longer exists on server")

    # Schedule cleanup after 5 minutes to support resumed/range downloads
    cleanup_file_delayed(file_path, job_id, delay_seconds=300)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
