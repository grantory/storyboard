#!/usr/bin/env bash

set -euo pipefail

# ========================================
#   Project Maestro v2 - AI Storyboard
# ========================================
echo

# Resolve script directory and move there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Choose Python interpreter (prefer python3)
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "[ERROR] Python is not installed or not in PATH"
  echo "Please install Python 3.8+ from https://python.org"
  exit 1
fi

# Check for git updates (best-effort)
echo "[INFO] Checking for updates..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if ! git pull --ff-only >/dev/null 2>&1; then
    echo "[WARN] Git pull failed"
  else
    echo "[OK] Repository is up to date"
  fi
else
  echo "[WARN] Not a git repository. Skipping update."
fi

# Set environment variable for Real-ESRGAN weights
export REAL_ESRGAN_WEIGHTS_DIR="$SCRIPT_DIR/weights"

# Check if .env file exists and has API key
if [[ ! -f .env ]]; then
  echo "[INFO] Creating .env file..."
  cat > .env <<'EOF'
# Project Maestro v2 Configuration
OPENROUTER_API_KEY=
V2_OPENROUTER_CONTEXT_MODEL=gpt-4o-mini
V2_OPENROUTER_DIRECTOR_MODEL=gpt-4o
V2_OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview
EOF
  echo
  echo "[WARN] Please edit .env file and add your OPENROUTER_API_KEY"
  echo
else
  if grep -q '^OPENROUTER_API_KEY=sk-' .env; then
    echo "[OK] API key found in .env file"
  else
    echo "[WARN] OPENROUTER_API_KEY not found in .env file"
    echo "Please add your API key to .env file"
    echo
  fi
fi

# Launch the application
echo "[INFO] Launching Project Maestro v2..."
echo
if ! "$PYTHON" -m src.gui.main; then
  echo
  echo "[ERROR] Application exited with an error"
  echo
  exit 1
fi


