# EMA API 接口文档 v3.0

> 基地址：`http://127.0.0.1:6188` | Swagger UI: `/docs` | 版本：v3.5.0
> 最后更新: 2026-06-11

> **注意**: 本项目使用 FastAPI，完整交互式 API 文档请访问 `http://127.0.0.1:6188/docs` (Swagger UI) 或 `http://127.0.0.1:6188/redoc` (ReDoc)。
> 本文档仅覆盖核心端点和 v3.5.0 新增功能。

---

## 一、认证方式

| 场景 | 方式 | Header |
|------|------|--------|
| 已登录 | Bearer Token | `Authorization: Bearer <token>` |
| 登录中 | 表单 | `Content-Type: application/x-www-form-urlencoded` |
| 公开 | 无需认证 | — |

## 二、通用错误码

| HTTP Status | 错误码 | 说明 | 处理建议 |
|------------|--------|------|---------|
| 200 | — | 成功 | — |
| 400 | `invalid_request` | 请求参数错误 | 检查请求格式 |
| 400 | `weak_password` | 密码不符合要求 | 至少8位，含大小写字母和数字 |
| 400 | `duplicate_user` | 用户已存在 | 使用登录或换个用户名 |
| 400 | `invalid_plan` | 无效套餐ID | 使用 free/pro/enterprise/private |
| 401 | `unauthorized` | 未认证 | 请先登录获取 Token |
| 401 | `invalid_token` | Token 无效或过期 | 使用 refresh 刷新或重新登录 |
| 401 | `wrong_password` | 密码错误 | 检查密码或使用找回功能 |
| 403 | `forbidden` | 权限不足 | 当前套餐不支持此功能 |
| 403 | `admin_password_required` | 需要管理后台密码 | 输入管理员密码 |
| 404 | `not_found` | 资源不存在 | 检查 ID 是否正确 |
| 404 | `agent_not_found` | Agent 不存在 | 使用 /api/v1/agents 查看可用 Agent |
| 413 | `file_too_large` | 文件过大 | 检查文件大小限制 |
| 415 | `unsupported_file` | 不支持的文件类型 | 使用 DWG/DXF/PDF/JPG/PNG |
| 422 | `validation_error` | 请求体验证失败 | 检查字段类型和必填项 |
| 429 | `rate_limited` | 请求频率超限 | 稍后重试（拉黑需等待1小时） |
| 500 | `internal_error` | 服务器内部错误 | 联系管理员 |
| 503 | `service_unavailable` | 服务不可用 | 稍后重试 |

---

## 三、端点分组

### 3.1 系统与健康

**`GET /health`**

```bash
curl http://127.0.0.1:5188/health
```

**响应示例：**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-05-20T08:00:00.000Z"
}
```

**`GET /api/v1/system/health-check`** — 完整健康检查（含 ChromaDB/Ollama 状态）

**`GET /api/v1/system/cache-stats`** — 性能缓存统计

**`POST /api/v1/system/benchmark`** — 性能压测（需 Boss 权限）

---

### 3.2 认证 (Auth)

**`POST /api/v1/auth/login`**

```bash
curl -X POST http://127.0.0.1:5188/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=boss&password=xxxxxx"
```

**响应示例：**
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "username": "boss",
    "role": "super_admin",
    "plan_id": "private"
  }
}
```

**`POST /api/v1/auth/register`**

```bash
curl -X POST http://127.0.0.1:5188/api/v1/auth/register \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=zhangsan&password=Abcd1234&email=zhang@test.com&phone=13800138000"
```

**响应示例：**
```json
{
  "success": true,
  "message": "注册成功",
  "user_id": "user_xxx"
}
```

**`POST /api/v1/auth/refresh`** — 刷新 Token（过期前续期）
**`GET /api/v1/auth/me`** — 获取当前用户信息
**`POST /api/v1/auth/forgot-password`** — 忘记密码（通过邮箱）
**`POST /api/v1/auth/reset-password`** — 重置密码（通过安全问题）
**`POST /api/v1/auth/verify-admin-password`** — 验证管理后台密码
**`GET /api/v1/auth/wechat-qr`** — 生成微信扫码登录二维码
**`GET /api/v1/auth/wechat-poll`** — 微信扫码轮询验证
**`POST /api/v1/auth/wechat-register`** — 微信扫码注册

---

### 3.3 Agent 管理

**`GET /api/v1/agents`** — 列出所有 Agent

**响应示例：**
```json
{
  "agents": [
    {
      "agent_id": "tech_rd",
      "name": "技术研发中心",
      "icon": "🔧",
      "status": "active",
      "tasks": ["parse", "classify", "analyze", "extract", "optimize", "chat"]
    }
  ]
}
```

**`GET /api/v1/agents/{agent_id}`** — Agent 详情
**`POST /api/v1/agent/task`** — 提交 Agent 任务
**`GET /api/v1/agent/task/{task_id}`** — 查询任务状态
**`POST /api/v1/agent/chat`** — Agent 对话路由

---

### 3.4 主对话

**`POST /api/v1/main/chat`** — EMA 主对话入口

```bash
curl -X POST http://127.0.0.1:5188/api/v1/main/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我分析这个图纸",
    "file_path": "/uploads/test.dwg",
    "model": "ollama:minimax-m2.7:cloud"
  }'
```

**请求参数：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息内容 |
| file_path | string | 否 | 图纸文件路径（已上传后） |
| task_type | string | 否 | 强制指定任务类型（覆盖意图分类） |
| model | string | 否 | 指定模型（不传则用默认） |

