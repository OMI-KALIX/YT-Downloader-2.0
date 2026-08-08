import json
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from system.paths import get_binary_path, get_default_downloads_dir
from downloader.formats import parse_yt_dlp_metadata


class YtDlpRunner:
    """Wrapper for executing yt-dlp.exe in a safe, windowless subprocess with high-speed 100ms progress streaming."""

    def __init__(self, binary_path: Optional[Path] = None, ffmpeg_path: Optional[Path] = None):
        self.binary_path = binary_path or get_binary_path("yt-dlp.exe")
        self.ffmpeg_path = ffmpeg_path or get_binary_path("ffmpeg.exe")
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            res = subprocess.run(
                [str(self.binary_path), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            return res.returncode == 0
        except Exception:
            return False

    def get_formats(self, url: str) -> Dict[str, Any]:
        """Fetches video metadata & available formats for a video or playlist URL."""
        cmd = [
            str(self.binary_path),
            "--dump-json",
            "--no-warnings",
            "--no-playlist",
            url,
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"yt-dlp extraction failed: {stderr.strip()}")

        data = json.loads(stdout)
        return parse_yt_dlp_metadata(data)

    def cancel_download(self, job_id: str) -> bool:
        """Terminates an active download process for a given job_id."""
        with self._lock:
            proc = self.active_processes.get(job_id)
            if proc:
                try:
                    proc.terminate()
                    proc.kill()
                except Exception:
                    pass
                del self.active_processes[job_id]
                return True
        return False

    def download(
        self,
        url: str,
        format_selection: str,
        job_id: str = "default_job",
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[float, str, str, str], None]] = None,
    ) -> Path:
        """Executes a high-speed multi-threaded video or audio download using yt-dlp with 100ms real-time progress streaming."""
        out_dir = output_dir or get_default_downloads_dir()
        out_template = str(out_dir / "%(title)s [%(id)s].%(ext)s")

        if progress_callback:
            progress_callback(2.0, "Initializing Engine", "Calculating...", "FETCHING FRAGMENTS")

        # High-performance parallel download flags with 100ms progress delta
        cmd = [
            str(self.binary_path),
            "--newline",
            "--no-playlist",
            "--no-mtime",
            "--progress-delta", "0.1",
            "--concurrent-fragments", "16",
            "--buffer-size", "16M",
            "--http-chunk-size", "10M",
            "--progress-template",
            "%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
            "-o", out_template,
        ]

        if self.ffmpeg_path.exists():
            cmd.extend(["--ffmpeg-location", str(self.ffmpeg_path.parent)])

        # Handle format selection accurately without duplicate format flags
        if format_selection in ["audio_320k", "bestaudio"] or format_selection.endswith("mp3"):
            cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "0"])
        elif format_selection == "audio_192k":
            cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "2"])
        elif format_selection == "audio_128k":
            cmd.extend(["-x", "--audio-format", "mp3", "--audio-quality", "5"])
        elif format_selection:
            if "bestvideo" in format_selection or "+" in format_selection:
                cmd.extend(["-f", format_selection, "--merge-output-format", "mp4"])
            elif format_selection.endswith("p") and format_selection[:-1].isdigit():
                h = format_selection[:-1]
                cmd.extend(["-f", f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best", "--merge-output-format", "mp4"])
            else:
                cmd.extend(["-f", f"{format_selection}+bestaudio/best", "--merge-output-format", "mp4"])
        else:
            cmd.extend(["-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"])

        cmd.append(url)

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered stdout for 0ms latency streaming
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )

        with self._lock:
            self.active_processes[job_id] = process

        last_filename = None
        max_pct = 2.0
        current_stream = 1  # 1 = Video, 2 = Audio

        try:
            if process.stdout:
                for line in process.stdout:
                    line_str = line.strip()
                    if not line_str:
                        continue

                    if "[download] Destination:" in line_str:
                        dest = line_str.replace("[download] Destination:", "").strip()
                        last_filename = dest
                        if ".f" in dest and current_stream == 1 and max_pct > 20:
                            current_stream = 2
                    elif "[Merger] Merging formats into" in line_str:
                        last_filename = line_str.replace("[Merger] Merging formats into", "").replace('"', "").strip()
                        if progress_callback:
                            progress_callback(96.0, "Muxing", "00:02", "PROCESSING")
                    elif "[ExtractAudio] Destination:" in line_str:
                        last_filename = line_str.replace("[ExtractAudio] Destination:", "").strip()
                        if progress_callback:
                            progress_callback(96.0, "Audio Mux", "00:02", "PROCESSING")

                    if "|" in line_str:
                        parts = line_str.split("|")
                        if len(parts) >= 3:
                            percent_str, speed_str, eta_str = parts[0], parts[1], parts[2]
                            clean_percent = re.sub(r"[^\d.]", "", percent_str)
                            try:
                                raw_pct = float(clean_percent)

                                if current_stream == 1:
                                    computed_pct = max(2.0, min(85.0, raw_pct * 0.85))
                                else:
                                    computed_pct = min(95.0, 85.0 + (raw_pct * 0.10))

                                if computed_pct > max_pct:
                                    max_pct = computed_pct

                                status_tag = "DOWNLOADING"
                                if current_stream == 2:
                                    status_tag = "AUDIO STREAM"

                                if progress_callback:
                                    progress_callback(round(max_pct, 1), speed_str.strip(), eta_str.strip(), status_tag)
                            except ValueError:
                                pass

            stdout, stderr = process.communicate()
        finally:
            with self._lock:
                if job_id in self.active_processes:
                    del self.active_processes[job_id]

        if process.returncode != 0 and process.returncode != -15 and process.returncode != 1:
            raise RuntimeError(f"Download process ended: {stderr.strip()}")

        if last_filename:
            return Path(last_filename)
        return out_dir
