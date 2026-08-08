import threading
from typing import Dict, Optional, List
from .models import DownloadJob, JobState


class JobManager:
    """Thread-safe manager for download jobs."""

    def __init__(self):
        self._jobs: Dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def create_job(self, job_id: str, url: str, format_id: str) -> DownloadJob:
        with self._lock:
            job = DownloadJob(job_id=job_id, url=url, format_id=format_id)
            self._jobs[job_id] = job
            return job

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_state(self, job_id: str, state: JobState, error_message: Optional[str] = None) -> Optional[DownloadJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.state = state
                if error_message:
                    job.error_message = error_message
            return job

    def update_progress(self, job_id: str, percent: float, speed: str = "", eta: str = "", downloaded_bytes: int = 0, total_bytes: int = 0) -> Optional[DownloadJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress.percent = percent
                if speed:
                    job.progress.speed = speed
                if eta:
                    job.progress.eta = eta
                if downloaded_bytes:
                    job.progress.downloaded_bytes = downloaded_bytes
                if total_bytes:
                    job.progress.total_bytes = total_bytes
            return job

    def set_filename(self, job_id: str, filename: str) -> Optional[DownloadJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.filename = filename
            return job

    def list_jobs(self) -> List[DownloadJob]:
        with self._lock:
            return list(self._jobs.values())
