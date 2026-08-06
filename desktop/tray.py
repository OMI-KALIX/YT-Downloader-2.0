import os
import sys
import subprocess
import webbrowser
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("yt_backend")

def create_default_icon_image():
    """Generates a high-quality 64x64 PIL Image for system tray icon."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Red circular background
        draw.ellipse([4, 4, 60, 60], fill=(220, 38, 38, 255))
        
        # White down arrow
        draw.polygon([(32, 44), (20, 28), (26, 28), (26, 16), (38, 16), (38, 28), (44, 28)], fill=(255, 255, 255, 255))
        # White bar at bottom
        draw.rectangle([20, 48, 44, 52], fill=(255, 255, 255, 255))
        return img
    except Exception as e:
        logger.error(f"Error creating PIL icon: {e}")
        return None

class SystemTrayApp:
    def __init__(self, port: int, download_dir: str, config_path: str, on_exit_callback: Optional[Callable] = None):
        self.port = port
        self.download_dir = download_dir
        self.config_path = config_path
        self.on_exit_callback = on_exit_callback
        self.icon = None

    def open_downloads_folder(self, item=None):
        if os.path.exists(self.download_dir):
            if os.name == 'nt':
                os.startfile(self.download_dir)
            else:
                subprocess.Popen(["open" if sys.platform == 'darwin' else "xdg-open", self.download_dir])
        else:
            logger.warning(f"Download directory does not exist: {self.download_dir}")

    def open_api_docs(self, item=None):
        webbrowser.open(f"http://127.0.0.1:{self.port}/docs")

    def edit_config(self, item=None):
        if os.path.exists(self.config_path):
            if os.name == 'nt':
                os.startfile(self.config_path)
            else:
                subprocess.Popen(["open" if sys.platform == 'darwin' else "xdg-open", self.config_path])

    def stop(self, item=None):
        logger.info("Stopping system tray app...")
        if self.icon:
            self.icon.stop()
        if self.on_exit_callback:
            self.on_exit_callback()

    def run(self):
        try:
            import pystray
            from pystray import MenuItem as item
        except ImportError:
            logger.warning("pystray not installed; system tray icon disabled.")
            return

        image = create_default_icon_image()
        if not image:
            logger.warning("Could not create icon image; skipping tray app.")
            return

        menu = pystray.Menu(
            item('🎬 AnyDownloader Local Backend', None, enabled=False),
            item(f'🌐 API Docs (Port {self.port})', self.open_api_docs),
            item('📁 Open Downloads Folder', self.open_downloads_folder),
            item('⚙️ Open Settings (config.json)', self.edit_config),
            pystray.Menu.SEPARATOR,
            item('❌ Exit', self.stop)
        )

        self.icon = pystray.Icon("AnyDownloader", image, "AnyDownloader Local Backend", menu)
        logger.info("System tray icon initialized.")
        self.icon.run()
