import time
import asyncio
import logging
from typing import Dict, Any, Optional, Set, Callable
import threading

logger = logging.getLogger("yt_backend")

class ProgressTracker:
    def __init__(self, ttl_seconds: int = 3600):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._subscribers: Dict[str, Set[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds

    def _cleanup_stale_jobs(self):
        """Purge jobs older than TTL seconds to prevent RAM growth on free tier."""
        now = time.time()
        stale_ids = [
            jid for jid, job in self._jobs.items()
            if now - job.get("updated_at", now) > self._ttl_seconds
        ]
        for jid in stale_ids:
            self._jobs.pop(jid, None)
            self._subscribers.pop(jid, None)
            logger.info(f"Purged stale job {jid} from memory tracker (TTL expired)")

    def create_job(self, job_id: str, url: str, parent_job_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            self._cleanup_stale_jobs()
            job_data = {
                "job_id": job_id,
                "parent_job_id": parent_job_id,
                "url": url,
                "status": "pending",  # pending, downloading, processing, completed, failed, cancelled
                "percent": 0.0,
                "speed": "0 KiB/s",
                "eta": "--:--",
                "filename": "",
                "file_path": "",
                "error": None,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            self._jobs[job_id] = job_data
            return dict(job_data)

    def update_job(self, job_id: str, data: Dict[str, Any]) -> None:
        callbacks_to_notify = []
        job_snapshot = None
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(data)
                self._jobs[job_id]["updated_at"] = time.time()
                job_snapshot = dict(self._jobs[job_id])
                if job_id in self._subscribers:
                    callbacks_to_notify = list(self._subscribers[job_id])

        if job_snapshot and callbacks_to_notify:
            for cb in callbacks_to_notify:
                try:
                    cb(job_snapshot)
                except Exception as e:
                    logger.warning(f"Error notifying subscriber for job {job_id}: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def subscribe(self, job_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = set()
            self._subscribers[job_id].add(callback)

    def unsubscribe(self, job_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        with self._lock:
            if job_id in self._subscribers:
                self._subscribers[job_id].discard(callback)
                if not self._subscribers[job_id]:
                    self._subscribers.pop(job_id, None)

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)
            self._subscribers.pop(job_id, None)

progress_tracker = ProgressTracker()

