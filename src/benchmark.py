"""
benchmark.py - EMA 性能压测工具

Phase 9: API 压力测试 + 响应时间分析 + 吞吐量基准

用法:
    python3 src/benchmark.py --concurrent 10 --requests 100
    python3 src/benchmark.py --endpoint /api/v1/main/chat --body '{"message":"hello"}'
"""

import sys
import time
import json
import argparse
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
from pathlib import Path

import requests

# 将 src 加入路径
sys.path.insert(0, str(Path(__file__).parent))


# ── 配置 ──────────────────────────────────────────────────────

ENDPOINTS = [
    {"name": "health", "method": "GET", "path": "/health", "body": None},
    {"name": "agents", "method": "GET", "path": "/api/v1/agents", "body": None},
    {"name": "dashboard", "method": "GET", "path": "/api/v1/dashboard", "body": None},
    {"name": "security_baseline", "method": "GET", "path": "/api/v1/security/baseline", "body": None},
    {"name": "subscription_plans", "method": "GET", "path": "/api/v1/subscription/plans", "body": None},
    {"name": "main_chat", "method": "POST", "path": "/api/v1/main/chat",
        "body": {"message": "你好", "user_id": "benchmark", "task_type": "tech_rd"}},
]


# ── 单次请求 ──────────────────────────────────────────────────

