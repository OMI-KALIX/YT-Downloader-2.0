from fastapi import APIRouter
from ..schemas.responses import VersionResponse

router = APIRouter()


@router.get("/version", response_model=VersionResponse)
def get_version():
    return VersionResponse(extension="3.0.0", agent="3.0.0")
