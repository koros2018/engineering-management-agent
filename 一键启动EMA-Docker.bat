@echo off
chcp 65001 >nul 2>&1
title EMA - Docker 部署
echo ============================================
echo   EMA 工程管理智能体 - Docker 部署
echo ============================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Docker CLI
    echo.
    echo 请安装 Docker Desktop:
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    echo 安装后重新运行此脚本。
    pause & exit /b 1
)

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo [1/3] 构建 Docker 镜像...
docker-compose build --no-cache
if errorlevel 1 (
    echo [错误] 构建失败
    pause & exit /b 1
)

echo.
echo [2/3] 启动服务...
docker-compose up -d
if errorlevel 1 (
    echo [错误] 启动失败
    pause & exit /b 1
)

echo.
echo [3/3] 等待服务就绪...
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   Docker 部署完成！
echo.
echo   UI:      http://localhost/ui/
echo   API:     http://localhost/api/v1/...
echo   Admin:   http://localhost/ui/admin.html
echo   Health:  http://localhost/api/v1/health
echo.
echo   常用命令:
echo     停止:  docker-compose down
echo     日志:  docker-compose logs -f api
echo     重启:  docker-compose restart
echo     更新:  docker-compose build --no-cache ^&^& docker-compose up -d
echo ============================================
echo.

docker-compose ps

echo.
set /p OPEN="是否打开浏览器？(Y/n): "
if /i "%OPEN%"=="Y" start http://localhost/ui/
if /i "%OPEN%"=="y" start http://localhost/ui/

echo.
pause
