@echo off
chcp 65001 >nul 2>&1
title EMA UI Service

echo.
echo ====================================
echo   EMA UI Service
echo ====================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [INFO] Checking API service...

echo [INFO] Starting UI service (port 5189)...

REM Write and launch the custom UI server
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

echo [INFO] Waiting...
ping -n 3 127.0.0.1 >nul 2>&1

echo.
echo ====================================
echo   UI: http://127.0.0.1:5189/ui/index.html
echo ====================================
echo.

start http://127.0.0.1:5189/ui/index.html

pause