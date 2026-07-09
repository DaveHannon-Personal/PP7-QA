#Requires -Version 5.1
<#
.SYNOPSIS
    PP7-QA Setup — Windows
    Creates a desktop shortcut for the PP7-QA Launcher GUI.

.EXAMPLE
    .\setup.ps1
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "PP7-QA Setup" -ForegroundColor Cyan
Write-Host "============" -ForegroundColor Cyan

# ── Desktop shortcut ──────────────────────────────────────────────────────────
$desktop  = [Environment]::GetFolderPath("Desktop")
$lnkPath  = Join-Path $desktop "PP7-QA.lnk"

# Prefer pythonw (no console window) but fall back to python
$target = if (Get-Command "pythonw" -ErrorAction SilentlyContinue) { "pythonw" } else { "python" }

$WshShell          = New-Object -ComObject WScript.Shell
$shortcut          = $WshShell.CreateShortcut($lnkPath)
$shortcut.TargetPath      = $target
$shortcut.Arguments       = "`"$ScriptDir\launcher.py`""
$shortcut.WorkingDirectory = $ScriptDir
$shortcut.WindowStyle     = 1
$shortcut.Description     = "PP7-QA Launcher"
$shortcut.Save()

Write-Host "Desktop shortcut created: $lnkPath" -ForegroundColor Green
Write-Host ""
Write-Host "Double-click 'PP7-QA' on your desktop to open the launcher." -ForegroundColor White
