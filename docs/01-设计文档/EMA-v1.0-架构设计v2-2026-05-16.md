# 工程管理智能体 v1.0 - 完整解决方案
> **日期：** 2026-05-16  
> **版本：** v2.0（重大升级版）  
> **背景：** 项目从"图纸AI助手"升级为"工程管理智能体"，定位工程管理全生命周期AI协作者

---

## 一、项目定位与目标

### 1.1 项目重命名

| 属性 | 内容 |
|------|------|
| **项目名称** | 工程管理智能体（Engineering Management Agent，简称EMA） |
| **版本** | v1.0 |
| **定位** | 工程管理全生命周期AI协作平台 |
| **Slogan** | 工程管理，从"人管"到"智能体协管" |
| **项目路径** | `D:\OpenClawDataworkspace\Projects\engineering-management-agent` |

### 1.2 客户群体分析

| 客户类型 | 核心痛点 | EMA能提供的价值 |
|----------|----------|----------------|
| **勘察规划设计院** | 图纸量大、规范多、审查周期长 | AI审图、规范化检查、设计优化 |
| **住建局** | 审批量大、监管难、跨部门协调 | 智能预审、违规自动识别、报告生成 |
| **审图单位** | 审图效率低、遗漏风险大 | 自动审图、合规检查、问题标注 |
| **造价单位** | 算量慢、价格波动大、对量繁琐 | 自动算量、材料询价、变更追踪 |
| **项目咨询单位** | 多项目并行、信息碎片化 | 项目统筹、文档管理、进度追踪 |
| **建设单位** | 协调复杂、进度难控、成本超支 | 全流程管理、成本控制、风险预警 |
| **施工单位** | 现场管理难、资料多、验收繁琐 | 现场AI辅助、资料自动归档、验收清单 |
| **运营公司** | 资产分散、维护记录缺失、安全隐患 | 资产台账、维保计划、安全预警 |

**战略洞察：** 以上客户覆盖工程全生命周期，EMA的竞争优势在于：
1. 从图纸理解出发，向全流程延伸（差异化竞争点）
2. 本地化部署 + 数据自主（政企客户核心诉求）
3. 一人公司逻辑（成本低，定价灵活）

---

## 二、组织架构设计

### 2.1 一人公司 team 架构

```
🌐 刚哥（BOSS · 创始人）
│
└── 🤖 工程管理与发展研究中心（MAIN-AGENT）
    │
    ├── 🔒 安全与合规中心（SUB-AGENT-1）
    ├── 📡 市场与销售中心（SUB-AGENT-2）
    ├── 💻 技术研发中心（SUB-AGENT-3）
    ├── 🏗️ 工程交付中心（SUB-AGENT-4）
    ├── 💰 成本效益中心（SUB-AGENT-5）
    └── 🤝 客户服务中心（SUB-AGENT-6）
```

### 2.2 MAIN-AGENT：工程管理与发展研究中心

**定位：** 刚哥的AI大脑，统管所有Sub-Agent，负责任务分解、调度、整合、汇报

**核心职责：**
- 接收刚哥的自然语言指令
- 理解任务，分解为子任务
- 调度合适的Sub-Agent执行
- 整合各Agent输出为最终成果
- 向刚哥汇报进度和结果
- 主动发现跨中心协作需求

**能力矩阵：**
- 任务规划（Task Planning）
- Agent调度（Agent Orchestration）
- 上下文管理（Context Management）
- 质量把控（Quality Control）
- 战略建议（Strategic Advisory）

### 2.3 SUB-AGENT-1：安全与合规中心

**定位：** 工程安全与合规守护者

**服务客户：** 住建局、审图单位、施工单位、运营公司

**核心能力：**
- 消防合规审查（疏散距离、防火分区、排烟竖井）
- 结构安全审查（荷载计算、抗震验算）
- 施工安全规范检查
- 法规合规性审核（对照国标/地标）
- 安全风险预警
- 合规报告自动生成

**现有基础：** `review.py`（5条国标规则引擎）→ 升级为智能合规Agent