def single_request(base_url: str, endpoint: Dict, timeout: int = 30) -> Dict:
    """执行单次 API 请求并返回耗时 + 状态码"""
    method = endpoint["method"].lower()
    url = f"{base_url}{endpoint['path']}"

    start = time.time()
    try:
        if method == "get":
            resp = requests.get(url, timeout=timeout)
        elif method == "post":
            resp = requests.post(
                url,
                json=endpoint.get("body"),
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
        else:
            return {"elapsed_s": 0, "status": -1, "error": f"Unsupported method: {method}"}

        elapsed = time.time() - start
        return {
            "elapsed_s": round(elapsed, 3),
            "status": resp.status_code,
            "size_bytes": len(resp.content),
            "error": None if resp.status_code < 400 else f"HTTP {resp.status_code}",
        }

    except requests.RequestException as e:
        elapsed = time.time() - start
        return {"elapsed_s": round(elapsed, 3), "status": -1, "error": str(e)}


# ── 并发压测 ──────────────────────────────────────────────────

def benchmark(
    base_url: str = "http://127.0.0.1:5188",
    endpoint: str = None,
    concurrent: int = 10,
    total: int = 100,
    timeout: int = 60,
) -> Dict:
    """
    并发压测

    Args:
        base_url: API 地址
        endpoint: 指定端点名称，None = 全部
        concurrent: 并发数
        total: 总请求数
        timeout: 单次超时

    Returns:
        dict: 压测报告
    """
    # 选择端点
    targets = ENDPOINTS
    if endpoint:
        targets = [e for e in ENDPOINTS if e["name"] == endpoint]
        if not targets:
            print(f"❌ 未知端点: {endpoint}")
            return {}

    results: List[Dict] = []
    per_endpoint = max(1, total // len(targets))

    print(f"🚀 EMA 性能压测")
    print(f"  目标: {base_url}")
    print(f"  并发: {concurrent} | 总计: {total} | 超时: {timeout}s")
    print(f"  端点: {len(targets)} 个\n")

    overall_start = time.time()

    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        futures = []
        for ep in targets:
            for _ in range(per_endpoint):
                futures.append(executor.submit(single_request, base_url, ep, timeout))

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            if i % max(1, total // 10) == 0:
                print(f"  [{i}/{total}] 已完成...")

    overall_elapsed = time.time() - overall_start

    # 统计
    successes = [r for r in results if r["status"] >= 200 and r["status"] < 400]
    failures = [r for r in results if r["status"] < 0 or r["status"] >= 400]

    elapsed_times = [r["elapsed_s"] for r in results]
    elapsed_times.sort()

    report = {
        "total_requests": len(results),
        "successful": len(successes),
        "failed": len(failures),
        "concurrent": concurrent,
        "total_time_s": round(overall_elapsed, 2),
        "throughput_rps": round(len(results) / overall_elapsed, 2) if overall_elapsed > 0 else 0,
        "latency": {
            "min_ms": round(min(elapsed_times) * 1000, 1) if elapsed_times else 0,
            "max_ms": round(max(elapsed_times) * 1000, 1) if elapsed_times else 0,
            "avg_ms": round(sum(elapsed_times) / len(elapsed_times) * 1000, 1) if elapsed_times else 0,
            "p50_ms": round(statistics.median(elapsed_times) * 1000, 1) if elapsed_times else 0,
            "p95_ms": round(elapsed_times[int(len(elapsed_times) * 0.95)] * 1000, 1) if elapsed_times and len(elapsed_times) >= 20 else 0,
            "p99_ms": round(elapsed_times[int(len(elapsed_times) * 0.99)] * 1000, 1) if elapsed_times and len(elapsed_times) >= 100 else 0,
        },
        "errors": [],
    }

    if failures:
        error_types = {}
        for f in failures[:20]:
            err_key = f.get("error", "unknown")
            error_types[err_key] = error_types.get(err_key, 0) + 1
        report["errors"] = [{"error": k, "count": v} for k, v in error_types.items()]

    return report


def format_report(report: Dict) -> str:
    """格式化压测报告"""
    if not report:
        return "无数据"

    lines = [
        "",
        "╔══════════════════════════════════════════╗",
        "║        EMA 性能压测报告                    ║",
        "╚══════════════════════════════════════════╝",
        "",
        f"📊 请求概况: {report['total_requests']} 次 | ✅ {report['successful']} | ❌ {report['failed']}",
        f"⏱️  总耗时: {report['total_time_s']}s | 吞吐量: {report['throughput_rps']} req/s",
        "",
        "📈 延迟分布:",
        f"  最小: {report['latency']['min_ms']}ms | 最大: {report['latency']['max_ms']}ms",
        f"  平均: {report['latency']['avg_ms']}ms | 中位数: {report['latency']['p50_ms']}ms",
        f"  P95: {report['latency']['p95_ms']}ms | P99: {report['latency']['p99_ms']}ms",
    ]

    if report.get("errors"):
        lines.append("\n⚠️  错误分布:")
        for err in report["errors"]:
            lines.append(f"  {err['error']}: {err['count']}次")

    lines.append(f"\n💡 建议: 如果 P99 > 1s，考虑增加 worker 进程或使用 async endpoints")

    return "\n".join(lines)


def run_health_check(base_url: str = "http://127.0.0.1:5188") -> Dict:
    """快速健康检查（单次请求每个端点）"""
    results = {}
    print("🏥 EMA 快速健康检查\n")

    for ep in ENDPOINTS:
        result = single_request(base_url, ep)
        status = "✅" if result["status"] >= 200 and result["status"] < 400 else "❌"
        ms = result["elapsed_s"] * 1000
        results[ep["name"]] = {
            "status": status,
            "latency_ms": round(ms, 1),
            "size_bytes": result.get("size_bytes", 0),
        }
        print(f"  {status} {ep['name']}: {ms:.0f}ms")

    return results


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EMA 性能压测工具")
    parser.add_argument("--base-url", default="http://127.0.0.1:5188", help="API 地址")
    parser.add_argument("--endpoint", default=None, help="指定端点名称")
    parser.add_argument("--concurrent", type=int, default=10, help="并发数")
    parser.add_argument("--requests", type=int, default=100, help="总请求数")
    parser.add_argument("--health", action="store_true", help="快速健康检查")
    parser.add_argument("--output", default=None, help="输出 JSON 报告文件")

    args = parser.parse_args()

    if args.health:
        results = run_health_check(args.base_url)
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
    else:
        report = benchmark(
            base_url=args.base_url,
            endpoint=args.endpoint,
            concurrent=args.concurrent,
            total=args.requests,
        )

        print(format_report(report))

        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 报告已保存: {args.output}")
