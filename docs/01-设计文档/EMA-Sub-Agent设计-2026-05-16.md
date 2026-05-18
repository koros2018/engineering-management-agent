# EMA Agent 详细设计文档
> **日期：** 2026-05-16  
> **版本：** v1.0  
> **状态：** 进行中  
> **依据Rule：** 技术规范参照Manus，工作目标："工程管理从'人管'到'智能体协管'"

---

## 一、扁平化Agent架构总览

```
🌐 刚哥（Boss）
│
└── 🤖 Main-Agent（工程管理与发展研究中心）
    ├── SafetyComplianceAgent
    ├── MarketSalesAgent
    ├── TechRdAgent
    ├── EngineeringDeliveryAgent
    ├── CostBenefitAgent
    └── CustomerServiceAgent

扁平化原则：
- 6个Agent平行运行，无层级嵌套
- Main-Agent负责任务分发、结果整合、质量把控
- Agent之间不直接通信，都通过Main-Agent协调
- 每个Agent独立工具集，但可调用共享工具层
```

---

## 二、Main-Agent 详细设计

### 2.1 核心定位

**工程管理与发展研究中心（Main-Agent）**

- **唯一入口**：所有来自Boss的指令首先进入Main-Agent
- **智能调度**：将任务分解并分发给合适的Sub-Agent
- **结果整合**：收集各Agent输出，整合为最终交付物
- **质量把控**：验证各Agent输出质量，不合格打回重做
- **战略建议**：在适当时机主动提供建议，不只是被动执行

### 2.2 核心模块

```python
class EngineeringManagementAgent:
    """
    Main-Agent: 工程管理与发展研究中心

    工作流程：
    receive() → understand() → plan() → dispatch() → integrate() → deliver()
    """

    def __init__(self):
        # 核心组件
        self.nlu = NLUModule()           # 自然语言理解
        self.planner = TaskPlanner()       # 任务规划器
        self.orchestrator = Orchestrator() # Agent调度器
        self.quality_controller = QualityController() # 质量控制
        self.result_compiler = ResultCompiler() # 结果整合
        self.memory = AgentMemory()        # 记忆管理
        self.context = ContextManager()    # 上下文管理

        # 6个专业Agent（扁平化，平行运行）
        self.agents = {
            'safety_compliance': SafetyComplianceAgent(),
            'market_sales': MarketSalesAgent(),
            'tech_rd': TechRdAgent(),
            'engineering_delivery': EngineeringDeliveryAgent(),
            'cost_benefit': CostBenefitAgent(),
            'customer_service': CustomerServiceAgent(),
        }

    async def run(self, user_input: str, user_id: str, context: dict) -> AgentResponse:
        # === 阶段1：接收与理解 ===
        parsed = await self.nlu.parse(user_input)  # 意图+实体+情感

        # === 阶段2：任务规划 ===
        plan = await self.planner.create_plan(
            intent=parsed.intent,
            entities=parsed.entities,
            context=context
        )

        # === 阶段3：Agent调度（可并行） ===
        agent_results = await self.orchestrator.dispatch(plan, self.agents)

        # === 阶段4：质量检查 ===
        quality_results = []
        for agent_id, result in agent_results:
            qr = await self.quality_controller.check(result)
            if not qr.passed:
                # 打回重做（最多2次）
                result = await self.retry(agent_id, plan.steps[agent_id], attempt=qr.attempt+1)
            quality_results.append((agent_id, result, qr))

        # === 阶段5：结果整合 ===
        output = await self.result_compiler.compile(
            plan=plan,
            results=quality_results,
            user_context=context
        )

        # === 阶段6：记忆存储 ===
        await self.memory.save(
            user_id=user_id,
            intent=parsed.intent,
            plan=plan,
            output=output
        )

        # === 阶段7：主动建议 ===
        suggestions = await self.proactive_suggest(output, context)

        return AgentResponse(
            main_output=output,
            suggestions=suggestions,
            quality_report=self.generate_quality_report(quality_results)
        )
```

### 2.3 NLU模块（自然语言理解）

