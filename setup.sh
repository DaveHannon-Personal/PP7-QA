#!/usr/bin/env bash
# =============================================================================
# PP7-QA Setup Script — macOS / Linux
# Checks and installs all prerequisites for running PP7-QA.
# Run once before your first `./start.sh`.
#
# Usage:  ./setup.sh
# =============================================================================
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

ok()   { echo -e "${GREEN}  ✔${RESET}  $*"; }
warn() { echo -e "${YELLOW}  ⚠${RESET}  $*"; }
info() { echo -e "${CYAN}  →${RESET}  $*"; }
err()  { echo -e "${RED}  ✖${RESET}  $*"; }
header() { echo -e "\n${BOLD}${CYAN}$*${RESET}"; echo "$(printf '─%.0s' {1..60})"; }

# ── Detect OS ─────────────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

echo -e "\n${BOLD}PP7-QA Setup${RESET}  •  ProPresenter 7 AI Quality Assurance"
echo "$(printf '═%.0s' {1..60})"
info "OS: $OS  •  Arch: $ARCH"

# ── Helper: prompt yes/no ──────────────────────────────────────────────────────
confirm() {
  local prompt="${1:-Continue?}"
  read -r -p "$(echo -e "${YELLOW}  ?${RESET}  $prompt [y/N] ")" response
  [[ "$response" =~ ^[Yy]$ ]]
}

# =============================================================================
# 1. Homebrew (macOS only)
# =============================================================================
if [[ "$OS" == "Darwin" ]]; then
  header "1 / 5  Homebrew"
  if command -v brew &>/dev/null; then
    ok "Homebrew $(brew --version | head -1 | awk '{print $2}') is installed"
  else
    warn "Homebrew not found — required to install other tools on macOS"
    if confirm "Install Homebrew now?"; then
      info "Installing Homebrew…"
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      # Add brew to PATH for the rest of this session
      eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
      ok "Homebrew installed"
    else
      err "Homebrew is required on macOS. Install manually from https://brew.sh then re-run setup."
      exit 1
    fi
  fi
fi

# =============================================================================
# 2. Docker Desktop / Docker Engine + Docker Compose
# =============================================================================
header "2 / 5  Docker"

DOCKER_OK=false
COMPOSE_OK=false

if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  DOCKER_VERSION=$(docker --version | awk '{print $3}' | tr -d ',')
  ok "Docker $DOCKER_VERSION is installed and running"
  DOCKER_OK=true
else
  warn "Docker is not installed or not running"
  if [[ "$OS" == "Darwin" ]]; then
    if confirm "Install Docker Desktop via Homebrew?"; then
      info "Installing Docker Desktop (this may take a few minutes)…"
      brew install --cask docker
      info "Docker Desktop installed. Please open it from Applications and wait for it to start."
      info "Then re-run this setup script."
      open -a Docker 2>/dev/null || true
      exit 0
    else
      err "Docker is required. Install from https://www.docker.com/products/docker-desktop"
      exit 1
    fi
  else
    err "Docker is required. Install from https://docs.docker.com/engine/install/"
    exit 1
  fi
fi

# Check Docker Compose (v2 — bundled with Docker Desktop; standalone on Linux)
if docker compose version &>/dev/null 2>&1; then
  COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || docker compose version | awk '{print $NF}')
  ok "Docker Compose $COMPOSE_VERSION is available"
  COMPOSE_OK=true
elif command -v docker-compose &>/dev/null; then
  warn "Found legacy docker-compose v1 — Docker Compose v2 is recommended"
  ok "docker-compose (v1) $(docker-compose --version | awk '{print $3}' | tr -d ',')"
  COMPOSE_OK=true
else
  warn "Docker Compose not found"
  if [[ "$OS" == "Darwin" ]]; then
    info "Docker Compose ships with Docker Desktop — make sure Docker Desktop is up to date"
  else
    if confirm "Install Docker Compose plugin?"; then
      sudo apt-get update -qq && sudo apt-get install -y docker-compose-plugin
      ok "Docker Compose plugin installed"
    fi
  fi
fi

# =============================================================================
# 3. Ollama
# =============================================================================
header "3 / 5  Ollama (local AI)"

if command -v ollama &>/dev/null; then
  OLLAMA_VERSION=$(ollama --version 2>/dev/null | awk '{print $NF}' || echo "unknown")
  ok "Ollama $OLLAMA_VERSION is installed"
