# 🚀 YT Downloader 2.0 Architectural Specification

## Overview

YT Downloader 2.0 implements a **Native Agent Architecture** separating the user interface, execution engine, and control plane:

```
                     YT DOWNLOADER
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
       EXTENSION        NATIVE AGENT    CLOUD API
            │              │              │
            │              ├── yt-dlp     ├── Version
            │              ├── FFmpeg     ├── Config
            │              ├── Jobs       ├── Health
            │              └── Files      └── Releases
            │
            └──── Native Messaging ───────┘
                           │
                           ▼
                        YouTube
                           │
                           ▼
                     User Downloads
```

- **Browser Extension**: Handles YouTube watch page detection, quality selection UI, and progress display. Communicates strictly via Chrome/Edge Native Messaging.
- **Native Downloader Agent (`downloader-agent.exe`)**: Invisible local binary running silently on the user's PC. Handles yt-dlp subprocess extraction, hardware-accelerated FFmpeg stream merging, job state tracking, and output file management.
- **Cloud Control Plane**: Lightweight FastAPI service hosted on Render providing application versioning, feature flags, health status, and update release metadata.

## Key Design Constraints
1. The cloud control plane **never** processes or downloads videos.
2. The browser extension **never** executes native shell commands directly.
3. The end-user **never** starts a manual server or installs Python/FFmpeg manually.