**关键输出：**
- 合规审查报告（PDF/Word）
- 违规问题清单（带位置标注）
- 整改建议书
- 安全风险等级评定

### 2.4 SUB-AGENT-2：市场与销售中心

**定位：** 客户获取与商务推进

**服务客户：** 所有客户类型的商务阶段

**核心能力：**
- 市场分析（行业趋势、竞品分析）
- 客户需求挖掘（对话式理解）
- 自动生成商务方案（PPT/PDF）
- 投标文件辅助生成
- 客户报价智能生成
- 市场情报收集（联网搜索）
- 商务邮件/合同草稿

**关键输出：**
- 客户需求分析报告
- 商务方案书
- 投标文件（技术标/商务标）
- 报价单

### 2.5 SUB-AGENT-3：技术研发中心

**定位：** 技术能力底座，图纸AI核心

**服务客户：** 勘察规划设计院（核心用户）、审图单位

**核心能力：**
- 图纸智能解析（DWG/DXF/PDF）
- 图纸类型自动识别（建筑/结构/机电等）
- 图层语义理解
- 工程量自动提取
- 设计优化建议
- 技术规范匹配
- **（重构自现有blueprint-ai项目）**

**现有基础：** `blueprint-ai` 全套解析能力 → 封装为技术研发中心工具集

**关键输出：**
- 图纸分析报告
- 工程量清单
- 设计问题清单
- 技术交底书

### 2.6 SUB-AGENT-4：工程交付中心

**定位：** 项目执行与交付管理

**服务客户：** 施工单位、建设单位、项目咨询单位

**核心能力：**
- 项目计划制定（甘特图自动生成）
- 施工方案生成
- 进度追踪与预警
- 质量检查清单
- 竣工资料自动整理
- 技术核定单处理
- 工程联系单管理

**关键输出：**
- 项目计划书
- 施工组织设计
- 进度报告
- 质量验收报告
- 竣工资料包

### 2.7 SUB-AGENT-5：成本效益中心

**定位：** 工程造价与经济效益分析

**服务客户：** 造价单位、建设单位、施工单位、建设单位

**核心能力：**
- 工程量计算（基于图纸）
- 材料价格智能询价
- 预算/概算/结算生成
- 变更签证管理
- 成本对比分析（目标成本vs实际）
- 经济效益评估
- 投资回报分析

**现有基础：** `budget.py`（规则+材料库）→ 升级为智能成本Agent

**关键输出：**
- 工程预算书
- 变更签证清单
- 成本分析报告
- 投资回报方案

### 2.8 SUB-AGENT-6：客户服务中心

**定位：** 客户支持与关系维护

**服务客户：** 所有已成交客户

**核心能力：**
- 客户问题智能答疑（FAQ知识库）
- 工单管理（创建/跟踪/关闭）
- 客户回访计划制定
- 满意度分析
- 需求建议收集
- 使用培训材料生成
- 客户成功案例整理

**关键输出：**
- 问题处理报告
- 回访计划
- 培训材料
- 客户分析报告

---

## 三、产品架构

### 3.1 系统架构图

```
🌐 刚哥（BOSS）
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│              工程管理与发展研究中心（MAIN-AGENT）             │
│  • 自然语言理解（NLU）                                      │
│  • 任务规划与分解（Task Planning）                           │
│  • Agent调度与协调（Orchestration）                          │
│  • 结果整合与质量控制                                       │
└────┬────┬────┬────┬────┬──────────────────────────────────┘
     │    │    │    │    │
 ┌───┴┐┌─┴┐┌─┴┐┌─┴┐┌─┴┐┌─┴───┐
 │安全││市场││技术││工程││成本 ││客户 │
 │合规││销售││研发││交付││效益 ││服务 │
 └─┬─┘└─┬─┘└─┬─┘└─┬─┘└─┬─┘└─┬─┘
   │    │    │    │    │    │
   ▼    ▼    ▼    ▼    ▼    ▼
 ┌────────────────────────────────────────────────────────┐
 │                    工具层（TOOLS）                       │
 │  图纸解析 │ 规范库 │ 文档生成 │ 预算引擎 │ 知识库 │ 搜索 │
 └────────────────────────────────────────────────────────┘
 │                    执行层（SANDBOX）                      │
 │  Pyodide（前端）│ Docker（后端）│ Python Runtime          │
 └────────────────────────────────────────────────────────┘
 │                    记忆层（MEMORY）                       │
 │  短期 │ 长期（ChromaDB）│ 用户画像 │ 项目历史             │
 └────────────────────────────────────────────────────────┘
 │                    模型层（LLM）                          │
 │  Ollama（本地）│ 云端降级 │ 规划模型 │ 专项模型           │
 └────────────────────────────────────────────────────────┘
```

