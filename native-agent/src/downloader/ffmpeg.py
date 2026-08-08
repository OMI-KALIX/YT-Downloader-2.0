import subprocess
from pathlib import Path
from typing import List, Optional
from system.paths import get_binary_path


class FFmpegRunner:
    """Wrapper for invoking FFmpeg subprocess directly with argument arrays."""

    def __init__(self, binary_path: Optional[Path] = None):
        self.binary_path = binary_path or get_binary_path("ffmpeg.exe")

    def is_available(self) -> bool:
        try:
            res = subprocess.run(
                [str(self.binary_path), "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if subprocess.os.name == "nt" else 0,
            )
            return res.returncode == 0
        except Exception:
            return False

    def convert_audio(self, input_file: Path, output_file: Path, bitrate: str = "320k") -> bool:
        cmd = [
            str(self.binary_path),
            "-y",
            "-i", str(input_file),
            "-vn",
            "-ar", "44100",
            "-ac", "2",
            "-b:a", bitrate,
            str(output_file),
        ]
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if subprocess.os.name == "nt" else 0,
            )
            return res.returncode == 0
        except Exception:
            return False
