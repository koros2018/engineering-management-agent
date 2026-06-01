"""
model_registry.py - EMA 大模型配置与智能路由

支持多 provider：
- ollama: 本地 ollama 服务 (http://127.0.0.1:11434)
- nvidia: NVIDIA NGC API (https://integrate.api.nvidia.com/v1)
- fastapi: 第三方 FastAPI 兼容接口

路由策略：
- Boss/管理员 → 始终最优模型
- 用户类型 (free/pro/enterprise) + 网络状况 + 成本评分 → 自动推荐
"""

import json
import time as _time
import os
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict


# ── 数据目录 ──────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
MODELS_FILE = EMA_DATA_DIR / "models.json"
REGISTRY_FILE = EMA_DATA_DIR / "model_registry.json"


# ── Provider 定义 ──────────────────────────────────────────────

class Provider(Enum):
    OLLAMA = "ollama"
    LONGCAT = "longcat"
    OPENCODE = "opencode"
    FASTAPI = "fastapi"
    CLOUD = "cloud"


# ── 模型配置 dataclass ────────────────────────────────────────

@dataclass
class ModelConfig:
    id: str           # 唯一标识，如 "ollama/qwen3.5:9b"
    name: str         # 显示名称，如 "Qwen 3.5 9B"
    provider: str     # "ollama" | "nvidia" | "fastapi" | "cloud"
    base_url: str     # API 基础地址
    api_key: str      # API 密钥（可加密存储）
    model_name: str   # 实际模型名
    context_window: int = 128000
    reasoning: bool = False
    cost_input: float = 0.0      # 每 1M tokens 输入成本
    cost_output: float = 0.0      # 每 1M tokens 输出成本
    enabled: bool = True
    tags: List[str] = None       # ["free", "fast", "vision"] 等
    description: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    @property
    def is_local(self) -> bool:
        return self.provider in (Provider.OLLAMA.value,)

    @property
    def is_free(self) -> bool:
        return self.cost_input == 0 and self.cost_output == 0

    def cost_score(self) -> float:
        """成本友好性评分（0-100，越高越推荐）"""
        if self.is_free:
            return 95
        # 免费额度内
        if self.cost_input == 0 or self.cost_output == 0:
            return 80
        # 按量计费模型
        avg = (self.cost_input + self.cost_output) / 2
        if avg < 0.5:
            return 70
        elif avg < 2:
            return 55
        elif avg < 10:
            return 35
        return 20


# ── NVIDIA API RPM 限速（滑动窗口）────────────────────────────
# 单用户/单租户 每分钟最大 40 请求

RPM_LIMIT = 40  # 每分钟最大请求数

_rate_limit_lock = threading.Lock()
_request_counts: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
_peak_rpm = {"value": 0, "reset_at": 0}  # 全局峰值（每天重置）


def _clean_window(timestamps: list, window_seconds: int = 60) -> list:
    """清理滑动窗口外的时间戳"""
    now = _time.time()
    return [ts for ts in timestamps if (now - ts) < window_seconds]


def _get_user_key(request) -> str:
    """从请求中提取 user_id 或 tenant_id"""
    # 先尝试 FastAPI request.state.user
    if hasattr(request, "state") and hasattr(request.state, "user"):
        user = request.state.user
        if user:
            if isinstance(user, dict):
                return f"user:{user.get('id', user.get('username', 'anon'))}"
            else:
                user_id = getattr(user, 'id', None) or getattr(user, 'username', 'anon')
                return f"user:{user_id}"
    # 尝试 query/path param
    if hasattr(request, "query_params"):
        uid = (request.query_params.get("user_id")
               or request.query_params.get("tenant_id")
               or request.query_params.get("session_id"))
        if uid:
            return f"tenant:{uid}"
    # header 中的 x-user-id
    if hasattr(request, "headers"):
        uid = request.headers.get("x-user-id") or request.headers.get("x-session-id")
        if uid:
            return f"header:{uid}"
    return "global"


def check_nvidia_rate_limit(request) -> Tuple[bool, str, int]:
    """
    检查 NVIDIA API 请求是否超限
    返回: (allowed, error_msg, current_rpm)
    """
    user_key = _get_user_key(request)
    now = _time.time()

    with _rate_limit_lock:
        # 清理过期时间戳
        nvapi_ts = _request_counts[user_key]["nvapi"]
        # 清理过期时间戳（先过滤再替换）
        nvapi_ts = _request_counts[user_key]["nvapi"] = [t for t in nvapi_ts if (now - t) < 60]

        current_rpm = len(nvapi_ts)

        # 检查限制
        if current_rpm >= RPM_LIMIT:
            return False, f"NVIDIA API rate limit exceeded ({RPM_LIMIT} RPM per minute). Please retry after a while.", current_rpm

        # 记录本次请求
        nvapi_ts.append(now)

        # 更新峰值
        if current_rpm + 1 > _peak_rpm["value"]:
            _peak_rpm["value"] = current_rpm + 1
            _peak_rpm["reset_at"] = int(now) + 86400  # 次日零点 UTC

        return True, "", current_rpm + 1


