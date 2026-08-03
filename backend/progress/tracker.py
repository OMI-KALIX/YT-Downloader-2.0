import time
from typing import Dict, Any, Optional
import threading

class ProgressTracker:
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_job(self, job_id: str, url: str) -> None:
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "url": url,
                "status": "pending",  # pending, downloading, processing, completed, failed
                "percent": 0.0,
                "speed": "0 KiB/s",
                "eta": "--:--",
                "filename": "",
                "file_path": "",
                "error": None,
                "updated_at": time.time()
            }

    def update_job(self, job_id: str, data: Dict[str, Any]) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(data)
                self._jobs[job_id]["updated_at"] = time.time()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id, None)

progress_tracker = ProgressTracker()
