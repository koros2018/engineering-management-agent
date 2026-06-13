"""
llm_supervisor.py - 云大模型超时监督与自动降级（通用机制）

适用范围：
- EMA 项目
- 日志系统中所有 LLM 调用
- 全局云模型健康状况追踪

功能：
1. 追踪每次 LLM 调用的超时/错误（按模型、按供应商）
2. 连续超时 → 自动禁用云模型 → 降级到本地模型
3. 每日错误率 > 30% → 降级优先级
4. 定时健康检测（周期检查云模型可达性）
5. 提供监控统计 API / 日志
6. 主动告警

用法：
  from llm_supervisor import supervisor
  supervisor.record_call("nvidia/deepseek-v4-pro", success=True, elapsed=2.5)
  if supervisor.should_fallback("nvidia/deepseek-v4-pro"):
      model = "ollama/qwen3.5:9b"  # 使用本地模型
"""

import time
import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict, deque

# ── 配置（可环境变量覆盖） ─────────────────────────────────

CLOUD_TIMEOUT_SECS = int(os.environ.get("LLM_CLOUD_TIMEOUT", "30"))
LOCAL_TIMEOUT_SECS = int(os.environ.get("LLM_LOCAL_TIMEOUT", "120"))
MAX_CONSECUTIVE = int(os.environ.get("LLM_MAX_FAILURES", "3"))
COOLDOWN_SECS = int(os.environ.get("LLM_COOLDOWN", "3600"))
ERROR_RATE_THRESHOLD = float(os.environ.get("LLM_ERROR_RATE", "0.3"))
HEALTH_CHECK_INTERVAL = int(os.environ.get("LLM_HEALTH_INTERVAL", "300"))

# ── 持久化路径 ─────────────────────────────────────────────

_workspace = Path(os.environ.get("OPENCLAW_WORKSPACE", "/mnt/d/OpenClawDataworkspace"))
_DATA_DIR = _workspace / "data"
_MONITOR_FILE = _DATA_DIR / "llm_supervisor.json"


class ModelHealth:
    """单个模型的健康状态"""
    __slots__ = (
        "total", "success", "timeout", "error", "consecutive_failures",
        "total_time", "last_call", "disabled_until", "alert_sent"
    )

    def __init__(self):
        self.total = 0
        self.success = 0
        self.timeout = 0
        self.error = 0
        self.consecutive_failures = 0
        self.total_time = 0.0
        self.last_call = 0.0
        self.disabled_until = 0.0
        self.alert_sent = False

    @property
    def error_rate(self) -> float:
        return (self.timeout + self.error) / max(self.total, 1)

    @property
    def avg_time(self) -> float:
        return self.total_time / max(self.total, 1) if self.total > 0 else 0.0

    @property
    def is_disabled(self) -> bool:
        return time.time() < self.disabled_until

    @property
    def status(self) -> str:
        if self.is_disabled:
            return "disabled"
        if self.error_rate > ERROR_RATE_THRESHOLD and self.total >= 3:
            return "degraded"
        if self.total == 0:
            return "untested"
        return "healthy"

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "success": self.success,
            "timeout": self.timeout,
            "error": self.error,
            "consecutive_failures": self.consecutive_failures,
            "error_rate": round(self.error_rate, 3),
            "avg_time_ms": round(self.avg_time * 1000, 1),
            "last_call": self.last_call,
            "disabled_until": self.disabled_until,
            "status": self.status,
        }


