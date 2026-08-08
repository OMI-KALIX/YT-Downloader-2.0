# ⚙️ YT Downloader Native Agent Installation Guide

## 1. Load Unpacked Browser Extension (100% Automatic Setup)

1. Open Chrome or Edge and navigate to `chrome://extensions` or `edge://extensions`.
2. Enable **Developer mode** toggle in the top right corner.
3. Click **Load unpacked** and select the [`extension/`](../extension/) directory from this repository.
4. Because a fixed manifest key is pre-configured, Chrome/Edge will **automatically assign the fixed Extension ID**:
   `pgnbdcmmbmmolimdfhhffifcbnkobifn`

---

## 2. 1-Click Agent Setup (Zero Configuration)

1. Double-click `install.bat` inside `dist/YT-Downloader-Setup/` (or run `install.ps1` in PowerShell):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\installer\scripts\install.ps1
   ```

2. That's it! The installer automatically registers Chrome & Edge Native Messaging host registry keys pointing to your unpacked extension. No manual typing, copying, or ID entering required!

---

## 3. Uninstallation

To remove registry host entries and clean up installed files:
```powershell
powershell -ExecutionPolicy Bypass -File .\installer\scripts\uninstall.ps1
```
