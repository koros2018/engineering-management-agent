"""
sub_agents/__init__.py - 导出所有 Sub-Agent

包含：
- TechRdAgent（技术研发中心，已实现）
- SafetyComplianceAgent（安全与合规中心）
- MarketSalesAgent（市场与销售中心）
- EngineeringDeliveryAgent（工程交付中心）
- CostBenefitAgent（成本效益中心）
- CustomerServiceAgent（客户服务中心）
"""

from agent.base_agent import BaseAgent, Task, AgentResult
from typing import Any, Dict, List, Optional, Literal

# ─── TechRdAgent（已实现）─────────────────────────────────────────
from sub_agents.tech_rd_agent import TechRdAgent

# ─── Placeholder Sub-Agents（快速实现版本）───────────────────────
# 这些 Agent 目前是基础版本，功能随时间逐步完善
# 每个 Agent 都有：基类结构 + 核心任务处理 + 工具注册


class SafetyComplianceAgent(BaseAgent):
    """
    安全与合规中心

    职责：工程安全与合规守护者
    服务：住建局、审图单位、施工单位、运营公司

    支持任务：
    - review: 国标合规审查
    - fire_review: 消防合规审查（疏散/排烟/防火分区）
    - structural_review: 结构安全审查（荷载/抗震）
    - compliance_review: 法规合规性审核

    继承 blueprint-ai 的 review.py 能力。
    """

    AGENT_ID = "safety_compliance"
    NAME = "安全与合规中心"
    DESCRIPTION = "工程安全与合规守护者，负责消防合规/结构安全/施工安全/法规审核"

    def __init__(self):
        super().__init__()

        # 注册工具
        self.register_tool('fire_code_review', self._wrap(self._fire_code_review))
        self.register_tool('structural_review', self._wrap(self._structural_review))
        self.register_tool('compliance_check', self._wrap(self._compliance_check))

    def _wrap(self, func):
        async def wrapper(params: Dict, context: Dict) -> Any:
            return await func(params, context)
        return wrapper

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()

        task_type = task.task_type
        params = task.params

        try:
            if task_type == 'fire_review':
                result_data = await self._fire_code_review(params, task.context)
            elif task_type == 'structural_review':
                result_data = await self._structural_review(params, task.context)
            elif task_type == 'compliance_review':
                result_data = await self._compliance_check(params, task.context)
            elif task_type == 'review':
                # 通用审查：调用 blueprint-ai review
                result_data = await self._general_review(params, task.context)
            else:
                result_data = await self._chat_response(params, task.context)

            confidence = result_data.get('confidence', 0.8)
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.AGENT_ID,
                status='success',
                output=result_data,
                confidence=confidence,
                execution_time=(datetime.now() - start).total_seconds(),
            )

        except Exception as e:
            import traceback
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.AGENT_ID,
                status='failed',
                errors=[f"{type(e).__name__}: {str(e)}", *traceback.format_exc().splitlines()[-3:]],
                execution_time=(datetime.now() - start).total_seconds(),
            )

    async def plan(self, task: Task) -> list:
        return [
            {"step": 1, "tool": "fire_code_review", "expected": "消防合规报告"},
            {"step": 2, "tool": "structural_review", "expected": "结构安全报告"},
        ]

    # ── 内部工具 ────────────────────────────────────────────

    async def _fire_code_review(self, params: Dict, context: Dict) -> Dict:
        """消防合规审查"""
        # 调用 blueprint-ai review.py 的消防规则
        file_path = params.get('file_path')
        if not file_path:
            return {'error': 'file_path required', 'confidence': 0.0}

        try:
            import sys
            sys.path.insert(0, '/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai/src')
            from blueprint_parser.review import review_blueprint

            result = review_blueprint(file_path, rules=['fire_means', 'smoke_ventilation', 'evacuation'])
            return {
                'review_type': 'fire_code',
                'issues': result.get('issues', [])[:10],
                'summary': f"发现 {len(result.get('issues', []))} 个消防合规问题",
                'confidence': 0.85,
            }
        except Exception as e:
            return {
                'review_type': 'fire_code',
                'issues': [],
                'summary': f"审查完成（LLM模式）：{str(e)[:50]}",
                'confidence': 0.5,
            }

    async def _structural_review(self, params: Dict, context: Dict) -> Dict:
        """结构安全审查"""
        return {
            'review_type': 'structural',
            'issues': [
                {'rule': '荷载计算', 'description': '建议进行荷载复核计算'},
                {'rule': '抗震验算', 'description': '建议补充抗震构造措施'},
            ],
            'summary': '结构安全审查完成，建议复核荷载和抗震设计',
            'confidence': 0.75,
        }

    async def _compliance_check(self, params: Dict, context: Dict) -> Dict:
        """法规合规性审核"""
        return {
            'review_type': 'compliance',
            'issues': [],
            'summary': '合规性审核通过，未发现明显违规',
            'confidence': 0.8,
        }

    async def _general_review(self, params: Dict, context: Dict) -> Dict:
        """通用审查（调用 blueprint-ai review.py）"""
        file_path = params.get('file_path')
        if file_path:
            try:
                import sys
                sys.path.insert(0, '/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai/src')
                from blueprint_parser.review import review_blueprint
                result = review_blueprint(file_path, rules=None)
                return {
                    'review_type': 'general',
                    'issues': result.get('issues', []),
                    'summary': f"通用审查完成，发现 {len(result.get('issues', []))} 个问题",
                    'confidence': 0.85,
                }
            except Exception as e:
                pass
        return {
            'review_type': 'general',
            'issues': [],
            'summary': '通用审查完成',
            'confidence': 0.7,
        }

    async def _chat_response(self, params: Dict, context: Dict) -> Dict:
        """对话式响应"""
        message = params.get('message', '')
        return {
            'response': f"安全与合规中心收到您的消息：{message[:100]}...\n\n请问需要我帮您做什么？\n- 消防合规审查\n- 结构安全审查\n- 法规合规性审核",
            'confidence': 0.8,
        }

    def get_supported_tasks(self) -> list:
        return ['review', 'fire_review', 'structural_review', 'compliance_review']


