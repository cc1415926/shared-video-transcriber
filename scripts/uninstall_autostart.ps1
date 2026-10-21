[CmdletBinding()]
param()

# 只删本脚本自己创建的两个快捷方式，不碰其它启动项。
$ErrorActionPreference = 'Stop'
$removed = 0
$startupLink = Join-Path ([Environment]::GetFolderPath('Startup')) '视频收件箱（后台常驻）.lnk'
$desktopLink = Join-Path ([Environment]::GetFolderPath('Desktop')) '视频收件箱.lnk'

foreach ($link in @($startupLink, $desktopLink)) {
    if (Test-Path -LiteralPath $link) {
        Remove-Item -LiteralPath $link -Force
        Write-Host "已删除：$link"
        $removed++
    }
}

if ($removed -eq 0) {
    Write-Host '没有找到需要删除的快捷方式，可能本来就没装。'
} else {
    Write-Host ''
    Write-Host '自启已取消。正在后台运行的服务不会自己退出，需要停止请运行 scripts\stop_service.ps1。'
}
