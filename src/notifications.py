"""
notifications.py - 主动智能推送

Phase 6: 项目里程碑提醒 / 规范更新通知 / 订阅到期提醒 / 使用量预警

支持：
- 定时检查（cron触发）
- 基于 ChromaDB 的项目状态变化推送
- 推送渠道：系统内通知 + 可扩展(邮件/微信)
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


# ── 数据文件 ──────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
NOTIFICATIONS_FILE = EMA_DATA_DIR / "notifications.json"
ALERTS_FILE = EMA_DATA_DIR / "alerts.json"
CHECKPOINTS_FILE = EMA_DATA_DIR / "checkpoints.json"


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ── 通知类型 ──────────────────────────────────────────────────

NOTIFICATION_TYPES = {
    "subscription_expiring": "subscription_expiring",   # 订阅即将到期
    "subscription_expired": "subscription_expired",     # 订阅已到期
    "quota_alert": "quota_alert",                       # 配额预警
    "standard_update": "standard_update",               # 国标规范更新
    "project_milestone": "project_milestone",           # 项目里程碑提醒
    "system_update": "system_update",                   # 系统更新通知
    "security_alert": "security_alert",                 # 安全告警
    "usage_summary": "usage_summary",                   # 使用量周报
}


# ── 通知引擎 ──────────────────────────────────────────────────

def create_notification(
    tenant_id: str,
    notify_type: str,
    title: str,
    message: str,
    severity: str = "info",     # info / warning / critical
    actionable: bool = True,
    action_url: str = None,
) -> Dict:
    """
    创建通知

    Args:
        tenant_id: 目标租户
        notify_type: 通知类型（见 NOTIFICATION_TYPES）
        title: 标题
        message: 内容
        severity: info/warning/critical
        actionable: 是否可操作
        action_url: 操作的链接
    """
    notifications = _load_json(NOTIFICATIONS_FILE)

    now = datetime.now().isoformat()
    nid = f"notif_{int(time.time() * 1000)}_{tenant_id[-8:]}"

    notification = {
        "id": nid,
        "tenant_id": tenant_id,
        "type": notify_type,
        "title": title,
        "message": message,
        "severity": severity,
        "actionable": actionable,
        "action_url": action_url,
        "read": False,
        "created_at": now,
    }

    # 按租户分组存储
    if tenant_id not in notifications:
        notifications[tenant_id] = []
    notifications[tenant_id].insert(0, notification)

    # 最多保留100条
    notifications[tenant_id] = notifications[tenant_id][:100]

    _save_json(NOTIFICATIONS_FILE, notifications)
    return notification


def get_notifications(
    tenant_id: str,
    unread_only: bool = False,
    limit: int = 20
) -> list:
    """获取通知列表"""
    notifications = _load_json(NOTIFICATIONS_FILE)
    nlist = notifications.get(tenant_id, [])

    if unread_only:
        nlist = [n for n in nlist if not n.get("read", False)]

    return nlist[:limit]


def mark_read(tenant_id: str, notification_id: str) -> bool:
    """标记通知已读"""
    notifications = _load_json(NOTIFICATIONS_FILE)
    nlist = notifications.get(tenant_id, [])
    for n in nlist:
        if n["id"] == notification_id:
            n["read"] = True
            _save_json(NOTIFICATIONS_FILE, notifications)
            return True
    return False


def mark_all_read(tenant_id: str) -> int:
    """标记全部已读"""
    notifications = _load_json(NOTIFICATIONS_FILE)
    nlist = notifications.get(tenant_id, [])
    count = 0
    for n in nlist:
        if not n.get("read", False):
            n["read"] = True
            count += 1
    _save_json(NOTIFICATIONS_FILE, notifications)
    return count


def get_unread_count(tenant_id: str) -> int:
    """获取未读通知数"""
    notifications = _load_json(NOTIFICATIONS_FILE)
    nlist = notifications.get(tenant_id, [])
    return sum(1 for n in nlist if not n.get("read", False))


# ── 主动检查引擎 ──────────────────────────────────────────────

def run_subscription_check(tenant_id: str) -> list:
    """
    检查订阅状态并生成提醒

    Returns:
        list: 生成的提醒列表
    """
    from subscription import check_subscription

    sub = check_subscription(tenant_id)
    reminders = []

    if sub["status"] == "none":
        return reminders

    days = sub.get("days_remaining", -1)

    if days == 0:
        r = create_notification(
            tenant_id, "subscription_expiring",
            title="🔔 订阅即将到期",
            message=f"您的{sub['plan_name']}订阅将在今天到期，请及时续费以保持服务不中断。",
            severity="critical",
            actionable=True,
            action_url="/settings/subscription",
        )
        reminders.append(r)

    elif 1 <= days <= 7:
        r = create_notification(
            tenant_id, "subscription_expiring",
            title="🔔 订阅即将到期",
            message=f"您的{sub['plan_name']}订阅将在{days}天后到期，请及时续费。",
            severity="warning",
            actionable=True,
            action_url="/settings/subscription",
        )
        reminders.append(r)

    return reminders


def run_quota_check(tenant_id: str) -> list:
    """
    检查配额使用量并生成预警

    Returns:
        list: 生成的预警列表
    """
    from subscription import check_quota

    quota = check_quota(tenant_id)
    alerts = []

    if not quota.get("violations"):
        return alerts

    for v in quota["violations"]:
        r = create_notification(
            tenant_id, "quota_alert",
            title="⚠️ 配额预警",
            message=v,
            severity="warning",
            actionable=True,
            action_url="/settings/subscription?suggest=upgrade",
        )
        alerts.append(r)

    return alerts


def run_standard_update_check() -> list:
    """
    检查国标规范更新（simulate）

    基于 checkpoints 比对来模拟规范版本变化
    """
    checkpoints = _load_json(CHECKPOINTS_FILE)
    now = datetime.now()
    key = now.strftime("%Y-%m-%d")

    if key in checkpoints:
        return []  # 今日已检查

    # --- 模拟检查逻辑 ---
    # 实际生产：对接国家标准网爬虫/API 检查最新版本
    # 这里用模拟数据：每周一检查一次
    if now.weekday() != 0:  # 非周一
        checkpoints[key] = {"checked": True}
        _save_json(CHECKPOINTS_FILE, checkpoints)
        return []

    # 模拟规范更新
    simulated_updates = [
        {
            "code": "GB 50016-2026",
            "name": "建筑设计防火规范",
            "version": "2026版",
            "previous": "2014版（2018局部修订）",
            "effective_date": (now + timedelta(days=30)).strftime("%Y-%m-%d"),
        }
    ]

    for update in simulated_updates:
        # 发给所有付费租户的租户管理员
        from subscription import _load_json as load_sub
        subscribers = load_sub(Path(EMA_DATA_DIR / "subscribers.json"))

        notified = set()
        for tid, sub in subscribers.items():
            if tid in notified:
                continue
            notified.add(tid)

            create_notification(
                tid, "standard_update",
                title="📋 国标规范更新",
                message=f"{update['name']}（{update['code']}）已更新至{update['version']}，将于{update['effective_date']}生效。原有{update['previous']}将同时废止。请确认您的项目是否受影响。",
                severity="info",
                actionable=True,
                action_url="/specs/library",
            )

    checkpoints[key] = {"checked": True, "updates_found": len(simulated_updates)}
    _save_json(CHECKPOINTS_FILE, checkpoints)

    return simulated_updates


def run_daily_checks():
    """
    执行每日主动检查（由 cron/heartbeat 触发）

    遍历所有租户，执行：
    1. 订阅到期检查
    2. 配额使用检查
    3. 规范更新检查

    Returns:
        dict: 检查结果统计
    """
    results = {
        "subscription_checks": 0,
        "subscription_alerts": 0,
        "quota_checks": 0,
        "quota_alerts": 0,
        "standard_updates": 0,
        "errors": [],
    }

    from subscription import _load_json as load_sub
    subscribers = load_sub(Path(EMA_DATA_DIR / "subscribers.json"))

    for tenant_id in list(subscribers.keys()):
        try:
            # 订阅检查
            reminders = run_subscription_check(tenant_id)
            results["subscription_checks"] += 1
            results["subscription_alerts"] += len(reminders)

            # 配额检查
            alerts = run_quota_check(tenant_id)
            results["quota_checks"] += 1
            results["quota_alerts"] += len(alerts)

        except Exception as e:
            results["errors"].append(f"{tenant_id}: {str(e)}")

    # 规范更新检查
    try:
        updates = run_standard_update_check()
        results["standard_updates"] += len(updates)
    except Exception as e:
        results["errors"].append(f"standard_update: {str(e)}")

    return results