```python
class NLUModule:
    """
    自然语言理解模块
    解析用户输入，提取：意图、实体、情感、紧急程度
    """

    # 预定义意图（覆盖工程管理全场景）
    INTENTS = {
        # 技术研发
        'analyze_blueprint': '分析图纸',
        'extract_quantities': '提取工程量',
        'optimize_design': '优化设计',

        # 安全合规
        'review_compliance': '合规审查',
        'check_fire_safety': '消防审查',
        'check_structural': '结构安全审查',

        # 工程交付
        'generate_plan': '生成施工计划',
        'create_checklist': '生成验收清单',
        'draft_tech_change': '起草技术核定单',

        # 成本效益
        'generate_budget': '生成预算',
        'track_changes': '变更追踪',
        'cost_analysis': '成本分析',

        # 市场销售
        'generate_proposal': '生成商务方案',
        'prepare_bid': '准备投标',
        'market_research': '市场调研',

        # 客户服务
        'answer_faq': '答疑',
        'generate_training': '生成培训材料',
        'track_issue': '工单追踪',
    }

    async def parse(self, text: str) -> ParsedInput:
        # 使用LLM进行意图分类 + 实体抽取
        # 备用：规则匹配（当LLM不可用时）
        pass
```

### 2.4 任务规划器

```python
class TaskPlanner:
    """
    任务规划器
    将复杂任务分解为可执行的步骤序列
    """

    async def create_plan(self, intent: str, entities: dict, context: dict) -> Plan:
        """
        生成执行计划

        输出格式：
        Plan {
            steps: List[Step]           # 执行步骤列表
            estimated_time: str         # 预估时间
            required_agents: List[str]  # 需要调用的Agent
            fallback_strategy: str     # 降级策略
        }
        """
        pass

    def _decompose_intent(self, intent: str) -> List[Step]:
        """将意图分解为原子步骤"""
        # 例如：'review_compliance' → ['parse_blueprint', 'check_fire_safety',
        #                                'check_structural', 'generate_report']
        pass
```

### 2.5 调度器（扁平化核心）

```python
class Orchestrator:
    """
    Agent调度器
    扁平化调度：将任务分发给合适的Agent，支持并行执行
    """

    async def dispatch(self, plan: Plan, agents: dict) -> Dict[str, AgentResult]:
        """
        调度执行

        并行策略：
        - 无依赖的步骤并行执行
        - 有依赖的步骤串行执行

        例如：
        - 审图 + 预算 → 并行（不同Agent）
        - 解析图纸 → 生成报告 → 串行（同Agent）
        """
        results = {}

        # 找出可并行的步骤组
        parallel_groups = self._identify_parallel_groups(plan.steps)

        for group in parallel_groups:
            if len(group) == 1:
                # 串行执行
                step = group[0]
                agent = agents[step.agent_id]
                results[step.agent_id] = await agent.execute(step)
            else:
                # 并行执行（asyncio.gather）
                tasks = []
                for step in group:
                    agent = agents[step.agent_id]
                    tasks.append(agent.execute(step))
                group_results = await asyncio.gather(*tasks)
                for step, result in zip(group, group_results):
                    results[step.agent_id] = result

        return results
```

### 2.6 质量控制器

```python
class QualityController:
    """
    质量控制模块
    验证Agent输出质量，不合格打回重做
    """

    QUALITY_THRESHOLDS = {
        'blueprint_analysis': 0.8,   # 图纸分析置信度 ≥ 0.8
        'compliance_review': 0.9,    # 合规审查置信度 ≥ 0.9（涉及安全）
        'budget_generation': 0.85,   # 预算生成置信度 ≥ 0.85
        'document_generation': 0.75,  # 文档生成置信度 ≥ 0.75
    }

    async def check(self, result: AgentResult) -> QualityResult:
        """
        检查输出质量

        检查维度：
        1. 完整性（是否包含所有必需字段）
        2. 准确性（置信度是否达标）
        3. 一致性（与上下文是否矛盾）
        4. 格式合规（是否符合输出规范）
        """
        pass

    async def retry(self, agent_id: str, step: Step, attempt: int) -> AgentResult:
        """重试机制（最多2次）"""
        pass
```

---

## 三、Sub-Agent 详细设计

