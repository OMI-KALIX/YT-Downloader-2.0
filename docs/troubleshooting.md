# 🛠️ Native Agent Troubleshooting Guide

## Common Issues & Solutions

### 1. `Downloader unavailable` in Extension Popup
- **Cause**: Native Messaging host registry key is missing or pointing to invalid executable location.
- **Fix**: Re-run `install.ps1` in PowerShell to re-register `HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.omikalix.ytdownloader`.

### 2. `INVALID_URL` Error
- **Cause**: The input string is not a valid HTTP/HTTPS YouTube video link or contains forbidden shell parameters.
- **Fix**: Ensure standard YouTube video URLs (`https://www.youtube.com/watch?v=...`) are provided.

### 3. Output files missing
- **Cause**: Output path restriction prevented saving to non-standard directories.
- **Fix**: Downloaded files are saved to default `%USERPROFILE%\Downloads`.
