"""EMA 通用工具函数"""
import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_json(path: Path, default: Any = None) -> Any:
    """安全加载 JSON 文件"""
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return default if default is not None else {}


def save_json(path: Path, data: Any) -> bool:
    """安全保存 JSON 文件"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def json_dumps(data: Any) -> str:
    """JSON 序列化（统一 ensure_ascii=False）"""
    return json.dumps(data, ensure_ascii=False)


def json_loads(text: str) -> Any:
    """JSON 反序列化"""
    return json.loads(text)


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_get(d: dict, key: str, default: Any = None) -> Any:
    """安全获取字典值（兼容 None 输入）"""
    if d is None:
        return default
    if isinstance(d, dict):
        return d.get(key, default)
    return default


def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_len:
        return text
    return text[:max_len - len(suffix)] + suffix
