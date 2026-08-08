from fastapi import APIRouter
from ..schemas.responses import AgentReleaseResponse

router = APIRouter()


@router.get("/agent/latest", response_model=AgentReleaseResponse)
def get_agent_latest():
    return AgentReleaseResponse(
        version="3.0.0",
        platform="windows-x64",
        download_url="https://github.com/OMI-KALIX/youtube-downloader-extension/releases/download/v3.0.0/downloader-agent.exe",
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