### 3.2 技术架构

```
工程管理智能体
├── 前端（UI Layer）
│   ├── Web对话界面（Vue3）
│   ├── 管理控制台（项目管理/用户管理）
│   └── 移动端适配（H5）
│
├── 主控层（Main-Agent）
│   ├── intent_classifier    — 意图识别
│   ├── task_planner         — 任务规划
│   ├── agent_orchestrator   — Agent调度
│   ├── result_compiler     — 结果整合
│   └── quality_controller   — 质量控制
│
├── 子Agent层（Sub-Agents）
│   ├── safety_compliance_agent    — 安全与合规
│   ├── market_sales_agent         — 市场与销售
│   ├── tech_rd_agent              — 技术研发（继承blueprint-ai）
│   ├── engineering_delivery_agent — 工程交付
│   ├── cost_benefit_agent         — 成本效益
│   └── customer_service_agent      — 客户服务
│
├── 工具层（Tools）
│   ├── blueprint_parser     — 图纸解析工具
│   ├── specs_engine         — 规范引擎
│   ├── doc_generator        — 文档生成器
│   ├── budget_engine        — 预算引擎
│   ├── knowledge_base       — 知识库
│   └── web_search           — 联网搜索
│
├── 执行层（Sandbox）
│   ├── Pyodide（前端执行）
│   └── Docker（后端执行）
│
├── 记忆层（Memory）
│   ├── session_context      — 短期记忆
│   ├── chromadb             — 长期向量记忆
│   └── user_project_db      — 用户/项目结构化数据
│
└── 模型层（LLM）
    ├── Ollama（本地部署）
    └── 云端降级（OpenAI兼容）
```

### 3.3 数据架构

```
用户数据（User Data）
├── 用户信息（Users）
├── 项目（Projects）
├── 图纸文件（Blueprints）
├── 分析结果（Analysis Results）
├── 生成文档（Documents）
└── 审计日志（Audit Logs）

知识库（Knowledge Base）
├── 国标库（Standards）— 结构化规范
├── 行业知识（Domain Knowledge）
├── 模板库（Templates）
└── 案例库（Case Studies）

向量数据库（ChromaDB）
├── 用户偏好向量
├── 项目特征向量
├── 对话历史摘要
└── 知识索引

内存数据库（Redis/SQLite）
├── 会话状态
├── Agent调度状态
├── 任务队列
└── 缓存
```

---

## 四、Agent详细设计

### 4.1 Main-Agent：工程管理与发展研究中心

