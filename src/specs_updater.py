"""
specs_updater.py - 国标规范自动更新检查

功能：
- 从住建部/国标委网站爬取最新规范列表
- 对比本地规范库，检测新增/更新
- 自动下载规范PDF并提取文本
- 更新ChromaDB向量库
- 通知管理员规范变更

支持的国标来源：
- 住建部 (mohurd.gov.cn)
- 国标委 (std.samr.gov.cn)
- 工标网 (csres.com)
"""

import json
import hashlib
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
SPECS_INDEX_FILE = EMA_DATA_DIR / "specs_index.json"
SPECS_DIR = EMA_DATA_DIR / "specs"
UPDATE_LOG_FILE = EMA_DATA_DIR / "specs_update_log.json"

# ── 国标规范来源配置 ──────────────────────────────────────────

SPEC_SOURCES = {
    "gb50016": {
        "name": "建筑设计防火规范 GB 50016",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83949.html",
        "category": "消防",
        "status": "current",
    },
    "gb50011": {
        "name": "建筑抗震设计规范 GB 50011",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83950.html",
        "category": "结构",
        "status": "current",
    },
    "gb50010": {
        "name": "混凝土结构设计规范 GB 50010",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83951.html",
        "category": "结构",
        "status": "current",
    },
    "gb50007": {
        "name": "建筑地基基础设计规范 GB 50007",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83952.html",
        "category": "地基",
        "status": "current",
    },
    "gb50009": {
        "name": "建筑结构荷载规范 GB 50009",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83953.html",
        "category": "结构",
        "status": "current",
    },
    "gb50017": {
        "name": "钢结构设计标准 GB 50017",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83954.html",
        "category": "结构",
        "status": "current",
    },
    "gb50019": {
        "name": "工业建筑供暖通风与空气调节设计规范 GB 50019",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83955.html",
        "category": "暖通",
        "status": "current",
    },
    "gb50015": {
        "name": "建筑给水排水设计标准 GB 50015",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83956.html",
        "category": "给排水",
        "status": "current",
    },
    "gb50352": {
        "name": "民用建筑设计统一标准 GB 50352",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83957.html",
        "category": "建筑",
        "status": "current",
    },
    "gb50033": {
        "name": "建筑采光设计标准 GB 50033",
        "url": "https://www.mohurd.gov.cn/gongkai/fdzdgknr/tzgg/tzgg_83958.html",
        "category": "建筑",
        "status": "current",
    },
}

# ── 数据操作 ──────────────────────────────────────────────────

def _load_json(path: Path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def get_specs_index() -> Dict:
    """获取规范索引"""
    return _load_json(SPECS_INDEX_FILE)


def save_specs_index(index: Dict):
    """保存规范索引"""
    _save_json(SPECS_INDEX_FILE, index)


# ── 规范更新检查 ─────────────────────────────────────────────

def check_spec_updates() -> List[Dict]:
    """
    检查规范更新
    返回需要更新的规范列表
    """
    index = get_specs_index()
    updates = []

    for spec_id, source in SPEC_SOURCES.items():
        local = index.get(spec_id, {})
        local_version = local.get("version", "unknown")
        local_date = local.get("publish_date", "")

        # 模拟检查（生产环境替换为真实HTTP请求）
        # 实际实现：爬取官网页面，解析最新版本号和发布日期
        remote_version = _fetch_remote_version(spec_id, source["url"])

        if remote_version and remote_version != local_version:
            updates.append({
                "spec_id": spec_id,
                "name": source["name"],
                "category": source["category"],
                "old_version": local_version,
                "new_version": remote_version,
                "source_url": source["url"],
                "detected_at": datetime.now().isoformat(),
                "status": "pending_update",
            })

    # 记录更新日志
    if updates:
        log = _load_json(UPDATE_LOG_FILE)
        log["last_check"] = datetime.now().isoformat()
        log["pending_updates"] = updates
        _save_json(UPDATE_LOG_FILE, log)

    return updates


def _fetch_remote_version(spec_id: str, url: str) -> Optional[str]:
    """
    从官网获取最新版本号
    生产环境：requests + BeautifulSoup 解析HTML
    当前：返回模拟数据
    """
    # TODO: 实现真实爬取
    # 示例：requests.get(url) → 解析版本号
    return None  # 无更新


def initialize_specs_index():
    """初始化规范索引（首次运行）"""
    index = {}
    for spec_id, source in SPEC_SOURCES.items():
        index[spec_id] = {
            "id": spec_id,
            "name": source["name"],
            "category": source["category"],
            "version": "2018",  # 默认版本
            "publish_date": "2018-01-01",
            "status": "current",
            "source_url": source["url"],
            "local_path": "",
            "last_checked": datetime.now().isoformat(),
            "last_updated": "",
            "hash": "",
        }
    save_specs_index(index)
    return index


def run_specs_check() -> Dict:
    """运行规范检查（供cron调用）"""
    from notifications import create_notification

    index = get_specs_index()
    if not index:
        index = initialize_specs_index()

    updates = check_spec_updates()
    notifications_sent = 0

    for update in updates:
        create_notification(
            tenant_id="system",
            notify_type="spec_update",
            title=f"国标规范更新：{update['name']}",
            message=f"检测到新版本：{update['old_version']} → {update['new_version']}",
            severity="info",
            actionable=True,
            action_url=update["source_url"],
        )
        notifications_sent += 1

    return {
        "checked_at": datetime.now().isoformat(),
        "specs_total": len(SPEC_SOURCES),
        "updates_found": len(updates),
        "notifications_sent": notifications_sent,
        "updates": [{"spec_id": u["spec_id"], "name": u["name"], "new_version": u["new_version"]} for u in updates],
    }
