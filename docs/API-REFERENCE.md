# EMA API 参考文档

**版本**: 1.0.0  
**生成时间**: 2026-05-29  
**端点总数**: 97  

---


## 


### `GET` /

**Root**

**响应:**
- `200`: Successful Response

---

## api


### `GET` /api/v1/admin/advice

**Admin Advice**

决策建议 + 市场洞察

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/admin/alerts

**Admin Alerts**

系统预警

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/admin/feedback

**List Feedback**

查看反馈列表（管理端）

**参数:**
- `date` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/admin/models

**List Models Api**

列出所有模型配置（仅超级管理员）

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/admin/models

**Add Model Api**

添加模型配置（仅超级管理员）

**请求格式**: application/json

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT` /api/v1/admin/models/{model_id}

**Update Model Api**

更新模型配置（仅超级管理员）

**参数:**
- `model_id` (path) (必填): 

**请求格式**: application/json

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `DELETE` /api/v1/admin/models/{model_id}

**Delete Model Api**

删除模型配置（仅超级管理员）

**参数:**
- `model_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/admin/report

**Admin Report**

平台周报生成

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/admin/tenants

**Admin List Tenants**

租户列表（仅超级管理员）

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/admin/tenants

**Admin Create Tenant**

创建租户（仅超级管理员）

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT` /api/v1/admin/tenants/{tenant_id}

**Admin Update Tenant**

编辑租户（仅超级管理员）

**参数:**
- `tenant_id` (path) (必填): 

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `DELETE` /api/v1/admin/tenants/{tenant_id}

**Admin Delete Tenant**

删除租户（仅超级管理员）

**参数:**
- `tenant_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/admin/users

**Admin List Users**

用户列表（仅超级管理员）

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/agent/analyze

**Agent Analyze**

完整分析工作流：解析→分类→AI分析→工程量

请求体: {"file_path": "/path/to/file.dxf", "use_llm": false}

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/agent/capabilities

**Agent Capabilities**

列出所有Agent能力

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/agent/chat

**Agent Chat**

Sub-Agent 对话接口（兼容模式）
直接路由到指定 Agent

**请求格式**: application/json

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/agent/documents

**文档生成**

上传图纸文件，自动生成工程文档。

**支持文档类型**:
- 设计说明 — 工程概况、设计依据、技术指标
- 工程量清单 — 按专业分类的估算清单
- 施工技术交底 — 施工工艺、质量标准、安全措施
- 技术核定单 — 设计变更确认
- 招投标文件 — 招标文件框架

**流程**: 文件上传 → 图纸解析 → AI信息提取 → 文档生成

**请求格式**: multipart/form-data

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/agent/pipeline

**端到端流水线**

一键执行完整的Agent工作流：解析 → 分类 → AI分析 → 审查 → 文档生成。

**5步流程**:
1. 图纸解析 (DWG/DXF/PDF)
2. 图层分类 (规则+AI)
3. 工程信息提取 (smart_extract)
4. 智能审查 (15条国标规则)
5. 文档生成 (设计说明+工程量清单+技术交底)

**返回**: 完整的分析结果、审查报告、生成文档

**请求格式**: multipart/form-data

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/agent/review

**智能审查**

上传图纸文件(DWG/DXF/PDF)，执行AI智能审查。

**流程**: 文件上传 → 图纸解析 → 图层分类 → 规则引擎审查 → 输出审查报告

**审查规则**: 消防疏散、防火分区、楼梯规范、标题栏、标注规范、结构安全等15条国标规则

**返回**: 审查问题列表(严重/警告/建议)、质量评分、规范引用

**请求格式**: multipart/form-data

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/agent/task

**Submit Task**

通用任务提交接口

**请求格式**: application/json

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/agent/task/{task_id}

**Get Task Status**

查询任务状态（预留）

**参数:**
- `task_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/agents

**List Agents**

列出所有Agent及其能力

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/agents/{agent_id}

**Get Agent Info**

获取单个Agent信息

**参数:**
- `agent_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/analytics/summary

**Analytics Summary**

用户行为汇总统计

**参数:**
- `days` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/analytics/track

**行为埋点**

记录前端用户行为事件，用于产品分析和用户画像。

**参数**:
- event: 事件名称 (page_view/click/upload/review等)
- metadata: 附加数据 (页面/按钮/文件信息等)

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/auth/forgot-password

**Forgot Password**

密码找回

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/auth/login

**Auth Login**

用户登录 - Boss只需账号密码即可进入主界面

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/auth/me

**Auth Me**

获取当前登录用户信息

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/auth/refresh