```python
class EngineeringManagementAgent:
    """
    主控Agent - 工程管理与发展研究中心

    核心工作流程：
    1. 接收用户指令（自然语言）
    2. 意图分类（intent_classification）
    3. 任务规划（task_planning）
    4. 子Agent调度（agent_dispatch）
    5. 结果整合（result_compilation）
    6. 输出交付（delivery）
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.task_planner = TaskPlanner()
        self.orchestrator = AgentOrchestrator()
        self.result_compiler = ResultCompiler()
        self.quality_controller = QualityController()

        # 六个子Agent
        self.sub_agents = {
            'safety_compliance': SafetyComplianceAgent(),
            'market_sales': MarketSalesAgent(),
            'tech_rd': TechRDAgent(),           # 继承 blueprint-ai
            'engineering_delivery': EngineeringDeliveryAgent(),
            'cost_benefit': CostBenefitAgent(),
            'customer_service': CustomerServiceAgent(),
        }

    async def run(self, user_input: str, user_id: str, project_id: str):
        # Step 1: 理解意图
        intent = await self.intent_classifier.classify(user_input)

        # Step 2: 规划任务
        plan = await self.task_planner.create_plan(
            intent=intent,
            user_input=user_input,
            context=await self.load_context(user_id, project_id)
        )

        # Step 3: 调度子Agent
        results = await self.orchestrator.dispatch(plan, self.sub_agents)

        # Step 4: 质量检查
        quality_check = await self.quality_controller.check(results)

        # Step 5: 整合输出
        output = await self.result_compiler.compile(
            plan=plan,
            results=results,
            quality=quality_check
        )

        # Step 6: 记忆存储
        await self.save_to_memory(user_id, project_id, intent, plan, output)

        return output
```

### 4.2 Sub-Agent：通用设计模式

每个Sub-Agent遵循统一设计：

```python
class BaseSubAgent:
    """Sub-Agent 基类"""

    def __init__(self, name: str, capabilities: List[str]):
        self.name = name
        self.capabilities = capabilities
        self.tools = []  # 可用工具列表
        self.memory = AgentMemory()

    async def execute(self, task: Task) -> AgentResult:
        # 1. 理解任务
        # 2. 选择工具
        # 3. 执行（可能多步）
        # 4. 验证结果
        # 5. 返回
        pass

    async def plan(self, task: str) -> Plan:
        """将任务分解为可执行步骤"""
        pass

    async def validate(self, result: Any) -> ValidationResult:
        """验证输出质量"""
        pass
```

### 4.3 Agent间通信协议

```
Main-Agent → Sub-Agent: 任务描述 + 上下文 + 约束
Sub-Agent → Main-Agent: 执行结果 + 状态 + 置信度
Sub-Agent ↔ Sub-Agent: 通过Main-Agent协调，共享数据需经过主Agent
```

---

## 五、功能模块规划

### 5.1 第一期（v1.0.0）— 核心框架

**目标：** 搭建Agent骨架，实现技术研发中心（继承blueprint-ai）

| 模块 | 功能 | 优先级 |
|------|------|--------|
| Main-Agent框架 | 任务调度/意图识别/结果整合 | P0 |
| 技术研发中心 | 图纸解析/类型识别/分析 | P0 |
| 基础对话UI | Web对话界面（Vue3） | P0 |
| 用户系统 | 注册/登录/权限 | P1 |
| 项目管理 | 创建/管理工程项目 | P1 |

### 5.2 第二期（v1.1.0）— 合规与交付

| 模块 | 功能 | 优先级 |
|------|------|--------|
| 安全与合规中心 | 国标审查/消防检查/报告生成 | P1 |
| 工程交付中心 | 施工方案/进度计划/验收清单 | P1 |
| 文档工具集 | Word/PDF生成 | P1 |

### 5.3 第三期（v1.2.0）— 成本与市场

| 模块 | 功能 | 优先级 |
|------|------|--------|
| 成本效益中心 | 工程量计算/预算生成 | P2 |
| 市场与销售中心 | 商务方案/投标文件 | P2 |
| 国标库扩充 | 更多规范类别 | P2 |

### 5.4 第四期（v1.3.0）— 服务与高级功能

| 模块 | 功能 | 优先级 |
|------|------|--------|
| 客户服务中心 | FAQ/工单/培训材料 | P2 |
| 记忆系统 | ChromaDB持久化 | P2 |
| 多Agent协作 | 并行任务执行 | P3 |

---

## 六、技术实现方案

### 6.1 项目目录结构

