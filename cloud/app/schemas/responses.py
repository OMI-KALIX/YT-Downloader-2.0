from pydantic import BaseModel
from typing import Dict, Any, Optional


class HealthResponse(BaseModel):
    status: str = "ok"


class VersionResponse(BaseModel):
    extension: str = "2.1.0"
    agent: str = "2.1.0"


class ConfigResponse(BaseModel):
    max_concurrent_downloads: int = 2
    update_check_interval: int = 86400


class AgentReleaseResponse(BaseModel):
    version: str = "3.0.0"
    platform: str = "windows-x64"
    download_url: str = "https://github.com/OMI-KALIX/youtube-downloader-extension/releases/download/v3.0.0/downloader-agent.exe"
    sha256: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
