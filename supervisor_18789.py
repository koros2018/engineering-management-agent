#!/usr/bin/env python3
"""
supervisor_18789.py - EMA 影子监督员守护进程

独立运行，不依赖 OpenClaw cron。
用 systemd timer 或 supervisord 驱动。

三大核心能力：
1. LLM 透测：定期发简单对话到 companion agent，超时10秒=卡顿
2. 会话锁死检测：监控最近 session 是否超过 N 分钟无响应，自动 kill
3. 项目推进监督：检查 git log 是否有新 commit，没有则推动干活

用法：
  python3 supervisor_18789.py          # 单次检查
  python3 supervisor_18789.py --daemon # 持续运行（每3分钟一轮）
  python3 supervisor_18789.py --once   # 单次后退出（给 systemd timer 用）
"""

import os
import sys
import json
import time
import signal
import socket
import logging
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────

PROJECT_DIR = Path("/mnt/d/OpenClawDataworkspace/Projects/engineering-management-agent")
OPENCLAW_DIR = Path("/home/kezhigang/.openclaw")
SESSIONS_DIR = OPENCLAW_DIR / "sessions"
LOG_DIR = PROJECT_DIR / "data"
LOG_FILE = LOG_DIR / "shadow_supervisor.log"
STATE_FILE = LOG_DIR / "supervisor_state.json"
PID_FILE = LOG_DIR / "supervisor.pid"

# 端口
API_PORT = 6188
OLLAMA_PORT = 11434

# 阈值
LLM_TIMEOUT_SEC = 10          # LLM 透测超时
SESSION_STALL_MINUTES = 15    # session 超过N分钟无响应=锁死
CHECK_INTERVAL_SEC = 180      # 每3分钟一轮

# ── 日志 ──────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("shadow_supervisor")


# ── 工具函数 ──────────────────────────────────────────────────

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def http_check(url, timeout=5):
    """HTTP 连通性检查，返回 (ok, status_code, elapsed_ms, error)"""
    try:
        t0 = time.time()
        req = urllib.request.Request(url, method="GET")
        resp = urllib.request.urlopen(req, timeout=timeout)
        ms = (time.time() - t0) * 1000
        return True, resp.status, ms, None
    except urllib.error.HTTPError as e:
        ms = (time.time() - t0) * 1000
        # 401/403 也算可达（需要认证）
        return e.code in (401, 403), e.code, ms, None
    except Exception as e:
        return False, 0, 0, str(e)[:100]


def run_cmd(cmd, timeout=15):
    """运行shell命令，返回 (ok, stdout, stderr)"""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=str(PROJECT_DIR)
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "timeout"
    except Exception as e:
        return False, "", str(e)[:100]


def alert(msg):
    """输出告警（同时写日志和 stdout）"""
    log.warning(f"🚨 {msg}")
    # 写入告警文件供 OpenClaw 读取
    alert_file = LOG_DIR / "supervisor_alert.txt"
    with open(alert_file, "w", encoding="utf-8") as f:
        f.write(f"[{now_str()}] {msg}\n")


def ok(msg):
    log.info(f"✅ {msg}")


def fail(msg):
    log.error(f"❌ {msg}")


# ── 检查 1: LLM 透测 ──────────────────────────────────────────

