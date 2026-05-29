# EMA API 文档
**工程管理智能体 (Engineering Management Agent)**
版本: 1.0.0 | 端点总数: 105
**Base URL**: `http://127.0.0.1:6188`
---

## 🔐 认证 (Auth)
### `POST /api/v1/auth/forgot-password`
**Forgot Password**
密码找回
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/auth/login`
**Auth Login**
用户登录 - Boss只需账号密码即可进入主界面
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/auth/me`
**Auth Me**
获取当前登录用户信息
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/auth/refresh`
**Auth Refresh**
用 refresh_token 换取新的 access_token
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/auth/register`
**Auth Register**
用户注册 - 密码强度检查 + 用户名验证
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/auth/reset-password`
**Reset Pw**
重置密码
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/auth/verify-admin-password`
**Verify Admin Pw Route**
验证管理后台密码（Boss进入后台时调用）
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/auth/wechat-poll`
**Wechat Poll**
轮询微信扫码状态
**参数:**
- `state` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/auth/wechat-qr`
**Wechat Qr**
微信扫码登录 - 生成真实QR码(base64) + 会话
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/auth/wechat-register`
**Wechat Register**
扫码后注册新账号 + 绑定微信
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---

## 👤 用户管理 (Users)
### `GET /api/v1/admin/users`
**Admin List Users**
用户列表（仅超级管理员）
**响应:**
- `200`: Successful Response
---

## 🏢 租户管理 (Tenants)
### `GET /api/v1/admin/tenants`
**Admin List Tenants**
租户列表（仅超级管理员）
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/admin/tenants`
**Admin Create Tenant**
创建租户（仅超级管理员）
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `PUT /api/v1/admin/tenants/{tenant_id}`
**Admin Update Tenant**
编辑租户（仅超级管理员）
**参数:**
- `tenant_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `DELETE /api/v1/admin/tenants/{tenant_id}`
**Admin Delete Tenant**
删除租户（仅超级管理员）
**参数:**
- `tenant_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---

## 📐 图纸解析 (Blueprint)
### `POST /api/v1/blueprint/ai-analyze`
**Blueprint Ai Analyze**
AI增强型图纸分析 — 上传图纸返回完整AI分析（分类+提取+设计原则+施工要求）
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/blueprint/ai-extract`
**Blueprint Ai Extract**
工程信息智能提取 — 轻量级，只返回工程信息（项目名/面积/层数/结构/材料/参数）
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/blueprint/documents/generate`
**Blueprint Generate Documents**
生成完整工程文档集

请求体: {"analysis": {...}, "doc_types": ["all"] 或 ["design_description", ...]}
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/blueprint/documents/single`
**Blueprint Generate Single Document**
生成单个类型的工程文档

请求体: {"analysis": {...}, "doc_type": "design_description"}
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/blueprint/documents/types`
**Blueprint Document Types**
列出支持的文档类型
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/blueprint/review`
**Blueprint Review**
图纸智能审查（基于国标规范）

请求体: {"file_path": "/path/to/file.dxf", "drawing_type": "建筑平面图"}
或: {"analysis": {...已有的分析结果...}}
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/blueprint/review/analysis`
**Blueprint Review Analysis**
从已有分析结果进行审查
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/blueprint/review/rules`
**Blueprint Review Rules**
列出所有审查规则
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/blueprint/supported-formats`
**Blueprint Supported Formats**
列出支持的图纸格式和AI能力
**响应:**
- `200`: Successful Response
---

## 🤖 Agent工作流 (Agent)
### `POST /api/v1/agent/analyze`
**Agent Analyze**
完整分析工作流：解析→分类→AI分析→工程量

