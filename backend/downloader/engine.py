import os
import tempfile
import logging
from typing import Dict, Any, List, Optional
import yt_dlp

from backend.progress.tracker import progress_tracker

logger = logging.getLogger("yt_backend")

def get_video_formats(url: str, cookie_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts video metadata and list of available quality options (formats up to 4K & 320kbps audio).
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {"skip": ["authcheck"]},
            "youtubetab": {"skip": ["authcheck"]}
        }
    }
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        formats_list = []
        if "formats" in info:
            seen_res = set()
            for f in info["formats"]:
                vcodec = f.get("vcodec", "none")
                height = f.get("height")
                fps = f.get("fps")
                ext = f.get("ext", "")

                if height and height not in seen_res and vcodec != "none":
                    seen_res.add(height)
                    
                    # Create clear quality labels (e.g. 4K Ultra HD, 2K, 1080p60, etc.)
                    label = f"{height}p"
                    if height >= 2160:
                        label = "4K Ultra HD (2160p)"
                    elif height >= 1440:
                        label = "2K Quad HD (1440p)"
                    elif height >= 1080:
                        label = f"Full HD (1080p{int(fps)}fps)" if fps and fps > 30 else "Full HD (1080p)"
                    elif height >= 720:
                        label = f"HD (720p{int(fps)}fps)" if fps and fps > 30 else "HD (720p)"

                    formats_list.append({
                        "format_id": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                        "resolution": label,
                        "ext": "mp4",
                        "height": height,
                        "type": "video"
                    })
            
            # Sort by height descending
            formats_list.sort(key=lambda x: x.get("height", 0), reverse=True)

        # High priority preset formats (4K / Best Video / 320kbps Audio)
        result_formats = [
            {"format_id": "bestvideo+bestaudio/best", "resolution": "🔥 Best Available Quality (Up to 4K)", "type": "video"},
            {"format_id": "bestaudio/best", "resolution": "🎵 High Quality Audio (320 kbps MP3)", "type": "audio"}
        ] + formats_list

        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "formats": result_formats
        }

def download_media(job_id: str, url: str, format_id: str, output_dir: str, cookie_path: Optional[str] = None) -> str:
    """
    Downloads media using yt-dlp with parallel fragment concurrency, resume download support,
    320kbps audio, and FFmpeg stream merging.
    """
    def progress_hook(d):
        if d.get("status") == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded_bytes = d.get("downloaded_bytes") or 0
            
            percent = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0.0
            speed_bytes = d.get("speed") or 0
            speed_str = f"{speed_bytes / 1024 / 1024:.2f} MB/s" if speed_bytes else "0 KB/s"
            
            eta = d.get("eta")
            eta_str = f"{eta}s" if eta is not None else "--:--"

            progress_tracker.update_job(job_id, {
                "status": "downloading",
                "percent": round(percent, 1),
                "speed": speed_str,
                "eta": eta_str
            })
        elif d.get("status") == "finished":
            progress_tracker.update_job(job_id, {
                "status": "processing",
                "percent": 99.0,
                "speed": "Merging streams...",
                "eta": "0s"
            })

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

    is_audio = format_id == "bestaudio/best" or "audio" in format_id
    
    ydl_opts: Dict[str, Any] = {
        "outtmpl": output_template,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {"skip": ["authcheck"]},
            "youtubetab": {"skip": ["authcheck"]}
        },
        
        # Resume download & retry optimizations
        "continuedl": True,
        "retries": 10,
        "fragment_retries": 10,
        "skip_unavailable_fragments": True,

        # Multi-threaded download speed & memory optimization
        "concurrent_fragment_downloads": 4,
        "buffersize": 1024 * 64,  # 64KB memory buffer for optimal disk streaming
    }

    if is_audio:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",  # Highest audio quality: 320 kbps
            }]
        })
    else:
        ydl_opts.update({
            "format": format_id if format_id else "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        })

    if cookie_path and os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    logger.info(f"Starting optimized yt-dlp download for job {job_id} [format: {format_id}]")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        
        if is_audio:
            base, _ = os.path.splitext(filename)
            filename = base + ".mp3"
        elif not filename.endswith(".mp4") and os.path.exists(os.path.splitext(filename)[0] + ".mp4"):
            filename = os.path.splitext(filename)[0] + ".mp4"

        return filename
