document.addEventListener("DOMContentLoaded", () => {
  const mainView = document.getElementById("main-view");
  const historyView = document.getElementById("history-view");
  const settingsView = document.getElementById("settings-view");

  const tabDownloaderBtn = document.getElementById("tab-downloader");
  const tabHistoryBtn = document.getElementById("tab-history");
  const tabSettingsBtn = document.getElementById("tab-settings");

  const titleEl = document.getElementById("title");
  const uploaderEl = document.getElementById("uploader");
  const thumbEl = document.getElementById("thumb");
  const qualitySelect = document.getElementById("quality-select");
  const scheduleSecondsInput = document.getElementById("schedule-seconds");
  const downloadBtn = document.getElementById("download-btn");
  
  const progressSection = document.getElementById("progress-section");
  const progressStatus = document.getElementById("progress-status");
  const progressPercent = document.getElementById("progress-percent");
  const progressFill = document.getElementById("progress-fill");
  const progressSpeed = document.getElementById("progress-speed");
  const progressEta = document.getElementById("progress-eta");
  const statusError = document.getElementById("status-error");

  const historyList = document.getElementById("history-list");
  const clearHistoryBtn = document.getElementById("clear-history-btn");

  const backendUrlInput = document.getElementById("backend-url");
  const apiKeyInput = document.getElementById("api-key-input");
  const saveSettingsBtn = document.getElementById("save-settings-btn");

  let currentTabUrl = "";
  let isPlaylistUrl = false;

  // Load saved settings & quality preference
  chrome.storage.local.get(["backendUrl", "apiKey", "qualityPref"], (res) => {
    if (res.backendUrl) backendUrlInput.value = res.backendUrl;
    if (res.apiKey) apiKeyInput.value = res.apiKey;
    if (res.qualityPref) qualitySelect.value = res.qualityPref;
  });

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

  // Save Settings
  saveSettingsBtn.addEventListener("click", () => {
    const url = backendUrlInput.value.trim().replace(/\/$/, "");
    const key = apiKeyInput.value.trim();
    chrome.storage.local.set({ backendUrl: url, apiKey: key }, () => {
      switchTab(mainView, tabDownloaderBtn);
    });
  });

  // Remember Quality Preference change
  qualitySelect.addEventListener("change", () => {
    chrome.storage.local.set({ qualityPref: qualitySelect.value });
  });

  const backendStatusBanner = document.getElementById("backend-status-banner");
  const backendStatusText = document.getElementById("backend-status-text");

  function checkBackendStatus() {
    chrome.runtime.sendMessage({ action: "CHECK_BACKEND_HEALTH" }, (res) => {
      if (res) updateBackendBanner(res.status, res.attempt);
    });
  }

  function updateBackendBanner(status, attempt) {
    if (status === "online") {
      backendStatusBanner.className = "backend-banner online";
      backendStatusBanner.querySelector(".banner-spinner").style.display = "none";
      backendStatusText.textContent = "Cloud Backend Online & Ready";
      downloadBtn.disabled = false;
      setTimeout(() => backendStatusBanner.classList.add("hidden"), 3000);
      loadVideoFormats();
    } else if (status === "waking") {
      backendStatusBanner.className = "backend-banner";
      backendStatusBanner.querySelector(".banner-spinner").style.display = "block";
      backendStatusBanner.classList.remove("hidden");
      backendStatusText.textContent = `Waking up cloud backend (Render cold start)... ${attempt ? `Attempt #${attempt}` : 'Please wait'}`;
      downloadBtn.disabled = true;
    } else if (status === "offline") {
      backendStatusBanner.className = "backend-banner";
      backendStatusBanner.querySelector(".banner-spinner").style.display = "none";
      backendStatusBanner.classList.remove("hidden");
      backendStatusText.textContent = "Backend offline or unreachable. Check settings.";
      downloadBtn.disabled = true;
    }
  }

  function loadVideoFormats() {
    if (!currentTabUrl || !currentTabUrl.includes("youtube.com")) return;
    chrome.runtime.sendMessage(
      { action: "FETCH_FORMATS", url: currentTabUrl },
      (response) => {
        if (response && response.success && response.data) {
          const data = response.data;
          if (data.title) titleEl.textContent = data.title;
          if (data.uploader) uploaderEl.textContent = data.uploader;
          if (data.thumbnail) thumbEl.src = data.thumbnail;

          if (data.formats && data.formats.length > 0) {
            qualitySelect.innerHTML = "";
            const videoGroup = document.createElement("optgroup");
            videoGroup.label = "🎬 Video Quality";
            const audioGroup = document.createElement("optgroup");
            audioGroup.label = "🎵 Audio Quality (MP3)";

            data.formats.forEach((fmt) => {
              const opt = document.createElement("option");
              opt.value = fmt.format_id;
              opt.textContent = fmt.resolution;
              if (fmt.type === "audio" || fmt.format_id.includes("audio")) {
                audioGroup.appendChild(opt);
              } else {
                videoGroup.appendChild(opt);
              }
            });

            if (videoGroup.children.length > 0) qualitySelect.appendChild(videoGroup);
            if (audioGroup.children.length > 0) qualitySelect.appendChild(audioGroup);

            // Restore saved quality if present
            chrome.storage.local.get(["qualityPref"], (res) => {
              if (res.qualityPref && qualitySelect.querySelector(`option[value="${res.qualityPref}"]`)) {
                qualitySelect.value = res.qualityPref;
              }
            });
          }
        } else if (response && !response.success && response.error) {
          if (response.error.includes("auth") || response.error.includes("cookie") || response.error.includes("401")) {
            showError("⚠️ YouTube Cookie/Auth expired. Please refresh the YouTube video page.");
          }
        }
      }
    );
  }

  checkBackendStatus();

  // Query active tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || !tabs[0]) return;
    const tab = tabs[0];
    currentTabUrl = tab.url || "";
    isPlaylistUrl = currentTabUrl.includes("list=") || currentTabUrl.includes("/playlist");

    if (currentTabUrl.includes("youtube.com")) {
      titleEl.textContent = tab.title ? tab.title.replace("- YouTube", "").trim() : "YouTube Video";
      uploaderEl.textContent = isPlaylistUrl ? "YouTube Playlist / Batch" : "YouTube Video";
      if (isPlaylistUrl) downloadBtn.innerHTML = "<span>Download Playlist (Batch)</span>";
      loadVideoFormats();
    } else {
      titleEl.textContent = "Please open a YouTube watch or playlist page";
      uploaderEl.textContent = "No video detected";
      downloadBtn.disabled = true;
    }
  });

  // Download Action
  downloadBtn.addEventListener("click", () => {
    if (!currentTabUrl) return;

    statusError.classList.add("hidden");
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = `<div class="loader"></div> Processing...`;
    progressSection.style.display = "block";

    const selectedFormat = qualitySelect.value;
    const delaySec = parseInt(scheduleSecondsInput.value || "0", 10);
    const actionType = isPlaylistUrl ? "START_BATCH_DOWNLOAD" : "START_DOWNLOAD";

    chrome.runtime.sendMessage(
      {
        action: actionType,
        url: currentTabUrl,
        format_id: selectedFormat,
        delay_seconds: delaySec
      },
      (res) => {
        if (!res || !res.success) {
          showError(res ? res.error : "Failed to start download");
          downloadBtn.disabled = false;
          downloadBtn.innerHTML = "<span>Download Now</span>";
        } else {
          saveToHistory({
            title: titleEl.textContent,
            url: currentTabUrl,
            format: selectedFormat,
            status: "started",
            timestamp: new Date().toLocaleTimeString()
          });
        }
      }
    );
  });

  // Messages listener
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === "BACKEND_STATUS_UPDATE") {
      updateBackendBanner(msg.status, msg.attempt);
    }

    if (msg.action === "JOB_PROGRESS_UPDATE" && msg.job) {
      const job = msg.job;
      progressSection.style.display = "block";
      progressStatus.textContent = (job.status || "Downloading").toUpperCase();
      progressPercent.textContent = `${job.percent || 0}%`;
      progressFill.style.width = `${job.percent || 0}%`;
      progressSpeed.textContent = job.speed || "0 MB/s";
      progressEta.textContent = `ETA: ${job.eta || "--"}`;

      if (job.status === "completed") {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = "<span>Downloaded!</span>";
        updateHistoryItem(currentTabUrl, "completed");
        setTimeout(() => downloadBtn.innerHTML = "<span>Download Now</span>", 3000);
      } else if (job.status === "failed") {
        showError(job.error || "Download failed");
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = "<span>Retry Download</span>";
        updateHistoryItem(currentTabUrl, "failed");
      }
    }
  });

  // History persistence helpers
  function saveToHistory(item) {
    chrome.storage.local.get(["downloadHistory"], (res) => {
      let history = res.downloadHistory || [];
      history.unshift(item);
      if (history.length > 30) history = history.slice(0, 30);
      chrome.storage.local.set({ downloadHistory: history });
    });
  }

  function updateHistoryItem(url, status) {
    chrome.storage.local.get(["downloadHistory"], (res) => {
      let history = res.downloadHistory || [];
      let found = history.find(h => h.url === url);
      if (found) {
        found.status = status;
        chrome.storage.local.set({ downloadHistory: history });
      }
    });
  }

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
        div.innerHTML = `
          <div>
            <div class="history-item-title">${item.title}</div>
            <div class="history-item-meta">${item.timestamp} • ${item.status.toUpperCase()}</div>
          </div>
          <button class="btn-sm retry-btn" data-url="${item.url}">Retry</button>
        `;
        div.querySelector(".retry-btn").addEventListener("click", () => {
          switchTab(mainView, tabDownloaderBtn);
          currentTabUrl = item.url;
          titleEl.textContent = item.title;
          loadVideoFormats();
        });
        historyList.appendChild(div);
      });
    });
  }

  clearHistoryBtn.addEventListener("click", () => {
    chrome.storage.local.set({ downloadHistory: [] }, () => renderHistory());
  });

  function showError(msg) {
    statusError.textContent = msg;
    statusError.classList.remove("hidden");
  }
});
