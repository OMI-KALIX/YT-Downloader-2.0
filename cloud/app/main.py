from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import health_router, version_router, config_router, agent_router, metadata_router

app = FastAPI(
    title="YT Downloader Cloud Control Plane",
    description="Lightweight control plane for versioning, configuration, fast metadata extraction, and agent updates.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(version_router)
app.include_router(config_router)
app.include_router(agent_router)
app.include_router(metadata_router)
