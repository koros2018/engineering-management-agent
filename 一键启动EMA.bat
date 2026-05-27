@echo off
chcp 65001 >nul 2>&1
title EMA - 一键启动 (Python直部署)
echo ============================================
echo   EMA 工程管理智能体 - 启动
echo ============================================
echo.

set "ROOT=%~dp0"
cd /d "%ROOT%"

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause & exit /b 1
)

REM ── 启动 API 服务 ──────────────────────────────────
echo [1/2] 启动 API 服务 (端口 6188)...
start "EMA-API" /min python "%ROOT%src\main.py" --port 6188
timeout /t 3 /nobreak >nul

REM ── 启动 UI 静态文件服务 ────────────────────────────
echo [2/2] 启动 UI 服务 (端口 6189)...

REM 动态生成 UI 服务器脚本
set "UISCRIPT=%TEMP%\ema_ui_serve.py"
echo import http.server, socketserver, shutil, os > "%UISCRIPT%"
echo ROOT = r"%ROOT:~0,-1%" >> "%UISCRIPT%"
echo os.chdir(ROOT) >> "%UISCRIPT%"
echo socketserver.TCPServer.allow_reuse_address = True >> "%UISCRIPT%"
echo class H(http.server.SimpleHTTPRequestHandler): >> "%UISCRIPT%"
echo     def log_message(self,*a): pass >> "%UISCRIPT%"
echo     def copyfile(self,s,o): >> "%UISCRIPT%"
echo         try: shutil.copyfileobj(s,o) >> "%UISCRIPT%"
echo         except: pass >> "%UISCRIPT%"
echo     def translate_path(self,path): >> "%UISCRIPT%"
echo         if path.startswith('/ui'): rel=path[4:] >> "%UISCRIPT%"
echo         else: rel=path >> "%UISCRIPT%"
echo         if not rel or rel=='/': rel='/index.html' >> "%UISCRIPT%"
echo         return os.path.join(ROOT,'ui',rel.lstrip('/')) >> "%UISCRIPT%"
echo socketserver.TCPServer(('', 6189), H).serve_forever() >> "%UISCRIPT%"

start "EMA-UI" /min python "%UISCRIPT%"
timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo   启动完成！
echo.
echo   UI:      http://127.0.0.1:6189/ui/
echo   API:     http://127.0.0.1:6188
echo   Admin:   http://127.0.0.1:6189/ui/admin.html
echo   Health:  http://127.0.0.1:6188/health
echo.
echo   浏览器即将打开...
echo ============================================
timeout /t 2 /nobreak >nul

start http://127.0.0.1:6189/ui/
echo.
pause