else
  warn "Ollama not found"
  if [[ "$OS" == "Darwin" ]]; then
    if confirm "Install Ollama via Homebrew?"; then
      info "Installing Ollama…"
      brew install ollama
      ok "Ollama installed"
    else
      info "Download manually from https://ollama.com and re-run setup"
      exit 1
    fi
  else
    if confirm "Install Ollama via the official install script?"; then
      curl -fsSL https://ollama.com/install.sh | sh
      ok "Ollama installed"
    else
      info "Download manually from https://ollama.com and re-run setup"
      exit 1
    fi
  fi
fi

# Check if Ollama is running
if curl -sf http://localhost:11434/v1/models &>/dev/null; then
  ok "Ollama is running on port 11434"
else
  warn "Ollama service is not running"
  if [[ "$OS" == "Darwin" ]]; then
    info "Starting Ollama in the background…"
    open -a Ollama 2>/dev/null || (ollama serve &>/dev/null &)
    sleep 3
    if curl -sf http://localhost:11434/v1/models &>/dev/null; then
      ok "Ollama started"
    else
      warn "Could not auto-start Ollama. Open the Ollama app manually and re-run setup."
    fi
  else
    info "Start Ollama with:  ollama serve &"
  fi
fi

# =============================================================================
# 4. Pull AI model
# =============================================================================
header "4 / 5  AI Model"

echo -e "  Choose a model to use with PP7-QA:\n"
echo -e "    ${BOLD}1)${RESET} llama3.2:3b   — Fast, ~2 GB RAM  ${GREEN}[Recommended for most Macs]${RESET}"
echo -e "    ${BOLD}2)${RESET} mistral:7b    — Better reasoning, ~5 GB RAM"
echo -e "    ${BOLD}3)${RESET} llama3.2:1b   — Very fast, ~1 GB RAM  (limited reasoning)"
echo -e "    ${BOLD}4)${RESET} Skip — I will pull a model manually\n"

read -r -p "$(echo -e "${YELLOW}  ?${RESET}  Select model [1-4, default=1]: ")" MODEL_CHOICE
MODEL_CHOICE="${MODEL_CHOICE:-1}"

case "$MODEL_CHOICE" in
  1) SELECTED_MODEL="llama3.2:3b" ;;
  2) SELECTED_MODEL="mistral:7b" ;;
  3) SELECTED_MODEL="llama3.2:1b" ;;
  4) SELECTED_MODEL=""; info "Skipping model pull — set OLLAMA_MODEL in .env manually" ;;
  *) SELECTED_MODEL="llama3.2:3b"; warn "Invalid choice, defaulting to llama3.2:3b" ;;
esac

if [[ -n "$SELECTED_MODEL" ]]; then
  # Check if model is already pulled
  if ollama list 2>/dev/null | grep -q "^${SELECTED_MODEL%:*}"; then
    ok "Model $SELECTED_MODEL is already available"
  else
    info "Pulling $SELECTED_MODEL (this may take several minutes on first run)…"
    ollama pull "$SELECTED_MODEL"
    ok "Model $SELECTED_MODEL pulled successfully"
  fi
fi

# =============================================================================
# 5. Environment file
# =============================================================================
header "5 / 5  Configuration"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  info "Creating .env from .env.example…"
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  ok ".env created"
else
  ok ".env already exists"
fi

# Update model in .env if user selected one
if [[ -n "${SELECTED_MODEL:-}" ]]; then
  if grep -q "^OLLAMA_MODEL=" "$ENV_FILE"; then
    # Use sed in-place (macOS compatible)
    sed -i '' "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$SELECTED_MODEL|" "$ENV_FILE" 2>/dev/null \
      || sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$SELECTED_MODEL|" "$ENV_FILE"
  else
    echo "OLLAMA_MODEL=$SELECTED_MODEL" >> "$ENV_FILE"
  fi
  ok "OLLAMA_MODEL set to $SELECTED_MODEL in .env"
fi

# =============================================================================
# Done
# =============================================================================
echo ""
echo -e "$(printf '═%.0s' {1..60})"
echo -e "${BOLD}${GREEN}  Setup complete!${RESET}"
echo ""
echo -e "  Next steps:"
echo -e "  ${BOLD}1.${RESET}  Make sure ProPresenter 7 is running with the Network API enabled"
echo -e "       ProPresenter → Preferences → Network → Enable Network API"
echo -e "  ${BOLD}2.${RESET}  Run:  ${BOLD}./start.sh${RESET}"
echo -e "  ${BOLD}3.${RESET}  Open: ${CYAN}http://localhost:3000${RESET}"
echo ""
echo -e "  To stop the app:  ${BOLD}./stop.sh${RESET}"
echo -e "$(printf '─%.0s' {1..60})"
