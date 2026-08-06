import { convertToNetscapeCookies } from '../utils/cookie_exporter.js';

// Default backend URL & API key (configurable via storage)
let BACKEND_URL = "https://youtube-downloader-extension-bul7.onrender.com";
let API_KEY = "";

// Load custom storage settings
chrome.storage.local.get(["backendUrl", "apiKey"], (res) => {
  if (res.backendUrl) BACKEND_URL = res.backendUrl.replace(/\/$/, "");
  if (res.apiKey) API_KEY = res.apiKey;
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.backendUrl) BACKEND_URL = changes.backendUrl.newValue.replace(/\/$/, "");
  if (changes.apiKey) API_KEY = changes.apiKey.newValue || "";
});

async function getAuthHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (API_KEY) headers["x-api-key"] = API_KEY;
  return headers;
}

// Extract cookies for YouTube domain
async function getYouTubeNetscapeCookies() {
  return new Promise((resolve) => {
    chrome.cookies.getAll({ domain: ".youtube.com" }, (cookies) => {
      if (chrome.runtime.lastError || !cookies) {
        console.error("Failed to get cookies:", chrome.runtime.lastError);
        resolve("");
        return;
      }
      const netscapeStr = convertToNetscapeCookies(cookies);
      resolve(netscapeStr);
    });
  });
}

// Helper function to ping backend health
async function pingBackendHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(`${BACKEND_URL}/api/health`, { signal: controller.signal });
    clearTimeout(timeoutId);
    return res.ok;
  } catch (err) {
    return false;
  }
}

// Automatically wake up backend when user opens YouTube in any tab
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && tab.url.includes("youtube.com")) {
    pingBackendHealth().then(isOnline => {
      console.log(`Auto-pinged Render backend on YouTube tab load. Online: ${isOnline}`);
    });
  }
});

