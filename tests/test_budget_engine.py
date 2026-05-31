#!/usr/bin/env python3
"""
tests/test_budget_engine.py - 成本预算引擎单元测试

Phase 21: 工程量提取 + 单价匹配 + 造价计算
"""
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tools.budget_engine import (
    load_unit_prices,
    get_unit_price,
    extract_quantities_from_analysis,
    calculate_budget,
    generate_budget_from_analysis,
    generate_budget_report,
    export_budget_json,
    export_budget_report,
    REGION_FACTOR,
    UNIT_COST_PER_SQM,
    BudgetEngine,
)


# ── 测试数据 ──────────────────────────────────────────────────

def make_analysis(drawing_type="建筑", area_sqm=5000, layers=None, entities=None):
    """构造测试用的分析结果"""
    if layers is None:
        layers = [
            {"name": "WALL", "color": "7", "visible": True},
            {"name": "COLUMN", "color": "1", "visible": True},
            {"name": "BEAM", "color": "3", "visible": True},
            {"name": "SLAB", "color": "5", "visible": True},
            {"name": "DOOR", "color": "2", "visible": True},
            {"name": "WINDOW", "color": "4", "visible": True},
        ]
    if entities is None:
        entities = [
            {"type": "LINE", "layer": "WALL"},
            {"type": "LINE", "layer": "WALL"},
            {"type": "INSERT", "layer": "DOOR"},
            {"type": "INSERT", "layer": "WINDOW"},
        ]
    return {
        "ai_analysis": {
            "drawing_type": {"primary": drawing_type},
            "project_info": {"building_area": f"{area_sqm} ㎡"},
        },
        "file_name": "test_project.dxf",
        "parse_result": {
            "layers": layers,
            "entities": entities,
            "metadata": {},
        },
    }


# ── 单价库测试 ────────────────────────────────────────────────

class TestUnitPrices:
    def test_load_prices(self):
        prices = load_unit_prices()
        assert isinstance(prices, dict)
        assert len(prices) > 0

    def test_get_existing_price(self):
        prices = load_unit_prices()
        info = get_unit_price(prices, "混凝土浇筑")
        assert info is not None
        assert "unit_price" in info
        assert info["unit_price"] > 0

    def test_get_missing_price(self):
        prices = load_unit_prices()
        info = get_unit_price(prices, "不存在的项目")
        assert info is None

    def test_price_categories(self):
        prices = load_unit_prices()
        # 检查至少有土建和安装
        categories = [k for k in prices if not k.startswith("_")]
        assert len(categories) >= 4


# ── 工程量提取测试 ────────────────────────────────────────────

class TestExtractQuantities:
    def test_basic_extraction(self):
        analysis = make_analysis()
        quantities = extract_quantities_from_analysis(analysis)
        assert isinstance(quantities, list)
        assert len(quantities) > 0

    def test_quantity_has_required_fields(self):
        analysis = make_analysis()
        quantities = extract_quantities_from_analysis(analysis)
        for q in quantities:
            assert "item_name" in q
            assert "category" in q
            assert "unit" in q
            assert "quantity" in q
            assert "unit_price" in q
            assert "total_price" in q

    def test_quantity_math(self):
        analysis = make_analysis()
        quantities = extract_quantities_from_analysis(analysis)
        for q in quantities:
            expected = round(q["quantity"] * q["unit_price"], 2)
            assert q["total_price"] == expected

    def test_structural_drawing(self):
        analysis = make_analysis(
            drawing_type="结构",
            layers=[
                {"name": "COLUMN", "color": "1", "visible": True},
                {"name": "BEAM", "color": "3", "visible": True},
                {"name": "REBAR", "color": "6", "visible": True},
            ]
        )
        quantities = extract_quantities_from_analysis(analysis)
        assert len(quantities) > 0
        # 应该有混凝土和钢筋
        item_names = [q["item_name"] for q in quantities]
        assert any("混凝土" in n for n in item_names)

    def test_empty_analysis(self):
        """空分析结果应返回空列表"""
        analysis = make_analysis(layers=[], entities=[])
        quantities = extract_quantities_from_analysis(analysis)
        assert isinstance(quantities, list)


# ── 造价计算测试 ──────────────────────────────────────────────