def get_nvidia_stats() -> Dict:
    """获取当前 NVIDIA API 统计"""
    with _rate_limit_lock:
        return {
            "peak_rpm": _peak_rpm["value"],
            "peak_resets_at": _peak_rpm["reset_at"],
            "alert": _peak_rpm["value"] >= RPM_LIMIT,
            "limit": RPM_LIMIT,
        }


def reset_nvidia_peak():
    """重置峰值（每日cron调用）"""
    with _rate_limit_lock:
        _peak_rpm["value"] = 0


# ── 网络检测 ──────────────────────────────────────────────────

_network_ok = {"ollama_com": True, "nvidia_api": True}
_network_lock = threading.Lock()


def check_network() -> Dict[str, bool]:
    """检测外网连通性（结果缓存60秒，超时2秒）"""
    global _network_ok
    now = _time.time()

    if hasattr(check_network, "_last_check") and (now - check_network._last_check) < 60:
        return _network_ok.copy()

    import urllib.request

    def _ping(url, timeout=2):
        try:
            urllib.request.urlopen(url, timeout=timeout)
            return True
        except urllib.error.HTTPError as e:
            return e.code in (401, 403)
        except Exception:
            return False

    with _network_lock:
        _network_ok["ollama_com"] = _ping("https://ollama.com/api/version")
        _network_ok["nvidia_api"] = _ping("https://integrate.api.nvidia.com/v1/models")
        check_network._last_check = now
        return _network_ok.copy()


# ── 模型路由 ──────────────────────────────────────────────────

def route_model(
    user_role: str = "free",
    task_type: str = "chat",
    force_provider: str = None,
    request = None,  # 可传入请求对象用于NVIDIA RPM检查
) -> Tuple[ModelConfig, str]:
    """
    根据用户类型/任务/网络状况自动路由模型

    返回: (ModelConfig, reason)

    路由策略：
    - Boss 管理员 → deepseek-v4-pro (最强)
    - Enterprise → 优先云端旗舰，本地为 fallback
    - Pro → 云端主力，本地优先
    - Free → 本地优先，免费模型

    - 网络不可用 → 强制本地
    - reasoning 任务 → 优先有 reasoning 能力的模型
    """

    # NVIDIA RPM 检查（仅针对云端NVIDIA模型）
    if request is not None:
        allowed, err_msg, rpm = check_nvidia_rate_limit(request)
        if not allowed:
            # 路由到本地模型作为降级
            configs = list_models()
            local = [c for c in configs if c.enabled and c.is_local]
            if local:
                return local[0], f"nvidia_rpm_limit_fallback/{err_msg}"
            # 无本地模型则返回错误
            from dataclasses import replace
            err_model = ModelConfig(
                id="error", name="Rate Limited",
                provider="nvidia", base_url="", api_key="", model_name="",
            )
            return err_model, f"nvidia_rpm_limit/{err_msg}"

    configs = list_models()
    if not configs:
        # fallback：内置默认
        default = ModelConfig(
            id="ollama/qwen3.5:9b", name="Qwen 3.5 9B",
            provider="ollama",
            base_url="http://127.0.0.1:11434", api_key="",
            model_name="qwen3.5:9b",
        )
        return default, "default (no config)"

    # 过滤可用
    available = [c for c in configs if c.enabled]

    # Boss 永远最强
    if user_role in ("boss", "super_admin"):
        # 优先 NVIDIA deepseek-v4-pro（带RPM检查）
        for c in available:
            if c.provider == "nvidia" and "deepseek" in c.model_name.lower():
                return c, "boss_mode"
        # 其次 cloud
        for c in available:
            if c.provider in ("nvidia", "cloud") and "deepseek" in c.model_name.lower():
                return c, "boss_mode"
        return available[0], "boss_mode"

    # 网络检测
    net = check_network()
    local_only = not net["ollama_com"] and not net["nvidia_api"]

    # 任务类型
    is_reasoning = task_type in ("full_analysis", "review", "optimize")
    is_vision = task_type in ("upload_analyze", "design", "spec_compare")

    # 候选过滤
    candidates = available

    # 免费用户：本地优先
    if user_role == "free":
        # 优先本地
        local = [c for c in candidates if c.is_local]
        free = [c for c in candidates if c.is_free and not c.is_local]
        if local_only:
            candidates = local or candidates
        else:
            candidates = local + free
        candidates.sort(key=lambda c: c.cost_score(), reverse=True)

    # Pro：成本+效果平衡
    elif user_role == "pro":
        if local_only:
            local = [c for c in candidates if c.is_local]
            candidates = local or candidates
        else:
            # 有 reasoning 优先 reasoning
            if is_reasoning:
                reasoning_c = [c for c in candidates if c.reasoning]
                if reasoning_c:
                    candidates = reasoning_c
            candidates.sort(key=lambda c: c.cost_score(), reverse=True)

    # Enterprise：效果优先
    elif user_role == "enterprise":
        if not local_only:
            # 优先云端
            cloud = [c for c in candidates if not c.is_local]
            candidates = cloud + [c for c in candidates if c.is_local]
        if is_reasoning:
            reasoning_c = [c for c in candidates if c.reasoning]
            if reasoning_c:
                candidates = reasoning_c
        # 优先最高分
        candidates.sort(key=lambda c: c.cost_score(), reverse=True)

    if not candidates:
        candidates = available

    chosen = candidates[0]
    reason = f"{user_role}/{task_type}" + ("/local_only" if local_only else "")
    return chosen, reason


