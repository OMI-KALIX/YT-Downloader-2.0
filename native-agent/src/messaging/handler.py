import re
from typing import Dict, Any, Callable, Optional
from downloader.manager import DownloadEngineManager
from jobs.manager import JobManager
from updater.updater import AGENT_VERSION


class NativeMessageHandler:
    """Message handler & request validator for browser extension messages."""

    def __init__(self, job_manager: JobManager, event_callback: Callable[[Dict[str, Any]], None]):
        self.job_manager = job_manager
        self.event_callback = event_callback
        self.engine = DownloadEngineManager(job_manager)

    def handle_message(self, message: Dict[str, Any]):
        req_id = message.get("id") or "req_default"
        action = message.get("action")
        payload = message.get("payload") or message

        if not action:
            self._send_error(req_id, "INVALID_REQUEST", "Action name is required.")
            return

        try:
            if action == "ping":
                self.event_callback({
                    "id": req_id,
                    "event": "pong",
                    "payload": {"version": AGENT_VERSION, "status": "ready"},
                })

            elif action == "status":
                # Instant non-blocking check for binary existence
                ytdlp_available = self.engine.runner.binary_path.exists()
                ffmpeg_available = self.engine.runner.ffmpeg_path.exists()
                self.event_callback({
                    "id": req_id,
                    "event": "status",
                    "payload": {
                        "status": "ready",
                        "version": AGENT_VERSION,
                        "ytdlp": ytdlp_available,
                        "ffmpeg": ffmpeg_available,
                    },
                })

            elif action == "get_metadata":
                url = payload.get("url")
                if not self._validate_url(url):
                    self._send_error(req_id, "INVALID_URL", "A valid HTTP/HTTPS video URL is required.")
                    return
                
                res = self.engine.get_formats(url)
                self.event_callback({
                    "id": req_id,
                    "event": "metadata",
                    "payload": {
                        "id": res.get("id", ""),
                        "title": res.get("title", ""),
                        "uploader": res.get("uploader", ""),
                        "thumbnail": res.get("thumbnail", ""),
                        "duration": res.get("duration", 0),
                    },
                })

            elif action == "get_formats":
                url = payload.get("url")
                if not self._validate_url(url):
                    self._send_error(req_id, "INVALID_URL", "A valid HTTP/HTTPS video URL is required.")
                    return
                
                res = self.engine.get_formats(url)
                self.event_callback({
                    "id": req_id,
                    "event": "formats",
                    "payload": res,
                })

            elif action == "download":
                url = payload.get("url")
                format_sel = payload.get("format") or "1080p"

                if not self._validate_url(url):
                    self._send_error(req_id, "INVALID_URL", "A valid HTTP/HTTPS video URL is required.")
                    return

                # Send immediate confirmation payload
                self.event_callback({
                    "id": req_id,
                    "event": "download_started",
                    "payload": {"job_id": req_id, "status": "started"},
                })

                self.engine.start_download(
                    job_id=req_id,
                    url=url,
                    format_selection=format_sel,
                    event_callback=self.event_callback,
                )

            elif action == "cancel":
                job_id = payload.get("job_id") or req_id
                success = self.engine.cancel_job(job_id)
                self.event_callback({
                    "id": req_id,
                    "event": "cancelled",
                    "payload": {"job_id": job_id, "success": success},
                })

            else:
                self._send_error(req_id, "UNKNOWN_ACTION", f"Action '{action}' is not supported.")

        except Exception as e:
            self._send_error(req_id, "EXTRACTION_FAILED", str(e))

    def _validate_url(self, url: Optional[str]) -> bool:
        if not url or not isinstance(url, str):
            return False
        if not (url.startswith("http://") or url.startswith("https://")):
            return False
        if url.strip().startswith("-"):
            return False
        return True

    def _send_error(self, req_id: str, code: str, message: str):
        self.event_callback({
            "id": req_id,
            "event": "error",
            "payload": {
                "code": code,
                "message": message,
            },
        })
