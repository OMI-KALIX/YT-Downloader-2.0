import os
import json
import logging
from typing import Dict, Any

from desktop.path_resolver import get_config_path, get_default_downloads_dir

logger = logging.getLogger("yt_backend")

DEFAULT_CONFIG: Dict[str, Any] = {
    "port": 8000,
    "host": "127.0.0.1",
    "download_dir": get_default_downloads_dir(),
    "max_concurrent_jobs": 3,
    "log_level": "INFO",
    "auto_start_windows": False,
    "start_minimized": True,
    "cookies_file": "",
    "ytdlp_proxy": ""
}

class ConfigManager:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or get_config_path()
        self._config: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config.update(data)
                logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed loading config.json, using defaults: {e}")
        else:
            self.save()
        return self._config

    def save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed saving config.json: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        self.save()

config_manager = ConfigManager()
