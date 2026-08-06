import os
import sys
import time
import logging
import threading
import uvicorn

# Include project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from desktop.path_resolver import get_ffmpeg_path, get_config_path
from desktop.config import config_manager
from desktop.tray import SystemTrayApp
from backend.main import app as fastapi_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("yt_backend")

class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        logger.info(f"Starting Uvicorn server on http://{self.host}:{self.port}...")
        config = uvicorn.Config(app=fastapi_app, host=self.host, port=self.port, log_level="info", access_log=False)
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True

def main():
    # 1. Initialize bundled FFmpeg path
    ffmpeg_dir = get_ffmpeg_path()
    logger.info(f"Resolved FFmpeg directory: {ffmpeg_dir}")

    # 2. Load configuration settings
    host = config_manager.get("host", "127.0.0.1")
    port = config_manager.get("port", 8000)
    download_dir = config_manager.get("download_dir", os.path.expanduser("~/Downloads"))
    config_path = get_config_path()

    # 3. Start Uvicorn FastAPI Server in background daemon thread
    server_thread = ServerThread(host=host, port=port)
    server_thread.start()

    # Force safe UTF-8 encoding for Windows console output
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    # Print clean user-facing startup banner
    print("\n" + "="*65)
    print(" >>> AnyDownloader Local Backend is RUNNING! <<<")
    print(f" [+] API Server: http://{host}:{port}")
    print(f" [+] Downloads Folder: {download_dir}")
    print(f" [+] Settings File: {config_path}")
    print(" [*] Keep this window open in the background while downloading.")
    print("="*65 + "\n")


    # Auto-open browser so user gets instant visual confirmation
    import webbrowser
    def _open_browser_delayed():
        time.sleep(1.2)
        try:
            webbrowser.open(f"http://{host}:{port}")
        except Exception:
            pass
    threading.Thread(target=_open_browser_delayed, daemon=True).start()


    # 4. Handle System Tray App (runs on main thread)
    def on_exit():
        logger.info("Shutting down application...")
        server_thread.stop()
        sys.exit(0)

    try:
        tray_app = SystemTrayApp(
            port=port,
            download_dir=download_dir,
            config_path=config_path,
            on_exit_callback=on_exit
        )
        tray_app.run()
    except Exception as e:
        logger.error(f"Tray application error: {e}")

    # Keep Uvicorn server thread alive permanently until explicitly terminated
    try:
        while server_thread.is_alive():
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        on_exit()


if __name__ == "__main__":
    main()
