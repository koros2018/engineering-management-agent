"""
agent/tech_rd_agent.py - 技术研发Agent (Phase 8重构)

使用EMA自研blueprint模块（src/blueprint/），不再依赖blueprint-ai项目。
新增审查工具和文档生成工具，实现解析→审查→文档端到端工作流。

Agent ID: tech_rd
Name: 技术研发中心
"""

import asyncio
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.base_agent import BaseAgent, Task, AgentResult, ToolResult


# ─────────────────────────────────────────────────────────────────
# EMA Blueprint Parser Tool (使用自研模块)
# ─────────────────────────────────────────────────────────────────

class EMABlueprintParserTool:
    """图纸解析工具 - 使用EMA自研blueprint模块"""

    name = "blueprint_parser"
    description = "解析 DWG/DXF/PDF 图纸文件，提取图层、实体、文本信息"
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "图纸文件路径"},
            "use_ai": {"type": "boolean", "default": False, "description": "是否启用AI增强分析"},
        },
        "required": ["file_path"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        file_path = params["file_path"]
        use_ai = params.get("use_ai", False)

        from src.blueprint.core import BlueprintParser
        parser = BlueprintParser()

        if use_ai:
            result = parser.parse_with_ai(file_path)
        else:
            result = parser.parse(file_path)

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "未知错误")}

        parse_result = result.get("parse_result", result)
        return {
            "success": True,
            "file_path": file_path,
            "file_type": parse_result.get("file_type", ""),
            "layer_count": len(parse_result.get("layers", [])),
            "entity_count": len(parse_result.get("entities", [])),
            "raw_text_length": len(parse_result.get("raw_text", "")),
            "layers": parse_result.get("layers", []),
            "geometry": parse_result.get("geometry", {}),
            "layer_stats": parse_result.get("layer_stats", {}),
            "drawing_type": parse_result.get("drawing_type", {}),
            "ai_analysis": result.get("ai_analysis", {}),
        }


# ─────────────────────────────────────────────────────────────────
# EMA Type Classifier Tool
# ─────────────────────────────────────────────────────────────────

