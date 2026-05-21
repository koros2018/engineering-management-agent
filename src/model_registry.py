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
import time
import os
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


# ── 数据目录 ──────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
MODELS_FILE = EMA_DATA_DIR / "models.json"
REGISTRY_FILE = EMA_DATA_DIR / "model_registry.json"


# ── Provider 定义 ──────────────────────────────────────────────

class Provider(Enum):
    OLLAMA = "ollama"
    NVIDIA = "nvidia"
    FASTAPI = "fastapi"
    CLOUD = "cloud"  # 泛指云端（ollama.com 等）


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


# ── 网络检测 ──────────────────────────────────────────────────

_network_ok = {"ollama_com": True, "nvidia_api": True}
_network_lock = threading.Lock()


def check_network() -> Dict[str, bool]:
    """检测外网连通性（结果缓存5分钟）"""
    global _network_ok
    now = time.time()

    if hasattr(check_network, "_last_check") and (now - check_network._last_check) < 300:
        return _network_ok.copy()

    import urllib.request

    with _network_lock:
        # 检测 ollama.com
        try:
            urllib.request.urlopen("https://ollama.com/api/version", timeout=4)
            _network_ok["ollama_com"] = True
        except Exception:
            _network_ok["ollama_com"] = False

        # 检测 NVIDIA API
        try:
            urllib.request.urlopen("https://integrate.api.nvidia.com/v1/models", timeout=4)
            _network_ok["nvidia_api"] = True
        except Exception:
            _network_ok["nvidia_api"] = False

        check_network._last_check = now
        return _network_ok.copy()


# ── 模型路由 ──────────────────────────────────────────────────

def route_model(
    user_role: str = "free",
    task_type: str = "chat",
    force_provider: str = None,
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
        # 优先 NVIDIA deepseek-v4-pro
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
    """初始化默认模型（如果为空）"""
    if MODELS_FILE.exists():
        return

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
            description="本地 Qwen 3.5 9B（免费）",
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
            description="本地 DeepSeek R1 7B（免费）",
        ),
        ModelConfig(
            id="ollama/minimax-m2.7:cloud", name="MiniMax M2.7 (Cloud)",
            provider="ollama",
            base_url="http://127.0.0.1:11434", api_key="",
            model_name="minimax-m2.7:cloud",
            context_window=196608,
            reasoning=True,
            cost_input=0, cost_output=0,
            enabled=True,
            tags=["free", "cloud", "reasoning"],
            description="MiniMax Cloud (通过 ollama.com 中转，免费额度）",
        ),
        ModelConfig(
            id="ollama/qwen3.5:cloud", name="Qwen 3.5 Cloud",
            provider="ollama",
            base_url="http://127.0.0.1:11434", api_key="",
            model_name="qwen3.5:cloud",
            context_window=262144,
            reasoning=True,
            cost_input=0, cost_output=0,
            enabled=True,
            tags=["free", "cloud", "vision"],
            description="通义千问 Cloud（免费额度）",
        ),
    ]

    # 保存到 registry（不是 models.json）
    reg = {"providers": {"ollama": {"name": "Ollama", "base_url": "http://127.0.0.1:11434"}}, "models": [asdict(m) for m in defaults]}
    _save_registry(reg)

    # 同时写 models.json 供兼容
    MODELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"default_models": [asdict(m) for m in defaults]}, open(MODELS_FILE, "w"), ensure_ascii=False, indent=2)


ensure_default_models()