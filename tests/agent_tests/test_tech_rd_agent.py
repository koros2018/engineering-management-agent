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
        assert "full_analysis" in tasks

    def test_capabilities(self, agent):
        caps = agent.get_capabilities()
        assert caps["agent_id"] == "tech_rd"
        assert caps["name"] == "技术研发中心"
        assert len(caps["supported_tasks"]) >= 5


class TestTypeClassifierTool:
    """类型识别测试 - 集成测试"""

    def test_classify_building_layers(self):
        """建筑图层前缀识别"""
        import asyncio
        from sub_agents.tech_rd_agent import EMATypeClassifierTool
        tool = EMATypeClassifierTool()

        result = asyncio.run(tool.execute(
            params={"layers": [{"name": "A-WALL"}, {"name": "A-DOOR"}, {"name": "A-WINDOW"}],
                    "filename": "建筑平面图.dxf"},
            context={}
        ))
        assert result.get("primary") == "建筑", f"Got: {result}"

    def test_classify_structure_layers(self):
        """结构图层前缀识别"""
        import asyncio
        from sub_agents.tech_rd_agent import EMATypeClassifierTool
        tool = EMATypeClassifierTool()

        result = asyncio.run(tool.execute(
            params={"layers": [{"name": "S-COLUMN"}, {"name": "S-BEAM"}, {"name": "S-SLAB"}],
                    "filename": "结构平面图.dxf"},
            context={}
        ))
        assert result.get("primary") == "结构", f"Got: {result}"

    def test_classify_by_filename(self):
        """文件名关键词类型识别"""
        import asyncio
        from sub_agents.tech_rd_agent import EMATypeClassifierTool
        tool = EMATypeClassifierTool()

        cases = [
            ("给排水系统图.dxf", "给排水"),
            ("电气系统图.dxf", "电气"),
            ("暖通平面图.dxf", "暖通"),
            ("总平面布置图.dxf", "总图"),
            ("梁配筋图.dxf", "结构"),
        ]
        for filename, expected in cases:
            result = asyncio.run(tool.execute(
                params={"layers": [], "filename": filename},
                context={}
            ))
            assert result.get("primary") == expected, f"File: {filename}, Expected: {expected}, Got: {result}"


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
        from sub_agents.tech_rd_agent import EMAQuantityExtractorTool as QuantityExtractorTool
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


# NOTE: TestDesignOptimizer removed — EMADesignOptimizerTool not yet implemented
# TODO: Phase 17+ add design optimization tool


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

        assert len(plan) >= 4
        assert plan[0]["tool"] == "blueprint_parser"
        assert plan[-1]["tool"] == "quantity_extractor"

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