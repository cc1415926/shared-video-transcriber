[CmdletBinding()]
param()

# 按命令行精确定位本项目的 pythonw/python 进程，只停这几个，不动别的 Python。
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = [System.IO.Path]::GetFullPath((Join-Path $root '.venv\Scripts\python.exe'))
$pythonw = [System.IO.Path]::GetFullPath((Join-Path $root '.venv\Scripts\pythonw.exe'))
$stopped = 0

$targets = Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
    Where-Object {
        $_.ExecutablePath -and $_.CommandLine -and
        ([System.IO.Path]::GetFullPath($_.ExecutablePath) -in @($python, $pythonw)) -and
        $_.CommandLine -match '(?i)(^|[\\/\s"])\s*(app|launcher)\.py([\s"]|$)'
    }

foreach ($process in $targets) {
    try {
        Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
        Write-Host "已停止进程 $($process.ProcessId)"
        $stopped++
    } catch {
        Write-Host "进程 $($process.ProcessId) 无法停止：$($_.Exception.Message)"
    }
}

if ($stopped -eq 0) {
    Write-Host '没有找到正在运行的视频收件箱服务。'
} else {
    Write-Host ''
    Write-Host "已停止 $stopped 个进程。页面上的操作会提示服务已停止，重新双击桌面图标即可恢复。"
}