def check_llm_health():
    """
    真实 LLM 透测：
    1. NVIDIA API — 发一条简单对话，超时10秒=卡顿
    2. Ollama 本地 — 发一条生成请求，超时10秒=卡顿
    3. OpenClaw companion — 检查 gateway 是否响应
    """
    results = {}

    # 1. NVIDIA API 透测
    nvidia_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    nvidia_key = os.environ.get("NVIDIA_API_KEY", "")
    if nvidia_key:
        try:
            payload = json.dumps({
                "model": "deepseek-ai/deepseek-v4-pro",
                "messages": [{"role": "user", "content": "回复OK"}],
                "max_tokens": 10,
            }).encode()
            req = urllib.request.Request(
                nvidia_url, data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {nvidia_key}"}
            )
            t0 = time.time()
            resp = urllib.request.urlopen(req, timeout=LLM_TIMEOUT_SEC)
            ms = (time.time() - t0) * 1000
            data = json.loads(resp.read().decode())
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if text:
                results["nvidia"] = {"status": "ok", "ms": round(ms, 0)}
            else:
                results["nvidia"] = {"status": "empty", "ms": round(ms, 0)}
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                results["nvidia"] = {"status": "auth_error", "code": e.code}
            elif e.code == 429:
                results["nvidia"] = {"status": "rate_limited", "code": 429}
            else:
                results["nvidia"] = {"status": "http_error", "code": e.code}
        except socket.timeout:
            results["nvidia"] = {"status": "timeout", "threshold": LLM_TIMEOUT_SEC}
        except Exception as e:
            results["nvidia"] = {"status": "error", "error": str(e)[:80]}
    else:
        results["nvidia"] = {"status": "no_key"}

    # 2. Ollama 本地透测
    try:
        payload = json.dumps({
            "model": "qwen3.5:9b",
            "prompt": "回复OK",
            "stream": False,
            "options": {"num_predict": 10}
        }).encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{OLLAMA_PORT}/api/generate",
            data=payload, headers={"Content-Type": "application/json"}
        )
        t0 = time.time()
        resp = urllib.request.urlopen(req, timeout=LLM_TIMEOUT_SEC)
        ms = (time.time() - t0) * 1000
        data = json.loads(resp.read().decode())
        text = data.get("response", "")
        if text:
            results["ollama"] = {"status": "ok", "ms": round(ms, 0)}
        else:
            results["ollama"] = {"status": "empty", "ms": round(ms, 0)}
    except socket.timeout:
        results["ollama"] = {"status": "timeout", "threshold": LLM_TIMEOUT_SEC}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            results["ollama"] = {"status": "model_not_found"}
        else:
            results["ollama"] = {"status": "http_error", "code": e.code}
    except Exception as e:
        results["ollama"] = {"status": "error", "error": str(e)[:80]}

    # 3. OpenClaw Gateway 检查
    ok_gw, code_gw, ms_gw, err_gw = http_check("http://127.0.0.1:18789/health", timeout=5)
    if ok_gw:
        results["openclaw_gw"] = {"status": "ok", "ms": round(ms_gw, 0)}
    else:
        results["openclaw_gw"] = {"status": "down", "error": err_gw or f"code={code_gw}"}

    return results


# ── 检查 2: 会话锁死检测 ──────────────────────────────────────

def check_session_stall():
    """
    监控最近的 session 是否超过 N 分钟无响应。
    检查 OpenClaw session 文件的最后修改时间。
    """
    stalled = []
    if not SESSIONS_DIR.exists():
        return stalled

    cutoff = datetime.now() - timedelta(minutes=SESSION_STALL_MINUTES)

    for f in SESSIONS_DIR.glob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                # 检查文件大小变化（是否有新写入）
                size_now = f.stat().st_size
                # 记录到 state 文件对比
                stalled.append({
                    "file": f.name,
                    "last_write": mtime.strftime("%H:%M:%S"),
                    "idle_min": round((datetime.now() - mtime).total_seconds() / 60, 1),
                    "size_bytes": size_now,
                })
        except Exception:
            pass

    return stalled


def check_session_context():
    """
    检查 OpenClaw 主 session 上下文大小。
    接近上限时提前告警，避免 compaction 超时。
    """
    alerts = []
    sessions_file = SESSIONS_DIR / "sessions.json"
    if not sessions_file.exists():
        return alerts

    try:
        import json
        with open(sessions_file) as f:
            sessions = json.load(f)
        for key, val in sessions.items():
            if ":main:main" not in key:
                continue
            ctx_tokens = val.get("contextTokens", 0)
            ctx_window = val.get("contextWindow", 200000)
            if ctx_window > 0:
                usage_pct = (ctx_tokens / ctx_window) * 100
                if usage_pct >= 90:
                    alerts.append({
                        "session": key,
                        "ctx_tokens": ctx_tokens,
                        "ctx_window": ctx_window,
                        "usage_pct": round(usage_pct, 1),
                        "severity": "critical" if usage_pct >= 95 else "warning",
                    })
    except Exception:
        pass
    return alerts


def check_session_locks():
    """检查残留 .lock 文件"""
    locks = []
    if SESSIONS_DIR.exists():
        for f in SESSIONS_DIR.rglob("*.lock"):
            try:
                age_min = (time.time() - f.stat().st_mtime) / 60
                if age_min > 5:
                    locks.append({
                        "file": str(f.relative_to(SESSIONS_DIR)),
                        "age_min": round(age_min, 1),
                    })
            except Exception:
                pass
    return locks


def cleanup_locks(locks):
    """清理残留锁文件"""
    cleaned = 0
    for lock_info in locks:
        try:
            f = SESSIONS_DIR / lock_info["file"]
            f.unlink(missing_ok=True)
            cleaned += 1
        except Exception:
            pass
    return cleaned


# ── 检查 3: 服务健康 ──────────────────────────────────────────

UI_PORT = 6189