**Auth Refresh**

用 refresh_token 换取新的 access_token

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/auth/register

**Auth Register**

用户注册 - 密码强度检查 + 用户名验证

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/auth/reset-password

**Reset Pw**

重置密码

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/auth/verify-admin-password

**Verify Admin Pw Route**

验证管理后台密码（Boss进入后台时调用）

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/auth/wechat-poll

**Wechat Poll**

轮询微信扫码状态

**参数:**
- `state` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/auth/wechat-qr

**Wechat Qr**

微信扫码登录 - 生成真实QR码(base64) + 会话

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/auth/wechat-register

**Wechat Register**

扫码后注册新账号 + 绑定微信

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/blueprint/ai-analyze

**Blueprint Ai Analyze**

AI增强型图纸分析 — 上传图纸返回完整AI分析（分类+提取+设计原则+施工要求）

**请求格式**: multipart/form-data

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/blueprint/ai-extract

**Blueprint Ai Extract**

工程信息智能提取 — 轻量级，只返回工程信息（项目名/面积/层数/结构/材料/参数）

**请求格式**: multipart/form-data

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/blueprint/documents/generate

**Blueprint Generate Documents**

生成完整工程文档集

请求体: {"analysis": {...}, "doc_types": ["all"] 或 ["design_description", ...]}

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/blueprint/documents/single

**Blueprint Generate Single Document**

生成单个类型的工程文档

请求体: {"analysis": {...}, "doc_type": "design_description"}

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/blueprint/documents/types

**Blueprint Document Types**

列出支持的文档类型

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/blueprint/review

**Blueprint Review**

图纸智能审查（基于国标规范）

请求体: {"file_path": "/path/to/file.dxf", "drawing_type": "建筑平面图"}
或: {"analysis": {...已有的分析结果...}}

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/blueprint/review/analysis

**Blueprint Review Analysis**

从已有分析结果进行审查

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/blueprint/review/rules

**Blueprint Review Rules**

列出所有审查规则

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/blueprint/supported-formats

**Blueprint Supported Formats**

列出支持的图纸格式和AI能力

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/conversations

**Get Conversations**

获取对话历史（从 ChromaDB）

**参数:**
- `session_id` (query): 
- `limit` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/conversations/search

**Search Conversations**

搜索对话历史

**参数:**
- `q` (query): 
- `session_id` (query): 
- `limit` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/dashboard

**Dashboard**

综合数据看板

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/dashboard/agents

**Dashboard Agents**

Agent使用热度

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/dashboard/projects

**Dashboard Projects**

项目统计

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/dashboard/revenue

**Dashboard Revenue**

收益报表

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/dashboard/usage

**Dashboard Usage**

使用趋势

**参数:**
- `days` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/feedback

**提交用户反馈**

收集用户反馈意见。

**参数**:
- type: 反馈类型 (bug/feature/other)
- score: 评分 (1-5星)
- content: 反馈内容

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/llm/health

**LLM健康检查**

获取大模型服务健康状态和超时监督数据。

**返回数据**:
- 各模型状态 (可用/禁用/超时次数)
- 超时监督统计 (连续失败/自动降级/恢复记录)
- 响应时间分布
- 错误率统计

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/llm/health/check

**Llm Health Check**

立即执行云模型健康检测

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/llm/health/reset

**Llm Health Reset**

重置每日统计

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/llm/models

**List Llm Models**

列出所有可用的 LLM 模型（本地 Ollama + 云端）

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/llm/test

**Test Llm Model**

测试指定模型是否可用 (接受 JSON {"model": "xxx"} 或 Form model=xxx)

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/logs/errors

**Get Error Summary Stats**

错误汇总（默认7天）

**参数:**
- `hours` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/logs/stats

**Get Log Stats**

日志统计（默认24小时，支持1-168小时）

**参数:**
- `hours` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/logs/stats/full

**Get Full Log Stats**

全量统计（24h + 7天 + 用户活动 + 错误汇总）

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/logs/user-activity

**Get User Activity Stats**

用户活动统计（默认7天）

**参数:**
- `hours` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/main/chat

**Main Agent Chat**

Main-Agent 主对话接口
接收自然语言 → 意图分类 → 任务规划 → Sub-Agent调度 → 结果整合

这是 EMA 的核心入口，支持所有 Agent 的自然语言调度。

**请求格式**: application/json

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/models/nvidia-stats

**Nvidia Rpm Stats**

获取NVIDIA API速率限制统计

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/models/nvidia-stats/reset

**Nvidia Rpm Reset**

