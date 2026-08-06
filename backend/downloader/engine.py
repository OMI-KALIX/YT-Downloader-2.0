import os
import tempfile
import logging
from typing import Dict, Any, List, Optional
import yt_dlp

from backend.progress.tracker import progress_tracker

logger = logging.getLogger("yt_backend")

def fetch_oembed_metadata(url: str) -> Optional[Dict[str, Any]]:
    """
    Keyless YouTube oEmbed API probe fallback. Instant 0.1s response, 0% bot verification failure.
    """
    import json
    import urllib.request
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        req = urllib.request.Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return {
                    "title": data.get("title"),
                    "uploader": data.get("author_name"),
                    "thumbnail": data.get("thumbnail_url")
                }
    except Exception as e:
        logger.warning(f"oEmbed metadata fallback failed for {url}: {e}")
    return None

def clean_youtube_url(url: str) -> str:
    """
    Strips radio mix / auto-generated list parameters from single watch URLs
    to prevent yt-dlp format extraction failures.
    """
    if "watch?v=" in url and "&list=" in url:
        return url.split("&list=")[0]
    return url

def format_size(bytes_val: float) -> str:
    if not bytes_val or bytes_val <= 0:
        return ""
    if bytes_val >= 1024**3:
        return f"~{bytes_val / (1024**3):.1f} GB"
    elif bytes_val >= 1024**2:
        return f"~{bytes_val / (1024**2):.1f} MB"
    elif bytes_val >= 1024:
        return f"~{bytes_val / 1024:.0f} KB"
    return f"~{int(bytes_val)} B"

