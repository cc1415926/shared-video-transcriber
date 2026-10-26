[CmdletBinding()]
param(
    [string]$BundlePath = '',
    [string]$CollectorPath = '',
    [string]$OutputDirectory = ''
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
if (-not $BundlePath) { $BundlePath = Join-Path $root 'dist\VideoInbox' }
if (-not $CollectorPath) { $CollectorPath = Join-Path $root 'packaging\generated\wx-channel' }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $root 'dist\installers' }

$bundle = [IO.Path]::GetFullPath($BundlePath)
$collector = [IO.Path]::GetFullPath($CollectorPath)
$output = [IO.Path]::GetFullPath($OutputDirectory)
if (-not (Test-Path -LiteralPath (Join-Path $bundle 'VideoInbox.exe') -PathType Leaf)) {
    throw "未找到可运行的 VideoInbox.exe：$bundle"
}
if (-not (Test-Path -LiteralPath (Join-Path $collector 'wx_channel.exe') -PathType Leaf)) {
    throw "未找到完整的视频号采集器：$collector"
}

New-Item -ItemType Directory -Force -Path $output | Out-Null
$staging = Join-Path $output 'VideoInbox-Portable-Windows-x64'
if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
New-Item -ItemType Directory -Force -Path $staging | Out-Null
Copy-Item -LiteralPath $bundle -Destination (Join-Path $staging 'VideoInbox') -Recurse -Force
Copy-Item -LiteralPath $collector -Destination (Join-Path $staging 'wx-channel') -Recurse -Force

$start = @'
@echo off
setlocal
set "APP_ROOT=%~dp0"
set "WX_CHANNEL_HOME=%APP_ROOT%wx-channel"
set "WX_CHANNEL_DOWNLOADS_DIR=%WX_CHANNEL_HOME%\downloads"
set "WX_CHANNEL_EXECUTABLE=%WX_CHANNEL_HOME%\wx_channel.exe"
start "Video Inbox" "%APP_ROOT%VideoInbox\VideoInbox.exe"
endlocal
'@
Set-Content -LiteralPath (Join-Path $staging '启动视频收件箱.cmd') -Value $start -Encoding ascii

$readme = @'
# 视频收件箱（便携版）

1. 将整个文件夹解压到本机可写位置，例如“下载”或“文档”。
2. 双击“启动视频收件箱.cmd”。浏览器会打开本机地址：http://127.0.0.1:7860/
3. 要采集微信视频号：在收件箱的“微信视频号”页点击启动下载器；首次启动按 Windows 的管理员提示确认。

不要只移动 VideoInbox 或 wx-channel 子文件夹；它们必须保持在同一解压目录中。
'@
Set-Content -LiteralPath (Join-Path $staging '使用说明.txt') -Value $readme -Encoding utf8

$archive = Join-Path $output 'VideoInbox-Portable-Windows-x64.zip'
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
$items = Get-ChildItem -LiteralPath $staging -Force
Compress-Archive -Path $items.FullName -DestinationPath $archive -CompressionLevel Optimal
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archive.sha256" -Value "$hash  $(Split-Path -Leaf $archive)" -Encoding ascii
Write-Output $archive
Write-Output "$archive.sha256"