**响应示例：**
```json
{
  "intent": "tech_rd:full_analysis",
  "agent": "tech_rd",
  "task_type": "full_analysis",
  "response_text": "图纸分析结果...",
  "results": [...],
  "model_used": "ollama:minimax-m2.7:cloud"
}
```

---

### 3.5 图纸上传与解析

**`POST /api/v1/upload/analyze`**

```bash
curl -X POST http://127.0.0.1:5188/api/v1/upload/analyze \
  -H "Authorization: Bearer <token>" \
  -F "file=@建筑平面图.dxf"
```

**响应示例：**
```json
{
  "success": true,
  "file_path": "/uploads/user_xxx/建筑平面图.dxf",
  "drawing_type": "建筑",
  "analysis": {
    "layers": [...],
    "entities": [...],
    "type_confidence": 0.95
  }
}
```

---

### 3.6 订阅与支付

**`GET /api/v1/subscription/plans`** — 套餐列表
**`GET /api/v1/subscription/status`** — 当前订阅状态
**`POST /api/v1/subscription/subscribe`** — 订阅/升级套餐

```bash
curl -X POST http://127.0.0.1:5188/api/v1/subscription/subscribe \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": "pro", "duration_months": 12}'
```

**`POST /api/v1/payment/create`** — 创建支付订单

```bash
curl -X POST http://127.0.0.1:5188/api/v1/payment/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": "pro", "amount": 299.0, "payment_method": "wechat"}'
```

**响应示例：**
```json
{
  "order_id": "EMA20260520083000A1B2C3",
  "tenant_id": "user_xxx",
  "amount": 299.0,
  "status": "pending",
  "pay_url": "http://127.0.0.1:5188/api/v1/payment/mock-pay/EMA2026...",
  "expires_at": "2026-05-20T10:30:00.000"
}
```

**`GET /api/v1/payment/orders`** — 订单列表
**`GET /api/v1/payment/orders/{order_id}`** — 订单详情
**`POST /api/v1/payment/mock-pay/{order_id}`** — 模拟支付成功
**`POST /api/v1/payment/wechat-callback`** — 微信支付回调
**`POST /api/v1/payment/alipay-callback`** — 支付宝回调

---

### 3.7 通知

**`GET /api/v1/notifications`** — 通知列表

```bash
curl http://127.0.0.1:5188/api/v1/notifications?unread_only=true&limit=10 \
  -H "Authorization: Bearer <token>"
```

**`POST /api/v1/notifications/{id}/read`** — 标记单条已读
**`POST /api/v1/notifications/read-all`** — 全部已读

---

### 3.8 对话历史

**`GET /api/v1/conversations`** — 对话历史列表

```bash
curl "http://127.0.0.1:5188/api/v1/conversations?limit=20" \
  -H "Authorization: Bearer <token>"
```

**`GET /api/v1/conversations/search?q=图纸`** — 搜索对话

---

### 3.9 项目管理

**`GET /api/v1/projects`** — 项目列表
**`POST /api/v1/projects`** — 创建项目

```bash
curl -X POST http://127.0.0.1:5188/api/v1/projects \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "C448项目", "description": "某住宅小区"}'
```

**`GET /api/v1/projects/{id}`** — 项目详情
**`DELETE /api/v1/projects/{id}`** — 删除项目

---

### 3.10 安全

**`GET /api/v1/security/audit`** — 安全审计日志
**`GET /api/v1/security/baseline`** — 安全基线检查
**`GET /api/v1/security/rate-limit`** — 速率限制状态

---

### 3.11 数据看板

**`GET /api/v1/dashboard`** — 概览数据
**`GET /api/v1/dashboard/projects`** — 项目统计
**`GET /api/v1/dashboard/usage`** — 使用趋势
**`GET /api/v1/dashboard/revenue`** — 收益报表
**`GET /api/v1/dashboard/agents`** — Agent 热度

---

### 3.12 LLM 模型

**`GET /api/v1/llm/models`** — 可用模型列表

```bash
curl http://127.0.0.1:5188/api/v1/llm/models
```

**`POST /api/v1/llm/test`** — 测试模型可用性

```bash
curl -X POST http://127.0.0.1:5188/api/v1/llm/test \
  -H "Content-Type: application/json" \
  -d '{"model": "ollama:minimax-m2.7:cloud", "prompt": "Hello"}'
```

---

## 四、WebSocket（规划中）

| 端点 | 说明 |
|------|------|
| `ws://127.0.0.1:5188/ws/agent/{agent_id}` | Agent 实时对话流 |
| `ws://127.0.0.1:5188/ws/notifications` | 通知实时推送 |

---

## 五、速率限制

| 限制项 | 阈值 | 处罚 |
|--------|------|------|
| 普通请求 | 20次/秒 | — |
| 窗口内超标 | 50次/60秒 | IP 拉黑 1小时 |
| 单文件上传 | 500MB | 413 拒绝 |
| 单次对话 | 60秒 | 超时断开 |

---

## 六、版本演进

| 版本 | 日期 | 端点数 | 关键变更 |
|------|------|--------|---------|
| v0.16.3 | 2026-05-11 | ~12 | blueprint-ai 单体工具 |
| v1.0.0 | 2026-05-19 | 26 | EMA 6Agent 框架 |
| v1.3.0 | 2026-05-19 | 45 | 订阅/支付/安全/看板 |
| v2.0.0 | 2026-05-20 | 53 | 登录系统/Boss仪表仓/登出闭环 |