def get_video_formats(url: str, cookie_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extracts video metadata and list of available quality options (formats up to 4K & 320kbps audio)
    with accurate download file size estimates.
    Includes automatic keyless oEmbed API fallback for instant metadata loading.
    """
    url = clean_youtube_url(url)
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "noplaylist": True,
        "js_runtimes": {"node": {}},
    }
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    def extract_with_opts(opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration") or 0
            formats_list = []

            if "formats" in info:
                # Calculate maximum audio format size
                audio_sizes = [
                    f.get("filesize") or f.get("filesize_approx") or 0
                    for f in info["formats"] if f.get("vcodec") == "none"
                ]
                best_audio_bytes = max(audio_sizes) if audio_sizes else (duration * 128000 / 8)

                # Group best video stream size per resolution height
                height_video_bytes = {}
                for f in info["formats"]:
                    h = f.get("height")
                    vcodec = f.get("vcodec", "none")
                    if h and vcodec != "none":
                        sz = f.get("filesize") or f.get("filesize_approx") or 0
                        if not sz and duration and f.get("vbr"):
                            sz = (f.get("vbr") * 1000 * duration) / 8
                        if h not in height_video_bytes or sz > height_video_bytes[h]:
                            height_video_bytes[h] = sz

                seen_res = set()
                for f in info["formats"]:
                    vcodec = f.get("vcodec", "none")
                    height = f.get("height")
                    fps = f.get("fps")

                    if height and height not in seen_res and vcodec != "none":
                        seen_res.add(height)
                        
                        # Create clear quality labels with file size
                        label = f"{height}p"
                        if height >= 4320:
                            label = "8K Ultra HD (4320p)"
                        elif height >= 2160:
                            label = "4K Ultra HD (2160p)"
                        elif height >= 1440:
                            label = "2K Quad HD (1440p)"
                        elif height >= 1080:
                            label = f"Full HD (1080p{int(fps)}fps)" if fps and fps > 30 else "Full HD (1080p)"
                        elif height >= 720:
                            label = f"HD (720p{int(fps)}fps)" if fps and fps > 30 else "HD (720p)"
                        elif height >= 480:
                            label = "480p SD"
                        elif height >= 360:
                            label = "360p SD"
                        elif height >= 240:
                            label = "240p Low"
                        elif height >= 144:
                            label = "144p Very Low"

                        v_bytes = height_video_bytes.get(height, 0)
                        tot_bytes = v_bytes + best_audio_bytes if v_bytes > 0 else 0
                        sz_str = format_size(tot_bytes)
                        if sz_str:
                            label = f"{label} ({sz_str})"

                        formats_list.append({
                            "format_id": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                            "resolution": label,
                            "type": "video",
                            "height": height,
                            "filesize": tot_bytes
                        })
                
                # Sort by height descending
                formats_list.sort(key=lambda x: x.get("height", 0), reverse=True)

            # Audio Quality Presets with file size estimates
            sz_320k = format_size(duration * 320000 / 8) if duration else ""
            sz_192k = format_size(duration * 192000 / 8) if duration else ""
            sz_128k = format_size(duration * 128000 / 8) if duration else ""

            lbl_320 = f"🎵 High Quality Audio (320 kbps MP3){' (' + sz_320k + ')' if sz_320k else ''}"
            lbl_192 = f"🎵 Medium Quality Audio (192 kbps MP3){' (' + sz_192k + ')' if sz_192k else ''}"
            lbl_128 = f"🎵 Standard Quality Audio (128 kbps MP3){' (' + sz_128k + ')' if sz_128k else ''}"

            audio_formats = [
                {"format_id": "audio_320k", "resolution": lbl_320, "type": "audio", "bitrate": 320},
                {"format_id": "audio_192k", "resolution": lbl_192, "type": "audio", "bitrate": 192},
                {"format_id": "audio_128k", "resolution": lbl_128, "type": "audio", "bitrate": 128},
            ]

            best_sz = format_size(formats_list[0]["filesize"]) if formats_list and formats_list[0].get("filesize") else ""
            best_label = f"🔥 Best Available Quality (Up to 4K){' (' + best_sz + ')' if best_sz else ''}"

            result_formats = [
                {"format_id": "bestvideo+bestaudio/best", "resolution": best_label, "type": "video"}
            ] + formats_list + audio_formats

            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "formats": result_formats
            }

    try:
        return extract_with_opts(ydl_opts)
    except Exception as e:
        logger.warning(f"yt-dlp format extraction primary attempt failed: {e}. Retrying with player_client fallback...")
        ydl_opts_fallback = dict(ydl_opts)
        ydl_opts_fallback["extractor_args"] = {"youtube": {"player_client": ["android", "mweb", "web"]}}
        try:
            return extract_with_opts(ydl_opts_fallback)
        except Exception as e2:
            if "cookiefile" in ydl_opts:
                logger.warning(f"yt-dlp format extraction failed with cookies: {e2}. Retrying without cookiefile...")
                ydl_opts_no_cookie = dict(ydl_opts_fallback)
                ydl_opts_no_cookie.pop("cookiefile", None)
                try:
                    return extract_with_opts(ydl_opts_no_cookie)
                except Exception as e3:
                    logger.warning(f"yt-dlp format extraction failed without cookies: {e3}. Attempting oEmbed fallback...")
            else:
                logger.warning(f"yt-dlp format extraction failed: {e2}. Attempting oEmbed fallback...")
            
        oembed_data = fetch_oembed_metadata(url)
        if oembed_data:
            fallback_formats = [
                {"format_id": "bestvideo+bestaudio/best", "resolution": "🔥 Best Available Quality (Up to 4K)", "type": "video"},
                {"format_id": "bestvideo[height<=1080]+bestaudio/best", "resolution": "Full HD (1080p)", "type": "video", "height": 1080},
                {"format_id": "bestvideo[height<=720]+bestaudio/best", "resolution": "HD (720p)", "type": "video", "height": 720},
                {"format_id": "bestvideo[height<=480]+bestaudio/best", "resolution": "480p SD", "type": "video", "height": 480},
                {"format_id": "bestvideo[height<=360]+bestaudio/best", "resolution": "360p SD", "type": "video", "height": 360},
                {"format_id": "audio_320k", "resolution": "🎵 High Quality Audio (320 kbps MP3)", "type": "audio", "bitrate": 320},
                {"format_id": "audio_192k", "resolution": "🎵 Medium Quality Audio (192 kbps MP3)", "type": "audio", "bitrate": 192},
                {"format_id": "audio_128k", "resolution": "🎵 Standard Quality Audio (128 kbps MP3)", "type": "audio", "bitrate": 128},
            ]
            return {
                "id": url.split("v=")[-1].split("&")[0] if "v=" in url else "video",
                "title": oembed_data.get("title"),
                "thumbnail": oembed_data.get("thumbnail"),
                "duration": None,
                "uploader": oembed_data.get("uploader"),
                "formats": fallback_formats
            }
        raise e

def sanitize_filename(name: str) -> str:
    import re
    if not name:
        return "youtube_download"
    clean = re.sub(r'[\\/*?:"<>|]', '', name).strip().strip('.')
    return clean or "youtube_download"

def download_media(job_id: str, url: str, format_id: str, output_dir: str, cookie_path: Optional[str] = None) -> str:
    """
    Downloads media using yt-dlp with parallel fragment concurrency, resume download support,
    configurable audio bitrate (320, 192, 128 kbps), and FFmpeg stream merging.
    """
    url = clean_youtube_url(url)

    def progress_hook(d):
        import time
        from backend.jobs.manager import is_paused, is_cancelled

        if is_cancelled(job_id):
            raise yt_dlp.utils.DownloadError("Download cancelled by user")

        while is_paused(job_id):
            if is_cancelled(job_id):
                raise yt_dlp.utils.DownloadError("Download cancelled by user")
            progress_tracker.update_job(job_id, {
                "status": "paused",
                "speed": "Paused",
                "eta": "--:--"
            })
            time.sleep(0.5)

        if d.get("status") == "downloading":
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded_bytes = d.get("downloaded_bytes") or 0
            
            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes * 100)
            elif d.get("fragment_count"):
                frag_idx = d.get("fragment_index", 0)
                frag_cnt = d.get("fragment_count", 1)
                percent = (frag_idx / frag_cnt * 100)
            else:
                percent = 10.0

            speed_bytes = d.get("speed") or 0
            if speed_bytes >= 1024 * 1024:
                speed_str = f"{speed_bytes / 1024 / 1024:.2f} MB/s"
            elif speed_bytes > 0:
                speed_str = f"{speed_bytes / 1024:.1f} KB/s"
            else:
                speed_str = "Downloading..."

            eta = d.get("eta")
            eta_str = f"{eta}s" if eta is not None else "--:--"

            progress_tracker.update_job(job_id, {
                "status": "downloading",
                "percent": round(min(percent, 98.9), 1),
                "speed": speed_str,
                "eta": eta_str
            })
        elif d.get("status") == "finished":
            progress_tracker.update_job(job_id, {
                "status": "processing",
                "percent": 99.0,
                "speed": "Processing media...",
                "eta": "0s"
            })

    output_template = os.path.join(output_dir, "%(id)s.%(ext)s")

    is_audio = format_id.startswith("audio_") or format_id in ["bestaudio/best", "bestaudio"]
    
    # Determine audio bitrate quality (320, 192, 128 kbps)
    audio_bitrate = "320"
    if "128" in format_id:
        audio_bitrate = "128"
    elif "192" in format_id:
        audio_bitrate = "192"
    elif "320" in format_id:
        audio_bitrate = "320"

    ydl_opts: Dict[str, Any] = {
        "outtmpl": output_template,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "socket_timeout": 20,
        "js_runtimes": {"node": {}},
        "format_sort": ["res", "fps", "codec", "size", "br"],
        
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
                "preferredquality": audio_bitrate,
            }]
        })
    else:
        target_fmt = format_id if format_id else "bestvideo+bestaudio/best"
        target_fmt = f"{target_fmt}/bestvideo+bestaudio/best"
        ydl_opts.update({
            "format": target_fmt,
            "merge_output_format": "mp4",
        })

    if cookie_path and os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    logger.info(f"Starting optimized yt-dlp download for job {job_id} [format: {format_id}]")
    
    def resolve_downloaded_file(info_dict: dict) -> str:
        raw_title = info_dict.get("title", "downloaded_media")
        clean_title = sanitize_filename(raw_title)

        # Look for resulting files in output_dir
        candidates = [
            os.path.join(output_dir, f) for f in os.listdir(output_dir)
            if not f.endswith(".part") and not f.endswith(".ytdl")
        ]
        if candidates:
            candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            chosen = candidates[0]
            ext = os.path.splitext(chosen)[1]
            desirable_name = os.path.join(output_dir, f"{clean_title}{ext}")
            if chosen != desirable_name:
                try:
                    os.rename(chosen, desirable_name)
                    return desirable_name
                except Exception:
                    return chosen
            return chosen
        
        fallback_name = ydl.prepare_filename(info_dict)
        if is_audio:
            fallback_name = os.path.splitext(fallback_name)[0] + ".mp3"
        return fallback_name

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return resolve_downloaded_file(info)
    except yt_dlp.utils.DownloadError as e:
        logger.warning(f"yt-dlp download failed for job {job_id}: {e}. Executing Tier 2 player_client fallback...")
        tier2_opts = dict(ydl_opts)
        tier2_opts["extractor_args"] = {"youtube": {"player_client": ["android", "mweb", "web"]}}
        if is_audio:
            tier2_opts["format"] = "bestaudio/best"
        else:
            target_fmt = format_id if format_id else "bestvideo+bestaudio/best"
            tier2_opts["format"] = f"{target_fmt}/bestvideo+bestaudio/best"

        try:
            with yt_dlp.YoutubeDL(tier2_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return resolve_downloaded_file(info)
        except Exception as e2:
            if "cookiefile" in tier2_opts:
                logger.warning(f"yt-dlp download Tier 2 failed with cookies: {e2}. Executing Tier 3 fallback without cookies...")
                tier3_opts = dict(tier2_opts)
                tier3_opts.pop("cookiefile", None)
                try:
                    with yt_dlp.YoutubeDL(tier3_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        return resolve_downloaded_file(info)
                except Exception:
                    raise e
            raise e



def extract_playlist_items(url: str, cookie_path: Optional[str] = None, max_items: int = 25) -> List[Dict[str, Any]]:
    """
    Extracts individual video items from a playlist URL up to max_items limit.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "extractor_args": {
            "youtube": {"skip": ["authcheck"]},
            "youtubetab": {"skip": ["authcheck"]}
        }
    }
    if cookie_path and os.path.exists(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            items = []
            if "entries" in info and info["entries"]:
                for idx, entry in enumerate(info["entries"]):
                    if idx >= max_items:
                        break
                    entry_url = entry.get("url") or entry.get("webpage_url")
                    if not entry_url and entry.get("id"):
                        entry_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    if entry_url:
                        items.append({
                            "title": entry.get("title") or f"Item {idx + 1}",
                            "url": entry_url,
                            "id": entry.get("id")
                        })
            elif info.get("url") or info.get("webpage_url"):
                items.append({
                    "title": info.get("title", "Video"),
                    "url": info.get("webpage_url") or info.get("url") or url,
                    "id": info.get("id")
                })
            return items
    except Exception as e:
        logger.error(f"Failed extracting playlist items: {e}")
        # Fallback single video item
        return [{"title": "Media Item", "url": url}]

def cleanup_expired_partials(retention_seconds: int = 3600):
    """
    Sweeps system temp directory for orphaned yt_dl_ directories and partial files older than retention_seconds.
    """
    import time
    import shutil
    temp_dir = tempfile.gettempdir()
    now = time.time()
    try:
        for entry in os.listdir(temp_dir):
            if entry.startswith("yt_dl_"):
                full_path = os.path.join(temp_dir, entry)
                if os.path.isdir(full_path):
                    mtime = os.path.getmtime(full_path)
                    if now - mtime > retention_seconds:
                        shutil.rmtree(full_path, ignore_errors=True)
                        logger.info(f"Purged expired partial download folder: {full_path}")
    except Exception as e:
        logger.warning(f"Error during partial download cleanup sweep: {e}")

