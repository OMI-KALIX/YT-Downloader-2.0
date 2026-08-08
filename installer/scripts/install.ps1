# YT Downloader Native Agent PowerShell Automated Installer
param(
    [string]$ExtensionId = "pgnbdcmmbmmolimdfhhffifcbnkobifn"
)

$ErrorActionPreference = "Stop"

$InstallDir = "$env:LOCALAPPDATA\YTDownloader"
$HostName = "com.omikalix.ytdownloader"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Installing YT Downloader Native Agent   " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Create target installation directory
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Host "[+] Created target directory: $InstallDir" -ForegroundColor Green
}

# Stop any running instance of downloader-agent to release file locks before copying
Get-Process -Name "downloader-agent" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

# 2. Locate source files
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = (Get-Item $ScriptDir).Parent.Parent.FullName

$SourceAgent = "$RootDir\native-agent\dist\downloader-agent.exe"
if (-not (Test-Path $SourceAgent)) {
    $SourceAgent = "$RootDir\dist\downloader-agent.exe"
}
if (-not (Test-Path $SourceAgent)) {
    $SourceAgent = "$ScriptDir\downloader-agent.exe"
}

# 3. Copy binaries to install dir
if (Test-Path $SourceAgent) {
    Copy-Item -Path $SourceAgent -Destination "$InstallDir\downloader-agent.exe" -Force
    Write-Host "[+] Copied downloader-agent.exe" -ForegroundColor Green
} else {
    Write-Host "[!] Warning: downloader-agent.exe source binary not found at $SourceAgent. Please run build.py first." -ForegroundColor Yellow
}

# Copy FFmpeg / yt-dlp binaries if present
$BinDir = "$RootDir\bin"
if (Test-Path "$BinDir\ffmpeg.exe") {
    Copy-Item -Path "$BinDir\ffmpeg.exe" -Destination "$InstallDir\ffmpeg.exe" -Force
    Write-Host "[+] Copied ffmpeg.exe" -ForegroundColor Green
}

# 4. Configure allowed_origins array automatically
$CleanId = $ExtensionId.Trim()
if ($CleanId -notlike "chrome-extension://*") {
    $CleanId = "chrome-extension://$CleanId/"
}
if (-not $CleanId.EndsWith("/")) {
    $CleanId = "$CleanId/"
}
$AllowedOrigins = @($CleanId)

# 5. Generate installed manifest with absolute binary path
$TargetManifestPath = "$InstallDir\$HostName.json"

$ManifestContent = @{
    "name" = $HostName
    "description" = "YT Downloader Native Agent Host"
    "path" = "$InstallDir\downloader-agent.exe"
    "type" = "stdio"
    "allowed_origins" = $AllowedOrigins
}

$ManifestJson = ConvertTo-Json $ManifestContent -Depth 5
Set-Content -Path $TargetManifestPath -Value $ManifestJson -Encoding UTF8
Write-Host "[+] Manifest configured automatically for Extension ID: $CleanId" -ForegroundColor Green

# 6. Register in Windows Registry for Chrome and Edge
$ChromeRegKey = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName"
$EdgeRegKey = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName"

New-Item -Path $ChromeRegKey -Force | Out-Null
Set-ItemProperty -Path $ChromeRegKey -Name "(default)" -Value $TargetManifestPath
Write-Host "[+] Registered Chrome Native Messaging Host in Registry" -ForegroundColor Green

New-Item -Path $EdgeRegKey -Force | Out-Null
Set-ItemProperty -Path $EdgeRegKey -Name "(default)" -Value $TargetManifestPath
Write-Host "[+] Registered Edge Native Messaging Host in Registry" -ForegroundColor Green

Write-Host "`n[OK] YT Downloader Native Agent successfully installed!" -ForegroundColor Green
