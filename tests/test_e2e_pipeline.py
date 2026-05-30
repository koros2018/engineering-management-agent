#!/usr/bin/env python3
"""
端到端测试：DWG→DXF转换后的完整流水线测试
测试: 解析 → 分类 → AI分析 → 审查 → 文档生成
"""
import os
import sys
import json
import time
import requests
import pytest

API = "http://127.0.0.1:6188"
E2E_DIR = os.path.join(os.path.dirname(__file__), "e2e")

# 测试文件（转换后的DXF）
TEST_FILES = [
    ("C0000-7004-011 钢结构安装说明.dxf", "钢结构安装说明"),
    ("C448B-0010-010_P&ID_P1_B_A1.dxf", "P&ID管道仪表图"),
    ("C448D-0002-010 总平面布置图_P3_A_A1.dxf", "总平面布置图"),
    ("C448D-7120-010 凝结水管道布置图_P1_A_A1.dxf", "凝结水管道布置图"),
]

def test_api_health():
    """测试API健康状态"""
    r = requests.get(f"{API}/", timeout=5)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "running"
    print(f"  ✅ API健康: {d['name']} v{d['version']}")

@pytest.mark.parametrize("filepath,name", [
    (os.path.join(E2E_DIR, f), n) for f, n in TEST_FILES
])
def test_upload_and_analyze(filepath, name):
    """测试上传+分析"""
    print(f"\n  📄 测试文件: {name}")
    print(f"     路径: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"     ⚠️  文件不存在，跳过")
        return None
    
    file_size = os.path.getsize(filepath)
    print(f"     大小: {file_size/1024:.0f}KB")
    
    # 1. 上传并分析
    t0 = time.time()
    with open(filepath, "rb") as f:
        r = requests.post(
            f"{API}/api/v1/upload/analyze",
            files={"file": (os.path.basename(filepath), f, "application/dxf")},
            timeout=60
        )
    t1 = time.time()
    
    if r.status_code != 200:
        print(f"     ❌ 上传失败: {r.status_code} {r.text[:200]}")
        return None
    
    result = r.json()
    print(f"     ✅ 解析成功 ({(t1-t0)*1000:.0f}ms)")
    
    # 打印分析摘要
    if "analysis" in result:
        a = result["analysis"]
        layers = a.get("layers", {})
        entities = a.get("entities", {})
        print(f"     图层数: {len(layers)}, 实体数: {len(entities)}")
        
        # 图纸类型
        if "drawing_type" in a:
            print(f"     图纸类型: {a['drawing_type']}")
    
    return result

@pytest.mark.parametrize("filepath,name", [
    (os.path.join(E2E_DIR, f), n) for f, n in TEST_FILES
])
def test_ai_analyze(filepath, name):
    """测试AI分析"""
    print(f"\n  🤖 AI分析: {name}")
    
    t0 = time.time()
    with open(filepath, "rb") as f:
        r = requests.post(
            f"{API}/api/v1/blueprint/ai-analyze",
            files={"file": (os.path.basename(filepath), f, "application/dxf")},
            timeout=120
        )
    t1 = time.time()
    
    if r.status_code != 200:
        print(f"     ❌ AI分析失败: {r.status_code} {r.text[:200]}")
        return None
    
    result = r.json()
    print(f"     ✅ AI分析完成 ({(t1-t0)*1000:.0f}ms)")
    
    if "ai_analysis" in result:
        ai = result["ai_analysis"]
        if "drawing_type" in ai:
            print(f"     分类结果: {ai['drawing_type']}")
        if "confidence" in ai:
            print(f"     置信度: {ai['confidence']}")
    
    return result

@pytest.mark.parametrize("analysis_data,name", [
    ({"analysis": {"layers": {}, "entities": {}}}, n) for _, n in TEST_FILES
])
def test_review(analysis_data, name):
    """测试智能审查"""
    print(f"\n  🔍 智能审查: {name}")
    
    t0 = time.time()
    r = requests.post(
        f"{API}/api/v1/blueprint/review/analysis",
        json=analysis_data,
        timeout=60
    )
    t1 = time.time()
    
    if r.status_code != 200:
        print(f"     ❌ 审查失败: {r.status_code} {r.text[:200]}")
        return None
    
    result = r.json()
    print(f"     ✅ 审查完成 ({(t1-t0)*1000:.0f}ms)")
    
    if "summary" in result:
        s = result["summary"]
        print(f"     严重: {s.get('critical',0)}, 警告: {s.get('warning',0)}, 建议: {s.get('suggestion',0)}")
        print(f"     质量评分: {s.get('quality_score', 'N/A')}")
    
    return result

@pytest.mark.parametrize("analysis_data,name", [
    ({"analysis": {"layers": {}, "entities": {}}}, n) for _, n in TEST_FILES
])
def test_documents(analysis_data, name):
    """测试文档生成"""
    print(f"\n  📝 文档生成: {name}")
    
    t0 = time.time()
    r = requests.post(
        f"{API}/api/v1/blueprint/documents/generate",
        json=analysis_data,
        timeout=60
    )
    t1 = time.time()
    
    if r.status_code != 200:
        print(f"     ❌ 文档生成失败: {r.status_code} {r.text[:200]}")
        return None
    
    result = r.json()
    print(f"     ✅ 文档生成完成 ({(t1-t0)*1000:.0f}ms)")
    
    if "documents" in result:
        docs = result["documents"]
        print(f"     生成文档数: {len(docs)}")
        for doc_name in list(docs.keys())[:5]:
            print(f"       - {doc_name}")
    
    return result

@pytest.mark.parametrize("filepath,name", [
    (os.path.join(E2E_DIR, f), n) for f, n in TEST_FILES
])
def test_full_pipeline(filepath, name):
    """测试完整流水线"""
    print(f"\n{'='*60}")
    print(f"🚀 完整流水线: {name}")
    print(f"{'='*60}")
    
    total_start = time.time()
    
    # Step 1: 解析
    result = test_upload_and_analyze(filepath, name)
    if not result:
        return None
    
    analysis = result.get("analysis", {})
    
    # Step 2: AI分析
    ai_result = test_ai_analyze(filepath, name)
    
    # Step 3: 审查
    review_result = test_review(analysis, name)
    
    # Step 4: 文档生成
    doc_result = test_documents(analysis, name)
    
    total_time = time.time() - total_start
    
    print(f"\n  ⏱️  总耗时: {total_time*1000:.0f}ms")
    
    return {
        "name": name,
        "parse": result is not None,
        "ai": ai_result is not None,
        "review": review_result is not None,
        "documents": doc_result is not None,
        "total_ms": round(total_time * 1000)
    }

def main():
    print("=" * 60)
    print("🧪 EMA 端到端流水线测试")
    print(f"   API: {API}")
    print(f"   目录: {E2E_DIR}")
    print("=" * 60)
    
    # 1. API健康检查
    print("\n📊 Step 0: API健康检查")
    try:
        test_api_health()
    except Exception as e:
        print(f"  ❌ API不可达: {e}")
        sys.exit(1)
    
    # 2. 逐个文件测试
    results = []
    for filename, name in TEST_FILES:
        filepath = os.path.join(E2E_DIR, filename)
        r = test_full_pipeline(filepath, name)
        if r:
            results.append(r)
    
    # 3. 汇总
    print(f"\n{'='*60}")
    print("📊 测试汇总")
    print(f"{'='*60}")
    
    print(f"\n{'文件':<30} {'解析':>6} {'AI':>6} {'审查':>6} {'文档':>6} {'耗时':>10}")
    print("-" * 70)
    
    all_ok = True
    for r in results:
        status = lambda v: "✅" if v else "❌"
        print(f"{r['name']:<28} {status(r['parse']):>6} {status(r['ai']):>6} {status(r['review']):>6} {status(r['documents']):>6} {r['total_ms']:>8}ms")
        if not all([r['parse'], r['ai'], r['review'], r['documents']]):
            all_ok = False
    
    print("-" * 70)
    total_files = len(results)
    print(f"\n总计: {total_files} 个文件")
    
    if all_ok:
        print("🎉 全部通过！")
    else:
        print("⚠️  部分测试失败，请检查日志")
    
    # 保存报告
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api": API,
        "results": results,
        "all_passed": all_ok
    }
    report_path = os.path.join(E2E_DIR, "e2e_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n报告: {report_path}")

if __name__ == "__main__":
    main()
