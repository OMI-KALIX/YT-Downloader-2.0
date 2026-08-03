import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.api.router import router as api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="YouTube Downloader Cloud Backend",
    description="Backend API for processing YouTube downloads using yt-dlp & FFmpeg.",
    version="1.0.0"
)

# Enable CORS for extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Extension origins (chrome-extension://...)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/")
def root():
    return {
        "message": "YouTube Downloader Cloud API is running.",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
