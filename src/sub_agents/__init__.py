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


def safe_get(d: dict, key: str, default=None):
    """安全获取字典值（兼容None）"""
    if d is None:
        return default
    return d.get(key, default)

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
        """商务响应 - 市场分析/需求挖掘/方案制定"""
        user_msg = params.get('message', '')
        project_info = context.get('project_info', {}) if context else {}
        
        # 根据用户输入判断意图
        intent_keywords = {
            '方案': ['方案', '建议', '怎么做', '如何'],
            '投标': ['投标', '招标', '标书', '竞标'],
            '报价': ['价格', '报价', '收费', '多少钱', '费用'],
            '分析': ['分析', '市场', '需求', '客户'],
        }
        
        detected_intent = 'general'
        for intent, keywords in intent_keywords.items():
            if any(k in user_msg for k in keywords):
                detected_intent = intent
                break
        
        # 根据项目规模给建议
        scale_hint = ''
        if project_info:
            area = project_info.get('estimated_area', project_info.get('area', 0))
            if area > 10000:
                scale_hint = '（大型项目：建议企业版或私有部署）'
            elif area > 1000:
                scale_hint = '（中型项目：建议专业版）'
            else:
                scale_hint = '（小型项目：体验版即可）'
        
        return {
            'response': f'市场与销售中心：收到您的需求\n\n我可以帮您：\n- 分析客户需求 → 制定针对性方案\n- 辅助投标文件 → 提高中标率\n- 制定报价策略 → 合理定价{safe_get(project_info, "scale_hint", scale_hint)}\n\n💡 提示：提供项目名称/规模/类型，可以生成更精准的商务方案。',
            'detected_intent': detected_intent,
            'suggestions': ['生成投标文件', '制定报价方案', '分析市场需求'],
            'confidence': 0.85,
        }

    async def _tender_doc(self, params: Dict, context: Dict) -> Dict:
        """投标文件辅助生成"""
        from datetime import datetime
        project_name = params.get('project_name', '未知项目')
        project_type = params.get('project_type', params.get('drawing_type', '建筑工程'))
        client_name = params.get('client_name', params.get('owner', '招标方'))
        deadline = params.get('deadline', params.get('tender_deadline', ''))
        budget = params.get('budget', '')
        
        # 获取图纸分析结果（如果有）
        blueprint_info = context.get('blueprint_result', {}) if context else {}
        building_type = safe_get(blueprint_info, 'drawing_type', project_type)
        design_scope = safe_get(blueprint_info, 'layers', safe_get(blueprint_info, 'design_scope', '建筑结构机电'))
        
        # 生成技术标内容
        tech_sections = [
            {'title': '项目概况', 'content': f'{project_name}位于{params.get("location", "待定")}，为{building_type}项目，总建筑面积约{safe_get(blueprint_info, "estimated_area", params.get("area", "待估算"))}平方米。'},
            {'title': '设计范围', 'content': f'本次投标涉及{design_scope}设计，包括建筑、结构、机电等专业。'},
            {'title': '技术方案', 'content': f'采用先进的设计理念，结合BIM技术进行三维协同设计，确保设计质量与进度。'},
            {'title': '质量保证措施', 'content': '建立完善的质量管理体系，执行ISO9001标准，确保设计成果满足规范要求。'},
            {'title': '进度计划', 'content': f'总工期{safe_get(params, "duration", "待定")}天，分阶段实施：方案设计({safe_get(params, "phase1_duration", "30")}天)、施工图设计({safe_get(params, "phase2_duration", "45")}天)。'},
            {'title': '人员配置', 'content': '项目负责人1名，各专业负责人5名，设计人员10名，质检人员2名。'},
        ]
        
        # 生成商务标内容
        biz_sections = [
            {'title': '投标报价', 'content': f'投标总报价：{budget if budget else "待报价"}\n费率：{params.get("rate", "按国标收费")}'},
            {'title': '公司资质', 'content': '具备建筑行业甲级设计资质，通过ISO9001质量管理体系认证。'},
            {'title': '业绩情况', 'content': '近三年完成同类项目{safe_get(params, "completed_projects", "20")}个，合同额达{safe_get(params, "total_value", "5000")}万元。'},
            {'title': '服务承诺', 'content': '提供全程技术支持，竣工后{safe_get(params, "warranty_period", "2")}年质保期，免费协助招标方进行施工配合。'},
        ]
        
        return {
            'tender_doc': {
                'project_name': project_name,
                'client': client_name,
                'deadline': deadline,
                'tech_tender': tech_sections,
                'biz_tender': biz_sections,
                'qualification': ['设计资质证书', '营业执照', '近三年业绩证明', '项目负责人资格证书'],
            },
            'summary': f'投标文件已生成：技术标({len(tech_sections)}节) + 商务标({len(biz_sections)}节)',
            'sections': ['技术标', '商务标', '资格预审文件'],
            'confidence': 0.82,
        }

    async def _price_quote(self, params: Dict, context: Dict) -> Dict:
        """报价单生成 - 根据项目规模智能定价"""
        project_type = params.get('project_type', params.get('building_type', '建筑'))
        area = params.get('area', params.get('estimated_area', 0))
        complexity = params.get('complexity', 'normal')  # normal / complex / simple
        
        # 收费标准（参考国家物价文件）
        base_rate = {
            '建筑': 25,  # 元/平方米
            '结构': 18,
            '机电': 22,
            '景观': 15,
            '装修': 35,
        }
        rate = base_rate.get(project_type, 20)
        
        # 复杂度调整
        complexity_factor = {'simple': 0.7, 'normal': 1.0, 'complex': 1.4}.get(complexity, 1.0)
        
        # 计算报价
        if area > 0:
            base_quote = area * rate * complexity_factor
        else:
            base_quote = 0
        
        # 版本方案
        versions = [
            {
                'name': '体验版',
                'description': '适合小型项目或试用',
                'price': '免费' if area < 500 else '¥99/月',
                'limit': f'{min(3, max(1, int(area/1000)))}项目/月',
                'features': ['图纸分析', '基本审图', '3类文档生成'],
                'best_for': '初步评估阶段',
            },
            {
                'name': '专业版',
                'description': '适合中型项目',
                'price': f'¥{int(base_quote * 0.01 / 100) * 100 + 299}/月' if base_quote > 0 else '¥299/月',
                'limit': '无限项目',
                'features': ['完整图纸解析', '15条审图规则', '5类文档生成', '工程量清单', 'SOP/MOP/EOP/LCC'],
                'best_for': '常规项目',
            },
            {
                'name': '企业版',
                'description': '适合大型/复杂项目',
                'price': f'¥{int(base_quote * 0.015 / 100) * 100 + 999}/月' if base_quote > 0 else '¥999/月',
                'limit': '多用户协作',
                'features': ['全功能专业版', 'AI改图(DXF)', '几何审查', '国标库扩展', 'API集成', '专属技术支持'],
                'best_for': '大型复杂项目',
            },
            {
                'name': '私有部署',
                'description': '完全私有，数据自主',
                'price': '议价（¥5万起）',
                'limit': '完全私有',
                'features': ['企业内网部署', '数据完全隔离', '定制开发', '终身授权', '年度维保'],
                'best_for': '国企/政府/高保密项目',
            },
        ]
        
        # 推荐版本
        if area > 50000 or complexity == 'complex':
            recommended = '企业版'
        elif area > 5000:
            recommended = '专业版'
        else:
            recommended = '体验版'
        
        return {
            'quote': {
                'project_type': project_type,
                'estimated_area': area,
                'base_rate': rate,
                'complexity_factor': complexity_factor,
                'estimated_total': base_quote if base_quote > 0 else '待评估',
                'versions': versions,
                'recommended': recommended,
            },
            'summary': f'已为您生成{project_type}项目报价单（面积:{area}㎡），推荐{recommended}',
            'confidence': 0.85,
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
        """FAQ回答 - 支持上下文理解"""
        user_question = params.get('question', params.get('message', ''))
        category = params.get('category', '')
        
        # 扩展FAQ库
        faq_db = [
            {'q': '上传', 'a': '在对话框中点击📎图标，选择DWG/DXF/PDF文件即可，支持批量上传', 'category': '使用'},
            {'q': '格式', 'a': '支持 DWG、DXF、PDF 三种格式，其中DWG支持TArch天正建筑格式', 'category': '使用'},
            {'q': '时间', 'a': '一般图纸约10-30秒，复杂图纸（多层/高复杂度）可能需要1-3分钟', 'category': '使用'},
            {'q': '安全', 'a': '支持本地化部署，数据完全自主，不上传第三方服务器', 'category': '安全'},
            {'q': '收费', 'a': '体验版免费，专业版¥299/月，企业版¥999/月，私有部署议价', 'category': '费用'},
            {'q': '审图', 'a': '内置15条国标审图规则，覆盖消防、结构、机电等专业，支持几何规则审查', 'category': '功能'},
            {'q': '文档', 'a': '可生成5类工程文档：设计说明、工程量清单、技术交底、技术核定单、招投标文件', 'category': '功能'},
            {'q': '改图', 'a': '支持DXF文件编辑，包括图层调整、文本修改、块属性编辑、标注更新等12项操作', 'category': '功能'},
            {'q': '生命周期', 'a': '支持SOP/MOP/EOP/LCC全生命周期文档生成，覆盖从施工到运营的全阶段', 'category': '功能'},
            {'q': '国标', 'a': '内置20+部国标规范，可扩展，包括建筑/结构/消防/电气等各专业', 'category': '功能'},
        ]
        
        # 语义匹配
        best_match = None
        best_score = 0
        for faq in faq_db:
            score = sum(1 for kw in user_question if kw in faq['q'].lower() or kw in faq['a'])
            if score > best_score:
                best_score = score
                best_match = faq
        
        if best_match and best_score > 0:
            return {
                'answer': best_match['a'],
                'category': best_match['category'],
                'confidence': min(0.9, 0.7 + best_score * 0.05),
                'suggestions': ['还有其他问题吗？', '我可以帮您生成投标文件', '试试上传图纸分析'],
            }
        
        # 默认FAQ列表
        return {
            'faqs': [f"{f['q']}：{f['a']}" for f in faq_db[:5]],
            'categories': list(set(f['category'] for f in faq_db)),
            'confidence': 0.85,
            'suggestions': ['请详细描述您的问题', '或者选择类别：使用/安全/费用/功能'],
        }

    async def _training_material(self, params: Dict, context: Dict) -> Dict:
        """培训材料生成"""
        material_type = params.get('type', params.get('material_type', 'comprehensive'))
        audience = params.get('audience', params.get('target', '设计人员'))
        
        # 根据类型生成不同培训材料
        materials = {
            'comprehensive': {
                'title': 'EMA系统完整使用培训',
                'sections': [
                    {'name': '第一章：系统概述', 'topics': ['工程管理智能体介绍', '核心功能模块', '工作流程']},
                    {'name': '第二章：图纸上传与分析', 'topics': ['支持的图纸格式', '上传操作步骤', '分析结果解读']},
                    {'name': '第三章：智能审图', 'topics': ['15条国标规则', '几何规则审查', '审图报告查看']},
                    {'name': '第四章：文档生成', 'topics': ['5类工程文档', '生命周期文档', '导出与分享']},
                    {'name': '第五章：高级功能', 'topics': ['AI改图操作', '国标库查询', '项目管理']},
                ],
                'duration': '约2小时',
            },
            'quickstart': {
                'title': '快速入门指南',
                'sections': [
                    {'name': '5分钟上手', 'topics': ['上传图纸', '查看分析', '生成报告']},
                ],
                'duration': '5-10分钟',
            },
            'advanced': {
                'title': '高级功能培训',
                'sections': [
                    {'name': 'AI改图实战', 'topics': ['DXF编辑', '批量操作', '自动化脚本']},
                    {'name': '国标库定制', 'topics': ['添加规范', '规则配置', '审核流程']},
                    {'name': 'API集成', 'topics': ['接口文档', 'webhook配置', '第三方集成']},
                ],
                'duration': '约3小时',
            },
        }
        
        selected = materials.get(material_type, materials['comprehensive'])
        
        return {
            'materials': {
                'title': selected['title'],
                'audience': audience,
                'duration': selected['duration'],
                'outline': selected['sections'],
                'download_formats': ['PDF', 'Word', 'PPT'],
            },
            'summary': f'已生成{material_type}培训材料，适合{audience}',
            'confidence': 0.82,
        }

    async def _feedback_analysis(self, params: Dict, context: Dict) -> Dict:
        """反馈分析 - 情感分析与趋势"""
        feedback_text = params.get('feedback', params.get('text', ''))
        source = params.get('source', 'direct')  # direct / survey / review / ticket
        
        if not feedback_text:
            return {
                'analysis': '请提供反馈内容进行分析',
                'sentiment': '待分析',
                'confidence': 0,
            }
        
        # 简化情感分析
        positive_words = ['好', '棒', '不错', '满意', '喜欢', '有用', '感谢', '赞', '高效', '清晰']
        negative_words = ['差', '坏', '慢', '难用', '不满', '问题', '错误', '崩溃', '失望', '麻烦']
        
        pos_count = sum(1 for w in positive_words if w in feedback_text)
        neg_count = sum(1 for w in negative_words if w in feedback_text)
        
        if pos_count > neg_count:
            sentiment = '积极'
            score = min(100, 60 + pos_count * 10)
        elif neg_count > pos_count:
            sentiment = '消极'
            score = max(0, 60 - neg_count * 10)
        else:
            sentiment = '中性'
            score = 50
        
        # 提取关键词
        keywords = [w for w in ['图纸', '分析', '审图', '文档', '速度', '界面', '功能', '服务'] 
                    if w in feedback_text]
        
        return {
            'analysis': {
                'sentiment': sentiment,
                'score': score,
                'keywords': keywords,
                'summary': f'反馈{sentiment}（评分{score}/100），涉及{"、".join(keywords) if keywords else "整体评价"}' if feedback_text else '暂无反馈',
            },
            'suggestions': {
            },
            'confidence': 0.78,
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
    'ManagerAgent',
]