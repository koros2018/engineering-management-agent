#!/bin/bash
# ── EMA 一键部署脚本 ──────────────────────────────────────────
# 用法:
#   ./deploy.sh                # 开发模式 (HTTP)
#   ./deploy.sh --prod         # 生产模式 (HTTPS + Nginx)
#   ./prod.sh --ssl            # 生产模式 + 自签名证书
#   ./deploy.sh --ssl --domain=your.com  # 生产模式 + 指定域名
# ──────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 解析参数
MODE="dev"
SSL=false
DOMAIN="localhost"

for arg in "$@"; do
    case $arg in
        --prod)   MODE="prod" ;;
        --ssl)    SSL=true ;;
        --domain=*) DOMAIN="${arg#*=}" ;;
    esac
done

echo "═══════════════════════════════════════════"
echo "  EMA 部署脚本"
echo "  模式: $MODE"
echo "  SSL:  $SSL"
echo "  域名: $DOMAIN"
echo "═══════════════════════════════════════════"

# 检查 .env
if [ ! -f .env ]; then
    echo "⚠️  .env 不存在，从 .env.example 创建..."
    cp .env.example .env
    echo "  ✅ 已创建 .env，请编辑填入实际值"
    echo "  ⚠️  特别是 JWT_SECRET 和 API Key"
fi

# 生成 SSL 证书
if [ "$SSL" = true ]; then
    echo ""
    echo "[SSL] 检查证书..."
    if [ ! -f docker/certs/selfsigned.crt ]; then
        echo "  生成自签名证书..."
        mkdir -p docker/certs
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout docker/certs/selfsigned.key \
            -out docker/certs/selfsigned.crt \
            -subj "/C=CN/ST=Shanghai/L=Shanghai/O=EMA/CN=$DOMAIN" \
            -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost,IP:127.0.0.1"
        echo "  ✅ 证书已生成"
    else
        echo "  ✅ 证书已存在"
    fi
    
    # 更新 .env 中的 SSL 配置
    if grep -q "EMA_SSL_ENABLED=false" .env; then
        sed -i 's/EMA_SSL_ENABLED=false/EMA_SSL_ENABLED=true/' .env
        sed -i "s/EMA_SERVER_NAME=localhost/EMA_SERVER_NAME=$DOMAIN/" .env
        echo "  ✅ .env SSL 配置已更新"
    fi
fi

# 构建并启动
echo ""
echo "[Docker] 构建并启动服务..."

if [ "$MODE" = "prod" ]; then
    # 生产模式: API + Nginx
    docker-compose build --no-cache api
    docker-compose --profile prod up -d
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  ✅ 生产模式部署完成"
    if [ "$SSL" = true ]; then
        echo "  🌐 https://$DOMAIN"
    else
        echo "  🌐 http://$DOMAIN"
    fi
    echo "  📡 API:  http://localhost:6188"
    echo "  📖 Docs: http://localhost:6188/docs"
    echo "═══════════════════════════════════════════"
else
    # 开发模式: API + UI
    docker-compose build --no-cache
    docker-compose --profile dev up -d
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  ✅ 开发模式部署完成"
    echo "  🌐 UI:   http://localhost:6189"
    echo "  📡 API:  http://localhost:6188"
    echo "  📖 Docs: http://localhost:6188/docs"
    echo "═══════════════════════════════════════════"
fi

# 等待健康检查
echo ""
echo "[Health] 等待服务就绪..."
sleep 5

if curl -sf http://localhost:6188/health > /dev/null 2>&1; then
    echo "  ✅ API 服务健康"
else
    echo "  ⚠️  API 服务未就绪，请检查日志:"
    echo "     docker-compose logs api"
fi

echo ""
echo "常用命令:"
echo "  docker-compose logs -f api    # 查看日志"
echo "  docker-compose down           # 停止服务"
echo "  docker-compose ps             # 查看状态"
echo "═══════════════════════════════════════════"
