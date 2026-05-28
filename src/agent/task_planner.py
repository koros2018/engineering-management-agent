"""
agent/task_planner.py - 任务规划

根据意图分类结果，制定执行计划：
1. 判断单步还是多步
2. 确定需要哪些 Agent/工具
3. 返回步骤列表
"""

from typing import Any, Dict, List


# ─────────────────────────────────────────────────────────────────
# 任务模板
# ─────────────────────────────────────────────────────────────────

# 单步任务模板（直接路由到对应Agent）
SINGLE_STEP_TASKS = {
    # tech_rd
    'tech_rd:parse': {'agent_id': 'tech_rd', 'task_type': 'parse', 'mode': 'single'},
    'tech_rd:classify': {'agent_id': 'tech_rd', 'task_type': 'classify', 'mode': 'single'},
    'tech_rd:analyze': {'agent_id': 'tech_rd', 'task_type': 'analyze', 'mode': 'single'},
    'tech_rd:review': {'agent_id': 'tech_rd', 'task_type': 'review', 'mode': 'single'},
    'tech_rd:extract_quantities': {'agent_id': 'tech_rd', 'task_type': 'extract_quantities', 'mode': 'single'},
    'tech_rd:optimize': {'agent_id': 'tech_rd', 'task_type': 'optimize', 'mode': 'single'},
    'tech_rd:full_analysis': {'agent_id': 'tech_rd', 'task_type': 'full_analysis', 'mode': 'single'},
    'tech_rd:documents': {'agent_id': 'tech_rd', 'task_type': 'documents', 'mode': 'single'},
    'tech_rd:full_pipeline': {'agent_id': 'tech_rd', 'task_type': 'full_pipeline', 'mode': 'single'},
    # safety_compliance
    'safety_compliance:review': {'agent_id': 'safety_compliance', 'task_type': 'review', 'mode': 'single'},
    'safety_compliance:fire_review': {'agent_id': 'safety_compliance', 'task_type': 'fire_review', 'mode': 'single'},
    'safety_compliance:structural_review': {'agent_id': 'safety_compliance', 'task_type': 'structural_review', 'mode': 'single'},
    'safety_compliance:compliance_review': {'agent_id': 'safety_compliance', 'task_type': 'compliance_review', 'mode': 'single'},
    # market_sales
    'market_sales:chat': {'agent_id': 'market_sales', 'task_type': 'chat', 'mode': 'single'},
    # engineering_delivery
    'engineering_delivery:chat': {'agent_id': 'engineering_delivery', 'task_type': 'chat', 'mode': 'single'},
    # cost_benefit
    'cost_benefit:chat': {'agent_id': 'cost_benefit', 'task_type': 'chat', 'mode': 'single'},
    # customer_service
    'customer_service:chat': {'agent_id': 'customer_service', 'task_type': 'chat', 'mode': 'single'},
    # 通用
    'chat': {'agent_id': 'tech_rd', 'task_type': 'full_analysis', 'mode': 'single'},
}

# 多步任务模板（需要多个Agent协作）
MULTI_STEP_TASKS = {
    # 完整图纸分析 + 安全审查
    'full_review': {
        'mode': 'multi',
        'steps': [
            {'agent_id': 'tech_rd', 'task_type': 'full_analysis', 'params': {}},
            {'agent_id': 'safety_compliance', 'task_type': 'review', 'params': {}},
        ],
    },
    # 完整图纸分析 + 工程量 + 成本预算
    'full_with_budget': {
        'mode': 'multi',
        'steps': [
            {'agent_id': 'tech_rd', 'task_type': 'full_analysis', 'params': {}},
            {'agent_id': 'cost_benefit', 'task_type': 'budget', 'params': {}},
        ],
    },
    # 从设计到交付完整流程
    'design_to_delivery': {
        'mode': 'multi',
        'steps': [
            {'agent_id': 'tech_rd', 'task_type': 'full_analysis', 'params': {}},
            {'agent_id': 'safety_compliance', 'task_type': 'review', 'params': {}},
            {'agent_id': 'engineering_delivery', 'task_type': 'plan', 'params': {}},
        ],
    },
}


# ─────────────────────────────────────────────────────────────────
# TaskPlanner
# ─────────────────────────────────────────────────────────────────

class TaskPlanner:
    """
    任务规划器

    根据意图分类结果，创建执行计划：
    1. 匹配任务模板（单步/多步）
    2. 推断执行模式
    3. 返回计划（包含步骤列表）
    """

    def __init__(self):
        self._single_templates = SINGLE_STEP_TASKS
        self._multi_templates = MULTI_STEP_TASKS

    async def create_plan(self, intent: Dict, context: Dict) -> Dict:
        """
        根据意图创建执行计划

        Args:
            intent: IntentClassifier 返回的意图结果
            context: 执行上下文（包含 message 等）

        Returns:
            {
                'execution_mode': 'single' | 'multi',
                'intent_key': str,          # 匹配的模板key
                'steps': List[Dict],       # 执行步骤（multi模式）
                'agent_id': str,            # 目标Agent（single模式）
                'task_type': str,           # 任务类型（single模式）
            }
        """
        intent_key = intent.get('intent', '')
        message = context.get('message', '').lower()

        # 检查是否有特殊多步需求
        multi_key = self._detect_multi_step(message)
        if multi_key and multi_key in self._multi_templates:
            template = self._multi_templates[multi_key]
            return {
                'execution_mode': 'multi',
                'intent_key': multi_key,
                'steps': template['steps'],
            }

        # 单步任务匹配
        if intent_key in self._single_templates:
            template = self._single_templates[intent_key]
            return {
                'execution_mode': 'single',
                'intent_key': intent_key,
                'agent_id': template['agent_id'],
                'task_type': template['task_type'],
            }

        # 尝试按 agent_id:task_type 匹配
        agent_id = intent.get('agent_id', 'tech_rd')
        task_type = intent.get('task_type', 'full_analysis')
        key = f'{agent_id}:{task_type}'
        if key in self._single_templates:
            template = self._single_templates[key]
            return {
                'execution_mode': 'single',
                'intent_key': key,
                'agent_id': template['agent_id'],
                'task_type': template['task_type'],
            }

        # 默认：tech_rd 完整分析
        return {
            'execution_mode': 'single',
            'intent_key': 'default',
            'agent_id': 'tech_rd',
            'task_type': 'full_analysis',
        }

    def _detect_multi_step(self, message: str) -> str:
        """检测是否需要多步执行"""
        if any(k in message for k in ['完整审查', '全面审查', '设计审查']):
            return 'full_review'
        if any(k in message for k in ['预算', '造价', '成本分析']):
            return 'full_with_budget'
        if any(k in message for k in ['交付', '完整流程', '从设计到']):
            return 'design_to_delivery'
        return None

    def get_supported_plans(self) -> List[str]:
        """返回支持的plan类型"""
        return list(self._single_templates.keys()) + list(self._multi_templates.keys())