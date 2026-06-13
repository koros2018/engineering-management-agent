#!/usr/bin/env python3
import http.server, socketserver, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI_DIR = os.path.join(ROOT, 'ui')
PORT = 6189
os.chdir(ROOT)
socketserver.TCPServer.allow_reuse_address = True

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass
    def translate_path(self, path):
        if path.startswith('/ui'):
            rel = path[4:]
        else:
            rel = path
        if not rel or rel == '/':
            rel = '/index.html'
        return os.path.join(UI_DIR, rel.lstrip('/'))

with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
    print(f'EMA UI server on http://127.0.0.1:{PORT}')
    httpd.serve_forever()
