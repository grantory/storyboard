#!/usr/bin/env bash

set -euo pipefail

# =================================================================================
# ==                                                                             ==
# ==                      Storyboard Project Launcher                            ==
# ==                                                                             ==
# =================================================================================
echo

# Resolve script directory and move there
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[STEP 1/5] Verifying prerequisites..."

# Choose Python interpreter (prefer python3)
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "[ERROR] Python is not installed or not found in your system's PATH."
  echo
  echo "        Please install Python 3.10+ from https://www.python.org"
  echo "        and ensure it is added to your PATH before running this script again."
  echo
  exit 1
fi

# Ensure Python version is 3.10+
if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "[ERROR] Python 3.10+ is required. Found: $($PYTHON --version 2>&1)"
  exit 1
fi
echo "[OK] Python found. Using: $($PYTHON --version 2>&1)"
echo

echo "[STEP 2/5] Configuring and syncing the storyboard repository..."

GIT_STORYBOARD_URL="https://github.com/grantory/storyboard"
STORYBOARD_DIR="$SCRIPT_DIR/storyboard"

if command -v git >/dev/null 2>&1; then
  if [[ -d "$STORYBOARD_DIR/.git" ]]; then
    echo "[INFO] Existing storyboard repository found. Attempting to update..."
    (cd "$STORYBOARD_DIR" && git pull --ff-only) || true
  else
    if [[ -d "$STORYBOARD_DIR" ]]; then
      echo "[WARN] Found an existing, non-git folder at '$STORYBOARD_DIR'."
      echo "       Skipping clone to avoid data loss."
    else
      echo "[INFO] Cloning storyboard repository into '$STORYBOARD_DIR'..."
      git clone "$GIT_STORYBOARD_URL" "$STORYBOARD_DIR"
    fi
  fi
else
  echo "[WARN] Git not found. Skipping storyboard repository sync."
  echo "       The application may not function correctly without it."
fi
echo "[OK] Storyboard repository sync complete."
echo

echo "[STEP 3/5] Installing Python dependencies..."

if [[ -f "requirements.txt" ]]; then
  echo "[INFO] Found local 'requirements.txt'. Installing dependencies..."
  if ! "$PYTHON" -m pip install -r requirements.txt; then
    echo "[ERROR] Failed to install local dependencies. Aborting."
    exit 1
  fi
  echo "[OK] Local dependencies installed successfully."
else
  echo "[INFO] No local 'requirements.txt' found. Skipping."
fi
echo

if [[ -f "$STORYBOARD_DIR/requirements.txt" ]]; then
  echo "[INFO] Found storyboard 'requirements.txt'. Installing dependencies..."
  if ! "$PYTHON" -m pip install -r "$STORYBOARD_DIR/requirements.txt"; then
    echo "[WARN] Failed to install some storyboard dependencies. The app will continue,"
    echo "       but some features might not work as expected."
  else
    echo "[OK] Storyboard dependencies installed successfully."
  fi
fi
echo

echo "[STEP 4/5] Setting up environment and configuration..."

export REAL_ESRGAN_WEIGHTS_DIR="$SCRIPT_DIR/weights"

echo "[INFO] Checking for Real-ESRGAN weights..."
if [[ ! -f "$REAL_ESRGAN_WEIGHTS_DIR/realesr-general-x4v3.pth" ]]; then
  echo
  echo "[WARN] Real-ESRGAN weights not found at:"
  echo "       $REAL_ESRGAN_WEIGHTS_DIR/realesr-general-x4v3.pth"
  echo "       The application will attempt to download them at runtime."
  echo
else
  echo "[OK] Weights found."
fi

if [[ -f .env ]]; then
  echo "[INFO] Existing '.env' file found. Skipping creation."
else
  echo
  echo "[INFO] '.env' file not found. Starting interactive setup..."
  echo "+------------------------------------------------------------------------+"
  echo "| Enter your OpenRouter API Key. If you don't have one, press Enter      |"
  echo "| to leave it blank and you can set it in the '.env' file later.         |"
  echo "+------------------------------------------------------------------------+"
  read -r -p "> Enter OPENROUTER_API_KEY: " INPUT_OPENROUTER_KEY || true
  echo
  echo "[INFO] Creating .env file with default settings..."
  {
    echo "OPENROUTER_API_KEY=${INPUT_OPENROUTER_KEY}"
    echo "V2_OPENROUTER_CONTEXT_MODEL=openai/gpt-5-mini"
    echo "V2_OPENROUTER_CONTEXT_VISION_MODEL=openai/gpt-5-mini"
    echo "V2_OPENROUTER_DIRECTOR_MODEL=openai/gpt-5"
    echo "V2_OPENROUTER_DIRECTOR_VISION_MODEL=openai/gpt-5"
    echo "V2_OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview"
    echo "V2_MAX_CONCURRENT_REQUESTS=5"
    echo "V2_REQUEST_TIMEOUT_SEC=60"
  } > .env
  echo "[OK] '.env' file saved successfully."
fi
echo

echo "[STEP 5/5] Preparing to launch the application..."

LAUNCH_FILE=""
if [[ -f "$SCRIPT_DIR/src/gui/main.py" ]]; then
  LAUNCH_FILE="$SCRIPT_DIR/src/gui/main.py"
elif [[ -f "$STORYBOARD_DIR/src/gui/main.py" ]]; then
  LAUNCH_FILE="$STORYBOARD_DIR/src/gui/main.py"
fi

if [[ -z "$LAUNCH_FILE" ]]; then
  echo "[ERROR] Could not find the application entry point to launch."
  echo "        Looked for:"
  echo "        - $SCRIPT_DIR/src/gui/main.py"
  echo "        - $STORYBOARD_DIR/src/gui/main.py"
  echo
  exit 1
fi

echo "[INFO] Launch target found: $LAUNCH_FILE"
echo "[INFO] Setting up Python Path..."

export PYTHONPATH="$SCRIPT_DIR${STORYBOARD_DIR:+:$STORYBOARD_DIR}"

echo
echo "================================================================================="
echo "==                          Launching Application...                           =="
echo "================================================================================="
exec "$PYTHON" "$LAUNCH_FILE"