请求体: {"file_path": "/path/to/file.dxf", "use_llm": false}
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/agent/capabilities`
**Agent Capabilities**
列出所有Agent能力
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/agent/chat`
**Agent Chat**
Sub-Agent 对话接口（兼容模式）
直接路由到指定 Agent
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/agent/documents`
**Agent Documents**
上传图纸并生成工程文档
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/agent/pipeline`
**Agent Pipeline**
端到端Agent工作流：解析→分类→AI分析→审查→文档
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/agent/review`
**Agent Review**
上传图纸并执行智能审查
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/agent/task`
**Submit Task**
通用任务提交接口
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/agent/task/{task_id}`
**Get Task Status**
查询任务状态（预留）
**参数:**
- `task_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/conversations`
**Get Conversations**
获取对话历史（从 ChromaDB）
**参数:**
- `session_id` (query, ) - 
- `limit` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/conversations/search`
**Search Conversations**
搜索对话历史
**参数:**
- `q` (query, ) - 
- `session_id` (query, ) - 
- `limit` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/main/chat`
**Main Agent Chat**
Main-Agent 主对话接口
接收自然语言 → 意图分类 → 任务规划 → Sub-Agent调度 → 结果整合

这是 EMA 的核心入口，支持所有 Agent 的自然语言调度。
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/tasks/analyze`
**Create Analyze Task**
创建异步图纸分析任务
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/tasks/{task_id}`
**Get Task Status**
查询异步任务状态
**参数:**
- `task_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---

## 📊 数据分析 (Analytics)
### `GET /api/v1/analytics/summary`
**Analytics Summary**
用户行为汇总统计
**参数:**
- `days` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/analytics/track`
**Track Event**
前端埋点：记录用户行为事件
**响应:**
- `200`: Successful Response
---

## ⚙️ 系统管理 (System)
### `POST /api/v1/system/benchmark`
**Run Benchmark**
执行性能压测（后台异步执行，不阻塞API）
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/system/cache-stats`
**Cache Stats**
获取解析缓存统计
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/system/health-check`
**System Health Check**
系统快速健康检查（本地直调，不经过HTTP）
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/system/performance`
**System Performance**
系统性能监控面板数据
**响应:**
- `200`: Successful Response
---

## 💰 支付订阅 (Payment)
### `POST /api/v1/payment/alipay-callback`
**Alipay Callback**
支付宝支付回调（生产环境）
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/payment/create`
**Create Payment**
创建支付订单（微信/支付宝）
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/payment/mock-pay/{order_id}`
**Mock Pay**
模拟支付成功（Phase 7 Stub，生产环境改为微信/支付宝回调）
**参数:**
- `order_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/payment/orders`
**List Payment Orders**
列出用户的支付订单
**参数:**
- `status` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/payment/orders/{order_id}`
**Get Payment Order**
查询单个订单
**参数:**
- `order_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/payment/wechat-callback`
**Wechat Callback**
微信支付回调（生产环境）
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/subscription/plans`
**Get Plans**
列出所有订阅套餐
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/subscription/status`
**Subscription Status**
获取当前用户/租户的订阅状态
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/subscription/subscribe`
**Subscribe**
订阅/升级套餐
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---

## 📋 项目管理 (Projects)
### `GET /api/v1/projects/checks`
**Run Project Checks**
运行项目检查（里程碑提醒等）
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/projects/milestones/{milestone_id}/complete`
**Complete Milestone**
完成里程碑
**参数:**
- `milestone_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/projects/{project_id}`
**Get Project**
获取项目详情
**参数:**
- `project_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `DELETE /api/v1/projects/{project_id}`
**Delete Project**
删除项目
**参数:**
- `project_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `PUT /api/v1/projects/{project_id}`
**Update Project**
更新项目
**参数:**
- `project_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/projects/{project_id}/milestones`
**List Milestones**
项目里程碑列表
**参数:**
- `project_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/projects/{project_id}/milestones`
**Add Milestone**
添加里程碑
**参数:**
- `project_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---

