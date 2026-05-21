"""
log_stats.py - EMA 日志统计分析模块

功能：
- 解析 JSON 日志文件
- 统计 API 请求量、响应时间、错误率
- 按租户/用户聚合
- 按时间粒度（小时/天）统计趋势
- 热门端点排行
- 错误分布
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional


LOG_DIR = Path(__file__).parent.parent / "src" / "logs"
DATA_DIR = Path(__file__).parent.parent / "data"


# ── 日志解析 ──────────────────────────────────────────────────

def _parse_log_line(line: str) -> Optional[Dict]:
    try:
        return json.loads(line)
    except Exception:
        return None


def _load_logs(since: datetime = None, until: datetime = None) -> List[Dict]:
    """加载指定时间范围的日志"""
    records = []
    today = datetime.now()
    # 最多读最近7天
    for days_ago in range(7):
        d = today - timedelta(days=days_ago)
        log_file = LOG_DIR / f"ema-{d.strftime('%Y-%m-%d')}.log"
        if not log_file.exists():
            continue
        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = _parse_log_line(line)
                    if not rec:
                        continue
                    ts_str = rec.get("timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except Exception:
                        continue
                    if since and ts < since:
                        continue
                    if until and ts > until:
                        continue
                    records.append(rec)
        except Exception:
            continue
    return records


# ── 统计分析 ──────────────────────────────────────────────────

def get_api_stats(since_hours: int = 24) -> Dict:
    """
    API 统计（默认24小时）
    返回：请求量、错误率、平均响应时间、热门端点、错误分布
    """
    since = datetime.now() - timedelta(hours=since_hours)
    records = _load_logs(since=since)

    # 只看 API 请求类日志（来自 api_server）
    api_records = [r for r in records if r.get("logger") in ("ema.api_server", "ema.api")]

    # 路由提取（从 message 中提取 path/method/status）
    # 格式: "POST /api/v1/xxx → 200 (123ms)"
    path_pattern = re.compile(r"(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)\s+→\s+(\d+)")
    duration_pattern = re.compile(r"\((\d+)ms\)")

    total_requests = 0
    total_errors = 0
    total_duration = 0
    duration_count = 0
    path_stats = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0})
    error_types = defaultdict(int)
    hourly_stats = defaultdict(lambda: {"requests": 0, "errors": 0})

    for rec in api_records:
        msg = rec.get("message", "")
        m = path_pattern.search(msg)
        if m:
            method, path, status = m.group(1), m.group(2), int(m.group(3))
            status_category = status // 100
            total_requests += 1

            # 聚合 path（去掉 trailing params）
            base_path = re.sub(r"/[a-f0-9-]{36,}", "/{id}", path)  # 替换 UUID
            base_path = re.sub(r"/\d+", "/{n}", base_path)          # 替换数字ID
            path_stats[base_path]["count"] += 1

            dur_m = duration_pattern.search(msg)
            if dur_m:
                ms = int(dur_m.group(1))
                path_stats[base_path]["total_ms"] += ms
                total_duration += ms
                duration_count += 1

            if status >= 400:
                total_errors += 1
                path_stats[base_path]["errors"] += 1
                error_types[f"{status} {path}"] = error_types[f"{status} {path}"] + 1

            # 小时聚合
            ts_str = rec.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                hour_key = ts.strftime("%Y-%m-%d %H:00")
                hourly_stats[hour_key]["requests"] += 1
                if status >= 400:
                    hourly_stats[hour_key]["errors"] += 1
            except Exception:
                pass
        elif "error" in rec.get("level", "").lower():
            # 非请求日志但有错误
            total_errors += 1
            error_types[rec.get("message", "unknown")] += 1

    # 热门端点
    top_endpoints = sorted(
        [
            {
                "path": p,
                "count": s["count"],
                "errors": s["errors"],
                "avg_ms": round(s["total_ms"] / s["count"], 1) if s["count"] else 0,
                "error_rate": round(s["errors"] / s["count"] * 100, 1) if s["count"] else 0,
            }
            for p, s in path_stats.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:15]

    # 错误排行
    top_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]

    # 小时趋势（最近24小时，填充空缺）
    hourly_list = []
    now = datetime.now()
    for i in range(24):
        h = now - timedelta(hours=23 - i)
        key = h.strftime("%Y-%m-%d %H:00")
        hourly_list.append({
            "hour": key,
            "requests": hourly_stats.get(key, {}).get("requests", 0),
            "errors": hourly_stats.get(key, {}).get("errors", 0),
        })

    error_rate = round(total_errors / total_requests * 100, 2) if total_requests else 0
    avg_response_time = round(total_duration / duration_count, 1) if duration_count else 0

    return {
        "period_hours": since_hours,
        "total_requests": total_requests,
        "total_errors": total_errors,
        "error_rate_pct": error_rate,
        "avg_response_ms": avg_response_time,
        "hourly_trend": hourly_list,
        "top_endpoints": top_endpoints,
        "top_errors": [{"msg": k, "count": v} for k, v in top_errors],
        "generated_at": datetime.now().isoformat(),
    }


def get_user_activity(since_hours: int = 168) -> Dict:
    """
    用户活动统计（默认7天）
    """
    since = datetime.now() - timedelta(hours=since_hours)
    records = _load_logs(since=since)

    user_requests = defaultdict(int)
    user_errors = defaultdict(int)
    user_agents = defaultdict(set)

    for rec in records:
        uid = rec.get("user_id") or rec.get("extra_data", {}).get("user_id", "anonymous")
        if uid and uid != "None":
            user_requests[uid] += 1
            if rec.get("level") in ("ERROR", "CRITICAL"):
                user_errors[uid] += 1

    top_users = sorted(
        [
            {"user_id": u, "requests": c, "errors": user_errors.get(u, 0)}
            for u, c in user_requests.items()
        ],
        key=lambda x: x["requests"],
        reverse=True,
    )[:20]

    return {
        "period_hours": since_hours,
        "total_users": len(user_requests),
        "top_users": top_users,
        "generated_at": datetime.now().isoformat(),
    }


def get_error_summary(since_hours: int = 168) -> Dict:
    """
    错误汇总（最近7天）
    """
    since = datetime.now() - timedelta(hours=since_hours)
    records = _load_logs(since=since)

    errors = [r for r in records if r.get("level") in ("ERROR", "CRITICAL")]

    error_groups = defaultdict(int)
    for e in errors:
        msg = e.get("message", "")[:120]  # 截断
        error_groups[msg] += 1

    critical_count = sum(1 for e in errors if e.get("level") == "CRITICAL")

    return {
        "period_hours": since_hours,
        "total_errors": len(errors),
        "critical_errors": critical_count,
        "top_error_messages": [
            {"msg": m, "count": c} for m, c in sorted(error_groups.items(), key=lambda x: x[1], reverse=True)[:20]
        ],
        "generated_at": datetime.now().isoformat(),
    }


def get_full_stats() -> Dict:
    """
    全量统计（一次性返回所有维度）
    """
    api_24h = get_api_stats(24)
    api_7d = get_api_stats(168)
    user_act = get_user_activity(168)
    err_sum = get_error_summary(168)

    return {
        "api_24h": api_24h,
        "api_7d": api_7d,
        "user_activity": user_act,
        "error_summary": err_sum,
        "generated_at": datetime.now().isoformat(),
    }