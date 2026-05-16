"""
agent/base_agent.py - Sub-Agent 基类

所有6个专业Agent必须继承此类。
扁平化管理：各Agent独立执行，通过Main-Agent协调。
"""

import asyncio
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal


# ─────────────────────────────────────────────────────────────────
# 数据结构
# ─────────────────────────────────────────────────────────────────

@dataclass
class Task:
    """Agent收到的任务"""
    task_id: str
    agent_id: str
    task_type: str          # e.g. 'parse', 'analyze', 'review'
    params: Dict[str, Any]  # 任务参数
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文
    constraints: Dict[str, Any] = field(default_factory=dict)  # 约束
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResult:
    """Agent执行结果"""
    task_id: str
    agent_id: str
    status: Literal['success', 'partial', 'failed'] = 'success'
    output: Any = None
    confidence: float = 0.0          # 0-1
    execution_time: float = 0.0     # 秒
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'status': self.status,
            'confidence': self.confidence,
            'execution_time': self.execution_time,
            'errors': self.errors,
            'suggestions': self.suggestions,
            'metadata': self.metadata,
        }


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    data: Any = None
    error: str = ""
    execution_time: float = 0.0


# ─────────────────────────────────────────────────────────────────
# BaseAgent 基类
# ─────────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    """
    Sub-Agent 基类

    设计原则（参照Manus）：
    - 每个Agent独立可运行
    - 扁平化管理（不直接调用其他Agent）
    - Main-Agent负责调度和协调
    - 支持重试机制（最多2次）
    - 所有输出包含置信度
    """

    # 子类必须定义
    AGENT_ID: str = ""
    NAME: str = ""
    DESCRIPTION: str = ""

    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.max_retries = 2
        self._tool_registry: Dict[str, callable] = {}

    # ── 抽象方法（子类必须实现）────────────────────────────

    @abstractmethod
    async def execute(self, task: Task) -> AgentResult:
        """
        执行任务（子类必须实现）

        Args:
            task: 任务对象

        Returns:
            AgentResult: 包含执行结果和置信度
        """
        pass

    @abstractmethod
    async def plan(self, task: Task) -> List[Dict]:
        """
        将任务分解为步骤（子类可选实现）

        Returns:
            List[Dict]: 步骤列表，每步包含 {step, tool, expected_output}
        """
        return []

    # ── 通用方法 ─────────────────────────────────────────

    def register_tool(self, name: str, tool_func: callable):
        """注册工具"""
        self._tool_registry[name] = tool_func

    async def execute_tool(self, tool_name: str, params: Dict, context: Dict) -> ToolResult:
        """执行工具（带超时保护）"""
        start = datetime.now()
        try:
            if tool_name not in self._tool_registry:
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Tool '{tool_name}' not found",
                    execution_time=0.0
                )

            tool_func = self._tool_registry[tool_name]
            result = await asyncio.wait_for(
                tool_func(params, context),
                timeout=context.get('timeout', 120)
            )
            elapsed = (datetime.now() - start).total_seconds()
            return ToolResult(
                tool_name=tool_name,
                success=True,
                data=result,
                execution_time=elapsed
            )
        except asyncio.TimeoutError:
            elapsed = (datetime.now() - start).total_seconds()
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' timeout after {elapsed}s",
                execution_time=elapsed
            )
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"{type(e).__name__}: {str(e)}",
                execution_time=elapsed
            )

    async def run_with_retry(self, task: Task) -> AgentResult:
        """带重试的执行"""
        last_error = ""
        for attempt in range(self.max_retries):
            try:
                result = await self.execute(task)
                if await self.validate(result):
                    return result
                if attempt < self.max_retries - 1:
                    result = await self._adjust(task, result)
            except Exception as e:
                last_error = f"{type(e).__name__}: {str(e)}"
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=self.AGENT_ID,
                    status='failed',
                    errors=[last_error, *traceback.format_exc().splitlines()[-3:]]
                )
            if attempt == self.max_retries - 1:
                result.errors.append(f"Fatal after {self.max_retries} attempts: {last_error}")
                result.status = 'failed'
        return result

    async def validate(self, result: AgentResult) -> bool:
        """验证输出（基础版：检查状态和置信度）"""
        if result.status == 'failed':
            return False
        if result.confidence < 0.5:
            return False
        return True

    async def _adjust(self, task: Task, result: AgentResult) -> AgentResult:
        """根据上次结果调整参数后重试（子类可覆盖）"""
        return result

    def get_capabilities(self) -> Dict[str, Any]:
        """返回Agent能力描述"""
        return {
            'agent_id': self.AGENT_ID,
            'name': self.NAME,
            'description': self.DESCRIPTION,
            'supported_tasks': self.get_supported_tasks(),
            'tool_count': len(self._tool_registry),
        }

    def get_supported_tasks(self) -> List[str]:
        """子类返回支持的task_type列表（子类可覆盖）"""
        return []