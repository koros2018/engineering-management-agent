# EMA 全面功能测试 & Manus架构对照报告

> **日期：** 2026-06-03 | **版本：** v3.9.0 | **测试：** 200/200 passed
> **执行：** GDP影子

---

## 一、基线数据

| 维度 | 数值 |
|------|------|
| API端点 | 123个 |
| 后端代码 | 61 py / 20324行 |
| UI代码 | 3文件 / 7426行 |
| 测试用例 | 200 passed / 0 failed |
| LLM模型 | 4个全通 (LongCat/Kimi/Qwen/R1) |
| 国标规范库 | 65个标准文件 |
| 数据文件 | 40+ (用户/租户/分析/反馈/缓存) |

---

## 二、对照 Manus 架构的差距分析

### 2.1 Manus 核心架构 vs EMA 现状

| Manus 特征 | EMA 现状 | 差距 |
|------------|----------|------|
| **规划-执行-验证循环** | main/chat 有意图分类，但无规划→验证闭环 | 🔴 缺失验证环节 |
| **Multi-Agent 编排** | 6个Agent定义存在，但只有 tech_rd 有实际逻辑 | 🔴 5个Agent是空壳 |
| **Sandbox 隔离执行** | 无隔离环境，所有Agent共享同一进程 | 🔴 无沙箱 |
| **工具调用 (Tool Use)** | 部分支持 (upload/review/documents/pipeline) | 🟡 工具可用但分散 |
| **上下文管理 (Memory)** | 无持久化对话记忆 | 🔴 缺失 |
| **任务分解 (Task Decomposition)** | main/chat 有意图分类 | 🟡 基础实现 |
| **结果整合 (Result Synthesis)** | 无多Agent结果融合 | 🔴 缺失 |

### 2.2 Sub-Agent 真实状态

**测试方法：** 对每个 Agent 发送 `agent/chat` 请求，检验回复内容

| Agent | 定义 | 实际回复 | 状态 |
|-------|------|----------|------|
| tech_rd | 图纸解析/AI分析/工程量 | ✅ "🔧 技术研发中心..." | 🟢 有内容（模板回复） |
| safety_compliance | 消防合规/结构安全 | ❌ 同 tech_rd | 🔴 未实现 |
| engineering_delivery | SOP/MOP/EOP/LCC | ❌ 同 tech_rd | 🔴 未实现 |
| cost_benefit | 工程量/预算/变更 | ❌ 同 tech_rd | 🔴 未实现 |
| market_sales | 方案/投标/市场 | ❌ 同 tech_rd | 🔴 未实现 |
| customer_service | FAQ/工单/培训 | ❌ 同 tech_rd | 🔴 未实现 |

**根因：**
1. `AgentChatRequest` 模型缺少 `agent_id` 字段
2. `agent/chat` 端点用 `req.task_type` 而非 `agent_id` 路由
3. 只有 `tech_rd` Agent 的 `_chat` 方法有实际实现
4. 其余 5 个 Agent 的 `_chat` 方法是空壳/回退到 tech_rd

---

## 三、详细功能测试

### 3.1 LLM 连通性 ✅

| 模型 | Provider | 状态 | 延迟 |
|------|----------|------|------|
| LongCat 2.0 Preview | longcat | ✅ enabled | — |
| Kimi K2.6 | opencode | ✅ enabled | — |
| Qwen 3.5 9B | ollama | ✅ enabled | — |
| DeepSeek R1 7B | ollama | ✅ enabled | — |

### 3.2 核心工作流测试

