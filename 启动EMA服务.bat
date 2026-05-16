@echo off
chcp 65001 >nul 2>&1
title EMA API 服务

echo.
echo  ╔══════════════════════════════════════╗
echo  ║   工程管理智能体 (EMA) - 后台服务      ║
echo  ╠══════════════════════════════════════╣
echo  ║  技术标准: Manus Agent 架构            ║
echo  ║  端口: 5188                           ║
echo  ╚══════════════════════════════════════╝
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 启动服务（后台运行）
echo [%time%] 正在启动 API 服务...
start /min "EMA-API" python "%SCRIPT_DIR%src\main.py" --port 5188

REM 等待服务就绪
echo [%time%] 等待服务启动...
timeout /t 3 /nobreak >nul

REM 检查是否启动成功
curl -s http://127.0.0.1:5188/health >nul 2>&1
if errorlevel 1 (
    echo [警告] 服务可能未就绪，请检查日志
) else (
    echo.
    echo  ✅ API 服务已启动
    echo  📍 http://127.0.0.1:5188
    echo  📊 http://127.0.0.1:5188/docs (API文档)
    echo.
    echo  按任意键打开前端UI...
    pause >nul
    start "" "%SCRIPT_DIR%ui\index.html"
)

echo.
echo 提示：服务已在后台运行，关闭窗口不会停止服务
echo 如需停止服务，请打开任务管理器结束 python 进程
pause