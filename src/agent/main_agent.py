"""
agent/main_agent.py - 工程管理与发展研究中心（Main-Agent）

EMA 的 AI 大脑，负责：
1. 接收自然语言指令
2. 意图分类（intent_classifier）
3. 任务规划（task_planner）
4. Agent 调度（orchestrator）
5. 结果整合（result_compiler）
6. 向用户返回结果

扁平化管理：6个 Sub-Agent 独立运行，通过 Main-Agent 协调。
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent.base_agent import BaseAgent, Task, AgentResult
from agent.intent_classifier import IntentClassifier
from agent.task_planner import TaskPlanner
from agent.orchestrator import AgentOrchestrator
from agent.result_compiler import ResultCompiler


# ─────────────────────────────────────────────────────────────────
# Main-Agent 主类
# ─────────────────────────────────────────────────────────────────

class EngineeringManagementAgent(BaseAgent):
    """
    Main-Agent - 工程管理与发展研究中心

    工作流程：
    1. 接收用户指令（自然语言）
    2. 意图分类（IntentClassifier）
    3. 任务规划（TaskPlanner）→ 分解为子任务
    4. Sub-Agent 执行（AgentOrchestrator）
    5. 结果整合（ResultCompiler）
    6. 返回结果
    """

    AGENT_ID = "main"
    NAME = "工程管理与发展研究中心"
    DESCRIPTION = "EMA 大脑，统管所有 Sub-Agent，负责任务分解、调度、整合、汇报"

    def __init__(self):
        super().__init__()

        # 初始化子组件
        self.intent_classifier = IntentClassifier()
        self.task_planner = TaskPlanner()
        self.orchestrator = AgentOrchestrator()
        self.result_compiler = ResultCompiler()

        # Memory 层（懒加载，避免 ChromaDB 下载阻塞启动）
        self._chroma = None

        # 初始化所有 Sub-Agent
        self._init_sub_agents()

    @property
    def _chroma_store(self):
        """懒加载 ChromaDBStore，避免启动时下载 ONNX 模型阻塞"""
        if self._chroma is None:
            try:
                from memory import get_chroma_store
                self._chroma = get_chroma_store()
            except Exception:
                self._chroma = None
        return self._chroma

        # 注册工具
        self.register_tool('classify_intent', self._wrap(self._classify_intent))
        self.register_tool('plan_task', self._wrap(self._plan_task))
        self.register_tool('dispatch', self._wrap(self._dispatch))
        self.register_tool('chat', self._wrap(self._chat))

    def _init_sub_agents(self):
        """初始化所有 Sub-Agent（懒加载）"""
        from sub_agents import (
            TechRdAgent,
            SafetyComplianceAgent,
            MarketSalesAgent,
            EngineeringDeliveryAgent,
            CostBenefitAgent,
            CustomerServiceAgent,
        )

        self.sub_agents = {
            'tech_rd': TechRdAgent(),
            'safety_compliance': SafetyComplianceAgent(),
            'market_sales': MarketSalesAgent(),
            'engineering_delivery': EngineeringDeliveryAgent(),
            'cost_benefit': CostBenefitAgent(),
            'customer_service': CustomerServiceAgent(),
        }

        # Agent元数据
        self.agent_info = {
            'tech_rd': {'name': '技术研发中心', 'description': '图纸解析/类型识别/AI分析/工程量/设计优化'},
            'safety_compliance': {'name': '安全与合规中心', 'description': '消防合规/结构安全/施工安全/法规审核'},
            'market_sales': {'name': '市场与销售中心', 'description': '市场分析/商务方案/投标文件/客户需求'},
            'engineering_delivery': {'name': '工程交付中心', 'description': '项目计划/施工方案/进度追踪/竣工资料'},
            'cost_benefit': {'name': '成本效益中心', 'description': '工程量计算/预算生成/变更签证/经济效益'},
            'customer_service': {'name': '客户服务中心', 'description': 'FAQ/工单管理/回访计划/培训材料'},
        }

    def _wrap(self, func):
        async def wrapper(params: Dict, context: Dict) -> Any:
            return await func(params, context)
        return wrapper

    # ── BaseAgent 必须实现 ─────────────────────────────────────

    async def execute(self, task: Task) -> AgentResult:
        """Main-Agent 不直接执行任务，而是路由到子 Agent"""
        # 实际上 chat 接口是主要入口，这里仅作备用
        return await self._chat({'message': task.params.get('message', '')}, task.context)

    async def plan(self, task: Task) -> List[Dict]:
        """Main-Agent 规划任务步骤"""
        intent = await self.intent_classifier.classify(task.params.get('message', ''))
        return await self.task_planner.create_plan(intent, task.context)

    # ── 核心方法 ──────────────────────────────────────────────

    async def _classify_intent(self, params: Dict, context: Dict) -> Dict:
        """意图分类"""
        message = params.get('message', '')
        intent = await self.intent_classifier.classify(message)
        return {
            'intent': intent,
            'message': message,
            'agent_id': intent.get('agent_id', 'tech_rd'),
            'task_type': intent.get('task_type', 'full_analysis'),
        }

    async def _plan_task(self, params: Dict, context: Dict) -> Dict:
        """任务规划"""
        intent = params.get('intent', {})
        plan = await self.task_planner.create_plan(intent, context)
        return {
            'plan': plan,
            'steps_count': len(plan),
        }

    async def _dispatch(self, params: Dict, context: Dict) -> Dict:
        """Agent 调度"""
        intent = params.get('intent', {})
        plan = params.get('plan', [])
        results = await self.orchestrator.dispatch(intent, plan, self.sub_agents, context)
        return results

    async def _chat(self, params: Dict, context: Dict) -> Dict:
        """
        主对话入口：一站式处理用户请求

        工作流：
        1. 意图分类
        2. 任务规划（多步则并行/串行调度）
        3. 结果整合
        4. 存储对话历史到 ChromaDB
        5. 返回
        """
        start_time = datetime.now()
        message = params.get('message', '')
        file_path = params.get('file_path')
        session_id = context.get('session_id') or context.get('user_id', 'default')

        # Step 1: 意图分类
        intent = await self.intent_classifier.classify(message)

        # Step 2: 任务规划
        plan = await self.task_planner.create_plan(intent, {**context, 'message': message})

        # Step 3: 调度 Sub-Agent（支持单步和多步）
        if plan.get('execution_mode') == 'single':
            # 单步任务：直接调度
            agent_id = intent.get('agent_id', 'tech_rd')
            task_type = intent.get('task_type', 'full_analysis')

            agent = self.sub_agents.get(agent_id)
            if not agent:
                return {
                    'success': False,
                    'error': f"Agent '{agent_id}' not found",
                    'execution_time': (datetime.now() - start_time).total_seconds(),
                }

            task = Task(
                task_id=str(uuid.uuid4()),
                agent_id=agent_id,
                task_type=task_type,
                params={'message': message, 'file_path': file_path},
                context={**context, 'message': message, 'task_id': str(uuid.uuid4())}
            )

            result = await agent.run_with_retry(task)
            compiled = await self.result_compiler.compile(result)

        elif plan.get('execution_mode') == 'multi':
            # 多步任务：并行调度多个 Agent
            steps = plan.get('steps', [])
            results = await self.orchestrator.dispatch_parallel(steps, self.sub_agents, {**context, 'message': message})
            compiled = await self.result_compiler.compile_multi(results)
        else:
            return {
                'success': False,
                'error': f"Unknown execution mode: {plan.get('execution_mode')}",
                'execution_time': (datetime.now() - start_time).total_seconds(),
            }

        elapsed = (datetime.now() - start_time).total_seconds()

        # Step 4: 存储对话历史到 ChromaDB（异步，不阻塞返回）
        try:
            chroma = self._chroma_store
            if chroma:
                session_id_copy = session_id
                intent_data = {'agent_id': intent.get('agent_id', 'main'), 'intent': intent.get('intent'), 'confidence': intent.get('confidence', 0)}
                response_text = compiled.get('text', '') or ''
                # 在后台线程存储，不阻塞响应
                import threading
                def _store():
                    try:
                        chroma.add_conversation(session_id=session_id_copy, role='user', content=message, agent_id=intent_data['agent_id'], metadata={'intent': intent_data.get('intent'), 'confidence': intent_data.get('confidence', 0)})
                        if response_text:
                            chroma.add_conversation(session_id=session_id_copy, role='agent', content=response_text[:500], agent_id=intent_data['agent_id'], metadata={'plan': plan.get('intent_key'), 'confidence': compiled.get('confidence', 0)})
                    except Exception:
                        pass
                threading.Thread(target=_store, daemon=True).start()
        except Exception:
            pass  # 不因记忆存储失败影响主流程

        return {
            'success': True,
            'intent': intent,
            'plan': plan,
            'output': compiled.get('output'),
            'confidence': compiled.get('confidence', 0.8),
            'execution_time': elapsed,
            'response_text': compiled.get('text'),
        }

    def get_capabilities(self) -> Dict[str, Any]:
        """返回 Main-Agent + 所有 Sub-Agent 的能力"""
        return {
            'agent_id': self.AGENT_ID,
            'name': self.NAME,
            'description': self.DESCRIPTION,
            'supported_tasks': ['chat', 'classify_intent', 'plan_task', 'dispatch'],
            'sub_agents': [
                {
                    'agent_id': agent_id,
                    'name': info['name'],
                    'description': info['description'],
                    'supported_tasks': self.sub_agents[agent_id].get_supported_tasks(),
                }
                for agent_id, info in self.agent_info.items()
            ],
            'tool_count': len(self._tool_registry),
        }

    def get_supported_tasks(self) -> List[str]:
        return ['chat', 'classify_intent', 'plan_task', 'dispatch']