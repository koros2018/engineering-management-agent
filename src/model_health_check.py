"""
model_health_check.py - EMA 大模型全面健康检测

逐个测试所有已配置模型的：
1. 网络连通性
2. API响应速度
3. 生成质量（能否返回有效JSON/文本）
4. 连续3次稳定性

输出报告，标记不可用/慢/不稳定的模型。
"""

import time
import sys
from src.utils import json_dumps, json_loads
import os
from pathlib import Path

# 确保 EMA src 在路径最前面
sys.path.insert(0, str(Path(__file__).parent))
os.environ["PYTHONPATH"] = str(Path(__file__).parent)

from model_registry import (
    list_models, check_network, ModelConfig, ensure_default_models
)

# ── 测试配置 ──────────────────────────────────────────────────

TEST_PROMPT = "用一句话介绍建筑工程管理，返回JSON格式：{\"summary\": \"...\"}"
TIMEOUT_SECONDS = 30
SLOW_THRESHOLD_MS = 5000       # 超过5秒算慢
VERY_SLOW_THRESHOLD_MS = 15000  # 超过15秒算极慢
STABILITY_RUNS = 3             # 连续测试次数

# ── 颜色输出 ──────────────────────────────────────────────────

class C:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def ok(msg):   print(f"{C.GREEN}✅ {msg}{C.RESET}")
def fail(msg): print(f"{C.RED}❌ {msg}{C.RESET}")
def warn(msg): print(f"{C.YELLOW}⚠️  {msg}{C.RESET}")
def info(msg): print(f"{C.CYAN}ℹ️  {msg}{C.RESET}")
def bold(msg): print(f"{C.BOLD}{msg}{C.RESET}")


# ── 单个模型测试 ──────────────────────────────────────────────

def test_model(cfg: ModelConfig) -> dict:
    """测试单个模型，返回结果字典"""
    result = {
        "id": cfg.id,
        "name": cfg.name,
        "provider": cfg.provider,
        "base_url": cfg.base_url,
        "enabled": cfg.enabled,
        "reachable": False,
        "avg_ms": 0,
        "min_ms": 0,
        "max_ms": 0,
        "stability": 0,  # 成功次数/总次数
        "quality": "unknown",  # good / poor / none
        "error": None,
        "status": "unknown",  # ok / slow / unstable / dead
        "detail": "",
    }

    times = []
    successes = 0
    last_error = None

    for run in range(STABILITY_RUNS):
        try:
            start = time.time()

            if cfg.provider == "ollama":
                success, text = _test_ollama(cfg)
            elif cfg.provider == "nvidia":
                success, text = _test_nvidia(cfg)
            elif cfg.provider == "fastapi":
                success, text = _test_fastapi(cfg)
            else:
                success, text = _test_openai_compat(cfg)

            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)

            if success:
                successes += 1
                # 检查质量
                quality = _check_quality(text)
                if quality == "good" and result["quality"] != "poor":
                    result["quality"] = "good"
                elif quality == "poor" and result["quality"] == "unknown":
                    result["quality"] = "poor"
            else:
                result["quality"] = "none"
                last_error = text  # error message

        except Exception as e:
            times.append(TIMEOUT_SECONDS * 1000)
            last_error = str(e)[:200]

    # 汇总
    if times:
        result["avg_ms"] = round(sum(times) / len(times), 0)
        result["min_ms"] = round(min(times), 0)
        result["max_ms"] = round(max(times), 0)

    result["stability"] = f"{successes}/{STABILITY_RUNS}"
    result["reachable"] = successes > 0

    if successes == 0:
        result["status"] = "dead"
        result["error"] = last_error or "All runs failed"
    elif successes < STABILITY_RUNS:
        result["status"] = "unstable"
        result["error"] = last_error or f"Only {successes}/{STABILITY_RUNS} succeeded"
    elif result["avg_ms"] > VERY_SLOW_THRESHOLD_MS:
        result["status"] = "very_slow"
    elif result["avg_ms"] > SLOW_THRESHOLD_MS:
        result["status"] = "slow"
    else:
        result["status"] = "ok"

    return result