```
engineering-management-agent/
├── PROJECT.md
├── README.md
├── LICENSE
│
├── src/
│   ├── main.py                    # 主入口
│   ├── api_server.py             # FastAPI服务（保留原有）
│   │
│   ├── agent/                    # Agent框架
│   │   ├── __init__.py
│   │   ├── main_agent.py         # 工程管理与发展研究中心
│   │   ├── intent_classifier.py  # 意图识别
│   │   ├── task_planner.py       # 任务规划
│   │   ├── orchestrator.py       # Agent调度器
│   │   ├── result_compiler.py    # 结果整合
│   │   └── quality_controller.py # 质量控制
│   │
│   ├── sub_agents/               # 六个子Agent
│   │   ├── __init__.py
│   │   ├── safety_compliance_agent.py
│   │   ├── market_sales_agent.py
│   │   ├── tech_rd_agent.py      # 继承blueprint-ai核心能力
│   │   ├── engineering_delivery_agent.py
│   │   ├── cost_benefit_agent.py
│   │   └── customer_service_agent.py
│   │
│   ├── tools/                    # 工具层（重构自现有模块）
│   │   ├── blueprint_parser/     # 图纸解析工具集
│   │   │   ├── __init__.py
│   │   │   ├── core.py
│   │   │   ├── dwg_parser.py
│   │   │   ├── dxf_parser.py
│   │   │   ├── pdf_parser.py
│   │   │   └── inference.py
│   │   ├── specs_engine/         # 规范引擎
│   │   ├── doc_generator/        # 文档生成
│   │   ├── budget_engine/        # 预算引擎
│   │   └── knowledge_base/       # 知识库
│   │
│   ├── sandbox/                  # 执行环境
│   │   ├── __init__.py
│   │   ├── pyodide_runner.py     # 前端Pyodide
│   │   └── docker_runner.py      # 后端Docker
│   │
│   ├── memory/                   # 记忆层
│   │   ├── __init__.py
│   │   ├── session_context.py
│   │   ├── chromadb_store.py
│   │   └── user_project_db.py
│   │
│   └── models/                   # 模型层
│       ├── llm_service.py        # 已有
│       ├── llm_supervisor.py     # 已有
│       └── prompts/
│           ├── main_agent_prompts.py
│           └── sub_agent_prompts.py
│
├── ui/                          # 前端
│   ├── ui-vue/                  # Vue3源码
│   ├── ui-dist/                 # 构建产物
│   └── public/
│
├── tests/                       # 测试
│   ├── agent_tests/
│   ├── tool_tests/
│   └── integration_tests/
│
├── docs/                        # 文档
│   ├── 01-设计文档/
│   ├── 02-用户手册/
│   ├── 03-开发文档/
│   └── 04-项目进展/              # 进度报告
│
├── data/                        # 数据
│   ├── standards/               # 国标库
│   ├── templates/               # 文档模板
│   └── samples/                 # 样例数据
│
├── requirements.txt
├── start.sh
└── .env
```

### 6.2 迁移策略（从blueprint-ai）

```
blueprint-ai → engineering-management-agent/tech_rd_agent/

继承关系：
├── tools/blueprint_parser/*    ← 直接迁移（core.py/dxf_parser.py等）
├── src/llm_service.py          ← 迁移到 models/llm_service.py
├── src/llm_supervisor.py       ← 迁移到 models/llm_supervisor.py
├── src/api_server.py           ← 保留，重构为Agent API
├── ui-vue/*                    ← 迁移，重构对话UI
├── alembic/                    ← 用户系统数据库迁移
└── docs/standards/             ← 国标库迁移

新增：
├── agent/*                     — Agent框架（新建）
├── sub_agents/*                — 6个子Agent（新建）
├── sandbox/*                   — 执行环境（新建）
├── memory/*                    — 记忆层（新建）
└── docs/04-项目进展/            — 本方案归档
```

### 6.3 API设计（Agent风格）

```python
# 核心Agent接口

# 对话式接口（主要交互方式）
POST /api/v1/agent/chat
Body: {
    "message": "帮我审查这张图纸的消防合规性",
    "user_id": "xxx",
    "project_id": "xxx"
}
Response: {
    "agent_id": "safety_compliance",
    "status": "completed",
    "output": {...},
    "confidence": 0.95
}

# 任务状态查询
GET /api/v1/agent/task/{task_id}

# Agent能力查询
GET /api/v1/agent/capabilities

# 保留原有REST API（兼容）
POST /api/v1/upload/analyze
POST /api/v1/generate/documents
...
```

