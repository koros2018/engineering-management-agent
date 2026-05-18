# 图纸AI助手 · Agent化重构方案
> **日期：** 2026-05-16  
> **版本：** v1.0（初始版）  
> **背景：** 参照Manus智能体架构，对项目AI能力重新评估并给出可行性重构方案

---

## 一、现状评估

### 1.1 架构概览

项目当前为 **FastAPI REST API + Vue3 前端** 的传统架构，核心模块：

| 模块 | 文件 | 定位 |
|------|------|------|
| 解析引擎 | `core.py` / `pdf_parser.py` / `dxf_parser.py` | 纯规则引擎，无AI |
| AI分析 | `inference.py` / `knowledge_base_ai.py` | Ollama LLM调用 |
| 文档生成 | `documents.py` / `pdf_documents.py` | 模板填充+规则 |
| 智能审查 | `review.py` / `specs.py` | 规则引擎（5条国标） |
| AI改图 | `dxf_editor.py` | DWG→DXF转换+ezdxf编辑 |
| LLM服务 | `llm_service.py` | Ollama API封装（降级链） |
| LLM监督 | `llm_supervisor.py` | 监控+模型降级 |
| 前端 | `ui-vue/` (Vue3+Pinia+Router) | SPA |

### 1.2 现有AI能力分析

| 能力 | 当前实现 | AI介入程度 | 问题 |
|------|----------|------------|------|
| 图纸解析 | 规则引擎（PyMuPDF/ezdxf/libredwg） | ❌ 无 | DWG语义理解浅层 |
| 图纸类型识别 | `inference.py` 关键词+图层匹配 | ⚠️ 弱 | 覆盖有限，扩展性差 |
| 设计分析 | `inference.py` → LLM文本生成 | ✅ 有 | 单次调用，无规划 |
| 国标库 | `knowledge_base_ai.py` AI提取+搜索 | ✅ 有 | 无Agent规划能力 |
| 智能审图 | `review.py` 规则引擎 | ❌ 无 | 规则固定，无法自适应 |
| 文档生成 | `documents.py` 模板+填充 | ⚠️ 弱 | 模板驱动，非生成式 |
| AI改图 | `dxf_editor.py` 结构化API | ⚠️ 弱 | 需人工编排操作序列 |
| 预算生成 | `budget.py` 规则+材料库 | ⚠️ 弱 | 规则驱动 |

**核心问题：**
- 各模块AI能力分散，无统一Agent调度
- LLM调用为单次request-response，无多步骤规划
- 无Sandbox执行环境，无法动态生成并执行代码
- 无记忆/上下文持久化（会话级）
- 无自主工具调用链（Tool Use是硬编码的）
- 无自我纠错和反思机制

### 1.3 当前LLM能力

```
配置：Ollama本地 + 云端降级链
默认模型：qwen3.5:9b（本地）
降级池：deepseek-r1:7b → qwen3.5:9b → llama3.1:8b → minimax-m2.7:cloud → rule_engine
超时：120s（本地）/ 60s（云端）
问题：generation endpoints超时严重，Manus已放弃此路径
```

---

## 二、Manus架构核心解析

### 2.1 Manus的关键架构特征

通过研究Manus公开资料，其核心架构如下：

**① 可执行代码生成（而非工具调用）**
- 传统Agent：LLM调用预定义工具（HTTP/RAG/代码执行）
- Manus：**动态生成Python/JS代码块** → 在沙箱中执行 → 返回结果
- 优势：无限扩展，无预定义工具集限制；代码即工具，可自举

**② 云端Sandbox执行环境**
- 每个任务在隔离的云容器中运行
- 完整的文件系统访问 + npm/pip安装 + 网络访问
- 代码执行 + 结果验证形成闭环

**③ Multi-Agent编排**
- 一个"主Agent"负责任务分解和协调
- 多个专业子Agent并行/串行执行子任务
- Agent间通过共享上下文通信

**④ 上下文工程（Context Engineering）**
- 精心设计system prompt和few-shot示例
- 主动管理上下文长度（摘要/截断策略）
- 记忆模块：短期（会话）+ 长期（向量数据库）

**⑤ 自主验证循环**
- 执行结果 → 自检（LLM判断） → 失败则重试/调整 → 最终交付
- 关键：不是线性执行，而是"计划-执行-验证-修正"循环

### 2.2 Manus架构简图

```
用户请求
    ↓
┌─────────────────┐
│   主控 Agent    │ ← 任务规划 + 分解 + 结果整合
│  (规划、调度)   │
└───────┬─────────┘
    ↓         ↓
┌────────┐ ┌────────┐
│子Agent1│ │子Agent2│ ← 专业任务执行（解析/审查/生成）
│ (MCP)  │ │ (MCP)  │
└───┬────┘ └───┬────┘
    ↓          ↓
┌─────────────────────┐
│   Sandbox执行环境   │ ← 代码生成 + 执行 + 验证
│  (Python/JS/终端)  │
└─────────────────────┘
    ↓
 结果返回 → 失败则循环重试
```

