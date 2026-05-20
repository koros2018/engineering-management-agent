#!/usr/bin/env python3
"""EMA 数据自动备份脚本"""
import json, os, shutil, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
DATA_DIR = BASE / "data"
BACKUP_DIR = BASE / "backups"
KEEP_DAYS = 7

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
now = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_name = f"ema_backup_{now}"
backup_path = BACKUP_DIR / backup_name

try:
    shutil.make_archive(str(backup_path), "zip", DATA_DIR)
    size = os.path.getsize(f"{backup_path}.zip") / (1024*1024)
    print(f"✅ 备份完成: {backup_path}.zip ({size:.1f} MB)")

    # 清理过期备份
    cutoff = time.time() - KEEP_DAYS * 86400
    for f in sorted(BACKUP_DIR.glob("ema_backup_*.zip")):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            print(f"🗑️  清理过期: {f.name}")

    # 生成备份清单
    manifest = {"backups": []}
    for f in sorted(BACKUP_DIR.glob("ema_backup_*.zip"), reverse=True):
        manifest["backups"].append({
            "file": f.name,
            "size_mb": round(f.stat().st_size / (1024*1024), 2),
            "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    with open(BACKUP_DIR / "manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    print(f"📊 保留 {len(manifest['backups'])} 个备份")
except Exception as e:
    print(f"❌ 备份失败: {e}")
