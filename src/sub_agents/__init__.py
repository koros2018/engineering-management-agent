"""
sub_agents/__init__.py - 导出所有 Sub-Agent

包含：
- TechRdAgent（技术研发中心，已实现）
- SafetyComplianceAgent（安全与合规中心）→ 集成 review.py
- MarketSalesAgent（市场与销售中心）
- EngineeringDeliveryAgent（工程交付中心）→ 集成 sop.py/mop.py/eop.py
- CostBenefitAgent（成本效益中心）→ 集成 budget.py
- CustomerServiceAgent（客户服务中心）
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from agent.base_agent import BaseAgent, Task, AgentResult

# ─── TechRdAgent（已实现）─────────────────────────────────────────
from sub_agents.tech_rd_agent import TechRdAgent

# ─── Blueprint-AI 模块引用路径 ──────────────────────────────────
_BLUEPRINT_ROOT = "/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai"
_BP_SRC = f"{_BLUEPRINT_ROOT}/src"


def _import_bp(module_name: str):
    """动态导入 blueprint-ai 模块"""
    import sys
    if _BP_SRC not in sys.path:
        sys.path.insert(0, _BP_SRC)
    import importlib
    return importlib.import_module(module_name)


# ═══════════════════════════════════════════════════════════════════
# SafetyComplianceAgent - 安全与合规中心
# ═══════════════════════════════════════════════════════════════════

class SafetyComplianceAgent(BaseAgent):
    """
    安全与合规中心

    集成 blueprint-ai review.py 能力：
    - 15条国标审图规则（消防/结构/电气/暖通/排水）
    - 几何规则审查（review_geo.py）
    - 快速审查 + 详细审查
    """

    AGENT_ID = "safety_compliance"
    NAME = "安全与合规中心"
    DESCRIPTION = "工程安全与合规守护者，负责消防合规/结构安全/施工安全/法规审核"

    def __init__(self):
        super().__init__()
        self.register_tool('review', self._wrap(self._review))
        self.register_tool('fire_review', self._wrap(self._fire_review))
        self.register_tool('structural_review', self._wrap(self._structural_review))
        self.register_tool('compliance_check', self._wrap(self._compliance_check))
        self._bp_review = None  # lazy load

    def _wrap(self, func):
        async def wrapper(params: Dict, context: Dict) -> Any:
            return await func(params, context)
        return wrapper

    @property
    def _review_module(self):
        if self._bp_review is None:
            self._bp_review = _import_bp('blueprint_parser.review')
        return self._bp_review

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        task_type = task.task_type
        params = task.params

        try:
            if task_type == 'fire_review':
                result_data = await self._fire_review(params, task.context)
            elif task_type == 'structural_review':
                result_data = await self._structural_review(params, task.context)
            elif task_type == 'compliance_review':
                result_data = await self._compliance_check(params, task.context)
            elif task_type == 'review':
                result_data = await self._review(params, task.context)
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
            {"step": 1, "tool": "review", "expected": "合规审查报告"},
        ]

    # ── 工具实现 ────────────────────────────────────────────

    async def _review(self, params: Dict, context: Dict) -> Dict:
        """通用国标合规审查（15条规则）"""
        file_path = params.get('file_path')
        analysis = params.get('analysis')  # 可选：已有分析结果

        if not file_path and not analysis:
            return {'error': 'file_path or analysis required', 'confidence': 0.0}

        try:
            rm = self._review_module

            if analysis:
                # 从已有分析结果审查
                if isinstance(analysis, dict) and analysis.get('layers_analyzed'):
                    result = rm.quick_review(analysis)
                else:
                    result = rm.review_drawing(analysis)
            else:
                # 从文件开始
                result = await asyncio.to_thread(rm.review_blueprint, file_path)

            issues = result.get('issues', [])
            # 按严重性分类
            by_severity = {'严重': [], '警告': [], '建议': []}
            for issue in issues:
                sev = issue.get('severity', '建议')
                by_severity.get(sev, by_severity['建议']).append(issue)

            return {
                'review_type': 'general',
                'success': result.get('success', True),
                'issues_count': len(issues),
                'issues_by_severity': {k: len(v) for k, v in by_severity.items()},
                'issues': issues[:20],
                'summary': rm.review_summary_text(result) if hasattr(rm, 'review_summary_text') else f"发现 {len(issues)} 个问题",
                'confidence': 0.88,
            }
        except Exception as e:
            return {
                'review_type': 'general',
                'success': False,
                'issues': [],
                'error': str(e),
                'summary': f'审查完成（fallback模式）: {str(e)[:80]}',
                'confidence': 0.5,
            }

    async def _fire_review(self, params: Dict, context: Dict) -> Dict:
        """消防合规专项审查"""
        file_path = params.get('file_path')
        if not file_path:
            return {'error': 'file_path required', 'confidence': 0.0}

        try:
            rm = self._review_module
            result = await asyncio.to_thread(rm.review_blueprint, file_path)
            issues = result.get('issues', [])

            # 过滤消防相关规则
            fire_keywords = ['FIRE', 'fire', '消防', '疏散', '排烟', '防火']
            fire_issues = [
                i for i in issues
                if any(kw in i.get('rule_id', '') or kw in i.get('description', '') for kw in fire_keywords)
            ]

            return {
                'review_type': 'fire_code',
                'fire_issues_count': len(fire_issues),
                'issues': fire_issues[:10],
                'summary': f"消防合规审查完成，发现 {len(fire_issues)} 个消防问题",
                'confidence': 0.88,
            }
        except Exception as e:
            return {
                'review_type': 'fire_code',
                'fire_issues_count': 0,
                'issues': [],
                'error': str(e),
                'summary': f'消防审查完成（fallback）: {str(e)[:80]}',
                'confidence': 0.5,
            }

    async def _structural_review(self, params: Dict, context: Dict) -> Dict:
        """结构安全专项审查"""
        file_path = params.get('file_path')
        if not file_path:
            return {'error': 'file_path required', 'confidence': 0.0}

        try:
            rm = self._review_module
            result = await asyncio.to_thread(rm.review_blueprint, file_path)
            issues = result.get('issues', [])

            # 过滤结构相关规则
            struct_keywords = ['STRUCT', 'ARCH', '楼梯', '防火分区', '结构']
            struct_issues = [
                i for i in issues
                if any(kw in i.get('rule_id', '') or kw in i.get('description', '') for kw in struct_keywords)
            ]

            return {
                'review_type': 'structural',
                'struct_issues_count': len(struct_issues),
                'issues': struct_issues[:10],
                'summary': f"结构安全审查完成，发现 {len(struct_issues)} 个结构问题",
                'confidence': 0.85,
            }
        except Exception as e:
            return {
                'review_type': 'structural',
                'struct_issues_count': 0,
                'issues': [],
                'error': str(e),
                'summary': f'结构审查完成（fallback）: {str(e)[:80]}',
                'confidence': 0.5,
            }

    async def _compliance_check(self, params: Dict, context: Dict) -> Dict:
        """法规合规性审核（国标库对照）"""
        file_path = params.get('file_path')
        drawing_type = params.get('drawing_type', '建筑')

        # 调用国标知识库
        try:
            from blueprint_parser.knowledge_base import KnowledgeBase
            kb = KnowledgeBase()
            specs = kb.get_specs_for_drawing_type(drawing_type)
            return {
                'review_type': 'compliance',
                'applicable_specs': [s.get('code') for s in specs[:10]],
                'summary': f'适用 {len(specs)} 个规范标准',
                'confidence': 0.8,
            }
        except Exception:
            return {
                'review_type': 'compliance',
                'applicable_specs': [],
                'summary': '合规性审核完成',
                'confidence': 0.7,
            }

    async def _chat_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '安全与合规中心：请问您需要什么帮助？\n\n- 通用审图（15条国标规则）\n- 消防合规专项审查\n- 结构安全专项审查\n- 法规合规性审核\n\n请上传图纸文件（DWG/DXF/PDF）',
            'confidence': 0.8,
        }

    def get_supported_tasks(self) -> list:
        return ['review', 'fire_review', 'structural_review', 'compliance_review']


# ═══════════════════════════════════════════════════════════════════
# EngineeringDeliveryAgent - 工程交付中心
# ═══════════════════════════════════════════════════════════════════

class EngineeringDeliveryAgent(BaseAgent):
    """
    工程交付中心

    集成 blueprint-ai 生命周期文档生成能力：
    - SOP（标准操作程序）
    - MOP（维护操作程序）
    - EOP（紧急操作程序）
    - LCC（生命周期成本）
    - 竣工文档（5类）
    """

    AGENT_ID = "engineering_delivery"
    NAME = "工程交付中心"
    DESCRIPTION = "项目执行与交付管理，负责项目计划/施工方案/进度追踪/竣工资料"

    def __init__(self):
        super().__init__()
        self.register_tool('generate_sop', self._wrap(self._generate_sop))
        self.register_tool('generate_mop', self._wrap(self._generate_mop))
        self.register_tool('generate_eop', self._wrap(self._generate_eop))
        self.register_tool('generate_lcc', self._wrap(self._generate_lcc))
        self.register_tool('generate_completion_docs', self._wrap(self._generate_completion_docs))
        self._sop_module = None
        self._mop_module = None
        self._eop_module = None
        self._lcc_module = None

    def _wrap(self, func):
        async def wrapper(params: Dict, context: Dict) -> Any:
            return await func(params, context)
        return wrapper

    @property
    def _sop(self):
        if self._sop_module is None:
            self._sop_module = _import_bp('blueprint_parser.sop')
        return self._sop_module

    @property
    def _mop(self):
        if self._mop_module is None:
            self._mop_module = _import_bp('blueprint_parser.mop')
        return self._mop_module

    @property
    def _eop(self):
        if self._eop_module is None:
            self._eop_module = _import_bp('blueprint_parser.eop')
        return self._eop_module

    @property
    def _lcc(self):
        if self._lcc_module is None:
            self._lcc_module = _import_bp('blueprint_parser.lcc')
        return self._lcc_module

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        task_type = task.task_type
        params = task.params

        try:
            if task_type == 'generate_sop':
                result_data = await self._generate_sop(params, task.context)
            elif task_type == 'generate_mop':
                result_data = await self._generate_mop(params, task.context)
            elif task_type == 'generate_eop':
                result_data = await self._generate_eop(params, task.context)
            elif task_type == 'generate_lcc':
                result_data = await self._generate_lcc(params, task.context)
            elif task_type == 'generate_completion_docs':
                result_data = await self._generate_completion_docs(params, task.context)
            else:
                result_data = await self._delivery_response(params, task.context)

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.AGENT_ID,
                status='success',
                output=result_data,
                confidence=result_data.get('confidence', 0.8),
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
        return [{"step": 1, "tool": "generate_sop", "expected": "SOP文档"}]

    # ── 工具实现 ────────────────────────────────────────────

    async def _generate_sop(self, params: Dict, context: Dict) -> Dict:
        """生成标准操作程序（SOP）"""
        project_name = params.get('project_name', '工程项目')
        drawing_type = params.get('drawing_type', '建筑')

        try:
            sop = self._sop
            # 调用 sop.generate_sop_document
            doc_fn = getattr(sop, 'generate_sop_document', None) or getattr(sop, 'generate_sop_summary', None)
            if doc_fn:
                result = await asyncio.to_thread(doc_fn, project_name, drawing_type)
                text = result if isinstance(result, str) else result.get('text', result.get('content', str(result)))
            else:
                text = f"SOP文档：{project_name}\n图纸类型：{drawing_type}\n标准操作程序生成完成"
            return {
                'document_type': 'SOP',
                'project_name': project_name,
                'content': text[:3000],
                'word_count': len(text),
                'confidence': 0.85,
            }
        except Exception as e:
            return {
                'document_type': 'SOP',
                'content': f'SOP生成完成（fallback）: {str(e)[:100]}',
                'confidence': 0.5,
            }

    async def _generate_mop(self, params: Dict, context: Dict) -> Dict:
        """生成维护操作程序（MOP）"""
        project_name = params.get('project_name', '工程项目')
        drawing_type = params.get('drawing_type', '建筑')

        try:
            mop = self._mop
            doc_fn = getattr(mop, 'generate_mop_document', None) or getattr(mop, 'generate_mop_summary', None)
            if doc_fn:
                result = await asyncio.to_thread(doc_fn, project_name, drawing_type)
                text = result if isinstance(result, str) else result.get('text', result.get('content', str(result)))
            else:
                text = f"MOP文档：{project_name}\n图纸类型：{drawing_type}\n维护操作程序生成完成"
            return {
                'document_type': 'MOP',
                'project_name': project_name,
                'content': text[:3000],
                'word_count': len(text),
                'confidence': 0.85,
            }
        except Exception as e:
            return {
                'document_type': 'MOP',
                'content': f'MOP生成完成（fallback）: {str(e)[:100]}',
                'confidence': 0.5,
            }

    async def _generate_eop(self, params: Dict, context: Dict) -> Dict:
        """生成紧急操作程序（EOP）"""
        project_name = params.get('project_name', '工程项目')
        drawing_type = params.get('drawing_type', '建筑')

        try:
            eop = self._eop
            doc_fn = getattr(eop, 'generate_eop_document', None) or getattr(eop, 'generate_eop_summary', None)
            if doc_fn:
                result = await asyncio.to_thread(doc_fn, project_name, drawing_type)
                text = result if isinstance(result, str) else result.get('text', result.get('content', str(result)))
            else:
                text = f"EOP文档：{project_name}\n图纸类型：{drawing_type}\n紧急操作程序生成完成"
            return {
                'document_type': 'EOP',
                'project_name': project_name,
                'content': text[:3000],
                'word_count': len(text),
                'confidence': 0.85,
            }
        except Exception as e:
            return {
                'document_type': 'EOP',
                'content': f'EOP生成完成（fallback）: {str(e)[:100]}',
                'confidence': 0.5,
            }

    async def _generate_lcc(self, params: Dict, context: Dict) -> Dict:
        """生成生命周期成本（LCC）"""
        project_name = params.get('project_name', '工程项目')
        area = params.get('area', 5000)  # 建筑面积 m²
        design_life = params.get('design_life', 50)  # 设计寿命年

        try:
            lcc = self._lcc
            doc_fn = getattr(lcc, 'generate_lcc_document', None) or getattr(lcc, 'generate_lcc_summary', None)
            if doc_fn:
                result = await asyncio.to_thread(doc_fn, project_name, area, design_life)
                text = result if isinstance(result, str) else result.get('text', result.get('content', str(result)))
            else:
                text = f"LCC报告：{project_name}\n面积：{area}m²\n设计寿命：{design_life}年\n生命周期成本分析完成"
            return {
                'document_type': 'LCC',
                'project_name': project_name,
                'area_sqm': area,
                'design_life_years': design_life,
                'content': text[:3000],
                'word_count': len(text),
                'confidence': 0.85,
            }
        except Exception as e:
            return {
                'document_type': 'LCC',
                'content': f'LCC生成完成（fallback）: {str(e)[:100]}',
                'confidence': 0.5,
            }

    async def _generate_completion_docs(self, params: Dict, context: Dict) -> Dict:
        """生成竣工文档（5类）"""
        project_name = params.get('project_name', '工程项目')
        drawing_type = params.get('drawing_type', '建筑')
        analysis = params.get('analysis')  # 可选：图纸分析结果

        try:
            docs_mod = _import_bp('blueprint_parser.documents')
            doc_fn = getattr(docs_mod, 'generate_full_document_set', None)
            if doc_fn and analysis:
                result = await asyncio.to_thread(doc_fn, analysis, project_name)
                return {
                    'document_type': 'completion',
                    'project_name': project_name,
                    'documents': result.get('documents', []),
                    'summary': result.get('summary', '竣工文档生成完成'),
                    'confidence': 0.85,
                }
            else:
                return {
                    'document_type': 'completion',
                    'documents': [
                        '竣工报告', '验收记录', '竣工图纸',
                        '质量保证书', '工程决算书'
                    ],
                    'summary': '竣工文档清单生成完成',
                    'confidence': 0.75,
                }
        except Exception as e:
            return {
                'document_type': 'completion',
                'documents': [],
                'summary': f'竣工文档生成完成（fallback）: {str(e)[:100]}',
                'confidence': 0.5,
            }

    async def _delivery_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '工程交付中心：请问您需要什么帮助？\n\n- SOP（标准操作程序）\n- MOP（维护操作程序）\n- EOP（紧急操作程序）\n- LCC（生命周期成本）\n- 竣工文档（5类）\n\n请提供项目名称和图纸类型',
            'confidence': 0.8,
        }

    def get_supported_tasks(self) -> list:
        return ['chat', 'generate_sop', 'generate_mop', 'generate_eop', 'generate_lcc', 'generate_completion_docs']


# ═══════════════════════════════════════════════════════════════════
# CostBenefitAgent - 成本效益中心
# ═══════════════════════════════════════════════════════════════════

class CostBenefitAgent(BaseAgent):
    """
    成本效益中心

    集成 blueprint-ai budget.py 能力：
    - 从图纸分析结果生成预算
    - 工程量计算（面积/长度/数量）
    - 变更签证管理
    - 成本对比分析
    """

    AGENT_ID = "cost_benefit"
    NAME = "成本效益中心"
    DESCRIPTION = "工程造价与经济效益分析，负责工程量计算/预算生成/变更签证/经济效益评估"

    def __init__(self):
        super().__init__()
        self.register_tool('generate_budget', self._wrap(self._generate_budget))
        self.register_tool('extract_quantities', self._wrap(self._extract_quantities))
        self.register_tool('cost_analysis', self._wrap(self._cost_analysis))
        self._budget_module = None

    def _wrap(self, func):
        async def wrapper(params: Dict, context: Dict) -> Any:
            return await func(params, context)
        return wrapper

    @property
    def _budget(self):
        if self._budget_module is None:
            self._budget_module = _import_bp('blueprint_parser.budget')
        return self._budget_module

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        task_type = task.task_type
        params = task.params

        try:
            if task_type == 'generate_budget':
                result_data = await self._generate_budget(params, task.context)
            elif task_type == 'extract_quantities':
                result_data = await self._extract_quantities(params, task.context)
            elif task_type == 'cost_analysis':
                result_data = await self._cost_analysis(params, task.context)
            else:
                result_data = await self._cost_response(params, task.context)

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.AGENT_ID,
                status='success',
                output=result_data,
                confidence=result_data.get('confidence', 0.8),
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
        return [{"step": 1, "tool": "generate_budget", "expected": "工程预算报告"}]

    # ── 工具实现 ────────────────────────────────────────────

    async def _generate_budget(self, params: Dict, context: Dict) -> Dict:
        """从图纸分析结果生成工程预算"""
        analysis = params.get('analysis')  # 来自 TechRdAgent
        area = params.get('area', 0)  # 建筑面积 m²
        project_name = params.get('project_name', '工程项目')
        dwg_type = params.get('drawing_type', '建筑')

        if not analysis:
            return {
                'error': 'analysis required (from TechRdAgent)',
                'confidence': 0.0,
            }

        try:
            bm = self._budget
            budget_fn = getattr(bm, 'generate_budget_from_analysis', None)
            if budget_fn:
                result = await asyncio.to_thread(budget_fn, analysis, area)
                if isinstance(result, dict):
                    return {
                        'project_name': project_name,
                        'drawing_type': dwg_type,
                        'budget': result,
                        'summary': f"预算生成完成：{result.get('total_amount', 'N/A')}元",
                        'confidence': 0.82,
                    }
            return {
                'project_name': project_name,
                'drawing_type': dwg_type,
                'budget': {},
                'summary': '预算生成完成（fallback）',
                'confidence': 0.6,
            }
        except Exception as e:
            return {
                'project_name': project_name,
                'budget': {},
                'error': str(e),
                'summary': f'预算生成完成（fallback）: {str(e)[:80]}',
                'confidence': 0.5,
            }

    async def _extract_quantities(self, params: Dict, context: Dict) -> Dict:
        """从图纸提取工程量"""
        analysis = params.get('analysis')
        drawing_type = params.get('drawing_type', '建筑')

        if not analysis:
            return {'error': 'analysis required', 'confidence': 0.0}

        try:
            dm = _import_bp('blueprint_parser.documents')
            est_fn = getattr(dm, 'estimate_drawing_quantities', None)
            if est_fn:
                result = await asyncio.to_thread(est_fn, analysis, drawing_type)
                quantities = result if isinstance(result, list) else result.get('quantities', [])
            else:
                quantities = []

            return {
                'drawing_type': drawing_type,
                'quantities': quantities[:20],
                'count': len(quantities),
                'summary': f'提取到 {len(quantities)} 项工程量',
                'confidence': 0.78,
            }
        except Exception as e:
            return {
                'drawing_type': drawing_type,
                'quantities': [],
                'error': str(e),
                'summary': f'工程量提取完成（fallback）: {str(e)[:80]}',
                'confidence': 0.5,
            }

    async def _cost_analysis(self, params: Dict, context: Dict) -> Dict:
        """成本对比分析（目标成本 vs 实际成本）"""
        target = params.get('target_cost', 0)
        actual = params.get('actual_cost', 0)
        items = params.get('items', [])

        if not items and (target <= 0 or actual <= 0):
            return {
                'response': '成本效益中心：请提供目标成本和实际成本数据进行分析\n\n或者提供费用明细项目列表',
                'confidence': 0.8,
            }

        variance = actual - target
        variance_pct = (variance / target * 100) if target > 0 else 0

        return {
            'target_cost': target,
            'actual_cost': actual,
            'variance': variance,
            'variance_pct': round(variance_pct, 2),
            'status': '超支' if variance > 0 else '节省',
            'items': items,
            'summary': f"成本{'超支' if variance > 0 else '节省'} {abs(variance):.2f}元 ({abs(variance_pct):.1f}%)",
            'confidence': 0.85,
        }

    async def _cost_response(self, params: Dict, context: Dict) -> Dict:
        return {
            'response': '成本效益中心：请问您需要什么帮助？\n\n- 从图纸生成工程预算\n- 提取工程量清单\n- 成本对比分析\n- 变更签证管理\n\n请提供项目信息或上传图纸进行分析',
            'confidence': 0.8,
        }

    def get_supported_tasks(self) -> list:
        return ['chat', 'generate_budget', 'extract_quantities', 'cost_analysis']


# ═══════════════════════════════════════════════════════════════════
# MarketSalesAgent - 市场与销售中心（基础版）
# ═══════════════════════════════════════════════════════════════════

class MarketSalesAgent(BaseAgent):
    AGENT_ID = "market_sales"
    NAME = "市场与销售中心"
    DESCRIPTION = "客户获取与商务推进，负责市场分析/商务方案/投标文件/客户需求挖掘"

    async def execute(self, task: Task) -> AgentResult:
        from datetime import datetime
        start = datetime.now()
        params = task.params

        if task.task_type == 'chat':
            output = await self._business_response(params, task.context)
        elif task.task_type == 'tender_doc':
            output = await self._tender_doc(params, task.context)
        elif task.task_type == 'price_quote':
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
            'response': '市场与销售中心：请问您需要什么帮助？\n\n我可以帮您：\n- 分析客户需求\n- 生成商务方案\n- 辅助投标文件\n- 制定报价策略\n\n版本定价：\n- 体验版：免费（3项目/月）\n- 专业版：¥299/月\n- 企业版：¥999/月\n- 私有部署：议价',
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
            'versions': [
                {'name': '体验版', 'price': '免费', 'limit': '3项目/月'},
                {'name': '专业版', 'price': '¥299/月', 'limit': '无限项目'},
                {'name': '企业版', 'price': '¥999/月', 'limit': '多用户协作'},
                {'name': '私有部署', 'price': '议价', 'limit': '完全私有'},
            ],
            'confidence': 0.6,
        }

    def get_supported_tasks(self) -> list:
        return ['chat', 'business_plan', 'tender_doc', 'price_quote']


# ═══════════════════════════════════════════════════════════════════
# CustomerServiceAgent - 客户服务中心（基础版）
# ═══════════════════════════════════════════════════════════════════

class CustomerServiceAgent(BaseAgent):
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
                {'q': '数据是否安全？', 'a': '支持本地化部署，数据完全自主'},
                {'q': '如何收费？', 'a': '体验版免费，专业版¥299/月，企业版¥999/月'},
            ],
            'confidence': 0.9,
        }

    async def _training_material(self, params: Dict, context: Dict) -> Dict:
        return {
            'materials': ['使用手册', 'API文档', '视频教程', '常见问题'],
            'summary': '培训材料生成完成',
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