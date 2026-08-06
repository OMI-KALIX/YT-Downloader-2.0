(function () {
  let currentVideoUrl = "";

  function injectDownloadButton() {
    // Check if on watch page
    if (!window.location.pathname.includes("/watch")) return;

    // Find YouTube actions container (Like, Share, etc.)
    const actionsContainer = document.querySelector(
      "#top-level-buttons-computed, ytd-menu-renderer #items"
    );

    if (!actionsContainer) return;
    if (document.getElementById("yt-downloader-btn")) return; // Already injected

    currentVideoUrl = window.location.href;

    // Create Download Button Container
    const btnWrapper = document.createElement("div");
    btnWrapper.style.position = "relative";
    btnWrapper.style.display = "inline-block";

    const btn = document.createElement("button");
    btn.id = "yt-downloader-btn";
    btn.className = "yt-downloader-btn";
    btn.innerHTML = `
      <svg viewBox="0 0 24 24">
        <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
      </svg>
      <span>Download</span>
    `;

    function renderDefaultMenu(menu) {
      menu.innerHTML = `
        <div class="yt-downloader-menu-header">🎬 Video Quality</div>
        <div class="yt-downloader-menu-item" data-format="bestvideo+bestaudio/best">
          <span>🔥 Best Available (4K / HD)</span>
          <span class="badge">BEST</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="bestvideo[height<=1080]+bestaudio/best">
          <span>Full HD (1080p)</span>
          <span class="badge">1080p</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="bestvideo[height<=720]+bestaudio/best">
          <span>HD (720p)</span>
          <span class="badge">720p</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="bestvideo[height<=480]+bestaudio/best">
          <span>480p SD</span>
          <span class="badge">480p</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="bestvideo[height<=360]+bestaudio/best">
          <span>360p SD</span>
          <span class="badge">360p</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="bestvideo[height<=240]+bestaudio/best">
          <span>240p Low</span>
          <span class="badge">240p</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="bestvideo[height<=144]+bestaudio/best">
          <span>144p Very Low</span>
          <span class="badge">144p</span>
        </div>
        <div class="yt-downloader-menu-header">🎵 Audio Quality (MP3)</div>
        <div class="yt-downloader-menu-item" data-format="audio_320k">
          <span>High Quality (320 kbps)</span>
          <span class="badge">MP3</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="audio_192k">
          <span>Medium Quality (192 kbps)</span>
          <span class="badge">MP3</span>
        </div>
        <div class="yt-downloader-menu-item" data-format="audio_128k">
          <span>Standard Quality (128 kbps)</span>
          <span class="badge">MP3</span>
        </div>
      `;
    }

    renderDefaultMenu(menu);

    btnWrapper.appendChild(btn);
    btnWrapper.appendChild(menu);

    actionsContainer.appendChild(btnWrapper);

    function attachMenuListeners() {
      menu.querySelectorAll(".yt-downloader-menu-item").forEach((item) => {
        item.replaceWith(item.cloneNode(true));
      });
      menu.querySelectorAll(".yt-downloader-menu-item").forEach((item) => {
        item.addEventListener("click", (e) => {
          e.stopPropagation();
          menu.classList.remove("show");

          const formatId = item.getAttribute("data-format");
          btn.querySelector("span").textContent = "Starting...";

          chrome.runtime.sendMessage(
            {
              action: "START_DOWNLOAD",
              url: window.location.href,
              format_id: formatId
            },
            (res) => {
              if (res && res.success) {
                btn.querySelector("span").textContent = "Downloading...";
              } else {
                btn.querySelector("span").textContent = "Error!";
                setTimeout(() => {
                  btn.querySelector("span").textContent = "Download";
                }, 3000);
              }
            }
          );
        });
      });
    }

    attachMenuListeners();

    // Fetch dynamic formats from backend if available
    chrome.runtime.sendMessage(
      { action: "FETCH_FORMATS", url: currentVideoUrl },
      (res) => {
        if (res && res.success && res.data && res.data.formats && res.data.formats.length > 0) {
          menu.innerHTML = "";
          
          const videoFormats = res.data.formats.filter(f => f.type !== "audio" && !f.format_id.includes("audio"));
          const audioFormats = res.data.formats.filter(f => f.type === "audio" || f.format_id.includes("audio"));

          if (videoFormats.length > 0) {
            const vHeader = document.createElement("div");
            vHeader.className = "yt-downloader-menu-header";
            vHeader.textContent = "🎬 Video Quality";
            menu.appendChild(vHeader);

            videoFormats.forEach(fmt => {
              const div = document.createElement("div");
              div.className = "yt-downloader-menu-item";
              div.setAttribute("data-format", fmt.format_id);

              let badgeText = "MP4";
              if (fmt.resolution.includes("4K")) badgeText = "4K";
              else if (fmt.resolution.includes("2K")) badgeText = "2K";
              else if (fmt.resolution.includes("1080p")) badgeText = "1080p";
              else if (fmt.resolution.includes("720p")) badgeText = "720p";
              else if (fmt.resolution.includes("480p")) badgeText = "480p";
              else if (fmt.resolution.includes("360p")) badgeText = "360p";
              else if (fmt.resolution.includes("240p")) badgeText = "240p";
              else if (fmt.resolution.includes("144p")) badgeText = "144p";

              div.innerHTML = `<span>${fmt.resolution}</span><span class="badge">${badgeText}</span>`;
              menu.appendChild(div);
            });
          }

          if (audioFormats.length > 0) {
            const aHeader = document.createElement("div");
            aHeader.className = "yt-downloader-menu-header";
            aHeader.textContent = "🎵 Audio Quality (MP3)";
            menu.appendChild(aHeader);

            audioFormats.forEach(fmt => {
              const div = document.createElement("div");
              div.className = "yt-downloader-menu-item";
              div.setAttribute("data-format", fmt.format_id);
              div.innerHTML = `<span>${fmt.resolution}</span><span class="badge">MP3</span>`;
              menu.appendChild(div);
            });
          }

          attachMenuListeners();
        }
      }
    );

    // Toggle menu
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("show");
    });

    // Close menu when clicking outside
    document.addEventListener("click", () => {
      menu.classList.remove("show");
    });
  }

  // Listen for progress updates
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === "JOB_PROGRESS_UPDATE" && msg.job) {
      const btn = document.getElementById("yt-downloader-btn");
      if (btn) {
        if (msg.job.status === "downloading") {
          btn.querySelector("span").textContent = `${msg.job.percent}%`;
        } else if (msg.job.status === "paused") {
          btn.querySelector("span").textContent = "Paused";
        } else if (msg.job.status === "completed") {
          btn.querySelector("span").textContent = "Done!";
          setTimeout(() => {
            btn.querySelector("span").textContent = "Download";
          }, 4000);
        } else if (msg.job.status === "failed") {
          btn.querySelector("span").textContent = "Failed";
          setTimeout(() => {
            btn.querySelector("span").textContent = "Download";
          }, 3000);
        } else if (msg.job.status === "cancelled") {
          btn.querySelector("span").textContent = "Cancelled";
          setTimeout(() => {
            btn.querySelector("span").textContent = "Download";
          }, 3000);
        }
      }
    }
  });

  // Watch for page navigation (YouTube SPA)
  const observer = new MutationObserver(() => {
    if (window.location.href !== currentVideoUrl) {
      injectDownloadButton();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // Automatically trigger cloud backend wake-up on YouTube visit
  chrome.runtime.sendMessage({ action: "WAKE_BACKEND" });

  // Initial attempt
  setTimeout(injectDownloadButton, 1500);
})();
