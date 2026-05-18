"""
agent/orchestrator.py - Agent调度器

负责：
1. 将任务分发到正确的 Sub-Agent
2. 处理并行/串行执行
3. 汇总子Agent返回的结果
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from agent.base_agent import Task, AgentResult


# ─────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────

class AgentOrchestrator:
    """
    Agent编排器

    职责：
    - 根据计划调度 Sub-Agent
    - 支持并行（parallel）和串行（sequential）执行
    - 处理超时和错误
    - 汇总结果
    """

    def __init__(self, timeout: int = 120):
        self.timeout = timeout  # 单个Agent超时（秒）

    async def dispatch(
        self,
        intent: Dict,
        plan: Dict,
        sub_agents: Dict[str, Any],
        context: Dict,
    ) -> Dict:
        """
        调度 Sub-Agent 执行任务

        Args:
            intent: 意图分类结果
            plan: 任务计划
            sub_agents: 所有 Sub-Agent 实例字典
            context: 执行上下文

        Returns:
            {
                'success': bool,
                'results': List[AgentResult],
                'execution_mode': str,
            }
        """
        execution_mode = plan.get('execution_mode', 'single')

        if execution_mode == 'single':
            return await self._dispatch_single(intent, plan, sub_agents, context)
        elif execution_mode == 'multi':
            return await self._dispatch_multi(plan, sub_agents, context)
        else:
            return {
                'success': False,
                'error': f'Unknown execution mode: {execution_mode}',
                'results': [],
            }

    async def _dispatch_single(
        self,
        intent: Dict,
        plan: Dict,
        sub_agents: Dict[str, Any],
        context: Dict,
    ) -> Dict:
        """单步执行：直接路由到目标Agent"""
        agent_id = plan.get('agent_id', intent.get('agent_id', 'tech_rd'))
        task_type = plan.get('task_type', intent.get('task_type', 'full_analysis'))

        agent = sub_agents.get(agent_id)
        if not agent:
            return {
                'success': False,
                'error': f"Agent '{agent_id}' not found",
                'results': [],
            }

        try:
            task = Task(
                task_id=context.get('task_id', ''),
                agent_id=agent_id,
                task_type=task_type,
                params=context.get('params', {}),
                context=context,
            )

            result = await asyncio.wait_for(
                agent.run_with_retry(task),
                timeout=self.timeout,
            )

            return {
                'success': True,
                'results': [result],
                'execution_mode': 'single',
            }

        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': f'Agent {agent_id} timeout after {self.timeout}s',
                'results': [],
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'{type(e).__name__}: {str(e)}',
                'results': [],
            }

    async def _dispatch_multi(
        self,
        plan: Dict,
        sub_agents: Dict[str, Any],
        context: Dict,
    ) -> Dict:
        """多步执行：按顺序调度多个Agent"""
        steps = plan.get('steps', [])
        results = []
        all_success = True

        for i, step in enumerate(steps):
            agent_id = step.get('agent_id')
            task_type = step.get('task_type')
            task_params = step.get('params', {})

            agent = sub_agents.get(agent_id)
            if not agent:
                results.append(AgentResult(
                    task_id=f'{i}',
                    agent_id=agent_id,
                    status='failed',
                    errors=[f"Agent '{agent_id}' not found"],
                ))
                all_success = False
                continue

            try:
                task = Task(
                    task_id=f'step_{i}',
                    agent_id=agent_id,
                    task_type=task_type,
                    params={**task_params, **context.get('params', {})},
                    context={**context, 'step_index': i},
                )

                result = await asyncio.wait_for(
                    agent.run_with_retry(task),
                    timeout=self.timeout,
                )
                results.append(result)

                if result.status == 'failed':
                    all_success = False

            except asyncio.TimeoutError:
                results.append(AgentResult(
                    task_id=f'step_{i}',
                    agent_id=agent_id,
                    status='failed',
                    errors=[f'Timeout after {self.timeout}s'],
                ))
                all_success = False
            except Exception as e:
                results.append(AgentResult(
                    task_id=f'step_{i}',
                    agent_id=agent_id,
                    status='failed',
                    errors=[f'{type(e).__name__}: {str(e)}'],
                ))
                all_success = False

        return {
            'success': all_success,
            'results': results,
            'execution_mode': 'multi',
        }

    async def dispatch_parallel(
        self,
        steps: List[Dict],
        sub_agents: Dict[str, Any],
        context: Dict,
    ) -> List[AgentResult]:
        """并行执行多个Agent任务"""
        tasks = []
        for i, step in enumerate(steps):
            agent_id = step.get('agent_id')
            task_type = step.get('task_type')
            agent = sub_agents.get(agent_id)
            if not agent:
                tasks.append(self._failed_result(f'{i}', agent_id, f"Agent '{agent_id}' not found"))
                continue

            task = Task(
                task_id=f'parallel_{i}',
                agent_id=agent_id,
                task_type=task_type,
                params={},
                context={**context, 'step_index': i},
            )
            tasks.append(agent.run_with_retry(task))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def _failed_result(self, task_id: str, agent_id: str, error: str) -> AgentResult:
        return AgentResult(
            task_id=task_id,
            agent_id=agent_id,
            status='failed',
            errors=[error],
        )