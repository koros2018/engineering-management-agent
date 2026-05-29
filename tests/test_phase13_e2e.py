#!/usr/bin/env python3
"""
Phase 13 E2E测试：Agent工作流 + 用户行为分析 + 性能监控
覆盖: pipeline / review / documents / analytics / performance / feedback
支持: pytest 运行 或 直接 python3 test_phase13_e2e.py
"""
import os, sys, json, time, requests

API = "http://127.0.0.1:6188"
E2E_DIR = os.path.join(os.path.dirname(__file__), "e2e")

TEST_DWGS = [
    "C448B-0010-010_P&ID_P1_B_A1.dwg",
    "C448D-0002-010 总平面布置图_P3_A_A1.dwg",
]
TEST_DXFS = [
    "C0000-7004-011 钢结构安装说明.dxf",
]


# ─── pytest 测试函数 ───

def test_api_health():
    r = requests.get(f"{API}/", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") == "running"

def test_pipeline_dwg():
    """端到端流水线：DWG上传→分析→审查→文档"""
    path = os.path.join(E2E_DIR, TEST_DWGS[0])
    assert os.path.exists(path), f"测试文件不存在: {path}"
    with open(path, "rb") as f:
        r = requests.post(f"{API}/api/v1/agent/pipeline",
            files={"file": (TEST_DWGS[0], f, "application/octet-stream")},
            data={"user_id": "e2e_test", "use_llm": "false"},
            timeout=120)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    assert d.get("success"), f"pipeline failed: {d}"

def test_review_dwg():
    """智能审查：DWG上传→审查"""
    path = os.path.join(E2E_DIR, TEST_DWGS[0])
    assert os.path.exists(path)
    with open(path, "rb") as f:
        r = requests.post(f"{API}/api/v1/agent/review",
            files={"file": (TEST_DWGS[0], f, "application/octet-stream")},
            data={"user_id": "e2e", "use_llm": "false"},
            timeout=60)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    assert d.get("success"), f"review failed: {d}"
    out = d.get("output", {})
    assert "summary" in out, "missing summary"
    assert "issues" in out, "missing issues"

def test_documents_dwg():
    """文档生成：DWG上传→文档"""
    path = os.path.join(E2E_DIR, TEST_DWGS[0])
    assert os.path.exists(path)
    with open(path, "rb") as f:
        r = requests.post(f"{API}/api/v1/agent/documents",
            files={"file": (TEST_DWGS[0], f, "application/octet-stream")},
            data={"user_id": "e2e", "use_llm": "false", "doc_types": "design_spec"},
            timeout=60)
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    assert d.get("success"), f"documents failed: {d}"

def test_analytics_track():
    r = requests.post(f"{API}/api/v1/analytics/track",
        json={"user_id": "e2e", "event": "test", "metadata": {}}, timeout=5)
    assert r.status_code == 200

def test_analytics_summary():
    r = requests.get(f"{API}/api/v1/analytics/summary?user_id=e2e", timeout=5)
    assert r.status_code == 200

def test_performance():
    r = requests.get(f"{API}/api/v1/system/performance", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert "system" in d or "modules" in d

def test_feedback():
    r = requests.post(f"{API}/api/v1/feedback",
        json={"type": "test", "score": 5, "content": "e2e test"}, timeout=5)
    assert r.status_code == 200

def test_llm_health():
    r = requests.get(f"{API}/api/v1/llm/health", timeout=5)
    assert r.status_code == 200


# ─── 直接运行入口 ───
if __name__ == "__main__":
    # 手动运行所有测试
    tests = [
        ("API Health", test_api_health),
        ("Pipeline DWG", test_pipeline_dwg),
        ("Review DWG", test_review_dwg),
        ("Documents DWG", test_documents_dwg),
        ("Analytics Track", test_analytics_track),
        ("Analytics Summary", test_analytics_summary),
        ("Performance", test_performance),
        ("Feedback", test_feedback),
        ("LLM Health", test_llm_health),
    ]
    passed = failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"结果: {passed}通过 / {failed}失败 / {passed+failed}总计")
    sys.exit(0 if failed == 0 else 1)
