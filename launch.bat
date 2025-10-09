@echo off
setlocal ENABLEDELAYEDEXPANSION

REM =================================================================================
REM ==                                                                             ==
REM ==                      Storyboard Project Launcher                            ==
REM ==                                                                             ==
REM =================================================================================
echo.

REM Project root is the directory of this script
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ---------------------------------------------------------------------------------
echo [STEP 1/5] Verifying prerequisites...
REM ---------------------------------------------------------------------------------

REM Check Python
echo [INFO] Checking for Python installation...
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed or not found in your system's PATH.
  echo.
  echo         Please install Python 3.10+ from https://www.python.org
  echo         and ensure it is added to your PATH before running this script again.
  echo.
  pause
  exit /b 1
)
echo [OK] Python found. Using system installation.
echo.

REM ---------------------------------------------------------------------------------
echo [STEP 2/5] Configuring and syncing the storyboard repository...
REM ---------------------------------------------------------------------------------

REM Configure external storyboard repository
set "GIT_STORYBOARD_URL=https://github.com/grantory/storyboard"
set "STORYBOARD_DIR=%SCRIPT_DIR%storyboard"

REM Clone or update external repository if Git is available
where git >nul 2>nul
if errorlevel 1 (
  echo [WARN] Git not found. Skipping storyboard repository sync.
  echo        The application may not function correctly without it.
) else (
  if exist "%STORYBOARD_DIR%\.git" (
    echo [INFO] Existing storyboard repository found. Attempting to update...
    pushd "%STORYBOARD_DIR%"
    git pull --ff-only
    popd
  ) else (
    if exist "%STORYBOARD_DIR%" (
      echo [WARN] Found an existing, non-git folder at '%STORYBOARD_DIR%'.
      echo        Skipping clone to avoid data loss.
    ) else (
      echo [INFO] Cloning storyboard repository into '%STORYBOARD_DIR%'...
      git clone "%GIT_STORYBOARD_URL%" "%STORYBOARD_DIR%"
    )
  )
)
echo [OK] Storyboard repository sync complete.
echo.

REM ---------------------------------------------------------------------------------
echo [STEP 3/5] Installing Python dependencies...
REM ---------------------------------------------------------------------------------

REM Install local requirements if present
if exist "requirements.txt" (
  echo [INFO] Found local 'requirements.txt'. Installing dependencies...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Failed to install local dependencies. Aborting.
    pause
    exit /b 1
  )
  echo [OK] Local dependencies installed successfully.
 ) else (
  echo [INFO] No local 'requirements.txt' found. Skipping.
 )
echo.

REM Optionally install storyboard repo requirements if present
if exist "%STORYBOARD_DIR%\requirements.txt" (
  echo [INFO] Found storyboard 'requirements.txt'. Installing dependencies...
  python -m pip install -r "%STORYBOARD_DIR%\requirements.txt"
  if errorlevel 1 (
    echo [WARN] Failed to install some storyboard dependencies. The app will continue,
    echo        but some features might not work as expected.
  ) else (
    echo [OK] Storyboard dependencies installed successfully.
  )
)
echo.

REM ---------------------------------------------------------------------------------
echo [STEP 4/5] Setting up environment and configuration...
REM ---------------------------------------------------------------------------------

REM Point Real-ESRGAN to the packaged weights directory
set "REAL_ESRGAN_WEIGHTS_DIR=%SCRIPT_DIR%weights"

REM Verify weights are present
echo [INFO] Checking for Real-ESRGAN weights...
if not exist "%REAL_ESRGAN_WEIGHTS_DIR%\realesr-general-x4v3.pth" (
  echo.
  echo [WARN] Real-ESRGAN weights not found at:
  echo        %REAL_ESRGAN_WEIGHTS_DIR%\realesr-general-x4v3.pth
  echo        The application will attempt to download them at runtime.
  echo.
) else (
    echo [OK] Weights found.
)

REM Create .env if missing and optionally capture OpenRouter key
if exist .env (
  echo [INFO] Existing '.env' file found. Skipping creation.
) else (
  echo.
  echo [INFO] '.env' file not found. Starting interactive setup...
  echo +------------------------------------------------------------------------+
  echo ^| Enter your OpenRouter API Key. If you don't have one, press Enter      ^|
  echo ^| to leave it blank and you can set it in the '.env' file later.         ^|
  echo +------------------------------------------------------------------------+
  set "INPUT_OPENROUTER_KEY="
  set /p "INPUT_OPENROUTER_KEY= > Enter OPENROUTER_API_KEY: "
  echo.
  echo [INFO] Creating .env file with default settings...
  >.env echo OPENROUTER_API_KEY=!INPUT_OPENROUTER_KEY!
  >>.env echo V2_OPENROUTER_CONTEXT_MODEL=openai/gpt-5-mini
  >>.env echo V2_OPENROUTER_CONTEXT_VISION_MODEL=openai/gpt-5-mini
  >>.env echo V2_OPENROUTER_DIRECTOR_MODEL=openai/gpt-5
  >>.env echo V2_OPENROUTER_DIRECTOR_VISION_MODEL=openai/gpt-5
  >>.env echo V2_OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview
  >>.env echo V2_MAX_CONCURRENT_REQUESTS=5
  >>.env echo V2_REQUEST_TIMEOUT_SEC=60
  echo [OK] '.env' file saved successfully.
)
echo.

REM ---------------------------------------------------------------------------------
echo [STEP 5/5] Preparing to launch the application...
REM ---------------------------------------------------------------------------------

REM Determine launch target (prefer local, fallback to storyboard)
set "LAUNCH_FILE="
if exist "%SCRIPT_DIR%src\gui\main.py" set "LAUNCH_FILE=%SCRIPT_DIR%src\gui\main.py"
if not defined LAUNCH_FILE if exist "%STORYBOARD_DIR%\src\gui\main.py" set "LAUNCH_FILE=%STORYBOARD_DIR%\src\gui\main.py"

if not defined LAUNCH_FILE (
  echo [ERROR] Could not find the application entry point to launch.
  echo         Looked for:
  echo         - %SCRIPT_DIR%src\gui\main.py
  echo         - %STORYBOARD_DIR%\src\gui\main.py
  echo.
  pause
  exit /b 1
)

echo [INFO] Launch target found: %LAUNCH_FILE%
echo [INFO] Setting up Python Path...

REM Launch the GUI app with both roots on PYTHONPATH
set "PYTHONPATH=%SCRIPT_DIR%"
if exist "%STORYBOARD_DIR%" set "PYTHONPATH=%PYTHONPATH%;%STORYBOARD_DIR%"

echo.
echo =================================================================================
echo ==                          Launching Application...                           ==
echo =================================================================================
python "%LAUNCH_FILE%"

endlocal