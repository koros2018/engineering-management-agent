#!/bin/bash
# EMA 一键部署脚本 (Docker)
# 工程管理智能体 - Docker 快速部署

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   工程管理智能体 (EMA) - Docker 部署      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 未找到 Docker，请先安装: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 未找到 docker-compose"
    exit 1
fi

cd "$(dirname "$0")"

# 构建
echo "🔨 构建镜像..."
docker-compose build --no-cache

# 启动
echo "🚀 启动服务..."
docker-compose up -d

# 等待健康检查
echo "⏳ 等待服务就绪..."
for i in $(seq 1 30); do
    if curl -fs http://127.0.0.1:6188/health > /dev/null 2>&1; then
        echo ""
        echo "═══════════════════════════════════════════"
        echo "✅ EMA 部署成功！"
        echo ""
        echo "📊 API:     http://localhost:6188"
        echo "📚 Swagger: http://localhost:6188/docs"
        echo "🏥 Health:  http://localhost:6188/health"
        echo ""
        echo "停止: docker-compose down"
        echo "日志: docker-compose logs -f api"
        echo "═══════════════════════════════════════════"
        exit 0
    fi
    sleep 2
done

echo "⚠️  服务启动超时，请检查日志: docker-compose logs -f api"
