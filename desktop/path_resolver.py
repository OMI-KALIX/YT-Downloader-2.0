import os
import sys
import shutil
import logging

logger = logging.getLogger("yt_backend")

def get_app_dir() -> str:
    """
    Returns the main directory where the executable or main script resides.
    In PyInstaller frozen mode, this is the directory containing the .exe file.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bundle_dir() -> str:
    """
    Returns the runtime bundle directory.
    In PyInstaller frozen mode, this is sys._MEIPASS (temporary extracted directory).
    In normal script execution, it returns the project root.
    """
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', get_app_dir())
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bin_dir() -> str:
    """
    Locates the directory containing ffmpeg.exe and ffprobe.exe.
    Checks sys._MEIPASS/bin, app_dir/bin, and app_dir/ffmpeg.
    """
    bundle_dir = get_bundle_dir()
    app_dir = get_app_dir()

    candidates = [
        os.path.join(bundle_dir, "bin"),
        os.path.join(app_dir, "bin"),
        os.path.join(bundle_dir, "ffmpeg"),
        os.path.join(app_dir, "ffmpeg"),
        bundle_dir,
        app_dir
    ]

    for cand in candidates:
        ffmpeg_exe = os.path.join(cand, "ffmpeg.exe" if os.name == 'nt' else "ffmpeg")
        if os.path.exists(ffmpeg_exe):
            return cand

    # Fallback to system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return os.path.dirname(system_ffmpeg)

    return os.path.join(app_dir, "bin")

def get_ffmpeg_path() -> str:
    """
    Returns the absolute path to the directory containing ffmpeg.exe.
    Also automatically prepends the folder to os.environ['PATH'].
    """
    bin_dir = get_bin_dir()
    
    # Prepend to PATH so subprocess calls find ffmpeg automatically
    current_path = os.environ.get("PATH", "")
    if bin_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = bin_dir + os.pathsep + current_path
        logger.info(f"Prepended FFmpeg path to environment PATH: {bin_dir}")
        
    return bin_dir

def get_config_path() -> str:
    """
    Returns the path to config.json.
    Defaults to config.json adjacent to the executable or project root.
    """
    return os.path.join(get_app_dir(), "config.json")

def get_default_downloads_dir() -> str:
    """
    Returns the user's default Downloads directory on Windows / OS.
    """
    home = os.path.expanduser("~")
    downloads = os.path.join(home, "Downloads")
    if os.path.exists(downloads):
        return downloads
    return home