def check_services():
    """检查 API 6188、UI 6189、Ollama 11434 等服务"""
    results = {}

    # API 6188
    ok_api, code_api, ms_api, err_api = http_check(
        f"http://127.0.0.1:{API_PORT}/health", timeout=5
    )
    results["api_6188"] = {
        "status": "ok" if ok_api else "down",
        "ms": round(ms_api, 0) if ok_api else 0,
        "error": err_api,
    }

    # UI 6189
    ok_ui, code_ui, ms_ui, err_ui = http_check(
        f"http://127.0.0.1:{UI_PORT}/", timeout=5
    )
    results["ui_6189"] = {
        "status": "ok" if ok_ui else "down",
        "ms": round(ms_ui, 0) if ok_ui else 0,
        "error": err_ui,
    }

    # Ollama 11434
    ok_ol, code_ol, ms_ol, err_ol = http_check(
        f"http://127.0.0.1:{OLLAMA_PORT}/api/version", timeout=5
    )
    results["ollama_11434"] = {
        "status": "ok" if ok_ol else "down",
        "ms": round(ms_ol, 0) if ok_ol else 0,
        "error": err_ol,
    }

    # NVIDIA API
    ok_nv, code_nv, ms_nv, err_nv = http_check(
        "https://integrate.api.nvidia.com/v1/models", timeout=5
    )
    results["nvidia_api"] = {
        "status": "ok" if ok_nv else "down",
        "ms": round(ms_nv, 0) if ok_nv else 0,
    }

    return results


def restart_api():
    """自动重启 API 服务"""
    log.info("尝试重启 API 服务...")
    # 先 kill 旧的
    run_cmd("pkill -f 'uvicorn.*6188'", timeout=5)
    time.sleep(2)
    # 启动新的
    run_cmd(
        f"cd {PROJECT_DIR} && nohup python3 -m uvicorn src.api_server:app "
        f"--host 0.0.0.0 --port 6188 > /tmp/ema_api.log 2>&1 &",
        timeout=10
    )
    time.sleep(5)
    # 验证
    _ok, _, _ms, _ = http_check(f"http://127.0.0.1:{API_PORT}/health", timeout=5)
    if _ok:
        ok("API 重启成功")
        return True
    else:
        fail("API 重启失败")
        return False


def restart_ui():
    """自动重启 UI 静态文件服务"""
    log.info("尝试重启 UI 服务...")
    run_cmd("pkill -f 'http.server.*6189'", timeout=5)
    time.sleep(1)
    # 用自定义路由脚本（/ui/* → ui/目录，/ → ui/index.html）
    run_cmd("pkill -f 'ema_ui_serve'", timeout=3)
    run_cmd(
        f"nohup python3 {PROJECT_DIR}/scripts/ema_ui_serve.py "
        f"> /tmp/ema_ui.log 2>&1 &",
        timeout=5
    )
    time.sleep(3)
    _ok, _, _ms, _ = http_check(f"http://127.0.0.1:{UI_PORT}/", timeout=5)
    if _ok:
        ok("UI 重启成功")
        return True
    else:
        fail("UI 重启失败")
        return False


# ── 检查 4: 项目进度监督 ──────────────────────────────────────

def check_project_progress():
    """
    检查项目是否有新进展。
    如果最近 N 分钟没有新 commit，则提醒需要推进。
    """
    _ok, stdout, _ = run_cmd("git log --oneline -1", timeout=10)
    if not _ok:
        return {"status": "git_error"}

    last_commit = stdout.strip()

    # 检查最近 commit 时间
    ok2, stdout2, _ = run_cmd("git log -1 --format='%ci'", timeout=10)
    if ok2:
        try:
            last_time = datetime.fromisoformat(stdout2.strip().replace(" +", "+"))
            idle_min = (datetime.now() - last_time).total_seconds() / 60
        except Exception:
            idle_min = 0
    else:
        idle_min = 0

    # 检查未提交改动
    ok3, stdout3, _ = run_cmd("git status --short", timeout=10)
    uncommitted = len([l for l in stdout3.split("\n") if l.strip()]) if ok3 else 0

    return {
        "last_commit": last_commit,
        "idle_min": round(idle_min, 1),
        "uncommitted_files": uncommitted,
        "needs_push": uncommitted > 0 or idle_min > 30,
    }


# ── 主检查循环 ────────────────────────────────────────────────

