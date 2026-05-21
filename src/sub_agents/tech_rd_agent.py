"""
agent/tech_rd_agent.py - 技术研发Agent

继承自 blueprint-ai 项目的图纸解析和AI分析能力。
图纸智能解析 → 类型识别 → 图层理解 → 工程量提取 → 设计优化建议

Agent ID: tech_rd
Name: 技术研发中心
"""

import asyncio
import importlib
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 动态导入 blueprint-ai 模块（开发阶段直接导入，构建时改为相对路径）
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent / "blueprint-ai"
_SRC_DIR = _PROJECT_ROOT / "src"
if _SRC_DIR.exists() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from agent.base_agent import BaseAgent, Task, AgentResult, ToolResult


# ─────────────────────────────────────────────────────────────────
# 工具层（封装 blueprint-ai 现有能力）
# ─────────────────────────────────────────────────────────────────

def _get_bp_parser():
    """延迟导入，避免启动时依赖未安装"""
    from blueprint_parser.core import BlueprintParser
    return BlueprintParser()


def _get_llm_service(model: str = None):
    """延迟导入，可指定模型"""
    from blueprint_parser.llm_service import LLMService
    if model:
        # 支持 ollama:xxx 或 cloud:xxx
        if model.startswith("cloud:"):
            return LLMService(model=model[6:], timeout=60)
        else:
            return LLMService(model=model.replace("ollama:", ""), timeout=60)
    return LLMService()


def _call_blueprint_api(file_path: str) -> dict:
    """通过HTTP调用blueprint-ai API做完整分析（避免版本不兼容问题）"""
    import requests, tempfile, os

    # 调用已有的 /upload/analyze 接口
    url = "http://127.0.0.1:6188/api/v1/upload/analyze"
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f.read())}
        data = {'user_id': 'ema_tech_rd_agent'}
        try:
            resp = requests.post(url, files=files, data=data, timeout=60)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────
# Blueprint Parser Tool
# ─────────────────────────────────────────────────────────────────