### 3.1 通用Sub-Agent基类

```python
class BaseAgent(ABC):
    """
    Sub-Agent基类
    所有6个专业Agent继承此类
    """

    def __init__(self, agent_id: str, name: str, description: str):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.tools = []          # 可用工具
        self.memory = AgentMemory()
        self.max_retries = 2

    @abstractmethod
    async def execute(self, task: Task) -> AgentResult:
        """执行任务（子类必须实现）"""
        pass

    async def plan(self, task: str) -> Plan:
        """将任务分解为步骤"""
        pass

    async def validate(self, result: Any) -> bool:
        """验证输出"""
        pass

    async def run_with_retry(self, task: Task) -> AgentResult:
        """带重试的执行"""
        for attempt in range(self.max_retries):
            result = await self.execute(task)
            if await self.validate(result):
                return result
            if attempt < self.max_retries - 1:
                result = await self._adjust(task, result)
        return result
```

### 3.2 SafetyComplianceAgent（安全与合规Agent）

**Agent ID：** `safety_compliance`  
**名称：** 安全与合规中心  
**定位：** 工程安全与合规守护者

```python
class SafetyComplianceAgent(BaseAgent):
    """
    SafetyComplianceAgent - 安全与合规Agent

    核心能力：
    1. 消防合规审查（疏散距离、防火分区、排烟竖井）
    2. 结构安全审查（荷载、抗震）
    3. 施工安全规范检查
    4. 合规报告自动生成

    工具集：
    - blueprint_parser: 图纸解析
    - specs_engine: 规范匹配
    - compliance_checker: 合规检查器
    - report_generator: 报告生成
    """

    AGENT_ID = 'safety_compliance'
    NAME = '安全与合规中心'
    DESCRIPTION = '负责工程安全检查和合规性审查'

    def __init__(self):
        super().__init__(
            agent_id=self.AGENT_ID,
            name=self.NAME,
            description=self.DESCRIPTION
        )
        self.tools = [
            BlueprintParserTool(),       # 图纸解析
            SpecsMatcherTool(),          # 规范匹配
            FireSafetyChecker(),         # 消防检查
            StructuralSafetyChecker(),   # 结构检查
            ComplianceReportGenerator(), # 报告生成
        ]

    async def execute(self, task: Task) -> AgentResult:
        # 1. 解析任务类型
        check_type = task.params.get('check_type', 'full')

        # 2. 调用工具链
        if check_type == 'fire_safety':
            return await self._check_fire_safety(task)
        elif check_type == 'structural':
            return await self._check_structural(task)
        else:
            return await self._full_compliance_review(task)

    async def _check_fire_safety(self, task: Task) -> AgentResult:
        """
        消防合规审查
        检查：疏散距离 / 防火分区 / 排烟竖井 / 消防车道
        """
        # 继承现有 review.py 的5条国标规则
        # 扩展：LLM解读 + 自然语言报告
        pass

    async def _full_compliance_review(self, task: Task) -> AgentResult:
        """全量合规审查"""
        # 并行：消防 + 结构 + 电气 + 给排水
        # 整合：生成综合合规报告
        pass
```

**输出规范：**
```python
class ComplianceReport:
    report_id: str
    project_name: str
    check_date: datetime
    checker: str  # 'SafetyComplianceAgent'

    items: List[ComplianceItem]
    # ComplianceItem: {rule_id, description, status, severity, location, suggestion}

    overall_status: Literal['pass', 'fail', 'warning']
    confidence: float  # 0-1
    next_review_date: datetime
```

### 3.3 MarketSalesAgent（市场与销售Agent）

**Agent ID：** `market_sales`  
**名称：** 市场与销售中心  
**定位：** 客户获取与商务推进

