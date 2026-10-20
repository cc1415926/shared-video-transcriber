param([switch]$Check,[switch]$InstallOnly,[switch]$SkipBrowser)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$options = @{}
if ($Check) { $options.CheckOnly = $true }
if ($SkipBrowser) { $options.SkipBrowser = $true }
if (-not $Check -and -not $InstallOnly) { $options.Start = $true }
& (Join-Path $PSScriptRoot 'scripts\deploy.ps1') @options
exit $LASTEXITCODE
