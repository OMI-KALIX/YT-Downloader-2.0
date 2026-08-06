import os
import time
import logging
import asyncio
from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

from backend.downloader.engine import get_video_formats
from backend.cookies.manager import temporary_cookie_file
from backend.jobs.manager import start_download_job, start_batch_job, start_mux_job, cancel_job, pause_job, resume_job
from backend.progress.tracker import progress_tracker

logger = logging.getLogger("yt_backend")
router = APIRouter(prefix="/api")

# Rate Limiter: In-memory sliding window per IP
_request_records: Dict[str, List[float]] = {}
_rate_limit_lock = asyncio.Lock()
RATE_LIMIT_REQUESTS = 40  # Max requests
RATE_LIMIT_WINDOW = 60    # Per 60 seconds

def enforce_rate_limit(client_ip: str):
    now = time.time()
    if client_ip not in _request_records:
        _request_records[client_ip] = []
    
    # Remove timestamps older than window
    _request_records[client_ip] = [
        ts for ts in _request_records[client_ip] if now - ts < RATE_LIMIT_WINDOW
    ]
    
    if len(_request_records[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait 60 seconds before making more requests."
        )
    
    _request_records[client_ip].append(now)

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    required_key = os.environ.get("ANYDOWNLOADER_API_KEY")
    if required_key and x_api_key != required_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

class FormatsRequest(BaseModel):
    url: str
    cookies: Optional[str] = None

class DownloadRequest(BaseModel):
    url: str
    format_id: str = "bestvideo+bestaudio/best"
    cookies: Optional[str] = None
    delay_seconds: int = 0

class BatchRequest(BaseModel):
    url: str
    format_id: str = "bestvideo+bestaudio/best"
    cookies: Optional[str] = None
    max_items: int = 25
    delay_seconds: int = 0

class MuxRequest(BaseModel):
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    title: Optional[str] = None
    format_id: Optional[str] = None

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "youtube-downloader-backend"}

@router.get("/metrics")
def get_metrics():
    all_jobs = list(progress_tracker._jobs.values())
    active_count = sum(1 for j in all_jobs if j.get("status") in ["pending", "downloading", "processing", "starting"])
    completed_count = sum(1 for j in all_jobs if j.get("status") == "completed")
    failed_count = sum(1 for j in all_jobs if j.get("status") == "failed")
    
    return {
        "active_jobs": active_count,
        "completed_jobs": completed_count,
        "failed_jobs": failed_count,
        "total_jobs_tracked": len(all_jobs)
    }

@router.post("/formats")
def fetch_formats(req: FormatsRequest, request: Request, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(client_ip)

    try:
        with temporary_cookie_file(req.cookies or "") as cookie_path:
            info = get_video_formats(req.url, cookie_path)
            return {"status": "success", "data": info}
    except Exception as e:
        logger.error(f"Error fetching formats: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/download")
def request_download(req: DownloadRequest, request: Request, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(client_ip)

    try:
        job_id = start_download_job(req.url, req.format_id, req.cookies, delay_seconds=req.delay_seconds)
        return {"status": "started", "job_id": job_id}
    except Exception as e:
        logger.error(f"Error starting download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch")
def request_batch_download(req: BatchRequest, request: Request, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(client_ip)

    try:
        parent_job_id = start_batch_job(req.url, req.format_id, req.cookies, max_items=req.max_items, delay_seconds=req.delay_seconds)
        return {"status": "started", "job_id": parent_job_id, "is_batch": True}
    except Exception as e:
        logger.error(f"Error starting batch download: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mux")
def request_mux_download(req: MuxRequest, request: Request, x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    client_ip = request.client.host if request.client else "unknown"
    enforce_rate_limit(client_ip)

    if not req.video_url and not req.audio_url:
        raise HTTPException(status_code=400, detail="At least one media stream URL (video_url or audio_url) must be provided.")

    try:
        job_id = start_mux_job(
            video_url=req.video_url,
            audio_url=req.audio_url,
            title=req.title,
            format_id=req.format_id
        )
        return {"status": "started", "job_id": job_id}
    except Exception as e:
        logger.error(f"Error initiating direct stream mux job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cancel/{job_id}")
def cancel_download_job(job_id: str):
    success = cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already ended")
    return {"status": "cancelled", "job_id": job_id}

@router.post("/pause/{job_id}")
def pause_download_job(job_id: str):
    success = pause_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already ended")
    return {"status": "paused", "job_id": job_id}

@router.post("/resume/{job_id}")
def resume_download_job(job_id: str):
    success = resume_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already ended")
    return {"status": "resumed", "job_id": job_id}

@router.get("/progress/{job_id}")
def check_progress(job_id: str):
    job = progress_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.websocket("/ws/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = progress_tracker.get_job(job_id)
    if not job:
        await websocket.send_json({"error": "Job not found", "status": "404"})
        await websocket.close(code=4004)
        return

    # Send current initial state
    await websocket.send_json(job)
    if job.get("status") in ["completed", "failed", "cancelled"]:
        await websocket.close()
        return

    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()

    def subscriber_callback(job_snapshot: dict):
        loop.call_soon_threadsafe(queue.put_nowait, job_snapshot)

    progress_tracker.subscribe(job_id, subscriber_callback)
    try:
        while True:
            try:
                job_data = await asyncio.wait_for(queue.get(), timeout=25.0)
                await websocket.send_json(job_data)
                if job_data.get("status") in ["completed", "failed", "cancelled"]:
                    break
            except asyncio.TimeoutError:
                await websocket.send_json({"ping": True})
    except (WebSocketDisconnect, Exception) as e:
        logger.info(f"WebSocket client disconnected for job {job_id}: {e}")
    finally:
        progress_tracker.unsubscribe(job_id, subscriber_callback)
        try:
            await websocket.close()
        except Exception:
            pass

def cleanup_file_delayed(file_path: str, job_id: str, delay_seconds: int = 300):
    import threading
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
