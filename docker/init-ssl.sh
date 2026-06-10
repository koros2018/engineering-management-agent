#!/bin/bash
# ── EMA SSL 证书初始化脚本 ────────────────────────────────────
# 用法:
#   ./init-ssl.sh          # 生成自签名证书（开发/测试）
#   ./init-ssl.sh --prod   # 提示配置 Let's Encrypt（生产）
# ──────────────────────────────────────────────────────────────

set -e

CERT_DIR="$(cd "$(dirname "$0")/certs" && pwd)"

echo "═══════════════════════════════════════════"
echo "  EMA SSL 证书初始化"
echo "═══════════════════════════════════════════"

if [ "$1" == "--prod" ]; then
    echo ""
    echo "生产环境 SSL 证书配置"
    echo ""
    echo "选项 1: Let's Encrypt (推荐，免费自动续期)"
    echo "  需要: certbot + 域名解析到服务器"
    echo "  命令: certbot certonly --standalone -d your-domain.com"
    echo "  证书路径: /etc/letsencrypt/live/your-domain.com/"
    echo ""
    echo "选项 2: 商业证书"
    echo "  将证书文件放到: $CERT_DIR/"
    echo "  需要文件:"
    echo "    - fullchain.pem (或 selfsigned.crt)"
    echo "    - privkey.pem  (或 selfsigned.key)"
    echo ""
    echo "然后更新 .env:"
    echo "  EMA_SSL_CERT_PATH=/path/to/fullchain.pem"
    echo "  EMA_SSL_KEY_PATH=/path/to/privkey.pem"
    echo "  EMA_SERVER_NAME=your-domain.com"
else
    echo "开发/测试环境: 生成自签名证书..."
    
    if [ -f "$CERT_DIR/selfsigned.crt" ] && [ -f "$CERT_DIR/selfsigned.key" ]; then
        echo "  ✅ 自签名证书已存在"
        echo "  路径: $CERT_DIR/selfsigned.crt"
        echo "  过期: $(openssl x509 -enddate -noout -in $CERT_DIR/selfsigned.crt 2>/dev/null | cut -d= -f2)"
    else
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$CERT_DIR/selfsigned.key" \
            -out "$CERT_DIR/selfsigned.crt" \
            -subj "/C=CN/ST=Shanghai/L=Shanghai/O=EMA/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,DNS:ema.local,IP:127.0.0.1"
        echo "  ✅ 自签名证书已生成"
    fi
    
    echo ""
    echo "自签名证书仅用于开发/测试！"
    echo "生产环境请运行: $0 --prod"
fi

echo "═══════════════════════════════════════════"
