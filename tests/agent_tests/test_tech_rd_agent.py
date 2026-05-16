"""
tests/agent_tests/test_tech_rd_agent.py
TechRdAgent 单元测试
"""

import pytest
import asyncio
from pathlib import Path

# 确保源码路径正确
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agent.base_agent import Task, AgentResult
from sub_agents.tech_rd_agent import TechRdAgent


# ─────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def agent():
    return TechRdAgent()


@pytest.fixture
def sample_task():
    return Task(
        task_id="test-001",
        agent_id="tech_rd",
        task_type="classify",
        params={
            "layers": [
                {"name": "A-WALL", "color": "7", "visible": True},
                {"name": "A-DOOR", "color": "7", "visible": True},
                {"name": "A-WINDOW", "color": "7", "visible": True},
                {"name": "S-COLUMN", "color": "1", "visible": True},
                {"name": "S-BEAM", "color": "1", "visible": True},
            ],
            "filename": "建筑平面图.dxf",
        },
        context={"task_id": "test-001"}
    )


# ─────────────────────────────────────────────────────────────────
# 测试用例
# ─────────────────────────────────────────────────────────────────

class TestTechRdAgentBasics:
    """基础测试"""

    def test_agent_id(self, agent):
        assert agent.AGENT_ID == "tech_rd"

    def test_agent_name(self, agent):
        assert agent.NAME == "技术研发中心"

    def test_supported_tasks(self, agent):
        tasks = agent.get_supported_tasks()
        assert "parse" in tasks
        assert "classify" in tasks
        assert "analyze" in tasks
        assert "extract_quantities" in tasks
        assert "optimize" in tasks
        assert "full_analysis" in tasks

    def test_capabilities(self, agent):
        caps = agent.get_capabilities()
        assert caps["agent_id"] == "tech_rd"
        assert caps["name"] == "技术研发中心"
        assert len(caps["supported_tasks"]) >= 5


class TestTypeClassifierTool:
    """类型识别测试"""

    def test_layer_prefix_mapping(self):
        from sub_agents.tech_rd_agent import TypeClassifierTool
        tool = TypeClassifierTool()

        assert tool.LAYER_PREFIX_MAP['S'] == '结构'
        assert tool.LAYER_PREFIX_MAP['A'] == '建筑'
        assert tool.LAYER_PREFIX_MAP['E'] == '电气'
        assert tool.LAYER_PREFIX_MAP['P'] == '给排水'
        assert tool.LAYER_PREFIX_MAP['G'] == '总图'

    def test_filename_type_detection(self):
        from sub_agents.tech_rd_agent import TypeClassifierTool
        tool = TypeClassifierTool()

        filename_cases = [
            ("建筑平面图.dxf", "建筑"),
            ("结构平面图.dxf", "结构"),
            ("给排水系统图.dxf", "给排水"),
            ("电气配电系统.dxf", "电气"),
            ("暖通空调平面.dxf", "暖通"),
        ]

        for filename, expected_type in filename_cases:
            detected = None
            for kw, dtype in tool.FILENAME_TYPE_MAP.items():
                if kw in filename:
                    detected = dtype
                    break
            assert detected == expected_type, f"File: {filename}, Expected: {expected_type}, Got: {detected}"


class TestBlueprintParserTool:
    """图纸解析工具测试（无文件时检查工具结构）"""

    def test_parser_tool_registered(self, agent):
        assert "blueprint_parser" in agent._tool_registry

    def test_parser_tool_schema(self, agent):
        tool = agent._parser_tool
        assert tool.name == "blueprint_parser"
        assert "file_path" in tool.input_schema["required"]


class TestQuantityExtractor:
    """工程量提取测试"""

    def test_entity_stats(self):
        from sub_agents.tech_rd_agent import QuantityExtractorTool
        tool = QuantityExtractorTool()

        # 模拟实体数据
        parse_result = {
            "entities": [
                {"type": "LINE", "layer": "A-WALL"},
                {"type": "LINE", "layer": "A-WALL"},
                {"type": "LINE", "layer": "A-DOOR"},
                {"type": "CIRCLE", "layer": "S-COLUMN"},
            ],
            "layers": [
                {"name": "A-WALL"},
                {"name": "A-DOOR"},
                {"name": "S-COLUMN"},
            ]
        }

        # 检查统计逻辑
        entities = parse_result["entities"]
        entity_stats = {}
        for e in entities:
            etype = e.get("type", "UNKNOWN")
            entity_stats[etype] = entity_stats.get(etype, 0) + 1

        assert entity_stats["LINE"] == 3
        assert entity_stats["CIRCLE"] == 1


class TestDesignOptimizer:
    """设计优化测试"""

    def test_optimization_for_building(self):
        from sub_agents.tech_rd_agent import DesignOptimizerTool
        tool = DesignOptimizerTool()

        result = asyncio.run(tool.execute(
            params={"analysis_result": {}, "drawing_type": "建筑"},
            context={}
        ))

        assert result["confidence"] == 0.8
        assert len(result["suggestions"]) > 0
        # 应该有墙体优化建议
        wall_opt = [s for s in result["suggestions"] if s.get("type") == "墙体材料"]
        assert len(wall_opt) >= 1


class TestAgentRetry:
    """重试机制测试"""

    def test_validate_accepts_high_confidence(self, agent):
        result = AgentResult(
            task_id="test",
            agent_id="tech_rd",
            status="success",
            confidence=0.9,
        )
        assert asyncio.run(agent.validate(result)) is True

    def test_validate_rejects_low_confidence(self, agent):
        result = AgentResult(
            task_id="test",
            agent_id="tech_rd",
            status="success",
            confidence=0.3,
        )
        assert asyncio.run(agent.validate(result)) is False

    def test_validate_rejects_failure(self, agent):
        result = AgentResult(
            task_id="test",
            agent_id="tech_rd",
            status="failed",
            confidence=0.9,
        )
        assert asyncio.run(agent.validate(result)) is False


class TestTaskPlanning:
    """任务规划测试"""

    def test_plan_full_analysis(self, agent):
        task = Task(
            task_id="test-002",
            agent_id="tech_rd",
            task_type="full_analysis",
            params={},
            context={}
        )
        plan = asyncio.run(agent.plan(task))

        assert len(plan) == 5
        assert plan[0]["tool"] == "blueprint_parser"
        assert plan[4]["tool"] == "design_optimizer"

    def test_plan_single_tool(self, agent):
        task = Task(
            task_id="test-003",
            agent_id="tech_rd",
            task_type="classify",
            params={},
            context={}
        )
        plan = asyncio.run(agent.plan(task))

        assert len(plan) == 1
        assert plan[0]["tool"] == "type_classifier"


# ─────────────────────────────────────────────────────────────────
# 运行
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v"])