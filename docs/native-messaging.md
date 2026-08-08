# 📡 Chrome / Edge Native Messaging Protocol Specification

## Overview

Communication between the Chrome/Edge extension and `downloader-agent.exe` uses standard input (`stdin`) and standard output (`stdout`).

Each payload frame is prefixed with a 4-byte uint32 little-endian length integer specifying the byte size of the JSON payload.

## Message Schema

### Request (Extension -> Agent)

```json
{
  "id": "req_101",
  "action": "download",
  "payload": {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "1080p"
  }
}
```

### Supported Actions

1. **`ping`**: Health check.
2. **`status`**: Returns readiness, agent version (`v2.1.0`), and presence of yt-dlp/ffmpeg binaries.
3. **`get_metadata`**: Fast metadata extraction returning `title`, `uploader`, `thumbnail`, and `duration`.
4. **`get_formats`**: Full format extraction with estimated file sizes.
5. **`download`**: Enqueues video download task. Returns immediate `download_started` event confirmation.
6. **`cancel`**: Cancels active running `yt-dlp` download subprocess.

---

### Response Events (Agent -> Extension)

#### 1. Download Started Event
```json
{
  "id": "req_101",
  "event": "download_started",
  "payload": {
    "job_id": "req_101",
    "status": "started"
  }
}
```

#### 2. Monotonic Progress Update Event
```json
{
  "id": "req_101",
  "event": "progress",
  "payload": {
    "job_id": "req_101",
    "percent": 45.2,
    "speed": "12.4 MB/s",
    "eta": "00:15",
    "state": "DOWNLOADING"
  }
}
```

#### 3. Download Completed Event
```json
{
  "id": "req_101",
  "event": "completed",
  "payload": {
    "job_id": "req_101",
    "filename": "Video Title [id].mp4",
    "filepath": "C:\\Users\\User\\Downloads\\Video Title [id].mp4",
    "state": "COMPLETED"
  }
}
```

#### 4. Job Cancelled Event
```json
{
  "id": "req_101",
  "event": "cancelled",
  "payload": {
    "job_id": "req_101",
    "state": "CANCELLED"
  }
}
```
