@echo off
chcp 65001 >nul 2>&1
title EMA API 服务

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   工程管理智能体 (EMA) - 后台服务      ║
echo  ╠══════════════════════════════════════╣
echo  ║  技术标准: Manus Agent 架构            ║
echo  ╚══════════════════════════════════════╝
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装
    pause
    exit /b 1
)

REM 启动API服务（端口5188，后台，最小化）
echo [%time%] 启动 API 服务 (端口 5188)...
start /min "EMA-API" python "%SCRIPT_DIR%src\main.py" --port 5188
echo  [%time%] 等待服务就绪...
timeout /t 3 /nobreak >nul

REM 检查服务状态
curl -s http://127.0.0.1:5188/health >nul 2>&1
if errorlevel 1 (
    echo  ⚠️  服务可能未就绪，请稍后刷新
) else (
    echo  ✅ API 服务已就绪
)

echo.
echo  ═══════════════════════════════════════
echo  📍 API:  http://127.0.0.1:5188
echo  📚 文档: http://127.0.0.1:5188/docs
echo  📍 UI:   http://127.0.0.1:5189/ui/index.html
echo.
echo  服务已在后台运行，关闭窗口不会停止
echo  如需停止，请结束 python 进程
echo  ═══════════════════════════════════════
pause