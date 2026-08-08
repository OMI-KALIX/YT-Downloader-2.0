from fastapi import APIRouter
from ..schemas.responses import ConfigResponse

router = APIRouter()


@router.get("/config", response_model=ConfigResponse)
def get_config():
    return ConfigResponse(max_concurrent_downloads=2, update_check_interval=86400)
