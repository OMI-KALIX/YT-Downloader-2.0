from .health import health_router
from .version import version_router
from .config import config_router
from .agent import agent_router
from .metadata import metadata_router

__all__ = ["health_router", "version_router", "config_router", "agent_router", "metadata_router"]
