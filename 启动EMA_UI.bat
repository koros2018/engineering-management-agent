@echo off
chcp 65001 >nul 2>&1
title EMA UI 前端

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   工程管理智能体 (EMA) - 前端UI      ║
echo  ╚══════════════════════════════════════╝
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0

REM 检查API服务是否运行
curl -s http://127.0.0.1:5188/health >nul 2>&1
if errorlevel 1 (
    echo  ⚠️  检测到 API 服务未运行
    echo.
    echo  请先运行 [启动EMA服务.bat] 启动后端
    echo.
    set /p choice=是否现在启动后端服务? (Y/N):
    if /i "%choice%"=="Y" (
        start "" "%SCRIPT_DIR%启动EMA服务.bat"
        echo  正在启动后端服务，请稍候...
        timeout /t 4 /nobreak >nul
    ) else (
        echo  已取消
        pause
        exit /b 0
    )
)

REM 直接打开HTML文件（默认浏览器）
echo  ✅ 正在打开前端UI...
start "" "%SCRIPT_DIR%ui\index.html"

echo.
echo  📍 UI 地址: ui\index.html (已用默认浏览器打开)
echo.
pause