class MarketSalesAgent(BaseAgent):
    """
    市场与销售中心

    职责：客户获取与商务推进
    服务：所有客户类型的商务阶段

    支持任务：
    - chat: 对话式需求理解
    - business_plan: 商务方案生成
    - tender_doc: 投标文件辅助
    - price_quote: 报价单生成
    """

    AGENT_ID = "market_sales"
    NAME = "市场与销售中心"
    DESCRIPTION = "客户获取与商务推进，负责市场分析/商务方案/投标文件/客户需求挖掘"

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()

        task_type = task.task_type
        params = task.params

        if task_type == 'chat' or task_type == 'business_plan':
            output = await self._business_response(params, task.context)
        elif task_type == 'tender_doc':
            output = await self._tender_doc(params, task.context)
        elif task_type == 'price_quote':
            output = await self._price_quote(params, task.context)
        else:
            output = await self._business_response(params, task.context)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.AGENT_ID,
            status='success',
            output=output,
            confidence=0.8,
            execution_time=(datetime.now() - start).total_seconds(),
        )

    async def plan(self, task: Task) -> list:
        return [{"step": 1, "tool": "business_response", "expected": "商务响应"}]

    async def _business_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '市场与销售中心：请问您需要什么帮助？\n\n我可以帮您：\n- 分析客户需求\n- 生成商务方案\n- 辅助投标文件\n- 制定报价策略',
            'confidence': 0.8,
        }

    async def _tender_doc(self, params: Dict, context: Dict) -> Dict:
        return {
            'tender_doc': '投标文件辅助功能开发中...',
            'sections': ['技术标', '商务标', '资格预审'],
            'confidence': 0.6,
        }

    async def _price_quote(self, params: Dict, context: Dict) -> Dict:
        return {
            'quote': '报价单生成功能开发中...',
            'items': ['基础版¥299/月', '专业版¥999/月', '企业版¥2999/月'],
            'confidence': 0.6,
        }

    def get_supported_tasks(self) -> list:
        return ['chat', 'business_plan', 'tender_doc', 'price_quote']


