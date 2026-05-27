# ── EMA Dockerfile ───────────────────────────────────────────────
# 工程管理智能体 - Docker 容器化部署
# 构建: docker build -t ema:latest .
# 运行: docker run -d -p 6188:6188 -v ema-data:/app/data --name ema-api ema:latest

FROM python:3.12-slim

LABEL maintainer="EMA Team"
LABEL description="工程管理智能体 (Engineering Management Agent)"

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用 Docker 缓存层）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝源码
COPY . .

# 数据目录
RUN mkdir -p /app/data/chromadb /app/data/sessions /app/data/tenants /app/data/cache /app/data/uploads /app/output

# 端口
EXPOSE 6188

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fs http://localhost:6188/health || exit 1

# 启动
CMD ["python3", "src/main.py", "--host", "0.0.0.0", "--port", "6188"]
