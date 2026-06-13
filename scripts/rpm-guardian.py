#!/usr/bin/env python3
"""
rpm-guardian.py - RPM限流监控与自动恢复系统

功能：
1. 滑动窗口RPM计数器（按模型、按供应商）
2. 自动检测API速率限制（429错误 / 超时 / 挂起）
3. 自动降级到备用模型 + 恢复后自动回切
4. 集成OpenClaw gateway + EMA项目LLMSupervisor
5. 状态报告与告警

用法：
  python3 rpm-guardian.py check          # 一键健康检查
  python3 rpm-guardian.py monitor        # 持续监控（daemon模式）
  python3 rpm-guardian.py recover        # 手动触发恢复
  python3 rpm-guardian.py status         # 查看状态
  python3 rpm-guardian.py probe          # 探测主模型是否恢复

配置：
  通过环境变量或 CONFIG 字典调整:
    RPM_LIMIT: 单模型每分钟请求上限 (默认: 35)
    RPM_WINDOW: 滑动窗口大小(秒) (默认: 60)
    COOLDOWN_SECS: 禁封冷却时间(秒) (默认: 300)
    PROBE_INTERVAL: 健康探测间隔(秒) (默认: 120)
    TIMEOUT_SECS: API超时阈值(秒) (默认: 30)
    FALLBACK_THRESHOLD: 触发降级的连续失败次数 (默认: 2)
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

# ── 工作区路径 ──────────────────────────────────────────────

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE", "/mnt/d/OpenClawDataworkspace"))
OPENCLAW_CONFIG = Path(os.environ.get("OPENCLAW_CONFIG",
                                       "/home/kezhigang/.openclaw/openclaw.json"))
DATA_DIR = WORKSPACE / "data"
LOG_DIR = WORKSPACE / "logs"
STATE_FILE = DATA_DIR / "rpm-guardian-state.json"

# ── 默认配置 ────────────────────────────────────────────────

CONFIG = {
    "rpm_limit": int(os.environ.get("RPM_LIMIT", "35")),
    "rpm_window": int(os.environ.get("RPM_WINDOW", "60")),
    "cooldown_secs": int(os.environ.get("COOLDOWN_SECS", "300")),
    "probe_interval": int(os.environ.get("PROBE_INTERVAL", "120")),
    "timeout_secs": int(os.environ.get("TIMEOUT_SECS", "30")),
    "fallback_threshold": int(os.environ.get("FALLBACK_THRESHOLD", "2")),
    "health_check_interval": int(os.environ.get("HEALTH_CHECK_INTERVAL", "180")),
}

# ── 模型配置（与OpenClaw config同步） ─────────────────────────

PRIMARY_MODEL = "opencode/deepseek-v4-flash-free"
FALLBACK_CHAIN = [
    "nvidia/deepseek-v4-pro",
    "nvidia/minimaxai/minimax-m2.5",
    "nvidia/z-ai/glm5",
    "opencode/deepseek-v4-flash-free",  # 最后兜底
]

# ── 日志 ────────────────────────────────────────────────────

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "rpm-guardian.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("rpm-guardian")

# ── 工具函数 ────────────────────────────────────────────────


def _run_cmd(cmd: List[str], timeout: int = 15) -> Tuple[int, str, str]:
    """运行shell命令并返回 (returncode, stdout, stderr)"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def _openclaw_config_get() -> Optional[dict]:
    """读取OpenClaw配置"""
    try:
        with open(OPENCLAW_CONFIG) as f:
            return json.load(f)
    except Exception as e:
        log.error(f"读取配置失败: {e}")
        return None


