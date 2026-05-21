#!/bin/bash
# deploy-prod.sh - EMA 生产环境一键部署
# 用法: bash deploy-prod.sh [--ssl] [--domain ema.example.com]

set -e

echo "╔══════════════════════════════════════════╗"
echo "║   EMA 工程管理智能体 - 生产环境部署       ║"
echo "╚══════════════════════════════════════════╝"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── 参数解析 ──────────────────────────────────────────────────

ENABLE_SSL=false
DOMAIN="localhost"
DATA_DIR="./data"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ssl) ENABLE_SSL=true; shift ;;
        --domain) DOMAIN="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

# ── 环境检查 ──────────────────────────────────────────────────

if ! command -v python3 &> /dev/null; then
    echo "❌ 需要 Python 3.10+"
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PY_VER"

if ! command -v pip3 &> /dev/null; then
    echo "❌ 需要 pip3"
    exit 1
fi

# ── 安装依赖 ──────────────────────────────────────────────────

echo ""
echo "📦 安装 Python 依赖..."
pip3 install -r requirements.txt -q 2>/dev/null || {
    echo "⚠️ pip 部分依赖安装失败，继续..."
}

# ── 创建目录 ──────────────────────────────────────────────────

mkdir -p "$DATA_DIR/chromadb" "$DATA_DIR/sessions" "$DATA_DIR/tenants"
mkdir -p output logs

# ── 检查 Ollama ───────────────────────────────────────────────

if command -v ollama &> /dev/null; then
    echo "✅ Ollama 已安装"
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        echo "✅ Ollama 服务运行中"
    else
        echo "⚠️ Ollama 服务未启动，请手动启动：ollama serve"
    fi
else
    echo "⚠️ 未安装 Ollama，部分 AI 功能不可用"
fi

# ── SSL 证书 ──────────────────────────────────────────────────

if $ENABLE_SSL; then
    CERT_DIR="./certs"
    mkdir -p "$CERT_DIR"

    if [ ! -f "$CERT_DIR/server.crt" ]; then
        echo "🔐 生成自签 SSL 证书..."
        openssl req -x509 -newkey rsa:2048 -keyout "$CERT_DIR/server.key" \
            -out "$CERT_DIR/server.crt" -days 365 -nodes \
            -subj "/CN=$DOMAIN" 2>/dev/null || {
            echo "⚠️ openssl 不可用，跳过 SSL"
            ENABLE_SSL=false
        }
    fi

    if [ -f "$CERT_DIR/server.crt" ]; then
        echo "✅ SSL 证书已就绪"
        SSL_ARGS="--ssl-keyfile $CERT_DIR/server.key --ssl-certfile $CERT_DIR/server.crt"
    fi
fi

# ── 系统服务（systemd）─────────────────────────────────────────

install_service() {
    SERVICE_FILE="/etc/systemd/system/ema.service"

    if [ -f "$SERVICE_FILE" ]; then
        echo "📝 更新 systemd 服务..."
        sudo systemctl stop ema 2>/dev/null || true
    fi

    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=EMA 工程管理智能体
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
Environment=PYTHONPATH=$SCRIPT_DIR/src
Environment=EMA_ENV=production
ExecStart=python3 src/main.py --host 0.0.0.0 --port 6188
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable ema
    sudo systemctl start ema
    echo "✅ systemd 服务已安装并启动"
}

# ── Nginx 配置 ────────────────────────────────────────────────

setup_nginx() {
    if ! command -v nginx &> /dev/null; then
        echo "⚠️ Nginx 未安装，跳过反向代理配置"
        return
    fi

    NGINX_CONF="/etc/nginx/sites-available/ema"
    sudo tee "$NGINX_CONF" > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 500M;

    location /ui/ {
        alias $SCRIPT_DIR/ui/;
        index index.html;
        try_files \$uri \$uri/ /ui/index.html;
    }

    location = / {
        return 301 /ui/index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:6188;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://127.0.0.1:6188/health;
    }

    location /docs {
        proxy_pass http://127.0.0.1:6188/docs;
    }
}
EOF

    sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/ema 2>/dev/null || true
    sudo nginx -t && sudo systemctl reload nginx
    echo "✅ Nginx 反向代理已配置"
}

# ── Docker 模式 ────────────────────────────────────────────────

if [ "$1" == "--docker" ]; then
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        echo "🐳 启动 Docker 模式..."
        docker-compose up -d --build
        echo "✅ Docker 容器已启动"
        echo ""
        echo "📍 访问: http://localhost/ui/index.html"
        exit 0
    else
        echo "❌ Docker 未安装"
        exit 1
    fi
fi

# ── 启动 ──────────────────────────────────────────────────────

echo ""
echo "🚀 启动 EMA 服务..."

PYTHONPATH=src nohup python3 src/main.py --host 0.0.0.0 --port 6188 \
    > logs/ema.log 2>&1 &
EMA_PID=$!
echo "   PID: $EMA_PID"

sleep 3

if curl -s http://127.0.0.1:6188/health > /dev/null 2>&1; then
    echo "✅ EMA API 已就绪 (http://127.0.0.1:6188)"
else
    echo "⚠️ API 启动中，请稍后检查"
fi

# ── UI 服务 ───────────────────────────────────────────────────

if ! curl -s http://127.0.0.1:6189/ui/ > /dev/null 2>&1; then
    echo "🚀 启动 UI 静态服务 (6189)..."
    nohup python3 - << 'PYEOF' > logs/ui.log 2>&1 &
import http.server, socketserver, os
ROOT = os.path.dirname(os.path.abspath('$SCRIPT_DIR'))
os.chdir(ROOT)
socketserver.TCPServer.allow_reuse_address = True
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
    def translate_path(self,path):
        if path.startswith('/ui'): rel=path[4:]
        else: rel=path
        if not rel or rel=='/': rel='/index.html'
        return os.path.join(ROOT,'ui',rel.lstrip('/'))
socketserver.TCPServer(('0.0.0.0', 6189), H).serve_forever()
PYEOF
    UI_PID=$!
    sleep 1
    echo "   UI PID: $UI_PID"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "✅ EMA 部署完成！"
echo ""
echo "📍 UI:  http://127.0.0.1:6189/ui/index.html"
echo "📊 API: http://127.0.0.1:6188"
echo "📚 文档: http://127.0.0.1:6188/docs"
echo "📋 日志: logs/ema.log"
echo ""
echo "🛠️  运维命令:"
echo "   查看状态: curl http://127.0.0.1:6188/health"
echo "   重启服务: kill $EMA_PID && bash deploy-prod.sh"
echo "   Docker:  bash deploy-prod.sh --docker"
echo "   systemd:  sudo systemctl status ema"
echo "═══════════════════════════════════════════"
