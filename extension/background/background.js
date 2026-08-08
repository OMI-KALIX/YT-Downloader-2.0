import { convertToNetscapeCookies } from '../utils/cookie_exporter.js';
import { nativeClient } from '../native/messaging.js';

// Default cloud control plane URL
let CLOUD_CONTROL_URL = "https://youtube-downloader-extension-bul7.onrender.com";

const activeJobsMap = new Map();
let currentActiveJob = null;

function extractYouTubeId(url) {
  if (!url) return "";
  let match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  return match ? match[1] : "";
}

function fetchOembedTitle(url, callback) {
  if (!url || (!url.includes("youtube.com") && !url.includes("youtu.be"))) return;
  const oembedUrl = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
  fetch(oembedUrl)
    .then(r => r.json())
    .then(data => {
      if (data && data.title) {
        callback(data.title, data.author_name);
      }
    })
    .catch(() => {});
}

function updateActiveJobStorage(jobData) {
  currentActiveJob = jobData;
  if (jobData === null) {
    chrome.storage.local.remove(["activeJob"]);
  } else {
    chrome.storage.local.set({ activeJob: jobData });
  }
}

// Universal History Logger - Matches primarily by URL so completion always updates the correct item!
function saveHistoryItem(item) {
  if (!item) return;
  const targetUrl = item.url || (item.job_id ? (activeJobsMap.get(item.job_id) || {}).url : "");
  if (!targetUrl && !item.job_id) return;

  chrome.storage.local.get(["downloadHistory"], (res) => {
    let history = res.downloadHistory || [];
    
    // Find index matching URL first, or matching job_id
    let idx = -1;
    if (targetUrl) {
      idx = history.findIndex(h => h.url && (h.url === targetUrl || extractYouTubeId(h.url) === extractYouTubeId(targetUrl)));
    }
    if (idx < 0 && item.job_id) {
      idx = history.findIndex(h => h.job_id && h.job_id === item.job_id);
    }

    let titleToSave = item.title;
    if (idx >= 0 && history[idx].title && !history[idx].title.startsWith("YouTube Video [") && (!titleToSave || titleToSave.startsWith("YouTube Video ["))) {
      titleToSave = history[idx].title;
    }

    if (!titleToSave || titleToSave.includes("Extracting video details") || titleToSave.includes("Loading metadata")) {
      const vId = extractYouTubeId(targetUrl);
      titleToSave = vId ? `YouTube Video [${vId}]` : (targetUrl || "YouTube Video");
    }

    const newItem = {
      job_id: item.job_id || (idx >= 0 ? history[idx].job_id : `job_${Date.now()}`),
      url: targetUrl || (idx >= 0 ? history[idx].url : ""),
      title: titleToSave,
      format: item.format || (idx >= 0 ? history[idx].format : "1080p"),
      status: item.status || (idx >= 0 ? history[idx].status : "downloading"),
      timestamp: item.timestamp || (idx >= 0 ? history[idx].timestamp : new Date().toLocaleString()),
      ...item
    };
    newItem.title = titleToSave;
    newItem.url = targetUrl || newItem.url;

    if (idx >= 0) {
      history[idx] = { ...history[idx], ...newItem };
    } else {
      history.unshift(newItem);
    }

    if (history.length > 50) history = history.slice(0, 50);
    chrome.storage.local.set({ downloadHistory: history });

    // Fetch oEmbed title if title is still generic
    if (newItem.url && titleToSave.startsWith("YouTube Video [")) {
      fetchOembedTitle(newItem.url, (realTitle) => {
        if (realTitle) {
          saveHistoryItem({ url: newItem.url, title: realTitle });
        }
      });
    }
  });
}

// Keep-alive heartbeat so Manifest V3 service worker stays awake during active downloads
setInterval(() => {
  if (currentActiveJob) {
    try {
      nativeClient.connect();
    } catch (e) {}
  }
}, 15000);

