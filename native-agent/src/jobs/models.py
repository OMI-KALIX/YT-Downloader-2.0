from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional
import time


class JobState(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    EXTRACTING = "EXTRACTING"
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


@dataclass
class DownloadProgress:
    percent: float = 0.0
    speed: str = "0B/s"
    eta: str = "--:--"
    downloaded_bytes: int = 0
    total_bytes: int = 0


@dataclass
class DownloadJob:
    job_id: str
    url: str
    format_id: str
    state: JobState = JobState.STARTING
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    filename: Optional[str] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "url": self.url,
            "format_id": self.format_id,
            "state": self.state.value,
            "filename": self.filename,
            "error_message": self.error_message,
            "progress": {
                "percent": round(self.progress.percent, 1),
                "speed": self.progress.speed,
                "eta": self.progress.eta,
                "downloaded_bytes": self.progress.downloaded_bytes,
                "total_bytes": self.progress.total_bytes,
            },
        }
