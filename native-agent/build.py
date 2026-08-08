import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build_tmp"
BINARIES_DIR = BASE_DIR / "binaries"
PROJECT_BIN_DIR = BASE_DIR.parent / "bin"


def ensure_binaries():
    """Ensures yt-dlp.exe and ffmpeg.exe exist in native-agent/binaries."""
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    # Copy ffmpeg binaries from project root bin if available
    for binary_name in ["ffmpeg.exe", "ffprobe.exe"]:
        src = PROJECT_BIN_DIR / binary_name
        dest = BINARIES_DIR / binary_name
        if src.exists() and not dest.exists():
            shutil.copy2(src, dest)
            print(f"Copied {binary_name} from project bin to {dest}")


def build():
    """Builds downloader-agent.exe using PyInstaller."""
    ensure_binaries()

    main_script = SRC_DIR / "main.py"
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=downloader-agent",
        "--noconsole",
        "--clean",
        "--onefile",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--paths={SRC_DIR}",
        str(main_script),
    ]

    print("Building downloader-agent.exe with PyInstaller...")
    print("Executing command:", " ".join(cmd))

    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode == 0:
        print(f"Build succeeded! Binary output location: {DIST_DIR / 'downloader-agent.exe'}")
    else:
        print("Build failed with return code:", res.returncode)
        sys.exit(res.returncode)


if __name__ == "__main__":
    build()
