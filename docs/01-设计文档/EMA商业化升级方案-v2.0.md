# 🚀 EMA 商业化升级方案 v2.0

**编制时间**: 2026-05-18
**编制者**: GDP 影子
**版本**: v2.0（商业化架构设计）
**状态**: 方案阶段，待刚哥审批

---

## 目录

1. [现状诊断](#一现状诊断)
2. [商业化产品定位](#二商业化产品定位)
3. [多租户架构与数据隔离](#三多租户架构与数据隔离)
4. [多用户并发与弹性伸缩](#四多用户并发与弹性伸缩)
5. [用户引导与工作流融合](#五用户引导与工作流融合)
6. [Sub-Agent 主动智能服务](#六sub-agent-主动智能服务)
7. [知识库实时更新体系](#七知识库实时更新体系)
8. [计费与支付体系](#八计费与支付体系)
9. [实施路线图](#九实施路线图)
10. [风险与对策](#十风险与对策)

---

## 一、现状诊断

### 1.1 已有能力（✅）

| 能力 | 状态 | 说明 |
|------|------|------|
| Main-Agent 框架 | ✅ | 意图分类 / 任务规划 / 编排调度 / 结果整合 |
| 6个 Sub-Agent | ✅ | 技术/安全/市场/交付/成本/客服 |
| 图纸解析 | ✅ | DWG/DXF/PDF 全支持 |
| 国标审图 | ✅ | 15条规则 |
| 生命周期文档 | ✅ | SOP/MOP/EOP/LCC |
| 工程量/预算 | ✅ | 继承 blueprint-ai |
| ChromaDB 记忆 | ✅ | 懒加载，后台存储 |
| UI 多Agent切换 | ✅ | 侧边栏切换 + 模型选择器 |

### 1.2 缺失能力（❌）

| 能力 | 状态 | 为什么重要 |
|------|------|----------|
| **多租户数据隔离** | ❌ | 所有用户数据混在一起，没有隔离 |
| **JWT 认证体系** | ❌ | `user_id="guest"` 硬编码，无鉴权 |
| **并发处理** | ❌ | 单进程同步阻塞，多用户同时操作会卡死 |
| **用户引导** | ❌ | 欢迎页简陋，无新手任务流 |
| **Sub-Agent 主动服务** | ❌ | Agent 只会被动响应，不会主动通知 |
| **知识库更新** | ❌ | 国标库本地静态，无实时同步 |
| **计费/支付** | ❌ | 完全没有收费体系 |
| **项目管理** | ❌ | 无项目创建/编辑/共享 |
| **移动端支持** | ❌ | 仅桌面 Web UI |
| **审计日志** | ❌ | 无法追溯用户操作 |

### 1.3 一句话总结

> **EMA 现在是"单机玩具"——一个好大脑，但没有身体（多租户架构）、没有血液（支付体系）、没有手脚（主动服务/移动端）。**

---

## 二、商业化产品定位

### 2.1 产品愿景

```
EMA = 工程管理界的 GitHub Copilot + Notion AI + Monday.com Agent

从"图纸AI工具"升级为"工程企业AI随身助手"
```

### 2.2 目标用户画像

| 角色 | 场景 | 核心需求 |
|------|------|---------|
| **设计工程师** | 画图 → 审图 → 改图 | 图纸快速审图 + AI 辅助设计 |
| **项目经理** | 进度管控 → 文档生成 | 自动生成施工方案/技术交底 |
| **造价工程师** | 算量 → 报价 → 结算 | 工程量提取 + 预算自动生成 |
| **安全总监** | 安全检查 → 合规 | 消防/结构合规自动审查 |
| **企业老板** | 全局把控 | 多项目 Dashboard + 成本分析 |
| **审图单位** | 图纸审查 | 批量审图 + 报告自动生成 |

### 2.3 产品形态

| 形态 | 交付方式 | 用户群体 |
|------|---------|---------|
| **SaaS Web** | 浏览器访问（核心形态） | 所有用户 |
| **移动端** | PWA / 小程序 | 项目经理/老板随时查看 |
| **企业私有部署** | Docker Compose / K8s | 安全要求高的设计院 |
| **API 服务** | REST API + SDK | 第三方系统集成 |

### 2.4 竞品差异化

| 对比维度 | 传统软件（广联达/品茗） | EMA |
|---------|---------------------|-----|
| 交互方式 | 菜单点击 | **自然语言对话** |
| 学习成本 | 高（培训数周） | **零（说人话就行）** |
| 智能审图 | 规则匹配 | **AI 推理 + 国标规则** |
| 多项目协同 | 单机 | **云端多项目实时协作** |
| 主动服务 | 无 | **项目异常自动预警** |
| 性价比 | 年费数万/套 | **按需付费，¥99/月起步** |

---

## 三、多租户架构与数据隔离

### 3.1 隔离策略：逐级递进

```
Level 1 — 代码层隔离
  ↓
Level 2 — 数据库层隔离（PostgreSQL RLS）
  ↓
Level 3 — 文件系统层隔离
  ↓
Level 4 — AI 推理层隔离（独立 Sandbox）
```

### 3.2 Level 1: 代码层隔离

```python
# 每条 API 请求都注入 tenant_id
class TenantMiddleware:
    """从 JWT Token 解析 tenant_id，注入到 request.state"""

    async def __call__(self, request, call_next):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        request.state.tenant_id = payload["tenant_id"]  # 企业ID
        request.state.user_id = payload["user_id"]      # 用户ID
        request.state.role = payload.get("role", "viewer")
        return await call_next(request)

# 所有数据库查询自动过滤
def get_db_session(tenant_id: str) -> Session:
    """创建数据库会话时自动注入 tenant_id"""
    session = SessionLocal()
    session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))
    return session
```

### 3.3 Level 2: PostgreSQL Row-Level Security (RLS)

```sql
-- 开启 RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;

-- 自动过滤策略
CREATE POLICY tenant_isolation ON projects
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id'))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id'));

CREATE POLICY user_isolation ON conversations
    FOR ALL
    USING (user_id = current_setting('app.current_user_id'));
```

**效果**:
- 数据库层面强制隔离，即使代码 bug 也无法跨租户访问数据
- PostgreSQL RLS 是行业标准（GitLab、Notion、Linear 都在用）

### 3.4 Level 3: 文件系统隔离

```
output/
├── tenant_abc123/           ← 企业A
│   ├── projects/
│   │   ├── proj_001/        ← 项目1
│   │   │   ├── uploads/     ← 上传的图纸
│   │   │   ├── analysis/    ← AI分析结果
│   │   │   └── exports/     ← 导出的文档
│   │   └── proj_002/
│   └── shared/              ← 企业内共享文件
├── tenant_def456/           ← 企业B
│   └── ...
└── _system/                 ← 系统级文件
```

```python
def get_tenant_dir(tenant_id: str) -> Path:
    """文件路径强制隔离"""
    base = Path(os.environ.get("DATA_DIR", "/data"))
    tenant_dir = (base / "output" / tenant_id).resolve()
    # 安全检查：确保路径在允许范围内
    if not str(tenant_dir).startswith(str(base / "output")):
        raise SecurityError("路径越界")
    return tenant_dir
```

### 3.5 Level 4: AI 推理层隔离

```python
class SandboxedAgentExecutor:
    """
    每个用户请求在独立的 Sandbox 中执行
    避免 user A 的代码/数据污染 user B
    """

    def __init__(self, tenant_id: str, user_id: str):
        self.sandbox = DockerSandbox(
            image="ema-agent-sandbox:latest",
            volumes={
                f"/data/output/{tenant_id}": "/workspace",
            },
            memory_limit="2g",
            cpu_limit=1,
            network="none",  # 无网络访问
            timeout=300,     # 5分钟超时
        )

    async def execute(self, task: Task) -> AgentResult:
        async with self.sandbox:
            return await self.sandbox.run(task)
```

### 3.6 多租户架构全景图

```
                          ┌─────────────────────┐
                          │   Nginx / Traefik   │
                          │   (TLS 终止 + 限流)   │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   FastAPI Gateway   │
                          │   JWT Auth + RBAC   │
                          └──────────┬──────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
     │  Tenant A       │   │  Tenant B       │   │  Tenant C       │
     │  (RLS 过滤)      │   │  (RLS 过滤)      │   │  (RLS 过滤)      │
     │  /data/A/       │   │  /data/B/       │   │  /data/C/       │
     └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
              │                      │                      │
              └──────────────────────┼──────────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   PostgreSQL 15+    │
                          │   (RLS + 分表)       │
                          └─────────────────────┘
```

---

## 四、多用户并发与弹性伸缩

### 4.1 问题分析

当前 EMA 是单进程 FastAPI，同步执行 Agent 任务。10 个用户同时上传图纸，后面 9 个会卡死。

### 4.2 解决方案：任务队列 + Worker 池

```
用户请求 → FastAPI (接收) → Redis Queue (排队) → Worker Pool (执行) → 结果返回
```

#### 技术选型

| 组件 | 技术 | 原因 |
|------|------|------|
| 消息队列 | **Redis Streams** 或 **RabbitMQ** | 轻量级，无需额外运维 |
| 任务调度 | **Celery** 或 **arq** (async) | Python 生态成熟 |
| Worker 池 | **uvicorn workers** (--workers=4) | 多进程并发 |
| GPU 推理 | **vLLM** + 请求队列 | GPU 高效批处理 |
| 服务发现 | Kubernetes Service | 自动负载均衡 |

#### 实现方案

```python
# 1. FastAPI 接收请求 → 入队
@app.post("/api/v1/main/chat")
async def main_agent_chat(req: AgentChatRequest, tenant=Depends(get_tenant)):
    # 入队（非阻塞）
    task_id = await task_queue.enqueue(
        "agent_tasks",
        {
            "message": req.message,
            "tenant_id": tenant.id,
            "user_id": tenant.user_id,
            "model": req.model,
        }
    )
    return {"task_id": task_id, "status": "queued"}

# 2. Worker 消费队列 → 执行
@worker.task("agent_tasks")
async def execute_agent_task(payload: dict):
    main_agent = get_main_agent()
    result = await main_agent._chat(
        params={"message": payload["message"]},
        context={"tenant_id": payload["tenant_id"]}
    )
    return result

# 3. 前端轮询 / WebSocket 获取结果
@app.websocket("/ws/tasks/{task_id}")
async def task_websocket(ws: WebSocket, task_id: str):
    await ws.accept()
    while True:
        result = await get_task_result(task_id)
        if result:
            await ws.send_json(result)
            break
        await asyncio.sleep(1)
```

#### 伸缩策略

| 层级 | 伸缩方式 | 触发条件 |
|------|---------|---------|
| API Gateway | K8s HPA | CPU > 70% 或 请求队列深度 > 100 |
| Worker Pool | K8s HPA | 队列积压 > 50 |
| PostgreSQL | 连接池 (PgBouncer) | 连接数 > 50 |
| Redis | 主从 + Sentinel | 内存 > 80% |
| vLLM GPU | 独占 Pod + 请求排队 | max_batch_size=32 |

#### 最小部署配置

```yaml
# docker-compose.yml (10-50 用户规模)
services:
  api:
    image: ema-api:latest
    deploy:
      replicas: 2
    environment:
      - WORKERS=4

  worker:
    image: ema-worker:latest
    deploy:
      replicas: 3

  redis:
    image: redis:7-alpine

  postgres:
    image: pgvector/pgvector:pg16
    # pgvector 支持向量搜索，可替代 ChromaDB
```

---

## 五、用户引导与工作流融合

### 5.1 核心理念

> **不要求用户"学习软件"——EMA 主动适配用户的工作方式**

### 5.2 分层引导体系

```
新用户注册
  │
  ├── Step 1: 角色选择（你是谁？）
  │   ├── 设计工程师 → 引导上传图纸 + 审图
  │   ├── 项目经理 → 引导创建项目 + SOP
  │   ├── 造价工程师 → 引导算量 + 预算
  │   └── 企业老板 → 引导 Dashboard
  │
  ├── Step 2: 首次任务（5分钟拿到第一个结果）
  │   └── "上传你的第一张图纸，我来帮你分析" → 即时反馈
  │
  ├── Step 3: 工作流模板库（常用流程一键启动）
  │   ├── "图纸审图" → 上传图纸 → 自动审图 → 导出报告
  │   ├── "项目启动" → 创建项目 → 导入图纸 → 生成SOP → 生成预算
  │   └── "投标辅助" → 图纸分析 → 工程量 → 商务报价
  │
  ├── Step 4: 智能化运营（EMA 记住你的习惯）
  │   ├── "你上次做的是结构审图，需要继续吗？"
  │   └── "你每周五生成周报，要我现在生成吗？"
  │
  └── Step 5: 团队协作（邀请同事）
      └── "你的团队有3人，开通团队版解锁协作功能"
```

### 5.3 企业工作流融合

```python
class WorkflowTemplate:
    """
    预定义工作流模板，适配不同企业角色

    用户可以用自然语言描述，也可以用模板一键启动
    """

    TEMPLATES = {
        "图纸审图流程": {
            "steps": [
                {"agent": "tech_rd", "task": "parse", "prompt": "解析上传的图纸"},
                {"agent": "safety_compliance", "task": "review", "prompt": "国标合规审图"},
                {"agent": "result_compiler", "task": "compile", "prompt": "生成审图报告"},
            ],
            "estimated_time": "3分钟",
            "icon": "🔍",
        },
        "项目启动流程": {
            "steps": [
                {"agent": "tech_rd", "task": "full_analysis"},
                {"agent": "cost_benefit", "task": "budget"},
                {"agent": "engineering_delivery", "task": "generate_sop"},
                {"agent": "result_compiler", "task": "compile"},
            ],
            "estimated_time": "8分钟",
            "icon": "🚀",
        },
        "投标辅助流程": {
            "steps": [
                {"agent": "tech_rd", "task": "extract_quantities"},
                {"agent": "cost_benefit", "task": "generate_budget"},
                {"agent": "market_sales", "task": "tender_doc"},
            ],
            "estimated_time": "5分钟",
            "icon": "📋",
        },
    }
```

### 5.4 持续吸引机制

| 机制 | 实现方式 | 效果 |
|------|---------|------|
| **每日摘要** | 早 8:00 推送"今日待办" | 打开率 60%+ |
| **项目里程碑提醒** | 节点前 3 天自动预警 | 减少延期 |
| **成本异常检测** | 预算超 10% 自动通知 | 及时止损 |
| **周报自动生成** | 每周五 17:00 生成并推送 | 节省 2h/周 |
| **知识推荐** | 根据最近项目推荐相关规范 | 持续学习 |
| **成就系统** | "你已完成 100 次审图！" | 粘性提升 |

---

## 六、Sub-Agent 主动智能服务

### 6.1 核心转变

```
当前:  用户 → 提问 → EMA 响应  (被动)
目标:  事件 → EMA 分析 → 主动通知用户  (主动)
```

### 6.2 事件驱动架构

```python
class EMAEventBus:
    """
    EMA 事件总线：所有 Sub-Agent 通过事件总线通信

    事件类型：
    - project.created → 新项目创建
    - blueprint.uploaded → 图纸上传
    - review.issues_found → 审图发现问题
    - budget.over_budget → 预算超标
    - deadline.approaching → 节点临近
    - spec.updated → 规范更新
    """

    def __init__(self):
        self.subscribers: Dict[str, List[callable]] = {}

    def subscribe(self, event_type: str, handler: callable):
        self.subscribers.setdefault(event_type, []).append(handler)

    async def publish(self, event_type: str, event_data: dict):
        for handler in self.subscribers.get(event_type, []):
            await handler(event_data)

# ──── 主动服务示例 ────

async def on_blueprint_uploaded(event: dict):
    """图纸上传 → 自动触发完整分析"""
    tech_rd = get_agent("tech_rd")
    result = await tech_rd.full_analysis(event["file_path"])
    await notify_user(event["user_id"], "图纸分析完成", result)

async def on_budget_overrun(event: dict):
    """预算超标 10% → 自动通知项目经理"""
    cost_agent = get_agent("cost_benefit")
    analysis = await cost_agent.cost_analysis(event["project_id"])
    if analysis["over_budget_percent"] > 10:
        await notify_user(
            event["project_id"],
            f"⚠️ 项目 {event['project_name']} 预算超标 {analysis['over_budget_percent']}%",
            analysis
        )

async def on_spec_updated(event: dict):
    """国标更新 → 检查所有受影响的在审项目"""
    safety_agent = get_agent("safety_compliance")
    affected_projects = await safety_agent.find_affected_projects(event["spec_id"])
    for project in affected_projects:
        await notify_user(
            project["owner"],
            f"📋 新国标 {event['spec_name']} 发布，可能影响你的项目 {project['name']}"
        )
```

### 6.3 Sub-Agent 主动服务清单

| Sub-Agent | 主动服务 | 触发条件 |
|-----------|---------|---------|
| **SafetyComplianceAgent** | 新国标影响评估 | 标准库更新 |
| **MarketSalesAgent** | 投标机会提醒 | 招标公告爬取 |
| **EngineeringDeliveryAgent** | 进度异常预警 | 节点临近未完成 |
| **CostBenefitAgent** | 成本超标警示 | 实际 > 预算 10% |
| **CustomerServiceAgent** | 回访自动安排 | 项目完工后 30 天 |
| **TechRdAgent** | 图纸变更影响分析 | 图纸版本更新 |

### 6.4 调度器实现

```python
class ProactiveScheduler:
    """
    主动服务调度器

    每个 Sub-Agent 注册定时任务或事件监听
    """

    def __init__(self):
        self.cron_jobs = {}

    def register_agent_schedule(self, agent_id: str, cron_expr: str, task: callable):
        """
        注册 Agent 的定时任务

        示例：
        - 每天 8:00: CostBenefitAgent 扫描所有项目预算
        - 每小时: SafetyComplianceAgent 检查是否有新规范发布
        - 每周五 17:00: EngineeringDeliveryAgent 生成周报
        """
        self.cron_jobs[agent_id] = {
            "schedule": cron_expr,
            "task": task,
        }

    async def run_scheduled(self):
        """执行所有到期的定时任务"""
        for agent_id, job in self.cron_jobs.items():
            if self._is_due(job["schedule"]):
                try:
                    result = await job["task"]()
                    if result.get("notify"):
                        await self._send_notification(agent_id, result)
                except Exception as e:
                    logger.error(f"Agent {agent_id} 定时任务失败: {e}")
```

---

## 七、知识库实时更新体系

### 7.1 知识库架构

```
EMA 知识库
├── 国家标准库 (GB)
│   ├── 建筑规范 (GB 50016 等)
│   ├── 消防规范
│   ├── 结构规范
│   ├── 给排水规范
│   └── 电气规范
├── 行业标准库
│   ├── 勘察设计标准
│   ├── 造价标准
│   └── 施工标准
├── 企业知识库
│   ├── 企业模板
│   ├── 历史项目数据
│   └── 企业标准做法
└── 案例库
    ├── 优秀项目案例
    └── 常见问题 & 解决方案
```

### 7.2 实时更新机制

```python
class KnowledgeBaseManager:
    """
    知识库管理器

    更新来源：
    1. 国家标准网 (std.samr.gov.cn) — 自动爬取
    2. 住建部公告 — 自动爬取
    3. 行业标准网站 — 定时同步
    4. 用户反馈 — 人工审核后加入
    """

    UPDATE_SOURCES = {
        "国家标准全文公开系统": {
            "url": "https://openstd.samr.gov.cn",
            "frequency": "daily",
            "parser": "std_samr_parser",
        },
        "住建部标准定额": {
            "url": "https://www.mohurd.gov.cn/gongkai/zhengce/",
            "frequency": "daily",
            "parser": "mohurd_parser",
        },
        "工程建设标准化信息网": {
            "url": "http://www.cecs.org.cn",
            "frequency": "weekly",
            "parser": "cecs_parser",
        },
    }

    async def check_updates(self):
        """
        定时检查各数据源，发现新标准自动入库

        流程：
        1. 爬取最新公告
        2. AI 提取标准编号、名称、实施日期
        3. 自动下载标准全文
        4. 向量化存入 ChromaDB
        5. 通知受影响的 Sub-Agent
        """
        for source_name, config in self.UPDATE_SOURCES.items():
            try:
                new_items = await self._fetch_source(source_name, config)
                for item in new_items:
                    existing = await self._find_existing(item["spec_id"])
                    if not existing:
                        await self._ingest_spec(item)
                        await event_bus.publish("spec.updated", item)
            except Exception as e:
                logger.error(f"更新失败: {source_name} - {e}")

    async def _ingest_spec(self, spec: dict):
        """将新标准入库"""
        # 1. 下载并解析 PDF
        pdf_path = await self._download_pdf(spec["pdf_url"])

        # 2. AI 提取关键条款和参数
        extracted = await spec_extractor.extract(pdf_path)

        # 3. 向量化存入 ChromaDB
        chroma_db.add_knowledge(
            doc_id=spec["spec_id"],
            title=spec["title"],
            content=extracted["full_text"],
            metadata={
                "spec_number": spec["spec_number"],
                "effective_date": spec["effective_date"],
                "category": spec["category"],
                "keywords": extracted["keywords"],
            }
        )

        # 4. 建立条款级别的索引（可以精确引用）
        for clause in extracted["clauses"]:
            chroma_db.add_knowledge(
                doc_id=f"{spec['spec_id']}_{clause['number']}",
                title=f"{spec['title']} §{clause['number']}",
                content=clause["text"],
                metadata={"parent_spec": spec["spec_id"]}
            )
```

### 7.3 智能规范应用

```python
class SpecAgent(SafetyComplianceAgent):
    """
    规范智能应用 Agent

    在审图时自动匹配最新规范，而非硬编码规则
    """

    async def smart_review(self, blueprint_data: dict, project_type: str):
        # 1. 从知识库检索适用的规范
        applicable_specs = await chroma_db.search_knowledge(
            query=f"{project_type} 设计规范 强制性条文",
            limit=20,
            filter={"effective": True}
        )

        # 2. 对每条规范检查图纸的符合性
        issues = []
        for spec in applicable_specs:
            # AI 逐条对比图纸与规范
            clause_check = await llm.check_compliance(
                blueprint_context=blueprint_data,
                spec_clause=spec["content"],
            )
            if not clause_check["compliant"]:
                issues.append({
                    "spec_id": spec["doc_id"],
                    "clause": spec["title"],
                    "severity": "严重" if clause_check.get("mandatory") else "警告",
                    "description": clause_check["finding"],
                    "suggestion": clause_check["suggestion"],
                })

        return issues
```

---

## 八、计费与支付体系

### 8.1 定价策略

```
┌─────────────────────────────────────────────────────────────┐
│  版本               价格              适合                │
├─────────────────────────────────────────────────────────────┤
│  免费版             ¥0/月             个人试用              │
│  ├── 3个项目                                             │
│  ├── 10次AI分析/月                                        │
│  ├── 基础的审图规则                                       │
│  └── 输出带水印                                           │
│                                                             │
│  专业版             ¥99/月            个人工程师            │
│  ├── 无限项目                                             │
│  ├── 100次AI分析/月                                        │
│  ├── 全部Sub-Agent可用                                     │
│  ├── 图纸版本对比                                         │
│  ├── 企业知识库（只读）                                    │
│  └── 无水印输出                                           │
│                                                             │
│  团队版             ¥499/月            设计团队/小企业       │
│  ├── 5个用户席位                                         │
│  ├── 500次AI分析/月                                        │
│  ├── 团队协作（共享项目）                                  │
│  ├── 自定义工作流                                         │
│  ├── 企业知识库（读写）                                    │
│  ├── 优先客服支持                                         │
│  └── API 访问权限                                         │
│                                                             │
│  企业版             ¥1999/月以上        设计院/大型企业       │
│  ├── 无限用户                                             │
│  ├── 无限AI分析                                           │
│  ├── 私有部署可选                                         │
│  ├── SSO 集成                                             │
│  ├── 专属客服 + 定制Agent                                  │
│  ├── SLA 99.9% 可用性                                     │
│  ├── 审计日志 + 合规报告                                   │
│  └── 数据导出 API                                         │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 用量计费（弹性扩展）

```python
class UsageTracker:
    """
    用量追踪器

    计费维度：
    1. AI 分析次数（每次调用 LLM / 审图）
    2. 图纸处理页数（PDF/DWG 页数）
    3. 存储空间（上传文件总量）
    4. API 调用次数（对外 API）
    5. 用户席位数量
    """

    METRICS = {
        "ai_analysis": {"unit": "次", "free_limit": 10, "overage_price": 1.0},
        "blueprint_pages": {"unit": "页", "free_limit": 50, "overage_price": 0.5},
        "storage_mb": {"unit": "MB", "free_limit": 500, "overage_price": 0.01},
        "api_calls": {"unit": "次", "free_limit": 1000, "overage_price": 0.001},
    }

    async def track(self, tenant_id: str, metric: str, quantity: float):
        """追踪用量，超出限额时通知"""
        redis_key = f"usage:{tenant_id}:{metric}:{current_billing_period()}"
        current = await redis_client.incrbyfloat(redis_key, quantity)

        limit = self.METRICS[metric]["free_limit"]
        if current > limit * 1.2:  # 超出 20% 暂停
            raise QuotaExceededError(f"{metric} 已超出限额")
        elif current > limit * 0.9:  # 接近限额 90% 提醒
            await notify_user(tenant_id, f"⚠️ {metric} 已使用 {current}/{limit}")
```

### 8.3 支付集成方案

```
                    ┌─────────────┐
                    │  EMA 平台    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼──────┐ ┌──▼──────┐ ┌───▼────────┐
    │  Stripe        │ │LemonSqueezy│ │ Ping++     │
    │  (海外支付)     │ │(全球MoR)  │ │ (中国聚合)  │
    │                │ │          │ │            │
    │  • Visa/MC    │ │ • Stripe │ │ • 微信支付  │
    │  • PayPal     │ │ • PayPal │ │ • 支付宝    │
    │  • Alipay+    │ │ • 发票   │ │ • 银联      │
    │  • WeChat Pay │ │ • 税务   │ │ • 对公转账   │
    └───────────────┘ └──────────┘ └────────────┘
```

#### 推荐方案：双通道支付

| 用户类型 | 支付方案 | 集成方式 |
|---------|---------|---------|
| **国内用户** | **Ping++** (聚合支付) | 微信/支付宝/银联/对公转账 |
| **海外用户** | **Stripe** (国际支付) | Visa/MC/PayPal/Alipay+ |
| **开票用户** | **LemonSqueezy** (MoR) | 自动处理增值税/电子发票 |

```python
class PaymentService:
    """
    支付服务抽象层

    支持多种支付方式，统一接口
    """

    PROVIDERS = {
        "stripe": StripeProvider,
        "pingpp": PingPlusPlusProvider,
        "lemonsqueezy": LemonSqueezyProvider,
    }

    def __init__(self, provider: str = "pingpp"):
        self.provider = self.PROVIDERS[provider]()

    async def create_checkout_session(
        self,
        tenant_id: str,
        plan_id: str,
        payment_method: str,  # "wechat" / "alipay" / "unionpay" / "card"
        success_url: str,
        cancel_url: str,
    ) -> dict:
        """
        创建支付订单
        """
        plan = await self._get_plan(plan_id)

        checkout = await self.provider.create_payment(
            amount=plan["price"],
            currency="CNY",
            description=f"EMA {plan['name']}",
            metadata={
                "tenant_id": tenant_id,
                "plan_id": plan_id,
            },
            payment_method=payment_method,
            return_url=success_url,
        )
        return checkout  # 返回支付二维码URL或跳转链接

    async def handle_webhook(self, payload: dict, signature: str) -> dict:
        """
        处理支付回调
        """
        event = await self.provider.parse_webhook(payload, signature)

        if event["type"] == "payment.succeeded":
            await self._activate_subscription(
                tenant_id=event["metadata"]["tenant_id"],
                plan_id=event["metadata"]["plan_id"],
                payment_id=event["payment_id"],
                amount=event["amount"],
            )

        return {"status": "ok"}
```

#### 支付流程图

```
用户选择套餐 → 选择支付方式 → 生成支付订单 → 扫码/跳转支付
                                            │
                    ┌───────────────────────┘
                    │
          ┌─────────▼──────────┐
          │  支付平台回调       │
          │  Webhook 通知 EMA  │
          └─────────┬──────────┘
                    │
          ┌─────────▼──────────┐
          │  EMA 激活订阅      │
          │  - 更新 subscription│
          │  - 发送欢迎邮件     │
          │  - 开通对应功能     │
          └────────────────────┘
```

### 8.4 刚哥的收益管理

```python
class RevenueDashboard:
    """
    刚哥的收益面板

    实时查看：
    - 今日/本月/总营收
    - 各套餐订阅数
    - 用户增长曲线
    - 流失率预警
    - 单个用户价值 (LTV)
    """

    async def get_dashboard(self, period: str = "month") -> dict:
        return {
            "mrr": 0,  # 月经常性收入
            "arr": 0,  # 年经常性收入
            "active_subscribers": 0,
            "churn_rate": 0,
            "new_signups": 0,
            "revenue_by_plan": {},
            "revenue_by_channel": {},  # 微信/支付宝/对公/海外
        }
```

---

## 九、实施路线图

### Phase 4: 多租户基础设施（2周）

```
Week 1-2: 认证 + 隔离 + 项目系统
├── JWT 认证体系 (注册/登录/密码重置)
├── 多租户 RLS (PostgreSQL RLS 策略)
├── 文件系统隔离 (tenant_id 目录)
├── 项目管理 (创建/编辑/删除/归档)
└── RBAC 权限系统 (admin/editor/viewer)
```

### Phase 5: 并发与弹性（2周）

```
Week 3-4: 队列 + Worker + K8s
├── Redis 任务队列 (arq)
├── Worker Pool (Celery 或 arq workers)
├── WebSocket 实时推送结果
├── Docker 部署脚本 (docker-compose + K8s)
└── 负载测试 (Locust 1000 并发)
```

### Phase 6: 商业化上线（3周）

```
Week 5-7: 支付 + 引导 + 知识库
├── Ping++ 支付集成 (微信/支付宝/银联)
├── Stripe 支付集成 (海外)
├── 定价页 + 套餐切换
├── 用量追踪 + 限额提醒
├── 新手引导系统 (5步引导)
├── 工作流模板库
├── 知识库自动更新 (爬虫 + AI 提取)
└── 邮件/短信通知系统
```

### Phase 7: 主动智能（2周）

```
Week 8-9: 事件驱动 + Sub-Agent 主动服务
├── EMAEventBus 事件总线
├── ProactiveScheduler 定时调度
├── 各 Sub-Agent 主动服务实现
├── 通知系统集成
└── 用户偏好学习
```

### Phase 8: 移动端 + 私有部署（2周）

```
Week 10-11: PWA + 小程序 + 私有化
├── PWA 移动端 (响应式 + 离线缓存)
├── 企业微信小程序
├── 私有部署包 (Docker Compose)
├── 企业 SSO 集成 (LDAP/OAuth)
└── 数据导出/备份工具
```

### 总体时间线

```
            May                  Jun                  Jul
      ┌─────┼─────┬─────┬─────┼─────┬─────┬─────┼─────┤
Phase 4 ████████
Phase 5         ████████
Phase 6                 ████████████████
Phase 7                                 ████████
Phase 8                                         ████████
            └── MVP ──┘ └── Beta ──┘ └── GA v2.0 ──┘

MVP:  7月初，10 个种子用户内测
Beta: 7月中旬，开放注册 + 付费
GA:   8月初，正式商业化发布
```

---

## 十、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| 支付资质（国内需支付牌照） | 中 | 高 | 用 Ping++ 聚合支付，无需牌照 |
| Stripe 中国区限制 | 低 | 中 | 用 Stripe HK/SG 账号 + 跨境收款 |
| LLM 推理成本高 | 高 | 中 | 本地 Ollama 优先 + 云端 fallback + 缓存 |
| 国标数据版权问题 | 中 | 中 | 仅引用标准编号 + 用户自行确认 |
| 大企业私有部署需求 | 中 | 中 | 提供 Docker Compose 一键部署 |
| 竞品抄袭 | 中 | 低 | 快速迭代 + 知识库护城河 |
| 数据安全合规（个保法） | 高 | 高 | 数据本地化 + 加密存储 + 用户可导出删除 |

---

## 附录：技术栈升级建议

| 当前 | 建议升级 | 原因 |
|------|---------|------|
| SQLite | **PostgreSQL 16 + pgvector** | 支持 RLS + 向量搜索替代 ChromaDB |
| 单进程 FastAPI | **FastAPI + Redis Queue + Arq Workers** | 并发处理 |
| ChromaDB | **pgvector** 或保留 + 懒加载 | 生产稳定性 |
| Ollama 直接调用 | **vLLM** 或 **Ollama API + 请求队列** | GPU 高效批处理 |
| 无认证 | **JWT + OAuth2 + RBAC** | 多租户安全 |
| 无支付 | **Ping++ (国内) + Stripe (海外)** | 商业化变现 |
| HTML Vanilla JS | 保持（或 Vue 3 SPA） | 当前够用，后续可升级 |
| WSL2 开发 | **K8s 部署 (GKE/AKS/自建)** | 生产环境 |

---

**文档完成时间**: 2026-05-18 18:00
**下一步**: 刚哥审批 → 启动 Phase 4（多租户基础设施）