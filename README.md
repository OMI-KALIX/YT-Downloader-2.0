# 🎬 YouTube Downloader Extension & Cloud Backend

A high-performance Chrome / Edge browser extension paired with a cloud-ready FastAPI backend for downloading YouTube videos (up to **4K Ultra HD**) and audio (up to **320 kbps MP3**) using authenticated browser session cookies.

---

## 🌟 Features

- 🚀 **Cloud Backend Execution**: Heavy media processing (`yt-dlp` + `FFmpeg`) runs on the cloud, offloading CPU and RAM from the user's machine.
- 📺 **Up to 4K Ultra HD**: Supports resolutions from 360p, 720p, 1080p, 2K (1440p), up to 4K (2160p) with no quality loss.
- 🎵 **320 kbps MP3 Audio**: Dedicated high-bitrate audio extraction post-processing.
- 🍪 **Automatic Session Cookie Handler**: Seamlessly uses the user's active YouTube cookies for private/restricted video downloads. Temporary Netscape cookie files are created dynamically and **deleted immediately** after processing.
- ⚡ **Render Auto-Wakeup**: When the user opens YouTube in any browser tab, the extension automatically pre-warms free-tier cloud backends (e.g., Render) in advance.
- 🔄 **Resumable Downloads & Fragment Concurrency**: Uses 4-thread parallel fragment downloading (`concurrent_fragment_downloads`) and HTTP Range request support (`206 Partial Content`) for browser download managers.
- 🧩 **Native YouTube UI Injection**: Injects a sleek, dark-themed gradient **Download** button directly next to YouTube's player action bar.

---

## 🏗️ Architecture

```
┌──────────────────────────────┐
│  Chrome / Edge Extension     │
│  (Manifest V3 + JS)          │
└──────────────┬───────────────┘
               │ 1. Read YouTube Cookies (chrome.cookies)
               │ 2. Send HTTPS Request (URL + Quality + Netscape Cookies)
               ▼
┌──────────────────────────────┐
│  FastAPI Cloud Backend       │
│  (Python 3.11 + Docker)      │
└──────────────┬───────────────┘
               │ 3. Temporary Cookie File (.txt)
               │ 4. Parallel yt-dlp + FFmpeg Merging
               ▼
┌──────────────────────────────┐
│ Stream Completed File &      │
│ Delete Temp Cookie File      │
└──────────────────────────────┘
```

---

## 📁 Repository Structure

```
youtube-downloader-extension/
├── extension/                 # Chrome / Edge Extension (Manifest V3)
│   ├── manifest.json          # Extension Manifest V3
│   ├── background/            # Service worker (Background requests & auto-wake)
│   │   └── background.js
│   ├── content/               # Injected YouTube watch page UI
│   │   ├── content.js
│   │   └── content.css
│   ├── popup/                 # Toolbar extension popup UI & settings
│   │   ├── popup.html
│   │   ├── popup.js
│   │   └── popup.css
│   └── utils/                 # Netscape cookie converter
│       └── cookie_exporter.js
├── backend/                   # FastAPI Cloud Backend
│   ├── main.py                # App entrypoint & CORS config
│   ├── api/                   # REST API routes (/formats, /download, /progress, /file)
│   │   └── router.py
│   ├── downloader/            # yt-dlp wrapper engine & quality parsing
│   │   └── engine.py
│   ├── cookies/               # Secure temporary cookie file manager
│   │   └── manager.py
│   ├── jobs/                  # Background threading job manager
│   │   └── manager.py
│   ├── progress/              # Thread-safe job status & progress tracker
│   │   └── tracker.py
│   └── requirements.txt       # Python dependencies
├── docker/                    # Docker containerization
│   ├── Dockerfile             # Python 3.11 + FFmpeg image
│   └── docker-compose.yml     # Docker Compose setup
├── render.yaml                # Render 1-click Blueprint deployment spec
└── README.md
```

---

## ⚡ Quick Start

### 1. Run Backend Locally

#### Option A: Python Direct
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run FastAPI server
python -m backend.main
```
The server runs on `http://localhost:8000`.

#### Option B: Docker Compose
```bash
docker-compose -f docker/docker-compose.yml up --build
```

---

### 2. Load Browser Extension

1. Open Chrome or Edge and navigate to `chrome://extensions` or `edge://extensions`.
2. Enable **Developer mode** toggle in the top right.
3. Click **Load unpacked**.
4. Select the `extension/` folder from this repository.

---

### 3. Deploy Cloud Backend on Render

1. Fork or push this repository to GitHub.
2. Go to [dashboard.render.com](https://dashboard.render.com/) and click **New +** -> **Blueprints**.
3. Select your repository. Render automatically reads `render.yaml` and deploys your Dockerized FastAPI container.
4. Copy your deployed Render URL (e.g., `https://youtube-downloader-backend.onrender.com`).
5. Open the Chrome Extension popup, click **Settings (⚙️)**, paste your Render URL, and click **Save Settings**.

---

## 🔒 Security & Privacy

- **No Persistent Cookie Storage**: Authentication cookies are sent over HTTPS per request, stored in a temporary isolated file, and **immediately deleted** as soon as `yt-dlp` finishes.
- **No Analytics / Telemetry**: Zero tracking scripts or analytics embedded.

---

## ⚙️ Environment Configuration & Datacenter IP Anti-Bot Mitigations

The backend supports environment variables for tuning `yt-dlp` rate limiting, proxying, and image rebuilding:

| Environment Variable | Type | Description |
| :--- | :--- | :--- |
| `YTDLP_SLEEP_REQUESTS` | Float | Seconds to sleep before each HTTP request (e.g. `1.0`) |
| `YTDLP_SLEEP_INTERVAL` | Float | Minimum seconds to sleep between downloads (e.g. `1.0`) |
| `YTDLP_MAX_SLEEP_INTERVAL` | Float | Maximum seconds to sleep between downloads (e.g. `5.0`) |
| `YTDLP_RATELIMIT` | String/Int | Download speed limit (e.g. `5M` or bytes/sec) |
| `YTDLP_PROXY` | String | HTTP/HTTPS/SOCKS5 proxy URL (e.g. `http://user:pass@proxy.example.com:8080`) |
| `YTDLP_CACHE_TTL` | Integer | Probe format extraction cache TTL in seconds (default `300`) |
| `YTDLP_VIDEO_COOLDOWN` | Integer | Per-video request cooldown window in seconds (default `15`) |
| `RETRY_BACKOFF_SECONDS` | Float | Base exponential backoff delay before retries in seconds (default `2.0`) |

### Residential/Mobile Proxy Integration for Datacenter IPs (Render)
Cloud host providers (like Render, AWS, GCP) use shared datacenter IP ranges. If YouTube increases bot verification enforcement on datacenter IPs, setting `YTDLP_PROXY` to a residential or mobile proxy route is the most durable solution to bypass IP reputation blocks.

---

## 📄 License

MIT License. Free for personal and open-source use.
