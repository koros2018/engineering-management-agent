"""
llm_monitor.py - LLM 调用超时监督与自动降级

功能：
1. 追踪每次LLM调用的超时/错误
2. 自动禁用多次超时的云模型（切换本地模型）
3. 提供监控统计端点
4. 日志记录

策略：
- 连续3次超时 → 自动禁用该模型1小时
- 每日超时率 > 30% → 降级该模型优先级
- 全局统计可通过API查询
"""

import time
import threading
import json
import os
from pathlib import Path

from utils import load_json, save_json
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime

# ── 数据目录 ──────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"
MONITOR_FILE = DATA_DIR / "llm_monitor.json"

# ── 配置 ───────────────────────────────────────────────────────

CLOUD_TIMEOUT_SECS = 30          # 云模型超时阈值
LOCAL_TIMEOUT_SECS = 120          # 本地模型超时阈值
MAX_CONSECUTIVE_FAILURES = 3      # 连续失败次数上限
COOLDOWN_SECS = 3600              # 禁封冷却时长(1小时)
DAILY_ERROR_RATE_THRESHOLD = 0.3  # 每日错误率阈值

# ── 内存状态 ──────────────────────────────────────────────────

_lock = threading.Lock()
_state = {
    "models": {},       # model_id -> ModelStats
    "disabled": {},     # model_id -> disabled_until_timestamp
    "daily": None,      # DailyStats
    "alerts": [],       # alert log
}


class ModelStats:
    """单个模型统计"""
    __slots__ = ("total", "success", "timeout", "error", "consecutive_failures",
                 "total_time", "last_call", "disabled_until")

    def __init__(self):
        self.total = 0
        self.success = 0
        self.timeout = 0
        self.error = 0
        self.consecutive_failures = 0
        self.total_time = 0.0
        self.last_call = 0.0
        self.disabled_until = 0.0

    @property
    def error_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.timeout + self.error) / self.total

    @property
    def avg_time(self) -> float:
        if self.total == 0:
            return 0.0
        return self.total_time / self.total

    @property
    def is_disabled(self) -> bool:
        return time.time() < self.disabled_until

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
            "is_disabled": self.is_disabled,
        }


class DailyStats:
    """每日汇总"""
    def __init__(self, date: str = None):
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.total_calls = 0
        self.timeout_count = 0
        self.fallback_count = 0

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "total_calls": self.total_calls,
            "timeout_count": self.timeout_count,
            "fallback_count": self.fallback_count,
            "timeout_rate": round(self.timeout_count / max(self.total_calls, 1), 3),
        }


# ── 核心接口 ──────────────────────────────────────────────────

def record_call(model_id: str, success: bool, elapsed: float,
                is_timeout: bool = False, is_cloud: bool = False) -> None:
    """
    记录一次LLM调用结果

    参数：
    - model_id: 模型标识
    - success: 是否成功
    - elapsed: 耗时(秒)
    - is_timeout: 是否超时
    - is_cloud: 是否云模型（影响超时阈值判定）
    """
    with _lock:
        if model_id not in _state["models"]:
            _state["models"][model_id] = ModelStats()

        s = _state["models"][model_id]
        s.total += 1
        s.last_call = time.time()

        if success:
            s.success += 1
            s.consecutive_failures = 0
            s.total_time += elapsed
        else:
            s.consecutive_failures += 1
            if is_timeout:
                s.timeout += 1
            else:
                s.error += 1

            # 连续失败达阈值 → 自动禁用（如果是云模型）
            if is_cloud and s.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                s.disabled_until = time.time() + COOLDOWN_SECS
                _state["alerts"].append({
                    "time": time.time(),
                    "type": "auto_disable",
                    "model": model_id,
                    "reason": f"连续{s.consecutive_failures}次失败，禁封{COOLDOWN_SECS}s",
                })

        # 更新每日统计
        if _state["daily"] is None:
            _state["daily"] = DailyStats()
        ds = _state["daily"]
        ds.total_calls += 1
        if is_timeout:
            ds.timeout_count += 1

        # 持久化
        _persist()


def should_fallback(model_id: str) -> Tuple[bool, str]:
    """
    检查模型是否需要自动降级

    返回：(需要降级, 原因)
    """
    with _lock:
        s = _state["models"].get(model_id)
        if not s:
            return False, ""

        if s.is_disabled:
            return True, f"模型已被自动禁用（{MAX_CONSECUTIVE_FAILURES}次连续失败）"

        if s.error_rate > DAILY_ERROR_RATE_THRESHOLD and s.total >= 5:
            return True, f"错误率{s.error_rate:.0%}超过阈值{DAILY_ERROR_RATE_THRESHOLD:.0%}"

        return False, ""


def get_model_health(model_id: str) -> dict:
    """获取单个模型的健康状态"""
    with _lock:
        s = _state["models"].get(model_id)
        if not s:
            return {"model_id": model_id, "status": "unknown", "total": 0}
        return {
            "model_id": model_id,
            "status": "disabled" if s.is_disabled else ("degraded" if s.error_rate > 0.1 else "healthy"),
            **s.to_dict(),
        }


def get_monitor_stats() -> dict:
    """获取完整监控统计"""
    with _lock:
        return {
            "models": {mid: s.to_dict() for mid, s in _state["models"].items()},
            "disabled": {mid: until for mid, until in _state["disabled"].items() if time.time() < until},
            "daily": _state["daily"].to_dict() if _state["daily"] else None,
            "alerts": _state["alerts"][-20:],  # 最近20条告警
            "config": {
                "cloud_timeout_secs": CLOUD_TIMEOUT_SECS,
                "local_timeout_secs": LOCAL_TIMEOUT_SECS,
                "max_consecutive_failures": MAX_CONSECUTIVE_FAILURES,
                "cooldown_secs": COOLDOWN_SECS,
                "daily_error_rate_threshold": DAILY_ERROR_RATE_THRESHOLD,
            },
        }


def reset_daily():
    """重置每日统计（每日cron调用）"""
    with _lock:
        _state["daily"] = DailyStats()


# ── 持久化 ──────────────────────────────────────────────────

def _load():
    """从磁盘加载监控状态"""
    global _state
    try:
        if MONITOR_FILE.exists():
            data = load_json(MONITOR_FILE, default={})
            # 恢复模型统计
            for mid, sdata in data.get("models", {}).items():
                s = ModelStats()
                for attr in ModelStats.__slots__:
                    if attr in sdata:
                        setattr(s, attr, sdata[attr])
                _state["models"][mid] = s
            # 恢复每日统计
            if data.get("daily"):
                ds = DailyStats(data["daily"]["date"])
                ds.total_calls = data["daily"].get("total_calls", 0)
                ds.timeout_count = data["daily"].get("timeout_count", 0)
                ds.fallback_count = data["daily"].get("fallback_count", 0)
                _state["daily"] = ds
            # 恢复告警
            _state["alerts"] = data.get("alerts", [])
    except Exception:
        pass


def _persist():
    """持久化到磁盘"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "models": {mid: s.to_dict() for mid, s in _state["models"].items()},
            "daily": _state["daily"].to_dict() if _state["daily"] else None,
            "alerts": _state["alerts"][-100:],
        }
        save_json(MONITOR_FILE, data)
    except Exception:
        pass


# ── 初始化 ──────────────────────────────────────────────────

_load()
