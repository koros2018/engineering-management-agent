# EMA API 接口文档 v1.0

> **版本：** v1.0.0 | **更新日期：** 2026-05-19
> **Base URL：** `http://127.0.0.1:5188`

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    🌐 前端 UI (5189)                       │
│                   Vue 3 + Vanilla JS                     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────┐
│               🧠 Main-Agent (5188)                       │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │IntentClassifier│ │ TaskPlanner  │ │Orchestrator    │  │
│  └──────────────┘ └──────────────┘ └────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              ResultCompiler                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │TechRdAgent│ │Safety    │ │Market    │ │Delivery  │  │
│  │(技术研发) │ │Compliance│ │Sales     │ │(工程交付) │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐                             │
│  │CostBenefit│ │Customer  │                             │
│  │(成本效益) │ │Service   │                             │
│  └──────────┘ └──────────┘                             │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Memory Layer                                      │  │
│  │ ┌────────────────┐  ┌─────────────────────────┐  │  │
│  │ │ SessionContext  │  │ ChromaDBStore (向量DB)  │  │  │
│  │ │ (短期记忆)     │  │ (长期记忆)              │  │  │
│  │ └────────────────┘  └─────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              🔧 blueprint-ai 核心引擎                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ core.py  │ │review.py │ │documents │ │budget.py │  │
│  │(图纸解析)│ │(国标审查)│ │(文档生成)│ │(预算)    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│  │ sop.py   │ │ mop.py   │ │ eop.py   │               │
│  │ lcc.py   │ │ llm_svc  │ │ auth.py  │               │
│  └──────────┘ └──────────┘ └──────────┘               │
└─────────────────────────────────────────────────────────┘
```

---

## 全部 API 端点（26个）

### 🏥 系统

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/` | 服务信息 |
| `GET` | `/health` | 健康检查 |

### 👤 认证（JWT + RBAC）

| 方法 | 端点 | 描述 | 鉴权 |
|------|------|------|------|
| `POST` | `/api/v1/auth/register` | 用户注册 | 无 |
| `POST` | `/api/v1/auth/login` | 用户登录 → access_token | 无 |
| `GET` | `/api/v1/auth/me` | 当前用户信息 | JWT |
| `POST` | `/api/v1/auth/refresh` | 刷新token | Refresh Token |

### 📁 项目管理

| 方法 | 端点 | 描述 | 鉴权 |
|------|------|------|------|
| `GET` | `/api/v1/projects` | 列出项目 | optional |
| `POST` | `/api/v1/projects` | 创建项目 | optional |
| `GET` | `/api/v1/projects/{project_id}` | 项目详情 | optional |
| `DELETE` | `/api/v1/projects/{project_id}` | 删除项目 | optional |

### 🤖 Agent 管理

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/api/v1/agents` | 列出所有 Agent（含状态/能力） |
| `GET` | `/api/v1/agents/{agent_id}` | 单个 Agent 详情 |

### 🧠 Main-Agent 对话（核心入口）

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/v1/main/chat` | **主对话入口** — 自然语言 → 意图分类 → Sub-Agent调度 |

**请求体：**
```json
{
  "message": "帮我分析这张图纸",
  "user_id": "web_user",
  "project_id": "optional-project-id",
  "file_path": "optional-file-path",
  "model": "ollama:qwen3.5:9b",
  "model_chain": ["ollama:qwen3.5:9b", "cloud:gpt-4o-mini"]
}
```

**响应体：**
```json
{
  "success": true,
  "task_id": "uuid",
  "intent": "图纸分析",
  "plan": {"steps": [...]},
  "confidence": 0.85,
  "output": {...},
  "response_text": "分析完成...",
  "execution_time": 2.3
}
```

### 🔗 Sub-Agent 路由（兼容）

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/v1/agent/chat` | 直接路由到指定Sub-Agent |
| `POST` | `/api/v1/agent/task` | 提交异步任务 |
| `GET` | `/api/v1/agent/task/{task_id}` | 查询任务状态 |

### 📤 图纸处理

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/v1/upload/analyze` | 上传图纸（DWG/DXF/PDF）→ 完整分析 |
| `POST` | `/api/v1/upload/review` | 上传图纸 → 国标审图 |
| `POST` | `/api/v1/upload/budget` | 上传图纸 → 工程预算 |

**上传请求：** `multipart/form-data`
- `file`: 图纸文件（DWG/DXF/PDF）
- `user_id`: (可选) 用户ID

### 📝 文档生成

| 方法 | 端点 | 描述 |
|------|------|------|
| `POST` | `/api/v1/generate/sop` | 生成SOP（标准操作程序） |
| `POST` | `/api/v1/generate/mop` | 生成MOP（维护操作程序） |
| `POST` | `/api/v1/generate/eop` | 生成EOP（紧急操作程序） |
| `POST` | `/api/v1/generate/lcc` | 生成LCC（生命周期成本） |

### 💬 对话历史

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/api/v1/conversations` | 获取对话历史（按session分组） |
| `GET` | `/api/v1/conversations/search` | 向量搜索对话 |

**参数：**
- `?session_id=xxx` — 限定会话
- `?q=关键词` — 搜索内容
- `?limit=20` — 返回数量

### 🤖 LLM 管理

| 方法 | 端点 | 描述 |
|------|------|------|
| `GET` | `/api/v1/llm/models` | 列出可用模型 |
| `POST` | `/api/v1/llm/test` | 测试模型可用性 |

---

## 6大 Sub-Agent 能力清单

| Agent | ID | 能力 |
|-------|-----|------|
| 🔧 技术研发中心 | `tech_rd` | 图纸解析/类型识别/AI分析/工程量提取/设计优化 |
| 🔒 安全与合规中心 | `safety_compliance` | 15条国标审图/消防合规/结构安全/法规审核 |
| 📡 市场与销售中心 | `market_sales` | 市场分析/商务方案/投标文件/报价策略 |
| 🏗️ 工程交付中心 | `engineering_delivery` | SOP/MOP/EOP/LCC/竣工文档 |
| 💰 成本效益中心 | `cost_benefit` | 工程量计算/预算生成/成本分析/投资回报 |
| 🤝 客户服务中心 | `customer_service` | FAQ/培训材料/反馈分析/工单管理 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.10+) |
| 前端 | Vue 3 CDN + Vanilla JS |
| LLM | Ollama（本地）+ 云端 API fallback |
| 向量存储 | ChromaDB（长期记忆） |
| 用户系统 | JWT + SQLite (passlib + bcrypt) |
| 图纸解析 | ezdxf / PyMuPDF / libredwg WASM |
| 代码质量 | pytest + black + ruff |

---

## 服务端口

| 服务 | 端口 | 地址 |
|------|------|------|
| EMA API | 5188 | `http://127.0.0.1:5188` |
| EMA UI | 5189 | `http://127.0.0.1:5189/ui/` |
| Swagger Docs | 5188 | `http://127.0.0.1:5188/docs` |
