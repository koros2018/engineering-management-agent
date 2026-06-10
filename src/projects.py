"""
projects.py - 项目管理 + 里程碑追踪

功能：
- 项目CRUD（创建/编辑/删除）
- 里程碑管理（设计/施工/验收/交付）
- 自动里程碑提醒（cron触发）
- 项目状态流转（规划中→设计中→施工中→验收中→已交付）
"""

import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from utils import load_json, save_json

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
PROJECTS_FILE = EMA_DATA_DIR / "projects.json"
MILESTONES_FILE = EMA_DATA_DIR / "milestones.json"


# ── 项目状态 ──────────────────────────────────────────────────

PROJECT_STATUSES = {
    "planning":   {"label": "📋 规划中",   "color": "#6366f1", "order": 0},
    "designing":  {"label": "✏️ 设计中",   "color": "#3b82f6", "order": 1},
    "reviewing":  {"label": "🔍 审查中",   "color": "#f59e0b", "order": 2},
    "constructing": {"label": "🏗️ 施工中", "color": "#10b981", "order": 3},
    "accepting":  {"label": "✅ 验收中",   "color": "#8b5cf6", "order": 4},
    "delivered":  {"label": "📦 已交付",   "color": "#6b7280", "order": 5},
    "paused":     {"label": "⏸️ 已暂停",   "color": "#ef4444", "order": 6},
}

# 里程碑类型
MILESTONE_TYPES = {
    "design_start":    "设计启动",
    "design_review":   "设计审查",
    "design_complete": "设计完成",
    "construction_start": "施工启动",
    "construction_50": "施工50%",
    "construction_100": "施工完成",
    "acceptance":      "竣工验收",
    "delivery":        "项目交付",
    "custom":          "自定义",
}


# ── 项目 CRUD ────────────────────────────────────────────────

def create_project(tenant_id: str, name: str, description: str = "",
                   project_type: str = "construction",
                   budget: float = 0, start_date: str = None,
                   end_date: str = None, created_by: str = "") -> Dict:
    """创建项目"""
    projects = load_json(PROJECTS_FILE)
    pid = f"proj_{uuid.uuid4().hex[:12]}"
    now = datetime.now().isoformat()
    projects[pid] = {
        "id": pid,
        "tenant_id": tenant_id,
        "name": name,
        "description": description,
        "type": project_type,
        "status": "planning",
        "budget": budget,
        "start_date": start_date or now[:10],
        "end_date": end_date or "",
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
        "file_count": 0,
        "review_count": 0,
    }
    save_json(PROJECTS_FILE, projects)
    return projects[pid]


def update_project(project_id: str, **kwargs) -> Optional[Dict]:
    """更新项目"""
    projects = load_json(PROJECTS_FILE)
    if project_id not in projects:
        return None
    p = projects[project_id]
    for k, v in kwargs.items():
        if k in p and v is not None:
            p[k] = v
    p["updated_at"] = datetime.now().isoformat()
    save_json(PROJECTS_FILE, projects)
    return p


def delete_project(project_id: str) -> bool:
    """删除项目"""
    projects = load_json(PROJECTS_FILE)
    if project_id not in projects:
        return False
    del projects[project_id]
    save_json(PROJECTS_FILE, projects)
    # 清理里程碑
    milestones = load_json(MILESTONES_FILE)
    for mid in [k for k, v in milestones.items() if v.get("project_id") == project_id]:
        del milestones[mid]
    save_json(MILESTONES_FILE, milestones)
    return True


def list_projects(tenant_id: str = None, status: str = None) -> List[Dict]:
    """列出项目"""
    projects = load_json(PROJECTS_FILE)
    result = list(projects.values())
    if tenant_id:
        result = [p for p in result if p.get("tenant_id") == tenant_id]
    if status:
        result = [p for p in result if p.get("status") == status]
    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return result


def get_project(project_id: str) -> Optional[Dict]:
    """获取项目详情"""
    projects = load_json(PROJECTS_FILE)
    return projects.get(project_id)


