#!/bin/bash
# EMA Docker Entrypoint
# 容器启动前执行：环境检查、目录初始化、健康验证
set -e

echo "═══════════════════════════════════════════"
echo "  工程管理智能体 (EMA) - Docker 启动"
echo "═══════════════════════════════════════════"

# 1. 初始化数据目录
echo "[1/4] 初始化数据目录..."
mkdir -p /app/data/{chromadb,sessions,tenants,cache,uploads,analytics,feedback,logs,projects}
echo "  ✅ 数据目录就绪"

# 2. 检查Python依赖
echo "[2/4] 检查运行环境..."
python3 -c "import fastapi, uvicorn, pydantic; print(f'  ✅ Python {__import__(\"sys\").version.split()[0]} | FastAPI OK')" 2>/dev/null || {
    echo "  ❌ 依赖检查失败"
    exit 1
}

# 3. 验证源码完整性
echo "[3/4] 验证源码..."
for f in src/api_server.py src/agent/base_agent.py src/blueprint/core.py; do
    if [ ! -f "/app/$f" ]; then
        echo "  ❌ 缺失关键文件: $f"
        exit 1
    fi
done
echo "  ✅ 源码完整"

# 4. 启动API服务
echo "[4/4] 启动API服务 (端口 ${EMA_PORT:-6188})..."
echo "═══════════════════════════════════════════"

# 用exec替换shell进程，确保信号正确传递
exec python3 src/api_server.py --host 0.0.0.0 --port "${EMA_PORT:-6188}" --workers "${EMA_API_WORKERS:-1}"
