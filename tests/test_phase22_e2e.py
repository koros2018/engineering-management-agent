#!/usr/bin/env python3
"""
tests/test_phase22_e2e.py - Phase 22 E2E全链路测试

客户试用场景验证：
1. 上传图纸 → 分析 → 预算计算 → 报告生成
2. 上传图纸 → 分析 → 知识库推荐 → 规范查询
3. 上传图纸 → 分析 → 智能审查 → 文档生成
4. 完整流水线：上传 → 分析 → 审查 → 预算 → 文档 → LCC

需要API服务在 6188 端口运行。
"""

import os
import sys
import json
import time
import requests
import pytest

API = "http://127.0.0.1:6188"
E2E_DIR = os.path.join(os.path.dirname(__file__), "e2e")

# 测试DXF文件
TEST_DXFS = [
    ("C0000-7004-011 钢结构安装说明.dxf", "钢结构安装说明"),
    ("C448D-0002-010 总平面布置图_P3_A_A1.dxf", "总平面布置图"),
]


def upload_and_analyze(filepath):
    """上传并分析图纸，返回分析结果"""
    with open(filepath, "rb") as f:
        r = requests.post(
            f"{API}/api/v1/upload/analyze",
            files={"file": (os.path.basename(filepath), f, "application/dxf")},
            timeout=60,
        )
    assert r.status_code == 200, f"上传失败: {r.status_code}"
    data = r.json()
    assert data.get("success"), f"分析失败: {data}"
    return data["analysis"]


class TestBudgetE2E:
    """预算引擎 E2E 测试"""

    @pytest.mark.parametrize("filepath,name", [
        (os.path.join(E2E_DIR, f), n) for f, n in TEST_DXFS
        if os.path.exists(os.path.join(E2E_DIR, f))
    ])
    def test_budget_calculate(self, filepath, name):
        """上传图纸 → 分析 → 计算预算"""
        print(f"\n  📊 预算测试: {name}")
        analysis = upload_and_analyze(filepath)

        # 计算预算
        r = requests.post(
            f"{API}/api/v1/budget/calculate",
            json={"analysis": analysis, "city": "北京", "project_name": f"测试-{name}"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success"), f"预算计算失败: {data}"

        budget = data["budget"]
        assert budget["summary"]["total_cost"] > 0, "总造价应为正数"
        assert len(budget["quantities"]) > 0, "工程量清单不应为空"
        print(f"    ✅ 总造价: {budget['summary']['total_cost']:,.0f} 元")

    @pytest.mark.parametrize("filepath,name", [
        (os.path.join(E2E_DIR, f), n) for f, n in TEST_DXFS[:1]
        if os.path.exists(os.path.join(E2E_DIR, f))
    ])
    def test_budget_report(self, filepath, name):
        """预算 → 生成报告"""
        print(f"\n  📝 报告测试: {name}")
        analysis = upload_and_analyze(filepath)

        # 计算预算
        r = requests.post(
            f"{API}/api/v1/budget/calculate",
            json={"analysis": analysis, "city": "上海"},
            timeout=30,
        )
        budget = r.json()["budget"]

        # 生成报告
        r = requests.post(
            f"{API}/api/v1/budget/report",
            json={"budget": budget, "format": "text"},
            timeout=30,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success")
        assert len(data["report"]) > 100, "报告应有内容"
        assert "工程预算书" in data["report"]
        print(f"    ✅ 报告生成成功 ({len(data['report'])} 字符)")

    def test_unit_prices(self):
        """单价库API"""
        r = requests.get(f"{API}/api/v1/budget/unit-prices", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data.get("success")
        assert len(data["prices"]) > 0
        print(f"\n  ✅ 单价库: {len(data['prices'])} 个类别")

    def test_regions(self):
        """地区系数API"""
        r = requests.get(f"{API}/api/v1/budget/regions", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data.get("success")
        assert len(data["regions"]) > 0
        print(f"\n  ✅ 地区系数: {len(data['regions'])} 个城市")


class TestKnowledgeE2E:
    """知识库 E2E 测试"""

    def test_knowledge_stats(self):
        """知识库统计"""
        r = requests.get(f"{API}/api/v1/knowledge/stats", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data.get("success")
        print(f"\n  ✅ 知识库统计: {len(data.get('categories', []))} 个类别")

    def test_knowledge_search(self):
        """知识库搜索"""
        r = requests.get(
            f"{API}/api/v1/knowledge/search",
            params={"q": "消防", "limit": 5},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success")
        print(f"\n  ✅ 知识库搜索: {len(data.get('results', []))} 条结果")

    def test_knowledge_recommend(self):
        """知识库推荐"""
        r = requests.get(
            f"{API}/api/v1/knowledge/recommend",
            params={"drawing_type": "建筑"},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("success")
        print(f"\n  ✅ 知识库推荐: {len(data.get('results', []))} 条推荐")


class TestFullPipelineE2E:
    """完整流水线 E2E 测试"""

    def test_full_pipeline(self):
        """上传 → 分析 → 审查 → 预算 → 文档"""
        filepath = os.path.join(E2E_DIR, TEST_DXFS[0][0])
        if not os.path.exists(filepath):
            pytest.skip(f"测试文件不存在: {filepath}")

        print(f"\n  🚀 全链路测试: {TEST_DXFS[0][1]}")

        t0 = time.time()

        # 1. 上传分析
        analysis = upload_and_analyze(filepath)
        t1 = time.time()
        print(f"    ✅ 分析完成 ({(t1-t0):.1f}s)")

        # 2. 智能审查（端点期望 {"analysis": {...}} 格式）
        r = requests.post(
            f"{API}/api/v1/blueprint/review/analysis",
            json={"analysis": analysis},
            timeout=60,
        )
        assert r.status_code == 200
        review_data = r.json()
        assert review_data.get("success"), f"审查失败: {review_data}"
        t2 = time.time()
        issues = review_data.get("issues", [])
        print(f"    ✅ 审查完成 ({(t2-t1):.1f}s) — {len(issues)} 个问题")

        # 3. 预算计算
        r = requests.post(
            f"{API}/api/v1/budget/calculate",
            json={"analysis": analysis, "city": "北京"},
            timeout=30,
        )
        budget_data = r.json()
        assert budget_data.get("success")
        t3 = time.time()
        print(f"    ✅ 预算完成 ({(t3-t2):.1f}s) — {budget_data['budget']['summary']['total_cost']:,.0f} 元")

        # 4. 知识库推荐
        r = requests.get(
            f"{API}/api/v1/knowledge/recommend",
            params={"drawing_type": analysis.get("ai_analysis", {}).get("drawing_type", {}).get("primary", "建筑")},
            timeout=10,
        )
        kb_data = r.json()
        assert kb_data.get("success")
        t4 = time.time()
        print(f"    ✅ 知识库推荐 ({(t4-t3):.1f}s) — {len(kb_data.get('results', []))} 条")

        total = time.time() - t0
        print(f"\n  🎉 全链路完成! 总耗时: {total:.1f}s")
        assert total < 120, f"全链路应在120s内完成，实际 {total:.1f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