### 2.3 Manus的局限性与教训

- **生成endpoint超时问题**：Manus已转向"可执行代码"模式，放弃依赖LLM生成endpoint
- **成本**：云端沙箱+大模型调用成本高
- **速度**：复杂任务4分钟，仍有优化空间
- **私密性**：云端执行，数据不留在本地

---

## 三、图纸AI助手Agent化重构方案

### 3.1 重构目标

```
当前：REST API + 规则引擎 + 分散LLM调用
目标：Multi-Agent系统 + Sandbox执行 + 统一调度
```

### 3.2 架构设计

#### 层级一：Agent调度层（核心新增）

```
┌─────────────────────────────────────────────┐
│           BlueprintAgent（主控Agent）        │
│  - 任务理解与分解                            │
│  - 子Agent调度                               │
│  - 结果整合与输出                            │
│  - 自我纠错循环                              │
└─────────────────┬───────────────────────────┘
                  │
      ┌───────────┼────────────┐
      ↓           ↓            ↓
 ┌─────────┐ ┌─────────┐ ┌───────────┐
 │Parser   │ │Review   │ │Document  │
 │Agent    │ │Agent    │ │Agent     │
 │(解析专家)│ │(审图专家)│ │(文档专家) │
 └────┬────┘ └────┬────┘ └─────┬────┘
      │           │            │
```

**新增模块：**
- `src/agent/__init__.py`
- `src/agent/blueprint_agent.py` — 主控Agent
- `src/agent/sub_agents/parser_agent.py` — 图纸解析Agent
- `src/agent/sub_agents/review_agent.py` — 智能审图Agent
- `src/agent/sub_agents/document_agent.py` — 文档生成Agent
- `src/agent/planner.py` — 任务规划器
- `src/agent/executor.py` — Sandbox执行器
- `src/agent/memory.py` — 记忆模块（短期+长期）
- `src/agent/verifier.py` — 结果验证器

#### 层级二：Sandbox执行层（核心新增）

```
执行流程：
  1. Agent决定需要执行的代码（Python代码块）
  2. Executor接收代码，在隔离环境中运行
  3. 执行结果返回Agent进行验证
  4. 验证通过则进入下一步，失败则重试/回退
```

**技术选型：**
- **选项A（推荐）：** `Pyodide`（WebAssembly Python运行时，浏览器内执行）
  - 优点：前端集成方便，无服务器资源消耗，完全隔离
  - 适用场景：前端AI助手中的代码执行
- **选项B：** 后端Python subprocess + 资源限制
  - 优点：功能完整，可调用所有Python库
  - 缺点：需要安全沙箱（docker/pid namespace）
- **选项C：** Node.js vm2 隔离执行
  - 适用场景：JS脚本执行

#### 层级三：工具层（重构现有模块）

现有模块经过Agent封装后变为"工具"：

| 工具名 | 封装现有模块 | 能力 |
|--------|-------------|------|
| `parse_blueprint` | `core.py` / `pdf_parser.py` | 图纸解析+类型识别 |
| `review_blueprint` | `review.py` + `specs.py` | 国标合规审查 |
| `generate_document` | `documents.py` | 文档生成 |
| `edit_dxf` | `dxf_editor.py` | 图纸修改 |
| `search_knowledge_base` | `knowledge_base.py` | 国标库检索 |
| `browse_web` | 外部搜索 | 联网查规范 |
| `run_python` | Sandbox | 动态执行Python代码 |

#### 层级四：记忆层（新增）

```
短期记忆：当前会话上下文（TTL会话级）
长期记忆：向量数据库（Chroma/Pgvector）
  - 用户偏好
  - 项目历史摘要
  - 成功执行模式
```

### 3.3 关键模块详细设计

#### BlueprintAgent（主控）

```python
class BlueprintAgent:
    """
    主控Agent：接收用户请求 → 规划 → 调度 → 整合输出
    """
    def __init__(self, user_id: str, project_id: str):
        self.planner = Planner()        # 任务分解
        self.executor = Executor()      # 代码执行
        self.memory = AgentMemory()      # 记忆管理
        self.verifier = Verifier()      # 结果验证

    async def run(self, task: str) -> AgentResult:
        # Step 1: 理解任务
        context = await self.memory.load_context(user_id, project_id)
        plan = await self.planner.create_plan(task, context)

        # Step 2: 逐步执行+验证循环
        for step in plan.steps:
            result = await self.execute_step(step)
            if not self.verifier.check(result):
                result = await self.retry_with_adjustment(step, result)

        # Step 3: 整合输出
        return self.compile_final_output(plan, plan.execution_history)
```

#### Planner（任务规划）

