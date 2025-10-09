@echo off
chcp 65001 >nul 2>&1
cls
echo.
echo ========================================
echo   Project Maestro v2 - AI Storyboard
echo ========================================
echo.

REM Ensure we are running from this script's directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    echo.
    pause
    exit /b 1
)

REM Check for git updates
echo [INFO] Checking for updates...
git pull >nul 2>&1
if errorlevel 1 (
    echo [WARN] Git pull failed or not in a git repository
) else (
    echo [OK] Repository is up to date
)

REM Set environment variable for Real-ESRGAN weights
set "REAL_ESRGAN_WEIGHTS_DIR=%SCRIPT_DIR%weights"
echo [INFO] REAL_ESRGAN_WEIGHTS_DIR=%REAL_ESRGAN_WEIGHTS_DIR%

REM Ensure output directory exists and is writable
set "OUTPUT_DIR=%SCRIPT_DIR%output"
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%" 2>nul
)
if errorlevel 1 (
    echo [ERROR] Cannot create output directory: %OUTPUT_DIR%
    echo         Move this project to a writable location (e.g. Documents or Desktop)
    echo         and avoid protected folders like Program Files.
    echo.
    pause
    exit /b 1
) else (
    echo [OK] Output directory ready: %OUTPUT_DIR%
)

REM Check if .env file exists and has API key
if not exist ".env" (
    echo [INFO] Creating .env file...
    echo # Project Maestro v2 Configuration > .env
    echo OPENROUTER_API_KEY= >> .env
    echo V2_OPENROUTER_CONTEXT_MODEL=gpt-4o-mini >> .env
    echo V2_OPENROUTER_DIRECTOR_MODEL=gpt-4o >> .env
    echo V2_OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image-preview >> .env
    echo.
    echo [WARN] Please edit .env file and add your OPENROUTER_API_KEY
    echo.
) else (
    REM Check if API key is set
    findstr /C:"OPENROUTER_API_KEY=sk-" .env >nul 2>&1
    if errorlevel 1 (
        echo [WARN] OPENROUTER_API_KEY not found in .env file
        echo Please add your API key to .env file
        echo.
    ) else (
        echo [OK] API key found in .env file
    )
)

REM Launch the application
echo [INFO] Launching Project Maestro v2...
echo.
python -m src.gui.main

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error
    echo.
    pause
)
