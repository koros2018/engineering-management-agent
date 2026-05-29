# ── EMA Dockerfile (Multi-Stage, Production) ───────────────────
# 工程管理智能体 - Docker 容器化部署
#
# 构建:
#   docker build -t ema:latest .
# 运行:
#   docker run -d -p 6188:6188 -v ema-data:/app/data --name ema-api ema:latest
# 开发:
#   docker compose --profile dev up -d
# 生产:
#   docker compose --profile prod up -d
# ──────────────────────────────────────────────────────────────

# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# 利用层缓存：依赖不变时不重新安装
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="EMA Team"
LABEL description="工程管理智能体 (Engineering Management Agent)"
LABEL version="2.4.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EMA_ENV=production

# 运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# 从builder复制Python包
COPY --from=builder /install /usr/local

# 创建非root用户
RUN groupadd -r ema && useradd -r -g ema -d /app -s /bin/bash ema

WORKDIR /app

# 拷贝源码（分层：依赖→源码→配置→脚本，最大化缓存命中率）
COPY --chown=ema:ema src/ ./src/
COPY --chown=ema:ema ui/ ./ui/
COPY --chown=ema:ema docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# 初始化数据目录
RUN mkdir -p /app/data/{chromadb,sessions,tenants,cache,uploads,analytics,feedback,logs,projects,output} \
    && chown -R ema:ema /app

EXPOSE 6188

# 健康检查（30秒间隔，5秒超时，15秒启动宽限，3次失败重启）
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fs http://localhost:6188/health || exit 1

USER ema

# tini做init进程（正确处理SIGTERM + 回收僵尸进程）
ENTRYPOINT ["tini", "--"]
CMD ["./docker-entrypoint.sh"]
