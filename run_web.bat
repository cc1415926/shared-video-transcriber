@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -File "%~dp0run_web.ps1" %*
if errorlevel 1 pause
