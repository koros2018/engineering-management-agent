@echo off
chcp 65001 >nul 2>&1
title EMA UI

echo.
echo ====================================
echo   EMA UI
echo ====================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [INFO] Checking API service...
ping -n 2 127.0.0.1 >nul 2>&1

echo [INFO] Starting UI service (port 5189)...
start /min python -m http.server 5189

echo [INFO] Waiting...
ping -n 3 127.0.0.1 >nul 2>&1

echo.
echo ====================================
echo   UI: http://127.0.0.1:5189/ui/index.html
echo ====================================
echo.

start http://127.0.0.1:5189/ui/index.html

pause
