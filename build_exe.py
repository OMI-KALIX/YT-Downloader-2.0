import os
import sys
import shutil
import zipfile
import urllib.request
import subprocess

# Force UTF-8 encoding for Windows console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
BIN_DIR = os.path.join(PROJECT_DIR, "bin")
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def kill_existing_processes():
    """Terminates any active instances of Downloader_Standalone.exe or Downloader.exe locking output files."""
    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/F", "/IM", "Downloader_Standalone.exe", "/IM", "Downloader.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def ensure_dependencies():
    """Installs PyInstaller, pystray, and Pillow if not already present."""
    kill_existing_processes()
    required = ["pyinstaller", "pystray", "Pillow"]
    for pkg in required:
        try:
            __import__(pkg if pkg != "Pillow" else "PIL")
        except ImportError:
            print(f"📦 Installing missing dependency: {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


def ensure_ffmpeg_binaries():
    """Ensures bin/ffmpeg.exe and bin/ffprobe.exe exist."""
    os.makedirs(BIN_DIR, exist_ok=True)
    ffmpeg_exe = os.path.join(BIN_DIR, "ffmpeg.exe")
    ffprobe_exe = os.path.join(BIN_DIR, "ffprobe.exe")

    if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
        print(f"✅ FFmpeg binaries found in {BIN_DIR}")
        return

    # Check system PATH fallback
    sys_ffmpeg = shutil.which("ffmpeg")
    sys_ffprobe = shutil.which("ffprobe")

    if sys_ffmpeg and sys_ffprobe:
        print(f"📋 Copying system FFmpeg binaries from {os.path.dirname(sys_ffmpeg)} to {BIN_DIR}...")
        shutil.copy2(sys_ffmpeg, ffmpeg_exe)
        shutil.copy2(sys_ffprobe, ffprobe_exe)
        print("✅ FFmpeg binaries copied successfully.")
        return

    print("⬇️ Downloading static FFmpeg binaries for Windows...")
    zip_path = os.path.join(PROJECT_DIR, "ffmpeg_temp.zip")
    try:
        urllib.request.urlretrieve(FFMPEG_URL, zip_path)
        print("📦 Extracting FFmpeg binaries...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith("ffmpeg.exe"):
                    with zip_ref.open(member) as source, open(ffmpeg_exe, "wb") as target:
                        shutil.copyfileobj(source, target)
                elif member.endswith("ffprobe.exe"):
                    with zip_ref.open(member) as source, open(ffprobe_exe, "wb") as target:
                        shutil.copyfileobj(source, target)
        print("✅ FFmpeg binaries downloaded & extracted successfully!")
    except Exception as e:
        print(f"⚠️ Warning: Automatic FFmpeg download failed ({e}). Please manually place ffmpeg.exe and ffprobe.exe in {BIN_DIR}")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

def build_executable():
    print("🚀 Starting PyInstaller Directory Build (Downloader.exe)...")
    spec_file = os.path.join(PROJECT_DIR, "Downloader.spec")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file])

    dist_dir = os.path.join(PROJECT_DIR, "dist", "Downloader")
    bin_dist = os.path.join(dist_dir, "bin")
    os.makedirs(bin_dist, exist_ok=True)
    for b in ["ffmpeg.exe", "ffprobe.exe"]:
        src = os.path.join(BIN_DIR, b)
        dst = os.path.join(bin_dist, b)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)

    print("\n📦 Starting PyInstaller Single-File Portable Build (Downloader_v1.exe)...")
    onefile_spec = os.path.join(PROJECT_DIR, "Downloader_OneFile.spec")
    res_onefile = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", onefile_spec])

    if res_onefile.returncode == 0:
        standalone_exe = os.path.join(PROJECT_DIR, "dist", "Downloader_v1.exe")
        print("\n" + "="*65)
        print("🎉 ALL BUILDS SUCCESSFUL!")
        print(f"📍 Directory Build: {os.path.join(dist_dir, 'Downloader.exe')}")
        print(f"🌟 Portable Single-File EXE (Share this file anywhere): {standalone_exe}")
        print("="*65 + "\n")
    else:
        print("\n❌ PyInstaller single-file build failed. Check error logs above.\n")




if __name__ == "__main__":
    ensure_dependencies()
    ensure_ffmpeg_binaries()
    build_executable()