```python
class MarketSalesAgent(BaseAgent):
    """
    MarketSalesAgent - 市场与销售Agent

    核心能力：
    1. 市场分析（行业趋势、竞品分析）
    2. 客户需求挖掘（对话式理解）
    3. 商务方案自动生成
    4. 投标文件辅助生成
    5. 智能报价

    工具集：
    - web_search: 联网市场调研
    - document_generator: 文档生成
    - proposal_builder: 方案构建器
    - bid_preparer: 投标助手
    """

    AGENT_ID = 'market_sales'
    NAME = '市场与销售中心'

    def __init__(self):
        super().__init__(agent_id=self.AGENT_ID, name=self.NAME, description=...)
        self.tools = [
            WebSearchTool(),             # 联网搜索
            DocumentGeneratorTool(),     # 文档生成
            ProposalBuilderTool(),       # 方案构建
            BidPreparerTool(),           # 投标准备
            PricingCalculatorTool(),     # 报价计算
        ]

    async def execute(self, task: Task) -> AgentResult:
        task_type = task.params.get('type')

        if task_type == 'market_research':
            return await self._market_research(task)
        elif task_type == 'generate_proposal':
            return await self._generate_proposal(task)
        elif task_type == 'prepare_bid':
            return await self._prepare_bid(task)
        elif task_type == 'calculate_quote':
            return await self._calculate_quote(task)
```

**输出规范：**
```python
class MarketSalesOutput:
    outputs: List[Union[
        MarketAnalysisReport,    # 市场分析报告
        BusinessProposal,        # 商务方案
        BidDocument,             # 投标文件
        PriceQuote,              # 报价单
    ]]
    confidence: float
```

### 3.4 TechRdAgent（技术研发Agent）

**Agent ID：** `tech_rd`  
**名称：** 技术研发中心  
**定位：** 技术能力底座，图纸AI核心（继承blueprint-ai）

```python
class TechRdAgent(BaseAgent):
    """
    TechRdAgent - 技术研发Agent

    核心能力（继承自blueprint-ai）：
    1. 图纸智能解析（DWG/DXF/PDF）
    2. 图纸类型自动识别（建筑/结构/机电等）
    3. 图层语义理解
    4. 工程量自动提取
    5. 设计优化建议

    工具集：
    - BlueprintParserTool: 图纸解析
    - TypeClassifierTool: 类型识别
    - LayerAnalyzerTool: 图层分析
    - QuantityExtractorTool: 工程量提取
    - DesignOptimizerTool: 设计优化
    """

    AGENT_ID = 'tech_rd'
    NAME = '技术研发中心'

    def __init__(self):
        super().__init__(...)
        self.tools = [
            BlueprintParserTool(),       # 继承 core.py
            TypeClassifierTool(),         # 继承 inference.py
            LayerAnalyzerTool(),         # 新增
            QuantityExtractorTool(),     # 继承 budget.py
            DesignOptimizerTool(),       # 继承 optimizer.py
        ]

    async def execute(self, task: Task) -> AgentResult:
        task_type = task.params.get('type')

        if task_type == 'parse':
            return await self._parse_blueprint(task)
        elif task_type == 'analyze':
            return await self._analyze_blueprint(task)
        elif task_type == 'extract_quantities':
            return await self._extract_quantities(task)
        elif task_type == 'optimize':
            return await self._optimize_design(task)
```

**输出规范：**
```python
class TechRdOutput:
    blueprint_type: str              # '建筑'/'结构'/'机电'等
    analysis_result: dict            # 解析结果
    quantities: List[QuantityItem]   # 工程量清单
    suggestions: List[DesignSuggestion]  # 优化建议
    confidence: float
```

### 3.5 EngineeringDeliveryAgent（工程交付Agent）

**Agent ID：** `engineering_delivery`  
**名称：** 工程交付中心  
**定位：** 项目执行与交付管理

```python
class EngineeringDeliveryAgent(BaseAgent):
    """
    EngineeringDeliveryAgent - 工程交付Agent

    核心能力：
    1. 项目计划制定（甘特图）
    2. 施工方案生成
    3. 进度追踪与预警
    4. 质量检查清单
    5. 竣工资料整理
    6. 技术核定单处理

    工具集：
    - PlanGeneratorTool: 计划生成
    - ConstructionSchemeGenerator: 施工方案生成
    - ProgressTrackerTool: 进度追踪
    - QualityChecklistGenerator: 质量清单
    - CompletionDocsGenerator: 竣工资料
    - TechChangeHandler: 技术核定单
    """

    AGENT_ID = 'engineering_delivery'
    NAME = '工程交付中心'

    async def execute(self, task: Task) -> AgentResult:
        task_type = task.params.get('type')

        if task_type == 'generate_plan':
            return await self._generate_project_plan(task)
        elif task_type == 'generate_scheme':
            return await self._generate_construction_scheme(task)
        elif task_type == 'track_progress':
            return await self._track_progress(task)
        elif task_type == 'generate_checklist':
            return await self._generate_quality_checklist(task)
        elif task_type == 'organize_completion':
            return await self._organize_completion_docs(task)
```