// Register native message event listener to broadcast progress updates & maintain persistent history
nativeClient.addEventListener((msg) => {
  const reqId = msg.id;
  const activeJob = activeJobsMap.get(reqId) || {};
  const jobUrl = activeJob.url || msg.payload.url;

  if (msg.event === "progress" || msg.event === "download_started") {
    const jobState = {
      job_id: reqId,
      status: msg.payload.state || msg.payload.status || "downloading",
      percent: msg.payload.percent || 1,
      speed: msg.payload.speed || "Connecting...",
      eta: msg.payload.eta || "Calculating...",
      url: jobUrl,
      title: activeJob.title,
    };

    updateActiveJobStorage(jobState);

    chrome.runtime.sendMessage({
      action: "JOB_PROGRESS_UPDATE",
      job: jobState
    }).catch(() => {});

    saveHistoryItem({
      job_id: reqId,
      url: jobUrl,
      title: activeJob.title,
      status: msg.payload.state || "downloading",
      percent: msg.payload.percent,
    });
  } else if (msg.event === "completed") {
    const completedJob = {
      job_id: reqId,
      status: "completed",
      percent: 100,
      filename: msg.payload.filename,
    };

    updateActiveJobStorage(completedJob);

    chrome.runtime.sendMessage({
      action: "JOB_PROGRESS_UPDATE",
      job: completedJob
    }).catch(() => {});

    saveHistoryItem({
      job_id: reqId,
      url: jobUrl,
      title: msg.payload.filename || activeJob.title,
      status: "completed",
      percent: 100,
      filename: msg.payload.filename,
    });

    activeJobsMap.delete(reqId);

    // Clear active job storage after 4 seconds so subsequent downloads start clean
    setTimeout(() => {
      if (currentActiveJob && currentActiveJob.job_id === reqId) {
        updateActiveJobStorage(null);
      }
    }, 4000);
  } else if (msg.event === "cancelled") {
    const cancelledJob = {
      job_id: reqId,
      status: "cancelled",
      percent: 0,
    };

    updateActiveJobStorage(cancelledJob);

    chrome.runtime.sendMessage({
      action: "JOB_PROGRESS_UPDATE",
      job: cancelledJob
    }).catch(() => {});

    saveHistoryItem({
      job_id: reqId,
      url: jobUrl,
      status: "cancelled",
    });

    activeJobsMap.delete(reqId);
    setTimeout(() => updateActiveJobStorage(null), 2000);
  } else if (msg.event === "error") {
    const failedJob = {
      job_id: reqId,
      status: "failed",
      error: msg.payload.message || msg.payload.code,
    };

    updateActiveJobStorage(failedJob);

    chrome.runtime.sendMessage({
      action: "JOB_PROGRESS_UPDATE",
      job: failedJob
    }).catch(() => {});

    saveHistoryItem({
      job_id: reqId,
      url: jobUrl,
      status: "failed",
      error: msg.payload.message,
    });

    activeJobsMap.delete(reqId);
    setTimeout(() => updateActiveJobStorage(null), 2000);
  }
});

// Auto connect to native agent host
try {
  nativeClient.connect();
} catch (e) {}

// Handle incoming UI messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_ACTIVE_JOB") {
    sendResponse({ activeJob: currentActiveJob });
    return true;
  }

  if (request.action === "CHECK_AGENT_STATUS") {
    if (nativeClient.port || currentActiveJob) {
      sendResponse({ success: true, isReady: true });
      return true;
    }
    nativeClient.sendRequest("status", {}, 5000)
      .then(res => sendResponse({ success: true, isReady: true, status: res }))
      .catch(err => sendResponse({ success: false, isReady: false, error: err.message }));
    return true;
  }

  if (request.action === "FETCH_FORMATS") {
    nativeClient.sendRequest("get_formats", { url: request.url }, 45000)
      .then(res => {
        if (res && res.title) {
          saveHistoryItem({
            url: request.url,
            title: res.title,
          });
        }
        sendResponse({ success: true, data: res });
      })
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === "START_DOWNLOAD") {
    const videoId = extractYouTubeId(request.url);
    const thumbUrl = videoId ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg` : "";

    const jobId = `job_${Date.now()}`;
    const historyItem = {
      job_id: jobId,
      url: request.url,
      title: request.title || "YouTube Video",
      thumbnail: thumbUrl,
      format: request.format_id || "1080p",
      status: "downloading",
      timestamp: new Date().toLocaleString(),
    };

    const initialJob = {
      job_id: jobId,
      status: "CONNECTING TO YOUTUBE",
      percent: 1,
      speed: "Connecting...",
      eta: "Calculating...",
      url: request.url,
      title: request.title || "YouTube Video",
    };

    updateActiveJobStorage(initialJob);

    activeJobsMap.set(jobId, historyItem);
    saveHistoryItem(historyItem);

    // Broadcast instant progress update right away
    chrome.runtime.sendMessage({
      action: "JOB_PROGRESS_UPDATE",
      job: initialJob
    }).catch(() => {});

    nativeClient.sendRequest("download", { url: request.url, format: request.format_id || "1080p" }, 30000)
      .then(res => {
        const finalId = res.id || res.job_id || jobId;
        activeJobsMap.set(finalId, historyItem);
        sendResponse({ success: true, jobId: finalId });
      })
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === "CANCEL_JOB") {
    updateActiveJobStorage(null);
    nativeClient.sendRequest("cancel", { job_id: request.jobId }, 3000)
      .then(res => sendResponse({ success: true, data: res }))
      .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }

  if (request.action === "WAKE_BACKEND" || request.action === "CHECK_BACKEND_HEALTH") {
    if (nativeClient.port || currentActiveJob) {
      sendResponse({ isOnline: true, status: "online", native: true });
      return true;
    }
    nativeClient.sendRequest("status", {}, 5000)
      .then(res => sendResponse({ isOnline: true, status: "online", native: true }))
      .catch(err => sendResponse({ isOnline: false, status: "offline", native: false, error: err.message }));
    return true;
  }
});
