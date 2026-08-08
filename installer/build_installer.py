import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DIST_DIR = ROOT_DIR / "dist"


def build_installer():
    """Packages installer scripts and binaries into release output."""
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    setup_dir = DIST_DIR / "YT-Downloader-Setup"
    setup_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build native agent if needed
    agent_exe = ROOT_DIR / "native-agent" / "dist" / "downloader-agent.exe"
    if not agent_exe.exists():
        print("Building native-agent binary first...")
        res = subprocess.run([sys.executable, str(ROOT_DIR / "native-agent" / "build.py")])
        if res.returncode != 0:
            print("Native agent build failed!")
            sys.exit(res.returncode)

    # 2. Copy binaries and installer scripts into setup output folder
    shutil.copy2(agent_exe, setup_dir / "downloader-agent.exe")
    shutil.copy2(BASE_DIR / "scripts" / "install.ps1", setup_dir / "install.ps1")
    shutil.copy2(BASE_DIR / "scripts" / "uninstall.ps1", setup_dir / "uninstall.ps1")
    shutil.copy2(BASE_DIR / "native-host" / "com.omikalix.ytdownloader.json", setup_dir / "com.omikalix.ytdownloader.json")

    # Create quick-launcher install batch file
    install_bat = setup_dir / "install.bat"
    with open(install_bat, "w") as f:
        f.write('@echo off\npowershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"\npause\n')

    print(f"[OK] Setup package created at: {setup_dir}")


if __name__ == "__main__":
    build_installer()