# ── 模型 CRUD ──────────────────────────────────────────────────

def _load_registry() -> Dict:
    if REGISTRY_FILE.exists():
        try:
            return json.load(open(REGISTRY_FILE))
        except Exception:
            pass
    return {"providers": {}, "models": []}


def _save_registry(reg: Dict):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump(reg, open(REGISTRY_FILE, "w"), ensure_ascii=False, indent=2)


def list_models() -> List[ModelConfig]:
    """列出所有配置的模型"""
    reg = _load_registry()
    return [ModelConfig(**m) for m in reg.get("models", [])]


def add_model(cfg: ModelConfig) -> bool:
    """添加或更新模型配置"""
    reg = _load_registry()
    # 去重
    reg["models"] = [m for m in reg.get("models", []) if m["id"] != cfg.id]
    reg["models"].append(asdict(cfg))
    # 同步 providers
    if cfg.provider not in reg["providers"]:
        reg["providers"][cfg.provider] = {
            "name": cfg.provider,
            "base_url": cfg.base_url,
        }
    _save_registry(reg)
    return True


def remove_model(model_id: str) -> bool:
    """删除模型"""
    reg = _load_registry()
    reg["models"] = [m for m in reg.get("models", []) if m["id"] != model_id]
    _save_registry(reg)
    return True


def update_model_status(model_id: str, enabled: bool) -> bool:
    """启用/禁用模型"""
    reg = _load_registry()
    for m in reg.get("models", []):
        if m["id"] == model_id:
            m["enabled"] = enabled
            _save_registry(reg)
            return True
    return False


def get_model(model_id: str) -> Optional[ModelConfig]:
    """获取单个模型"""
    for m in list_models():
        if m.id == model_id:
            return m
    return None


# ── 预设默认配置 ──────────────────────────────────────────────

def ensure_default_models():
    """初始化默认模型（如果 registry 为空则写入本地ollama模型）"""
    reg = _load_registry()
    if reg.get("models"):
        return  # 已有配置，不覆盖

    defaults = [
        ModelConfig(
            id="ollama/qwen3.5:9b", name="Qwen 3.5 9B",
            provider="ollama",
            base_url="http://127.0.0.1:11434", api_key="",
            model_name="qwen3.5:9b",
            context_window=32768,
            reasoning=True,
            cost_input=0, cost_output=0,
            enabled=True,
            tags=["free", "local", "reasoning"],
            description="本地 Qwen 3.5 9B（免费，需先 ollama pull qwen3.5:9b）",
        ),
        ModelConfig(
            id="ollama/deepseek-r1:7b", name="DeepSeek R1 7B",
            provider="ollama",
            base_url="http://127.0.0.1:11434", api_key="",
            model_name="deepseek-r1:7b",
            context_window=128000,
            reasoning=True,
            cost_input=0, cost_output=0,
            enabled=True,
            tags=["free", "local", "reasoning"],
            description="本地 DeepSeek R1 7B（免费，需先 ollama pull deepseek-r1:7b）",
        ),
    ]

    reg["providers"] = {"ollama": {"name": "Ollama", "base_url": "http://127.0.0.1:11434"}}
    reg["models"] = [asdict(m) for m in defaults]
    _save_registry(reg)


ensure_default_models()