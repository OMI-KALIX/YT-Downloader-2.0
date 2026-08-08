import os
import platform
import sys
from typing import Dict, Any


def get_system_info() -> Dict[str, Any]:
    """Returns OS and platform diagnostics."""
    return {
        "os": sys.platform,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "arch": platform.machine(),
    }


def is_windows() -> bool:
    """Returns True if running on Windows."""
    return sys.platform == "win32"