# ── 里程碑管理 ──────────────────────────────────────────────

def add_milestone(project_id: str, milestone_type: str, title: str,
                  due_date: str, description: str = "",
                  notify_days_before: int = 3) -> Dict:
    """添加里程碑"""
    milestones = load_json(MILESTONES_FILE)
    mid = f"ms_{uuid.uuid4().hex[:10]}"
    now = datetime.now().isoformat()
    milestones[mid] = {
        "id": mid,
        "project_id": project_id,
        "type": milestone_type,
        "title": title,
        "description": description,
        "due_date": due_date,
        "status": "pending",  # pending / completed / overdue
        "notify_days_before": notify_days_before,
        "notified": False,
        "completed_at": None,
        "created_at": now,
    }
    save_json(MILESTONES_FILE, milestones)
    return milestones[mid]


def complete_milestone(milestone_id: str) -> Optional[Dict]:
    """完成里程碑"""
    milestones = load_json(MILESTONES_FILE)
    if milestone_id not in milestones:
        return None
    milestones[milestone_id]["status"] = "completed"
    milestones[milestone_id]["completed_at"] = datetime.now().isoformat()
    save_json(MILESTONES_FILE, milestones)
    return milestones[milestone_id]


def list_milestones(project_id: str = None) -> List[Dict]:
    """列出里程碑"""
    milestones = load_json(MILESTONES_FILE)
    result = list(milestones.values())
    if project_id:
        result = [m for m in result if m.get("project_id") == project_id]
    result.sort(key=lambda x: x.get("due_date", ""))
    return result


# ── 里程碑检查 + 通知 ────────────────────────────────────────

def check_milestones() -> List[Dict]:
    """
    检查即将到期和已过期的里程碑
    返回需要通知的里程碑列表
    """
    milestones = load_json(MILESTONES_FILE)
    projects = load_json(PROJECTS_FILE)
    now = datetime.now()
    alerts = []

    for mid, ms in milestones.items():
        if ms.get("status") == "completed":
            continue

        due_str = ms.get("due_date", "")
        if not due_str:
            continue

        try:
            due = datetime.strptime(due_str[:10], "%Y-%m-%d")
        except ValueError:
            continue

        days_until = (due - now).days
        notify_before = ms.get("notify_days_before", 3)

        if days_until < 0:
            # 已过期
            ms["status"] = "overdue"
            alerts.append({
                "milestone": ms,
                "project": projects.get(ms.get("project_id"), {}),
                "type": "overdue",
                "message": f"⚠️ 里程碑「{ms['title']}」已过期 {abs(days_until)} 天",
                "severity": "critical",
            })
        elif days_until <= notify_before and not ms.get("notified"):
            # 即将到期
            alerts.append({
                "milestone": ms,
                "project": projects.get(ms.get("project_id"), {}),
                "type": "upcoming",
                "message": f"📅 里程碑「{ms['title']}」{days_until}天后到期（{due_str[:10]}）",
                "severity": "warning" if days_until <= 1 else "info",
            })
            ms["notified"] = True

    save_json(MILESTONES_FILE, milestones)
    return alerts


def run_project_checks() -> Dict:
    """运行所有项目检查（供cron调用）"""
    from notifications import create_notification

    milestone_alerts = check_milestones()
    notifications_sent = 0

    for alert in milestone_alerts:
        ms = alert["milestone"]
        proj = alert["project"]
        tenant_id = proj.get("tenant_id", "system")

        create_notification(
            tenant_id=tenant_id,
            notify_type="project_milestone",
            title=f"项目里程碑提醒：{ms['title']}",
            message=alert["message"],
            severity=alert["severity"],
            actionable=True,
            action_url=f"#/project/{ms.get('project_id')}",
        )
        notifications_sent += 1

    return {
        "checked_at": datetime.now().isoformat(),
        "milestone_alerts": len(milestone_alerts),
        "notifications_sent": notifications_sent,
        "alerts": [{"type": a["type"], "message": a["message"]} for a in milestone_alerts],
    }