重置NVIDIA API速率峰值（管理员）

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/models/route

**Route Model Api**

智能路由：返回当前用户应使用的模型（含NVIDIA RPM检查）

**参数:**
- `task_type` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/notifications

**List Notifications**

获取通知列表

**参数:**
- `unread_only` (query): 
- `limit` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/notifications/read-all

**Read All Notifications**

标记全部通知已读

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/notifications/{notification_id}/read

**Read Notification**

标记单条通知已读

**参数:**
- `notification_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/payment/alipay-callback

**Alipay Callback**

支付宝支付回调（生产环境）

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/payment/create

**Create Payment**

创建支付订单（微信/支付宝）

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/payment/mock-pay/{order_id}

**Mock Pay**

模拟支付成功（Phase 7 Stub，生产环境改为微信/支付宝回调）

**参数:**
- `order_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/payment/orders

**List Payment Orders**

列出用户的支付订单

**参数:**
- `status` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/payment/orders/{order_id}

**Get Payment Order**

查询单个订单

**参数:**
- `order_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/payment/wechat-callback

**Wechat Callback**

微信支付回调（生产环境）

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/performance/cache-clear

**Cache Clear**

清理所有缓存

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/performance/cache-stats

**Cache Stats**

缓存统计

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/performance/cache-warmup

**Cache Warmup**

缓存预热：扫描样本目录并预解析

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/performance/health

**Perf Health**

性能健康检查（无需认证）

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/projects

**List Projects**

项目列表

**参数:**
- `tenant_id` (query): 
- `status` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/projects

**Create Project**

创建项目

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/projects/checks

**Run Project Checks**

运行项目检查（里程碑提醒等）

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/projects/milestones/{milestone_id}/complete

**Complete Milestone**

完成里程碑

**参数:**
- `milestone_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/projects/{project_id}

**Get Project**

获取项目详情

**参数:**
- `project_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `DELETE` /api/v1/projects/{project_id}

**Delete Project**

删除项目

**参数:**
- `project_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `PUT` /api/v1/projects/{project_id}

**Update Project**

更新项目

**参数:**
- `project_id` (path) (必填): 

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/projects/{project_id}/milestones

**List Milestones**

项目里程碑列表

**参数:**
- `project_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/projects/{project_id}/milestones

**Add Milestone**

添加里程碑

**参数:**
- `project_id` (path) (必填): 

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/security/audit

**Security Audit**

查看安全审计日志

**参数:**
- `severity` (query): 
- `event_type` (query): 
- `limit` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/security/baseline

**Security Baseline**

执行安全基线检查

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/security/rate-limit

**Check Rate**

检查当前IP的速率限制状态

**参数:**
- `client_ip` (query): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/specs

**List Specs**

规范列表

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/specs/check

**Check Specs Update**

手动触发规范更新检查

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/specs/initialize

**Initialize Specs**

初始化规范索引

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/subscription/plans

**Get Plans**

列出所有订阅套餐

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/subscription/status

**Subscription Status**

获取当前用户/租户的订阅状态

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/subscription/subscribe

**Subscribe**

订阅/升级套餐

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/system/benchmark

**Run Benchmark**

执行性能压测（后台异步执行，不阻塞API）

**请求格式**: application/x-www-form-urlencoded

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/system/cache-stats

**Cache Stats**

获取解析缓存统计

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/system/health-check

**System Health Check**

系统快速健康检查（本地直调，不经过HTTP）

**响应:**
- `200`: Successful Response

---

### `GET` /api/v1/system/performance

**系统性能监控**

获取系统各模块的性能指标。

**返回数据**:
- 系统信息 (CPU/内存/磁盘/OS)
- 模块加载状态 (Blueprint/Review/Documents/LLM)
- LLM健康状态 (超时统计/错误率/降级记录)
- 缓存统计 (命中率/大小/TTL)
- 数据统计 (用户数/项目数/文件数)

**响应:**
- `200`: Successful Response

---

### `POST` /api/v1/tasks/analyze

**Create Analyze Task**

创建异步图纸分析任务

**请求格式**: multipart/form-data

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `GET` /api/v1/tasks/{task_id}

**Get Task Status**

查询异步任务状态

**参数:**
- `task_id` (path) (必填): 

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

### `POST` /api/v1/upload/analyze

**Upload And Analyze**

上传图纸并分析（含缓存加速）
支持格式：DWG, DXF, PDF

**请求格式**: multipart/form-data

**响应:**
- `200`: Successful Response
- `422`: Validation Error

---

## health


### `GET` /health

**Health**

**响应:**
- `200`: Successful Response

---