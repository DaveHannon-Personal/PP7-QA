#!/usr/bin/env bash
# =============================================================================
# PP7-QA GUI Launcher — macOS / Linux
# Opens the graphical launcher. Run this instead of setup.sh / start.sh.
# =============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Find Python 3 ─────────────────────────────────────────────────────────────
PYTHON=""
for candidate in python3 python python3.12 python3.11 python3.10 python3.9; do
  if command -v "$candidate" &>/dev/null; then
    version=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.9 or later is required."
  echo "Install with: brew install python"
  exit 1
fi

# ── Check tkinter is available ────────────────────────────────────────────────
if ! "$PYTHON" -c "import tkinter" 2>/dev/null; then
  echo "ERROR: tkinter is not available in $PYTHON."
  echo "On macOS, install python-tk via Homebrew:"
  echo "  brew install python-tk"
  echo ""
  echo "Or install Python from https://python.org (includes tkinter)"
  exit 1
fi

echo "Starting PP7-QA Launcher GUI..."
"$PYTHON" "$SCRIPT_DIR/launcher.py" "$@"
