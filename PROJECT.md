# 工程管理智能体 (EMA) - Engineering Management Agent

**版本：** v1.0.0（开发中）
**口号：** 工程管理，从"人管"到"智能体协管"

---

## 项目概述

EMA 是一个基于 Manus Agent 架构的工程管理智能体系统，集成图纸 AI 解析、国标审图、工程文档生成、工程量计算等能力，服务于勘察规划设计院、住建局、审图单位、造价单位、建设单位、施工单位、运营公司等客户。

**项目路径：** `/mnt/d/OpenClawDataworkspace/Projects/engineering-management-agent`

---

## 系统架构

```
🌐 刚哥 (Boss)
└── EngineeringManagementAgent (Main-Agent)
    ├── IntentClassifier     ← 自然语言意图分类
    ├── TaskPlanner          ← 任务规划
    ├── AgentOrchestrator    ← 多Agent编排调度
    ├── ResultCompiler       ← 结果整合输出
    │
    ├── 🔧 TechRdAgent (技术研发中心)
    │   └── 工具: parse / classify / analyze / extract_quantities / optimize / full_analysis / chat
    │
    ├── 🔒 SafetyComplianceAgent (安全与合规中心)
    │   └── 工具: review (15条国标规则) / fire_review / structural_review / compliance_review
    │
    ├── 📡 MarketSalesAgent (市场与销售中心)
    │   └── 工具: chat / tender_doc / price_quote / market_analysis
    │
    ├── 🏗️ EngineeringDeliveryAgent (工程交付中心)
    │   └── 工具: generate_sop / generate_mop / generate_eop / generate_lcc / completion_docs
    │
    ├── 💰 CostBenefitAgent (成本效益中心)
    │   └── 工具: generate_budget / extract_quantities / cost_analysis / investment_return
    │
    └── 🤝 CustomerServiceAgent (客户服务中心)
        └── 工具: chat / faq / training / feedback

Memory 层:
├── SessionContext (短期会话记忆，跨请求上下文)
└── ChromaDBStore (长期向量记忆，对话历史/项目特征/知识库)
```

---

## 核心模块

### Main-Agent
- **入口：** `POST /api/v1/main/chat`
- **工作流：** 意图分类 → 任务规划 → Sub-Agent 调度 → 结果整合 → ChromaDB 存储
- **支持：** 单步执行 / 多步并行（`dispatch_parallel`）

### Sub-Agent 继承关系
- **TechRdAgent** ← `blueprint-ai` (parse / classify / analyze / extract / optimize)
- **SafetyComplianceAgent** ← `blueprint-ai/review.py` (15条国标规则)
- **EngineeringDeliveryAgent** ← `blueprint-ai/sop.py, mop.py, eop.py, lcc.py`
- **CostBenefitAgent** ← `blueprint-ai/budget.py, documents.py`

---

## 服务地址

| 服务 | 地址 | 状态 |
|------|------|------|
| EMA API | `http://127.0.0.1:5188` | ✅ 运行中 |
| EMA UI | `http://127.0.0.1:5189/ui/` | ✅ 正常 |
| ChromaDB | `data/chromadb/` | ✅ 就绪（懒加载） |

---

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/agents` | GET | 列出所有 Agent |
| `/api/v1/agents/{id}` | GET | 单个 Agent 信息 |
| `/api/v1/main/chat` | POST | **主对话入口**（自然语言 → 全流程） |
| `/api/v1/agent/chat` | POST | Sub-Agent 路由（兼容） |
| `/api/v1/upload/analyze` | POST | 图纸上传分析 |
| `/api/v1/upload/review` | POST | 图纸审图 |
| `/api/v1/upload/budget` | POST | 工程预算生成 |
| `/api/v1/generate/sop` | POST | SOP 文档生成 |
| `/api/v1/generate/mop` | POST | MOP 文档生成 |
| `/api/v1/generate/eop` | POST | EOP 文档生成 |
| `/api/v1/generate/lcc` | POST | LCC 文档生成 |

---

## 开发进度

### ✅ Phase 1（2026-05-16）
- [x] Main-Agent 框架（IntentClassifier / TaskPlanner / Orchestrator / ResultCompiler）
- [x] 6个 Sub-Agent 骨架
- [x] SessionContext 短期记忆
- [x] API Server + UI

### ✅ Phase 2（2026-05-18 第一批）
- [x] ChromaDBStore 长期记忆层
- [x] SafetyComplianceAgent → `review.py`（15条国标规则）
- [x] EngineeringDeliveryAgent → `sop/mop/eop/lcc.py`
- [x] CostBenefitAgent → `budget.py` + `documents.py`
- [x] UI 增强（Agent 切换 + 多轮对话）

### ✅ Phase 3（2026-05-18 第二批）
- [x] Main-Agent 集成 ChromaDB 懒加载
- [x] 对话历史后台线程存储（不阻塞 API）
- [x] dispatch_parallel 多 Agent 并行执行
- [x] IntentClassifier greeting 优化（无图纸返回 chat）
- [x] TechRdAgent chat task_type 响应

### ✅ Phase 4（2026-05-19）
- [x] MarketSalesAgent 真实业务能力（投标文件生成/报价单生成/商务响应）
- [x] CustomerServiceAgent 真实业务能力（FAQ语义匹配/培训材料/反馈分析）
- [x] ChromaDB 对话历史 API（`/api/v1/conversations` + `/api/v1/conversations/search`）
- [x] PROJECT.md 技术文档更新（Phase 1-4 完整记录）

---

## 启动方式

```bash
# Linux/macOS
./start.sh

# Windows（双击运行）
一键启动EMA.bat

# API 单独启动
python3 src/main.py
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + Python 3.10+ |
| 前端 | HTML + Vanilla JS（Vue 3 CDN） |
| LLM | Ollama（本地）+ 云端 fallback |
| Sandbox | Pyodide（前端）+ Docker（后端） |
| 向量存储 | ChromaDB（长期记忆） |
| SQLite | 用户系统 / 审计日志 |

---

## Git 记录（2026-05-18）

```
e3d7e89 fix: 修复闲聊响应 + ChromaDB后台存储 + intent误判
bb7550b feat: EMA UI 增强 - Agent切换 + 多轮对话 + 结果展示优化
4642745 feat: Phase 2 - ChromaDB长期记忆层集成
28b5706 feat: Phase 2 - Sub-Agent集成完成
762e9a5 fix: 启动文件UI路径映射 - /ui/→ui/正确解析
969582a feat: EMA Phase 1 完成 - Main-Agent框架 + 5个Sub-Agent + Memory层
ac457a9 fix: TechRdAgent - LLMService.call() + Blueprint API调用双重保障
```

---

## 下一步

- [ ] UI对话历史展示（前端集成 `/api/v1/conversations`）
- [ ] 完整生命周期文档体系验证
- [ ] 技术文档完善（架构图/接口文档）
- [ ] EMA v1.0 正式release