### 3.6 CostBenefitAgent（成本效益Agent）

**Agent ID：** `cost_benefit`  
**名称：** 成本效益中心  
**定位：** 工程造价与经济效益分析

```python
class CostBenefitAgent(BaseAgent):
    """
    CostBenefitAgent - 成本效益Agent

    核心能力：
    1. 工程量计算（基于图纸）
    2. 材料价格智能询价
    3. 预算/概算/结算生成
    4. 变更签证管理
    5. 成本对比分析
    6. 投资回报分析

    工具集：
    - QuantityCalculatorTool: 工程量计算
    - PriceInquiryTool: 价格询价
    - BudgetGeneratorTool: 预算生成
    - ChangeTrackerTool: 变更追踪
    - CostAnalyzerTool: 成本分析
    - ROIAnalyzerTool: ROI分析
    """

    AGENT_ID = 'cost_benefit'
    NAME = '成本效益中心'

    async def execute(self, task: Task) -> AgentResult:
        task_type = task.params.get('type')

        if task_type == 'calculate_quantities':
            return await self._calculate_quantities(task)
        elif task_type == 'generate_budget':
            return await self._generate_budget(task)
        elif task_type == 'track_changes':
            return await self._track_changes(task)
        elif task_type == 'cost_analysis':
            return await self._cost_analysis(task)
        elif task_type == 'roi_analysis':
            return await self._roi_analysis(task)
```

**输出规范：**
```python
class CostBenefitOutput:
    budget: BudgetDocument
    change_orders: List[ChangeOrder]
    cost_comparison: CostComparison  # 目标 vs 实际
    roi_report: ROIReport
    confidence: float
```

### 3.7 CustomerServiceAgent（客户服务Agent）

**Agent ID：** `customer_service`  
**名称：** 客户服务服务中心  
**定位：** 客户支持与关系维护

```python
class CustomerServiceAgent(BaseAgent):
    """
    CustomerServiceAgent - 客户服务Agent

    核心能力：
    1. 智能答疑（FAQ知识库）
    2. 工单管理
    3. 客户回访计划
    4. 满意度分析
    5. 需求建议收集
    6. 培训材料生成

    工具集：
    - FAQBotTool: 智能答疑
    - TicketManagerTool: 工单管理
    - FollowupPlannerTool: 回访计划
    - SatisfactionAnalyzerTool: 满意度分析
    - TrainingMaterialGenerator: 培训材料
    """

    AGENT_ID = 'customer_service'
    NAME = '客户服务中心'

    async def execute(self, task: Task) -> AgentResult:
        task_type = task.params.get('type')

        if task_type == 'answer':
            return await self._answer_faq(task)
        elif task_type == 'manage_ticket':
            return await self._manage_ticket(task)
        elif task_type == 'plan_followup':
            return await self._plan_followup(task)
        elif task_type == 'generate_training':
            return await self._generate_training(task)
```

---

## 四、Agent间通信协议

### 4.1 Main-Agent → Sub-Agent 消息格式

```python
class AgentTask:
    """分发给Sub-Agent的任务"""
    task_id: str
    agent_id: str                    # 目标Agent
    task_type: str                   # 任务类型
    params: dict                     # 任务参数
    context: dict                    # 上下文（项目信息、用户偏好等）
    constraints: dict                # 约束条件（时间、质量标准等）
    callback_url: str                # 结果回调地址
```

### 4.2 Sub-Agent → Main-Agent 结果格式