---

## 七、商业模式

### 7.1 定价策略

| 版本 | 定价 | 功能 | 目标客户 |
|------|------|------|----------|
| **体验版** | 免费 | 3个项目/月，基础审图 | 个人/小团队 |
| **专业版** | ¥299/月 | 无限项目，高级审图，文档生成 | 小型设计院/咨询公司 |
| **企业版** | ¥999/月 | 多用户协作，定制规范，API接入 | 中型设计院/建设单位 |
| **私有部署** | 议价 | 完全私有，数据自主，定制开发 | 住建局，大型企业 |

### 7.2 竞争壁垒

1. **图纸理解能力**（差异化）：不是通用AI，是懂工程的AI
2. **本地化部署**：数据不出门，政企客户刚需
3. **规范库积累**：国标/地标库持续更新，先发优势
4. **一人公司逻辑**：成本优势，价格灵活

---

## 八、实施计划

### 8.1 时间规划

```
2026-05  ───────  项目立项，目录重建，方案确认
         │
2026-06  ───────  第一期：Agent框架 + 技术研发中心
         │        • Main-Agent骨架
         │        • Tech RD Agent（继承blueprint-ai）
         │        • 基础对话UI
         │        • 用户系统
         │
2026-07  ───────  第二期：合规与交付Agent
         │        • Safety Compliance Agent
         │        • Engineering Delivery Agent
         │        • 文档生成工具集
         │
2026-08  ───────  第三期：成本与市场Agent
         │        • Cost Benefit Agent
         │        • Market Sales Agent
         │        • 国标库扩充
         │
2026-09  ───────  第四期：服务+高级功能
         │        • Customer Service Agent
         │        • Memory系统
         │        • 多Agent协作
         │
2026-10  ───────  正式发布 v1.0
```

### 8.2 资源估算

- **人力**：1人（刚哥）+ AI助手（GDP影子）
- **服务器**：1台（API+LLM+Ollama），预计 ¥200/月
- **开发工具**：VSCode + Git + OpenClaw

---

## 九、风险与应对

| 风险 | 级别 | 应对 |
|------|------|------|
| blueprint-ai历史代码迁移量大 | 🔴 高 | 分阶段迁移，核心先转，工具层逐步重构 |
| Agent规划质量不稳定 | 🟡 中 | 先规则后LLM，验证环路上线 |
| 单人公司时间有限 | 🔴 高 | AI助手（GDP影子）承担更多开发任务 |
| 政企客户决策周期长 | 🟡 中 | 先做小B市场，快速验证 |
| 规范库覆盖不足 | 🟡 中 | 用户贡献 + 联网搜索补充 |

---

## 十、结论

**工程管理智能体 v1.0** 是从"图纸AI工具"向"工程管理AI平台"的战略升级。

核心差异化：
- 覆盖工程全生命周期（勘察→设计→施工→运营）
- 组织化Agent架构（6中心+1大脑）
- 图纸理解能力作为切入点（竞争壁垒）

从blueprint-ai迁移开始，逐步构建完整产品。

---

## 附录：术语表

| 术语 | 说明 |
|------|------|
| Main-Agent | 主控智能体，负责全局调度 |
| Sub-Agent | 子智能体，负责专业领域 |
| Sandbox | 隔离执行环境，用于安全运行生成的代码 |
| Intent Classification | 意图识别，判断用户想要什么 |
| Task Planning | 任务规划，将复杂任务分解为步骤 |
| Orchestration | Agent编排，协调多Agent工作 |
| ChromaDB | 向量数据库，用于长期记忆存储 |
| Pyodide | 浏览器内Python运行时，用于前端代码执行 |

---

## 文档更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-05-16 | v1.0 | 初始方案（基于Manus架构） |
| 2026-05-16 | v2.0 | 重大升级：项目重命名+组织架构+完整解决方案 |