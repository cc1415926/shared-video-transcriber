[CmdletBinding()]
param(
    [string]$Version = '',
    [string]$BundlePath = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Version) {
    $Version = & (Join-Path $root '.venv\Scripts\python.exe') -c "from version import __version__;print(__version__)"
}
if (-not $BundlePath) {
    & (Join-Path $root '.venv\Scripts\python.exe') (Join-Path $root 'scripts\build_package.py')
    $BundlePath = Join-Path $root 'dist\VideoInbox'
}
$bundle = [IO.Path]::GetFullPath($BundlePath)
if (-not (Test-Path -LiteralPath (Join-Path $bundle 'VideoInbox.exe') -PathType Leaf)) {
    throw "未找到 Windows onedir 包：$bundle"
}
$candidates = @(
    (Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source),
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path -LiteralPath $_ -PathType Leaf) }
if (-not $candidates) {
    throw '未找到 Inno Setup 编译器。请安装 Inno Setup 6 后重试；CI 会使用同一份 .iss 脚本构建。'
}
$env:VIDEO_INBOX_VERSION = $Version.Trim()
$env:VIDEO_INBOX_DIST = $bundle
& $candidates[0] (Join-Path $root 'packaging\windows\VideoInbox.iss')
if ($LASTEXITCODE -ne 0) { throw "Inno Setup 编译失败：$LASTEXITCODE" }
$installer = Join-Path $root 'dist\installers\VideoInbox-Setup-Windows-x64.exe'
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Inno Setup 未生成预期安装包。' }
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$installer.sha256" -Value "$hash  $(Split-Path -Leaf $installer)" -Encoding ascii
Write-Output $installer
Write-Output "$installer.sha256"
