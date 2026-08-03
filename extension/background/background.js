import { convertToNetscapeCookies } from '../utils/cookie_exporter.js';

// Default backend URL (configurable via storage)
let BACKEND_URL = "https://youtube-downloader-extension-bul7.onrender.com";

// Load custom backend URL if set
chrome.storage.local.get(["backendUrl"], (res) => {
  if (res.backendUrl) {
    BACKEND_URL = res.backendUrl.replace(/\/$/, "");
  }
});

chrome.storage.onChanged.addListener((changes) => {
  if (changes.backendUrl) {
    BACKEND_URL = changes.backendUrl.newValue.replace(/\/$/, "");
  }
});

// Extract cookies for YouTube domain
async function getYouTubeNetscapeCookies() {
  return new Promise((resolve) => {
    chrome.cookies.getAll({ domain: ".youtube.com" }, (cookies) => {
      if (chrome.runtime.lastError || !cookies) {
        logger.error("Failed to get cookies:", chrome.runtime.lastError);
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
      
      // If offline/sleeping, poll up to 30 times (60s)
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
    return true; // Keep channel open for async response
  }

  if (request.action === "FETCH_FORMATS") {
    (async () => {
      try {
        const cookies = await getYouTubeNetscapeCookies();
        const res = await fetch(`${BACKEND_URL}/api/formats`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: request.url, cookies })
        });
        const data = await res.json();
        sendResponse({ success: true, data: data.data });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    })();
    return true;
  }

  if (request.action === "START_DOWNLOAD") {
    (async () => {
      try {
        const cookies = await getYouTubeNetscapeCookies();
        const res = await fetch(`${BACKEND_URL}/api/download`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: request.url,
            format_id: request.format_id || "bestvideo+bestaudio/best",
            cookies
          })
        });
        const data = await res.json();
        
        if (data.job_id) {
          sendResponse({ success: true, jobId: data.job_id });
          pollDownloadProgress(data.job_id);
        } else {
          sendResponse({ success: false, error: "No job ID returned" });
        }
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

// Poll download progress until complete, then trigger chrome.downloads
async function pollDownloadProgress(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/progress/${jobId}`);
      if (!res.ok) {
        clearInterval(interval);
        return;
      }
      const data = await res.json();
      
      // Notify popup or content scripts
      chrome.runtime.sendMessage({ action: "JOB_PROGRESS_UPDATE", job: data });

      if (data.status === "completed") {
        clearInterval(interval);
        // Trigger browser download
        const fileUrl = `${BACKEND_URL}/api/file/${jobId}`;
        chrome.downloads.download({
          url: fileUrl,
          filename: data.filename || "youtube_download",
          saveAs: true
        });
      } else if (data.status === "failed") {
        clearInterval(interval);
      }
    } catch (e) {
      clearInterval(interval);
    }
  }, 1000);
}
