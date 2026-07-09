#Requires -Version 5.1
<#
.SYNOPSIS
    PP7-QA GUI Launcher — Windows
    Opens the graphical launcher. Run this instead of setup.ps1 / start.ps1.

.EXAMPLE
    .\launcher.ps1
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── Find Python 3.9+ ──────────────────────────────────────────────────────────
$python = $null

# Check PATH first
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 9) {
                $python = $candidate
                break
            }
        }
    } catch { }
}

# Try the Windows Store Python / py launcher
if (-not $python) {
    try {
        $ver = & py -3 --version 2>&1
        if ($ver -match "Python 3") { $python = "py -3" }
    } catch { }
}

if (-not $python) {
    Write-Host "ERROR: Python 3.9 or later is required." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Python from https://www.python.org/downloads/"
    Write-Host "  - Check 'Add Python to PATH' during installation"
    Write-Host ""
    $open = Read-Host "Open python.org download page? [y/N]"
    if ($open -match "^[Yy]$") { Start-Process "https://www.python.org/downloads/" }
    exit 1
}

# ── Check tkinter ──────────────────────────────────────────────────────────────
& $python.Split()[0] ($python.Split()[1..99] + @("-c", "import tkinter")) 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: tkinter is not available." -ForegroundColor Red
    Write-Host "Reinstall Python from https://python.org and ensure tkinter is included (it is by default)."
    exit 1
}

Write-Host "Starting PP7-QA Launcher GUI..." -ForegroundColor Cyan
$launcherPath = Join-Path $ScriptDir "launcher.py"

# Launch without showing a console window (use pythonw on Windows if available)
$pythonWCmd = Get-Command "pythonw" -ErrorAction SilentlyContinue
$pythonW = if ($pythonWCmd) { $pythonWCmd.Source } else { $null }
if ($pythonW) {
    Start-Process -FilePath $pythonW -ArgumentList "`"$launcherPath`"" -WindowStyle Hidden
} else {
    & $python.Split()[0] ($python.Split()[1..99] + @($launcherPath))
}