```python
class Planner:
    """
    任务规划器：使用LLM将复杂请求分解为可执行步骤
    """
    def create_plan(self, task: str, context: dict) -> Plan:
        # 使用few-shot提示让LLM输出结构化步骤
        prompt = f"""
        任务：{task}
        当前上下文：{context}
        请将任务分解为步骤，每个步骤包含：
        - action: 操作类型（parse/review/generate/edit/search/run_code）
        - target: 目标文件/模块
        - expected_output: 预期输出
        - depends_on: 依赖的前置步骤
        """
        # 调用LLM生成计划
        # 解析为Plan对象
```

#### Executor（Sandbox执行）

```python
import pyodide

class Executor:
    """
    Sandbox执行器：接收代码字符串 → 执行 → 返回结果
    """
    async def execute(self, code: str, lang: str = "python") -> ExecutionResult:
        if lang == "python":
            # 方案A: Pyodide（前端）
            result = await self.run_in_pyodide(code)
        elif lang == "python_server":
            # 方案B: 后端subprocess + dockar隔离
            result = await self.run_in_docker(code)
        return result

    async def run_in_pyodide(self, code: str):
        # Pyodide在浏览器中运行，完全隔离
        # 可导入numpy/pandas等科学计算库
        pass
```

### 3.4 重构实施路线

#### 第一阶段：架构基础（2-3周）

**目标：** 建立Agent骨架，验证核心流程

1. 新建 `src/agent/` 目录结构
2. 实现 `BlueprintAgent` 主控类（无LLM，纯状态机）
3. 实现 `Planner`（先用规则版本，LLM后加）
4. 实现基础 `Executor`（Pyodide集成）
5. 迁移现有API → Agent工具封装

**里程碑：** 用户说"帮我分析这张图纸" → Agent自动完成解析+类型识别+输出

#### 第二阶段：LLM驱动（2-3周）

**目标：** 接入LLM实现智能规划和执行

1. 为Planner添加LLM任务分解能力
2. 实现Verifier（LLM判断结果质量）
3. 添加Memory模块（向量存储）
4. 实现自我纠错循环
5. 多子Agent并行调度

**里程碑：** 复杂请求"审图+生成文档+改图"一键完成，Agent自主决策执行顺序

#### 第三阶段：高级能力（持续迭代）

1. Multi-Agent协作（并行审图+并行文档生成）
2. 记忆持久化（跨会话理解用户项目偏好）
3. 外部工具扩展（联网搜索规范、调用外部API）
4. 前端AI助手界面（对话式操作）

### 3.5 技术选型建议

| 组件 | 推荐方案 | 理由 |
|------|----------|------|
| Agent框架 | **自研**（轻量级） | 项目特殊性，通用框架过于重型 |
| LLM | Ollama（本地）+ 云端降级 | 已有基础设施，Manus经验教训 |
| Sandbox（前端） | Pyodide | 浏览器内隔离执行，无需服务器 |
| Sandbox（后端） | Docker + gVisor | 生产级隔离 |
| 向量存储 | Chromadb（轻量） | 简单部署，支持本地 |
| 规划提示 | Few-shot + CoT | 平衡效果与成本 |
| 验证 | LLM self-check | 通用做法 |

---

## 四、方案评估

### 4.1 优势

1. **架构先进**：对标Manus，agent化后能力边界大幅扩展
2. **可落地**：基于现有模块渐进重构，风险可控
3. **成本可控**：Pyodide前端执行无服务器成本，LLM用Ollama本地
4. **体验提升**：从"填表单等结果"变为"说一句话，Agent搞定"
5. **可扩展**：Sandbox引入后能力无上限，未来可加任意工具

### 4.2 风险与挑战

| 风险 | 级别 | 应对 |
|------|------|------|
| Ollama生成endpoint持续超时 | 🔴 高 | 切换为可执行代码模式（核心改进），不再依赖generation |
| Pyodide加载慢（首次10s+） | 🟡 中 | 按需加载，显示加载进度 |
| Agent规划质量不稳定 | 🟡 中 | 先规则后LLM，两阶段上线 |
| Docker沙箱安全 | 🟡 中 | 用gVisor，严格syscall过滤 |
| 多Agent协作复杂性 | 🟡 中 | 第二阶段逐步引入，先单Agent验证 |

### 4.3 核心结论

> **当前项目AI能力的最大瓶颈：LLM以工具调用为主，无法自主生成可执行代码，导致复杂任务失败率高。**
>
> **Manus的启示：放弃"更聪明的工具调用"，转向"LLM生成代码+Sandbox执行"是更可靠的道路。**
>
> **本方案可行性高，基于现有基础设施渐进重构，第一阶段2-3周可验证核心假设。**

---

## 五、存档与更新记录

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-05-16 | v1.0 | 初始版本，完成现状评估+Manus架构分析+重构方案 |