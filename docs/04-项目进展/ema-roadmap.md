# EMA 工程管理智能体 — 项目规划与进度

> **项目路径：** `/mnt/d/OpenClawDataworkspace/Projects/EMA`
> **远程仓库：** `https://github.com/koros2018/engineering-management-agent.git`
> **Slogan：** 工程管理，从"人管"到"智能体协管"

---

## 📊 当前状态

| 维度 | 状态 |
|------|------|
| **版本** | v3.5.0（Phase 21）|
| **代码量** | 25,546 行 Python + 4,989 行前端 |
| **API 端点** | 125 个 |
| **测试** | 200 个用例 |
| **Agent** | 6 Sub-Agent + Manager |
| **大模型** | LongCat 2.0 + Kimi K2.6 + Qwen 3.5 + DeepSeek R1 |
| **功能完成度** | ~96% |
| **API** | http://127.0.0.1:6188 |
| **UI** | http://127.0.0.1:6189 |

---

## 已完成 Phase（v1.0 → v3.5.0）

### Phase 1-5: 基础架构（v1.0 → v1.3.0）
- DWG/DXF/PDF 解析、图纸分类、规则引擎、文档生成、智能审查

### Phase 6-7: 管理功能（v1.4 → v1.6.0）
- 多租户、项目管理、登录系统、Docker部署

### Phase 9-15: 前端+文档（v2.0.0 → v2.6.0）
- 审查/文档/流水线工作流、E2E测试、API文档、Docker、Admin面板

### Phase 16-20: 性能+安全（v2.7.0 → v3.1.0）
- 测试修复、批量处理、EMA独立化、性能监控、安全审计

### Phase 21: Agent LLM接入（v3.4.0 ✅）
- agent_llm.py（327行）— 统一LLM调用
- 6个Agent角色化system prompt
- 200/200 tests passed

---

## 后续规划（2026-06-05 确认）

### 第一阶段：稳固基础（1-2 周）

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | GitHub 远程同步 | ✅ 2026-06-07 tag v3.5.0 + feat/sse-streaming 已推送 |
| P0 | admin.html 登录验证 | ✅ 2026-06-07 已验证（boss_ke/koros0001 + admin后台 kzg@2023@SHMTU） |
| P1 | 端到端冒烟测试 | ✅ 2026-06-07 8/11 通过（SSE流式479+ tokens正常，CRUD接口正常） |
| P1 | 代码清理 | ✅ 2026-06-07 完成（admin.html 34 ref/27函数全部在setup内，花括号平衡，无截断） |

### 第二阶段：LLM 对话增强（2-3 周）

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 打字机效果 | ✅ 2026-06-07 SSE流式输出已完成（commit 4a1a83a） |
| P1 | Agent 独立对话 | ✅ 2026-06-07 per-agent messages/sessionId（commit 58b6fec） |
| P0 | 模型切换 UI | ✅ 2026-06-10 已完成（model-select + per-agent selectedModel） |
| P1 | Agent 独立对话 | ✅ 2026-06-10 已完成（7个Agent chip 独立 messages/sessionId） |
| P1 | 对话历史持久化 | ✅ 2026-06-07 ChromaDB持久化（commit 5317e1d） |
| P1 | 文件上传+分析 | ✅ 2026-06-10 已完成（upload/chat SSE流式端点） |

### 第三阶段：商业化准备（2026-06-10 启动，Phase 6 v2 深化 2026-06-12 进行中）

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | Docker 生产部署 | ✅ 2026-06-10 已完成 (SSL + 安全头 + 一键部署) |
| P0 | 主动智能推送 | ✅ 2026-06-10 已完成（里程碑检查 + API端点 + cron定时任务） |
| P1 | 批量处理增强 | ✅ 2026-06-10 已完成（批量并行上传分析 API + ThreadPoolExecutor） |
| P1 | 代码质量提升 | 🔲 清理.bak文件 + 消除重复代码 + 统一风格 |
| P1 | Phase 6 v2 深化 | 🔲 多租户UI增强 + 支付闭环 + 推送增强 + 性能优化 + 移动端适配 |
| P1 | 性能优化 | ✅ 2026-06-10 已完成（Semaphore并发控制 + 多worker + 超时配置） |
| P2 | 知识库 RAG | ✅ 2026-06-10 已完成（ChromaDB + 21条工程规范种子 + 对话自动检索） |
| P2 | 使用文档完善 | 🔲 API文档 + 部署指南 + 用户手册 |

### 第四阶段：生态扩展（待 Phase 3 完成后启动）

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P0 | 微信小程序对接 | 接入真实微信 OAuth（需要刚哥提供 AppID） |
| P1 | 客户试用 | 部署到云服务器，收集反馈 |
| P1 | 多租户运营 | 租户管理 + 计费 + 订阅 |

---

## 关键架构决策

### EMA 完全独立（刚性规则）
- 不依赖 blueprint-ai 项目
- 所有模块在 `src/` 下自包含
- 唯一外部依赖：PyPI 包

### 技术栈
- **后端：** FastAPI + SQLite + asyncio
- **前端：** Vue 3（CDN） + 原生 JS（admin.html）
- **AI：** Ollama（本地） + LongCat/Kimi（云端）
- **部署：** Docker + nginx + SSL

### 客户群体
勘察规划设计院 / 住建局 / 审图单位 / 造价单位 / 咨询单位 / 建设单位 / 施工单位 / 运营公司

---

## Git 提交规范
- feat: 新功能
- fix: 修复
- docs: 文档
- refactor: 重构
- test: 测试
- chore: 运维

详细进度见 `docs/04-项目进展/` 目录。
