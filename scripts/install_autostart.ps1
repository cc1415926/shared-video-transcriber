[CmdletBinding()]
param(
    [switch]$NoDesktop,
    [switch]$StartNow
)

# 装两类快捷方式：
#   1) 启动项里的静默自启（登录后后台常驻，不开浏览器）
#   2) 桌面上的“打开视频收件箱”（服务没跑时拉起来，跑着就直接开页面）
# 全部放在当前用户目录下，不需要管理员权限，也不会写注册表。
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$wscript = Join-Path $env:SystemRoot 'System32\wscript.exe'
$icon = Join-Path $root 'packaging\generated\videoinbox.ico'
$startupScript = Join-Path $root 'scripts\autostart_hidden.vbs'
# 桌面图标用免代理打开器：先确认服务在跑，再用不带代理、不带扩展的浏览器窗口打开，
# 避免某些代理软件或扩展对 127.0.0.1 返回 502。
$manualScript = Join-Path $root 'scripts\open_app.vbs'

if (-not (Test-Path -LiteralPath $pythonw)) {
    throw '还没有可用的 .venv。请先双击 run_web.bat 把环境装好，再运行这个脚本。'
}
if (-not (Test-Path -LiteralPath $wscript)) { throw "找不到 wscript.exe：$wscript" }

$shell = New-Object -ComObject WScript.Shell

function New-Shortcut([string]$path, [string]$target, [string]$arguments, [string]$description) {
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $target
    $shortcut.Arguments = $arguments
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = $description
    if (Test-Path -LiteralPath $icon) { $shortcut.IconLocation = "$icon,0" }
    $shortcut.Save()
    Write-Host "已写入：$path"
}

$startupDir = [Environment]::GetFolderPath('Startup')
$startupLink = Join-Path $startupDir '视频收件箱（后台常驻）.lnk'
New-Shortcut $startupLink $wscript "`"$startupScript`"" '视频收件箱：登录后自动在后台运行'

if (-not $NoDesktop) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $desktopLink = Join-Path $desktop '视频收件箱.lnk'
    New-Shortcut $desktopLink $wscript "`"$manualScript`"" '打开视频收件箱（自动绕开代理和扩展）'
}

if ($StartNow) {
    Start-Process -FilePath $wscript -ArgumentList "`"$startupScript`""
    Write-Host '已在后台启动，浏览器打开 http://127.0.0.1:7860 即可使用。'
}

Write-Host ''
Write-Host '完成。下次登录 Windows 会自动在后台跑，不需要再点任何东西。'
Write-Host '常用地址：http://127.0.0.1:7860'
Write-Host '停止服务：运行 scripts\stop_service.ps1'
Write-Host '取消自启：运行 scripts\uninstall_autostart.ps1'
