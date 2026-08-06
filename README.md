# 🎬 AnyDownloader: YouTube Downloader Extension & Native Desktop App

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Manifest V3](https://img.shields.io/badge/Chrome_Extension-Manifest_V3-green.svg)](extension/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-brightgreen.svg)](backend/)
[![PyInstaller](https://img.shields.io/badge/Executable-Portable_.exe-orange.svg)](build_exe.py)

A ultra high-performance YouTube video & audio downloader suite combining a **Chrome/Edge Extension (Manifest V3)** with a **Standalone Portable Desktop Backend Executable (`Downloader_v1.exe`)**. Supports resolutions up to **4K / 8K Ultra HD @ 60 FPS** and high-bitrate **320 kbps MP3 Audio** extraction.

---

## 🌟 Key Features

- ⚡ **Native YouTube UI Injection**: Injects a sleek, dark-themed **Download** button directly into YouTube's player action bar next to Like/Share buttons.
- 🚀 **100% Residential IP Reliability**: Runs locally on your machine—completely immune to YouTube's datacenter IP bans and `HTTP 429 Too Many Requests` errors.
- 📺 **Up to 4K / 8K Ultra HD**: Multi-threaded parallel downloading (`yt-dlp` engine) with hardware-accelerated **FFmpeg** audio/video stream muxing.
- 🎵 **320 kbps High-Bitrate MP3 Extraction**: High-fidelity audio processing with automated ID3 tag extraction.
- 🍪 **Automatic Session Cookie Exporter**: Seamlessly passes active YouTube session cookies for private, restricted, or member-only video downloads without manual login.
- 🖥️ **System Tray Native Desktop Integration**: Runs silently in the background with a Windows tray icon (`pystray`) for quick access to download folders, settings, and logs.
- 📦 **Portable Standalone Executable**: No Python or dependencies required for end-users! Simply run `Downloader_v1.exe`.

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USER'S LOCAL COMPUTER                           │
│                                                                        │
│  ┌──────────────────────────────┐        HTTP API (127.0.0.1:8000)    │
│  │  Chrome / Edge Extension     ├──────────────────────────┐           │
│  │  (Manifest V3 + Injected UI) │                          │           │
│  └──────────────────────────────┘                          ▼           │
│                                           ┌──────────────────────────┐ │
│                                           │ Portable Desktop App     │ │
│                                           │ (Downloader_v1.exe)      │ │
│                                           │ FastAPI + yt-dlp + FFmpeg│ │
│                                           └────────────┬─────────────┘ │
│                                                        │               │
│                                                        ▼               │
│                                             Downloads Folder (~/Downloads)
└────────────────────────────────────────────────────────────────────────┘
```

For the complete architectural evolution and past iterations (Cloud containers, Client-side WASM, etc.), read [PROJECT_HISTORY.md](PROJECT_HISTORY.md).

---

## 🚀 Quick Start Guide

### Option 1: Portable Executable (Recommended for Windows Users)

1. Launch `dist/Downloader_v1.exe` or download the pre-built single-file release.
2. The app starts a background local service on `http://127.0.0.1:8000` and displays a system tray icon.
3. Open Chrome or Edge, navigate to `chrome://extensions` (or `edge://extensions`), enable **Developer Mode**, and click **Load Unpacked**.
4. Select the [`extension/`](extension/) directory from this repository.
5. Open any YouTube video! Click the injected **Download** button to download instantly.

---

### Option 2: Developer / Python Local Setup

1. **Install Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```
2. **Run Desktop App**:
   ```bash
   python -m desktop.app
   ```
3. **Load Browser Extension**:
   - Load [`extension/`](extension/) folder as an Unpacked Extension in Chrome or Edge.

---

## 🔨 Building the Standalone `.exe` Package

You can build your own portable `.exe` package using the included `build_exe.py` script:

```bash
python build_exe.py
```

This automated builder:
1. Automatically verifies PyInstaller and GUI dependencies.
2. Automatically downloads static Windows **FFmpeg** binaries (`ffmpeg.exe` & `ffprobe.exe`) if not found locally.
3. Packages the backend engine, routes, and tray icons into a portable single-file executable: `dist/Downloader_v1.exe`.

---

## 📁 Repository Structure

```
youtube-downloader-extension/
├── extension/                 # Chrome / Edge Extension (Manifest V3)
│   ├── manifest.json          # Extension Manifest V3 spec
│   ├── background/            # Service worker & background message routing
│   ├── content/               # Injected YouTube watch page UI button & modal
│   ├── popup/                 # Toolbar extension popup UI & settings
│   └── utils/                 # Netscape cookie converter
├── desktop/                   # Desktop Native GUI & Tray Server
│   ├── app.py                 # Desktop app entrypoint (FastAPI + Tray)
│   ├── tray.py                # System tray icon & context menu handlers
│   ├── config.py              # User settings manager
│   └── path_resolver.py       # Portable binary path resolver
├── backend/                   # Core Python Backend Engine
│   ├── main.py                # FastAPI app initialization
│   ├── api/                   # REST API routes (/formats, /download, /mux)
│   ├── downloader/            # yt-dlp wrapper & format parser
│   └── jobs/                  # Thread-safe job & progress tracker
├── tests/                     # Unit test suite
├── build_exe.py               # Automated PyInstaller & FFmpeg build script
├── PROJECT_HISTORY.md         # Detailed chapterwise architectural history
└── CODE_OF_CONDUCT.md         # Open-source community guidelines
```

---

## 📖 Chapterwise Project History & Failures

Curious about how this project was designed? Read our chapter-by-chapter history document:
- 📖 [PROJECT_HISTORY.md](PROJECT_HISTORY.md)
  - **Chapter 1**: Pure Extension & Client-Side WebAssembly (WASM OOM & DASH splitting issues)
  - **Chapter 2**: Cloud Backend Service (YouTube Datacenter IP 429 Bans & Cold Starts)
  - **Chapter 3**: Hybrid Client Stream Link Resolution (IP-Bound 403 Forbidden errors)
  - **Chapter 4**: Final Solution (Chrome Extension + Local Portable Desktop App)

---

## 📄 License & Community

- **License**: [MIT License](LICENSE)
- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
