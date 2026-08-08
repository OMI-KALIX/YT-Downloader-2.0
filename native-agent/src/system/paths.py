import os
import re
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Returns the base directory of the running binary or script."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


def get_default_downloads_dir() -> Path:
    """Returns the user's default Downloads directory (%USERPROFILE%\\Downloads)."""
    user_home = Path.home()
    downloads_path = user_home / "Downloads"
    downloads_path.mkdir(parents=True, exist_ok=True)
    return downloads_path


def get_binary_path(binary_name: str) -> Path:
    """Locates a required binary (e.g. yt-dlp.exe, ffmpeg.exe).
    Searches in bundled binaries dir, app dir, workspace bin dir, or system PATH.
    """
    if not binary_name.endswith(".exe") and sys.platform == "win32":
        binary_name += ".exe"

    app_dir = get_app_dir()
    search_locations = [
        app_dir / "binaries" / binary_name,
        app_dir / "bin" / binary_name,
        app_dir / binary_name,
        Path(__file__).resolve().parent.parent.parent.parent / "bin" / binary_name,
    ]

    for path in search_locations:
        if path.exists() and path.is_file():
            return path.resolve()

    import shutil
    system_path = shutil.which(binary_name)
    if system_path:
        return Path(system_path)

    return search_locations[0]


def sanitize_filename(filename: str) -> str:
    """Sanitizes a string to be a safe filename."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "_", filename)
    cleaned = cleaned.strip(". ")
    return cleaned or "downloaded_video"


def is_safe_target_directory(target_path: Path) -> bool:
    """Verifies target path resides within an allowed download location."""
    downloads_dir = get_default_downloads_dir().resolve()
    try:
        resolved_target = target_path.resolve()
        return downloads_dir in resolved_target.parents or resolved_target == downloads_dir
    except Exception:
        return False
