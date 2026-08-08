# YT Downloader Native Agent PowerShell Uninstaller
$ErrorActionPreference = "Continue"

$InstallDir = "$env:LOCALAPPDATA\YTDownloader"
$HostName = "com.omikalix.ytdownloader"

Write-Host "=========================================" -ForegroundColor Yellow
Write-Host " Uninstalling YT Downloader Native Agent " -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Yellow

# Stop any running process instance first
Get-Process -Name "downloader-agent" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

# 1. Unregister Chrome & Edge registry keys
$ChromeRegKey = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"
$EdgeRegKey = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName"

if (Test-Path $ChromeRegKey) {
    Remove-Item -Path $ChromeRegKey -Recurse -Force
    Write-Host "[+] Removed Chrome Native Messaging Host registry key" -ForegroundColor Green
}

if (Test-Path $EdgeRegKey) {
    Remove-Item -Path $EdgeRegKey -Recurse -Force
    Write-Host "[+] Removed Edge Native Messaging Host registry key" -ForegroundColor Green
}

# 2. Remove installation files
if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force
    Write-Host "[+] Removed installation directory: $InstallDir" -ForegroundColor Green
}

Write-Host "`n[OK] YT Downloader Native Agent uninstalled." -ForegroundColor Green