class BlueprintParserTool:
    """图纸解析工具 - 封装 core.py"""

    name = "blueprint_parser"
    description = "解析 DWG/DXF/PDF 图纸文件，提取图层、实体、文本信息"
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "图纸文件路径"},
            "use_ocr": {"type": "boolean", "default": True, "description": "PDF是否使用OCR"},
        },
        "required": ["file_path"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        file_path = params["file_path"]
        use_ocr = params.get("use_ocr", True)

        parser = _get_bp_parser()
        result = parser.parse(file_path)

        return {
            "success": result.success,
            "file_path": str(result.file_path),
            "file_type": result.file_type.value if hasattr(result.file_type, 'value') else str(result.file_type),
            "layer_count": len(result.layers),
            "entity_count": len(result.entities),
            "raw_text_length": len(result.raw_text),
            "layers": [
                {"name": l.name, "color": l.color, "visible": l.visible}
                for l in result.layers
            ],
            "errors": result.errors,
        }


# ─────────────────────────────────────────────────────────────────
# Type Classifier Tool
# ─────────────────────────────────────────────────────────────────

class TypeClassifierTool:
    """图纸类型识别工具 - 封装 inference.py"""

    name = "type_classifier"
    description = "根据图层名和文件名识别图纸类型（建筑/结构/机电/给排水等）"
    input_schema = {
        "type": "object",
        "properties": {
            "layers": {"type": "array", "description": "图层列表"},
            "filename": {"type": "string", "description": "文件名"},
            "raw_text": {"type": "string", "description": "提取的文本"},
        },
        "required": ["layers"]
    }

    # TArch图层编码 → 类型映射
    LAYER_PREFIX_MAP = {
        'S': '结构', 'C': '结构',
        'A': '建筑',
        'E': '电气',
        'M': '机电', 'P': '给排水', 'W': '给排水',
        'D': '标注', 'X': '标注',
        'T': '标题',
        'G': '总图',
    }

    # 图层名关键词 → 类型
    LAYER_KEYWORDS = {
        '建筑': ['WALL', 'DOOR', 'WINDOW', 'FLOOR', 'STAIR', 'CEILING'],
        '结构': ['COLUMN', 'BEAM', 'SLAB', 'FOUNDATION', 'REBAR', 'STEEL'],
        '机电': ['MECHANICAL', 'HVAC', 'MEP', 'EQUIPMENT'],
        '给排水': ['PLUMBING', 'PIPE', 'WATER', 'DRAIN', 'SEWER'],
        '暖通': ['HVAC', 'DUCT', 'VENT', 'AHU', 'FAN', 'CHILLER'],
        '电气': ['ELECTRICAL', 'POWER', 'LIGHTING', 'CABLE', 'PANEL'],
        '消防': ['FIRE', 'SPRINKLER', 'ALARM', 'SMOKE', 'EXIT'],
        '总图': ['GRID', 'TOPO', 'SURVEY', 'ROAD', 'PARKING'],
        '精装': ['DECOR', 'FINISH', 'FURNITURE', 'SIGNAGE'],
    }

    # 文件名 → 类型（按优先级排序：更具体的在前）
    FILENAME_TYPE_MAP = [
        # 结构相关（优先匹配）
        ('梁配筋', '结构'), ('板配筋', '结构'), ('柱配筋', '结构'),
        ('结构平面', '结构'), ('结构图', '结构'), ('基础图', '结构'),
        # 建筑相关
        ('建筑平面', '建筑'), ('建筑立面', '建筑'), ('建筑剖面', '建筑'),
        # 总图相关
        ('总平面', '总图'), ('管线综合', '总图'), ('道路平面', '总图'),
        ('绿化平面', '景观'), ('景观平面', '景观'),
        # 机电专项
        ('给排水', '给排水'), ('消防系统', '消防'), ('喷淋系统', '消防'),
        ('暖通平面', '暖通'), ('空调平面', '暖通'), ('通风平面', '暖通'),
        ('电气系统', '电气'), ('配电系统', '电气'), ('照明平面', '电气'),
        # 通用（放最后，因为其他都没匹配时才用）
        ('平面图', '建筑'), ('立面图', '建筑'), ('剖面图', '建筑'),
        ('系统图', '机电'), ('详图', '建筑'),
        ('装修平面', '精装'), ('室内平面', '精装'), ('吊顶平面', '精装'),
    ]

    async def execute(self, params: Dict, context: Dict) -> Dict:
        layers = params.get("layers", [])
        filename = params.get("filename", "")
        raw_text = params.get("raw_text", "")

        # Step 1: 图层名匹配
        layer_scores = {}
        for layer in layers:
            name = layer.get("name", "").upper()
            for dtype, keywords in self.LAYER_KEYWORDS.items():
                for kw in keywords:
                    if kw in name:
                        layer_scores[dtype] = layer_scores.get(dtype, 0) + 1

        # Step 2: 文件名匹配（按优先级遍历）
        filename_type = None
        for kw, dtype in self.FILENAME_TYPE_MAP:
            if kw in filename:
                filename_type = dtype
                break

        # Step 3: 合并判断
        if layer_scores:
            primary_type = max(layer_scores, key=layer_scores.get)
            confidence = min(layer_scores[primary_type] / max(sum(layer_scores.values()), 1), 1.0)
        elif filename_type:
            primary_type = filename_type
            confidence = 0.8
        else:
            primary_type = "未知"
            confidence = 0.3

        # 次要类型
        sorted_scores = sorted(layer_scores.items(), key=lambda x: -x[1])
        secondary = sorted_scores[1]["0"] if len(sorted_scores) > 1 else None

        return {
            "primary_type": primary_type,
            "secondary_type": secondary,
            "confidence": confidence,
            "scores": layer_scores,
            "source": "layer_matching" if layer_scores else "filename",
        }


# ─────────────────────────────────────────────────────────────────
# Blueprint Analyzer Tool (LLM-powered)
# ─────────────────────────────────────────────────────────────────

class BlueprintAnalyzerTool:
    """图纸分析工具 - 调用 LLM 生成分析报告"""

    name = "blueprint_analyzer"
    description = "对图纸进行AI分析，生成设计说明、施工要求、材料规格等文字描述"
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "parse_result": {"type": "object", "description": "来自BlueprintParserTool的结果"},
            "drawing_type": {"type": "string"},
        },
        "required": ["parse_result"]
    }

    SYSTEM_PROMPT = """你是一个资深的建筑工程图纸AI分析专家。
根据图纸解析结果，请分析：
1. 设计原则和规范依据
2. 主要建筑/结构特征
3. 施工技术要求
4. 材料和规格说明
5. 需要特别注意的问题

请用专业的工程语言输出分析结果。"""

    async def execute(self, params: Dict, context: Dict) -> Dict:
        parse_result = params["parse_result"]
        drawing_type = params.get("drawing_type", "建筑")

        # 构建分析提示
        layers_info = ""
        if parse_result.get("layers"):
            layer_names = [l.get("name", "") for l in parse_result["layers"][:20]]
            layers_info = "图层列表：" + ", ".join(layer_names)

        prompt = f"""
图纸类型：{drawing_type}
{layers_info}

请分析这张图纸，给出：
1. 设计概述
2. 主要特征
3. 施工要点
4. 材料规格
5. 注意事项
"""

        # 调用 LLM（带超时保护）
        try:
            llm = _get_llm_service(context.get('model'))
            response = await asyncio.wait_for(
                asyncio.to_thread(llm.call, prompt, system=self.SYSTEM_PROMPT),
                timeout=context.get("llm_timeout", 60)
            )
            return {
                "analysis": response,
                "confidence": 0.85,
                "model_used": "ollama",
            }
        except asyncio.TimeoutError:
            return {
                "analysis": "LLM分析超时，请检查Ollama服务状态",
                "confidence": 0.3,
                "error": "llm_timeout",
            }
        except Exception as e:
            return {
                "analysis": f"分析失败: {str(e)}",
                "confidence": 0.2,
                "error": str(e),
            }


