"""
agent/__init__.py - Agent框架核心
"""

from .base_agent import BaseAgent, Task, AgentResult, ToolResult

__all__ = ['BaseAgent', 'Task', 'AgentResult', 'ToolResult']