[CmdletBinding()]
param(
    [switch]$Start,
    [switch]$CheckOnly,
    [switch]$SkipBrowser,
    [switch]$InstallFfmpeg
)

# Agent-friendly, repeatable source deployment for Windows 10/11 x64.
# It never deletes .venv, .data, the platform data directory, or user media.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = '1'
$uvVersion = '0.12.8'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'

function Find-Python {
    if ($env:VIDEO_PYTHON -and (Test-Path -LiteralPath $env:VIDEO_PYTHON -PathType Leaf)) { return $env:VIDEO_PYTHON }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source, '-3.12') }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and $python.Source -notlike '*WindowsApps*') { return $python.Source }
    return $null
}

function Invoke-Python([object]$command, [string[]]$arguments) {
    if ($command -is [array]) { & $command[0] $command[1] @arguments } else { & $command @arguments }
    if ($LASTEXITCODE -ne 0) { throw "Python command failed: $arguments" }
}

function Find-Uv {
    $found = Get-Command uv -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $userBase = $null
    $python = Find-Python
    if ($python) {
        try {
            if ($python -is [array]) { $userBase = & $python[0] $python[1] -m site --user-base } else { $userBase = & $python -m site --user-base }
        } catch { }
    }
    $candidate = if ($userBase) { Join-Path $userBase.Trim() 'Scripts\uv.exe' } else { $null }
    if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return $candidate }
    return $null
}

$uv = Find-Uv
if (-not $uv) {
    $python = Find-Python
    if (-not $python) {
        throw '未找到 uv 或 64 位 Python。请先安装 Python 3.12（python.org，勾选 PATH），再重新运行此脚本。'
    }
    Write-Host "正在通过 Python 用户目录安装 uv $uvVersion（不需要管理员权限）……"
    Invoke-Python $python @('-m', 'pip', 'install', '--user', "uv==$uvVersion")
    $uv = Find-Uv
    if (-not $uv) { throw 'uv 已安装但当前会话找不到它。请重新打开 PowerShell 后重试。' }
}
Write-Host "uv: $(& $uv --version)"

if ($CheckOnly) {
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) { throw '项目环境尚未创建。请先运行 .\scripts\deploy.ps1。' }
    & $venvPython diagnostics.py
    exit $LASTEXITCODE
}

if ((Test-Path -LiteralPath (Join-Path $root '.venv')) -and -not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw '发现不完整的 .venv，脚本不会删除它。请关闭服务后把 .venv 改名备份，再重新运行此脚本；不要删除 .data 或用户数据目录。'
}
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Write-Host '创建项目专用 Python 3.12 环境；uv 会优先复用本机解释器和缓存……'
    & $uv venv --python 3.12 .venv
    if ($LASTEXITCODE -ne 0) { throw '创建 .venv 失败。请检查网络、Python 3.12 或 uv 输出后重试。' }
}

Write-Host '按 requirements.lock 安装/修复依赖；uv 会复用已下载的缓存……'
& $uv pip install --python $venvPython -r requirements.lock
if ($LASTEXITCODE -ne 0) { throw 'Python 依赖安装失败。请检查网络/代理和 uv 输出，再直接重试同一条命令。' }
& $uv pip check --python $venvPython
if ($LASTEXITCODE -ne 0) { throw '已安装依赖存在冲突；请保留输出并提交 issue。' }

$browser = & $venvPython -c "from runtime_paths import browser_executable; print(browser_executable() or '')"
$cacheBrowser = & $venvPython -c "from runtime_paths import configure_runtime; configure_runtime(); from pathlib import Path; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print('yes' if Path(p.chromium.executable_path).is_file() else ''); p.stop()"
if (-not $SkipBrowser -and -not $browser.Trim() -and -not $cacheBrowser.Trim()) {
    Write-Host '未发现 Chrome/Edge 或 Playwright Chromium；正在按需安装 Chromium……'
    & $venvPython -c "from runtime_paths import configure_runtime; configure_runtime()"
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Chromium 安装失败。网络恢复后重试；仅本地文件可改用 -SkipBrowser。' }
} elseif ($browser.Trim()) {
    Write-Host "将复用系统浏览器：$browser"
} elseif ($SkipBrowser) {
    Write-Host '已跳过浏览器安装：本地视频、转写和片段截取仍可使用。'
}

$ffmpeg = & $venvPython -c "from runtime_paths import executable; print(executable('ffmpeg') or '')"
if (-not $ffmpeg.Trim()) {
    if ($InstallFfmpeg) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $winget) { throw '未找到 winget，无法自动安装 FFmpeg。请从可信来源安装 FFmpeg 后重新运行。' }
        & $winget.Source install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) { throw 'FFmpeg 安装失败；可稍后重新运行 -InstallFfmpeg。' }
    } else {
        Write-Warning '未找到 FFmpeg：基础界面可启动，但完整下载合并、音轨提取和片段导出需要它。可重试：.\scripts\deploy.ps1 -InstallFfmpeg'
    }
} else { Write-Host "将复用 FFmpeg：$ffmpeg" }

Write-Host '环境检查：'
& $venvPython diagnostics.py
if ($LASTEXITCODE -ne 0) { throw '环境检查报告错误；请阅读上方输出后重试。' }
if ($Start) {
    Write-Host '启动本地服务（仅监听 127.0.0.1）……'
    & $venvPython app.py
    exit $LASTEXITCODE
}
Write-Host '部署完成。启动：.\scripts\deploy.ps1 -Start'