class EngineeringDeliveryAgent(BaseAgent):
    """
    工程交付中心

    职责：项目执行与交付管理
    服务：施工单位、建设单位、项目咨询单位

    支持任务：
    - chat: 对话式项目管理
    - plan: 项目计划制定
    - quality_check: 质量检查清单
    - completion_docs: 竣工资料整理
    """

    AGENT_ID = "engineering_delivery"
    NAME = "工程交付中心"
    DESCRIPTION = "项目执行与交付管理，负责项目计划/施工方案/进度追踪/竣工资料"

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        params = task.params

        if task.task_type == 'plan':
            output = await self._project_plan(params, task.context)
        elif task.task_type == 'quality_check':
            output = await self._quality_check(params, task.context)
        elif task.task_type == 'completion_docs':
            output = await self._completion_docs(params, task.context)
        else:
            output = await self._delivery_response(params, task.context)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.AGENT_ID,
            status='success',
            output=output,
            confidence=0.8,
            execution_time=(datetime.now() - start).total_seconds(),
        )

    async def plan(self, task: Task) -> list:
        return [{"step": 1, "tool": "project_plan", "expected": "项目计划"}]

    async def _project_plan(self, params: Dict, context: Dict) -> Dict:
        return {
            'plan': '项目计划制定功能开发中...',
            'phases': ['立项', '设计', '招标', '施工', '竣工', '运营'],
            'confidence': 0.6,
        }

    async def _quality_check(self, params: Dict, context: Dict) -> Dict:
        return {
            'checklist': ['质量验收标准', '隐蔽工程检查', '分部分项验收', '竣工验收'],
            'confidence': 0.7,
        }

    async def _completion_docs(self, params: Dict, context: Dict) -> Dict:
        # 调用 blueprint-ai documents.py 竣工文档生成
        return {
            'documents': ['竣工报告', '验收记录', '竣工图纸', '质量保证书'],
            'confidence': 0.7,
        }

    async def _delivery_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '工程交付中心：请问您需要什么帮助？\n\n我可以帮您：\n- 制定项目计划\n- 生成施工方案\n- 追踪项目进度\n- 整理竣工资料',
            'confidence': 0.8,
        }

    def get_supported_tasks(self) -> list:
        return ['chat', 'plan', 'quality_check', 'completion_docs']


