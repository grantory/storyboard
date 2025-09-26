@echo off
echo ========================================
echo    Git Commit Helper - KeyFrame App
echo ========================================
echo.

echo Checking git status...
git status
echo.

echo ========================================
echo What would you like to do?
echo ========================================
echo 1. Add all changes and commit
echo 2. Add specific files and commit
echo 3. Just push existing commits
echo 4. Show git log
echo 5. Exit
echo.

set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto addall
if "%choice%"=="2" goto addspecific
if "%choice%"=="3" goto push
if "%choice%"=="4" goto log
if "%choice%"=="5" goto exit
goto invalid

:addall
echo.
echo Adding all changes...
git add .
echo.
set /p message="Enter commit message: "
git commit -m "%message%"
echo.
echo Committed successfully! Pushing to GitHub...
git push origin main
echo.
echo Done! Your changes are now on GitHub.
pause
goto exit

:addspecific
echo.
echo Current modified files:
git status --porcelain
echo.
set /p files="Enter file names to add (space separated, or . for all): "
git add %files%
echo.
set /p message="Enter commit message: "
git commit -m "%message%"
echo.
echo Committed successfully! Pushing to GitHub...
git push origin main
echo.
echo Done! Your changes are now on GitHub.
pause
goto exit

:push
echo.
echo Pushing existing commits to GitHub...
git push origin main
echo.
echo Done! Your commits are now on GitHub.
pause
goto exit

:log
echo.
echo Recent git commits:
git log --oneline -10
echo.
pause
goto menu

:invalid
echo.
echo Invalid choice! Please try again.
pause
goto menu

:menu
cls
goto start

:exit
echo.
echo Thanks for using Git Commit Helper!
pause
:: Build GUI (one-folder)
echo.
echo ========================================
echo Build GUI (one-folder)
echo ========================================
echo.
pyinstaller --noconfirm --clean --name MaestroV2 --onedir --add-data "weights;weights" --hidden-import cv2 --hidden-import basicsr --hidden-import realesrgan src/gui/main.py