## 🔧 管理后台 (Admin)
### `GET /api/v1/admin/advice`
**Admin Advice**
决策建议 + 市场洞察
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/admin/alerts`
**Admin Alerts**
系统预警
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/admin/feedback`
**List Feedback**
查看反馈列表（管理端）
**参数:**
- `date` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/admin/models`
**List Models Api**
列出所有模型配置（仅超级管理员）
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/admin/models`
**Add Model Api**
添加模型配置（仅超级管理员）
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `PUT /api/v1/admin/models/{model_id}`
**Update Model Api**
更新模型配置（仅超级管理员）
**参数:**
- `model_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `DELETE /api/v1/admin/models/{model_id}`
**Delete Model Api**
删除模型配置（仅超级管理员）
**参数:**
- `model_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/admin/report`
**Admin Report**
平台周报生成
**响应:**
- `200`: Successful Response
---

## 🤖 LLM管理 (LLM)
### `GET /api/v1/llm/health`
**Llm Health**
获取LLM健康状态（超时监督数据）
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/llm/health/check`
**Llm Health Check**
立即执行云模型健康检测
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/llm/health/reset`
**Llm Health Reset**
重置每日统计
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/llm/models`
**List Llm Models**
列出所有可用的 LLM 模型（本地 Ollama + 云端）
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/llm/test`
**Test Llm Model**
测试指定模型是否可用 (接受 JSON {"model": "xxx"} 或 Form model=xxx)
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/models/nvidia-stats`
**Nvidia Rpm Stats**
获取NVIDIA API速率限制统计
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/models/nvidia-stats/reset`
**Nvidia Rpm Reset**
重置NVIDIA API速率峰值（管理员）
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/models/route`
**Route Model Api**
智能路由：返回当前用户应使用的模型（含NVIDIA RPM检查）
**参数:**
- `task_type` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---

## 📝 其他 (Other)
### `GET /`
**Root**
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/agents`
**List Agents**
列出所有Agent及其能力
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/agents/{agent_id}`
**Get Agent Info**
获取单个Agent信息
**参数:**
- `agent_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/dashboard`
**Dashboard**
综合数据看板
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/dashboard/agents`
**Dashboard Agents**
Agent使用热度
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/dashboard/projects`
**Dashboard Projects**
项目统计
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/dashboard/revenue`
**Dashboard Revenue**
收益报表
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/dashboard/usage`
**Dashboard Usage**
使用趋势
**参数:**
- `days` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/feedback`
**Submit Feedback**
收集用户反馈
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/logs/errors`
**Get Error Summary Stats**
错误汇总（默认7天）
**参数:**
- `hours` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/logs/stats`
**Get Log Stats**
日志统计（默认24小时，支持1-168小时）
**参数:**
- `hours` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/logs/stats/full`
**Get Full Log Stats**
全量统计（24h + 7天 + 用户活动 + 错误汇总）
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/logs/user-activity`
**Get User Activity Stats**
用户活动统计（默认7天）
**参数:**
- `hours` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/notifications`
**List Notifications**
获取通知列表
**参数:**
- `unread_only` (query, ) - 
- `limit` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/notifications/read-all`
**Read All Notifications**
标记全部通知已读
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/notifications/{notification_id}/read`
**Read Notification**
标记单条通知已读
**参数:**
- `notification_id` (path, ) -  *(必填)*
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/performance/cache-clear`
**Cache Clear**
清理所有缓存
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/performance/cache-stats`
**Cache Stats**
缓存统计
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/performance/cache-warmup`
**Cache Warmup**
缓存预热：扫描样本目录并预解析
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/performance/health`
**Perf Health**
性能健康检查（无需认证）
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/projects`
**List Projects**
项目列表
**参数:**
- `tenant_id` (query, ) - 
- `status` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `POST /api/v1/projects`
**Create Project**
创建项目
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/security/audit`
**Security Audit**
查看安全审计日志
**参数:**
- `severity` (query, ) - 
- `event_type` (query, ) - 
- `limit` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/security/baseline`
**Security Baseline**
执行安全基线检查
**响应:**
- `200`: Successful Response
---
### `GET /api/v1/security/rate-limit`
**Check Rate**
检查当前IP的速率限制状态
**参数:**
- `client_ip` (query, ) - 
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /api/v1/specs`
**List Specs**
规范列表
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/specs/check`
**Check Specs Update**
手动触发规范更新检查
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/specs/initialize`
**Initialize Specs**
初始化规范索引
**响应:**
- `200`: Successful Response
---
### `POST /api/v1/upload/analyze`
**Upload And Analyze**
上传图纸并分析（含缓存加速）
支持格式：DWG, DXF, PDF
**响应:**
- `200`: Successful Response
- `422`: Validation Error
---
### `GET /health`
**Health**
**响应:**
- `200`: Successful Response
---
