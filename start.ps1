#Requires -Version 5.1
<#
.SYNOPSIS
    PP7-QA Start Script — Windows

.DESCRIPTION
    Starts the PP7-QA Docker containers with configurable options for
    memory limits, ports, and Ollama model selection.

.PARAMETER Detach
    Run containers in the background (no log output in this window).

.PARAMETER Build
    Force rebuild of Docker images before starting.

.PARAMETER Model
    Ollama model name to use (e.g. llama3.2:3b, mistral:7b).

.PARAMETER ApiMemory
    Memory limit for the API container (e.g. 512m, 1g, 2g).

.PARAMETER FrontendMemory
    Memory limit for the frontend container (e.g. 256m, 512m).

.PARAMETER ApiPort
    Port to expose the API on (default: 8000).

.PARAMETER FrontendPort
    Port to expose the frontend UI on (default: 3000).

.PARAMETER Status
    Show container status and exit.

.EXAMPLE
    .\start.ps1
    .\start.ps1 -Detach
    .\start.ps1 -Build -Model mistral:7b -ApiMemory 2g
    .\start.ps1 -Status
#>

[CmdletBinding()]
param(
    [switch]$Detach,
    [switch]$Build,
    [string]$Model = "",
    [string]$ApiMemory = "",
    [string]$FrontendMemory = "",
    [string]$ApiPort = "",
    [string]$FrontendPort = "",
    [switch]$Status
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Ok   ($msg) { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn ($msg) { Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Info ($msg) { Write-Host "  -->   $msg" -ForegroundColor Cyan }
function Write-Err  ($msg) { Write-Host "  [X]   $msg" -ForegroundColor Red; exit 1 }

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvFile = Join-Path $ScriptDir ".env"
$EnvExample = Join-Path $ScriptDir ".env.example"

# ── Load .env into a hashtable ────────────────────────────────────────────────
function Read-EnvFile ($path) {
    $vars = @{}
    if (Test-Path $path) {
        Get-Content $path | Where-Object { $_ -match "^\s*[^#\s].*=" } | ForEach-Object {
            $parts = $_ -split "=", 2
            $vars[$parts[0].Trim()] = $parts[1].Trim()
        }
    }
    return $vars
}

function Set-EnvValue ($path, $key, $value) {
    $content = Get-Content $path -Raw
    if ($content -match "(?m)^$key=") {
        $content = $content -replace "(?m)^$key=.*", "$key=$value"
    }
    else {
        $content = $content.TrimEnd() + "`n$key=$value"
    }
    Set-Content -Path $path -Value $content.TrimEnd() -NoNewline
}

# ── Status-only mode ──────────────────────────────────────────────────────────
if ($Status) {
    Write-Host "`nContainer Status" -ForegroundColor Cyan
    Set-Location $ScriptDir
    docker compose ps
    exit 0
}

# ── Title ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "PP7-QA Launcher  •  ProPresenter 7 AI Quality Assurance" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ("-" * 60)

# ── Ensure .env exists ────────────────────────────────────────────────────────
if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Info ".env created from .env.example"
}

$envData = Read-EnvFile $EnvFile

# Apply defaults from .env, then override with CLI params
function Get-EnvOrDefault($val, $envKey, $default) {
    if ($val) { return $val }
    $e = $script:envData[$envKey]; if ($e) { return $e } else { return $default }
}

$cfg = @{
    Model          = Get-EnvOrDefault $Model          "OLLAMA_MODEL"    "llama3.2:3b"
    ApiMemory      = Get-EnvOrDefault $ApiMemory      "API_MEMORY"      "1g"
    FrontendMemory = Get-EnvOrDefault $FrontendMemory "FRONTEND_MEMORY" "512m"
    ApiPort        = Get-EnvOrDefault $ApiPort        "API_PORT"        "8000"
    FrontendPort   = Get-EnvOrDefault $FrontendPort   "FRONTEND_PORT"   "3000"
}

# =============================================================================
# Pre-flight checks
# =============================================================================
Write-Info "Running pre-flight checks..."

# Docker
try {
    $null = & docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw "not running" }
    Write-Ok "Docker is running"
}
catch {
    Write-Err "Docker is not running. Start Docker Desktop and try again."
}

# Docker Compose
try {
    $null = & docker compose version 2>&1
    Write-Ok "Docker Compose is available"
}
catch {
    Write-Err "Docker Compose not found. Update Docker Desktop."
}

# Ollama
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:11434/v1/models" -TimeoutSec 5 -ErrorAction Stop
    Write-Ok "Ollama is running on port 11434"

    # Check model
    $modelBase = $cfg.Model.Split(":")[0]
    $modelAvailable = $resp.data | Where-Object { $_.id -like "$modelBase*" }
    if ($modelAvailable) {
        Write-Ok "Model '$($cfg.Model)' is available"
    }
    else {
        Write-Warn "Model '$($cfg.Model)' is not pulled."
        $pull = Read-Host "  [?]  Pull it now? [y/N]"
        if ($pull -match "^[Yy]$") {
            Write-Info "Pulling $($cfg.Model)..."
            & ollama pull $cfg.Model
        }
        else {
            Write-Warn "Skipping model pull. The AI chat feature may not work."
        }
    }
}
catch {
    Write-Warn "Ollama is not running. The AI chat feature will not work."
    Write-Info "Start Ollama from the Start Menu, then refresh the app."
}

