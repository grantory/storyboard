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

REM Non-fatal: Check for git updates
echo [INFO] Checking for updates...
git pull
if errorlevel 1 (
    echo [WARN] Git pull failed or not in a git repository. Continuing...
) else (
    echo [OK] Repository is up to date
)

REM Optional: point Real-ESRGAN to local weights dir (if present)
set "REAL_ESRGAN_WEIGHTS_DIR=%SCRIPT_DIR%weights"

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
