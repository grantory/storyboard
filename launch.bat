@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Project root is the directory of this script
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check Python
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed or not in PATH.
  echo Please install Python 3.10+ from https://www.python.org and rerun launch.bat
  pause
  exit /b 1
)

REM Create venv if missing
if not exist .venv (
  echo Creating virtual environment .venv ...
  python -m venv .venv
)

REM Activate venv
call .venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install requirements
echo Installing requirements...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install dependencies.
  pause
  exit /b 1
)

REM Prepare .env
if not exist .env (
  if exist env.example (
    copy /Y env.example .env >nul
    echo Created .env from env.example
  ) else (
    echo OPENROUTER_API_KEY=>.env
    echo V2_OPENROUTER_CONTEXT_MODEL=openai/gpt-5-mini>>.env
    echo V2_OPENROUTER_CONTEXT_VISION_MODEL=openai/gpt-5-mini>>.env
    echo V2_OPENROUTER_DIRECTOR_MODEL=openai/gpt-5>>.env
    echo V2_OPENROUTER_DIRECTOR_VISION_MODEL=openai/gpt-5>>.env
    echo V2_OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview>>.env
    echo V2_MAX_CONCURRENT_REQUESTS=5>>.env
    echo V2_REQUEST_TIMEOUT_SEC=60>>.env
    echo Created default .env
  )
)

REM Warn if API key is empty
for /f "usebackq tokens=*" %%A in (`findstr /b "OPENROUTER_API_KEY=" .env`) do (
  set "LINE=%%A"
)
if "!LINE!"=="OPENROUTER_API_KEY=" (
  echo.
  echo NOTE: OPENROUTER_API_KEY is empty in .env
  echo Open .env in a text editor and paste your API key after OPENROUTER_API_KEY=
  echo.
)

REM Point Real-ESRGAN to the packaged weights directory
set REAL_ESRGAN_WEIGHTS_DIR=%SCRIPT_DIR%weights

REM Verify weights are present
if not exist "%REAL_ESRGAN_WEIGHTS_DIR%\realesr-general-x4v3.pth" (
  echo.
  echo WARNING: Real-ESRGAN weights not found at %REAL_ESRGAN_WEIGHTS_DIR%\realesr-general-x4v3.pth
  echo The app will attempt to download at runtime. To avoid this, place the file there and re-launch.
  echo.
)

REM Launch the GUI app
set PYTHONPATH=%SCRIPT_DIR%
python -m src.gui.main

endlocal
