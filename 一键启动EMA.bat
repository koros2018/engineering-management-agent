@echo off
chcp 65001 >nul 2>&1
title EMA - one-click start

echo.
echo ============================================
echo   Engineering Management Agent - Start
echo ============================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [INFO] Starting API service (port 5188)...
start /min python "%SCRIPT_DIR%src\main.py" --port 5188

echo [INFO] Waiting for API...
ping -n 4 127.0.0.1 >nul 2>&1

echo [INFO] Starting UI service (port 5189)...
start /min python -m http.server 5189

echo [INFO] Waiting for UI...
ping -n 3 127.0.0.1 >nul 2>&1

echo.
echo ============================================
echo   DONE!
echo.
echo   UI:  http://127.0.0.1:5189/ui/index.html
echo   API: http://127.0.0.1:5188
echo.
echo   Press any key to open browser...
pause >nul

start http://127.0.0.1:5189/ui/index.html

echo [INFO] Browser opened. Services running in background.
echo [INFO] To stop: Task Manager - end python processes
pause
