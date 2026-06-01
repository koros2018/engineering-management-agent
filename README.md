# 🏗️ EMA — 工程管理智能体

> **工程管理，从"人管"到"智能体协管"**

EMA（Engineering Management Agent）是一款面向工程全生命周期的 AI 智能体平台，支持 DWG/DXF/PDF 图纸解析、AI 智能审查、工程文档生成、成本预算、知识库搜索等核心能力。

## ✨ 核心功能

| 功能 | 说明 | 状态 |
|------|------|------|
| 📐 图纸解析 | DWG/DXF/PDF 多格式解析，图层语义识别 | ✅ |
| 🔍 AI 智能审查 | 15条国标审查规则 + 12条几何审查 | ✅ |
| 📄 文档生成 | 设计说明/技术交底/工程量清单/技术核定单/招投标文件 | ✅ |
| 💰 成本预算 | 工程量提取 + 单价匹配 + 造价计算 + 地区系数 | ✅ |
| 📚 知识库 | 57个国标规范搜索 + 推荐 | ✅ |
| 📊 性能监控 | 全请求延迟追踪 + 自动告警 | ✅ |
| 📱 微信登录 | 扫码登录 + 注册绑定 | ✅ |
| 💳 支付系统 | 微信支付/支付宝（SDK就绪，需配置商户号） | 🔧 |
| 🐳 Docker部署 | 一键部署 + Nginx反向代理 | ✅ |

## 🚀 快速开始

### 方式一：本机部署（推荐开发/试用）

```bash
# 1. 克隆项目
git clone <repo-url> && cd engineering-management-agent

# 2. 安装依赖
pip3 install -r requirements.txt

# 3. 启动API服务
python3 src/api_server.py --host 0.0.0.0 --port 6188

# 4. 启动UI（另开终端）
cd ui && python3 -m http.server 6189

# 5. 访问
open http://localhost:6189
```

### 方式二：Docker 部署（推荐生产）

```bash
# 构建 + 启动
docker-compose up -d --build

# 查看状态
docker-compose ps
docker-compose logs -f api

# 访问
open http://localhost:6188/docs   # API文档
open http://localhost:6189         # UI
```

### 方式三：一键部署脚本

```bash
# 开发模式
bash deploy-prod.sh

# Docker模式
bash deploy-prod.sh --docker
```

## 📋 系统要求

| 组件 | 最低要求 | 推荐 |
|------|---------|------|
| Python | 3.10+ | 3.12 |
| 内存 | 2GB | 4GB |
| 磁盘 | 1GB | 5GB |
| Ollama | 可选（本地AI） | 推荐安装 |

## 🔧 配置

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `EMA_ENV` | 运行环境 | `production` |
| `EMA_PORT` | API端口 | `6188` |
| `OLLAMA_HOST` | Ollama地址 | `http://host.docker.internal:11434` |
| `NVIDIA_API_KEY` | NVIDIA API密钥（云端大模型） | 空 |
| `JWT_SECRET` | JWT签名密钥（生产必须修改！） | 内置默认值 |
| `EMA_MEMORY_LIMIT` | Docker内存限制 | `2G` |
| `EMA_CPU_LIMIT` | Docker CPU限制 | `2.0` |

### 大模型配置

**本地模型（Ollama）：**
```bash
# 安装 Ollama: https://ollama.com/download
ollama serve
ollama pull qwen3.5:9b
```

**云端模型（NVIDIA）：**
```bash
# 在 .env 中设置
NVIDIA_API_KEY=your_key_here
```

### 支付配置（可选）

微信支付和支付宝 SDK 已内置，需配置商户号后启用：

```bash
# 微信支付
WECHAT_APP_ID=your_app_id
WECHAT_MCH_ID=your_mch_id
WECHAT_API_V3_KEY=your_v3_key
WECHAT_PRIVATE_KEY_PATH=/path/to/private_key.pem

# 支付宝
ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY=your_private_key
ALIPAY_PUBLIC_KEY=alipay_public_key
```

未配置时自动降级为模拟支付（演示用）。

## 📡 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API文档 |
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/wechat-qr` | POST | 微信扫码登录 |
| `/api/v1/auth/wechat-poll` | GET | 轮询扫码状态 |
| `/api/v1/upload/analyze` | POST | 上传图纸分析 |
| `/api/v1/blueprint/review` | POST | 图纸智能审查 |
| `/api/v1/blueprint/documents/generate` | POST | 生成工程文档 |
| `/api/v1/budget/calculate` | POST | 成本预算计算 |
| `/api/v1/knowledge/search` | GET | 知识库搜索 |
| `/api/v1/models/route` | GET | 智能模型路由 |
| `/api/v1/subscription/plans` | GET | 订阅套餐列表 |
| `/api/v1/payment/create` | POST | 创建支付订单 |
| `/api/v1/system/metrics` | GET | 性能监控指标 |

完整 API 文档：启动服务后访问 `/docs`

## 🧪 测试

```bash
# 全量测试
python3 -m pytest tests/ -v

# 指定模块
python3 -m pytest tests/test_budget_engine.py -v
python3 -m pytest tests/test_e2e_pipeline.py -v
```

## 📁 项目结构

```
engineering-management-agent/
├── src/                    # 后端源码
│   ├── api_server.py       # FastAPI 主服务
│   ├── agent/              # Agent 框架
│   ├── blueprint/          # 图纸解析+AI引擎
│   │   ├── core.py         # DWG/DXF/PDF 解析
│   │   ├── ai/             # 推理引擎
│   │   ├── review/         # 审查引擎
│   │   └── documents/      # 文档生成
│   ├── tools/              # 工具模块
│   ├── payment.py          # 支付模块
│   ├── payment_sdk.py      # 支付SDK
│   ├── auth_extended.py    # 认证扩展（微信/JWT）
│   └── model_registry.py   # 模型管理
├── ui/                     # 前端
│   ├── index.html          # 主应用（Vue 3 SPA）
│   ├── login.html          # 登录页
│   ├── admin.html          # 管理后台
│   └── manifest.json       # PWA配置
├── tests/                  # 测试（200个用例）
├── Dockerfile              # Docker构建
├── docker-compose.yml      # Docker编排
├── deploy-prod.sh          # 一键部署脚本
└── requirements.txt        # Python依赖
```

## 🔒 安全

- JWT Token 认证（标准库实现，无额外依赖）
- 密码 PBKDF2-SHA256 哈希
- 登录失败锁定（5次失败锁定15分钟）
- API 用户隔离（租户体系）
- CORS 配置

## 📊 性能

| 指标 | 数值 |
|------|------|
| API 响应时间（平均） | 266ms |
| 图纸解析 | <100ms |
| 审查引擎 | <10ms |
| 预算计算 | <10ms |
| 并发（50并发） | 0失败，QPS 1009 |
| 内存占用 | ~84MB |

## 📄 开源协议

内部项目，未经授权不得外传。

---

**EMA Team** · 工程管理与发展研究中心
