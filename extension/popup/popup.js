document.addEventListener("DOMContentLoaded", () => {
  const mainView = document.getElementById("main-view");
  const settingsView = document.getElementById("settings-view");
  const toggleSettingsBtn = document.getElementById("toggle-settings");

  const titleEl = document.getElementById("title");
  const uploaderEl = document.getElementById("uploader");
  const thumbEl = document.getElementById("thumb");
  const qualitySelect = document.getElementById("quality-select");
  const downloadBtn = document.getElementById("download-btn");
  
  const progressSection = document.getElementById("progress-section");
  const progressStatus = document.getElementById("progress-status");
  const progressPercent = document.getElementById("progress-percent");
  const progressFill = document.getElementById("progress-fill");
  const progressSpeed = document.getElementById("progress-speed");
  const progressEta = document.getElementById("progress-eta");
  const statusError = document.getElementById("status-error");

  const backendUrlInput = document.getElementById("backend-url");
  const saveSettingsBtn = document.getElementById("save-settings-btn");

  let currentTabUrl = "";

  // Load saved backend URL
  chrome.storage.local.get(["backendUrl"], (res) => {
    if (res.backendUrl) {
      backendUrlInput.value = res.backendUrl;
    }
  });

  // Settings view toggle
  toggleSettingsBtn.addEventListener("click", () => {
    if (settingsView.classList.contains("hidden")) {
      settingsView.classList.remove("hidden");
      mainView.classList.add("hidden");
    } else {
      settingsView.classList.add("hidden");
      mainView.classList.remove("hidden");
    }
  });

  saveSettingsBtn.addEventListener("click", () => {
    const url = backendUrlInput.value.trim().replace(/\/$/, "");
    if (url) {
      chrome.storage.local.set({ backendUrl: url }, () => {
        settingsView.classList.add("hidden");
        mainView.classList.remove("hidden");
      });
    }
  });

  const backendStatusBanner = document.getElementById("backend-status-banner");
  const backendStatusText = document.getElementById("backend-status-text");

  // Check Backend Health on Popup Open
  function checkBackendStatus() {
    chrome.runtime.sendMessage({ action: "CHECK_BACKEND_HEALTH" }, (res) => {
      if (res) {
        updateBackendBanner(res.status, res.attempt);
      }
    });
  }

  function updateBackendBanner(status, attempt) {
    if (status === "online") {
      backendStatusBanner.className = "backend-banner online";
      backendStatusBanner.querySelector(".banner-spinner").style.display = "none";
      backendStatusText.textContent = "Cloud Backend Online & Ready";
      downloadBtn.disabled = false;
      setTimeout(() => {
        backendStatusBanner.classList.add("hidden");
      }, 3000);
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
      backendStatusText.textContent = "Backend offline or unreachable. Please check settings.";
      downloadBtn.disabled = true;
    }
  }

  function loadVideoFormats() {
    if (!currentTabUrl || !currentTabUrl.includes("youtube.com/watch")) return;
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
          }
        }
      }
    );
  }

  // Initial Health Check
  checkBackendStatus();

  // Query active tab
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || !tabs[0]) return;
    const tab = tabs[0];
    currentTabUrl = tab.url || "";

    if (currentTabUrl.includes("youtube.com/watch")) {
      titleEl.textContent = tab.title ? tab.title.replace("- YouTube", "").trim() : "YouTube Video";
      uploaderEl.textContent = "YouTube Video";
      loadVideoFormats();
    } else {
      titleEl.textContent = "Please open a YouTube watch page";
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

    chrome.runtime.sendMessage(
      {
        action: "START_DOWNLOAD",
        url: currentTabUrl,
        format_id: selectedFormat
      },
      (res) => {
        if (!res || !res.success) {
          showError(res ? res.error : "Failed to start download");
          downloadBtn.disabled = false;
          downloadBtn.innerHTML = "<span>Download Now</span>";
        }
      }
    );
  });

  // Messages listener (backend status updates & job progress)
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === "BACKEND_STATUS_UPDATE") {
      updateBackendBanner(msg.status, msg.attempt);
    }

    if (msg.action === "JOB_PROGRESS_UPDATE" && msg.job) {
      const job = msg.job;
      progressSection.style.display = "block";
      progressStatus.textContent = job.status.toUpperCase();
      progressPercent.textContent = `${job.percent}%`;
      progressFill.style.width = `${job.percent}%`;
      progressSpeed.textContent = job.speed || "0 MB/s";
      progressEta.textContent = `ETA: ${job.eta || "--"}`;

      if (job.status === "completed") {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = "<span>Downloaded!</span>";
        setTimeout(() => {
          downloadBtn.innerHTML = "<span>Download Now</span>";
        }, 3000);
      } else if (job.status === "failed") {
        showError(job.error || "Download failed");
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = "<span>Retry Download</span>";
      }
    }
  });

  function showError(msg) {
    statusError.textContent = msg;
    statusError.classList.remove("hidden");
  }
});
