(function () {
  let currentVideoUrl = "";

  function extractYouTubeFormatsFromPage() {
    let playerResponse = window.ytInitialPlayerResponse;

    if (!playerResponse || !playerResponse.streamingData) {
      const scripts = document.querySelectorAll("script");
      for (const s of scripts) {
        if (s.textContent.includes("ytInitialPlayerResponse = ")) {
          try {
            const jsonStr = s.textContent.split("ytInitialPlayerResponse = ")[1].split(";var ")[0].split(";\n")[0];
            playerResponse = JSON.parse(jsonStr);
            break;
          } catch (e) {}
        }
      }
    }

    if (!playerResponse || !playerResponse.streamingData) return null;

    const streamingData = playerResponse.streamingData;
    const clientFormats = [];
    const videoTitle = playerResponse.videoDetails ? playerResponse.videoDetails.title : document.title.replace(" - YouTube", "");

    // Progressive formats (single stream video+audio)
    if (streamingData.formats) {
      for (const f of streamingData.formats) {
        if (f.url) {
          const height = f.height || 360;
          clientFormats.push({
            format_id: f.formatId || `progressive_${height}p`,
            resolution: `${height}p SD (Direct Browser Download)`,
            height: height,
            type: "progressive",
            url: f.url,
            title: videoTitle
          });
        }
      }
    }

    // Adaptive formats (DASH separate video & audio)
    if (streamingData.adaptiveFormats) {
      let bestAudioUrl = null;
      for (const f of streamingData.adaptiveFormats) {
        if (f.mimeType && f.mimeType.includes("audio") && f.url) {
          bestAudioUrl = f.url;
          break;
        }
      }

      const seenHeights = new Set();
      for (const f of streamingData.adaptiveFormats) {
        if (f.mimeType && f.mimeType.includes("video") && f.height && f.url) {
          if (!seenHeights.has(f.height)) {
            seenHeights.add(f.height);
            let label = `${f.height}p`;
            if (f.height >= 2160) label = "4K Ultra HD (2160p)";
            else if (f.height >= 1440) label = "2K Quad HD (1440p)";
            else if (f.height >= 1080) label = "Full HD (1080p)";
            else if (f.height >= 720) label = "HD (720p)";
            else if (f.height >= 480) label = "480p SD";
            else if (f.height >= 360) label = "360p SD";
            else if (f.height >= 240) label = "240p Low";
            else if (f.height >= 144) label = "144p Very Low";

            clientFormats.push({
              format_id: `adaptive_${f.height}p`,
              resolution: label,
              height: f.height,
              type: "adaptive",
              video_url: f.url,
              audio_url: bestAudioUrl,
              title: videoTitle
            });
          }
        }
      }

      if (bestAudioUrl) {
        clientFormats.push({
          format_id: "client_audio_mp3",
          resolution: "🎵 Audio Stream (MP3)",
          height: 0,
          type: "adaptive",
          video_url: null,
          audio_url: bestAudioUrl,
          title: videoTitle
        });
      }
    }

    clientFormats.sort((a, b) => (b.height || 0) - (a.height || 0));
    return { title: videoTitle, formats: clientFormats };
  }

  function injectDownloadButton() {
    if (!window.location.pathname.includes("/watch")) return;

    const actionsContainer = document.querySelector(
      "#top-level-buttons-computed, ytd-menu-renderer #items"
    );

    if (!actionsContainer) return;
    if (document.getElementById("yt-downloader-btn")) return; // Already injected

    currentVideoUrl = window.location.href;

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

    const menu = document.createElement("div");
    menu.className = "yt-downloader-menu";

    btnWrapper.appendChild(btn);
    btnWrapper.appendChild(menu);
    actionsContainer.appendChild(btnWrapper);

    // Try client-side DOM extraction first
    const clientData = extractYouTubeFormatsFromPage();

    if (clientData && clientData.formats && clientData.formats.length > 0) {
      console.log(`[AnyDownloader] Extracted ${clientData.formats.length} formats client-side on residential IP.`);
      renderClientMenu(menu, clientData, btn);
    } else {
      console.log("[AnyDownloader] Client-side extraction unavailable. Falling back to server probe.");
      renderDefaultMenu(menu, btn);
    }

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("show");
    });

    document.addEventListener("click", () => {
      menu.classList.remove("show");
    });
  }

  function renderClientMenu(menu, clientData, btn) {
    menu.innerHTML = "";

    const vHeader = document.createElement("div");
    vHeader.className = "yt-downloader-menu-header";
    vHeader.textContent = "🎬 Video Quality (Residential Direct)";
    menu.appendChild(vHeader);

    clientData.formats.forEach((fmt) => {
      const div = document.createElement("div");
      div.className = "yt-downloader-menu-item";
      
      let badge = "MP4";
      if (fmt.type === "progressive") badge = "FAST";
      else if (fmt.resolution.includes("4K")) badge = "4K";
      else if (fmt.resolution.includes("1080p")) badge = "1080p";
      else if (fmt.resolution.includes("MP3")) badge = "MP3";

      div.innerHTML = `<span>${fmt.resolution}</span><span class="badge">${badge}</span>`;
      
      div.addEventListener("click", (e) => {
        e.stopPropagation();
        menu.classList.remove("show");
        btn.querySelector("span").textContent = "Starting...";

        if (fmt.type === "progressive" && fmt.url) {
          // Pure client-side download via browser download manager
          chrome.runtime.sendMessage(
            {
              action: "START_CLIENT_DOWNLOAD",
              url: fmt.url,
              title: fmt.title
            },
            (res) => {
              if (res && res.success) {
                btn.querySelector("span").textContent = "Downloading...";
                setTimeout(() => { btn.querySelector("span").textContent = "Download"; }, 3000);
              } else {
                btn.querySelector("span").textContent = "Error!";
                setTimeout(() => { btn.querySelector("span").textContent = "Download"; }, 3000);
              }
            }
          );
        } else {
          // Direct stream muxing via /api/mux
          chrome.runtime.sendMessage(
            {
              action: "START_MUX_DOWNLOAD",
              video_url: fmt.video_url,
              audio_url: fmt.audio_url,
              title: fmt.title,
              format_id: fmt.format_id
            },
            (res) => {
              if (res && res.success) {
                btn.querySelector("span").textContent = "Downloading...";
              } else {
                btn.querySelector("span").textContent = "Error!";
                setTimeout(() => { btn.querySelector("span").textContent = "Download"; }, 3000);
              }
            }
          );
        }
      });

      menu.appendChild(div);
    });
  }

  function renderDefaultMenu(menu, btn) {
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
      <div class="yt-downloader-menu-header">🎵 Audio Quality (MP3)</div>
      <div class="yt-downloader-menu-item" data-format="audio_320k">
        <span>High Quality (320 kbps)</span>
        <span class="badge">MP3</span>
      </div>
    `;

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
              setTimeout(() => { btn.querySelector("span").textContent = "Download"; }, 3000);
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
        } else if (msg.job.status === "paused") {
          btn.querySelector("span").textContent = "Paused";
        } else if (msg.job.status === "completed") {
          btn.querySelector("span").textContent = "Done!";
          setTimeout(() => { btn.querySelector("span").textContent = "Download"; }, 4000);
        } else if (msg.job.status === "failed") {
          btn.querySelector("span").textContent = "Failed";
          setTimeout(() => { btn.querySelector("span").textContent = "Download"; }, 3000);
        } else if (msg.job.status === "cancelled") {
          btn.querySelector("span").textContent = "Cancelled";
          setTimeout(() => { btn.querySelector("span").textContent = "Download"; }, 3000);
        }
      }
    }
  });

  const observer = new MutationObserver(() => {
    if (window.location.href !== currentVideoUrl) {
      injectDownloadButton();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  chrome.runtime.sendMessage({ action: "WAKE_BACKEND" });

  setTimeout(injectDownloadButton, 1500);
})();