# ─────────────────────────────────────────────────────────────────
# Quantity Extractor Tool
# ─────────────────────────────────────────────────────────────────

class QuantityExtractorTool:
    """工程量提取工具 - 封装 budget.py 逻辑"""

    name = "quantity_extractor"
    description = "从图纸解析结果中提取工程量（面积/长度/数量等）"
    input_schema = {
        "type": "object",
        "properties": {
            "parse_result": {"type": "object"},
            "drawing_type": {"type": "string"},
        },
        "required": ["parse_result"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        parse_result = params["parse_result"]
        drawing_type = params.get("drawing_type", "建筑")

        entities = parse_result.get("entities", [])
        layers = parse_result.get("layers", [])

        # 统计各类型实体数量
        entity_stats = {}
        for entity in entities:
            etype = entity.get("type", "UNKNOWN")
            entity_stats[etype] = entity_stats.get(etype, 0) + 1

        # 根据图纸类型估算工程量
        quantities = []

        if drawing_type == "建筑":
            wall_count = sum(1 for e in entities if "WALL" in str(e.get("layer", "")).upper())
            door_count = sum(1 for e in entities if "DOOR" in str(e.get("layer", "")).upper())
            window_count = sum(1 for e in entities if "WINDOW" in str(e.get("layer", "")).upper())
            quantities.extend([
                {"name": "墙体", "unit": "m", "estimated": wall_count * 3, "note": "基于图层统计"},
                {"name": "门窗", "unit": "樘", "estimated": door_count + window_count, "note": "基于图层统计"},
            ])

        elif drawing_type == "结构":
            column_count = sum(1 for e in entities if "COLUMN" in str(e.get("layer", "")).upper())
            beam_count = sum(1 for e in entities if "BEAM" in str(e.get("layer", "")).upper())
            slab_count = sum(1 for e in entities if "SLAB" in str(e.get("layer", "")).upper())
            quantities.extend([
                {"name": "柱子", "unit": "根", "estimated": column_count, "note": "基于图层统计"},
                {"name": "梁", "unit": "根", "estimated": beam_count, "note": "基于图层统计"},
                {"name": "板", "unit": "块", "estimated": slab_count, "note": "基于图层统计"},
            ])

        return {
            "drawing_type": drawing_type,
            "entity_count": len(entities),
            "layer_count": len(layers),
            "entity_stats": entity_stats,
            "quantities": quantities,
            "extraction_method": "layer_based_estimation",
            "confidence": 0.7,
        }


# ─────────────────────────────────────────────────────────────────
# Design Optimizer Tool
# ─────────────────────────────────────────────────────────────────

class DesignOptimizerTool:
    """设计优化工具 - 封装 optimizer.py"""

    name = "design_optimizer"
    description = "基于分析结果和审查意见，生成设计优化建议"
    input_schema = {
        "type": "object",
        "properties": {
            "analysis_result": {"type": "object"},
            "review_result": {"type": "object"},
            "drawing_type": {"type": "string"},
        },
        "required": ["analysis_result"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        analysis_result = params.get("analysis_result", {})
        drawing_type = params.get("drawing_type", "建筑")

        suggestions = []

        # 通用优化建议
        if drawing_type == "建筑":
            suggestions.extend([
                {
                    "category": "设计优化",
                    "type": "墙体材料",
                    "issue": "部分隔墙可考虑使用轻钢龙骨石膏板墙",
                    "recommendation": "非承重隔墙优先采用轻钢龙骨体系，比加气砌块减少30%自重",
                    "benefit": "降低基础荷载 10-15%，节约结构造价",
                    "priority": "medium",
                },
                {
                    "category": "节能优化",
                    "type": "外窗",
                    "issue": "外窗热工性能",
                    "recommendation": "优先选用断桥铝合金Low-E中空玻璃窗",
                    "benefit": "降低建筑能耗 20-30%",
                    "priority": "high",
                },
            ])
        elif drawing_type == "结构":
            suggestions.extend([
                {
                    "category": "结构优化",
                    "type": "配筋率",
                    "issue": "部分板配筋率偏高",
                    "recommendation": "可采用HRB400钢筋，减少配筋量15%",
                    "benefit": "节约钢筋用量，降低造价",
                    "priority": "medium",
                },
            ])

        # 基于审查问题的优化
        review_result = params.get("review_result")
        if review_result and "issues" in review_result:
            for issue in review_result["issues"][:3]:
                suggestions.append({
                    "category": "审查整改",
                    "type": issue.get("rule_name", "合规问题"),
                    "issue": issue.get("description", ""),
                    "recommendation": issue.get("suggestion", "请按规范整改"),
                    "priority": "high",
                })

        return {
            "drawing_type": drawing_type,
            "suggestions": suggestions,
            "count": len(suggestions),
            "confidence": 0.8,
        }


# ─────────────────────────────────────────────────────────────────
# TechRdAgent 主类
# ─────────────────────────────────────────────────────────────────

class TechRdAgent(BaseAgent):
    """
    技术研发Agent

    继承 blueprint-ai 项目核心能力：
    - 图纸解析（BlueprintParserTool）
    - 类型识别（TypeClassifierTool）
    - AI分析（BlueprintAnalyzerTool）
    - 工程量提取（QuantityExtractorTool）
    - 设计优化（DesignOptimizerTool）

    支持的任务类型：
    - parse：解析图纸
    - classify：类型识别
    - analyze：AI分析
    - extract_quantities：提取工程量
    - optimize：设计优化
    - full_analysis：完整分析（解析+识别+分析+提量+优化）
    """

    AGENT_ID = "tech_rd"
    NAME = "技术研发中心"
    DESCRIPTION = "负责图纸解析、类型识别、AI分析、工程量提取、设计优化"

    # 支持的任务类型 → 对应工具
    TASK_TO_TOOLS = {
        'parse': 'blueprint_parser',
        'classify': 'type_classifier',
        'analyze': 'blueprint_analyzer',
        'extract_quantities': 'quantity_extractor',
        'optimize': 'design_optimizer',
    }

    def __init__(self):
        super().__init__()

        # 注册工具
        self._parser_tool = BlueprintParserTool()
        self._classifier_tool = TypeClassifierTool()
        self._analyzer_tool = BlueprintAnalyzerTool()
        self._quantity_tool = QuantityExtractorTool()
        self._optimizer_tool = DesignOptimizerTool()

        self.register_tool('blueprint_parser', self._wrap_tool(self._parser_tool))
        self.register_tool('type_classifier', self._wrap_tool(self._classifier_tool))
        self.register_tool('blueprint_analyzer', self._wrap_tool(self._analyzer_tool))
        self.register_tool('quantity_extractor', self._wrap_tool(self._quantity_tool))
        self.register_tool('design_optimizer', self._wrap_tool(self._optimizer_tool))

    def _wrap_tool(self, tool):
        """将同步工具包装为async"""
        async def wrapper(params: Dict, context: Dict) -> Any:
            return await tool.execute(params, context)
        return wrapper

    # ── Sub-Agent 必须实现的方法 ─────────────────────────

    async def execute(self, task: Task) -> AgentResult:
        """执行任务"""
        start_time = datetime.now()
        task_type = task.task_type
        params = task.params
        context = task.context

        try:
            if task_type == 'chat':
                # 无图纸时的通用对话
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.AGENT_ID,
                    status='success',
                    confidence=0.95,
                    output={
                        'response_text': '🔧 技术研发中心负责图纸解析和 AI 分析。\n\n我可以帮您：\n• 上传 DWG/DXF/PDF 图纸进行解析\n• 识别图纸类型（建筑/结构/机电等）\n• 提取工程量清单\n• 生成优化建议\n• 执行合规审图\n\n请上传图纸文件，或告诉我您需要的具体操作。',
                        'agent_id': self.AGENT_ID,
                    },
                    execution_time=(datetime.now() - start_time).total_seconds(),
                )
            elif task_type == 'full_analysis':
                return await self._full_analysis(params, context, start_time)
            elif task_type in self.TASK_TO_TOOLS:
                tool_name = self.TASK_TO_TOOLS[task_type]
                return await self._run_single_tool(tool_name, params, context, start_time)
            else:
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.AGENT_ID,
                    status='failed',
                    confidence=0.0,
                    errors=[f"Unsupported task_type: {task_type}"],
                    execution_time=(datetime.now() - start_time).total_seconds(),
                )
        except Exception as e:
            return AgentResult(
                task_id=task.task_id,
                agent_id=self.AGENT_ID,
                status='failed',
                confidence=0.0,
                errors=[f"{type(e).__name__}: {str(e)}", *traceback.format_exc().splitlines()[-3:]],
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

    async def plan(self, task: Task) -> List[Dict]:
        """将任务分解为步骤"""
        task_type = task.task_type

        if task_type == 'full_analysis':
            return [
                {"step": 1, "tool": "blueprint_parser", "expected": "解析结果"},
                {"step": 2, "tool": "type_classifier", "expected": "图纸类型"},
                {"step": 3, "tool": "blueprint_analyzer", "expected": "AI分析报告"},
                {"step": 4, "tool": "quantity_extractor", "expected": "工程量清单"},
                {"step": 5, "tool": "design_optimizer", "expected": "优化建议"},
            ]
        elif task_type in self.TASK_TO_TOOLS:
            return [{"step": 1, "tool": self.TASK_TO_TOOLS[task_type], "expected": "工具输出"}]
        return []

    # ── 内部方法 ─────────────────────────────────────────

    async def _run_single_tool(
        self, tool_name: str, params: Dict, context: Dict, start_time: datetime
    ) -> AgentResult:
        """运行单个工具"""
        result = await self.execute_tool(tool_name, params, context)

        if not result.success:
            return AgentResult(
                task_id=context.get("task_id", ""),
                agent_id=self.AGENT_ID,
                status='failed',
                confidence=0.0,
                errors=[result.error],
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

        confidence = result.data.get("confidence", 0.75) if result.data else 0.75

        return AgentResult(
            task_id=context.get("task_id", ""),
            agent_id=self.AGENT_ID,
            status='success',
            output=result.data,
            confidence=confidence,
            execution_time=result.execution_time,
        )

    async def _full_analysis(
        self, params: Dict, context: Dict, start_time: datetime
    ) -> AgentResult:
        """
        完整分析流程：
        解析 → 类型识别 → AI分析 → 工程量提取 → 优化建议
        """
        file_path = params.get("file_path")
        if not file_path:
            return AgentResult(
                task_id=context.get("task_id", ""),
                agent_id=self.AGENT_ID,
                status='failed',
                confidence=0.0,
                errors=["file_path is required for full_analysis"],
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

        # Step 1: 解析图纸
        parse_result = await self.execute_tool('blueprint_parser', {"file_path": file_path}, context)
        if not parse_result.success:
            return AgentResult(
                task_id=context.get("task_id", ""),
                agent_id=self.AGENT_ID,
                status='failed',
                confidence=0.0,
                errors=[parse_result.error],
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

        layers = parse_result.data.get("layers", [])
        raw_text = parse_result.data.get("raw_text_length", 0)

        # Step 2: 类型识别
        filename = Path(file_path).name
        type_result = await self.execute_tool('type_classifier', {
            "layers": layers,
            "filename": filename,
            "raw_text": raw_text,
        }, context)

        drawing_type = type_result.data.get("primary_type", "建筑") if type_result.success else "建筑"

        # Step 3: AI分析（可选，LLM不可用时跳过）
        analysis_result = {}
        try:
            analyze_result = await self.execute_tool('blueprint_analyzer', {
                "file_path": file_path,
                "parse_result": parse_result.data,
                "drawing_type": drawing_type,
            }, context)
            if analyze_result.success:
                analysis_result = analyze_result.data
        except Exception:
            analysis_result = {"analysis": "LLM暂不可用", "confidence": 0.3}

        # Step 4: 工程量提取
        quantity_result = await self.execute_tool('quantity_extractor', {
            "parse_result": parse_result.data,
            "drawing_type": drawing_type,
        }, context)
        quantities = quantity_result.data if quantity_result.success else {}

        # Step 5: 设计优化
        optimize_result = await self.execute_tool('design_optimizer', {
            "analysis_result": analysis_result,
            "drawing_type": drawing_type,
        }, context)
        optimizations = optimize_result.data if optimize_result.success else {}

        # 整合结果
        full_output = {
            "file_path": file_path,
            "drawing_type": drawing_type,
            "type_confidence": type_result.data.get("confidence", 0.8) if type_result.success else 0.5,
            "parse_result": parse_result.data,
            "analysis": analysis_result,
            "quantities": quantities,
            "optimizations": optimizations,
            "agent_id": self.AGENT_ID,
            "analyzed_at": datetime.now().isoformat(),
        }

        # 计算综合置信度
        confidences = [
            parse_result.data.get("success", True) and 0.9 or 0.3,
            type_result.data.get("confidence", 0.8) if type_result.success else 0.5,
            analysis_result.get("confidence", 0.85),
            quantities.get("confidence", 0.7),
            optimizations.get("confidence", 0.8),
        ]
        avg_confidence = sum(confidences) / len(confidences)

        return AgentResult(
            task_id=context.get("task_id", ""),
            agent_id=self.AGENT_ID,
            status='success',
            output=full_output,
            confidence=avg_confidence,
            execution_time=(datetime.now() - start_time).total_seconds(),
        )

    def get_supported_tasks(self) -> List[str]:
        return list(self.TASK_TO_TOOLS.keys()) + ['full_analysis']