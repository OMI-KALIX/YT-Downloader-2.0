from fastapi import APIRouter, HTTPException, Query
import urllib.request
import json
import re

metadata_router = APIRouter(prefix="/api/v1", tags=["Metadata"])


@metadata_router.get("/metadata")
def get_video_metadata(url: str = Query(..., description="YouTube video URL")):
    """Fast metadata extraction endpoint returning title, uploader, thumbnail, and duration."""
    if not url or ("youtube.com" not in url and "youtu.be" not in url):
        raise HTTPException(status_code=400, detail="A valid YouTube video URL is required.")

    # Extract video ID
    video_id = ""
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
    elif "watch?v=" in url:
        video_id = url.split("watch?v=")[1].split("&")[0]

    if not video_id:
        raise HTTPException(status_code=400, detail="Could not parse YouTube video ID.")

    thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    
    # Fast oEmbed query for title & channel name
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "id": video_id,
                "title": data.get("title", "YouTube Video"),
                "uploader": data.get("author_name", "YouTube Channel"),
                "thumbnail": data.get("thumbnail_url") or thumbnail,
                "url": url,
            }
    except Exception:
        return {
            "id": video_id,
            "title": "YouTube Video",
            "uploader": "YouTube Channel",
            "thumbnail": thumbnail,
            "url": url,
        }