class LLMSupervisor:
    """
    LLM 监督器（单例）
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def _init(self):
        if self._initialized:
            return
        self._lock = threading.Lock()
        self._models: Dict[str, ModelHealth] = {}
        self._alerts: deque = deque(maxlen=100)
        self._daily = {"date": "", "total": 0, "timeout": 0, "fallback": 0}
        self._load()
        self._initialized = True

    # ── 记录调用 ──────────────────────────────────────────

    def record_call(self, model_id: str, success: bool, elapsed: float,
                    is_timeout: bool = False, is_cloud: bool = False,
                    provider: str = "") -> None:
        """记录一次LLM调用结果"""
        self._init()
        with self._lock:
            if model_id not in self._models:
                self._models[model_id] = ModelHealth()
            s = self._models[model_id]
            s.total += 1
            s.last_call = time.time()

            if success:
                s.success += 1
                s.consecutive_failures = 0
                s.total_time += elapsed
                s.alert_sent = False
            else:
                s.consecutive_failures += 1
                if is_timeout:
                    s.timeout += 1
                else:
                    s.error += 1

                # 云模型连续失败 → 自动禁用
                if is_cloud and s.consecutive_failures >= MAX_CONSECUTIVE and not s.is_disabled:
                    s.disabled_until = time.time() + COOLDOWN_SECS
                    s.alert_sent = True
                    self._alerts.append({
                        "time": datetime.now().isoformat(),
                        "type": "auto_disable",
                        "model": model_id,
                        "reason": f"连续{MAX_CONSECUTIVE}次失败，自动禁封{COOLDOWN_SECS//60}分钟",
                    })

            # 每日统计
            today = datetime.now().strftime("%Y-%m-%d")
            if self._daily["date"] != today:
                self._daily = {"date": today, "total": 0, "timeout": 0, "fallback": 0}
            self._daily["total"] += 1
            if is_timeout:
                self._daily["timeout"] += 1

            self._persist()

    def record_fallback(self, from_model: str, to_model: str, reason: str) -> None:
        """记录一次降级事件"""
        self._init()
        with self._lock:
            self._daily["fallback"] += 1
            self._alerts.append({
                "time": datetime.now().isoformat(),
                "type": "fallback",
                "from": from_model,
                "to": to_model,
                "reason": reason,
            })
            self._persist()

    # ── 决策接口 ──────────────────────────────────────────

    def should_fallback(self, model_id: str) -> Tuple[bool, str]:
        """检查模型是否需要降级"""
        self._init()
        with self._lock:
            s = self._models.get(model_id)
            if not s:
                return False, ""
            if s.is_disabled:
                return True, f"模型被自动禁用（连续失败{s.total - s.success}次）"
            if s.error_rate > ERROR_RATE_THRESHOLD and s.total >= 3:
                return True, f"错误率{s.error_rate:.0%} 超过阈值{ERROR_RATE_THRESHOLD:.0%}"
            return False, ""

    def get_health(self, model_id: str = None) -> dict:
        """获取健康状态"""
        self._init()
        with self._lock:
            if model_id:
                s = self._models.get(model_id)
                return {"model_id": model_id, "health": s.to_dict() if s else None}
            return {
                "models": {mid: s.to_dict() for mid, s in self._models.items()},
                "daily": {
                    **self._daily,
                    "timeout_rate": round(self._daily["timeout"] / max(self._daily["total"], 1), 3),
                },
                "alerts": list(self._alerts),
                "config": {
                    "cloud_timeout_secs": CLOUD_TIMEOUT_SECS,
                    "max_consecutive": MAX_CONSECUTIVE,
                    "cooldown_secs": COOLDOWN_SECS,
                    "error_rate_threshold": ERROR_RATE_THRESHOLD,
                },
            }

    def get_healthy_models(self, model_ids: List[str]) -> List[str]:
        """从模型列表中过滤出健康可用的"""
        self._init()
        with self._lock:
            result = []
            for mid in model_ids:
                s = self._models.get(mid)
                if not s or not s.is_disabled:
                    result.append(mid)
            return result

    # ── 健康检测 ──────────────────────────────────────────

    def check_nvidia_health(self) -> dict:
        """检测NVIDIA API可达性（401=可达需认证，仅连接超时/拒绝才算不可达）"""
        import urllib.request
        import urllib.error
        result = {"reachable": False, "latency_ms": 0, "error": ""}
        try:
            start = time.time()
            urllib.request.urlopen("https://integrate.api.nvidia.com/v1/models", timeout=10)
            elapsed = (time.time() - start) * 1000
            result["reachable"] = True
            result["latency_ms"] = round(elapsed, 1)
        except urllib.error.HTTPError as e:
            elapsed = (time.time() - start) * 1000
            if e.code in (401, 403):
                result["reachable"] = True
                result["latency_ms"] = round(elapsed, 1)
                result["error"] = f"HTTP {e.code} (auth required, server reachable)"
            else:
                result["error"] = f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            result["error"] = str(e)
            err_str = str(e).lower()
            if "timed out" in err_str or "connection" in err_str or "refused" in err_str:
                self.record_call("nvidia/api-check", False, 0, is_timeout=True, is_cloud=True)
        return result

    def check_ollama_health(self) -> dict:
        """检测Ollama本地可达性"""
        import urllib.request
        result = {"reachable": False, "latency_ms": 0, "error": ""}
        try:
            start = time.time()
            urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5)
            elapsed = (time.time() - start) * 1000
            result["reachable"] = True
            result["latency_ms"] = round(elapsed, 1)
        except Exception as e:
            result["error"] = str(e)
        return result

    # ── 持久化 ──────────────────────────────────────────

    def _load(self):
        try:
            if _MONITOR_FILE.exists():
                data = json.load(open(_MONITOR_FILE))
                for mid, sdata in data.get("models", {}).items():
                    s = ModelHealth()
                    for attr in ModelHealth.__slots__:
                        if attr in sdata:
                            setattr(s, attr, sdata[attr])
                    self._models[mid] = s
                if data.get("daily"):
                    self._daily = data["daily"]
                for a in data.get("alerts", []):
                    self._alerts.append(a)
        except Exception:
            pass

    def _persist(self):
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            json.dump({
                "models": {mid: s.to_dict() for mid, s in self._models.items()},
                "daily": self._daily,
                "alerts": list(self._alerts),
            }, open(_MONITOR_FILE, "w"), ensure_ascii=False, indent=2)
        except Exception:
            pass

    def reset_daily(self):
        """重置每日统计"""
        self._init()
        with self._lock:
            self._daily = {"date": datetime.now().strftime("%Y-%m-%d"), "total": 0, "timeout": 0, "fallback": 0}
            self._persist()


# ── 全局单例 ──────────────────────────────────────────────

supervisor = LLMSupervisor()
