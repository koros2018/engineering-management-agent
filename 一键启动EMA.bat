@echo off
chcp 65001 >nul 2>&1
title EMA - 一键启动

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   工程管理智能体 (EMA) - 一键启动         ║
echo  ╠══════════════════════════════════════════╣
echo  ║  Slogan: 工程管理，从"人管"到            ║
echo  ║         "智能体协管"                     ║
echo  ╚══════════════════════════════════════════╝
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 启动后端API服务（端口5188，后台）
echo [%time%] 启动 API 服务 (端口 5188)...
start /min "EMA-API" python "%SCRIPT_DIR%src\main.py" --port 5188
echo  [%time%] 等待服务就绪...
timeout /t 3 /nobreak >nul

REM 启动UI静态文件服务（端口5189，后台）
echo [%time%] 启动 UI 文件服务 (端口 5189)...
start /min "EMA-UI" python -m http.server 5189
timeout /t 2 /nobreak >nul

REM 检查服务状态
curl -s http://127.0.0.1:5188/health >nul 2>&1
if errorlevel 1 (
    echo  ⚠️  API 服务可能未就绪
) else (
    echo  ✅ API 服务已就绪 (http://127.0.0.1:5188)
)

curl -s http://127.0.0.1:5189/ >nul 2>&1
if errorlevel 1 (
    echo  ⚠️  UI 服务可能未就绪
) else (
    echo  ✅ UI 服务已就绪
)

REM 打开浏览器
echo [%time%] 打开前端UI...
start http://127.0.0.1:5189/ui/index.html

echo.
echo  ═══════════════════════════════════════════
echo  ✅ 启动完成！
echo.
echo  📍 前端UI: http://127.0.0.1:5189/ui/index.html
echo  📊 API:    http://127.0.0.1:5188
echo  📚 文档:   http://127.0.0.1:5188/docs
echo.
echo  按任意键退出（服务继续在后台运行）...
pause >nul