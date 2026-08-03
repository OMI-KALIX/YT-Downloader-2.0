import os
import tempfile
import logging
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger("yt_backend")

@contextmanager
def temporary_cookie_file(cookie_content: str) -> Generator[str, None, None]:
    """
    Creates a temporary Netscape-formatted cookie file on disk,
    yields the path to yt-dlp, and ensures immediate deletion afterwards.
    """
    if not cookie_content or not cookie_content.strip():
        yield None
        return

    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    file_path = temp_file.name
    try:
        # Ensure header if missing
        if "# Netscape HTTP Cookie File" not in cookie_content:
            cookie_content = "# Netscape HTTP Cookie File\n# http://curl.haxx.se/rfc/cookie_spec.html\n# This is a generated file! Do not edit.\n\n" + cookie_content
        
        temp_file.write(cookie_content)
        temp_file.flush()
        temp_file.close()
        
        logger.info(f"Temporary cookie file created: {file_path}")
        yield file_path
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Temporary cookie file deleted: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temporary cookie file {file_path}: {e}")