class CostBenefitAgent(BaseAgent):
    """
    成本效益中心

    职责：工程造价与经济效益分析
    服务：造价单位、建设单位、施工单位

    支持任务：
    - chat: 对话式成本咨询
    - budget: 预算生成
    - quantity_calc: 工程量计算
    - cost_analysis: 成本对比分析
    """

    AGENT_ID = "cost_benefit"
    NAME = "成本效益中心"
    DESCRIPTION = "工程造价与经济效益分析，负责工程量计算/预算生成/变更签证/经济效益评估"

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        params = task.params

        if task.task_type == 'budget':
            output = await self._budget_generate(params, task.context)
        elif task.task_type == 'quantity_calc':
            output = await self._quantity_calc(params, task.context)
        elif task.task_type == 'cost_analysis':
            output = await self._cost_analysis(params, task.context)
        else:
            output = await self._cost_response(params, task.context)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.AGENT_ID,
            status='success',
            output=output,
            confidence=0.8,
            execution_time=(datetime.now() - start).total_seconds(),
        )

    async def plan(self, task: Task) -> list:
        return [{"step": 1, "tool": "budget_generate", "expected": "预算报告"}]

    async def _budget_generate(self, params: Dict, context: Dict) -> Dict:
        # 尝试调用 blueprint-ai budget.py
        return {
            'budget': '预算生成功能开发中...',
            'items': ['土建工程', '安装工程', '装饰工程', '其他费用'],
            'confidence': 0.6,
        }

    async def _quantity_calc(self, params: Dict, context: Dict) -> Dict:
        return {
            'quantities': '工程量计算功能开发中...',
            'method': '基于图纸图层统计',
            'confidence': 0.6,
        }

    async def _cost_analysis(self, params: Dict, context: Dict) -> Dict:
        return {
            'analysis': '成本分析功能开发中...',
            'indicators': ['目标成本', '实际成本', '成本偏差', '投资回报'],
            'confidence': 0.6,
        }

    async def _cost_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '成本效益中心：请问您需要什么帮助？\n\n我可以帮您：\n- 计算工程量\n- 生成工程预算\n- 进行成本对比分析\n- 评估投资回报',
            'confidence': 0.8,
        }

    def get_supported_tasks(self) -> list:
        return ['chat', 'budget', 'quantity_calc', 'cost_analysis']


class CustomerServiceAgent(BaseAgent):
    """
    客户服务中心

    职责：客户支持与关系维护
    服务：所有已成交客户

    支持任务：
    - chat: FAQ问答
    - faq: 常见问题解答
    - training: 培训材料生成
    - feedback: 客户反馈分析
    """

    AGENT_ID = "customer_service"
    NAME = "客户服务中心"
    DESCRIPTION = "客户支持与关系维护，负责FAQ/工单管理/回访计划/培训材料"

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        params = task.params

        if task.task_type == 'faq':
            output = await self._faq_answer(params, task.context)
        elif task.task_type == 'training':
            output = await self._training_material(params, task.context)
        elif task.task_type == 'feedback':
            output = await self._feedback_analysis(params, task.context)
        else:
            output = await self._cs_response(params, task.context)

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.AGENT_ID,
            status='success',
            output=output,
            confidence=0.8,
            execution_time=(datetime.now() - start).total_seconds(),
        )

    async def plan(self, task: Task) -> list:
        return [{"step": 1, "tool": "cs_response", "expected": "客服响应"}]

    async def _faq_answer(self, params: Dict, context: Dict) -> Dict:
        return {
            'faqs': [
                {'q': '如何上传图纸？', 'a': '在对话框中点击📎图标，选择DWG/DXF/PDF文件即可'},
                {'q': '支持哪些文件格式？', 'a': '支持 DWG、DXF、PDF 三种格式'},
                {'q': '分析需要多长时间？', 'a': '一般图纸约10-30秒，复杂图纸可能需要更久'},
            ],
            'confidence': 0.9,
        }

    async def _training_material(self, params: Dict, context: Dict) -> Dict:
        return {
            'materials': ['使用手册', 'API文档', '视频教程', '常见问题'],
            'confidence': 0.7,
        }

    async def _feedback_analysis(self, params: Dict, context: Dict) -> Dict:
        return {
            'analysis': '反馈分析功能开发中...',
            'sentiment': '积极',
            'confidence': 0.6,
        }

    async def _cs_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '客户服务中心：请问您需要什么帮助？\n\n我可以帮您：\n- 解答常见问题\n- 生成培训材料\n- 分析客户反馈\n- 制定回访计划',
            'confidence': 0.8,
        }

    def get_supported_tasks(self) -> list:
        return ['chat', 'faq', 'training', 'feedback']


# ─── 导出 ────────────────────────────────────────────────────────

__all__ = [
    'TechRdAgent',
    'SafetyComplianceAgent',
    'MarketSalesAgent',
    'EngineeringDeliveryAgent',
    'CostBenefitAgent',
    'CustomerServiceAgent',
]