document.addEventListener("DOMContentLoaded", () => {
  const mainView = document.getElementById("main-view");
  const historyView = document.getElementById("history-view");
  const settingsView = document.getElementById("settings-view");

  const tabDownloaderBtn = document.getElementById("tab-downloader");
  const tabHistoryBtn = document.getElementById("tab-history");
  const tabSettingsBtn = document.getElementById("tab-settings");
  const refreshBtn = document.getElementById("refresh-btn");

  const customUrlInput = document.getElementById("custom-url-input");
  const fetchUrlBtn = document.getElementById("fetch-url-btn");

  const titleEl = document.getElementById("title");
  const uploaderEl = document.getElementById("uploader");
  const thumbEl = document.getElementById("thumb");
  const durationTag = document.getElementById("duration-tag");
  const qualitySelect = document.getElementById("quality-select");
  const downloadBtn = document.getElementById("download-btn");

  const progressSection = document.getElementById("progress-section");
  const progressStatus = document.getElementById("progress-status");
  const progressPercent = document.getElementById("progress-percent");
  const progressFill = document.getElementById("progress-fill");
  const progressSpeed = document.getElementById("progress-speed");
  const progressEta = document.getElementById("progress-eta");
  const statusError = document.getElementById("status-error");

  const jobControls = document.getElementById("job-controls");
  const pauseBtn = document.getElementById("pause-btn");
  const resumeBtn = document.getElementById("resume-btn");
  const cancelBtn = document.getElementById("cancel-btn");

  const historyList = document.getElementById("history-list");
  const clearHistoryBtn = document.getElementById("clear-history-btn");

  const backendUrlInput = document.getElementById("backend-url");
  const apiKeyInput = document.getElementById("api-key-input");
  const saveSettingsBtn = document.getElementById("save-settings-btn");

  const backendStatusBanner = document.getElementById("backend-status-banner");
  const backendStatusText = document.getElementById("backend-status-text");

  let currentTabUrl = "";
  let isPlaylistUrl = false;
  let activeJobId = null;
  let isDownloadActive = false;
  let fetchCounter = 0;

  // Load saved settings
  chrome.storage.local.get(["backendUrl", "apiKey", "qualityPref"], (res) => {
    if (res.backendUrl) backendUrlInput.value = res.backendUrl;
    if (res.apiKey) apiKeyInput.value = res.apiKey;
    if (res.qualityPref) qualitySelect.value = res.qualityPref;
  });

  // Extract YouTube Video ID from URL
  function extractYouTubeId(url) {
    if (!url) return "";
    let match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
    return match ? match[1] : "";
  }

  // Fast YouTube oEmbed lookup for instant video title & channel name
  function fetchFastOembedMetadata(url) {
    if (!url || (!url.includes("youtube.com") && !url.includes("youtu.be"))) return;
    const oembedUrl = `https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`;
    fetch(oembedUrl)
      .then(r => r.json())
      .then(data => {
        if (data && data.title) {
          titleEl.textContent = data.title;
          uploaderEl.textContent = data.author_name || "YouTube Channel";
          saveToHistory({ url: url, title: data.title });
        }
      })
      .catch(() => {});
  }

  function getCleanTitle(rawTitle, fallbackUrl) {
    if (!rawTitle || rawTitle.includes("Extracting video details") || rawTitle.includes("Loading metadata") || rawTitle === "YouTube Video") {
      const vId = extractYouTubeId(fallbackUrl);
      return vId ? `YouTube Video [${vId}]` : (fallbackUrl || "YouTube Video");
    }
    return rawTitle;
  }

  // Save history item locally
  function saveToHistory(item) {
    chrome.storage.local.get(["downloadHistory"], (res) => {
      let history = res.downloadHistory || [];
      let idx = history.findIndex(h => (h.url && item.url && h.url === item.url));
      
      let titleToSave = item.title;
      if (idx >= 0 && history[idx].title && !history[idx].title.startsWith("YouTube Video [") && (!titleToSave || titleToSave.startsWith("YouTube Video ["))) {
        titleToSave = history[idx].title;
      }

      titleToSave = getCleanTitle(titleToSave, item.url);
      const cleanItem = { ...item, title: titleToSave };

      if (idx >= 0) {
        history[idx] = { ...history[idx], ...cleanItem };
      } else {
        history.unshift(cleanItem);
      }
      if (history.length > 50) history = history.slice(0, 50);
      chrome.storage.local.set({ downloadHistory: history });
    });
  }

  // Render job progress dynamically
  function renderProgress(job) {
    if (!job) {
      if (!isDownloadActive) {
        progressSection.style.display = "none";
      }
      return;
    }

    if (job.job_id) activeJobId = job.job_id;
    isDownloadActive = true;
    backendStatusBanner.classList.add("hidden");
    statusError.classList.add("hidden");
    statusError.textContent = "";

    progressSection.style.display = "block";
    progressStatus.textContent = (job.status || "DOWNLOADING").toUpperCase();
    progressPercent.textContent = `${job.percent || 0}%`;
    progressFill.style.width = `${job.percent || 0}%`;
    progressSpeed.textContent = job.speed || "0 MB/s";
    progressEta.textContent = `ETA: ${job.eta || "--"}`;

    if (["downloading", "starting", "extracting", "audio stream", "connecting to youtube", "fetching fragments"].includes((job.status || "").toLowerCase())) {
      jobControls.classList.remove("hidden");
      pauseBtn.classList.remove("hidden");
    } else {
      jobControls.classList.add("hidden");
    }

    if (job.status === "completed") {
      isDownloadActive = false;
      downloadBtn.disabled = false;
      downloadBtn.innerHTML = "<span>✓ Download Complete!</span>";
    } else if (job.status === "cancelled") {
      isDownloadActive = false;
      showError("Download cancelled.");
      downloadBtn.disabled = false;
      downloadBtn.innerHTML = "<span>Download Now</span>";
    } else if (job.status === "failed") {
      isDownloadActive = false;
      showError(job.error || "Download failed");
      downloadBtn.disabled = false;
      downloadBtn.innerHTML = "<span>Retry Download</span>";
    }
  }

  // Check active running job synchronously from local storage & background
  function checkActiveJob() {
    chrome.storage.local.get(["activeJob"], (res) => {
      if (res && res.activeJob) {
        renderProgress(res.activeJob);
      }
    });
  }

  // Reactive listener for live progress updates via chrome.storage
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && changes.activeJob) {
      if (changes.activeJob.newValue) {
        renderProgress(changes.activeJob.newValue);
      } else {
        if (!isDownloadActive) {
          progressSection.style.display = "none";
        }
      }
    }
  });

  // Fast 300ms polling loop for instant UI sync
  setInterval(() => {
    checkActiveJob();
  }, 300);

  // Tab switching logic
  function switchTab(activeView, activeBtn) {
    [mainView, historyView, settingsView].forEach(v => v.classList.add("hidden"));
    [tabDownloaderBtn, tabHistoryBtn, tabSettingsBtn].forEach(b => b.classList.remove("active"));

    activeView.classList.remove("hidden");
    activeBtn.classList.add("active");

    if (activeView === historyView) renderHistory();
  }

  tabDownloaderBtn.addEventListener("click", () => switchTab(mainView, tabDownloaderBtn));
  tabHistoryBtn.addEventListener("click", () => switchTab(historyView, tabHistoryBtn));
  tabSettingsBtn.addEventListener("click", () => switchTab(settingsView, tabSettingsBtn));

  // Manual Refresh Button logic
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      refreshBtn.style.transform = "rotate(360deg)";
      refreshBtn.style.transition = "transform 0.5s";
      setTimeout(() => { refreshBtn.style.transform = "none"; }, 500);

      checkBackendStatus();
      checkActiveJob();
      if (currentTabUrl) loadVideoFormats();
      if (!historyView.classList.contains("hidden")) renderHistory();
    });
  }

  saveSettingsBtn.addEventListener("click", () => {
    const url = backendUrlInput.value.trim().replace(/\/$/, "");
    const key = apiKeyInput.value.trim();
    chrome.storage.local.set({ backendUrl: url, apiKey: key }, () => {
      switchTab(mainView, tabDownloaderBtn);
    });
  });

  qualitySelect.addEventListener("change", () => {
    chrome.storage.local.set({ qualityPref: qualitySelect.value });
  });

  function formatDuration(sec) {
    if (!sec || sec <= 0) return "";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  function checkBackendStatus() {
    if (isDownloadActive) {
      updateBackendBanner("online");
      return;
    }
    chrome.runtime.sendMessage({ action: "CHECK_BACKEND_HEALTH" }, (res) => {
      if (res) {
        updateBackendBanner(res.status, res.attempt, res.error);
      } else {
        updateBackendBanner("offline");
      }
    });
  }

  function updateBackendBanner(status, attempt, errorDetail) {
    if (status === "online" || isDownloadActive) {
      backendStatusBanner.className = "backend-banner online";
      backendStatusBanner.querySelector(".banner-spinner").style.display = "none";
      backendStatusText.textContent = "● Downloader Engine Ready (v2.1)";
      downloadBtn.disabled = false;
      setTimeout(() => backendStatusBanner.classList.add("hidden"), 3000);
    } else {
      backendStatusBanner.className = "backend-banner";
      backendStatusBanner.querySelector(".banner-spinner").style.display = "none";
      backendStatusBanner.classList.remove("hidden");
      const detail = errorDetail ? ` (${errorDetail})` : '';
      backendStatusText.textContent = `Native agent offline${detail}. Click Load or run install.bat.`;
      if (currentTabUrl) downloadBtn.disabled = false;
    }
  }

  function loadVideoFormats() {
    if (!currentTabUrl) return;
    if (!currentTabUrl.includes("youtube.com") && !currentTabUrl.includes("youtu.be")) return;

    // Fast oEmbed Title Lookup
    fetchFastOembedMetadata(currentTabUrl);

    // Instant local thumbnail display
    const videoId = extractYouTubeId(currentTabUrl);
    if (videoId) {
      thumbEl.src = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
    }

    const reqNum = ++fetchCounter;

    chrome.runtime.sendMessage(
      { action: "FETCH_FORMATS", url: currentTabUrl },
      (response) => {
        if (reqNum !== fetchCounter || isDownloadActive) return;

        if (response && response.success && response.data) {
          const data = response.data;
          const formats = Array.isArray(data) ? data : (data.formats || []);

          if (!Array.isArray(data)) {
            if (data.title) {
              titleEl.textContent = data.title;
              saveToHistory({ url: currentTabUrl, title: data.title });
            }
            if (data.uploader) uploaderEl.textContent = data.uploader;
            if (data.thumbnail) {
              thumbEl.src = data.thumbnail.replace("http://", "https://");
            } else if (videoId) {
              thumbEl.src = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
            }
            if (data.duration && durationTag) {
              durationTag.textContent = formatDuration(data.duration);
              durationTag.classList.remove("hidden");
            }
          }

          if (formats.length > 0) {
            qualitySelect.innerHTML = "";
            const videoGroup = document.createElement("optgroup");
            videoGroup.label = "🎬 Video Resolutions (with Sizes)";
            const audioGroup = document.createElement("optgroup");
            audioGroup.label = "🎵 High Quality Audio (MP3)";

            formats.forEach((fmt) => {
              const opt = document.createElement("option");
              opt.value = fmt.id;
              opt.textContent = fmt.resolution;
              if (fmt.type === "audio" || (fmt.extension && fmt.extension.includes("mp3"))) {
                audioGroup.appendChild(opt);
              } else {
                videoGroup.appendChild(opt);
              }
            });

            if (videoGroup.children.length > 0) qualitySelect.appendChild(videoGroup);
            if (audioGroup.children.length > 0) qualitySelect.appendChild(audioGroup);

            chrome.storage.local.get(["qualityPref"], (res) => {
              if (res.qualityPref && qualitySelect.querySelector(`option[value="${res.qualityPref}"]`)) {
                qualitySelect.value = res.qualityPref;
              }
            });
          }
        } else if (response && !response.success && response.error && !isDownloadActive) {
          showError(response.error);
        }
      }
    );
  }

  function processUrl(url) {
    if (!url) return;
    currentTabUrl = url.trim();
    if (customUrlInput) customUrlInput.value = currentTabUrl;
    isPlaylistUrl = currentTabUrl.includes("/playlist") || (currentTabUrl.includes("list=") && !currentTabUrl.includes("watch?v="));
    
    // Fast oEmbed Title Lookup
    fetchFastOembedMetadata(currentTabUrl);

    // Instant thumbnail display
    const videoId = extractYouTubeId(currentTabUrl);
    if (videoId) {
      thumbEl.src = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
    }

    uploaderEl.textContent = isPlaylistUrl ? "YouTube Playlist Batch" : "YouTube Video";
    downloadBtn.disabled = false;
    if (isPlaylistUrl) downloadBtn.innerHTML = "<span>Download Playlist (Batch)</span>";
    else downloadBtn.innerHTML = "<span>Download Now</span>";
    loadVideoFormats();
  }

  if (fetchUrlBtn) {
    fetchUrlBtn.addEventListener("click", () => processUrl(customUrlInput.value));
  }
  if (customUrlInput) {
    customUrlInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") processUrl(customUrlInput.value);
    });
  }

  checkBackendStatus();
  checkActiveJob();

  // Query active tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || !tabs[0]) return;
    const tab = tabs[0];
    const tabUrl = tab.url || "";
    if (tabUrl.includes("youtube.com") || tabUrl.includes("youtu.be")) {
      processUrl(tabUrl);
    }
  });

  // Download Action
  downloadBtn.addEventListener("click", () => {
    if (!currentTabUrl) return;

    isDownloadActive = true;
    backendStatusBanner.classList.add("hidden");
    statusError.classList.add("hidden");
    statusError.textContent = "";
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = `<div class="loader"></div> Starting Download...`;
    
    const selectedFormat = qualitySelect.value;
    const videoId = extractYouTubeId(currentTabUrl);
    const cleanT = getCleanTitle(titleEl.textContent, currentTabUrl);

    const initialJob = {
      job_id: `job_${Date.now()}`,
      status: "CONNECTING TO YOUTUBE",
      percent: 1,
      speed: "Connecting...",
      eta: "Calculating...",
      url: currentTabUrl,
      title: cleanT,
    };

    // Immediately render and persist the new download job so old completed jobs are replaced instantly!
    chrome.storage.local.set({ activeJob: initialJob });
    renderProgress(initialJob);

    // Save clean history immediately
    saveToHistory({
      url: currentTabUrl,
      title: cleanT,
      thumbnail: videoId ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg` : "",
      format: selectedFormat,
      status: "downloading",
      timestamp: new Date().toLocaleString()
    });

    chrome.runtime.sendMessage(
      {
        action: "START_DOWNLOAD",
        url: currentTabUrl,
        title: cleanT,
        format_id: selectedFormat,
      },
      (res) => {
        if (!res || !res.success) {
          isDownloadActive = false;
          showError(res ? res.error : "Failed to start download");
          downloadBtn.disabled = false;
          downloadBtn.innerHTML = "<span>Download Now</span>";
        } else {
          if (res.jobId) activeJobId = res.jobId;
          checkActiveJob();
        }
      }
    );
  });

  pauseBtn.addEventListener("click", () => {
    progressStatus.textContent = "PAUSED";
    pauseBtn.classList.add("hidden");
    resumeBtn.classList.remove("hidden");
  });

  resumeBtn.addEventListener("click", () => {
    progressStatus.textContent = "DOWNLOADING";
    resumeBtn.classList.add("hidden");
    pauseBtn.classList.remove("hidden");
  });

  cancelBtn.addEventListener("click", () => {
    if (activeJobId) {
      chrome.runtime.sendMessage({ action: "CANCEL_JOB", jobId: activeJobId });
    }
    isDownloadActive = false;
    jobControls.classList.add("hidden");
    progressStatus.textContent = "CANCELLED";
    showError("Download cancelled.");
    downloadBtn.disabled = false;
    downloadBtn.innerHTML = "<span>Download Now</span>";
  });

  // Messages listener
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === "JOB_PROGRESS_UPDATE" && msg.job) {
      renderProgress(msg.job);
    }
  });

  // History Renderer with hover full title support
  function renderHistory() {
    chrome.storage.local.get(["downloadHistory"], (res) => {
      const history = res.downloadHistory || [];
      if (history.length === 0) {
        historyList.innerHTML = `<div class="empty-history">No download history yet.</div>`;
        return;
      }
      historyList.innerHTML = "";
      history.forEach(item => {
        const div = document.createElement("div");
        div.className = "history-item";
        const st = (item.status || "DONE").toUpperCase();
        const displayTitle = getCleanTitle(item.title, item.url);

        div.innerHTML = `
          <div>
            <div class="history-item-title" title="${displayTitle}">${displayTitle}</div>
            <div class="history-item-meta">${item.timestamp || ''} • <span class="status-pill status-${st.toLowerCase()}">${st}</span></div>
          </div>
          <button class="btn-sm retry-btn" data-url="${item.url}">Retry</button>
        `;
        div.querySelector(".retry-btn").addEventListener("click", () => {
          saveToHistory({ url: item.url, title: displayTitle, status: "retried" });
          switchTab(mainView, tabDownloaderBtn);
          processUrl(item.url);
        });
        historyList.appendChild(div);
      });
    });
  }

  clearHistoryBtn.addEventListener("click", () => {
    chrome.storage.local.set({ downloadHistory: [] }, () => renderHistory());
  });

  function showError(msg) {
    if (isDownloadActive && msg.includes("timed out")) return;
    statusError.textContent = msg;
    statusError.classList.remove("hidden");
  }
});
