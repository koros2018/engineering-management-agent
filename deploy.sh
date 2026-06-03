#!/bin/bash
# EMA 一键部署脚本 (Docker)
# 工程管理智能体 - Docker 快速部署
# 用法: ./deploy.sh [--prod]

set -e

# Docker Compose v2 兼容
if docker compose version > /dev/null 2>&1; then
  DOCKER_COMPOSE="docker compose"
else
  DOCKER_COMPOSE="docker-compose"
fi

PROFILE=""
if [ "$1" = "--prod" ]; then
  PROFILE="--profile prod"
fi

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

# 检查 .env
if [ ! -f .env ]; then
    echo "📝 未找到 .env，从 .env.example 创建..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 修改默认配置（尤其是 JWT_SECRET），然后重新运行"
    exit 1
fi

cd "$(dirname "$0")"

# 构建
echo "🔨 构建镜像..."
$DOCKER_COMPOSE build --no-cache

# 启动
echo "🚀 启动服务..."
$DOCKER_COMPOSE $PROFILE up -d

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
        echo "🖥️  UI:      http://localhost:6189"
        echo ""
        echo "停止: $DOCKER_COMPOSE down"
        echo "日志: $DOCKER_COMPOSE logs -f api"
        echo "═══════════════════════════════════════════"
        exit 0
    fi
    sleep 2
done

echo "⚠️  服务启动超时，请检查日志: $DOCKER_COMPOSE logs api"