class TestCalculateBudget:
    def test_basic_calculation(self):
        quantities = [
            {"item_name": "混凝土浇筑", "category": "土建工程",
             "unit": "m³", "quantity": 100, "unit_price": 680,
             "total_price": 68000, "source": "test", "note": ""},
        ]
        budget = calculate_budget(quantities, area_sqm=5000, city="")
        assert budget["summary"]["total_cost"] > 0
        assert budget["summary"]["direct_cost"] == 68000

    def test_region_factor(self):
        quantities = [
            {"item_name": "混凝土浇筑", "category": "土建工程",
             "unit": "m³", "quantity": 100, "unit_price": 680,
             "total_price": 68000, "source": "test", "note": ""},
        ]
        budget_bj = calculate_budget(quantities, area_sqm=5000, city="北京")
        budget_default = calculate_budget(quantities, area_sqm=5000, city="")
        # 北京系数1.25 > 默认1.0
        assert budget_bj["summary"]["direct_cost"] > budget_default["summary"]["direct_cost"]
        assert budget_bj["region_factor"] == 1.25

    def test_cost_per_sqm(self):
        quantities = [
            {"item_name": "混凝土浇筑", "category": "土建工程",
             "unit": "m³", "quantity": 100, "unit_price": 680,
             "total_price": 68000, "source": "test", "note": ""},
        ]
        budget = calculate_budget(quantities, area_sqm=5000, city="")
        assert budget["summary"]["cost_per_sqm"] > 0
        # 单位造价 = 总造价 / 面积
        expected = budget["summary"]["total_cost"] / 5000
        assert abs(budget["summary"]["cost_per_sqm"] - expected) < 1

    def test_subtotals(self):
        quantities = [
            {"item_name": "混凝土浇筑", "category": "土建工程",
             "unit": "m³", "quantity": 100, "unit_price": 680,
             "total_price": 68000, "source": "test", "note": ""},
            {"item_name": "钢筋制安", "category": "土建工程",
             "unit": "t", "quantity": 5, "unit_price": 5800,
             "total_price": 29000, "source": "test", "note": ""},
            {"item_name": "电气配管", "category": "安装工程",
             "unit": "m", "quantity": 200, "unit_price": 45,
             "total_price": 9000, "source": "test", "note": ""},
        ]
        budget = calculate_budget(quantities, area_sqm=5000, city="")
        assert "土建工程" in budget["subtotals"]
        assert "安装工程" in budget["subtotals"]
        assert budget["subtotals"]["土建工程"] == 97000  # 68000 + 29000

    def test_empty_quantities(self):
        budget = calculate_budget([], area_sqm=5000, city="")
        assert budget["summary"]["direct_cost"] == 0
        assert budget["summary"]["total_cost"] >= 0


# ── 完整流程测试 ──────────────────────────────────────────────

class TestGenerateBudget:
    def test_full_pipeline(self):
        analysis = make_analysis()
        budget = generate_budget_from_analysis(analysis, city="北京", project_name="测试项目")
        assert budget["project_name"] == "测试项目"
        assert budget["area_sqm"] == 5000
        assert budget["drawing_type"] == "建筑"
        assert len(budget["quantities"]) > 0
        assert budget["summary"]["total_cost"] > 0

    def test_auto_area_estimate(self):
        """未指定面积时应自动估算"""
        analysis = make_analysis(area_sqm=0)
        budget = generate_budget_from_analysis(analysis)
        assert budget["area_sqm"] > 0

    def test_default_quantities(self):
        """无图层无实体时应生成默认工程量"""
        analysis = make_analysis(layers=[], entities=[])
        budget = generate_budget_from_analysis(analysis)
        assert len(budget["quantities"]) > 0

    def test_different_drawing_types(self):
        for dtype in ["建筑", "结构", "给排水", "电气", "暖通"]:
            analysis = make_analysis(drawing_type=dtype)
            budget = generate_budget_from_analysis(analysis)
            assert budget["drawing_type"] == dtype
            assert budget["summary"]["total_cost"] > 0


# ── 报告生成测试 ──────────────────────────────────────────────

class TestReport:
    def test_report_not_empty(self):
        analysis = make_analysis()
        budget = generate_budget_from_analysis(analysis, city="上海")
        report = generate_budget_report(budget)
        assert len(report) > 100
        assert "工程预算书" in report
        assert "总造价" in report

    def test_report_contains_key_data(self):
        analysis = make_analysis()
        budget = generate_budget_from_analysis(analysis, city="北京", project_name="测试大厦")
        report = generate_budget_report(budget)
        assert "测试大厦" in report
        assert "北京" in report

    def test_export_json(self, tmp_path):
        analysis = make_analysis()
        budget = generate_budget_from_analysis(analysis)
        path = str(tmp_path / "budget.json")
        export_budget_json(budget, path)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["summary"]["total_cost"] == budget["summary"]["total_cost"]

    def test_export_report(self, tmp_path):
        analysis = make_analysis()
        budget = generate_budget_from_analysis(analysis)
        path = str(tmp_path / "budget_report.txt")
        export_budget_report(budget, path)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert len(content) > 100


# ── 单例测试 ──────────────────────────────────────────────────

class TestBudgetEngine:
    def test_instance(self):
        eng = BudgetEngine()
        assert eng is not None
        assert hasattr(eng, 'generate_budget')
        assert hasattr(eng, 'generate_report')

    def test_engine_generate(self):
        eng = BudgetEngine()
        analysis = make_analysis()
        budget = eng.generate_budget(analysis, city="北京")
        assert budget["summary"]["total_cost"] > 0

    def test_engine_report(self):
        eng = BudgetEngine()
        analysis = make_analysis()
        budget = eng.generate_budget(analysis)
        report = eng.generate_report(budget)
        assert "工程预算书" in report


# ── 地区系数测试 ──────────────────────────────────────────────

class TestRegionFactor:
    def test_beijing_factor(self):
        assert REGION_FACTOR["北京"] == 1.25

    def test_shanghai_factor(self):
        assert REGION_FACTOR["上海"] == 1.22

    def test_default_factor(self):
        assert REGION_FACTOR["default"] == 1.0

    def test_unknown_city_uses_default(self):
        quantities = [
            {"item_name": "混凝土浇筑", "category": "土建工程",
             "unit": "m³", "quantity": 100, "unit_price": 680,
             "total_price": 68000, "source": "test", "note": ""},
        ]
        budget = calculate_budget(quantities, area_sqm=5000, city="未知城市")
        assert budget["region_factor"] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