def _save_state(state: dict):
    """持久化状态"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _load_state() -> dict:
    """加载持久化状态"""
    if STATE_FILE.exists():
        try:
            return json.load(open(STATE_FILE))
        except Exception:
            pass
    return {
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "models": {},  # model_id → { rpm_history: [], last_check, status, ... }
        "daily": {"date": "", "total_probes": 0, "detected_rate_limits": 0, "fallbacks": 0},
        "active_fallback": None,  # 当前是否在降级状态
        "last_recovery_at": None,
    }


# ── 滑动窗口计数器 ──────────────────────────────────────────


class SlidingWindowCounter:
    """
    滑动窗口速率计数器
    
    用法:
        counter = SlidingWindowCounter(window_secs=60, max_count=35)
        counter.record()  # 记录一次请求
        if counter.is_limited():
            print("达到速率限制!")
        print(f"当前RPM: {counter.count()}")
    """

    def __init__(self, window_secs: int = 60, max_count: int = 35):
        self.window_secs = window_secs
        self.max_count = max_count
        self._timestamps: deque = deque()

    def record(self):
        """记录一次请求"""
        now = time.time()
        self._timestamps.append(now)
        self._trim(now)

    def count(self) -> int:
        """获取当前窗口内的请求数"""
        self._trim(time.time())
        return len(self._timestamps)

    def is_limited(self) -> bool:
        """是否达到速率限制"""
        return self.count() >= self.max_count

    def remaining(self) -> int:
        """剩余可用请求数"""
        return max(0, self.max_count - self.count())

    def time_until_reset(self) -> float:
        """窗口重置剩余时间(秒)"""
        if not self._timestamps:
            return 0
        now = time.time()
        self._trim(now)
        if not self._timestamps:
            return 0
        # 最早的时间戳 + 窗口大小 = 重置时间
        return max(0, self._timestamps[0] + self.window_secs - now)

    def _trim(self, now: float):
        """移除窗口外的记录"""
        cutoff = now - self.window_secs
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    def to_dict(self) -> dict:
        return {
            "count": self.count(),
            "max": self.max_count,
            "remaining": self.remaining(),
            "window_secs": self.window_secs,
            "is_limited": self.is_limited(),
        }


# ── 模型健康探测 ────────────────────────────────────────────


class ModelProbe:
    """
    模型健康探测
    
    发送轻量级请求测试模型是否可用。
    支持 opencode API 和 NVIDIA API 的探测。
    """

    # OpenCode API 轻量探测端点
    OPENCODE_PROBE_URL = "https://api.opencode.ai/v1/models"

    # NVIDIA API 轻量探测
    NVIDIA_PROBE_URL = "https://integrate.api.nvidia.com/v1/models"

    @staticmethod
    def probe_opencode() -> dict:
        """探测OpenCode API可达性"""
        result = {"reachable": False, "latency_ms": 0, "error": "", "status_code": 0}
        try:
            req = urllib.request.Request(
                ModelProbe.OPENCODE_PROBE_URL,
                headers={"User-Agent": "RPM-Guardian/1.0"},
            )
            start = time.time()
            resp = urllib.request.urlopen(req, timeout=15)
            elapsed = (time.time() - start) * 1000
            result["reachable"] = True
            result["latency_ms"] = round(elapsed, 1)
            result["status_code"] = resp.getcode()
        except urllib.error.HTTPError as e:
            result["status_code"] = e.code
            result["error"] = f"HTTP {e.code}: {e.reason}"
            if e.code == 429:
                result["error"] += " (RATE_LIMITED)"
        except Exception as e:
            result["error"] = str(e)
        return result

    @staticmethod
    def probe_nvidia() -> dict:
        """探测NVIDIA API可达性"""
        result = {"reachable": False, "latency_ms": 0, "error": "", "status_code": 0}
        try:
            req = urllib.request.Request(
                ModelProbe.NVIDIA_PROBE_URL,
                headers={"User-Agent": "RPM-Guardian/1.0"},
            )
            start = time.time()
            resp = urllib.request.urlopen(req, timeout=10)
            elapsed = (time.time() - start) * 1000
            result["reachable"] = True
            result["latency_ms"] = round(elapsed, 1)
            result["status_code"] = resp.getcode()
        except urllib.error.HTTPError as e:
            result["status_code"] = e.code
            result["error"] = f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            result["error"] = str(e)
        return result

    @staticmethod
    def get_probe_for_model(model_id: str):
        """根据模型ID获取对应的探测方法"""
        if model_id.startswith("opencode/"):
            return ModelProbe.probe_opencode
        elif model_id.startswith("nvidia/"):
            return ModelProbe.probe_nvidia
        return None


# ── RPM Guardian主引擎 ─────────────────────────────────────


class RPMGuardian:
    """
    RPM限流监护者 - 核心引擎
    
    功能:
    - 跟踪多个模型的RPM使用情况
    - 检测速率限制
    - 自动降级到备用模型
    - 恢复后自动回切
    - 与LLMSupervisor集成
    - 提供状态报告
    """

    def __init__(self):
        self.state = _load_state()
        self.counters: Dict[str, SlidingWindowCounter] = {}
        self._init_counters()

        # 每日统计重置
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state["daily"]["date"] != today:
            self.state["daily"] = {
                "date": today,
                "total_probes": 0,
                "detected_rate_limits": 0,
                "fallbacks": 0,
            }

    def _init_counters(self):
        """为所有模型创建计数器"""
        all_models = [PRIMARY_MODEL] + FALLBACK_CHAIN
        for model_id in all_models:
            if model_id not in self.counters:
                # 不同的模型可能有不同的RPM限制
                limit = CONFIG["rpm_limit"]
                if "free" in model_id:
                    limit = min(limit, 35)  # 免费模型更严格的限制
                elif "pro" in model_id:
                    limit = min(limit, 60)  # Pro模型较高限制
                self.counters[model_id] = SlidingWindowCounter(
                    window_secs=CONFIG["rpm_window"], max_count=limit
                )

    # ── 核心方法 ──────────────────────────────────────────

    def record_api_call(self, model_id: str, success: bool, elapsed: float,
                        status_code: int = 200) -> dict:
        """
        记录一次API调用
        
        返回: 当前模型状态
        """
        if model_id not in self.counters:
            self.counters[model_id] = SlidingWindowCounter(
                window_secs=CONFIG["rpm_window"],
                max_count=CONFIG["rpm_limit"],
            )

        counter = self.counters[model_id]
        counter.record()

        # 更新模型状态
        if model_id not in self.state["models"]:
            self.state["models"][model_id] = {
                "total_calls": 0,
                "success_calls": 0,
                "failed_calls": 0,
                "rate_limited": 0,
                "last_call_at": None,
                "last_error": None,
                "consecutive_failures": 0,
                "is_disabled": False,
                "disabled_until": None,
            }

        m_state = self.state["models"][model_id]
        m_state["total_calls"] += 1
        m_state["last_call_at"] = datetime.now().isoformat()

        if success:
            m_state["success_calls"] += 1
            m_state["consecutive_failures"] = 0
        else:
            m_state["failed_calls"] += 1
            m_state["consecutive_failures"] += 1
            m_state["last_error"] = f"HTTP {status_code}"

            # 检测速率限制
            if status_code == 429:
                m_state["rate_limited"] += 1
                self.state["daily"]["detected_rate_limits"] += 1
                log.warning(f"🚫 检测到速率限制: {model_id} (429)")

            # 连续失败 → 自动禁用
            if (m_state["consecutive_failures"] >= CONFIG["fallback_threshold"]
                    and not m_state["is_disabled"]):
                self._disable_model(model_id)

        # 检查是否需要降级
        needs_fallback = self._check_fallback_needed(model_id)

        _save_state(self.state)
        return {
            "model": model_id,
            "rpm": counter.count(),
            "remaining": counter.remaining(),
            "is_limited": counter.is_limited(),
            "needs_fallback": needs_fallback,
            "consecutive_failures": m_state["consecutive_failures"],
        }

    def _disable_model(self, model_id: str):
        """禁用一个模型（标记为不可用）"""
        m_state = self.state["models"].get(model_id)
        if not m_state:
            return
        m_state["is_disabled"] = True
        m_state["disabled_until"] = time.time() + CONFIG["cooldown_secs"]
        log.warning(f"⛔ 模型已禁用: {model_id} (冷却{CONFIG['cooldown_secs']}秒)")

    def _check_fallback_needed(self, model_id: str) -> bool:
        """检查当前模型是否需要降级"""
        # 如果已经是降级状态，不需要再次触发
        if self.state["active_fallback"]:
            return False

        m_state = self.state["models"].get(model_id)
        if not m_state:
            return False

        # 条件1: 模型被禁用
        if m_state["is_disabled"]:
            return True

        # 条件2: 速率限制
        counter = self.counters.get(model_id)
        if counter and counter.is_limited():
            return True

        # 条件3: 错误率过高
        if m_state["total_calls"] >= 5:
            error_rate = m_state["failed_calls"] / m_state["total_calls"]
            if error_rate > 0.5:  # 50%+ 错误率
                return True

        return False

    # ── 健康探测 ──────────────────────────────────────────

    def probe_primary(self) -> dict:
        """探测主模型健康状态"""
        self.state["daily"]["total_probes"] += 1
        log.info(f"🔍 探测主模型: {PRIMARY_MODEL}")

        probe_fn = ModelProbe.get_probe_for_model(PRIMARY_MODEL)
        if not probe_fn:
            return {"model": PRIMARY_MODEL, "reachable": False, "error": "no probe method"}

        result = probe_fn()

        # 记录探测结果
        is_healthy = result["reachable"] and result.get("status_code", 0) not in (429, 503)
        self.record_api_call(
            PRIMARY_MODEL,
            success=is_healthy,
            elapsed=result.get("latency_ms", 0) / 1000,
            status_code=result.get("status_code", 0),
        )

        result["model"] = PRIMARY_MODEL
        result["is_healthy"] = is_healthy
        result["rpm_info"] = self.counters.get(PRIMARY_MODEL, {}).to_dict() if hasattr(self.counters.get(PRIMARY_MODEL, {}), 'to_dict') else {}

        _save_state(self.state)
        return result

    def probe_fallback(self, model_id: str) -> dict:
        """探测备用模型健康状态"""
        probe_fn = ModelProbe.get_probe_for_model(model_id)
        if not probe_fn:
            return {"model": model_id, "reachable": False, "error": "no probe method"}

        result = probe_fn()
        is_healthy = result["reachable"] and result.get("status_code", 0) != 429

        self.record_api_call(
            model_id,
            success=is_healthy,
            elapsed=result.get("latency_ms", 0) / 1000,
            status_code=result.get("status_code", 0),
        )

        result["model"] = model_id
        result["is_healthy"] = is_healthy
        return result

    # ── 降级与恢复 ────────────────────────────────────────

    def trigger_fallback(self, reason: str = "") -> bool:
        """
        触发模型降级 - 切换到备用模型
        
        返回: 是否成功
        """
        if self.state["active_fallback"]:
            log.info("ℹ️ 已在降级状态，跳过")
            return True

        log.warning(f"🔄 触发模型降级: {reason}")

        # 探测备用模型，选择第一个健康的
        target_model = None
        for fallback in FALLBACK_CHAIN:
            if fallback == PRIMARY_MODEL:
                continue
            result = self.probe_fallback(fallback)
            if result["is_healthy"]:
                target_model = fallback
                log.info(f"✅ 备用模型可用: {target_model}")
                break
            else:
                log.warning(f"❌ 备用模型不可用: {fallback} - {result.get('error', 'unknown')}")

        if not target_model:
            log.error("❌ 所有备用模型均不可用，无法降级")
            return False

        # 执行模型切换
        success = self._switch_model(target_model)
        if success:
            self.state["active_fallback"] = {
                "from": PRIMARY_MODEL,
                "to": target_model,
                "reason": reason,
                "triggered_at": datetime.now().isoformat(),
            }
            self.state["daily"]["fallbacks"] += 1
            _save_state(self.state)
            log.info(f"✅ 成功降级到 {target_model}")

            # 同步通知LLMSupervisor
            self._notify_llm_supervisor(PRIMARY_MODEL, target_model, reason)
        return success

    def try_recovery(self) -> bool:
        """
        尝试恢复主模型 - 探测主模型是否已恢复
        
        返回: 是否已恢复
        """
        if not self.state["active_fallback"]:
            log.info("ℹ️ 不在降级状态，无需恢复")
            return True

        # 检查冷却期
        disabled_until = self.state["models"].get(PRIMARY_MODEL, {}).get("disabled_until")
        if disabled_until and time.time() < disabled_until:
            remaining = int(disabled_until - time.time())
            log.info(f"⏳ 主模型仍在冷却中 (剩余{remaining}秒)")
            return False

        # 探测主模型
        result = self.probe_primary()

        if result["is_healthy"]:
            log.info(f"✅ 主模型已恢复: {PRIMARY_MODEL}")

            # 切回主模型
            target = self.state["active_fallback"]["to"]
            success = self._switch_model(PRIMARY_MODEL)
            if success:
                self.state["active_fallback"] = None
                self.state["last_recovery_at"] = datetime.now().isoformat()

                # 重置主模型状态
                if PRIMARY_MODEL in self.state["models"]:
                    self.state["models"][PRIMARY_MODEL]["consecutive_failures"] = 0
                    self.state["models"][PRIMARY_MODEL]["is_disabled"] = False
                    self.state["models"][PRIMARY_MODEL]["disabled_until"] = None

                _save_state(self.state)
                log.info(f"✅ 已恢复主模型: {PRIMARY_MODEL}")

                # 通知LLMSupervisor
                self._notify_llm_supervisor(PRIMARY_MODEL, target, "primary_recovered")
                return True
        else:
            log.info(f"❌ 主模型仍未恢复: {result.get('error', 'unknown')}")
        return False

    def _switch_model(self, target_model: str) -> bool:
        """
        切换当前模型
        
        使用 openclaw models set 命令切换默认模型
        """
        try:
            # 尝试通过 openclaw CLI 切换
            rc, out, err = _run_cmd(
                ["openclaw", "models", "set", target_model],
                timeout=10,
            )
            if rc == 0:
                log.info(f"📋 openclaw models set 输出: {out[:200] if out else 'ok'}")
                return True
            else:
                log.error(f"❌ openclaw models set 失败: {err[:200]}")
                return False
        except Exception as e:
            log.error(f"❌ 切换模型异常: {e}")
            return False

    def _notify_llm_supervisor(self, from_model: str, to_model: str, reason: str):
        """
        通知 LLMSupervisor 状态变更
        
        写入共享状态文件，LLMSupervisor 会在下次检查时读取
        """
        try:
            notice = {
                "time": datetime.now().isoformat(),
                "type": "rpm_guardian_fallback" if reason != "primary_recovered" else "rpm_guardian_recovery",
                "from": from_model,
                "to": to_model,
                "reason": reason,
            }
            notice_path = DATA_DIR / "rpm-guardian-notices.jsonl"
            with open(notice_path, "a") as f:
                f.write(json.dumps(notice, ensure_ascii=False) + "\n")
            log.info(f"📝 已通知LLMSupervisor: {notice['type']}")
        except Exception as e:
            log.error(f"通知LLMSupervisor失败: {e}")

    # ── 状态查询 ──────────────────────────────────────────

    def get_status(self) -> dict:
        """获取完整状态报告"""
        # 刷新计数器信息
        for model_id, counter in self.counters.items():
            counter._trim(time.time())

        models_status = {}
        for model_id, m_state in self.state["models"].items():
            counter = self.counters.get(model_id)
            models_status[model_id] = {
                **m_state,
                "rpm_current": counter.count() if counter else 0,
                "rpm_limit": counter.max_count if counter else CONFIG["rpm_limit"],
                "rpm_remaining": counter.remaining() if counter else 0,
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "config": CONFIG,
            "primary_model": PRIMARY_MODEL,
            "fallback_chain": FALLBACK_CHAIN,
            "active_fallback": self.state.get("active_fallback"),
            "last_recovery_at": self.state.get("last_recovery_at"),
            "models": models_status,
            "daily": self.state["daily"],
            "healthy": not bool(self.state["active_fallback"]),
        }

    def monitor_session(self) -> dict:
        """
        监控当前活跃session的模型使用情况
        
        通过 openclaw sessions list 获取session状态
        """
        try:
            rc, out, err = _run_cmd(
                ["openclaw", "sessions", "list", "--limit", "5", "--json"],
                timeout=10,
            )
            if rc != 0:
                return {"error": f"CLI error: {err[:200]}"}

            data = json.loads(out)
            sessions = data.get("sessions", [])

            result = {"sessions": [], "total_rpm_estimate": 0}
            for session in sessions[:3]:  # 只看最近3个session
                model = session.get("model", "unknown")
                provider = session.get("modelProvider", "unknown")
                model_id = f"{provider}/{model}"

                # 估算这个session的RPM消耗
                # (基于最近活动时间)
                age_ms = session.get("ageMs", 0)
                total_tokens = session.get("totalTokens", 0)
                rpm_estimate = 0
                if age_ms > 0:
                    # 粗略估算: 每1000 token ≈ 1次API调用
                    est_calls = max(1, total_tokens // 1000)
                    rpm_estimate = est_calls / max(1, age_ms / 60000)

                session_info = {
                    "id": session.get("sessionId", "")[:12],
                    "model_id": model_id,
                    "age_min": round(age_ms / 60000, 1),
                    "total_tokens": total_tokens,
                    "rpm_estimate": round(rpm_estimate, 1),
                }
                result["sessions"].append(session_info)
                result["total_rpm_estimate"] += rpm_estimate

                # 记录到计数器
                self.record_api_call(model_id, True, 0)

            return result

        except Exception as e:
            return {"error": str(e)}

    # ── 主循环 ────────────────────────────────────────────

    def run_check(self) -> dict:
        """执行一次完整健康检查"""
        log.info("=" * 50)
        log.info("🔬 RPM Guardian 健康检查")
        log.info("=" * 50)

        # 1. 探测主模型
        probe_result = self.probe_primary()
        log.info(f"  主模型 {PRIMARY_MODEL}: {'✅' if probe_result['is_healthy'] else '❌'} "
                 f"(延迟: {probe_result.get('latency_ms', 'N/A')}ms)")

        # 2. 检查session状态
        session_info = self.monitor_session()
        total_rpm = session_info.get("total_rpm_estimate", 0)
        log.info(f"  活跃session: {len(session_info.get('sessions', []))}")
        log.info(f"  估算总RPM: {total_rpm:.1f}")

        # 3. 检查是否需要降级
        if not probe_result["is_healthy"] or total_rpm >= CONFIG["rpm_limit"] * 0.8:
            log.warning(f"⚡ 检测到异常: "
                        f"reachable={probe_result['is_healthy']}, "
                        f"rpm≈{total_rpm:.1f}/{CONFIG['rpm_limit']}")

            if self._check_fallback_needed(PRIMARY_MODEL):
                reason_parts = []
                if not probe_result["is_healthy"]:
                    reason_parts.append(f"API不可达 ({probe_result.get('error', 'unknown')})")
                if total_rpm >= CONFIG["rpm_limit"] * 0.8:
                    reason_parts.append(f"RPM接近限制 ({total_rpm:.0f}/{CONFIG['rpm_limit']})")
                reason = "; ".join(reason_parts)
                self.trigger_fallback(reason)
        else:
            # 4. 如果健康且在降级状态，尝试恢复
            if self.state["active_fallback"]:
                self.try_recovery()
            else:
                log.info("✅ 一切正常")

        # 5. 汇总状态
        status = self.get_status()
        log.info(f"  健康状态: {'✅' if status['healthy'] else '⚠️ 已降级'}")
        log.info(f"  RPM统计: "
                 f"limit={CONFIG['rpm_limit']}, "
                 f"today_alerts={status['daily']['detected_rate_limits']}, "
                 f"today_fallbacks={status['daily']['fallbacks']}")

        _save_state(self.state)
        return status

    def run_monitor(self):
        """持续监控模式"""
        log.info("🔄 启动持续监控模式")
        log.info(f"  探测间隔: {CONFIG['health_check_interval']}秒")

        try:
            while True:
                self.run_check()
                log.info(f"⏳ 等待{CONFIG['health_check_interval']}秒后下一次检查...")
                time.sleep(CONFIG["health_check_interval"])
        except KeyboardInterrupt:
            log.info("👋 监控已停止")


# ── CLI入口 ────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print("用法: python3 rpm-guardian.py <command>")
        print("命令:")
        print("  check    执行一次健康检查")
        print("  monitor  持续监控模式")
        print("  status   查看当前状态")
        print("  probe    探测主模型是否恢复")
        print("  recover  手动触发恢复")
        print("  fallback 手动触发降级")
        return 1

    guardian = RPMGuardian()
    cmd = sys.argv[1]

    if cmd == "check":
        status = guardian.run_check()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif cmd == "monitor":
        guardian.run_monitor()

    elif cmd == "status":
        status = guardian.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))

    elif cmd == "probe":
        result = guardian.probe_primary()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        if result["is_healthy"]:
            print(f"✅ 主模型 {PRIMARY_MODEL} 正常 (延迟: {result.get('latency_ms', 'N/A')}ms)")
        else:
            print(f"❌ 主模型 {PRIMARY_MODEL} 不可用: {result.get('error', 'unknown')}")

    elif cmd == "recover":
        if guardian.state["active_fallback"]:
            success = guardian.try_recovery()
            print(f"{'✅' if success else '❌'} 恢复{'成功' if success else '失败，仍不可用'}")
        else:
            print("ℹ️ 不在降级状态，无需恢复")

    elif cmd == "fallback":
        reason = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "手动触发"
        success = guardian.trigger_fallback(reason)
        print(f"{'✅' if success else '❌'} 降级{'成功' if success else '失败'}")

    else:
        print(f"未知命令: {cmd}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
