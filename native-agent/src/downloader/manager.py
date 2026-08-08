import threading
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from downloader.ytdlp import YtDlpRunner
from jobs.manager import JobManager
from jobs.models import JobState
from system.paths import get_default_downloads_dir


class DownloadEngineManager:
    """High-level download manager driving yt-dlp & job tracking."""

    def __init__(self, job_manager: JobManager):
        self.job_manager = job_manager
        self.runner = YtDlpRunner()

    def get_formats(self, url: str) -> Dict[str, Any]:
        """Synchronously extracts metadata & formats using yt-dlp."""
        return self.runner.get_formats(url)

    def cancel_job(self, job_id: str) -> bool:
        """Cancels an active download job."""
        self.job_manager.update_state(job_id, JobState.CANCELLED)
        return self.runner.cancel_download(job_id)

    def start_download(
        self,
        job_id: str,
        url: str,
        format_selection: str,
        event_callback: Callable[[Dict[str, Any]], None],
        output_dir: Optional[Path] = None,
    ):
        """Starts an asynchronous download task in a background worker thread."""
        job = self.job_manager.create_job(job_id, url, format_selection)

        def worker():
            try:
                self.job_manager.update_state(job_id, JobState.DOWNLOADING)
                
                # Emit instant initial progress reflection event
                event_callback({
                    "id": job_id,
                    "event": "progress",
                    "payload": {
                        "job_id": job_id,
                        "percent": 1.0,
                        "speed": "Connecting...",
                        "eta": "Calculating...",
                        "state": "CONNECTING TO YOUTUBE",
                    },
                })

                def on_progress(pct: float, speed: str, eta: str, status_tag: str = "DOWNLOADING"):
                    self.job_manager.update_progress(job_id, pct, speed, eta)
                    event_callback({
                        "id": job_id,
                        "event": "progress",
                        "payload": {
                            "job_id": job_id,
                            "percent": pct,
                            "speed": speed,
                            "eta": eta,
                            "state": status_tag,
                        },
                    })

                output_path = self.runner.download(
                    url=url,
                    format_selection=format_selection,
                    job_id=job_id,
                    output_dir=output_dir or get_default_downloads_dir(),
                    progress_callback=on_progress,
                )

                cur_job = self.job_manager.get_job(job_id)
                if cur_job and cur_job.state == JobState.CANCELLED:
                    event_callback({
                        "id": job_id,
                        "event": "cancelled",
                        "payload": {
                            "job_id": job_id,
                            "state": JobState.CANCELLED.value,
                        },
                    })
                    return

                self.job_manager.set_filename(job_id, output_path.name)
                self.job_manager.update_state(job_id, JobState.COMPLETED)

                event_callback({
                    "id": job_id,
                    "event": "completed",
                    "payload": {
                        "job_id": job_id,
                        "filename": output_path.name,
                        "filepath": str(output_path),
                        "state": JobState.COMPLETED.value,
                    },
                })

            except Exception as e:
                cur_job = self.job_manager.get_job(job_id)
                if cur_job and cur_job.state == JobState.CANCELLED:
                    event_callback({
                        "id": job_id,
                        "event": "cancelled",
                        "payload": {
                            "job_id": job_id,
                            "state": JobState.CANCELLED.value,
                        },
                    })
                    return

                err_msg = str(e)
                self.job_manager.update_state(job_id, JobState.ERROR, error_message=err_msg)
                event_callback({
                    "id": job_id,
                    "event": "error",
                    "payload": {
                        "job_id": job_id,
                        "code": "DOWNLOAD_FAILED",
                        "message": err_msg,
                        "state": JobState.ERROR.value,
                    },
                })

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
