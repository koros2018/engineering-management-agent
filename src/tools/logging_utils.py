"""
logging_utils.py - EMA 统一日志系统

设计原则：
- 结构化 JSON 日志（file handler）
- 控制台简洁输出（console handler）
- 支持日志级别过滤（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 支持上下文追踪（request_id / tenant_id / user_id）
- 单例 logger，全局复用

Usage:
    from tools.logging_utils import get_logger
    logger = get_logger(__name__)
    logger.info("服务启动", extra={"port": 6188})
    logger.error("数据库连接失败", exc_info=True, extra={"retry_count": 3})
"""

import logging
from utils import json_dumps
import sys
import time
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from contextvars import ContextVar

# ── 上下文变量（跨线程/协程追踪） ──────────────────────────────

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

LOG_DIR = Path(__file__).parent.parent / "logs"

# ── 自定义 JSON Formatter ─────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """结构化 JSON 格式输出"""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 上下文信息
        request_id = request_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        tenant_id = tenant_id_var.get()
        if tenant_id:
            entry["tenant_id"] = tenant_id
        user_id = user_id_var.get()
        if user_id:
            entry["user_id"] = user_id

        # extra 字段合并
        if hasattr(record, "extra_data") and record.extra_data:
            entry.update(record.extra_data)

        # 异常信息
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json_dumps(entry, ensure_ascii=False, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """控制台彩色输出（开发友好）"""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    GRAY = "\033[90m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        ts = datetime.now().strftime("%H:%M:%S")
        ctx = ""
        tenant_id = tenant_id_var.get()
        if tenant_id:
            ctx = f" [tenant={tenant_id}]"
        return f"{self.GRAY}{ts}{self.RESET} {color}{record.levelname:8}{self.RESET} {record.getMessage()}{ctx}"


# ── Logger 工厂 ──────────────────────────────────────────────

_loggers: Dict[str, logging.Logger] = {}

def get_logger(name: str, level: str = None) -> logging.Logger:
    """
    获取或创建 logger

    Args:
        name: logger 名称（通常用 __name__）
        level: 日志级别（默认：环境变量 EMA_LOG_LEVEL 或 INFO）

    Returns:
        logging.Logger
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(f"ema.{name}")
    logger.setLevel(level or os.environ.get("EMA_LOG_LEVEL", "INFO"))
    logger.propagate = False  # 避免重复

    if not logger.handlers:
        # 控制台 handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(ColoredConsoleFormatter())
        console_handler.setLevel(logging.DEBUG)  # 控制台打印所有级别
        logger.addHandler(console_handler)

        # 文件 handler（JSON 格式）
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            today = datetime.now().strftime("%Y-%m-%d")
            file_handler = logging.FileHandler(
                LOG_DIR / f"ema-{today}.log", encoding="utf-8"
            )
            file_handler.setFormatter(JSONFormatter())
            file_handler.setLevel(logging.INFO)
            logger.addHandler(file_handler)
        except Exception:
            pass  # 文件日志失败不影响服务

    _loggers[name] = logger
    return logger


# ── 便捷上下文设置 ──────────────────────────────────────────

def set_request_context(request_id: str = None, tenant_id: str = None, user_id: str = None):
    """设置当前请求的日志上下文"""
    if request_id:
        request_id_var.set(request_id)
    if tenant_id:
        tenant_id_var.set(tenant_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context():
    """清除当前请求的日志上下文"""
    request_id_var.set(None)
    tenant_id_var.set(None)
    user_id_var.set(None)


# ── 日志辅助函数 ────────────────────────────────────────────

def log_api_request(method: str, path: str, status: int, duration_ms: float, **kwargs):
    """记录 API 请求（统一格式）"""
    logger = get_logger("api")
    extra = {
        "method": method,
        "path": path,
        "status_code": status,
        "duration_ms": round(duration_ms, 2),
    }
    extra.update(kwargs)

    if status >= 500:
        logger.error(f"{method} {path} → {status} ({duration_ms:.0f}ms)", extra={"extra_data": extra})
    elif status >= 400:
        logger.warning(f"{method} {path} → {status} ({duration_ms:.0f}ms)", extra={"extra_data": extra})
    else:
        logger.info(f"{method} {path} → {status} ({duration_ms:.0f}ms)", extra={"extra_data": extra})


def log_security_event(event_type: str, detail: str, severity: str = "medium", **kwargs):
    """记录安全事件（统一格式）"""
    logger = get_logger("security")
    extra = {"event_type": event_type, "severity": severity}
    extra.update(kwargs)

    if severity == "critical":
        logger.critical(f"[{event_type}] {detail}", extra={"extra_data": extra})
    elif severity == "high":
        logger.error(f"[{event_type}] {detail}", extra={"extra_data": extra})
    elif severity == "medium":
        logger.warning(f"[{event_type}] {detail}", extra={"extra_data": extra})
    else:
        logger.info(f"[{event_type}] {detail}", extra={"extra_data": extra})