```python
class AgentResult:
    """Sub-Agent返回结果"""
    task_id: str
    agent_id: str
    status: Literal['success', 'partial', 'failed']
    output: Any                     # Agent特定输出
    confidence: float               # 置信度 0-1
    execution_time: float           # 执行时间（秒）
    errors: List[str]               # 错误信息
    suggestions: List[str]          # 建议（可选项）
    metadata: dict                   # 元数据
```

### 4.3 扁平化通信流程

```
Boss: "帮我审查这个项目的合规性并生成预算"

         ┌─────────────────────────────────────┐
         │            Main-Agent                │
         │  意图: review_compliance + generate_budget │
         └──────┬──────────────────────────────┘
                │
    dispatch ──┼──→ SafetyComplianceAgent
                │         ↓
                │    [审查图纸+合规检查]
                │         ↓
                └──────→ CostBenefitAgent
                         ↓
                    [计算工程量+生成预算]

         ┌─────────────────────────────────────┐
         │  整合结果 → 质量检查 → 输出报告     │
         └─────────────────────────────────────┘
```

---

## 五、执行状态机

### 5.1 Main-Agent状态机

```
IDLE → UNDERSTANDING → PLANNING → DISPATCHING → INTEGRATING → DELIVERING → COMPLETE
                    ↓            ↓
                  ERROR        ERROR
                    ↓            ↓
                  RETRY        RETRY
                    ↓            ↓
                (max 3)      (max 3)
                    ↓            ↓
                  FAIL         FAIL
```

### 5.2 Sub-Agent状态机

```
RECEIVED → EXECUTING → VALIDATING → COMPLETE
              ↓              ↓
            ERROR          ERROR
              ↓              ↓
            RETRY          RETRY
              ↓              ↓
          (max 2)        (max 2)
              ↓              ↓
            FAILED         FAILED
```

---

## 六、工具层设计（Tool Layer）

### 6.1 共享工具vs专属工具

| 工具 | 类型 | 使用Agent |
|------|------|-----------|
| BlueprintParserTool | 共享 | TechRd, SafetyCompliance, CostBenefit |
| SpecsMatcherTool | 共享 | SafetyCompliance, TechRd |
| DocumentGeneratorTool | 共享 | 所有Agent |
| WebSearchTool | 共享 | MarketSales, TechRd |
| ComplianceCheckerTool | 专属 | SafetyCompliance |
| BudgetGeneratorTool | 专属 | CostBenefit |
| ProposalBuilderTool | 专属 | MarketSales |
| TicketManagerTool | 专属 | CustomerService |

### 6.2 Tool基类

```python
class BaseTool(ABC):
    """工具基类"""

    name: str
    description: str
    input_schema: dict
    output_schema: dict

    @abstractmethod
    async def execute(self, params: dict, context: dict) -> ToolResult:
        pass

    async def validate(self, params: dict) -> bool:
        """验证输入参数"""
        pass
```

---

## 七、实施优先级

### Phase 1：骨架验证（1-2周）

```
Main-Agent骨架：
- NLU模块（规则版）
- 任务规划器（规则版）
- Agent调度器（支持串行+并行）
- 质量控制器（基础版）

TechRdAgent（继承blueprint-ai）：
- BlueprintParserTool
- TypeClassifierTool
- 基础分析能力

目标：输入"分析这张图纸"，Agent自动完成解析+识别+输出
```

### Phase 2：多Agent扩展（2-3周）

```
SafetyComplianceAgent（继承review.py）
EngineeringDeliveryAgent
CostBenefitAgent
```

### Phase 3：全能力上线（2-3周）

```
MarketSalesAgent
CustomerServiceAgent
记忆系统（ChromaDB）
LLM驱动的任务规划
```

---

## 八、验收标准

每个Agent上线前必须满足：

1. ✅ 独立可运行（给定任务，返回结构化结果）
2. ✅ 置信度评分（输出附带0-1置信度）
3. ✅ 质量控制（Main-Agent检查，不合格打回）
4. ✅ 错误处理（失败有清晰错误信息，不崩溃）
5. ✅ 工具文档（每个tool有清晰input/output schema）
6. ✅ 单元测试（每个Agent有≥3个测试用例）

---

## 文档更新记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-05-16 | v1.0 | 初始版本，完成Main-Agent + 6个Sub-Agent详细设计 |