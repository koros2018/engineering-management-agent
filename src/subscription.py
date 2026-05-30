"""
subscription.py - 订阅与支付模型

Phase 6: 订阅计划 / 使用量追踪 / 过期检查 / 配额管理
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from utils import load_json as _load_json, save_json as _save_json



# ── 数据文件 ──────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
SUBSCRIBERS_FILE = EMA_DATA_DIR / "subscribers.json"
USAGE_FILE = EMA_DATA_DIR / "usage.json"




# ── 订阅计划定义 ────────────────────────────────────────────────

@dataclass
class Plan:
    """订阅计划"""
    plan_id: str
    name: str                   # 体验版 / 专业版 / 企业版 / 私有部署
    price_yuan: int             # 月费（元）
    projects_per_month: int     # 每月项目数（-1=无限）
    file_size_mb: int           # 单文件大小限制（MB）
    agents_enabled: List[str]   # 可用 Agent
    storage_mb: int             # 存储空间（MB）
    features: List[str]         # 特性列表
    support_level: str          # basic / priority / dedicated


PLANS: Dict[str, Plan] = {
    "free": Plan(
        plan_id="free",
        name="体验版",
        price_yuan=0,
        projects_per_month=3,
        file_size_mb=25,
        agents_enabled=["tech_rd", "safety_compliance", "customer_service"],
        storage_mb=100,
        features=["图纸解析", "基本审图", "3类文档生成", "FAQ支持"],
        support_level="basic",
    ),
    "pro": Plan(
        plan_id="pro",
        name="专业版",
        price_yuan=299,
        projects_per_month=-1,
        file_size_mb=100,
        agents_enabled=["tech_rd", "safety_compliance", "engineering_delivery",
                        "cost_benefit", "market_sales", "customer_service"],
        storage_mb=1024,
        features=["完整图纸解析", "15条审图规则", "5类文档生成",
                  "工程量清单", "SOP/MOP/EOP/LCC", "投标文件辅助",
                  "智能报价", "API集成"],
        support_level="priority",
    ),
    "enterprise": Plan(
        plan_id="enterprise",
        name="企业版",
        price_yuan=999,
        projects_per_month=-1,
        file_size_mb=500,
        agents_enabled=["*"],  # 全部Agent
        storage_mb=10240,
        features=["全功能专业版", "AI改图(DXF)", "几何审查",
                  "国标库扩展", "API集成", "专属技术支持",
                  "多用户协作", "审计日志"],
        support_level="dedicated",
    ),
    "private": Plan(
        plan_id="private",
        name="私有部署",
        price_yuan=-1,  # 议价
        projects_per_month=-1,
        file_size_mb=-1,  # 无限制
        agents_enabled=["*"],
        storage_mb=-1,
        features=["企业内网部署", "数据完全隔离", "定制开发",
                  "终身授权", "年度维保", "私有模型接入"],
        support_level="dedicated",
    ),
}


# ── 订阅管理 ──────────────────────────────────────────────────

def get_plan(plan_id: str) -> Optional[Plan]:
    return PLANS.get(plan_id)


def list_plans() -> list:
    """列出全部计划"""
    return [
        {
            "plan_id": p.plan_id,
            "name": p.name,
            "price_yuan": p.price_yuan,
            "projects_per_month": p.projects_per_month,
            "file_size_mb": p.file_size_mb,
            "features": p.features[:8],
            "support_level": p.support_level,
        }
        for p in PLANS.values()
    ]


def subscribe(tenant_id: str, plan_id: str, duration_months: int = 1) -> Dict:
    """
    租户订阅计划

    Args:
        tenant_id: 租户ID
        plan_id: 计划ID (free/pro/enterprise/private)
        duration_months: 订阅月数

    Returns:
        dict: 订阅信息
    """
    if plan_id not in PLANS:
        raise ValueError(f"无效的订阅计划: {plan_id}")

    subscribers = _load_json(SUBSCRIBERS_FILE)
    plan = PLANS[plan_id]

    now = datetime.now()
    start_at = now.isoformat()
    end_at = (now + timedelta(days=30 * duration_months)).isoformat() if plan.price_yuan > 0 else None

    subscribers[tenant_id] = {
        "tenant_id": tenant_id,
        "plan_id": plan_id,
        "plan_name": plan.name,
        "started_at": start_at,
        "expires_at": end_at,
        "auto_renew": True,
        "status": "active",
        "payment_history": subscribers.get(tenant_id, {}).get("payment_history", []),
    }

    _save_json(SUBSCRIBERS_FILE, subscribers)

    # 初始化使用量
    reset_usage(tenant_id)

    return subscribers[tenant_id]


def get_subscription(tenant_id: str) -> Optional[Dict]:
    """获取租户订阅信息"""
    subscribers = _load_json(SUBSCRIBERS_FILE)
    return subscribers.get(tenant_id)


def check_subscription(tenant_id: str) -> Dict:
    """
    检查订阅状态

    Returns:
        {
            "active": bool,
            "plan_id": str,
            "plan_name": str,
            "expires_at": str or None,
            "days_remaining": int,
            "status": "active" | "expired" | "trial" | "none",
        }
    """
    sub = get_subscription(tenant_id)
    if not sub:
        return {
            "active": False,
            "plan_id": "free",
            "plan_name": "体验版（默认）",
            "expires_at": None,
            "days_remaining": -1,
            "status": "none",
        }

    now = datetime.now()
    expires_at = sub.get("expires_at")
    days_remaining = -1

    if expires_at:
        exp = datetime.fromisoformat(expires_at)
        days_remaining = (exp - now).days

    active = True
    status = sub.get("status", "active")

    if expires_at and days_remaining < 0:
        active = False
        status = "expired"

    return {
        "active": active,
        "plan_id": sub.get("plan_id", "free"),
        "plan_name": sub.get("plan_name", ""),
        "started_at": sub.get("started_at"),
        "expires_at": expires_at,
        "days_remaining": max(0, days_remaining) if active else 0,
        "status": status,
    }


# ── 使用量追踪 ────────────────────────────────────────────────

def _get_current_month_key() -> str:
    now = datetime.now()
    return f"{now.year}-{now.month:02d}"


def reset_usage(tenant_id: str):
    """每月重置使用量"""
    usage = _load_json(USAGE_FILE)
    usage[tenant_id] = {
        "tenant_id": tenant_id,
        "month": _get_current_month_key(),
        "projects_created": 0,
        "files_uploaded": 0,
        "api_calls": 0,
        "storage_used_mb": 0,
        "last_updated": datetime.now().isoformat(),
    }
    _save_json(USAGE_FILE, usage)


def _ensure_current_month(tenant_id: str):
    """确保使用量是当前月份"""
    usage = _load_json(USAGE_FILE)
    current_month = _get_current_month_key()
    if tenant_id not in usage or usage[tenant_id].get("month") != current_month:
        reset_usage(tenant_id)


def track_usage(tenant_id: str, metric: str, amount: int = 1) -> Dict:
    """
    追踪使用量

    metric: projects_created / files_uploaded / api_calls / storage_used_mb
    """
    _ensure_current_month(tenant_id)
    usage = _load_json(USAGE_FILE)

    if tenant_id not in usage:
        reset_usage(tenant_id)
        usage = _load_json(USAGE_FILE)

    usage[tenant_id][metric] = usage[tenant_id].get(metric, 0) + amount
    usage[tenant_id]["last_updated"] = datetime.now().isoformat()
    _save_json(USAGE_FILE, usage)

    return usage[tenant_id]


def get_usage(tenant_id: str) -> Dict:
    """获取当前使用量"""
    _ensure_current_month(tenant_id)
    usage = _load_json(USAGE_FILE)
    return usage.get(tenant_id, {})


def check_quota(tenant_id: str) -> Dict:
    """
    检查配额是否超限

    Returns:
        {
            "can_create_project": bool,
            "can_upload": bool,
            "quota_used": Dict,
            "quota_limit": Dict,
            "violations": List[str],
        }
    """
    sub = check_subscription(tenant_id)
    plan = PLANS.get(sub["plan_id"])
    usage = get_usage(tenant_id)

    if not plan:
        return {"can_create_project": True, "can_upload": True, "violations": []}

    projects_used = usage.get("projects_created", 0)
    storage_used = usage.get("storage_used_mb", 0)

    violations = []

    if plan.projects_per_month > 0 and projects_used >= plan.projects_per_month:
        violations.append(f"本月项目数已达上限（{plan.projects_per_month}个）")

    if plan.storage_mb > 0 and storage_used >= plan.storage_mb:
        violations.append(f"存储空间已达上限（{plan.storage_mb}MB）")

    return {
        "can_create_project": plan.projects_per_month < 0 or projects_used < plan.projects_per_month,
        "can_upload": plan.storage_mb < 0 or storage_used < plan.storage_mb,
        "quota_used": {
            "projects": projects_used,
            "storage_mb": storage_used,
            "api_calls": usage.get("api_calls", 0),
        },
        "quota_limit": {
            "projects": plan.projects_per_month,
            "storage_mb": plan.storage_mb if plan.storage_mb > 0 else "无限制",
        },
        "violations": violations,
        "plan": plan.name,
    }