// Handle incoming messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "WAKE_BACKEND") {
    pingBackendHealth().then(isOnline => sendResponse({ isOnline }));
    return true;
  }

  if (request.action === "CHECK_BACKEND_HEALTH") {
    (async () => {
      let isOnline = await pingBackendHealth();
      if (isOnline) {
        sendResponse({ isOnline: true, status: "online" });
        return;
      }
      
      let attempts = 0;
      const maxAttempts = 30;
      const interval = setInterval(async () => {
        attempts++;
        isOnline = await pingBackendHealth();
        if (isOnline) {
          clearInterval(interval);
          chrome.runtime.sendMessage({ action: "BACKEND_STATUS_UPDATE", status: "online" });
        } else if (attempts >= maxAttempts) {
          clearInterval(interval);
          chrome.runtime.sendMessage({ action: "BACKEND_STATUS_UPDATE", status: "offline" });
        } else {
          chrome.runtime.sendMessage({ action: "BACKEND_STATUS_UPDATE", status: "waking", attempt: attempts });
        }
      }, 2000);

      sendResponse({ isOnline: false, status: "waking" });
    })();
    return true;
  }

  if (request.action === "GET_COOKIES") {
    getYouTubeNetscapeCookies().then(cookies => sendResponse({ cookies }));
    return true;
  }

  if (request.action === "FETCH_FORMATS") {
    (async () => {
      try {
        const cookies = await getYouTubeNetscapeCookies();
        const headers = await getAuthHeaders();
        const res = await fetch(`${BACKEND_URL}/api/formats`, {
          method: "POST",
          headers,
          body: JSON.stringify({ url: request.url, cookies })
        });
        const data = await res.json();
        if (!res.ok) {
          sendResponse({ success: false, error: data.detail || "Error fetching formats" });
          return;
        }
        sendResponse({ success: true, data: data.data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === "START_CLIENT_DOWNLOAD") {
    const filename = `${sanitizeFilename(request.title || "youtube_video")}.mp4`;
    console.log(`[AnyDownloader] Starting direct client-side browser download for ${filename}`);
    chrome.downloads.download(
      {
        url: request.url,
        filename: filename,
        saveAs: false
      },
      (downloadId) => {
        if (chrome.runtime.lastError) {
          console.error("Client download failed:", chrome.runtime.lastError);
          sendResponse({ success: false, error: chrome.runtime.lastError.message });
        } else {
          sendResponse({ success: true, downloadId });
        }
      }
    );
    return true;
  }

  if (request.action === "START_MUX_DOWNLOAD") {
    (async () => {
      try {
        const headers = await getAuthHeaders();
        console.log(`[AnyDownloader] Posting direct stream URLs to /api/mux [video: ${Boolean(request.video_url)}, audio: ${Boolean(request.audio_url)}]`);
        const res = await fetch(`${BACKEND_URL}/api/mux`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            video_url: request.video_url,
            audio_url: request.audio_url,
            title: request.title,
            format_id: request.format_id
          })
        });
        const data = await res.json();
        if (!res.ok) {
          sendResponse({ success: false, error: data.detail || "Direct stream mux request rejected" });
          return;
        }

        if (data.job_id) {
          sendResponse({ success: true, jobId: data.job_id });
          trackDownloadProgress(data.job_id);
        } else {
          sendResponse({ success: false, error: "No job ID returned for mux request" });
        }
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === "START_DOWNLOAD" || request.action === "START_BATCH_DOWNLOAD") {
    (async () => {
      try {
        const cookies = await getYouTubeNetscapeCookies();
        const headers = await getAuthHeaders();
        const endpoint = request.action === "START_BATCH_DOWNLOAD" ? "/api/batch" : "/api/download";

        const res = await fetch(`${BACKEND_URL}${endpoint}`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            url: request.url,
            format_id: request.format_id || "bestvideo+bestaudio/best",
            cookies,
            delay_seconds: request.delay_seconds || 0
          })
        });
        const data = await res.json();
        if (!res.ok) {
          sendResponse({ success: false, error: data.detail || "Download request rejected" });
          return;
        }

        if (data.job_id) {
          sendResponse({ success: true, jobId: data.job_id });
          trackDownloadProgress(data.job_id);
        } else {
          sendResponse({ success: false, error: "No job ID returned" });
        }
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === "CANCEL_JOB") {
    (async () => {
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`${BACKEND_URL}/api/cancel/${request.jobId}`, { method: "POST", headers });
        const data = await res.json();
        sendResponse({ success: res.ok, data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === "PAUSE_JOB") {
    (async () => {
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`${BACKEND_URL}/api/pause/${request.jobId}`, { method: "POST", headers });
        const data = await res.json();
        sendResponse({ success: res.ok, data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === "RESUME_JOB") {
    (async () => {
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`${BACKEND_URL}/api/resume/${request.jobId}`, { method: "POST", headers });
        const data = await res.json();
        sendResponse({ success: res.ok, data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === "GET_JOB_STATUS") {
    (async () => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/progress/${request.jobId}`);
        const data = await res.json();
        sendResponse({ success: true, data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }
});

function sanitizeFilename(name) {
  if (!name) return "youtube_download";
  return name.replace(/[\\/*?:"<>|]/g, "").trim() || "youtube_download";
}

// Primary tracker: attempts WebSocket connection first, falls back seamlessly to HTTP polling
function trackDownloadProgress(jobId) {
  let isFinished = false;

  const wsScheme = BACKEND_URL.startsWith("https") ? "wss" : "ws";
  const wsHost = BACKEND_URL.replace(/^https?:\/\//, "");
  const wsUrl = `${wsScheme}://${wsHost}/api/ws/${jobId}`;

  console.log(`[AnyDownloader] Connecting WebSocket: ${wsUrl}`);
  let ws = null;

  try {
    ws = new WebSocket(wsUrl);
  } catch (err) {
    console.warn(`[AnyDownloader] WebSocket creation failed: ${err.message}. Falling back to polling.`);
    pollDownloadProgress(jobId);
    return;
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.ping) return;

      chrome.runtime.sendMessage({ action: "JOB_PROGRESS_UPDATE", job: data });

      if (data.status === "completed") {
        isFinished = true;
        ws.close();
        if (!data.is_batch && (data.file_path || data.filename)) {
          const fileUrl = `${BACKEND_URL}/api/file/${jobId}`;
          const cleanName = sanitizeFilename(data.filename);
          chrome.downloads.download({
            url: fileUrl,
            filename: cleanName,
            saveAs: true
          }, (downloadId) => {
            if (chrome.runtime.lastError) {
              console.error("[AnyDownloader] Chrome download failed:", chrome.runtime.lastError.message);
            } else {
              console.log(`[AnyDownloader] Chrome download started with ID: ${downloadId}`);
            }
          });
        } else if (data.is_batch && data.sub_jobs) {
          // Trigger download for each sub job
          data.sub_jobs.forEach(subId => trackDownloadProgress(subId));
        }
      } else if (data.status === "failed" || data.status === "cancelled") {
        isFinished = true;
        ws.close();
      }
    } catch (e) {
      console.error("[AnyDownloader] Error parsing WS message:", e);
    }
  };

  ws.onerror = (err) => {
    console.warn("[AnyDownloader] WebSocket error. Initiating HTTP polling fallback.", err);
    if (!isFinished) pollDownloadProgress(jobId);
  };

  ws.onclose = () => {
    if (!isFinished) {
      console.log("[AnyDownloader] WebSocket closed. Switching to HTTP polling.");
      pollDownloadProgress(jobId);
    }
  };
}

// HTTP Polling Fallback
async function pollDownloadProgress(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/progress/${jobId}`);
      if (!res.ok) {
        clearInterval(interval);
        return;
      }
      const data = await res.json();
      
      chrome.runtime.sendMessage({ action: "JOB_PROGRESS_UPDATE", job: data });

      if (data.status === "completed") {
        clearInterval(interval);
        if (!data.is_batch && (data.file_path || data.filename)) {
          const fileUrl = `${BACKEND_URL}/api/file/${jobId}`;
          const cleanName = sanitizeFilename(data.filename);
          chrome.downloads.download({
            url: fileUrl,
            filename: cleanName,
            saveAs: true
          }, (downloadId) => {
            if (chrome.runtime.lastError) {
              console.error("[AnyDownloader] Chrome download failed:", chrome.runtime.lastError.message);
            }
          });
        } else if (data.is_batch && data.sub_jobs) {
          data.sub_jobs.forEach(subId => trackDownloadProgress(subId));
        }
      } else if (data.status === "failed" || data.status === "cancelled") {
        clearInterval(interval);
      }
    } catch (e) {
      clearInterval(interval);
    }
  }, 1000);
}