# =============================================================================
# Interactive configuration (only when running without explicit CLI overrides)
# =============================================================================
$hasCliOverrides = $Model -or $ApiMemory -or $FrontendMemory -or $ApiPort -or $FrontendPort -or $Build -or $Detach

if (-not $hasCliOverrides) {
    Write-Host ""
    Write-Info "Configuration (press Enter to accept current value, or type a new one):"
    Write-Host ""

    $ans = Read-Host "  Ollama model      [$($cfg.Model)]"
    if ($ans) { $cfg.Model = $ans }

    $ans = Read-Host "  API memory limit  [$($cfg.ApiMemory)]"
    if ($ans) { $cfg.ApiMemory = $ans }

    $ans = Read-Host "  Frontend memory   [$($cfg.FrontendMemory)]"
    if ($ans) { $cfg.FrontendMemory = $ans }

    $ans = Read-Host "  API port          [$($cfg.ApiPort)]"
    if ($ans) { $cfg.ApiPort = $ans }

    $ans = Read-Host "  Frontend port     [$($cfg.FrontendPort)]"
    if ($ans) { $cfg.FrontendPort = $ans }

    Write-Host ""
    $detachInput = Read-Host "  Run in background (detached)? [y/N]"
    if ($detachInput -match "^[Yy]$") { $Detach = $true }
    Write-Host ""
}

# =============================================================================
# Persist chosen options back to .env
# =============================================================================
Set-EnvValue $EnvFile "OLLAMA_MODEL"    $cfg.Model
Set-EnvValue $EnvFile "API_MEMORY"      $cfg.ApiMemory
Set-EnvValue $EnvFile "FRONTEND_MEMORY" $cfg.FrontendMemory
Set-EnvValue $EnvFile "API_PORT"        $cfg.ApiPort
Set-EnvValue $EnvFile "FRONTEND_PORT"   $cfg.FrontendPort

# =============================================================================
# Build & start
# =============================================================================
Write-Host ""
Write-Info "Configuration:"
Write-Host "    Model:    $($cfg.Model)"
Write-Host "    API:      $($cfg.ApiMemory) RAM  (port $($cfg.ApiPort))"
Write-Host "    Frontend: $($cfg.FrontendMemory) RAM  (port $($cfg.FrontendPort))"
Write-Host "    Detached: $Detach"
Write-Host ""

Set-Location $ScriptDir

$composeArgs = @("compose", "up")
if ($Build) { $composeArgs += "--build" }
if ($Detach) { $composeArgs += "-d" }

Write-Info "Starting PP7-QA containers..."
& docker @composeArgs

if ($Detach) {
    Write-Host ""
    Write-Ok "PP7-QA is running in the background"
    Write-Host ""
    Write-Host "  UI:       http://localhost:$($cfg.FrontendPort)" -ForegroundColor Cyan
    Write-Host "  API docs: http://localhost:$($cfg.ApiPort)/docs"  -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  View logs:  docker compose logs -f"
    Write-Host "  Stop:       .\stop.ps1"
}
