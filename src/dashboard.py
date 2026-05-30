"""
dashboard.py - 数据看板

Phase 8: 项目统计 / 使用趋势 / 收益报表 / Agent使用热度 / 租户活跃度
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List
from utils import load_json as _load_json, save_json as _save_json



EMA_DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"



# ── 项目统计 ──────────────────────────────────────────────────

def get_project_stats() -> Dict:
    """项目总览统计"""
    tenants_dir = EMA_DATA_DIR / "tenants"
    total_projects = 0
    total_files = 0
    total_output = 0
    tenant_count = 0

    if tenants_dir.exists():
        for td in tenants_dir.iterdir():
            if td.is_dir():
                tenant_count += 1
                projects_dir = td / "projects"
                if projects_dir.exists():
                    for pd in projects_dir.iterdir():
                        if pd.is_dir():
                            total_projects += 1
                            total_files += sum(1 for _ in pd.rglob("*") if _.is_file())

    if OUTPUT_DIR.exists():
        total_output = sum(1 for _ in OUTPUT_DIR.rglob("*") if _.is_file())

    return {
        "tenants": tenant_count,
        "projects": total_projects,
        "files": total_files,
        "outputs": total_output,
    }


# ── 使用趋势 ──────────────────────────────────────────────────

def get_usage_trends(days: int = 30) -> Dict:
    """使用趋势（近 N 天）"""
    usage_file = EMA_DATA_DIR / "usage.json"
    if not usage_file.exists():
        return {"trends": [], "total": {"api_calls": 0, "projects": 0, "storage_mb": 0}}

    usage = _load_json(usage_file)

    # 聚合所有租户的日使用量
    daily = {}
    total = {"api_calls": 0, "projects": 0, "storage_mb": 0}

    for tid, u in usage.items():
        month = u.get("month", "")
        if month:
            daily_key = month + "-01"  # 月级别聚合
            if daily_key not in daily:
                daily[daily_key] = {"api_calls": 0, "projects": 0, "storage_mb": 0}
            daily[daily_key]["api_calls"] += u.get("api_calls", 0)
            daily[daily_key]["projects"] += u.get("projects_created", 0)
            daily[daily_key]["storage_mb"] += u.get("storage_used_mb", 0)

    for d in daily.values():
        total["api_calls"] += d["api_calls"]
        total["projects"] += d["projects"]
        total["storage_mb"] += d["storage_mb"]

    # 排序
    trends = sorted(
        [{"date": k, **v} for k, v in daily.items()],
        key=lambda x: x["date"],
        reverse=True,
    )[:days]

    return {"trends": trends, "total": total}


# ── 收益报表 ──────────────────────────────────────────────────

def get_revenue_report() -> Dict:
    """收益报表"""
    payments = _load_json(EMA_DATA_DIR / "payments.json")
    orders = _load_json(EMA_DATA_DIR / "orders.json")
    subscribers = _load_json(EMA_DATA_DIR / "subscribers.json")

    total_revenue = 0.0
    paid_count = 0
    plan_distribution = {}
    monthly_revenue = {}

    for pid, p in payments.items():
        if p.get("status") == "success":
            total_revenue += p.get("amount", 0)
            paid_count += 1

            paid_at = p.get("paid_at", "")
            if paid_at:
                month_key = paid_at[:7]
                monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + p.get("amount", 0)

    for tid, sub in subscribers.items():
        plan_id = sub.get("plan_id", "free")
        plan_distribution[plan_id] = plan_distribution.get(plan_id, 0) + 1

    # 订阅总数
    total_subscribers = len(subscribers)
    active_subscribers = sum(
        1 for s in subscribers.values()
        if s.get("status") == "active"
    )

    # 本月收入
    this_month = datetime.now().strftime("%Y-%m")
    revenue_this_month = monthly_revenue.get(this_month, 0)

    return {
        "total_revenue": round(total_revenue, 2),
        "paid_orders": paid_count,
        "revenue_this_month": round(revenue_this_month, 2),
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "plan_distribution": plan_distribution,
        "monthly_revenue": dict(sorted(monthly_revenue.items(), reverse=True)[:12]),
    }


# ── Agent 使用热度 ────────────────────────────────────────────

def get_agent_heatmap() -> Dict:
    """Agent 使用热度（基于 ChromaDB conversations）"""
    try:
        from memory import get_chroma_store
        store = get_chroma_store()

        agent_counts = {
            "tech_rd": 0, "safety_compliance": 0, "market_sales": 0,
            "engineering_delivery": 0, "cost_benefit": 0, "customer_service": 0,
        }

        collection = store.get_collection("conversations")
        if collection and collection.count() > 0:
            results = collection.get(limit=min(1000, collection.count()))
            if results and results.get('metadatas'):
                for meta in results['metadatas']:
                    agent_id = meta.get('agent_id', '')
                    if agent_id in agent_counts:
                        agent_counts[agent_id] += 1
    except Exception:
        pass

    # 排序
    sorted_agents = sorted(agent_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "heatmap": [{"agent_id": aid, "count": c} for aid, c in sorted_agents],
        "total_conversations": sum(c for _, c in sorted_agents),
        "most_active": sorted_agents[0][0] if sorted_agents else "N/A",
    }


# ── 综合看板 ──────────────────────────────────────────────────

def get_dashboard() -> Dict:
    """综合看板（单次调用获取全部）"""
    stats = get_project_stats()
    trends = get_usage_trends(7)
    revenue = get_revenue_report()
    heatmap = get_agent_heatmap()

    return {
        "timestamp": datetime.now().isoformat(),
        "project_stats": stats,
        "usage_summary": {
            "total_api_calls": trends["total"]["api_calls"],
            "total_projects": trends["total"]["projects"],
            "storage_mb": trends["total"]["storage_mb"],
        },
        "revenue": revenue,
        "agent_usage": heatmap,
    }