def run_check():
    """执行一轮完整检查"""
    log.info(f"{'='*60}")
    log.info(f"影子监督员巡检 — {now_str()}")
    log.info(f"{'='*60}")

    report = {
        "timestamp": now_str(),
        "services": {},
        "llm": {},
        "sessions": {},
        "project": {},
        "actions": [],
    }

    # 1. 服务健康
    log.info("[1/4] 服务健康检查...")
    services = check_services()
    report["services"] = services

    for name, info in services.items():
        if info["status"] == "ok":
            ok(f"  {name}: OK ({info['ms']}ms)")
        else:
            fail(f"  {name}: DOWN ({info.get('error', '')})")

    # API 挂了自动重启
    if services.get("api_6188", {}).get("status") != "ok":
        alert("API 6188 不可达，尝试自动重启")
        if restart_api():
            report["actions"].append("restarted_api")

    # UI 挂了自动重启
    if services.get("ui_6189", {}).get("status") != "ok":
        alert("UI 6189 不可达，尝试自动重启")
        if restart_ui():
            report["actions"].append("restarted_ui")

    # 2. LLM 透测
    log.info("[2/4] LLM 透测...")
    llm = check_llm_health()
    report["llm"] = llm

    for name, info in llm.items():
        status = info["status"]
        if status == "ok":
            ok(f"  {name}: OK ({info.get('ms', '?')}ms)")
        elif status == "timeout":
            alert(f"  {name}: TIMEOUT (>{LLM_TIMEOUT_SEC}s) — 模型卡顿")
            report["actions"].append(f"llm_timeout:{name}")
        elif status in ("rate_limited", "auth_error"):
            fail(f"  {name}: {status} ({info.get('code', '')})")
        else:
            fail(f"  {name}: {status}")

    # 3. Session 上下文监控
    log.info("[3/4] Session 上下文监控...")
    ctx_alerts = check_session_context()
    if ctx_alerts:
        for a in ctx_alerts:
            if a["severity"] == "critical":
                alert(f"🚨 主 session 上下文 {a['usage_pct']}% ({a['ctx_tokens']}/{a['ctx_window']}) — 即将触发 compaction，可能超时！")
            else:
                log.warning(f"  ⚠️ 主 session 上下文 {a['usage_pct']}% ({a['ctx_tokens']}/{a['ctx_window']})")
            report["actions"].append(f"ctx_alert:{a['usage_pct']}")
    else:
        ok("  主 session 上下文正常")

    # 4. 会话锁死检测
    log.info("[4/4] 会话锁死检测...")
    stalled = check_session_stall()
    locks = check_session_locks()

    report["sessions"] = {
        "stalled_count": len(stalled),
        "stalled": stalled,
        "lock_count": len(locks),
        "locks": locks,
        "ctx_alerts": ctx_alerts,
    }

    if stalled:
        alert(f"发现 {len(stalled)} 个锁死 session（>{SESSION_STALL_MINUTES}min 无响应）")
        for s in stalled:
            log.warning(f"  🔒 {s['file']}: 空闲 {s['idle_min']}min")
        report["actions"].append(f"stalled_sessions:{len(stalled)}")

    if locks:
        cleaned = cleanup_locks(locks)
        ok(f"清理了 {cleaned} 个残留锁文件")
        report["actions"].append(f"cleaned_locks:{cleaned}")

    if not stalled and not locks:
        ok("  无锁死 session，无残留锁")

    # 5. 项目进度
    log.info("[5/5] 项目进度监督...")
    progress = check_project_progress()
    report["project"] = progress

    log.info(f"  最近 commit: {progress['last_commit']}")
    log.info(f"  空闲时间: {progress['idle_min']}min")
    log.info(f"  未提交文件: {progress['uncommitted_files']}")

    if progress["needs_push"]:
        if progress["uncommitted_files"] > 0:
            alert(f"有 {progress['uncommitted_files']} 个文件未提交")
            report["actions"].append("uncommitted_files")
        if progress["idle_min"] > 30:
            alert(f"项目 {progress['idle_min']:.0f}min 没有新进展")
            report["actions"].append("project_idle")

    # 保存报告
    report_path = LOG_DIR / "supervisor_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 汇总
    log.info(f"{'='*60}")
    if report["actions"]:
        log.info(f"本轮处理: {', '.join(report['actions'])}")
    else:
        log.info("本轮无异常，一切正常 ✅")
    log.info(f"{'='*60}\n")

    return report


# ── 守护模式 ──────────────────────────────────────────────────

def daemon_loop():
    """持续运行模式"""
    log.info("影子监督员守护进程启动")
    log.info(f"检查间隔: {CHECK_INTERVAL_SEC}s")
    log.info(f"LLM超时: {LLM_TIMEOUT_SEC}s")
    log.info(f"Session锁死阈值: {SESSION_STALL_MINUTES}min")

    # 写 PID 文件
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def handle_signal(sig, frame):
        log.info("收到退出信号，清理中...")
        PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while True:
        try:
            run_check()
        except Exception as e:
            log.error(f"检查异常: {e}")

        time.sleep(CHECK_INTERVAL_SEC)


# ── 入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon_loop()
    elif "--once" in sys.argv:
        run_check()
    else:
        # 默认单次检查
        report = run_check()
        # 如果有问题，退出码非0
        if report.get("actions"):
            sys.exit(1)
        sys.exit(0)
