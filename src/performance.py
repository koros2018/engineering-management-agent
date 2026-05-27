"""
performance.py - 性能优化

Phase 6: DWG解析缓存 / 大文件分块 / 异步优化
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any


# ── 配置 ──────────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR = EMA_DATA_DIR / "cache"
CACHE_INDEX_FILE = CACHE_DIR / "index.json"
CACHE_MAX_SIZE_MB = 500  # 最大缓存 500MB
CACHE_TTL_SECONDS = 86400 * 7  # 7天过期


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ── 文件哈希 ──────────────────────────────────────────────────

def file_hash(file_path: Path) -> str:
    """计算文件 SHA256 前 16 字符"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ── 解析缓存 ──────────────────────────────────────────────────

def get_cached_analysis(file_path: Path) -> Optional[Dict]:
    """
    获取缓存的图纸分析结果

    Returns:
        dict or None: 缓存结果，过期返回 None
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    index = _load_json(CACHE_INDEX_FILE)

    fhash = file_hash(file_path)
    entry = index.get(fhash)

    if not entry:
        return None

    # 检查过期
    if time.time() - entry.get("cached_at", 0) > CACHE_TTL_SECONDS:
        return None

    # 检查文件是否变更
    if entry.get("file_size") != file_path.stat().st_size:
        return None

    # 从缓存文件加载
    cache_file = CACHE_DIR / f"{fhash}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)

    return None


def cache_analysis(file_path: Path, result: Dict):
    """
    缓存图纸分析结果

    Args:
        file_path: 原始文件路径
        result: 分析结果
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    index = _load_json(CACHE_INDEX_FILE)

    fhash = file_hash(file_path)
    file_size = file_path.stat().st_size

    # 写入缓存文件
    cache_file = CACHE_DIR / f"{fhash}.json"
    with open(cache_file, "w") as f:
        json.dump(result, f, ensure_ascii=False, default=str)

    # 更新索引
    index[fhash] = {
        "hash": fhash,
        "file_name": file_path.name,
        "file_size": file_size,
        "cached_at": time.time(),
        "expires_at": time.time() + CACHE_TTL_SECONDS,
    }
    _save_json(CACHE_INDEX_FILE, index)

    # 清理过期缓存
    cleanup_cache()


def cleanup_cache():
    """清理过期缓存"""
    index = _load_json(CACHE_INDEX_FILE)
    now = time.time()
    removed = []

    for fhash, entry in list(index.items()):
        if now - entry.get("cached_at", 0) > CACHE_TTL_SECONDS:
            cache_file = CACHE_DIR / f"{fhash}.json"
            if cache_file.exists():
                cache_file.unlink()
            removed.append(fhash)

    for fhash in removed:
        del index[fhash]

    if removed:
        _save_json(CACHE_INDEX_FILE, index)


def get_cache_stats() -> Dict:
    """获取缓存统计"""
    index = _load_json(CACHE_INDEX_FILE)
    total_size = 0
    for fhash, entry in index.items():
        cache_file = CACHE_DIR / f"{fhash}.json"
        if cache_file.exists():
            total_size += cache_file.stat().st_size

    return {
        "cached_count": len(index),
        "total_size_kb": round(total_size / 1024, 1),
        "max_size_mb": CACHE_MAX_SIZE_MB,
        "ttl_hours": CACHE_TTL_SECONDS // 3600,
    }


def preload_cache(file_paths: list) -> Dict:
    """预加载缓存（批量解析图纸后缓存结果）"""
    from blueprint_parser.core import BlueprintParser
    parser = BlueprintParser()
    results = {"cached": 0, "skipped": 0, "errors": 0}

    for fp in file_paths:
        p = Path(fp)
        if not p.exists():
            results["skipped"] += 1
            continue
        if get_cached_analysis(p):
            results["skipped"] += 1
            continue
        try:
            result = parser.parse(str(p))
            if result.success:
                cache_analysis(p, {"analysis": {"file_type": str(result.file_type), "layer_count": len(result.layers), "entity_count": len(result.entities)}})
                results["cached"] += 1
            else:
                results["errors"] += 1
        except Exception:
            results["errors"] += 1

    return results
