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

    // Dropdown menu
    const menu = document.createElement("div");
    menu.className = "yt-downloader-menu";
    menu.innerHTML = `
      <div class="yt-downloader-menu-item" data-format="bestvideo+bestaudio/best">
        <span>Video (Best Quality)</span>
        <span class="badge">HD</span>
      </div>
      <div class="yt-downloader-menu-item" data-format="bestaudio/best">
        <span>Audio Only</span>
        <span class="badge">MP3</span>
      </div>
    `;

    btnWrapper.appendChild(btn);
    btnWrapper.appendChild(menu);

    actionsContainer.appendChild(btnWrapper);

    // Toggle menu
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("show");
    });

    // Close menu when clicking outside
    document.addEventListener("click", () => {
      menu.classList.remove("show");
    });

    // Handle format selection
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

  // Listen for progress updates
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.action === "JOB_PROGRESS_UPDATE" && msg.job) {
      const btn = document.getElementById("yt-downloader-btn");
      if (btn) {
        if (msg.job.status === "downloading") {
          btn.querySelector("span").textContent = `${msg.job.percent}%`;
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