def _test_ollama(cfg: ModelConfig) -> tuple:
    """测试 Ollama 模型"""
    import urllib.request
    url = f"{cfg.base_url}/api/generate"
    payload = json_dumps({
        "model": cfg.model_name,
        "prompt": TEST_PROMPT,
        "stream": False,
        "options": {"num_predict": 200}
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
        data = json_loads(resp.read().decode())
        text = data.get("response", "")
        return bool(text), text
    except Exception as e:
        return False, str(e)[:200]


def _test_nvidia(cfg: ModelConfig) -> tuple:
    """测试 NVIDIA API"""
    import urllib.request
    url = f"{cfg.base_url}/chat/completions"
    payload = json_dumps({
        "model": cfg.model_name,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "max_tokens": 200,
        "temperature": 0.3,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg.api_key}",
    }
    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
        data = json_loads(resp.read().decode())
        choices = data.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")
            return bool(text), text
        return False, "No choices in response"
    except Exception as e:
        return False, str(e)[:200]


def _test_fastapi(cfg: ModelConfig) -> tuple:
    """测试 FastAPI 兼容接口"""
    return _test_openai_compat(cfg)


def _test_openai_compat(cfg: ModelConfig) -> tuple:
    """测试 OpenAI 兼容接口"""
    import urllib.request
    url = f"{cfg.base_url}/chat/completions"
    payload = json_dumps({
        "model": cfg.model_name,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "max_tokens": 200,
        "temperature": 0.3,
    }).encode()

    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    req = urllib.request.Request(url, data=payload, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)
        data = json_loads(resp.read().decode())
        choices = data.get("choices", [])
        if choices:
            text = choices[0].get("message", {}).get("content", "")
            return bool(text), text
        return False, "No choices in response"
    except Exception as e:
        return False, str(e)[:200]


def _check_quality(text: str) -> str:
    """检查生成质量"""
    if not text or len(text.strip()) < 5:
        return "poor"
    # 检查是否是有效JSON
    try:
        data = json_loads(text)
        if data and isinstance(data, dict):
            return "good"
    except Exception:
        pass
    # 纯文本但有内容
    if len(text.strip()) > 20:
        return "good"
    return "poor"


# ── 主流程 ────────────────────────────────────────────────────

def main():
    bold("=" * 60)
    bold("  EMA 大模型全面健康检测")
    bold(f"  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    bold("=" * 60)
    print()

    # 确保默认模型已初始化
    ensure_default_models()

    # 网络检测
    info("检测网络连通性...")
    net = check_network()
    if net.get("ollama_com"):
        ok("ollama.com: 可达")
    else:
        warn("ollama.com: 不可达")
    if net.get("nvidia_api"):
        ok("NVIDIA API: 可达")
    else:
        warn("NVIDIA API: 不可达（401/403视为可达需认证）")
    print()

    # 列出所有模型
    models = list_models()
    if not models:
        fail("未配置任何模型！")
        return

    info(f"共 {len(models)} 个模型，逐个测试中（每个模型 {STABILITY_RUNS} 轮）...")
    print()

    results = []
    dead_models = []
    slow_models = []
    unstable_models = []

    for i, cfg in enumerate(models):
        prefix = f"[{i+1}/{len(models)}]"
        print(f"{prefix} 测试 {cfg.name} ({cfg.id})...", end=" ", flush=True)

        result = test_model(cfg)
        results.append(result)

        status = result["status"]
        if status == "dead":
            fail(f"DEAD - {result['error']}")
            dead_models.append(result)
        elif status == "unstable":
            warn(f"UNSTABLE - {result['stability']} - {result['error']}")
            unstable_models.append(result)
        elif status == "very_slow":
            warn(f"VERY SLOW - {result['avg_ms']:.0f}ms avg")
            slow_models.append(result)
        elif status == "slow":
            warn(f"SLOW - {result['avg_ms']:.0f}ms avg")
            slow_models.append(result)
        else:
            ok(f"OK - {result['avg_ms']:.0f}ms avg - quality: {result['quality']}")

    # ── 汇总报告 ────────────────────────────────────────────
    print()
    bold("=" * 60)
    bold("  检测报告汇总")
    bold("=" * 60)
    print()

    total = len(results)
    ok_count = sum(1 for r in results if r["status"] == "ok")
    slow_count = len(slow_models)
    unstable_count = len(unstable_models)
    dead_count = len(dead_models)

    info(f"总计: {total} 个模型")
    ok(f"正常: {ok_count}")
    if slow_count: warn(f"慢速: {slow_count}")
    if unstable_count: warn(f"不稳定: {unstable_count}")
    if dead_count: fail(f"不可用: {dead_count}")
    print()

    # 详细表格
    bold(f"{'ID':<35} {'状态':<10} {'延迟':>8} {'稳定性':>8} {'质量':<8}")
    bold("-" * 75)
    for r in results:
        status_color = ""
        if r["status"] == "ok": status_color = C.GREEN
        elif r["status"] in ("slow", "very_slow"): status_color = C.YELLOW
        else: status_color = C.RED

        ms_str = f"{r['avg_ms']:.0f}ms" if r["avg_ms"] > 0 else "N/A"
        print(f"{r['id']:<35} {status_color}{r['status']:<10}{C.RESET} {ms_str:>8} {r['stability']:>8} {r['quality']:<8}")

    # ── 建议 ────────────────────────────────────────────────
    print()
    bold("=" * 60)
    bold("  处理建议")
    bold("=" * 60)
    print()

    if dead_models:
        fail("以下模型不可用，建议禁用：")
        for r in dead_models:
            print(f"  - {r['id']}: {r['error']}")
            print(f"    操作: UPDATE model_registry SET enabled=false WHERE id='{r['id']}'")
        print()

    if unstable_models:
        warn("以下模型不稳定，建议降级或禁用：")
        for r in unstable_models:
            print(f"  - {r['id']}: {r['stability']} 成功, {r['error']}")
        print()

    if slow_models:
        warn("以下模型响应慢，建议标记为慢速：")
        for r in slow_models:
            print(f"  - {r['id']}: {r['avg_ms']:.0f}ms 平均延迟")
        print()

    if ok_count > 0:
        ok("推荐使用的模型：")
        for r in results:
            if r["status"] == "ok":
                print(f"  ✅ {r['id']} ({r['avg_ms']:.0f}ms, {r['quality']})")
        print()

    # 保存报告
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "network": net,
        "summary": {
            "total": total,
            "ok": ok_count,
            "slow": slow_count,
            "unstable": unstable_count,
            "dead": dead_count,
        },
        "results": results,
        "recommendations": {
            "disable": [r["id"] for r in dead_models + unstable_models],
            "mark_slow": [r["id"] for r in slow_models],
            "recommended": [r["id"] for r in results if r["status"] == "ok"],
        }
    }

    report_path = Path(__file__).parent.parent / "data" / "model_health_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    info(f"报告已保存: {report_path}")

    return report


if __name__ == "__main__":
    main()