| 端点 | 功能 | 状态 | 备注 |
|------|------|------|------|
| `/api/v1/main/chat` | Main-Agent 对话 | ✅ 已修复 | 之前缺 `req.` 前缀导致500 |
| `/api/v1/agent/chat` | Sub-Agent 对话 | ✅ 已修复 | 之前缺 `req.` 前缀导致500 |
| `/api/v1/agent/task` | 通用任务提交 | ✅ | 仅支持 tech_rd |
| `/api/v1/agent/review` | 智能审查 | ✅ | 15条国标规则 |
| `/api/v1/agent/documents` | 文档生成 | ✅ | 5类文档 |
| `/api/v1/agent/pipeline` | 端到端流水线 | ✅ | 5步流程 |
| `/api/v1/agent/analyze` | 图纸分析 | ✅ | 解析+分类+提取 |
| `/api/v1/budget/calculate` | 预算计算 | ✅ | 工程量清单 |

### 3.3 数据完整性 ✅

| 数据类型 | 状态 |
|----------|------|
| 用户数据 (users.json) | ✅ 5612 bytes |
| 租户数据 (tenants.json) | ✅ 3959 bytes |
| 行为分析 (5天数据) | ✅ ~10KB |
| 反馈数据 (5天) | ✅ ~8.7KB |
| 国标规范库 (65标准) | ✅ ~75KB |
| 缓存数据 | ✅ 9文件 |
| 通知 (111KB) | ✅ |
| 模型配置 | ✅ 4模型 |

---

## 四、关键 Bug 修复（本轮）

| Bug | 文件 | 修复 |
|-----|------|------|
| `main/chat` 500错误 | api_server.py:821 | `message` → `req.message` 等4处 |
| `agent/chat` 500错误 | api_server.py:871 | `file_path` → `req.file_path` 等4处 |

---

## 五、Phase 26 方案：Manus 风格 Sub-Agent 真实化

### 目标
> 将 EMA 从"1个真Agent + 5个空壳"升级为"6个真正的Sub-Agent，在Main-Agent管理下协作"

### 架构设计

```
                    ┌──────────────────────┐
                    │    Main-Agent (大脑)   │
                    │  意图分类 → 任务规划   │
                    │  → 调度 → 整合 → 汇报  │
                    └──────┬───────────────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Tech RD   │    │Safety    │    │Delivery  │
    │图纸解析   │    │合规审查   │    │工程交付   │
    │蓝图AI    │    │国标规则   │    │SOP/MOP   │
    │大模型🧠  │    │大模型🧠  │    │大模型🧠  │
    └──────────┘    └──────────┘    └──────────┘
           │               │               │
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │Cost      │    │Market    │    │Customer  │
    │成本预算   │    │市场销售   │    │客户服务   │
    │清单计算   │    │投标方案   │    │FAQ/工单   │
    │大模型🧠  │    │大模型🧠  │    │大模型🧠  │
    └──────────┘    └──────────┘    └──────────┘
```

### 每个 Sub-Agent 需要实现

1. **独立 System Prompt** — 定义专业领域和输出规范
2. **LLM 连接** — 调用模型路由获取大脑
3. **专业工具** — 每个Agent的专属 tool set
4. **输入/输出 Schema** — 规范化的数据格式
5. **错误处理** — 独立错误恢复

### 实施计划

| Phase | 内容 | 预估 |
|-------|------|------|
| 26-A | AgentChatRequest 添加 agent_id 字段 + 路由修复 | 0.5轮 |
| 26-B | 每个 Sub-Agent 独立的 System Prompt + LLM 对话 | 2轮 |
| 26-C | Sub-Agent 专属 tool set (审查/预算/文档/LCC等) | 2轮 |
| 26-D | Main-Agent 规划→调度→整合→汇报完整流程 | 1.5轮 |
| 26-E | 前端无缝对接 + 端到端测试 | 1轮 |
| **合计** | — | **~7轮** |

---

## 六、决策点

> ⚠️ **需刚哥确认：**

1. **Phase 26 优先级？** — 比照 Manus 架构实现 6 个真实 Sub-Agent
2. **每个 Sub-Agent 用哪个 LLM？** — 建议：规则类用本地 Ollama，创意类用云端 LongCat/Kimi
3. **是否需要 Sandbox 隔离？** — Docker 容器隔离 vs 进程内隔离
4. **前端是否需要调整？** — 当前 Agent 列表已就绪，后端打通后自然可用