class EMATypeClassifierTool:
    """图纸类型识别工具 - 使用EMA自研classifier"""

    name = "type_classifier"
    description = "AI增强型图纸分类器（规则+LLM双引擎）"
    input_schema = {
        "type": "object",
        "properties": {
            "layers": {"type": "array", "description": "图层列表"},
            "filename": {"type": "string", "description": "文件名"},
            "raw_text": {"type": "string", "description": "提取的文本"},
            "use_llm": {"type": "boolean", "default": False},
        },
        "required": ["layers"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        layers = params.get("layers", [])
        filename = params.get("filename", "")
        raw_text = params.get("raw_text", "")
        use_llm = params.get("use_llm", False)

        from src.blueprint.ai.classifier import smart_classify

        layer_names = [l.get("name", "") if isinstance(l, dict) else str(l) for l in layers]
        blocks = params.get("blocks", [])

        result = smart_classify(
            layers=layer_names,
            blocks=blocks,
            raw_text=raw_text,
            file_name=filename,
            use_llm=use_llm,
        )
        return result


# ─────────────────────────────────────────────────────────────────
# EMA Review Tool (新增)
# ─────────────────────────────────────────────────────────────────

class EMAReviewTool:
    """图纸智能审查工具 - 使用EMA自研review模块"""

    name = "blueprint_review"
    description = "基于国标规范的图纸合规性审查"
    input_schema = {
        "type": "object",
        "properties": {
            "analysis_result": {"type": "object", "description": "图纸分析结果"},
            "file_path": {"type": "string", "description": "图纸文件路径"},
            "drawing_type": {"type": "string", "description": "图纸类型"},
        },
        "required": ["analysis_result"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        analysis = params.get("analysis_result", {})
        file_path = params.get("file_path", "")
        drawing_type = params.get("drawing_type", "")

        from src.blueprint.review.engine import review_analysis, review_blueprint

        if drawing_type:
            # 从分析结果中更新drawing_type
            analysis["drawing_type"] = {"primary": drawing_type, "confidence": 0.9}

        result = review_analysis(analysis)
        return result


# ─────────────────────────────────────────────────────────────────
# EMA Document Generator Tool (新增)
# ─────────────────────────────────────────────────────────────────

class EMADocumentTool:
    """工程文档生成工具 - 使用EMA自研documents模块"""

    name = "blueprint_documents"
    description = "生成工程文档（设计说明/技术交底/工程量清单/核定单/招投标）"
    input_schema = {
        "type": "object",
        "properties": {
            "analysis_result": {"type": "object", "description": "图纸分析结果"},
            "doc_types": {
                "type": "array",
                "default": ["all"],
                "description": "文档类型列表，或['all']生成全部"
            },
        },
        "required": ["analysis_result"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        analysis = params.get("analysis_result", {})
        doc_types = params.get("doc_types", ["all"])

        from src.blueprint.documents.generator import (
            generate_full_document_set,
            generate_design_description,
            generate_technical_disclosure,
            generate_quantity_list,
            generate_change_request,
            generate_bid_document,
        )

        if "all" in doc_types:
            result = generate_full_document_set(analysis)
        else:
            type_map = {
                "design_description": generate_design_description,
                "technical_disclosure": generate_technical_disclosure,
                "quantity_list": generate_quantity_list,
                "change_request": generate_change_request,
                "bid_document": generate_bid_document,
            }
            docs = {dt: type_map[dt](analysis) for dt in doc_types if dt in type_map}
            result = {"success": True, "analysis": analysis, "documents": docs}

        return result


# ─────────────────────────────────────────────────────────────────
# EMA AI Analyzer Tool
# ─────────────────────────────────────────────────────────────────

class EMAAIAnalyzerTool:
    """AI分析工具 - 使用EMA自研extractor+inference"""

    name = "blueprint_analyzer"
    description = "对图纸进行AI分析，提取工程信息、设计参数、材料规格"
    input_schema = {
        "type": "object",
        "properties": {
            "parse_result": {"type": "object", "description": "解析结果"},
            "drawing_type": {"type": "string"},
            "use_llm": {"type": "boolean", "default": False},
        },
        "required": ["parse_result"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        parse_result = params.get("parse_result", {})
        drawing_type = params.get("drawing_type", "")
        use_llm = params.get("use_llm", False)

        from src.blueprint.ai.extractor import smart_extract
        from src.blueprint.ai.inference import infer_design_principles, infer_construction_requirements
        from src.blueprint.ai.inference import infer_layer_semantics

        layers = parse_result.get("layers", [])
        raw_text = parse_result.get("raw_text", "")
        file_name = parse_result.get("file_name", "")

        layer_names = [l.get("name", "") if isinstance(l, dict) else str(l) for l in layers]

        # 工程信息提取
        extraction = smart_extract(
            raw_text=raw_text,
            file_name=file_name,
            drawing_type=drawing_type,
            layers=layer_names,
            use_llm=use_llm,
        )

        # 设计原则和施工要求
        semantics = infer_layer_semantics(layer_names)
        principles = infer_design_principles(layer_names, drawing_type)
        requirements = infer_construction_requirements(layer_names, drawing_type)

        return {
            "extraction": extraction,
            "semantics": semantics,
            "design_principles": principles,
            "construction_requirements": requirements,
            "confidence": extraction.get("confidence", 0.7),
            "llm_used": use_llm,
        }


# ─────────────────────────────────────────────────────────────────
# EMA Quantity Extractor Tool
# ─────────────────────────────────────────────────────────────────

class EMAQuantityExtractorTool:
    """工程量提取工具"""

    name = "quantity_extractor"
    description = "从图纸解析结果中提取工程量（面积/长度/数量等）"
    input_schema = {
        "type": "object",
        "properties": {
            "parse_result": {"type": "object"},
            "drawing_type": {"type": "string"},
            "geometry": {"type": "object"},
        },
        "required": ["parse_result"]
    }

    async def execute(self, params: Dict, context: Dict) -> Dict:
        parse_result = params.get("parse_result", {})
        drawing_type = params.get("drawing_type", "建筑")
        geometry = params.get("geometry", {})
        layer_stats = parse_result.get("layer_stats", {})

        quantities = []

        # 从geometry提取
        if geometry:
            if geometry.get("wall_length", 0) > 0:
                quantities.append({"name": "墙体长度", "unit": "m", "value": geometry["wall_length"], "source": "geometry"})
            if geometry.get("column_count", 0) > 0:
                quantities.append({"name": "柱子", "unit": "根", "value": geometry["column_count"], "source": "geometry"})
            if geometry.get("beam_length", 0) > 0:
                quantities.append({"name": "梁长度", "unit": "m", "value": geometry["beam_length"], "source": "geometry"})
            if geometry.get("slab_area", 0) > 0:
                quantities.append({"name": "楼板面积", "unit": "m²", "value": geometry["slab_area"], "source": "geometry"})
            if geometry.get("window_count", 0) > 0:
                quantities.append({"name": "窗户", "unit": "樘", "value": geometry["window_count"], "source": "geometry"})
            if geometry.get("door_count", 0) > 0:
                quantities.append({"name": "门", "unit": "樘", "value": geometry["door_count"], "source": "geometry"})

        # 从layer_stats估算
        for layer_name, stats in layer_stats.items():
            count = stats.get("entity_count", 0)
            if count > 0:
                lname = layer_name.upper()
                if "COLUMN" in lname or "柱" in lname:
                    quantities.append({"name": "柱子(估算)", "unit": "根", "value": count, "source": "layer_stats"})
                elif "BEAM" in lname or "梁" in lname:
                    quantities.append({"name": "梁(估算)", "unit": "根", "value": count, "source": "layer_stats"})
                elif "WALL" in lname or "墙" in lname:
                    quantities.append({"name": "墙体段(估算)", "unit": "段", "value": count, "source": "layer_stats"})

        return {
            "drawing_type": drawing_type,
            "quantities": quantities,
            "geometry_available": bool(geometry),
            "layer_stats_available": bool(layer_stats),
            "confidence": 0.8 if geometry else 0.6,
        }


# ─────────────────────────────────────────────────────────────────
# TechRdAgent 主类 (Phase 8重构)
# ─────────────────────────────────────────────────────────────────

class TechRdAgent(BaseAgent):
    """
    技术研发Agent (Phase 8重构)

    使用EMA自研blueprint模块，不再依赖blueprint-ai项目。
    新增审查和文档生成能力。

    支持的任务类型：
    - parse：解析图纸
    - classify：类型识别
    - analyze：AI分析
    - review：智能审查
    - documents：文档生成
    - extract_quantities：提取工程量
    - full_pipeline：端到端（解析→分类→AI分析→审查→文档）
    - full_analysis：完整分析（解析+识别+分析+提量）
    """

    AGENT_ID = "tech_rd"
    NAME = "技术研发中心"
    DESCRIPTION = "负责图纸解析、类型识别、AI分析、智能审查、文档生成、工程量提取"

    TASK_TO_TOOLS = {
        'parse': 'blueprint_parser',
        'classify': 'type_classifier',
        'analyze': 'blueprint_analyzer',
        'review': 'blueprint_review',
        'documents': 'blueprint_documents',
        'extract_quantities': 'quantity_extractor',
    }

    def __init__(self):
        super().__init__()

        # 注册所有工具
        self._parser_tool = EMABlueprintParserTool()
        self._classifier_tool = EMATypeClassifierTool()
        self._review_tool = EMAReviewTool()
        self._document_tool = EMADocumentTool()
        self._analyzer_tool = EMAAIAnalyzerTool()
        self._quantity_tool = EMAQuantityExtractorTool()

        self.register_tool('blueprint_parser', self._wrap_tool(self._parser_tool))
        self.register_tool('type_classifier', self._wrap_tool(self._classifier_tool))
        self.register_tool('blueprint_review', self._wrap_tool(self._review_tool))
        self.register_tool('blueprint_documents', self._wrap_tool(self._document_tool))
        self.register_tool('blueprint_analyzer', self._wrap_tool(self._analyzer_tool))
        self.register_tool('quantity_extractor', self._wrap_tool(self._quantity_tool))

    def _wrap_tool(self, tool):
        async def wrapper(params: Dict, context: Dict) -> Any:
            return await tool.execute(params, context)
        return wrapper

    async def execute(self, task: Task) -> AgentResult:
        """执行任务"""
        start_time = datetime.now()
        task_type = task.task_type
        params = task.params
        context = task.context

        try:
            if task_type == 'chat':
                return AgentResult(
                    task_id=task.task_id,
                    agent_id=self.AGENT_ID,
                    status='success',
                    confidence=0.95,
                    output={
                        'response_text': '🔧 技术研发中心 (EMA自研blueprint模块)\n\n支持操作：\n• 图纸解析 (DWG/DXF/PDF)\n• AI类型识别\n• 智能审查（15条国标规则）\n• 工程文档生成（设计说明/交底/清单/招投标）\n• 工程量提取\n• 端到端流水线（解析→审查→文档）',
                        'agent_id': self.AGENT_ID,
                    },
                    execution_time=(datetime.now() - start_time).total_seconds(),
                )
            elif task_type == 'full_pipeline':
                return await self._full_pipeline(params, context, start_time)
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
        task_type = task.task_type

        if task_type == 'full_pipeline':
            return [
                {"step": 1, "tool": "blueprint_parser", "expected": "解析结果+几何数据"},
                {"step": 2, "tool": "type_classifier", "expected": "图纸类型"},
                {"step": 3, "tool": "blueprint_analyzer", "expected": "AI分析+工程信息提取"},
                {"step": 4, "tool": "blueprint_review", "expected": "审查报告"},
                {"step": 5, "tool": "blueprint_documents", "expected": "工程文档集"},
            ]
        elif task_type == 'full_analysis':
            return [
                {"step": 1, "tool": "blueprint_parser", "expected": "解析结果"},
                {"step": 2, "tool": "type_classifier", "expected": "图纸类型"},
                {"step": 3, "tool": "blueprint_analyzer", "expected": "AI分析报告"},
                {"step": 4, "tool": "quantity_extractor", "expected": "工程量清单"},
            ]
        elif task_type in self.TASK_TO_TOOLS:
            return [{"step": 1, "tool": self.TASK_TO_TOOLS[task_type], "expected": "工具输出"}]
        return []

    async def _run_single_tool(self, tool_name, params, context, start_time):
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

    async def _full_pipeline(self, params, context, start_time):
        """
        端到端流水线：解析 → 分类 → AI分析 → 审查 → 文档
        Phase 8核心工作流
        """
        file_path = params.get("file_path")
        if not file_path:
            return AgentResult(
                task_id=context.get("task_id", ""),
                agent_id=self.AGENT_ID,
                status='failed',
                confidence=0.0,
                errors=["file_path is required for full_pipeline"],
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

        use_llm = params.get("use_llm", False)
        doc_types = params.get("doc_types", ["all"])

        # Step 1: 解析图纸
        parse_result = await self.execute_tool('blueprint_parser', {
            "file_path": file_path,
            "use_ai": use_llm,
        }, context)
        if not parse_result.success:
            return AgentResult(
                task_id=context.get("task_id", ""),
                agent_id=self.AGENT_ID,
                status='failed',
                confidence=0.0,
                errors=[f"解析失败: {parse_result.error}"],
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

        parsed = parse_result.data
        layers = parsed.get("layers", [])
        layer_names = [l.get("name", "") if isinstance(l, dict) else str(l) for l in layers]
        raw_text = parsed.get("raw_text", "")
        geometry = parsed.get("geometry", {})
        layer_stats = parsed.get("layer_stats", {})
        drawing_type_info = parsed.get("drawing_type", {})

        # Step 2: 类型识别
        filename = Path(file_path).name
        type_result = await self.execute_tool('type_classifier', {
            "layers": layer_names,
            "filename": filename,
            "raw_text": raw_text,
            "use_llm": use_llm,
        }, context)
        drawing_type = type_result.data.get("primary_type", "建筑") if type_result.success else "建筑"

        # Step 3: AI分析
        analysis_result = {}
        try:
            analyze_result = await self.execute_tool('blueprint_analyzer', {
                "parse_result": parsed,
                "drawing_type": drawing_type,
                "use_llm": use_llm,
            }, context)
            if analyze_result.success:
                analysis_result = analyze_result.data
        except Exception:
            analysis_result = {"extraction": {}, "confidence": 0.3}

        # 构建审查用的analysis dict
        review_analysis = {
            "file_name": filename,
            "drawing_type": {"primary": drawing_type, "confidence": 0.85},
            "layers": layer_names,
            "layer_stats": layer_stats,
            "entities": [],
            "geometry": geometry,
            "ai_analysis": analysis_result,
        }

        # Step 4: 智能审查
        review_result = await self.execute_tool('blueprint_review', {
            "analysis_result": review_analysis,
            "drawing_type": drawing_type,
        }, context)
        review = review_result.data if review_result.success else {}

        # Step 5: 文档生成
        doc_result = await self.execute_tool('blueprint_documents', {
            "analysis_result": review_analysis,
            "doc_types": doc_types,
        }, context)
        documents = doc_result.data if doc_result.success else {}

        # 整合结果
        pipeline_output = {
            "file_path": file_path,
            "drawing_type": drawing_type,
            "pipeline_steps": ["parse", "classify", "analyze", "review", "documents"],
            "parse": {
                "layer_count": len(layers),
                "entity_count": parsed.get("entity_count", 0),
                "file_type": parsed.get("file_type", ""),
            },
            "classification": type_result.data if type_result.success else {},
            "ai_analysis": analysis_result,
            "review": review,
            "documents": documents,
            "agent_id": self.AGENT_ID,
            "analyzed_at": datetime.now().isoformat(),
        }

        return AgentResult(
            task_id=context.get("task_id", ""),
            agent_id=self.AGENT_ID,
            status='success',
            output=pipeline_output,
            confidence=analysis_result.get("confidence", 0.75),
            execution_time=(datetime.now() - start_time).total_seconds(),
        )

    async def _full_analysis(self, params, context, start_time):
        """
        完整分析流程（原有功能）：解析 → 类型识别 → AI分析 → 工程量提取
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

        parsed = parse_result.data
        layers = parsed.get("layers", [])
        layer_names = [l.get("name", "") if isinstance(l, dict) else str(l) for l in layers]

        # Step 2: 类型识别
        filename = Path(file_path).name
        type_result = await self.execute_tool('type_classifier', {
            "layers": layer_names,
            "filename": filename,
            "raw_text": parsed.get("raw_text", ""),
        }, context)
        drawing_type = type_result.data.get("primary_type", "建筑") if type_result.success else "建筑"

        # Step 3: AI分析
        analysis_result = {}
        try:
            analyze_result = await self.execute_tool('blueprint_analyzer', {
                "parse_result": parsed,
                "drawing_type": drawing_type,
            }, context)
            if analyze_result.success:
                analysis_result = analyze_result.data
        except Exception:
            analysis_result = {"extraction": {}, "confidence": 0.3}

        # Step 4: 工程量提取
        quantity_result = await self.execute_tool('quantity_extractor', {
            "parse_result": parsed,
            "drawing_type": drawing_type,
            "geometry": parsed.get("geometry", {}),
        }, context)
        quantities = quantity_result.data if quantity_result.success else {}

        full_output = {
            "file_path": file_path,
            "drawing_type": drawing_type,
            "type_confidence": type_result.data.get("confidence", 0.8) if type_result.success else 0.5,
            "parse_result": parsed,
            "analysis": analysis_result,
            "quantities": quantities,
            "agent_id": self.AGENT_ID,
            "analyzed_at": datetime.now().isoformat(),
        }

        return AgentResult(
            task_id=context.get("task_id", ""),
            agent_id=self.AGENT_ID,
            status='success',
            output=full_output,
            confidence=analysis_result.get("confidence", 0.75),
            execution_time=(datetime.now() - start_time).total_seconds(),
        )

    def get_supported_tasks(self) -> List[str]:
        return list(self.TASK_TO_TOOLS.keys()) + ['full_analysis', 'full_pipeline']
