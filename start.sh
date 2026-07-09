#!/usr/bin/env bash
# =============================================================================
# PP7-QA Start Script — macOS / Linux
#
# Usage:
#   ./start.sh                    # Interactive — prompts for options
#   ./start.sh --detach           # Start in background (no log output)
#   ./start.sh --build            # Force rebuild of Docker images
#   ./start.sh --model mistral:7b # Override Ollama model
#   ./start.sh --api-memory 2g    # Override API container memory limit
#   ./start.sh --frontend-memory 512m
#   ./start.sh --api-port 8001    # Override API port
#   ./start.sh --frontend-port 3001
#   ./start.sh --help
# =============================================================================
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}  ✔${RESET}  $*"; }
warn() { echo -e "${YELLOW}  ⚠${RESET}  $*"; }
info() { echo -e "${CYAN}  →${RESET}  $*"; }
err()  { echo -e "${RED}  ✖${RESET}  $*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# ── Load existing .env values as defaults ─────────────────────────────────────
load_env() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  fi
}
load_env

# ── Defaults (from .env or hardcoded fallbacks) ────────────────────────────────
DETACH="${DETACH:-false}"
BUILD="${BUILD:-false}"
MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
API_MEM="${API_MEMORY:-1g}"
FRONTEND_MEM="${FRONTEND_MEMORY:-512m}"
API_PORT_VAL="${API_PORT:-8000}"
FRONTEND_PORT_VAL="${FRONTEND_PORT:-3000}"

# ── Argument parser ────────────────────────────────────────────────────────────
show_help() {
  echo -e "\n${BOLD}PP7-QA Start Script${RESET}"
  echo ""
  echo -e "  ${BOLD}./start.sh${RESET} [OPTIONS]"
  echo ""
  echo "  OPTIONS:"
  echo "    -d, --detach            Run containers in the background"
  echo "    -b, --build             Force rebuild of Docker images"
  echo "    --model <name>          Ollama model (e.g. llama3.2:3b, mistral:7b)"
  echo "    --api-memory <size>     API container RAM limit (e.g. 512m, 1g, 2g)"
  echo "    --frontend-memory <sz>  Frontend container RAM limit (e.g. 256m, 512m)"
  echo "    --api-port <port>       API port (default: 8000)"
  echo "    --frontend-port <port>  Frontend UI port (default: 3000)"
  echo "    --status                Show container status and exit"
  echo "    -h, --help              Show this help"
  echo ""
  exit 0
}

STATUS_ONLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--detach)            DETACH=true ;;
    -b|--build)             BUILD=true ;;
    --model)                MODEL="$2"; shift ;;
    --api-memory)           API_MEM="$2"; shift ;;
    --frontend-memory)      FRONTEND_MEM="$2"; shift ;;
    --api-port)             API_PORT_VAL="$2"; shift ;;
    --frontend-port)        FRONTEND_PORT_VAL="$2"; shift ;;
    --status)               STATUS_ONLY=true ;;
    -h|--help)              show_help ;;
    *) warn "Unknown option: $1" ;;
  esac
  shift
done

# ── Status-only mode ──────────────────────────────────────────────────────────
if $STATUS_ONLY; then
  echo -e "\n${BOLD}Container Status${RESET}"
  cd "$SCRIPT_DIR"
  docker compose ps
  exit 0
fi

# =============================================================================
# Pre-flight checks
# =============================================================================
echo ""
echo -e "${BOLD}PP7-QA Launcher${RESET}  •  ProPresenter 7 AI Quality Assurance"
echo "$(printf '─%.0s' {1..60})"

# Check Docker
if ! docker info &>/dev/null 2>&1; then
  err "Docker is not running. Start Docker Desktop and try again."
fi
ok "Docker is running"

# Check Ollama
if curl -sf http://localhost:11434/v1/models &>/dev/null; then
  ok "Ollama is running on port 11434"
else
  warn "Ollama does not appear to be running on port 11434"
  warn "The AI chat feature will not work until Ollama is started."
  warn "Start Ollama and ensure 'ollama serve' is active, then refresh the app."
fi

# Verify model is pulled
if command -v ollama &>/dev/null; then
  if ollama list 2>/dev/null | grep -q "^${MODEL%:*}"; then
    ok "Model '$MODEL' is available"
  else
    warn "Model '$MODEL' is not pulled. Pulling now…"
    ollama pull "$MODEL" || warn "Pull failed — run: ollama pull $MODEL"
  fi
fi

# =============================================================================
# Interactive config (only when no CLI flags override anything meaningful)
# =============================================================================
if [[ $# -eq 0 ]] && [[ -t 0 ]]; then
  echo ""
  info "Current configuration (press Enter to accept, or type a new value):"
  echo ""

  read -r -p "  Ollama model      [$MODEL]: " input_model
  MODEL="${input_model:-$MODEL}"

  read -r -p "  API memory limit  [$API_MEM]: " input_api_mem
  API_MEM="${input_api_mem:-$API_MEM}"

  read -r -p "  Frontend memory   [$FRONTEND_MEM]: " input_fe_mem
  FRONTEND_MEM="${input_fe_mem:-$FRONTEND_MEM}"

  read -r -p "  API port          [$API_PORT_VAL]: " input_api_port
  API_PORT_VAL="${input_api_port:-$API_PORT_VAL}"

  read -r -p "  Frontend port     [$FRONTEND_PORT_VAL]: " input_fe_port
  FRONTEND_PORT_VAL="${input_fe_port:-$FRONTEND_PORT_VAL}"

  echo ""
  read -r -p "  Run in background (detached)? [y/N]: " input_detach
  [[ "$input_detach" =~ ^[Yy]$ ]] && DETACH=true

  echo ""
fi

# =============================================================================
# Save chosen options back to .env
# =============================================================================
update_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i '' "s|^${key}=.*|${key}=${val}|" "$ENV_FILE" 2>/dev/null \
      || sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

[[ -f "$ENV_FILE" ]] || cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
update_env "OLLAMA_MODEL"     "$MODEL"
update_env "API_MEMORY"       "$API_MEM"
update_env "FRONTEND_MEMORY"  "$FRONTEND_MEM"
update_env "API_PORT"         "$API_PORT_VAL"
update_env "FRONTEND_PORT"    "$FRONTEND_PORT_VAL"

# =============================================================================
# Build / start containers
# =============================================================================
echo ""
info "Configuration:"
echo "    Model:     $MODEL"
echo "    API mem:   $API_MEM  (port $API_PORT_VAL)"
echo "    FE mem:    $FRONTEND_MEM  (port $FRONTEND_PORT_VAL)"
echo "    Detached:  $DETACH"
echo ""

cd "$SCRIPT_DIR"

COMPOSE_ARGS=()
$BUILD && COMPOSE_ARGS+=("--build")
$DETACH && COMPOSE_ARGS+=("-d")

info "Starting PP7-QA containers…"
docker compose up "${COMPOSE_ARGS[@]}"

if $DETACH; then
  echo ""
  ok "PP7-QA is running in the background"
  echo ""
  echo -e "  ${BOLD}UI:${RESET}      ${CYAN}http://localhost:${FRONTEND_PORT_VAL}${RESET}"
  echo -e "  ${BOLD}API docs:${RESET} ${CYAN}http://localhost:${API_PORT_VAL}/docs${RESET}"
  echo ""
  echo -e "  View logs:  ${BOLD}docker compose logs -f${RESET}"
  echo -e "  Stop:       ${BOLD}./stop.sh${RESET}"
fi
