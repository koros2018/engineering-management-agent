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

REM ── API 服务 ──────────────────────────────────────
echo [INFO] Starting API service (port 5188)...
start /min python "%SCRIPT_DIR%src\main.py" --port 5188

echo [INFO] Waiting for API...
ping -n 4 127.0.0.1 >nul 2>&1

REM ── UI 服务 ──────────────────────────────────────
REM 使用自定义 Python 服务器，正确映射 /ui/ 路径
echo [INFO] Starting UI service (port 5189)...

set UI_SERVER_SCRIPT=%TEMP%\ema_ui_serve.py
python -c "import os
ROOT=r'%SCRIPT_DIR:~0,-1%'
PY='''
import http.server, socketserver, shutil, os, sys
ROOT=r\"%s\"
os.chdir(ROOT)
socketserver.TCPServer.allow_reuse_address = True
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
    def copyfile(self,s,o):
        try: shutil.copyfileobj(s,o)
        except: pass
    def translate_path(self,path):
        if path.startswith('/ui'): rel=path[4:]
        else: rel=path
        if not rel or rel=='/': rel='/index.html'
        return os.path.join(ROOT,'ui',rel.lstrip('/'))
with socketserver.TCPServer((''0.0.0.0'', 5189), H) as httpd:
    httpd.serve_forever()
'''.replace('ROOT=r\"%s\"', 'ROOT=r\"'+ROOT.replace('\\','\\\\')+'\"')
with open(r'%UI_SERVER_SCRIPT:~0,-1%','w') as f:
    f.write(PY.replace('%TEMP%',os.environ.get('TEMP','')))
" >nul 2>&1

REM Write the server script properly using a temp .py file approach
(
echo import http.server, socketserver, shutil, os, sys
echo ROOT = r"%SCRIPT_DIR:~0,-1%"
echo os.chdir(ROOT)
echo socketserver.TCPServer.allow_reuse_address = True
echo class H(http.server.SimpleHTTPRequestHandler):
echo     def log_message(self,*a): pass
echo     def copyfile(self,s,o):
echo         try: shutil.copyfileobj(s,o)
echo         except: pass
echo     def translate_path(self,path):
echo         if path.startswith('/ui'): rel=path[4:]
echo         else: rel=path
echo         if not rel or rel=='/': rel='/index.html'
echo         return os.path.join(ROOT,'ui',rel.lstrip('/'))
echo with socketserver.TCPServer(('0.0.0.0', 5189), H) as httpd:
echo     httpd.serve_forever()
) > "%TEMP%\ema_ui_serve.py"

start /min python "%TEMP%\ema_ui_serve.py"

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