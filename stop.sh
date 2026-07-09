#!/usr/bin/env bash
# =============================================================================
# PP7-QA Stop Script — macOS / Linux
#
# Usage:
#   ./stop.sh              # Stop containers, keep data volumes
#   ./stop.sh --clean      # Stop containers AND remove volumes (resets DB)
#   ./stop.sh --prune      # Stop + remove unused Docker images (free disk space)
#   ./stop.sh --status     # Show container status and exit
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
ok()   { echo -e "${GREEN}  ✔${RESET}  $*"; }
warn() { echo -e "${YELLOW}  ⚠${RESET}  $*"; }
info() { echo -e "${CYAN}  →${RESET}  $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEAN=false
PRUNE=false
STATUS_ONLY=false

for arg in "$@"; do
  case "$arg" in
    --clean)  CLEAN=true ;;
    --prune)  PRUNE=true ;;
    --status) STATUS_ONLY=true ;;
    --help|-h)
      echo -e "\n${BOLD}PP7-QA Stop Script${RESET}"
      echo ""
      echo "  ./stop.sh              Stop containers, keep data (database preserved)"
      echo "  ./stop.sh --clean      Stop containers and delete data volumes (resets DB!)"
      echo "  ./stop.sh --prune      Stop containers and remove unused Docker images"
      echo "  ./stop.sh --status     Show running container status"
      exit 0
      ;;
    *) warn "Unknown option: $arg" ;;
  esac
done

cd "$SCRIPT_DIR"

if $STATUS_ONLY; then
  echo -e "\n${BOLD}Container Status${RESET}"
  docker compose ps
  exit 0
fi

echo ""
echo -e "${BOLD}PP7-QA — Stopping${RESET}"
echo "$(printf '─%.0s' {1..60})"

if $CLEAN; then
  warn "This will remove data volumes — your saved rules, profiles, and settings will be deleted!"
  read -r -p "$(echo -e "${YELLOW}  ?${RESET}  Are you sure? [y/N] ")" confirm
  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    info "Stopping containers and removing volumes…"
    docker compose down -v
    ok "Containers stopped and volumes removed"
  else
    info "Cancelled — no changes made"
    exit 0
  fi
else
  info "Stopping containers (data volumes preserved)…"
  docker compose down
  ok "Containers stopped"
fi

if $PRUNE; then
  info "Removing unused Docker images to free disk space…"
  docker image prune -f
  ok "Unused images removed"
fi

echo ""
ok "PP7-QA has been stopped"
echo ""
echo -e "  Data preserved at: ${CYAN}./data/pp7qa.db${RESET}"
echo -e "  Restart with:      ${BOLD}./start.sh${RESET}"
