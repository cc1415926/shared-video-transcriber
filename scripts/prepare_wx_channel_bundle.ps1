[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,
    [string]$Destination = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Destination) {
    $Destination = Join-Path $root 'packaging\generated\wx-channel'
}
$archive = [IO.Path]::GetFullPath($ArchivePath)
$destinationPath = [IO.Path]::GetFullPath($Destination)
$expectedSha256 = '0218d72770d723aa48b22c55bd73e4efef04b55393bfca2203072fa72e4f5f06'

if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) {
    throw "未找到视频号采集器发布包：$archive"
}
$actualSha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) {
    throw "视频号采集器 SHA-256 不匹配。期望 $expectedSha256，实际 $actualSha256"
}

$temporary = "$destinationPath.tmp-$PID"
if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
New-Item -ItemType Directory -Path $temporary -Force | Out-Null
try {
    Expand-Archive -LiteralPath $archive -DestinationPath $temporary -Force
    if (-not (Test-Path -LiteralPath (Join-Path $temporary 'wx_channel.exe') -PathType Leaf)) {
        throw '发布包中缺少 wx_channel.exe'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $temporary 'web') -PathType Container)) {
        throw '发布包中缺少 web 资源目录'
    }
    $license = Join-Path $root 'packaging\third_party\wx_channel_LICENSE.txt'
    if (-not (Test-Path -LiteralPath $license -PathType Leaf)) {
        throw "缺少 wx_channel 许可证文件：$license"
    }
    Copy-Item -LiteralPath $license -Destination (Join-Path $temporary 'LICENSE-wx_channel.txt') -Force
    if (Test-Path -LiteralPath $destinationPath) { Remove-Item -LiteralPath $destinationPath -Recurse -Force }
    Move-Item -LiteralPath $temporary -Destination $destinationPath
} finally {
    if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force }
}

Write-Output $destinationPath
