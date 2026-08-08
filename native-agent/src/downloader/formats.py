from typing import Any, Dict, List


def format_bytes(b: int) -> str:
    """Formats byte counts into clean human-readable size strings."""
    if not b or b <= 0:
        return ""
    if b >= 1073741824:
        return f"~{b / 1073741824:.1f} GB"
    if b >= 1048576:
        return f"~{b / 1048576:.1f} MB"
    if b >= 1024:
        return f"~{b / 1024:.0f} KB"
    return f"~{b} B"


def parse_yt_dlp_metadata(dump_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parses raw yt-dlp json metadata into video metadata + standard format options."""
    title = dump_data.get("title") or dump_data.get("fulltitle") or "YouTube Video"
    uploader = dump_data.get("uploader") or dump_data.get("channel") or dump_data.get("uploader_id") or "YouTube Channel"
    duration = dump_data.get("duration") or 0
    video_id = dump_data.get("id") or ""

    # Guaranteed high-resolution thumbnail extraction
    thumbnail = dump_data.get("thumbnail") or ""
    if not thumbnail and dump_data.get("thumbnails"):
        thumbnails = dump_data.get("thumbnails")
        if isinstance(thumbnails, list) and len(thumbnails) > 0:
            thumbnail = thumbnails[-1].get("url") or ""
    if not thumbnail and video_id:
        thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    # Playlist support
    entries = dump_data.get("entries")
    is_playlist = bool(entries is not None)
    playlist_count = len(entries) if entries else 0

    raw_formats = dump_data.get("formats", [])
    result: List[Dict[str, Any]] = []
    seen_heights = set()

    for fmt in raw_formats:
        fmt_id = fmt.get("format_id")
        height = fmt.get("height")
        vcodec = fmt.get("vcodec", "none")
        ext = fmt.get("ext", "mp4")
        filesize = fmt.get("filesize") or fmt.get("filesize_approx") or 0

        if height and height >= 144 and vcodec != "none":
            if height not in seen_heights:
                seen_heights.add(height)
                sz_str = format_bytes(filesize)
                
                if height >= 2160:
                    label = "🎬 4K Ultra HD (2160p)"
                elif height >= 1440:
                    label = "🎬 2K Quad HD (1440p)"
                elif height >= 1080:
                    label = "🎬 Full HD (1080p)"
                elif height >= 720:
                    label = "🎬 HD (720p)"
                elif height >= 480:
                    label = "🎬 480p SD"
                elif height >= 360:
                    label = "🎬 360p SD"
                else:
                    label = f"🎬 {height}p SD"

                if sz_str:
                    label += f" ({sz_str})"

                result.append({
                    "id": fmt_id,
                    "resolution": label,
                    "height": height,
                    "extension": ext,
                    "filesize": filesize,
                    "filesize_str": sz_str,
                    "type": "video",
                })

    # Sort video formats by resolution height descending
    result.sort(key=lambda x: x.get("height", 0), reverse=True)

    # Always provide rich audio quality selection
    result.extend([
        {
            "id": "audio_320k",
            "resolution": "🎵 320 kbps High Quality MP3",
            "height": 0,
            "extension": "mp3",
            "filesize": 0,
            "filesize_str": "~10 MB",
            "type": "audio",
        },
        {
            "id": "audio_192k",
            "resolution": "🎵 192 kbps Medium Quality MP3",
            "height": 0,
            "extension": "mp3",
            "filesize": 0,
            "filesize_str": "~6 MB",
            "type": "audio",
        },
        {
            "id": "audio_128k",
            "resolution": "🎵 128 kbps Standard Quality MP3",
            "height": 0,
            "extension": "mp3",
            "filesize": 0,
            "filesize_str": "~4 MB",
            "type": "audio",
        },
    ])

    return {
        "id": video_id,
        "title": title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "duration": duration,
        "is_playlist": is_playlist,
        "playlist_count": playlist_count,
        "formats": result,
    }


def parse_yt_dlp_formats(dump_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Legacy helper returning formats list."""
    parsed = parse_yt_dlp_metadata(dump_data)
    return parsed.get("formats", [])
