import hashlib
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import requests
from system.paths import get_app_dir

AGENT_VERSION = "2.1.0"


class AgentUpdater:
    """Agent auto-update verification and updater module."""

    def __init__(self, cloud_url: str = "http://localhost:8000"):
        self.cloud_url = cloud_url.rstrip("/")
        self.current_version = AGENT_VERSION

    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """Queries cloud control endpoint for latest release version."""
        try:
            res = requests.get(f"{self.cloud_url}/agent/latest", timeout=5)
            if res.status_code == 200:
                data = res.json()
                latest_ver = data.get("version")
                if latest_ver and latest_ver != self.current_version:
                    return data
        except Exception:
            pass
        return None

    def verify_sha256(self, file_path: Path, expected_hash: str) -> bool:
        """Calculates SHA-256 hash of a downloaded file and compares against expected hash."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest().lower() == expected_hash.lower()
        except Exception:
            return False

    def download_and_verify(self, download_url: str, expected_sha256: str) -> Optional[Path]:
        """Downloads updated binary to a temp file and verifies its checksum."""
        try:
            res = requests.get(download_url, stream=True, timeout=30)
            if res.status_code == 200:
                temp_file = get_app_dir() / "downloader-agent-update.tmp"
                with open(temp_file, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                if self.verify_sha256(temp_file, expected_sha256):
                    return temp_file
                else:
                    if temp_file.exists():
                        temp_file.unlink()
        except Exception:
            pass
        return None
