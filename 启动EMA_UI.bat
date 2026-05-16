@echo off
chcp 65001 >nul 2>&1
title EMA UI 前端

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   工程管理智能体 (EMA) - 前端UI      ║
echo  ╚══════════════════════════════════════╝
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 检查API服务是否运行
curl -s http://127.0.0.1:5188/health >nul 2>&1
if errorlevel 1 (
    echo  ⚠️  检测到 API 服务未运行
    echo.
    echo  请先运行 [启动EMA服务.bat] 或 [一键启动EMA.bat]
    echo.
    pause
    exit /b 1
)

REM 检查UI服务是否运行，没有则启动
curl -s http://127.0.0.1:5189/ >nul 2>&1
if errorlevel 1 (
    echo  [%time%] 启动 UI 文件服务 (端口 5189)...
    start /min "EMA-UI" python -m http.server 5189
    timeout /t 2 /nobreak >nul
)

echo  ✅ 服务已就绪，正在打开浏览器...
start http://127.0.0.1:5189/ui/index.html

echo.
echo  📍 访问地址: http://127.0.0.1:5189/ui/index.html
echo.
pause