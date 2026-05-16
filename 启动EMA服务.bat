@echo off
chcp 65001 >nul 2>&1
title EMA API Service

echo.
echo ====================================
echo   EMA API Service
echo ====================================
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

echo [INFO] Waiting...
ping -n 4 127.0.0.1 >nul 2>&1

echo.
echo ====================================
echo   API: http://127.0.0.1:5188
echo   Docs: http://127.0.0.1:5188/docs
echo   UI:   http://127.0.0.1:5189/ui/index.html
echo.
echo   Running in background. Close window to keep running.
echo ====================================
pause
